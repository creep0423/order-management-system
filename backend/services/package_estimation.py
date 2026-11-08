"""Deterministic rules-based package estimation for Batch J1.

Data flow::

    OrderService
      -> PackageEstimationService.estimate_for_order(order, products)
           -> PackagingRuleSetReader.get_active(checked_at)
           -> PackageEstimationService.estimate(order, products, ruleset)
                -> SkuPackagingSpec / PackageMaterialSpec lookups
                -> sequential first-fit allocation (volume + gross weight)
                -> quantity conservation + split policy verification
                -> Package / PackageProvenance construction
      -> PackageEstimationResult -> OrderDetailResult.packages

Boundaries enforced here:

- Product physical data (``weight_g``, ``dimensions_mm``, ``volume_mm3``,
  ``volumetric_gross_weight_kg``) is **never** read. Package dimensions, unit
  weights and packaging weights come only from the ruleset. This is what D-019
  and contract §4.4 require: products are only SKU lookup inputs.
- Every failure returns the frozen public reason codes
  ``PACKAGE_RULES_NOT_CONFIGURED`` or ``PACKAGE_DATA_INCOMPLETE``; finer causes
  stay in internal ``PackageEstimationDiagnostic`` categories.
- The allocation strategy is synthetic-only. It is a deterministic first-fit
  over packaged-unit volume and gross weight, not a production three-dimensional
  bin packing algorithm (DEC-3 open, DEC-4 open).
"""

from __future__ import annotations

from collections.abc import Callable
from datetime import UTC, datetime
from decimal import Decimal
from typing import Protocol

from pydantic import ValidationError

from backend.models import Order, Package, PackageItem, PackageItemReference, Product
from backend.models.package import (
    PackageDiagnosticCategory,
    PackageEstimationDiagnostic,
    PackageEstimationResult,
    PackageEstimationStatus,
    PackageProvenance,
    PackageReasonCode,
    PackageSource,
    PackageWeight,
    make_input_fingerprint,
)
from backend.models.packaging_rules import (
    PackageMaterialSpec,
    PackagingRuleSet,
    SkuPackagingSpec,
    SyntheticMaterialSelection,
    SyntheticPackingStrategy,
)
from backend.services.packaging_rules import (
    PackagingRulesConfigurationError,
    PackagingRuleSetReader,
)


class PackageEstimationSupport(Protocol):
    """Service surface OrderService depends on."""

    def estimate_for_order(
        self, order: Order, products: tuple[Product, ...]
    ) -> PackageEstimationResult: ...


class _OpenPackage:
    """Mutable accumulator used only while building immutable domain models."""

    def __init__(self, material: PackageMaterialSpec) -> None:
        self.material = material
        self.item_volume_mm3 = Decimal("0")
        self.item_weight_g = Decimal("0")
        self.allocations: dict[int, tuple[str, int]] = {}
        self.unit_weights: dict[int, Decimal] = {}

    @property
    def skus(self) -> frozenset[str]:
        return frozenset(sku for sku, _quantity in self.allocations.values())

    def add(self, line_index: int, spec: SkuPackagingSpec) -> None:
        sku, quantity = self.allocations.get(line_index, (spec.sku, 0))
        self.allocations[line_index] = (sku, quantity + 1)
        self.unit_weights[line_index] = spec.unit_weight_g
        unit_volume = spec.packed_unit_dimensions_mm.volume_mm3
        self.item_volume_mm3 += unit_volume
        self.item_weight_g += spec.unit_weight_g

    def can_accept(
        self,
        spec: SkuPackagingSpec,
        *,
        allow_mixed_sku: bool,
    ) -> bool:
        if self.material.material_id not in spec.compatible_material_ids:
            return False
        if not allow_mixed_sku and self.skus - {spec.sku}:
            return False

        unit_volume = spec.packed_unit_dimensions_mm.volume_mm3
        if self.item_volume_mm3 + unit_volume > self.material.inner_dimensions_mm.volume_mm3:
            return False

        projected_weight = self.item_weight_g + spec.unit_weight_g + self.material.tare_weight_g
        return projected_weight <= self.material.max_gross_weight_g


class PackageEstimationService:
    """Produce at most one deterministic package set, or a stable failure."""

    def __init__(
        self,
        rules_reader: PackagingRuleSetReader,
        clock: Callable[[], datetime] | None = None,
    ) -> None:
        self._rules_reader = rules_reader
        self._clock = clock or (lambda: datetime.now(UTC))

    def estimate_for_order(
        self, order: Order, products: tuple[Product, ...]
    ) -> PackageEstimationResult:
        """Resolve the active ruleset and estimate packages for one order."""

        checked_at = self._clock()
        try:
            ruleset = self._rules_reader.get_active(checked_at)
        except PackagingRulesConfigurationError:
            return self._failure(
                checked_at,
                PackageReasonCode.PACKAGE_RULES_NOT_CONFIGURED,
                PackageDiagnosticCategory.RULES_NOT_CONFIGURED,
                safe_detail="no active packaging ruleset is configured",
            )
        return self.estimate(order, products, ruleset)

    def estimate(
        self,
        order: Order,
        products: tuple[Product, ...],
        rules: PackagingRuleSet,
    ) -> PackageEstimationResult:
        """Estimate packages from explicit order items and an immutable ruleset."""

        checked_at = self._clock()

        # Defence in depth for the Batch J1 synthetic boundary. `synthetic_only`
        # is typed Literal[True] so a validated ruleset cannot claim production
        # status, but a bypassed/corrupted publication (model_construct) must not
        # be able to execute and be reported as production packaging.
        if not rules.synthetic_only:
            return self._failure(
                checked_at,
                PackageReasonCode.PACKAGE_RULES_NOT_CONFIGURED,
                PackageDiagnosticCategory.RULES_NOT_CONFIGURED,
                ruleset=rules,
                safe_detail="only synthetic-only rulesets may run in Batch J1",
            )

        if not order.items:
            return self._failure(
                checked_at,
                PackageReasonCode.PACKAGE_DATA_INCOMPLETE,
                PackageDiagnosticCategory.INVALID_INPUT,
                ruleset=rules,
                safe_detail="order has no order lines to allocate",
            )
        if len(products) != len(order.items) or any(
            product.sku != item.sku for item, product in zip(order.items, products, strict=True)
        ):
            return self._failure(
                checked_at,
                PackageReasonCode.PACKAGE_DATA_INCOMPLETE,
                PackageDiagnosticCategory.INVALID_INPUT,
                ruleset=rules,
                safe_detail="order lines and product associations do not match",
            )

        policies = rules.ordered_policies()
        if not policies:
            return self._failure(
                checked_at,
                PackageReasonCode.PACKAGE_DATA_INCOMPLETE,
                PackageDiagnosticCategory.RULES_NOT_CONFIGURED,
                ruleset=rules,
                safe_detail="ruleset declares no packing policy",
            )
        policy = policies[0]

        if not policy.synthetic_only:
            return self._failure(
                checked_at,
                PackageReasonCode.PACKAGE_RULES_NOT_CONFIGURED,
                PackageDiagnosticCategory.RULES_NOT_CONFIGURED,
                ruleset=rules,
                safe_detail="only synthetic-only packing policies may run in Batch J1",
            )

        if policy.strategy is not SyntheticPackingStrategy.SEQUENTIAL_FIRST_FIT:
            return self._failure(
                checked_at,
                PackageReasonCode.PACKAGE_RULES_NOT_CONFIGURED,
                PackageDiagnosticCategory.RULES_NOT_CONFIGURED,
                ruleset=rules,
                safe_detail="packing strategy is not implemented",
            )
        if policy.material_selection is not SyntheticMaterialSelection.SMALLEST_VOLUME_FIT:
            return self._failure(
                checked_at,
                PackageReasonCode.PACKAGE_RULES_NOT_CONFIGURED,
                PackageDiagnosticCategory.RULES_NOT_CONFIGURED,
                ruleset=rules,
                safe_detail="material selection strategy is not implemented",
            )

        specs: list[SkuPackagingSpec] = []
        for item in order.items:
            spec = rules.sku_spec_for(item.sku)
            if spec is None:
                return self._failure(
                    checked_at,
                    PackageReasonCode.PACKAGE_DATA_INCOMPLETE,
                    PackageDiagnosticCategory.SKU_SPEC_MISSING,
                    ruleset=rules,
                    sku=item.sku,
                    safe_detail="sku packaging specification is missing",
                )
            if not any(
                rules.material_for(material_id) is not None
                for material_id in spec.compatible_material_ids
            ):
                return self._failure(
                    checked_at,
                    PackageReasonCode.PACKAGE_DATA_INCOMPLETE,
                    PackageDiagnosticCategory.MATERIAL_MISSING,
                    ruleset=rules,
                    sku=item.sku,
                    safe_detail="no compatible packaging material is available",
                )
            specs.append(spec)

        open_packages: list[_OpenPackage] = []
        for line_index, (item, spec) in enumerate(zip(order.items, specs, strict=True)):
            for _unit in range(item.quantity):
                target = next(
                    (
                        candidate
                        for candidate in open_packages
                        if candidate.can_accept(spec, allow_mixed_sku=policy.allow_mixed_sku)
                    ),
                    None,
                )
                if target is None:
                    material = self._select_material(rules, spec)
                    if material is None:
                        return self._failure(
                            checked_at,
                            PackageReasonCode.PACKAGE_DATA_INCOMPLETE,
                            PackageDiagnosticCategory.CAPACITY_EXCEEDED,
                            ruleset=rules,
                            sku=spec.sku,
                            safe_detail="no compatible material can hold one packaged unit",
                        )
                    target = _OpenPackage(material)
                    open_packages.append(target)
                target.add(line_index, spec)

        conservation_failure = self._first_conservation_failure(order, open_packages)
        if conservation_failure is not None:
            return self._failure(
                checked_at,
                PackageReasonCode.PACKAGE_DATA_INCOMPLETE,
                PackageDiagnosticCategory.QUANTITY_CONSERVATION,
                ruleset=rules,
                safe_detail=conservation_failure,
            )

        if not policy.allow_split:
            split_line = self._first_split_line(open_packages)
            if split_line is not None:
                return self._failure(
                    checked_at,
                    PackageReasonCode.PACKAGE_DATA_INCOMPLETE,
                    PackageDiagnosticCategory.CAPACITY_EXCEEDED,
                    ruleset=rules,
                    sku=order.items[split_line].sku,
                    safe_detail="packing policy forbids splitting one order line",
                )

        try:
            packages = self._build_packages(order, open_packages, rules, checked_at)
            return PackageEstimationResult(
                status=PackageEstimationStatus.AVAILABLE,
                reason_code=None,
                checked_at=checked_at,
                source=PackageSource.RULES,
                ruleset_id=rules.ruleset_id,
                ruleset_version=rules.version,
                synthetic_ruleset=rules.synthetic_only,
                packages=packages,
                diagnostics=(),
            )
        except (ValidationError, ArithmeticError, ValueError):
            return self._failure(
                checked_at,
                PackageReasonCode.PACKAGE_DATA_INCOMPLETE,
                PackageDiagnosticCategory.INTERNAL_ERROR,
                ruleset=rules,
                safe_detail="package projection failed validation",
            )

    def _select_material(
        self, rules: PackagingRuleSet, spec: SkuPackagingSpec
    ) -> PackageMaterialSpec | None:
        """Choose the smallest compatible material that fits one packaged unit."""

        unit_volume = spec.packed_unit_dimensions_mm.volume_mm3
        candidates = [
            material
            for material_id in spec.compatible_material_ids
            if (material := rules.material_for(material_id)) is not None
            and unit_volume <= material.inner_dimensions_mm.volume_mm3
            and spec.unit_weight_g + material.tare_weight_g <= material.max_gross_weight_g
        ]
        if not candidates:
            return None
        return min(
            candidates,
            key=lambda material: (material.inner_dimensions_mm.volume_mm3, material.material_id),
        )

    @staticmethod
    def _first_conservation_failure(order: Order, packages: list[_OpenPackage]) -> str | None:
        allocated: dict[int, int] = {}
        for package in packages:
            for line_index, (_sku, quantity) in package.allocations.items():
                allocated[line_index] = allocated.get(line_index, 0) + quantity

        if len(allocated) != len(order.items):
            return "allocation does not cover every order line"
        for line_index, item in enumerate(order.items):
            if allocated.get(line_index, 0) != item.quantity:
                return "packaged quantity does not equal the ordered quantity"
        return None

    @staticmethod
    def _first_split_line(packages: list[_OpenPackage]) -> int | None:
        seen: dict[int, int] = {}
        for package in packages:
            for line_index in package.allocations:
                seen[line_index] = seen.get(line_index, 0) + 1
        for line_index, occurrences in sorted(seen.items()):
            if occurrences > 1:
                return line_index
        return None

    def _build_packages(
        self,
        order: Order,
        open_packages: list[_OpenPackage],
        rules: PackagingRuleSet,
        checked_at: datetime,
    ) -> tuple[Package, ...]:
        lines = tuple(
            (line_index, item.sku, item.quantity) for line_index, item in enumerate(order.items)
        )
        fingerprint = make_input_fingerprint(order.order_no, lines, rules.ruleset_id, rules.version)

        packages: list[Package] = []
        for index, open_package in enumerate(open_packages, start=1):
            material = open_package.material
            items = tuple(
                PackageItem(
                    order_item_ref=PackageItemReference(
                        order_number=order.order_no, line_index=line_index
                    ),
                    sku=sku,
                    quantity=quantity,
                )
                for line_index, (sku, quantity) in sorted(open_package.allocations.items())
            )
            packaging_weight = material.tare_weight_g
            packages.append(
                Package(
                    package_id=f"PKG-{index:03d}",
                    order_number=order.order_no,
                    source=PackageSource.RULES,
                    items=items,
                    dimensions=material.outer_dimensions_mm,
                    weight=PackageWeight(
                        item_weight_g=open_package.item_weight_g,
                        packaging_weight_g=packaging_weight,
                        gross_weight_g=open_package.item_weight_g + packaging_weight,
                        volumetric_weight_kg=None,
                        chargeable_weight_kg=None,
                    ),
                    material_id=material.material_id,
                    ruleset_id=rules.ruleset_id,
                    ruleset_version=rules.version,
                    estimated_at=checked_at,
                    provenance=PackageProvenance(
                        source=PackageSource.RULES,
                        source_revision=rules.source_revision,
                        ruleset_id=rules.ruleset_id,
                        ruleset_version=rules.version,
                        input_fingerprint=fingerprint,
                        generated_at=checked_at,
                    ),
                )
            )
        return tuple(packages)

    @staticmethod
    def _failure(
        checked_at: datetime,
        reason: PackageReasonCode,
        category: PackageDiagnosticCategory,
        *,
        ruleset: PackagingRuleSet | None = None,
        sku: str | None = None,
        material_id: str | None = None,
        safe_detail: str | None = None,
    ) -> PackageEstimationResult:
        return PackageEstimationResult(
            status=PackageEstimationStatus.UNAVAILABLE,
            reason_code=reason,
            checked_at=checked_at,
            source=None,
            ruleset_id=ruleset.ruleset_id if ruleset is not None else None,
            ruleset_version=ruleset.version if ruleset is not None else None,
            synthetic_ruleset=ruleset.synthetic_only if ruleset is not None else False,
            packages=(),
            diagnostics=(
                PackageEstimationDiagnostic(
                    category=category,
                    sku=sku,
                    material_id=material_id,
                    ruleset_id=ruleset.ruleset_id if ruleset is not None else None,
                    ruleset_version=ruleset.version if ruleset is not None else None,
                    safe_detail=safe_detail,
                ),
            ),
        )
