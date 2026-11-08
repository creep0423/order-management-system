"""API v1 and OpenAPI contract tests for Batch J1 package estimation."""

import json
import re
from datetime import UTC, date, datetime
from decimal import Decimal
from typing import Any

import pytest
from fastapi.testclient import TestClient
from pydantic import ValidationError

from backend.api.dependencies import get_order_service
from backend.api.schemas import (
    CustomerResponse,
    Money,
    OrderDetailResponse,
    OrderPricingResponse,
    PackageDimensionsResponse,
    PackageEstimationResponse,
    PackageItemReferenceResponse,
    PackageItemResponse,
    PackageResponse,
    PackageWeightResponse,
    ShippingAddressResponse,
    ShippingQuoteResponse,
)
from backend.main import app
from backend.models import PackageReasonCode
from backend.repositories import RepositoryCollection
from backend.services import (
    OrderService,
    PackageEstimationService,
    StaticPackagingRuleSetReader,
)
from backend.tests.packaging_fixtures import NOW as NOW_FOR_PACKAGES
from backend.tests.packaging_fixtures import ruleset_for_skus

MEASURE_PATTERN = re.compile(r"^\d+(\.\d+)?$")
TEST_SKUS = ("TEST-SKU-1", "TEST-SKU-2")


@pytest.fixture
def repositories(
    write_data_directory: object,
    orders_payload: dict[str, object],
    products_payload: dict[str, object],
    tracking_payload: dict[str, object],
) -> RepositoryCollection:
    data_directory = write_data_directory(orders_payload, products_payload, tracking_payload)
    return RepositoryCollection(data_directory)


def _service(repositories: RepositoryCollection, *, with_ruleset: bool) -> OrderService:
    if not with_ruleset:
        return OrderService(repositories)
    ruleset = ruleset_for_skus(TEST_SKUS)
    return OrderService(
        repositories,
        package_estimation_service=PackageEstimationService(
            StaticPackagingRuleSetReader(ruleset), clock=lambda: NOW_FOR_PACKAGES
        ),
    )


def _client(service: object) -> TestClient:
    app.dependency_overrides[get_order_service] = lambda: service
    return TestClient(app, raise_server_exceptions=False)


def _detail_payload(repositories: RepositoryCollection, *, with_ruleset: bool) -> dict[str, Any]:
    client = _client(_service(repositories, with_ruleset=with_ruleset))
    try:
        response = client.get("/api/v1/orders/TEST-ORDER-001")
    finally:
        client.close()
        app.dependency_overrides.clear()
    assert response.status_code == 200
    return response.json()["data"]


# ------------------------------------------------------------- default runtime


def test_default_runtime_fails_closed_without_a_ruleset(
    repositories: RepositoryCollection,
) -> None:
    data = _detail_payload(repositories, with_ruleset=False)

    estimation = data["package_estimation"]
    assert estimation["status"] == "unavailable"
    assert estimation["reason_code"] == "PACKAGE_RULES_NOT_CONFIGURED"
    assert estimation["source"] is None
    assert estimation["ruleset_id"] is None
    assert estimation["ruleset_version"] is None
    assert estimation["synthetic_ruleset"] is False
    assert estimation["packages"] == []
    assert estimation["checked_at"].endswith("Z")
    # Tracking and the D-015 quote are untouched by the package gap.
    assert len(data["tracking_results"]) == 2
    assert data["shipping_quote"]["status"] == "unsupported"


def test_default_runtime_never_injects_synthetic_fixtures(
    repositories: RepositoryCollection,
) -> None:
    from backend.main import build_package_estimation_service

    estimation = build_package_estimation_service().estimate_for_order(
        repositories.orders.get_by_order_no("TEST-ORDER-001"),
        repositories.get_products_for_order("TEST-ORDER-001"),
    )

    assert estimation.status.value == "unavailable"
    assert estimation.reason_code is PackageReasonCode.PACKAGE_RULES_NOT_CONFIGURED
    assert estimation.packages == ()
    assert estimation.synthetic_ruleset is False


# ------------------------------------------------------------ available shape


def test_available_estimation_projects_frozen_package_shape(
    repositories: RepositoryCollection,
) -> None:
    data = _detail_payload(repositories, with_ruleset=True)

    estimation = data["package_estimation"]
    assert estimation["status"] == "available"
    assert estimation["reason_code"] is None
    assert estimation["source"] == "rules"
    assert estimation["ruleset_id"] == "synthetic-ruleset-j1"
    assert estimation["ruleset_version"] == "synthetic-v1"
    assert estimation["synthetic_ruleset"] is True
    assert estimation["packages"]

    first = estimation["packages"][0]
    assert set(first) == {
        "package_id",
        "source",
        "items",
        "dimensions",
        "weight",
        "ruleset_id",
        "ruleset_version",
    }
    assert first["source"] == "rules"
    assert first["ruleset_id"] == "synthetic-ruleset-j1"
    assert first["ruleset_version"] == "synthetic-v1"

    for key in ("length_mm", "width_mm", "height_mm", "volume_mm3"):
        assert MEASURE_PATTERN.fullmatch(first["dimensions"][key]) is not None
    for key in ("item_weight_g", "packaging_weight_g", "gross_weight_g"):
        assert MEASURE_PATTERN.fullmatch(first["weight"][key]) is not None

    item = first["items"][0]
    assert set(item) == {"order_item_ref", "sku", "quantity"}
    assert set(item["order_item_ref"]) == {"order_number", "line_index"}
    assert item["order_item_ref"]["order_number"] == "TEST-ORDER-001"
    assert isinstance(item["order_item_ref"]["line_index"], int)
    assert item["quantity"] > 0


def test_package_projection_hides_internal_diagnostics_and_material(
    repositories: RepositoryCollection,
) -> None:
    data = _detail_payload(repositories, with_ruleset=True)

    serialized = json.dumps(data)
    for forbidden in (
        "diagnostics",
        "material_id",
        "input_fingerprint",
        "capacity",
        "policy",
        "tare",
    ):
        assert forbidden not in serialized


def test_list_projection_never_contains_packages(repositories: RepositoryCollection) -> None:
    client = _client(_service(repositories, with_ruleset=True))
    try:
        response = client.get("/api/v1/orders")
    finally:
        client.close()
        app.dependency_overrides.clear()

    assert response.status_code == 200
    serialized = json.dumps(response.json())
    assert "package_estimation" not in serialized
    assert "packages" not in serialized


def test_estimation_fault_still_returns_200_with_a_stable_projection(
    repositories: RepositoryCollection,
) -> None:
    class RaisingEstimation:
        def estimate_for_order(self, order: object, products: object) -> object:
            raise RuntimeError("synthetic estimation failure")

    service = OrderService(
        repositories,
        package_estimation_service=RaisingEstimation(),  # type: ignore[arg-type]
    )
    client = _client(service)
    try:
        response = client.get("/api/v1/orders/TEST-ORDER-001")
    finally:
        client.close()
        app.dependency_overrides.clear()

    assert response.status_code == 200
    estimation = response.json()["data"]["package_estimation"]
    assert estimation["status"] == "unavailable"
    assert estimation["reason_code"] == "PACKAGE_DATA_INCOMPLETE"
    assert estimation["packages"] == []


# ------------------------------------------------------------- schema guards


def _dimensions(**overrides: object) -> PackageDimensionsResponse:
    values: dict[str, object] = {
        "length_mm": Decimal("210"),
        "width_mm": Decimal("160"),
        "height_mm": Decimal("110"),
        "volume_mm3": Decimal("3696000"),
    }
    values.update(overrides)
    return PackageDimensionsResponse(**values)  # type: ignore[arg-type]


def _package(**overrides: object) -> PackageResponse:
    values: dict[str, object] = {
        "package_id": "PKG-001",
        "source": "rules",
        "items": (
            PackageItemResponse(
                order_item_ref={"order_number": "TEST-ORDER-001", "line_index": 0},  # type: ignore[arg-type]
                sku="TEST-SKU-1",
                quantity=2,
            ),
        ),
        "dimensions": _dimensions(),
        "weight": PackageWeightResponse(
            item_weight_g=Decimal("600"),
            packaging_weight_g=Decimal("50"),
            gross_weight_g=Decimal("650"),
        ),
        "ruleset_id": "synthetic-ruleset-j1",
        "ruleset_version": "synthetic-v1",
    }
    values.update(overrides)
    return PackageResponse(**values)  # type: ignore[arg-type]


def _estimation(**overrides: object) -> PackageEstimationResponse:
    values: dict[str, object] = {
        "status": "available",
        "reason_code": None,
        "checked_at": datetime(2026, 11, 8, 1, 2, tzinfo=UTC),
        "source": "rules",
        "ruleset_id": "synthetic-ruleset-j1",
        "ruleset_version": "synthetic-v1",
        "synthetic_ruleset": True,
        "packages": (_package(),),
    }
    values.update(overrides)
    return PackageEstimationResponse(**values)  # type: ignore[arg-type]


def test_dimensions_response_rejects_inconsistent_volume() -> None:
    with pytest.raises(ValidationError, match="volume_mm3"):
        _dimensions(volume_mm3=Decimal("1"))


def test_weight_response_rejects_inconsistent_gross() -> None:
    with pytest.raises(ValidationError, match="gross_weight_g"):
        PackageWeightResponse(
            item_weight_g=Decimal("600"),
            packaging_weight_g=Decimal("50"),
            gross_weight_g=Decimal("700"),
        )


def test_package_response_requires_positive_quantity() -> None:
    with pytest.raises(ValidationError):
        PackageItemResponse(
            order_item_ref={"order_number": "TEST-ORDER-001", "line_index": 0},  # type: ignore[arg-type]
            sku="TEST-SKU-1",
            quantity=0,
        )


def test_rules_package_response_requires_ruleset_provenance() -> None:
    with pytest.raises(ValidationError, match="ruleset"):
        _package(ruleset_id=None, ruleset_version=None)


@pytest.mark.parametrize(
    "overrides",
    [
        {"packages": ()},
        {"reason_code": "PACKAGE_DATA_INCOMPLETE"},
        {"source": None},
        {"ruleset_id": None, "ruleset_version": None},
    ],
)
def test_estimation_response_rejects_illegal_available_combinations(
    overrides: dict[str, object],
) -> None:
    with pytest.raises(ValidationError):
        _estimation(**overrides)


@pytest.mark.parametrize(
    "overrides",
    [
        {"reason_code": None},
        {"packages": (_package(),)},
        {"source": "rules"},
    ],
)
def test_estimation_response_rejects_illegal_unavailable_combinations(
    overrides: dict[str, object],
) -> None:
    values: dict[str, object] = {
        "status": "unavailable",
        "reason_code": "PACKAGE_RULES_NOT_CONFIGURED",
        "source": None,
        "ruleset_id": None,
        "ruleset_version": None,
        "synthetic_ruleset": False,
        "packages": (),
    }
    values.update(overrides)
    with pytest.raises(ValidationError):
        PackageEstimationResponse(**values)  # type: ignore[arg-type]


def test_estimation_requires_unique_package_ids() -> None:
    with pytest.raises(ValidationError, match="unique"):
        _estimation(packages=(_package(), _package()))


def test_estimation_measures_serialize_as_decimal_strings() -> None:
    payload = _package().model_dump(mode="json")

    assert payload["dimensions"] == {
        "length_mm": "210",
        "width_mm": "160",
        "height_mm": "110",
        "volume_mm3": "3696000",
    }
    assert payload["weight"] == {
        "item_weight_g": "600",
        "packaging_weight_g": "50",
        "gross_weight_g": "650",
    }


# -------------------------------------------------------------------- OpenAPI


def test_openapi_documents_package_contract() -> None:
    schema = app.openapi()
    components = schema["components"]["schemas"]

    estimation = components["PackageEstimationResponse"]
    assert set(estimation["required"]) == {
        "status",
        "reason_code",
        "checked_at",
        "source",
        "ruleset_id",
        "ruleset_version",
        "synthetic_ruleset",
        "packages",
    }
    assert estimation["properties"]["status"]["enum"] == ["available", "unavailable"]
    reason = estimation["properties"]["reason_code"]
    reason_text = json.dumps(reason)
    assert "PACKAGE_RULES_NOT_CONFIGURED" in reason_text
    assert "PACKAGE_DATA_INCOMPLETE" in reason_text

    package = components["PackageResponse"]
    assert "material_id" not in package["properties"]
    assert "diagnostics" not in package["properties"]
    assert set(package["required"]) == {
        "package_id",
        "source",
        "items",
        "dimensions",
        "weight",
        "ruleset_id",
        "ruleset_version",
    }

    dimensions = components["PackageDimensionsResponse"]
    # Measurements are decimal strings, never JSON numbers.
    assert dimensions["properties"]["length_mm"]["type"] == "string"

    detail = components["OrderDetailResponse"]
    assert "package_estimation" in detail["required"]
    assert "package_estimation" in detail["properties"]

    # Tracking contract from Batch I is unchanged.
    tracking = components["TrackingResponse"]
    provider = tracking["properties"]["provider"]
    assert {"type": "null"} in provider["anyOf"]
    assert tracking["examples"][0]["provider"] is None


def _property_names(node: object) -> set[str]:
    names: set[str] = set()
    if isinstance(node, dict):
        properties = node.get("properties")
        if isinstance(properties, dict):
            names.update(properties)
        for value in node.values():
            names |= _property_names(value)
    elif isinstance(node, list):
        for value in node:
            names |= _property_names(value)
    return names


def test_openapi_package_schemas_expose_no_internal_fields_or_fixtures() -> None:
    schema = app.openapi()
    package_schemas = {
        name: value
        for name, value in schema["components"]["schemas"].items()
        if name.startswith("Package")
    }
    assert package_schemas

    exposed = _property_names(package_schemas)
    for forbidden in (
        "diagnostics",
        "material_id",
        "input_fingerprint",
        "capacity",
        "policy",
        "tare_weight_g",
    ):
        assert forbidden not in exposed

    serialized = json.dumps(package_schemas)
    for fixture_token in ("SYNTH-", "synthetic-ruleset", "SYNTH-ORDER", "@example.invalid"):
        assert fixture_token not in serialized


# --------------------------------------------- API projection cross-consistency


def test_estimation_rejects_a_package_ruleset_that_disagrees() -> None:
    drifted = _package(ruleset_version="synthetic-v9")

    with pytest.raises(ValidationError, match="ruleset must match"):
        _estimation(packages=(drifted,))


def test_detail_rejects_package_items_from_another_order() -> None:
    estimation = PackageEstimationResponse(
        status="available",
        reason_code=None,
        checked_at=datetime(2026, 11, 8, 1, 2, tzinfo=UTC),
        source="rules",
        ruleset_id="synthetic-ruleset-j1",
        ruleset_version="synthetic-v1",
        synthetic_ruleset=True,
        packages=(
            _package(
                items=(
                    PackageItemResponse(
                        order_item_ref=PackageItemReferenceResponse(  # type: ignore[arg-type]
                            order_number="OTHER-ORDER", line_index=0
                        ),
                        sku="TEST-SKU-1",
                        quantity=2,
                    ),
                )
            ),
        ),
    )

    with pytest.raises(ValidationError, match="line of this order"):
        OrderDetailResponse(
            order_number="TEST-ORDER-001",
            order_date=date(2026, 1, 2),
            company="Synthetic Company",
            customer=CustomerResponse(
                name="Test Customer",
                phone="0000000000",
                email="customer@example.invalid",
            ),
            shipping_address=ShippingAddressResponse(
                line1="1 Example Street",
                suburb="Exampleville",
                state="NSW",
                postcode="2000",
                country="Australia",
            ),
            status="IN_TRANSIT",
            currency="AUD",
            items=(),
            pricing=OrderPricingResponse(
                order_subtotal=Money(amount=Decimal("100.00")),
                gst_amount=Money(amount=Decimal("10.00")),
                order_total=Money(amount=Decimal("110.00")),
            ),
            quote_request_state="requested",
            shipping_quote=ShippingQuoteResponse(
                status="unsupported",
                reason_code="SHIPPING_QUOTE_NOT_IMPLEMENTED",
                checked_at=datetime(2026, 11, 8, 1, 2, tzinfo=UTC),
                quoted_fee=None,
                applied_fee=Money(amount=Decimal("0.00")),
            ),
            package_estimation=estimation,
            tracking_results=(),
        )


def test_api_package_measures_reject_floats() -> None:
    with pytest.raises(ValidationError):
        PackageDimensionsResponse.model_validate(
            {
                "length_mm": 210.0,
                "width_mm": 160.0,
                "height_mm": 110.0,
                "volume_mm3": 3696000.0,
            }
        )
    with pytest.raises(ValidationError):
        PackageWeightResponse.model_validate(
            {"item_weight_g": 600.0, "packaging_weight_g": 50.0, "gross_weight_g": 650.0}
        )
