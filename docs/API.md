# API Documentation

## Authentication

### POST /auth/login
Authenticate user and receive JWT tokens.

**Request:**
```json
{
  "username": "demo",
  "password": "demo123"
}
```

**Response:**
```json
{
  "access_token": "eyJ...",
  "refresh_token": "eyJ...",
  "token_type": "bearer"
}
```

**Demo Users:**
- Username: `demo`, Password: `demo123`, Role: `user`
- Username: `admin`, Password: `admin123`, Role: `admin`

### POST /auth/token
Refresh access token using refresh token.

**Request:**
```json
{
  "refresh_token": "eyJ..."
}
```

### POST /auth/logout
Revoke refresh token (requires authentication).

**Headers:** `Authorization: Bearer <access_token>`

**Request:**
```json
{
  "refresh_token": "eyJ..."
}
```

## Highlights API

All highlight endpoints require authentication via Bearer token in Authorization header.

### POST /highlights
Create new highlight.

**Rate Limit:** 10 requests/minute per IP

**Headers:** `Authorization: Bearer <token>`

**Request:**
```json
{
  "text": "Highlight text (max 2000 chars)",
  "source": "Source name (max 500 chars)",
  "tags": ["tag1", "tag2"]
}
```

### GET /highlights
List all highlights for authenticated user.

**Query Parameters:**
- `tag` (optional): Filter by tag

### GET /highlights/{id}
Get specific highlight by ID (owner or admin only).

### PUT /highlights/{id}
Update highlight (owner only).

### DELETE /highlights/{id}
Delete highlight (owner only).

### GET /highlights/export/markdown
Export highlights to markdown format.

## Authorization

- **User role:** Can access only their own highlights
- **Admin role:** Can access all highlights
- **Ownership:** Resources are filtered by `owner_id` automatically

## Error Format (RFC 7807)

All errors follow RFC 7807 Problem Details format:

```json
{
  "type": "/errors/validation",
  "title": "Validation Error",
  "status": 422,
  "detail": "Validation failed: 1 error(s)",
  "correlation_id": "550e8400-e29b-41d4-a716-446655440000",
  "instance": "/highlights",
  "validation_errors": [...]
}
```

## Security Features

- JWT authentication with HS256
- Access token TTL: 15 minutes
- Refresh token TTL: 7 days
- Rate limiting on sensitive endpoints
- Owner-based resource isolation
- Correlation ID for request tracing
- RFC 7807 error format with masked details in production
