# Stack Reference — Condensed Knowledge

Quick-reference for stack-specific patterns. Read the section matching the user's choices.

## Frontend Frameworks

### Next.js (App Router)
- **Key paths**: `src/app/` (routes), `src/components/ui/` (shared), `src/lib/` (utils), `src/server/actions/` (mutations)
- **Commands**: `npm run dev`, `npm run build`, `npm run test`, `npm run lint`, `npx tsc --noEmit`
- **Conventions**: Server Components by default. `"use client"` only when needed. Server Actions for mutations. Zod for all input validation in `src/lib/validations/`. `next/image` for images, `next/link` for links.
- **Mistakes**: Never `"use client"` at page level without reason. Never import server code in client components. Never put secrets without `NEXT_PUBLIC_` prefix. Always add `loading.tsx` + `error.tsx` per route.
- **Testing**: Vitest + React Testing Library + Playwright. Mock `next/navigation`, `next/headers`.
- **Rules target**: `src/app/api/**/*.ts` (route handlers must validate with zod, return NextResponse), `src/server/actions/**/*.ts` (must start with `"use server"`, validate input, use revalidatePath)

### React + Vite
- **Key paths**: `src/pages/` (routes), `src/components/` (UI), `src/hooks/`, `src/stores/` (Zustand), `src/lib/api.ts`
- **Commands**: `npm run dev`, `npm run build`, `npm run test`, `npm run lint`, `npx tsc --noEmit`
- **Conventions**: Feature-based component organization. React Query for server state, Zustand for app state. API calls through `src/lib/api.ts`. Lazy-load route components.
- **Mistakes**: Never store server state in Zustand. Never make API calls in components directly. Always handle loading/error states.
- **Testing**: Vitest + jsdom + @testing-library/react. MSW for API mocks.

### Vue 3 / Nuxt 3
- **Key paths**: `app/components/` (auto-imported), `app/composables/`, `app/pages/`, `server/api/`, `stores/` (Pinia)
- **Commands**: `npm run dev`, `npm run build`, `npm run test`, `npm run lint`, `npx nuxi typecheck`
- **Conventions**: Composition API with `<script setup>` exclusively. Composables prefixed with `use`. Pinia for global state. `useFetch`/`useAsyncData` for data.
- **Mistakes**: Never use Options API. Never mutate props directly. Use `ref()` not `reactive()` for primitives.

### SvelteKit
- **Key paths**: `src/routes/` (file routing), `src/lib/components/`, `src/lib/server/` (server-only), `src/lib/stores/`
- **Commands**: `npm run dev`, `npm run build`, `npm run test`, `npm run check`
- **Conventions**: `+page.server.ts` for server data loading. Form actions for mutations. `$lib` alias. Svelte 5 runes (`$state`, `$derived`, `$effect`).
- **Mistakes**: Never import `$lib/server` in client code. Always use form actions for mutations. Always add `+error.svelte`.

## Backend Frameworks

### Node.js / Express
- **Key paths**: `src/routes/`, `src/controllers/`, `src/services/`, `src/middleware/`, `src/models/`, `src/validations/`
- **Commands**: `npm run dev` (tsx watch), `npm run build` (tsc), `npm run test`, `npm run lint`
- **Conventions**: Controller → Service → Model. Validate all input via zod middleware. Centralized error handler. Structured logging (pino). Environment validated at startup.
- **Mistakes**: Never put business logic in controllers. Never use `console.log`. Always validate ALL input. Never catch errors in routes — let them bubble.
- **Rules target**: `src/routes/**/*.ts` (only route definitions + middleware), `src/services/**/*.ts` (no Express types, return typed results)

### Python / FastAPI
- **Key paths**: `app/api/v1/`, `app/core/` (config, security), `app/models/`, `app/schemas/`, `app/services/`, `app/db/`
- **Commands**: `uvicorn app.main:app --reload`, `pytest`, `ruff check .`, `ruff format .`, `mypy app/`
- **Conventions**: Async everywhere. Pydantic for all schemas. `Depends()` for DI. Separate models (DB) from schemas (API). Type hints on everything.
- **Mistakes**: Never return SQLAlchemy models directly. Never use sync DB operations. Always use `Depends()`. Never modify applied migrations. Never use `print()`.
- **Rules target**: `app/api/**/*.py` (type-annotated Pydantic schemas, Depends for auth), `app/db/migrations/**/*.py` (never modify existing migrations)

### Go
- **Key paths**: `cmd/server/main.go`, `internal/handler/`, `internal/service/`, `internal/repository/`, `internal/model/`, `pkg/`
- **Commands**: `go run cmd/server/main.go`, `go test ./...`, `golangci-lint run`, Makefile for common tasks
- **Conventions**: Standard Go layout (cmd/internal/pkg). Handler → Service → Repository. Interfaces defined by consumer. Context propagation. Errors wrapped with `%w`. Table-driven tests.
- **Mistakes**: Never ignore errors. Never use global state. Never put business logic in handlers. Always use `context.Context`. Always `defer` close resources.

## Databases

### PostgreSQL + Prisma
- **Commands**: `npx prisma generate`, `npx prisma migrate dev --name <desc>`, `npx prisma migrate deploy`, `npx prisma studio`, `npx prisma db seed`
- **Conventions**: PascalCase models, camelCase fields, `@map`/`@@map` for snake_case DB. Always include `createdAt`/`updatedAt`. `@@index` for common queries.
- **Mistakes**: Never edit applied migrations. Always run `prisma generate` after schema changes. Always create migrations (not `db push` in prod).

### PostgreSQL + Drizzle
- **Commands**: `npx drizzle-kit generate`, `npx drizzle-kit migrate`, `npx drizzle-kit studio`
- **Key paths**: `src/db/schema.ts`, `src/db/migrations/`, `drizzle.config.ts`

### PostgreSQL + SQLAlchemy/Alembic
- **Commands**: `alembic revision --autogenerate -m "desc"`, `alembic upgrade head`, `alembic downgrade -1`
- **Key paths**: `app/db/session.py`, `app/db/migrations/versions/`

### PostgreSQL + Go (pgx/sqlx)
- **Commands**: `migrate -path migrations -database $DATABASE_URL up`, `migrate create -ext sql -dir migrations -seq <name>`

### MongoDB + Mongoose
- **Conventions**: TypeScript interfaces alongside Mongoose schemas. `lean()` for read-only. `timestamps: true`. Indexes in schema definitions. Embed 1:few, reference 1:many.

### Supabase
- **Commands**: `supabase start`, `supabase migration new <name>`, `supabase db push`, `supabase gen types typescript --local > src/lib/database.types.ts`
- **Conventions**: RLS on ALL tables. Server client for SSR, browser client for components. Service role only in trusted server code. Regenerate types after schema changes.
- **Mistakes**: Never expose service role key to client. Never disable RLS on user data tables.

## Authentication

### Clerk
- **Key paths**: `src/middleware.ts` (clerkMiddleware), `src/app/sign-in/`, `src/app/sign-up/`, `src/app/api/webhooks/clerk/`
- **Conventions**: `auth()` in Server Components, `useUser()` in Client Components. Route groups: `(protected)` and `(public)`. Sync users via webhooks. Store `clerk_user_id` as FK.
- **Env**: `NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY`, `CLERK_SECRET_KEY`

### NextAuth / Auth.js v5
- **Key paths**: `src/auth.ts`, `src/auth.config.ts`, `src/middleware.ts`, `src/app/api/auth/[...nextauth]/route.ts`
- **Conventions**: JWT strategy default. PrismaAdapter for DB sessions. Callbacks for custom JWT/session content. `signIn()`/`signOut()` server actions.
- **Mistakes**: Never store sensitive data in JWT. Always use database adapter for user profiles.
- **Env**: `AUTH_SECRET`, `AUTH_GOOGLE_ID`, `AUTH_GOOGLE_SECRET`

### Custom JWT
- **Conventions**: Stateless tokens with short expiry (15min access, 7d refresh). Refresh token rotation. Store refresh tokens in DB. httpOnly cookies for web, Authorization header for API.

## Deployment

### Vercel
- **Conventions**: Preview auto-deploys on PR branches. Production on push to main. Env vars in Dashboard. `vercel env pull .env.local` to sync.
- **Gotchas**: 10s default timeout (30s Pro). Edge functions can't use Node native modules. ISR only works on Vercel.

### Railway
- **Conventions**: Dockerfile or Nixpacks. `railway up` or git push. `railway status` for state. Environment-based deploy targets.

### AWS
- **Conventions**: Verify credentials with `aws sts get-caller-identity`. Build before deploy. Check CloudWatch for deployment logs.
