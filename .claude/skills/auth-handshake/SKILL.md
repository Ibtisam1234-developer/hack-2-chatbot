---
name: auth-handshake
description: Protocol for cross-language authentication between Next.js and FastAPI.
---

# Authentication Protocol

## Overview

This skill defines the JWT authentication handshake protocol between Better Auth (Next.js frontend) and FastAPI (Python backend), ensuring secure token generation, transmission, and verification with a shared secret.

## Token Generation (Frontend - Better Auth)

1. **Token Generation**: Better Auth (Frontend) must use the `jwt()` plugin to issue a signed JWT.

   ```typescript
   // frontend/src/lib/auth.ts
   import { betterAuth } from "better-auth"
   import { jwt } from "better-auth/plugins"

   export const auth = betterAuth({
     secret: process.env.BETTER_AUTH_SECRET!,
     plugins: [
       jwt({
         expiresIn: "7d",
         algorithm: "HS256",
         issuer: "todoweb",
         audience: "todoweb-api"
       })
     ]
   })
   ```

2. **Secret Synchronization**: Both services must use the `BETTER_AUTH_SECRET` environment variable.
   - **Critical**: The secret MUST be identical in both `.env` files
   - Generate using: `openssl rand -base64 32`
   - Length: Exactly 44 characters (base64 encoded 32 bytes)
   - Never commit to version control

3. **Token Structure**: Generated JWT contains:
   ```json
   {
     "sub": "user_123abc",      // User ID (authoritative)
     "email": "user@example.com",
     "iat": 1704672000,          // Issued at
     "exp": 1705276800,          // Expires at
     "iss": "todoweb",           // Issuer
     "aud": "todoweb-api"        // Audience
   }
   ```

## Token Transmission (Frontend → Backend)

3. **Transmission**: The Frontend must send the token in the `Authorization: Bearer <token>` header.

   ```typescript
   // frontend/src/lib/api-client.ts
   export async function apiClient<T>(endpoint: string, options: RequestInit = {}): Promise<T> {
     const session = await auth.api.getSession()

     if (!session?.token) {
       throw new Error("Not authenticated")
     }

     const response = await fetch(`${process.env.NEXT_PUBLIC_API_URL}${endpoint}`, {
       ...options,
       headers: {
         ...options.headers,
         "Authorization": `Bearer ${session.token}`,
         "Content-Type": "application/json"
       }
     })

     if (!response.ok) {
       if (response.status === 401) {
         window.location.href = "/login"
         throw new Error("Authentication required")
       }
       throw new Error(`API error: ${response.status}`)
     }

     return response.json()
   }
   ```

## Token Verification (Backend - FastAPI)

4. **Verification**: The Backend (FastAPI) must decode the token using `python-jose` (Algorithm: HS256).

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
           raise HTTPException(status_code=500, detail="Server configuration error")

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
           raise HTTPException(status_code=401, detail="Token has expired")
       except jwt.JWTClaimsError:
           raise HTTPException(status_code=401, detail="Invalid token claims")
       except JWTError:
           raise HTTPException(status_code=401, detail="Invalid authentication token")
   ```

5. **Identity**: Extract the `sub` field from the JWT; this is the authoritative `user_id`.

   ```python
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
           raise HTTPException(status_code=401, detail="Invalid token: missing user ID")

       return user_id
   ```

## Route Protection Pattern

Use `get_current_user_id` as a dependency in all protected routes:

```python
# backend/src/api/routes/todos.py
from fastapi import APIRouter, Depends
from typing import Annotated

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

## Error Handling

### 401 Unauthorized
**Trigger**: Invalid, missing, or expired JWT token

**Backend Response**:
```json
{
  "detail": "Invalid authentication token"
}
```

**Frontend Handling**: Redirect to login page

### 403 Forbidden
**Trigger**: Valid token but insufficient permissions

**Backend Response**:
```json
{
  "detail": "Insufficient permissions"
}
```

## Security Checklist

- [ ] BETTER_AUTH_SECRET is identical in both services
- [ ] Secret is 44 characters (base64 encoded 32 bytes)
- [ ] Secret is stored in .env (never committed)
- [ ] Frontend sends token in Authorization header
- [ ] Backend verifies token signature
- [ ] Backend validates issuer and audience claims
- [ ] Backend extracts user_id from sub claim
- [ ] All protected routes use get_current_user_id dependency
- [ ] 401 errors redirect to login page
- [ ] HTTPS is used in production

## Testing Protocol

### Unit Tests

```python
# backend/tests/test_auth.py
def test_valid_token():
    """Test that valid token is accepted"""
    secret = "test-secret"
    payload = {"sub": "user_123", "exp": datetime.utcnow() + timedelta(days=1)}
    token = jwt.encode(payload, secret, algorithm="HS256")
    # Assert token verification succeeds

def test_expired_token():
    """Test that expired token is rejected"""
    secret = "test-secret"
    payload = {"sub": "user_123", "exp": datetime.utcnow() - timedelta(days=1)}
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

## References

- Better Auth JWT Plugin: https://better-auth.com/docs/plugins/jwt
- python-jose Documentation: https://python-jose.readthedocs.io/
- JWT RFC 7519: https://tools.ietf.org/html/rfc7519
