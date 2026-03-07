# Custom JWT Authentication Reference

## Best For
Projects needing full control over auth, API-only backends, or non-JavaScript backends.

## Setup Pattern (Node.js/Express)

### Directory additions
```
src/
├── middleware/
│   └── auth.ts           # JWT verification middleware
├── services/
│   └── auth.service.ts   # Login, register, token refresh logic
├── lib/
│   └── jwt.ts            # JWT sign/verify utilities
└── routes/
    └── auth.routes.ts    # /login, /register, /refresh, /logout
```

### Environment Variables
```
JWT_SECRET=<long-random-string>
JWT_EXPIRES_IN=15m
JWT_REFRESH_SECRET=<different-long-random-string>
JWT_REFRESH_EXPIRES_IN=7d
```

## CLAUDE.md Additions

```markdown
## Authentication
- Method: Custom JWT (access + refresh tokens)
- Access token: 15min expiry, sent in Authorization header
- Refresh token: 7d expiry, sent in httpOnly cookie
- Password hashing: bcrypt (cost factor 12)

## Auth Flow
1. Login: POST /api/auth/login → returns access token + sets refresh cookie
2. Protected requests: Authorization: Bearer <access_token>
3. Token refresh: POST /api/auth/refresh (uses httpOnly cookie)
4. Logout: POST /api/auth/logout (clears refresh cookie + blacklists token)

## Auth Conventions
- NEVER store JWT secret in code — environment variable only
- ALWAYS use httpOnly, secure, sameSite cookies for refresh tokens
- NEVER store access tokens in localStorage (XSS vulnerable) — keep in memory
- ALWAYS hash passwords with bcrypt (cost 12+)
- ALWAYS validate JWT signature AND expiration on every request
- Use a token blacklist (Redis) for logout before token expiry
- Rate-limit auth endpoints (5 attempts per minute per IP)
```

## Setup Pattern (Python/FastAPI)

```python
# Using python-jose for JWT
from jose import JWTError, jwt
from passlib.context import CryptContext

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

def create_access_token(data: dict, expires_delta: timedelta) -> str:
    to_encode = data.copy()
    expire = datetime.utcnow() + expires_delta
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, SECRET_KEY, algorithm="HS256")
```

## Security Rules

```
- Tokens must be short-lived (15min access, 7d refresh)
- Refresh token rotation: issue new refresh token on each refresh
- Store password reset tokens with expiry in database, not JWT
- Use HTTPS only — never transmit tokens over HTTP
- CORS configuration must be explicit (never use wildcard with credentials)
- Implement account lockout after N failed login attempts
```

## RBAC Pattern

```typescript
// In JWT payload
{ sub: userId, role: "admin", permissions: ["read:users", "write:users"] }

// Middleware
const requireRole = (role: string) => (req, res, next) => {
  if (req.user.role !== role) return res.status(403).json({ error: "Forbidden" })
  next()
}

// Usage
router.delete('/users/:id', auth, requireRole('admin'), deleteUser)
```
