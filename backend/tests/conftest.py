"""Safe synthetic JSON fixtures for repository and model tests."""

import copy
import json
from collections.abc import Callable
from pathlib import Path

import pytest


@pytest.fixture
def orders_payload() -> dict[str, object]:
    return {
        "schema_version": "1.0.0",
        "currency": "AUD",
        "orders": [
            {
                "order_no": "TEST-ORDER-001",
                "order_date": "2026-01-02",
                "company": "Synthetic Company",
                "customer": {
                    "name": "Test Customer",
                    "phone": "0000000000",
                    "email": "customer@example.invalid",
                },
                "shipping_address": {
                    "line1": "1 Example Street",
                    "suburb": "Exampleville",
                    "state": "NSW",
                    "postcode": "2000",
                    "country": "Australia",
                },
                "status": "IN_TRANSIT",
                "items": [
                    {"sku": "TEST-SKU-1", "quantity": 2, "tracking_group_id": "GROUP-1"},
                    {"sku": "TEST-SKU-2", "quantity": 1, "tracking_group_id": "GROUP-2"},
                ],
            }
        ],
    }


def _product(
    sku: str,
    *,
    description: str | None = "Synthetic description",
    description_status: str = "available",
    eta_raw: str = "10Days",
    eta_days: int | None = 10,
    rrp: str = "29.9900",
) -> dict[str, object]:
    return {
        "sku": sku,
        "spu": "",
        "barcode": "0000000000000",
        "product_name": f"Synthetic {sku}",
        "description": description,
        "description_status": description_status,
        "product_type": "Synthetic Type",
        "size": "10 g",
        "status": "List",
        "schedule": "Synthetic Schedule",
        "dosage_type": "Synthetic Dosage",
        "plant_species": "Synthetic Species",
        "strain_lineage": "Synthetic Lineage",
        "spectrum": "Synthetic Spectrum",
        "route_of_administration": "Synthetic Route",
        "tga_category": "Synthetic Category",
        "eta_raw": eta_raw,
        "eta_days": eta_days,
        "rrp_aud_incl_gst": rrp,
        "weight_g": "10.500",
        "dimensions_mm": {"length": "20.1", "width": "10.2", "height": "5.3"},
        "volume_mm3": "1086.906",
        "volumetric_gross_weight_kg": "0.0002",
        "max_storage_per_container": "100",
        "warning_threshold": "5",
        "source_date": "2026-01-01 12:34:56",
    }


@pytest.fixture
def products_payload() -> dict[str, object]:
    products = [
        _product("TEST-SKU-1"),
        _product(
            "TEST-SKU-2",
            description=None,
            description_status="missing",
            eta_raw="nullDays",
            eta_days=None,
        ),
    ]
    return {
        "schema_version": "1.0.0",
        "currency": "AUD",
        "price_tax_treatment": "RRP includes GST",
        "record_count": len(products),
        "products": products,
    }


@pytest.fixture
def tracking_payload() -> dict[str, object]:
    return {
        "GROUP-1": {"carrier": "Synthetic Carrier", "tracking_number": "TRACK-TEST-1"},
        "GROUP-2": {"carrier": "Synthetic Carrier", "tracking_number": "TRACK-TEST-2"},
    }


@pytest.fixture
def write_data_directory(tmp_path: Path) -> Callable[..., Path]:
    def write(
        orders: dict[str, object],
        products: dict[str, object],
        tracking: dict[str, object],
    ) -> Path:
        data_directory = tmp_path / "data"
        data_directory.mkdir()
        payloads = {
            "orders.json": copy.deepcopy(orders),
            "skus.json": copy.deepcopy(products),
            "tracking.json": copy.deepcopy(tracking),
        }
        for name, payload in payloads.items():
            (data_directory / name).write_text(
                json.dumps(payload, ensure_ascii=False), encoding="utf-8"
            )
        return data_directory

    return write
