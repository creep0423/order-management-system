"""Read-only packaging rules reader (D-021).

The reader returns exactly one validated, immutable active ruleset revision and
never fabricates data. Batch J1 ships only a static reader because no approved
production ruleset exists yet; a future configuration-release-backed reader can
implement the same protocol.
"""

from __future__ import annotations

from datetime import datetime
from typing import Protocol

from backend.models.packaging_rules import PackagingRuleSet


class PackagingRulesConfigurationError(Exception):
    """No usable active packaging ruleset exists for the requested instant."""


class PackagingRuleSetReader(Protocol):
    def get_active(self, at: datetime) -> PackagingRuleSet: ...


class StaticPackagingRuleSetReader:
    """Serve one fixed ruleset revision while it is effective.

    ``None`` models an application with no approved packaging ruleset, which is
    the Batch J1 default. That state must fail closed rather than fall back to
    synthetic fixtures.
    """

    def __init__(self, ruleset: PackagingRuleSet | None) -> None:
        self._ruleset = ruleset

    def get_active(self, at: datetime) -> PackagingRuleSet:
        if self._ruleset is None:
            raise PackagingRulesConfigurationError("packaging ruleset is not configured")
        if not self._ruleset.is_active(at):
            raise PackagingRulesConfigurationError("packaging ruleset is not active")
        return self._ruleset
