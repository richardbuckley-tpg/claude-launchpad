# Clerk Authentication Reference

## Best For
Projects wanting drop-in auth with beautiful UI, social logins, MFA, and organization support
out of the box. Excellent with Next.js and React.

## Setup Pattern

### Environment Variables
```
NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY=pk_...
CLERK_SECRET_KEY=sk_...
NEXT_PUBLIC_CLERK_SIGN_IN_URL=/sign-in
NEXT_PUBLIC_CLERK_SIGN_UP_URL=/sign-up
```

### Directory additions
```
src/
├── middleware.ts          # Clerk auth middleware (protects routes)
├── app/
│   ├── sign-in/[[...sign-in]]/page.tsx
│   ├── sign-up/[[...sign-up]]/page.tsx
│   └── (protected)/      # Routes requiring auth
│       └── layout.tsx     # Wraps with auth check
```

## CLAUDE.md Additions

```markdown
## Authentication
- Provider: Clerk
- UI: Clerk's pre-built components (<SignIn/>, <UserButton/>)
- Middleware: src/middleware.ts (protects routes via clerkMiddleware)
- Webhooks: /api/webhooks/clerk for user sync

## Auth Patterns
- Use auth() in Server Components for current user
- Use useUser() in Client Components
- Use clerkMiddleware() to protect routes (default: protect all, allow public routes)
- Sync Clerk users to your database via webhooks (user.created, user.updated)
- Use Clerk Organizations for multi-tenant features
- Use Clerk's JWT templates for custom claims

## Auth Conventions
- NEVER check auth in individual pages — use middleware + route groups
- ALWAYS sync user data to your DB via webhooks (don't query Clerk API on every request)
- Use (protected) route group for authenticated pages
- Use (public) route group for landing pages, docs, etc.
```

## Webhook Sync Pattern

```typescript
// app/api/webhooks/clerk/route.ts
import { Webhook } from 'svix'

export async function POST(req: Request) {
  // Verify webhook signature with svix
  // On user.created: create user in your DB
  // On user.updated: update user in your DB
  // On user.deleted: soft-delete user in your DB
}
```

## Multi-Tenant with Clerk Organizations

```markdown
## Multi-Tenant Setup
- Use Clerk Organizations for tenant management
- org_id maps to your tenant/organization table
- RLS policies filter by org_id from Clerk's JWT claims
- Use OrganizationSwitcher component for tenant switching
```

## Rules for auth-related code

```
- Always use clerkMiddleware() — not manual auth checks in API routes
- Webhook endpoint must verify Svix signatures
- User creation in DB must be idempotent (webhook may fire multiple times)
- Store clerk_user_id as the foreign key in your DB, not email
```
