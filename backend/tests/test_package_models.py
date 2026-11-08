"""Domain contract tests for Batch J1 package models."""

from datetime import UTC, datetime
from decimal import Decimal

import pytest
from pydantic import ValidationError

from backend.models import (
    Package,
    PackageDiagnosticCategory,
    PackageDimensions,
    PackageEstimationDiagnostic,
    PackageEstimationResult,
    PackageEstimationStatus,
    PackageItem,
    PackageItemReference,
    PackageProvenance,
    PackageReasonCode,
    PackageSource,
    PackageWeight,
    make_input_fingerprint,
)
from backend.tests.packaging_fixtures import NOW, dimensions

CHECKED_AT = datetime(2026, 11, 8, 1, 2, tzinfo=UTC)


def dimensions_of(length: str, width: str, height: str) -> PackageDimensions:
    return dimensions(length, width, height)


def provenance(source: PackageSource = PackageSource.RULES) -> PackageProvenance:
    return PackageProvenance(
        source=source,
        source_revision="synthetic-source-revision-1",
        ruleset_id="synthetic-ruleset-j1",
        ruleset_version="synthetic-v1",
        input_fingerprint=make_input_fingerprint(
            "SYNTH-ORDER-001", ((0, "SYNTH-SKU-ALPHA", 2),), "synthetic-ruleset-j1", "synthetic-v1"
        ),
        generated_at=CHECKED_AT,
    )


def package(**overrides: object) -> Package:
    values: dict[str, object] = {
        "package_id": "PKG-001",
        "order_number": "SYNTH-ORDER-001",
        "source": PackageSource.RULES,
        "items": (
            PackageItem(
                order_item_ref=PackageItemReference(order_number="SYNTH-ORDER-001", line_index=0),
                sku="SYNTH-SKU-ALPHA",
                quantity=2,
            ),
        ),
        "dimensions": dimensions_of("210", "160", "110"),
        "weight": PackageWeight(
            item_weight_g=Decimal("500"),
            packaging_weight_g=Decimal("50"),
            gross_weight_g=Decimal("550"),
        ),
        "material_id": "SYNTH-BOX-S",
        "ruleset_id": "synthetic-ruleset-j1",
        "ruleset_version": "synthetic-v1",
        "estimated_at": CHECKED_AT,
        "provenance": provenance(),
    }
    values.update(overrides)
    return Package(**values)


# ----------------------------------------------------------------- dimensions


def test_dimensions_volume_must_equal_the_exact_product() -> None:
    from backend.models import PackageDimensions as DimensionsModel

    with pytest.raises(ValidationError, match="volume_mm3"):
        DimensionsModel(
            length_mm=Decimal("10"),
            width_mm=Decimal("10"),
            height_mm=Decimal("10"),
            volume_mm3=Decimal("999"),
        )


@pytest.mark.parametrize("value", [Decimal("0"), Decimal("-1")])
def test_dimensions_reject_non_positive_sides(value: Decimal) -> None:
    from backend.models import PackageDimensions as DimensionsModel

    with pytest.raises(ValidationError):
        DimensionsModel(
            length_mm=value,
            width_mm=Decimal("10"),
            height_mm=Decimal("10"),
            volume_mm3=Decimal("100"),
        )


def test_dimensions_reject_float_inputs() -> None:
    from backend.models import PackageDimensions as DimensionsModel

    with pytest.raises(ValidationError):
        DimensionsModel.model_validate(
            {"length_mm": 10.0, "width_mm": 10.0, "height_mm": 10.0, "volume_mm3": 1000.0}
        )


# --------------------------------------------------------------------- weight


def test_weight_gross_must_equal_item_plus_packaging() -> None:
    with pytest.raises(ValidationError, match="gross_weight_g"):
        PackageWeight(
            item_weight_g=Decimal("500"),
            packaging_weight_g=Decimal("50"),
            gross_weight_g=Decimal("600"),
        )


def test_weight_keeps_provider_weights_null_without_evidence() -> None:
    weight = PackageWeight(
        item_weight_g=Decimal("500"),
        packaging_weight_g=Decimal("50"),
        gross_weight_g=Decimal("550"),
    )

    assert weight.volumetric_weight_kg is None
    assert weight.chargeable_weight_kg is None


# -------------------------------------------------------------------- package


def test_valid_rules_package_keeps_ruleset_and_provenance() -> None:
    result = package()

    assert result.source is PackageSource.RULES
    assert result.ruleset_id == "synthetic-ruleset-j1"
    assert result.provenance.ruleset_version == "synthetic-v1"
    assert result.estimated_at == CHECKED_AT


def test_package_rejects_items_from_another_order() -> None:
    with pytest.raises(ValidationError, match="another order"):
        package(
            items=(
                PackageItem(
                    order_item_ref=PackageItemReference(order_number="OTHER-ORDER", line_index=0),
                    sku="SYNTH-SKU-ALPHA",
                    quantity=1,
                ),
            )
        )


def test_package_rejects_allocating_the_same_order_line_twice() -> None:
    duplicate = PackageItem(
        order_item_ref=PackageItemReference(order_number="SYNTH-ORDER-001", line_index=0),
        sku="SYNTH-SKU-ALPHA",
        quantity=1,
    )

    with pytest.raises(ValidationError, match="twice"):
        package(items=(duplicate, duplicate))


def test_rules_package_requires_ruleset_identifier() -> None:
    with pytest.raises(ValidationError, match="ruleset_id"):
        package(ruleset_id=None, ruleset_version=None)


def test_rules_package_requires_estimation_time() -> None:
    with pytest.raises(ValidationError, match="estimated_at"):
        package(estimated_at=None)


def test_package_requires_matching_provenance_ruleset() -> None:
    mismatched = PackageProvenance(
        source=PackageSource.RULES,
        source_revision="synthetic-source-revision-1",
        ruleset_id="synthetic-ruleset-j1",
        ruleset_version="synthetic-v2",
        input_fingerprint=provenance().input_fingerprint,
        generated_at=CHECKED_AT,
    )

    with pytest.raises(ValidationError, match="provenance ruleset"):
        package(provenance=mismatched)


def test_package_provenance_source_must_match_package_source() -> None:
    with pytest.raises(ValidationError, match="provenance source"):
        package(provenance=provenance(source=PackageSource.ACTUAL))


def test_package_rejects_zero_quantity_items() -> None:
    with pytest.raises(ValidationError):
        PackageItem(
            order_item_ref=PackageItemReference(order_number="SYNTH-ORDER-001", line_index=0),
            sku="SYNTH-SKU-ALPHA",
            quantity=0,
        )


def test_package_requires_at_least_one_item() -> None:
    with pytest.raises(ValidationError):
        package(items=())


def test_package_provenance_requires_rules_identifier_for_rules_source() -> None:
    with pytest.raises(ValidationError, match="rules provenance"):
        PackageProvenance(
            source=PackageSource.RULES,
            source_revision="synthetic-source-revision-1",
            ruleset_id=None,
            ruleset_version=None,
            input_fingerprint=provenance().input_fingerprint,
            generated_at=CHECKED_AT,
        )


def test_provenance_fingerprint_must_be_lowercase_hex() -> None:
    with pytest.raises(ValidationError, match="lowercase hexadecimal"):
        PackageProvenance(
            source=PackageSource.RULES,
            source_revision="synthetic-source-revision-1",
            ruleset_id="synthetic-ruleset-j1",
            ruleset_version="synthetic-v1",
            input_fingerprint="Z" * 64,
            generated_at=CHECKED_AT,
        )


# ------------------------------------------------------- estimation result


def available_result(**overrides: object) -> PackageEstimationResult:
    values: dict[str, object] = {
        "status": PackageEstimationStatus.AVAILABLE,
        "reason_code": None,
        "checked_at": CHECKED_AT,
        "source": PackageSource.RULES,
        "ruleset_id": "synthetic-ruleset-j1",
        "ruleset_version": "synthetic-v1",
        "synthetic_ruleset": True,
        "packages": (package(),),
        "diagnostics": (),
    }
    values.update(overrides)
    return PackageEstimationResult(**values)


def test_available_estimation_requires_packages_and_no_reason() -> None:
    result = available_result()

    assert result.status is PackageEstimationStatus.AVAILABLE
    assert result.reason_code is None
    assert len(result.packages) == 1

    with pytest.raises(ValidationError, match="reason code"):
        available_result(reason_code=PackageReasonCode.PACKAGE_DATA_INCOMPLETE)
    with pytest.raises(ValidationError, match="at least one package"):
        available_result(packages=())
    with pytest.raises(ValidationError, match="requires a source"):
        available_result(source=None)


def test_unavailable_estimation_requires_reason_and_no_packages() -> None:
    result = PackageEstimationResult(
        status=PackageEstimationStatus.UNAVAILABLE,
        reason_code=PackageReasonCode.PACKAGE_RULES_NOT_CONFIGURED,
        checked_at=CHECKED_AT,
        source=None,
        synthetic_ruleset=False,
        packages=(),
        diagnostics=(
            PackageEstimationDiagnostic(
                category=PackageDiagnosticCategory.RULES_NOT_CONFIGURED,
                safe_detail="no active packaging ruleset is configured",
            ),
        ),
    )

    assert result.packages == ()
    assert result.reason_code is PackageReasonCode.PACKAGE_RULES_NOT_CONFIGURED

    with pytest.raises(ValidationError, match="requires a reason code"):
        PackageEstimationResult(
            status=PackageEstimationStatus.UNAVAILABLE,
            reason_code=None,
            checked_at=CHECKED_AT,
            source=None,
            synthetic_ruleset=False,
        )
    with pytest.raises(ValidationError, match="cannot include packages"):
        PackageEstimationResult(
            status=PackageEstimationStatus.UNAVAILABLE,
            reason_code=PackageReasonCode.PACKAGE_DATA_INCOMPLETE,
            checked_at=CHECKED_AT,
            source=None,
            synthetic_ruleset=False,
            packages=(package(),),
        )
    with pytest.raises(ValidationError, match="cannot claim a source"):
        PackageEstimationResult(
            status=PackageEstimationStatus.UNAVAILABLE,
            reason_code=PackageReasonCode.PACKAGE_DATA_INCOMPLETE,
            checked_at=CHECKED_AT,
            source=PackageSource.RULES,
            synthetic_ruleset=False,
        )


def test_estimation_requires_unique_package_ids() -> None:
    with pytest.raises(ValidationError, match="unique"):
        available_result(packages=(package(), package()))


def test_estimation_rejects_non_utc_checked_at() -> None:
    from datetime import timedelta, timezone

    with pytest.raises(ValidationError, match="UTC"):
        available_result(
            checked_at=datetime(2026, 11, 8, 11, 2, tzinfo=timezone(timedelta(hours=10)))
        )


# ------------------------------------------------------------------ fingerprint


def test_input_fingerprint_is_deterministic_and_input_sensitive() -> None:
    first = make_input_fingerprint(
        "SYNTH-ORDER-001", ((0, "SYNTH-SKU-ALPHA", 2),), "synthetic-ruleset-j1", "synthetic-v1"
    )
    same = make_input_fingerprint(
        "SYNTH-ORDER-001", ((0, "SYNTH-SKU-ALPHA", 2),), "synthetic-ruleset-j1", "synthetic-v1"
    )
    other_quantity = make_input_fingerprint(
        "SYNTH-ORDER-001", ((0, "SYNTH-SKU-ALPHA", 3),), "synthetic-ruleset-j1", "synthetic-v1"
    )
    other_ruleset = make_input_fingerprint(
        "SYNTH-ORDER-001", ((0, "SYNTH-SKU-ALPHA", 2),), "synthetic-ruleset-j1", "synthetic-v2"
    )

    assert first == same
    assert first != other_quantity
    assert first != other_ruleset
    assert len(first) == 64
    assert all(character in "0123456789abcdef" for character in first)


def test_diagnostics_do_not_expose_detail_in_repr() -> None:
    marker = "SYNTHETIC-SENSITIVE-MARKER"
    diagnostic = PackageEstimationDiagnostic(
        category=PackageDiagnosticCategory.INTERNAL_ERROR,
        safe_detail=marker,
    )

    assert marker not in repr(diagnostic)


def test_fixture_ruleset_timestamp_is_utc() -> None:
    assert NOW.utcoffset() is not None


def test_estimation_requires_an_explicit_synthetic_flag() -> None:
    # A result must state its ruleset provenance; omitting the flag may not
    # silently read as production data.
    with pytest.raises(ValidationError, match="synthetic_ruleset"):
        PackageEstimationResult.model_validate(
            {
                "status": "available",
                "reason_code": None,
                "checked_at": CHECKED_AT,
                "source": "rules",
                "ruleset_id": "synthetic-ruleset-j1",
                "ruleset_version": "synthetic-v1",
                "packages": [package().model_dump()],
            }
        )
