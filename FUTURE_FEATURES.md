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

### Implementation Progress

#### ✅ Phase 1: Core Infrastructure (COMPLETED)
- ✅ Created error class hierarchy in `src/util/error.py`
- ✅ Implemented `ErrorHandlingMiddleware`
- ✅ All error classes follow consistent pattern

#### ✅ Phase 2: Registration & Configuration (COMPLETED)
- ✅ Registered `ErrorHandlingMiddleware` in `src/main.py`
- ✅ Removed old `catch_all_exceptions_middleware`
- ✅ Middleware properly catches and handles all exceptions

#### ✅ Phase 3: Database Layer Migration (COMPLETED)
- ✅ Migrated all 9 functions in `src/dependencies/database/crud.py`
  - Replaced `DatabaseError` with specific error classes
  - `NotFoundError` for missing resources
  - `AuthorizationError` for permission issues
  - `ValidationError` for invalid data
  - `DatabaseOperationError` for database failures
- ✅ Migrated all 5 functions in `src/dependencies/database/relations.py`
  - `ConflictError` for duplicate signups
  - `ValidationError` for capacity violations
- ✅ Updated all database tests in `src/tests/database/`
  - `test_crud.py` - All tests passing ✅
  - `test_relations.py` - All tests passing ✅

#### ✅ Phase 4: Router Layer Migration (COMPLETED)
- ✅ Migrated `src/routers/auth.py`
  - Authentication errors use `AuthenticationError`
  - Authorization checks use `AuthorizationError`
  - Not found cases use `NotFoundError`
  - Removed unnecessary try/except blocks
- ✅ Migrated `src/routers/event.py`
  - Clean authorization checks
  - Proper error propagation to middleware
- ✅ Migrated `src/routers/org.py`
  - Consistent error handling pattern
- ✅ Migrated `src/routers/volunteer.py`
  - Fixed logic error in authorization check (line 41)
  - Proper permission validation
- ✅ All API tests passing in `src/tests/api/test_event_routes.py`

#### 🔄 Phase 5: AWS Operations Migration (NEXT - OPTIONAL)
**Priority: Medium** - Can be skipped if AWS operations are stable

**Files to Update:**
- `src/dependencies/aws.py` - S3 operations

**Current Issues:**
- Generic `HTTPException(500)` for environment variable errors
- Generic `HTTPException(422)` for validation errors
- No error handling for S3 operation failures

**Proposed Changes:**
Replace generic exceptions with specific error classes:
```python
from ..util.error import ExternalServiceError, ValidationError

# Environment errors become ExternalServiceError
if None in [AWS_ACCESS_KEY, AWS_SECRET_KEY, AWS_BUCKET_NAME]:
    raise ExternalServiceError("AWS_S3", "Required AWS credentials not configured")

# Validation errors become ValidationError
if file_extension not in ["jpg", "jpeg", "png", ...]:
    raise ValidationError(
        "Invalid file format",
        {"file": f"Format .{file_extension} not supported"}
    )

# S3 operation failures become ExternalServiceError
try:
    s3.upload_fileobj(...)
except Exception as e:
    raise ExternalServiceError("AWS_S3", f"Failed to upload image: {str(e)}")
```

**Estimated Time:** 1-2 hours

#### 🔄 Phase 6: Authentication Layer Migration (NEXT - RECOMMENDED)
**Priority: High** - Fixes 401 vs 403 semantic issue

**The Problem You Identified:**
Currently, authentication failures (missing token, expired token, invalid token) return **403 Forbidden** instead of **401 Unauthorized**. This is semantically incorrect:
- **401** = "You need to authenticate" → should prompt login
- **403** = "You're authenticated but not allowed" → show access denied

**Why This Matters:**
- Browsers and API clients handle these differently
- 401 often triggers authentication flows
- 403 is treated as a "final answer"
- Frontend should redirect to login on 401, show error on 403

**Files to Update:**
- `src/dependencies/auth.py` - JWT validation and bearer token handling

**Current Problematic Code:**
```python
# Line 79-84: Token validation
except jwt.ExpiredSignatureError:
    raise HTTPException(status_code=403, detail="Expired token!")
except jwt.InvalidTokenError:
    raise HTTPException(status_code=403, detail="Invalid token!")

# Line 106, 129: Missing/invalid tokens
if not token:
    raise HTTPException(status_code=403, detail="Invalid authorization code!")
```

**Should Become:**
```python
from ..util.error import AuthenticationError, ExternalServiceError

def decodeJWT(token: str):
    try:
        if JWT_SECRET is None:
            raise ExternalServiceError("JWT", "JWT secret not configured")
        decoded_token = jwt.decode(token, JWT_SECRET, algorithms=ALGORITHMS)
        return decoded_token
    except jwt.ExpiredSignatureError:
        raise AuthenticationError("Token has expired - please log in again")
    except jwt.InvalidTokenError:
        raise AuthenticationError("Invalid token credentials")
    except Exception:
        raise AuthenticationError("Token validation failed")

class JWTBearer(HTTPBearer):
    async def __call__(self, request: Request) -> str | None:
        token = request.cookies.get("access_token")
        if not token:
            credentials = await super().__call__(request)
            if credentials and credentials.scheme == "Bearer":
                token = credentials.credentials

        if not token:
            raise AuthenticationError("No authentication token provided")

        if not self.verify_jwt(token):
            raise AuthenticationError("Invalid or expired token")

        return token

async def get_current_user(token: str = Depends(JWTBearer())):
    payload = decodeJWT(token)
    if not payload:
        raise AuthenticationError("Invalid token payload")

    user_id: int | None = payload.get("userId")
    user_type: str | None = payload.get("userType")
    if not user_id or not user_type:
        raise AuthenticationError("Token missing required claims")

    return UserTokenInfo(user_id=user_id, user_type=user_type)
```

**Additional Locations to Check:**
- Line 62, 77: `HTTPException(500)` for missing JWT_SECRET → `ExternalServiceError`
- Any other places raising `HTTPException` in auth flow

**Testing Considerations:**
After this change, your frontend should:
- Redirect to login on 401 responses
- Show "access denied" message on 403 responses
- Update any tests expecting 403 for authentication failures to expect 401

**Estimated Time:** 2-3 hours including tests

#### ⏸️ Phase 7: Final Cleanup (AFTER ALL MIGRATIONS)
**Priority: Low** - Only after confirming everything works

- [ ] Deprecate `DatabaseError` class with warning
- [ ] Remove old exception handlers if no longer needed
- [ ] Update documentation with new error response format
- [ ] Add API documentation for error codes

---

### Current Status Summary

**✅ Completed (Phases 1-4):**
- Core error infrastructure built
- Database layer fully migrated and tested
- Router layer fully migrated and tested
- All tests passing
- Code is cleaner and more maintainable

**🎯 Recommended Next Steps:**

**Option A: Phase 6 (Authentication Layer)** - **RECOMMENDED**
- **Why**: Fixes important semantic issue you identified (401 vs 403)
- **Impact**: Improves API correctness and client behavior
- **Time**: 2-3 hours
- **Risk**: Low - well-defined changes

**Option B: Phase 5 (AWS Operations)** - **OPTIONAL**
- **Why**: Makes AWS errors more descriptive
- **Impact**: Better error messages for file upload failures
- **Time**: 1-2 hours
- **Risk**: Very low - AWS code is isolated

**Option C: Skip to Phase 7 (Cleanup)** - **NOT RECOMMENDED YET**
- **Why**: Should wait until authentication layer is fixed
- **Impact**: Removes old code, final polish
- **Time**: 1-2 hours
- **Risk**: None if other phases complete

### Design Questions to Consider

**For Phase 6 (Authentication):**

1. **Frontend Impact**: Does your React frontend currently handle 403 from auth failures?
   - Will it need updates to handle 401 correctly?
   - Do you have a login redirect flow that triggers on 401?

2. **Token Expiration UX**: When a token expires (currently 403), what should happen?
   - Automatic redirect to login?
   - Show a "session expired" message first?
   - Try to refresh the token (if refresh tokens are implemented)?

3. **Error Messages**: Should different auth failures have different messages?
   - "Token expired" vs "Invalid token" vs "No token provided"
   - Or generic "Please log in again" for all?

**For Phase 5 (AWS):**

1. **File Upload Errors**: What should users see when file upload fails?
   - Generic "Upload failed, try again"?
   - Specific error (e.g., "File too large", "Invalid format")?

2. **AWS Configuration**: Should missing AWS credentials crash the app or fail gracefully?
   - Current: Returns 500 error
   - Better: Log error and use ExternalServiceError

### Estimated Total Time Remaining
- Phase 5 (AWS): 1-2 hours
- Phase 6 (Auth): 2-3 hours
- Phase 7 (Cleanup): 1-2 hours
- **Total: 4-7 hours** (about 1 day of focused work)

### Questions for Understanding

To help you decide what to tackle next:

1. **Which issue impacts your users more?**
   - Incorrect HTTP status codes (401 vs 403)?
   - File upload error messages?

2. **What's your frontend's current behavior?**
   - Does it already distinguish between 401 and 403?
   - Or does it treat all auth errors the same?

3. **What's your deployment timeline?**
   - Need to ship soon → Skip Phase 5, do Phase 6
   - Have time → Do both Phase 5 and 6
   - Just learning → Do everything for completeness

---

### Benefits Achieved So Far

1. ✅ **Better Debugging**: Error IDs allow tracing specific issues
2. ✅ **Security**: Sensitive details stay in logs, not API responses
3. ✅ **Consistency**: All errors follow same JSON structure
4. ✅ **Cleaner Code**: Removed unnecessary try/except blocks in routers
5. ✅ **Type Safety**: Using specific error classes instead of generic exceptions
6. ✅ **Easier Testing**: Tests check specific error types, not just status codes

### Related Files

**✅ Completed:**
- `src/util/error.py` - Error class definitions
- `src/main.py` - Middleware registration
- `src/dependencies/database/crud.py` - 9 functions migrated
- `src/dependencies/database/relations.py` - 5 functions migrated
- `src/routers/auth.py` - 8 error sites updated
- `src/routers/event.py` - 8 error sites updated
- `src/routers/org.py` - 4 error sites updated
- `src/routers/volunteer.py` - 1 error site updated
- `src/tests/database/test_crud.py` - All tests passing
- `src/tests/database/test_relations.py` - All tests passing
- `src/tests/api/test_event_routes.py` - All tests passing

**🔄 Remaining:**
- `src/dependencies/aws.py` - Phase 5
- `src/dependencies/auth.py` - Phase 6
- Documentation updates - Phase 7