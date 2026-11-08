"""Unit tests for strict source parsing and immutable domain models."""

import json
from datetime import UTC, date, datetime
from decimal import Decimal

import pytest
from pydantic import ValidationError

from backend.models import (
    Customer,
    Dimensions,
    Order,
    OrderItem,
    Product,
    ShippingAddress,
    ShippingQuoteResult,
    TrackingGroup,
)
from backend.models.source import (
    CustomerSource,
    OrdersFileSource,
    ProductsFileSource,
    ShippingAddressSource,
    TrackingFileSource,
    TrackingSource,
)


def _assert_hidden_from_repr_and_str(model: object, sensitive_values: tuple[str, ...]) -> None:
    representations = (repr(model), str(model))
    assert all(
        value not in representation
        for value in sensitive_values
        for representation in representations
    )


def test_order_source_parses_required_fields_and_date(orders_payload: dict[str, object]) -> None:
    source = OrdersFileSource.model_validate(orders_payload)

    assert source.orders[0].order_date == date(2026, 1, 2)
    assert source.orders[0].items[0].quantity == 2


def test_order_source_rejects_missing_required_field(orders_payload: dict[str, object]) -> None:
    del orders_payload["orders"][0]["order_no"]

    with pytest.raises(ValidationError):
        OrdersFileSource.model_validate(orders_payload)


@pytest.mark.parametrize("invalid_date", [20260102, "20260102", "02/01/2026", "not-a-date"])
def test_order_source_rejects_invalid_date_type_or_format(
    orders_payload: dict[str, object], invalid_date: object
) -> None:
    orders_payload["orders"][0]["order_date"] = invalid_date

    with pytest.raises(ValidationError):
        OrdersFileSource.model_validate(orders_payload)


@pytest.mark.parametrize("quantity", [0, -1, "2", 1.5, None])
def test_order_source_rejects_invalid_quantity(
    orders_payload: dict[str, object], quantity: object
) -> None:
    orders_payload["orders"][0]["items"][0]["quantity"] = quantity

    with pytest.raises(ValidationError):
        OrdersFileSource.model_validate(orders_payload)


def test_product_source_preserves_nullable_fields(products_payload: dict[str, object]) -> None:
    source = ProductsFileSource.model_validate(products_payload)
    missing = source.products[1]

    assert missing.description is None
    assert missing.eta_raw == "nullDays"
    assert missing.eta_days is None


@pytest.mark.parametrize("description", [".", " . ", "", "   "])
def test_product_source_rejects_invalid_standardized_description(
    products_payload: dict[str, object], description: str
) -> None:
    products_payload["products"][0]["description"] = description

    with pytest.raises(ValidationError):
        ProductsFileSource.model_validate(products_payload)


def test_product_source_accepts_available_description(products_payload: dict[str, object]) -> None:
    source = ProductsFileSource.model_validate(products_payload)

    assert source.products[0].description_status == "available"
    assert source.products[0].description == "Synthetic description"


def test_product_source_preserves_partial_description(products_payload: dict[str, object]) -> None:
    product = products_payload["products"][0]
    product["description"] = "Existing incomplete source text"
    product["description_status"] = "partial_needs_requery"

    source = ProductsFileSource.model_validate(products_payload)

    assert source.products[0].description == "Existing incomplete source text"
    assert source.products[0].description_status == "partial_needs_requery"


def test_product_source_preserves_zero_day_without_interpretation(
    products_payload: dict[str, object],
) -> None:
    product = products_payload["products"][0]
    product["eta_raw"] = "0Days"
    product["eta_days"] = 0

    source = ProductsFileSource.model_validate(products_payload)

    assert source.products[0].eta_raw == "0Days"
    assert source.products[0].eta_days == 0


def test_product_source_preserves_decimal_precision(products_payload: dict[str, object]) -> None:
    source = ProductsFileSource.model_validate(products_payload)

    assert source.products[0].rrp_aud_incl_gst == Decimal("29.9900")
    assert source.products[0].weight_g == Decimal("10.500")
    assert isinstance(source.products[0].rrp_aud_incl_gst, Decimal)


@pytest.mark.parametrize("invalid_amount", [29.99, 30, "not-a-decimal", "NaN", "Infinity"])
def test_product_source_rejects_non_decimal_string_amounts(
    products_payload: dict[str, object], invalid_amount: object
) -> None:
    products_payload["products"][0]["rrp_aud_incl_gst"] = invalid_amount

    with pytest.raises(ValidationError):
        ProductsFileSource.model_validate(products_payload)


def test_product_source_parses_source_datetime(products_payload: dict[str, object]) -> None:
    source = ProductsFileSource.model_validate(products_payload)

    assert source.products[0].source_date == datetime(2026, 1, 1, 12, 34, 56)


@pytest.mark.parametrize("invalid_datetime", [20260101, "2026-01-01", "invalid"])
def test_product_source_rejects_invalid_source_datetime(
    products_payload: dict[str, object], invalid_datetime: object
) -> None:
    products_payload["products"][0]["source_date"] = invalid_datetime

    with pytest.raises(ValidationError):
        ProductsFileSource.model_validate(products_payload)


@pytest.mark.parametrize(
    ("description", "status"),
    [(None, "available"), ("Unexpected value", "missing")],
)
def test_product_source_rejects_inconsistent_description_state(
    products_payload: dict[str, object], description: str | None, status: str
) -> None:
    product = products_payload["products"][0]
    product["description"] = description
    product["description_status"] = status

    with pytest.raises(ValidationError):
        ProductsFileSource.model_validate(products_payload)


def test_product_source_rejects_inconsistent_eta(products_payload: dict[str, object]) -> None:
    products_payload["products"][0]["eta_days"] = 9

    with pytest.raises(ValidationError):
        ProductsFileSource.model_validate(products_payload)


def test_product_file_rejects_incorrect_record_count(products_payload: dict[str, object]) -> None:
    products_payload["record_count"] = 999

    with pytest.raises(ValidationError):
        ProductsFileSource.model_validate(products_payload)


def test_domain_models_are_immutable(products_payload: dict[str, object]) -> None:
    source = ProductsFileSource.model_validate(products_payload).products[0]
    product = Product(**source.model_dump())

    with pytest.raises(ValidationError):
        product.product_name = "Changed"


@pytest.mark.parametrize("invalid_decimal", [1.5, "1.5", 1])
def test_domain_decimal_fields_reject_non_decimal_types(invalid_decimal: object) -> None:
    with pytest.raises(ValidationError):
        Dimensions(
            length=invalid_decimal,
            width=Decimal("2"),
            height=Decimal("3"),
        )


@pytest.mark.parametrize(
    "invalid_decimal",
    [Decimal("NaN"), Decimal("Infinity"), Decimal("-Infinity")],
)
def test_domain_decimal_fields_reject_non_finite_values(invalid_decimal: Decimal) -> None:
    with pytest.raises(ValidationError):
        Dimensions(
            length=invalid_decimal,
            width=Decimal("2"),
            height=Decimal("3"),
        )


def test_domain_decimal_fields_reject_negative_values() -> None:
    with pytest.raises(ValidationError):
        Dimensions(
            length=Decimal("-0.01"),
            width=Decimal("2"),
            height=Decimal("3"),
        )


def test_domain_decimal_fields_accept_finite_non_negative_decimal() -> None:
    dimensions = Dimensions(
        length=Decimal("1.25"),
        width=Decimal("0"),
        height=Decimal("3.50"),
    )

    assert dimensions.length == Decimal("1.25")
    assert dimensions.width == Decimal("0")


@pytest.mark.parametrize(
    "zero_fee",
    [
        Decimal("0"),
        Decimal("0.000"),
        Decimal("-0"),
        Decimal("-0.000"),
        Decimal("0E+10"),
    ],
)
def test_unsupported_shipping_quote_normalizes_every_decimal_zero(
    zero_fee: Decimal,
) -> None:
    quote = ShippingQuoteResult(
        status="unsupported",
        reason_code="SHIPPING_QUOTE_NOT_IMPLEMENTED",
        checked_at=datetime(2026, 11, 6, 12, 0, tzinfo=UTC),
        quoted_fee=None,
        applied_fee=zero_fee,
    )

    assert quote.applied_fee.as_tuple() == Decimal("0.00").as_tuple()


@pytest.mark.parametrize("nonzero_fee", [Decimal("12.34"), Decimal("-0.01")])
def test_unsupported_shipping_quote_rejects_nonzero_applied_fee(
    nonzero_fee: Decimal,
) -> None:
    with pytest.raises(ValidationError):
        ShippingQuoteResult(
            status="unsupported",
            reason_code="SHIPPING_QUOTE_NOT_IMPLEMENTED",
            checked_at=datetime(2026, 11, 6, 12, 0, tzinfo=UTC),
            quoted_fee=None,
            applied_fee=nonzero_fee,
        )


@pytest.mark.parametrize("invalid_quantity", [1.5, "1", True])
def test_domain_order_item_rejects_non_strict_quantity(invalid_quantity: object) -> None:
    with pytest.raises(ValidationError):
        OrderItem(sku="TEST-SKU", quantity=invalid_quantity, tracking_group_id="GROUP-1")


def test_domain_order_item_accepts_strict_positive_integer() -> None:
    item = OrderItem(sku="TEST-SKU", quantity=1, tracking_group_id="GROUP-1")

    assert item.quantity == 1
    assert type(item.quantity) is int


def test_tracking_source_root_mapping_is_immutable(
    tracking_payload: dict[str, object],
) -> None:
    source = TrackingFileSource.model_validate(tracking_payload)

    with pytest.raises(TypeError):
        source.root["NEW-GROUP"] = source.root["GROUP-1"]
    with pytest.raises(ValidationError):
        source.root["GROUP-1"].carrier = "Changed"


def test_customer_repr_and_str_hide_sensitive_fields() -> None:
    values = ("synthetic-name-marker", "synthetic-phone-marker", "synthetic-email-marker")
    customer = Customer(name=values[0], phone=values[1], email=values[2])

    _assert_hidden_from_repr_and_str(customer, values)
    assert customer.model_dump() == {"name": values[0], "phone": values[1], "email": values[2]}


def test_shipping_address_repr_and_str_hide_sensitive_fields() -> None:
    values = (
        "synthetic-line-marker",
        "synthetic-suburb-marker",
        "synthetic-state-marker",
        "synthetic-postcode-marker",
        "synthetic-country-marker",
    )
    address = ShippingAddress(
        line1=values[0],
        suburb=values[1],
        state=values[2],
        postcode=values[3],
        country=values[4],
    )

    _assert_hidden_from_repr_and_str(address, values)
    assert tuple(address.model_dump().values()) == values


def test_order_repr_and_str_do_not_recursively_expose_customer_or_address() -> None:
    customer_values = ("nested-name-marker", "nested-phone-marker", "nested-email-marker")
    address_values = (
        "nested-line-marker",
        "nested-suburb-marker",
        "nested-state-marker",
        "nested-postcode-marker",
        "nested-country-marker",
    )
    order = Order(
        order_no="SYNTHETIC-ORDER",
        order_date=date(2026, 1, 2),
        company="Synthetic Company",
        customer=Customer(
            name=customer_values[0], phone=customer_values[1], email=customer_values[2]
        ),
        shipping_address=ShippingAddress(
            line1=address_values[0],
            suburb=address_values[1],
            state=address_values[2],
            postcode=address_values[3],
            country=address_values[4],
        ),
        status="SYNTHETIC",
        currency="AUD",
        items=(OrderItem(sku="TEST-SKU", quantity=1, tracking_group_id="GROUP-1"),),
    )

    _assert_hidden_from_repr_and_str(order, customer_values + address_values)
    dumped = order.model_dump()
    assert dumped["customer"]["name"] == customer_values[0]
    assert dumped["shipping_address"]["line1"] == address_values[0]


def test_customer_source_repr_and_str_hide_sensitive_fields() -> None:
    values = ("source-name-marker", "source-phone-marker", "source-email-marker")
    customer = CustomerSource(name=values[0], phone=values[1], email=values[2])

    _assert_hidden_from_repr_and_str(customer, values)
    assert tuple(customer.model_dump().values()) == values


def test_shipping_address_source_repr_and_str_hide_sensitive_fields() -> None:
    values = (
        "source-line-marker",
        "source-suburb-marker",
        "source-state-marker",
        "source-postcode-marker",
        "source-country-marker",
    )
    address = ShippingAddressSource(
        line1=values[0],
        suburb=values[1],
        state=values[2],
        postcode=values[3],
        country=values[4],
    )

    _assert_hidden_from_repr_and_str(address, values)
    assert tuple(address.model_dump().values()) == values


def test_order_source_repr_and_str_hide_nested_sensitive_fields(
    orders_payload: dict[str, object],
) -> None:
    markers = (
        "order-source-name-marker",
        "order-source-phone-marker",
        "order-source-email-marker",
        "order-source-line-marker",
        "order-source-suburb-marker",
        "order-source-state-marker",
        "order-source-postcode-marker",
        "order-source-country-marker",
    )
    order_payload = orders_payload["orders"][0]
    order_payload["customer"] = {
        "name": markers[0],
        "phone": markers[1],
        "email": markers[2],
    }
    order_payload["shipping_address"] = {
        "line1": markers[3],
        "suburb": markers[4],
        "state": markers[5],
        "postcode": markers[6],
        "country": markers[7],
    }
    source = OrdersFileSource.model_validate(orders_payload)

    _assert_hidden_from_repr_and_str(source.orders[0], markers)
    _assert_hidden_from_repr_and_str(source, markers)
    dumped = source.model_dump()
    assert dumped["orders"][0]["customer"]["email"] == markers[2]
    assert dumped["orders"][0]["shipping_address"]["postcode"] == markers[6]


def test_tracking_models_hide_tracking_number_from_repr_and_str() -> None:
    marker = "synthetic-tracking-marker"
    domain = TrackingGroup(
        tracking_group_id="GROUP-1", carrier="Synthetic Carrier", tracking_number=marker
    )
    source = TrackingSource(carrier="Synthetic Carrier", tracking_number=marker)

    _assert_hidden_from_repr_and_str(domain, (marker,))
    _assert_hidden_from_repr_and_str(source, (marker,))
    assert domain.model_dump()["tracking_number"] == marker
    assert source.model_dump()["tracking_number"] == marker


def test_tracking_file_model_dump_returns_independent_plain_dictionary(
    tracking_payload: dict[str, object],
) -> None:
    source = TrackingFileSource.model_validate(tracking_payload)

    dumped = source.model_dump()

    assert isinstance(dumped, dict)
    assert isinstance(dumped["GROUP-1"], dict)
    assert dumped == tracking_payload


def test_tracking_file_model_dump_json_round_trips(
    tracking_payload: dict[str, object],
) -> None:
    source = TrackingFileSource.model_validate(tracking_payload)

    serialized = source.model_dump_json()
    parsed = json.loads(serialized)
    restored = TrackingFileSource.model_validate_json(serialized)

    assert parsed == tracking_payload
    assert restored.model_dump() == tracking_payload


def test_tracking_file_serialized_mutation_does_not_affect_immutable_root(
    tracking_payload: dict[str, object],
) -> None:
    source = TrackingFileSource.model_validate(tracking_payload)
    original_number = source.root["GROUP-1"].tracking_number
    dumped = source.model_dump()

    dumped["GROUP-1"]["tracking_number"] = "changed-serialized-value"

    assert source.root["GROUP-1"].tracking_number == original_number
    with pytest.raises(TypeError):
        source.root["GROUP-1"] = source.root["GROUP-2"]
