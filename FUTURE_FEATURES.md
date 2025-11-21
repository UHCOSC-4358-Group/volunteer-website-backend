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

### Overview
Implement geocoding functionality with a normalized `Location` table to store geographic information (address, latitude, longitude) separately. This approach eliminates data duplication since multiple entities (volunteers, events, organizations) share the same location model structure.

### Current State
- Event, Volunteer, and Organization models each have a `location: str` field
- No coordinate storage or distance calculation capability
- Location data is duplicated across tables
- Matching algorithm in `match_volunteers_to_event()` doesn't consider location

### Why a Separate Location Table?
**Benefits:**
1. **DRY Principle**: Avoid repeating latitude, longitude, and address fields in every table
2. **Data Integrity**: Consistent location format across all entities
3. **Efficient Updates**: Update geocoding logic in one place
4. **Reusability**: Multiple entities can reference the same physical location
5. **Easier Migration**: Centralized location data makes future spatial queries simpler

**Trade-offs:**
- Additional JOIN operations for queries
- Slightly more complex relationships
- Need to manage location lifecycle (when to create/update/delete)

### Use Cases
1. **Volunteer Matching**: Prioritize volunteers closer to event locations
2. **Event Discovery**: Allow volunteers to search events within a specific radius
3. **Organization Mapping**: Show all events/volunteers associated with an organization's area
4. **Statistics**: Generate insights on volunteer coverage and service areas

### Proposed Changes

#### 1. Database Schema Updates

**New `locations` table:**
```sql
CREATE TABLE locations (
    id SERIAL PRIMARY KEY,
    address VARCHAR(255) NOT NULL,
    city VARCHAR(100),
    state VARCHAR(50),
    zip_code VARCHAR(20),
    country VARCHAR(100) DEFAULT 'USA',
    latitude DECIMAL(10, 8),
    longitude DECIMAL(11, 8),
    geocoded_at TIMESTAMP,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),
    UNIQUE(address, city, state, zip_code)  -- Prevent duplicate locations
);

CREATE INDEX idx_locations_coordinates ON locations(latitude, longitude);
CREATE INDEX idx_locations_zip ON locations(zip_code);
```

**Update existing tables to reference `locations`:**
```sql
-- Update volunteers table
ALTER TABLE volunteer DROP COLUMN location;
ALTER TABLE volunteer ADD COLUMN location_id INTEGER;
ALTER TABLE volunteer ADD CONSTRAINT fk_volunteer_location 
    FOREIGN KEY (location_id) REFERENCES locations(id) ON DELETE SET NULL;

-- Update events table
ALTER TABLE event DROP COLUMN location;
ALTER TABLE event ADD COLUMN location_id INTEGER NOT NULL;
ALTER TABLE event ADD CONSTRAINT fk_event_location 
    FOREIGN KEY (location_id) REFERENCES locations(id) ON DELETE RESTRICT;

-- Update organizations table
ALTER TABLE organization DROP COLUMN location;
ALTER TABLE organization ADD COLUMN location_id INTEGER NOT NULL;
ALTER TABLE organization ADD CONSTRAINT fk_organization_location 
    FOREIGN KEY (location_id) REFERENCES locations(id) ON DELETE RESTRICT;
```

**Foreign Key Deletion Strategies:**
- **Volunteer**: `SET NULL` - If location is deleted, volunteer remains but without location
- **Event**: `RESTRICT` - Cannot delete location if events reference it (events require location)
- **Organization**: `RESTRICT` - Cannot delete location if organizations reference it

#### 2. Updated SQLAlchemy Models in `src/models/dbmodels.py`

```python
class Location(Base):
    __tablename__ = "locations"
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    address: Mapped[str] = mapped_column(String(255), nullable=False)
    city: Mapped[str] = mapped_column(String(100), nullable=True)
    state: Mapped[str] = mapped_column(String(50), nullable=True)
    zip_code: Mapped[str] = mapped_column(String(20), nullable=True)
    country: Mapped[str] = mapped_column(String(100), default="USA", server_default="USA")
    latitude: Mapped[float] = mapped_column(Float, nullable=True)
    longitude: Mapped[float] = mapped_column(Float, nullable=True)
    geocoded_at: Mapped[datetime] = mapped_column(DateTime, nullable=True)
    
    # Relationships
    volunteers: Mapped[List["Volunteer"]] = relationship(back_populates="location")
    events: Mapped[List["Event"]] = relationship(back_populates="location")
    organizations: Mapped[List["Organization"]] = relationship(back_populates="location")


class Volunteer(Base):
    # ...existing fields...
    
    location_id: Mapped[int] = mapped_column(
        ForeignKey("locations.id", ondelete="SET NULL"),
        nullable=True,
        index=True
    )
    location: Mapped["Location"] = relationship(back_populates="volunteers")


class Event(Base):
    # ...existing fields...
    
    location_id: Mapped[int] = mapped_column(
        ForeignKey("locations.id", ondelete="RESTRICT"),
        nullable=False,
        index=True
    )
    location: Mapped["Location"] = relationship(back_populates="events")


class Organization(Base):
    # ...existing fields...
    
    location_id: Mapped[int] = mapped_column(
        ForeignKey("locations.id", ondelete="RESTRICT"),
        nullable=False,
        index=True
    )
    location: Mapped["Location"] = relationship(back_populates="organizations")
```

#### 3. Updated Pydantic Models in `src/models/pydanticmodels.py`

```python
class LocationBase(BaseModel):
    address: str
    city: str | None = None
    state: str | None = None
    zip_code: str | None = None
    country: str = "USA"

class LocationCreate(LocationBase):
    pass

class LocationResponse(LocationBase):
    id: int
    latitude: float | None = None
    longitude: float | None = None
    geocoded_at: datetime | None = None
    
    class Config:
        from_attributes = True

# Update existing models to use LocationCreate instead of string
class EventCreate(BaseModel):
    name: str
    description: str
    location: LocationCreate  # Changed from str
    # ...other fields...

class EventResponse(BaseModel):
    id: int
    name: str
    location: LocationResponse  # Return full location object
    # ...other fields...

class VolunteerCreate(BaseModel):
    # ...existing fields...
    location: LocationCreate | None = None  # Optional for volunteers

class VolunteerResponse(BaseModel):
    id: int
    # ...existing fields...
    location: LocationResponse | None = None
```

#### 4. Geocoding Service Integration

Choose a geocoding API provider:

**Recommended: Mapbox Geocoding API**
- Good accuracy and address parsing
- Generous free tier (100,000 requests/month)
- Good documentation and Python support

**New utility file: `src/util/geocoding.py`**
```python
import httpx
from typing import Optional
from datetime import datetime

async def geocode_address(
    address: str,
    city: Optional[str] = None,
    state: Optional[str] = None,
    zip_code: Optional[str] = None
) -> tuple[float, float, str]:
    """
    Convert address components to (latitude, longitude, formatted_address).
    
    Returns:
        tuple: (latitude, longitude, formatted_address)
    Raises:
        ValueError: If geocoding fails or address is invalid
    """
    # Build full address string
    # Call geocoding API
    # Parse and return coordinates

async def calculate_distance(
    lat1: float, lon1: float,
    lat2: float, lon2: float,
    unit: str = "miles"
) -> float:
    """
    Calculate distance between two points using Haversine formula.
    
    Args:
        lat1, lon1: First coordinate pair
        lat2, lon2: Second coordinate pair
        unit: "miles" or "kilometers"
    
    Returns:
        float: Distance in specified unit
    """
    # Implement Haversine formula

async def reverse_geocode(lat: float, lon: float) -> dict:
    """
    Convert coordinates to address components.
    
    Returns:
        dict: {address, city, state, zip_code, country}
    """
    pass
```

#### 5. Location CRUD Operations in `src/dependencies/database/crud.py`

```python
def get_or_create_location(
    db: Session,
    location_data: LocationCreate,
    geocode: bool = True
) -> Location:
    """
    Get existing location or create new one with geocoding.
    
    Args:
        db: Database session
        location_data: Location information
        geocode: Whether to geocode address immediately
    
    Returns:
        Location: Existing or newly created location
    """
    # Check if location already exists (by address + city + state + zip)
    # If exists, return existing location
    # If not, create new location
    # If geocode=True, call geocoding service and populate lat/lon
    # Return location

def update_location(
    db: Session,
    location_id: int,
    location_updates: LocationCreate
) -> Location:
    """
    Update location and re-geocode if address changed.
    """
    # Update location fields
    # If address changed, re-geocode
    # Update geocoded_at timestamp

def get_locations_within_radius(
    db: Session,
    lat: float,
    lon: float,
    radius_miles: float
) -> list[Location]:
    """
    Find all locations within radius of given coordinates.
    Uses bounding box approximation for efficiency.
    """
    # Calculate bounding box
    # Query locations within box
    # Filter by precise Haversine distance
```

#### 6. Updated Event/Volunteer CRUD Operations

Modify existing CRUD functions to handle location creation:

```python
def create_org_event(
    db: Session,
    event: EventCreate,
    admin_id: int
) -> Event:
    # Validate admin authorization
    
    # Create or get location
    location = get_or_create_location(db, event.location, geocode=True)
    
    # Create event with location_id
    new_event = Event(
        name=event.name,
        description=event.description,
        location_id=location.id,
        # ...other fields...
    )
    
    db.add(new_event)
    db.commit()
    db.refresh(new_event)
    
    return new_event

def update_org_event(
    db: Session,
    event_id: int,
    event_updates: EventUpdate,
    admin_id: int
) -> Event:
    # Find event and validate authorization
    
    # If location is being updated
    if event_updates.location is not None:
        location = get_or_create_location(db, event_updates.location, geocode=True)
        event.location_id = location.id
    
    # Update other fields
    # Commit changes
```

#### 7. New API Endpoints

**Location-specific endpoints in `src/routers/location.py`:**
```python
GET /locations/{location_id}
# Returns: LocationResponse with coordinates

POST /locations/geocode
# Body: LocationCreate
# Returns: LocationResponse with geocoded coordinates

GET /locations/nearby?lat={lat}&lon={lon}&radius={miles}
# Returns: List[LocationResponse] within radius
```

**Enhanced event endpoints in `src/routers/event.py`:**
```python
GET /events/nearby?lat={lat}&lon={lon}&radius={miles}
# Returns: List of events within radius, sorted by distance

GET /events/nearby?zip_code={zip}&radius={miles}
# Alternative: search by zip code instead of coordinates
```

#### 8. Enhanced Matching Algorithm

Update `match_volunteers_to_event()` in `src/dependencies/database/relations.py`:

```python
def match_volunteers_to_event(
    db: Session,
    event_id: int,
    admin_id: int,
    max_distance_miles: float = 50.0,
    distance_weight: float = 0.3
) -> list[tuple[Volunteer, float]]:
    """
    Match volunteers to event considering skills, availability, AND distance.
    
    Args:
        max_distance_miles: Maximum distance to consider volunteers
        distance_weight: How much distance affects score (0.0 to 1.0)
    
    Returns:
        List of (volunteer, match_score) tuples, sorted by score descending
    """
    # Get event with location
    event = db.query(Event).filter(Event.id == event_id).first()
    
    # Get volunteers with locations within max distance
    nearby_volunteers = get_volunteers_within_distance(
        db, 
        event.location.latitude,
        event.location.longitude,
        max_distance_miles
    )
    
    # Calculate composite score:
    # score = (skill_match * (1 - distance_weight)) + (distance_score * distance_weight)
    
    # Return sorted matches
```

### Design Decisions to Consider

1. **Location Lifecycle Management**
   - Should unused locations be automatically deleted?
   - How to handle location updates when multiple entities reference it?
   - Should we allow entities to share location objects or always create new ones?

2. **Geocoding Strategy**
   - Geocode immediately on creation (slower writes, always available)
   - Geocode on first access (faster writes, may need lazy loading)
   - Background job after creation (best performance, more complex)

3. **Location Uniqueness**
   - Current design: UNIQUE constraint on (address, city, state, zip_code)
   - Should "123 Main St" in different cities be different locations? (Yes - handled by constraint)
   - How to handle slight address variations (typos, abbreviations)?

4. **Privacy Considerations**
   - Should volunteer addresses be stored at full precision?
   - Consider storing zip code centroid instead of exact address for volunteers
   - Who can access precise location data?

5. **Error Handling**
   - What if geocoding fails during event creation?
   - Should we allow creating events with just address but no coordinates?
   - How to handle partial address information?

### Configuration
Add to `.env`:
```
GEOCODING_PROVIDER=mapbox
MAPBOX_API_KEY=your_api_key_here
GEOCODING_RATE_LIMIT=50
MAX_DISTANCE_FOR_MATCHING=50
GEOCODE_ON_CREATE=true
DEFAULT_COUNTRY=USA
```

### Implementation Phases

**Phase 1: Database Schema & Models (2-3 days)**
- Create `locations` table and migration
- Update SQLAlchemy models with relationships
- Update Pydantic models for API contracts
- Create database migration script

**Phase 2: Location CRUD Operations (2-3 days)**
- Implement `get_or_create_location()`
- Implement location update logic
- Add location querying functions
- Update existing event/volunteer CRUD to use locations

**Phase 3: Geocoding Integration (2-3 days)**
- Choose and configure geocoding provider
- Implement `geocode_address()` function
- Add error handling and retry logic
- Implement caching strategy

**Phase 4: Distance Calculation (1-2 days)**
- Implement Haversine distance formula
- Add `get_locations_within_radius()` query
- Create distance utility functions
- Add unit tests for calculations

**Phase 5: API Endpoints (2-3 days)**
- Create location router and endpoints
- Update event/volunteer endpoints to return location objects
- Add nearby search endpoints
- Update API documentation

**Phase 6: Enhanced Matching (2-3 days)**
- Update matching algorithm to include distance
- Add configurable distance weights
- Test and tune scoring algorithm
- Add distance information to match results

**Phase 7: Testing & Optimization (2-3 days)**
- Write unit tests for all location functions
- Integration tests with geocoding API (mocked)
- Performance testing with large datasets
- Add database indexes for common queries

### Estimated Total Effort
14-18 days including:
- Database schema design and migration
- Model updates across codebase
- Geocoding service integration
- Location CRUD operations
- API endpoint creation
- Matching algorithm updates
- Comprehensive testing
- Documentation updates
- Performance optimization

### Migration Strategy

**Step 1: Create locations table and add foreign keys**
```sql
-- Run migration to create locations table
-- Add nullable location_id columns to existing tables
-- Keep old location string columns temporarily
```

**Step 2: Migrate existing data**
```python
# Migration script to:
# 1. Extract unique locations from existing tables
# 2. Geocode all unique addresses (batch process)
# 3. Populate location_id in existing records
# 4. Verify all records have location_id
```

**Step 3: Make location_id required and drop old columns**
```sql
-- Make location_id NOT NULL where required
-- Drop old location string columns
-- Add foreign key constraints
```

### Security Considerations
- Rate limit geocoding endpoints to prevent API abuse
- Store API keys securely in environment variables
- Validate and sanitize all address inputs
- Consider privacy implications of storing precise coordinates
- Implement proper error handling to avoid exposing API keys
- Add authorization checks for sensitive location data
- Log geocoding operations for audit trail

### Testing Considerations
- Mock geocoding API calls in unit tests
- Test with invalid/incomplete addresses
- Test distance calculations with known coordinates (e.g., NYC to LA)
- Test location sharing between entities
- Test location update cascading effects
- Integration tests with actual API (sparingly)
- Performance tests with spatial queries

### Performance Considerations
- Cache geocoding results in database (via `geocoded_at`)
- Index latitude/longitude columns for spatial queries
- Consider PostgreSQL + PostGIS extension for advanced spatial queries
- Implement bounding box filtering before precise distance calculations
- Use database-level spatial indexes if available
- Monitor API usage and implement rate limiting
- Consider background workers for bulk geocoding
- Add query result caching for popular locations

### Related Files
- `src/models/dbmodels.py` - Add `Location` model, update relationships
- `src/models/pydanticmodels.py` - Add location schemas
- `src/util/geocoding.py` - New file for geocoding utilities
- `src/routers/location.py` - New router for location endpoints
- `src/routers/event.py` - Update to use location objects
- `src/routers/volunteer.py` - Update to use location objects
- `src/dependencies/database/crud.py` - Add location CRUD operations
- `src/dependencies/database/relations.py` - Update matching algorithm
- Database migrations - Schema changes and data migration
- `requirements.txt` - Add `httpx`, `geopy` or similar
- `.env.example` - Add geocoding configuration

### Third-Party Libraries to Add
```
httpx>=0.24.0              # Async HTTP client for API calls
geopy>=2.3.0               # Optional: geocoding utilities
python-dotenv>=1.0.0       # If not already included
```