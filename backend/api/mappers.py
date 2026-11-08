"""Map internal Phase 3 results to explicit API v1 response schemas."""

from decimal import Decimal

from backend.api.schemas import (
    CustomerResponse,
    Money,
    OrderDetailResponse,
    OrderItemResponse,
    OrderPricingResponse,
    OrderSummaryResponse,
    PackageDimensionsResponse,
    PackageEstimationResponse,
    PackageItemReferenceResponse,
    PackageItemResponse,
    PackageResponse,
    PackageWeightResponse,
    ProductResponse,
    ShippingAddressResponse,
    ShippingQuoteResponse,
    TrackingEventResponse,
    TrackingResponse,
)
from backend.models import (
    OrderDetailResult,
    OrderSummaryResult,
    Package,
    PackageEstimationResult,
    Product,
    TrackingResult,
)


def _money(amount: Decimal) -> Money:
    return Money(amount=amount)


def _product(product: Product) -> ProductResponse:
    return ProductResponse(
        sku=product.sku,
        spu=product.spu,
        barcode=product.barcode,
        product_name=product.product_name,
        description=product.description,
        description_status=product.description_status,
        product_type=product.product_type,
        size=product.size,
        status=product.status,
        schedule=product.schedule,
        dosage_type=product.dosage_type,
        plant_species=product.plant_species,
        strain_lineage=product.strain_lineage,
        spectrum=product.spectrum,
        route_of_administration=product.route_of_administration,
        tga_category=product.tga_category,
        eta_raw=product.eta_raw,
        eta_days=product.eta_days,
    )


def to_order_summary(result: OrderSummaryResult) -> OrderSummaryResponse:
    """Create the minimal order-management list projection."""

    return OrderSummaryResponse(
        order_number=result.order.order_no,
        order_date=result.order.order_date,
        company=result.order.company,
        status=result.order.status,
        item_count=len(result.items),
        unit_count=sum(item.quantity for item in result.items),
        order_total=_money(result.pricing.order_total),
        quote_request_state=result.quote_request_state,
        shipping_quote_status=None,
        shipping_quote_reason_code=None,
    )


def _tracking(result: TrackingResult) -> TrackingResponse:
    return TrackingResponse(
        tracking_group_id=result.tracking_group_id,
        provider=result.provider,
        status=result.status,
        reason_code=result.reason_code,
        checked_at=result.checked_at,
        provider_status=result.provider_status,
        current_status=result.current_status,
        latest_event_at=result.latest_event_at,
        events=tuple(
            TrackingEventResponse(
                event_time=event.event_time,
                location=event.location,
                description=event.description,
                provider_status=event.provider_status,
                normalized_status=event.normalized_status,
            )
            for event in result.events
        ),
    )


def _package(package: Package) -> PackageResponse:
    return PackageResponse(
        package_id=package.package_id,
        source=package.source,
        items=tuple(
            PackageItemResponse(
                order_item_ref=PackageItemReferenceResponse(
                    order_number=item.order_item_ref.order_number,
                    line_index=item.order_item_ref.line_index,
                ),
                sku=item.sku,
                quantity=item.quantity,
            )
            for item in package.items
        ),
        dimensions=PackageDimensionsResponse(
            length_mm=package.dimensions.length_mm,
            width_mm=package.dimensions.width_mm,
            height_mm=package.dimensions.height_mm,
            volume_mm3=package.dimensions.volume_mm3,
        ),
        weight=PackageWeightResponse(
            item_weight_g=package.weight.item_weight_g,
            packaging_weight_g=package.weight.packaging_weight_g,
            gross_weight_g=package.weight.gross_weight_g,
        ),
        ruleset_id=package.ruleset_id,
        ruleset_version=package.ruleset_version,
    )


def _package_estimation(estimation: PackageEstimationResult) -> PackageEstimationResponse:
    """Project only the public estimation fields; diagnostics stay internal."""

    return PackageEstimationResponse(
        status=estimation.status,
        reason_code=estimation.reason_code,
        checked_at=estimation.checked_at,
        source=estimation.source,
        ruleset_id=estimation.ruleset_id,
        ruleset_version=estimation.ruleset_version,
        synthetic_ruleset=estimation.synthetic_ruleset,
        packages=tuple(_package(package) for package in estimation.packages),
    )


def to_order_detail(result: OrderDetailResult) -> OrderDetailResponse:
    """Create the complete API detail projection without recalculating prices."""

    order = result.order
    estimation = result.package_estimation
    return OrderDetailResponse(
        order_number=order.order_no,
        order_date=order.order_date,
        company=order.company,
        customer=CustomerResponse(
            name=order.customer.name,
            phone=order.customer.phone,
            email=order.customer.email,
        ),
        shipping_address=ShippingAddressResponse(**order.shipping_address.model_dump()),
        status=order.status,
        currency=order.currency,
        items=tuple(
            OrderItemResponse(
                sku=item.sku,
                quantity=item.quantity,
                tracking_group_id=item.tracking_group_id,
                product=_product(item.product),
                unit_price_incl_gst=_money(item.unit_price_incl_gst),
                unit_price_ex_gst=_money(item.unit_price_ex_gst),
                line_subtotal=_money(item.line_subtotal),
            )
            for item in result.items
        ),
        pricing=OrderPricingResponse(
            order_subtotal=_money(result.pricing.order_subtotal),
            gst_amount=_money(result.pricing.gst_amount),
            order_total=_money(result.pricing.order_total),
        ),
        quote_request_state=result.quote_request_state,
        shipping_quote=ShippingQuoteResponse(
            status=result.shipping_quote.status,
            reason_code=result.shipping_quote.reason_code,
            checked_at=result.shipping_quote.checked_at,
            quoted_fee=(
                _money(result.shipping_quote.quoted_fee)
                if result.shipping_quote.quoted_fee is not None
                else None
            ),
            applied_fee=_money(result.shipping_quote.applied_fee),
        ),
        package_estimation=_package_estimation(estimation),
        tracking_results=tuple(_tracking(tracking) for tracking in result.tracking_results),
    )
