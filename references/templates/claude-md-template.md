# CLAUDE.md Generation Template

Use this template as the structure for every CLAUDE.md you generate. The golden rule: keep it
under 200 lines. Every line should pass the test: "Would removing this cause Claude to make mistakes?"

## Template

```markdown
# {Project Name}

{One-to-two sentence description. e.g., "A multi-tenant SaaS invoicing platform built with
Next.js 15, PostgreSQL, and Clerk authentication."}

## Tech Stack
- Frontend: {framework} with {styling}
- Backend: {framework/language}
- Database: {database} with {ORM}
- Auth: {provider}
- Hosting: {platform}
- Testing: {framework}

## Commands
- Dev: {command}
- Build: {command}
- Test: {command}
- Test single: {command} {path}
- Lint: {command}
- Type check: {command}
- DB migrate: {command}
- DB seed: {command}
- Deploy: {command or "push to main"}

## Architecture
{2-3 sentences describing how the main components connect. e.g., "Next.js App Router handles
all frontend rendering and API routes. Server Actions handle mutations with Prisma for database
access. Clerk manages auth with webhook sync to our user table."}

{If monorepo:}
- apps/web: Next.js frontend
- apps/api: Express backend
- packages/shared: Shared types and utilities

## Code Conventions
{Only rules that DIFFER from the stack's standard conventions. Don't restate what Claude knows.}
- {Convention 1}
- {Convention 2}
- {Convention 3}

## Repository Etiquette
- Branch naming: {pattern, e.g., feature/TICKET-description, fix/TICKET-description}
- Commit format: {pattern, e.g., conventional commits}
- PR process: {description, e.g., "require 1 review, squash merge to main"}

## Key Paths
- API routes: {path}
- Database schema: {path}
- Shared components: {path}
- Auth config: {path}
- Environment config: {path}

## Mistakes to Avoid
- NEVER {critical mistake 1 for this specific stack}
- NEVER {critical mistake 2}
- ALWAYS {critical rule 1}
- ALWAYS {critical rule 2}
- CRITICAL: {most important rule, e.g., "Run tests before committing"}
```

## Customization Guidelines

### For monorepos
Add a "Workspaces" section listing each package/app and its purpose.

### For microservices
Add a "Services" section with each service name, port, and responsibility.

### For AI-integrated projects
Add an "AI Integration" section with provider, model, and usage patterns.

### For multi-tenant
Add a "Tenancy" section explaining the isolation model and how tenant context is resolved.

## What to EXCLUDE from CLAUDE.md

- Standard language conventions Claude already knows
- Detailed API documentation (link to docs instead)
- Long narrative paragraphs (Claude processes direct instructions better)
- Code style enforced by linters (they handle it automatically)
- File-by-file descriptions (Claude can read the code)
- More than 200 lines total
