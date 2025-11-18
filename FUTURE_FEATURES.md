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