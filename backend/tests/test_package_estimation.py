"""Package estimation service tests: determinism, conservation and fail-closed rules."""

from datetime import timedelta
from decimal import Decimal

import pytest

from backend.models import (
    PackageDiagnosticCategory,
    PackageEstimationStatus,
    PackageReasonCode,
    PackageSource,
    PackagingRuleSet,
    PackingPolicy,
    SkuPackagingSpec,
)
from backend.services import (
    PackageEstimationService,
    StaticPackagingRuleSetReader,
)
from backend.tests.packaging_fixtures import (
    BOX_LARGE,
    BOX_SMALL,
    NOW,
    SKU_ALPHA,
    SKU_BETA,
    alpha_spec,
    beta_spec,
    dimensions,
    mixed_ruleset,
    products_for,
    synthetic_order,
    synthetic_ruleset,
)


def service(ruleset: PackagingRuleSet | None) -> PackageEstimationService:
    return PackageEstimationService(StaticPackagingRuleSetReader(ruleset), clock=lambda: NOW)


def estimate_with(
    ruleset: PackagingRuleSet | None,
    items: tuple[tuple[str, int, str], ...],
) -> object:
    order = synthetic_order(items)
    return service(ruleset).estimate_for_order(order, products_for(order))


def allocated(order_items: tuple[tuple[str, int, str], ...], result: object) -> dict[int, int]:
    """Return total allocated quantity per order line index."""

    totals: dict[int, int] = {}
    for package in result.packages:  # type: ignore[attr-defined]
        for item in package.items:
            totals[item.order_item_ref.line_index] = (
                totals.get(item.order_item_ref.line_index, 0) + item.quantity
            )
    return totals


# ------------------------------------------------------------------ happy path


def test_single_sku_produces_rules_packages_with_real_ruleset_facts() -> None:
    result = estimate_with(synthetic_ruleset(), ((SKU_ALPHA, 2, "GROUP-1"),))

    assert result.status is PackageEstimationStatus.AVAILABLE
    assert result.reason_code is None
    assert result.source is PackageSource.RULES
    assert result.ruleset_id == "synthetic-ruleset-j1"
    assert result.ruleset_version == "synthetic-v1"
    assert result.synthetic_ruleset is True
    assert len(result.packages) == 1

    package = result.packages[0]
    assert package.package_id == "PKG-001"
    assert package.order_number == "SYNTH-ORDER-001"
    assert package.source is PackageSource.RULES
    assert package.material_id == BOX_SMALL
    # Dimensions are the material's outer dimensions, never the product's.
    assert package.dimensions.length_mm == Decimal("210")
    # 2 units x 250 g packaged weight + 50 g tare.
    assert package.weight.item_weight_g == Decimal("500")
    assert package.weight.packaging_weight_g == Decimal("50")
    assert package.weight.gross_weight_g == Decimal("550")
    assert package.estimated_at == NOW


def test_package_weight_ignores_product_physical_data() -> None:
    order = synthetic_order(((SKU_ALPHA, 1, "GROUP-1"),))
    products = products_for(order)

    package = service(synthetic_ruleset()).estimate_for_order(order, products).packages[0]

    # The synthetic product weighs 7 g with 1x1x1 mm dimensions; the packaged unit
    # spec says 250 g and 100x80x60 mm. Only the ruleset may decide packaging.
    assert package.weight.item_weight_g == Decimal("250")
    assert package.dimensions.volume_mm3 == Decimal("3696000")
    assert products[0].weight_g == Decimal("7")


def test_quantity_is_conserved_exactly() -> None:
    items = ((SKU_ALPHA, 7, "GROUP-1"), (SKU_BETA, 3, "GROUP-2"))
    result = estimate_with(synthetic_ruleset(), items)

    assert result.status is PackageEstimationStatus.AVAILABLE
    assert allocated(items, result) == {0: 7, 1: 3}
    total = sum(item.quantity for package in result.packages for item in package.items)
    assert total == 10


def test_split_across_packages_is_supported() -> None:
    # Small box volume 3,000,000 / unit volume 480,000 => 6 units per box.
    result = estimate_with(synthetic_ruleset(), ((SKU_ALPHA, 7, "GROUP-1"),))

    assert [sum(item.quantity for item in p.items) for p in result.packages] == [6, 1]
    assert [p.package_id for p in result.packages] == ["PKG-001", "PKG-002"]


def test_same_sku_never_mixes_when_policy_forbids_it() -> None:
    result = estimate_with(
        synthetic_ruleset(), ((SKU_ALPHA, 2, "GROUP-1"), (SKU_BETA, 2, "GROUP-2"))
    )

    assert len(result.packages) == 2
    assert [package.material_id for package in result.packages] == [BOX_SMALL, BOX_LARGE]
    for package in result.packages:
        assert len({item.sku for item in package.items}) == 1


def test_mixed_sku_package_is_allowed_by_policy() -> None:
    result = estimate_with(mixed_ruleset(), ((SKU_ALPHA, 2, "GROUP-1"), (SKU_BETA, 2, "GROUP-2")))

    assert len(result.packages) == 1
    package = result.packages[0]
    assert {item.sku for item in package.items} == {SKU_ALPHA, SKU_BETA}
    assert allocated(((SKU_ALPHA, 2, "GROUP-1"), (SKU_BETA, 2, "GROUP-2")), result) == {
        0: 2,
        1: 2,
    }


def test_highest_priority_policy_wins() -> None:
    ruleset = synthetic_ruleset(
        versions=(alpha_spec(materials=(BOX_LARGE,)), beta_spec(materials=(BOX_LARGE,))),
    )
    with_policies = PackagingRuleSet(
        ruleset_id=ruleset.ruleset_id,
        version=ruleset.version,
        effective_from=ruleset.effective_from,
        effective_to=ruleset.effective_to,
        source_revision=ruleset.source_revision,
        synthetic_only=True,
        sku_specs=ruleset.sku_specs,
        materials=ruleset.materials,
        policies=(
            PackingPolicy(policy_id="SYNTH-POLICY-A", priority=0, allow_mixed_sku=False),
            PackingPolicy(policy_id="SYNTH-POLICY-B", priority=1, allow_mixed_sku=True),
        ),
    )

    result = estimate_with(with_policies, ((SKU_ALPHA, 1, "GROUP-1"), (SKU_BETA, 1, "GROUP-2")))

    # Priority 0 forbids mixing, so the permissive priority 1 policy never applies.
    assert len(result.packages) == 2


# ---------------------------------------------------------------- determinism


def test_estimation_is_deterministic_for_the_same_input_and_ruleset() -> None:
    ruleset = synthetic_ruleset()
    items = ((SKU_ALPHA, 7, "GROUP-1"), (SKU_BETA, 5, "GROUP-2"))

    first = estimate_with(ruleset, items)
    second = estimate_with(ruleset, items)

    assert first.model_dump() == second.model_dump()

    package_ids = [package.package_id for package in first.packages]
    assert package_ids == sorted(package_ids)
    assert len(package_ids) == len(set(package_ids))


def test_provenance_is_recorded_and_stable() -> None:
    ruleset = synthetic_ruleset()
    items = ((SKU_ALPHA, 2, "GROUP-1"),)

    first = estimate_with(ruleset, items)
    second = estimate_with(ruleset, items)

    provenance = first.packages[0].provenance
    assert provenance.source is PackageSource.RULES
    assert provenance.source_revision == "synthetic-source-revision-1"
    assert provenance.ruleset_id == "synthetic-ruleset-j1"
    assert provenance.ruleset_version == "synthetic-v1"
    assert provenance.generated_at == NOW
    assert provenance.input_fingerprint == second.packages[0].provenance.input_fingerprint


def test_provenance_fingerprint_differs_for_a_different_ruleset_version() -> None:
    items = ((SKU_ALPHA, 2, "GROUP-1"),)

    first = estimate_with(synthetic_ruleset(version="synthetic-v1"), items)
    second = estimate_with(synthetic_ruleset(version="synthetic-v2"), items)

    assert (
        first.packages[0].provenance.input_fingerprint
        != second.packages[0].provenance.input_fingerprint
    )


# ----------------------------------------------------------------- fail closed


def test_missing_active_ruleset_fails_closed() -> None:
    result = estimate_with(None, ((SKU_ALPHA, 1, "GROUP-1"),))

    assert result.status is PackageEstimationStatus.UNAVAILABLE
    assert result.reason_code is PackageReasonCode.PACKAGE_RULES_NOT_CONFIGURED
    assert result.packages == ()
    assert result.source is None
    assert result.synthetic_ruleset is False
    assert result.diagnostics[0].category is PackageDiagnosticCategory.RULES_NOT_CONFIGURED


def test_inactive_ruleset_fails_closed() -> None:
    expired = synthetic_ruleset(effective_from=NOW - timedelta(days=2), effective_to=NOW)

    result = estimate_with(expired, ((SKU_ALPHA, 1, "GROUP-1"),))

    assert result.reason_code is PackageReasonCode.PACKAGE_RULES_NOT_CONFIGURED


def test_missing_sku_packaging_spec_fails_closed() -> None:
    rules_without_beta = synthetic_ruleset(
        versions=(alpha_spec(),),
        materials=(synthetic_ruleset().materials[0], synthetic_ruleset().materials[1]),
    )

    result = estimate_with(rules_without_beta, ((SKU_BETA, 1, "GROUP-1"),))

    assert result.status is PackageEstimationStatus.UNAVAILABLE
    assert result.reason_code is PackageReasonCode.PACKAGE_DATA_INCOMPLETE
    assert result.packages == ()
    diagnostic = result.diagnostics[0]
    assert diagnostic.category is PackageDiagnosticCategory.SKU_SPEC_MISSING
    assert diagnostic.sku == SKU_BETA


def test_missing_material_spec_fails_closed() -> None:
    valid = synthetic_ruleset()
    # Model a corrupted publication: specs still reference materials that the
    # published ruleset no longer contains.
    corrupted = PackagingRuleSet.model_construct(
        ruleset_id=valid.ruleset_id,
        version=valid.version,
        effective_from=valid.effective_from,
        effective_to=valid.effective_to,
        source_revision=valid.source_revision,
        synthetic_only=True,
        sku_specs=valid.sku_specs,
        materials=(),
        policies=valid.policies,
    )

    result = estimate_with(corrupted, ((SKU_ALPHA, 1, "GROUP-1"),))

    assert result.status is PackageEstimationStatus.UNAVAILABLE
    assert result.reason_code is PackageReasonCode.PACKAGE_DATA_INCOMPLETE
    assert result.diagnostics[0].category is PackageDiagnosticCategory.MATERIAL_MISSING


def test_ruleset_without_policy_fails_closed() -> None:
    valid = synthetic_ruleset()
    corrupted = PackagingRuleSet.model_construct(
        ruleset_id=valid.ruleset_id,
        version=valid.version,
        effective_from=valid.effective_from,
        effective_to=valid.effective_to,
        source_revision=valid.source_revision,
        synthetic_only=True,
        sku_specs=valid.sku_specs,
        materials=valid.materials,
        policies=(),
    )

    result = estimate_with(corrupted, ((SKU_ALPHA, 1, "GROUP-1"),))

    assert result.status is PackageEstimationStatus.UNAVAILABLE
    assert result.reason_code is PackageReasonCode.PACKAGE_DATA_INCOMPLETE


def test_oversized_packaged_unit_fails_closed_on_capacity() -> None:
    oversized = SkuPackagingSpec(
        sku=SKU_ALPHA,
        unit_weight_g=Decimal("250"),
        packed_unit_dimensions_mm=dimensions("500", "500", "500"),
        compatible_material_ids=(BOX_SMALL, BOX_LARGE),
    )

    result = estimate_with(synthetic_ruleset(versions=(oversized,)), ((SKU_ALPHA, 1, "GROUP-1"),))

    assert result.status is PackageEstimationStatus.UNAVAILABLE
    assert result.reason_code is PackageReasonCode.PACKAGE_DATA_INCOMPLETE
    assert result.diagnostics[0].category is PackageDiagnosticCategory.CAPACITY_EXCEEDED


def test_oversized_packaged_weight_fails_closed_on_capacity() -> None:
    overweight = SkuPackagingSpec(
        sku=SKU_ALPHA,
        unit_weight_g=Decimal("30000"),
        packed_unit_dimensions_mm=dimensions("100", "80", "60"),
        compatible_material_ids=(BOX_SMALL, BOX_LARGE),
    )

    result = estimate_with(synthetic_ruleset(versions=(overweight,)), ((SKU_ALPHA, 1, "GROUP-1"),))

    assert result.reason_code is PackageReasonCode.PACKAGE_DATA_INCOMPLETE
    assert result.diagnostics[0].category is PackageDiagnosticCategory.CAPACITY_EXCEEDED


def test_split_forbidden_policy_fails_closed_when_split_is_required() -> None:
    result = estimate_with(synthetic_ruleset(allow_split=False), ((SKU_ALPHA, 7, "GROUP-1"),))

    assert result.status is PackageEstimationStatus.UNAVAILABLE
    assert result.reason_code is PackageReasonCode.PACKAGE_DATA_INCOMPLETE
    assert result.diagnostics[0].safe_detail is not None
    assert "splitting" in (result.diagnostics[0].safe_detail or "")


def test_mismatched_product_association_fails_closed() -> None:
    order = synthetic_order(((SKU_ALPHA, 1, "GROUP-1"),))
    wrong_products = products_for(synthetic_order(((SKU_BETA, 1, "GROUP-1"),)))

    result = service(synthetic_ruleset()).estimate_for_order(order, wrong_products)

    assert result.reason_code is PackageReasonCode.PACKAGE_DATA_INCOMPLETE
    assert result.diagnostics[0].category is PackageDiagnosticCategory.INVALID_INPUT


def test_order_without_lines_fails_closed() -> None:
    order = synthetic_order(((SKU_ALPHA, 1, "GROUP-1"),))
    empty_order = order.model_copy(update={"items": ()})

    result = service(synthetic_ruleset()).estimate_for_order(empty_order, ())

    assert result.status is PackageEstimationStatus.UNAVAILABLE
    assert result.reason_code is PackageReasonCode.PACKAGE_DATA_INCOMPLETE
    assert result.diagnostics[0].category is PackageDiagnosticCategory.INVALID_INPUT


def test_unavailable_result_never_contains_packages() -> None:
    for ruleset in (None, synthetic_ruleset(versions=(alpha_spec(),))):
        result = estimate_with(ruleset, ((SKU_BETA, 1, "GROUP-1"),))
        assert result.packages == ()
        assert result.source is None


def test_public_reason_codes_are_limited_to_the_frozen_pair() -> None:
    assert {code.value for code in PackageReasonCode} == {
        "PACKAGE_RULES_NOT_CONFIGURED",
        "PACKAGE_DATA_INCOMPLETE",
    }


@pytest.mark.parametrize("quantity", [1, 6, 7, 13])
def test_various_quantities_preserve_conservation(quantity: int) -> None:
    items = ((SKU_ALPHA, quantity, "GROUP-1"),)

    result = estimate_with(synthetic_ruleset(), items)

    assert result.status is PackageEstimationStatus.AVAILABLE
    assert allocated(items, result) == {0: quantity}


# ------------------------------------------------- synthetic isolation hardening


def test_non_synthetic_ruleset_is_refused_even_if_validation_is_bypassed() -> None:
    valid = synthetic_ruleset()
    # Simulate a corrupted or bypassed publication that claims production status.
    claimed_production = PackagingRuleSet.model_construct(
        ruleset_id="claimed-production",
        version="v9",
        effective_from=valid.effective_from,
        effective_to=valid.effective_to,
        source_revision="claimed-source",
        synthetic_only=False,
        sku_specs=valid.sku_specs,
        materials=valid.materials,
        policies=valid.policies,
    )

    result = estimate_with(claimed_production, ((SKU_ALPHA, 1, "GROUP-1"),))

    assert result.status is PackageEstimationStatus.UNAVAILABLE
    assert result.reason_code is PackageReasonCode.PACKAGE_RULES_NOT_CONFIGURED
    assert result.packages == ()
    assert result.synthetic_ruleset is False
    assert result.diagnostics[0].category is PackageDiagnosticCategory.RULES_NOT_CONFIGURED


def test_non_synthetic_policy_is_refused_even_if_validation_is_bypassed() -> None:
    valid = synthetic_ruleset()
    plain_policy = PackingPolicy.model_construct(
        policy_id="PLAIN-POLICY",
        priority=0,
        synthetic_only=False,
        strategy=valid.policies[0].strategy,
        material_selection=valid.policies[0].material_selection,
        allow_split=True,
        allow_mixed_sku=False,
    )
    claimed_production = PackagingRuleSet.model_construct(
        ruleset_id=valid.ruleset_id,
        version=valid.version,
        effective_from=valid.effective_from,
        effective_to=valid.effective_to,
        source_revision=valid.source_revision,
        synthetic_only=True,
        sku_specs=valid.sku_specs,
        materials=valid.materials,
        policies=(plain_policy,),
    )

    result = estimate_with(claimed_production, ((SKU_ALPHA, 1, "GROUP-1"),))

    assert result.status is PackageEstimationStatus.UNAVAILABLE
    assert result.reason_code is PackageReasonCode.PACKAGE_RULES_NOT_CONFIGURED
    assert result.packages == ()


def test_synthetic_estimation_always_reports_the_synthetic_flag() -> None:
    result = estimate_with(synthetic_ruleset(), ((SKU_ALPHA, 1, "GROUP-1"),))

    assert result.status is PackageEstimationStatus.AVAILABLE
    assert result.synthetic_ruleset is True
