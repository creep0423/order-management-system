"""Immutable tracking domain models and safe integration diagnostics."""

from __future__ import annotations

from datetime import datetime, timedelta
from decimal import Decimal
from enum import StrEnum
from typing import Annotated, Literal
from urllib.parse import urlsplit

from pydantic import (
    AwareDatetime,
    BaseModel,
    ConfigDict,
    Field,
    SecretStr,
    field_validator,
    model_validator,
)


class DomainModel(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")


StrictNonNegativeDecimal = Annotated[
    Decimal,
    Field(strict=True, ge=Decimal("0"), allow_inf_nan=False),
]


class CarrierProvider(StrEnum):
    AUSTRALIA_POST = "australia_post"
    STARTRACK = "startrack"
    TNT = "tnt"


class ResultStatus(StrEnum):
    AVAILABLE = "available"
    UNAVAILABLE = "unavailable"
    UNSUPPORTED = "unsupported"


class NormalizedTrackingStatus(StrEnum):
    PENDING = "pending"
    READY_FOR_PICKUP = "ready_for_pickup"
    IN_TRANSIT = "in_transit"
    OUT_FOR_DELIVERY = "out_for_delivery"
    AWAITING_COLLECTION = "awaiting_collection"
    DELIVERED = "delivered"
    DELIVERY_EXCEPTION = "delivery_exception"
    CANCELLED = "cancelled"
    UNKNOWN = "unknown"


class TrackingReasonCode(StrEnum):
    CARRIER_NOT_IMPLEMENTED = "CARRIER_NOT_IMPLEMENTED"
    PROVIDER_CONFIGURATION_MISSING = "PROVIDER_CONFIGURATION_MISSING"
    CARRIER_MAPPING_UNRESOLVED = "CARRIER_MAPPING_UNRESOLVED"
    PROVIDER_AUTHENTICATION_FAILED = "PROVIDER_AUTHENTICATION_FAILED"
    PROVIDER_TIMEOUT = "PROVIDER_TIMEOUT"
    PROVIDER_NETWORK_ERROR = "PROVIDER_NETWORK_ERROR"
    PROVIDER_RATE_LIMITED = "PROVIDER_RATE_LIMITED"
    TRACKING_ID_INVALID = "TRACKING_ID_INVALID"
    PRODUCT_NOT_TRACKABLE = "PRODUCT_NOT_TRACKABLE"
    PROVIDER_RESPONSE_INVALID = "PROVIDER_RESPONSE_INVALID"
    PROVIDER_ERROR = "PROVIDER_ERROR"


class TrackingDiagnosticCategory(StrEnum):
    CONFIGURATION = "configuration"
    AUTHENTICATION = "authentication"
    TIMEOUT = "timeout"
    NETWORK = "network"
    RATE_LIMIT = "rate_limit"
    INVALID_REQUEST = "invalid_request"
    INVALID_RESPONSE = "invalid_response"
    PRODUCT_NOT_TRACKABLE = "product_not_trackable"
    PROVIDER = "provider"


class ProviderEnvironment(StrEnum):
    TESTBED = "testbed"
    PRODUCTION = "production"


class ConfigurationCapability(StrEnum):
    TRACKING = "tracking"
    SHIPPING_QUOTE = "shipping_quote"


def _require_utc(value: datetime, field_name: str) -> datetime:
    if value.utcoffset() != timedelta(0):
        raise ValueError(f"{field_name} must use UTC")
    return value


def _validated_base_url(value: str) -> str:
    """Normalize and validate a credential-free HTTPS provider base URL."""

    normalized = value.rstrip("/")
    parsed = urlsplit(normalized)
    if (
        parsed.scheme != "https"
        or not parsed.hostname
        or parsed.username is not None
        or parsed.password is not None
        or parsed.query
        or parsed.fragment
    ):
        raise ValueError("provider base_url must be a credential-free HTTPS URL")
    return normalized


class TrackingEvent(DomainModel):
    event_time: AwareDatetime
    location: str | None = None
    description: str = Field(min_length=1, max_length=500)
    provider_status: str | None = Field(default=None, max_length=200)
    normalized_status: NormalizedTrackingStatus

    @field_validator("event_time")
    @classmethod
    def event_time_must_be_utc(cls, value: datetime) -> datetime:
        return _require_utc(value, "event_time")


class TrackingRequest(DomainModel):
    tracking_group_id: str = Field(min_length=1, max_length=200)
    provider: CarrierProvider
    tracking_id: str = Field(min_length=1, max_length=100, repr=False)
    requested_at: AwareDatetime

    @field_validator("requested_at")
    @classmethod
    def requested_at_must_be_utc(cls, value: datetime) -> datetime:
        return _require_utc(value, "requested_at")


class TrackingDiagnostic(DomainModel):
    category: TrackingDiagnosticCategory
    provider_code: str | None = Field(default=None, max_length=100, repr=False)
    http_status: int | None = Field(default=None, strict=True, ge=100, le=599)
    retryable: bool
    safe_detail: str | None = Field(default=None, max_length=300, repr=False)
    item_index: int | None = Field(default=None, strict=True, ge=0)


class ProviderTrackingResult(DomainModel):
    request_item_index: int = Field(strict=True, ge=0)
    provider_status: str | None = Field(default=None, max_length=200)
    current_status: NormalizedTrackingStatus | None = None
    latest_event_at: AwareDatetime | None = None
    events: tuple[TrackingEvent, ...] = ()
    error_category: TrackingDiagnosticCategory | None = None
    diagnostic: TrackingDiagnostic | None = Field(default=None, repr=False)

    @model_validator(mode="after")
    def validate_success_or_failure(self) -> ProviderTrackingResult:
        if self.error_category is None:
            if self.diagnostic is not None:
                raise ValueError("successful provider result cannot include a diagnostic")
        else:
            if self.provider_status is not None or self.current_status is not None or self.events:
                raise ValueError("failed provider result cannot include tracking facts")
            if self.latest_event_at is not None:
                raise ValueError("failed provider result cannot include a latest event time")
            if self.diagnostic is None:
                raise ValueError("failed provider result requires a diagnostic")

        expected_latest = max((event.event_time for event in self.events), default=None)
        if self.latest_event_at != expected_latest:
            raise ValueError("latest_event_at must equal the latest event time")
        return self


class TrackingResult(DomainModel):
    """One public tracking outcome per unique tracking group.

    Per D-031 ``provider`` is conditionally nullable: it may only be ``None``
    together with ``status=unavailable`` and ``reason_code=CARRIER_MAPPING_UNRESOLVED``.
    Every other tracking outcome must name a concrete carrier provider.
    """

    tracking_group_id: str = Field(min_length=1, max_length=200)
    provider: CarrierProvider | None
    status: ResultStatus
    reason_code: TrackingReasonCode | None
    checked_at: AwareDatetime
    provider_status: str | None = Field(default=None, max_length=200)
    current_status: NormalizedTrackingStatus | None = None
    latest_event_at: AwareDatetime | None = None
    events: tuple[TrackingEvent, ...] = ()

    @field_validator("checked_at")
    @classmethod
    def checked_at_must_be_utc(cls, value: datetime) -> datetime:
        return _require_utc(value, "checked_at")

    @model_validator(mode="after")
    def validate_provider_resolution(self) -> TrackingResult:
        """Enforce the D-031 provider/status/reason projection matrix."""

        mapping_unresolved = (
            self.status is ResultStatus.UNAVAILABLE
            and self.reason_code is TrackingReasonCode.CARRIER_MAPPING_UNRESOLVED
        )
        if self.provider is None and not mapping_unresolved:
            raise ValueError(
                "provider may only be null for unavailable tracking with CARRIER_MAPPING_UNRESOLVED"
            )
        if self.provider is not None and mapping_unresolved:
            raise ValueError(
                "CARRIER_MAPPING_UNRESOLVED requires an unresolved provider and cannot "
                "name a carrier provider"
            )
        return self

    @model_validator(mode="after")
    def validate_status_matrix(self) -> TrackingResult:
        if self.status is ResultStatus.AVAILABLE:
            if self.reason_code is not None:
                raise ValueError("available tracking result cannot include a reason code")
            expected_latest = max((event.event_time for event in self.events), default=None)
            if self.latest_event_at != expected_latest:
                raise ValueError("latest_event_at must equal the latest event time")
            return self

        if self.reason_code is None:
            raise ValueError("failed tracking result requires a reason code")
        if self.provider_status is not None or self.current_status is not None:
            raise ValueError("failed tracking result cannot include provider status")
        if self.latest_event_at is not None or self.events:
            raise ValueError("failed tracking result cannot include provider events")
        if self.status is ResultStatus.UNSUPPORTED:
            if self.reason_code is not TrackingReasonCode.CARRIER_NOT_IMPLEMENTED:
                raise ValueError("unsupported tracking requires CARRIER_NOT_IMPLEMENTED")
        elif self.reason_code is TrackingReasonCode.CARRIER_NOT_IMPLEMENTED:
            raise ValueError("unavailable tracking cannot use CARRIER_NOT_IMPLEMENTED")
        return self


class ProviderConfiguration(DomainModel):
    """Pinned runtime configuration for one verified tracking adapter revision."""

    model_config = ConfigDict(frozen=True, extra="forbid", arbitrary_types_allowed=True)

    release_revision_id: str = Field(min_length=1)
    mapping_revision_id: str = Field(min_length=1)
    provider_revision_id: str = Field(min_length=1)
    account_revision_id: str = Field(min_length=1)
    product_revision_id: str = Field(min_length=1)
    provider: CarrierProvider
    adapter_key: str = Field(min_length=1)
    environment: ProviderEnvironment
    base_url: str = Field(min_length=1)
    credential_ref: str = Field(min_length=1, repr=False)
    connect_timeout_seconds: float = Field(strict=True, gt=0, le=30)
    read_timeout_seconds: float = Field(strict=True, gt=0, le=60)
    max_response_bytes: int = Field(default=1_000_000, strict=True, gt=0, le=10_000_000)
    validation_status: Literal["verified"] = "verified"
    evidence_ref: str = Field(min_length=1)

    @field_validator("base_url")
    @classmethod
    def base_url_must_be_https(cls, value: str) -> str:
        return _validated_base_url(value)


class ProviderCredentials(DomainModel):
    """Ephemeral secret material resolved outside versioned configuration models."""

    provider: CarrierProvider
    api_key: SecretStr = Field(repr=False)
    api_secret: SecretStr = Field(repr=False)
    account_number: SecretStr = Field(repr=False)

    @model_validator(mode="after")
    def validate_account_shape(self) -> ProviderCredentials:
        account = self.account_number.get_secret_value()
        if self.provider is CarrierProvider.AUSTRALIA_POST:
            valid = len(account) == 10 and account.isdigit()
        elif self.provider is CarrierProvider.STARTRACK:
            valid = len(account) == 8 and account.isdigit() and not account.startswith("0")
        else:
            valid = bool(account)
        if not valid:
            raise ValueError("account number does not match provider requirements")
        return self


class _VerifiedConfigurationRevision(DomainModel):
    """Immutable governance fields shared by every configuration revision type."""

    validation_status: Literal["verified"] = "verified"
    validated_at: AwareDatetime
    evidence_ref: str = Field(min_length=1)

    @field_validator("validated_at")
    @classmethod
    def validated_at_must_be_utc(cls, value: datetime) -> datetime:
        return _require_utc(value, "validated_at")


class ProviderRevision(_VerifiedConfigurationRevision):
    """One immutable Provider configuration revision.

    A ``provider_revision_id`` alone determines every field below; the same ID
    may never describe a different adapter, environment, base URL, capability
    set, timeout or credential reference.
    """

    provider_revision_id: str = Field(min_length=1)
    provider: CarrierProvider
    adapter_key: str = Field(min_length=1)
    environment: ProviderEnvironment
    base_url: str = Field(min_length=1)
    capabilities: frozenset[ConfigurationCapability] = Field(min_length=1)
    connect_timeout_seconds: float = Field(strict=True, gt=0, le=30)
    read_timeout_seconds: float = Field(strict=True, gt=0, le=60)
    max_response_bytes: int = Field(default=1_000_000, strict=True, gt=0, le=10_000_000)
    credential_ref: str = Field(min_length=1, repr=False)

    @field_validator("base_url")
    @classmethod
    def base_url_must_be_https(cls, value: str) -> str:
        return _validated_base_url(value)


class AccountRevision(_VerifiedConfigurationRevision):
    """One immutable Account configuration revision.

    The account number/reference, origin, environment and provider identity are
    all frozen by ``account_revision_id``.
    """

    account_revision_id: str = Field(min_length=1)
    provider_revision_id: str = Field(min_length=1)
    environment: ProviderEnvironment
    origin_id: str = Field(min_length=1)
    account_ref: str = Field(min_length=1, repr=False)
    capabilities: frozenset[ConfigurationCapability] = Field(min_length=1)


class ProductRevision(_VerifiedConfigurationRevision):
    """One immutable Product configuration revision.

    Service code, currency, GST evidence and precision rules are frozen by
    ``product_revision_id``; ``quote_source`` stays ``contract`` until PAC is
    separately approved.
    """

    product_revision_id: str = Field(min_length=1)
    provider_revision_id: str = Field(min_length=1)
    environment: ProviderEnvironment
    product_id: str = Field(min_length=1)
    service_code: str = Field(min_length=1)
    currency: Literal["AUD"] = "AUD"
    capabilities: frozenset[ConfigurationCapability] = Field(min_length=1)
    quote_source: Literal["contract"] = "contract"
    # Governance evidence only: the amount is never consumed by the tracking
    # vertical slice and remains unrounded until an approved Quote flow uses it.
    contract_price_aud: StrictNonNegativeDecimal | None = None
    gst_semantics_ref: str = Field(min_length=1)
    precision_rule_ref: str = Field(min_length=1)


class MappingRevision(_VerifiedConfigurationRevision):
    """One immutable Mapping revision pinning exact Provider/Account/Product revisions."""

    mapping_revision_id: str = Field(min_length=1)
    capability: ConfigurationCapability
    provider_revision_id: str = Field(min_length=1)
    account_revision_id: str = Field(min_length=1)
    product_revision_id: str = Field(min_length=1)
    environment: ProviderEnvironment
    selection_scope: str = Field(min_length=1)
    tracking_group_id: str | None = Field(default=None, min_length=1, max_length=200)

    @model_validator(mode="after")
    def validate_capability_selection(self) -> MappingRevision:
        if self.capability is ConfigurationCapability.TRACKING:
            if self.tracking_group_id is None:
                raise ValueError("tracking mapping revision requires a tracking group selection")
        elif self.tracking_group_id is not None:
            raise ValueError("non-tracking mapping revision cannot select a tracking group")
        return self


def _index_revisions(
    revisions: tuple[object, ...],
    revision_id_attribute: str,
    revision_label: str,
) -> dict[str, object]:
    """Index revisions by ID and reject one ID describing two different contents."""

    index: dict[str, object] = {}
    contents: dict[str, dict[str, object]] = {}
    for revision in revisions:
        revision_id = getattr(revision, revision_id_attribute)
        content = revision.model_dump()  # type: ignore[attr-defined]
        prior_content = contents.setdefault(revision_id, content)
        if prior_content != content:
            raise ValueError(f"{revision_label} revision id maps to inconsistent immutable content")
        index[revision_id] = revision
    return index


class ResolvedTrackingMapping(DomainModel):
    tracking_group_id: str = Field(min_length=1)
    configuration: ProviderConfiguration
    resolved_at: AwareDatetime

    @field_validator("resolved_at")
    @classmethod
    def resolved_at_must_be_utc(cls, value: datetime) -> datetime:
        return _require_utc(value, "resolved_at")


class TrackingConfigurationRelease(DomainModel):
    """Request-pinned, already-approved tracking configuration release.

    Every revision type is validated independently by Revision ID, so a
    provider/account/product tuple can never hide a mutated revision. The
    release also pins the exact Mapping Revision set it was approved with.
    """

    release_revision_id: str = Field(min_length=1)
    environment: ProviderEnvironment
    configuration_scope: str = Field(min_length=1)
    provider_revisions: tuple[ProviderRevision, ...] = Field(min_length=1)
    account_revisions: tuple[AccountRevision, ...] = Field(min_length=1)
    product_revisions: tuple[ProductRevision, ...] = Field(min_length=1)
    mapping_revisions: tuple[MappingRevision, ...] = Field(min_length=1)
    mappings: tuple[ResolvedTrackingMapping, ...] = Field(min_length=1)
    captured_at: AwareDatetime

    @field_validator("captured_at")
    @classmethod
    def captured_at_must_be_utc(cls, value: datetime) -> datetime:
        return _require_utc(value, "captured_at")

    @model_validator(mode="after")
    def validate_release_membership(self) -> TrackingConfigurationRelease:
        group_ids = [mapping.tracking_group_id for mapping in self.mappings]
        if len(group_ids) != len(set(group_ids)):
            raise ValueError("release contains duplicate tracking group mappings")

        providers = _index_revisions(self.provider_revisions, "provider_revision_id", "provider")
        accounts = _index_revisions(self.account_revisions, "account_revision_id", "account")
        products = _index_revisions(self.product_revisions, "product_revision_id", "product")
        mapping_revisions = _index_revisions(
            self.mapping_revisions, "mapping_revision_id", "mapping"
        )

        for mapping in self.mappings:
            config = mapping.configuration
            if config.release_revision_id != self.release_revision_id:
                raise ValueError("mapping configuration is not pinned to this release")
            if config.environment is not self.environment:
                raise ValueError("mapping configuration environment does not match release")
            provider = providers.get(config.provider_revision_id)
            account = accounts.get(config.account_revision_id)
            product = products.get(config.product_revision_id)
            mapping_revision = mapping_revisions.get(config.mapping_revision_id)
            if provider is None or account is None or product is None or mapping_revision is None:
                raise ValueError("mapping configuration must reference published revisions")
            self._validate_provider_content(provider, config)
            self._validate_account_content(account, config)
            self._validate_product_content(product, config)
            self._validate_mapping_content(mapping_revision, mapping, config)
        return self

    @staticmethod
    def _validate_provider_content(
        provider: ProviderRevision, config: ProviderConfiguration
    ) -> None:
        if (
            provider.provider is not config.provider
            or provider.adapter_key != config.adapter_key
            or provider.environment is not config.environment
            or provider.base_url != config.base_url
            or provider.connect_timeout_seconds != config.connect_timeout_seconds
            or provider.read_timeout_seconds != config.read_timeout_seconds
            or provider.max_response_bytes != config.max_response_bytes
            or provider.credential_ref != config.credential_ref
            or provider.evidence_ref != config.evidence_ref
        ):
            raise ValueError("provider revision content does not match pinned configuration")
        if ConfigurationCapability.TRACKING not in provider.capabilities:
            raise ValueError("provider revision does not declare the tracking capability")

    @staticmethod
    def _validate_account_content(account: AccountRevision, config: ProviderConfiguration) -> None:
        if (
            account.provider_revision_id != config.provider_revision_id
            or account.environment is not config.environment
        ):
            raise ValueError("account revision does not match pinned configuration")
        if ConfigurationCapability.TRACKING not in account.capabilities:
            raise ValueError("account revision does not declare the tracking capability")

    @staticmethod
    def _validate_product_content(product: ProductRevision, config: ProviderConfiguration) -> None:
        if (
            product.provider_revision_id != config.provider_revision_id
            or product.environment is not config.environment
        ):
            raise ValueError("product revision does not match pinned configuration")
        if ConfigurationCapability.TRACKING not in product.capabilities:
            raise ValueError("product revision does not declare the tracking capability")

    @staticmethod
    def _validate_mapping_content(
        mapping_revision: MappingRevision,
        mapping: ResolvedTrackingMapping,
        config: ProviderConfiguration,
    ) -> None:
        if mapping_revision.capability is not ConfigurationCapability.TRACKING:
            raise ValueError("tracking release requires tracking mapping revisions")
        if (
            mapping_revision.provider_revision_id != config.provider_revision_id
            or mapping_revision.account_revision_id != config.account_revision_id
            or mapping_revision.product_revision_id != config.product_revision_id
            or mapping_revision.environment is not config.environment
            or mapping_revision.tracking_group_id != mapping.tracking_group_id
        ):
            raise ValueError("mapping revision does not match pinned configuration")


class TrackingProviderError(Exception):
    """Safe classified provider failure; raw payloads and secrets are never retained."""

    def __init__(
        self,
        category: TrackingDiagnosticCategory,
        *,
        retryable: bool,
        diagnostic: TrackingDiagnostic,
    ) -> None:
        self.category = category
        self.retryable = retryable
        self.diagnostic = diagnostic
        super().__init__(f"tracking provider failed: {category.value}")
