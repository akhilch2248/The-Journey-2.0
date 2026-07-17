"""Real Apple / Google identity-token verification (Step 10).

Both providers sign id_tokens with RS256 and publish their public keys as
JWKS. We verify the signature against the provider's keys, then check
audience (our app), issuer (the provider), and expiry.
"""

import jwt
from jwt import PyJWKClient

APPLE_JWKS_URL = "https://appleid.apple.com/auth/keys"
APPLE_ISSUER = "https://appleid.apple.com"
GOOGLE_JWKS_URL = "https://www.googleapis.com/oauth2/v3/certs"
GOOGLE_ISSUERS = ("https://accounts.google.com", "accounts.google.com")

_jwks_clients: dict[str, PyJWKClient] = {}


class ProviderTokenError(Exception):
    """The id_token failed verification."""


def _signing_key(provider: str, token: str):
    """Fetch the public key matching the token's kid from the provider's JWKS.
    Patched in tests to avoid network calls."""
    url = APPLE_JWKS_URL if provider == "apple" else GOOGLE_JWKS_URL
    client = _jwks_clients.setdefault(url, PyJWKClient(url, cache_keys=True))
    return client.get_signing_key_from_jwt(token).key


def verify_provider_token(provider: str, id_token: str, audience: str) -> dict:
    """Returns {"provider_id", "email"} from a verified token, or raises
    ProviderTokenError."""
    issuers = (APPLE_ISSUER,) if provider == "apple" else GOOGLE_ISSUERS
    try:
        key = _signing_key(provider, id_token)
        claims = jwt.decode(
            id_token,
            key,
            algorithms=["RS256"],
            audience=audience,
            # PyJWT's issuer check takes a single value; Google has two valid
            # issuers, so we check it ourselves below.
            options={"verify_iss": False},
        )
    except (jwt.InvalidTokenError, jwt.PyJWKClientError) as exc:
        raise ProviderTokenError(f"Invalid {provider} token: {exc}") from exc

    if claims.get("iss") not in issuers:
        raise ProviderTokenError(f"Invalid {provider} token issuer")
    if "sub" not in claims:
        raise ProviderTokenError(f"{provider} token missing subject")

    return {"provider_id": claims["sub"], "email": claims.get("email")}
