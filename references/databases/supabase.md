# Supabase Database Reference

## Directory additions
```
supabase/
├── migrations/           # SQL migrations
├── seed.sql              # Seed data
└── config.toml           # Supabase CLI config
src/lib/
├── supabase/
│   ├── client.ts         # Browser client
│   ├── server.ts         # Server client (SSR)
│   ├── admin.ts          # Service role client (server-only)
│   └── middleware.ts      # Auth middleware
└── database.types.ts     # Auto-generated types
```

## CLAUDE.md Additions

```markdown
## Database
- Platform: Supabase (PostgreSQL)
- Client: @supabase/supabase-js
- Auth: Supabase Auth (integrated)
- Realtime: Supabase Realtime (WebSocket)
- Storage: Supabase Storage (S3-compatible)

## DB Commands
- Start local: supabase start
- Stop local: supabase stop
- Create migration: supabase migration new <name>
- Apply migrations: supabase db push
- Generate types: supabase gen types typescript --local > src/lib/database.types.ts
- Reset local DB: supabase db reset
- Link project: supabase link --project-ref <ref>
- Push to remote: supabase db push

## Code Conventions
- ALWAYS regenerate types after schema changes: supabase gen types typescript
- Use the server client for SSR/API routes, browser client for client components
- Use Row Level Security (RLS) policies for ALL tables — no exceptions
- Service role client bypasses RLS — use only in trusted server-side code
- Use Supabase Auth for user management, not custom auth tables
- Use database functions for complex business logic (keeps logic close to data)
- Prefer Supabase Realtime subscriptions over polling for live data

## Mistakes to Avoid
- NEVER expose the service role key to the client
- NEVER disable RLS on tables with user data
- ALWAYS use the anon key (NEXT_PUBLIC_SUPABASE_ANON_KEY) in client code
- NEVER use database.types.ts imports in non-TypeScript files
- ALWAYS handle Supabase error responses (they return { data, error }, not exceptions)
```

## Rules

### supabase/migrations/**/*.sql
```
Migration conventions:
- NEVER modify existing migration files
- ALWAYS include RLS policies in the same migration as table creation
- ALWAYS enable RLS: ALTER TABLE table_name ENABLE ROW LEVEL SECURITY;
- Name policies descriptively: "Users can read own data"
- Include both UP logic in migrations (Supabase doesn't auto-generate down)
```

## Auth Integration Pattern

```typescript
// Server-side (API route or Server Component)
import { createClient } from '@/lib/supabase/server'

const supabase = await createClient()
const { data: { user } } = await supabase.auth.getUser()

// Client-side
import { createClient } from '@/lib/supabase/client'

const supabase = createClient()
const { data, error } = await supabase.from('table').select()
```

## RLS Policy Patterns

```sql
-- Users can only read their own data
CREATE POLICY "Users read own data" ON public.profiles
  FOR SELECT USING (auth.uid() = user_id);

-- Users can only insert their own data
CREATE POLICY "Users insert own data" ON public.profiles
  FOR INSERT WITH CHECK (auth.uid() = user_id);

-- Multi-tenant: users can read data from their organization
CREATE POLICY "Org members read org data" ON public.resources
  FOR SELECT USING (
    org_id IN (
      SELECT org_id FROM public.org_members WHERE user_id = auth.uid()
    )
  );
```
