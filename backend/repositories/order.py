"""Read-only order repository backed by orders.json."""

from pathlib import Path

from backend.models import Customer, Order, OrderItem, ShippingAddress
from backend.models.source import OrdersFileSource, OrderSource
from backend.repositories.exceptions import DuplicateIdentifierError, RecordNotFoundError
from backend.repositories.loader import load_json_model


class OrderRepository:
    """Load, cache and query validated orders without business calculations."""

    def __init__(self, path: Path) -> None:
        source = load_json_model(path, OrdersFileSource)
        orders = tuple(self._to_domain(record, source.currency) for record in source.orders)
        by_order_no = {order.order_no: order for order in orders}
        if len(by_order_no) != len(orders):
            raise DuplicateIdentifierError("order")
        self._orders = orders
        self._by_order_no = by_order_no

    @staticmethod
    def _to_domain(order: OrderSource, currency: str) -> Order:
        return Order(
            order_no=order.order_no,
            order_date=order.order_date,
            company=order.company,
            customer=Customer(**order.customer.model_dump()),
            shipping_address=ShippingAddress(**order.shipping_address.model_dump()),
            status=order.status,
            currency=currency,
            items=tuple(OrderItem(**item.model_dump()) for item in order.items),
        )

    def list_orders(self) -> tuple[Order, ...]:
        return self._orders

    def get_by_order_no(self, order_no: str) -> Order:
        try:
            return self._by_order_no[order_no]
        except KeyError:
            raise RecordNotFoundError("order") from None

    def list_by_tracking_group(self, tracking_group_id: str) -> tuple[Order, ...]:
        return tuple(
            order
            for order in self._orders
            if any(item.tracking_group_id == tracking_group_id for item in order.items)
        )
