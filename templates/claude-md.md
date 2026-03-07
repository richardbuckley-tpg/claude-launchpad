# CLAUDE.md Template (target: ≤100 lines)

Fill in values from the interview. Remove sections that don't apply.

```markdown
# {project_name}

{one_line_description}

## Tech Stack
- Frontend: {frontend_framework}
- Backend: {backend_framework}
- Database: {database} + {orm}
- Auth: {auth_provider}
- Hosting: {hosting_platform}

## Commands
- Dev: {dev_command}
- Build: {build_command}
- Test: {test_command}
- Lint: {lint_command}
- Type check: {typecheck_command}
- DB migrate: {migrate_command}
- DB seed: {seed_command}

## Architecture
{2-3 sentences: how components connect, data flow, key patterns}

See [ARCHITECTURE.md](./ARCHITECTURE.md) for detailed design decisions.

## Code Conventions
{5-8 bullet points — only conventions that differ from stack defaults}
- {convention_1}
- {convention_2}
- {convention_3}

## Mistakes to Avoid
- NEVER {mistake_1}
- NEVER {mistake_2}
- ALWAYS {practice_1}
- ALWAYS {practice_2}

## Key Paths
- {path_description}: `{path}`
- {path_description}: `{path}`
- {path_description}: `{path}`
- {path_description}: `{path}`

## Repository
- Branches: feature/*, fix/*, chore/*
- Commits: {conventional_commits | freeform}
- PRs: {pr_process}

## Session Management
Run `/handoff` at the end of each session to preserve context.
Run `/audit` periodically to check config health.
```
