"""API v1 order read endpoints."""

from typing import Annotated

from fastapi import APIRouter, Depends, Path

from backend.api.dependencies import get_order_service
from backend.api.mappers import to_order_detail, to_order_summary
from backend.api.schemas import ErrorResponse, OrderDetailEnvelope, OrderListEnvelope
from backend.services import OrderService

router = APIRouter(prefix="/api/v1/orders", tags=["Orders"])
OrderServiceDependency = Annotated[OrderService, Depends(get_order_service)]
OrderNumber = Annotated[
    str,
    Path(
        min_length=1,
        max_length=100,
        pattern=r"^[A-Za-z0-9][A-Za-z0-9._-]*$",
        description="Stable order number",
        examples=["TEST-ORDER-001"],
    ),
]

SERVER_ERROR_RESPONSE = {
    "model": ErrorResponse,
    "description": "The order data source or server could not complete the request.",
}


@router.get(
    "",
    response_model=OrderListEnvelope,
    summary="List orders",
    description=(
        "Return independently priced summaries before shipping; no logistics provider is called."
    ),
    responses={500: SERVER_ERROR_RESPONSE},
)
def list_orders(service: OrderServiceDependency) -> OrderListEnvelope:
    results = service.list_orders()
    return OrderListEnvelope(data=tuple(to_order_summary(result) for result in results))


@router.get(
    "/{order_number}",
    response_model=OrderDetailEnvelope,
    summary="Get order details",
    description=(
        "Return one order with customer, product, pricing, shipping quote and tracking results."
    ),
    responses={
        404: {"model": ErrorResponse, "description": "The order does not exist."},
        422: {"model": ErrorResponse, "description": "The order number is invalid."},
        500: SERVER_ERROR_RESPONSE,
    },
)
def get_order(order_number: OrderNumber, service: OrderServiceDependency) -> OrderDetailEnvelope:
    return OrderDetailEnvelope(data=to_order_detail(service.get_order(order_number)))
