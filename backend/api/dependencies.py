"""Application-managed dependencies for API routes."""

from typing import cast

from fastapi import Request

from backend.services import OrderService


class DataSourceUnavailableError(Exception):
    """Raised when startup could not initialize the read-only data boundary."""


def get_order_service(request: Request) -> OrderService:
    """Return the application-scoped service without per-request data loading."""

    service = getattr(request.app.state, "order_service", None)
    if service is None:
        raise DataSourceUnavailableError
    return cast(OrderService, service)
