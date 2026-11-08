"""Append-only tracking configuration revisions with per-ID immutability.

Provider, Account, Product, Mapping and Release revisions are frozen by their
own Revision ID. Registration is idempotent for identical content and rejected
for conflicting content, so a Provider/Account/Product tuple (or any other
combination of IDs) can never mask a mutated revision.
"""

from __future__ import annotations

from typing import TypeVar

from backend.models import (
    AccountRevision,
    MappingRevision,
    ProductRevision,
    ProviderRevision,
    TrackingConfigurationRelease,
)

RevisionT = TypeVar(
    "RevisionT",
    ProviderRevision,
    AccountRevision,
    ProductRevision,
    MappingRevision,
    TrackingConfigurationRelease,
)


class ConfigurationRevisionConflictError(Exception):
    """One Revision ID was published with content that differs from its original."""

    def __init__(self, revision_kind: str, revision_id: str) -> None:
        self.revision_kind = revision_kind
        self.revision_id = revision_id
        super().__init__(f"{revision_kind} revision id maps to conflicting immutable content")


class TrackingConfigurationCatalog:
    """Append-only store freezing every Revision ID to exactly one content.

    Publication registers Provider, Account, Product, Mapping and Release
    revisions independently. The Active Release pointer remains the only
    intentionally mutable activation reference; revisions themselves are never
    updated or deleted.
    """

    def __init__(self) -> None:
        self._provider_revisions: dict[str, ProviderRevision] = {}
        self._account_revisions: dict[str, AccountRevision] = {}
        self._product_revisions: dict[str, ProductRevision] = {}
        self._mapping_revisions: dict[str, MappingRevision] = {}
        self._release_revisions: dict[str, TrackingConfigurationRelease] = {}

    def register_provider_revision(self, revision: ProviderRevision) -> None:
        self._register(
            self._provider_revisions, revision.provider_revision_id, revision, "provider"
        )

    def register_account_revision(self, revision: AccountRevision) -> None:
        self._register(self._account_revisions, revision.account_revision_id, revision, "account")

    def register_product_revision(self, revision: ProductRevision) -> None:
        self._register(self._product_revisions, revision.product_revision_id, revision, "product")

    def register_mapping_revision(self, revision: MappingRevision) -> None:
        self._register(self._mapping_revisions, revision.mapping_revision_id, revision, "mapping")

    def register_release(self, release: TrackingConfigurationRelease) -> None:
        """Publish one approved release and freeze every revision it references."""

        for provider_revision in release.provider_revisions:
            self.register_provider_revision(provider_revision)
        for account_revision in release.account_revisions:
            self.register_account_revision(account_revision)
        for product_revision in release.product_revisions:
            self.register_product_revision(product_revision)
        for mapping_revision in release.mapping_revisions:
            self.register_mapping_revision(mapping_revision)
        self._register(self._release_revisions, release.release_revision_id, release, "release")

    def get_provider_revision(self, provider_revision_id: str) -> ProviderRevision:
        return self._get(self._provider_revisions, provider_revision_id, "provider")

    def get_account_revision(self, account_revision_id: str) -> AccountRevision:
        return self._get(self._account_revisions, account_revision_id, "account")

    def get_product_revision(self, product_revision_id: str) -> ProductRevision:
        return self._get(self._product_revisions, product_revision_id, "product")

    def get_mapping_revision(self, mapping_revision_id: str) -> MappingRevision:
        return self._get(self._mapping_revisions, mapping_revision_id, "mapping")

    def get_release(self, release_revision_id: str) -> TrackingConfigurationRelease:
        return self._get(self._release_revisions, release_revision_id, "release")

    @staticmethod
    def _register(
        store: dict[str, RevisionT],
        revision_id: str,
        revision: RevisionT,
        revision_kind: str,
    ) -> None:
        published = store.get(revision_id)
        if published is None:
            store[revision_id] = revision
            return
        if published.model_dump() != revision.model_dump():
            raise ConfigurationRevisionConflictError(revision_kind, revision_id)

    @staticmethod
    def _get(store: dict[str, RevisionT], revision_id: str, revision_kind: str) -> RevisionT:
        revision = store.get(revision_id)
        if revision is None:
            raise KeyError(f"{revision_kind} revision is not published")
        return revision
