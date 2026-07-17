"""Step 10: production-mode verification of Apple/Google id_tokens.

We can't call Apple/Google in tests, so we mint our own RSA keypair, sign
id_tokens with it, and patch the JWKS lookup to return our public key. The
verification logic itself (signature, aud, iss, exp) runs for real.
"""

from datetime import datetime, timedelta, timezone

import jwt
import pytest
from cryptography.hazmat.primitives.asymmetric import rsa

from app.config import Settings
from app.routes import auth as auth_module
from app.utils import provider_tokens

PRIVATE_KEY = rsa.generate_private_key(public_exponent=65537, key_size=2048)
PUBLIC_KEY = PRIVATE_KEY.public_key()

BUNDLE_ID = "com.akhil.thejourney"
GOOGLE_CLIENT = "1234-abc.apps.googleusercontent.com"


@pytest.fixture(autouse=True)
def production_auth(monkeypatch):
    monkeypatch.setattr(
        auth_module,
        "get_settings",
        lambda: Settings(
            auth_mode="production",
            apple_audience=BUNDLE_ID,
            google_audience=GOOGLE_CLIENT,
        ),
    )
    monkeypatch.setattr(provider_tokens, "_signing_key", lambda provider, token: PUBLIC_KEY)


def make_token(
    iss="https://appleid.apple.com",
    aud=BUNDLE_ID,
    sub="apple-user-001",
    email="akhil@example.com",
    expired=False,
    key=PRIVATE_KEY,
):
    now = datetime.now(timezone.utc)
    exp = now - timedelta(hours=1) if expired else now + timedelta(hours=1)
    return jwt.encode(
        {"iss": iss, "aud": aud, "sub": sub, "email": email, "exp": exp, "iat": now},
        key,
        algorithm="RS256",
    )


def test_valid_apple_token(client):
    res = client.post("/auth/apple", json={"id_token": make_token()})
    assert res.status_code == 200, res.text
    headers = {"Authorization": f"Bearer {res.json()['access_token']}"}
    me = client.get("/auth/me", headers=headers).json()
    assert me["provider"] == "apple"
    assert me["email"] == "akhil@example.com"


def test_valid_google_token_both_issuers(client):
    for iss in ("https://accounts.google.com", "accounts.google.com"):
        res = client.post(
            "/auth/google",
            json={"id_token": make_token(iss=iss, aud=GOOGLE_CLIENT, sub="g-1")},
        )
        assert res.status_code == 200, res.text


def test_same_sub_maps_to_same_user(client):
    r1 = client.post("/auth/apple", json={"id_token": make_token(sub="stable-id")})
    r2 = client.post("/auth/apple", json={"id_token": make_token(sub="stable-id")})
    h1 = {"Authorization": f"Bearer {r1.json()['access_token']}"}
    h2 = {"Authorization": f"Bearer {r2.json()['access_token']}"}
    assert client.get("/auth/me", headers=h1).json()["id"] == client.get("/auth/me", headers=h2).json()["id"]


def test_wrong_audience_rejected(client):
    res = client.post("/auth/apple", json={"id_token": make_token(aud="com.someone.else")})
    assert res.status_code == 401


def test_expired_token_rejected(client):
    res = client.post("/auth/apple", json={"id_token": make_token(expired=True)})
    assert res.status_code == 401


def test_wrong_issuer_rejected(client):
    res = client.post("/auth/apple", json={"id_token": make_token(iss="https://evil.example.com")})
    assert res.status_code == 401


def test_google_token_on_apple_endpoint_rejected(client):
    # Right key, but Google issuer + Google audience must not pass Apple checks.
    res = client.post(
        "/auth/apple",
        json={"id_token": make_token(iss="https://accounts.google.com", aud=GOOGLE_CLIENT)},
    )
    assert res.status_code == 401


def test_forged_signature_rejected(client):
    other_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    res = client.post("/auth/apple", json={"id_token": make_token(key=other_key)})
    assert res.status_code == 401


def test_dev_style_string_rejected_in_production(client):
    res = client.post("/auth/apple", json={"id_token": "akhil-test"})
    assert res.status_code == 401
