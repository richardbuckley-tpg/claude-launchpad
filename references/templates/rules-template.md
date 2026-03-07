# Rules Generation Template

Generate rules in `.claude/rules/` based on the project's stack and architecture.
Each rule file is a markdown file with optional YAML frontmatter for path scoping.

## Path-Scoped Rule Pattern

```markdown
---
scope: src/api/**/*.ts
---
# API Route Rules
{Rules that only apply to API code}
```

## Core Rules (generate for all projects)

### general.md
```markdown
# General Development Rules

- Run tests after every significant code change
- Verify the build succeeds before considering a task complete
- Use Plan Mode (Shift+Tab) for any change touching more than 3 files
- When investigating bugs, scope narrowly — examine only the relevant module
- Prefer modifying existing files over creating new ones
- Keep functions focused — if a function does more than one thing, split it
```

### git.md
```markdown
# Git Conventions

- Branch naming: {branch_pattern}
- Commit messages: {commit_format}
- Always run tests before committing
- Never commit .env files, secrets, or credentials
- Never force push to {main_branch}
- Squash merge feature branches to keep history clean
- Delete branches after merge
```

## Stack-Specific Rules (generate based on choices)

### Frontend Rules ({frontend_scope})

```markdown
---
scope: {frontend_path}/**/*
---
# Frontend Rules

{Generated from the relevant stack reference — only non-obvious conventions}
```

### Backend Rules ({backend_scope})

```markdown
---
scope: {backend_path}/**/*
---
# Backend Rules

{Generated from the relevant stack reference}
```

### Database Rules

```markdown
---
scope: {migration_path}/**/*
---
# Database Migration Rules

- NEVER modify existing migration files
- ALWAYS test migrations forward and backward
- {ORM-specific rules from database reference}
```

### Test Rules

```markdown
---
scope: {test_pattern}
---
# Testing Rules

- Test files live alongside source files (ComponentName.test.{ext})
- Use descriptive test names: "should [expected behavior] when [condition]"
- Mock external dependencies, never make real API/network calls in unit tests
- Each test should be independent — no shared mutable state between tests
- {Framework-specific rules}
```

## Multi-Tenant Rules (if applicable)

```markdown
# Multi-Tenant Rules

- EVERY database query must include tenant context (org_id, tenant_id)
- NEVER allow cross-tenant data access — verify tenant isolation in tests
- Tenant context must be set in middleware, not passed manually
- Test with multiple tenants to verify isolation
- {RLS/query filter specific patterns}
```

## AI Integration Rules (if applicable)

```markdown
---
scope: {ai_code_path}/**/*
---
# AI/LLM Integration Rules

- Store system prompts in version-controlled files, not inline strings
- Always set max_tokens to prevent cost overruns
- Implement retry logic with exponential backoff
- Never log full prompts or completions in production (PII risk)
- Validate and sanitize all LLM outputs before use
- Use structured output (tool use / JSON mode) when possible
- Track token usage and costs per request
```

## Rules to AVOID Creating

Don't create rules for:
- Standard language conventions (Claude knows these)
- Style preferences enforced by linters/formatters
- Obvious good practices ("write clean code", "use meaningful variable names")
- Anything already in CLAUDE.md (rules supplement, not duplicate)
