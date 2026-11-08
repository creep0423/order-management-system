"""Centralized, read-only UTF-8 JSON loading and Pydantic validation."""

import json
import re
from pathlib import Path
from typing import Any

from pydantic import BaseModel, ValidationError

from backend.repositories.exceptions import (
    DataSourceNotFoundError,
    DataSourceParseError,
    DataValidationError,
    DuplicateIdentifierError,
    ValidationDiagnostic,
)

_SAFE_LOCATION_FIELDS = frozenset(
    {
        "barcode",
        "carrier",
        "company",
        "country",
        "currency",
        "customer",
        "description",
        "description_status",
        "dimensions_mm",
        "dosage_type",
        "email",
        "eta_days",
        "eta_raw",
        "height",
        "items",
        "length",
        "line1",
        "max_storage_per_container",
        "name",
        "order_date",
        "order_no",
        "orders",
        "phone",
        "plant_species",
        "postcode",
        "price_tax_treatment",
        "product_name",
        "product_type",
        "products",
        "quantity",
        "record_count",
        "root",
        "route_of_administration",
        "rrp_aud_incl_gst",
        "schedule",
        "schema_version",
        "shipping_address",
        "size",
        "sku",
        "source_date",
        "spectrum",
        "spu",
        "state",
        "status",
        "strain_lineage",
        "suburb",
        "tga_category",
        "tracking_group_id",
        "tracking_number",
        "volume_mm3",
        "volumetric_gross_weight_kg",
        "warning_threshold",
        "weight_g",
        "width",
    }
)


def _safe_location_part(part: object) -> str | int:
    if isinstance(part, int) and not isinstance(part, bool) and part >= 0:
        return part
    if isinstance(part, str) and part in _SAFE_LOCATION_FIELDS:
        return part
    return "<key>"


def _format_location(parts: tuple[str | int, ...]) -> str:
    if not parts:
        return "$"
    rendered = ""
    for part in parts:
        if isinstance(part, int):
            rendered += f"[{part}]"
        elif not rendered:
            rendered = part
        else:
            rendered += f".{part}"
    return rendered


def _safe_error_type(value: object) -> str:
    if isinstance(value, str) and re.fullmatch(r"[a-z0-9_.]+", value):
        return value
    return "validation_error"


def _validation_diagnostics(errors: list[dict[str, Any]]) -> tuple[ValidationDiagnostic, ...]:
    diagnostics: list[ValidationDiagnostic] = []
    for error in errors:
        raw_location = error.get("loc")
        location = (
            tuple(_safe_location_part(part) for part in raw_location)
            if isinstance(raw_location, tuple | list)
            else ()
        )
        last_index = max(
            (index for index, part in enumerate(location) if isinstance(part, int)),
            default=-1,
        )
        if last_index >= 0:
            record_parts = location[: last_index + 1]
            field_parts = location[last_index + 1 :]
        else:
            record_parts = ()
            field_parts = location
        diagnostics.append(
            ValidationDiagnostic(
                record_path=_format_location(record_parts),
                field_path=_format_location(field_parts),
                error_type=_safe_error_type(error.get("type")),
            )
        )
    return tuple(diagnostics)


def _reject_duplicate_json_keys(pairs: list[tuple[str, object]]) -> dict[str, object]:
    result: dict[str, object] = {}
    for key, value in pairs:
        if key in result:
            raise DuplicateIdentifierError("JSON object key")
        result[key] = value
    return result


def load_json_model[SourceModelT: BaseModel](
    path: Path, model_type: type[SourceModelT]
) -> SourceModelT:
    """Read one JSON file exactly once and validate it without exposing its contents."""

    try:
        text = path.read_text(encoding="utf-8")
    except FileNotFoundError:
        raise DataSourceNotFoundError(path) from None
    except (OSError, UnicodeDecodeError):
        raise DataSourceParseError(path) from None

    try:
        payload = json.loads(text, object_pairs_hook=_reject_duplicate_json_keys)
    except DuplicateIdentifierError:
        raise
    except (json.JSONDecodeError, TypeError, ValueError):
        raise DataSourceParseError(path) from None

    try:
        return model_type.model_validate(payload)
    except ValidationError as exc:
        diagnostics = _validation_diagnostics(
            exc.errors(include_url=False, include_context=False, include_input=False)
        )
    raise DataValidationError(path, diagnostics) from None
