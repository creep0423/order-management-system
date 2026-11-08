"""Pure Decimal pricing rules approved for Phase 3."""

from collections.abc import Iterable
from decimal import (
    MAX_EMAX,
    MAX_PREC,
    MIN_EMIN,
    ROUND_HALF_EVEN,
    ROUND_HALF_UP,
    Context,
    Decimal,
    DecimalException,
    DivisionByZero,
    InvalidOperation,
    Overflow,
    localcontext,
)

from backend.models import LinePricingResult, PricingResult, Product
from backend.services.exceptions import (
    InvalidMonetaryAmountError,
    InvalidPricingInputError,
    InvalidQuantityError,
    PricingComputationError,
)

GST_DIVISOR = Decimal("1.10")
GST_RATE = Decimal("0.10")
MONEY_QUANTUM = Decimal("0.01")
ZERO_MONEY = Decimal("0.00")
MINIMUM_WORKING_PRECISION = 28
DIVISION_GUARD_DIGITS = 32


def _decimal_span(amount: Decimal) -> int:
    """Return digits needed to preserve the coefficient and exponent range."""

    decimal_tuple = amount.as_tuple()
    exponent = decimal_tuple.exponent
    if not isinstance(exponent, int):
        raise InvalidMonetaryAmountError
    return max(1, len(decimal_tuple.digits)) + abs(exponent)


def _integer_digits(value: int) -> int:
    return Decimal(abs(value)).adjusted() + 1


def _calculation_context(
    amounts: Iterable[Decimal],
    *,
    integer_factors: Iterable[int] = (),
    accumulation_count: int = 1,
) -> Context:
    """Build a fresh context sized from every input that can grow a result."""

    amount_span = max((_decimal_span(amount) for amount in amounts), default=1)
    multiplication_growth = sum(_integer_digits(factor) for factor in integer_factors)
    accumulation_growth = _integer_digits(accumulation_count) if accumulation_count > 1 else 0
    precision = max(
        MINIMUM_WORKING_PRECISION,
        amount_span + multiplication_growth + accumulation_growth + DIVISION_GUARD_DIGITS,
    )
    if precision > MAX_PREC:
        raise PricingComputationError
    return Context(
        prec=precision,
        rounding=ROUND_HALF_EVEN,
        Emin=MIN_EMIN,
        Emax=MAX_EMAX,
        traps=[InvalidOperation, DivisionByZero, Overflow],
    )


class PricingService:
    """Calculate line and order totals without I/O or mutable order state."""

    @staticmethod
    def _validate_amount(amount: object) -> Decimal:
        if not isinstance(amount, Decimal) or not amount.is_finite() or amount < 0:
            raise InvalidMonetaryAmountError
        return amount

    @staticmethod
    def _validate_quantity(quantity: object) -> int:
        if type(quantity) is not int or quantity <= 0:
            raise InvalidQuantityError
        return quantity

    def calculate_ex_gst_unit_price(self, rrp_incl_gst: Decimal) -> Decimal:
        """Remove GST without quantizing the internal unit price."""

        rrp = self._validate_amount(rrp_incl_gst)
        try:
            with localcontext(_calculation_context((rrp,))):
                return rrp / GST_DIVISOR
        except DecimalException:
            raise PricingComputationError from None

    def calculate_line(self, product: Product, quantity: int) -> LinePricingResult:
        """Price one product line and round only its subtotal."""

        validated_quantity = self._validate_quantity(quantity)
        rrp = self._validate_amount(product.rrp_aud_incl_gst)
        try:
            context = _calculation_context((rrp,), integer_factors=(validated_quantity,))
            with localcontext(context):
                ex_gst_unit_price = rrp / GST_DIVISOR
                line_subtotal = (ex_gst_unit_price * validated_quantity).quantize(
                    MONEY_QUANTUM,
                    rounding=ROUND_HALF_UP,
                )
        except DecimalException:
            raise PricingComputationError from None
        return LinePricingResult(
            sku=product.sku,
            quantity=validated_quantity,
            unit_price_incl_gst=rrp,
            unit_price_ex_gst=ex_gst_unit_price,
            line_subtotal=line_subtotal,
        )

    def calculate_order(
        self,
        product_lines: Iterable[tuple[Product, int]],
        shipment_fee: Decimal = ZERO_MONEY,
    ) -> PricingResult:
        """Price an isolated order from validated products and quantities."""

        normalized_fee = self._validate_amount(shipment_fee)
        lines = tuple(self.calculate_line(product, quantity) for product, quantity in product_lines)
        if not lines:
            raise InvalidPricingInputError("at least one order line is required")
        try:
            context = _calculation_context(
                tuple(line.line_subtotal for line in lines) + (normalized_fee,),
                accumulation_count=len(lines) + 2,
            )
            with localcontext(context):
                order_subtotal = sum(
                    (line.line_subtotal for line in lines),
                    start=ZERO_MONEY,
                )
                gst_amount = (order_subtotal * GST_RATE).quantize(
                    MONEY_QUANTUM,
                    rounding=ROUND_HALF_UP,
                )
                normalized_fee = normalized_fee.quantize(
                    MONEY_QUANTUM,
                    rounding=ROUND_HALF_UP,
                )
                order_total = (order_subtotal + gst_amount + normalized_fee).quantize(
                    MONEY_QUANTUM,
                    rounding=ROUND_HALF_UP,
                )
        except DecimalException:
            raise PricingComputationError from None
        return PricingResult(
            lines=lines,
            order_subtotal=order_subtotal,
            gst_amount=gst_amount,
            shipment_fee=normalized_fee,
            order_total=order_total,
        )
