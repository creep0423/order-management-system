"""Read-only integration checks against the local approved JSON baseline."""

import hashlib
import json
from datetime import date, datetime
from decimal import Decimal
from pathlib import Path

import pytest

from backend.repositories import RepositoryCollection

DATA_DIRECTORY = Path(__file__).resolve().parents[1] / "data"
DATA_FILES = ("orders.json", "skus.json", "skus_raw.json", "tracking.json")


def _hashes() -> dict[str, str]:
    return {
        name: hashlib.sha256((DATA_DIRECTORY / name).read_bytes()).hexdigest()
        for name in DATA_FILES
    }


def test_real_json_baseline_loads_with_closed_references_and_no_mutation() -> None:
    before = _hashes()

    repositories = RepositoryCollection()
    orders = repositories.orders.list_orders()
    products = repositories.products.list_products()
    groups = repositories.tracking.list_tracking_groups()

    assert len(orders) == 2
    assert sum(len(order.items) for order in orders) == 9
    assert sum(item.quantity for order in orders for item in order.items) == 31
    assert len(products) == 9
    assert len(groups) == 3
    assert all(
        len(repositories.get_products_for_order(order.order_no)) == len(order.items)
        for order in orders
    )
    assert all(repositories.get_tracking_groups_for_order(order.order_no) for order in orders)
    assert _hashes() == before


def test_real_json_uses_typed_dates_decimals_and_preserves_missing_data() -> None:
    repositories = RepositoryCollection()
    orders = repositories.orders.list_orders()
    products = repositories.products.list_products()

    assert all(isinstance(order.order_date, date) for order in orders)
    assert all(isinstance(product.source_date, datetime) for product in products)
    assert all(isinstance(product.rrp_aud_incl_gst, Decimal) for product in products)
    assert sum(product.description is None for product in products) == 3
    assert sum(product.eta_days is None for product in products) == 6
    assert sum(product.eta_raw == "0Days" and product.eta_days == 0 for product in products) == 2


def test_default_repository_paths_do_not_depend_on_current_working_directory(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.chdir(tmp_path)

    repositories = RepositoryCollection()

    assert len(repositories.orders.list_orders()) == 2


def test_normalized_and_raw_product_sources_remain_consistent() -> None:
    normalized = json.loads((DATA_DIRECTORY / "skus.json").read_text(encoding="utf-8"))
    raw = json.loads((DATA_DIRECTORY / "skus_raw.json").read_text(encoding="utf-8"))
    normalized_by_sku = {product["sku"]: product for product in normalized["products"]}
    raw_by_sku = {product["SKU"]: product for product in raw["records"]}

    assert set(normalized_by_sku) == set(raw_by_sku)
    assert all(
        normalized_by_sku[sku]["rrp_aud_incl_gst"] == raw_by_sku[sku]["RRP"]
        for sku in normalized_by_sku
    )
    assert all(
        normalized_by_sku[sku]["barcode"] == raw_by_sku[sku]["Barcode"] for sku in normalized_by_sku
    )
    assert all(
        normalized_by_sku[sku]["description"] is None
        and normalized_by_sku[sku]["description_status"] == "missing"
        for sku in normalized_by_sku
        if raw_by_sku[sku]["Description"] == "."
    )
    assert all(
        normalized_by_sku[sku]["eta_days"] is None
        for sku in normalized_by_sku
        if raw_by_sku[sku]["ETA"] == "nullDays"
    )
