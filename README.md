# Claude Launchpad

A Claude Code skill that bootstraps complete project configurations through a structured interview. Generates agents, rules, skills, commands, hooks, MCP config, CI/CD, and more — all with real values from your answers, not placeholders.

## Install

Clone into your Claude Code skills directory:

```bash
# Global (available to all projects)
git clone https://github.com/richardbuckley-tpg/claude-launchpad.git ~/.claude/skills/claude-launchpad

# Per-project
git clone https://github.com/richardbuckley-tpg/claude-launchpad.git .claude/skills/claude-launchpad
```

Requires Python 3.10+ (stdlib only, no dependencies).

## Getting Started

### Bootstrap a New Project

Open Claude Code and say any of these:

- **"Bootstrap a new project"**
- **"Set up Claude Code for my project"**
- **"Scaffold my app"**

Launchpad conducts a 4-phase interview about your stack, then generates everything:

1. **Project Identity** — name, description, architecture
2. **Tech Stack** — frontend, backend, database, ORM, auth
3. **Infrastructure** — hosting, git platform, CI/CD
4. **Preferences** — TDD, MCP servers, conventional commits

After the interview, it scaffolds your `.claude/` directory and runs an audit to verify quality.

### Use a Preset (Skip the Interview)

If you know your stack, use a preset for instant scaffolding:

```
"Bootstrap with the nextjs-fullstack preset"
```

Available presets:
- `nextjs-fullstack` — Next.js + Prisma + Clerk + Vercel
- `nextjs-supabase` — Next.js + Supabase Auth + Vercel
- `react-express` — React + Express + Prisma + Railway
- `fastapi` — FastAPI + SQLAlchemy + Railway
- `go-api` — Go API + PostgreSQL + AWS
- `sveltekit-fullstack` — SvelteKit + Drizzle + Vercel
- `rails` — Ruby on Rails + ActiveRecord + Railway

### Add to an Existing Project

Say **"Set up Claude Code for this project"** in an existing codebase.

Launchpad auto-detects your stack from `package.json`, `requirements.txt`, `go.mod`, etc., then fills gaps. Use `--update` mode to merge new config into existing `.claude/` files without overwriting anything.

### Audit Any Config

Say **"Audit my Claude Code config"** or run `/audit`

The auditor works on any `.claude/` setup — not just Launchpad-generated ones. It checks:
- **Structure** (30pts) — CLAUDE.md exists and is right-sized, agents have frontmatter, settings valid
- **Efficiency** (30pts) — token budgets per component, context window % estimate
- **Freshness** (20pts) — rules reference paths that exist, commands are installed
- **Practices** (20pts) — no duplicate agents, handoff exists, no hardcoded secrets

```
Claude Launchpad Audit Report
────────────────────────────────────────
Health Score: 92/100
  Structure: 30/30  Efficiency: 27/30  Freshness: 20/20  Practices: 15/20

Token Budget
  CLAUDE.md              62 lines    ~248 tokens  ✓
  Agents (5)            140 lines    ~560 tokens  ✓
  Rules (3)              45 lines    ~180 tokens  ✓
  ───────────────────────────────────────────────────────
  Total                 247 lines    ~988 tokens
```

Use `--recommend` for improvement suggestions, `--fix` to auto-fix safe issues.

## What Gets Generated

```
your-project/
├── CLAUDE.md                        # ≤100 lines, discoverability-first
├── ARCHITECTURE.md                  # Design decisions + data flow
├── .claude/
│   ├── agents/                      # 5-6 parameterized agents
│   │   ├── architect.md
│   │   ├── testing.md
│   │   ├── reviewer.md
│   │   ├── debugger.md
│   │   ├── push.md
│   │   └── security.md             # (when auth/AI involved)
│   ├── rules/                       # Path-scoped, stack-specific
│   │   ├── frontend.md              # (globs: src/app/**/*.tsx)
│   │   ├── backend.md
│   │   └── database.md
│   ├── commands/                    # 5-7 slash commands
│   │   ├── status.md
│   │   ├── handoff.md
│   │   ├── new-feature.md
│   │   ├── fix-bug.md
│   │   ├── audit.md
│   │   ├── tdd.md                   # (when --tdd)
│   │   └── pipeline.md             # (when --team)
│   ├── skills/                      # 8-10 stack-specific skills
│   ├── settings.json                # Hooks + MCP servers
│   ├── handoff.md                   # Session context preservation
│   └── launchpad-config.json        # Interview answers + version
├── .github/                         # (when --ci-cd github-actions)
│   ├── workflows/ci.yml
│   └── pull_request_template.md
├── docs/
│   ├── first-feature.md             # Step-by-step getting started guide
│   └── blueprints/                  # Architecture blueprints
├── .claudeignore
└── .env.example
```

## Key Features

### Token-Optimized
Strict line limits keep your config lean: CLAUDE.md ≤100 lines, agents ≤30 lines, rules ≤20 lines. After scaffolding, Launchpad shows the estimated token impact on your context window.

### Discoverability-First CLAUDE.md
Based on research showing that auto-discoverable content (file trees, import patterns) in CLAUDE.md can hurt task success. The template only includes information Claude can't find by reading your code: commands, architecture decisions, process rules.

### Real Parameterized Agents
Each agent is customized with your actual stack, commands, and STOP conditions — not generic templates. The architect agent knows your frontend/backend, the testing agent uses your real test command, the push agent respects your commit conventions.

### Path-Scoped Rules
Rules target specific file patterns with `globs:` frontmatter. A Next.js project gets rules for `src/app/**/*.tsx`, a FastAPI project gets rules for `app/api/**/*.py`. Stack-specific conventions from the interview are baked in.

### CI/CD Generation
Generates GitHub Actions or GitLab CI pipelines with your actual lint, test, and build commands. Detects your runtime (Node, Python, Go, Rust) and configures the right setup steps. Includes a PR template.

### Post-Scaffold Verification
Use `--verify` to run checks after scaffolding: directories exist, settings.json is valid, MCP env vars are documented in .env.example, commands pass the safety allowlist.

### Version Upgrades
Use `--upgrade` to migrate an existing Launchpad config to the latest version. Creates missing directories, adds new files, updates the version — without touching your customizations.

### Community MCP Servers
Beyond the official MCP servers (GitHub, GitLab, PostgreSQL, SQLite, Sentry), Launchpad supports Context7 (docs lookup) and Sequential Thinking with `--context7` and `--sequential-thinking` flags. Use `--minimal-mcp` to skip community servers.

## Supported Stacks

**Frontend**: Next.js, React+Vite, Vue 3/Nuxt, SvelteKit
**Backend**: Express, Fastify, FastAPI, Django, Go, Rust/Actix, Ruby/Rails, integrated (Next.js/SvelteKit)
**Database**: PostgreSQL, MongoDB, Supabase, SQLite, MySQL, DynamoDB
**ORM**: Prisma, Drizzle, SQLAlchemy, Mongoose, TypeORM, Sequelize, ActiveRecord
**Auth**: Clerk, NextAuth/Auth.js, Supabase Auth, custom JWT
**Hosting**: Vercel, Railway, AWS, Fly.io, self-hosted
**CI/CD**: GitHub Actions, GitLab CI
**MCP**: GitHub, GitLab, PostgreSQL, SQLite, Filesystem, Sentry, Context7, Sequential Thinking

## CLI Reference

The scaffold script supports these flags (used internally by the skill, but can also be run directly):

```bash
python scripts/scaffold.py --project-name "my-app" \
  --frontend nextjs --backend integrated --database postgresql \
  --orm prisma --auth clerk --hosting vercel \
  --git-platform github --ci-cd github-actions \
  --lint-cmd "npm run lint" --test-cmd "npm run test" \
  --dev-cmd "npm run dev" --build-cmd "npm run build" \
  --migrate-cmd "npx prisma migrate dev" \
  --ai --tdd --team --conventional-commits \
  --context7 --sentry \
  --verify --create-root
```

Key flags:
- `--preset <name>` — Use a preset stack configuration
- `--update` — Merge into existing .claude/ (don't overwrite)
- `--force` — Overwrite all existing files
- `--dry-run` — Show what would be created without writing
- `--verify` — Run verification checks after scaffolding
- `--upgrade` — Upgrade existing config to current version
- `--minimal-mcp` — Skip community MCP servers

The auditor:
```bash
python scripts/audit.py /path/to/project
python scripts/audit.py /path/to/project --fix        # Auto-fix safe issues
python scripts/audit.py /path/to/project --recommend   # Show improvement suggestions
python scripts/audit.py /path/to/project --json        # JSON output
```

## Development

```bash
# Run tests (185 tests, stdlib only)
cd scripts/
python -m pytest test_scaffold.py test_audit.py -v
```

## License

MIT
