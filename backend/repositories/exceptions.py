"""Non-sensitive exception types exposed by the repository boundary."""

from dataclasses import dataclass
from pathlib import Path


class RepositoryError(Exception):
    """Base exception for repository failures."""


class DataSourceNotFoundError(RepositoryError):
    """Raised when an expected JSON data source does not exist."""

    def __init__(self, path: Path) -> None:
        self.source_name = path.name
        super().__init__(f"data source not found: {self.source_name}")


class DataSourceParseError(RepositoryError):
    """Raised when a data source is not valid UTF-8 JSON."""

    def __init__(self, path: Path) -> None:
        self.source_name = path.name
        super().__init__(f"data source is not valid JSON: {self.source_name}")


@dataclass(frozen=True, slots=True)
class ValidationDiagnostic:
    """A safe Pydantic error projection containing no source input or message."""

    record_path: str
    field_path: str
    error_type: str


class DataValidationError(RepositoryError):
    """Raised when parsed JSON does not match its source schema."""

    def __init__(self, path: Path, diagnostics: tuple[ValidationDiagnostic, ...]) -> None:
        self.source_name = path.name
        self.diagnostics = diagnostics
        first = (
            diagnostics[0] if diagnostics else ValidationDiagnostic("$", "$", "validation_error")
        )
        self.record_path = first.record_path
        self.field_path = first.field_path
        self.error_type = first.error_type
        super().__init__(
            "data source failed validation: "
            f"source={self.source_name} "
            f"record={self.record_path} "
            f"field={self.field_path} "
            f"error_type={self.error_type} "
            f"error_count={len(diagnostics)}"
        )


class DataIntegrityError(RepositoryError):
    """Raised when identifiers or cross-file references are inconsistent."""


class DuplicateIdentifierError(DataIntegrityError):
    """Raised when a repository source contains a duplicate logical key."""

    def __init__(self, entity: str) -> None:
        self.entity = entity
        super().__init__(f"duplicate {entity} identifier")


class MissingReferenceError(DataIntegrityError):
    """Raised when an order references data absent from another repository."""

    def __init__(self, entity: str) -> None:
        self.entity = entity
        super().__init__(f"missing referenced {entity}")


class RecordNotFoundError(RepositoryError):
    """Raised when a requested logical record does not exist."""

    def __init__(self, entity: str) -> None:
        self.entity = entity
        super().__init__(f"{entity} not found")
