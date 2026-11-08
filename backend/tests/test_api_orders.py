"""API v1 tests for order responses, errors, OpenAPI and layer boundaries."""

import copy
import inspect
import json
import re
from datetime import UTC, datetime, timedelta, timezone
from decimal import ROUND_DOWN, Context, Decimal, localcontext
from pathlib import Path
from types import SimpleNamespace
from typing import Any

import pytest
from fastapi.testclient import TestClient
from pydantic import ValidationError

from backend.api.dependencies import get_order_service
from backend.api.routes import orders as order_routes
from backend.api.schemas import Money, ShippingQuoteResponse, TrackingResponse
from backend.integrations.tracking import HttpxTrackingTransport
from backend.main import app
from backend.models import (
    CarrierProvider,
    NormalizedTrackingStatus,
    ResultStatus,
    TrackingEvent,
    TrackingResult,
)
from backend.repositories import RepositoryCollection, RepositoryError
from backend.services import OrderService


@pytest.fixture
def order_service(
    write_data_directory: object,
    orders_payload: dict[str, object],
    products_payload: dict[str, object],
    tracking_payload: dict[str, object],
) -> OrderService:
    data_directory = write_data_directory(orders_payload, products_payload, tracking_payload)
    return OrderService(RepositoryCollection(data_directory))


@pytest.fixture
def api_client(order_service: OrderService) -> TestClient:
    app.dependency_overrides[get_order_service] = lambda: order_service
    client = TestClient(app, raise_server_exceptions=False)
    yield client
    client.close()
    app.dependency_overrides.clear()


def _client_for_service(service: object) -> TestClient:
    app.dependency_overrides[get_order_service] = lambda: service
    return TestClient(app, raise_server_exceptions=False)


def _assert_money(value: dict[str, object]) -> None:
    assert set(value) == {"amount", "currency"}
    assert isinstance(value["amount"], str)
    assert re.fullmatch(r"\d+\.\d{2}", value["amount"])
    assert value["currency"] == "AUD"


def test_order_list_returns_success_envelope_and_summary(api_client: TestClient) -> None:
    response = api_client.get("/api/v1/orders")

    assert response.status_code == 200
    payload = response.json()
    assert set(payload) == {"data"}
    assert len(payload["data"]) == 1
    summary = payload["data"][0]
    assert summary == {
        "order_number": "TEST-ORDER-001",
        "order_date": "2026-01-02",
        "company": "Synthetic Company",
        "status": "IN_TRANSIT",
        "item_count": 2,
        "unit_count": 3,
        "order_total": {"amount": "89.97", "currency": "AUD"},
        "quote_request_state": "not_requested",
        "shipping_quote_status": None,
        "shipping_quote_reason_code": None,
    }


def test_order_list_returns_multiple_independently_priced_orders(
    write_data_directory: object,
    orders_payload: dict[str, object],
    products_payload: dict[str, object],
    tracking_payload: dict[str, object],
) -> None:
    second = copy.deepcopy(orders_payload["orders"][0])
    second["order_no"] = "TEST-ORDER-002"
    second["items"] = [{"sku": "TEST-SKU-2", "quantity": 1, "tracking_group_id": "GROUP-2"}]
    orders_payload["orders"].append(second)
    data_directory = write_data_directory(orders_payload, products_payload, tracking_payload)
    client = _client_for_service(OrderService(RepositoryCollection(data_directory)))

    response = client.get("/api/v1/orders")
    client.close()
    app.dependency_overrides.clear()

    assert response.status_code == 200
    data = response.json()["data"]
    assert [order["order_number"] for order in data] == ["TEST-ORDER-001", "TEST-ORDER-002"]
    assert [order["order_total"]["amount"] for order in data] == ["89.97", "29.99"]


def test_order_list_supports_empty_service_result() -> None:
    service = SimpleNamespace(list_orders=lambda: ())
    client = _client_for_service(service)

    response = client.get("/api/v1/orders")
    client.close()
    app.dependency_overrides.clear()

    assert response.status_code == 200
    assert response.json() == {"data": []}


def test_order_list_money_is_decimal_string(api_client: TestClient) -> None:
    summary = api_client.get("/api/v1/orders").json()["data"][0]

    _assert_money(summary["order_total"])


def test_order_detail_returns_complete_supported_business_data(api_client: TestClient) -> None:
    response = api_client.get("/api/v1/orders/TEST-ORDER-001")

    assert response.status_code == 200
    data = response.json()["data"]
    assert data["order_number"] == "TEST-ORDER-001"
    assert data["order_date"] == "2026-01-02"
    assert data["company"] == "Synthetic Company"
    assert data["customer"] == {
        "name": "Test Customer",
        "phone": "0000000000",
        "email": "customer@example.invalid",
    }
    assert data["shipping_address"] == {
        "line1": "1 Example Street",
        "suburb": "Exampleville",
        "state": "NSW",
        "postcode": "2000",
        "country": "Australia",
    }
    assert data["currency"] == "AUD"
    assert data["quote_request_state"] == "requested"
    # D-031: this order has two unique tracking groups and no approved mapping,
    # so detail exposes one provider-null unavailable result per group instead of
    # an empty array or a guessed carrier.
    assert [
        (row["tracking_group_id"], row["provider"], row["status"], row["reason_code"])
        for row in data["tracking_results"]
    ] == [
        ("GROUP-1", None, "unavailable", "CARRIER_MAPPING_UNRESOLVED"),
        ("GROUP-2", None, "unavailable", "CARRIER_MAPPING_UNRESOLVED"),
    ]
    assert len(data["items"]) == 2


def test_order_detail_projects_raw_normalized_unknown_and_empty_tracking_results(
    order_service: OrderService,
) -> None:
    base = order_service.get_order("TEST-ORDER-001")
    event_time = datetime(2026, 11, 8, 0, 30, tzinfo=UTC)
    checked_at = datetime(2026, 11, 8, 1, 2, tzinfo=UTC)
    tracking = (
        TrackingResult(
            tracking_group_id="GROUP-1",
            provider=CarrierProvider.AUSTRALIA_POST,
            status=ResultStatus.AVAILABLE,
            reason_code=None,
            checked_at=checked_at,
            provider_status="New provider status",
            current_status=NormalizedTrackingStatus.UNKNOWN,
            latest_event_at=event_time,
            events=(
                TrackingEvent(
                    event_time=event_time,
                    location=None,
                    description="Synthetic carrier event",
                    provider_status=None,
                    normalized_status=NormalizedTrackingStatus.UNKNOWN,
                ),
            ),
        ),
        TrackingResult(
            tracking_group_id="GROUP-2",
            provider=CarrierProvider.STARTRACK,
            status=ResultStatus.AVAILABLE,
            reason_code=None,
            checked_at=checked_at,
            provider_status=None,
            current_status=None,
            latest_event_at=None,
            events=(),
        ),
    )
    detail = base.model_copy(update={"tracking_results": tracking})
    service = SimpleNamespace(
        list_orders=order_service.list_orders,
        get_order=lambda _order_number: detail,
    )
    client = _client_for_service(service)

    response = client.get("/api/v1/orders/TEST-ORDER-001")
    client.close()
    app.dependency_overrides.clear()

    assert response.status_code == 200
    results = response.json()["data"]["tracking_results"]
    assert results[0]["provider_status"] == "New provider status"
    assert results[0]["current_status"] == "unknown"
    assert results[0]["events"][0]["normalized_status"] == "unknown"
    assert results[0]["events"][0]["location"] is None
    assert results[1]["status"] == "available"
    assert results[1]["events"] == []


def test_order_detail_preserves_multi_sku_quantity_and_tracking_group_associations(
    api_client: TestClient,
) -> None:
    items = api_client.get("/api/v1/orders/TEST-ORDER-001").json()["data"]["items"]

    assert [(item["sku"], item["quantity"], item["tracking_group_id"]) for item in items] == [
        ("TEST-SKU-1", 2, "GROUP-1"),
        ("TEST-SKU-2", 1, "GROUP-2"),
    ]
    assert [item["product"]["sku"] for item in items] == ["TEST-SKU-1", "TEST-SKU-2"]
    assert items[1]["product"]["description"] is None
    assert items[1]["product"]["eta_days"] is None


def test_order_detail_uses_service_pricing_without_api_recalculation(
    api_client: TestClient,
) -> None:
    data = api_client.get("/api/v1/orders/TEST-ORDER-001").json()["data"]

    assert [item["line_subtotal"]["amount"] for item in data["items"]] == ["54.53", "27.26"]
    assert data["pricing"] == {
        "order_subtotal": {"amount": "81.79", "currency": "AUD"},
        "gst_amount": {"amount": "8.18", "currency": "AUD"},
        "order_total": {"amount": "89.97", "currency": "AUD"},
    }


def test_order_detail_exposes_unsupported_shipping_quote_not_free_shipping(
    api_client: TestClient,
) -> None:
    data = api_client.get("/api/v1/orders/TEST-ORDER-001").json()["data"]
    quote = data["shipping_quote"]

    assert quote["status"] == "unsupported"
    assert quote["reason_code"] == "SHIPPING_QUOTE_NOT_IMPLEMENTED"
    assert quote["quoted_fee"] is None
    assert quote["applied_fee"] == {"amount": "0.00", "currency": "AUD"}
    checked_at = datetime.fromisoformat(quote["checked_at"].replace("Z", "+00:00"))
    assert checked_at.tzinfo is not None
    assert checked_at.utcoffset() == UTC.utcoffset(checked_at)
    assert "free" not in json.dumps(quote).lower()


def test_applied_shipping_fee_is_the_single_api_fee_source_used_by_order_total(
    api_client: TestClient,
) -> None:
    data = api_client.get("/api/v1/orders/TEST-ORDER-001").json()["data"]

    assert "shipment_fee" not in data["pricing"]
    subtotal = Decimal(data["pricing"]["order_subtotal"]["amount"])
    gst = Decimal(data["pricing"]["gst_amount"]["amount"])
    applied_fee = Decimal(data["shipping_quote"]["applied_fee"]["amount"])
    total = Decimal(data["pricing"]["order_total"]["amount"])
    assert total == subtotal + gst + applied_fee


def test_every_order_detail_money_value_is_a_two_decimal_string(api_client: TestClient) -> None:
    data = api_client.get("/api/v1/orders/TEST-ORDER-001").json()["data"]

    for item in data["items"]:
        _assert_money(item["unit_price_incl_gst"])
        _assert_money(item["unit_price_ex_gst"])
        _assert_money(item["line_subtotal"])
    for money in data["pricing"].values():
        _assert_money(money)
    assert data["shipping_quote"]["quoted_fee"] is None
    _assert_money(data["shipping_quote"]["applied_fee"])


def test_shipping_quote_does_not_change_or_fabricate_tracking_result(
    api_client: TestClient,
) -> None:
    data = api_client.get("/api/v1/orders/TEST-ORDER-001").json()["data"]

    assert data["shipping_quote"]["status"] == "unsupported"
    assert [item["tracking_group_id"] for item in data["items"]] == ["GROUP-1", "GROUP-2"]
    assert "tracking" not in data


def test_missing_order_returns_stable_404_error(api_client: TestClient) -> None:
    response = api_client.get("/api/v1/orders/NO-SUCH-ORDER")

    assert response.status_code == 404
    assert response.json() == {"error": {"code": "ORDER_NOT_FOUND", "message": "Order not found."}}


def test_invalid_order_number_returns_stable_422_error(api_client: TestClient) -> None:
    response = api_client.get("/api/v1/orders/invalid%20order")

    assert response.status_code == 422
    assert response.json() == {
        "error": {
            "code": "REQUEST_VALIDATION_ERROR",
            "message": "Request validation failed.",
        }
    }


class _RaisingService:
    def __init__(self, exception: Exception) -> None:
        self._exception = exception

    def list_orders(self) -> tuple[()]:
        raise self._exception

    def get_order(self, order_number: str) -> Any:
        raise self._exception


def test_repository_failure_returns_safe_data_source_error() -> None:
    marker = "private-path-marker.json"
    client = _client_for_service(_RaisingService(RepositoryError(marker)))

    response = client.get("/api/v1/orders")
    client.close()
    app.dependency_overrides.clear()

    assert response.status_code == 500
    assert response.json() == {
        "error": {"code": "DATA_SOURCE_ERROR", "message": "Order data is unavailable."}
    }
    assert marker not in response.text


def test_unknown_failure_returns_safe_internal_error_without_sensitive_marker() -> None:
    marker = "private-customer-marker@example.invalid"
    client = _client_for_service(_RaisingService(RuntimeError(marker)))

    response = client.get("/api/v1/orders/TEST-ORDER-001")
    client.close()
    app.dependency_overrides.clear()

    assert response.status_code == 500
    assert response.json() == {
        "error": {
            "code": "INTERNAL_SERVER_ERROR",
            "message": "An unexpected server error occurred.",
        }
    }
    assert marker not in response.text
    assert "traceback" not in response.text.lower()


@pytest.mark.parametrize(
    ("amount", "expected"),
    [
        (Decimal("123.45"), "123.45"),
        (Decimal("0"), "0.00"),
        (Decimal("0.000"), "0.00"),
        (Decimal("-0"), "0.00"),
        (Decimal("-0.000"), "0.00"),
        (Decimal("0E+10"), "0.00"),
        (Decimal("1.005"), "1.01"),
        (Decimal("999999999999999999999999.995"), "1000000000000000000000000.00"),
    ],
)
def test_money_explicitly_serializes_decimal_to_two_place_string(
    amount: Decimal, expected: str
) -> None:
    assert Money(amount=amount).model_dump(mode="json") == {
        "amount": expected,
        "currency": "AUD",
    }


def test_money_serialization_preserves_decimal_precision_under_low_external_context() -> None:
    amount = Decimal("123456789012345678901234567890.995")

    with localcontext(Context(prec=4, rounding=ROUND_DOWN)):
        serialized = Money(amount=amount).model_dump(mode="json")

    assert serialized["amount"] == "123456789012345678901234567891.00"


def test_money_rejects_float_input() -> None:
    with pytest.raises(ValidationError):
        Money(amount=1.25)


@pytest.mark.parametrize(
    "invalid_amount",
    [Decimal("-0.01"), Decimal("NaN"), Decimal("Infinity"), Decimal("-Infinity")],
)
def test_money_rejects_negative_nonzero_and_non_finite_decimals(
    invalid_amount: Decimal,
) -> None:
    with pytest.raises(ValidationError):
        Money(amount=invalid_amount)


def _shipping_quote_response(**overrides: object) -> ShippingQuoteResponse:
    values: dict[str, object] = {
        "status": "unsupported",
        "reason_code": "SHIPPING_QUOTE_NOT_IMPLEMENTED",
        "checked_at": datetime(2026, 11, 6, 12, 0, tzinfo=UTC),
        "quoted_fee": None,
        "applied_fee": Money(amount=Decimal("0.00")),
    }
    values.update(overrides)
    return ShippingQuoteResponse.model_validate(values)


def test_shipping_quote_response_rejects_nonzero_applied_fee() -> None:
    with pytest.raises(ValidationError, match="applied fee must be zero"):
        _shipping_quote_response(applied_fee=Money(amount=Decimal("12.34")))


def test_shipping_quote_response_rejects_non_null_quoted_fee() -> None:
    with pytest.raises(ValidationError, match="quoted fee must be null"):
        _shipping_quote_response(quoted_fee=Money(amount=Decimal("1.00")))


@pytest.mark.parametrize(
    "invalid_time",
    [
        datetime(2026, 11, 6, 12, 0),
        datetime(2026, 11, 6, 12, 0, tzinfo=timezone(timedelta(hours=10))),
    ],
)
def test_shipping_quote_response_rejects_non_utc_checked_at(
    invalid_time: datetime,
) -> None:
    with pytest.raises(ValidationError, match="checked_at must use UTC|timezone_aware"):
        _shipping_quote_response(checked_at=invalid_time)


def test_shipping_quote_response_accepts_utc_null_quote_and_serializes_zero_fee() -> None:
    quote = _shipping_quote_response(applied_fee=Money(amount=Decimal("-0.000")))

    assert quote.model_dump(mode="json") == {
        "status": "unsupported",
        "reason_code": "SHIPPING_QUOTE_NOT_IMPLEMENTED",
        "checked_at": "2026-11-06T12:00:00Z",
        "quoted_fee": None,
        "applied_fee": {"amount": "0.00", "currency": "AUD"},
    }


def _tracking_response(**overrides: object) -> TrackingResponse:
    values: dict[str, object] = {
        "tracking_group_id": "GROUP-1",
        "provider": None,
        "status": "unavailable",
        "reason_code": "CARRIER_MAPPING_UNRESOLVED",
        "checked_at": datetime(2026, 11, 8, 1, 2, tzinfo=UTC),
        "provider_status": None,
        "current_status": None,
        "latest_event_at": None,
        "events": (),
    }
    values.update(overrides)
    return TrackingResponse.model_validate(values)


def test_tracking_response_accepts_d031_provider_null_mapping_unresolved() -> None:
    response = _tracking_response()

    assert response.provider is None
    assert response.status == "unavailable"
    assert response.reason_code == "CARRIER_MAPPING_UNRESOLVED"
    assert response.model_dump(mode="json")["provider"] is None


@pytest.mark.parametrize(
    ("status", "reason"),
    [
        ("available", None),
        ("unsupported", "CARRIER_NOT_IMPLEMENTED"),
        ("unavailable", "PROVIDER_TIMEOUT"),
        ("unavailable", "PROVIDER_ERROR"),
        ("unavailable", "PROVIDER_CONFIGURATION_MISSING"),
        ("unavailable", None),
    ],
)
def test_tracking_response_rejects_illegal_provider_null_combinations(
    status: str,
    reason: str | None,
) -> None:
    with pytest.raises(ValidationError, match="provider"):
        _tracking_response(status=status, reason_code=reason)


def test_tracking_response_rejects_mapping_unresolved_with_a_named_provider() -> None:
    with pytest.raises(ValidationError, match="CARRIER_MAPPING_UNRESOLVED"):
        _tracking_response(provider="australia_post")


def test_tracking_response_keeps_strict_validation_for_named_provider_failures() -> None:
    with pytest.raises(ValidationError, match="tracking facts"):
        _tracking_response(
            provider="australia_post",
            status="unavailable",
            reason_code="PROVIDER_TIMEOUT",
            events=(
                {
                    "event_time": datetime(2026, 11, 8, 0, 30, tzinfo=UTC),
                    "location": None,
                    "description": "Synthetic event",
                    "provider_status": None,
                    "normalized_status": "unknown",
                },
            ),
        )


def test_openapi_documents_v1_paths_money_and_stable_errors() -> None:
    schema = app.openapi()

    assert schema["info"]["title"] == "Order Management System"
    assert schema["info"]["version"] == "1.0.0"
    assert set(schema["paths"]) == {
        "/health",
        "/api/v1/orders",
        "/api/v1/orders/{order_number}",
    }
    money = schema["components"]["schemas"]["Money"]["properties"]["amount"]
    assert money["type"] == "string"
    assert money["pattern"] == r"^\d+\.\d{2}$"
    detail_responses = schema["paths"]["/api/v1/orders/{order_number}"]["get"]["responses"]
    assert {"200", "404", "422", "500"} <= set(detail_responses)
    for status in ("404", "422", "500"):
        response_schema = detail_responses[status]["content"]["application/json"]["schema"]
        assert response_schema == {"$ref": "#/components/schemas/ErrorResponse"}
    shipping_quote = schema["components"]["schemas"]["ShippingQuoteResponse"]
    assert shipping_quote["properties"]["status"]["const"] == "unsupported"
    assert shipping_quote["properties"]["reason_code"]["const"] == "SHIPPING_QUOTE_NOT_IMPLEMENTED"
    assert shipping_quote["properties"]["checked_at"]["format"] == "date-time"
    assert shipping_quote["properties"]["applied_fee"] == {"$ref": "#/components/schemas/Money"}
    summary = schema["components"]["schemas"]["OrderSummaryResponse"]
    assert summary["properties"]["quote_request_state"]["const"] == "not_requested"
    assert summary["properties"]["shipping_quote_status"]["type"] == "null"
    assert summary["properties"]["shipping_quote_reason_code"]["type"] == "null"
    assert {
        "quote_request_state",
        "shipping_quote_status",
        "shipping_quote_reason_code",
    } <= set(summary["required"])
    tracking = schema["components"]["schemas"]["TrackingResponse"]
    assert tracking["properties"]["status"]["enum"] == [
        "available",
        "unavailable",
        "unsupported",
    ]
    assert tracking["properties"]["checked_at"]["format"] == "date-time"
    assert "unknown" in tracking["properties"]["current_status"]["anyOf"][0]["enum"]
    assert tracking["properties"]["events"]["items"] == {
        "$ref": "#/components/schemas/TrackingEventResponse"
    }
    provider = tracking["properties"]["provider"]
    assert {"type": "null"} in provider["anyOf"]
    assert any(
        option.get("enum") == ["australia_post", "startrack", "tnt"] for option in provider["anyOf"]
    )
    assert "provider" in tracking["required"]
    assert {
        "tracking_group_id",
        "status",
        "reason_code",
        "checked_at",
        "provider_status",
        "current_status",
        "latest_event_at",
        "events",
    } <= set(tracking["required"])
    assert "D-031" in provider["description"]
    assert "CARRIER_MAPPING_UNRESOLVED" in provider["description"]
    assert "D-031" in tracking["description"]
    assert tracking["examples"][0]["provider"] is None
    assert tracking["examples"][0]["reason_code"] == "CARRIER_MAPPING_UNRESOLVED"
    assert tracking["examples"][0]["status"] == "unavailable"
    assert tracking["examples"][0]["events"] == []
    assert "carrier query succeeded" in tracking["properties"]["status"]["description"]
    assert "adapter is not implemented" in tracking["properties"]["status"]["description"]


def test_openapi_examples_do_not_contain_runtime_customer_or_tracking_data() -> None:
    rendered = json.dumps(app.openapi())

    assert "customer@example.invalid" not in rendered
    assert "TRACK-TEST" not in rendered


def test_router_has_no_repository_file_or_pricing_implementation() -> None:
    source = inspect.getsource(order_routes)

    for forbidden in (
        "RepositoryCollection",
        "backend.data",
        "open(",
        "read_text",
        "json.load",
        "Decimal(",
        "quantize",
        "ROUND_HALF_UP",
    ):
        assert forbidden not in source


def test_api_mapper_never_uses_float_or_recalculates_money() -> None:
    mapper_path = Path(__file__).resolve().parents[1] / "api" / "mappers.py"
    source = mapper_path.read_text(encoding="utf-8")

    assert "float(" not in source
    assert "quantize" not in source
    assert "ROUND_" not in source


def test_real_application_lifespan_reuses_one_service_and_serves_both_endpoints() -> None:
    app.dependency_overrides.clear()
    with TestClient(app, raise_server_exceptions=False) as client:
        service = app.state.order_service
        list_response = client.get("/api/v1/orders")
        first_order_number = list_response.json()["data"][0]["order_number"]
        detail_response = client.get(f"/api/v1/orders/{first_order_number}")

        assert app.state.order_service is service

    assert list_response.status_code == 200
    assert len(list_response.json()["data"]) == 2
    assert detail_response.status_code == 200
    detail = detail_response.json()["data"]
    expected_groups = tuple(dict.fromkeys(item["tracking_group_id"] for item in detail["items"]))
    assert expected_groups != ()
    assert [row["tracking_group_id"] for row in detail["tracking_results"]] == list(expected_groups)
    for row in detail["tracking_results"]:
        assert row["provider"] is None
        assert row["status"] == "unavailable"
        assert row["reason_code"] == "CARRIER_MAPPING_UNRESOLVED"
        assert row["events"] == []


def test_default_application_detail_cannot_make_a_provider_network_call(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def forbidden(self: object, request: object) -> None:
        raise AssertionError("the default application must not call a provider")

    monkeypatch.setattr(HttpxTrackingTransport, "get", forbidden)
    app.dependency_overrides.clear()
    with TestClient(app, raise_server_exceptions=False) as client:
        list_response = client.get("/api/v1/orders")
        order_number = list_response.json()["data"][0]["order_number"]
        detail_response = client.get(f"/api/v1/orders/{order_number}")

    assert detail_response.status_code == 200
    assert detail_response.json()["data"]["quote_request_state"] == "requested"
    assert detail_response.json()["data"]["tracking_results"]


def test_order_endpoint_keeps_existing_cors_boundary(api_client: TestClient) -> None:
    origin = "http://localhost:5173"

    response = api_client.get("/api/v1/orders", headers={"Origin": origin})

    assert response.status_code == 200
    assert response.headers["access-control-allow-origin"] == origin
