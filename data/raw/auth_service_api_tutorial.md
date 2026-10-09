# Internal Authentication Service API Tutorial

## Overview
The Central Auth Service (`auth-core`) issues cryptographically signed JSON Web Tokens (JWT) for inter-service communication and user authentication across all engineering domains.

## Endpoints

### 1. Issue Service Token
- **Method**: `POST /api/v1/oauth/token`
- **Headers**: `Content-Type: application/json`
- **Payload**:
```json
{
  "client_id": "service-flocard-telemetry",
  "client_secret": "env_vault_secret_key",
  "grant_type": "client_credentials",
  "scope": "telemetry:write profiles:read"
}
```
- **Success Response (200 OK)**:
```json
{
  "access_token": "eyJhbGciOiJSUzI1NiIsIn...",
  "token_type": "Bearer",
  "expires_in": 3600,
  "refresh_token": "rfr_98a7sd6f..."
}
```

### 2. Verify Token & Introspect
- **Method**: `POST /api/v1/oauth/introspect`
- **Headers**: `Authorization: Bearer <access_token>`
- **Response**:
```json
{
  "active": true,
  "sub": "service-flocard-telemetry",
  "scopes": ["telemetry:write", "profiles:read"],
  "exp": 1774500000
}
```

## Rate Limiting & Throttling
- Internal services: 10,000 requests per minute per IP.
- Public client gateways: 120 requests per minute per authenticated user.
- Status code 429 Too Many Requests includes `Retry-After` header in seconds.
