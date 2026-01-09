# JWT Authentication Protocol: Better Auth ↔ FastAPI

**Feature**: Todo API with Authentication
**Date**: 2026-01-07

## Overview

This document defines the JWT authentication handshake protocol between Better Auth (Next.js frontend) and FastAPI (Python backend), ensuring secure token generation, transmission, and verification per constitution Principle II.

## Architecture

```
┌─────────────────┐         ┌──────────────────┐         ┌─────────────────┐
│   Next.js       │         │   Better Auth    │         │   FastAPI       │
│   Frontend      │────────▶│   (JWT Plugin)   │────────▶│   Backend       │
│                 │  Login  │                  │  Token  │                 │
└─────────────────┘         └──────────────────┘         └─────────────────┘
                                     │                            │
                                     │   BETTER_AUTH_SECRET       │
                                     └────────────────────────────┘
                                          (Shared Secret)
```

## Token Generation (Better Auth)

### Configuration

```typescript
// frontend/src/lib/auth.ts
import { betterAuth } from "better-auth"
import { jwt } from "better-auth/plugins"

export const auth = betterAuth({
  secret: process.env.BETTER_AUTH_SECRET!, // Shared with FastAPI
  database: {
    // Better Auth manages user database
    provider: "postgres",
    url: process.env.DATABASE_URL
  },
  plugins: [
    jwt({
      expiresIn: "7d",        // Token valid for 7 days
      algorithm: "HS256",     // Symmetric signing algorithm
      issuer: "todoweb",      // Token issuer
      audience: "todoweb-api" // Token audience
    })
  ]
})
```

### Token Structure

When a user logs in via Better Auth, a JWT token is generated with this payload:

```json
{
  "sub": "user_123abc",           // User ID (our primary key)
  "email": "user@example.com",    // User email
  "iat": 1704672000,              // Issued at (Unix timestamp)
  "exp": 1705276800,              // Expires at (Unix timestamp)
  "iss": "todoweb",               // Issuer
  "aud": "todoweb-api"            // Audience
}
```

**Critical Fields**:
- `sub`: User identifier - extracted as `user_id` in FastAPI
- `iat`: Issued at timestamp - for token age validation
- `exp`: Expiration timestamp - enforced by JWT library

## Token Transmission (Frontend → Backend)

### API Client Implementation

```typescript
// frontend/src/lib/api-client.ts
import { auth } from "./auth"

export async function apiClient<T>(
  endpoint: string,
  options: RequestInit = {}
): Promise<T> {
  // Get current session with JWT token
  const session = await auth.api.getSession()

  if (!session?.token) {
    throw new Error("Not authenticated")
  }

  const response = await fetch(
    `${process.env.NEXT_PUBLIC_API_URL}${endpoint}`,
    {
      ...options,
      headers: {
        ...options.headers,
        "Authorization": `Bearer ${session.token}`,
        "Content-Type": "application/json"
      }
    }
  )

  if (!response.ok) {
    if (response.status === 401) {
      // Token expired or invalid - redirect to login
      window.location.href = "/login"
      throw new Error("Authentication required")
    }
    throw new Error(`API error: ${response.status}`)
  }

  return response.json()
}
```

### Request Format

```http
GET /api/todos HTTP/1.1
Host: localhost:8000
Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...
Content-Type: application/json
```

## Token Verification (FastAPI)

### Middleware Implementation

```python
# backend/src/api/middleware/auth.py
from fastapi import HTTPException, Security
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from jose import jwt, JWTError
from typing import Annotated
import os

security = HTTPBearer()

def verify_token(
    credentials: Annotated[HTTPAuthorizationCredentials, Security(security)]
) -> dict:
    """
    Verify JWT token and extract payload
    Raises HTTPException(401) if token is invalid
    """
    token = credentials.credentials
    secret = os.getenv("BETTER_AUTH_SECRET")

    if not secret:
        raise HTTPException(
            status_code=500,
            detail="Server configuration error"
        )

    try:
        payload = jwt.decode(
            token,
            secret,
            algorithms=["HS256"],
            issuer="todoweb",
            audience="todoweb-api"
        )
        return payload
    except jwt.ExpiredSignatureError:
        raise HTTPException(
            status_code=401,
            detail="Token has expired"
        )
    except jwt.JWTClaimsError:
        raise HTTPException(
            status_code=401,
            detail="Invalid token claims"
        )
    except JWTError:
        raise HTTPException(
            status_code=401,
            detail="Invalid authentication token"
        )

def get_current_user_id(
    credentials: Annotated[HTTPAuthorizationCredentials, Security(security)]
) -> str:
    """
    Extract user_id from JWT token
    Used as FastAPI dependency for protected routes
    """
    payload = verify_token(credentials)
    user_id = payload.get("sub")

    if not user_id:
        raise HTTPException(
            status_code=401,
            detail="Invalid token: missing user ID"
        )

    return user_id
```

### Route Protection

```python
# backend/src/api/routes/todos.py
from fastapi import APIRouter, Depends
from typing import Annotated
from api.middleware.auth import get_current_user_id

router = APIRouter(prefix="/api/todos", tags=["todos"])

@router.get("/")
async def list_todos(
    user_id: Annotated[str, Depends(get_current_user_id)],
    session: AsyncSession = Depends(get_session)
):
    """
    List all todos for authenticated user
    user_id automatically extracted from JWT token
    """
    statement = select(Todo).where(Todo.user_id == user_id)
    result = await session.execute(statement)
    return result.scalars().all()
```

## Error Responses

### 401 Unauthorized

**Trigger**: Invalid, missing, or expired JWT token

```json
{
  "detail": "Invalid authentication token"
}
```

**HTTP Status**: 401 Unauthorized

**Frontend Handling**: Redirect to login page

### 403 Forbidden

**Trigger**: Valid token but insufficient permissions (not used in current implementation)

```json
{
  "detail": "Insufficient permissions"
}
```

**HTTP Status**: 403 Forbidden

## Security Considerations

### Shared Secret Management

1. **Environment Variables**: Store in `.env` file (never commit)
2. **Same Secret**: Must be identical in Next.js and FastAPI
3. **Secret Rotation**: Change secret requires re-authentication of all users
4. **Secret Strength**: Minimum 256 bits (32 characters)

```bash
# Generate secure secret
openssl rand -base64 32
```

### Token Security

1. **HTTPS Only**: Tokens must only be transmitted over HTTPS in production
2. **Storage**: Store tokens in memory or httpOnly cookies (not localStorage)
3. **Expiration**: 7-day expiration balances security and UX
4. **Refresh**: Implement token refresh before expiration (future enhancement)

### Attack Prevention

1. **Token Replay**: Expiration prevents indefinite token reuse
2. **Token Tampering**: HMAC signature prevents modification
3. **Token Theft**: HTTPS prevents man-in-the-middle attacks
4. **Brute Force**: Rate limiting on login endpoints (Better Auth handles)

## Testing Protocol

### Unit Tests

```python
# backend/tests/test_auth.py
import pytest
from jose import jwt
from datetime import datetime, timedelta

def test_valid_token():
    """Test that valid token is accepted"""
    secret = "test-secret"
    payload = {
        "sub": "user_123",
        "exp": datetime.utcnow() + timedelta(days=1)
    }
    token = jwt.encode(payload, secret, algorithm="HS256")
    # Assert token verification succeeds

def test_expired_token():
    """Test that expired token is rejected"""
    secret = "test-secret"
    payload = {
        "sub": "user_123",
        "exp": datetime.utcnow() - timedelta(days=1)
    }
    token = jwt.encode(payload, secret, algorithm="HS256")
    # Assert token verification raises 401

def test_invalid_signature():
    """Test that token with wrong signature is rejected"""
    token = jwt.encode({"sub": "user_123"}, "wrong-secret", algorithm="HS256")
    # Assert token verification raises 401

def test_missing_sub_claim():
    """Test that token without sub claim is rejected"""
    secret = "test-secret"
    payload = {"email": "user@example.com"}
    token = jwt.encode(payload, secret, algorithm="HS256")
    # Assert token verification raises 401
```

### Integration Tests

```python
# backend/tests/test_user_isolation.py
import pytest
from httpx import AsyncClient

async def test_user_cannot_access_other_user_todos():
    """Test that User A cannot access User B's todos"""
    # Create todo for User A
    user_a_token = create_test_token("user_a")
    response = await client.post(
        "/api/todos",
        json={"title": "User A's todo"},
        headers={"Authorization": f"Bearer {user_a_token}"}
    )
    todo_id = response.json()["id"]

    # Attempt to access with User B's token
    user_b_token = create_test_token("user_b")
    response = await client.get(
        f"/api/todos/{todo_id}",
        headers={"Authorization": f"Bearer {user_b_token}"}
    )

    # Assert 404 (not 403, to prevent information leakage)
    assert response.status_code == 404
```

## Environment Configuration

### Development (.env)

```bash
# Shared secret (same in both .env files)
BETTER_AUTH_SECRET=your-256-bit-secret-here

# Backend (FastAPI)
DATABASE_URL=postgresql+asyncpg://user:pass@host.neon.tech/db
API_PORT=8000
CORS_ORIGINS=http://localhost:3000

# Frontend (Next.js)
NEXT_PUBLIC_API_URL=http://localhost:8000
NEXTAUTH_URL=http://localhost:3000
DATABASE_URL=postgresql://user:pass@host.neon.tech/db
```

### Production

```bash
# Use environment variables from hosting platform
# Ensure BETTER_AUTH_SECRET is identical in both services
# Use HTTPS URLs for all endpoints
```

## Troubleshooting

### "Invalid authentication token"

**Causes**:
1. Token signed with different secret
2. Token expired
3. Token format incorrect

**Solution**: Verify BETTER_AUTH_SECRET matches in both services

### "Token has expired"

**Causes**:
1. Token older than 7 days
2. System clock skew

**Solution**: Re-authenticate user, check system time

### "Missing user ID"

**Causes**:
1. Token missing `sub` claim
2. Better Auth misconfigured

**Solution**: Verify Better Auth jwt() plugin configuration

## Next Steps

1. ✅ JWT protocol defined
2. ⏭️ Implement middleware in backend/src/api/middleware/auth.py
3. ⏭️ Configure Better Auth in frontend/src/lib/auth.ts
4. ⏭️ Test token generation and verification
