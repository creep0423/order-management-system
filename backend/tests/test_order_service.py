"""Unit and integration tests for Phase 3 order orchestration."""

import copy
from collections.abc import Callable
from datetime import UTC, date, datetime, timedelta, timezone
from decimal import Decimal
from types import SimpleNamespace

import pytest
from pydantic import ValidationError

from backend.models import (
    CarrierProvider,
    Customer,
    Order,
    OrderDetailResult,
    OrderResult,
    OrderSummaryResult,
    Package,
    PackageEstimationResult,
    PackageEstimationStatus,
    PackageItem,
    PackageItemReference,
    PackageReasonCode,
    PricingResult,
    Product,
    ResultStatus,
    ShippingAddress,
    ShippingQuoteResult,
    TrackingReasonCode,
    TrackingResult,
)
from backend.repositories import RecordNotFoundError, RepositoryCollection
from backend.services import (
    OrderDataIntegrityError,
    OrderNotFoundError,
    OrderService,
    PackageEstimationService,
    ProductNotFoundError,
    StaticPackagingRuleSetReader,
)
from backend.tests.packaging_fixtures import NOW as NOW_FOR_PACKAGES
from backend.tests.packaging_fixtures import ruleset_for_skus


@pytest.fixture
def repositories(
    write_data_directory: object,
    orders_payload: dict[str, object],
    products_payload: dict[str, object],
    tracking_payload: dict[str, object],
) -> RepositoryCollection:
    data_directory = write_data_directory(orders_payload, products_payload, tracking_payload)
    return RepositoryCollection(data_directory)


def test_normal_order_query_returns_enriched_priced_result(
    repositories: RepositoryCollection,
) -> None:
    result = OrderService(repositories).get_order("TEST-ORDER-001")

    assert result.order.order_no == "TEST-ORDER-001"
    assert len(result.items) == 2
    assert result.pricing.shipment_fee == Decimal("0.00")
    assert result.pricing.order_total == (result.pricing.order_subtotal + result.pricing.gst_amount)
    assert result.shipping_quote.status == "unsupported"
    assert result.shipping_quote.reason_code == "SHIPPING_QUOTE_NOT_IMPLEMENTED"
    assert result.shipping_quote.quoted_fee is None
    assert result.shipping_quote.applied_fee == Decimal("0.00")
    assert result.shipping_quote.checked_at.utcoffset() == timedelta(0)


def test_list_orders_prices_every_order_through_the_service(
    repositories: RepositoryCollection,
) -> None:
    results = OrderService(repositories).list_orders()

    assert [result.order.order_no for result in results] == ["TEST-ORDER-001"]
    assert results[0].pricing.order_total == Decimal("89.97")
    assert results[0].quote_request_state == "not_requested"
    assert results[0].pricing.shipment_fee == Decimal("0.00")
    assert not hasattr(results[0], "shipping_quote")


class _TrackingServiceStub:
    def __init__(self, results: tuple[TrackingResult, ...]) -> None:
        self.results = results
        self.calls = 0

    def track_order(self, groups: tuple[object, ...]) -> tuple[TrackingResult, ...]:
        self.calls += 1
        assert len(groups) == 2
        return self.results


def test_detail_calls_tracking_once_but_list_never_calls_tracking(
    repositories: RepositoryCollection,
) -> None:
    tracking = TrackingResult(
        tracking_group_id="GROUP-1",
        provider=CarrierProvider.AUSTRALIA_POST,
        status=ResultStatus.UNAVAILABLE,
        reason_code=TrackingReasonCode.PROVIDER_TIMEOUT,
        checked_at=datetime(2026, 11, 8, 1, 2, tzinfo=UTC),
        provider_status=None,
        current_status=None,
        latest_event_at=None,
        events=(),
    )
    second_tracking = tracking.model_copy(update={"tracking_group_id": "GROUP-2"})
    stub = _TrackingServiceStub((tracking, second_tracking))
    service = OrderService(repositories, tracking_service=stub)  # type: ignore[arg-type]

    summaries = service.list_orders()
    detail = service.get_order("TEST-ORDER-001")

    assert stub.calls == 1
    assert summaries[0].quote_request_state == "not_requested"
    assert detail.quote_request_state == "requested"
    assert detail.tracking_results == (tracking, second_tracking)
    assert detail.shipping_quote.status == "unsupported"
    assert detail.shipping_quote.reason_code == "SHIPPING_QUOTE_NOT_IMPLEMENTED"


def test_shipping_quote_uses_injected_utc_check_time_and_applied_fee_for_total(
    repositories: RepositoryCollection,
) -> None:
    checked_at = datetime(2026, 11, 6, 12, 0, tzinfo=UTC)

    result = OrderService(repositories, clock=lambda: checked_at).get_order("TEST-ORDER-001")

    assert result.shipping_quote.checked_at == checked_at
    assert result.pricing.shipment_fee == result.shipping_quote.applied_fee
    assert result.pricing.order_total == (
        result.pricing.order_subtotal
        + result.pricing.gst_amount
        + result.shipping_quote.applied_fee
    )


@pytest.mark.parametrize(
    "invalid_time",
    [
        datetime(2026, 11, 6, 12, 0),
        datetime(2026, 11, 6, 12, 0, tzinfo=timezone(timedelta(hours=10))),
    ],
)
def test_shipping_quote_rejects_naive_or_non_utc_check_time(
    repositories: RepositoryCollection,
    invalid_time: datetime,
) -> None:
    with pytest.raises(ValidationError, match="checked_at must use UTC|timezone_aware"):
        OrderService(repositories, clock=lambda: invalid_time).get_order("TEST-ORDER-001")


def test_order_result_rejects_matching_nonzero_unsupported_shipping_fee(
    repositories: RepositoryCollection,
) -> None:
    result = OrderService(repositories).get_order("TEST-ORDER-001")
    nonzero_fee = Decimal("12.34")
    pricing = result.pricing.model_copy(
        update={
            "shipment_fee": nonzero_fee,
            "order_total": result.pricing.order_total + nonzero_fee,
        }
    )
    invalid_quote = ShippingQuoteResult.model_construct(
        status="unsupported",
        reason_code="SHIPPING_QUOTE_NOT_IMPLEMENTED",
        checked_at=datetime(2026, 11, 6, 12, 0, tzinfo=UTC),
        quoted_fee=None,
        applied_fee=nonzero_fee,
    )

    with pytest.raises(
        ValidationError, match="unsupported shipping quote applied fee must be zero"
    ):
        OrderResult(
            order=result.order,
            items=result.items,
            pricing=pricing,
            shipping_quote=invalid_quote,
            packages=(),
            package_estimation=_unavailable_estimation(),
        )


def test_multi_sku_order_associates_each_line_with_the_correct_product(
    repositories: RepositoryCollection,
) -> None:
    result = OrderService(repositories).get_order("TEST-ORDER-001")

    assert [item.sku for item in result.items] == ["TEST-SKU-1", "TEST-SKU-2"]
    assert [item.product.sku for item in result.items] == ["TEST-SKU-1", "TEST-SKU-2"]
    assert [item.quantity for item in result.items] == [2, 1]
    assert [item.tracking_group_id for item in result.items] == ["GROUP-1", "GROUP-2"]
    assert [item.line_subtotal for item in result.items] == [
        line.line_subtotal for line in result.pricing.lines
    ]


def test_order_not_found_is_mapped_to_safe_service_error(
    repositories: RepositoryCollection,
) -> None:
    marker = "missing-sensitive-order-marker"

    with pytest.raises(OrderNotFoundError) as captured:
        OrderService(repositories).get_order(marker)

    assert marker not in str(captured.value)


class _MissingProductReader:
    def list_products(self) -> tuple[Product, ...]:
        return ()

    def get_by_sku(self, sku: str) -> Product:
        raise RecordNotFoundError("product")


def test_missing_product_association_is_mapped_to_safe_service_error(
    repositories: RepositoryCollection,
) -> None:
    broken = SimpleNamespace(orders=repositories.orders, products=_MissingProductReader())

    with pytest.raises(ProductNotFoundError) as captured:
        OrderService(broken).get_order("TEST-ORDER-001")

    assert "TEST-SKU" not in str(captured.value)


class _MismatchedProductReader:
    def __init__(self, product: Product) -> None:
        self._product = product

    def list_products(self) -> tuple[Product, ...]:
        return (self._product,)

    def get_by_sku(self, sku: str) -> Product:
        return self._product


def test_mismatched_product_association_is_rejected(
    repositories: RepositoryCollection,
) -> None:
    wrong_product = repositories.products.get_by_sku("TEST-SKU-2")
    broken = SimpleNamespace(
        orders=repositories.orders,
        products=_MismatchedProductReader(wrong_product),
    )

    with pytest.raises(OrderDataIntegrityError):
        OrderService(broken).get_order("TEST-ORDER-001")


def test_multiple_orders_are_calculated_independently_without_state_pollution(
    write_data_directory: object,
    orders_payload: dict[str, object],
    products_payload: dict[str, object],
    tracking_payload: dict[str, object],
) -> None:
    second = copy.deepcopy(orders_payload["orders"][0])
    second["order_no"] = "TEST-ORDER-002"
    second["items"] = [{"sku": "TEST-SKU-2", "quantity": 4, "tracking_group_id": "GROUP-2"}]
    orders_payload["orders"].append(second)
    data_directory = write_data_directory(orders_payload, products_payload, tracking_payload)
    service = OrderService(RepositoryCollection(data_directory))

    first = service.get_order("TEST-ORDER-001")
    second_result = service.get_order("TEST-ORDER-002")
    first_again = service.get_order("TEST-ORDER-001")

    assert len(first.items) == 2
    assert len(second_result.items) == 1
    assert first.pricing.order_subtotal != second_result.pricing.order_subtotal
    assert first.shipping_quote.status == "unsupported"
    assert second_result.shipping_quote.status == "unsupported"
    assert first.pricing.shipment_fee == Decimal("0.00")
    assert second_result.pricing.shipment_fee == Decimal("0.00")
    assert first_again.pricing.shipment_fee == Decimal("0.00")
    assert first_again.pricing.order_total == (
        first_again.pricing.order_subtotal + first_again.pricing.gst_amount
    )


def test_order_result_is_immutable(repositories: RepositoryCollection) -> None:
    result = OrderService(repositories).get_order("TEST-ORDER-001")

    with pytest.raises(ValidationError):
        result.items[0].quantity = 99


def test_real_repository_baseline_can_be_priced_without_cross_order_merging() -> None:
    repositories = RepositoryCollection()
    service = OrderService(repositories)
    orders: tuple[Order, ...] = repositories.orders.list_orders()

    results = tuple(service.get_order(order.order_no) for order in orders)

    assert len(results) == 2
    assert [len(result.items) for result in results] == [len(order.items) for order in orders]
    assert sum(len(result.items) for result in results) == 9
    assert all(result.pricing.shipment_fee == Decimal("0.00") for result in results)
    assert all(
        result.pricing.order_subtotal
        == sum((item.line_subtotal for item in result.items), start=Decimal("0.00"))
        for result in results
    )


def test_detail_without_an_injected_tracking_service_still_projects_every_group(
    repositories: RepositoryCollection,
) -> None:
    detail = OrderService(repositories).get_order("TEST-ORDER-001")

    expected_groups = tuple(dict.fromkeys(item.tracking_group_id for item in detail.items))
    assert [result.tracking_group_id for result in detail.tracking_results] == list(expected_groups)
    assert expected_groups == ("GROUP-1", "GROUP-2")
    for result in detail.tracking_results:
        assert result.provider is None
        assert result.status is ResultStatus.UNAVAILABLE
        assert result.reason_code is TrackingReasonCode.CARRIER_MAPPING_UNRESOLVED
        assert result.events == ()


def test_detail_without_a_tracking_repository_still_projects_every_group(
    repositories: RepositoryCollection,
) -> None:
    without_tracking = SimpleNamespace(
        orders=repositories.orders,
        products=repositories.products,
    )

    detail = OrderService(without_tracking).get_order("TEST-ORDER-001")

    assert [result.tracking_group_id for result in detail.tracking_results] == [
        "GROUP-1",
        "GROUP-2",
    ]
    assert all(result.provider is None for result in detail.tracking_results)
    assert all(
        result.reason_code is TrackingReasonCode.CARRIER_MAPPING_UNRESOLVED
        for result in detail.tracking_results
    )


def test_tracking_unavailable_does_not_degrade_shipping_quote_or_pricing(
    repositories: RepositoryCollection,
) -> None:
    unavailable = TrackingResult(
        tracking_group_id="GROUP-1",
        provider=None,
        status=ResultStatus.UNAVAILABLE,
        reason_code=TrackingReasonCode.CARRIER_MAPPING_UNRESOLVED,
        checked_at=datetime(2026, 11, 8, 1, 2, tzinfo=UTC),
        provider_status=None,
        current_status=None,
        latest_event_at=None,
        events=(),
    )
    second = unavailable.model_copy(update={"tracking_group_id": "GROUP-2"})
    stub = _TrackingServiceStub((unavailable, second))
    service = OrderService(repositories, tracking_service=stub)  # type: ignore[arg-type]

    detail = service.get_order("TEST-ORDER-001")

    assert detail.tracking_results == (unavailable, second)
    assert detail.shipping_quote.status == "unsupported"
    assert detail.shipping_quote.reason_code == "SHIPPING_QUOTE_NOT_IMPLEMENTED"
    assert detail.pricing.order_total == (
        detail.pricing.order_subtotal
        + detail.pricing.gst_amount
        + detail.shipping_quote.applied_fee
    )


def _empty_order() -> Order:
    return Order(
        order_no="TEST-ORDER-EMPTY",
        order_date=date(2026, 1, 2),
        company="Synthetic Company",
        customer=Customer(name="Test", phone="0000000000", email="customer@example.invalid"),
        shipping_address=ShippingAddress(
            line1="1 Example Street",
            suburb="Exampleville",
            state="NSW",
            postcode="2000",
            country="Australia",
        ),
        status="SYNTHETIC",
        currency="AUD",
        items=(),
    )


def _zero_pricing() -> PricingResult:
    return PricingResult(
        lines=(),
        order_subtotal=Decimal("0.00"),
        gst_amount=Decimal("0.00"),
        shipment_fee=Decimal("0.00"),
        order_total=Decimal("0.00"),
    )


def _unsupported_quote() -> ShippingQuoteResult:
    return ShippingQuoteResult(
        status="unsupported",
        reason_code="SHIPPING_QUOTE_NOT_IMPLEMENTED",
        checked_at=datetime(2026, 11, 8, 1, 2, tzinfo=UTC),
        quoted_fee=None,
        applied_fee=Decimal("0.00"),
    )


def _unavailable_estimation() -> PackageEstimationResult:
    return PackageEstimationResult(
        status=PackageEstimationStatus.UNAVAILABLE,
        reason_code=PackageReasonCode.PACKAGE_RULES_NOT_CONFIGURED,
        checked_at=datetime(2026, 11, 8, 1, 2, tzinfo=UTC),
        source=None,
        synthetic_ruleset=False,
        packages=(),
    )


def test_empty_tracking_results_are_only_allowed_without_tracking_groups() -> None:
    result = OrderDetailResult(
        order=_empty_order(),
        items=(),
        pricing=_zero_pricing(),
        shipping_quote=_unsupported_quote(),
        packages=(),
        package_estimation=_unavailable_estimation(),
        tracking_results=(),
    )

    assert result.tracking_results == ()


def test_detail_result_rejects_a_missing_result_for_an_order_tracking_group(
    repositories: RepositoryCollection,
) -> None:
    detail = OrderService(repositories).get_order("TEST-ORDER-001")

    with pytest.raises(ValidationError, match="tracking results must cover"):
        OrderDetailResult(
            order=detail.order,
            items=detail.items,
            pricing=detail.pricing,
            shipping_quote=detail.shipping_quote,
            packages=detail.packages,
            package_estimation=detail.package_estimation,
            tracking_results=(),
        )


def test_summary_enforces_d030_total_equals_goods_subtotal_plus_gst(
    repositories: RepositoryCollection,
) -> None:
    summary = OrderService(repositories).list_orders()[0]

    assert summary.pricing.shipment_fee == Decimal("0.00")
    assert (
        summary.pricing.order_total == summary.pricing.order_subtotal + summary.pricing.gst_amount
    )
    assert isinstance(summary.pricing.order_total, Decimal)
    assert summary.pricing.order_total.as_tuple().exponent == -2


def _summary_with_pricing(
    summary: OrderSummaryResult, **pricing_updates: object
) -> OrderSummaryResult:
    return OrderSummaryResult(
        order=summary.order,
        items=summary.items,
        pricing=summary.pricing.model_copy(update=pricing_updates),
    )


@pytest.mark.parametrize("difference", [Decimal("-0.01"), Decimal("0.01")])
def test_summary_rejects_order_total_that_differs_from_the_d030_formula(
    repositories: RepositoryCollection,
    difference: Decimal,
) -> None:
    summary = OrderService(repositories).list_orders()[0]

    with pytest.raises(ValidationError, match="order_total must equal"):
        _summary_with_pricing(
            summary,
            order_total=summary.pricing.order_total + difference,
        )


def test_summary_rejects_inconsistent_gst_amount(repositories: RepositoryCollection) -> None:
    summary = OrderService(repositories).list_orders()[0]

    with pytest.raises(ValidationError, match="order_total must equal"):
        _summary_with_pricing(
            summary,
            gst_amount=summary.pricing.gst_amount + Decimal("0.01"),
        )


def test_summary_rejects_a_nonzero_shipment_fee(repositories: RepositoryCollection) -> None:
    summary = OrderService(repositories).list_orders()[0]

    with pytest.raises(ValidationError, match="shipment fee must be zero"):
        _summary_with_pricing(
            summary,
            shipment_fee=Decimal("0.01"),
            order_total=summary.pricing.order_total + Decimal("0.01"),
        )


def test_summary_pricing_rejects_float_amounts(repositories: RepositoryCollection) -> None:
    summary = OrderService(repositories).list_orders()[0]

    with pytest.raises(ValidationError):
        PricingResult(
            lines=summary.pricing.lines,
            order_subtotal=summary.pricing.order_subtotal,
            gst_amount=summary.pricing.gst_amount,
            shipment_fee=0.0,
            order_total=summary.pricing.order_total,
        )


# ------------------------------------------------- Batch J1 package estimation


class _RaisingPackageEstimation:
    """Package estimation stub that always raises, to prove fault isolation."""

    def __init__(self) -> None:
        self.calls = 0

    def estimate_for_order(self, order: Order, products: tuple[Product, ...]) -> object:
        self.calls += 1
        raise RuntimeError("synthetic package estimation failure")


class _CountingPackageEstimation:
    def __init__(self) -> None:
        self.calls = 0

    def estimate_for_order(self, order: Order, products: tuple[Product, ...]) -> object:
        self.calls += 1
        raise AssertionError("list flow must never estimate packages")


def _package_service(ruleset: object) -> PackageEstimationService:
    return PackageEstimationService(
        StaticPackagingRuleSetReader(ruleset),  # type: ignore[arg-type]
        clock=lambda: NOW_FOR_PACKAGES,
    )


def _skus(repositories: RepositoryCollection) -> tuple[str, ...]:
    order = repositories.orders.get_by_order_no("TEST-ORDER-001")
    return tuple(item.sku for item in order.items)


def test_detail_includes_rules_packages_when_a_ruleset_is_configured(
    repositories: RepositoryCollection,
) -> None:
    ruleset = ruleset_for_skus(_skus(repositories))
    service = OrderService(repositories, package_estimation_service=_package_service(ruleset))

    detail = service.get_order("TEST-ORDER-001")

    estimation = detail.package_estimation
    assert estimation is not None
    assert estimation.status.value == "available"
    assert estimation.reason_code is None
    assert estimation.ruleset_id == "synthetic-ruleset-j1"
    assert estimation.synthetic_ruleset is True
    assert detail.packages == estimation.packages
    assert detail.packages

    allocated: dict[int, int] = {}
    for package in detail.packages:
        assert package.provenance.source.value == "rules"
        assert package.provenance.ruleset_version == "synthetic-v1"
        for item in package.items:
            allocated[item.order_item_ref.line_index] = (
                allocated.get(item.order_item_ref.line_index, 0) + item.quantity
            )
    assert allocated == {index: item.quantity for index, item in enumerate(detail.order.items)}


def test_detail_without_a_ruleset_fails_closed_and_keeps_tracking(
    repositories: RepositoryCollection,
) -> None:
    detail = OrderService(repositories).get_order("TEST-ORDER-001")

    estimation = detail.package_estimation
    assert estimation is not None
    assert estimation.status.value == "unavailable"
    assert estimation.reason_code == PackageReasonCode.PACKAGE_RULES_NOT_CONFIGURED
    assert estimation.packages == ()
    assert detail.packages == ()
    # Tracking is unaffected by the package configuration gap.
    assert [result.tracking_group_id for result in detail.tracking_results] == [
        "GROUP-1",
        "GROUP-2",
    ]
    # D-015 Shipping Quote and Pricing are unchanged by Batch J1.
    assert detail.shipping_quote.status == "unsupported"
    assert detail.pricing.shipment_fee == Decimal("0.00")


def test_list_never_estimates_packages(repositories: RepositoryCollection) -> None:
    counting = _CountingPackageEstimation()
    service = OrderService(
        repositories,
        package_estimation_service=counting,  # type: ignore[arg-type]
    )

    summaries = service.list_orders()

    assert counting.calls == 0
    assert summaries
    for summary in summaries:
        assert not hasattr(summary, "packages")
        assert not hasattr(summary, "package_estimation")


def test_package_estimation_fault_does_not_break_the_order_detail(
    repositories: RepositoryCollection,
) -> None:
    raising = _RaisingPackageEstimation()
    service = OrderService(
        repositories,
        package_estimation_service=raising,  # type: ignore[arg-type]
    )

    detail = service.get_order("TEST-ORDER-001")

    assert raising.calls == 1
    assert detail.package_estimation is not None
    assert detail.package_estimation.reason_code == PackageReasonCode.PACKAGE_DATA_INCOMPLETE
    assert detail.packages == ()
    assert len(detail.tracking_results) == 2
    assert detail.shipping_quote.status == "unsupported"


def test_tracking_failure_does_not_affect_package_estimation(
    repositories: RepositoryCollection,
) -> None:
    ruleset = ruleset_for_skus(_skus(repositories))
    service = OrderService(
        repositories,
        tracking_service=_TrackingServiceStub(
            (
                _unavailable_tracking("GROUP-1"),
                _unavailable_tracking("GROUP-2"),
            )
        ),  # type: ignore[arg-type]
        package_estimation_service=_package_service(ruleset),
    )

    detail = service.get_order("TEST-ORDER-001")

    assert all(result.status is ResultStatus.UNAVAILABLE for result in detail.tracking_results)
    assert detail.package_estimation is not None
    assert detail.package_estimation.status.value == "available"
    assert detail.packages


def _unavailable_tracking(group_id: str) -> TrackingResult:
    return TrackingResult(
        tracking_group_id=group_id,
        provider=None,
        status=ResultStatus.UNAVAILABLE,
        reason_code=TrackingReasonCode.CARRIER_MAPPING_UNRESOLVED,
        checked_at=datetime(2026, 11, 8, 1, 2, tzinfo=UTC),
        provider_status=None,
        current_status=None,
        latest_event_at=None,
        events=(),
    )


def test_detail_requires_a_package_estimation_result(
    repositories: RepositoryCollection,
) -> None:
    detail = OrderService(repositories).get_order("TEST-ORDER-001")

    # The estimation outcome is not optional: contract §4.1 states every detail
    # carries one, so a detail result without it is not constructible.
    with pytest.raises(ValidationError, match="package_estimation"):
        OrderDetailResult(
            order=detail.order,
            items=detail.items,
            pricing=detail.pricing,
            shipping_quote=detail.shipping_quote,
            packages=detail.packages,
            tracking_results=detail.tracking_results,
        )


def test_detail_rejects_packages_that_disagree_with_the_estimation(
    repositories: RepositoryCollection,
) -> None:
    detail = OrderService(
        repositories,
        package_estimation_service=_package_service(ruleset_for_skus(_skus(repositories))),
    ).get_order("TEST-ORDER-001")

    with pytest.raises(ValidationError, match="must match the package estimation"):
        OrderDetailResult(
            order=detail.order,
            items=detail.items,
            pricing=detail.pricing,
            shipping_quote=detail.shipping_quote,
            packages=(),
            package_estimation=detail.package_estimation,
            tracking_results=detail.tracking_results,
        )


# ------------------------------------------- independent package/order verification


def _detail_with_packages(
    repositories: RepositoryCollection,
    mutate: Callable[[tuple[Package, ...]], tuple[Package, ...]],
) -> tuple[OrderDetailResult, tuple[Package, ...], PackageEstimationResult]:
    detail = OrderService(
        repositories,
        package_estimation_service=_package_service(ruleset_for_skus(_skus(repositories))),
    ).get_order("TEST-ORDER-001")
    packages = mutate(detail.packages)
    estimation = detail.package_estimation.model_copy(update={"packages": packages})
    return detail, packages, estimation


def _rebuild_detail(
    detail: OrderDetailResult,
    packages: tuple[Package, ...],
    estimation: PackageEstimationResult,
) -> OrderDetailResult:
    return OrderDetailResult(
        order=detail.order,
        items=detail.items,
        pricing=detail.pricing,
        shipping_quote=detail.shipping_quote,
        packages=packages,
        package_estimation=estimation,
        tracking_results=detail.tracking_results,
    )


def _replace_first_item(packages: tuple[Package, ...], item: PackageItem) -> tuple[Package, ...]:
    updated = list(packages)
    updated[0] = updated[0].model_copy(update={"items": (item,)})
    return tuple(updated)


def test_domain_rejects_a_package_referencing_a_missing_order_line(
    repositories: RepositoryCollection,
) -> None:
    item = PackageItem(
        order_item_ref=PackageItemReference(order_number="TEST-ORDER-001", line_index=99),
        sku="TEST-SKU-1",
        quantity=1,
    )
    detail, packages, estimation = _detail_with_packages(
        repositories, lambda existing: _replace_first_item(existing, item)
    )

    with pytest.raises(ValidationError, match="non-existent order line"):
        _rebuild_detail(detail, packages, estimation)


def test_domain_rejects_a_package_sku_that_disagrees_with_the_order_line(
    repositories: RepositoryCollection,
) -> None:
    item = PackageItem(
        order_item_ref=PackageItemReference(order_number="TEST-ORDER-001", line_index=0),
        sku="SKU-NOT-IN-ORDER",
        quantity=2,
    )
    detail, packages, estimation = _detail_with_packages(
        repositories, lambda existing: _replace_first_item(existing, item)
    )

    with pytest.raises(ValidationError, match="must match the referenced order line"):
        _rebuild_detail(detail, packages, estimation)


def test_domain_rejects_packaged_quantity_that_loses_ordered_units(
    repositories: RepositoryCollection,
) -> None:
    item = PackageItem(
        order_item_ref=PackageItemReference(order_number="TEST-ORDER-001", line_index=0),
        sku="TEST-SKU-1",
        quantity=1,
    )
    detail, packages, estimation = _detail_with_packages(
        repositories, lambda existing: _replace_first_item(existing, item)
    )

    with pytest.raises(ValidationError, match="packaged quantity must equal"):
        _rebuild_detail(detail, packages, estimation)


def test_domain_rejects_a_package_from_another_order(
    repositories: RepositoryCollection,
) -> None:
    def move_to_other_order(packages: tuple[Package, ...]) -> tuple[Package, ...]:
        # Internally consistent package that belongs to a different order, so the
        # Package-level guard cannot catch it and the order-level guard must.
        original = packages[0]
        updated = list(packages)
        updated[0] = original.model_copy(
            update={
                "order_number": "OTHER-ORDER",
                "items": tuple(
                    item.model_copy(
                        update={
                            "order_item_ref": item.order_item_ref.model_copy(
                                update={"order_number": "OTHER-ORDER"}
                            )
                        }
                    )
                    for item in original.items
                ),
            }
        )
        return tuple(updated)

    detail, packages, estimation = _detail_with_packages(repositories, move_to_other_order)

    with pytest.raises(ValidationError, match="must belong to the order"):
        _rebuild_detail(detail, packages, estimation)


def test_domain_rejects_a_package_whose_ruleset_disagrees_with_the_estimation(
    repositories: RepositoryCollection,
) -> None:
    def drift_ruleset(packages: tuple[object, ...]) -> tuple[object, ...]:
        updated = list(packages)
        updated[0] = updated[0].model_copy(update={"ruleset_version": "synthetic-v9"})  # type: ignore[attr-defined]
        return tuple(updated)

    detail, packages, estimation = _detail_with_packages(repositories, drift_ruleset)

    with pytest.raises(ValidationError, match="ruleset must match"):
        _rebuild_detail(detail, packages, estimation)
