"""Read-only JSON repositories and their shared access collection."""

from backend.repositories.collection import RepositoryCollection
from backend.repositories.exceptions import (
    DataIntegrityError,
    DataSourceNotFoundError,
    DataSourceParseError,
    DataValidationError,
    DuplicateIdentifierError,
    MissingReferenceError,
    RecordNotFoundError,
    RepositoryError,
    ValidationDiagnostic,
)
from backend.repositories.order import OrderRepository
from backend.repositories.product import ProductRepository
from backend.repositories.tracking import TrackingRepository

__all__ = [
    "DataIntegrityError",
    "DataSourceNotFoundError",
    "DataSourceParseError",
    "DataValidationError",
    "DuplicateIdentifierError",
    "MissingReferenceError",
    "OrderRepository",
    "ProductRepository",
    "RecordNotFoundError",
    "RepositoryCollection",
    "RepositoryError",
    "TrackingRepository",
    "ValidationDiagnostic",
]
