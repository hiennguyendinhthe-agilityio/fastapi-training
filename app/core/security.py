"""
app/core/security.py
Clerk RS256 JWKS verification — fetch_jwks_client(), verify_clerk_token().
Implemented in: Task 3.2
"""

from functools import lru_cache
from typing import Any

import jwt
from fastapi import HTTPException, status

from app.core.config import get_settings


@lru_cache(maxsize=1)
def fetch_jwks_client() -> jwt.PyJWKClient:
    """
    Creates and caches the PyJWKClient instance.
    - LRU Cache ensures we only instantiate the client once per worker.
    - PyJWKClient's internal lifespan (300s = 5m) handles cache expiration
      to avoid hitting Clerk API rate limits.
    """
    settings = get_settings()
    return jwt.PyJWKClient(
        settings.CLERK_JWKS_URL,
        cache_keys=True,
        cache_jwk_set=True,
        lifespan=300,
    )


def verify_clerk_token(token: str) -> dict:
    """
    Decodes and verifies a Clerk RS256 JWT using the JWKS endpoint.
    Returns the decoded payload.
    Raises HTTPException(401) if invalid, expired, or missing 'sub' claim.
    """
    try:
        jwks_client = fetch_jwks_client()
        signing_key = jwks_client.get_signing_key_from_jwt(token)

        settings = get_settings()
        options: Any = {}
        if settings.ENVIRONMENT == "development":
            options["verify_exp"] = False

        payload = jwt.decode(
            token,
            key=signing_key.key,
            algorithms=["RS256"],
            leeway=5,  # 5 seconds clock skew tolerance
            options=options,
        )

        if "sub" not in payload:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Token payload is missing 'sub' claim",
            )

        return payload
    except jwt.ExpiredSignatureError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token has expired",
        )
    except jwt.PyJWKClientError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Unable to fetch signing keys",
        )
    except jwt.InvalidTokenError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token",
        )
