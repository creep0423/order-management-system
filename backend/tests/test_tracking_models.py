"""Contract tests for immutable tracking domain models."""

from datetime import UTC, datetime, timedelta, timezone

import pytest
from pydantic import SecretStr, ValidationError

from backend.models import (
    CarrierProvider,
    NormalizedTrackingStatus,
    ProviderConfiguration,
    ProviderCredentials,
    ProviderEnvironment,
    ProviderTrackingResult,
    ResultStatus,
    TrackingDiagnostic,
    TrackingDiagnosticCategory,
    TrackingEvent,
    TrackingReasonCode,
    TrackingRequest,
    TrackingResult,
)

NOW = datetime(2026, 11, 8, 1, 2, tzinfo=UTC)


def test_tracking_request_hides_id_and_requires_utc() -> None:
    request = TrackingRequest(
        tracking_group_id="GROUP-SYNTHETIC",
        provider=CarrierProvider.AUSTRALIA_POST,
        tracking_id="SYNTHETIC-TRACKING-ID",
        requested_at=NOW,
    )

    assert "SYNTHETIC-TRACKING-ID" not in repr(request)
    with pytest.raises(ValidationError, match="requested_at must use UTC"):
        TrackingRequest(
            tracking_group_id="GROUP-SYNTHETIC",
            provider=CarrierProvider.AUSTRALIA_POST,
            tracking_id="SYNTHETIC-TRACKING-ID",
            requested_at=datetime(2026, 11, 8, 11, 2, tzinfo=timezone(timedelta(hours=10))),
        )


def test_available_tracking_preserves_unknown_raw_status_and_real_events() -> None:
    event = TrackingEvent(
        event_time=NOW,
        location=None,
        description="Synthetic carrier event",
        provider_status=None,
        normalized_status=NormalizedTrackingStatus.UNKNOWN,
    )
    result = TrackingResult(
        tracking_group_id="GROUP-SYNTHETIC",
        provider=CarrierProvider.STARTRACK,
        status=ResultStatus.AVAILABLE,
        reason_code=None,
        checked_at=NOW,
        provider_status="New provider state",
        current_status=NormalizedTrackingStatus.UNKNOWN,
        latest_event_at=NOW,
        events=(event,),
    )

    assert result.provider_status == "New provider state"
    assert result.current_status is NormalizedTrackingStatus.UNKNOWN
    with pytest.raises(ValidationError, match="latest_event_at"):
        TrackingResult(**{**result.model_dump(), "latest_event_at": None})


@pytest.mark.parametrize(
    ("status", "reason"),
    [
        (ResultStatus.AVAILABLE, TrackingReasonCode.PROVIDER_TIMEOUT),
        (ResultStatus.UNAVAILABLE, None),
        (ResultStatus.UNSUPPORTED, TrackingReasonCode.PROVIDER_TIMEOUT),
        (ResultStatus.UNAVAILABLE, TrackingReasonCode.CARRIER_NOT_IMPLEMENTED),
    ],
)
def test_tracking_result_rejects_invalid_status_reason_combinations(
    status: ResultStatus,
    reason: TrackingReasonCode | None,
) -> None:
    with pytest.raises(ValidationError):
        TrackingResult(
            tracking_group_id="GROUP-SYNTHETIC",
            provider=CarrierProvider.TNT,
            status=status,
            reason_code=reason,
            checked_at=NOW,
            provider_status=None,
            current_status=None,
            latest_event_at=None,
            events=(),
        )


def test_tracking_result_accepts_d031_mapping_unresolved_provider_null() -> None:
    result = TrackingResult(
        tracking_group_id="GROUP-SYNTHETIC",
        provider=None,
        status=ResultStatus.UNAVAILABLE,
        reason_code=TrackingReasonCode.CARRIER_MAPPING_UNRESOLVED,
        checked_at=NOW,
        provider_status=None,
        current_status=None,
        latest_event_at=None,
        events=(),
    )

    assert result.provider is None
    assert result.status is ResultStatus.UNAVAILABLE
    assert result.reason_code is TrackingReasonCode.CARRIER_MAPPING_UNRESOLVED
    assert result.events == ()


@pytest.mark.parametrize(
    ("status", "reason"),
    [
        (ResultStatus.AVAILABLE, None),
        (ResultStatus.UNSUPPORTED, TrackingReasonCode.CARRIER_NOT_IMPLEMENTED),
        (ResultStatus.UNAVAILABLE, TrackingReasonCode.PROVIDER_TIMEOUT),
        (ResultStatus.UNAVAILABLE, TrackingReasonCode.PROVIDER_ERROR),
        (ResultStatus.UNAVAILABLE, TrackingReasonCode.PROVIDER_CONFIGURATION_MISSING),
        (ResultStatus.UNAVAILABLE, None),
    ],
)
def test_tracking_result_rejects_provider_null_outside_d031_combination(
    status: ResultStatus,
    reason: TrackingReasonCode | None,
) -> None:
    with pytest.raises(ValidationError, match="provider"):
        TrackingResult(
            tracking_group_id="GROUP-SYNTHETIC",
            provider=None,
            status=status,
            reason_code=reason,
            checked_at=NOW,
            provider_status=None,
            current_status=None,
            latest_event_at=None,
            events=(),
        )


def test_tracking_result_rejects_named_provider_for_mapping_unresolved() -> None:
    with pytest.raises(ValidationError, match="CARRIER_MAPPING_UNRESOLVED"):
        TrackingResult(
            tracking_group_id="GROUP-SYNTHETIC",
            provider=CarrierProvider.AUSTRALIA_POST,
            status=ResultStatus.UNAVAILABLE,
            reason_code=TrackingReasonCode.CARRIER_MAPPING_UNRESOLVED,
            checked_at=NOW,
            provider_status=None,
            current_status=None,
            latest_event_at=None,
            events=(),
        )


@pytest.mark.parametrize(
    ("provider", "status", "reason"),
    [
        (
            CarrierProvider.AUSTRALIA_POST,
            ResultStatus.UNAVAILABLE,
            TrackingReasonCode.PROVIDER_TIMEOUT,
        ),
        (
            CarrierProvider.STARTRACK,
            ResultStatus.UNAVAILABLE,
            TrackingReasonCode.PROVIDER_CONFIGURATION_MISSING,
        ),
        (
            CarrierProvider.TNT,
            ResultStatus.UNSUPPORTED,
            TrackingReasonCode.CARRIER_NOT_IMPLEMENTED,
        ),
    ],
)
def test_tracking_result_keeps_named_provider_for_non_mapping_failures(
    provider: CarrierProvider,
    status: ResultStatus,
    reason: TrackingReasonCode,
) -> None:
    result = TrackingResult(
        tracking_group_id="GROUP-SYNTHETIC",
        provider=provider,
        status=status,
        reason_code=reason,
        checked_at=NOW,
        provider_status=None,
        current_status=None,
        latest_event_at=None,
        events=(),
    )

    assert result.provider is provider


def test_failed_provider_result_contains_only_internal_safe_diagnostic() -> None:
    marker = "SYNTHETIC-SECRET-MARKER"
    diagnostic = TrackingDiagnostic(
        category=TrackingDiagnosticCategory.AUTHENTICATION,
        provider_code="AUTH-001",
        http_status=401,
        retryable=False,
        safe_detail=marker,
        item_index=0,
    )
    result = ProviderTrackingResult(
        request_item_index=0,
        error_category=TrackingDiagnosticCategory.AUTHENTICATION,
        diagnostic=diagnostic,
    )

    assert marker not in repr(result)
    with pytest.raises(ValidationError, match="failed provider result"):
        ProviderTrackingResult(
            request_item_index=0,
            provider_status="Delivered",
            error_category=TrackingDiagnosticCategory.PROVIDER,
            diagnostic=diagnostic,
        )


def test_provider_configuration_validates_provider_account_and_masks_secrets() -> None:
    config = ProviderConfiguration(
        release_revision_id="release-rev-1",
        mapping_revision_id="mapping-rev-1",
        provider_revision_id="provider-rev-1",
        account_revision_id="account-rev-1",
        product_revision_id="product-rev-1",
        provider=CarrierProvider.AUSTRALIA_POST,
        adapter_key="auspost-track-v1",
        environment=ProviderEnvironment.TESTBED,
        base_url="https://example.invalid/test/",
        credential_ref="credential-ref-1",
        connect_timeout_seconds=2.0,
        read_timeout_seconds=5.0,
        evidence_ref="official-contract-test-evidence",
    )

    assert "credential-ref-1" not in repr(config)
    assert config.base_url == "https://example.invalid/test"

    with pytest.raises(ValidationError, match="credential-free HTTPS"):
        ProviderConfiguration(
            **{
                **config.model_dump(),
                "base_url": "https://username:password@example.invalid/test",
            }
        )

    with pytest.raises(ValidationError, match="account number"):
        ProviderCredentials(
            provider=CarrierProvider.AUSTRALIA_POST,
            api_key=SecretStr("SYNTHETIC-KEY"),
            api_secret=SecretStr("SYNTHETIC-SECRET"),
            account_number=SecretStr("123"),
        )
