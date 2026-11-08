"""Order business orchestration over read-only repository interfaces."""

from collections.abc import Callable
from datetime import UTC, datetime
from decimal import Decimal
from typing import Protocol, cast

from backend.models import (
    Order,
    OrderDetailResult,
    OrderResultItem,
    OrderSummaryResult,
    PackageEstimationResult,
    PackageEstimationStatus,
    PackageReasonCode,
    PricingResult,
    Product,
    ShippingQuoteResult,
    TrackingGroup,
    TrackingResult,
)
from backend.models.package import PackageDiagnosticCategory, PackageEstimationDiagnostic
from backend.repositories.exceptions import RecordNotFoundError
from backend.repositories.interfaces import OrderReader, ProductReader, TrackingReader
from backend.services.exceptions import (
    OrderDataIntegrityError,
    OrderNotFoundError,
    ProductNotFoundError,
)
from backend.services.package_estimation import PackageEstimationService
from backend.services.packaging_rules import StaticPackagingRuleSetReader
from backend.services.pricing import ZERO_MONEY, PricingService
from backend.services.tracking import (
    StaticTrackingConfigurationReader,
    StaticTrackingProviderRegistry,
    TrackingService,
    mapping_unresolved_result,
)


class OrderRepositories(Protocol):
    """Minimum repository collection surface required by OrderService."""

    orders: OrderReader
    products: ProductReader


class TrackingOrderRepositories(OrderRepositories, Protocol):
    tracking: TrackingReader


def _no_release_tracking_service(
    clock: Callable[[], datetime],
) -> TrackingService:
    """Default tracking orchestration for an application with no approved release.

    No mapping, credential, account or adapter is fabricated: every unique
    tracking group is projected as D-031 ``CARRIER_MAPPING_UNRESOLVED`` and no
    provider request can be made.
    """

    return TrackingService(
        StaticTrackingConfigurationReader(None),
        StaticTrackingProviderRegistry(),
        clock,
    )


def _no_ruleset_package_estimation_service(
    clock: Callable[[], datetime],
) -> PackageEstimationService:
    """Default package estimation for an application with no approved ruleset.

    No synthetic fixture, default material, capacity or package dimension is
    fabricated. Every order detail therefore reports
    ``unavailable / PACKAGE_RULES_NOT_CONFIGURED`` and returns zero packages.
    """

    return PackageEstimationService(StaticPackagingRuleSetReader(None), clock)


class OrderService:
    """Load, enrich and price exactly one order per service call."""

    def __init__(
        self,
        repositories: OrderRepositories,
        pricing_service: PricingService | None = None,
        tracking_service: TrackingService | None = None,
        package_estimation_service: PackageEstimationService | None = None,
        clock: Callable[[], datetime] | None = None,
    ) -> None:
        self._repositories = repositories
        self._pricing = pricing_service or PricingService()
        self._clock = clock or (lambda: datetime.now(UTC))
        self._tracking = tracking_service or _no_release_tracking_service(self._clock)
        self._package_estimation = (
            package_estimation_service or _no_ruleset_package_estimation_service(self._clock)
        )

    def list_orders(self) -> tuple[OrderSummaryResult, ...]:
        """Return independently priced results for every available order."""

        results = []
        for order in self._repositories.orders.list_orders():
            products = self._products_for_order(order)
            pricing, result_items = self._price_order(order, products, ZERO_MONEY)
            results.append(
                OrderSummaryResult(
                    order=order,
                    items=result_items,
                    pricing=pricing,
                    quote_request_state="not_requested",
                )
            )
        return tuple(results)

    def get_order(self, order_no: str) -> OrderDetailResult:
        """Return a complete business result or a classified safe error."""

        try:
            order = self._repositories.orders.get_by_order_no(order_no)
        except RecordNotFoundError:
            raise OrderNotFoundError from None

        products = self._products_for_order(order)

        shipping_quote = ShippingQuoteResult(
            status="unsupported",
            reason_code="SHIPPING_QUOTE_NOT_IMPLEMENTED",
            checked_at=self._clock(),
            quoted_fee=None,
            applied_fee=ZERO_MONEY,
        )
        pricing, result_items = self._price_order(order, products, shipping_quote.applied_fee)
        package_estimation = self._estimate_packages(order, products)
        return OrderDetailResult(
            order=order,
            items=result_items,
            pricing=pricing,
            quote_request_state="requested",
            shipping_quote=shipping_quote,
            packages=package_estimation.packages,
            package_estimation=package_estimation,
            tracking_results=self._tracking_results(order),
        )

    def _estimate_packages(
        self, order: Order, products: tuple[Product, ...]
    ) -> PackageEstimationResult:
        """Estimate packages without ever failing the order detail request.

        Package estimation is an independent capability: a rules configuration
        gap, incomplete packaging data or an unexpected estimation fault degrades
        only this section and never blocks Tracking, the Shipping Quote or
        Pricing. Successful packages are always real rules-derived domain models,
        never placeholders.
        """

        try:
            return self._package_estimation.estimate_for_order(order, products)
        except Exception as error:  # noqa: BLE001 - last-resort isolation of one capability
            # Capability isolation, not defect concealment: the internal diagnostic
            # keeps the exception class so the cause stays discoverable while the
            # public contract only exposes PACKAGE_DATA_INCOMPLETE.
            return PackageEstimationResult(
                status=PackageEstimationStatus.UNAVAILABLE,
                reason_code=PackageReasonCode.PACKAGE_DATA_INCOMPLETE,
                checked_at=self._clock(),
                source=None,
                synthetic_ruleset=False,
                packages=(),
                diagnostics=(
                    PackageEstimationDiagnostic(
                        category=PackageDiagnosticCategory.INTERNAL_ERROR,
                        safe_detail=(
                            f"unexpected package estimation failure ({type(error).__name__})"
                        )[:300],
                    ),
                ),
            )

    def _tracking_results(self, order: Order) -> tuple[TrackingResult, ...]:
        """Project exactly one result per unique tracking group.

        An empty tuple is only valid when the order has no tracking group. A
        group whose mapping cannot be resolved becomes a D-031 unavailable
        result instead of an order-level failure or a silently empty list.
        """

        group_ids = tuple(dict.fromkeys(item.tracking_group_id for item in order.items))
        if not group_ids:
            return ()
        tracking_reader = getattr(self._repositories, "tracking", None)
        if tracking_reader is None:
            checked_at = self._clock()
            return tuple(mapping_unresolved_result(group_id, checked_at) for group_id in group_ids)
        repositories = cast(TrackingOrderRepositories, self._repositories)
        groups: tuple[TrackingGroup, ...] = tuple(
            repositories.tracking.get_by_group_id(group_id) for group_id in group_ids
        )
        return self._tracking.track_order(groups)

    def _products_for_order(self, order: Order) -> tuple[Product, ...]:
        products = []
        for item in order.items:
            try:
                product = self._repositories.products.get_by_sku(item.sku)
            except RecordNotFoundError:
                raise ProductNotFoundError from None
            if product.sku != item.sku:
                raise OrderDataIntegrityError from None
            products.append(product)
        return tuple(products)

    def _price_order(
        self,
        order: Order,
        products: tuple[Product, ...],
        shipment_fee: Decimal,
    ) -> tuple[PricingResult, tuple[OrderResultItem, ...]]:
        pricing = self._pricing.calculate_order(
            ((product, item.quantity) for item, product in zip(order.items, products, strict=True)),
            shipment_fee,
        )
        result_items = tuple(
            OrderResultItem(
                sku=item.sku,
                quantity=item.quantity,
                tracking_group_id=item.tracking_group_id,
                product=product,
                unit_price_incl_gst=line.unit_price_incl_gst,
                unit_price_ex_gst=line.unit_price_ex_gst,
                line_subtotal=line.line_subtotal,
            )
            for item, product, line in zip(order.items, products, pricing.lines, strict=True)
        )
        return pricing, result_items
