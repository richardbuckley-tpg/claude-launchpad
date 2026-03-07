# Next.js Stack Reference

## Directory Structure (App Router)

```
src/
├── app/
│   ├── (auth)/           # Route group for auth pages
│   │   ├── login/
│   │   └── register/
│   ├── (dashboard)/      # Route group for authenticated pages
│   │   ├── layout.tsx
│   │   └── page.tsx
│   ├── api/              # API routes (Route Handlers)
│   │   └── [resource]/
│   │       └── route.ts
│   ├── layout.tsx        # Root layout
│   ├── page.tsx          # Home page
│   └── globals.css
├── components/
│   ├── ui/               # Reusable UI components (shadcn/ui pattern)
│   └── [feature]/        # Feature-specific components
├── lib/
│   ├── db.ts             # Database client
│   ├── auth.ts           # Auth configuration
│   ├── utils.ts          # Utility functions
│   └── validations/      # Zod schemas
├── hooks/                # Custom React hooks
├── types/                # TypeScript type definitions
└── server/
    ├── actions/          # Server Actions
    └── queries/          # Data fetching functions
```

## Directory Structure (Pages Router)

```
src/
├── pages/
│   ├── api/
│   ├── _app.tsx
│   ├── _document.tsx
│   └── index.tsx
├── components/
├── lib/
├── hooks/
├── styles/
└── types/
```

## CLAUDE.md Additions

```markdown
## Tech Stack
- Framework: Next.js 15 (App Router)
- Language: TypeScript with strict mode
- Styling: Tailwind CSS
- Testing: Vitest + React Testing Library + Playwright

## Commands
- Dev: npm run dev (or pnpm dev)
- Build: npm run build
- Test: npm run test
- Lint: npm run lint
- Type check: npx tsc --noEmit

## Code Conventions
- Use Server Components by default; add "use client" only when needed
- Server Actions for mutations, Route Handlers for webhooks/external APIs
- Colocate components with their routes when feature-specific
- Shared components go in src/components/ui/
- All API input must be validated with zod schemas from src/lib/validations/
- Use next/image for all images, next/link for all internal links
- Prefer parallel routes and intercepting routes over client-side modals

## Mistakes to Avoid
- NEVER use "use client" at the top of a page component without good reason
- NEVER import server-only code in client components
- NEVER put secrets in client-side code (prefix with NEXT_PUBLIC_ only for public values)
- ALWAYS use loading.tsx and error.tsx for each route segment
- ALWAYS validate environment variables at build time using zod
- NEVER modify the database schema directly — always create migrations
```

## Agent Customizations

### test-writer.md additions
- Use Vitest for unit tests, Playwright for E2E
- Mock next/navigation, next/headers in unit tests
- Test Server Actions by calling them directly
- E2E tests should use Playwright's page fixtures

### code-reviewer.md additions
- Check for unnecessary "use client" directives
- Verify Server/Client component boundary is correct
- Check that metadata exports exist on page components
- Verify proper error boundaries (error.tsx) exist

## Rules (path-scoped)

### src/app/api/**/*.ts
```
API Route Handlers must:
- Export named HTTP method functions (GET, POST, PUT, DELETE)
- Validate request body with zod
- Return NextResponse with appropriate status codes
- Handle errors with try/catch and return structured error responses
```

### src/server/actions/**/*.ts
```
Server Actions must:
- Start with "use server"
- Validate all input with zod
- Use revalidatePath or revalidateTag after mutations
- Return typed results, not throw errors (use a Result pattern)
```

## Hooks

### PostToolUse (after Edit/Write on .tsx/.ts files)
```bash
npx next lint --file $EDITED_FILE 2>/dev/null || true
```

## Common Patterns

### Data fetching
- Use async Server Components for initial data
- Use React Query (TanStack Query) for client-side data that needs refetching
- Use Server Actions for mutations

### Environment variables
- Create src/lib/env.ts with zod validation
- Import validated env object instead of using process.env directly
