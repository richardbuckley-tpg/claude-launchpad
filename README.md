# Claude Launchpad

A Claude Code skill that bootstraps complete project configurations — then keeps them evolving. Generates agents, rules, skills, commands, hooks, MCP config, CI/CD, and more. For existing codebases, analyzes your actual code to generate project-specific rules instead of generic framework advice.

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

Launchpad runs the **codebase analyzer** first — reading your actual source code to detect patterns, conventions, and key abstractions. Then it auto-detects your stack from `package.json`, `requirements.txt`, `go.mod`, etc., and fills gaps through the interview. Use `--analyze` to generate project-specific rules based on real code.

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
│   ├── agents/                      # 5-9 parameterized agents
│   │   ├── architect.md
│   │   ├── testing.md
│   │   ├── reviewer.md
│   │   ├── debugger.md
│   │   ├── push.md
│   │   ├── security.md             # (when auth/AI involved)
│   │   ├── compliance-auditor.md   # (when domain/compliance set)
│   │   ├── frontend-auditor.md     # (when domain + frontend)
│   │   └── architecture-auditor.md # (finance/healthcare/legal)
│   ├── rules/                       # Path-scoped + project-specific
│   │   ├── frontend.md              # (globs: src/app/**/*.tsx)
│   │   ├── backend.md
│   │   ├── database.md
│   │   ├── project-*.md             # (from codebase analyzer)
│   │   └── learned.md               # (from /learn corrections)
│   ├── commands/                    # 8-10 slash commands
│   │   ├── status.md
│   │   ├── handoff.md
│   │   ├── new-feature.md
│   │   ├── fix-bug.md
│   │   ├── audit.md
│   │   ├── build.md                 # Full agent pipeline
│   │   ├── analyze.md               # Codebase analysis
│   │   ├── learn.md                 # Record corrections
│   │   ├── tdd.md                   # (when --tdd)
│   │   └── pipeline.md             # (when --team)
│   ├── skills/                      # 8-10 stack + domain skills
│   │   ├── ...                      # (stack-specific skills)
│   │   ├── finance-domain-rules.md  # (when --domain finance)
│   │   ├── gdpr-rules.md           # (when --compliance gdpr)
│   │   └── ...domain/compliance     # (curated rule sets)
│   ├── settings.json                # Hooks + MCP servers
│   ├── handoff.md                   # Session context preservation
│   └── launchpad-config.json        # Interview answers + version
├── .github/                         # (when --ci-cd github-actions)
│   ├── workflows/ci.yml
│   └── pull_request_template.md
├── docs/
│   ├── first-feature.md             # Step-by-step getting started guide
│   └── blueprints/                  # Architecture blueprints (agent context)
│       └── .template.md             # Blueprint format for /build pipeline
├── .claudeignore
└── .env.example
```

## Key Features

### Codebase Analyzer

For existing projects, the analyzer reads your actual source code and generates targeted rules:

```bash
python scripts/analyze.py /path/to/project                # See what it detects
python scripts/analyze.py /path/to/project --write-rules  # Write to .claude/rules/
```

It detects: error handling patterns, auth middleware, validation libraries, data fetching, state management, file organization, testing conventions, API patterns, database access, and key abstractions (custom hooks, services, repositories).

The difference: instead of "use Server Components by default" (generic), you get "this project uses `AppError` from `src/lib/errors.ts` for all error handling — never throw generic Error" (specific).

### Learning System

The `/learn` command captures corrections so Claude doesn't repeat mistakes:

```
/learn "Always use zod schemas from src/schemas/, never manual validation"
/learn "Use AppError, not generic Error"
```

Corrections are stored in `.claude/rules/learned.md` and persist across sessions. Over time, the rules become a distilled record of your project's preferences. Use `--from-git` to automatically detect correction patterns from commit history.

### Agent Orchestration

The `/build` command runs the full development pipeline with context passing through blueprints:

1. **Architect** designs the feature → writes blueprint to `docs/blueprints/`
2. **Security** reviews the blueprint (when auth/payments involved)
3. **Implement** builds following the approved blueprint
4. **Testing** writes tests from the blueprint spec
5. **Reviewer** checks the full diff
6. **Push** creates the PR

Each agent receives the output of the previous one. The blueprint is the shared context.

### Feedback Loop (`/evolve`)

The analyzer, learning system, and audit are connected in a closed loop:

```
Analyze → Rules → Claude works → Developer corrects → /learn → /evolve → Updated rules
```

Say **"/evolve"** to re-analyze your codebase with learned corrections merged in. The auditor also detects staleness automatically — if analyzer rules reference deleted files or the analysis is >60 days old, it flags warnings suggesting `/evolve`.

### Domain Auditor Agents

For regulated domains, Launchpad generates specialized auditor agents paired with curated domain knowledge skills:

- **Finance** — UK accounting rules (VAT, MTD, double-entry), SOX internal controls, decimal-only money handling
- **Healthcare** — HIPAA PHI rules, clinical data integrity, consent management, de-identification
- **HR** — Employee data handling, payroll rules, GDPR employee rights, recruitment anonymization
- **E-commerce** — PCI-DSS card handling, pricing rules, consumer rights, inventory management
- **Legal** — Document retention, client confidentiality, legal hold, privilege tagging
- **Education** — Student data protection, WCAG accessibility, safeguarding, assessment integrity

Compliance frameworks (GDPR, SOX, HIPAA, PCI-DSS) can be combined — a UK fintech gets GDPR + SOX + PCI-DSS rules. The `/build` pipeline includes a domain audit step before code review. Extend any rule set with `/learn`.

### Enhanced Auto-Detection

For existing projects, the analyzer detects far more than just your stack. It finds your actual commands (test, lint, dev, build, migrate) from `package.json` scripts, `Makefile` targets, and `pyproject.toml`. It detects your git platform from `.git/config`, CI/CD from workflow files, and hosting from `vercel.json`/`fly.toml`/`railway.toml`. This means fewer interview questions — the analyzer fills in what it can find.

### Monorepo Support

Detects Turborepo, Nx, pnpm workspaces, yarn workspaces, and Lerna. Identifies all packages with their paths and generates a monorepo-specific rule covering workspace conventions, cross-package imports, and shared config respect.

### AI Config Migration

Migrates existing AI tool configs (`.cursorrules`, `.github/copilot-instructions.md`, `.windsurfrules`) to `.claude/rules/migrated-*.md`. Runs automatically with `--analyze` or explicitly with `--migrate-ai-configs`. Preserves original content with adaptation notes.

### Dependency Drift Detection

During `--analyze`, snapshots your project's dependencies. On subsequent audits, compares current deps against the snapshot and flags significant changes — new test frameworks, ORMs, auth providers, or major framework changes that may need config updates. Suggests `/evolve` when drift is detected.

### Token-Optimized

Strict line limits keep your config lean: CLAUDE.md ≤100 lines, agents ≤30 lines, rules ≤20 lines. After scaffolding, Launchpad shows the estimated token impact on your context window.

### Discoverability-First CLAUDE.md

Based on research showing that auto-discoverable content (file trees, import patterns) in CLAUDE.md can hurt task success. The template only includes information Claude can't find by reading your code: commands, architecture decisions, process rules.

### Real Parameterized Agents

Each agent is customized with your actual stack, commands, and STOP conditions. The architect knows your frontend/backend, the testing agent uses your real test command, the push agent respects your commit conventions.

### Path-Scoped Rules

Rules target specific file patterns with `globs:` frontmatter. A Next.js project gets rules for `src/app/**/*.tsx`, a FastAPI project gets rules for `app/api/**/*.py`. Stack-specific conventions are baked in, and the analyzer adds project-specific rules on top.

### CI/CD Generation

Generates GitHub Actions or GitLab CI pipelines with your actual lint, test, and build commands. Detects your runtime (Node, Python, Go, Rust) and configures the right setup steps.

### Post-Scaffold Verification

Use `--verify` to run checks after scaffolding: directories exist, settings.json is valid, MCP env vars are documented in .env.example, commands pass the safety allowlist.

## Supported Stacks

**Frontend**: Next.js, React+Vite, Vue 3/Nuxt, SvelteKit
**Backend**: Express, Fastify, FastAPI, Django, Go, Rust/Actix, Ruby/Rails, integrated (Next.js/SvelteKit)
**Database**: PostgreSQL, MongoDB, Supabase, SQLite, MySQL, DynamoDB
**ORM**: Prisma, Drizzle, SQLAlchemy, Mongoose, TypeORM, Sequelize, ActiveRecord
**Auth**: Clerk, NextAuth/Auth.js, Supabase Auth, custom JWT
**Hosting**: Vercel, Railway, AWS, Fly.io, self-hosted
**CI/CD**: GitHub Actions, GitLab CI
**Domains**: Finance, Healthcare, HR, E-commerce, Legal, Education
**Compliance**: GDPR, SOX, HIPAA, PCI-DSS
**MCP**: GitHub, GitLab, PostgreSQL, SQLite, Filesystem, Sentry, Context7, Sequential Thinking

## CLI Reference

The scaffold script:
```bash
python scripts/scaffold.py --project-name "my-app" \
  --frontend nextjs --backend integrated --database postgresql \
  --orm prisma --auth clerk --hosting vercel \
  --git-platform github --ci-cd github-actions \
  --domain finance --compliance gdpr sox \
  --lint-cmd "npm run lint" --test-cmd "npm run test" \
  --dev-cmd "npm run dev" --build-cmd "npm run build" \
  --migrate-cmd "npx prisma migrate dev" \
  --ai --tdd --team --conventional-commits \
  --context7 --sentry --analyze \
  --verify --create-root
```

Key flags:
- `--preset <name>` — Use a preset stack configuration
- `--analyze` — Run codebase analyzer to generate project-specific rules
- `--migrate-ai-configs` — Migrate .cursorrules, copilot-instructions.md, .windsurfrules to .claude/rules/
- `--monorepo` — Enable monorepo support (auto-detected with --analyze)
- `--update` — Merge into existing .claude/ (don't overwrite)
- `--force` — Overwrite all existing files
- `--dry-run` — Show what would be created without writing
- `--verify` — Run verification checks after scaffolding
- `--upgrade` — Upgrade existing config to current version
- `--minimal-mcp` — Skip community MCP servers

The analyzer:
```bash
python scripts/analyze.py /path/to/project                          # Print analysis report
python scripts/analyze.py /path/to/project --write-rules            # Write rule files
python scripts/analyze.py /path/to/project --incorporate-learned     # Merge learned corrections
python scripts/analyze.py /path/to/project --check-stale            # Find stale rule references
python scripts/analyze.py /path/to/project --json                   # JSON output
python scripts/analyze.py /path/to/project --migrate-ai-configs     # Migrate other AI tool configs
```

The learning system:
```bash
python scripts/learn.py /path/to/project --capture "Use AppError for all errors"
python scripts/learn.py /path/to/project --from-git         # Detect from git history
python scripts/learn.py /path/to/project --show             # Show learned rules
python scripts/learn.py /path/to/project --forget "AppError" # Remove a rule
```

The auditor:
```bash
python scripts/audit.py /path/to/project
python scripts/audit.py /path/to/project --fix        # Auto-fix safe issues
python scripts/audit.py /path/to/project --recommend   # Show improvement suggestions
python scripts/audit.py /path/to/project --json        # JSON output
```

## Development

```bash
# Run all tests (375 tests, stdlib only)
cd scripts/
python -m pytest test_scaffold.py test_audit.py test_analyze.py test_learn.py -v
```

## License

MIT
