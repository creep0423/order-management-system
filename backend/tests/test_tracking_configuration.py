"""Per-Revision-ID immutability for tracking configuration revisions."""

from datetime import UTC, datetime
from decimal import Decimal
from typing import Any

import pytest
from pydantic import ValidationError

from backend.models import (
    AccountRevision,
    CarrierProvider,
    ConfigurationCapability,
    MappingRevision,
    ProductRevision,
    ProviderConfiguration,
    ProviderEnvironment,
    ProviderRevision,
    ResolvedTrackingMapping,
    TrackingConfigurationRelease,
)
from backend.services import ConfigurationRevisionConflictError, TrackingConfigurationCatalog

NOW = datetime(2026, 11, 8, 1, 2, tzinfo=UTC)
GROUP_ID = "GROUP-1"


def provider_configuration(**overrides: Any) -> ProviderConfiguration:
    values: dict[str, Any] = {
        "release_revision_id": "release-rev-1",
        "mapping_revision_id": "mapping-rev-1",
        "provider_revision_id": "provider-rev-1",
        "account_revision_id": "account-rev-1",
        "product_revision_id": "product-rev-1",
        "provider": CarrierProvider.AUSTRALIA_POST,
        "adapter_key": "auspost-track-v1",
        "environment": ProviderEnvironment.TESTBED,
        "base_url": "https://example.invalid/track",
        "credential_ref": "credential-ref-1",
        "connect_timeout_seconds": 2.0,
        "read_timeout_seconds": 5.0,
        "evidence_ref": "synthetic-provider-evidence",
    }
    values.update(overrides)
    return ProviderConfiguration(**values)


def provider_revision(configuration: ProviderConfiguration, **overrides: Any) -> ProviderRevision:
    values: dict[str, Any] = {
        "provider_revision_id": configuration.provider_revision_id,
        "provider": configuration.provider,
        "adapter_key": configuration.adapter_key,
        "environment": configuration.environment,
        "base_url": configuration.base_url,
        "capabilities": frozenset({ConfigurationCapability.TRACKING}),
        "connect_timeout_seconds": configuration.connect_timeout_seconds,
        "read_timeout_seconds": configuration.read_timeout_seconds,
        "max_response_bytes": configuration.max_response_bytes,
        "credential_ref": configuration.credential_ref,
        "validated_at": NOW,
        "evidence_ref": configuration.evidence_ref,
    }
    values.update(overrides)
    return ProviderRevision(**values)


def account_revision(configuration: ProviderConfiguration, **overrides: Any) -> AccountRevision:
    values: dict[str, Any] = {
        "account_revision_id": configuration.account_revision_id,
        "provider_revision_id": configuration.provider_revision_id,
        "environment": configuration.environment,
        "origin_id": "origin-sydney",
        "account_ref": "synthetic-account-ref-1",
        "capabilities": frozenset({ConfigurationCapability.TRACKING}),
        "validated_at": NOW,
        "evidence_ref": "synthetic-account-evidence",
    }
    values.update(overrides)
    return AccountRevision(**values)


def product_revision(configuration: ProviderConfiguration, **overrides: Any) -> ProductRevision:
    values: dict[str, Any] = {
        "product_revision_id": configuration.product_revision_id,
        "provider_revision_id": configuration.provider_revision_id,
        "environment": configuration.environment,
        "product_id": "product-synthetic",
        "service_code": "SYNTHETIC-TRACK",
        "capabilities": frozenset({ConfigurationCapability.TRACKING}),
        "gst_semantics_ref": "synthetic-gst-evidence",
        "precision_rule_ref": "synthetic-precision-evidence",
        "validated_at": NOW,
        "evidence_ref": "synthetic-product-evidence",
    }
    values.update(overrides)
    return ProductRevision(**values)


def mapping_revision(
    configuration: ProviderConfiguration,
    *,
    tracking_group_id: str = GROUP_ID,
    **overrides: Any,
) -> MappingRevision:
    values: dict[str, Any] = {
        "mapping_revision_id": configuration.mapping_revision_id,
        "capability": ConfigurationCapability.TRACKING,
        "provider_revision_id": configuration.provider_revision_id,
        "account_revision_id": configuration.account_revision_id,
        "product_revision_id": configuration.product_revision_id,
        "environment": configuration.environment,
        "selection_scope": f"tracking-group:{tracking_group_id}",
        "tracking_group_id": tracking_group_id,
        "validated_at": NOW,
        "evidence_ref": "synthetic-mapping-evidence",
    }
    values.update(overrides)
    return MappingRevision(**values)


def bundle(
    *,
    group_id: str = GROUP_ID,
    provider_revision_id: str = "provider-rev-1",
    account_revision_id: str = "account-rev-1",
    product_revision_id: str = "product-rev-1",
    mapping_revision_id: str = "mapping-rev-1",
    release_revision_id: str = "release-rev-1",
    **configuration_overrides: Any,
) -> dict[str, Any]:
    configuration = provider_configuration(
        provider_revision_id=provider_revision_id,
        account_revision_id=account_revision_id,
        product_revision_id=product_revision_id,
        mapping_revision_id=mapping_revision_id,
        release_revision_id=release_revision_id,
        **configuration_overrides,
    )
    provider = provider_revision(configuration)
    account = account_revision(configuration)
    product = product_revision(configuration)
    mapping = mapping_revision(configuration, tracking_group_id=group_id)
    release = TrackingConfigurationRelease(
        release_revision_id=release_revision_id,
        environment=configuration.environment,
        configuration_scope="order-tracking",
        provider_revisions=(provider,),
        account_revisions=(account,),
        product_revisions=(product,),
        mapping_revisions=(mapping,),
        mappings=(
            ResolvedTrackingMapping(
                tracking_group_id=group_id,
                configuration=configuration,
                resolved_at=NOW,
            ),
        ),
        captured_at=NOW,
    )
    return {
        "configuration": configuration,
        "provider": provider,
        "account": account,
        "product": product,
        "mapping": mapping,
        "release": release,
    }


def test_registering_identical_revision_content_is_idempotent() -> None:
    base = bundle()
    catalog = TrackingConfigurationCatalog()

    catalog.register_release(base["release"])
    catalog.register_release(base["release"])

    assert (
        catalog.get_provider_revision("provider-rev-1").model_dump()
        == base["provider"].model_dump()
    )
    assert catalog.get_release("release-rev-1").model_dump() == base["release"].model_dump()


def test_same_provider_revision_id_with_different_base_url_is_rejected() -> None:
    catalog = TrackingConfigurationCatalog()
    catalog.register_release(bundle()["release"])

    with pytest.raises(ConfigurationRevisionConflictError, match="provider revision"):
        catalog.register_release(bundle(base_url="https://example.invalid/other")["release"])


def test_same_provider_revision_id_with_different_adapter_is_rejected() -> None:
    catalog = TrackingConfigurationCatalog()
    catalog.register_release(bundle()["release"])

    with pytest.raises(ConfigurationRevisionConflictError, match="provider revision"):
        catalog.register_release(bundle(adapter_key="auspost-track-v2")["release"])


def test_same_provider_revision_id_with_different_timeout_is_rejected() -> None:
    catalog = TrackingConfigurationCatalog()
    catalog.register_release(bundle()["release"])

    with pytest.raises(ConfigurationRevisionConflictError, match="provider revision"):
        catalog.register_release(bundle(read_timeout_seconds=9.0)["release"])


def test_same_account_revision_id_with_different_account_number_is_rejected() -> None:
    catalog = TrackingConfigurationCatalog()
    base = bundle()
    catalog.register_release(base["release"])

    with pytest.raises(ConfigurationRevisionConflictError, match="account revision"):
        catalog.register_account_revision(
            base["account"].model_copy(update={"account_ref": "synthetic-account-ref-2"})
        )


def test_same_account_revision_id_with_different_origin_is_rejected() -> None:
    catalog = TrackingConfigurationCatalog()
    base = bundle()
    catalog.register_release(base["release"])

    with pytest.raises(ConfigurationRevisionConflictError, match="account revision"):
        catalog.register_account_revision(
            base["account"].model_copy(update={"origin_id": "origin-melbourne"})
        )


def test_same_product_revision_id_with_different_service_code_is_rejected() -> None:
    catalog = TrackingConfigurationCatalog()
    base = bundle()
    catalog.register_release(base["release"])

    with pytest.raises(ConfigurationRevisionConflictError, match="product revision"):
        catalog.register_product_revision(
            base["product"].model_copy(update={"service_code": "OTHER-SERVICE"})
        )


@pytest.mark.parametrize(
    "overrides",
    [
        {"gst_semantics_ref": "different-gst-evidence"},
        {"precision_rule_ref": "different-precision-evidence"},
        {"contract_price_aud": Decimal("12.34")},
    ],
)
def test_same_product_revision_id_with_different_evidence_is_rejected(
    overrides: dict[str, Any],
) -> None:
    catalog = TrackingConfigurationCatalog()
    base = bundle()
    catalog.register_release(base["release"])

    with pytest.raises(ConfigurationRevisionConflictError, match="product revision"):
        catalog.register_product_revision(base["product"].model_copy(update=overrides))


def test_same_mapping_revision_id_with_different_references_is_rejected() -> None:
    catalog = TrackingConfigurationCatalog()
    catalog.register_release(bundle()["release"])

    with pytest.raises(ConfigurationRevisionConflictError, match="mapping revision"):
        catalog.register_release(
            bundle(
                provider_revision_id="provider-rev-2",
                account_revision_id="account-rev-2",
                product_revision_id="product-rev-2",
            )["release"]
        )


def test_same_release_revision_id_with_different_mapping_set_is_rejected() -> None:
    catalog = TrackingConfigurationCatalog()
    catalog.register_release(bundle()["release"])

    with pytest.raises(ConfigurationRevisionConflictError, match="release revision"):
        catalog.register_release(
            bundle(
                mapping_revision_id="mapping-rev-2",
                provider_revision_id="provider-rev-2",
                account_revision_id="account-rev-2",
                product_revision_id="product-rev-2",
            )["release"]
        )


def test_provider_content_change_is_rejected_even_when_other_revision_ids_differ() -> None:
    catalog = TrackingConfigurationCatalog()
    catalog.register_release(bundle()["release"])

    # A different Provider/Account/Product tuple must never hide a mutated
    # Provider Revision.
    with pytest.raises(ConfigurationRevisionConflictError, match="provider revision"):
        catalog.register_release(
            bundle(
                base_url="https://example.invalid/other",
                account_revision_id="account-rev-2",
                product_revision_id="product-rev-2",
                mapping_revision_id="mapping-rev-2",
                release_revision_id="release-rev-2",
            )["release"]
        )


def test_different_revision_ids_and_releases_may_hold_different_content() -> None:
    catalog = TrackingConfigurationCatalog()

    first = bundle()
    second = bundle(
        provider_revision_id="provider-rev-2",
        account_revision_id="account-rev-2",
        product_revision_id="product-rev-2",
        mapping_revision_id="mapping-rev-2",
        release_revision_id="release-rev-2",
        base_url="https://example.invalid/v2",
        adapter_key="auspost-track-v2",
        read_timeout_seconds=9.0,
    )
    catalog.register_release(first["release"])
    catalog.register_release(second["release"])

    assert catalog.get_provider_revision("provider-rev-1").base_url != (
        catalog.get_provider_revision("provider-rev-2").base_url
    )
    assert catalog.get_release("release-rev-1") is not catalog.get_release("release-rev-2")


def test_release_rejects_one_revision_id_with_two_contents() -> None:
    base = bundle()
    conflicting_account = base["account"].model_copy(
        update={"account_ref": "synthetic-account-ref-2"}
    )

    with pytest.raises(ValidationError, match="account revision id maps to inconsistent"):
        TrackingConfigurationRelease(
            release_revision_id=base["release"].release_revision_id,
            environment=base["release"].environment,
            configuration_scope=base["release"].configuration_scope,
            provider_revisions=base["release"].provider_revisions,
            account_revisions=(base["account"], conflicting_account),
            product_revisions=base["release"].product_revisions,
            mapping_revisions=base["release"].mapping_revisions,
            mappings=base["release"].mappings,
            captured_at=NOW,
        )


def test_release_accepts_identical_duplicate_revision_records() -> None:
    base = bundle()

    release = TrackingConfigurationRelease(
        release_revision_id=base["release"].release_revision_id,
        environment=base["release"].environment,
        configuration_scope=base["release"].configuration_scope,
        provider_revisions=(base["provider"], base["provider"]),
        account_revisions=base["release"].account_revisions,
        product_revisions=base["release"].product_revisions,
        mapping_revisions=base["release"].mapping_revisions,
        mappings=base["release"].mappings,
        captured_at=NOW,
    )

    assert len(release.provider_revisions) == 2


def test_release_rejects_provider_revision_content_that_differs_from_pinned_config() -> None:
    base = bundle()
    mismatched_provider = provider_revision(
        base["configuration"], base_url="https://example.invalid/other"
    )

    with pytest.raises(ValidationError, match="provider revision content"):
        TrackingConfigurationRelease(
            release_revision_id=base["release"].release_revision_id,
            environment=base["release"].environment,
            configuration_scope=base["release"].configuration_scope,
            provider_revisions=(mismatched_provider,),
            account_revisions=base["release"].account_revisions,
            product_revisions=base["release"].product_revisions,
            mapping_revisions=base["release"].mapping_revisions,
            mappings=base["release"].mappings,
            captured_at=NOW,
        )


def test_release_rejects_mapping_revision_for_another_tracking_group() -> None:
    base = bundle()

    with pytest.raises(ValidationError, match="mapping revision does not match"):
        TrackingConfigurationRelease(
            release_revision_id=base["release"].release_revision_id,
            environment=base["release"].environment,
            configuration_scope=base["release"].configuration_scope,
            provider_revisions=base["release"].provider_revisions,
            account_revisions=base["release"].account_revisions,
            product_revisions=base["release"].product_revisions,
            mapping_revisions=(
                mapping_revision(base["configuration"], tracking_group_id="GROUP-9"),
            ),
            mappings=base["release"].mappings,
            captured_at=NOW,
        )


def test_release_rejects_revisions_without_the_tracking_capability() -> None:
    base = bundle()
    quote_only_account = account_revision(
        base["configuration"],
        capabilities=frozenset({ConfigurationCapability.SHIPPING_QUOTE}),
    )

    with pytest.raises(ValidationError, match="tracking capability"):
        TrackingConfigurationRelease(
            release_revision_id=base["release"].release_revision_id,
            environment=base["release"].environment,
            configuration_scope=base["release"].configuration_scope,
            provider_revisions=base["release"].provider_revisions,
            account_revisions=(quote_only_account,),
            product_revisions=base["release"].product_revisions,
            mapping_revisions=base["release"].mapping_revisions,
            mappings=base["release"].mappings,
            captured_at=NOW,
        )
