"""Tests for the minimal FastAPI application."""

from fastapi import FastAPI
from fastapi.testclient import TestClient

from backend.main import app

client = TestClient(app)


def test_application_import() -> None:
    assert isinstance(app, FastAPI)


def test_health_returns_http_200() -> None:
    response = client.get("/health")

    assert response.status_code == 200


def test_health_returns_expected_json() -> None:
    response = client.get("/health")

    assert response.json() == {"status": "ok"}


def test_openapi_schema_includes_health_endpoint() -> None:
    schema = app.openapi()

    assert schema["info"]["title"] == "Order Management System"
    assert "get" in schema["paths"]["/health"]
