"""Repository unit tests using only safe synthetic data."""

import json
from decimal import Decimal
from pathlib import Path

import pytest
from pydantic import ValidationError

from backend.repositories import (
    DataSourceNotFoundError,
    DataSourceParseError,
    DataValidationError,
    DuplicateIdentifierError,
    MissingReferenceError,
    OrderRepository,
    ProductRepository,
    RecordNotFoundError,
    RepositoryCollection,
    TrackingRepository,
)


def _write_json(path: Path, payload: object) -> None:
    path.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")


def test_order_repository_lists_and_gets_order(
    write_data_directory: object,
    orders_payload: dict[str, object],
    products_payload: dict[str, object],
    tracking_payload: dict[str, object],
) -> None:
    data_directory = write_data_directory(orders_payload, products_payload, tracking_payload)
    repository = OrderRepository(data_directory / "orders.json")

    assert len(repository.list_orders()) == 1
    assert repository.get_by_order_no("TEST-ORDER-001").items[0].sku == "TEST-SKU-1"


def test_product_repository_lists_and_gets_decimal_product(
    write_data_directory: object,
    orders_payload: dict[str, object],
    products_payload: dict[str, object],
    tracking_payload: dict[str, object],
) -> None:
    data_directory = write_data_directory(orders_payload, products_payload, tracking_payload)
    repository = ProductRepository(data_directory / "skus.json")

    assert len(repository.list_products()) == 2
    assert repository.get_by_sku("TEST-SKU-1").rrp_aud_incl_gst == Decimal("29.9900")


def test_tracking_repository_lists_and_gets_group(
    write_data_directory: object,
    orders_payload: dict[str, object],
    products_payload: dict[str, object],
    tracking_payload: dict[str, object],
) -> None:
    data_directory = write_data_directory(orders_payload, products_payload, tracking_payload)
    repository = TrackingRepository(data_directory / "tracking.json")

    assert len(repository.list_tracking_groups()) == 2
    assert repository.get_by_group_id("GROUP-1").carrier == "Synthetic Carrier"


@pytest.mark.parametrize(
    ("repository_name", "missing_identifier"),
    [("orders", "NO-ORDER"), ("products", "NO-SKU"), ("tracking", "NO-GROUP")],
)
def test_single_record_query_reports_not_found(
    write_data_directory: object,
    orders_payload: dict[str, object],
    products_payload: dict[str, object],
    tracking_payload: dict[str, object],
    repository_name: str,
    missing_identifier: str,
) -> None:
    data_directory = write_data_directory(orders_payload, products_payload, tracking_payload)
    repositories = RepositoryCollection(data_directory)
    queries = {
        "orders": repositories.orders.get_by_order_no,
        "products": repositories.products.get_by_sku,
        "tracking": repositories.tracking.get_by_group_id,
    }

    with pytest.raises(RecordNotFoundError):
        queries[repository_name](missing_identifier)


def test_repository_collection_resolves_product_associations(
    write_data_directory: object,
    orders_payload: dict[str, object],
    products_payload: dict[str, object],
    tracking_payload: dict[str, object],
) -> None:
    data_directory = write_data_directory(orders_payload, products_payload, tracking_payload)
    repositories = RepositoryCollection(data_directory)

    products = repositories.get_products_for_order("TEST-ORDER-001")

    assert [product.sku for product in products] == ["TEST-SKU-1", "TEST-SKU-2"]


def test_repository_collection_resolves_unique_tracking_groups(
    write_data_directory: object,
    orders_payload: dict[str, object],
    products_payload: dict[str, object],
    tracking_payload: dict[str, object],
) -> None:
    orders_payload["orders"][0]["items"].append(
        {"sku": "TEST-SKU-1", "quantity": 1, "tracking_group_id": "GROUP-1"}
    )
    data_directory = write_data_directory(orders_payload, products_payload, tracking_payload)
    repositories = RepositoryCollection(data_directory)

    groups = repositories.get_tracking_groups_for_order("TEST-ORDER-001")

    assert [group.tracking_group_id for group in groups] == ["GROUP-1", "GROUP-2"]


def test_repository_collection_resolves_orders_for_product(
    write_data_directory: object,
    orders_payload: dict[str, object],
    products_payload: dict[str, object],
    tracking_payload: dict[str, object],
) -> None:
    data_directory = write_data_directory(orders_payload, products_payload, tracking_payload)
    repositories = RepositoryCollection(data_directory)

    orders = repositories.get_orders_for_product("TEST-SKU-2")

    assert [order.order_no for order in orders] == ["TEST-ORDER-001"]


def test_duplicate_order_identifier_is_rejected(
    write_data_directory: object,
    orders_payload: dict[str, object],
    products_payload: dict[str, object],
    tracking_payload: dict[str, object],
) -> None:
    orders_payload["orders"].append(orders_payload["orders"][0].copy())
    data_directory = write_data_directory(orders_payload, products_payload, tracking_payload)

    with pytest.raises(DuplicateIdentifierError, match="order"):
        OrderRepository(data_directory / "orders.json")


def test_duplicate_sku_identifier_is_rejected(
    write_data_directory: object,
    orders_payload: dict[str, object],
    products_payload: dict[str, object],
    tracking_payload: dict[str, object],
) -> None:
    products_payload["products"].append(products_payload["products"][0].copy())
    products_payload["record_count"] = 3
    data_directory = write_data_directory(orders_payload, products_payload, tracking_payload)

    with pytest.raises(DuplicateIdentifierError, match="SKU"):
        ProductRepository(data_directory / "skus.json")


def test_duplicate_tracking_json_key_is_rejected(tmp_path: Path) -> None:
    path = tmp_path / "tracking.json"
    path.write_text(
        '{"GROUP-1":{"carrier":"A","tracking_number":"1"},'
        '"GROUP-1":{"carrier":"B","tracking_number":"2"}}',
        encoding="utf-8",
    )

    with pytest.raises(DuplicateIdentifierError, match="JSON object key"):
        TrackingRepository(path)


def test_missing_sku_reference_is_rejected(
    write_data_directory: object,
    orders_payload: dict[str, object],
    products_payload: dict[str, object],
    tracking_payload: dict[str, object],
) -> None:
    orders_payload["orders"][0]["items"][0]["sku"] = "MISSING-SKU"
    data_directory = write_data_directory(orders_payload, products_payload, tracking_payload)

    with pytest.raises(MissingReferenceError, match="SKU"):
        RepositoryCollection(data_directory)


def test_missing_tracking_group_reference_is_rejected(
    write_data_directory: object,
    orders_payload: dict[str, object],
    products_payload: dict[str, object],
    tracking_payload: dict[str, object],
) -> None:
    orders_payload["orders"][0]["items"][0]["tracking_group_id"] = "MISSING-GROUP"
    data_directory = write_data_directory(orders_payload, products_payload, tracking_payload)

    with pytest.raises(MissingReferenceError, match="tracking group"):
        RepositoryCollection(data_directory)


def test_missing_file_has_classified_error(tmp_path: Path) -> None:
    with pytest.raises(DataSourceNotFoundError, match="orders.json"):
        OrderRepository(tmp_path / "orders.json")


def test_invalid_json_has_classified_error(tmp_path: Path) -> None:
    path = tmp_path / "orders.json"
    path.write_text("{invalid", encoding="utf-8")

    with pytest.raises(DataSourceParseError, match="orders.json"):
        OrderRepository(path)


def test_data_validation_failure_is_classified_without_payload_leakage(
    tmp_path: Path, orders_payload: dict[str, object]
) -> None:
    marker = "private-marker@example.invalid"
    orders_payload["orders"][0]["customer"]["email"] = marker
    orders_payload["orders"][0]["items"][0]["quantity"] = marker
    path = tmp_path / "orders.json"
    _write_json(path, orders_payload)

    with pytest.raises(DataValidationError) as captured:
        OrderRepository(path)

    error = captured.value
    assert error.source_name == "orders.json"
    assert error.record_path == "orders[0].items[0]"
    assert error.field_path == "quantity"
    assert error.error_type == "int_type"
    assert marker not in str(error)
    assert marker not in repr(error.diagnostics)
    assert error.__context__ is None
    assert error.__cause__ is None


def test_data_validation_diagnostic_sanitizes_unexpected_input_key(
    tmp_path: Path, orders_payload: dict[str, object]
) -> None:
    marker = "private-marker@example.invalid"
    orders_payload["orders"][0][marker] = "sensitive input"
    path = tmp_path / "orders.json"
    _write_json(path, orders_payload)

    with pytest.raises(DataValidationError) as captured:
        OrderRepository(path)

    error = captured.value
    assert error.record_path == "orders[0]"
    assert error.field_path == "<key>"
    assert error.error_type == "extra_forbidden"
    assert marker not in str(error)
    assert marker not in repr(error.diagnostics)


def test_product_validation_diagnostic_identifies_record_and_field_safely(
    tmp_path: Path, products_payload: dict[str, object]
) -> None:
    marker = "private-decimal-marker@example.invalid"
    products_payload["products"][0]["rrp_aud_incl_gst"] = marker
    path = tmp_path / "skus.json"
    _write_json(path, products_payload)

    with pytest.raises(DataValidationError) as captured:
        ProductRepository(path)

    error = captured.value
    assert error.source_name == "skus.json"
    assert error.record_path == "products[0]"
    assert error.field_path == "rrp_aud_incl_gst"
    assert error.error_type == "value_error"
    assert marker not in str(error)
    assert marker not in repr(error.diagnostics)


def test_repositories_cache_data_after_initial_read(
    write_data_directory: object,
    orders_payload: dict[str, object],
    products_payload: dict[str, object],
    tracking_payload: dict[str, object],
) -> None:
    data_directory = write_data_directory(orders_payload, products_payload, tracking_payload)
    repository = ProductRepository(data_directory / "skus.json")
    (data_directory / "skus.json").write_text("{invalid", encoding="utf-8")

    assert len(repository.list_products()) == 2


def test_repository_collection_never_reads_or_modifies_raw_sku_source(
    write_data_directory: object,
    orders_payload: dict[str, object],
    products_payload: dict[str, object],
    tracking_payload: dict[str, object],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    data_directory = write_data_directory(orders_payload, products_payload, tracking_payload)
    raw_path = data_directory / "skus_raw.json"
    raw_path.write_bytes(b"raw provenance bytes that are not runtime product data")
    original_read_text = Path.read_text
    paths_read: list[str] = []

    def guarded_read_text(path: Path, *args: object, **kwargs: object) -> str:
        if path.name == "skus_raw.json":
            raise AssertionError("Repository attempted to read the raw SKU source")
        paths_read.append(path.name)
        return original_read_text(path, *args, **kwargs)

    monkeypatch.setattr(Path, "read_text", guarded_read_text)

    RepositoryCollection(data_directory)

    assert paths_read == ["orders.json", "skus.json", "tracking.json"]


def test_repository_returns_deeply_immutable_order_data(
    write_data_directory: object,
    orders_payload: dict[str, object],
    products_payload: dict[str, object],
    tracking_payload: dict[str, object],
) -> None:
    data_directory = write_data_directory(orders_payload, products_payload, tracking_payload)
    order = RepositoryCollection(data_directory).orders.get_by_order_no("TEST-ORDER-001")

    with pytest.raises(ValidationError):
        order.status = "CHANGED"
    with pytest.raises(TypeError):
        order.items[0] = order.items[1]
    with pytest.raises(ValidationError):
        order.items[0].quantity = 999


def test_repository_returns_immutable_product_collection_and_nested_dimensions(
    write_data_directory: object,
    orders_payload: dict[str, object],
    products_payload: dict[str, object],
    tracking_payload: dict[str, object],
) -> None:
    data_directory = write_data_directory(orders_payload, products_payload, tracking_payload)
    products = RepositoryCollection(data_directory).products.list_products()

    with pytest.raises(TypeError):
        products[0] = products[1]
    with pytest.raises(ValidationError):
        products[0].dimensions_mm.length = Decimal("999")
