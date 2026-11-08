"""FastAPI application entry point."""

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from typing import Any

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from backend.api.errors import register_exception_handlers
from backend.api.routes.health import router as health_router
from backend.api.routes.orders import router as orders_router
from backend.api.schemas import TRACKING_MAPPING_UNRESOLVED_EXAMPLE
from backend.repositories import RepositoryCollection, RepositoryError
from backend.services import (
    OrderService,
    PackageEstimationService,
    StaticPackagingRuleSetReader,
    StaticTrackingConfigurationReader,
    StaticTrackingProviderRegistry,
    TrackingService,
)

ALLOWED_ORIGINS = [
    "http://localhost:5173",
    "http://127.0.0.1:5173",
]


class OrderManagementApp(FastAPI):
    """FastAPI app that keeps the D-031 nullable-provider example intact."""

    def openapi(self) -> dict[str, Any]:
        schema = super().openapi()
        tracking = schema.get("components", {}).get("schemas", {}).get("TrackingResponse")
        if isinstance(tracking, dict):
            # FastAPI encodes the generated document with exclude_none=True, which
            # would erase the very null fields that make the D-031 example
            # meaningful. Restore the canonical example verbatim.
            tracking["examples"] = [dict(TRACKING_MAPPING_UNRESOLVED_EXAMPLE)]
        return schema


def build_tracking_service() -> TrackingService:
    """Build the default tracking boundary for an app without approved configuration.

    No approved Active Release, mapping, credential or adapter is fabricated.
    Every resolved tracking group therefore becomes D-031
    ``CARRIER_MAPPING_UNRESOLVED`` and no provider request is possible.
    """

    return TrackingService(
        StaticTrackingConfigurationReader(None),
        StaticTrackingProviderRegistry(),
    )


def build_package_estimation_service() -> PackageEstimationService:
    """Build the default package estimation boundary with no approved ruleset.

    Batch J1 ships the estimation capability but no approved production
    packaging ruleset, material catalogue or SKU packaging specification exists.
    Synthetic fixtures are test-only and must never be wired here, so every
    order detail reports ``unavailable / PACKAGE_RULES_NOT_CONFIGURED`` and
    returns zero packages. No default dimension, weight, material or capacity is
    fabricated.
    """

    return PackageEstimationService(StaticPackagingRuleSetReader(None))


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    """Initialize the read-only data boundary once for the application."""

    app.state.order_service = None
    try:
        repositories = RepositoryCollection()
    except RepositoryError:
        pass
    else:
        app.state.order_service = OrderService(
            repositories,
            tracking_service=build_tracking_service(),
            package_estimation_service=build_package_estimation_service(),
        )
    yield
    app.state.order_service = None


app = OrderManagementApp(
    title="Order Management System",
    version="1.0.0",
    description="Read-only API v1 for order summaries and Decimal-safe order details.",
    lifespan=lifespan,
)
app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=False,
    allow_methods=["GET"],
    allow_headers=["Accept"],
)
register_exception_handlers(app)
app.include_router(health_router)
app.include_router(orders_router)
