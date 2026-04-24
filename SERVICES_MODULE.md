# Services Module Documentation

## Overview

The Services Module allows businesses to create and manage services that customers can book. This module includes:

- **Admin Endpoints**: Create, read, update, and delete services (requires authentication)
- **Public Endpoint**: Customers can view available services without authentication
- **Multi-Tenant Isolation**: All services are scoped to their business
- **Soft Delete**: Inactive services are hidden from customer view but retained in the database

## Architecture

### Service Layer Pattern

The Services Module follows the same clean architecture pattern used throughout CareOps:

```
Routes (app/routes/services.py)
    ↓ (delegates to)
Service Layer (app/services/service_service.py)
    ↓ (uses)
Models (app/models/service.py)
    ↓ (stored in)
Database (PostgreSQL)
```

### Multi-Tenant Isolation

All queries filter by `business_id` to prevent cross-tenant data access:

```python
# All service operations are scoped to the business
services = self.db.query(Service).filter(
    Service.business_id == business_id,
    Service.is_active == True
).all()
```

## Files Created

### 1. Model: `app/models/service.py`

Defines the Service data model with the following fields:

| Field | Type | Required | Notes |
|-------|------|----------|-------|
| `id` | Integer | ✅ | Primary key, auto-increment |
| `business_id` | ForeignKey | ✅ | Links to Business (multi-tenant) |
| `name` | String(255) | ✅ | Service name (e.g., "Haircut", "Consultation") |
| `description` | Text | ❌ | Detailed service description |
| `duration_minutes` | Integer | ✅ | Service duration in minutes (must be > 0) |
| `price` | Float | ❌ | Service price (must be >= 0.0 if provided) |
| `is_active` | Boolean | ✅ | Default: True. Hidden from public view if False |
| `created_at` | DateTime | ✅ | Auto-set on creation |
| `updated_at` | DateTime | ✅ | Auto-updated on modification |

**Relationships:**
- `business`: Many-to-One relationship with Business model

### 2. Schema: `app/schemas/service_schema.py`

Pydantic schemas for request/response validation:

**ServiceCreate** (POST request)
```python
{
  "name": "Haircut",
  "description": "Professional haircut with styling",
  "duration_minutes": 30,
  "price": 45.00
}
```

**ServiceUpdate** (PUT request)
```python
{
  "name": "Premium Haircut",  # optional
  "is_active": true           # optional
}
```

**ServiceResponse** (API response)
```python
{
  "id": 1,
  "name": "Haircut",
  "description": "Professional haircut with styling",
  "duration_minutes": 30,
  "price": 45.00,
  "is_active": true,
  "created_at": "2026-04-16T10:30:00",
  "updated_at": "2026-04-16T10:30:00"
}
```

**ServicePublicResponse** (Public API response, limited data)
```python
{
  "id": 1,
  "name": "Haircut",
  "description": "Professional haircut with styling",
  "duration_minutes": 30,
  "price": 45.00
}
```

### 3. Service Layer: `app/services/service_service.py`

Implements business logic with validations and multi-tenant isolation:

**Methods:**

#### `create_service(service_data: ServiceCreate, business_id: int) -> Service`
- **Validations:**
  - Name must be non-empty
  - Duration must be > 0
- **Multi-tenant:** Scoped to business_id
- **Returns:** Created Service object

#### `get_services(business_id: int, skip: int = 0, limit: int = 50) -> List[Service]`
- **Pagination:** Max 100 items per request
- **Filter:** Only active services (is_active=True)
- **Multi-tenant:** Scoped to business_id
- **Returns:** List of Service objects

#### `get_service(service_id: int, business_id: int) -> Service`
- **Multi-tenant:** Scoped to business_id
- **Returns:** Single Service object or None

#### `update_service(service_id: int, service_data: ServiceUpdate, business_id: int) -> Service`
- **Validations:**
  - If updating name: must be non-empty
  - If updating duration: must be > 0
- **Multi-tenant:** Scoped to business_id
- **Returns:** Updated Service object
- **Raises:** HTTPException 404 if not found

#### `delete_service(service_id: int, business_id: int) -> bool`
- **Soft Delete:** Sets is_active=False
- **Multi-tenant:** Scoped to business_id
- **Returns:** True if deleted, False if not found

#### `get_public_services(business_id: int) -> List[Service]`
- **Purpose:** For unauthenticated customers viewing available services
- **Filter:** Only active services (is_active=True)
- **No limit:** Returns all active services
- **Multi-tenant:** Scoped to business_id

### 4. Routes: `app/routes/services.py`

RESTful API endpoints with thin route handlers delegating to service layer:

## API Endpoints

### Authenticated Endpoints (Require login)

#### POST /services
Create a new service.

**Request:**
```json
{
  "name": "Haircut",
  "description": "Professional haircut with styling",
  "duration_minutes": 30,
  "price": 45.00
}
```

**Response:** 201 Created
```json
{
  "id": 1,
  "name": "Haircut",
  "description": "Professional haircut with styling",
  "duration_minutes": 30,
  "price": 45.00,
  "is_active": true,
  "created_at": "2026-04-16T10:30:00",
  "updated_at": "2026-04-16T10:30:00"
}
```

**Validations:**
- Name required, must be non-empty
- Duration must be > 0 minutes
- Price must be >= 0 (if provided)

---

#### GET /services
Get all active services for the current business.

**Query Parameters:**
- `skip`: int = 0 (records to skip)
- `limit`: int = 50 (max records, max 100)

**Response:** 200 OK
```json
[
  {
    "id": 1,
    "name": "Haircut",
    "duration_minutes": 30,
    "price": 45.00,
    "is_active": true,
    ...
  },
  {
    "id": 2,
    "name": "Color Treatment",
    "duration_minutes": 60,
    "price": 80.00,
    "is_active": true,
    ...
  }
]
```

---

#### GET /services/{service_id}
Get a single service by ID.

**Response:** 200 OK
```json
{
  "id": 1,
  "name": "Haircut",
  ...
}
```

**Error Responses:**
- 404 Not Found: Service doesn't exist or belongs to different business

---

#### PUT /services/{service_id}
Update a service.

**Request:**
```json
{
  "name": "Premium Haircut",
  "price": 55.00,
  "is_active": true
}
```

**Response:** 200 OK
```json
{
  "id": 1,
  "name": "Premium Haircut",
  "price": 55.00,
  ...
}
```

**Validations:**
- If updating name: must be non-empty
- If updating duration: must be > 0

---

#### DELETE /services/{service_id}
Delete a service (soft delete - sets is_active=False).

**Response:** 200 OK
```json
{
  "message": "Service deleted successfully"
}
```

**Note:** Service is not physically deleted, just marked inactive. Customers won't see it for new bookings.

---

### Public Endpoints (No authentication)

#### GET /public/services/{business_id}
Get all active services for a business (public).

**Purpose:** Allow customers to view available services when booking without logging in.

**Response:** 200 OK
```json
[
  {
    "id": 1,
    "name": "Haircut",
    "description": "Professional haircut with styling",
    "duration_minutes": 30,
    "price": 45.00
  },
  {
    "id": 2,
    "name": "Color Treatment",
    "description": "Professional hair coloring",
    "duration_minutes": 60,
    "price": 80.00
  }
]
```

**Note:** Returns limited data (no created_at/updated_at) and only active services.

## HTTP Status Codes

| Status | Meaning | Example |
|--------|---------|---------|
| 200 | Success | Service updated/deleted |
| 201 | Created | Service created successfully |
| 400 | Bad Request | Invalid name or duration |
| 404 | Not Found | Service doesn't exist |
| 409 | Conflict | (Reserved for future use) |

## Validations

### Create Service
- ✅ Name must be provided and non-empty
- ✅ Duration must be positive integer (> 0)
- ✅ Price must be non-negative (>= 0.0) if provided
- ✅ All fields scoped to business_id

### Update Service
- ✅ If name provided: must be non-empty
- ✅ If duration provided: must be > 0
- ✅ If price provided: must be >= 0
- ✅ Service must exist and belong to user's business

### Business Logic
- ✅ Soft delete: is_active=False instead of removing from DB
- ✅ Public endpoint: Only shows is_active=True services
- ✅ Pagination: Max 100 items per query
- ✅ Multi-tenant: All queries filtered by business_id

## Security

### Multi-Tenant Isolation
Every service query includes business_id filter:
```python
Service.business_id == business_id
```

Users can only:
- Create services in their own business
- View services in their own business
- Update services in their own business
- Delete services in their own business

### Authentication
- Admin endpoints: Require valid JWT token
- Public endpoint: No authentication required (but filtered by business_id)

### Data Protection
- Cross-tenant access returns 404 Not Found (not 403 Forbidden, to avoid leaking existence)
- Inactive services hidden from public view
- Soft delete maintains data integrity for historical records

## Database Schema

```sql
CREATE TABLE services (
    id INTEGER PRIMARY KEY AUTO_INCREMENT,
    business_id INTEGER NOT NULL REFERENCES businesses(id) ON DELETE CASCADE,
    name VARCHAR(255) NOT NULL,
    description TEXT,
    duration_minutes INTEGER NOT NULL,
    price FLOAT,
    is_active BOOLEAN DEFAULT TRUE,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    INDEX idx_business_id (business_id),
    INDEX idx_created_at (created_at),
    INDEX idx_is_active (is_active)
);
```

## Integration with Bookings

Services can be referenced in the Booking model:

```python
# In app/models/booking.py - add optional field:
service_id = Column(Integer, ForeignKey("services.id", ondelete="SET NULL"), nullable=True)
service = relationship("Service", foreign_keys=[service_id])
```

Then when creating a booking, customers can select a service:

```python
# In booking creation:
booking = Booking(
    contact_id=contact_id,
    service_id=service_id,  # Now linked to a service
    start_time=start_time,
    duration_minutes=Service.duration_minutes,  # Auto-set from service
)
```

## Pagination

All list endpoints support pagination:

```python
# Get 50 services, skip first 100
GET /services?skip=100&limit=50

# Get first 25 services
GET /services?skip=0&limit=25
```

**Max limit:** 100 items per request (enforced server-side)

## Logging

All operations are logged with [SERVICE] prefix:

```
[SERVICE] Creating service: Haircut for business 1
[SERVICE] Service created: id=1, name=Haircut
[SERVICE] Fetching services for business 1
[SERVICE] Updating service 1 for business 1
[SERVICE] Service updated: 1
[SERVICE] Deleting service 1
[SERVICE] Service deleted (soft): id=1
```

## Testing Examples

### Create a Service
```bash
curl -X POST "http://localhost:8000/services" \
  -H "Authorization: Bearer {token}" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Haircut",
    "description": "Professional haircut",
    "duration_minutes": 30,
    "price": 45.00
  }'
```

### List Services
```bash
curl -X GET "http://localhost:8000/services?skip=0&limit=10" \
  -H "Authorization: Bearer {token}"
```

### Get Public Services (No auth required)
```bash
curl -X GET "http://localhost:8000/public/services/1"
```

### Update a Service
```bash
curl -X PUT "http://localhost:8000/services/1" \
  -H "Authorization: Bearer {token}" \
  -H "Content-Type: application/json" \
  -d '{
    "price": 55.00,
    "is_active": true
  }'
```

### Delete a Service
```bash
curl -X DELETE "http://localhost:8000/services/1" \
  -H "Authorization: Bearer {token}"
```

## Migration

Migration file: `alembic/versions/004_add_services_table.py`

**To apply migration:**
```bash
alembic upgrade head
```

**To rollback:**
```bash
alembic downgrade -1
```

## Swagger Documentation

All endpoints are automatically documented in FastAPI Swagger UI at `/docs`:

- POST /services - Create service (with request/response examples)
- GET /services - List services (with pagination parameters)
- GET /services/{service_id} - Get single service
- PUT /services/{service_id} - Update service
- DELETE /services/{service_id} - Delete service (soft)
- GET /public/services/{business_id} - Public service listing

## Files Modified

1. ✅ `app/models/service.py` - Created Service model
2. ✅ `app/schemas/service_schema.py` - Created request/response schemas
3. ✅ `app/services/service_service.py` - Created ServiceService class
4. ✅ `app/routes/services.py` - Created API endpoints
5. ✅ `app/models/business.py` - Added services relationship
6. ✅ `app/models/__init__.py` - Imported Service model
7. ✅ `app/main.py` - Registered services router
8. ✅ `alembic/versions/004_add_services_table.py` - Created migration

## Next Steps

### Recommended Enhancements
1. **Service Categories**: Add category field to group services
2. **Service Staff Assignment**: Link services to specific staff members
3. **Service Availability**: Add time slots or availability schedule
4. **Service Pricing Tiers**: Support different prices based on variants
5. **Service Analytics**: Track which services are booked most frequently

### Integration Points
1. **Booking Module**: Link bookings to services by service_id
2. **Invoice Module**: Reference services in invoices
3. **Calendar Module**: Show service duration when displaying bookings
4. **Frontend**: Add service selection to booking form

## Troubleshooting

### Service Not Appearing in Public List
- Verify `is_active=True`
- Check `business_id` matches
- Confirm service was created in your business

### Cannot Update Service
- Verify authentication token is valid
- Check service_id exists in your business
- Validate duration > 0 if updating

### Database Migration Failed
- Run `alembic current` to check current revision
- Run `alembic upgrade head` to apply latest
- Check PostgreSQL logs for specific errors

---

**Document Version:** 1.0
**Last Updated:** April 16, 2026
**Status:** Production Ready ✅
