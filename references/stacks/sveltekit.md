# SvelteKit Stack Reference

## Directory Structure

```
src/
├── lib/
│   ├── components/       # Reusable components
│   │   ├── ui/
│   │   └── [feature]/
│   ├── server/           # Server-only modules ($lib/server/)
│   │   ├── db.ts
│   │   └── auth.ts
│   ├── stores/           # Svelte stores
│   ├── utils/            # Utility functions
│   └── types/            # TypeScript types
├── routes/
│   ├── (auth)/           # Route group for auth
│   │   ├── login/
│   │   │   └── +page.svelte
│   │   └── register/
│   ├── (app)/            # Route group for main app
│   │   ├── +layout.svelte
│   │   ├── +layout.server.ts
│   │   └── dashboard/
│   ├── api/              # API endpoints
│   │   └── [resource]/
│   │       └── +server.ts
│   ├── +layout.svelte
│   ├── +page.svelte
│   └── +error.svelte
├── params/               # Param matchers
├── hooks.server.ts       # Server hooks (auth, logging)
└── app.d.ts              # App type declarations
```

## CLAUDE.md Additions

```markdown
## Tech Stack
- Framework: SvelteKit
- Language: TypeScript
- Styling: Tailwind CSS
- Testing: Vitest + Playwright

## Commands
- Dev: npm run dev
- Build: npm run build
- Preview: npm run preview
- Test: npm run test
- Test E2E: npm run test:e2e
- Lint: npm run lint
- Check: npm run check (svelte-check)

## Code Conventions
- Use +page.server.ts for server-side data loading (load functions)
- Use +page.ts for universal data loading
- Form actions for mutations (not API endpoints)
- $lib alias for src/lib imports
- Server-only code in $lib/server/ (enforced by SvelteKit)
- Use Svelte stores for shared client state
- Use runes ($state, $derived, $effect) in Svelte 5

## Mistakes to Avoid
- NEVER import $lib/server modules in client code
- ALWAYS use form actions for data mutations, not fetch()
- NEVER access cookies or headers outside load functions or hooks
- ALWAYS add +error.svelte pages for error handling
```
