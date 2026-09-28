from fastapi.testclient import TestClient

from app.services.auth import COOKIE_NAME


def test_fresh_install_needs_a_passphrase(anon_client: TestClient) -> None:
    assert anon_client.get("/auth/status").json() == {"configured": False, "authenticated": False}
    assert anon_client.get("/path").status_code == 401


def test_setup_signs_in_with_a_hardened_cookie(anon_client: TestClient) -> None:
    response = anon_client.post("/auth/setup", json={"passphrase": "bonjour-canada"})

    cookie = response.headers["set-cookie"]
    assert response.status_code == 204
    assert "HttpOnly" in cookie and "SameSite=strict" in cookie
    assert anon_client.get("/auth/status").json() == {"configured": True, "authenticated": True}
    assert anon_client.get("/path").status_code == 200


def test_passphrase_can_only_be_set_once_and_must_be_long_enough(anon_client: TestClient) -> None:
    assert anon_client.post("/auth/setup", json={"passphrase": "court"}).status_code == 403
    anon_client.post("/auth/setup", json={"passphrase": "bonjour-canada"})

    assert anon_client.post("/auth/setup", json={"passphrase": "autre-phrase"}).status_code == 403


def test_login_checks_the_passphrase(anon_client: TestClient) -> None:
    anon_client.post("/auth/setup", json={"passphrase": "bonjour-canada"})
    anon_client.post("/auth/logout")
    anon_client.cookies.clear()

    assert anon_client.post("/auth/login", json={"passphrase": "wrong-guess"}).status_code == 401
    assert anon_client.post("/auth/login", json={"passphrase": "bonjour-canada"}).status_code == 204
    assert anon_client.get("/path").status_code == 200


def test_tampered_cookie_is_rejected(anon_client: TestClient) -> None:
    anon_client.cookies.set(COOKIE_NAME, "forged.value.here")

    assert anon_client.get("/path").status_code == 401


def test_login_attempts_are_rate_limited(anon_client: TestClient) -> None:
    anon_client.post("/auth/setup", json={"passphrase": "bonjour-canada"})
    anon_client.cookies.clear()

    codes = [
        anon_client.post("/auth/login", json={"passphrase": f"guess-{i}"}).status_code
        for i in range(6)
    ]

    assert codes == [401] * 5 + [429]
