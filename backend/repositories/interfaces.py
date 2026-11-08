"""Small read-only protocols used by later service-layer dependencies."""

from typing import Protocol

from backend.models import Order, Product, TrackingGroup


class OrderReader(Protocol):
    def list_orders(self) -> tuple[Order, ...]: ...

    def get_by_order_no(self, order_no: str) -> Order: ...


class ProductReader(Protocol):
    def list_products(self) -> tuple[Product, ...]: ...

    def get_by_sku(self, sku: str) -> Product: ...


class TrackingReader(Protocol):
    def list_tracking_groups(self) -> tuple[TrackingGroup, ...]: ...

    def get_by_group_id(self, tracking_group_id: str) -> TrackingGroup: ...
