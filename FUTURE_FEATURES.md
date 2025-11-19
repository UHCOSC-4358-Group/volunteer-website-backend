# Future Features

## Refresh Token Implementation

### Overview
Add refresh token functionality to allow users to maintain longer sessions without requiring re-authentication, while keeping access tokens short-lived for security.

### Current State
- Single JWT access token with 1-hour expiration
- Cookie-based storage (`httponly=True`)
- PyJWT handles `exp` claim validation
- No refresh mechanism

### Proposed Changes

#### 1. Database Schema
Add `refresh_tokens` table to track valid refresh tokens:
```sql
CREATE TABLE refresh_tokens (
    id SERIAL PRIMARY KEY,
    user_id INT NOT NULL,
    user_type VARCHAR(10) NOT NULL,
    token_hash VARCHAR(255) NOT NULL,
    expires_at TIMESTAMP NOT NULL,
    created_at TIMESTAMP DEFAULT NOW(),
    revoked BOOLEAN DEFAULT FALSE
);
```

#### 2. New Functions in `src/dependencies/auth.py`
- `sign_refresh_token()` - Generate refresh token with longer expiration (e.g., 7 days)
- `verify_refresh_token()` - Validate refresh token and check if revoked
- `revoke_refresh_token()` - Invalidate token on logout
- `rotate_refresh_token()` - Issue new refresh token on use (security best practice)

#### 3. New API Endpoint
- `POST /auth/refresh` - Exchange refresh token for new access token

#### 4. Cookie Management Updates
Modify `sign_JWT_admin()` and `sign_JWT_volunteer()` to set two cookies:
- `access_token` - Short-lived (1 hour)
- `refresh_token` - Longer-lived (7 days), also `httponly`

### Design Decisions to Consider
1. **Session Duration**: How long should volunteers vs admins stay logged in?
2. **Revocation Strategy**: Do we need "logout everywhere" functionality?
3. **Token Rotation**: Should refresh tokens be single-use (more secure) or reusable?
4. **Database Migration**: Consider using Alembic for schema changes

### Estimated Effort
2-3 days including:
- Database schema design and migration
- Auth functions implementation
- API endpoint creation
- Testing updates
- Documentation

### Security Considerations
- Store hashed versions of refresh tokens in database
- Implement token rotation to prevent replay attacks
- Add rate limiting to refresh endpoint
- Consider device tracking for suspicious activity

### Related Files
- `src/dependencies/auth.py` - Core auth logic
- `src/routers/auth.py` - Auth endpoints
- `src/tests/api/test_auth_routes.py` - Auth testing
- Database models and migrations

---

## Logout Route Implementation

### Overview
Add a proper logout endpoint to invalidate user sessions and clear authentication cookies, providing a secure way for users to end their sessions.

### Current State
- No logout endpoint exists
- Cookies remain valid until expiration (1 hour)
- No way to invalidate tokens server-side

### Proposed Changes

#### 1. New API Endpoint in `src/routers/auth.py`
- `POST /auth/logout` - Clear authentication cookies and invalidate session

#### 2. Implementation Details
The logout route should:
- Clear the `access_token` cookie by setting it with `max_age=0`
- If refresh tokens are implemented, also clear `refresh_token` cookie
- If refresh tokens exist in database, mark them as revoked
- Return success response

#### 3. Enhanced Logout Options
**Basic Logout:**
- Clear cookies for current device/browser only
- Simple implementation without database changes

**Advanced Logout (requires refresh token feature):**
- `POST /auth/logout` - Logout current session
- `POST /auth/logout-all` - Revoke all refresh tokens for user (logout everywhere)

### Design Decisions to Consider
1. **Scope**: Should logout affect just the current session or all user sessions?
2. **Token Blacklisting**: Do we need to track invalidated access tokens? (Note: JWTs are stateless, so this requires additional infrastructure)
3. **Response Format**: Should logout return a simple success message or redirect?

### Implementation Without Refresh Tokens
Can be implemented immediately by clearing cookies:
```python
@router.post("/logout")
async def logout(response: Response):
    response.delete_cookie("access_token", path="/", samesite="lax")
    return {"message": "Successfully logged out"}
```

### Implementation With Refresh Tokens
Would include database operations to revoke tokens:
```python
@router.post("/logout")
async def logout(
    response: Response,
    current_user: UserTokenInfo = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    # Revoke refresh tokens in database
    # Clear both access_token and refresh_token cookies
    return {"message": "Successfully logged out"}
```

### Estimated Effort
- **Basic implementation**: 1-2 hours
- **With refresh token integration**: 4-6 hours (depends on refresh token implementation)

### Security Considerations
- Ensure cookie clearing uses same `path`, `samesite`, and `secure` settings as when set
- Consider logging logout events for audit trail
- Handle logout for both volunteer and admin user types

### Related Files
- `src/routers/auth.py` - Add logout endpoint
- `src/dependencies/auth.py` - May need cookie clearing helper function
- `src/tests/api/test_auth_routes.py` - Add logout tests

### Dependencies
- Can be implemented standalone as basic version
- Full implementation depends on refresh token feature for "logout everywhere" functionality

---

## Enhanced Error Handling System

### Overview
Implement a comprehensive error handling system that clearly separates client-side errors (4xx) from server-side errors (5xx), provides descriptive messages to clients while protecting sensitive information, and maintains detailed logging for debugging.

### Current State
- Basic [`DatabaseError`](src/util/error.py) exception class for HTTP hints
- Generic error handlers for HTTPException and RequestValidationError
- Catch-all middleware logs errors but returns generic "Internal server error"
- No distinction between client/server errors in logging
- Limited error context for debugging

### Problems to Solve
1. **Information Leakage**: Stack traces and internal details can be exposed to clients
2. **Poor Debugging**: Generic error messages make troubleshooting difficult
3. **Inconsistent Responses**: Different error types return different response formats
4. **No Error Tracking**: No correlation IDs or request tracing
5. **Limited Context**: Errors don't capture enough information about request state

### Proposed Changes

#### 1. Enhanced Error Classes in `src/util/error.py`

````python
from typing import Any, Dict, Optional
import uuid
from datetime import datetime

class BaseAPIError(Exception):
    """Base class for all API errors with tracking"""
    def __init__(
        self,
        status_code: int,
        message: str,
        detail: Optional[str] = None,
        error_code: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ):
        self.status_code = status_code
        self.message = message  # Client-safe message
        self.detail = detail    # Internal detail (not sent to client)
        self.error_code = error_code
        self.metadata = metadata or {}
        self.error_id = str(uuid.uuid4())
        self.timestamp = datetime.utcnow()
        super().__init__(self.message)

class ClientError(BaseAPIError):
    """4xx errors - client mistakes"""
    pass

class ServerError(BaseAPIError):
    """5xx errors - server issues"""
    pass

# Specific error types
class ValidationError(ClientError):
    def __init__(self, message: str, fields: Optional[Dict] = None):
        super().__init__(
            status_code=422,
            message=message,
            error_code="VALIDATION_ERROR",
            metadata={"fields": fields} if fields else {}
        )

class AuthenticationError(ClientError):
    def __init__(self, message: str = "Authentication failed"):
        super().__init__(
            status_code=401,
            message=message,
            error_code="AUTH_ERROR"
        )

class AuthorizationError(ClientError):
    def __init__(self, message: str = "Insufficient permissions"):
        super().__init__(
            status_code=403,
            message=message,
            error_code="FORBIDDEN"
        )

class NotFoundError(ClientError):
    def __init__(self, resource: str, identifier: Any):
        super().__init__(
            status_code=404,
            message=f"{resource} not found",
            error_code="NOT_FOUND",
            metadata={"resource": resource, "id": str(identifier)}
        )

class ConflictError(ClientError):
    def __init__(self, message: str):
        super().__init__(
            status_code=409,
            message=message,
            error_code="CONFLICT"
        )

class DatabaseOperationError(ServerError):
    def __init__(self, operation: str, detail: str):
        super().__init__(
            status_code=500,
            message="Database operation failed",
            detail=f"Operation '{operation}' failed: {detail}",
            error_code="DB_ERROR",
            metadata={"operation": operation}
        )

class ExternalServiceError(ServerError):
    def __init__(self, service: str, detail: str):
        super().__init__(
            status_code=503,
            message="External service unavailable",
            detail=f"Service '{service}' error: {detail}",
            error_code="SERVICE_ERROR",
            metadata={"service": service}
        )
`````

#### 2. New Middleware for Error Handling
Add middleware to catch exceptions and convert to API errors:
```python
from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware

class ErrorHandlingMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        try:
            response: Response = await call_next(request)
            return response
        except BaseAPIError as api_error:
            # Handle known API errors
            return JSONResponse(
                status_code=api_error.status_code,
                content={
                    "error": {
                        "code": api_error.error_code,
                        "message": api_error.message,
                        "details": api_error.detail,
                        "request_id": api_error.error_id
                    }
                }
            )
        except Exception as ex:
            # Handle unexpected errors
            return JSONResponse(
                status_code=500,
                content={
                    "error": {
                        "code": "INTERNAL_SERVER_ERROR",
                        "message": "An unexpected error occurred",
                        "request_id": str(uuid.uuid4())
                    }
                }
            )
```

#### 3. Logging Enhancements
- Log error details at appropriate levels (e.g., `error`, `warning`, `info`)
- Include request context in logs (e.g., request ID, user ID)
- Optionally integrate with external logging/monitoring services (e.g., Sentry, Loggly)

### Estimated Effort
1-2 days including:
- Error class implementation
- Middleware development
- Logging configuration
- Testing error scenarios
- Documentation

### Security Considerations
- Ensure no sensitive information is leaked in error responses
- Rate limit error-prone endpoints to prevent abuse
- Monitor logs for unusual error patterns (e.g., spikes in 5xx errors)

### Related Files
- `src/util/error.py` - Error class definitions
- `src/middleware/error_handling.py` - Error handling middleware
- `src/tests/unit/test_error_handling.py` - Unit tests for error handling