"""Unified access point and cross-source integrity validation for repositories."""

from pathlib import Path

from backend.models import Order, Product, TrackingGroup
from backend.repositories.exceptions import MissingReferenceError
from backend.repositories.order import OrderRepository
from backend.repositories.product import ProductRepository
from backend.repositories.tracking import TrackingRepository

DEFAULT_DATA_DIRECTORY = Path(__file__).resolve().parents[1] / "data"


class RepositoryCollection:
    """Own the three cached repositories and validate their relationships."""

    def __init__(self, data_directory: Path = DEFAULT_DATA_DIRECTORY) -> None:
        self.orders = OrderRepository(data_directory / "orders.json")
        self.products = ProductRepository(data_directory / "skus.json")
        self.tracking = TrackingRepository(data_directory / "tracking.json")
        self._validate_references()

    def _validate_references(self) -> None:
        product_ids = {product.sku for product in self.products.list_products()}
        tracking_ids = {group.tracking_group_id for group in self.tracking.list_tracking_groups()}
        for order in self.orders.list_orders():
            for item in order.items:
                if item.sku not in product_ids:
                    raise MissingReferenceError("SKU")
                if item.tracking_group_id not in tracking_ids:
                    raise MissingReferenceError("tracking group")

    def get_products_for_order(self, order_no: str) -> tuple[Product, ...]:
        order = self.orders.get_by_order_no(order_no)
        return tuple(self.products.get_by_sku(item.sku) for item in order.items)

    def get_tracking_groups_for_order(self, order_no: str) -> tuple[TrackingGroup, ...]:
        order = self.orders.get_by_order_no(order_no)
        group_ids = dict.fromkeys(item.tracking_group_id for item in order.items)
        return tuple(self.tracking.get_by_group_id(group_id) for group_id in group_ids)

    def get_orders_for_product(self, sku: str) -> tuple[Order, ...]:
        self.products.get_by_sku(sku)
        return tuple(
            order
            for order in self.orders.list_orders()
            if any(item.sku == sku for item in order.items)
        )
