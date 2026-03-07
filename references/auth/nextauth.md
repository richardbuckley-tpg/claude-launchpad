# NextAuth / Auth.js Reference

## Best For
Self-hosted auth with full control. Good for projects that need custom auth flows or want to avoid
third-party auth service costs. Works with Next.js, SvelteKit, and other frameworks.

## Setup Pattern (Auth.js v5)

### Environment Variables
```
AUTH_SECRET=<generated-secret>
AUTH_GOOGLE_ID=<oauth-client-id>
AUTH_GOOGLE_SECRET=<oauth-secret>
# Add more providers as needed
```

### Directory additions
```
src/
├── auth.ts               # Auth.js configuration
├── auth.config.ts        # Edge-compatible config (for middleware)
├── middleware.ts          # Auth middleware
├── app/
│   ├── api/auth/[...nextauth]/route.ts  # Auth API routes
│   ├── login/page.tsx
│   └── (protected)/
```

## CLAUDE.md Additions

```markdown
## Authentication
- Provider: Auth.js v5 (NextAuth)
- Session strategy: JWT (or database sessions)
- Providers: [Google, GitHub, Email, etc.]
- Config: src/auth.ts

## Auth Patterns
- Use auth() in Server Components for session
- Use useSession() in Client Components (wrap app in SessionProvider)
- Middleware protects routes via auth.config.ts (edge-compatible)
- Use callbacks in auth.ts to customize JWT/session content
- Database adapter syncs auth state to your DB automatically

## Auth Conventions
- NEVER store sensitive data in JWT — it's readable (not encrypted)
- ALWAYS use database adapter if you need user profiles beyond auth
- Use signIn() and signOut() server actions for auth flows
- Protect API routes with auth() check at the top
```

## Database Adapter Pattern

With Prisma:
```typescript
// auth.ts
import { PrismaAdapter } from "@auth/prisma-adapter"
import { prisma } from "@/lib/db"

export const { handlers, auth, signIn, signOut } = NextAuth({
  adapter: PrismaAdapter(prisma),
  providers: [Google, GitHub],
  callbacks: {
    session: ({ session, user }) => ({
      ...session,
      user: { ...session.user, id: user.id, role: user.role }
    })
  }
})
```

## RBAC Pattern

```typescript
// In auth.ts callbacks
callbacks: {
  jwt: ({ token, user }) => {
    if (user) token.role = user.role
    return token
  },
  session: ({ session, token }) => {
    session.user.role = token.role
    return session
  }
}

// In middleware or pages
const session = await auth()
if (session?.user?.role !== 'admin') redirect('/unauthorized')
```
