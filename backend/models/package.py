"""Immutable package estimation domain models for the Batch J1 rules path.

Scope boundary (Batch J1):

- only the ``rules`` package source is produced by the estimation service;
  the ``actual`` source stays structurally representable because the frozen
  contract allows it, but no reader for real packing data exists yet.
- no production packing algorithm is approved (DEC-1, DEC-3, DEC-4 are still
  open), so every package carries an explicit ruleset revision and the
  estimation result records whether that ruleset is synthetic-only.

Units are explicit and never mixed: dimensions are millimetres (``_mm`` and
``_mm3``), weights are grams (``_g``) except provider-derived volumetric and
chargeable weights which are kilograms (``_kg``) and may only be populated when
provider evidence exists.
"""

from __future__ import annotations

import hashlib
import json
from datetime import datetime, timedelta
from decimal import Decimal
from enum import StrEnum
from typing import Annotated

from pydantic import AwareDatetime, BaseModel, ConfigDict, Field, field_validator, model_validator

PositiveDecimal = Annotated[
    Decimal,
    Field(strict=True, gt=Decimal("0"), allow_inf_nan=False),
]
NonNegativeDecimal = Annotated[
    Decimal,
    Field(strict=True, ge=Decimal("0"), allow_inf_nan=False),
]


class PackageDomainModel(BaseModel):
    """Immutable base model for package domain data."""

    model_config = ConfigDict(frozen=True, extra="forbid")


class PackageSource(StrEnum):
    """D-019 package provenance source."""

    ACTUAL = "actual"
    RULES = "rules"


class PackageEstimationStatus(StrEnum):
    """D-013 result status semantics applied to package estimation."""

    AVAILABLE = "available"
    UNAVAILABLE = "unavailable"


class PackageReasonCode(StrEnum):
    """D-024 public reason codes available to Batch J1.

    Only the two codes frozen by ``PHASE6_CONTRACT.md`` §3.1 are public. Every
    other failure keeps its own internal diagnostic category so that no new
    public reason code is invented.
    """

    PACKAGE_RULES_NOT_CONFIGURED = "PACKAGE_RULES_NOT_CONFIGURED"
    PACKAGE_DATA_INCOMPLETE = "PACKAGE_DATA_INCOMPLETE"


class PackageDiagnosticCategory(StrEnum):
    """Internal, non-public classification of an estimation failure."""

    RULES_NOT_CONFIGURED = "rules_not_configured"
    SKU_SPEC_MISSING = "sku_spec_missing"
    MATERIAL_MISSING = "material_missing"
    CAPACITY_EXCEEDED = "capacity_exceeded"
    QUANTITY_CONSERVATION = "quantity_conservation"
    INVALID_INPUT = "invalid_input"
    INTERNAL_ERROR = "internal_error"


def _require_utc(value: datetime, field_name: str) -> datetime:
    if value.utcoffset() != timedelta(0):
        raise ValueError(f"{field_name} must use UTC")
    return value


class PackageDimensions(PackageDomainModel):
    """Package outer dimensions in millimetres.

    ``volume_mm3`` is derived and must equal the exact product of the three
    dimensions; it is never rounded and never a copy of unrelated SKU data.
    """

    length_mm: PositiveDecimal
    width_mm: PositiveDecimal
    height_mm: PositiveDecimal
    volume_mm3: PositiveDecimal

    @model_validator(mode="after")
    def volume_must_match_product(self) -> PackageDimensions:
        if self.volume_mm3 != self.length_mm * self.width_mm * self.height_mm:
            raise ValueError("volume_mm3 must equal length_mm * width_mm * height_mm")
        return self

    @property
    def inner_volume_mm3(self) -> Decimal:
        """Return the exact available volume used for capacity checks."""

        return self.volume_mm3


class PackageWeight(PackageDomainModel):
    """Package weights in grams with provider-derived kilogram facts separated."""

    item_weight_g: NonNegativeDecimal
    packaging_weight_g: NonNegativeDecimal
    gross_weight_g: PositiveDecimal
    volumetric_weight_kg: PositiveDecimal | None = None
    chargeable_weight_kg: PositiveDecimal | None = None

    @model_validator(mode="after")
    def gross_must_match_components(self) -> PackageWeight:
        expected = self.item_weight_g + self.packaging_weight_g
        if self.gross_weight_g != expected:
            raise ValueError("gross_weight_g must equal item_weight_g + packaging_weight_g")
        return self


class PackageItemReference(PackageDomainModel):
    """Deterministic internal reference to the originating order line.

    There is no business order-line identifier in Phase 6, so the reference is
    the order number plus the zero-based line index. It is an internal
    deterministic reference, not a persisted business key.
    """

    order_number: str = Field(min_length=1, max_length=200)
    line_index: int = Field(strict=True, ge=0)


class PackageItem(PackageDomainModel):
    """One allocated quantity of an order line inside a package."""

    order_item_ref: PackageItemReference
    sku: str = Field(min_length=1, max_length=200)
    quantity: int = Field(strict=True, gt=0)


class PackageProvenance(PackageDomainModel):
    """Traceable origin of one package, without any PII or raw payload."""

    source: PackageSource
    source_revision: str = Field(min_length=1, max_length=200)
    ruleset_id: str | None = Field(default=None, min_length=1, max_length=200)
    ruleset_version: str | None = Field(default=None, min_length=1, max_length=200)
    input_fingerprint: str = Field(min_length=64, max_length=64, repr=False)
    generated_at: AwareDatetime

    @field_validator("input_fingerprint")
    @classmethod
    def fingerprint_must_be_lowercase_hex(cls, value: str) -> str:
        if any(character not in "0123456789abcdef" for character in value):
            raise ValueError("input_fingerprint must be lowercase hexadecimal")
        return value

    @field_validator("generated_at")
    @classmethod
    def generated_at_must_be_utc(cls, value: datetime) -> datetime:
        return _require_utc(value, "generated_at")

    @model_validator(mode="after")
    def rules_source_requires_ruleset(self) -> PackageProvenance:
        if self.source is PackageSource.RULES:
            if self.ruleset_id is None or self.ruleset_version is None:
                raise ValueError("rules provenance requires ruleset_id and ruleset_version")
        return self


class Package(PackageDomainModel):
    """One package produced by rules estimation for a single order."""

    package_id: str = Field(min_length=1, max_length=200)
    order_number: str = Field(min_length=1, max_length=200)
    source: PackageSource
    items: tuple[PackageItem, ...] = Field(min_length=1)
    dimensions: PackageDimensions
    weight: PackageWeight
    material_id: str = Field(min_length=1, max_length=200)
    ruleset_id: str | None = Field(default=None, min_length=1, max_length=200)
    ruleset_version: str | None = Field(default=None, min_length=1, max_length=200)
    estimated_at: AwareDatetime | None = None
    provenance: PackageProvenance

    @field_validator("estimated_at")
    @classmethod
    def estimated_at_must_be_utc(cls, value: datetime | None) -> datetime | None:
        if value is None:
            return None
        return _require_utc(value, "estimated_at")

    @model_validator(mode="after")
    def validate_package_invariants(self) -> Package:
        for item in self.items:
            if item.order_item_ref.order_number != self.order_number:
                raise ValueError("package cannot mix order items from another order")

        references = [item.order_item_ref for item in self.items]
        if len(references) != len(set((ref.order_number, ref.line_index) for ref in references)):
            raise ValueError("package cannot allocate the same order line twice")

        if self.provenance.source is not self.source:
            raise ValueError("package provenance source must match package source")

        if self.source is PackageSource.RULES:
            if self.ruleset_id is None or self.ruleset_version is None:
                raise ValueError("rules package requires ruleset_id and ruleset_version")
            if self.estimated_at is None:
                raise ValueError("rules package requires estimated_at")
            if (
                self.provenance.ruleset_id != self.ruleset_id
                or self.provenance.ruleset_version != self.ruleset_version
            ):
                raise ValueError("package ruleset must match its provenance ruleset")

        for item in self.items:
            if item.sku != item.sku.strip():
                raise ValueError("package item sku must not contain surrounding whitespace")

        return self


class PackageEstimationDiagnostic(PackageDomainModel):
    """Internal, de-identified reason detail. Never projected into the API."""

    category: PackageDiagnosticCategory
    sku: str | None = Field(default=None, max_length=200)
    material_id: str | None = Field(default=None, max_length=200)
    ruleset_id: str | None = Field(default=None, max_length=200)
    ruleset_version: str | None = Field(default=None, max_length=200)
    safe_detail: str | None = Field(default=None, max_length=300, repr=False)


class PackageEstimationResult(PackageDomainModel):
    """Frozen estimation outcome: either real packages or a stable failure."""

    status: PackageEstimationStatus
    reason_code: PackageReasonCode | None
    checked_at: AwareDatetime
    source: PackageSource | None
    ruleset_id: str | None = None
    ruleset_version: str | None = None
    # Required, never defaulted: a result must state whether it came from
    # synthetic-only rules. Omitting it may not silently read as production data.
    synthetic_ruleset: bool
    packages: tuple[Package, ...] = ()
    diagnostics: tuple[PackageEstimationDiagnostic, ...] = ()

    @field_validator("checked_at")
    @classmethod
    def checked_at_must_be_utc(cls, value: datetime) -> datetime:
        return _require_utc(value, "checked_at")

    @model_validator(mode="after")
    def validate_status_matrix(self) -> PackageEstimationResult:
        if self.status is PackageEstimationStatus.AVAILABLE:
            if self.reason_code is not None:
                raise ValueError("available package estimation cannot include a reason code")
            if not self.packages:
                raise ValueError("available package estimation requires at least one package")
            if self.source is None:
                raise ValueError("available package estimation requires a source")
            if self.source is PackageSource.RULES:
                if self.ruleset_id is None or self.ruleset_version is None:
                    raise ValueError("rules estimation requires ruleset id and version")
            package_ids = [package.package_id for package in self.packages]
            if len(package_ids) != len(set(package_ids)):
                raise ValueError("package ids must be unique within one estimation result")
            for package in self.packages:
                if package.source is not self.source:
                    raise ValueError("package source must match estimation source")
            return self

        if self.reason_code is None:
            raise ValueError("unavailable package estimation requires a reason code")
        if self.packages:
            raise ValueError("unavailable package estimation cannot include packages")
        if self.source is not None:
            raise ValueError("unavailable package estimation cannot claim a source")
        return self


def make_input_fingerprint(
    order_number: str,
    lines: tuple[tuple[int, str, int], ...],
    ruleset_id: str,
    ruleset_version: str,
) -> str:
    """Return an irreversible fingerprint of the normalized estimation input.

    The payload contains only order identification, line indices, SKUs, integer
    quantities and the ruleset revision. It never contains customer names,
    contact details, addresses or tracking numbers.
    """

    payload = {
        "order_number": order_number,
        "lines": [[line_index, sku, quantity] for line_index, sku, quantity in lines],
        "ruleset_id": ruleset_id,
        "ruleset_version": ruleset_version,
    }
    normalized = json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    return hashlib.sha256(normalized.encode("utf-8")).hexdigest()
