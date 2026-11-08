"""Explicit API v1 schemas independent from domain and source models."""

from datetime import date, timedelta
from decimal import (
    MAX_EMAX,
    MAX_PREC,
    MIN_EMIN,
    ROUND_HALF_UP,
    Context,
    Decimal,
    DivisionByZero,
    InvalidOperation,
    Overflow,
    localcontext,
)
from typing import Annotated, Literal

from pydantic import (
    AwareDatetime,
    BaseModel,
    ConfigDict,
    Field,
    field_serializer,
    field_validator,
    model_validator,
)

MONEY_QUANTUM = Decimal("0.01")
MoneyDecimal = Annotated[
    Decimal,
    Field(strict=True, ge=Decimal("0"), allow_inf_nan=False),
]
ErrorCode = Literal[
    "ORDER_NOT_FOUND",
    "REQUEST_VALIDATION_ERROR",
    "DATA_SOURCE_ERROR",
    "INTERNAL_SERVER_ERROR",
]


def _money_string(amount: Decimal) -> str:
    """Format a Decimal as two-place money without using caller context or float."""

    if amount.is_zero():
        return "0.00"
    decimal_tuple = amount.as_tuple()
    exponent = decimal_tuple.exponent
    if not isinstance(exponent, int):
        raise ValueError("money amount must be finite")
    precision = max(28, len(decimal_tuple.digits) + abs(exponent) + 4)
    if precision > MAX_PREC:
        raise ValueError("money amount exceeds Decimal runtime capacity")
    context = Context(
        prec=precision,
        rounding=ROUND_HALF_UP,
        Emin=MIN_EMIN,
        Emax=MAX_EMAX,
        traps=[InvalidOperation, DivisionByZero, Overflow],
    )
    with localcontext(context):
        normalized = amount.quantize(MONEY_QUANTUM, rounding=ROUND_HALF_UP)
    return format(normalized, ".2f")


class ApiSchema(BaseModel):
    """Immutable API output model with a closed field set."""

    model_config = ConfigDict(frozen=True, extra="forbid")


class Money(ApiSchema):
    """AUD amount serialized explicitly as a two-decimal string."""

    amount: MoneyDecimal = Field(
        description="AUD decimal string with exactly two places",
        json_schema_extra={"pattern": r"^\d+\.\d{2}$", "examples": ["123.45"]},
    )
    currency: Literal["AUD"] = "AUD"

    @field_serializer("amount", return_type=str)
    def serialize_amount(self, amount: Decimal) -> str:
        return _money_string(amount)


class CustomerResponse(ApiSchema):
    name: str
    phone: str
    email: str


class ShippingAddressResponse(ApiSchema):
    line1: str
    suburb: str
    state: str
    postcode: str
    country: str


class ProductResponse(ApiSchema):
    sku: str
    spu: str
    barcode: str
    product_name: str
    description: str | None
    description_status: str
    product_type: str
    size: str
    status: str
    schedule: str
    dosage_type: str
    plant_species: str
    strain_lineage: str
    spectrum: str
    route_of_administration: str
    tga_category: str
    eta_raw: str
    eta_days: int | None


class OrderItemResponse(ApiSchema):
    sku: str
    quantity: int = Field(strict=True, gt=0)
    tracking_group_id: str
    product: ProductResponse
    unit_price_incl_gst: Money
    unit_price_ex_gst: Money
    line_subtotal: Money


class OrderPricingResponse(ApiSchema):
    order_subtotal: Money
    gst_amount: Money
    order_total: Money


class ShippingQuoteResponse(ApiSchema):
    status: Literal["unsupported"]
    reason_code: Literal["SHIPPING_QUOTE_NOT_IMPLEMENTED"]
    checked_at: AwareDatetime
    quoted_fee: Money | None
    applied_fee: Money

    @model_validator(mode="after")
    def enforce_unsupported_quote_contract(self) -> "ShippingQuoteResponse":
        if self.checked_at.utcoffset() != timedelta(0):
            raise ValueError("checked_at must use UTC")
        if self.quoted_fee is not None:
            raise ValueError("unsupported shipping quote quoted fee must be null")
        if not self.applied_fee.amount.is_zero():
            raise ValueError("unsupported shipping quote applied fee must be zero")
        return self


class OrderSummaryResponse(ApiSchema):
    order_number: str
    order_date: date
    company: str
    status: str
    item_count: int = Field(strict=True, ge=0)
    unit_count: int = Field(strict=True, ge=0)
    order_total: Money
    quote_request_state: Literal["not_requested"]
    shipping_quote_status: None
    shipping_quote_reason_code: None


TrackingProvider = Literal["australia_post", "startrack", "tnt"]
TrackingStatus = Literal["available", "unavailable", "unsupported"]
NormalizedTrackingStatus = Literal[
    "pending",
    "ready_for_pickup",
    "in_transit",
    "out_for_delivery",
    "awaiting_collection",
    "delivered",
    "delivery_exception",
    "cancelled",
    "unknown",
]
TrackingReasonCode = Literal[
    "CARRIER_NOT_IMPLEMENTED",
    "PROVIDER_CONFIGURATION_MISSING",
    "CARRIER_MAPPING_UNRESOLVED",
    "PROVIDER_AUTHENTICATION_FAILED",
    "PROVIDER_TIMEOUT",
    "PROVIDER_NETWORK_ERROR",
    "PROVIDER_RATE_LIMITED",
    "TRACKING_ID_INVALID",
    "PRODUCT_NOT_TRACKABLE",
    "PROVIDER_RESPONSE_INVALID",
    "PROVIDER_ERROR",
]


class TrackingEventResponse(ApiSchema):
    event_time: AwareDatetime
    location: str | None
    description: str
    provider_status: str | None
    normalized_status: NormalizedTrackingStatus

    @field_validator("event_time")
    @classmethod
    def event_time_must_be_utc(cls, value):
        if value.utcoffset() != timedelta(0):
            raise ValueError("event_time must use UTC")
        return value


TRACKING_MAPPING_UNRESOLVED_EXAMPLE: dict[str, object] = {
    "tracking_group_id": "GROUP-1",
    "provider": None,
    "status": "unavailable",
    "reason_code": "CARRIER_MAPPING_UNRESOLVED",
    "checked_at": "2026-11-08T01:02:00Z",
    "provider_status": None,
    "current_status": None,
    "latest_event_at": None,
    "events": [],
}


def _tracking_response_schema_extra(schema: dict[str, object]) -> None:
    """Document the D-031 conditional provider contract and its example."""

    schema["description"] = (
        "One result per unique tracking group. provider is null only for "
        "status=unavailable with reason_code=CARRIER_MAPPING_UNRESOLVED (D-031)."
    )
    schema["examples"] = [dict(TRACKING_MAPPING_UNRESOLVED_EXAMPLE)]


class TrackingResponse(ApiSchema):
    """One public result per unique tracking group with the D-031 provider projection.

    ``provider`` is nullable, but the null is only legal together with
    ``status="unavailable"`` and ``reason_code="CARRIER_MAPPING_UNRESOLVED"``.
    Every other combination must name a concrete carrier provider.
    """

    model_config = ConfigDict(
        frozen=True,
        extra="forbid",
        json_schema_extra=_tracking_response_schema_extra,
    )

    tracking_group_id: str = Field(description="Unique tracking group for this order.")
    provider: TrackingProvider | None = Field(
        description=(
            "Concrete carrier provider. Nullable only for status=unavailable with "
            "reason_code=CARRIER_MAPPING_UNRESOLVED (D-031); no provider is ever inferred "
            "from carrier text, group IDs or tracking number shape."
        ),
    )
    status: TrackingStatus = Field(
        description=(
            "available = the carrier query succeeded; unavailable = implemented but this "
            "query failed, including an unresolved carrier mapping; unsupported = the "
            "carrier adapter is not implemented."
        )
    )
    reason_code: TrackingReasonCode | None = Field(
        description=(
            "D-024 stable public reason code. Required for every non-available result and "
            "always null when status=available."
        ),
    )
    checked_at: AwareDatetime = Field(description="UTC time of this system check.")
    provider_status: str | None
    current_status: NormalizedTrackingStatus | None
    latest_event_at: AwareDatetime | None
    events: tuple[TrackingEventResponse, ...] = Field(
        description="Carrier events. An empty array is a valid available result and never "
        "hides a mapping error.",
    )

    @model_validator(mode="after")
    def enforce_tracking_contract(self) -> "TrackingResponse":
        if self.checked_at.utcoffset() != timedelta(0):
            raise ValueError("checked_at must use UTC")
        if self.latest_event_at is not None and self.latest_event_at.utcoffset() != timedelta(0):
            raise ValueError("latest_event_at must use UTC")
        mapping_unresolved = (
            self.status == "unavailable" and self.reason_code == "CARRIER_MAPPING_UNRESOLVED"
        )
        if self.provider is None and not mapping_unresolved:
            raise ValueError(
                "provider may only be null for unavailable tracking with CARRIER_MAPPING_UNRESOLVED"
            )
        if self.provider is not None and mapping_unresolved:
            raise ValueError("CARRIER_MAPPING_UNRESOLVED requires a null provider")
        if self.status == "available":
            if self.reason_code is not None:
                raise ValueError("available tracking result cannot include reason code")
            latest = max((event.event_time for event in self.events), default=None)
            if latest != self.latest_event_at:
                raise ValueError("latest_event_at must match events")
        else:
            if self.reason_code is None:
                raise ValueError("failed tracking result requires reason code")
            if (
                any(
                    value is not None
                    for value in (self.provider_status, self.current_status, self.latest_event_at)
                )
                or self.events
            ):
                raise ValueError("failed tracking result cannot include tracking facts")
            if self.status == "unsupported" and self.reason_code != "CARRIER_NOT_IMPLEMENTED":
                raise ValueError("unsupported tracking reason is invalid")
            if self.status == "unavailable" and self.reason_code == "CARRIER_NOT_IMPLEMENTED":
                raise ValueError("unavailable tracking reason is invalid")
        return self


PackageSource = Literal["actual", "rules"]
PackageEstimationStatus = Literal["available", "unavailable"]
PackageReasonCode = Literal[
    "PACKAGE_RULES_NOT_CONFIGURED",
    "PACKAGE_DATA_INCOMPLETE",
]

# Physical measurements stay decimal strings across the API boundary. Money has
# its own frozen two-place contract; dimensions (mm/mm3) and weights (g) keep
# their exact Decimal scale so no consumer is forced through binary float.
MeasureDecimal = Annotated[
    Decimal,
    Field(strict=True, gt=Decimal("0"), allow_inf_nan=False),
]


def _measure_string(value: Decimal) -> str:
    """Render a physical measurement without rounding or exponent notation."""

    return format(value, "f")


class PackageItemReferenceResponse(ApiSchema):
    order_number: str = Field(description="Order that owns the referenced line.")
    line_index: int = Field(
        strict=True,
        ge=0,
        description="Zero-based order line index; the deterministic internal line reference.",
    )


class PackageItemResponse(ApiSchema):
    order_item_ref: PackageItemReferenceResponse
    sku: str
    quantity: int = Field(strict=True, gt=0)


class PackageDimensionsResponse(ApiSchema):
    length_mm: MeasureDecimal
    width_mm: MeasureDecimal
    height_mm: MeasureDecimal
    volume_mm3: MeasureDecimal

    @field_serializer("length_mm", "width_mm", "height_mm", "volume_mm3", return_type=str)
    def serialize_measure(self, value: Decimal) -> str:
        return _measure_string(value)

    @model_validator(mode="after")
    def volume_must_match_product(self) -> "PackageDimensionsResponse":
        if self.volume_mm3 != self.length_mm * self.width_mm * self.height_mm:
            raise ValueError("volume_mm3 must equal length_mm * width_mm * height_mm")
        return self


class PackageWeightResponse(ApiSchema):
    item_weight_g: MeasureDecimal
    packaging_weight_g: MeasureDecimal
    gross_weight_g: MeasureDecimal

    @field_serializer("item_weight_g", "packaging_weight_g", "gross_weight_g", return_type=str)
    def serialize_measure(self, value: Decimal) -> str:
        return _measure_string(value)

    @model_validator(mode="after")
    def gross_must_match_components(self) -> "PackageWeightResponse":
        if self.gross_weight_g != self.item_weight_g + self.packaging_weight_g:
            raise ValueError("gross_weight_g must equal item_weight_g + packaging_weight_g")
        return self


class PackageResponse(ApiSchema):
    """Frozen ``PackageResponse`` projection from contract §9.3.

    Deliberately excludes material identity, packing policy, capacity,
    diagnostics and any provider chargeable weight.
    """

    package_id: str = Field(description="Opaque package identifier, unique within the order.")
    source: PackageSource
    items: tuple[PackageItemResponse, ...] = Field(min_length=1)
    dimensions: PackageDimensionsResponse
    weight: PackageWeightResponse
    ruleset_id: str | None = Field(
        description="Packaging ruleset identity; required for a rules-sourced package.",
    )
    ruleset_version: str | None

    @model_validator(mode="after")
    def rules_source_requires_ruleset(self) -> "PackageResponse":
        if self.source == "rules" and (self.ruleset_id is None or self.ruleset_version is None):
            raise ValueError("rules package requires ruleset id and version")
        return self


class PackageEstimationResponse(ApiSchema):
    """One estimation outcome per order detail request.

    Packages are nested so that an ``unavailable`` estimation is unambiguous:
    it carries a frozen public reason code and never a partial package set.
    """

    status: PackageEstimationStatus
    reason_code: PackageReasonCode | None = Field(
        description=(
            "Frozen D-024 public code. Required for every unavailable result and "
            "always null when status=available. Internal diagnostics never appear here."
        )
    )
    checked_at: AwareDatetime = Field(description="UTC time of this estimation check.")
    source: PackageSource | None
    ruleset_id: str | None
    ruleset_version: str | None
    synthetic_ruleset: bool = Field(
        description=(
            "True when the estimation used synthetic-only rules. Batch J1 has no "
            "approved production ruleset, so a synthetic result is never production data."
        )
    )
    packages: tuple[PackageResponse, ...]

    @model_validator(mode="after")
    def enforce_estimation_contract(self) -> "PackageEstimationResponse":
        if self.checked_at.utcoffset() != timedelta(0):
            raise ValueError("checked_at must use UTC")

        if self.status == "available":
            if self.reason_code is not None:
                raise ValueError("available package estimation cannot include a reason code")
            if not self.packages:
                raise ValueError("available package estimation requires at least one package")
            if self.source is None:
                raise ValueError("available package estimation requires a source")
            if self.source == "rules" and (self.ruleset_id is None or self.ruleset_version is None):
                raise ValueError("rules estimation requires ruleset id and version")
            package_ids = [package.package_id for package in self.packages]
            if len(package_ids) != len(set(package_ids)):
                raise ValueError("package ids must be unique within one estimation result")
            for package in self.packages:
                if package.source != self.source:
                    raise ValueError("package source must match estimation source")
                if self.source == "rules" and (
                    package.ruleset_id != self.ruleset_id
                    or package.ruleset_version != self.ruleset_version
                ):
                    raise ValueError("package ruleset must match the estimation ruleset")
            return self

        if self.reason_code is None:
            raise ValueError("unavailable package estimation requires a reason code")
        if self.packages:
            raise ValueError("unavailable package estimation cannot include packages")
        if self.source is not None:
            raise ValueError("unavailable package estimation cannot claim a source")
        return self


class OrderDetailResponse(ApiSchema):
    order_number: str
    order_date: date
    company: str
    customer: CustomerResponse
    shipping_address: ShippingAddressResponse
    status: str
    currency: Literal["AUD"]
    items: tuple[OrderItemResponse, ...]
    pricing: OrderPricingResponse
    quote_request_state: Literal["requested"]
    shipping_quote: ShippingQuoteResponse
    package_estimation: PackageEstimationResponse
    tracking_results: tuple[TrackingResponse, ...]

    @model_validator(mode="after")
    def packages_must_belong_to_this_order(self) -> "OrderDetailResponse":
        """Projection guard: a package may never reference another order's line."""

        for package in self.package_estimation.packages:
            for item in package.items:
                if item.order_item_ref.order_number != self.order_number:
                    raise ValueError("package item must reference a line of this order")
        return self


class OrderListEnvelope(ApiSchema):
    data: tuple[OrderSummaryResponse, ...]


class OrderDetailEnvelope(ApiSchema):
    data: OrderDetailResponse


class ErrorDetail(ApiSchema):
    code: ErrorCode
    message: str


class ErrorResponse(ApiSchema):
    error: ErrorDetail
