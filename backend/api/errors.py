"""Safe, stable API error mapping for known and unexpected failures."""

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from backend.api.dependencies import DataSourceUnavailableError
from backend.api.schemas import ErrorDetail, ErrorResponse
from backend.repositories import RepositoryError
from backend.services import (
    OrderDataIntegrityError,
    OrderNotFoundError,
    ProductNotFoundError,
    ServiceError,
)


def _error(status_code: int, code: str, message: str) -> JSONResponse:
    payload = ErrorResponse(error=ErrorDetail(code=code, message=message))
    return JSONResponse(status_code=status_code, content=payload.model_dump(mode="json"))


def register_exception_handlers(app: FastAPI) -> None:
    """Install handlers that never expose raw exceptions or request data."""

    @app.exception_handler(OrderNotFoundError)
    async def order_not_found_handler(
        request: Request, exception: OrderNotFoundError
    ) -> JSONResponse:
        return _error(404, "ORDER_NOT_FOUND", "Order not found.")

    @app.exception_handler(RequestValidationError)
    async def request_validation_handler(
        request: Request, exception: RequestValidationError
    ) -> JSONResponse:
        return _error(422, "REQUEST_VALIDATION_ERROR", "Request validation failed.")

    @app.exception_handler(DataSourceUnavailableError)
    @app.exception_handler(RepositoryError)
    @app.exception_handler(ProductNotFoundError)
    @app.exception_handler(OrderDataIntegrityError)
    async def data_source_handler(request: Request, exception: Exception) -> JSONResponse:
        return _error(500, "DATA_SOURCE_ERROR", "Order data is unavailable.")

    @app.exception_handler(ServiceError)
    @app.exception_handler(Exception)
    async def internal_error_handler(request: Request, exception: Exception) -> JSONResponse:
        return _error(500, "INTERNAL_SERVER_ERROR", "An unexpected server error occurred.")
