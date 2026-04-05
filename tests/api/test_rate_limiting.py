"""
Tests for rate limiting middleware.

The ingest routes are limited to 10 requests/min.
"""

import pytest
import api.main as main_module


@pytest.fixture(autouse=True)
def reset_rate_counts():
    """Reset the module-level rate-limit counter before and after each test."""
    main_module._request_counts.clear()
    yield
    main_module._request_counts.clear()


def test_ingest_youtube_rate_limit(client):
    """11 rapid requests to /ingest/youtube must produce at least one 429."""
    payload = {"url": "https://www.youtube.com/watch?v=dQw4w9WgXcQ"}
    responses = [
        client.post("/ingest/youtube", json=payload)
        for _ in range(11)
    ]
    status_codes = [r.status_code for r in responses]
    assert 429 in status_codes, (
        f"Expected at least one 429 after 11 requests, got: {status_codes}"
    )


def test_rate_limit_response_body(client):
    """The 429 response must include a detail field."""
    payload = {"url": "https://www.youtube.com/watch?v=dQw4w9WgXcQ"}
    for _ in range(10):
        client.post("/ingest/youtube", json=payload)

    response = client.post("/ingest/youtube", json=payload)
    assert response.status_code == 429
    body = response.json()
    assert "detail" in body


def test_health_not_rate_limited(client):
    """Health endpoint uses the default 60/min limit — 11 requests should all succeed."""
    responses = [client.get("/health") for _ in range(11)]
    status_codes = [r.status_code for r in responses]
    assert 429 not in status_codes, (
        f"Health endpoint should not be rate-limited at 11 requests, got: {status_codes}"
    )
