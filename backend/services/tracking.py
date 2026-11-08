"""Tracking orchestration over explicit configuration and provider adapters."""

from __future__ import annotations

from collections import defaultdict
from collections.abc import Callable
from datetime import UTC, datetime
from typing import Protocol

from backend.integrations.tracking import MAX_TRACKING_IDS_PER_REQUEST, TrackingProvider
from backend.models import (
    CarrierProvider,
    ProviderTrackingResult,
    ResolvedTrackingMapping,
    ResultStatus,
    TrackingConfigurationRelease,
    TrackingDiagnosticCategory,
    TrackingGroup,
    TrackingProviderError,
    TrackingReasonCode,
    TrackingRequest,
    TrackingResult,
)


class TrackingConfigurationError(Exception):
    """Safe configuration failure that never retains credentials or group payloads."""

    def __init__(self, reason_code: TrackingReasonCode) -> None:
        self.reason_code = reason_code
        super().__init__("tracking configuration is unavailable")


def mapping_unresolved_result(tracking_group_id: str, checked_at: datetime) -> TrackingResult:
    """Project the single public result D-031 allows when no provider can be named."""

    return TrackingResult(
        tracking_group_id=tracking_group_id,
        provider=None,
        status=ResultStatus.UNAVAILABLE,
        reason_code=TrackingReasonCode.CARRIER_MAPPING_UNRESOLVED,
        checked_at=checked_at,
        provider_status=None,
        current_status=None,
        latest_event_at=None,
        events=(),
    )


class TrackingConfigurationReader(Protocol):
    def get_active(self, at: datetime) -> TrackingConfigurationRelease: ...


class TrackingProviderRegistry(Protocol):
    def get(self, configuration_key: tuple[str, str, str]) -> TrackingProvider | None: ...

    def is_implemented(self, adapter_key: str) -> bool: ...


class StaticTrackingConfigurationReader:
    """Read-only release reader used after an approved release has been published."""

    def __init__(self, release: TrackingConfigurationRelease | None) -> None:
        self._release = release

    def get_active(self, at: datetime) -> TrackingConfigurationRelease:
        del at
        if self._release is None:
            raise TrackingConfigurationError(TrackingReasonCode.PROVIDER_CONFIGURATION_MISSING)
        return self._release


class StaticTrackingProviderRegistry:
    def __init__(
        self,
        providers: tuple[TrackingProvider, ...] = (),
        implemented_adapter_keys: frozenset[str] = frozenset(),
    ) -> None:
        self._providers = {provider.configuration_key: provider for provider in providers}
        if len(self._providers) != len(providers):
            raise ValueError("provider/account configuration keys must be unique")
        self._implemented_adapter_keys = implemented_adapter_keys | frozenset(
            provider.adapter_key for provider in providers
        )

    def get(self, configuration_key: tuple[str, str, str]) -> TrackingProvider | None:
        return self._providers.get(configuration_key)

    def is_implemented(self, adapter_key: str) -> bool:
        return adapter_key in self._implemented_adapter_keys


def _reason_for_category(category: TrackingDiagnosticCategory) -> TrackingReasonCode:
    return {
        TrackingDiagnosticCategory.CONFIGURATION: (
            TrackingReasonCode.PROVIDER_CONFIGURATION_MISSING
        ),
        TrackingDiagnosticCategory.AUTHENTICATION: (
            TrackingReasonCode.PROVIDER_AUTHENTICATION_FAILED
        ),
        TrackingDiagnosticCategory.TIMEOUT: TrackingReasonCode.PROVIDER_TIMEOUT,
        TrackingDiagnosticCategory.NETWORK: TrackingReasonCode.PROVIDER_NETWORK_ERROR,
        TrackingDiagnosticCategory.RATE_LIMIT: TrackingReasonCode.PROVIDER_RATE_LIMITED,
        TrackingDiagnosticCategory.INVALID_REQUEST: TrackingReasonCode.TRACKING_ID_INVALID,
        TrackingDiagnosticCategory.INVALID_RESPONSE: (TrackingReasonCode.PROVIDER_RESPONSE_INVALID),
        TrackingDiagnosticCategory.PRODUCT_NOT_TRACKABLE: (
            TrackingReasonCode.PRODUCT_NOT_TRACKABLE
        ),
        TrackingDiagnosticCategory.PROVIDER: TrackingReasonCode.PROVIDER_ERROR,
    }[category]


class TrackingService:
    """Resolve, batch, call and normalize one result per unique tracking group."""

    def __init__(
        self,
        configuration_reader: TrackingConfigurationReader,
        provider_registry: TrackingProviderRegistry,
        clock: Callable[[], datetime] | None = None,
    ) -> None:
        self._configuration_reader = configuration_reader
        self._provider_registry = provider_registry
        self._clock = clock or (lambda: datetime.now(UTC))

    def track_order(self, groups: tuple[TrackingGroup, ...]) -> tuple[TrackingResult, ...]:
        unique_groups = tuple({group.tracking_group_id: group for group in groups}.values())
        if not unique_groups:
            return ()

        requested_at = self._clock()
        try:
            release = self._configuration_reader.get_active(requested_at)
        except TrackingConfigurationError:
            # D-031: no usable Active Release means the applicable mapping cannot
            # be resolved. That is a real per-group unavailable, never an order-
            # level exception and never a provider request.
            checked_at = self._clock()
            return tuple(
                mapping_unresolved_result(group.tracking_group_id, checked_at)
                for group in unique_groups
            )

        matches_by_group: dict[str, list[ResolvedTrackingMapping]] = defaultdict(list)
        for mapping in release.mappings:
            matches_by_group[mapping.tracking_group_id].append(mapping)

        output: dict[int, TrackingResult] = {}
        resolved: list[tuple[int, TrackingGroup, ResolvedTrackingMapping]] = []
        preflight_checked_at = self._clock()
        for index, group in enumerate(unique_groups):
            matches = matches_by_group.get(group.tracking_group_id, [])
            if len(matches) != 1:
                # Zero or multiple applicable mappings are CARRIER_MAPPING_UNRESOLVED.
                output[index] = mapping_unresolved_result(
                    group.tracking_group_id, preflight_checked_at
                )
                continue
            resolved.append((index, group, matches[0]))

        batches: dict[
            tuple[str, str, str], list[tuple[int, TrackingGroup, ResolvedTrackingMapping]]
        ] = defaultdict(list)
        for item in resolved:
            config = item[2].configuration
            configuration_key = (
                config.provider_revision_id,
                config.account_revision_id,
                config.product_revision_id,
            )
            batches[configuration_key].append(item)

        for configuration_key, items in batches.items():
            provider = self._provider_registry.get(configuration_key)
            config = items[0][2].configuration
            if provider is None:
                checked_at = self._clock()
                implemented = self._provider_registry.is_implemented(config.adapter_key)
                for index, group, _mapping in items:
                    output[index] = self._failed_result(
                        group,
                        config.provider,
                        ResultStatus.UNAVAILABLE if implemented else ResultStatus.UNSUPPORTED,
                        TrackingReasonCode.PROVIDER_CONFIGURATION_MISSING
                        if implemented
                        else TrackingReasonCode.CARRIER_NOT_IMPLEMENTED,
                        checked_at,
                    )
                continue
            if provider.provider is not config.provider:
                checked_at = self._clock()
                for index, group, _mapping in items:
                    output[index] = self._failed_result(
                        group,
                        config.provider,
                        ResultStatus.UNAVAILABLE,
                        TrackingReasonCode.PROVIDER_CONFIGURATION_MISSING,
                        checked_at,
                    )
                continue

            by_tracking_id: dict[str, list[tuple[int, TrackingGroup, ResolvedTrackingMapping]]] = (
                defaultdict(list)
            )
            for item in items:
                by_tracking_id[item[1].tracking_number].append(item)
            deduplicated = tuple(by_tracking_id.values())

            for offset in range(0, len(deduplicated), MAX_TRACKING_IDS_PER_REQUEST):
                chunk = deduplicated[offset : offset + MAX_TRACKING_IDS_PER_REQUEST]
                requests = tuple(
                    TrackingRequest(
                        tracking_group_id=matching_items[0][1].tracking_group_id,
                        provider=config.provider,
                        tracking_id=matching_items[0][1].tracking_number,
                        requested_at=requested_at,
                    )
                    for matching_items in chunk
                )
                try:
                    provider_results = provider.track(requests)
                except TrackingProviderError as error:
                    checked_at = self._clock()
                    reason = _reason_for_category(error.category)
                    for matching_items in chunk:
                        for index, group, _mapping in matching_items:
                            output[index] = self._failed_result(
                                group,
                                config.provider,
                                ResultStatus.UNAVAILABLE,
                                reason,
                                checked_at,
                            )
                    continue
                if len(provider_results) != len(chunk):
                    checked_at = self._clock()
                    for matching_items in chunk:
                        for index, group, _mapping in matching_items:
                            output[index] = self._failed_result(
                                group,
                                config.provider,
                                ResultStatus.UNAVAILABLE,
                                TrackingReasonCode.PROVIDER_RESPONSE_INVALID,
                                checked_at,
                            )
                    continue
                checked_at = self._clock()
                for chunk_index, provider_result in enumerate(provider_results):
                    for index, group, _mapping in chunk[chunk_index]:
                        output[index] = self._to_tracking_result(
                            group,
                            config.provider,
                            provider_result,
                            checked_at,
                            chunk_index,
                        )

        return tuple(output[index] for index in range(len(unique_groups)))

    @staticmethod
    def _failed_result(
        group: TrackingGroup,
        provider: CarrierProvider,
        status: ResultStatus,
        reason: TrackingReasonCode,
        checked_at: datetime,
    ) -> TrackingResult:
        return TrackingResult(
            tracking_group_id=group.tracking_group_id,
            provider=provider,
            status=status,
            reason_code=reason,
            checked_at=checked_at,
            provider_status=None,
            current_status=None,
            latest_event_at=None,
            events=(),
        )

    def _to_tracking_result(
        self,
        group: TrackingGroup,
        provider: CarrierProvider,
        result: ProviderTrackingResult,
        checked_at: datetime,
        expected_index: int,
    ) -> TrackingResult:
        if result.request_item_index != expected_index:
            return self._failed_result(
                group,
                provider,
                ResultStatus.UNAVAILABLE,
                TrackingReasonCode.PROVIDER_RESPONSE_INVALID,
                checked_at,
            )
        if result.error_category is not None:
            return self._failed_result(
                group,
                provider,
                ResultStatus.UNAVAILABLE,
                _reason_for_category(result.error_category),
                checked_at,
            )
        return TrackingResult(
            tracking_group_id=group.tracking_group_id,
            provider=provider,
            status=ResultStatus.AVAILABLE,
            reason_code=None,
            checked_at=checked_at,
            provider_status=result.provider_status,
            current_status=result.current_status,
            latest_event_at=result.latest_event_at,
            events=result.events,
        )
