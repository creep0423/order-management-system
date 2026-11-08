"""Server-side environment resolution for provider credentials."""

from __future__ import annotations

import os
from collections.abc import Mapping

from pydantic import BaseModel, ConfigDict, Field, SecretStr

from backend.integrations.tracking import _provider_error
from backend.models import (
    CarrierProvider,
    ProviderCredentials,
    TrackingDiagnosticCategory,
)
from backend.models.tracking import TrackingProviderError


class CredentialEnvironmentBinding(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    credential_ref: str = Field(min_length=1)
    provider: CarrierProvider
    api_key_variable: str = Field(min_length=1)
    api_secret_variable: str = Field(min_length=1)
    account_number_variable: str = Field(min_length=1)


class EnvironmentCredentialReader:
    """Resolve approved credential references without copying values into config records."""

    def __init__(
        self,
        bindings: tuple[CredentialEnvironmentBinding, ...],
        environment: Mapping[str, str] | None = None,
    ) -> None:
        self._bindings = {binding.credential_ref: binding for binding in bindings}
        if len(self._bindings) != len(bindings):
            raise ValueError("credential references must be unique")
        self._environment = environment if environment is not None else os.environ

    def get(self, credential_ref: str) -> ProviderCredentials:
        binding = self._bindings.get(credential_ref)
        if binding is None:
            raise self._missing()
        try:
            api_key = self._environment[binding.api_key_variable]
            api_secret = self._environment[binding.api_secret_variable]
            account_number = self._environment[binding.account_number_variable]
        except KeyError:
            raise self._missing() from None
        if not api_key or not api_secret or not account_number:
            raise self._missing()
        try:
            return ProviderCredentials(
                provider=binding.provider,
                api_key=SecretStr(api_key),
                api_secret=SecretStr(api_secret),
                account_number=SecretStr(account_number),
            )
        except ValueError:
            raise self._missing() from None

    @staticmethod
    def _missing() -> TrackingProviderError:
        return _provider_error(
            TrackingDiagnosticCategory.CONFIGURATION,
            retryable=False,
            safe_detail="provider credentials are unavailable",
        )
