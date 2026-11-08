"""Health check endpoint."""

from typing import Literal

from fastapi import APIRouter
from pydantic import BaseModel

router = APIRouter()


class HealthResponse(BaseModel):
    """Response returned when the application is healthy."""

    status: Literal["ok"] = "ok"


@router.get(
    "/health",
    response_model=HealthResponse,
    tags=["Health"],
    summary="Check API health",
    description="Report that the FastAPI process is available.",
)
async def health_check() -> HealthResponse:
    """Report that the API process is available."""
    return HealthResponse()
