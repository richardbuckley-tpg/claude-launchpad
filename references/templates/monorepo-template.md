# Monorepo Configuration Template

Generate monorepo configuration when the user chooses a monorepo structure.
Supports Turborepo, Nx, and pnpm workspaces.

## When to Use

- User explicitly chooses monorepo
- User has microservices with shared code
- User has frontend + backend in same repo with shared types
- User has multiple apps (web + mobile + admin) sharing code

## Turborepo (Recommended for Most Cases)

### Directory Structure
```
project-root/
├── CLAUDE.md                    # Root — monorepo-level instructions
├── turbo.json                   # Pipeline configuration
├── package.json                 # Root workspace config
├── .claude/
│   ├── agents/                  # Shared agents
│   ├── rules/
│   │   ├── packages.md          # Rules for shared packages
│   │   └── apps.md              # Rules for applications
│   └── settings.json
├── apps/
│   ├── web/
│   │   ├── CLAUDE.md            # App-specific instructions
│   │   └── ...
│   ├── admin/
│   │   ├── CLAUDE.md
│   │   └── ...
│   └── mobile/
│       ├── CLAUDE.md
│       └── ...
├── packages/
│   ├── ui/                      # Shared UI components
│   │   ├── CLAUDE.md
│   │   └── ...
│   ├── config/                  # Shared configs (eslint, tsconfig)
│   │   └── ...
│   ├── db/                      # Shared database client/schema
│   │   ├── CLAUDE.md
│   │   └── ...
│   └── types/                   # Shared TypeScript types
│       └── ...
└── tooling/                     # Build tooling, scripts
```

### Root CLAUDE.md Guidelines
```markdown
# {Project Name} — Monorepo

This is a Turborepo monorepo containing {list of apps/packages}.

## Monorepo Rules
- NEVER install dependencies in individual packages without updating root lockfile
- Always use `pnpm add <pkg> --filter <workspace>` to add dependencies
- Shared types go in `packages/types/` — never duplicate type definitions across apps
- Run `turbo build` before committing to verify all packages build correctly

## Commands
- `pnpm dev` — Start all apps in dev mode
- `pnpm build` — Build all packages and apps (uses Turborepo caching)
- `pnpm test` — Run tests across all packages
- `pnpm lint` — Lint all packages
- `turbo run build --filter=web` — Build only the web app and its dependencies
- `turbo run test --filter=./packages/*` — Test only shared packages

## Package Dependencies
- `apps/web` depends on: `packages/ui`, `packages/db`, `packages/types`
- `apps/admin` depends on: `packages/ui`, `packages/db`, `packages/types`
- `packages/ui` depends on: `packages/types`
- `packages/db` depends on: `packages/types`
```

### Per-Package CLAUDE.md (Shorter)
Each package/app gets a brief CLAUDE.md focused on:
- What this package does (1 sentence)
- Package-specific commands
- Key patterns unique to this package
- Cross-package dependencies to be aware of

### turbo.json Template
```json
{
  "$schema": "https://turbo.build/schema.json",
  "globalDependencies": ["**/.env.*local"],
  "pipeline": {
    "build": {
      "dependsOn": ["^build"],
      "outputs": ["dist/**", ".next/**", "!.next/cache/**"]
    },
    "test": {
      "dependsOn": ["build"]
    },
    "lint": {},
    "dev": {
      "cache": false,
      "persistent": true
    }
  }
}
```

## Nx (For Larger Teams / Enterprise)

### Additional Configuration
- `nx.json` for workspace configuration
- Per-project `project.json` files
- Nx Cloud for distributed caching (optional)

### Root CLAUDE.md Additions for Nx
```markdown
## Nx Commands
- `nx run <project>:<target>` — Run a specific target
- `nx affected --target=test` — Test only affected projects
- `nx graph` — Visualize project dependencies
- `nx migrate latest` — Update Nx and plugins
```

## pnpm Workspaces (Lightweight)

### pnpm-workspace.yaml
```yaml
packages:
  - 'apps/*'
  - 'packages/*'
```

## Monorepo-Specific Rules

Generate `.claude/rules/monorepo.md`:
```markdown
# Monorepo Rules

## Import Boundaries
- Apps can import from packages but NEVER from other apps
- Packages can import from other packages but check for circular dependencies
- Use workspace protocol (`workspace:*`) for internal dependencies

## Change Impact
- Changes to `packages/types` affect ALL apps — run full test suite
- Changes to `packages/ui` affect apps that use UI components
- Changes within a single app only require testing that app

## Dependency Management
- All dependencies managed at root via pnpm
- Use `pnpm add <pkg> --filter <workspace>` to add to specific workspace
- Run `pnpm install` from root after pulling to sync lockfile
```

## Generation Rules

1. Ask about monorepo tool preference during Phase 1 (default: Turborepo for JS/TS, Nx for enterprise)
2. Generate root CLAUDE.md + per-package CLAUDE.md files
3. Generate `.claude/rules/monorepo.md` with import boundaries
4. Adjust scaffold.py output for monorepo directory structure
5. Configure agents to understand the monorepo structure (especially CTO and reviewer agents)
6. Add monorepo-specific hooks (e.g., verify import boundaries on file save)
