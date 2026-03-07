# Vue 3 / Nuxt Stack Reference

## Directory Structure (Nuxt 3)

```
├── app/
│   ├── components/       # Auto-imported components
│   │   ├── ui/
│   │   └── [feature]/
│   ├── composables/      # Auto-imported composables (like React hooks)
│   ├── layouts/          # Layout components
│   ├── middleware/        # Route middleware
│   ├── pages/            # File-based routing
│   ├── plugins/          # Nuxt plugins
│   └── utils/            # Auto-imported utilities
├── server/
│   ├── api/              # Server API routes (Nitro)
│   ├── middleware/        # Server middleware
│   └── utils/            # Server utilities
├── stores/               # Pinia stores
├── types/                # TypeScript definitions
└── nuxt.config.ts
```

## Directory Structure (Vue 3 + Vite)

```
src/
├── components/
│   ├── ui/
│   └── [feature]/
├── composables/
├── views/                # Page components
├── router/               # Vue Router config
├── stores/               # Pinia stores
├── lib/
│   ├── api.ts
│   └── utils.ts
├── types/
├── App.vue
└── main.ts
```

## CLAUDE.md Additions

```markdown
## Tech Stack
- Framework: Nuxt 3 (or Vue 3 + Vite)
- Language: TypeScript
- State: Pinia
- Styling: Tailwind CSS (or UnoCSS)
- Testing: Vitest + Vue Test Utils + Playwright

## Commands
- Dev: npm run dev
- Build: npm run build
- Test: npm run test
- Lint: npm run lint
- Type check: npx nuxi typecheck (Nuxt) or npx vue-tsc (Vue)

## Code Conventions
- Use Composition API with <script setup> exclusively
- Composables for reusable logic (prefix with "use")
- Pinia stores for global state (one store per domain)
- Auto-imports enabled — don't manually import Vue APIs or composables
- Use definePageMeta for route metadata
- Use useFetch/useAsyncData for data fetching (Nuxt)

## Mistakes to Avoid
- NEVER use Options API — always Composition API with <script setup>
- NEVER mutate props directly
- ALWAYS use v-model with defineModel() for two-way binding in components
- NEVER use reactive() for primitives — use ref()
```

## Agent Customizations

### test-writer.md
- Use @vue/test-utils with Vitest
- Mount components with global plugins (Pinia, Router) in test setup
- Test composables by wrapping in a test component or using @vue/test-utils helpers
