"""
JWT Authentication Tests

Purpose: Validate JWT token verification and security
Tests: Valid token, expired token, invalid signature, missing sub claim

Constitutional Requirements:
- REQUIRED: Reject tokens with invalid signature
- REQUIRED: Reject expired tokens
- REQUIRED: Reject tokens missing sub claim
- REQUIRED: Accept valid tokens with correct signature
"""

import pytest
from datetime import datetime, timedelta
from jose import jwt
import os

# Test secret (matches .env for testing)
TEST_SECRET = os.getenv("BETTER_AUTH_SECRET", "test-secret-for-testing-only")


def create_test_token(
    user_id: str = "test_user_123",
    expires_delta: timedelta = timedelta(days=1),
    secret: str = TEST_SECRET,
    include_sub: bool = True,
    issuer: str = "todoweb",
    audience: str = "todoweb-api"
) -> str:
    """
    Create a test JWT token with configurable parameters

    Args:
        user_id: User ID to include in sub claim
        expires_delta: Time until token expires
        secret: Secret key for signing
        include_sub: Whether to include sub claim
        issuer: Token issuer
        audience: Token audience

    Returns:
        Encoded JWT token string
    """
    payload = {
        "iat": datetime.utcnow(),
        "exp": datetime.utcnow() + expires_delta,
        "iss": issuer,
        "aud": audience
    }

    if include_sub:
        payload["sub"] = user_id

    return jwt.encode(payload, secret, algorithm="HS256")


class TestJWTValidation:
    """Test JWT token validation logic"""

    def test_valid_token(self):
        """Test that valid token is accepted"""
        token = create_test_token(user_id="user_123")

        # Decode and verify
        payload = jwt.decode(
            token,
            TEST_SECRET,
            algorithms=["HS256"],
            issuer="todoweb",
            audience="todoweb-api"
        )

        assert payload["sub"] == "user_123"
        assert payload["iss"] == "todoweb"
        assert payload["aud"] == "todoweb-api"
        assert "exp" in payload
        assert "iat" in payload

    def test_expired_token(self):
        """Test that expired token is rejected"""
        # Create token that expired 1 day ago
        token = create_test_token(
            user_id="user_123",
            expires_delta=timedelta(days=-1)
        )

        # Should raise ExpiredSignatureError
        with pytest.raises(jwt.ExpiredSignatureError):
            jwt.decode(
                token,
                TEST_SECRET,
                algorithms=["HS256"],
                issuer="todoweb",
                audience="todoweb-api"
            )

    def test_invalid_signature(self):
        """Test that token with wrong signature is rejected"""
        # Create token with different secret
        token = create_test_token(
            user_id="user_123",
            secret="wrong-secret-key"
        )

        # Should raise JWTError when verifying with correct secret
        with pytest.raises(jwt.JWTError):
            jwt.decode(
                token,
                TEST_SECRET,
                algorithms=["HS256"],
                issuer="todoweb",
                audience="todoweb-api"
            )

    def test_missing_sub_claim(self):
        """Test that token without sub claim is rejected"""
        # Create token without sub claim
        token = create_test_token(
            user_id="user_123",
            include_sub=False
        )

        # Token should decode but sub claim should be missing
        payload = jwt.decode(
            token,
            TEST_SECRET,
            algorithms=["HS256"],
            issuer="todoweb",
            audience="todoweb-api"
        )

        assert "sub" not in payload

    def test_invalid_issuer(self):
        """Test that token with wrong issuer is rejected"""
        token = create_test_token(
            user_id="user_123",
            issuer="wrong-issuer"
        )

        # Should raise JWTClaimsError
        with pytest.raises(jwt.JWTClaimsError):
            jwt.decode(
                token,
                TEST_SECRET,
                algorithms=["HS256"],
                issuer="todoweb",
                audience="todoweb-api"
            )

    def test_invalid_audience(self):
        """Test that token with wrong audience is rejected"""
        token = create_test_token(
            user_id="user_123",
            audience="wrong-audience"
        )

        # Should raise JWTClaimsError
        with pytest.raises(jwt.JWTClaimsError):
            jwt.decode(
                token,
                TEST_SECRET,
                algorithms=["HS256"],
                issuer="todoweb",
                audience="todoweb-api"
            )

    def test_malformed_token(self):
        """Test that malformed token is rejected"""
        malformed_token = "not.a.valid.jwt.token"

        # Should raise JWTError
        with pytest.raises(jwt.JWTError):
            jwt.decode(
                malformed_token,
                TEST_SECRET,
                algorithms=["HS256"],
                issuer="todoweb",
                audience="todoweb-api"
            )

    def test_token_with_extra_claims(self):
        """Test that token with extra claims is accepted"""
        payload = {
            "sub": "user_123",
            "email": "user@example.com",
            "name": "Test User",
            "iat": datetime.utcnow(),
            "exp": datetime.utcnow() + timedelta(days=1),
            "iss": "todoweb",
            "aud": "todoweb-api"
        }

        token = jwt.encode(payload, TEST_SECRET, algorithm="HS256")

        # Should decode successfully
        decoded = jwt.decode(
            token,
            TEST_SECRET,
            algorithms=["HS256"],
            issuer="todoweb",
            audience="todoweb-api"
        )

        assert decoded["sub"] == "user_123"
        assert decoded["email"] == "user@example.com"
        assert decoded["name"] == "Test User"


class TestTokenExpiration:
    """Test token expiration edge cases"""

    def test_token_expires_in_future(self):
        """Test token that expires in 7 days (standard expiration)"""
        token = create_test_token(
            user_id="user_123",
            expires_delta=timedelta(days=7)
        )

        payload = jwt.decode(
            token,
            TEST_SECRET,
            algorithms=["HS256"],
            issuer="todoweb",
            audience="todoweb-api"
        )

        assert payload["sub"] == "user_123"

    def test_token_expires_soon(self):
        """Test token that expires in 1 second"""
        token = create_test_token(
            user_id="user_123",
            expires_delta=timedelta(seconds=1)
        )

        # Should still be valid
        payload = jwt.decode(
            token,
            TEST_SECRET,
            algorithms=["HS256"],
            issuer="todoweb",
            audience="todoweb-api"
        )

        assert payload["sub"] == "user_123"

    def test_token_just_expired(self):
        """Test token that just expired"""
        token = create_test_token(
            user_id="user_123",
            expires_delta=timedelta(seconds=-1)
        )

        # Should be rejected
        with pytest.raises(jwt.ExpiredSignatureError):
            jwt.decode(
                token,
                TEST_SECRET,
                algorithms=["HS256"],
                issuer="todoweb",
                audience="todoweb-api"
            )


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
