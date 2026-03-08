# CLAUDE.md Template — Discoverability-First (target: ≤100 lines)

Based on ETH Zurich research: only include information Claude CANNOT discover
by reading the codebase. Auto-discoverable info (file structure, import patterns,
existing code conventions) should NOT be in CLAUDE.md — it wastes tokens and
can reduce task success by ~3%.

Fill in values from the interview. Delete sections that don't apply.

```markdown
# {project_name}

{one_line_description}

## Commands
- Dev: `{dev_command}`
- Build: `{build_command}`
- Test: `{test_command}`
- Lint: `{lint_command}`
- Type check: `{typecheck_command}`
- DB migrate: `{migrate_command}`

## Architecture Decisions (non-obvious)
{2-3 key decisions that aren't visible from code alone}
- Why {technology_choice}: {reason}
- Why {pattern_choice}: {reason}

See [ARCHITECTURE.md](./ARCHITECTURE.md) for full design.

## Conventions Not Discoverable from Code
{Only conventions that deviate from framework defaults or can't be inferred}
- {convention_1}
- {convention_2}

## Mistakes to Avoid
- NEVER {mistake_1}
- NEVER {mistake_2}
- ALWAYS {practice_1}

## Environment Setup
{Only if non-standard — skip if just "npm install" or "pip install -r requirements.txt"}
- {setup_step_if_unusual}

## Repository
- Branches: feature/*, fix/*, chore/*
- Commits: {conventional_commits | freeform}

## Session Management
Run `/handoff` at end of each session. Run `/status` to resume.
```

## What NOT to Include

These waste tokens because Claude can discover them by reading the codebase:
- File/directory structure (Claude reads the filesystem)
- Import patterns (visible in source files)
- Component naming conventions (visible from existing components)
- API route patterns (visible from route files)
- Database schema (visible from ORM models/migrations)
- TypeScript/Python type patterns (visible from existing code)
- Error handling patterns (visible from existing error handlers)
- Test file naming conventions (visible from test directory)

## What TO Include

Only information that is NOT discoverable:
- Build/test/lint commands (not in source code)
- Why decisions were made (not in code — architectural context)
- Environment-specific setup steps
- External service dependencies and their quirks
- Security rules that aren't enforced by code
- Process rules (branching, PR conventions)
