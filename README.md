# Claude Launchpad

The ultimate bootstrapper for [Claude Code](https://docs.anthropic.com/en/docs/claude-code). Go from zero to a fully configured project in minutes — with agents that take you from idea to shipped PR.

**What it does:** You tell Claude about your project (or it reads your existing code), and Launchpad generates a complete `.claude/` configuration — agents, slash commands, rules, hooks, MCP servers, CI/CD — all customized to your actual stack, not generic templates.

**Why it exists:** Setting up Claude Code well takes hours of reading docs, writing agents, configuring hooks, and tuning rules. Launchpad does it in minutes, and keeps the config evolving as your project grows.

## Quick Start

### 1. Install (30 seconds)

```bash
git clone https://github.com/richardbuckley-tpg/claude-launchpad.git ~/.claude/skills/claude-launchpad
```

This installs Launchpad as a global Claude Code skill. Requires Python 3.10+ (stdlib only, no pip install needed).

### 2. Bootstrap (5 minutes)

Open Claude Code in any project directory and say:

```
"Bootstrap a new project"
```

Launchpad asks you about your stack through a short conversation, then generates everything. Or skip the interview with a preset:

```
"Bootstrap with the nextjs-fullstack preset"
```

### 3. Start Building

After scaffolding, you have working slash commands immediately:

```
/idea-to-prd "user dashboard with analytics"   # Research & write a PRD
/build user-dashboard                            # Full pipeline: design → test → ship
/status                                          # Where am I? What's next?
```

That's it. You're set up.

---

## What You Get

Launchpad generates a complete Claude Code configuration tailored to your project:

| What | Count | Purpose |
|------|-------|---------|
| **Agents** | 8-13 | Specialized AI teammates — architect, tester, reviewer, security auditor, and more |
| **Slash Commands** | 9-11 | `/build`, `/learn`, `/evolve`, `/audit`, `/idea-to-prd`, and more |
| **Rules** | 2-5 | Path-scoped conventions (e.g., Next.js rules only apply to `src/app/**/*.tsx`) |
| **Skills** | 8-13 | Code generation templates for your specific stack + domain knowledge |
| **Hooks** | 4-6 | Auto-lint on save, auto-test (TDD), force-push block, secret detection |
| **MCP Servers** | 1-3 | GitHub, database, docs — configured with `${ENV_VAR}` references |
| **CI/CD** | 1 | GitHub Actions or GitLab CI with your actual commands |
| **CLAUDE.md** | 1 | Lean project context (commands, stack, mistakes to avoid) |
| **ARCHITECTURE.md** | 1 | System diagram, key decisions, patterns |

### The Agents

**Always generated:**

| Agent | What it does |
|-------|-------------|
| `@architect` | Designs features → writes blueprints. Does NOT write code. |
| `@testing` | Creates test suites from specs. Writes tests BEFORE seeing implementation. |
| `@reviewer` | Code review with severity tiers. Must APPROVE before shipping. |
| `@debugger` | Systematic diagnosis: reproduce → isolate → fix → regression test. |
| `@push` | Git workflow — branching, commits, PRs. Blocks >500-line PRs. |
| `@idea-to-prd` | Researches an idea online → generates structured PRD with competitive analysis. |
| `@pre-push` | Pre-flight checklist: lint, test, build, type-check, secrets scan, debug code scan. |
| `@dev-ops` | Proposes infrastructure (local/staging/prod) with cost estimates + starter IaC. |

**Conditional (added when relevant):**

| Agent | When |
|-------|------|
| `@security` | Auth, payments, or AI involved |
| `@reliability-auditor` | Event systems (Kafka, BullMQ, etc.) detected |
| `@compliance-auditor` | Domain or compliance requirements set |
| `@frontend-auditor` | Domain + frontend (e.g., decimal precision for finance UI) |
| `@architecture-auditor` | Finance, healthcare, or legal domains |

### The Slash Commands

| Command | What it does |
|---------|-------------|
| `/build <feature>` | Full pipeline: PRD → design → test → implement → audit → review → pre-push → ship |
| `/idea-to-prd <idea>` | Research an idea, generate a PRD, feed it to `/build` |
| `/new-feature <name>` | Create branch, read context, present plan for approval |
| `/fix-bug <description>` | Systematic debug with regression test |
| `/learn <correction>` | Teach Claude a project-specific rule that persists |
| `/evolve` | Re-analyze codebase with learned corrections, update rules |
| `/audit` | Check config health, token cost, staleness |
| `/analyze` | Detect code patterns, generate project-specific rules |
| `/status` | Where am I? Recent changes, test health, next action |
| `/handoff` | Save session context for next time |
| `/tdd <feature>` | Red-green-refactor cycle (when `--tdd` is set) |

---

## The Idea-to-Ship Pipeline

This is the core workflow. Say `/build <feature>` and agents run in sequence:

```
/idea-to-prd "user dashboard"   ←  optional first step (generates PRD)
/build user-dashboard            ←  triggers the full pipeline:

  0. Read PRD (if one exists in docs/prds/)
  1. @architect designs → writes blueprint to docs/blueprints/
  2. @security reviews the blueprint (when auth/payments involved)
  3. @testing writes failing tests from the blueprint spec (TDD mode)
  4. Implement until tests pass
  5. @compliance-auditor checks domain rules (when domain is set)
  6. @reviewer code review — must APPROVE
  7. @pre-push full pre-flight (lint, test, build, secrets, debug code)
  8. @push creates the PR
```

The blueprint is the shared context between agents. Each step builds on the previous one.

---

## Three Ways to Use It

### New Project (Full Interview)

```
You: "Bootstrap a new project"
Claude: Asks about your stack in 4 phases
→ Generates complete .claude/ config
```

### New Project (Preset)

```
You: "Bootstrap with the fastapi preset"
→ Instant scaffolding, no questions
```

Available presets: `nextjs-fullstack`, `nextjs-supabase`, `react-express`, `fastapi`, `go-api`, `sveltekit-fullstack`, `rails`

### Existing Project

```
You: "Set up Claude Code for this project"
Claude: Analyzes your code first, asks about gaps
→ Project-specific rules based on your actual patterns
```

The analyzer reads your source code and generates targeted rules. Instead of "use Server Components by default" (generic), you get "this project uses `AppError` from `src/lib/errors.ts` for all error handling — never throw generic Error" (specific).

---

## Key Features

### Learning System

Claude makes a mistake? Teach it once, it remembers forever:

```
/learn "Always use zod schemas from src/schemas/, never manual validation"
/learn "Use AppError, not generic Error"
```

Rules persist in `.claude/rules/learned.md`. Use `/evolve` to bake learned corrections into the analyzer's rules.

### Config Auditor

Works on **any** `.claude/` setup — not just Launchpad-generated ones:

```
/audit
```

```
Health Score: 92/100
  Structure: 30/30  Efficiency: 27/30  Freshness: 20/20  Practices: 15/20

Token Budget
  CLAUDE.md              37 lines  ~148 tokens  ✓
  Agents (8)            180 lines  ~720 tokens  ✓
  Rules (3)              45 lines  ~180 tokens  ✓
  Total                 262 lines  ~1048 tokens
```

### Infrastructure Planning

```
You: "@dev-ops Set up infrastructure for this project"
```

The dev-ops agent proposes three environments with cost estimates:
- **Local** — Docker Compose (always)
- **Staging** — lightweight, cost-optimized
- **Production** — right-sized with monitoring

Generates starter `docker-compose.yml` and Terraform files.

### Domain & Compliance

For regulated industries, add `--domain` and `--compliance`:

- **Finance** — UK accounting rules, SOX controls, decimal-only money
- **Healthcare** — HIPAA PHI rules, consent management, de-identification
- **E-commerce** — PCI-DSS card handling, pricing rules
- **Legal** — Document retention, privilege tagging
- **HR** — Employee data handling, GDPR rights
- **Education** — Student data protection, WCAG accessibility

Compliance frameworks (GDPR, SOX, HIPAA, PCI-DSS) can be combined. A UK fintech gets GDPR + SOX + PCI-DSS rules automatically.

### Feedback Loop

```
Analyze → Rules → Claude works → You correct → /learn → /evolve → Better rules
```

The auditor detects staleness automatically — if rules reference deleted files or analysis is >60 days old, it suggests `/evolve`.

---

## Supported Stacks

| Category | Options |
|----------|---------|
| **Frontend** | Next.js, React+Vite, Vue 3/Nuxt, SvelteKit |
| **Backend** | Express, Fastify, FastAPI, Django, Go, Rust/Actix, Rails, integrated |
| **Database** | PostgreSQL, MongoDB, Supabase, SQLite, MySQL, DynamoDB |
| **ORM** | Prisma, Drizzle, SQLAlchemy, Mongoose, TypeORM, Sequelize, ActiveRecord |
| **Auth** | Clerk, NextAuth/Auth.js, Supabase Auth, custom JWT |
| **Hosting** | Vercel, Railway, AWS, Fly.io, self-hosted |
| **CI/CD** | GitHub Actions, GitLab CI |
| **Events** | Kafka, BullMQ, RabbitMQ, Celery, NATS, Redis Streams, Temporal |
| **MCP** | GitHub, GitLab, PostgreSQL, SQLite, Filesystem, Sentry, Context7 |

---

## Also Detects

For existing projects, the analyzer goes beyond stack detection:

- **Commands** — finds test/lint/dev/build/migrate from package.json, Makefile, pyproject.toml
- **Git platform** — detects from `.git/config` (GitHub, GitLab, Bitbucket)
- **CI/CD** — detects from workflow files
- **Hosting** — detects from vercel.json, fly.toml, railway.toml
- **Monorepo** — Turborepo, Nx, pnpm/yarn workspaces, Lerna
- **AI configs** — migrates .cursorrules, copilot-instructions.md, .windsurfrules
- **Dependency drift** — snapshots deps, flags changes on subsequent audits
- **Code patterns** — error handling, auth middleware, validation, data fetching, testing conventions, API patterns, key abstractions

---

## CLI Reference

Most users never need this — the skill handles everything through conversation. But the scripts work standalone:

<details>
<summary>Scaffold script</summary>

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
  --context7 --sentry --analyze --verify --create-root
```

Key flags:
- `--preset <name>` — Skip the interview
- `--analyze` — Generate rules from actual code
- `--update` — Merge into existing config
- `--dry-run` — Preview without writing
- `--verify` — Post-scaffold verification
- `--migrate-ai-configs` — Import .cursorrules etc.

</details>

<details>
<summary>Analyzer</summary>

```bash
python scripts/analyze.py /path/to/project                      # Print report
python scripts/analyze.py /path/to/project --write-rules        # Write rules
python scripts/analyze.py /path/to/project --incorporate-learned # Merge corrections
python scripts/analyze.py /path/to/project --check-stale        # Find stale refs
python scripts/analyze.py /path/to/project --json               # JSON output
```

</details>

<details>
<summary>Learning system</summary>

```bash
python scripts/learn.py /path/to/project --capture "Use AppError"
python scripts/learn.py /path/to/project --from-git     # Detect from history
python scripts/learn.py /path/to/project --show         # Show rules
python scripts/learn.py /path/to/project --forget "rule" # Remove a rule
```

</details>

<details>
<summary>Auditor</summary>

```bash
python scripts/audit.py /path/to/project               # Health report
python scripts/audit.py /path/to/project --fix          # Auto-fix safe issues
python scripts/audit.py /path/to/project --recommend    # Suggestions
python scripts/audit.py /path/to/project --json         # JSON output
```

</details>

## Development

```bash
# Run all tests (441 tests, stdlib only)
cd scripts/
python -m pytest test_scaffold.py test_audit.py test_analyze.py test_learn.py -v
```

## License

MIT
