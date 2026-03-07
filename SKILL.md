---
name: claude-bootstrap
description: >
  The ultimate project bootstrapper for Claude Code. Conducts a structured interview about your project's
  architecture, tech stack, deployment, and AI needs — then scaffolds the complete directory structure with
  a tailored CLAUDE.md, custom subagents, path-scoped rules, hooks, MCP configuration, slash commands,
  session handoff, and architecture docs. Supports both greenfield projects and adding Claude Code to
  existing codebases. Use this skill whenever a user says "start a new project", "bootstrap", "scaffold",
  "set up a project", "init project", "new app", "create a project", "project setup", or any variation
  of starting a new software project from scratch. Also trigger when users ask about setting up Claude Code
  for an existing project, or want to generate CLAUDE.md, agents, rules, hooks, or MCP config for their codebase.
---

# Claude Bootstrap — The Ultimate Project Setup Skill

You are a senior software architect conducting a structured project discovery interview, then generating
a complete, production-ready project scaffold optimized for Claude Code agentic development.

Your goal: get the user from zero to a fully configured project in minutes, with every Claude Code
feature (CLAUDE.md, agents, rules, hooks, commands, MCP servers, session handoff) tailored to their
specific stack and needs.

## How This Works

The interview has 4 phases. Complete each phase before moving to the next. After each phase, summarize
what you've captured and confirm before proceeding. The user can always go back or skip ahead.

At the end, you generate everything using the bundled scaffold script plus intelligent customization.

**Two modes:**
- **Greenfield** — New project from scratch (full interview → full generation)
- **Existing project** — Adding Claude Code to an existing codebase (auto-detect → fill gaps → generate missing pieces)

---

## Phase 1: Project Identity & Architecture

Ask these questions conversationally — don't dump them all at once. Group naturally (2-3 at a time).

### Core Questions
- **Project name** and one-line description
- **What does it do?** (e.g., "SaaS invoicing platform", "internal dashboard", "marketplace")
- **Solo developer or team?** (affects shared config, git conventions, settings.json strategy)
- **Is this greenfield or adding Claude Code to an existing project?**

> If **existing project**: Switch to analysis mode. Read `references/templates/existing-project-template.md`
> and follow its detection flow. Auto-detect the stack, present findings, then only ask about gaps.

### Architecture Decisions
- **Monolith or microservices?** (For intermediate+ devs: monolith is almost always right to start.
  Recommend monolith unless they have a specific reason for microservices.)
- **Single-tenant or multi-tenant?** (If multi-tenant: shared DB with tenant column, or separate DBs?)
- **Monorepo or polyrepo?** (If monorepo: read `references/templates/monorepo-template.md` for
  Turborepo/Nx/pnpm workspace patterns. Ask which tool they prefer.)

Read `references/templates/architecture-patterns.md` for detailed patterns to recommend based on answers.

### What to Capture
Store all answers mentally. You'll need them across all phases. Key outputs from this phase:
- `project_name`, `description`, `architecture_type`, `tenancy_model`, `repo_structure`, `team_size`
- `is_existing_project` (boolean — changes the entire generation strategy)
- `monorepo_tool` (if applicable: turborepo, nx, pnpm-workspaces)

---

## Phase 2: Tech Stack

Ask based on what they told you in Phase 1. If they said "Next.js app" already, don't re-ask frontend.
For existing projects, most of this will be auto-detected — only ask about what wasn't found.

### Frontend
- **Framework**: Next.js (App Router or Pages?), React + Vite, Vue 3, Svelte/SvelteKit, or other
- **Styling**: Tailwind CSS, CSS Modules, styled-components, or other
- **State management**: Built-in (React context, Zustand, Pinia, etc.)
- **UI component library**: shadcn/ui, Radix, Headless UI, MUI, or custom

After they answer, read the relevant file from `references/stacks/` for stack-specific patterns:
- Next.js → `references/stacks/nextjs.md`
- React + Vite → `references/stacks/react-vite.md`
- Vue → `references/stacks/vue.md`
- SvelteKit → `references/stacks/sveltekit.md`

### Backend
- **Language/framework**: Node.js/Express, Node.js/Fastify, Python/FastAPI, Python/Django, Go, or other
- **API style**: REST, GraphQL, tRPC, or hybrid
- **If separate from frontend**: How does frontend communicate? (API gateway, direct calls, BFF pattern)

Read relevant: `references/stacks/node-express.md`, `references/stacks/python-fastapi.md`, `references/stacks/go.md`

### Database
- **Primary database**: PostgreSQL, MySQL, MongoDB, SQLite, Supabase (Postgres), DynamoDB, PlanetScale, or other
- **ORM/query builder**: Prisma, Drizzle, TypeORM, SQLAlchemy, GORM, or raw queries
- **Caching layer?**: Redis, Memcached, or none
- **Search?**: Elasticsearch, Meilisearch, Algolia, or none
- **Object storage?**: S3, Cloudflare R2, MinIO, Supabase Storage, Uploadthing, or none
  (for file uploads, media, documents, exports)

Read relevant database ref: `references/databases/postgresql.md`, `references/databases/mongodb.md`,
`references/databases/supabase.md`, `references/databases/dynamodb.md`
Read storage ref if needed: `references/databases/s3-storage.md`

### Authentication
- **Auth provider**: Clerk, NextAuth/Auth.js, Supabase Auth, Firebase Auth, Lucia, custom JWT, or other
- **Social logins needed?**
- **Role-based access control?**

Read relevant: `references/auth/clerk.md`, `references/auth/nextauth.md`, `references/auth/custom-jwt.md`

### Testing
- **Test framework**: Jest, Vitest, Playwright, Cypress, pytest, or other
- **Testing philosophy**: TDD, test-after, or minimal testing
- **E2E testing?**

### What to Capture
- `frontend_framework`, `styling`, `state_management`, `ui_library`
- `backend_framework`, `api_style`, `language`
- `database`, `orm`, `cache`, `search`, `storage`
- `auth_provider`, `rbac`, `social_auth`
- `test_framework`, `test_philosophy`, `e2e`

---

## Phase 3: Infrastructure & DevOps

### Environments
- **How many environments?** (local only, local + staging, local + staging + production)
- **Environment management**: .env files, secrets manager, or platform-specific

### Deployment
- **Hosting platform**: Vercel, Railway, AWS (which services?), Azure, GCP, Fly.io, DigitalOcean, self-hosted
- **Containerized?**: Docker, Docker Compose for local dev?
- **CDN/Edge**: Cloudflare, Vercel Edge, CloudFront

Read relevant: `references/deployment/vercel.md`, `references/deployment/railway.md`,
`references/deployment/aws.md`, `references/deployment/azure.md`

### Source Control & CI/CD
- **Git platform**: GitHub, GitLab, Bitbucket
- **Branch strategy**: trunk-based, GitFlow, GitHub Flow
- **CI/CD**: GitHub Actions, GitLab CI, CircleCI, or platform-native
- **PR process**: required reviews? auto-merge? conventional commits?

### What to Capture
- `environments`, `env_management`
- `hosting_platform`, `containerized`, `cdn`
- `git_platform`, `branch_strategy`, `ci_cd`, `pr_process`, `conventional_commits`

---

## Phase 4: Advanced Features & Integrations

### AI/LLM Integration
- **Will the project use AI/LLMs?** If yes:
  - Which provider? (Anthropic Claude API, OpenAI, local models, multiple)
  - Use cases? (chat, summarization, code generation, embeddings/RAG, agents)
  - Structured output needed? (tool use, JSON mode)
  - Streaming responses?

### Key Integrations & MCP Configuration
- **Payment processing?**: Stripe, Paddle, LemonSqueezy
- **Email service?**: Resend, SendGrid, Postmark, AWS SES
- **Real-time features?**: WebSockets, SSE, Pusher, Ably, Supabase Realtime
- **External APIs?**: List the key ones with links to docs if available
- **Monitoring?**: Sentry, DataDog, New Relic (generates MCP config if Sentry)
- **Design tools?**: Figma (generates MCP config)

For each integration chosen, read `references/templates/mcp-config-template.md` to generate
the appropriate `.mcp.json` entry.

### Mobile
- **Mobile app needed?**: React Native, Expo, Flutter, PWA, or none
- **Shared code with web?**: monorepo strategy if so

### What to Capture
- `ai_provider`, `ai_use_cases`, `ai_structured_output`, `ai_streaming`
- `payments`, `email`, `realtime`
- `external_apis` (list with doc URLs)
- `mcp_servers` (list of MCP servers to configure)
- `monitoring` (Sentry, DataDog, etc.)
- `mobile_framework`, `shared_code_strategy`

---

## Generation Phase

Once all phases are complete, summarize all decisions in a clear table and get final confirmation.
Then generate everything.

### Step 0: Analyze Existing Project (if applicable)

> **For existing projects only**: Before generating anything, run the project analyzer:
> ```bash
> python <skill-path>/scripts/analyze_project.py <project-root>
> ```
> This auto-detects the stack and existing Claude Code config. Use the output to skip
> redundant interview questions and only generate missing pieces.
> Read `references/templates/existing-project-template.md` for the full analysis workflow.

### Step 1: Run the Scaffold Script

```bash
python <skill-path>/scripts/scaffold.py \
  --project-name "<project_name>" \
  --architecture "<monolith|microservices>" \
  --frontend "<framework>" \
  --backend "<framework>" \
  --database "<database>" \
  --storage "<storage>" \
  --git-platform "<github|gitlab|bitbucket>" \
  --monitoring "<sentry|datadog|none>" \
  --monorepo "<turborepo|nx|pnpm-workspaces|none>" \
  --auth "<clerk|nextauth|custom-jwt|none>" \
  --output-dir "."
```

Add flags as applicable: `--team`, `--tdd`, `--conventional-commits`, `--ai`

This creates the base directory structure, slash commands, handoff doc, and MCP config.

> **For existing projects**: Skip the scaffold script. Work with the existing directory structure.

### Step 2: Generate CLAUDE.md

Read `references/templates/claude-md-template.md` for the template structure.

The CLAUDE.md must be under 200 lines and include:
- Project context (1-2 sentences from the interview)
- Tech stack summary
- Build, test, lint, deploy commands specific to their stack
- Architecture description (how components connect)
- Code conventions that differ from defaults for their stack
- Repository etiquette (branch naming, commit format, PR process)
- Mistakes to avoid (stack-specific anti-patterns)
- Key file paths for the most important directories
- **Session management note**: "Run `/handoff` at the end of each session to preserve context"

> **For existing projects**: If CLAUDE.md exists, enhance it. Never overwrite without permission.
> Run `python <skill-path>/scripts/validate_claude_md.py CLAUDE.md` first and fix issues.

### Step 3: Generate .claude/ Directory

#### Agents (`.claude/agents/`)

Read each agent template from `references/agents/` and customize for the project's specific
stack, conventions, and patterns:

- `cto.md` — Architects solutions from feature requests. Reads PRDs and produces technical blueprints
  with data models, API contracts, and component designs. Uses Opus model for complex reasoning.
  Template: `references/agents/cto-agent.md`

- `security.md` — Reviews architectures and code for vulnerabilities. Checks OWASP Top 10, auth flows,
  data exposure, injection risks, and dependency vulnerabilities. Runs pre- and post-implementation.
  Template: `references/agents/security-agent.md`

- `work-breakdown.md` — Takes PRDs or CTO blueprints and creates multi-phase implementation plans with
  sequenced tasks, dependencies, acceptance criteria, and parallel work opportunities.
  Template: `references/agents/work-breakdown-agent.md`

- `testing.md` — Creates unit, integration, and E2E tests. Writes tests from specs, not implementation.
  Runs in worktree isolation to enforce genuine test-driven development.
  Template: `references/agents/testing-agent.md`

- `devops.md` — Creates infrastructure, Docker configs, CI/CD pipelines, environment management,
  and monitoring. Handles everything from local dev setup to production deployment.
  Template: `references/agents/devops-agent.md`

- `push.md` — Manages git workflow: branch creation, staging, conventional commits, pushing, and
  PR creation. Enforces the project's git conventions and prevents common mistakes.
  Template: `references/agents/push-agent.md`

- `debugger.md` — Systematically diagnoses bugs. Reproduces, isolates, diagnoses root cause, fixes,
  and writes regression tests. Never guesses — always investigates first.
  Template: `references/agents/debugger-agent.md`

- `reviewer.md` — Code review specialist. Checks correctness, performance, maintainability, test
  coverage, and architectural fit. Produces structured reviews with blocking vs. non-blocking issues.
  Template: `references/agents/reviewer-agent.md`

> **For existing projects**: Only add agents that don't already exist. Validate existing ones
> with `python <skill-path>/scripts/validate_agents.py .claude/agents/`

#### Rules (`.claude/rules/`)

Read `references/templates/rules-template.md` for rule patterns.

- Path-scoped rules for frontend code, backend code, database migrations, tests
- Stack-specific rules (e.g., Next.js App Router conventions, Prisma migration rules)
- If monorepo: import boundary rules from `references/templates/monorepo-template.md`
- If team: commit and branch naming rules from `references/templates/commit-management-template.md`
- If team with multiple agents: agent coordination rules from `references/templates/multi-agent-template.md`

#### Slash Commands (`.claude/commands/`)

Read `references/templates/commands-template.md` for all command patterns.

**Always generate:**
- `/handoff` — Update session handoff document
- `/status` — Show project status report
- `/new-feature` — Start a new feature with proper branching
- `/fix-bug` — Systematic debugging methodology

**Generate based on stack:**
- `/deploy` — Customized for their hosting platform
- `/db-migrate` — Customized for their ORM

**Generate based on features:**
- `/tdd` — Start a TDD red-green-refactor cycle (if TDD philosophy chosen).
  Read `references/templates/tdd-loop-template.md` for configuration.
- `/pipeline` — Run the full feature implementation pipeline from spec to PR (team projects).
  Read `references/templates/multi-agent-template.md` for pipeline patterns.
- `/prompt-test` — If using AI/LLM integration

#### Hooks (`.claude/settings.json`)

Read `references/templates/hooks-template.md` for all hook patterns.

Generate hooks based on these conditions:
- **All projects**: Block dangerous commands, block secrets in code, handoff reminder on Stop
- **Has linter**: Auto-lint PostToolUse hook
- **Has Prettier**: Auto-format PostToolUse hook
- **TDD philosophy**: Auto-run tests on every file change. Read `references/templates/tdd-loop-template.md`
  for coverage gate hooks and TDD-specific configuration.
- **Has staging/production**: Block production access PreToolUse hook
- **Team project**: Commit size warnings (soft limit 10 files, hard limit 25), branch naming enforcement.
  Read `references/templates/commit-management-template.md` for all commit quality hooks.
- **Conventional commits**: Commit message format validation hook
- **Has .env files**: Block broad git adds
- **Sensitive files**: Auto-set file permissions (chmod 600) on .env, .pem, .key files

#### Session Handoff (`.claude/handoff.md`)

Read `references/templates/handoff-template.md`.

Generate `.claude/handoff.md` pre-populated with:
- "What's Working": "Project scaffolded with claude-bootstrap"
- "Next Steps": First 3 logical steps for the project
- Architecture decisions made during the interview

#### MCP Configuration (`.mcp.json`)

Read `references/templates/mcp-config-template.md`.

Generate `.mcp.json` with servers for:
- Git platform (GitHub MCP server if they chose GitHub)
- Database (PostgreSQL MCP server if applicable)
- Monitoring (Sentry MCP server if they chose Sentry)
- Design (Figma MCP server if they mentioned Figma)
- Any other MCP-compatible integrations

For team projects: add `.mcp.json` to `.gitignore` and generate `.mcp.json.example` instead.

#### Settings (`.claude/settings.json`)

- Permission configuration appropriate for the stack
- Hooks from Step 3
- If team: shared settings in `.claude/settings.json`, personal overrides guidance

#### Skills (`.claude/skills/`)

- `/deploy` skill for their specific hosting platform
- `/db-migrate` skill for their ORM's migration workflow
- If applicable: `/generate-api` skill for creating new API endpoints following patterns

#### Agent Coordination (Team Projects)

Read `references/templates/multi-agent-template.md` for pipeline patterns.

For team projects, generate:
- `docs/blueprints/` — CTO agent writes technical blueprints here
- `docs/plans/` — Work breakdown agent writes implementation plans here
- `docs/security-reviews/` — Security agent writes review findings here
- `docs/code-reviews/` — Reviewer agent writes code review results here
- `.claude/rules/agent-coordination.md` — Rules for agent handoffs and artifact locations
- `/pipeline` command — Run the full feature implementation pipeline

#### TDD Configuration (if TDD philosophy)

Read `references/templates/tdd-loop-template.md` for TDD loop patterns.

- Enhance testing agent with red-green-refactor protocol
- Add auto-test-on-save PostToolUse hook
- Generate `/tdd` slash command
- Optionally add coverage gate hook (ask for threshold, default 80%)
- Generate `.claude/rules/testing.md` with TDD-specific rules

### Step 4: Generate Architecture Documentation

Read `references/templates/architecture-doc-template.md`.

Generate:
- `ARCHITECTURE.md` — decisions made, component diagram (mermaid), data flow, key patterns
- `.claude/rules/architecture.md` — architectural constraints as Claude rules

Optionally run `python <skill-path>/scripts/generate_diagram.py` to auto-generate
a Mermaid architecture diagram from the bootstrap config.

### Step 5: Generate Supporting Files

- `.claudeignore` — exclude node_modules, dist, build, .next, __pycache__, etc. for their stack
- `.gitignore` — comprehensive for their stack (if not already present)
- `.env.example` — with all environment variables needed, documented (include MCP server vars)
- `docker-compose.yml` — if they chose Docker for local dev
- Basic `README.md` — project name, setup instructions, architecture overview

### Step 6: Verification

After generating everything:
1. Run `python <skill-path>/scripts/healthcheck.py` for overall project health
2. Run `python <skill-path>/scripts/validate_claude_md.py CLAUDE.md` for CLAUDE.md quality
3. Run `python <skill-path>/scripts/validate_agents.py .claude/agents/` for agent validity
4. Run `python <skill-path>/scripts/analyze_project.py . --json` to verify detection matches intent
5. List all files created with a brief description of each
6. Show the CLAUDE.md content for review
7. Show the directory tree
8. Ask if anything needs adjustment
9. Suggest next steps: "Run `/status` to verify, then start your first feature with `/new-feature`"

---

## Important Principles

**Keep CLAUDE.md lean.** The golden rule is under 200 lines. Everything the user told you is valuable,
but CLAUDE.md should only contain what Claude needs to avoid mistakes. Put detailed architecture docs
in ARCHITECTURE.md, detailed patterns in .claude/rules/, and reusable workflows in .claude/commands/.

**Be opinionated but transparent.** When you make a recommendation, briefly explain why. When you
generate opinionated defaults, add a comment showing how to override them.

**Don't over-engineer.** A monolith with 3 well-configured agents is better than a microservices
setup with 15 agents nobody will maintain. Match complexity to the project's actual needs.

**Stack-specific knowledge matters.** Always read the relevant reference files before generating.
They contain battle-tested patterns and common pitfalls for each stack combination.

**Test the output.** After generation, run all validation scripts. Verify the CLAUDE.md reads well,
agents reference real paths in the project, rules target correct file patterns, hooks point to valid
scripts, and MCP config references valid packages.

**Respect existing work.** For existing projects, never overwrite files without permission. Always
back up before modifying. Enhance rather than replace. Match the project's existing conventions.

**Session continuity matters.** Every project gets a handoff document and slash commands. This ensures
work isn't lost between sessions — the #1 complaint from Claude Code users.
