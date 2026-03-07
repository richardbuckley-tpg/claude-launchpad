# claude-bootstrap

The ultimate project setup skill for Claude Code. Conducts a structured interview about your project's architecture, tech stack, deployment, and AI needs — then scaffolds a complete, production-ready project optimized for agentic development.

Works for both **new projects** and **existing codebases**.

## What It Does

`claude-bootstrap` takes you from zero to a fully configured project in minutes:

1. **Phased Interview** — Asks smart questions about your project across 4 phases: identity & architecture, tech stack, infrastructure, and advanced features
2. **Scaffolds Everything** — Creates the complete directory structure with a bundled Python script
3. **Generates Claude Code Config** — Tailored CLAUDE.md, 8 specialized subagents, path-scoped rules, hooks, slash commands, MCP configuration, session handoff, and skills
4. **Architecture Docs** — ARCHITECTURE.md with decision records, mermaid diagrams, and component descriptions
5. **Existing Project Mode** — Auto-detects your stack and generates only what's missing

## What Gets Generated

```
your-project/
├── CLAUDE.md                   # Tailored project context (under 200 lines)
├── ARCHITECTURE.md             # Decisions, diagrams, data flows
├── .mcp.json                   # MCP server configuration for integrations
├── .claude/
│   ├── agents/                 # 8 specialized agents (CTO, Security, Testing, etc.)
│   ├── rules/                  # Path-scoped rules for frontend, backend, DB
│   ├── commands/               # Slash commands (/status, /handoff, /deploy, etc.)
│   ├── skills/                 # /deploy, /db-migrate, etc.
│   ├── handoff.md              # Session context preservation
│   ├── settings.json           # Hooks, permissions, tool config
│   └── bootstrap-config.json   # Your project decisions (for reference)
├── .claudeignore               # Stack-specific exclusions
├── .env.example                # All needed env vars, documented
├── src/                        # Stack-appropriate directory structure
└── ...
```

## 8 Specialized Agents

Every project gets a full agent suite, customized for your stack:

| Agent | Purpose | Model |
|-------|---------|-------|
| **CTO** | Architects solutions from feature requests, produces technical blueprints | Opus |
| **Security** | Reviews OWASP Top 10, auth flows, data exposure, injection risks | Sonnet |
| **Work Breakdown** | Decomposes PRDs into multi-phase implementation plans | Sonnet |
| **Testing** | Creates unit/integration/E2E tests from specs (worktree isolation) | Sonnet |
| **DevOps** | Infrastructure, Docker, CI/CD pipelines, environment management | Sonnet |
| **Push** | Git workflow: branches, conventional commits, PRs | Haiku |
| **Debugger** | Systematic diagnosis: reproduce → isolate → fix → regression test | Sonnet |
| **Reviewer** | Code review: correctness, performance, maintainability, test coverage | Sonnet |

## Key Features

### Slash Commands
- `/status` — Quick project health check
- `/handoff` — Save session context for next time
- `/new-feature` — Start a feature with proper branching
- `/fix-bug` — Systematic debugging methodology
- `/deploy` — Pre-flight checks + deployment (customized per platform)
- `/db-migrate` — ORM-specific migration workflow
- `/tdd` — Start a TDD red-green-refactor cycle (if TDD enabled)
- `/pipeline` — Full feature pipeline: CTO → Work Breakdown → Security → Implement → Review → Push (team projects)

### Session Handoff
Never lose context between sessions. The handoff system tracks what's working, what's in progress, architecture decisions, and next steps.

### MCP Integration
Auto-generates `.mcp.json` for your chosen integrations: GitHub, PostgreSQL, Supabase, Sentry, Figma, and more.

### Smart Hooks
Auto-generated based on your stack:
- Auto-lint on file save
- Auto-run related tests (TDD mode)
- Block dangerous commands (force push, production DB access)
- Enforce conventional commits
- Prevent secrets in code
- Commit size warnings (soft limit: 10 files, hard limit: 25 files)
- Branch naming enforcement
- Secret pattern detection in code files
- Auto file permissions on .env, .pem, .key files

### Auto-Iterative TDD Loops
When TDD is enabled, Claude follows strict red-green-refactor cycles with auto-test-on-save hooks, coverage gates, and worktree isolation for genuine test-driven development.

### Multi-Agent Coordination
Structured agent pipelines for complex features with artifact-based handoffs between agents. Includes lock file patterns for running multiple Claude instances in parallel (Claude Squad).

### Commit Size Management
Automatic monitoring of commit size with configurable soft/hard limits. Enforces atomic commits that are easy to review, revert, and bisect.

### Monorepo Support
Turborepo, Nx, and pnpm workspaces with per-package CLAUDE.md files and import boundary rules.

### Existing Project Mode
Auto-detects your stack with a dedicated analysis script, validates existing configuration, and generates only what's missing — never overwrites without permission.

### Comprehensive .claudeignore
Stack-specific ignore patterns covering dependencies, build outputs, caches, environment secrets, IDE files, test outputs, logs, generated code, lock files, Docker volumes, and large media files.

## Supported Stacks

**Frontend**: Next.js (App Router), React + Vite, Vue 3 / Nuxt, SvelteKit

**Backend**: Node.js/Express, Node.js/Fastify, Python/FastAPI, Python/Django, Go

**Databases**: PostgreSQL, MongoDB, Supabase, DynamoDB, SQLite, MySQL

**Storage**: AWS S3, Cloudflare R2, MinIO, Supabase Storage, Uploadthing

**Auth**: Clerk, NextAuth/Auth.js, Custom JWT

**Deployment**: Vercel, Railway, AWS, Azure

**Monorepo**: Turborepo, Nx, pnpm workspaces

**Plus**: AI/LLM integration patterns, multi-tenant support, microservices scaffolding, MCP configuration

## Installation

### Option 1: Copy to your Claude Code skills directory

```bash
# Clone this repo
git clone https://github.com/YOUR_USERNAME/claude-bootstrap.git

# Copy to your global skills
cp -r claude-bootstrap ~/.claude/skills/

# Or to a specific project
cp -r claude-bootstrap your-project/.claude/skills/
```

### Option 2: Use as a .skill package

If packaged as a `.skill` file, install it through Claude Code's skill installation flow.

## Usage

Once installed, just tell Claude Code you want to start a new project:

```
> I want to build a SaaS invoicing platform
> bootstrap a new project
> set up a new Next.js app with Clerk and Supabase
> create a project for me
> add Claude Code to my existing project
```

Claude will automatically invoke the skill and guide you through the interview.

## How the Interview Works

**Phase 1: Project Identity** — name, description, greenfield vs existing, monolith vs microservices, single vs multi-tenant, monorepo

**Phase 2: Tech Stack** — frontend, backend, database, ORM, auth, testing framework, object storage

**Phase 3: Infrastructure** — hosting, environments, source control, CI/CD, Docker, branch strategy

**Phase 4: Advanced** — AI/LLM integration, payments, email, monitoring (Sentry), design tools (Figma), mobile, external APIs

After each phase, Claude summarizes your choices and confirms before moving on. At the end, everything generates at once with full verification.

## Scripts & Validation

```bash
# Analyze an existing project's stack and Claude config
python scripts/analyze_project.py /path/to/project

# Full project health check (agents, commands, handoff, MCP, etc.)
python scripts/healthcheck.py /path/to/project

# Validate CLAUDE.md against best practices
python scripts/validate_claude_md.py /path/to/CLAUDE.md

# Validate agent definitions
python scripts/validate_agents.py /path/to/.claude/agents/

# Generate architecture diagram from config
python scripts/generate_diagram.py /path/to/.claude/bootstrap-config.json
```

## Contributing

PRs welcome! Areas that would benefit from community contributions:

- Additional stack references (Ruby/Rails, Rust, Java/Spring, .NET)
- More deployment targets (Fly.io, DigitalOcean, GCP)
- Mobile frameworks (React Native, Flutter, Expo)
- Additional auth providers (Firebase Auth, Lucia, Supabase Auth)
- More MCP server integrations
- Improved scaffolding patterns based on real-world usage

## License

MIT
