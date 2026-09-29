from unittest.mock import MagicMock, patch

import jwt
import pytest
from fastapi import HTTPException

from app.core.security import verify_clerk_token


def test_verify_clerk_token_success():
    payload = {"sub": "user_123", "exp": 9999999999}
    token = jwt.encode(payload, "secret", algorithm="HS256")

    with patch("app.core.security.fetch_jwks_client") as mock_fetch:
        mock_client = MagicMock()
        mock_fetch.return_value = mock_client

        mock_key = MagicMock()
        mock_key.key = "secret"
        mock_client.get_signing_key_from_jwt.return_value = mock_key

        with patch("app.core.security.jwt.decode") as mock_decode:
            mock_decode.return_value = payload

            result = verify_clerk_token(token)
            assert result == payload
            assert result["sub"] == "user_123"


def test_verify_clerk_token_missing_sub():
    payload = {"exp": 9999999999}

    with patch("app.core.security.fetch_jwks_client") as mock_fetch:
        mock_client = MagicMock()
        mock_fetch.return_value = mock_client
        mock_client.get_signing_key_from_jwt.return_value = MagicMock()

        with patch("app.core.security.jwt.decode", return_value=payload):
            with pytest.raises(HTTPException) as exc:
                verify_clerk_token("fake_token")
            assert exc.value.status_code == 401
            assert "missing 'sub' claim" in exc.value.detail


def test_verify_clerk_token_expired():
    with patch("app.core.security.fetch_jwks_client") as mock_fetch:
        mock_client = MagicMock()
        mock_fetch.return_value = mock_client
        mock_client.get_signing_key_from_jwt.return_value = MagicMock()

        with patch(
            "app.core.security.jwt.decode", side_effect=jwt.ExpiredSignatureError
        ):
            with pytest.raises(HTTPException) as exc:
                verify_clerk_token("fake_token")
            assert exc.value.status_code == 401
            assert "expired" in exc.value.detail


def test_verify_clerk_token_invalid():
    with patch("app.core.security.fetch_jwks_client") as mock_fetch:
        mock_client = MagicMock()
        mock_fetch.return_value = mock_client
        mock_client.get_signing_key_from_jwt.side_effect = jwt.InvalidTokenError

        with pytest.raises(HTTPException) as exc:
            verify_clerk_token("fake_token")
        assert exc.value.status_code == 401
        assert "Invalid token" in exc.value.detail


def test_verify_clerk_token_jwks_fetch_error():
    with patch("app.core.security.fetch_jwks_client") as mock_fetch:
        mock_client = MagicMock()
        mock_fetch.return_value = mock_client
        mock_client.get_signing_key_from_jwt.side_effect = jwt.PyJWKClientError

        with pytest.raises(HTTPException) as exc:
            verify_clerk_token("fake_token")
        assert exc.value.status_code == 401
        assert "Unable to fetch signing keys" in exc.value.detail
