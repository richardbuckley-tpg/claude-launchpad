#!/usr/bin/env python3
"""
claude-launchpad scaffold script v6.0.0

Creates the .claude/ configuration directory with agents, rules, hooks, skills,
commands, and supporting files — all with real values from the interview.

Usage:
    python scaffold.py --project-name "my-app" --frontend nextjs --backend integrated \
        --database postgresql --auth clerk --output-dir .
"""

import argparse
import json
import re
import subprocess
import sys
from datetime import datetime
from pathlib import Path

VERSION = "6.0.0"

PROJECT_NAME_PATTERN = re.compile(r'^[a-zA-Z0-9][a-zA-Z0-9._-]*$')

# Allowlist for user-provided commands (--lint-cmd, --test-cmd)
# Only permit known safe command patterns to prevent injection
# Supports `--` arg separator (e.g., `npm run lint -- --fix`)
SAFE_CMD_PATTERN = re.compile(
    r'^(?:npm|npx|pnpm|yarn|bun) (?:run |exec |dlx )?[a-zA-Z0-9:_-]+(?:\s+(?:--|--[a-zA-Z0-9_-]+(?:=[a-zA-Z0-9_./-]+)?))*$'
    r'|^(?:pytest|ruff|mypy|black|flake8|pylint|isort)(?:\s+[a-zA-Z0-9_./-]+)*(?:\s+(?:--|--[a-zA-Z0-9_-]+(?:=[a-zA-Z0-9_./-]+)?))*$'
    r'|^(?:go (?:test|vet|fmt|run [\./a-zA-Z0-9_-]+)|golangci-lint run)(?:\s+[./a-zA-Z0-9_-]+)*$'
    r'|^(?:cargo (?:test|clippy|fmt|check|run|build))(?:\s+--[a-zA-Z0-9_-]+)*$'
    r'|^(?:bundle exec (?:rubocop|rspec|rails test))(?:\s+[a-zA-Z0-9_./-]+)*$'
    r'|^(?:rails (?:test|db:migrate|server))(?:\s+[a-zA-Z0-9_./-]+)*$'
    r'|^(?:flutter (?:test|analyze|build|run))(?:\s+[a-zA-Z0-9_./-]+)*$'
    r'|^(?:uvicorn\s+[a-zA-Z0-9_.:-]+)(?:\s+--[a-zA-Z0-9_-]+(?:\s+[a-zA-Z0-9_.:-]+)?)*$'
    r'|^(?:alembic (?:upgrade|downgrade|revision))(?:\s+[a-zA-Z0-9_. "-]+)*$'
    r'|^(?:npx prisma (?:migrate dev|migrate deploy|generate|db push|db seed|studio))(?:\s+--[a-zA-Z0-9_-]+(?:\s+[a-zA-Z0-9_./-]+)?)*$'
    r'|^(?:npx drizzle-kit (?:generate|migrate|studio))$'
    r'|^make\s+[a-zA-Z0-9_-]+$'
)


# Pinned MCP package versions (update periodically)
MCP_VERSIONS = {
    "server-github": "@modelcontextprotocol/server-github@2025.1.1",
    "server-gitlab": "@modelcontextprotocol/server-gitlab@2025.1.1",
    "server-postgres": "@modelcontextprotocol/server-postgres@2025.1.1",
    "server-sqlite": "@modelcontextprotocol/server-sqlite@2025.1.1",
    "server-filesystem": "@modelcontextprotocol/server-filesystem@2025.1.1",
    "server-sentry": "@modelcontextprotocol/server-sentry@2025.1.1",
    "context7": "context7-mcp@1.0.6",
    "sequential-thinking": "@anthropic/sequential-thinking-mcp@1.0.0",
}

# Estimated tokens per MCP server in context window (tool descriptions + overhead)
MCP_CONTEXT_COST = 3000  # ~3,000 tokens per active MCP server

# Valid top-level keys in settings.json
VALID_SETTINGS_KEYS = {"hooks", "mcpServers", "permissions", "env", "model", "apiKey"}

# Presets — common stack combinations
PRESETS = {
    "nextjs-fullstack": {
        "frontend": "nextjs", "backend": "integrated", "database": "postgresql",
        "orm": "prisma", "auth": "clerk", "hosting": "vercel",
        "git_platform": "github", "ci_cd": "github-actions",
        "conventional_commits": True, "tdd": True,
    },
    "nextjs-supabase": {
        "frontend": "nextjs", "backend": "integrated", "database": "supabase",
        "orm": "none", "auth": "supabase-auth", "hosting": "vercel",
        "git_platform": "github", "ci_cd": "github-actions",
        "conventional_commits": True,
    },
    "react-express": {
        "frontend": "react-vite", "backend": "node-express", "database": "postgresql",
        "orm": "prisma", "auth": "custom-jwt", "hosting": "railway",
        "git_platform": "github", "ci_cd": "github-actions",
    },
    "fastapi": {
        "frontend": "none", "backend": "python-fastapi", "database": "postgresql",
        "orm": "sqlalchemy", "auth": "custom-jwt", "hosting": "railway",
        "git_platform": "github", "ci_cd": "github-actions",
    },
    "go-api": {
        "frontend": "none", "backend": "go", "database": "postgresql",
        "orm": "none", "auth": "custom-jwt", "hosting": "aws",
        "git_platform": "github", "ci_cd": "github-actions",
    },
    "sveltekit-fullstack": {
        "frontend": "sveltekit", "backend": "integrated", "database": "postgresql",
        "orm": "drizzle", "auth": "custom-jwt", "hosting": "vercel",
        "git_platform": "github", "ci_cd": "github-actions",
    },
    "rails": {
        "frontend": "none", "backend": "ruby-rails", "database": "postgresql",
        "orm": "activerecord", "auth": "custom-jwt", "hosting": "railway",
        "git_platform": "github", "ci_cd": "github-actions",
    },
}

# ── Slash Commands ───────────────────────────────────────────────────────

def cmd_project_status():
    return """---
description: Show project status — recent changes, test health, open TODOs
---

Give me a quick project status report:
1. Check `git status` and `git log --oneline -5` for recent activity
2. Read `.claude/handoff.md` for current state
3. Run the test suite to check health
4. Look for TODO/FIXME in recently changed files

Present: recent changes, branch state, test health, open TODOs, next action.
"""

def cmd_handoff():
    return """---
description: Update session handoff document for context preservation
---

Update `.claude/handoff.md` with the current session state:
1. Read the current handoff document
2. Update "What's Working" with completed items
3. Update "In Progress" with current work
4. Update "Known Issues" with any problems found
5. Update "Next Steps" with recommended actions
6. Save the file

This preserves context for the next session.
"""

def cmd_new_feature():
    return """---
description: Start a new feature with proper branching and planning
---

Starting new feature: $ARGUMENTS

1. Create branch: `git checkout -b feature/$ARGUMENTS`
2. Read ARCHITECTURE.md for current design
3. Read `.claude/handoff.md` for project state
4. Plan: what files change, what's new, what tests needed, any DB changes?
5. Present plan for approval before writing code.
"""

def cmd_fix_bug():
    return """---
description: Systematically diagnose and fix a bug
---

Investigating: $ARGUMENTS

Follow the debugger methodology:
1. **Reproduce**: Trigger the bug
2. **Isolate**: Trace data flow, find the boundary where it breaks
3. **Diagnose**: Identify root cause (don't guess)
4. **Fix**: Minimal fix for root cause
5. **Test**: Write regression test that fails without fix
6. **Verify**: Run full test suite
"""

def cmd_audit(skill_path):
    return f"""---
description: Audit Claude Code config for health, token cost, and issues
---

Run the Claude Launchpad auditor on this project:
1. Run: `python3 {skill_path}/scripts/audit.py .`
2. Display the health report with token estimates
3. For each issue, suggest the specific fix
4. If $ARGUMENTS contains "--fix": `python3 {skill_path}/scripts/audit.py . --fix`
5. For recommendations: `python3 {skill_path}/scripts/audit.py . --recommend`
"""

def cmd_tdd():
    return """---
description: Start a TDD red-green-refactor cycle
---

TDD cycle for: $ARGUMENTS

1. **Red**: Write a failing test that describes the desired behavior
2. **Green**: Write the minimum code to make the test pass
3. **Refactor**: Clean up without changing behavior, re-run tests
4. Repeat until the feature is complete

Run tests after every change. Never skip the refactor step.
"""

def cmd_pipeline():
    return """---
description: Run full feature pipeline from spec to PR
---

Feature: $ARGUMENTS

Pipeline:
1. **Architect**: Design the solution (use architect agent)
2. **Security**: Review the design (use security agent)
3. **Implement**: Build it following the blueprint
4. **Test**: Write tests (use testing agent)
5. **Review**: Code review (use reviewer agent)
6. **Push**: Branch, commit, PR (use push agent)
"""

def cmd_idea_to_prd():
    return """---
description: Research an idea and generate a PRD for /build
---

Idea: $ARGUMENTS

Run `@idea-to-prd Research and write a PRD for "$ARGUMENTS"`

The agent will:
1. Research online for best practices and competitor features
2. Generate a structured PRD in `docs/prds/`
3. Present the PRD for your review

Once approved, start building with: `/build <feature-name>` (reference the PRD)
"""


def cmd_build(domain="general", compliance=None, tdd=False, worktree=True):
    has_domain = domain != "general"
    has_compliance = compliance and compliance != ['none'] and 'none' not in compliance
    has_domain_audit = has_domain or has_compliance

    # Worktree setup/cleanup steps
    worktree_setup = ""
    worktree_cleanup = ""
    if worktree:
        worktree_setup = """
1. **Worktree**: Create an isolated workspace for this feature
   - `git worktree add .worktrees/$ARGUMENTS -b feature/$ARGUMENTS`
   - If worktree creation fails (shallow clone, etc.), fall back to a regular branch: `git checkout -b feature/$ARGUMENTS`
   - All subsequent work happens in the worktree directory
"""
        worktree_cleanup = """
**Cleanup**: Remove the worktree (even if the pipeline failed)
   - `git worktree remove .worktrees/$ARGUMENTS`
"""

    step = 3 if worktree else 2  # account for worktree step

    # Build the pipeline stages
    # In TDD mode: [Security + Testing] parallel, then Implement, then [Domain + Review] parallel
    # In non-TDD mode: Security, Implement, then [Testing + Domain] parallel if domain, then Review

    if tdd:
        if has_domain_audit:
            # TDD + domain: two parallel groups
            return f"""---
description: Full feature pipeline — design, build, test, review, ship
---

Feature: $ARGUMENTS

Execute the full development pipeline with context passing through blueprints:

0. **PRD** (optional): If a PRD exists in `docs/prds/` for this feature, read it first.
   - The architect uses the PRD as input. If no PRD exists, skip this step.
   - To create a PRD from an idea: `/idea-to-prd <idea>`
{worktree_setup}
{step}. **Design**: Run `@architect Design the "$ARGUMENTS" feature`
   - Wait for blueprint in `docs/blueprints/`
   - Review the blueprint and get approval before continuing

{step + 1}. **Security + Testing** — run these IN PARALLEL (launch both simultaneously):
   - `@security Review the blueprint`
   - `@testing Write failing tests for "$ARGUMENTS"` (TDD: tests define the contract)
   Wait for BOTH to complete. If security finds CRITICAL: stop the pipeline.
   Run tests to confirm they fail (red) — this validates the tests are meaningful.

{step + 2}. **Implement**: Build until all tests pass (green)
   - Read the blueprint AND the failing tests — both are your spec
   - Follow existing patterns (check `.claude/rules/`)
   - Run tests after each major piece — stay in the red→green loop
   - Once green, refactor if needed (tests protect you)

{step + 3}. **Domain Audit + Review** — run these IN PARALLEL (launch both simultaneously):
   - `@compliance-auditor Audit "$ARGUMENTS" for domain compliance`
   - `@reviewer Review all changes`
   Wait for BOTH to complete. Non-compliant findings or REQUEST_CHANGES block shipping.

{step + 4}. **Pre-flight**: Run `@pre-push Run pre-push checks`
   - Must be READY before shipping — fix any failures first

{step + 5}. **Ship**: Run `@push Create PR for "$ARGUMENTS"`
{worktree_cleanup}
Update `.claude/handoff.md` after completion.
"""
        else:
            # TDD without domain: one parallel group (security + testing)
            return f"""---
description: Full feature pipeline — design, build, test, review, ship
---

Feature: $ARGUMENTS

Execute the full development pipeline with context passing through blueprints:

0. **PRD** (optional): If a PRD exists in `docs/prds/` for this feature, read it first.
   - The architect uses the PRD as input. If no PRD exists, skip this step.
   - To create a PRD from an idea: `/idea-to-prd <idea>`
{worktree_setup}
{step}. **Design**: Run `@architect Design the "$ARGUMENTS" feature`
   - Wait for blueprint in `docs/blueprints/`
   - Review the blueprint and get approval before continuing

{step + 1}. **Security + Testing** — run these IN PARALLEL (launch both simultaneously):
   - `@security Review the blueprint`
   - `@testing Write failing tests for "$ARGUMENTS"` (TDD: tests define the contract)
   Wait for BOTH to complete. If security finds CRITICAL: stop the pipeline.
   Run tests to confirm they fail (red) — this validates the tests are meaningful.

{step + 2}. **Implement**: Build until all tests pass (green)
   - Read the blueprint AND the failing tests — both are your spec
   - Follow existing patterns (check `.claude/rules/`)
   - Run tests after each major piece — stay in the red→green loop
   - Once green, refactor if needed (tests protect you)

{step + 3}. **Review**: Run `@reviewer Review all changes`
   - Must APPROVE before shipping

{step + 4}. **Pre-flight**: Run `@pre-push Run pre-push checks`
   - Must be READY before shipping — fix any failures first

{step + 5}. **Ship**: Run `@push Create PR for "$ARGUMENTS"`
{worktree_cleanup}
Update `.claude/handoff.md` after completion.
"""
    else:
        if has_domain_audit:
            # Non-TDD + domain: parallel testing + domain audit after implement
            return f"""---
description: Full feature pipeline — design, build, test, review, ship
---

Feature: $ARGUMENTS

Execute the full development pipeline with context passing through blueprints:

0. **PRD** (optional): If a PRD exists in `docs/prds/` for this feature, read it first.
   - The architect uses the PRD as input. If no PRD exists, skip this step.
   - To create a PRD from an idea: `/idea-to-prd <idea>`
{worktree_setup}
{step}. **Design**: Run `@architect Design the "$ARGUMENTS" feature`
   - Wait for blueprint in `docs/blueprints/`
   - Review the blueprint and get approval before continuing

{step + 1}. **Security** (if auth/payments involved): Run `@security Review the blueprint`

{step + 2}. **Implement**: Build following the approved blueprint
   - Read the blueprint first — it's the spec
   - Follow existing patterns (check `.claude/rules/`)
   - Create all layers: data model, API, UI, types

{step + 3}. **Testing + Domain Audit** — run these IN PARALLEL (launch both simultaneously):
   - `@testing Write tests for "$ARGUMENTS"` — tests must pass
   - `@compliance-auditor Audit "$ARGUMENTS" for domain compliance` — must be compliant
   Wait for BOTH to complete. Test failures or non-compliant findings block shipping.

{step + 4}. **Review**: Run `@reviewer Review all changes`
   - Must APPROVE before shipping

{step + 5}. **Pre-flight**: Run `@pre-push Run pre-push checks`
   - Must be READY before shipping — fix any failures first

{step + 6}. **Ship**: Run `@push Create PR for "$ARGUMENTS"`
{worktree_cleanup}
Update `.claude/handoff.md` after completion.
"""
        else:
            # Non-TDD without domain: no meaningful parallelism
            return f"""---
description: Full feature pipeline — design, build, test, review, ship
---

Feature: $ARGUMENTS

Execute the full development pipeline with context passing through blueprints:

0. **PRD** (optional): If a PRD exists in `docs/prds/` for this feature, read it first.
   - The architect uses the PRD as input. If no PRD exists, skip this step.
   - To create a PRD from an idea: `/idea-to-prd <idea>`
{worktree_setup}
{step}. **Design**: Run `@architect Design the "$ARGUMENTS" feature`
   - Wait for blueprint in `docs/blueprints/`
   - Review the blueprint and get approval before continuing

{step + 1}. **Security** (if auth/payments involved): Run `@security Review the blueprint`

{step + 2}. **Implement**: Build following the approved blueprint
   - Read the blueprint first — it's the spec
   - Follow existing patterns (check `.claude/rules/`)
   - Create all layers: data model, API, UI, types

{step + 3}. **Test**: Run `@testing Write tests for "$ARGUMENTS"`
   - Tests are based on the blueprint, not the implementation
   - Must pass before continuing

{step + 4}. **Review**: Run `@reviewer Review all changes`
   - Must APPROVE before shipping

{step + 5}. **Pre-flight**: Run `@pre-push Run pre-push checks`
   - Must be READY before shipping — fix any failures first

{step + 6}. **Ship**: Run `@push Create PR for "$ARGUMENTS"`
{worktree_cleanup}
Update `.claude/handoff.md` after completion.
"""


def cmd_analyze(skill_path):
    return f"""---
description: Analyze codebase and generate project-specific rules
---

Analyze the codebase to detect patterns and generate targeted rules:
1. Run: `python3 {skill_path}/scripts/analyze.py .`
2. Review detected patterns — stack, error handling, auth, validation, testing, etc.
3. If patterns look correct, write rules: `python3 {skill_path}/scripts/analyze.py . --write-rules`
4. Run audit to verify: `python3 {skill_path}/scripts/audit.py .`
5. Show what was generated

This replaces generic framework rules with project-specific ones based on actual code.
"""


def cmd_learn(skill_path):
    return f"""---
description: Record a correction for Claude to remember
---

$ARGUMENTS

Record this as a learned rule so Claude doesn't repeat the mistake:
1. Run: `python3 {skill_path}/scripts/learn.py . --capture "$ARGUMENTS"`
2. Confirm the rule was saved to .claude/rules/learned.md
3. Show all currently learned rules: `python3 {skill_path}/scripts/learn.py . --show`

These rules persist across sessions and get more specific over time.
To remove a learned rule: `python3 {skill_path}/scripts/learn.py . --forget "<query>"`
To analyze git history for corrections: `python3 {skill_path}/scripts/learn.py . --from-git`
"""


def cmd_evolve(skill_path):
    return f"""---
description: Re-analyze codebase, merge learned corrections, update rules, audit
---

Evolve the project's Claude Code configuration:

1. **Check stale rules**: `python3 {skill_path}/scripts/analyze.py . --check-stale`
2. **Re-analyze**: `python3 {skill_path}/scripts/analyze.py . --incorporate-learned --write-rules --force`
   This re-scans the codebase AND merges learned corrections into rules
3. **Audit**: `python3 {skill_path}/scripts/audit.py .`
4. **Report**: Show what changed — new patterns, incorporated corrections, stale rules fixed

This closes the feedback loop: corrections you taught Claude via /learn
get baked into the analyzer's rules, so they apply to new code automatically.
"""


# ── Skills ───────────────────────────────────────────────────────────────

def get_skills(args):
    """Return list of (name, content) tuples for skills based on interview answers."""
    skills = []
    fe = args.frontend
    be = args.backend
    db = args.database
    orm = getattr(args, 'orm', 'none') or 'none'

    # Always generated
    skills.append(("simplify", f"""---
description: Review code for unnecessary complexity and suggest simpler alternatives
---

Review $ARGUMENTS for complexity:
1. Over-engineered patterns, unnecessary abstractions, premature optimization
2. Dead code, unused imports, redundant assertions
3. Functions >50 lines that could decompose
4. Stack-specific anti-patterns ({fe}/{be})

Anti-patterns: Don't sacrifice readability for cleverness. Don't add abstraction for single-use code.

Verify: Run lint + tests after changes. Confirm no behavior change.
"""))

    skills.append(("generate-feature", f"""---
description: Scaffold a complete feature module with all layers
---

Generate feature: $ARGUMENTS

1. Read ARCHITECTURE.md for current patterns
2. Identify layers needed (UI, API, DB, types, tests)
3. Generate each file following existing conventions
4. Include imports, types, error handling, validation
5. Add tests for core logic
6. Update barrel exports or route registrations

Anti-patterns: Don't invent new patterns — extend existing ones. Don't skip tests.

Verify: All tests pass. New files follow existing naming conventions. No circular imports.
"""))

    # Frontend skills
    if fe and fe != "none":
        lib = {"nextjs": "React TSX", "react-vite": "React TSX", "vue": "Vue SFC", "sveltekit": "Svelte"}.get(fe, "component")

        skills.append(("generate-component", f"""---
description: Scaffold a {lib} component with types and tests
---

Create {lib} component: $ARGUMENTS

1. Component file in the right directory (check existing components)
2. TypeScript types/props interface
3. Default export, proper styling (match project approach)
4. Co-located test file
5. Add to barrel export if one exists

Anti-patterns: Don't exceed 150 lines — split if larger. Don't mix concerns in one component.

Verify: Component renders without errors. Props interface exported. Test file exists.
"""))

        skills.append(("generate-page", f"""---
description: Scaffold a new page/route with data fetching and SEO
---

Create page: $ARGUMENTS

1. Page file in routing directory
2. Metadata/SEO (title, description)
3. Data fetching (match project pattern)
4. Loading and error states
5. Auth protection if needed
6. Basic test

Anti-patterns: Don't skip error/loading states. Don't fetch data in client components when server is available.

Verify: Page loads without errors. SEO metadata present. Loading state works.
"""))

    # Backend / API skills
    if be and be not in ("none", "integrated"):
        api = {"node-express": "Express", "node-fastify": "Fastify", "python-fastapi": "FastAPI", "python-django": "Django", "go": "Go", "rust-actix": "Actix-web", "ruby-rails": "Rails"}.get(be, "API")
        skills.append(("generate-endpoint", f"""---
description: Scaffold a {api} endpoint with validation and tests
---

Create {api} endpoint: $ARGUMENTS

1. Route/handler following existing patterns
2. Input validation (project's validation library)
3. Error handling with proper HTTP status codes
4. Auth/authz checks if needed
5. Request/response types
6. Integration tests

Anti-patterns: Don't skip input validation. Don't return raw DB errors to clients.

Verify: All status codes tested. Auth checked. Input validation rejects bad data.
"""))
    elif fe in ("nextjs", "sveltekit"):
        rt = "Next.js API route" if fe == "nextjs" else "SvelteKit endpoint"
        skills.append(("generate-endpoint", f"""---
description: Scaffold a {rt} with validation and tests
---

Create {rt}: $ARGUMENTS

1. Route file in API directory
2. Input validation and type checking
3. Error handling with proper status codes
4. Auth checks if needed
5. Request/response types
6. Tests

Anti-patterns: Don't skip validation. Don't expose internal errors.

Verify: Status codes correct. Auth applied. Tests cover happy + error paths.
"""))

    # Database skills
    orm_label = STACK_LABELS.get(orm, orm) if orm and orm != "none" else "your ORM"
    if db and db != "none":
        if orm in ("prisma", "drizzle"):
            type_step = "6. Export TypeScript types (Prisma generates, Drizzle infers from schema)"
        elif orm in ("sqlalchemy",):
            type_step = "6. Add Pydantic schemas for API layer (separate from SQLAlchemy models)"
        elif orm in ("mongoose",):
            type_step = "6. Add TypeScript interfaces matching the Mongoose schema"
        elif orm in ("activerecord",):
            type_step = "6. Add serializer for API responses"
        else:
            type_step = "6. Add types/schemas for the model"
        skills.append(("generate-model", f"""---
description: Define a {orm_label} model with migration and seed data
---

Create model: $ARGUMENTS

1. Check existing models in project for naming conventions
2. Define {orm_label} schema with proper types and constraints
3. Add relationships to existing models if needed
4. Generate migration{' (`' + (getattr(args, 'migrate_cmd', None) or '') + '`)' if getattr(args, 'migrate_cmd', None) else ''}
5. Create seed data
{type_step}
7. Create basic CRUD query layer

Anti-patterns: Don't skip migrations. Don't create models without relationships to existing schema.

Verify: Migration runs cleanly. Seed data loads. Types match schema.
"""))

        skills.append(("generate-crud", f"""---
description: Generate complete CRUD operations for a model
---

CRUD for: $ARGUMENTS

1. Find model definition
2. Create: create, getById, getAll (paginated), update, delete
3. Input validation for create/update
4. Error handling (not found, validation, conflicts)
5. Filtering and sorting for list
6. Tests for each operation
7. API routes exposing operations

Anti-patterns: Don't skip pagination on list. Don't return unbounded results.

Verify: All 5 operations work. Validation rejects bad input. Pagination correct.
"""))

    # Auth skills
    auth = args.auth or "none"
    if auth != "none":
        skills.append(("add-protected-route", f"""---
description: Add auth protection to a route using {auth}
---

Protect: $ARGUMENTS

1. Check existing auth middleware/guards ({auth})
2. Add authentication check (redirect if not authenticated)
3. Add authorization if role-based access needed
4. Handle loading states during auth check
5. Handle expired sessions
6. Test both authenticated and unauthenticated cases

Auth: {auth}. Follow existing auth patterns.
"""))

    # AI skills
    if args.ai:
        skills.append(("prompt-engineer", """---
description: Design, test, and iterate on an AI/LLM prompt
---

Design prompt for: $ARGUMENTS

1. Define task: what input, what output expected
2. Write initial prompt: system instructions, I/O format, examples
3. Create 5 test cases (normal, edge, adversarial)
4. Run tests and evaluate
5. Iterate on failures
6. Document final prompt with usage notes

Version prompts. Explain changes in comments.
"""))

        skills.append(("add-ai-feature", """---
description: Add an AI feature with streaming, error handling, and fallbacks
---

Add AI feature: $ARGUMENTS

1. Design prompt (use prompt-engineer skill if complex)
2. Create API route/handler
3. Implement streaming if user-facing
4. Error handling: rate limits, timeouts, service unavailable
5. Input validation and output parsing
6. Caching if responses are deterministic
7. Cost tracking/logging
8. Tests with mocked AI responses
"""))

    # ── Domain knowledge skills (curated rule sets) ──
    domain = getattr(args, 'domain', 'general')
    compliance = getattr(args, 'compliance', ['none']) or ['none']

    if domain == "finance":
        skills.append(("finance-domain-rules", """---
description: Finance domain rules for code review and architecture decisions
---

**Not legal/financial advice — verify with your compliance team.**

**Monetary Calculations**
- Use decimal/BigDecimal types for ALL money — never floating point
- Store amounts as smallest unit (pence/cents) in integers when possible
- Currency must always travel with amount (never assume GBP/USD)
- Rounding: use banker's rounding (half-even) unless regulation specifies otherwise

**Audit Trail**
- Every financial transaction must have an immutable audit log entry
- Log: who, what, when, before-value, after-value, reason
- Audit records are append-only — never update or delete
- Retain audit logs per regulatory requirement (typically 7 years)

**Double-Entry Bookkeeping**
- Every transaction must have balanced debits and credits
- Chart of accounts must be consistent — validate account codes
- Period-end closing must prevent backdated entries

**UK-Specific (VAT / HMRC)**
- VAT calculations: apply rate to net amount, round per-line-item
- MTD (Making Tax Digital): maintain digital records, API submission capability
- FRS 102 reporting format if applicable

**Security**
- Financial data encrypted at rest and in transit
- Role-based access: segregation of duties (approver ≠ initiator)
- Payment operations require idempotency keys

Use /learn to add project-specific finance rules.
"""))

    elif domain == "healthcare":
        skills.append(("healthcare-domain-rules", """---
description: Healthcare domain rules for code review and architecture decisions
---

**Not medical or legal advice — verify with your compliance team.**

**Patient Data (PHI/PII)**
- Minimum necessary: only access/display data needed for the task
- Never log PHI in plaintext — redact or use tokens
- Display masking: show partial identifiers (***-**-1234)
- De-identification: follow Safe Harbor or Expert Determination method

**Clinical Data Integrity**
- Medication dosages: validate against safe ranges, flag outliers
- Lab results: include reference ranges and units with every value
- Date/time: always store in UTC with timezone, display in local time
- Clinical decisions: log the data that informed each decision

**Access Control**
- Role-based: clinician, nurse, admin, patient — different data views
- Break-glass access: allow emergency override with mandatory audit
- Session timeout: auto-logout after inactivity (typically 15 min)

**Interoperability**
- Use HL7 FHIR for data exchange where applicable
- ICD-10 codes for diagnoses, SNOMED CT for clinical terms
- Standardized medication codes (RxNorm/dm+d)

**Consent**
- Track patient consent per data use purpose
- Consent withdrawal must cascade to all downstream systems

Use /learn to add project-specific healthcare rules.
"""))

    elif domain == "hr":
        skills.append(("hr-domain-rules", """---
description: HR domain rules for code review and architecture decisions
---

**Not legal advice — verify with your legal/HR compliance team.**

**Employee Data**
- PII classification: name, DOB, NI/SSN, salary are highly sensitive
- Access segregation: managers see their reports only, HR sees all
- Right to access: employees can request their complete data file
- Retention: delete/anonymize data after employment ends + retention period

**Payroll**
- Salary calculations: use decimal types, never floating point
- Tax codes/brackets: must be configurable, not hardcoded
- Payslip data is confidential — encrypt at rest, access-controlled

**Recruitment**
- Anonymize candidate data for bias-free screening where required
- Right to erasure: unsuccessful candidates can request deletion
- Equal opportunities monitoring: store separately from application data

**Leave & Absence**
- Statutory entitlements vary by jurisdiction — make configurable
- Medical/sick leave reasons are sensitive — restricted access
- Accrual calculations: handle part-time pro-rata correctly

**Reporting**
- Aggregated reports only — never expose individual data in dashboards
- Gender pay gap reporting: anonymize before analysis
- Headcount/turnover metrics: define calculation methodology clearly

Use /learn to add project-specific HR rules.
"""))

    elif domain == "e-commerce":
        skills.append(("ecommerce-domain-rules", """---
description: E-commerce domain rules for code review and architecture decisions
---

**Not legal advice — verify with your compliance team.**

**Pricing & Payments**
- Store prices as integers in smallest currency unit (pence/cents)
- Tax calculations: apply per jurisdiction rules, never hardcode rates
- Display: always show currency symbol, tax-inclusive where required by law
- Payment amounts: validate server-side — never trust client-submitted totals
- Idempotency keys on all payment operations

**Inventory**
- Stock checks at cart-add AND checkout (prevent overselling)
- Concurrent purchase handling: use optimistic locking or reservations
- Backorder logic must be explicit — never silently accept unavailable items

**Order Lifecycle**
- State machine for order status: placed → paid → fulfilled → delivered
- Every state transition logged with timestamp and actor
- Cancellation/refund logic must handle partial fulfillment

**Consumer Rights**
- Cooling-off period: 14 days for online purchases (EU/UK)
- Returns: clear process, automated refund triggers
- Price display: final price including all taxes and fees shown before checkout

**Performance**
- Product catalog: paginated, cached, searchable
- Checkout flow: minimize steps, handle payment gateway timeouts gracefully
- Cart: handle session expiry and cart recovery

Use /learn to add project-specific e-commerce rules.
"""))

    elif domain == "legal":
        skills.append(("legal-domain-rules", """---
description: Legal domain rules for code review and architecture decisions
---

**Not legal advice — verify with your legal compliance team.**

**Document Management**
- Version control: every edit creates a new version, previous versions immutable
- Audit trail: who viewed/edited/shared each document, when
- Retention policies: configurable per document type, enforce automatically
- Redaction: must be irreversible — strip from all copies including metadata

**Client Confidentiality**
- Matter-based access control: users see only matters they're assigned to
- Chinese walls: prevent conflicts of interest across matters
- No cross-matter data leakage in search, reporting, or suggestions

**Data Handling**
- Privileged communications: flag and protect from disclosure
- Legal hold: freeze deletion of documents relevant to litigation
- Export: support court-mandated formats and pagination

**Time & Billing**
- Time entries: record in 6-minute increments (0.1 hour) by default
- Billing narratives: must be detailed enough for client review
- Rate cards: version-controlled, effective-dated

**Compliance**
- Know Your Client (KYC) checks for new matters
- Anti-money laundering (AML) screening where applicable
- Regulatory deadlines: track and alert on approaching deadlines

Use /learn to add project-specific legal rules.
"""))

    elif domain == "education":
        skills.append(("education-domain-rules", """---
description: Education domain rules for code review and architecture decisions
---

**Not legal advice — verify with your compliance team.**

**Student Data**
- Minors' data requires parental consent for collection
- Age-appropriate privacy: stricter rules for under-13 (COPPA) / under-16 (GDPR)
- Student records: access limited to authorized staff and the student/parent

**Assessment & Grading**
- Grade calculations: clearly defined, auditable methodology
- Moderation: support second-marking and external examiner workflows
- Results are sensitive until published — access-controlled before release date
- Academic integrity: flag potential plagiarism, maintain evidence chain

**Accessibility**
- WCAG 2.1 AA compliance minimum for all learning content
- Content must work with screen readers and keyboard-only navigation
- Provide alternatives: captions for video, alt text for images, transcripts for audio
- Adjustable time limits for timed assessments

**Safeguarding**
- Report concerns workflow: staff can flag issues confidentially
- Communication logs: retain all student-staff communications
- DBS/background check status tracking for staff

**Content Delivery**
- Offline access support where possible
- Progress tracking: save state, resume capability
- Multi-format content: handle video, PDF, interactive, SCORM

Use /learn to add project-specific education rules.
"""))

    # ── Compliance-specific rules (can apply to any domain) ──
    if "gdpr" in compliance:
        skills.append(("gdpr-rules", """---
description: GDPR compliance rules for code review and architecture decisions
---

**Reference checklist — not legal advice. Verify with your DPO/legal team.**

**Data Collection**
- Lawful basis documented for every personal data field
- Consent: explicit opt-in, no pre-ticked boxes, easy withdrawal
- Data minimization: only collect what's needed for stated purpose
- Privacy notice: clear, accessible, linked before data collection

**Data Subject Rights (implement all)**
- Right to access: export user data as JSON/CSV via API endpoint
- Right to erasure: hard-delete or anonymize on request, cascade to backups
- Right to portability: machine-readable export format
- Right to rectification: users can update their own data
- Right to restrict processing: flag to pause processing without deletion

**Technical Measures**
- Encryption at rest (AES-256) and in transit (TLS 1.2+)
- Pseudonymization where possible (separate identifiers from data)
- Data Processing Agreements with all third-party processors
- Breach notification: 72-hour reporting capability built in

**Code-Level Rules**
- Never log PII (names, emails, IPs) without redaction
- Cookie consent: required before non-essential cookies/tracking
- Analytics must respect DNT and consent preferences
- API responses must not over-expose personal data fields
- Retention: auto-delete/anonymize after defined period
- Cross-border transfers: verify adequacy decision or use SCCs

Use /learn to add project-specific GDPR rules.
"""))

    if "hipaa" in compliance:
        skills.append(("hipaa-rules", """---
description: HIPAA compliance rules for code review and architecture decisions
---

**Reference checklist — not legal advice. Verify with your compliance officer.**

**Protected Health Information (PHI)**
- Minimum necessary rule: only access/transmit PHI needed for the task
- PHI includes: name, DOB, SSN, medical record numbers, health data, photos
- De-identification: Safe Harbor (remove 18 identifiers) or Expert Determination

**Technical Safeguards**
- Encryption: AES-256 at rest, TLS 1.2+ in transit — no exceptions
- Access control: unique user IDs, role-based, automatic logoff
- Audit controls: log all PHI access — who, what, when, from where
- Integrity controls: detect unauthorized PHI alteration

**Administrative Safeguards**
- Business Associate Agreements (BAAs) with all vendors handling PHI
- Workforce training records: track who completed HIPAA training
- Incident response: document and report breaches within 60 days
- Risk assessments: periodic, documented, with remediation tracking

**Code-Level Rules**
- Never log PHI in plaintext — use tokenization or redaction
- Error messages must not expose PHI
- Test data: never use real PHI — use synthetic data generators
- API responses: include only minimum necessary PHI fields
- Session management: auto-timeout after 15 min inactivity
- Backup encryption: same standard as primary storage

Use /learn to add project-specific HIPAA rules.
"""))

    if "sox" in compliance:
        skills.append(("sox-rules", """---
description: SOX compliance rules for code review and architecture decisions
---

**Reference checklist — not legal advice. Verify with your compliance team.**

**Internal Controls (Section 404)**
- Segregation of duties: no single user can initiate, approve, AND record transactions
- Access reviews: quarterly review of who has access to financial systems
- Change management: all code changes to financial calculations require approval
- Audit trail: immutable log of all financial data modifications

**Financial Data Integrity**
- Calculations must be deterministic and reproducible
- Rounding methodology documented and consistent
- Period-end controls: prevent backdating across closed periods
- Reconciliation: automated checks between systems

**IT General Controls**
- Access management: provisioning, de-provisioning, periodic review
- Change management: documented, tested, approved deployments
- Backup and recovery: tested restoration procedures
- Logical security: password policies, MFA for financial systems

**Code-Level Rules**
- Financial calculations: use decimal types, document methodology
- All database changes to financial tables must go through audited functions
- Soft-delete only for financial records — never hard-delete
- Configuration changes (tax rates, exchange rates) must be version-controlled
- Batch jobs: log start, end, record count, error count
- API inputs affecting financial data: validate and log server-side

Use /learn to add project-specific SOX rules.
"""))

    if "pci-dss" in compliance:
        skills.append(("pci-dss-rules", """---
description: PCI-DSS compliance rules for code review and architecture decisions
---

**Reference checklist — not legal advice. Verify with your QSA/compliance team.**

**Cardholder Data**
- Never store full card number after authorization — use tokenization
- Never store CVV/CVC under any circumstances
- Mask PAN when displayed: show only first 6 / last 4 digits
- Encrypt stored cardholder data with AES-256, manage keys securely

**Network Security**
- Segment cardholder data environment (CDE) from other systems
- Firewall rules: deny-by-default, document all allowed connections
- No direct public access to systems storing cardholder data

**Access Control**
- Unique IDs for all users — no shared accounts
- MFA for all administrative access to CDE
- Role-based access: least privilege principle
- Revoke access immediately on termination

**Code-Level Rules**
- Never log full card numbers — truncate or tokenize before logging
- Use payment gateway SDKs — never handle raw card data server-side
- Input validation: reject malformed card data at entry point
- Error messages: never expose card data or internal system details
- Client-side: use hosted payment fields (Stripe Elements, etc.) not raw inputs
- CSP headers: restrict script sources on payment pages
- Dependencies: no known vulnerabilities in payment-related packages

**Testing**
- Penetration test the payment flow quarterly
- Vulnerability scans: automated, address critical/high within 30 days

Use /learn to add project-specific PCI-DSS rules.
"""))

    return skills


# ── MCP Servers ─────────────────────────────────────────────────────────

def get_mcp_servers(args):
    """Return MCP server configurations based on interview answers."""
    servers = {}

    git = args.git_platform or "none"

    # GitHub MCP — most common, high value
    if git == "github":
        servers["github"] = {
            "command": "npx",
            "args": ["-y", MCP_VERSIONS["server-github"]],
            "env": {"GITHUB_PERSONAL_ACCESS_TOKEN": "${GITHUB_TOKEN}"}
        }

    # GitLab MCP
    if git == "gitlab":
        servers["gitlab"] = {
            "command": "npx",
            "args": ["-y", MCP_VERSIONS["server-gitlab"]],
            "env": {
                "GITLAB_PERSONAL_ACCESS_TOKEN": "${GITLAB_TOKEN}",
                "GITLAB_API_URL": "https://gitlab.com/api/v4"
            }
        }

    # Database MCP servers
    db = args.database or "none"
    if db in ("postgresql", "sqlite"):
        pkg = MCP_VERSIONS["server-postgres"] if db == "postgresql" else MCP_VERSIONS["server-sqlite"]
        servers["database"] = {
            "command": "npx",
            "args": ["-y", pkg],
            "env": {"DATABASE_URL": "${DATABASE_URL}"} if db != "sqlite" else {}
        }
    # Note: MySQL MCP not included — no verified official package yet

    # Filesystem MCP — useful for docs-heavy projects
    # Only add if docs/ or specs/ directories actually exist (checked at generation time)
    if args.team:
        output_dir = Path(args.output_dir).resolve()
        project_dir = output_dir / args.project_name if args.create_root else output_dir
        fs_paths = []
        for d in ["docs", "specs", "design"]:
            if (project_dir / d).exists():
                fs_paths.append(f"./{d}")
        if not fs_paths:
            fs_paths = ["./docs"]  # Default — will be created by scaffold
        servers["filesystem"] = {
            "command": "npx",
            "args": ["-y", MCP_VERSIONS["server-filesystem"]] + fs_paths
        }

    # Sentry MCP — if user specified sentry in their monitoring
    if getattr(args, 'sentry', False):
        servers["sentry"] = {
            "command": "npx",
            "args": ["-y", MCP_VERSIONS["server-sentry"]],
            "env": {"SENTRY_AUTH_TOKEN": "${SENTRY_AUTH_TOKEN}"}
        }

    # Community MCP servers (skip in minimal mode)
    minimal_mcp = getattr(args, 'minimal_mcp', False)
    if not minimal_mcp:
        # Context7 — docs lookup for any stack (high value, low cost)
        if getattr(args, 'context7', False):
            servers["context7"] = {
                "command": "npx",
                "args": ["-y", MCP_VERSIONS["context7"]]
            }

        # Sequential Thinking — for complex architectural decisions
        if getattr(args, 'sequential_thinking', False):
            servers["sequential-thinking"] = {
                "command": "npx",
                "args": ["-y", MCP_VERSIONS["sequential-thinking"]]
            }

    return servers


# ── Hooks ───────────────────────────────────────────────────────────────

def get_hooks(args):
    """Return hooks configuration based on interview answers."""
    hooks = {}

    # PreToolUse hooks
    pre_hooks = []

    # All projects: block force-push to main
    # Hook reads JSON from stdin: { "tool_input": { "command": "..." }, ... }
    # jq guard: if jq is not installed, hook silently passes (safety degrades gracefully)
    JQ_GUARD = "command -v jq >/dev/null 2>&1 || { cat >/dev/null; exit 0; }; "
    pre_hooks.append({
        "matcher": "Bash",
        "hooks": [{
            "type": "command",
            "command": JQ_GUARD + "INPUT=$(cat); CMD=$(echo \"$INPUT\" | jq -r '.tool_input.command // empty'); if echo \"$CMD\" | grep -qE 'git push.*(--force|-f).*(main|master)'; then echo 'BLOCKED: Force push to main/master is not allowed' >&2; exit 2; fi"
        }]
    })

    # All projects: block committing secrets via git
    # Scoped to Bash + git add/commit to avoid false positives in source code edits
    pre_hooks.append({
        "matcher": "Bash",
        "hooks": [{
            "type": "command",
            "command": JQ_GUARD + "INPUT=$(cat); CMD=$(echo \"$INPUT\" | jq -r '.tool_input.command // empty'); if echo \"$CMD\" | grep -qE 'git (add|commit)' && echo \"$CMD\" | grep -qE '(sk-[a-zA-Z0-9]{20,}|ghp_[a-zA-Z0-9]{36}|AKIA[0-9A-Z]{16})'; then echo 'BLOCKED: Secrets detected in git command' >&2; exit 2; fi"
        }]
    })

    # Conventional commits: validate commit message format
    # Only blocks `git commit -m` with non-conventional prefix; allows --amend, -F, editor mode
    if args.conventional_commits:
        pre_hooks.append({
            "matcher": "Bash",
            "hooks": [{
                "type": "command",
                "command": JQ_GUARD + "INPUT=$(cat); CMD=$(echo \"$INPUT\" | jq -r '.tool_input.command // empty'); if echo \"$CMD\" | grep -qE 'git commit -m ' && ! echo \"$CMD\" | grep -qE 'git commit -m .*(feat|fix|refactor|test|docs|chore|ci|style|perf|build|revert)[(:]'; then echo 'BLOCKED: Commit message must use conventional format (feat|fix|refactor|...)' >&2; exit 2; fi"
            }]
        })

    if pre_hooks:
        hooks["PreToolUse"] = pre_hooks

    # PostToolUse hooks
    post_hooks = []

    # Auto-lint on source file edits (skip config/docs via jq + file extension check)
    # Claude Code pipes JSON to stdin: { "tool_input": { "file_path": "..." }, ... }
    # Falls back to running on all files if jq is not installed
    # Guards ensure hooks silently pass when deps aren't installed yet (greenfield projects)
    SKIP_FILTER = (
        'if command -v jq >/dev/null 2>&1; then '
        'F=$(cat | jq -r \'.tool_input.file_path // empty\'); '
        'case "$F" in *.md|*.json|*.yaml|*.yml|*.txt|*.env*|*.lock|*ignore) exit 0 ;; esac; '
        'else cat >/dev/null; fi; '
    )

    def _deps_guard(cmd):
        """Return a shell guard that exits 0 if deps aren't installed yet."""
        if cmd.startswith(('npm ', 'pnpm ', 'yarn ')):
            return '[ -d node_modules ] || exit 0; '
        if cmd.startswith('make '):
            return '[ -f Makefile ] || exit 0; '
        # For direct tool commands (ruff, pytest, mypy, go, cargo), check if available
        tool = cmd.split()[0]
        return f'command -v {tool} >/dev/null 2>&1 || exit 0; '

    lint_cmd = getattr(args, 'lint_cmd', None)
    if lint_cmd and SAFE_CMD_PATTERN.match(lint_cmd):
        post_hooks.append({
            "matcher": "Write|Edit",
            "hooks": [{
                "type": "command",
                "command": f"{SKIP_FILTER}{_deps_guard(lint_cmd)}{lint_cmd}"
            }]
        })
    elif lint_cmd:
        print(f"  ⚠ Skipping --lint-cmd: '{lint_cmd}' doesn't match allowed patterns.", file=sys.stderr)
        print(f"    Allowed: npm/pnpm/yarn run <script>, pytest, ruff, mypy, go test, cargo test, make <target>", file=sys.stderr)

    # Auto-test on source file edits (TDD mode, skip non-source files)
    test_cmd = getattr(args, 'test_cmd', None)
    if args.tdd and test_cmd and SAFE_CMD_PATTERN.match(test_cmd):
        post_hooks.append({
            "matcher": "Write|Edit",
            "hooks": [{
                "type": "command",
                "command": f"{SKIP_FILTER}{_deps_guard(test_cmd)}{test_cmd}"
            }]
        })
    elif args.tdd and test_cmd:
        print(f"  ⚠ Skipping --test-cmd: '{test_cmd}' doesn't match allowed patterns.", file=sys.stderr)

    if post_hooks:
        hooks["PostToolUse"] = post_hooks

    # Stop hook: remind to update handoff (only if handoff.md hasn't been updated recently)
    hooks["Stop"] = [{
        "matcher": "",
        "hooks": [{
            "type": "command",
            "command": "if [ -f .claude/handoff.md ] && [ $(find .claude/handoff.md -mmin +30 2>/dev/null | wc -l) -gt 0 ]; then echo '💡 Handoff is >30min old — consider running /handoff'; fi"
        }]
    }]

    return hooks


# ── Agents ───────────────────────────────────────────────────────────────

def get_agents(args):
    """Return list of (name, content) tuples for agent files based on interview answers."""
    agents = []
    fe = args.frontend
    be = args.backend
    db = args.database
    test_cmd = getattr(args, 'test_cmd', None) or "npm run test"
    lint_cmd = getattr(args, 'lint_cmd', None) or "npm run lint"
    build_cmd = getattr(args, 'build_cmd', None) or "npm run build"

    # architect — always
    agents.append(("architect", f"""---
name: architect
description: Designs technical solutions from feature requests
isolation: worktree
tools: [Read, Glob, Grep, Bash, Write]
model: opus
---

You are the principal architect for a {fe}/{be} project.
1. Read CLAUDE.md, ARCHITECTURE.md, and .claude/rules/ for current patterns
2. Assess which system parts this touches
3. Design: data model changes, API contract, components affected
4. Write blueprint to docs/blueprints/{{feature}}.md
5. Present trade-offs for non-obvious decisions

Blueprint format: Summary, Data Model Changes, API Changes, Components, Security, Test Plan, Risks.

Rules:
- Prefer extending existing patterns over new ones
- Keep solutions simple — complexity must be justified
- Do NOT write code — produce blueprints only
- STOP if the feature contradicts ARCHITECTURE.md — flag the conflict
"""))

    # testing — always
    agents.append(("testing", f"""---
name: testing
description: Creates comprehensive test suites
isolation: worktree
tools: [Bash, Read, Write, Edit, Grep, Glob]
model: sonnet
---

You are a test engineer for a {fe}/{be}/{db} stack.
Test command: `{test_cmd}`

1. Read the blueprint in docs/blueprints/ — do NOT read implementation first
2. Design: happy path, edge cases, error conditions, security
3. Write: unit (mock externals), integration (real DB), E2E (user flows)
4. Run `{test_cmd}` and verify tests pass

Rules:
- NEVER read implementation before writing tests — use the blueprint as spec
- Test behavior, not internals
- Each test independent — no shared mutable state
- STOP if tests require >5 external service mocks — simplify the design
"""))

    # reviewer — always
    agents.append(("reviewer", f"""---
name: reviewer
description: Reviews code for correctness, performance, and maintainability
tools: [Read, Glob, Grep, Bash]
model: sonnet
---

You review {fe}/{be} code. Lint: `{lint_cmd}`, Test: `{test_cmd}`

Check:
1. Correctness: Works? Edge cases? Error handling?
2. Architecture: Fits patterns? Scope right? Simpler alternative?
3. Performance: N+1 queries? Expensive loops? Pagination?
4. Tests: Exist? Cover error paths?

Output: APPROVE or REQUEST_CHANGES with Must Fix / Should Fix / Nice to Have.

Rules:
- Read the FULL diff before starting
- Explain WHY, suggest the fix
- STOP and escalate if you find a security vulnerability
"""))

    # debugger — always
    agents.append(("debugger", f"""---
name: debugger
description: Systematically diagnoses and fixes bugs
tools: [Bash, Read, Write, Edit, Grep, Glob]
model: sonnet
---

Debug methodology for {fe}/{be}/{db} stack:
1. Reproduce: trigger the bug
2. Isolate: trace data flow, find the break boundary
3. Diagnose: root cause (don't guess)
4. Fix: minimal fix for root cause
5. Verify: regression test + `{test_cmd}`

Rules:
- NEVER guess at fixes without understanding root cause
- ALWAYS reproduce before fixing
- ALWAYS write a regression test
- STOP if you can't find root cause after investigation — document and escalate
"""))

    # push — always
    cc_rule = "Conventional format: type(scope): description" if args.conventional_commits else "Clear, descriptive messages"
    agents.append(("push", f"""---
name: push
description: Manages git workflow — branches, commits, and PRs
tools: [Bash, Read, Grep, Glob]
model: sonnet
---

Git lifecycle for this project:
1. Branch: feature/{{desc}}, fix/{{desc}}, chore/{{desc}}
2. Stage: review `git diff` first. Stage specific files.
3. Commit: {cc_rule}
4. Push: `git push -u origin {{branch}}`
5. PR: `gh pr create` with summary, changes, test checklist

Rules:
- NEVER force push to main/master
- NEVER push directly to main — use PRs
- NEVER commit secrets or .env files
- STOP if PR >500 lines — suggest splitting
"""))

    # security — when auth/payments/user-data
    auth = getattr(args, 'auth', 'none') or 'none'
    if auth != "none" or args.ai:
        agents.append(("security", f"""---
name: security
description: Reviews code and architecture for vulnerabilities
tools: [Read, Glob, Grep, Bash]
model: sonnet
---

Security review for {fe}/{be} with auth={auth}:
1. Auth: All endpoints protected? Token handling sound?
2. Data: PII handled? API responses not over-exposing?
3. Input: All user input validated? XSS protection?
4. Infra: No hardcoded secrets? CORS restrictive? Rate limits?
5. Deps: Run audit command, check for known vulnerabilities

Output: CRITICAL/HIGH/MEDIUM/LOW with location, risk, fix.

Rules:
- NEVER approve code with hardcoded secrets
- ALWAYS verify auth middleware is applied
- STOP on any CRITICAL finding — block the PR
"""))

    # reliability-auditor — when event systems detected
    event_systems = getattr(args, 'event_systems', []) or []
    if event_systems:
        systems_str = ", ".join(event_systems)
        event_checks = []
        if "kafka" in event_systems:
            event_checks.append("Kafka: acks=all? Consumer group IDs meaningful? DLTs configured? Schema Registry backward-compat?")
        if "bullmq" in event_systems:
            event_checks.append("BullMQ: workers in separate processes? Concurrency limited? Stalled job handling?")
        if "rabbitmq" in event_systems:
            event_checks.append("RabbitMQ: prefetch configured? Queues durable? Messages persistent? DLX on every queue?")
        if "celery" in event_systems:
            event_checks.append("Celery: task_acks_late? JSON serializer? Time limits set? No ORM objects as args?")
        if "temporal" in event_systems:
            event_checks.append("Temporal: workflow code deterministic? No I/O in workflows? Activities handle all side effects?")
        if "redis-streams" in event_systems:
            event_checks.append("Redis Streams: MAXLEN/MINID trimming configured? XACK after processing? XAUTOCLAIM for stale messages?")
        checks_str = "\n".join(f"   - {c}" for c in event_checks) if event_checks else "   - Technology-specific best practices"

        agents.append(("reliability-auditor", f"""---
name: reliability-auditor
description: Reviews event-driven code for reliability, idempotency, and failure handling
tools: [Read, Glob, Grep, Bash]
model: sonnet
---

Reliability review for event-driven system ({systems_str}):
1. Idempotency: every consumer/worker handles duplicate messages?
2. DLQ: failed messages routed to dead letter queue, never silently dropped?
3. Retry: exponential backoff with max attempts? Poison messages handled?
4. Schema: events validated before publish? Backward-compatible changes?
5. Technology-specific:
{checks_str}

Output: RELIABLE / NEEDS-WORK per consumer with specific fix.

Rules:
- NEVER approve consumers without idempotency checks
- NEVER approve queues without dead letter configuration
- STOP if messages can be silently lost — this is a data loss risk
"""))

    # idea-to-prd — always
    agents.append(("idea-to-prd", f"""---
name: idea-to-prd
description: Researches an idea and generates a detailed PRD
tools: [Read, Glob, Grep, Bash, Write, WebSearch, WebFetch]
model: opus
---

You are a product strategist for a {fe}/{be} project.

1. Take the idea and clarify scope — ask 2-3 questions if ambiguous
2. Research online: competitor features, best practices, common pitfalls
3. Identify must-have vs nice-to-have requirements
4. Write PRD to docs/prds/{{feature-name}}.md

PRD format:
- **Problem Statement**: What problem does this solve? Who has it?
- **Target Users**: Who benefits? What's their current workflow?
- **Competitive Analysis**: How do leading products handle this? (cite sources)
- **Requirements**: Must-have (MVP) and Nice-to-have (v2) — each with acceptance criteria
- **User Stories**: As a [user], I want [action], so that [outcome]
- **Technical Constraints**: What the architecture supports/limits (read ARCHITECTURE.md)
- **Success Metrics**: How do we know this worked?
- **Open Questions**: Decisions that need human input

Rules:
- ALWAYS research before writing — don't generate requirements from assumptions
- Include specific acceptance criteria for every requirement (testable, not vague)
- Read ARCHITECTURE.md and CLAUDE.md to understand technical constraints
- Do NOT design the solution — that's the architect's job
- STOP if the idea conflicts with the project's core architecture — flag it
"""))

    # pre-push — always
    agents.append(("pre-push", f"""---
name: pre-push
description: Comprehensive pre-flight check before pushing code
tools: [Bash, Read, Grep, Glob]
model: sonnet
---

Run the full pre-push checklist for {fe}/{be} stack:

1. **Lint**: `{lint_cmd}` — must pass clean
2. **Type check**: Run type checker if available (tsc --noEmit, mypy, etc.)
3. **Tests**: `{test_cmd}` — all must pass
4. **Build**: `{build_cmd}` — must compile without errors
5. **Debug code**: Scan for console.log, debugger, print(), TODO, FIXME, XXX, @hack
6. **Secrets scan**: Check staged files for API keys, tokens, passwords, connection strings
7. **Large files**: Flag any staged file >500KB
8. **Git status**: No untracked files that should be committed, no merge conflicts
9. **Dependencies**: No mismatched lock file (package-lock.json matches package.json)

Output: READY / NOT READY with a checklist showing pass/fail per item.

Rules:
- Run ALL checks even if early ones fail — report everything at once
- NEVER skip the secrets scan
- Flag warnings (TODOs, large files) but only block on errors (lint, test, build, secrets)
- STOP and report — do NOT fix issues, just identify them
"""))

    # dev-ops — always
    hosting = getattr(args, 'hosting', 'none') or 'none'
    agents.append(("dev-ops", f"""---
name: dev-ops
description: Recommends infrastructure and generates starter deployment configs
tools: [Read, Glob, Grep, Bash, Write, WebSearch, WebFetch]
model: opus
---

You are a DevOps engineer advising a {fe}/{be}/{db} project (hosting: {hosting}).

1. Read ARCHITECTURE.md, CLAUDE.md, and package files to understand the stack
2. Analyze requirements: expected traffic, data sensitivity, team size, budget constraints
3. Propose infrastructure for three environments:
   - **Local**: Docker Compose for dev environment (app + database + any services)
   - **Staging** (if needed): lightweight, cost-optimized, mirrors production topology
   - **Production**: right-sized for the stack, with monitoring and backups
4. Write recommendation to `docs/infrastructure.md`
5. Generate starter IaC files in `infrastructure/`:
   - `docker-compose.yml` — local dev environment
   - `docker-compose.staging.yml` — staging (if applicable)
   - Terraform files for production (if cloud hosting)

For each environment, document:
- **Services**: what runs where
- **Estimated cost**: monthly range (e.g., "$0/free tier", "$20-50/mo", "$200-500/mo")
- **Scaling path**: what to change when traffic grows
- **Trade-offs**: why this choice over alternatives

Rules:
- ALWAYS start with the simplest viable infrastructure — don't over-engineer
- Include cost estimates — engineers need to justify spend
- Docker Compose for local is non-negotiable — every project needs reproducible dev setup
- Terraform for production cloud infra (not CloudFormation — Terraform is cloud-agnostic)
- Generated IaC is a STARTING POINT — flag what needs customization before production use
- Include health checks, logging, and backup configuration
- STOP if requirements are unclear — ask before generating expensive infrastructure
"""))

    # ── Domain auditor agents ──
    domain = getattr(args, 'domain', 'general')
    compliance = getattr(args, 'compliance', ['none']) or ['none']
    has_compliance = compliance != ['none'] and 'none' not in compliance

    # compliance-auditor — when domain is set or compliance requirements exist
    if domain != "general" or has_compliance:
        compliance_list = ", ".join(c.upper() for c in compliance if c != "none") if has_compliance else "domain best practices"
        domain_skills = []
        if domain != "general":
            domain_skills.append(f"{domain}-domain-rules")
        for c in compliance:
            if c != "none":
                domain_skills.append(f"{c}-rules")
        skills_ref = ", ".join(domain_skills) if domain_skills else "domain rules"

        agents.append(("compliance-auditor", f"""---
name: compliance-auditor
description: Reviews code against {domain} domain rules and {compliance_list} requirements
tools: [Read, Glob, Grep]
model: sonnet
---

Domain compliance review for {domain} project ({compliance_list}):
1. Read the domain knowledge skills: {skills_ref}
2. Scan the code changes against each applicable rule
3. Check data handling, access control, and audit trail requirements
4. Verify technical measures match regulatory requirements

Output format per finding:
- COMPLIANT / NON-COMPLIANT / NEEDS-REVIEW
- File and line reference
- Rule citation (which specific requirement)
- Recommended fix

Rules:
- ALWAYS read the domain knowledge skills before reviewing
- NEVER approve code that violates data handling requirements
- STOP on any non-compliant finding that affects user data or financial integrity
"""))

    # frontend-auditor — when frontend exists and domain is not general
    if fe != "none" and domain != "general":
        fe_domain_checks = {
            "finance": "decimal precision display, currency formatting, audit trail UI, number input validation",
            "healthcare": "PHI display masking, consent flows, WCAG AA accessibility, clinical data formatting",
            "hr": "PII masking in employee views, role-based UI visibility, sensitive field access control",
            "e-commerce": "price display with tax, card input security (hosted fields), cookie consent, checkout flow",
            "legal": "document version indicators, redaction UI, privileged content warnings, matter-based navigation",
            "education": "WCAG AA accessibility, age-appropriate content, progress save/resume, offline support indicators",
        }
        checks = fe_domain_checks.get(domain, "domain-appropriate UI patterns")

        agents.append(("frontend-auditor", f"""---
name: frontend-auditor
description: Reviews frontend code for {domain}-specific UI/UX requirements
tools: [Read, Glob, Grep]
model: sonnet
---

Frontend review for {domain} {fe} project:
1. Scan UI components for domain-specific requirements
2. Check: {checks}
3. Verify accessibility standards (WCAG 2.1 AA minimum)
4. Check error states show safe, user-appropriate messages (no data leaks)

Output: PASS / FAIL per component with specific fix.

Rules:
- NEVER approve UI that exposes sensitive data without masking
- ALWAYS verify form validation matches backend validation
- STOP if accessibility violations found — fix before shipping
"""))

    # architecture-auditor — for regulated domains with strict data requirements
    if domain in ("finance", "healthcare", "legal"):
        arch_checks = {
            "finance": "audit trail completeness, segregation of duties, immutable financial records, backup/retention",
            "healthcare": "PHI isolation, consent management architecture, break-glass access, data de-identification pipeline",
            "legal": "matter-based data isolation, legal hold mechanism, privilege tagging, document retention enforcement",
        }
        checks = arch_checks.get(domain, "data architecture compliance")

        agents.append(("architecture-auditor", f"""---
name: architecture-auditor
description: Reviews architecture for {domain} data handling and regulatory compliance
tools: [Read, Glob, Grep, Bash]
model: sonnet
---

Architecture review for {domain} system:
1. Verify data flow: where is sensitive data stored, processed, transmitted?
2. Check: {checks}
3. Review encryption: at rest (AES-256), in transit (TLS 1.2+)
4. Verify access control model matches regulatory requirements
5. Check third-party integrations have appropriate agreements

Output: architecture decision + compliant/non-compliant + risk level.

Rules:
- NEVER approve architecture that lacks audit trail for sensitive operations
- ALWAYS verify encryption meets regulatory minimums
- STOP if data residency or isolation requirements are violated
"""))

    return agents


# ── Rules ────────────────────────────────────────────────────────────────

def get_rules(args):
    """Return list of (name, content) tuples for path-scoped rule files."""
    rules = []
    fe = args.frontend
    be = args.backend
    db = args.database
    orm = getattr(args, 'orm', 'none') or 'none'

    # Frontend rules
    if fe == "nextjs":
        rules.append(("frontend", """---
globs: ["src/app/**/*.ts", "src/app/**/*.tsx", "src/components/**/*.tsx"]
description: Next.js App Router conventions
---

- Server Components by default. Only add "use client" when needed (hooks, browser APIs, interactivity).
- Server Actions for mutations — must start with "use server", validate input with zod.
- Every route group needs loading.tsx + error.tsx + not-found.tsx.
- Use next/image for images, next/link for navigation.
- No secrets without NEXT_PUBLIC_ prefix in client code.
"""))
    elif fe == "react-vite":
        rules.append(("frontend", """---
globs: ["src/components/**/*.tsx", "src/pages/**/*.tsx", "src/hooks/**/*.ts"]
description: React + Vite conventions
---

- Feature-based component organization.
- React Query for server state, Zustand for app state only.
- API calls through src/lib/api.ts — never directly in components.
- Lazy-load route components.
- Handle loading/error states for all async operations.
"""))
    elif fe == "vue":
        rules.append(("frontend", """---
globs: ["app/components/**/*.vue", "app/pages/**/*.vue", "app/composables/**/*.ts"]
description: Vue 3 / Nuxt 3 conventions
---

- Composition API with <script setup> exclusively. No Options API.
- Composables prefixed with `use`. Pinia for global state.
- useFetch/useAsyncData for data fetching.
- Never mutate props directly. Use ref() for primitives.
"""))
    elif fe == "sveltekit":
        rules.append(("frontend", """---
globs: ["src/routes/**/*.svelte", "src/routes/**/*.ts", "src/lib/**/*.ts"]
description: SvelteKit conventions
---

- +page.server.ts for server data loading. Form actions for mutations.
- $lib alias for imports. Svelte 5 runes ($state, $derived, $effect).
- Never import $lib/server in client code.
- Always add +error.svelte for route error handling.
"""))

    # Backend rules
    if be == "node-express" or be == "node-fastify":
        framework = "Express" if be == "node-express" else "Fastify"
        rules.append(("backend", f"""---
globs: ["src/routes/**/*.ts", "src/controllers/**/*.ts", "src/services/**/*.ts"]
description: {framework} API conventions
---

- Controller → Service → Model pattern. No business logic in controllers.
- Validate ALL input via zod middleware.
- Centralized error handler — never catch in routes.
- Structured logging (pino). No console.log.
- Environment validated at startup.
"""))
    elif be == "python-fastapi":
        rules.append(("backend", """---
globs: ["app/api/**/*.py", "app/services/**/*.py", "app/models/**/*.py"]
description: FastAPI conventions
---

- Async everywhere. Pydantic for all schemas.
- Depends() for dependency injection.
- Separate models (DB) from schemas (API).
- Type hints on everything. Never return ORM models directly.
- No sync DB operations. No print() — use logging.
"""))
    elif be == "python-django":
        rules.append(("backend", """---
globs: ["**/views.py", "**/models.py", "**/serializers.py", "**/urls.py"]
description: Django conventions
---

- Views → Serializers → Models. Thin views.
- DRF serializers for validation and response shaping.
- select_related/prefetch_related to avoid N+1.
- Custom managers for complex queries.
- Never modify applied migrations.
"""))
    elif be == "go":
        rules.append(("backend", """---
globs: ["internal/**/*.go", "cmd/**/*.go", "pkg/**/*.go"]
description: Go conventions
---

- Handler → Service → Repository. Interfaces defined by consumer.
- Context propagation everywhere. Errors wrapped with %w.
- Never ignore errors. Never use global state.
- Table-driven tests. Always defer close resources.
"""))
    elif be == "rust-actix":
        rules.append(("backend", """---
globs: ["src/**/*.rs"]
description: Rust / Actix-web conventions
---

- Handler → Service → Repository. Result<T, AppError> everywhere.
- Never .unwrap() in production code. Propagate errors with ?.
- Derive macros for serialization (serde). Sqlx for async DB.
- Always #[derive(Debug)] on custom types.
"""))
    elif be == "ruby-rails":
        rules.append(("backend", """---
globs: ["app/controllers/**/*.rb", "app/models/**/*.rb", "app/services/**/*.rb"]
description: Rails conventions
---

- MVC + service objects for business logic. Thin controllers.
- Strong params for input. ActiveRecord validations.
- RESTful routes. includes() to avoid N+1.
- Never modify applied migrations. Index all foreign keys.
"""))

    # Database rules
    if db != "none" and orm != "none":
        if orm == "prisma":
            rules.append(("database", """---
globs: ["prisma/**/*.prisma", "src/db/**/*.ts"]
description: Prisma ORM conventions
---

- PascalCase models, camelCase fields. @map/@@map for snake_case DB.
- Always include createdAt/updatedAt. @@index for common queries.
- Never edit applied migrations. Run prisma generate after schema changes.
- Create migrations (not db push) for production.
"""))
        elif orm == "drizzle":
            rules.append(("database", """---
globs: ["src/db/**/*.ts", "drizzle.config.ts"]
description: Drizzle ORM conventions
---

- Schema defined in src/db/schema.ts. Migrations via drizzle-kit.
- Use drizzle-kit generate for migrations, never manual edits.
- Type-safe queries with the query builder.
"""))
        elif orm == "sqlalchemy":
            rules.append(("database", """---
globs: ["app/db/**/*.py", "app/models/**/*.py"]
description: SQLAlchemy / Alembic conventions
---

- Async sessions. Alembic for migrations.
- Never modify applied migrations. Autogenerate revisions.
- Separate models from schemas. Use relationship() for joins.
"""))

    # Event system rules
    event_systems = getattr(args, 'event_systems', []) or []
    event_patterns = getattr(args, 'event_patterns', []) or []
    schema_format = getattr(args, 'schema_format', 'none') or 'none'
    workflow_orch = getattr(args, 'workflow_orchestration', 'none') or 'none'

    if event_systems:
        # Determine target globs based on backend
        if be in ("python-fastapi", "python-django"):
            event_globs = '["**/consumers/**/*.py", "**/producers/**/*.py", "**/workers/**/*.py", "**/tasks/**/*.py", "**/handlers/**/*.py"]'
        elif be == "go":
            event_globs = '["**/consumers/**/*.go", "**/producers/**/*.go", "**/handlers/**/*.go", "**/workers/**/*.go"]'
        elif be in ("rust-actix",):
            event_globs = '["**/consumers/**/*.rs", "**/producers/**/*.rs", "**/handlers/**/*.rs", "**/workers/**/*.rs"]'
        elif be in ("node-express", "node-fastify") or fe in ("nextjs", "sveltekit"):
            event_globs = '["**/consumers/**/*.ts", "**/producers/**/*.ts", "**/workers/**/*.ts", "**/handlers/**/*.ts", "**/jobs/**/*.ts", "**/queues/**/*.ts"]'
        else:
            event_globs = '["**/consumers/**", "**/producers/**", "**/workers/**", "**/handlers/**"]'

        systems_str = ", ".join(event_systems)
        lines = [f"- Event systems: {systems_str}"]
        lines.append("- ALL consumers/workers MUST be idempotent — at-least-once delivery is the norm")
        lines.append("- Configure dead letter queues on every consumer — never silently drop messages")
        lines.append("- Keep event payloads small — store data externally, pass references/IDs")
        lines.append("- Retry with exponential backoff and max attempts before DLQ")

        if "kafka" in event_systems:
            lines.append("- Kafka: use acks=all, disable auto topic creation in production, meaningful consumer group IDs")
        if "bullmq" in event_systems:
            lines.append("- BullMQ: run workers in separate processes from API, set concurrency limits")
        if "rabbitmq" in event_systems:
            lines.append("- RabbitMQ: one TCP connection per process, configure prefetch, durable queues + persistent messages")
        if "celery" in event_systems:
            lines.append("- Celery: task_acks_late=True, never pass ORM objects as arguments, use JSON serializer (not pickle)")
        if "nats" in event_systems:
            lines.append("- NATS: distinguish Core (at-most-once) from JetStream (at-least-once), subject hierarchies mirror domain")
        if "redis-streams" in event_systems:
            lines.append("- Redis Streams: configure MAXLEN/MINID trimming, XACK processed messages, use XAUTOCLAIM for stale recovery")

        if schema_format != "none":
            lines.append(f"- Schema format: {schema_format} — enforce backward compatibility, test in CI")

        rules.append(("event-consumers", f"""---
globs: {event_globs}
description: Event-driven system conventions ({systems_str})
---

{chr(10).join(lines)}
"""))

    if workflow_orch == "temporal":
        if be in ("python-fastapi", "python-django"):
            temporal_globs = '["**/workflows/**/*.py", "**/activities/**/*.py"]'
        elif be == "go":
            temporal_globs = '["**/workflows/**/*.go", "**/activities/**/*.go"]'
        elif be in ("node-express", "node-fastify") or fe in ("nextjs", "sveltekit"):
            temporal_globs = '["**/workflows/**/*.ts", "**/activities/**/*.ts"]'
        else:
            temporal_globs = '["**/workflows/**", "**/activities/**"]'

        rules.append(("temporal", f"""---
globs: {temporal_globs}
description: Temporal workflow conventions
---

- Workflow code MUST be deterministic — NO I/O, Date.now(), Math.random(), network calls, file access, DB queries
- ALL side effects go in activities — workflows only orchestrate
- One file per workflow, one file per activity group
- Use workflow versioning when changing existing workflow code (prevents non-determinism on replay)
- Use continue-as-new for long-running workflows (prevents unbounded history)
- Never set maximum retry limits on activities — use appropriate timeouts instead
"""))

    if event_patterns:
        pattern_lines = []
        if "event-sourcing" in event_patterns:
            pattern_lines.append("- Event Sourcing: events are immutable once written, use snapshots for long histories, schema versioning required")
        if "cqrs" in event_patterns:
            pattern_lines.append("- CQRS: separate write model (commands) from read model (queries), projections must be idempotent and rebuildable")
        if "saga" in event_patterns:
            pattern_lines.append("- Saga: every step MUST have a compensating transaction, compensations must be idempotent")
        if "outbox" in event_patterns:
            pattern_lines.append("- Outbox: write to outbox in SAME database transaction as state change, separate publisher reads outbox")

        if pattern_lines:
            rules.append(("event-patterns", f"""---
globs: ["**/events/**", "**/sagas/**", "**/projections/**", "**/commands/**", "**/queries/**"]
description: Event-driven architectural patterns
---

{chr(10).join(pattern_lines)}
"""))

    # Monorepo rule
    if getattr(args, 'monorepo', False) or getattr(args, '_monorepo_info', None):
        rules.append(("monorepo", """---
globs: ["**/package.json", "turbo.json", "nx.json"]
description: Monorepo conventions
---

- Changes in shared packages (packages/*) affect all consumers — run full test suite
- Each package has its own tsconfig/eslint — respect package-level config
- Import from packages using workspace protocol, never relative paths across packages
- Run commands from repo root using workspace tool (turbo/nx/pnpm)
"""))

    return rules


# ── Supporting file generators ───────────────────────────────────────────

def get_claudeignore(frontend, backend):
    """Generate .claudeignore."""
    lines = [
        "# Dependencies",
        "node_modules/", "vendor/", ".venv/", "__pycache__/",
        "",
        "# Build output",
        "dist/", "build/", ".next/", ".nuxt/", ".svelte-kit/", ".output/",
        "*.pyc", "*.pyo",
        "",
        "# Environment & secrets",
        ".env", ".env.local", ".env.*.local", "*.pem", "*.key",
        "",
        "# IDE & OS",
        ".idea/", ".vscode/", "*.swp", ".DS_Store", "Thumbs.db",
        "",
        "# Package locks",
        "package-lock.json", "pnpm-lock.yaml", "yarn.lock", "poetry.lock",
        "",
        "# Large/binary files",
        "*.min.js", "*.min.css", "*.map",
        "*.png", "*.jpg", "*.jpeg", "*.gif", "*.ico", "*.svg",
        "*.woff", "*.woff2", "*.ttf", "*.eot",
        "",
        "# Test artifacts",
        "coverage/", ".nyc_output/", "htmlcov/", ".pytest_cache/",
        "test-results/", "playwright-report/",
    ]
    return "\n".join(lines) + "\n"


def get_env_example(database, auth, ai):
    """Generate .env.example."""
    lines = ["# Environment Variables", "# Copy to .env and fill in values", ""]

    db_vars = {
        "postgresql": ["DATABASE_URL=postgresql://user:password@localhost:5432/dbname"],
        "mongodb": ["MONGODB_URI=mongodb://localhost:27017/dbname"],
        "supabase": [
            "NEXT_PUBLIC_SUPABASE_URL=https://your-project.supabase.co",
            "NEXT_PUBLIC_SUPABASE_ANON_KEY=your-anon-key",
            "SUPABASE_SERVICE_ROLE_KEY=your-service-role-key",
        ],
        "sqlite": ["DATABASE_URL=file:./dev.db"],
    }
    lines.extend(db_vars.get(database, []))
    lines.append("")

    auth_vars = {
        "clerk": ["NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY=pk_...", "CLERK_SECRET_KEY=sk_..."],
        "nextauth": ["AUTH_SECRET=generate-with-openssl-rand-base64-32", "AUTH_GOOGLE_ID=", "AUTH_GOOGLE_SECRET="],
    }
    lines.extend(auth_vars.get(auth, []))

    if ai:
        lines.extend(["", "ANTHROPIC_API_KEY=sk-ant-...", "# OPENAI_API_KEY=sk-..."])

    # MCP-related env vars
    mcp_vars = []
    if database in ("postgresql", "mysql"):
        pass  # DATABASE_URL already added above
    if auth == "none":
        pass  # No additional env vars

    return "\n".join(lines) + "\n"


def get_github_actions_ci(args):
    """Generate GitHub Actions CI workflow."""
    test_cmd = getattr(args, 'test_cmd', None) or "npm run test"
    lint_cmd = getattr(args, 'lint_cmd', None) or "npm run lint"
    build_cmd = getattr(args, 'build_cmd', None) or "npm run build"
    fe = args.frontend
    be = args.backend

    # Detect runtime
    if be in ("python-fastapi", "python-django"):
        runtime = "python"
        setup = """      - uses: actions/setup-python@v5
        with:
          python-version: '3.12'
      - run: pip install -r requirements.txt"""
    elif be in ("go",):
        runtime = "go"
        setup = """      - uses: actions/setup-go@v5
        with:
          go-version: '1.22'"""
    elif be in ("rust-actix",):
        runtime = "rust"
        setup = """      - uses: dtolnay/rust-toolchain@stable"""
    else:
        runtime = "node"
        setup = """      - uses: actions/setup-node@v4
        with:
          node-version: '20'
          cache: 'npm'
      - run: npm ci"""

    return f"""name: CI
on:
  push:
    branches: [main]
  pull_request:
    branches: [main]

jobs:
  ci:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
{setup}
      - name: Lint
        run: {lint_cmd}
      - name: Test
        run: {test_cmd}
      - name: Build
        run: {build_cmd}
"""


def get_gitlab_ci(args):
    """Generate GitLab CI configuration."""
    test_cmd = getattr(args, 'test_cmd', None) or "npm run test"
    lint_cmd = getattr(args, 'lint_cmd', None) or "npm run lint"
    build_cmd = getattr(args, 'build_cmd', None) or "npm run build"
    be = args.backend

    if be in ("python-fastapi", "python-django"):
        image = "python:3.12"
        install = "pip install -r requirements.txt"
    elif be in ("go",):
        image = "golang:1.22"
        install = "go mod download"
    else:
        image = "node:20"
        install = "npm ci"

    return f"""image: {image}

stages:
  - lint
  - test
  - build

before_script:
  - {install}

lint:
  stage: lint
  script:
    - {lint_cmd}

test:
  stage: test
  script:
    - {test_cmd}

build:
  stage: build
  script:
    - {build_cmd}
  only:
    - main
"""


def get_pr_template():
    """Generate a pull request template."""
    return """## Summary
<!-- What does this PR do? Why? -->

## Changes
<!-- List key changes -->
-

## Testing
- [ ] Unit tests pass
- [ ] Integration tests pass
- [ ] Manual testing done

## Checklist
- [ ] Tests added/updated
- [ ] No console.log or debug code
- [ ] No secrets or .env values committed
- [ ] ARCHITECTURE.md updated (if applicable)
"""


def get_first_feature_guide(args):
    """Generate a getting-started guide for the first feature."""
    fe = args.frontend
    be = args.backend
    test_cmd = getattr(args, 'test_cmd', None) or "npm run test"
    lint_cmd = getattr(args, 'lint_cmd', None) or "npm run lint"

    step = 1
    steps = [
        f"# First Feature Guide — {args.project_name}\n",
        "Follow these steps to build your first feature with Claude Code.\n",
        f"## {step}. Plan",
        "```",
        "/new-feature <feature-name>",
        "```",
        "This creates a branch and presents a plan for approval.\n",
    ]
    step += 1

    steps.extend([
        f"## {step}. Design",
        "Use the architect agent to produce a blueprint:",
        "```",
        "@architect Design the <feature-name> feature",
        "```",
        "Review the blueprint in `docs/blueprints/`.\n",
    ])
    step += 1

    if fe and fe != "none":
        steps.extend([
            f"## {step}. Build Frontend",
            f"Use skills to scaffold {fe} components:",
            "```",
            "/generate-component <ComponentName>",
            "/generate-page <page-name>",
            "```\n",
        ])
        step += 1

    if be and be not in ("none", "integrated"):
        steps.extend([
            f"## {step}. Build API",
            f"Scaffold {be} endpoints:",
            "```",
            "/generate-endpoint <endpoint-name>",
            "```\n",
        ])
        step += 1

    steps.extend([
        f"## {step}. Test",
        "Use the testing agent or TDD skill:",
        "```",
        f"@testing Write tests for <feature-name>",
        f"# or run: {test_cmd}",
        "```\n",
    ])
    step += 1

    steps.extend([
        f"## {step}. Review & Push",
        "```",
        "@reviewer Review my changes",
        "@push Create PR for <feature-name>",
        "```\n",
    ])
    step += 1

    steps.extend([
        f"## {step}. Wrap Up",
        "```",
        "/handoff",
        "```",
        "This saves session context for next time.\n",
    ])

    return "\n".join(steps)


def get_blueprint_template():
    """Generate the blueprint template for agent orchestration."""
    return """# Blueprint: {Feature Name}

## Summary
<!-- One paragraph: what this feature does and why -->

## Data Model Changes
<!-- Schema/migration changes needed -->
- (none)

## API Changes
<!-- New or modified endpoints -->
- (none)

## Components
<!-- UI components to create/modify -->
- (none)

## Security Considerations
<!-- Auth, validation, permissions -->
- (none)

## Test Plan
<!-- What to test: happy path, edge cases, error conditions -->
- [ ] Happy path
- [ ] Error handling
- [ ] Auth/permissions

## Risks
<!-- What could go wrong, dependencies, unknowns -->
- (none)
"""


def get_handoff(project_name):
    """Generate initial handoff document."""
    return f"""# Session Handoff — {project_name}

## What's Working
- Project scaffolded with Claude Launchpad
- .claude/ configuration generated

## In Progress
- (first session — nothing yet)

## Known Issues
- (none)

## Next Steps
1. Review CLAUDE.md and ARCHITECTURE.md
2. Run `/project-status` to verify setup
3. Start first feature with `/new-feature <feature-name>`

## Architecture Decisions
(Record key decisions here as the project evolves)
"""


# ── CLAUDE.md & ARCHITECTURE.md generators ──────────────────────────────

STACK_LABELS = {
    "nextjs": "Next.js (App Router)", "react-vite": "React + Vite", "vue": "Vue 3 / Nuxt",
    "sveltekit": "SvelteKit", "node-express": "Express", "node-fastify": "Fastify",
    "python-fastapi": "FastAPI", "python-django": "Django", "go": "Go", "rust-actix": "Rust / Actix",
    "ruby-rails": "Ruby on Rails", "integrated": "Integrated (Next.js/SvelteKit)",
    "postgresql": "PostgreSQL", "mongodb": "MongoDB", "supabase": "Supabase", "sqlite": "SQLite",
    "mysql": "MySQL", "dynamodb": "DynamoDB", "prisma": "Prisma", "drizzle": "Drizzle",
    "sqlalchemy": "SQLAlchemy", "mongoose": "Mongoose", "typeorm": "TypeORM",
    "sequelize": "Sequelize", "activerecord": "ActiveRecord",
    "clerk": "Clerk", "nextauth": "NextAuth / Auth.js", "supabase-auth": "Supabase Auth",
    "custom-jwt": "Custom JWT", "vercel": "Vercel", "railway": "Railway", "aws": "AWS",
    "fly": "Fly.io", "self-hosted": "Self-hosted",
}

STACK_MISTAKES = {
    "nextjs": [
        'NEVER add "use client" at page level without a specific reason',
        "NEVER import server code in client components",
        "NEVER expose secrets without NEXT_PUBLIC_ prefix in client code",
    ],
    "react-vite": [
        "NEVER store server state in Zustand — use React Query for server data",
        "NEVER make API calls directly in components — use the API layer",
    ],
    "python-fastapi": [
        "NEVER return SQLAlchemy models directly — use Pydantic schemas",
        "NEVER use sync DB operations — async everywhere",
    ],
    "python-django": [
        "NEVER put business logic in views — use model methods or service objects",
        "NEVER import User directly — use get_user_model()",
    ],
    "go": [
        "NEVER ignore errors — always handle or propagate with %w",
        "NEVER use global state — pass dependencies explicitly",
    ],
    "prisma": [
        "NEVER edit applied migrations — create new ones",
        "ALWAYS run prisma generate after schema changes",
    ],
    "drizzle": [
        "NEVER edit applied migrations — create new ones",
    ],
    "sqlalchemy": [
        "NEVER modify existing Alembic migrations — create new revisions",
    ],
}


def get_claude_md(args):
    """Generate a real, filled-in CLAUDE.md from interview data."""
    name = args.project_name
    fe = args.frontend
    be = args.backend
    db = args.database
    orm = getattr(args, 'orm', 'none') or 'none'
    auth = args.auth or 'none'

    dev_cmd = getattr(args, 'dev_cmd', None) or _default_cmd('dev', fe, be)
    build_cmd = getattr(args, 'build_cmd', None) or _default_cmd('build', fe, be)
    test_cmd = getattr(args, 'test_cmd', None) or _default_cmd('test', fe, be)
    lint_cmd = getattr(args, 'lint_cmd', None) or _default_cmd('lint', fe, be)
    migrate_cmd = getattr(args, 'migrate_cmd', None) or _default_cmd('migrate', fe, be, orm=orm)

    lines = [f"# {name}", ""]

    # Commands
    lines.append("## Commands")
    if dev_cmd:
        lines.append(f"- Dev: `{dev_cmd}`")
    if build_cmd:
        lines.append(f"- Build: `{build_cmd}`")
    if test_cmd:
        lines.append(f"- Test: `{test_cmd}`")
    if lint_cmd:
        lines.append(f"- Lint: `{lint_cmd}`")
    if migrate_cmd:
        lines.append(f"- Migrate: `{migrate_cmd}`")
    lines.append("")

    # Tech stack
    lines.append("## Tech Stack")
    stack_parts = []
    if fe and fe != "none":
        stack_parts.append(f"**Frontend**: {STACK_LABELS.get(fe, fe)}")
    if be and be != "none":
        stack_parts.append(f"**Backend**: {STACK_LABELS.get(be, be)}")
    if db and db != "none":
        db_label = STACK_LABELS.get(db, db)
        if orm and orm != "none":
            db_label += f" + {STACK_LABELS.get(orm, orm)}"
        stack_parts.append(f"**Database**: {db_label}")
    if auth and auth != "none":
        stack_parts.append(f"**Auth**: {STACK_LABELS.get(auth, auth)}")
    hosting = getattr(args, 'hosting', 'none') or 'none'
    if hosting != "none":
        stack_parts.append(f"**Hosting**: {STACK_LABELS.get(hosting, hosting)}")
    for part in stack_parts:
        lines.append(f"- {part}")
    lines.append("")

    # Architecture
    lines.append("## Architecture")
    if be == "integrated":
        lines.append(f"Monolith with {STACK_LABELS.get(fe, fe)} handling both frontend and API routes.")
    elif be and be != "none" and fe and fe != "none":
        lines.append(f"{STACK_LABELS.get(fe, fe)} frontend with {STACK_LABELS.get(be, be)} backend API.")
    elif be and be != "none":
        lines.append(f"{STACK_LABELS.get(be, be)} API service.")
    if db and db != "none":
        lines.append(f"Data in {STACK_LABELS.get(db, db)}" + (f" via {STACK_LABELS.get(orm, orm)}." if orm != "none" else "."))
    if auth and auth != "none":
        lines.append(f"Authentication via {STACK_LABELS.get(auth, auth)}.")
    lines.append("")
    lines.append("See [ARCHITECTURE.md](./ARCHITECTURE.md) for full design.")
    lines.append("")

    # Mistakes to avoid
    mistakes = []
    for key in (fe, be, orm):
        if key and key != "none" and key in STACK_MISTAKES:
            mistakes.extend(STACK_MISTAKES[key])
    if mistakes:
        lines.append("## Mistakes to Avoid")
        for m in mistakes[:6]:  # Cap at 6 to stay lean
            lines.append(f"- {m}")
        lines.append("")

    # Repository
    lines.append("## Repository")
    lines.append("- Branches: `feature/*`, `fix/*`, `chore/*`")
    cc = getattr(args, 'conventional_commits', False)
    lines.append(f"- Commits: {'Conventional Commits (feat/fix/refactor/test/docs/chore)' if cc else 'Descriptive messages'}")
    lines.append("")

    # Session management
    lines.append("## Session Management")
    lines.append("Run `/handoff` at end of each session. Run `/project-status` to resume.")
    lines.append("")

    return "\n".join(lines)


def _default_cmd(kind, fe, be, orm=None):
    """Return a sensible default command based on stack."""
    is_node = fe in ("nextjs", "react-vite", "vue", "sveltekit") or be in ("node-express", "node-fastify", "integrated")
    is_python = be in ("python-fastapi", "python-django")
    is_go = be == "go"
    is_rust = be == "rust-actix"
    is_ruby = be == "ruby-rails"

    defaults = {
        "dev": {True: "npm run dev", "python": "uvicorn app.main:app --reload", "django": "python manage.py runserver",
                "go": "go run cmd/server/main.go", "rust": "cargo run", "ruby": "rails server"},
        "build": {True: "npm run build", "go": "go build ./...", "rust": "cargo build --release", "ruby": None},
        "test": {True: "npm run test", "python": "pytest", "django": "python manage.py test",
                 "go": "go test ./...", "rust": "cargo test", "ruby": "rails test"},
        "lint": {True: "npm run lint", "python": "ruff check .", "django": "ruff check .",
                 "go": "golangci-lint run", "rust": "cargo clippy", "ruby": "bundle exec rubocop"},
        "migrate": {"prisma": "npx prisma migrate dev", "drizzle": "npx drizzle-kit migrate",
                     "sqlalchemy": "alembic upgrade head", "activerecord": "rails db:migrate"},
    }

    if kind == "migrate":
        return defaults["migrate"].get(orm)

    cmd_map = defaults.get(kind, {})
    if is_python and be == "python-django":
        return cmd_map.get("django")
    if is_python:
        return cmd_map.get("python")
    if is_go:
        return cmd_map.get("go")
    if is_rust:
        return cmd_map.get("rust")
    if is_ruby:
        return cmd_map.get("ruby")
    if is_node:
        return cmd_map.get(True)
    return None


def get_architecture_md(args):
    """Generate a real, filled-in ARCHITECTURE.md from interview data."""
    name = args.project_name
    fe = args.frontend
    be = args.backend
    db = args.database
    orm = getattr(args, 'orm', 'none') or 'none'
    auth = args.auth or 'none'

    fe_label = STACK_LABELS.get(fe, fe) if fe and fe != "none" else None
    be_label = STACK_LABELS.get(be, be) if be and be != "none" else None
    db_label = STACK_LABELS.get(db, db) if db and db != "none" else None
    auth_label = STACK_LABELS.get(auth, auth) if auth != "none" else None
    hosting_label = STACK_LABELS.get(getattr(args, 'hosting', 'none') or 'none', None)

    lines = [f"# Architecture — {name}", ""]

    # Overview
    lines.append("## Overview")
    parts = []
    if fe_label and be == "integrated":
        parts.append(f"Full-stack {fe_label} application with integrated API routes")
    elif fe_label and be_label:
        parts.append(f"{fe_label} frontend with {be_label} backend")
    elif be_label:
        parts.append(f"{be_label} API service")
    if db_label:
        orm_suffix = f" via {STACK_LABELS.get(orm, orm)}" if orm != "none" else ""
        parts.append(f"{db_label}{orm_suffix} for persistence")
    if auth_label:
        parts.append(f"{auth_label} for authentication")
    lines.append(". ".join(parts) + "." if parts else "")
    lines.append("")

    # Mermaid diagram
    lines.append("## System Architecture")
    lines.append("")
    lines.append("```mermaid")
    lines.append("graph LR")
    if fe_label and be == "integrated":
        lines.append(f'    Client["{fe_label}"] --> API["API Routes"]')
    elif fe_label and be_label:
        lines.append(f'    Client["{fe_label}"] --> API["{be_label}"]')
    elif be_label:
        lines.append(f'    Client["Client"] --> API["{be_label}"]')
    if db_label:
        lines.append(f'    API --> DB[("{db_label}")]')
    if auth_label:
        lines.append(f'    API --> Auth["{auth_label}"]')
    lines.append("```")
    lines.append("")

    # Key decisions table
    lines.append("## Key Decisions")
    lines.append("")
    lines.append("| Decision | Choice | Rationale |")
    lines.append("|----------|--------|-----------|")
    if fe_label:
        lines.append(f"| Frontend | {fe_label} | |")
    if be_label:
        lines.append(f"| Backend | {be_label} | |")
    if db_label:
        lines.append(f"| Database | {db_label} | |")
    if orm != "none":
        lines.append(f"| ORM | {STACK_LABELS.get(orm, orm)} | |")
    if auth_label:
        lines.append(f"| Auth | {auth_label} | |")
    if hosting_label:
        lines.append(f"| Hosting | {hosting_label} | |")
    lines.append("")

    # Patterns
    lines.append("## Patterns")
    lines.append("")
    lines.append("### Data Access")
    if orm == "prisma":
        lines.append("Prisma client for all database access. Models defined in `prisma/schema.prisma`.")
    elif orm == "drizzle":
        lines.append("Drizzle ORM for type-safe queries. Schema in `src/db/schema.ts`.")
    elif orm == "sqlalchemy":
        lines.append("SQLAlchemy async sessions with Alembic migrations. Models in `app/models/`.")
    elif orm == "activerecord":
        lines.append("ActiveRecord with Rails migrations. Models in `app/models/`.")
    elif orm == "mongoose":
        lines.append("Mongoose schemas with TypeScript interfaces. Models in `src/models/`.")
    else:
        lines.append("(Document your data access pattern here)")
    lines.append("")

    lines.append("### Error Handling")
    lines.append("(Document your error handling strategy: custom error classes, centralized handler, what gets logged vs shown)")
    lines.append("")

    lines.append("### Authentication Flow")
    if auth == "clerk":
        lines.append("`clerkMiddleware()` protects routes. `auth()` in Server Components, `useUser()` in Client Components. Users synced via webhooks.")
    elif auth == "nextauth":
        lines.append("NextAuth.js with JWT strategy. Callbacks for custom session content. `signIn()`/`signOut()` server actions.")
    elif auth == "supabase-auth":
        lines.append("Supabase Auth with RLS policies. Server client for SSR, browser client for components.")
    elif auth == "custom-jwt":
        lines.append("Custom JWT with short-lived access tokens (15min) and refresh token rotation. httpOnly cookies for web.")
    else:
        lines.append("(Document your auth flow here)")
    lines.append("")

    # Environment
    lines.append("## Environment Variables")
    lines.append("See `.env.example` for the complete list.")
    lines.append("")

    return "\n".join(lines)


# ── Main scaffold logic ─────────────────────────────────────────────────

def safe_write(filepath: Path, content: str, force: bool = False, update: bool = False, dry_run: bool = False) -> str:
    """Write a file safely with multiple modes.

    Modes:
        default:  Skip if file exists
        force:    Always overwrite
        dry_run:  Report what would happen, write nothing

    Returns: 'created', 'skipped', or 'overwritten'
    """
    existed = filepath.exists()
    if existed and not force:
        return "skipped"
    if dry_run:
        return "overwritten" if existed else "created"
    try:
        filepath.write_text(content)
    except OSError as e:
        print(f"  ✗ Failed to write {filepath.name}: {e}", file=sys.stderr)
        return "skipped"
    return "overwritten" if existed else "created"


def merge_settings(existing_path: Path, new_settings: dict) -> tuple[dict, list[str]]:
    """Merge new settings into existing settings.json without losing user config.

    Returns: (merged_dict, list_of_changes)
    """
    changes = []
    try:
        existing = json.loads(existing_path.read_text())
    except (json.JSONDecodeError, FileNotFoundError):
        return new_settings, ["Created new settings.json"]

    # Merge MCP servers — add missing, don't touch existing
    if "mcpServers" in new_settings:
        if "mcpServers" not in existing:
            existing["mcpServers"] = {}
        for name, config in new_settings["mcpServers"].items():
            if name not in existing["mcpServers"]:
                existing["mcpServers"][name] = config
                changes.append(f"Added MCP server: {name}")

    # Merge hooks — add missing hook types, don't duplicate existing matchers
    if "hooks" in new_settings:
        if "hooks" not in existing:
            existing["hooks"] = {}
        for hook_type, hook_list in new_settings["hooks"].items():
            if hook_type not in existing["hooks"]:
                existing["hooks"][hook_type] = hook_list
                changes.append(f"Added {hook_type} hooks ({len(hook_list)} rules)")
            else:
                # Add hooks with matchers that don't already exist
                existing_matchers = {h.get("matcher", "") for h in existing["hooks"][hook_type] if isinstance(h, dict)}
                for hook in hook_list:
                    if isinstance(hook, dict) and hook.get("matcher", "") not in existing_matchers:
                        existing["hooks"][hook_type].append(hook)
                        changes.append(f"Added {hook_type} hook: {hook.get('matcher', 'default')}")

    return existing, changes


def validate_settings(settings: dict) -> list[str]:
    """Validate generated settings.json structure. Returns list of warnings."""
    warnings = []
    unknown_keys = set(settings.keys()) - VALID_SETTINGS_KEYS
    if unknown_keys:
        warnings.append(f"Unknown top-level keys: {', '.join(sorted(unknown_keys))}")

    # Validate hooks structure
    hooks = settings.get("hooks", {})
    valid_hook_types = {"PreToolUse", "PostToolUse", "Stop", "Notification"}
    for hook_type in hooks:
        if hook_type not in valid_hook_types:
            warnings.append(f"Unknown hook type: {hook_type}")
        if not isinstance(hooks[hook_type], list):
            warnings.append(f"hooks.{hook_type} should be an array")
            continue
        for i, entry in enumerate(hooks[hook_type]):
            if not isinstance(entry, dict):
                warnings.append(f"hooks.{hook_type}[{i}] should be an object")
                continue
            if "hooks" not in entry:
                warnings.append(f"hooks.{hook_type}[{i}] missing 'hooks' array")

    # Validate MCP servers structure
    mcp = settings.get("mcpServers", {})
    for name, config in mcp.items():
        if not isinstance(config, dict):
            warnings.append(f"mcpServers.{name} should be an object")
            continue
        if "command" not in config:
            warnings.append(f"mcpServers.{name} missing 'command'")

    return warnings


def verify_scaffold(project_dir: Path, args) -> list[str]:
    """Post-scaffold verification. Returns list of issues found."""
    issues = []

    # Check required directories exist
    for subdir in ["agents", "rules", "skills", "commands"]:
        d = project_dir / ".claude" / subdir
        if not d.exists():
            issues.append(f"Missing directory: .claude/{subdir}/")

    # Check settings.json is valid
    settings_path = project_dir / ".claude" / "settings.json"
    if settings_path.exists():
        try:
            data = json.loads(settings_path.read_text())
            # Check MCP servers have env vars documented
            mcp = data.get("mcpServers", {})
            env_example = project_dir / ".env.example"
            if env_example.exists():
                env_content = env_example.read_text()
                for name, config in mcp.items():
                    for env_key, env_val in config.get("env", {}).items():
                        if env_val.startswith("${"):
                            var_name = env_val.strip("${}")
                            if var_name not in env_content:
                                issues.append(f"MCP '{name}' needs {var_name} but it's not in .env.example")
        except (json.JSONDecodeError, UnicodeDecodeError):
            issues.append("settings.json is not valid JSON")

    # Check CLAUDE.md and ARCHITECTURE.md exist
    for name in ["CLAUDE.md", "ARCHITECTURE.md"]:
        if not (project_dir / name).exists():
            issues.append(f"{name} not created")

    # Verify lint/test commands are syntactically valid
    for cmd_name, cmd_val in [("lint_cmd", getattr(args, 'lint_cmd', None)),
                               ("test_cmd", getattr(args, 'test_cmd', None)),
                               ("dev_cmd", getattr(args, 'dev_cmd', None)),
                               ("build_cmd", getattr(args, 'build_cmd', None)),
                               ("migrate_cmd", getattr(args, 'migrate_cmd', None))]:
        if cmd_val and not SAFE_CMD_PATTERN.match(cmd_val):
            issues.append(f"Command '{cmd_name}' ({cmd_val}) doesn't match allowed patterns")

    return issues


def print_token_summary(created_files: list[str], project_dir: Path, mcp_count: int):
    """Print estimated token impact of generated config."""
    TOKENS_PER_LINE = 4
    total_lines = 0
    components = []

    for rel_path in created_files:
        fp = project_dir / rel_path
        if fp.exists() and fp.suffix in ('.md', '.json'):
            try:
                lines = sum(1 for line in fp.read_text().splitlines() if line.strip())
                tokens = lines * TOKENS_PER_LINE
                total_lines += lines
                components.append((rel_path, lines, tokens))
            except (OSError, UnicodeDecodeError):
                pass

    mcp_tokens = mcp_count * MCP_CONTEXT_COST
    config_tokens = total_lines * TOKENS_PER_LINE
    total_tokens = config_tokens + mcp_tokens
    context_pct = round(total_tokens / 200000 * 100, 1)

    print(f"\n📊 Token Budget Summary")
    print(f"  Config files:  ~{config_tokens:,d} tokens ({total_lines} lines)")
    if mcp_count > 0:
        print(f"  MCP servers:   ~{mcp_tokens:,d} tokens ({mcp_count} servers × ~{MCP_CONTEXT_COST:,d})")
    print(f"  Total impact:  ~{total_tokens:,d} tokens ({context_pct}% of 200k context)")
    if context_pct > 5:
        print(f"  ⚠ Config uses >{context_pct}% of context — consider trimming")


def scaffold(args):
    """Main scaffold function."""
    output_dir = Path(args.output_dir).resolve()
    project_dir = output_dir / args.project_name if args.create_root else output_dir
    force = args.force
    update = args.update
    dry_run = getattr(args, 'dry_run', False)

    if force and update:
        print("Error: --force and --update are mutually exclusive.", file=sys.stderr)
        return 1

    if dry_run:
        print(f"DRY RUN — no files will be created or modified.\n")

    if args.create_root and not dry_run:
        project_dir.mkdir(parents=True, exist_ok=True)

    # Detect existing .claude/ and warn
    existing_claude = (project_dir / ".claude").exists()
    if existing_claude and not force and not update:
        print(f"⚠  Existing .claude/ detected in {project_dir}")
        print("   Existing files will NOT be overwritten. Only missing files will be created.")
        print("   Use --update to merge new config into existing files.")
        print("   Use --force to overwrite everything (backs up nothing — use git).\n")
    elif update:
        print(f"📦  Update mode: merging new config into existing .claude/ in {project_dir}\n")

    # Track all created files for manifest
    created_files = []

    print(f"Scaffolding {args.project_name} in {project_dir}")
    print(f"  Frontend: {args.frontend}, Backend: {args.backend}, DB: {args.database}")

    # 1. Create .claude/ structure (only create directories that don't exist)
    if not dry_run:
        for subdir in ["agents", "rules", "skills", "commands"]:
            d = project_dir / ".claude" / subdir
            if not d.exists():
                d.mkdir(parents=True, exist_ok=True)
        for docs_subdir in ("blueprints", "prds"):
            docs_dir = project_dir / "docs" / docs_subdir
            if not docs_dir.exists():
                docs_dir.mkdir(parents=True, exist_ok=True)
    print("  Created .claude/ directory structure")

    # 2. Slash commands
    skill_path = str(Path(__file__).resolve().parent.parent)
    cmds_dir = project_dir / ".claude" / "commands"
    commands = {
        "project-status": cmd_project_status(), "handoff": cmd_handoff(),
        "new-feature": cmd_new_feature(), "fix-bug": cmd_fix_bug(),
        "idea-to-prd": cmd_idea_to_prd(),
        "audit": cmd_audit(skill_path),
        "build": cmd_build(getattr(args, 'domain', 'general'), getattr(args, 'compliance', ['none']), args.tdd, getattr(args, 'worktree', True)),
        "analyze": cmd_analyze(skill_path), "learn": cmd_learn(skill_path),
        "evolve": cmd_evolve(skill_path),
    }
    if args.tdd:
        commands["tdd"] = cmd_tdd()
    if args.team:
        commands["pipeline"] = cmd_pipeline()
    # Handle renamed commands from previous versions
    RENAMED_COMMANDS = {"status": "project-status"}
    for old_name, new_name in RENAMED_COMMANDS.items():
        old_path = cmds_dir / f"{old_name}.md"
        new_path = cmds_dir / f"{new_name}.md"
        if old_path.exists() and not new_path.exists() and not dry_run:
            old_path.rename(new_path)
            print(f"  Renamed {old_name}.md → {new_name}.md")
        elif old_path.exists() and not dry_run:
            # New file already exists; keep old file as backup rather than deleting
            print(f"  Note: {new_name}.md exists; keeping obsolete {old_name}.md (delete manually if not needed)")

    created_cmds, skipped_cmds = 0, 0
    for name, content in commands.items():
        fp = cmds_dir / f"{name}.md"
        result = safe_write(fp, content, force, dry_run=dry_run)
        if result == "skipped":
            skipped_cmds += 1
        else:
            created_cmds += 1
            created_files.append(str(fp.relative_to(project_dir)) if project_dir.exists() else f".claude/commands/{name}.md")
    msg = f"  Created {created_cmds} commands"
    if skipped_cmds:
        msg += f" (skipped {skipped_cmds} existing)"
    print(msg)

    # 3. Skills
    skills_dir = project_dir / ".claude" / "skills"
    skills = get_skills(args)
    created_skills, skipped_skills = 0, 0
    for name, content in skills:
        fp = skills_dir / f"{name}.md"
        result = safe_write(fp, content, force, dry_run=dry_run)
        if result == "skipped":
            skipped_skills += 1
        else:
            created_skills += 1
            created_files.append(f".claude/skills/{name}.md")
    msg = f"  Created {created_skills} skills"
    if skipped_skills:
        msg += f" (skipped {skipped_skills} existing)"
    print(msg)

    # 4. Agents
    agents_dir = project_dir / ".claude" / "agents"
    agents = get_agents(args)
    created_agents, skipped_agents = 0, 0
    for name, content in agents:
        fp = agents_dir / f"{name}.md"
        result = safe_write(fp, content, force, dry_run=dry_run)
        if result == "skipped":
            skipped_agents += 1
        else:
            created_agents += 1
            created_files.append(f".claude/agents/{name}.md")
    msg = f"  Created {created_agents} agents"
    if skipped_agents:
        msg += f" (skipped {skipped_agents} existing)"
    print(msg)

    # 5. Rules
    rules_dir = project_dir / ".claude" / "rules"
    rules = get_rules(args)
    created_rules, skipped_rules = 0, 0
    for name, content in rules:
        fp = rules_dir / f"{name}.md"
        result = safe_write(fp, content, force, dry_run=dry_run)
        if result == "skipped":
            skipped_rules += 1
        else:
            created_rules += 1
            created_files.append(f".claude/rules/{name}.md")
    msg = f"  Created {created_rules} rules"
    if skipped_rules:
        msg += f" (skipped {skipped_rules} existing)"
    print(msg)

    # 6. Supporting files
    support_files = [
        ("claudeignore", ".claudeignore", get_claudeignore(args.frontend, args.backend)),
        ("env.example", ".env.example", get_env_example(args.database, args.auth or "none", args.ai)),
        ("handoff.md", ".claude/handoff.md", get_handoff(args.project_name)),
        ("first-feature.md", "docs/first-feature.md", get_first_feature_guide(args)),
        ("blueprint-template.md", "docs/blueprints/.template.md", get_blueprint_template()),
    ]
    results = []
    for label, rel_path, content in support_files:
        result = safe_write(project_dir / rel_path, content, force, dry_run=dry_run)
        results.append((label, result))
        if result != "skipped":
            created_files.append(rel_path)
    created = [n for n, r in results if r != "skipped"]
    skipped = [n for n, r in results if r == "skipped"]
    if created:
        print(f"  Created {', '.join(created)}")
    if skipped:
        print(f"  Skipped existing: {', '.join(skipped)}")

    # 5. MCP servers + hooks
    mcp_servers = get_mcp_servers(args)
    hooks = get_hooks(args)

    # 6. settings.json with hooks + MCP
    settings = {}
    if hooks:
        settings["hooks"] = hooks
    if mcp_servers:
        settings["mcpServers"] = mcp_servers
    # Validate before writing
    schema_warnings = validate_settings(settings)
    for w in schema_warnings:
        print(f"  ⚠ Settings validation: {w}", file=sys.stderr)

    settings_path = project_dir / ".claude" / "settings.json"
    if dry_run:
        if mcp_servers:
            print(f"  Would configure {len(mcp_servers)} MCP servers: {', '.join(mcp_servers.keys())}")
        else:
            print("  No MCP servers to configure")
        created_files.append(".claude/settings.json")
    elif not settings_path.exists():
        settings_path.write_text(json.dumps(settings, indent=2) + "\n")
        created_files.append(".claude/settings.json")
        if mcp_servers:
            print(f"  Configured {len(mcp_servers)} MCP servers: {', '.join(mcp_servers.keys())}")
        else:
            print("  No MCP servers configured (add later in .claude/settings.json)")
    elif update:
        merged, changes = merge_settings(settings_path, settings)
        if changes:
            settings_path.write_text(json.dumps(merged, indent=2) + "\n")
            created_files.append(".claude/settings.json")
            for c in changes:
                print(f"  ✓ {c}")
        else:
            print("  settings.json already up to date (no new MCP servers to add)")
    elif force:
        settings_path.write_text(json.dumps(settings, indent=2) + "\n")
        created_files.append(".claude/settings.json")
        if mcp_servers:
            print(f"  Configured {len(mcp_servers)} MCP servers: {', '.join(mcp_servers.keys())}")
    else:
        print("  Skipped existing settings.json (use --update to merge, --force to overwrite)")

    # 7. Generate real CLAUDE.md and ARCHITECTURE.md with interview data
    claude_md_path = project_dir / "CLAUDE.md"
    result = safe_write(claude_md_path, get_claude_md(args), force, dry_run=dry_run)
    if result == "skipped":
        print("  Skipped existing CLAUDE.md")
    else:
        created_files.append("CLAUDE.md")
        print("  Created CLAUDE.md")

    arch_md_path = project_dir / "ARCHITECTURE.md"
    result = safe_write(arch_md_path, get_architecture_md(args), force, dry_run=dry_run)
    if result == "skipped":
        print("  Skipped existing ARCHITECTURE.md")
    else:
        created_files.append("ARCHITECTURE.md")
        print("  Created ARCHITECTURE.md")

    # 8. CI/CD and PR template
    ci_cd = getattr(args, 'ci_cd', 'none') or 'none'
    if ci_cd == "github-actions":
        ci_dir = project_dir / ".github" / "workflows"
        if not dry_run:
            ci_dir.mkdir(parents=True, exist_ok=True)
        ci_path = ci_dir / "ci.yml"
        result = safe_write(ci_path, get_github_actions_ci(args), force, dry_run=dry_run)
        if result != "skipped":
            created_files.append(".github/workflows/ci.yml")
            print("  Created .github/workflows/ci.yml")

        # PR template
        pr_dir = project_dir / ".github"
        if not dry_run:
            pr_dir.mkdir(parents=True, exist_ok=True)
        pr_path = pr_dir / "pull_request_template.md"
        result = safe_write(pr_path, get_pr_template(), force, dry_run=dry_run)
        if result != "skipped":
            created_files.append(".github/pull_request_template.md")
            print("  Created .github/pull_request_template.md")

    elif ci_cd == "gitlab-ci":
        ci_path = project_dir / ".gitlab-ci.yml"
        result = safe_write(ci_path, get_gitlab_ci(args), force, dry_run=dry_run)
        if result != "skipped":
            created_files.append(".gitlab-ci.yml")
            print("  Created .gitlab-ci.yml")

    # 9. Config metadata (routed through safe_write for consistency)
    metadata = {
        "project_name": args.project_name,
        "frontend": args.frontend, "backend": args.backend,
        "database": args.database, "auth": args.auth or "none",
        "orm": getattr(args, 'orm', 'none') or "none",
        "domain": getattr(args, 'domain', 'general'),
        "compliance": getattr(args, 'compliance', ['none']),
        "event_systems": getattr(args, 'event_systems', []) or [],
        "event_patterns": getattr(args, 'event_patterns', []) or [],
        "schema_format": getattr(args, 'schema_format', 'none'),
        "workflow_orchestration": getattr(args, 'workflow_orchestration', 'none'),
        "ai": args.ai, "hosting": args.hosting or "none",
        "git_platform": args.git_platform or "none",
        "ci_cd": getattr(args, 'ci_cd', 'none') or "none",
        "team": args.team, "tdd": args.tdd,
        "conventional_commits": args.conventional_commits,
        "dev_cmd": getattr(args, 'dev_cmd', None),
        "build_cmd": getattr(args, 'build_cmd', None),
        "lint_cmd": getattr(args, 'lint_cmd', None),
        "test_cmd": getattr(args, 'test_cmd', None),
        "migrate_cmd": getattr(args, 'migrate_cmd', None),
        "skill_path": str(Path(__file__).resolve().parent.parent),
        "scaffolded_at": datetime.now().isoformat(),
        "version": VERSION,
        "last_analysis": datetime.now().isoformat() if getattr(args, 'analyze', False) else None,
    }

    # Save dependency snapshot for drift detection (Feature 5)
    # Use cached snapshot from analyze phase if available, otherwise scan fresh
    if getattr(args, '_dep_snapshot', None):
        metadata["dependency_snapshot"] = args._dep_snapshot
    elif getattr(args, 'analyze', False):
        try:
            from analyze import snapshot_dependencies
            output_dir_path = Path(args.output_dir).resolve()
            project_dir_for_deps = output_dir_path / args.project_name if args.create_root else output_dir_path
            if project_dir_for_deps.exists():
                dep_snapshot = snapshot_dependencies(project_dir_for_deps)
                if dep_snapshot:
                    metadata["dependency_snapshot"] = dep_snapshot
        except ImportError:
            pass

    config_path = project_dir / ".claude" / "launchpad-config.json"
    if not dry_run:
        if update and config_path.exists():
            try:
                existing_meta = json.loads(config_path.read_text())
                metadata["scaffolded_at"] = existing_meta.get("scaffolded_at", metadata["scaffolded_at"])
                metadata["updated_at"] = datetime.now().isoformat()
            except (json.JSONDecodeError, FileNotFoundError):
                pass
        result = safe_write(config_path, json.dumps(metadata, indent=2) + "\n", force=True, dry_run=False)
        if result != "skipped":
            created_files.append(".claude/launchpad-config.json")

    # 9. Write manifest of created files
    if created_files and not dry_run:
        manifest_path = project_dir / ".claude" / "launchpad-manifest.json"
        manifest = {
            "version": VERSION,
            "created_at": datetime.now().isoformat(),
            "files": sorted(created_files),
        }
        manifest_path.write_text(json.dumps(manifest, indent=2) + "\n")

    print(f"\nDone! {len(commands)} commands, {len(skills)} skills, {len(agents)} agents, {len(rules)} rules generated.")
    if created_files:
        print(f"  {len(created_files)} files created/updated (manifest: .claude/launchpad-manifest.json)")

    # Token budget summary
    if created_files and not dry_run:
        print_token_summary(created_files, project_dir, len(mcp_servers))

    # Post-scaffold verification
    verify = getattr(args, 'verify', False)
    if verify and not dry_run:
        issues = verify_scaffold(project_dir, args)
        if issues:
            print(f"\n⚠ Verification found {len(issues)} issues:")
            for issue in issues:
                print(f"  - {issue}")
        else:
            print("\n✓ Verification passed — all checks clean")

    print("\nNext: Review CLAUDE.md and ARCHITECTURE.md, then restart Claude Code so it picks up the new commands.")
    print("  After restarting, run /project-status to start building.")
    return 0


def upgrade(project_dir: Path) -> int:
    """Upgrade an existing Launchpad config to the current version."""
    config_path = project_dir / ".claude" / "launchpad-config.json"
    if not config_path.exists():
        print("Error: No launchpad-config.json found. Is this a Launchpad project?", file=sys.stderr)
        return 1

    try:
        config = json.loads(config_path.read_text())
    except (json.JSONDecodeError, UnicodeDecodeError):
        print("Error: launchpad-config.json is not valid JSON", file=sys.stderr)
        return 1

    old_version = config.get("version", "unknown")
    if old_version == VERSION:
        print(f"Already at version {VERSION} — nothing to upgrade.")
        return 0

    print(f"Upgrading {config.get('project_name', 'project')} from v{old_version} to v{VERSION}")
    changes = []

    # Migration: add missing directories
    for subdir in ["agents", "rules", "skills", "commands"]:
        d = project_dir / ".claude" / subdir
        if not d.exists():
            d.mkdir(parents=True, exist_ok=True)
            changes.append(f"Created missing .claude/{subdir}/")

    # Migration: add first-feature guide if missing
    guide_path = project_dir / "docs" / "first-feature.md"
    if not guide_path.exists():
        docs_dir = project_dir / "docs"
        if not docs_dir.exists():
            docs_dir.mkdir(parents=True, exist_ok=True)
        # Create a minimal guide
        guide_path.write_text("# First Feature Guide\n\nRun `/new-feature <name>` to start.\n")
        changes.append("Created docs/first-feature.md")

    # Migration: add handoff if missing
    handoff_path = project_dir / ".claude" / "handoff.md"
    if not handoff_path.exists():
        handoff_path.write_text("# Session Handoff\n\n## What's Working\n- (not yet populated)\n\n## Next Steps\n1. Run /project-status\n")
        changes.append("Created .claude/handoff.md")

    # Update version in config
    config["version"] = VERSION
    config["upgraded_at"] = datetime.now().isoformat()
    config_path.write_text(json.dumps(config, indent=2) + "\n")
    changes.append(f"Updated version to {VERSION}")

    if changes:
        print(f"Applied {len(changes)} changes:")
        for c in changes:
            print(f"  ✓ {c}")
    print(f"\nUpgrade complete. Run the auditor to check health:")
    print(f"  python audit.py {project_dir}")
    return 0


def main():
    p = argparse.ArgumentParser(description="Claude Launchpad scaffolder")
    p.add_argument("--project-name", required=False, default=None)
    p.add_argument("--frontend", choices=["nextjs", "react-vite", "vue", "sveltekit", "none"], default="nextjs")
    p.add_argument("--backend", choices=["node-express", "node-fastify", "python-fastapi", "python-django", "go", "rust-actix", "ruby-rails", "integrated", "none"], default="integrated")
    p.add_argument("--database", choices=["postgresql", "mongodb", "supabase", "sqlite", "mysql", "dynamodb", "none"], default="postgresql")
    p.add_argument("--auth", choices=["clerk", "nextauth", "supabase-auth", "custom-jwt", "none"], default="none")
    p.add_argument("--hosting", choices=["vercel", "railway", "aws", "fly", "self-hosted", "none"], default="none")
    p.add_argument("--git-platform", choices=["github", "gitlab", "bitbucket", "none"], default="none")
    p.add_argument("--domain", choices=["finance", "healthcare", "hr", "e-commerce", "legal", "education", "general"], default="general", help="Project domain for domain-specific auditor agents")
    p.add_argument("--compliance", nargs="*", choices=["gdpr", "sox", "hipaa", "pci-dss", "none"], default=["none"], help="Compliance requirements (multiple allowed)")
    p.add_argument("--ai", action="store_true")
    p.add_argument("--team", action="store_true")
    p.add_argument("--tdd", action="store_true")
    p.add_argument("--no-worktree", action="store_false", dest="worktree", help="Disable git worktree isolation for /build")
    p.add_argument("--conventional-commits", action="store_true")
    p.add_argument("--lint-cmd", default=None, help="Lint command (e.g., 'npm run lint')")
    p.add_argument("--test-cmd", default=None, help="Test command (e.g., 'npm run test')")
    p.add_argument("--dev-cmd", default=None, help="Dev server command (e.g., 'npm run dev')")
    p.add_argument("--build-cmd", default=None, help="Build command (e.g., 'npm run build')")
    p.add_argument("--migrate-cmd", default=None, help="DB migration command (e.g., 'npx prisma migrate dev')")
    p.add_argument("--orm", choices=["prisma", "drizzle", "sqlalchemy", "mongoose", "typeorm", "sequelize", "activerecord", "none"], default="none", help="ORM/database toolkit")
    p.add_argument("--ci-cd", choices=["github-actions", "gitlab-ci", "none"], default="none", help="CI/CD platform")
    p.add_argument("--sentry", action="store_true", help="Add Sentry MCP server")
    p.add_argument("--context7", action="store_true", help="Add Context7 docs MCP server")
    p.add_argument("--sequential-thinking", action="store_true", dest="sequential_thinking", help="Add Sequential Thinking MCP server")
    p.add_argument("--minimal-mcp", action="store_true", dest="minimal_mcp", help="Only include essential MCP servers (skip community)")
    p.add_argument("--force", action="store_true", help="Overwrite existing files (default: skip existing)")
    p.add_argument("--update", action="store_true", help="Merge new config into existing files (add missing commands/skills/MCP)")
    p.add_argument("--dry-run", action="store_true", help="Show what would be created without writing any files")
    p.add_argument("--verify", action="store_true", help="Run post-scaffold verification checks")
    p.add_argument("--preset", choices=list(PRESETS.keys()), default=None, help="Use a preset stack configuration")
    p.add_argument("--upgrade", action="store_true", help="Upgrade existing Launchpad config to current version")
    p.add_argument("--analyze", action="store_true", help="Analyze existing codebase to generate project-specific rules")
    p.add_argument("--monorepo", action="store_true", help="Enable monorepo conventions rule")
    p.add_argument("--migrate-ai-configs", action="store_true", dest="migrate_ai_configs", help="Detect and migrate other AI tool configs (.cursorrules, copilot, etc.)")
    p.add_argument("--event-systems", nargs="*", default=[], help="Event systems (kafka, bullmq, rabbitmq, celery, temporal, nats, aws-events, redis-streams, flink, spark-streaming)")
    p.add_argument("--event-patterns", nargs="*", default=[], help="Event patterns (event-sourcing, cqrs, saga, outbox)")
    p.add_argument("--schema-format", choices=["avro", "protobuf", "json-schema", "none"], default="none", help="Event schema format")
    p.add_argument("--workflow-orchestration", choices=["temporal", "none"], default="none", help="Workflow orchestration platform")
    p.add_argument("--output-dir", default=".")
    p.add_argument("--create-root", action="store_true")
    args = p.parse_args()

    # Handle --upgrade separately
    if args.upgrade:
        project_dir = Path(args.output_dir).resolve()
        sys.exit(upgrade(project_dir))

    # Apply preset defaults (user-specified flags override preset)
    if args.preset:
        preset = PRESETS[args.preset]
        # Default project-name to preset name if not specified
        if not args.project_name:
            args.project_name = args.preset
        for key, value in preset.items():
            # Only apply preset value if user didn't explicitly set it
            # For store_true flags, default is False; for choices, check if it's the argparse default
            current = getattr(args, key, None)
            if key in ("conventional_commits", "tdd", "ai", "team", "sentry"):
                # Boolean flags: only override if still False (default)
                if not current:
                    setattr(args, key, value)
            elif current is None or current == "none":
                setattr(args, key, value)

    # Require project-name (after preset may have set it)
    if not args.project_name:
        p.error("the following arguments are required: --project-name")

    # AI config migration — detect and migrate .cursorrules, copilot, etc.
    if getattr(args, 'migrate_ai_configs', False) or getattr(args, 'analyze', False):
        try:
            from analyze import detect_ai_configs, migrate_ai_configs
            output_dir = Path(args.output_dir).resolve()
            project_dir = output_dir / args.project_name if args.create_root else output_dir
            if project_dir.exists():
                ai_configs = detect_ai_configs(project_dir)
                if ai_configs:
                    print(f"Found {len(ai_configs)} AI tool config(s): {', '.join(c['source'] for c in ai_configs)}")
                    migrated = migrate_ai_configs(project_dir, ai_configs)
                    if migrated:
                        print(f"  Migrated {len(migrated)} config(s) to .claude/rules/")
        except ImportError:
            pass

    # Codebase analysis — detect stack and generate project-specific rules
    if getattr(args, 'analyze', False):
        try:
            from analyze import analyze as run_analysis, write_rules as write_analysis_rules
            output_dir = Path(args.output_dir).resolve()
            project_dir = output_dir / args.project_name if args.create_root else output_dir
            if project_dir.exists():
                print(f"Analyzing codebase in {project_dir}...")
                analysis = run_analysis(project_dir)
                # Override args defaults with detected stack
                stack_to_args = {
                    "frontend": "frontend", "backend": "backend",
                    "database": "database", "orm": "orm", "auth": "auth",
                    "git_platform": "git_platform", "ci_cd": "ci_cd",
                    "hosting": "hosting", "test_cmd": "test_cmd",
                    "lint_cmd": "lint_cmd", "dev_cmd": "dev_cmd",
                    "build_cmd": "build_cmd", "migrate_cmd": "migrate_cmd",
                    "schema_format": "schema_format",
                    "workflow_orchestration": "workflow_orchestration",
                }
                for stack_key, arg_key in stack_to_args.items():
                    detected = analysis.stack.get(stack_key)
                    if detected and getattr(args, arg_key, None) in (None, "none"):
                        setattr(args, arg_key, detected)
                        print(f"  Detected {arg_key}: {detected}")
                # Handle list values from analyzer
                for list_key in ("event_systems", "event_patterns"):
                    detected = analysis.stack.get(list_key)
                    if detected and not getattr(args, list_key, []):
                        setattr(args, list_key, detected)
                        print(f"  Detected {list_key}: {', '.join(detected)}")
                # Enable monorepo flag if analysis detected a monorepo
                monorepo_info = analysis.stack.get("monorepo")
                if monorepo_info:
                    args.monorepo = True
                    args._monorepo_info = monorepo_info
                    pkg_count = len(monorepo_info.get("packages", []))
                    print(f"  Detected monorepo: {monorepo_info['tool']} ({pkg_count} packages)")
                # Write analyzer rules
                created = write_analysis_rules(project_dir, analysis, force=args.force)
                if created:
                    print(f"  Generated {len(created)} project-specific rules from codebase analysis")
                # Capture dependency snapshot for drift detection
                try:
                    from analyze import snapshot_dependencies
                    dep_snapshot = snapshot_dependencies(project_dir)
                    if dep_snapshot:
                        args._dep_snapshot = dep_snapshot
                        print(f"  Captured dependency snapshot ({sum(len(v) for v in dep_snapshot.values())} packages)")
                except ImportError:
                    pass
                print()
            else:
                print(f"  Skipping analysis — {project_dir} doesn't exist yet")
        except ImportError:
            print("  Warning: analyze.py not found, skipping codebase analysis", file=sys.stderr)

    # M1: Validate project name
    if not PROJECT_NAME_PATTERN.match(args.project_name):
        print(f"Error: Invalid project name '{args.project_name}'. Use letters, numbers, dots, hyphens, underscores.", file=sys.stderr)
        sys.exit(1)

    sys.exit(scaffold(args))


if __name__ == "__main__":
    main()
