"""FastAPI surface tests that never enqueue a real repository clone."""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

import main


@pytest.fixture(autouse=True)
def clear_jobs() -> None:
    main.jobs.clear()
    yield
    main.jobs.clear()


def test_health_reports_service_readiness() -> None:
    with TestClient(main.app) as client:
        response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok", "service": "repomind"}


def test_local_frontend_origin_is_allowed_by_cors() -> None:
    with TestClient(main.app) as client:
        response = client.options(
            "/api/analyze",
            headers={
                "Origin": "http://localhost:5173",
                "Access-Control-Request-Method": "POST",
            },
        )

    assert response.status_code == 200
    assert response.headers["access-control-allow-origin"] == "http://localhost:5173"


def test_analyze_rejects_non_github_url_without_starting_a_job() -> None:
    with TestClient(main.app) as client:
        response = client.post("/api/analyze", json={"repo_url": "https://example.com/acme/demo"})

    assert response.status_code == 422
    assert "github.com" in response.json()["detail"]
    assert main.jobs == {}


def test_missing_job_and_artifact_return_not_found() -> None:
    with TestClient(main.app) as client:
        status_response = client.get("/api/analyze/job_does_not_exist")
        artifact_response = client.get("/api/analyze/job_does_not_exist/artifacts/AGENTS.md")

    assert status_response.status_code == 404
    assert status_response.json()["detail"] == "Analysis job not found"
    assert artifact_response.status_code == 404
    assert artifact_response.json()["detail"] == "Analysis job not found"


def test_unexpected_exception_is_replaced_with_a_safe_actionable_message() -> None:
    message = main._safe_failure_message(AttributeError("'NoneType' object has no attribute 'strip'"))

    assert "NoneType" not in message
    assert "Try again" in message
