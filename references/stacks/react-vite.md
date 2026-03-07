# React + Vite Stack Reference

## Directory Structure

```
src/
├── components/
│   ├── ui/               # Reusable UI primitives
│   ├── layout/           # Layout components (Header, Sidebar, Footer)
│   └── [feature]/        # Feature-specific components
├── pages/                # Page-level components (one per route)
├── hooks/                # Custom React hooks
├── lib/
│   ├── api.ts            # API client (fetch wrapper or axios instance)
│   ├── utils.ts          # Utility functions
│   └── validations/      # Zod schemas
├── stores/               # State management (Zustand stores or Context)
├── types/                # TypeScript type definitions
├── routes/               # Route definitions (React Router or TanStack Router)
├── assets/               # Static assets (images, fonts)
├── styles/               # Global styles
├── App.tsx
└── main.tsx
```

## CLAUDE.md Additions

```markdown
## Tech Stack
- Framework: React 19 + Vite
- Language: TypeScript with strict mode
- Routing: React Router v7 (or TanStack Router)
- State: Zustand for global state, React Query for server state
- Styling: Tailwind CSS
- Testing: Vitest + React Testing Library + Playwright

## Commands
- Dev: npm run dev
- Build: npm run build
- Preview: npm run preview
- Test: npm run test
- Test UI: npm run test:ui
- Lint: npm run lint
- Type check: npx tsc --noEmit

## Code Conventions
- Feature-based component organization
- Custom hooks extract complex logic from components
- API calls go through src/lib/api.ts, never directly in components
- All API responses validated with zod
- Use React Query for all server state
- Use Zustand for UI/app state that spans components
- Lazy-load route-level components with React.lazy()

## Mistakes to Avoid
- NEVER store server state in Zustand — use React Query
- NEVER make API calls directly in components — use hooks or queries
- ALWAYS handle loading and error states in data-fetching components
- NEVER use index.ts barrel exports excessively (hurts tree-shaking)
```

## Agent Customizations

### test-writer.md
- Use Vitest with jsdom environment
- Use @testing-library/react for component tests
- Use @testing-library/user-event for interactions
- Mock API calls with MSW (Mock Service Worker)

## Rules

### src/components/**/*.tsx
```
Components must:
- Be named exports (not default exports) for better refactoring
- Have co-located test files (ComponentName.test.tsx)
- Props defined as TypeScript interfaces, not inline types
- Use forwardRef when wrapping native elements
```

## Hooks

### PostToolUse (after Edit/Write)
```bash
npx eslint --fix $EDITED_FILE 2>/dev/null || true
```
