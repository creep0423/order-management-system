"""Credential resolution stays server-side and fails closed."""

import pytest

from backend.integrations import CredentialEnvironmentBinding, EnvironmentCredentialReader
from backend.models import CarrierProvider, TrackingDiagnosticCategory, TrackingProviderError


def binding() -> CredentialEnvironmentBinding:
    return CredentialEnvironmentBinding(
        credential_ref="credential-ref-1",
        provider=CarrierProvider.AUSTRALIA_POST,
        api_key_variable="TEST_TRACKING_API_KEY",
        api_secret_variable="TEST_TRACKING_API_SECRET",
        account_number_variable="TEST_TRACKING_ACCOUNT",
    )


def test_environment_reader_resolves_secrets_without_exposing_them() -> None:
    marker = "SYNTHETIC-SECRET-MARKER"
    reader = EnvironmentCredentialReader(
        (binding(),),
        {
            "TEST_TRACKING_API_KEY": "SYNTHETIC-KEY",
            "TEST_TRACKING_API_SECRET": marker,
            "TEST_TRACKING_ACCOUNT": "0001234567",
        },
    )

    credentials = reader.get("credential-ref-1")

    assert credentials.api_secret.get_secret_value() == marker
    assert marker not in repr(credentials)
    assert "0001234567" not in repr(credentials)


@pytest.mark.parametrize("reference", ["missing-ref", "credential-ref-1"])
def test_environment_reader_missing_binding_or_value_is_safe_configuration_error(
    reference: str,
) -> None:
    reader = EnvironmentCredentialReader((binding(),), {})

    with pytest.raises(TrackingProviderError) as captured:
        reader.get(reference)

    assert captured.value.category is TrackingDiagnosticCategory.CONFIGURATION
    assert "TEST_TRACKING" not in str(captured.value)
