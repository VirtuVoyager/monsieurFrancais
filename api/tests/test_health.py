from fastapi.testclient import TestClient


def test_health_reports_ok_and_request_id(client: TestClient) -> None:
    response = client.get("/health", headers={"x-request-id": "abc"})

    assert response.json() == {"status": "ok"}
    assert response.headers["x-request-id"] == "abc"
