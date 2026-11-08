"""Australia Post API-family tracking adapters with an injectable HTTP transport."""

from __future__ import annotations

import json
import threading
import time
from collections import deque
from collections.abc import Mapping
from dataclasses import dataclass, field
from datetime import UTC
from typing import Protocol

import httpx
from pydantic import AwareDatetime, BaseModel, ConfigDict, Field, ValidationError, field_validator

from backend.models import (
    CarrierProvider,
    NormalizedTrackingStatus,
    ProviderConfiguration,
    ProviderCredentials,
    ProviderTrackingResult,
    TrackingDiagnostic,
    TrackingDiagnosticCategory,
    TrackingEvent,
    TrackingProviderError,
    TrackingRequest,
)

MAX_TRACKING_IDS_PER_REQUEST = 10
TRACK_PATH = "/shipping/v1/track"


class TrackingProvider(Protocol):
    @property
    def adapter_key(self) -> str: ...

    @property
    def configuration_key(self) -> tuple[str, str, str]: ...

    @property
    def provider_revision_id(self) -> str: ...

    @property
    def provider(self) -> CarrierProvider: ...

    def track(self, batch: tuple[TrackingRequest, ...]) -> tuple[ProviderTrackingResult, ...]: ...


@dataclass(frozen=True)
class TrackingHttpRequest:
    url: str
    params: Mapping[str, str] = field(repr=False)
    headers: Mapping[str, str] = field(repr=False)
    auth: tuple[str, str] = field(repr=False)
    connect_timeout_seconds: float
    read_timeout_seconds: float
    max_response_bytes: int


@dataclass(frozen=True)
class TrackingHttpResponse:
    status_code: int
    content: bytes = field(repr=False)


class TrackingHttpTransport(Protocol):
    def get(self, request: TrackingHttpRequest) -> TrackingHttpResponse: ...


class TrackingRateLimiter(Protocol):
    def try_acquire(self) -> bool: ...


class InMemoryTrackingRateLimiter:
    """Thread-safe single-process guard for the official 10 requests/minute limit."""

    def __init__(
        self,
        max_requests: int = 10,
        window_seconds: float = 60.0,
        clock=time.monotonic,
    ) -> None:
        if max_requests <= 0 or window_seconds <= 0:
            raise ValueError("rate limit parameters must be positive")
        self._max_requests = max_requests
        self._window_seconds = window_seconds
        self._clock = clock
        self._calls: deque[float] = deque()
        self._lock = threading.Lock()

    def try_acquire(self) -> bool:
        now = self._clock()
        cutoff = now - self._window_seconds
        with self._lock:
            while self._calls and self._calls[0] <= cutoff:
                self._calls.popleft()
            if len(self._calls) >= self._max_requests:
                return False
            self._calls.append(now)
            return True


_SHARED_RATE_LIMITERS: dict[tuple[str, str], InMemoryTrackingRateLimiter] = {}
_SHARED_RATE_LIMITERS_LOCK = threading.Lock()


def _shared_rate_limiter(config: ProviderConfiguration) -> InMemoryTrackingRateLimiter:
    key = (config.provider_revision_id, config.account_revision_id)
    with _SHARED_RATE_LIMITERS_LOCK:
        limiter = _SHARED_RATE_LIMITERS.get(key)
        if limiter is None:
            limiter = InMemoryTrackingRateLimiter()
            _SHARED_RATE_LIMITERS[key] = limiter
        return limiter


def _provider_error(
    category: TrackingDiagnosticCategory,
    *,
    retryable: bool,
    http_status: int | None = None,
    provider_code: str | None = None,
    safe_detail: str | None = None,
    item_index: int | None = None,
) -> TrackingProviderError:
    return TrackingProviderError(
        category,
        retryable=retryable,
        diagnostic=TrackingDiagnostic(
            category=category,
            provider_code=provider_code,
            http_status=http_status,
            retryable=retryable,
            safe_detail=safe_detail,
            item_index=item_index,
        ),
    )


class HttpxTrackingTransport:
    """Bounded production transport; it never logs or retains request secrets."""

    def __init__(self, client: httpx.Client | None = None) -> None:
        self._client = client or httpx.Client(follow_redirects=False)

    def get(self, request: TrackingHttpRequest) -> TrackingHttpResponse:
        timeout = httpx.Timeout(
            connect=request.connect_timeout_seconds,
            read=request.read_timeout_seconds,
            write=request.read_timeout_seconds,
            pool=request.connect_timeout_seconds,
        )
        try:
            with self._client.stream(
                "GET",
                request.url,
                params=request.params,
                headers=request.headers,
                auth=request.auth,
                timeout=timeout,
            ) as response:
                declared_length = response.headers.get("content-length")
                if declared_length is not None:
                    try:
                        parsed_length = int(declared_length)
                    except ValueError:
                        raise _provider_error(
                            TrackingDiagnosticCategory.INVALID_RESPONSE,
                            retryable=False,
                            http_status=response.status_code,
                            safe_detail="provider response content length was invalid",
                        ) from None
                    if parsed_length < 0 or parsed_length > request.max_response_bytes:
                        raise _provider_error(
                            TrackingDiagnosticCategory.INVALID_RESPONSE,
                            retryable=False,
                            http_status=response.status_code,
                            safe_detail="provider response exceeded size limit",
                        )

                content = bytearray()
                for chunk in response.iter_bytes():
                    if len(content) + len(chunk) > request.max_response_bytes:
                        raise _provider_error(
                            TrackingDiagnosticCategory.INVALID_RESPONSE,
                            retryable=False,
                            http_status=response.status_code,
                            safe_detail="provider response exceeded size limit",
                        )
                    content.extend(chunk)
                status_code = response.status_code
        except httpx.TimeoutException:
            raise _provider_error(
                TrackingDiagnosticCategory.TIMEOUT,
                retryable=True,
                safe_detail="provider request timed out",
            ) from None
        except httpx.NetworkError:
            raise _provider_error(
                TrackingDiagnosticCategory.NETWORK,
                retryable=True,
                safe_detail="provider network request failed",
            ) from None
        except httpx.HTTPError:
            raise _provider_error(
                TrackingDiagnosticCategory.NETWORK,
                retryable=False,
                safe_detail="provider HTTP request failed",
            ) from None
        return TrackingHttpResponse(status_code=status_code, content=bytes(content))


class _ProviderSourceModel(BaseModel):
    model_config = ConfigDict(extra="ignore", frozen=True)


class _ProviderErrorSource(_ProviderSourceModel):
    code: str | None = None
    error_code: str | None = None
    name: str | None = None
    error_name: str | None = None
    message: str | None = None


class _ProviderEventSource(_ProviderSourceModel):
    date: AwareDatetime
    description: str = Field(min_length=1, max_length=500)
    location: str | None = Field(default=None, max_length=500)

    @field_validator("description")
    @classmethod
    def description_must_not_be_blank(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("event description must not be blank")
        return value.strip()


class _TrackableItemSource(_ProviderSourceModel):
    status: str | None = Field(default=None, max_length=200)
    events: tuple[_ProviderEventSource, ...] = ()
    items: tuple[_TrackableItemSource, ...] = ()


class _ConsignmentSource(_ProviderSourceModel):
    status: str | None = Field(default=None, max_length=200)
    events: tuple[_ProviderEventSource, ...] = ()


class _TrackingResultSource(_ProviderSourceModel):
    tracking_id: str = Field(min_length=1, max_length=100, repr=False)
    errors: tuple[_ProviderErrorSource, ...] = ()
    status: str | None = Field(default=None, max_length=200)
    consignment: _ConsignmentSource | None = None
    trackable_items: tuple[_TrackableItemSource, ...] = ()


class _TrackingResponseSource(_ProviderSourceModel):
    tracking_results: tuple[_TrackingResultSource, ...]


AUSTRALIA_POST_STATUS_MAP: Mapping[str, NormalizedTrackingStatus] = {
    "created": NormalizedTrackingStatus.PENDING,
    "sealed": NormalizedTrackingStatus.PENDING,
    "initiated": NormalizedTrackingStatus.PENDING,
    "in transit": NormalizedTrackingStatus.IN_TRANSIT,
    "delivered": NormalizedTrackingStatus.DELIVERED,
    "awaiting collection": NormalizedTrackingStatus.AWAITING_COLLECTION,
    "possible delay": NormalizedTrackingStatus.DELIVERY_EXCEPTION,
    "unsuccessful pickup": NormalizedTrackingStatus.DELIVERY_EXCEPTION,
    "article damaged": NormalizedTrackingStatus.DELIVERY_EXCEPTION,
    "cancelled": NormalizedTrackingStatus.CANCELLED,
    "held by courier": NormalizedTrackingStatus.DELIVERY_EXCEPTION,
    "cannot be delivered": NormalizedTrackingStatus.DELIVERY_EXCEPTION,
}

STARTRACK_STATUS_MAP: Mapping[str, NormalizedTrackingStatus] = {
    "confirmed": NormalizedTrackingStatus.PENDING,
    "incomplete": NormalizedTrackingStatus.PENDING,
    "unconfirmed": NormalizedTrackingStatus.PENDING,
    "deleted": NormalizedTrackingStatus.CANCELLED,
    "delivered in full": NormalizedTrackingStatus.DELIVERED,
    "item delivered": NormalizedTrackingStatus.DELIVERED,
    "final shortage": NormalizedTrackingStatus.DELIVERY_EXCEPTION,
    "in transit": NormalizedTrackingStatus.IN_TRANSIT,
    "on board for delivery": NormalizedTrackingStatus.OUT_FOR_DELIVERY,
    "picked up": NormalizedTrackingStatus.IN_TRANSIT,
    "ready for pickup": NormalizedTrackingStatus.READY_FOR_PICKUP,
    "unsuccessful delivery": NormalizedTrackingStatus.DELIVERY_EXCEPTION,
    "awaiting collection": NormalizedTrackingStatus.AWAITING_COLLECTION,
}


_PROVIDER_STATUS_MAPS: Mapping[CarrierProvider, Mapping[str, NormalizedTrackingStatus]] = {
    CarrierProvider.AUSTRALIA_POST: AUSTRALIA_POST_STATUS_MAP,
    CarrierProvider.STARTRACK: STARTRACK_STATUS_MAP,
}


def normalize_tracking_status(
    provider: CarrierProvider, raw_status: str
) -> NormalizedTrackingStatus:
    """Map a raw carrier status using only that carrier's approved table.

    TNT and any provider without an approved raw-to-normalized mapping resolve
    to ``unknown``; the raw status is preserved by the caller per D-028. Event
    descriptions are never used to infer a normalized status.
    """

    mapping = _PROVIDER_STATUS_MAPS.get(provider)
    if mapping is None:
        return NormalizedTrackingStatus.UNKNOWN
    return mapping.get(raw_status.strip().casefold(), NormalizedTrackingStatus.UNKNOWN)


def _iter_items(items: tuple[_TrackableItemSource, ...]):
    for item in items:
        yield item
        yield from _iter_items(item.items)


def _provider_status(item: _TrackingResultSource) -> str | None:
    if item.status:
        return item.status
    if item.consignment is not None and item.consignment.status:
        return item.consignment.status
    statuses = {nested.status for nested in _iter_items(item.trackable_items) if nested.status}
    if len(statuses) == 1:
        return statuses.pop()
    return None


def _events(item: _TrackingResultSource) -> tuple[TrackingEvent, ...]:
    sources: list[_ProviderEventSource] = []
    if item.consignment is not None:
        sources.extend(item.consignment.events)
    for nested in _iter_items(item.trackable_items):
        sources.extend(nested.events)

    events = [
        TrackingEvent(
            event_time=source.date.astimezone(UTC),
            location=source.location.strip()
            if source.location and source.location.strip()
            else None,
            description=source.description,
            provider_status=None,
            normalized_status=NormalizedTrackingStatus.UNKNOWN,
        )
        for source in sources
    ]
    events.sort(key=lambda event: event.event_time, reverse=True)
    return tuple(events)


def _item_error_category(code: str | None) -> TrackingDiagnosticCategory:
    if code in {"ESB-10001", "51104"}:
        return TrackingDiagnosticCategory.INVALID_REQUEST
    if code == "ESB-10002":
        return TrackingDiagnosticCategory.PRODUCT_NOT_TRACKABLE
    return TrackingDiagnosticCategory.PROVIDER


class AustraliaPostApiTrackingProvider:
    """Shared protocol implementation with provider-specific status normalization."""

    expected_provider: CarrierProvider

    def __init__(
        self,
        configuration: ProviderConfiguration,
        credentials: ProviderCredentials,
        transport: TrackingHttpTransport,
        rate_limiter: TrackingRateLimiter | None = None,
    ) -> None:
        if configuration.provider is not self.expected_provider:
            raise ValueError("provider configuration does not match adapter")
        if credentials.provider is not self.expected_provider:
            raise ValueError("provider credentials do not match adapter")
        self._configuration = configuration
        self._credentials = credentials
        self._transport = transport
        self._rate_limiter = rate_limiter or _shared_rate_limiter(configuration)

    @property
    def adapter_key(self) -> str:
        return self._configuration.adapter_key

    @property
    def configuration_key(self) -> tuple[str, str, str]:
        return (
            self._configuration.provider_revision_id,
            self._configuration.account_revision_id,
            self._configuration.product_revision_id,
        )

    @property
    def provider_revision_id(self) -> str:
        return self._configuration.provider_revision_id

    @property
    def provider(self) -> CarrierProvider:
        return self.expected_provider

    def track(self, batch: tuple[TrackingRequest, ...]) -> tuple[ProviderTrackingResult, ...]:
        if not batch or len(batch) > MAX_TRACKING_IDS_PER_REQUEST:
            raise ValueError("tracking batch must contain between 1 and 10 requests")
        if any(request.provider is not self.provider for request in batch):
            raise ValueError("tracking batch cannot mix providers")
        if not self._rate_limiter.try_acquire():
            raise _provider_error(
                TrackingDiagnosticCategory.RATE_LIMIT,
                retryable=True,
                safe_detail="local provider request budget exhausted",
            )

        config = self._configuration
        credentials = self._credentials
        response = self._transport.get(
            TrackingHttpRequest(
                url=f"{config.base_url}{TRACK_PATH}",
                params={"tracking_ids": ",".join(request.tracking_id for request in batch)},
                headers={
                    "Accept": "application/json",
                    "Account-Number": credentials.account_number.get_secret_value(),
                },
                auth=(
                    credentials.api_key.get_secret_value(),
                    credentials.api_secret.get_secret_value(),
                ),
                connect_timeout_seconds=config.connect_timeout_seconds,
                read_timeout_seconds=config.read_timeout_seconds,
                max_response_bytes=config.max_response_bytes,
            )
        )
        self._raise_for_status(response)
        payload = self._parse_payload(response)
        return self._map_items(batch, payload)

    def _raise_for_status(self, response: TrackingHttpResponse) -> None:
        status = response.status_code
        if status in {401, 403}:
            raise _provider_error(
                TrackingDiagnosticCategory.AUTHENTICATION,
                retryable=False,
                http_status=status,
                safe_detail="provider rejected authentication",
            )
        if status == 429:
            raise _provider_error(
                TrackingDiagnosticCategory.RATE_LIMIT,
                retryable=True,
                http_status=status,
                safe_detail="provider rate limit exceeded",
            )
        if 500 <= status <= 599:
            raise _provider_error(
                TrackingDiagnosticCategory.PROVIDER,
                retryable=True,
                http_status=status,
                safe_detail="provider service failed",
            )
        if status != 200:
            raise _provider_error(
                TrackingDiagnosticCategory.PROVIDER,
                retryable=False,
                http_status=status,
                safe_detail="provider rejected tracking request",
            )

    def _parse_payload(self, response: TrackingHttpResponse) -> _TrackingResponseSource:
        try:
            raw = json.loads(response.content)
            return _TrackingResponseSource.model_validate(raw)
        except (json.JSONDecodeError, UnicodeDecodeError, ValidationError, TypeError):
            raise _provider_error(
                TrackingDiagnosticCategory.INVALID_RESPONSE,
                retryable=False,
                http_status=response.status_code,
                safe_detail="provider response schema was invalid",
            ) from None

    def _map_items(
        self,
        batch: tuple[TrackingRequest, ...],
        payload: _TrackingResponseSource,
    ) -> tuple[ProviderTrackingResult, ...]:
        requested_indexes = {request.tracking_id: index for index, request in enumerate(batch)}
        if len(requested_indexes) != len(batch):
            raise ValueError("tracking batch contains duplicate tracking IDs")

        returned: dict[int, ProviderTrackingResult] = {}
        for source in payload.tracking_results:
            index = requested_indexes.get(source.tracking_id)
            if index is None or index in returned:
                raise _provider_error(
                    TrackingDiagnosticCategory.INVALID_RESPONSE,
                    retryable=False,
                    http_status=200,
                    safe_detail="provider response did not match request items",
                )
            if source.errors:
                error = source.errors[0]
                code = error.code or error.error_code
                category = _item_error_category(code)
                diagnostic = TrackingDiagnostic(
                    category=category,
                    provider_code=code,
                    http_status=200,
                    retryable=False,
                    safe_detail="provider rejected tracking item",
                    item_index=index,
                )
                returned[index] = ProviderTrackingResult(
                    request_item_index=index,
                    error_category=category,
                    diagnostic=diagnostic,
                )
                continue

            events = _events(source)
            raw_status = _provider_status(source)
            returned[index] = ProviderTrackingResult(
                request_item_index=index,
                provider_status=raw_status,
                current_status=(
                    normalize_tracking_status(self.provider, raw_status)
                    if raw_status is not None
                    else None
                ),
                latest_event_at=events[0].event_time if events else None,
                events=events,
            )

        if len(returned) != len(batch):
            raise _provider_error(
                TrackingDiagnosticCategory.INVALID_RESPONSE,
                retryable=False,
                http_status=200,
                safe_detail="provider response omitted request items",
            )
        return tuple(returned[index] for index in range(len(batch)))


class AustraliaPostTrackingProvider(AustraliaPostApiTrackingProvider):
    expected_provider = CarrierProvider.AUSTRALIA_POST


class StarTrackTrackingProvider(AustraliaPostApiTrackingProvider):
    expected_provider = CarrierProvider.STARTRACK
