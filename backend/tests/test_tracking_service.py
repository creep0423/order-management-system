"""Tracking service batching, error isolation and configuration tests."""

from collections.abc import Callable
from datetime import UTC, datetime

from backend.models import (
    AccountRevision,
    CarrierProvider,
    ConfigurationCapability,
    MappingRevision,
    NormalizedTrackingStatus,
    ProductRevision,
    ProviderConfiguration,
    ProviderEnvironment,
    ProviderRevision,
    ProviderTrackingResult,
    ResolvedTrackingMapping,
    ResultStatus,
    TrackingConfigurationRelease,
    TrackingDiagnostic,
    TrackingDiagnosticCategory,
    TrackingGroup,
    TrackingProviderError,
    TrackingReasonCode,
    TrackingRequest,
)
from backend.services import (
    StaticTrackingConfigurationReader,
    StaticTrackingProviderRegistry,
    TrackingService,
)

NOW = datetime(2026, 11, 8, 1, 2, tzinfo=UTC)


def config(
    provider: CarrierProvider,
    *,
    group_id: str,
    provider_revision_id: str | None = None,
) -> ProviderConfiguration:
    revision = provider_revision_id or f"provider-{provider.value}-rev-1"
    return ProviderConfiguration(
        release_revision_id="release-rev-1",
        mapping_revision_id=f"mapping-{revision}-{group_id}-rev-1",
        provider_revision_id=revision,
        account_revision_id=f"account-{provider.value}-rev-1",
        product_revision_id=f"product-{provider.value}-rev-1",
        provider=provider,
        adapter_key=f"{provider.value}-track-v1",
        environment=ProviderEnvironment.TESTBED,
        base_url="https://example.invalid/test",
        credential_ref=f"credential-{provider.value}",
        connect_timeout_seconds=2.0,
        read_timeout_seconds=5.0,
        evidence_ref="synthetic-approved-evidence",
    )


def provider_revision(configuration: ProviderConfiguration) -> ProviderRevision:
    return ProviderRevision(
        provider_revision_id=configuration.provider_revision_id,
        provider=configuration.provider,
        adapter_key=configuration.adapter_key,
        environment=configuration.environment,
        base_url=configuration.base_url,
        capabilities=frozenset({ConfigurationCapability.TRACKING}),
        connect_timeout_seconds=configuration.connect_timeout_seconds,
        read_timeout_seconds=configuration.read_timeout_seconds,
        max_response_bytes=configuration.max_response_bytes,
        credential_ref=configuration.credential_ref,
        validated_at=NOW,
        evidence_ref=configuration.evidence_ref,
    )


def account_revision(configuration: ProviderConfiguration) -> AccountRevision:
    return AccountRevision(
        account_revision_id=configuration.account_revision_id,
        provider_revision_id=configuration.provider_revision_id,
        environment=configuration.environment,
        origin_id=f"origin-{configuration.provider.value}",
        account_ref=f"account-ref-{configuration.provider.value}",
        capabilities=frozenset({ConfigurationCapability.TRACKING}),
        validated_at=NOW,
        evidence_ref="synthetic-account-evidence",
    )


def product_revision(configuration: ProviderConfiguration) -> ProductRevision:
    return ProductRevision(
        product_revision_id=configuration.product_revision_id,
        provider_revision_id=configuration.provider_revision_id,
        environment=configuration.environment,
        product_id=f"product-{configuration.provider.value}",
        service_code=f"{configuration.provider.value}-track",
        capabilities=frozenset({ConfigurationCapability.TRACKING}),
        gst_semantics_ref="synthetic-gst-evidence",
        precision_rule_ref="synthetic-precision-evidence",
        validated_at=NOW,
        evidence_ref="synthetic-product-evidence",
    )


def mapping_revision(
    configuration: ProviderConfiguration, tracking_group_id: str
) -> MappingRevision:
    return MappingRevision(
        mapping_revision_id=configuration.mapping_revision_id,
        capability=ConfigurationCapability.TRACKING,
        provider_revision_id=configuration.provider_revision_id,
        account_revision_id=configuration.account_revision_id,
        product_revision_id=configuration.product_revision_id,
        environment=configuration.environment,
        selection_scope=f"tracking-group:{tracking_group_id}",
        tracking_group_id=tracking_group_id,
        validated_at=NOW,
        evidence_ref="synthetic-mapping-evidence",
    )


def release(*configs: tuple[str, ProviderConfiguration]) -> TrackingConfigurationRelease:
    configurations = tuple(configuration for _group_id, configuration in configs)
    return TrackingConfigurationRelease(
        release_revision_id="release-rev-1",
        environment=ProviderEnvironment.TESTBED,
        configuration_scope="order-tracking",
        provider_revisions=tuple(provider_revision(item) for item in configurations),
        account_revisions=tuple(account_revision(item) for item in configurations),
        product_revisions=tuple(product_revision(item) for item in configurations),
        mapping_revisions=tuple(
            mapping_revision(configuration, group_id) for group_id, configuration in configs
        ),
        mappings=tuple(
            ResolvedTrackingMapping(
                tracking_group_id=group_id,
                configuration=configuration,
                resolved_at=NOW,
            )
            for group_id, configuration in configs
        ),
        captured_at=NOW,
    )


def group(index: int) -> TrackingGroup:
    return TrackingGroup(
        tracking_group_id=f"GROUP-{index}",
        carrier="Synthetic display only",
        tracking_number=f"SYNTHETIC-ID-{index}",
    )


class FakeProvider:
    def __init__(
        self,
        provider: CarrierProvider,
        revision_id: str,
        handler: Callable[[tuple[TrackingRequest, ...]], tuple[ProviderTrackingResult, ...]],
    ) -> None:
        self._provider = provider
        self._revision_id = revision_id
        self._handler = handler
        self.calls: list[tuple[TrackingRequest, ...]] = []

    @property
    def provider(self) -> CarrierProvider:
        return self._provider

    @property
    def adapter_key(self) -> str:
        return f"{self._provider.value}-track-v1"

    @property
    def configuration_key(self) -> tuple[str, str, str]:
        return (
            self._revision_id,
            f"account-{self._provider.value}-rev-1",
            f"product-{self._provider.value}-rev-1",
        )

    @property
    def provider_revision_id(self) -> str:
        return self._revision_id

    def track(self, batch: tuple[TrackingRequest, ...]) -> tuple[ProviderTrackingResult, ...]:
        self.calls.append(batch)
        return self._handler(batch)


def available(batch: tuple[TrackingRequest, ...]) -> tuple[ProviderTrackingResult, ...]:
    return tuple(
        ProviderTrackingResult(
            request_item_index=index,
            provider_status="In transit",
            current_status=NormalizedTrackingStatus.IN_TRANSIT,
            latest_event_at=None,
            events=(),
        )
        for index, _request in enumerate(batch)
    )


def service_for(
    configuration_release: TrackingConfigurationRelease,
    *providers: FakeProvider,
) -> TrackingService:
    return TrackingService(
        StaticTrackingConfigurationReader(configuration_release),
        StaticTrackingProviderRegistry(providers),
        clock=lambda: NOW,
    )


def test_service_batches_by_provider_and_preserves_group_order() -> None:
    ap_revision = "provider-australia_post-rev-1"
    st_revision = "provider-startrack-rev-1"
    mappings = (
        ("GROUP-1", config(CarrierProvider.AUSTRALIA_POST, group_id="GROUP-1")),
        ("GROUP-2", config(CarrierProvider.STARTRACK, group_id="GROUP-2")),
        ("GROUP-3", config(CarrierProvider.AUSTRALIA_POST, group_id="GROUP-3")),
    )
    ap = FakeProvider(CarrierProvider.AUSTRALIA_POST, ap_revision, available)
    st = FakeProvider(CarrierProvider.STARTRACK, st_revision, available)

    results = service_for(release(*mappings), ap, st).track_order((group(1), group(2), group(3)))

    assert [result.tracking_group_id for result in results] == ["GROUP-1", "GROUP-2", "GROUP-3"]
    assert [result.provider for result in results] == [
        CarrierProvider.AUSTRALIA_POST,
        CarrierProvider.STARTRACK,
        CarrierProvider.AUSTRALIA_POST,
    ]
    assert len(ap.calls) == 1
    assert len(ap.calls[0]) == 2
    assert len(st.calls) == 1


def test_service_splits_provider_batches_at_ten_and_deduplicates_groups() -> None:
    revision = "provider-australia_post-rev-1"
    mappings = tuple(
        (
            f"GROUP-{index}",
            config(
                CarrierProvider.AUSTRALIA_POST,
                group_id=f"GROUP-{index}",
                provider_revision_id=revision,
            ),
        )
        for index in range(1, 12)
    )
    provider = FakeProvider(CarrierProvider.AUSTRALIA_POST, revision, available)
    groups = tuple(group(index) for index in range(1, 12)) + (group(1),)

    results = service_for(release(*mappings), provider).track_order(groups)

    assert len(results) == 11
    assert [len(call) for call in provider.calls] == [10, 1]


def test_service_deduplicates_same_tracking_id_and_fans_out_real_result() -> None:
    revision = "provider-australia_post-rev-1"
    mappings = tuple(
        (
            f"GROUP-{index}",
            config(
                CarrierProvider.AUSTRALIA_POST,
                group_id=f"GROUP-{index}",
                provider_revision_id=revision,
            ),
        )
        for index in (1, 2)
    )
    provider = FakeProvider(CarrierProvider.AUSTRALIA_POST, revision, available)
    first = group(1)
    second = TrackingGroup(
        tracking_group_id="GROUP-2",
        carrier="Synthetic display only",
        tracking_number=first.tracking_number,
    )

    results = service_for(release(*mappings), provider).track_order((first, second))

    assert len(provider.calls) == 1
    assert len(provider.calls[0]) == 1
    assert [result.tracking_group_id for result in results] == ["GROUP-1", "GROUP-2"]
    assert all(result.status is ResultStatus.AVAILABLE for result in results)


def test_item_failure_does_not_cancel_successful_sibling() -> None:
    def mixed(batch: tuple[TrackingRequest, ...]) -> tuple[ProviderTrackingResult, ...]:
        del batch
        diagnostic = TrackingDiagnostic(
            category=TrackingDiagnosticCategory.INVALID_REQUEST,
            provider_code="ESB-10001",
            http_status=200,
            retryable=False,
            safe_detail="provider rejected item",
            item_index=1,
        )
        return (
            ProviderTrackingResult(
                request_item_index=0,
                provider_status="Delivered",
                current_status=NormalizedTrackingStatus.DELIVERED,
                latest_event_at=None,
                events=(),
            ),
            ProviderTrackingResult(
                request_item_index=1,
                error_category=TrackingDiagnosticCategory.INVALID_REQUEST,
                diagnostic=diagnostic,
            ),
        )

    provider = FakeProvider(CarrierProvider.AUSTRALIA_POST, "provider-australia_post-rev-1", mixed)
    mappings = tuple(
        (
            f"GROUP-{index}",
            config(CarrierProvider.AUSTRALIA_POST, group_id=f"GROUP-{index}"),
        )
        for index in (1, 2)
    )

    results = service_for(release(*mappings), provider).track_order((group(1), group(2)))

    assert results[0].status is ResultStatus.AVAILABLE
    assert results[1].status is ResultStatus.UNAVAILABLE
    assert results[1].reason_code is TrackingReasonCode.TRACKING_ID_INVALID


def test_provider_failure_does_not_propagate_to_other_provider() -> None:
    def fail(_batch: tuple[TrackingRequest, ...]) -> tuple[ProviderTrackingResult, ...]:
        diagnostic = TrackingDiagnostic(
            category=TrackingDiagnosticCategory.TIMEOUT,
            http_status=None,
            retryable=True,
            safe_detail="provider timed out",
        )
        raise TrackingProviderError(
            TrackingDiagnosticCategory.TIMEOUT,
            retryable=True,
            diagnostic=diagnostic,
        )

    ap = FakeProvider(CarrierProvider.AUSTRALIA_POST, "provider-australia_post-rev-1", fail)
    st = FakeProvider(CarrierProvider.STARTRACK, "provider-startrack-rev-1", available)
    mappings = (
        ("GROUP-1", config(CarrierProvider.AUSTRALIA_POST, group_id="GROUP-1")),
        ("GROUP-2", config(CarrierProvider.STARTRACK, group_id="GROUP-2")),
    )

    results = service_for(release(*mappings), ap, st).track_order((group(1), group(2)))

    assert results[0].reason_code is TrackingReasonCode.PROVIDER_TIMEOUT
    assert results[1].status is ResultStatus.AVAILABLE


def test_missing_adapter_is_unsupported_without_provider_call() -> None:
    configuration = config(CarrierProvider.TNT, group_id="GROUP-1")
    result = service_for(release(("GROUP-1", configuration))).track_order((group(1),))[0]

    assert result.status is ResultStatus.UNSUPPORTED
    assert result.reason_code is TrackingReasonCode.CARRIER_NOT_IMPLEMENTED
    assert result.events == ()


def test_implemented_adapter_with_missing_runtime_configuration_is_unavailable() -> None:
    configuration = config(CarrierProvider.AUSTRALIA_POST, group_id="GROUP-1")
    service = TrackingService(
        StaticTrackingConfigurationReader(release(("GROUP-1", configuration))),
        StaticTrackingProviderRegistry(
            implemented_adapter_keys=frozenset({"australia_post-track-v1"})
        ),
        clock=lambda: NOW,
    )

    result = service.track_order((group(1),))[0]

    assert result.status is ResultStatus.UNAVAILABLE
    assert result.reason_code is TrackingReasonCode.PROVIDER_CONFIGURATION_MISSING
    assert result.provider is CarrierProvider.AUSTRALIA_POST


def test_missing_release_projects_mapping_unresolved_for_every_group() -> None:
    service = TrackingService(
        StaticTrackingConfigurationReader(None),
        StaticTrackingProviderRegistry(),
        clock=lambda: NOW,
    )

    results = service.track_order((group(1), group(2)))

    assert [result.tracking_group_id for result in results] == ["GROUP-1", "GROUP-2"]
    for result in results:
        assert result.provider is None
        assert result.status is ResultStatus.UNAVAILABLE
        assert result.reason_code is TrackingReasonCode.CARRIER_MAPPING_UNRESOLVED
        assert result.events == ()
        assert result.latest_event_at is None


def test_unresolved_mapping_returns_provider_null_unavailable_without_guessing_provider() -> None:
    unrelated = config(CarrierProvider.AUSTRALIA_POST, group_id="GROUP-2")
    service = service_for(release(("GROUP-2", unrelated)))

    result = service.track_order((group(1),))[0]

    assert result.tracking_group_id == "GROUP-1"
    assert result.provider is None
    assert result.status is ResultStatus.UNAVAILABLE
    assert result.reason_code is TrackingReasonCode.CARRIER_MAPPING_UNRESOLVED
    assert "SYNTHETIC-ID" not in repr(result)


def test_mapping_failure_never_calls_a_provider_and_keeps_mapped_sibling() -> None:
    ap = FakeProvider(CarrierProvider.AUSTRALIA_POST, "provider-australia_post-rev-1", available)
    mapping = config(CarrierProvider.AUSTRALIA_POST, group_id="GROUP-1")

    results = service_for(release(("GROUP-1", mapping)), ap).track_order((group(1), group(2)))

    assert len(ap.calls) == 1
    assert [request.tracking_group_id for request in ap.calls[0]] == ["GROUP-1"]
    assert results[0].status is ResultStatus.AVAILABLE
    assert results[0].provider is CarrierProvider.AUSTRALIA_POST
    assert results[1].provider is None
    assert results[1].reason_code is TrackingReasonCode.CARRIER_MAPPING_UNRESOLVED


def test_ambiguous_mapping_selection_is_mapping_unresolved_without_provider_call() -> None:
    configuration = config(CarrierProvider.AUSTRALIA_POST, group_id="GROUP-1")
    provider = FakeProvider(
        CarrierProvider.AUSTRALIA_POST, "provider-australia_post-rev-1", available
    )
    # Bypass release validation to model a corrupted/ambiguous publication.
    duplicated = ResolvedTrackingMapping(
        tracking_group_id="GROUP-1",
        configuration=configuration,
        resolved_at=NOW,
    )
    base_release = release(("GROUP-1", configuration))
    ambiguous = TrackingConfigurationRelease.model_construct(
        release_revision_id="release-rev-1",
        environment=ProviderEnvironment.TESTBED,
        configuration_scope="order-tracking",
        provider_revisions=base_release.provider_revisions,
        account_revisions=base_release.account_revisions,
        product_revisions=base_release.product_revisions,
        mapping_revisions=base_release.mapping_revisions,
        mappings=(duplicated, duplicated),
        captured_at=NOW,
    )

    result = service_for(ambiguous, provider).track_order((group(1),))[0]

    assert provider.calls == []
    assert result.provider is None
    assert result.status is ResultStatus.UNAVAILABLE
    assert result.reason_code is TrackingReasonCode.CARRIER_MAPPING_UNRESOLVED


def test_no_tracking_groups_yields_no_results() -> None:
    service = TrackingService(
        StaticTrackingConfigurationReader(None),
        StaticTrackingProviderRegistry(),
        clock=lambda: NOW,
    )

    assert service.track_order(()) == ()


def test_valid_empty_event_result_is_available_not_unavailable() -> None:
    provider = FakeProvider(
        CarrierProvider.AUSTRALIA_POST,
        "provider-australia_post-rev-1",
        available,
    )
    mapping = config(CarrierProvider.AUSTRALIA_POST, group_id="GROUP-1")

    result = service_for(release(("GROUP-1", mapping)), provider).track_order((group(1),))[0]

    assert result.status is ResultStatus.AVAILABLE
    assert result.events == ()
    assert result.latest_event_at is None
