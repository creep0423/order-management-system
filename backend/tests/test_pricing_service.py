"""Unit tests for the frozen Phase 3 Decimal pricing rules."""

from decimal import (
    ROUND_DOWN,
    ROUND_HALF_EVEN,
    ROUND_HALF_UP,
    Context,
    Decimal,
    DivisionByZero,
    Inexact,
    Rounded,
    getcontext,
    localcontext,
)

import pytest
from pydantic import ValidationError

from backend.models import Product
from backend.repositories import RepositoryCollection
from backend.services import (
    InvalidMonetaryAmountError,
    InvalidPricingInputError,
    InvalidQuantityError,
    PricingService,
)


@pytest.fixture
def products(
    write_data_directory: object,
    orders_payload: dict[str, object],
    products_payload: dict[str, object],
    tracking_payload: dict[str, object],
) -> tuple[Product, Product]:
    data_directory = write_data_directory(orders_payload, products_payload, tracking_payload)
    loaded = RepositoryCollection(data_directory).products.list_products()
    return loaded[0], loaded[1]


def _with_rrp(product: Product, amount: str) -> Product:
    return product.model_copy(update={"rrp_aud_incl_gst": Decimal(amount)})


def test_single_product_single_quantity_keeps_ex_gst_internal_precision(
    products: tuple[Product, Product],
) -> None:
    product = _with_rrp(products[0], "29.9900")

    line = PricingService().calculate_line(product, 1)

    assert line.unit_price_incl_gst == Decimal("29.9900")
    assert str(line.unit_price_ex_gst).startswith("27.2636363636363636363636363636")
    assert len(line.unit_price_ex_gst.as_tuple().digits) > 28
    assert line.unit_price_ex_gst != line.unit_price_ex_gst.quantize(Decimal("0.01"))
    assert line.line_subtotal == Decimal("27.26")


def test_single_product_multiple_quantity_prices_the_full_line(
    products: tuple[Product, Product],
) -> None:
    product = _with_rrp(products[0], "29.9900")

    line = PricingService().calculate_line(product, 3)

    assert line.quantity == 3
    assert line.line_subtotal == Decimal("81.79")


def test_multiple_products_are_summed_from_rounded_lines(
    products: tuple[Product, Product],
) -> None:
    first = _with_rrp(products[0], "11.00")
    second = _with_rrp(products[1], "22.00")

    result = PricingService().calculate_order(((first, 2), (second, 1)))

    assert [line.line_subtotal for line in result.lines] == [
        Decimal("20.00"),
        Decimal("20.00"),
    ]
    assert result.order_subtotal == Decimal("40.00")
    assert result.gst_amount == Decimal("4.00")
    assert result.order_total == Decimal("44.00")


def test_gst_uses_order_subtotal_and_round_half_up(
    products: tuple[Product, Product],
) -> None:
    product = _with_rrp(products[0], "0.055")

    result = PricingService().calculate_order(((product, 1),))

    assert result.order_subtotal == Decimal("0.05")
    assert result.gst_amount == Decimal("0.01")
    assert result.order_total == Decimal("0.06")


def test_line_rounding_is_explicitly_half_up_not_half_even(
    products: tuple[Product, Product],
) -> None:
    product = _with_rrp(products[0], "1.1055")

    line = PricingService().calculate_line(product, 1)

    assert line.unit_price_ex_gst == Decimal("1.005")
    assert line.line_subtotal == Decimal("1.01")
    assert line.unit_price_ex_gst.quantize(Decimal("0.01"), rounding=ROUND_HALF_EVEN) == Decimal(
        "1.00"
    )


def test_each_line_is_rounded_before_order_subtotal_is_summed(
    products: tuple[Product, Product],
) -> None:
    first = _with_rrp(products[0], "1.1055")
    second = _with_rrp(products[1], "1.1055")

    result = PricingService().calculate_order(((first, 1), (second, 1)))
    aggregate_then_round = (
        sum((line.unit_price_ex_gst for line in result.lines), start=Decimal("0"))
    ).quantize(Decimal("0.01"))

    assert result.order_subtotal == Decimal("2.02")
    assert aggregate_then_round == Decimal("2.01")
    assert result.order_subtotal != aggregate_then_round


def test_shipment_fee_is_normalized_before_order_total(
    products: tuple[Product, Product],
) -> None:
    product = _with_rrp(products[0], "11.00")

    result = PricingService().calculate_order(((product, 1),), Decimal("1.005"))

    assert result.order_subtotal == Decimal("10.00")
    assert result.gst_amount == Decimal("1.00")
    assert result.shipment_fee == Decimal("1.01")
    assert result.order_total == Decimal("12.01")


def test_zero_amount_boundary_remains_valid_two_decimal_money(
    products: tuple[Product, Product],
) -> None:
    product = _with_rrp(products[0], "0")

    result = PricingService().calculate_order(((product, 1),), Decimal("0"))

    assert result.order_subtotal == Decimal("0.00")
    assert result.gst_amount == Decimal("0.00")
    assert result.shipment_fee == Decimal("0.00")
    assert result.order_total == Decimal("0.00")


@pytest.mark.parametrize(
    "invalid_amount",
    [1.25, Decimal("-0.01"), Decimal("NaN"), Decimal("Infinity")],
)
def test_invalid_monetary_amounts_are_rejected_without_coercion(invalid_amount: object) -> None:
    with pytest.raises(InvalidMonetaryAmountError):
        PricingService().calculate_ex_gst_unit_price(invalid_amount)


@pytest.mark.parametrize("invalid_quantity", [0, -1, True, 1.0, Decimal("1")])
def test_invalid_quantities_are_rejected(
    products: tuple[Product, Product], invalid_quantity: object
) -> None:
    with pytest.raises(InvalidQuantityError):
        PricingService().calculate_line(products[0], invalid_quantity)


def test_empty_order_is_rejected(products: tuple[Product, Product]) -> None:
    with pytest.raises(InvalidPricingInputError, match="at least one"):
        PricingService().calculate_order(())


def test_decimal_path_differs_from_binary_float_and_never_returns_float(
    products: tuple[Product, Product],
) -> None:
    product = _with_rrp(products[0], "0.29")

    result = PricingService().calculate_order(((product, 3),), Decimal("0.10"))
    ex_gst_from_binary_float = Decimal.from_float(0.29 / 1.10)

    assert result.lines[0].unit_price_ex_gst != ex_gst_from_binary_float
    assert result.lines[0].unit_price_ex_gst * Decimal("1.10") == Decimal("0.29")
    assert all(
        isinstance(value, Decimal)
        for value in (
            result.lines[0].unit_price_incl_gst,
            result.lines[0].unit_price_ex_gst,
            result.lines[0].line_subtotal,
            result.order_subtotal,
            result.gst_amount,
            result.shipment_fee,
            result.order_total,
        )
    )


def test_pricing_results_are_immutable(products: tuple[Product, Product]) -> None:
    result = PricingService().calculate_order(((products[0], 1),))

    with pytest.raises(ValidationError):
        result.order_total = Decimal("0.00")
    with pytest.raises(ValidationError):
        result.lines[0].line_subtotal = Decimal("0.00")


@pytest.mark.parametrize(
    ("precision", "rounding"),
    [
        (4, ROUND_DOWN),
        (6, ROUND_HALF_EVEN),
        (10, ROUND_DOWN),
        (28, ROUND_HALF_EVEN),
    ],
)
def test_external_context_does_not_change_pricing_results(
    products: tuple[Product, Product], precision: int, rounding: str
) -> None:
    first = _with_rrp(products[0], "29.9900")
    second = _with_rrp(products[1], "1.1055")
    service = PricingService()
    expected_ex_gst = service.calculate_ex_gst_unit_price(first.rrp_aud_incl_gst)
    expected = service.calculate_order(((first, 3), (second, 2)), Decimal("1.005"))

    with localcontext(Context(prec=precision, rounding=rounding)):
        actual_ex_gst = service.calculate_ex_gst_unit_price(first.rrp_aud_incl_gst)
        actual = service.calculate_order(((first, 3), (second, 2)), Decimal("1.005"))

    assert actual_ex_gst == expected_ex_gst
    assert actual == expected


def test_low_external_precision_cannot_truncate_ex_gst_unit_price(
    products: tuple[Product, Product],
) -> None:
    product = _with_rrp(products[0], "29.9900")

    with localcontext(Context(prec=4, rounding=ROUND_DOWN)):
        line = PricingService().calculate_line(product, 3)

    assert str(line.unit_price_ex_gst).startswith("27.2636363636363636363636363636")
    assert line.unit_price_ex_gst != Decimal("27.26")
    assert line.line_subtotal == Decimal("81.79")


def test_high_precision_large_amount_is_accepted_and_priced_under_low_external_precision(
    write_data_directory: object,
    orders_payload: dict[str, object],
    products_payload: dict[str, object],
    tracking_payload: dict[str, object],
) -> None:
    rrp_text = "1234567890123456789012345678901234567890.1234567890123456789012345678901234567890"
    quantity = 98765432101234567890
    shipment_fee = Decimal("999999999999999999999999.995")
    products_payload["products"][0]["rrp_aud_incl_gst"] = rrp_text
    orders_payload["orders"][0]["items"][0]["quantity"] = quantity
    data_directory = write_data_directory(orders_payload, products_payload, tracking_payload)

    with localcontext(Context(prec=4, rounding=ROUND_DOWN)):
        product = RepositoryCollection(data_directory).products.get_by_sku("TEST-SKU-1")
        result = PricingService().calculate_order(((product, quantity),), shipment_fee)

    with localcontext(Context(prec=300, rounding=ROUND_HALF_EVEN)):
        expected_ex_gst = Decimal(rrp_text) / Decimal("1.10")
        expected_line = (expected_ex_gst * quantity).quantize(
            Decimal("0.01"), rounding=ROUND_HALF_UP
        )
        expected_gst = (expected_line * Decimal("0.10")).quantize(
            Decimal("0.01"), rounding=ROUND_HALF_UP
        )
        expected_fee = shipment_fee.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
        expected_total = (expected_line + expected_gst + expected_fee).quantize(
            Decimal("0.01"), rounding=ROUND_HALF_UP
        )

    assert product.rrp_aud_incl_gst == Decimal(rrp_text)
    assert str(result.lines[0].unit_price_ex_gst)[:120] == str(expected_ex_gst)[:120]
    assert len(result.lines[0].unit_price_ex_gst.as_tuple().digits) > 150
    assert result.lines[0].line_subtotal == expected_line
    assert result.order_subtotal == expected_line
    assert result.gst_amount == expected_gst
    assert result.shipment_fee == expected_fee
    assert result.order_total == expected_total


def test_order_level_amounts_are_identical_across_external_contexts(
    products: tuple[Product, Product],
) -> None:
    first = _with_rrp(products[0], "29.9900")
    second = _with_rrp(products[1], "1.1055")
    service = PricingService()
    expected = service.calculate_order(((first, 3), (second, 2)), Decimal("1.005"))

    for precision, rounding in (
        (4, ROUND_DOWN),
        (6, ROUND_HALF_EVEN),
        (10, ROUND_DOWN),
        (28, ROUND_HALF_EVEN),
    ):
        with localcontext(Context(prec=precision, rounding=rounding)):
            actual = service.calculate_order(((first, 3), (second, 2)), Decimal("1.005"))

        assert [line.line_subtotal for line in actual.lines] == [
            line.line_subtotal for line in expected.lines
        ]
        assert actual.order_subtotal == expected.order_subtotal
        assert actual.gst_amount == expected.gst_amount
        assert actual.shipment_fee == expected.shipment_fee
        assert actual.order_total == expected.order_total


def test_pricing_does_not_modify_caller_context_flags_or_traps(
    products: tuple[Product, Product],
) -> None:
    product = _with_rrp(products[0], "29.9900")

    with localcontext(Context(prec=4, rounding=ROUND_DOWN)) as caller_context:
        caller_context.flags[Inexact] = True
        caller_context.flags[Rounded] = True
        caller_context.traps[DivisionByZero] = False
        before = caller_context.copy()

        PricingService().calculate_order(((product, 3),), Decimal("1.005"))
        after = getcontext().copy()

    assert after.prec == before.prec
    assert after.rounding == before.rounding
    assert after.Emin == before.Emin
    assert after.Emax == before.Emax
    assert after.flags == before.flags
    assert after.traps == before.traps
