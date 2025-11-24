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

## Geocoding and Distance Calculation with Normalized Location Table

### Status: ✅ COMPLETED (Database Schema & Models)

### Overview
Implement geospatial functionality with a normalized `Location` table using PostgreSQL and PostGIS extension to store geographic information (address, coordinates) separately. This approach eliminates data duplication since multiple entities (volunteers, events, organizations) share the same location model structure.

### Completed Work

#### ✅ Database Schema
- Created `location` table with PostGIS `GEOGRAPHY(POINT, 4326)` type
- Implemented foreign key relationships:
  - Volunteer → Location (SET NULL on delete - optional location)
  - Event → Location (RESTRICT on delete - required location)
  - Organization → Location (RESTRICT on delete - required location)
- Added `created_at` and `updated_at` timestamps
- Created spatial GIST index on `coordinates` column for optimal query performance

#### ✅ SQLAlchemy Models (src/models/dbmodels.py)
```python
class Location(Base):
    __tablename__ = "location"
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    address: Mapped[str] = mapped_column(String(255), nullable=False)
    city: Mapped[str] = mapped_column(String(100), nullable=True)
    state: Mapped[str] = mapped_column(String(50), nullable=True)
    zip_code: Mapped[str] = mapped_column(String(20), nullable=True)
    country: Mapped[str] = mapped_column(String(100), default="USA", server_default="USA")
    coordinates: Mapped[str] = mapped_column(Geography(geometry_type="POINT", srid=4326), nullable=True)
    created_at: Mapped[datetime]
    updated_at: Mapped[datetime]
    
    # Relationships established with all entity types
```

#### ✅ Technology Stack
- **Database**: PostgreSQL (migrated from SQLite)
- **Spatial Extension**: PostGIS for native geospatial support
- **ORM Integration**: GeoAlchemy2 for PostGIS types in SQLAlchemy
- **Coordinate System**: WGS84 (SRID 4326) - standard for GPS coordinates

### Current State
- ✅ Location table created and integrated
- ✅ All models updated to use `location_id` foreign keys
- ✅ PostGIS extension enabled
- ✅ Spatial indexing configured
- ⏳ No data migration needed (empty database)
- ❌ Geocoding service not yet integrated
- ❌ Distance calculation functions not yet implemented
- ❌ Location CRUD operations not yet implemented
- ❌ API endpoints not yet created
- ❌ Matching algorithm not yet updated

### Benefits of PostgreSQL + PostGIS Approach

1. **Native Spatial Types**
   - `GEOGRAPHY(POINT)` type handles Earth's curvature automatically
   - No manual Haversine formula needed
   - More accurate distance calculations

2. **Performance**
   - GIST spatial indexes provide 10-100x faster queries than lat/lon indexes
   - Built-in spatial query optimization
   - Efficient radius searches

3. **Simplified Queries**
   - `ST_Distance()` - Calculate distance between points
   - `ST_DWithin()` - Find points within radius (uses index automatically)
   - `ST_MakePoint()` - Create point geometries
   - No complex mathematical formulas in application code

4. **Industry Standard**
   - PostGIS used by Uber, Foursquare, and major mapping services
   - Extensive documentation and community support
   - Compatible with GIS tools and standards

### Next Steps

#### Phase 1: Location CRUD Operations (Priority: HIGH)
Implement basic location management:
- `get_or_create_location()` - Find existing or create new location
- `update_location()` - Update location details and coordinates
- `delete_location()` - Handle location deletion with foreign key constraints
- `get_location_by_id()` - Retrieve location with relationships

**Estimated Effort**: 1-2 days

#### Phase 2: Geospatial Query Functions (Priority: HIGH)
Leverage PostGIS for distance calculations:
```python
# src/dependencies/database/geospatial.py

def get_volunteers_within_radius(
    db: Session,
    center_lat: float,
    center_lon: float,
    radius_miles: float,
    distance_type: Literal["km", "mile"] = "mile"
) -> list[tuple[Volunteer, float]]:
    """
    Uses ST_DWithin with GIST index for optimal performance.
    """
    pass

def get_events_within_radius(
    db: Session,
    center_lat: float,
    center_lon: float,
    radius_miles: float
) -> list[tuple[Event, float]]:
    """
    Returns events sorted by distance.
    """
    pass
```

**Estimated Effort**: 2-3 days

#### Phase 3: Geocoding Integration (Priority: MEDIUM)
Integrate external geocoding service:
- Choose provider (Mapbox, Google Maps, or Nominatim)
- Implement `geocode_address()` function
- Add error handling and retry logic
- Configure rate limiting

**Estimated Effort**: 2-3 days

#### Phase 4: Enhanced Matching Algorithm (Priority: MEDIUM)
Update `match_volunteers_to_event()` in `relations.py`:
- Replace location string comparison with distance calculation
- Add distance weighting to scoring algorithm
- Filter volunteers within configurable radius
- Sort results by composite score (skills + schedule + distance)

**Estimated Effort**: 1-2 days

#### Phase 5: API Endpoints (Priority: LOW)
Create location-related endpoints:
```python
# src/routers/location.py

POST /locations/geocode
# Input: address components
# Output: coordinates

GET /locations/{location_id}
# Output: full location details

GET /events/nearby?lat={lat}&lon={lon}&radius={miles}
# Output: events within radius

GET /volunteers/nearby?lat={lat}&lon={lon}&radius={miles}  
# Output: volunteers within radius (admin only)
```

**Estimated Effort**: 2-3 days

#### Phase 6: Testing & Documentation (Priority: HIGH)
- Unit tests for location CRUD operations
- Integration tests for geospatial queries
- Mock geocoding API in tests
- Update API documentation
- Add configuration examples

**Estimated Effort**: 2-3 days

### Design Decisions Made

✅ **Location Storage Strategy**
- **Decision**: Use single `coordinates` column (PostGIS GEOGRAPHY type)
- **Rationale**: PostGIS handles all geospatial operations natively
- **Trade-off**: Removed separate `latitude` and `longitude` columns to avoid duplication

✅ **Foreign Key Constraints**
- **Volunteer**: `SET NULL` - Volunteers can exist without location
- **Event**: `RESTRICT` - Events require location, prevent accidental deletion
- **Organization**: `RESTRICT` - Organizations require location

✅ **Coordinate System**
- **Decision**: WGS84 (SRID 4326)
- **Rationale**: Standard GPS coordinate system, compatible with all mapping services

✅ **Database Choice**
- **Decision**: PostgreSQL with PostGIS
- **Rationale**: Native spatial support, much better performance than SQLite for geospatial queries

### Outstanding Design Decisions

❓ **Geocoding Strategy**
- **Options**:
  1. Geocode immediately on location creation (simpler, always available)
  2. Geocode on first access/lazy loading (faster writes)
  3. Background job after creation (best performance, more complex)
- **Recommendation**: Start with option 1, consider background jobs if performance becomes issue

❓ **Geocoding Provider**
- **Options**:
  1. **Mapbox** - Good accuracy, 100k free requests/month
  2. **Google Maps** - Most accurate, $200 free credit/month
  3. **Nominatim (OSM)** - Free, open source, but rate-limited
- **Recommendation**: Mapbox for balance of cost and features

❓ **Error Handling for Geocoding Failures**
- Should events be created with just address but no coordinates?
- Should we fail the entire creation if geocoding fails?
- **Recommendation**: Allow creation with `coordinates = NULL`, retry geocoding in background

❓ **Location Sharing vs Duplication**
- Should multiple entities share same `Location` record?
- Or should each entity get its own `Location` record?
- **Recommendation**: Share locations where address matches (use `get_or_create_location()`), but allow flexibility

❓ **Privacy for Volunteer Locations**
- Should we store exact addresses for volunteers?
- Consider storing only zip code centroids for privacy
- Who should have access to precise volunteer locations?
- **Recommendation**: Store full address but add privacy controls in API layer

### Configuration Needed

Add to `.env`:
```
# Geocoding
GEOCODING_PROVIDER=mapbox
MAPBOX_API_KEY=your_api_key_here
GEOCODING_RATE_LIMIT=50

# Distance defaults
MAX_DISTANCE_FOR_MATCHING=50
DEFAULT_DISTANCE_UNIT=mile

# Feature flags
GEOCODE_ON_CREATE=true
ALLOW_NULL_COORDINATES=true
```

### Required Dependencies

Already added to `requirements.txt`:
```
geoalchemy2>=0.14.0
psycopg2-binary>=2.9.9
```

Still needed:
```
httpx>=0.24.0              # For geocoding API calls
```

### Testing Considerations

**Spatial Query Testing:**
- Test distance calculations with known coordinates
- Test radius searches with various distances
- Test GIST index performance with large datasets
- Mock geocoding API in unit tests

**Edge Cases:**
- Null coordinates handling
- Invalid coordinate values
- Events/volunteers at same location
- Locations near poles (edge case for spherical calculations)

### Performance Considerations

✅ **Already Implemented:**
- GIST spatial index on `coordinates`
- Native PostGIS distance calculations

🔄 **Still Needed:**
- Geocoding result caching
- API rate limiting
- Query result caching for popular searches
- Consider materialized views for frequent queries

### Related Files

**Completed:**
- ✅ `src/models/dbmodels.py` - Location model and relationships
- ✅ Database schema - PostGIS-enabled PostgreSQL

**In Progress:**
- 🔄 `src/models/pydanticmodels.py` - Need Location schemas
- 🔄 `src/dependencies/database/crud.py` - Need location CRUD operations

**Not Started:**
- ❌ `src/util/geocoding.py` - Geocoding utilities
- ❌ `src/dependencies/database/geospatial.py` - Distance queries
- ❌ `src/routers/location.py` - Location API endpoints
- ❌ `src/dependencies/database/relations.py` - Update matching algorithm
- ❌ `src/tests/database/test_geospatial.py` - Spatial query tests

### Resources & Documentation

- [PostGIS Documentation](https://postgis.net/documentation/)
- [GeoAlchemy2 Documentation](https://geoalchemy-2.readthedocs.io/)
- [Mapbox Geocoding API](https://docs.mapbox.com/api/search/geocoding/)
- [Understanding SRID 4326](https://epsg.io/4326)

### Notes
- No data migration needed as database is empty
- Removed `latitude` and `longitude` columns to avoid duplication with `coordinates`
- PostGIS handles coordinate extraction when needed: `ST_X(coordinates)`, `ST_Y(coordinates)`

---

## Enhanced Volunteer-Event Matching with Distance Filtering

### Status: 🔄 IN PROGRESS (Ready for Implementation)

### Overview
Upgrade the `match_volunteers_to_event()` function to use a two-phase matching process:
1. **Phase 1**: Filter volunteers within a configurable radius using PostGIS
2. **Phase 2**: Score filtered volunteers based on distance, skills, and schedule

This approach combines the efficiency of spatial indexing with comprehensive scoring.

### Current State
- ✅ Location table with PostGIS support exists
- ✅ `scoring.py` has modular scoring components
- ✅ `geocoding.py` provides address-to-coordinates conversion
- ✅ `geospatial.py` has `get_volunteers_within_radius()` function
- ❌ Old `match_volunteers_to_event()` uses string comparison for location
- ❌ Distance not factored into scoring algorithm

### Proposed Architecture

#### Phase 1: Spatial Filtering (Database Layer)
```python
# src/dependencies/database/geospatial.py

def get_volunteers_within_radius(
    db: Session,
    center_lat: float,
    center_lon: float,
    radius_miles: float,
    distance_type: Literal["km", "mile"] = "mile"
) -> list[tuple[Volunteer, float]]:
    """
    Uses PostGIS ST_DWithin for efficient spatial filtering.
    
    Returns:
        List of (Volunteer, distance) tuples within radius.
        Distance is in the specified unit (km or miles).
    """
    # Uses GIST index for fast spatial lookup
    # Calculates actual distance for each result
    # Returns sorted by distance (closest first)
```

**Benefits:**
- Uses spatial index for O(log n) performance
- Reduces candidates before complex scoring
- Filters out volunteers too far away immediately

#### Phase 2: Composite Scoring (Application Layer)
```python
# src/dependencies/database/relations.py

def match_volunteers_to_event_enhanced(
    db: Session,
    event_id: int,
    admin_id: int,
    max_distance: float = 25.0,
    distance_unit: Literal["km", "mile"] = "mile"
) -> list[tuple[Volunteer, float, dict]]:
    """
    Two-phase matching process:
    1. Spatial filter: Get volunteers within max_distance
    2. Composite scoring: Calculate skills + schedule + distance scores
    
    Args:
        db: Database session
        event_id: Event to match volunteers to
        admin_id: Admin making the request (for auth)
        max_distance: Maximum search radius
        distance_unit: Unit for distance (km or mile)
    
    Returns:
        List of (Volunteer, total_score, score_breakdown) tuples
        sorted by total_score descending.
        
        score_breakdown = {
            "distance_score": float,  # 0-4 points
            "skills_score": int,      # 0-2 points
            "schedule_score": int,    # 0-4 points
            "total": float            # 0-10 points
        }
    """
```

### Implementation Steps

#### Step 1: Update `match_volunteers_to_event()` Function
Replace the existing function in `relations.py`:
```python
def match_volunteers_to_event(
    db: Session,
    event_id: int,
    admin_id: int,
    max_distance: float = 25.0,
    distance_unit: Literal["km", "mile"] = "mile"
) -> list[tuple[Volunteer, float, dict]]:
    """
    Enhanced matching with distance filtering:
    1. Filter volunteers within max_distance using geospatial query
    2. Score based on skills, schedule, and distance
    
    Args:
        db: Database session
        event_id: Event ID to match volunteers to
        admin_id: Admin ID (for permissions)
        max_distance: Maximum distance to consider (configurable)
        distance_unit: Unit for distance (kilometers or miles)
    
    Returns:
        List of tuples containing Volunteer object, distance, and score breakdown:
        - distance_score: 0-4 points based on closeness
        - skills_score: 0-2 points based on skill match
        - schedule_score: 0-4 points based on availability
        - total: 0-10 total points
    """
    # 1. Spatial filtering: Get volunteers within max_distance
    volunteer_distances = get_volunteers_within_radius(
        db=db,
        center_lat=center_coordinates.latitude,
        center_lon=center_coordinates.longitude,
        radius_miles=max_distance,
        distance_type=distance_unit
    )
    
    # 2. Score calculation for filtered volunteers
    results = []
    for volunteer, distance in volunteer_distances:
        # Calculate individual scores (0-4 scale)
        distance_score = max(0, 4 - distance / 10)  # Closer is better
        skills_score = calculate_skills_score(volunteer, event)
        schedule_score = calculate_schedule_score(volunteer, event)
        
        # Total score (0-10 scale)
        total_score = distance_score + skills_score + schedule_score
        
        # Score breakdown for analysis
        score_breakdown = {
            "distance_score": distance_score,
            "skills_score": skills_score,
            "schedule_score": schedule_score,
            "total": total_score
        }
        
        results.append((volunteer, total_score, score_breakdown))
    
    # Sort by total score (highest first)
    results.sort(key=lambda x: x[1], reverse=True)
    return results
```

#### Step 2: Update Tests
- Add unit tests for `get_volunteers_within_radius()`
- Update integration tests for `match_volunteers_to_event_enhanced()`
- Mock geocoding and distance functions as needed

#### Step 3: Update Documentation
- Update API documentation for new endpoint
- Add configuration examples for distance settings
- Document database changes and migration steps

### Estimated Effort
- **Function implementation**: 2-3 hours
- **Testing**: 1-2 hours
- **Documentation**: 1 hour

### Security Considerations
- Validate and sanitize all inputs to `match_volunteers_to_event_enhanced()`
- Ensure proper authentication and authorization for admin actions
- Rate limit the new API endpoint to prevent abuse

### Related Files
- `src/dependencies/database/geospatial.py` - New spatial query functions
- `src/dependencies/database/relations.py` - Updated matching function
- `src/tests/database/test_geospatial.py` - New tests for geospatial queries
- `src/tests/database/test_relations.py` - Updated tests for matching function