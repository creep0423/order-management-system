"""Pydantic models matching the approved JSON data-source structures."""

import re
from collections.abc import Mapping
from datetime import date, datetime
from decimal import Decimal, InvalidOperation
from types import MappingProxyType
from typing import Annotated, Literal

from pydantic import (
    BaseModel,
    BeforeValidator,
    ConfigDict,
    Field,
    RootModel,
    field_serializer,
    model_validator,
)


def _non_empty_string(value: object) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError("must be a non-empty string")
    return value


def _strict_string(value: object) -> str:
    if not isinstance(value, str):
        raise ValueError("must be a string")
    return value


def _description_text(value: object) -> str:
    description = _non_empty_string(value)
    if description.strip() == ".":
        raise ValueError("standardized description cannot use the raw missing marker")
    return description


def _decimal_string(value: object) -> Decimal:
    if not isinstance(value, str):
        raise ValueError("must be a decimal string")
    try:
        parsed = Decimal(value)
    except InvalidOperation as exc:
        raise ValueError("must be a valid decimal string") from exc
    if not parsed.is_finite():
        raise ValueError("must be a finite decimal string")
    return parsed


def _date_string(value: object) -> date:
    if not isinstance(value, str) or re.fullmatch(r"\d{4}-\d{2}-\d{2}", value) is None:
        raise ValueError("must be an ISO date string")
    try:
        return date.fromisoformat(value)
    except ValueError as exc:
        raise ValueError("must be an ISO date string") from exc


def _datetime_string(value: object) -> datetime:
    if (
        not isinstance(value, str)
        or re.fullmatch(r"\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}", value) is None
    ):
        raise ValueError("must be a source datetime string")
    try:
        return datetime.fromisoformat(value)
    except ValueError as exc:
        raise ValueError("must be a source datetime string") from exc


NonEmptyString = Annotated[str, BeforeValidator(_non_empty_string)]
StrictString = Annotated[str, BeforeValidator(_strict_string)]
DescriptionText = Annotated[str, BeforeValidator(_description_text)]
SourceDate = Annotated[date, BeforeValidator(_date_string)]
SourceDateTime = Annotated[datetime, BeforeValidator(_datetime_string)]
NonNegativeDecimalString = Annotated[
    Decimal,
    BeforeValidator(_decimal_string),
    Field(ge=0),
]


class SourceModel(BaseModel):
    """Strict base model for JSON records."""

    model_config = ConfigDict(extra="forbid", frozen=True)


class CustomerSource(SourceModel):
    name: NonEmptyString = Field(repr=False)
    phone: NonEmptyString = Field(repr=False)
    email: NonEmptyString = Field(repr=False)


class ShippingAddressSource(SourceModel):
    line1: NonEmptyString = Field(repr=False)
    suburb: NonEmptyString = Field(repr=False)
    state: NonEmptyString = Field(repr=False)
    postcode: NonEmptyString = Field(repr=False)
    country: NonEmptyString = Field(repr=False)


class OrderItemSource(SourceModel):
    sku: NonEmptyString
    quantity: int = Field(strict=True, gt=0)
    tracking_group_id: NonEmptyString


class OrderSource(SourceModel):
    order_no: NonEmptyString
    order_date: SourceDate
    company: NonEmptyString
    customer: CustomerSource = Field(repr=False)
    shipping_address: ShippingAddressSource = Field(repr=False)
    status: NonEmptyString
    items: tuple[OrderItemSource, ...] = Field(min_length=1)


class OrdersFileSource(SourceModel):
    schema_version: Literal["1.0.0"]
    currency: Literal["AUD"]
    orders: tuple[OrderSource, ...]


class DimensionsSource(SourceModel):
    length: NonNegativeDecimalString
    width: NonNegativeDecimalString
    height: NonNegativeDecimalString


class ProductSource(SourceModel):
    sku: NonEmptyString
    spu: StrictString
    barcode: NonEmptyString
    product_name: NonEmptyString
    description: DescriptionText | None
    description_status: Literal["available", "missing", "partial_needs_requery"]
    product_type: NonEmptyString
    size: NonEmptyString
    status: NonEmptyString
    schedule: NonEmptyString
    dosage_type: NonEmptyString
    plant_species: NonEmptyString
    strain_lineage: NonEmptyString
    spectrum: NonEmptyString
    route_of_administration: NonEmptyString
    tga_category: NonEmptyString
    eta_raw: NonEmptyString
    eta_days: int | None = Field(default=None, strict=True, ge=0)
    rrp_aud_incl_gst: NonNegativeDecimalString
    weight_g: NonNegativeDecimalString
    dimensions_mm: DimensionsSource
    volume_mm3: NonNegativeDecimalString
    volumetric_gross_weight_kg: NonNegativeDecimalString
    max_storage_per_container: NonNegativeDecimalString
    warning_threshold: NonNegativeDecimalString
    source_date: SourceDateTime

    @model_validator(mode="after")
    def validate_missing_data_markers(self) -> "ProductSource":
        if self.description_status == "missing" and self.description is not None:
            raise ValueError("missing description status requires a null description")
        if self.description_status != "missing" and self.description is None:
            raise ValueError("non-missing description status requires a description")

        if self.eta_raw == "nullDays":
            if self.eta_days is not None:
                raise ValueError("nullDays requires a null eta_days value")
            return self

        eta_match = re.fullmatch(r"(\d+)Days", self.eta_raw)
        if eta_match is None or self.eta_days != int(eta_match.group(1)):
            raise ValueError("eta_raw and eta_days are inconsistent")
        return self


class ProductsFileSource(SourceModel):
    schema_version: Literal["1.0.0"]
    currency: Literal["AUD"]
    price_tax_treatment: Literal["RRP includes GST"]
    record_count: int = Field(strict=True, ge=0)
    products: tuple[ProductSource, ...]

    @model_validator(mode="after")
    def validate_record_count(self) -> "ProductsFileSource":
        if self.record_count != len(self.products):
            raise ValueError("record_count does not match products length")
        return self


class TrackingSource(SourceModel):
    carrier: NonEmptyString
    tracking_number: NonEmptyString = Field(repr=False)


class TrackingFileSource(RootModel[Mapping[str, TrackingSource]]):
    """The tracking file is keyed directly by tracking group ID."""

    model_config = ConfigDict(frozen=True)

    @model_validator(mode="after")
    def validate_group_ids(self) -> "TrackingFileSource":
        if not self.root:
            raise ValueError("at least one tracking group is required")
        if any(not isinstance(group_id, str) or not group_id.strip() for group_id in self.root):
            raise ValueError("tracking group IDs must be non-empty strings")
        object.__setattr__(self, "root", MappingProxyType(dict(self.root)))
        return self

    @field_serializer("root")
    def serialize_root(self, root: Mapping[str, TrackingSource]) -> dict[str, dict[str, str]]:
        return {group_id: record.model_dump() for group_id, record in root.items()}
