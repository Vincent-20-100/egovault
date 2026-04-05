from unittest.mock import patch


def test_health_api_ok_ollama_down(client):
    with patch("api.routers.health._ping_ollama", return_value=False):
        response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["api"] == "ok"
    assert data["ollama"] == "down"
    assert data["db"] == "ok"


def test_health_all_ok(client):
    with patch("api.routers.health._ping_ollama", return_value=True):
        response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["ollama"] == "up"
