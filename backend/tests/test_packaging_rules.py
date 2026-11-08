"""Read-only, versioned packaging rules and reader tests (D-019, D-020, D-021)."""

from datetime import UTC, datetime, timedelta, timezone
from decimal import Decimal

import pytest
from pydantic import ValidationError

from backend.models import (
    PackageMaterialSpec,
    PackagingRuleSet,
    PackingPolicy,
    SkuPackagingSpec,
)
from backend.services import (
    PackagingRulesConfigurationError,
    StaticPackagingRuleSetReader,
)
from backend.tests.packaging_fixtures import (
    NOW,
    alpha_spec,
    beta_spec,
    dimensions,
    large_box,
    small_box,
    synthetic_ruleset,
)


def ruleset(**overrides: object) -> PackagingRuleSet:
    values: dict[str, object] = {
        "ruleset_id": "synthetic-ruleset-j1",
        "version": "synthetic-v1",
        "effective_from": NOW,
        "effective_to": None,
        "source_revision": "synthetic-source-revision-1",
        "synthetic_only": True,
        "sku_specs": (alpha_spec(), beta_spec()),
        "materials": (small_box(), large_box()),
        "policies": (PackingPolicy(policy_id="SYNTH-POLICY-1", priority=0),),
    }
    values.update(overrides)
    return PackagingRuleSet(**values)


# ------------------------------------------------------------------ identity


def test_ruleset_identity_and_version_are_required_and_reported() -> None:
    built = ruleset()

    assert built.ruleset_id == "synthetic-ruleset-j1"
    assert built.version == "synthetic-v1"
    assert built.source_revision == "synthetic-source-revision-1"
    assert built.synthetic_only is True


def test_ruleset_rejects_a_blank_identifier() -> None:
    with pytest.raises(ValidationError):
        ruleset(ruleset_id="")


def test_ruleset_rejects_non_synthetic_publication() -> None:
    # J1 has no approved production packing algorithm (DEC-3) or policy schema
    # (DEC-1), so a production ruleset cannot be constructed at all. This is what
    # prevents synthetic rules from ever being mixed into production behaviour.
    with pytest.raises(ValidationError):
        ruleset(synthetic_only=False)


def test_packing_policy_is_synthetic_only_by_contract() -> None:
    with pytest.raises(ValidationError):
        PackingPolicy.model_validate(
            {"policy_id": "POLICY-1", "priority": 0, "synthetic_only": False}
        )


# ----------------------------------------------------------- integrity checks


def test_ruleset_rejects_duplicate_sku_specs() -> None:
    with pytest.raises(ValidationError, match="one SKU twice"):
        ruleset(sku_specs=(alpha_spec(), alpha_spec()))


def test_ruleset_rejects_duplicate_materials() -> None:
    with pytest.raises(ValidationError, match="one material twice"):
        ruleset(materials=(small_box(), small_box()))


def test_ruleset_rejects_duplicate_policies() -> None:
    with pytest.raises(ValidationError, match="one policy twice"):
        ruleset(
            policies=(
                PackingPolicy(policy_id="SYNTH-POLICY-1", priority=0),
                PackingPolicy(policy_id="SYNTH-POLICY-1", priority=1),
            )
        )


def test_ruleset_rejects_unknown_material_reference() -> None:
    with pytest.raises(ValidationError, match="unknown material"):
        ruleset(
            sku_specs=(
                alpha_spec(materials=("SYNTH-BOX-MISSING",)),
                beta_spec(),
            )
        )


def test_ruleset_rejects_inverted_effective_window() -> None:
    with pytest.raises(ValidationError, match="effective_to"):
        ruleset(effective_to=NOW)


def test_ruleset_rejects_non_utc_effective_from() -> None:
    with pytest.raises(ValidationError, match="UTC"):
        ruleset(effective_from=datetime(2026, 11, 8, 11, 2, tzinfo=timezone(timedelta(hours=10))))


def test_material_requires_tare_below_max_gross_weight() -> None:
    with pytest.raises(ValidationError, match="tare weight"):
        PackageMaterialSpec(
            material_id="SYNTH-BOX-BAD",
            inner_dimensions_mm=dimensions("100", "100", "100"),
            outer_dimensions_mm=dimensions("110", "110", "110"),
            tare_weight_g=Decimal("1000"),
            max_gross_weight_g=Decimal("1000"),
        )


def test_material_outer_volume_must_contain_inner() -> None:
    with pytest.raises(ValidationError, match="outer material volume"):
        PackageMaterialSpec(
            material_id="SYNTH-BOX-BAD",
            inner_dimensions_mm=dimensions("200", "200", "200"),
            outer_dimensions_mm=dimensions("100", "100", "100"),
            tare_weight_g=Decimal("10"),
            max_gross_weight_g=Decimal("1000"),
        )


def test_sku_spec_requires_unique_compatible_materials() -> None:
    with pytest.raises(ValidationError, match="must be unique"):
        SkuPackagingSpec(
            sku="SYNTH-SKU-ALPHA",
            unit_weight_g=Decimal("250"),
            packed_unit_dimensions_mm=dimensions("100", "80", "60"),
            compatible_material_ids=("SYNTH-BOX-S", "SYNTH-BOX-S"),
        )


# ---------------------------------------------------------------- precedence


def test_policies_are_ordered_by_priority_then_id() -> None:
    built = ruleset(
        policies=(
            PackingPolicy(policy_id="SYNTH-POLICY-C", priority=2),
            PackingPolicy(policy_id="SYNTH-POLICY-B", priority=0),
            PackingPolicy(policy_id="SYNTH-POLICY-A", priority=0),
        )
    )

    assert [policy.policy_id for policy in built.ordered_policies()] == [
        "SYNTH-POLICY-A",
        "SYNTH-POLICY-B",
        "SYNTH-POLICY-C",
    ]


def test_lookup_helpers_return_none_for_unknown_identifiers() -> None:
    built = synthetic_ruleset()

    assert built.sku_spec_for("SYNTH-SKU-UNKNOWN") is None
    assert built.material_for("SYNTH-BOX-UNKNOWN") is None
    assert built.sku_spec_for(alpha_spec().sku) is not None


# --------------------------------------------------------------------- reader


def test_reader_raises_when_no_ruleset_is_configured() -> None:
    with pytest.raises(PackagingRulesConfigurationError):
        StaticPackagingRuleSetReader(None).get_active(NOW)


def test_reader_returns_the_active_ruleset() -> None:
    built = synthetic_ruleset()

    assert StaticPackagingRuleSetReader(built).get_active(NOW) is built


def test_reader_rejects_a_ruleset_outside_its_effective_window() -> None:
    built = synthetic_ruleset(effective_from=NOW, effective_to=NOW + timedelta(days=1))

    with pytest.raises(PackagingRulesConfigurationError):
        StaticPackagingRuleSetReader(built).get_active(NOW - timedelta(seconds=1))
    with pytest.raises(PackagingRulesConfigurationError):
        StaticPackagingRuleSetReader(built).get_active(NOW + timedelta(days=1))


def test_ruleset_is_active_at_window_boundaries() -> None:
    built = synthetic_ruleset(effective_from=NOW, effective_to=NOW + timedelta(days=1))

    assert built.is_active(NOW) is True
    assert built.is_active(NOW + timedelta(hours=23)) is True
    assert built.is_active(NOW + timedelta(days=1)) is False


def test_ruleset_models_are_immutable() -> None:
    built = synthetic_ruleset()

    with pytest.raises(ValidationError):
        built.version = "synthetic-v2"

    with pytest.raises(ValidationError):
        built.sku_specs[0].unit_weight_g = 1  # type: ignore[misc]


def test_utc_timestamp_helper_matches_fixture() -> None:
    assert NOW.tzinfo is not None
    assert NOW == datetime(2026, 11, 8, 1, 2, tzinfo=UTC)
