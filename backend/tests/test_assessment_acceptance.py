"""Assessment acceptance checks against the real two-order baseline.

These tests verify the coding-assessment requirements end to end: both orders are
loaded from the approved local JSON, priced independently with the frozen D-004
Decimal rules, and projected through the real application exactly as a browser
would receive them.

Every expected amount is recomputed here from the raw JSON with ``Decimal`` so the
test never trusts the implementation to mark its own homework.
"""

from __future__ import annotations

import hashlib
import json
import re
from decimal import ROUND_HALF_UP, Decimal
from pathlib import Path
from typing import Any

import pytest
from fastapi.testclient import TestClient

from backend.main import app

DATA_DIRECTORY = Path(__file__).resolve().parents[1] / "data"
DATA_FILES = ("orders.json", "skus.json", "skus_raw.json", "tracking.json")
MONEY_PATTERN = re.compile(r"^\d+\.\d{2}$")
CENT = Decimal("0.01")


def _hashes() -> dict[str, str]:
    return {
        name: hashlib.sha256((DATA_DIRECTORY / name).read_bytes()).hexdigest()
        for name in DATA_FILES
    }


def _raw_baseline() -> tuple[list[dict[str, Any]], dict[str, dict[str, Any]]]:
    orders = json.loads((DATA_DIRECTORY / "orders.json").read_text(encoding="utf-8"))["orders"]
    products = json.loads((DATA_DIRECTORY / "skus.json").read_text(encoding="utf-8"))["products"]
    return orders, {product["sku"]: product for product in products}


def _expected_pricing(order: dict[str, Any], products: dict[str, dict[str, Any]]) -> dict[str, Any]:
    """Recompute D-004 amounts independently for one order."""

    subtotal = Decimal("0")
    lines = []
    for item in order["items"]:
        rrp = Decimal(products[item["sku"]]["rrp_aud_incl_gst"])
        quantity = item["quantity"]
        ex_gst = rrp / Decimal("1.10")
        line_subtotal = (ex_gst * quantity).quantize(CENT, ROUND_HALF_UP)
        subtotal += line_subtotal
        lines.append(
            {
                "sku": item["sku"],
                "quantity": quantity,
                "rrp": rrp,
                "ex_gst": ex_gst,
                "line_subtotal": line_subtotal,
            }
        )
    gst = (subtotal * Decimal("0.10")).quantize(CENT, ROUND_HALF_UP)
    total = (subtotal + gst).quantize(CENT, ROUND_HALF_UP)
    return {
        "lines": lines,
        "order_subtotal": subtotal,
        "gst_amount": gst,
        "order_total": total,
        "unit_count": sum(line["quantity"] for line in lines),
    }


def _amount(value: dict[str, Any]) -> Decimal:
    assert set(value) == {"amount", "currency"}, value
    assert value["currency"] == "AUD"
    assert isinstance(value["amount"], str)
    assert MONEY_PATTERN.match(value["amount"]), value["amount"]
    return Decimal(value["amount"])


@pytest.fixture
def client() -> TestClient:
    with TestClient(app, raise_server_exceptions=False) as test_client:
        yield test_client


def test_two_orders_load_and_price_independently(client: TestClient) -> None:
    before = _hashes()
    orders, products = _raw_baseline()

    response = client.get("/api/v1/orders")
    assert response.status_code == 200
    summaries = response.json()["data"]

    assert len(summaries) == 2
    assert len(orders) == 2
    assert {summary["order_number"] for summary in summaries} == {
        order["order_no"] for order in orders
    }

    # D-030: the list total is the item subtotal plus item GST, with no shipping quote.
    for summary, order in zip(
        sorted(summaries, key=lambda row: row["order_number"]),
        sorted(orders, key=lambda row: row["order_no"]),
        strict=True,
    ):
        expected = _expected_pricing(order, products)
        assert summary["order_number"] == order["order_no"]
        assert summary["item_count"] == len(order["items"])
        assert summary["unit_count"] == expected["unit_count"]
        assert summary["quote_request_state"] == "not_requested"
        assert summary["shipping_quote_status"] is None
        assert summary["shipping_quote_reason_code"] is None
        assert _amount(summary["order_total"]) == expected["order_total"]

    assert _hashes() == before


def test_detail_amounts_match_independent_decimal_recomputation(client: TestClient) -> None:
    before = _hashes()
    orders, products = _raw_baseline()

    # The two orders must not share or merge amount state.
    totals = set()
    for order in orders:
        response = client.get(f"/api/v1/orders/{order['order_no']}")
        assert response.status_code == 200
        detail = response.json()["data"]
        expected = _expected_pricing(order, products)

        assert detail["order_number"] == order["order_no"]
        assert detail["currency"] == "AUD"
        assert detail["quote_request_state"] == "requested"

        pricing = detail["pricing"]
        assert _amount(pricing["order_subtotal"]) == expected["order_subtotal"]
        assert _amount(pricing["gst_amount"]) == expected["gst_amount"]
        assert _amount(pricing["order_total"]) == expected["order_total"]
        totals.add(pricing["order_total"]["amount"])

        assert len(detail["items"]) == len(order["items"])
        for index, (item, line) in enumerate(zip(detail["items"], expected["lines"], strict=True)):
            assert item["sku"] == order["items"][index]["sku"]
            assert item["quantity"] == line["quantity"]
            # RRP is the GST-inclusive source price and must be shown unchanged.
            assert _amount(item["unit_price_incl_gst"]) == line["rrp"]
            # API Money is exactly two decimals; internal precision is not exposed.
            assert _amount(item["unit_price_ex_gst"]) == line["ex_gst"].quantize(
                CENT, ROUND_HALF_UP
            )
            # Line subtotal must be rounded from the unrounded ex-GST unit price.
            assert _amount(item["line_subtotal"]) == line["line_subtotal"]

        # Order total = subtotal + GST + applied fee, and applied fee is the
        # D-015 degraded zero because no quote capability exists.
        applied_fee = _amount(detail["shipping_quote"]["applied_fee"])
        assert applied_fee == Decimal("0.00")
        assert _amount(pricing["order_total"]) == (
            _amount(pricing["order_subtotal"]) + _amount(pricing["gst_amount"]) + applied_fee
        )

    assert len(totals) == 2
    assert _hashes() == before


def test_tracking_quote_and_package_sections_degrade_without_fabrication(
    client: TestClient,
) -> None:
    orders, _products = _raw_baseline()

    for order in orders:
        detail = client.get(f"/api/v1/orders/{order['order_no']}").json()["data"]

        # Shipping quote keeps the frozen D-015 unsupported semantics.
        quote = detail["shipping_quote"]
        assert quote["status"] == "unsupported"
        assert quote["reason_code"] == "SHIPPING_QUOTE_NOT_IMPLEMENTED"
        assert quote["quoted_fee"] is None
        assert _amount(quote["applied_fee"]) == Decimal("0.00")

        # Exactly one tracking result per unique tracking group. With no approved
        # mapping every result is D-031 provider-null unavailable and no carrier
        # data, event, ETA or provider request is fabricated.
        groups = tuple(dict.fromkeys(item["tracking_group_id"] for item in order["items"]))
        results = detail["tracking_results"]
        assert len(results) == len(groups)
        assert tuple(result["tracking_group_id"] for result in results) == groups
        for result in results:
            assert result["provider"] is None
            assert result["status"] == "unavailable"
            assert result["reason_code"] == "CARRIER_MAPPING_UNRESOLVED"
            assert result["events"] == []
            assert result["provider_status"] is None
            assert result["current_status"] is None

        # Packaging has no approved ruleset, so it fails closed with no package.
        estimation = detail["package_estimation"]
        assert estimation["status"] == "unavailable"
        assert estimation["reason_code"] == "PACKAGE_RULES_NOT_CONFIGURED"
        assert estimation["packages"] == []
        assert estimation["synthetic_ruleset"] is False
        assert estimation["source"] is None

        # The three capabilities stay independent: a failed tracking/quote/package
        # section must not remove order items, pricing or the customer block.
        assert detail["items"]
        assert detail["pricing"]["order_total"]
        assert detail["customer"]["name"]


def test_product_data_and_missing_values_are_preserved_not_invented(
    client: TestClient,
) -> None:
    orders, products = _raw_baseline()
    detail = client.get(f"/api/v1/orders/{orders[0]['order_no']}").json()["data"]

    for item in detail["items"]:
        product = item["product"]
        source = products[item["sku"]]
        assert product["sku"] == item["sku"]
        assert product["product_name"] == source["product_name"]
        # RRP is exposed once, as the GST-inclusive unit price of the line.
        assert _amount(item["unit_price_incl_gst"]) == Decimal(source["rrp_aud_incl_gst"])
        assert product["description_status"] == source["description_status"]
        assert product["description"] == source["description"]
        assert product["eta_raw"] == source["eta_raw"]
        assert product["eta_days"] == source["eta_days"]

    missing = [item for item in detail["items"] if item["product"]["description"] is None]
    for item in missing:
        assert item["product"]["description_status"] == "missing"

    zero_eta = [item for item in detail["items"] if item["product"]["eta_days"] == 0]
    for item in zero_eta:
        # Raw source value is preserved; no delivery promise is derived from it.
        assert item["product"]["eta_raw"] == "0Days"
