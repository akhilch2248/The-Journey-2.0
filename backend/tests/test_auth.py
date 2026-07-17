from datetime import datetime, timedelta, timezone

import jwt

from app.config import get_settings
from app.utils.auth_tokens import ALGORITHM

from .conftest import login


def test_auth_config_reports_mode(client):
    res = client.get("/auth/config")
    assert res.status_code == 200
    assert res.json() == {"mode": "dev"}


def test_apple_login_returns_token(client):
    res = client.post("/auth/apple", json={"id_token": "akhil-test"})
    assert res.status_code == 200
    body = res.json()
    assert body["token_type"] == "bearer"
    assert body["access_token"]


def test_google_login_returns_token(client):
    res = client.post("/auth/google", json={"id_token": "akhil-google"})
    assert res.status_code == 200


def test_same_id_token_reuses_user(client):
    h1 = login(client, "same-person")
    h2 = login(client, "same-person")
    me1 = client.get("/auth/me", headers=h1).json()
    me2 = client.get("/auth/me", headers=h2).json()
    assert me1["id"] == me2["id"]


def test_same_token_different_provider_is_different_user(client):
    me_apple = client.get("/auth/me", headers=login(client, "x", "apple")).json()
    me_google = client.get("/auth/me", headers=login(client, "x", "google")).json()
    assert me_apple["id"] != me_google["id"]


def test_empty_id_token_rejected(client):
    res = client.post("/auth/apple", json={"id_token": "   "})
    assert res.status_code == 400


def test_me_requires_auth(client):
    assert client.get("/auth/me").status_code == 401  # HTTPBearer: no header


def test_garbage_token_rejected(client):
    res = client.get("/auth/me", headers={"Authorization": "Bearer not-a-jwt"})
    assert res.status_code == 401


def test_expired_token_rejected(client):
    settings = get_settings()
    expired = jwt.encode(
        {"sub": "1", "exp": datetime.now(timezone.utc) - timedelta(minutes=5)},
        settings.app_secret,
        algorithm=ALGORITHM,
    )
    res = client.get("/auth/me", headers={"Authorization": f"Bearer {expired}"})
    assert res.status_code == 401


def test_token_signed_with_wrong_secret_rejected(client):
    forged = jwt.encode(
        {"sub": "1", "exp": datetime.now(timezone.utc) + timedelta(minutes=5)},
        "attacker-secret",
        algorithm=ALGORITHM,
    )
    res = client.get("/auth/me", headers={"Authorization": f"Bearer {forged}"})
    assert res.status_code == 401


def test_token_for_deleted_user_rejected(client):
    settings = get_settings()
    ghost = jwt.encode(
        {"sub": "99999", "exp": datetime.now(timezone.utc) + timedelta(minutes=5)},
        settings.app_secret,
        algorithm=ALGORITHM,
    )
    res = client.get("/auth/me", headers={"Authorization": f"Bearer {ghost}"})
    assert res.status_code == 401
