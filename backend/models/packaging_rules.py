"""Read-only, versioned packaging rules (D-019, D-020, D-021) for Batch J1.

Frozen contract reference: ``docs/PHASE6_CONTRACT.md`` §5.1 defines the minimal
ruleset envelope (``ruleset_id``, ``version``, effective window,
``source_revision``, ``sku_specs``, ``materials``, ``policies``).

Batch J1 boundary: DEC-1 (full ``PackingPolicy`` field schema), DEC-2
(orientation / fragile / stacking / dangerous-goods placement), DEC-3
(production allocation algorithm) and DEC-4 (material selection strategy) are
still open business decisions. This module therefore implements only a closed,
explicitly synthetic policy shape. It does not invent match-criteria fields, and
a ruleset that claims to be non-synthetic is rejected so that synthetic packing
behaviour can never be mistaken for an approved production rule.
"""

from __future__ import annotations

from datetime import datetime, timedelta
from enum import StrEnum
from typing import Literal

from pydantic import AwareDatetime, BaseModel, ConfigDict, Field, field_validator, model_validator

from backend.models.package import PackageDimensions, PositiveDecimal


class RulesDomainModel(BaseModel):
    """Immutable base model for read-only packaging rules."""

    model_config = ConfigDict(frozen=True, extra="forbid")


class SyntheticPackingStrategy(StrEnum):
    """The only allocation strategy implemented in Batch J1.

    This is a deterministic sequential first-fit over packaged unit volume and
    gross weight. It is **not** a production three-dimensional bin packing
    algorithm; DEC-3 must approve any production strategy.
    """

    SEQUENTIAL_FIRST_FIT = "sequential_first_fit"


class SyntheticMaterialSelection(StrEnum):
    """The only material selection strategy implemented in Batch J1.

    DEC-4 (production material selection policy) remains open; this closed
    choice keeps J1 deterministic without claiming production semantics.
    """

    SMALLEST_VOLUME_FIT = "smallest_volume_fit"


class SkuPackagingSpec(RulesDomainModel):
    """Packaging specification for one SKU.

    ``unit_weight_g`` and ``packed_unit_dimensions_mm`` are packaging facts from
    the ruleset. They must never be derived from ``Product.weight_g`` or
    ``Product.dimensions_mm``; the estimation service reads no product physical
    data at all.
    """

    sku: str = Field(min_length=1, max_length=200)
    unit_weight_g: PositiveDecimal
    packed_unit_dimensions_mm: PackageDimensions
    compatible_material_ids: tuple[str, ...] = Field(min_length=1)
    handling_class: str | None = Field(default=None, max_length=100)

    @field_validator("compatible_material_ids")
    @classmethod
    def material_ids_must_be_unique_and_clean(cls, value: tuple[str, ...]) -> tuple[str, ...]:
        if any(not material_id.strip() for material_id in value):
            raise ValueError("compatible material ids must not be blank")
        if len(value) != len(set(value)):
            raise ValueError("compatible material ids must be unique")
        return value


class PackageMaterialSpec(RulesDomainModel):
    """One packaging material available to the ruleset.

    ``inner_dimensions_mm`` defines usable capacity; ``outer_dimensions_mm`` is
    the package's physical size. ``tare_weight_g`` is the packaging weight, never
    a guess.
    """

    material_id: str = Field(min_length=1, max_length=200)
    inner_dimensions_mm: PackageDimensions
    outer_dimensions_mm: PackageDimensions
    tare_weight_g: PositiveDecimal
    max_gross_weight_g: PositiveDecimal

    @model_validator(mode="after")
    def outer_must_contain_inner(self) -> PackageMaterialSpec:
        if self.outer_dimensions_mm.volume_mm3 < self.inner_dimensions_mm.volume_mm3:
            raise ValueError("outer material volume cannot be smaller than inner capacity")
        if self.max_gross_weight_g <= self.tare_weight_g:
            raise ValueError("max_gross_weight_g must exceed the material tare weight")
        return self


class PackingPolicy(RulesDomainModel):
    """Minimal synthetic-only packing policy for Batch J1.

    Deliberately narrow: no match criteria, no handling-class routing, no
    orientation or dangerous-goods constraints. Those have no frozen field
    location yet (DEC-1, DEC-2) and must not be invented here.
    """

    policy_id: str = Field(min_length=1, max_length=200)
    priority: int = Field(strict=True, ge=0)
    synthetic_only: Literal[True] = True
    strategy: SyntheticPackingStrategy = SyntheticPackingStrategy.SEQUENTIAL_FIRST_FIT
    material_selection: SyntheticMaterialSelection = SyntheticMaterialSelection.SMALLEST_VOLUME_FIT
    allow_split: bool = True
    allow_mixed_sku: bool = False


class PackagingRuleSet(RulesDomainModel):
    """One immutable, read-only packaging ruleset revision."""

    ruleset_id: str = Field(min_length=1, max_length=200)
    version: str = Field(min_length=1, max_length=200)
    effective_from: AwareDatetime
    effective_to: AwareDatetime | None = None
    source_revision: str = Field(min_length=1, max_length=200)
    synthetic_only: Literal[True]
    sku_specs: tuple[SkuPackagingSpec, ...] = Field(min_length=1)
    materials: tuple[PackageMaterialSpec, ...] = Field(min_length=1)
    policies: tuple[PackingPolicy, ...] = Field(min_length=1)

    @field_validator("effective_from", "effective_to")
    @classmethod
    def timestamps_must_be_utc(cls, value: datetime | None) -> datetime | None:
        if value is None:
            return None
        if value.utcoffset() != timedelta(0):
            raise ValueError("ruleset effective timestamps must use UTC")
        return value

    @model_validator(mode="after")
    def validate_ruleset(self) -> PackagingRuleSet:
        if self.effective_to is not None and self.effective_to <= self.effective_from:
            raise ValueError("effective_to must be later than effective_from")

        skus = [spec.sku for spec in self.sku_specs]
        if len(skus) != len(set(skus)):
            raise ValueError("ruleset must not declare one SKU twice")

        material_ids = [material.material_id for material in self.materials]
        if len(material_ids) != len(set(material_ids)):
            raise ValueError("ruleset must not declare one material twice")
        known_materials = set(material_ids)

        policy_ids = [policy.policy_id for policy in self.policies]
        if len(policy_ids) != len(set(policy_ids)):
            raise ValueError("ruleset must not declare one policy twice")

        for spec in self.sku_specs:
            unknown = [mid for mid in spec.compatible_material_ids if mid not in known_materials]
            if unknown:
                raise ValueError("sku packaging spec references an unknown material")

        return self

    def is_active(self, at: datetime) -> bool:
        """Return whether this ruleset revision is effective at ``at``."""

        if at < self.effective_from:
            return False
        if self.effective_to is not None and at >= self.effective_to:
            return False
        return True

    def sku_spec_for(self, sku: str) -> SkuPackagingSpec | None:
        """Return the packaging spec for ``sku`` or ``None`` when absent."""

        for spec in self.sku_specs:
            if spec.sku == sku:
                return spec
        return None

    def material_for(self, material_id: str) -> PackageMaterialSpec | None:
        """Return the material spec for ``material_id`` or ``None`` when absent."""

        for material in self.materials:
            if material.material_id == material_id:
                return material
        return None

    def ordered_policies(self) -> tuple[PackingPolicy, ...]:
        """Return policies in frozen precedence order: priority, then policy ID."""

        return tuple(sorted(self.policies, key=lambda policy: (policy.priority, policy.policy_id)))
