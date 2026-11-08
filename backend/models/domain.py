"""Validated domain models independent from JSON envelopes and API schemas."""

from datetime import date, datetime, timedelta
from decimal import Decimal
from typing import Annotated, Literal

from pydantic import AwareDatetime, BaseModel, ConfigDict, Field, field_validator, model_validator

from backend.models.package import Package, PackageEstimationResult, PackageEstimationStatus
from backend.models.tracking import TrackingResult

StrictNonNegativeDecimal = Annotated[
    Decimal,
    Field(strict=True, ge=Decimal("0"), allow_inf_nan=False),
]


class DomainModel(BaseModel):
    """Immutable base model for read-only domain data."""

    model_config = ConfigDict(frozen=True, extra="forbid")


class Customer(DomainModel):
    """Customer details required by an order.

    These values are sensitive and must not be written to ordinary logs.
    """

    name: str = Field(repr=False)
    phone: str = Field(repr=False)
    email: str = Field(repr=False)


class ShippingAddress(DomainModel):
    """Destination address required by an order."""

    line1: str = Field(repr=False)
    suburb: str = Field(repr=False)
    state: str = Field(repr=False)
    postcode: str = Field(repr=False)
    country: str = Field(repr=False)


class OrderItem(DomainModel):
    """An order line linked to product and tracking data by identifiers."""

    sku: str
    quantity: int = Field(strict=True, gt=0)
    tracking_group_id: str


class Order(DomainModel):
    """A single customer order loaded from the read-only order source."""

    order_no: str
    order_date: date
    company: str
    customer: Customer = Field(repr=False)
    shipping_address: ShippingAddress = Field(repr=False)
    status: str
    currency: str
    items: tuple[OrderItem, ...]


class Dimensions(DomainModel):
    """Normalized product dimensions in millimetres."""

    length: StrictNonNegativeDecimal
    width: StrictNonNegativeDecimal
    height: StrictNonNegativeDecimal


class Product(DomainModel):
    """A normalized SKU record used as the runtime product source."""

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
    eta_days: int | None = Field(default=None, strict=True, ge=0)
    rrp_aud_incl_gst: StrictNonNegativeDecimal
    weight_g: StrictNonNegativeDecimal
    dimensions_mm: Dimensions
    volume_mm3: StrictNonNegativeDecimal
    volumetric_gross_weight_kg: StrictNonNegativeDecimal
    max_storage_per_container: StrictNonNegativeDecimal
    warning_threshold: StrictNonNegativeDecimal
    source_date: datetime


class TrackingGroup(DomainModel):
    """Local mapping between an order grouping key and a carrier reference."""

    tracking_group_id: str
    carrier: str
    tracking_number: str = Field(repr=False)


class LinePricingResult(DomainModel):
    """Decimal-only pricing values for one validated order line."""

    sku: str
    quantity: int = Field(strict=True, gt=0)
    unit_price_incl_gst: StrictNonNegativeDecimal
    unit_price_ex_gst: StrictNonNegativeDecimal
    line_subtotal: StrictNonNegativeDecimal


class PricingResult(DomainModel):
    """Frozen pricing outcome before any API-specific serialization."""

    lines: tuple[LinePricingResult, ...]
    order_subtotal: StrictNonNegativeDecimal
    gst_amount: StrictNonNegativeDecimal
    shipment_fee: StrictNonNegativeDecimal
    order_total: StrictNonNegativeDecimal


class ShippingQuoteResult(DomainModel):
    """Current explicit result for the not-yet-implemented quote capability."""

    status: Literal["unsupported"]
    reason_code: Literal["SHIPPING_QUOTE_NOT_IMPLEMENTED"]
    checked_at: AwareDatetime
    quoted_fee: None = None
    applied_fee: StrictNonNegativeDecimal

    @field_validator("checked_at")
    @classmethod
    def checked_at_must_be_utc(cls, value: datetime) -> datetime:
        if value.utcoffset() != timedelta(0):
            raise ValueError("checked_at must use UTC")
        return value

    @field_validator("applied_fee")
    @classmethod
    def applied_fee_must_be_canonical_zero(cls, value: Decimal) -> Decimal:
        if not value.is_zero():
            raise ValueError("unsupported shipping quote applied fee must be zero")
        return Decimal("0.00")


class OrderResultItem(DomainModel):
    """An order line enriched with its product and calculated prices."""

    sku: str
    quantity: int = Field(strict=True, gt=0)
    tracking_group_id: str
    product: Product
    unit_price_incl_gst: StrictNonNegativeDecimal
    unit_price_ex_gst: StrictNonNegativeDecimal
    line_subtotal: StrictNonNegativeDecimal


class OrderSummaryResult(DomainModel):
    """List-use-case result with pricing before unrequested shipping."""

    order: Order
    items: tuple[OrderResultItem, ...]
    pricing: PricingResult
    quote_request_state: Literal["not_requested"] = "not_requested"

    @model_validator(mode="after")
    def enforce_d030_total_before_shipping(self) -> "OrderSummaryResult":
        """D-030: list total is goods subtotal plus goods GST, never freight."""

        if not self.pricing.shipment_fee.is_zero():
            raise ValueError("summary pricing shipment fee must be zero")
        if self.pricing.order_total != self.pricing.order_subtotal + self.pricing.gst_amount:
            raise ValueError("summary order_total must equal order_subtotal + gst_amount")
        return self


class OrderDetailResult(DomainModel):
    """Detail-use-case result with independent quote, package and tracking outcomes."""

    order: Order
    items: tuple[OrderResultItem, ...]
    pricing: PricingResult
    quote_request_state: Literal["requested"] = "requested"
    shipping_quote: ShippingQuoteResult
    packages: tuple[Package, ...]
    package_estimation: PackageEstimationResult
    tracking_results: tuple[TrackingResult, ...] = ()

    @model_validator(mode="after")
    def applied_fee_must_match_pricing(self) -> "OrderDetailResult":
        if not self.shipping_quote.applied_fee.is_zero():
            raise ValueError("unsupported shipping quote applied fee must be zero")
        if self.shipping_quote.applied_fee != self.pricing.shipment_fee:
            raise ValueError("shipping quote applied fee must match pricing shipment fee")
        expected_groups = tuple(dict.fromkeys(item.tracking_group_id for item in self.items))
        actual_groups = tuple(result.tracking_group_id for result in self.tracking_results)
        if expected_groups:
            if actual_groups != expected_groups:
                raise ValueError("tracking results must cover each tracking group in order")
        elif actual_groups:
            raise ValueError("tracking results require at least one order tracking group")

        self._validate_package_allocation()
        return self

    def _validate_package_allocation(self) -> None:
        """Independently verify packages against this order's lines (D-020).

        The estimation service performs the same check while allocating, but the
        domain result must not trust that: a malformed projection could otherwise
        expose packages that reference missing lines, disagree with the order's
        SKUs, belong to another order, or lose quantities.
        """

        if self.packages != self.package_estimation.packages:
            raise ValueError("packages must match the package estimation result")

        estimation = self.package_estimation
        order_items = self.order.items
        allocated: dict[int, int] = {}

        for package in self.packages:
            if package.order_number != self.order.order_no:
                raise ValueError("package must belong to the order being returned")
            if package.source is not estimation.source:
                raise ValueError("package source must match the package estimation source")
            if estimation.ruleset_id is not None and (
                package.ruleset_id != estimation.ruleset_id
                or package.ruleset_version != estimation.ruleset_version
            ):
                raise ValueError("package ruleset must match the package estimation ruleset")

            for item in package.items:
                line_index = item.order_item_ref.line_index
                if line_index >= len(order_items):
                    raise ValueError("package references a non-existent order line")
                if item.sku != order_items[line_index].sku:
                    raise ValueError("package item sku must match the referenced order line")
                allocated[line_index] = allocated.get(line_index, 0) + item.quantity

        if estimation.status is PackageEstimationStatus.AVAILABLE:
            if not self.packages:
                raise ValueError("available package estimation requires at least one package")
            for line_index, order_item in enumerate(order_items):
                if allocated.get(line_index, 0) != order_item.quantity:
                    raise ValueError("packaged quantity must equal the ordered quantity")
        elif self.packages:
            raise ValueError("unavailable package estimation cannot include packages")


# Compatibility alias for existing Phase 3/4 imports while callers migrate to the
# explicit list/detail result types.
OrderResult = OrderDetailResult
