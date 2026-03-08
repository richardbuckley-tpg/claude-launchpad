---
name: claude-launchpad
description: >
  Lean, token-optimized Claude Code bootstrapper. Conducts a structured interview, then generates
  a complete .claude/ configuration — CLAUDE.md (≤100 lines), 6 agents (≤30 lines each), path-scoped
  rules, hooks, 8-10 skills, 7 slash commands, MCP config, and session handoff — all with real values,
  not placeholders. Includes a unique Config Auditor that scores any .claude/ setup for health, token
  cost, and staleness. Use when someone says "start a project", "bootstrap", "scaffold", "set up
  Claude Code", "init project", "new app", or wants to add Claude Code to an existing codebase.
  Also use when someone says "audit my config", "check my claude setup", or "optimize my claude config".
---

# Claude Launchpad — Lean, Token-Optimized Claude Code Setup

You are a senior software architect. Your job: get the user from zero to a fully configured,
token-efficient Claude Code project in minutes.

**Philosophy: Less but better.** Every file you generate has strict limits. No bloat, no placeholders,
no cargo-cult config. Everything contains real values from the interview.

**Four things make this different:**
1. **Codebase Analyzer** — Reads actual code to extract patterns, conventions, and key abstractions. Generates project-specific rules, not generic framework advice.
2. **Config Auditor** — `/audit` scores any .claude/ setup for health, token cost, and issues
3. **Learning System** — `/learn` captures corrections so Claude doesn't repeat mistakes. Rules evolve over time.
4. **Token-optimized** — CLAUDE.md ≤100 lines, agents ≤30 lines. Everything fully rendered with real values.

## Modes

- **Greenfield** — New project from scratch (full interview → generation)
- **Existing project** — Analyze codebase → auto-detect stack → fill gaps → project-specific rules
- **Audit only** — Score and improve an existing .claude/ configuration
- **Learn** — Record corrections, analyze git history for mistake patterns

If the user asks to audit, skip to the Audit section. If they ask to analyze, use the Analyzer.
Otherwise, start the interview.

---

## Phase 1: Project Identity

Ask conversationally, 2-3 questions at a time. Don't dump all at once.

- **Project name** and one-line description
- **What does it do?** (SaaS, dashboard, marketplace, API, CLI, etc.)
- **Solo developer or team?**
- **Greenfield or adding Claude Code to an existing project?**
- **Architecture**: Monolith or microservices? (Recommend monolith unless they have a reason.)

> **Existing project**: Run the codebase analyzer first to detect stack AND extract patterns:
> ```bash
> python <skill-path>/scripts/analyze.py <project-root>
> ```
> This detects frontend, backend, ORM, auth, test framework, commands (test/lint/dev/build/migrate),
> git platform, CI/CD, hosting, monorepo structure, AND extracts project-specific patterns
> (error handling, validation, auth middleware, file organization, key abstractions).
> It also detects and migrates other AI configs (.cursorrules, copilot-instructions.md, .windsurfrules).
> Present findings, only ask about gaps the analyzer can't detect (preferences, team size).

Capture: `project_name`, `description`, `team`, `architecture`, `is_existing`

---

## Phase 2: Tech Stack

Skip questions they've already answered. For existing projects, auto-detect and confirm.

### Frontend
- **Framework**: Next.js, React+Vite, Vue 3/Nuxt, SvelteKit, or none
- **What's your test command?** (e.g., `npm run test`, `vitest`, `pytest`)
- **What's your lint command?** (e.g., `npm run lint`, `ruff check .`)

### Backend
- **Framework**: Node/Express, Node/Fastify, Python/FastAPI, Python/Django, Go, integrated (Next.js/SvelteKit), or none

### Database
- **Database + ORM**: PostgreSQL+Prisma, PostgreSQL+Drizzle, PostgreSQL+SQLAlchemy, MongoDB+Mongoose, Supabase, SQLite, or none
- **What's your migration command?** (e.g., `npx prisma migrate dev`, `alembic upgrade head`)
  Only ask ORM/migration for SQL databases (PostgreSQL, MySQL, SQLite). Skip for MongoDB, Supabase, DynamoDB.

### Auth
- **Provider**: Clerk, NextAuth/Auth.js, Supabase Auth, custom JWT, or none

### AI
- **Does the project use AI/LLMs?** (Enables AI-specific skills and `/prompt-test` command)

Read `reference/stacks.md` for the section matching each choice. Use it to inform CLAUDE.md
content, rules, and agent customizations.

Capture: `frontend`, `backend`, `database`, `orm`, `auth`, `ai`, `test_cmd`, `lint_cmd`, `migrate_cmd`, `dev_cmd`, `build_cmd`, `ci_cd`

---

## Phase 2.5: Event Systems & Messaging

Only ask if relevant — skip for simple CRUD apps. Infer from earlier answers when possible
(e.g., if the analyzer detected Kafka or BullMQ deps, confirm rather than ask from scratch).

- **Does this project use event-driven architecture or message queues?**
  Options: Kafka, BullMQ, RabbitMQ, Celery, NATS, AWS EventBridge/SQS, Redis Streams, or none
  Multiple selections allowed (e.g., Kafka for inter-service + BullMQ for background jobs).

- **Any event-driven patterns?** event-sourcing, CQRS, saga, outbox, or none
  Auto-suggest based on earlier answers (e.g., microservices → saga pattern likely).

- **Schema format for events?** Avro (with Schema Registry), Protobuf, JSON Schema, or none

- **Workflow orchestration?** Temporal, or none

When event systems are set, the scaffold generates:
- **Event consumer rules** — path-scoped rules for idempotency, DLQ, retry, schema validation
- **Reliability-auditor agent** — reviews event-driven code for failure handling
- **Technology-specific rules** — Temporal determinism constraints, Kafka consumer group conventions, etc.
- **Updated /build pipeline** — includes reliability audit step

Read `reference/stacks.md` → Event Brokers & Message Queues for conventions per system.

Capture: `event_systems`, `event_patterns`, `schema_format`, `workflow_orchestration`

---

## Phase 3: Domain & Compliance

Only ask if relevant — skip for generic apps. Infer from earlier answers when possible
(e.g., "accounting dashboard" → finance, "patient portal" → healthcare).

- **What domain is this project in?** finance, healthcare, HR, e-commerce, legal, education, or general
- **Any compliance requirements?** GDPR, SOX, HIPAA, PCI-DSS, or none
  Auto-suggest based on domain: finance → SOX, healthcare → HIPAA, e-commerce → PCI-DSS, EU users → GDPR.
  Multiple selections allowed (e.g., a UK fintech needs GDPR + SOX + PCI-DSS).

When domain ≠ general or compliance is set, the scaffold generates:
- **Domain auditor agents** — compliance-auditor, frontend-auditor (when frontend exists), architecture-auditor (finance/healthcare/legal)
- **Domain knowledge skills** — curated rule sets (e.g., `uk-accounting-rules`, `gdpr-rules`) that agents reference during review
- **Updated /build pipeline** — includes a domain audit step before code review

Capture: `domain`, `compliance`

---

## Phase 4: Infrastructure

- **Hosting**: Vercel, Railway, AWS, Fly.io, self-hosted, or undecided
- **Git platform**: GitHub, GitLab, Bitbucket
- **Conventional commits?** (yes/no)
- **CI/CD**: GitHub Actions, GitLab CI, or other

Capture: `hosting`, `git_platform`, `conventional_commits`, `ci_cd`

---

## Phase 5: Preferences

- **Do you want TDD support?** (Adds `/tdd` command and auto-test hooks)
- **Any MCP servers to configure?** (GitHub, Sentry, database, Figma)
  Read `reference/stacks.md` → MCP Servers section for available options and selection logic.
  Auto-suggest based on answers: GitHub platform → GitHub MCP, PostgreSQL → Postgres MCP, etc.

Summarize all decisions in a table (include MCP servers row). Get confirmation before generating.

---

## Generation

### Step 1: Run the Scaffold

```bash
python <skill-path>/scripts/scaffold.py \
  --project-name "{project_name}" \
  --frontend "{frontend}" \
  --backend "{backend}" \
  --database "{database}" \
  --auth "{auth}" \
  --hosting "{hosting}" \
  --git-platform "{git_platform}" \
  --orm "{orm}" \
  --ci-cd "{ci_cd}" \
  --output-dir "." \
  [--domain "{domain}"] [--compliance {compliance...}] \
  [--event-systems {event_systems...}] [--event-patterns {event_patterns...}] \
  [--schema-format "{schema_format}"] [--workflow-orchestration "{workflow_orchestration}"] \
  [--team] [--tdd] [--conventional-commits] [--ai] [--sentry] \
  [--context7] [--sequential-thinking] [--minimal-mcp] \
  [--lint-cmd "{lint_cmd}"] [--test-cmd "{test_cmd}"] \
  [--dev-cmd "{dev_cmd}"] [--build-cmd "{build_cmd}"] \
  [--migrate-cmd "{migrate_cmd}"] [--analyze] [--monorepo] \
  [--migrate-ai-configs] [--create-root]
```

This creates: directory structure, .claude/ skeleton, slash commands, skills, agents, rules, hooks,
MCP server config, .claudeignore, .env.example, handoff doc, and a token budget summary.

> **Important**: The scaffold creates parameterized agents, path-scoped rules, and all structural files.
> Steps 2-7 below are YOUR job as Claude — reading templates, filling real values, and writing
> CLAUDE.md and ARCHITECTURE.md. Customize agents and rules further with project-specific knowledge.

> **Existing projects**: Run with `--update` to merge new commands/skills/MCP into existing config:
> ```bash
> python <skill-path>/scripts/scaffold.py --project-name "{project_name}" ... --update --output-dir "."
> ```
> This adds missing files without touching existing ones. MCP servers are merged into settings.json.

### Step 2: Generate CLAUDE.md (≤100 lines)

> **Existing project with CLAUDE.md**: Do NOT overwrite. Read the existing CLAUDE.md first.
> Compare it against `templates/claude-md.md` and suggest additions/improvements. Only modify
> with the user's explicit permission. Show a diff of proposed changes.

For new projects: Read `templates/claude-md.md` for the template. Fill ALL values with real data
from the interview. No placeholders. The CLAUDE.md must contain the actual `test_cmd`, `lint_cmd`,
`dev_cmd`, etc.

Key sections: Tech Stack, Commands (real values), Architecture (2-3 sentences), Code Conventions
(stack-specific from `reference/stacks.md`), Mistakes to Avoid, Key Paths, Repository conventions.

### Step 3: Customize Agents (generated by scaffold)

The scaffold creates 5-6 parameterized agents with the project's stack, commands, and STOP conditions.

> **Existing project with agents**: List existing agents first. Only create agents that don't
> already exist. Never overwrite an existing agent file. If an existing agent could be improved,
> show the suggested changes and ask permission before modifying.

Review the generated agents in `.claude/agents/` and customize with:
- Project-specific review checks from `reference/stacks.md`
- Any additional context from the interview

Agents: architect, testing, reviewer, debugger, push (always) + security (when auth/payments/user data) + reliability-auditor (when event systems detected)

### Step 4: Customize Rules (generated by scaffold)

The scaffold creates path-scoped rules based on the frontend, backend, and ORM choices.

> **Existing project with rules**: List existing rules first. Only create rules for paths that
> don't already have coverage. Never overwrite existing rule files. If an existing rule is stale
> or could be improved, show the diff and ask permission.

Review the generated rules in `.claude/rules/` and add any project-specific conventions.
Reference `reference/stacks.md` "Rules target" sections for additional patterns.

### Step 5: Generate Hooks & Settings

> **Existing project with settings.json**: Read the existing file first. NEVER overwrite it.
> Merge new hooks alongside existing ones. If there are conflicts (e.g., user already has a
> PostToolUse hook and you want to add one), show both and ask which to keep or how to combine.

Based on interview:
- **All projects**: Block `git push --force` to main, secret detection
- **Has linter**: Auto-lint PostToolUse
- **Has tests + TDD**: Auto-test PostToolUse
- **Conventional commits**: Commit message validation
- **Stop hook**: Remind to run `/handoff`

### Step 6: Customize MCP & Settings

The scaffold generates initial `settings.json` with MCP servers. Now customize:
- **Add hooks** from the interview (auto-lint, auto-test, force-push block, conventional commits)
- **Verify MCP servers** — check env vars are documented in `.env.example`
- **Add any extra MCP servers** the user requested beyond auto-detected ones
- Reference `reference/stacks.md` → MCP Servers section for config details

### Step 7: Generate ARCHITECTURE.md

> **Existing project with ARCHITECTURE.md**: Do NOT overwrite. Read the existing file,
> compare against `templates/architecture.md`, suggest improvements. Only modify with permission.

For new projects: Read `templates/architecture.md`. Fill with real values. Include mermaid diagram
showing how frontend → backend → database → auth connect.

### Step 8: Run Audit

After generation, run the auditor to verify quality:

```bash
python <skill-path>/scripts/audit.py <project-root>
```

Show the health score and token estimate. Then act on the score:
- **Score < 70**: Fix all errors before presenting. Re-run audit to confirm.
- **Score 70-89**: Fix errors, flag warnings for user review.
- **Score ≥ 90**: Present as-is. Mention any warnings but don't block.

### Step 9: Present Results

1. Show the directory tree of generated files
2. Show CLAUDE.md content for review
3. Show audit score and token estimate
4. Ask if anything needs adjustment
5. Suggest next steps:
   - `/build <feature>` to start building with the full agent pipeline
   - `/analyze` to extract more patterns as code grows
   - `/learn <correction>` to teach Claude project-specific preferences

---

## Agent Orchestration

The `/build` command runs the full development pipeline with context passing through blueprints:

1. **Architect** designs → writes blueprint to `docs/blueprints/`
2. **Security** reviews the blueprint (when auth/payments involved)
3. **Implement** builds following the blueprint
4. **Testing** writes tests from the blueprint spec (not implementation)
5. **Domain Audit** reviews against domain/compliance rules (when domain is set)
6. **Reviewer** checks the full diff
7. **Push** creates the PR

Blueprints are the shared context. The template is in `docs/blueprints/.template.md`.

---

## Learning System

The `/learn` command captures corrections so Claude doesn't repeat mistakes:

```bash
# Explicit: record a correction
python <skill-path>/scripts/learn.py <project-root> --capture "Always use AppError, not generic Error"

# Git analysis: detect correction patterns from commit history
python <skill-path>/scripts/learn.py <project-root> --from-git

# Show all learned rules
python <skill-path>/scripts/learn.py <project-root> --show

# Forget a rule
python <skill-path>/scripts/learn.py <project-root> --forget "AppError"
```

Learned rules are stored in `.claude/rules/learned.md` and persist across sessions.
Over time, these rules become a distilled record of project-specific preferences.

---

## Evolve Mode (Feedback Loop)

The `/evolve` command closes the feedback loop between analyzer, learning system, and audit:

```
Analyze → Rules → Claude works → Developer corrects → /learn → /evolve → Updated rules
```

### How it works

1. **Check stale rules**: Finds project-*.md rules referencing deleted files or renamed identifiers
2. **Re-analyze with learned corrections**: Runs the analyzer with `--incorporate-learned --write-rules --force`
   - Re-scans the codebase for current patterns
   - Reads `.claude/learn-log.json` and matches corrections to pattern categories
   - Learned corrections appear in rules with `*(learned)*` markers
3. **Audit**: Verifies the updated config scores well
4. **Report**: Shows what changed

### Running evolve

```bash
# Via slash command
/evolve

# Or manually
python <skill-path>/scripts/analyze.py <project-root> --check-stale
python <skill-path>/scripts/analyze.py <project-root> --incorporate-learned --write-rules --force
python <skill-path>/scripts/audit.py <project-root>
```

The auditor also detects staleness automatically — if project-*.md rules reference files that no longer exist or if the analysis is >60 days old, it flags warnings suggesting `/evolve`.

---

## Audit Mode

The Config Auditor works on ANY .claude/ setup — not just Launchpad-generated ones.

### Running an Audit

```bash
python <skill-path>/scripts/audit.py <project-root> [--fix] [--json]
```

Read `reference/audit-rules.md` for full scoring rubric.

### What It Checks
- **Structure**: CLAUDE.md exists and is ≤100 lines, agents have valid frontmatter, settings.json valid
- **Token cost**: Line count × 4 tokens/line, broken down by component
- **Freshness**: Rules reference paths that exist, CLAUDE.md mentions installed commands, hooks call real scripts
- **Best practices**: No duplicate agents, no overlapping rules, no aggressive hooks, handoff exists

### Output Format
```
Claude Launchpad Audit Report
─────────────────────────────
Health Score: 82/100

Token Budget
  CLAUDE.md:      89 lines    ~356 tokens   ✓ within budget
  Agents (6):     168 lines   ~672 tokens   ✓ lean
  Rules (3):      57 lines    ~228 tokens   ✓ focused
  Settings:       42 lines    ~168 tokens   ✓ clean
  Total:          356 lines   ~1,424 tokens

Issues (2 warnings, 0 errors)
  ⚠ Rule frontend.md references src/pages/ but project uses src/app/
  ⚠ CLAUDE.md mentions "pytest" but package.json has Jest

Fixes
  1. Update frontend.md: change src/pages/ → src/app/
  2. Update CLAUDE.md line 47: change pytest → jest
```

### Fixing Issues

The auditor reports issues with specific fix suggestions. Apply fixes manually or ask Claude to help.
Each issue includes the exact file, line, and recommended change.

> Note: The `--fix` flag is reserved for future use. Currently all fixes require review.

---

## Important Principles

**≤100 lines for CLAUDE.md.** Move details to ARCHITECTURE.md or rules.

**≤30 lines per agent.** Agents are directives, not tutorials.

**Real values only.** Never generate `{placeholder}` — use actual commands, paths, and patterns.

**Stack knowledge matters.** Always read `reference/stacks.md` before generating.

**Respect existing work.** For existing projects, never overwrite without permission. Enhance, don't replace.

**Session continuity.** Every project gets handoff + `/handoff` command + `/status` command.

**Audit after generation.** Always run the auditor to verify what you produced.
