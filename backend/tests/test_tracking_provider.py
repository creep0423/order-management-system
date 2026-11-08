"""Offline contract tests for Australia Post API-family tracking adapters."""

import json
from datetime import UTC, datetime

import httpx
import pytest
from pydantic import SecretStr

from backend.integrations.tracking import (
    AustraliaPostTrackingProvider,
    HttpxTrackingTransport,
    InMemoryTrackingRateLimiter,
    StarTrackTrackingProvider,
    TrackingHttpRequest,
    TrackingHttpResponse,
    normalize_tracking_status,
)
from backend.models import (
    CarrierProvider,
    NormalizedTrackingStatus,
    ProviderConfiguration,
    ProviderCredentials,
    ProviderEnvironment,
    TrackingDiagnosticCategory,
    TrackingProviderError,
    TrackingRequest,
)

NOW = datetime(2026, 11, 8, 1, 2, tzinfo=UTC)


class FakeTransport:
    def __init__(self, status_code: int, payload: object) -> None:
        self.response = TrackingHttpResponse(
            status_code=status_code,
            content=(payload if isinstance(payload, bytes) else json.dumps(payload).encode()),
        )
        self.requests: list[TrackingHttpRequest] = []

    def get(self, request: TrackingHttpRequest) -> TrackingHttpResponse:
        self.requests.append(request)
        return self.response


def configuration(provider: CarrierProvider) -> ProviderConfiguration:
    return ProviderConfiguration(
        release_revision_id="release-rev-1",
        mapping_revision_id=f"mapping-{provider.value}-rev-1",
        provider_revision_id=f"provider-{provider.value}-rev-1",
        account_revision_id=f"account-{provider.value}-rev-1",
        product_revision_id=f"product-{provider.value}-rev-1",
        provider=provider,
        adapter_key=f"{provider.value}-track-v1",
        environment=ProviderEnvironment.TESTBED,
        base_url="https://example.invalid/test",
        credential_ref=f"credential-{provider.value}",
        connect_timeout_seconds=2.0,
        read_timeout_seconds=5.0,
        evidence_ref="official-track-items-contract",
    )


def credentials(provider: CarrierProvider) -> ProviderCredentials:
    return ProviderCredentials(
        provider=provider,
        api_key=SecretStr("SYNTHETIC-KEY"),
        api_secret=SecretStr("SYNTHETIC-SECRET"),
        account_number=SecretStr(
            "0001234567" if provider is CarrierProvider.AUSTRALIA_POST else "12345678"
        ),
    )


def request(provider: CarrierProvider, suffix: int = 1) -> TrackingRequest:
    return TrackingRequest(
        tracking_group_id=f"GROUP-{suffix}",
        provider=provider,
        tracking_id=f"SYNTHETIC-ID-{suffix}",
        requested_at=NOW,
    )


def test_australia_post_adapter_maps_raw_status_and_real_events() -> None:
    transport = FakeTransport(
        200,
        {
            "tracking_results": [
                {
                    "tracking_id": "SYNTHETIC-ID-1",
                    "status": "In transit",
                    "trackable_items": [
                        {
                            "article_id": "SYNTHETIC-ARTICLE",
                            "events": [
                                {
                                    "location": "SYNTHETIC FACILITY",
                                    "description": "Synthetic scanned event",
                                    "date": "2026-11-08T10:30:00+10:00",
                                }
                            ],
                        }
                    ],
                }
            ]
        },
    )
    adapter = AustraliaPostTrackingProvider(
        configuration(CarrierProvider.AUSTRALIA_POST),
        credentials(CarrierProvider.AUSTRALIA_POST),
        transport,
        rate_limiter=InMemoryTrackingRateLimiter(),
    )

    result = adapter.track((request(CarrierProvider.AUSTRALIA_POST),))[0]

    assert result.provider_status == "In transit"
    assert result.current_status is NormalizedTrackingStatus.IN_TRANSIT
    assert result.latest_event_at == datetime(2026, 11, 8, 0, 30, tzinfo=UTC)
    assert result.events[0].normalized_status is NormalizedTrackingStatus.UNKNOWN
    assert result.events[0].provider_status is None
    sent = transport.requests[0]
    assert sent.params == {"tracking_ids": "SYNTHETIC-ID-1"}
    assert sent.url == "https://example.invalid/test/shipping/v1/track"
    assert "SYNTHETIC-KEY" not in repr(sent)
    assert "SYNTHETIC-SECRET" not in repr(sent)
    assert "0001234567" not in repr(sent)
    assert "SYNTHETIC-ID-1" not in repr(sent)


def test_startrack_adapter_uses_consignment_status_without_guessing_event_status() -> None:
    transport = FakeTransport(
        200,
        {
            "tracking_results": [
                {
                    "tracking_id": "SYNTHETIC-ID-1",
                    "consignment": {
                        "status": "On Board for Delivery",
                        "events": [
                            {
                                "description": "Synthetic event description",
                                "date": "2026-11-08T00:00:00Z",
                            }
                        ],
                    },
                }
            ]
        },
    )
    adapter = StarTrackTrackingProvider(
        configuration(CarrierProvider.STARTRACK),
        credentials(CarrierProvider.STARTRACK),
        transport,
        rate_limiter=InMemoryTrackingRateLimiter(),
    )

    result = adapter.track((request(CarrierProvider.STARTRACK),))[0]

    assert result.provider_status == "On Board for Delivery"
    assert result.current_status is NormalizedTrackingStatus.OUT_FOR_DELIVERY
    assert result.events[0].normalized_status is NormalizedTrackingStatus.UNKNOWN


def test_unknown_provider_status_is_preserved_and_normalized_to_unknown() -> None:
    assert (
        normalize_tracking_status(CarrierProvider.AUSTRALIA_POST, "New status from provider")
        is NormalizedTrackingStatus.UNKNOWN
    )


@pytest.mark.parametrize(
    ("provider", "raw_status", "expected"),
    [
        (CarrierProvider.AUSTRALIA_POST, "Created", NormalizedTrackingStatus.PENDING),
        (CarrierProvider.AUSTRALIA_POST, "In Transit", NormalizedTrackingStatus.IN_TRANSIT),
        (
            CarrierProvider.AUSTRALIA_POST,
            "Awaiting Collection",
            NormalizedTrackingStatus.AWAITING_COLLECTION,
        ),
        # StarTrack-only raw values must not leak into the Australia Post mapping.
        (CarrierProvider.AUSTRALIA_POST, "On Board for Delivery", NormalizedTrackingStatus.UNKNOWN),
        (
            CarrierProvider.STARTRACK,
            "On Board for Delivery",
            NormalizedTrackingStatus.OUT_FOR_DELIVERY,
        ),
        (CarrierProvider.STARTRACK, "Ready for Pickup", NormalizedTrackingStatus.READY_FOR_PICKUP),
        # Australia Post-only raw values must not leak into the StarTrack mapping.
        (CarrierProvider.STARTRACK, "Held by Courier", NormalizedTrackingStatus.UNKNOWN),
        # TNT has no approved raw-status mapping and must stay unknown.
        (CarrierProvider.TNT, "In Transit", NormalizedTrackingStatus.UNKNOWN),
        (CarrierProvider.TNT, "Delivered", NormalizedTrackingStatus.UNKNOWN),
    ],
)
def test_status_normalization_uses_only_the_matching_provider_table(
    provider: CarrierProvider,
    raw_status: str,
    expected: NormalizedTrackingStatus,
) -> None:
    assert normalize_tracking_status(provider, raw_status) is expected


def test_unrecognised_provider_falls_back_to_unknown_without_guessing() -> None:
    unmapped_provider = "unapproved_carrier"

    assert (
        normalize_tracking_status(unmapped_provider, "Delivered")  # type: ignore[arg-type]
        is NormalizedTrackingStatus.UNKNOWN
    )


@pytest.mark.parametrize(
    ("provider_code", "category"),
    [
        ("ESB-10001", TrackingDiagnosticCategory.INVALID_REQUEST),
        ("ESB-10002", TrackingDiagnosticCategory.PRODUCT_NOT_TRACKABLE),
        ("ESB-20010", TrackingDiagnosticCategory.PROVIDER),
    ],
)
def test_http_200_item_errors_remain_classified_internal_failures(
    provider_code: str,
    category: TrackingDiagnosticCategory,
) -> None:
    transport = FakeTransport(
        200,
        {
            "tracking_results": [
                {
                    "tracking_id": "SYNTHETIC-ID-1",
                    "errors": [{"code": provider_code, "name": "Synthetic error"}],
                }
            ]
        },
    )
    adapter = AustraliaPostTrackingProvider(
        configuration(CarrierProvider.AUSTRALIA_POST),
        credentials(CarrierProvider.AUSTRALIA_POST),
        transport,
        rate_limiter=InMemoryTrackingRateLimiter(),
    )

    result = adapter.track((request(CarrierProvider.AUSTRALIA_POST),))[0]

    assert result.error_category is category
    assert result.diagnostic is not None
    assert result.diagnostic.provider_code == provider_code
    assert result.events == ()


@pytest.mark.parametrize(
    ("status_code", "category", "retryable"),
    [
        (401, TrackingDiagnosticCategory.AUTHENTICATION, False),
        (403, TrackingDiagnosticCategory.AUTHENTICATION, False),
        (429, TrackingDiagnosticCategory.RATE_LIMIT, True),
        (503, TrackingDiagnosticCategory.PROVIDER, True),
        (400, TrackingDiagnosticCategory.PROVIDER, False),
    ],
)
def test_http_failures_are_stably_classified(
    status_code: int,
    category: TrackingDiagnosticCategory,
    retryable: bool,
) -> None:
    adapter = AustraliaPostTrackingProvider(
        configuration(CarrierProvider.AUSTRALIA_POST),
        credentials(CarrierProvider.AUSTRALIA_POST),
        FakeTransport(status_code, {"errors": [{"message": "SENSITIVE RAW ERROR"}]}),
        rate_limiter=InMemoryTrackingRateLimiter(),
    )

    with pytest.raises(TrackingProviderError) as captured:
        adapter.track((request(CarrierProvider.AUSTRALIA_POST),))

    assert captured.value.category is category
    assert captured.value.retryable is retryable
    assert "SENSITIVE RAW ERROR" not in str(captured.value)


@pytest.mark.parametrize("payload", [b"not-json", {"tracking_results": [{}]}])
def test_invalid_provider_payload_is_rejected_without_raw_echo(payload: object) -> None:
    marker = b"not-json" if isinstance(payload, bytes) else b"tracking_results"
    adapter = AustraliaPostTrackingProvider(
        configuration(CarrierProvider.AUSTRALIA_POST),
        credentials(CarrierProvider.AUSTRALIA_POST),
        FakeTransport(200, payload),
        rate_limiter=InMemoryTrackingRateLimiter(),
    )

    with pytest.raises(TrackingProviderError) as captured:
        adapter.track((request(CarrierProvider.AUSTRALIA_POST),))

    assert captured.value.category is TrackingDiagnosticCategory.INVALID_RESPONSE
    assert marker.decode() not in str(captured.value)


def test_adapter_rejects_mixed_or_oversized_batches_before_transport() -> None:
    transport = FakeTransport(200, {"tracking_results": []})
    adapter = AustraliaPostTrackingProvider(
        configuration(CarrierProvider.AUSTRALIA_POST),
        credentials(CarrierProvider.AUSTRALIA_POST),
        transport,
        rate_limiter=InMemoryTrackingRateLimiter(),
    )

    mixed = (
        request(CarrierProvider.AUSTRALIA_POST),
        request(CarrierProvider.STARTRACK, 2),
    )
    with pytest.raises(ValueError, match="mix"):
        adapter.track(mixed)
    with pytest.raises(ValueError, match="between 1 and 10"):
        adapter.track(tuple(request(CarrierProvider.AUSTRALIA_POST, i) for i in range(11)))
    assert transport.requests == []


def test_local_rate_guard_prevents_an_eleventh_request_in_the_window() -> None:
    transport = FakeTransport(
        200,
        {"tracking_results": [{"tracking_id": "SYNTHETIC-ID-1", "status": "In transit"}]},
    )
    limiter = InMemoryTrackingRateLimiter(max_requests=10, window_seconds=60, clock=lambda: 1.0)
    adapter = AustraliaPostTrackingProvider(
        configuration(CarrierProvider.AUSTRALIA_POST),
        credentials(CarrierProvider.AUSTRALIA_POST),
        transport,
        rate_limiter=limiter,
    )

    for _ in range(10):
        adapter.track((request(CarrierProvider.AUSTRALIA_POST),))
    with pytest.raises(TrackingProviderError) as captured:
        adapter.track((request(CarrierProvider.AUSTRALIA_POST),))

    assert captured.value.category is TrackingDiagnosticCategory.RATE_LIMIT
    assert len(transport.requests) == 10


def test_default_rate_guard_is_shared_by_provider_account_revision() -> None:
    transport = FakeTransport(
        200,
        {"tracking_results": [{"tracking_id": "SYNTHETIC-ID-1", "status": "In transit"}]},
    )
    base = configuration(CarrierProvider.AUSTRALIA_POST)
    shared_config = ProviderConfiguration(
        **{**base.model_dump(), "provider_revision_id": "provider-shared-rate-test"}
    )
    first = AustraliaPostTrackingProvider(
        shared_config,
        credentials(CarrierProvider.AUSTRALIA_POST),
        transport,
    )
    second = AustraliaPostTrackingProvider(
        shared_config,
        credentials(CarrierProvider.AUSTRALIA_POST),
        transport,
    )

    for _ in range(5):
        first.track((request(CarrierProvider.AUSTRALIA_POST),))
        second.track((request(CarrierProvider.AUSTRALIA_POST),))
    with pytest.raises(TrackingProviderError) as captured:
        second.track((request(CarrierProvider.AUSTRALIA_POST),))

    assert captured.value.category is TrackingDiagnosticCategory.RATE_LIMIT
    assert len(transport.requests) == 10


def _http_request(max_response_bytes: int = 1_000) -> TrackingHttpRequest:
    return TrackingHttpRequest(
        url="https://example.invalid/shipping/v1/track",
        params={"tracking_ids": "SYNTHETIC-SENSITIVE-ID"},
        headers={"Accept": "application/json", "Account-Number": "0001234567"},
        auth=("SYNTHETIC-KEY", "SYNTHETIC-SECRET"),
        connect_timeout_seconds=1.0,
        read_timeout_seconds=1.0,
        max_response_bytes=max_response_bytes,
    )


def test_http_transport_classifies_timeout_without_sensitive_exception_chain() -> None:
    def timeout(request: httpx.Request) -> httpx.Response:
        raise httpx.ReadTimeout("SYNTHETIC-SENSITIVE-ID", request=request)

    transport = HttpxTrackingTransport(httpx.Client(transport=httpx.MockTransport(timeout)))

    with pytest.raises(TrackingProviderError) as captured:
        transport.get(_http_request())

    assert captured.value.category is TrackingDiagnosticCategory.TIMEOUT
    assert captured.value.__cause__ is None
    assert "SYNTHETIC-SENSITIVE-ID" not in str(captured.value)


def test_http_transport_rejects_oversized_response_without_body_echo() -> None:
    def oversized(_request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, content=b"SYNTHETIC-RAW-BODY", headers={"content-length": "18"})

    transport = HttpxTrackingTransport(httpx.Client(transport=httpx.MockTransport(oversized)))

    with pytest.raises(TrackingProviderError) as captured:
        transport.get(_http_request(max_response_bytes=10))

    assert captured.value.category is TrackingDiagnosticCategory.INVALID_RESPONSE
    assert "SYNTHETIC-RAW-BODY" not in str(captured.value)


def test_http_transport_stops_chunked_response_at_size_limit() -> None:
    class OversizedStream(httpx.SyncByteStream):
        def __iter__(self):  # type: ignore[no-untyped-def]
            yield b"SYNTHETIC"
            yield b"-RAW-BODY"

    def oversized(_request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, stream=OversizedStream())

    transport = HttpxTrackingTransport(httpx.Client(transport=httpx.MockTransport(oversized)))

    with pytest.raises(TrackingProviderError) as captured:
        transport.get(_http_request(max_response_bytes=10))

    assert captured.value.category is TrackingDiagnosticCategory.INVALID_RESPONSE
    assert "SYNTHETIC-RAW-BODY" not in str(captured.value)
