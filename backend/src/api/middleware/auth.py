"""
JWT Authentication Middleware for Todo API

Owner: Backend Security Engineer
Purpose: JWT token verification and user_id extraction
Architecture: FastAPI dependency injection with python-jose

Constitutional Constraints:
- REQUIRED: Verify JWT signature using BETTER_AUTH_SECRET
- REQUIRED: Validate issuer="todoweb" and audience="todoweb-api"
- REQUIRED: Extract user_id from "sub" claim
- REQUIRED: Return 401 for invalid/expired/missing tokens
- REQUIRED: Use HTTPBearer security scheme

Security Protocol:
1. Extract token from Authorization: Bearer <token> header
2. Verify signature with shared BETTER_AUTH_SECRET
3. Validate token claims (exp, iss, aud)
4. Extract user_id from sub claim
5. Return user_id for use in route handlers

All protected routes MUST use Depends(get_current_user_id) to enforce authentication.
"""

import os
import logging
from typing import Annotated
from fastapi import HTTPException, Security, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from jose import jwt, JWTError
from jose.exceptions import ExpiredSignatureError, JWTClaimsError
from dotenv import load_dotenv

# Configure logging
logger = logging.getLogger("api.auth")

# Load environment variables
load_dotenv()

# HTTPBearer security scheme for JWT tokens
security = HTTPBearer(
    scheme_name="Bearer",
    description="JWT token from Better Auth. Include in Authorization header as 'Bearer <token>'"
)


def get_better_auth_secret() -> str:
    """
    Get BETTER_AUTH_SECRET from environment.

    Returns:
        BETTER_AUTH_SECRET string

    Raises:
        HTTPException(500): If BETTER_AUTH_SECRET is not configured
    """
    secret = os.getenv("BETTER_AUTH_SECRET")
    if not secret:
        logger.error("BETTER_AUTH_SECRET environment variable not set")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Server configuration error: Authentication secret not configured"
        )
    return secret


def verify_token(credentials: HTTPAuthorizationCredentials) -> dict:
    """
    Verify JWT token and extract payload.

    Validates:
    - Token signature using BETTER_AUTH_SECRET
    - Token expiration (exp claim)
    - Issuer claim (iss="todoweb")
    - Audience claim (aud="todoweb-api")

    Args:
        credentials: HTTPAuthorizationCredentials from HTTPBearer

    Returns:
        dict: Decoded JWT payload containing user_id in "sub" claim

    Raises:
        HTTPException(401): If token is invalid, expired, or has invalid claims
    """
    token = credentials.credentials
    secret = get_better_auth_secret()

    try:
        # Decode and verify JWT token
        payload = jwt.decode(
            token,
            secret,
            algorithms=["HS256"],
            issuer="todoweb",
            audience="todoweb-api"
        )

        logger.debug(f"Token verified successfully for user: {payload.get('sub')}")
        return payload

    except ExpiredSignatureError:
        logger.warning("Token verification failed: Token has expired")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token has expired",
            headers={"WWW-Authenticate": "Bearer"}
        )
    except JWTClaimsError as e:
        logger.warning(f"Token verification failed: Invalid token claims - {e}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token claims (issuer or audience mismatch)",
            headers={"WWW-Authenticate": "Bearer"}
        )
    except JWTError as e:
        logger.warning(f"Token verification failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication token",
            headers={"WWW-Authenticate": "Bearer"}
        )


async def get_current_user_id(
    credentials: Annotated[HTTPAuthorizationCredentials, Security(security)]
) -> str:
    """
    FastAPI dependency to extract user_id from JWT token.

    This is the primary authentication dependency for all protected routes.

    Usage in routes:
        @router.get("/api/todos")
        async def list_todos(
            user_id: Annotated[str, Depends(get_current_user_id)],
            session: AsyncSession = Depends(get_session)
        ):
            # user_id is automatically extracted from JWT
            # All queries MUST filter by this user_id
            pass

    Args:
        credentials: Automatically extracted from Authorization header

    Returns:
        str: User ID from JWT "sub" claim

    Raises:
        HTTPException(401): If token is invalid or missing user_id
    """
    # Verify token and extract payload
    payload = verify_token(credentials)

    # Extract user_id from "sub" claim
    user_id = payload.get("sub")

    if not user_id:
        logger.error("Token verification succeeded but 'sub' claim is missing")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token: missing user ID",
            headers={"WWW-Authenticate": "Bearer"}
        )

    return user_id


# Optional: Additional dependency for extracting full user info
async def get_current_user_info(
    credentials: Annotated[HTTPAuthorizationCredentials, Security(security)]
) -> dict:
    """
    FastAPI dependency to extract full user information from JWT token.

    Returns the complete JWT payload including:
    - sub: User ID
    - email: User email (if present)
    - iat: Issued at timestamp
    - exp: Expiration timestamp

    Usage:
        @router.get("/api/profile")
        async def get_profile(
            user_info: Annotated[dict, Depends(get_current_user_info)]
        ):
            return {
                "user_id": user_info["sub"],
                "email": user_info.get("email")
            }

    Args:
        credentials: Automatically extracted from Authorization header

    Returns:
        dict: Complete JWT payload

    Raises:
        HTTPException(401): If token is invalid
    """
    return verify_token(credentials)
