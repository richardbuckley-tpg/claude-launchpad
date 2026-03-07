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

**Three things make this different:**
1. **Config Auditor** — `/audit` scores any .claude/ setup (yours, ECC, hand-crafted) for health, token cost, and issues
2. **Token-optimized** — CLAUDE.md ≤100 lines, agents ≤30 lines, total config ~2,800 tokens (vs ~7,200 for ECC)
3. **Fully rendered** — Generated files contain real commands, real paths, real patterns. No `{placeholder}` stubs.

## Modes

- **Greenfield** — New project from scratch (full interview → generation)
- **Existing project** — Adding Claude Code to existing codebase (auto-detect → fill gaps)
- **Audit only** — Score and improve an existing .claude/ configuration

If the user asks to audit, skip to the Audit section. Otherwise, start the interview.

---

## Phase 1: Project Identity

Ask conversationally, 2-3 questions at a time. Don't dump all at once.

- **Project name** and one-line description
- **What does it do?** (SaaS, dashboard, marketplace, API, CLI, etc.)
- **Solo developer or team?**
- **Greenfield or adding Claude Code to an existing project?**
- **Architecture**: Monolith or microservices? (Recommend monolith unless they have a reason.)

> **Existing project**: Auto-detect the stack by checking for `package.json`, `requirements.txt`,
> `go.mod`, `Cargo.toml`, `.claude/` directory. Present findings, only ask about gaps.
> If multiple frameworks detected (e.g., Next.js + Express in same package.json), list findings
> and ask user to confirm the primary frontend/backend split.

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

Capture: `frontend`, `backend`, `database`, `orm`, `auth`, `ai`, `test_cmd`, `lint_cmd`, `migrate_cmd`, `dev_cmd`, `build_cmd`

---

## Phase 3: Infrastructure

- **Hosting**: Vercel, Railway, AWS, Fly.io, self-hosted, or undecided
- **Git platform**: GitHub, GitLab, Bitbucket
- **Conventional commits?** (yes/no)
- **CI/CD**: GitHub Actions, GitLab CI, or other

Capture: `hosting`, `git_platform`, `conventional_commits`, `ci_cd`

---

## Phase 4: Preferences

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
  --output-dir "." \
  [--team] [--tdd] [--conventional-commits] [--ai] [--sentry] \
  [--lint-cmd "{lint_cmd}"] [--test-cmd "{test_cmd}"] [--create-root]
```

This creates: directory structure, .claude/ skeleton, slash commands, skills, hooks, MCP server config,
.claudeignore, .env.example, handoff doc.

> **Important**: The scaffold creates the structural files (commands, skills, hooks, MCP, supporting files).
> Steps 2-7 below are YOUR job as Claude — reading templates, filling real values, and writing
> agents, rules, CLAUDE.md, and ARCHITECTURE.md. The scaffold does NOT generate these content files.

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

### Step 3: Generate Agents (6 × ≤30 lines each)

> **Existing project with agents**: List existing agents first. Only create agents that don't
> already exist. Never overwrite an existing agent file. If an existing agent could be improved,
> show the suggested changes and ask permission before modifying.

Read `reference/agents.md` for all 6 templates. Customize each with:
- The project's actual stack names and paths
- Stack-specific review checks (from `reference/stacks.md`)
- The project's real test/lint/build commands

Agents: architect, testing, reviewer, debugger, push (always) + security (when auth/payments/user data involved)

### Step 4: Generate Rules (≤20 lines each)

> **Existing project with rules**: List existing rules first. Only create rules for paths that
> don't already have coverage. Never overwrite existing rule files. If an existing rule is stale
> or could be improved, show the diff and ask permission.

Create path-scoped rules based on the stack. Reference `reference/stacks.md` "Rules target" sections.
Typical rules:
- `frontend.md` — Component/page conventions for the chosen framework
- `backend.md` — API endpoint conventions (validation, error handling, auth)
- `database.md` — Migration rules, schema conventions for the chosen ORM

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
5. Suggest: "Run `/status` to verify, then `/new-feature` to start building"

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
