# Claude Launchpad

Most Claude Code setup tools give you the same generic agents, commands, and rules regardless of what you're building. A Django API gets the same config as a Next.js SaaS.

**Launchpad is different.** It reads your actual code — error handling patterns, auth middleware, validation libraries, API conventions, test structure — and generates a `.claude/` configuration tailored to your project. Then it keeps evolving: you correct Claude, it learns, rules update automatically.

## What Makes This Different

| | Generic tools | Launchpad |
|---|---|---|
| **Agents** | Same 30+ agents for every project | 10-15 agents customized to your stack, commands, and patterns |
| **Rules** | Framework boilerplate | Path-scoped rules from your actual code (e.g., "use `AppError` from `src/lib/errors.ts`") |
| **Learning** | None or raw session recall | Captures corrections, analyzes git history, re-generates rules via `/evolve` |
| **Config quality** | No feedback | Auditor scores health, token cost, and staleness — works on any `.claude/` setup |
| **Compliance** | None | GDPR, SOX, HIPAA, PCI-DSS rule sets with domain-specific auditor agents |
| **Event systems** | None | Kafka, BullMQ, RabbitMQ, Celery, Temporal — idempotency, DLQ, and retry rules |
| **Deep review** | None | 7-phase codebase assessment: architecture, security, testing, debt, recommendations |
| **Build pipeline** | Manual steps | `/build` orchestrates agents with worktree isolation, parallel execution, state tracking |

No external dependencies. Python 3.10+ stdlib only. 588 tests.

---

## Quick Start

### 1. Install

```bash
git clone https://github.com/richardbuckley-tpg/claude-launchpad.git ~/.claude/skills/claude-launchpad
```

Or as a plugin: `claude plugin install github:richardbuckley-tpg/claude-launchpad`

### 2. Bootstrap

```
"Bootstrap this project using claude-launchpad"
```

Launchpad asks about your stack, then generates everything. Or skip the interview:

```
"Bootstrap with the nextjs-fullstack preset using claude-launchpad"
```

### 3. Build

```
/idea-to-prd "user dashboard with analytics"   # Research & write a PRD
/build user-dashboard                            # Full pipeline: design → test → ship
/deep-review                                     # Comprehensive codebase assessment
```

---

## What You Get

| What | Count | Purpose |
|------|-------|---------|
| **Agents** | 10-15 | Specialized AI teammates — architect, tester, reviewer, refactorer, docs-generator, and more |
| **Slash Commands** | 15-20 | `/build`, `/learn`, `/evolve`, `/audit`, `/debt`, `/decision`, `/deep-review`, and more |
| **Rules** | 2-5 | Path-scoped conventions from your actual code patterns |
| **Skills** | 8-13 | Code generation templates for your specific stack + domain knowledge |
| **Hooks** | 4-6 | Auto-lint on save, auto-test (TDD), force-push block, secret detection |
| **MCP Servers** | 1-3 | GitHub, database, docs — configured with `${ENV_VAR}` references |
| **CI/CD** | 1 | GitHub Actions or GitLab CI with your actual commands |
| **CLAUDE.md** | 1 | Lean project context (commands, stack, mistakes to avoid) |
| **ARCHITECTURE.md** | 1 | System diagram, key decisions, real patterns from deep analysis |

### The Agents

**Always generated (customized to your stack):**

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
| `@refactorer` | Systematic refactoring with test safety — baseline → refactor → verify. |
| `@docs-generator` | Generates API docs, component docs, README sections from code. |

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
| `/deep-review` | 7-phase codebase assessment → `docs/project-review.md` with health score |
| `/learn <correction>` | Teach Claude a project-specific rule that persists |
| `/evolve` | Re-analyze codebase with learned corrections, update rules |
| `/audit` | Check config health, token cost, staleness |
| `/analyze` | Detect code patterns, generate project-specific rules |
| `/new-feature <name>` | Create branch, read context, present plan for approval |
| `/fix-bug <description>` | Systematic debug with regression test |
| `/project-status` | Where am I? Recent changes, test health, next action |
| `/handoff` | Auto-capture session state — git changes, test health, metrics |
| `/refactor <target>` | Systematic refactoring with test safety guarantees |
| `/generate-docs <scope>` | Generate documentation from source code |
| `/debt` | Scan for TODO/FIXME/HACK, track debt trends over time |
| `/decision <title>` | Record an architecture decision (ADR) in `docs/decisions/` |
| `/resume-build` | Resume an interrupted `/build` pipeline from last completed stage |
| `/cloud-fix` | Fix CI failures or review comments on current PR |
| `/tdd <feature>` | Red-green-refactor cycle (when `--tdd` is set) |
| `/setup-teams` | Enable Agent Teams for parallel multi-agent workflows (experimental) |

---

## The Idea-to-Ship Pipeline

Say `/build <feature>` and agents run with worktree isolation and parallel execution:

```
/idea-to-prd "user dashboard"   ←  optional first step (generates PRD)
/build user-dashboard            ←  triggers the full pipeline:

  0. Read PRD (if one exists in docs/prds/)
  1. Create git worktree (isolated workspace for the feature)
  2. @architect designs → writes blueprint to docs/blueprints/
  3. @security + @testing run IN PARALLEL (TDD mode)
  4. Implement until tests pass
  5. @compliance-auditor + @reviewer run IN PARALLEL (when domain set)
  6. @pre-push full pre-flight (lint, test, build, secrets, debug code)
  7. @push creates the PR, cleans up worktree
```

The blueprint is the shared context. Worktree isolation keeps your main directory clean — if the build fails, nothing to undo. Pipeline state is tracked in `.claude/pipeline-state.json` — if interrupted, `/resume-build` picks up where you left off.

**Agent Teams mode** (experimental): With `--agent-teams`, each agent runs as an independent Claude Code session with direct messaging and shared task lists, enabling true parallel execution.

---

## Codebase Analysis

For existing projects, the analyzer reads your source code and extracts real patterns:

**Standard analysis** (`--analyze`):
- **Stack** — frontend, backend, database, ORM, auth, test framework, commands
- **Infrastructure** — git platform, CI/CD, hosting, monorepo structure
- **Code patterns** — error handling, auth middleware, validation, data fetching, testing conventions, API patterns, key abstractions
- **Migrations** — imports .cursorrules, copilot-instructions.md, .windsurfrules
- **Dependencies** — snapshots for drift detection on subsequent audits

**Deep analysis** (`--analyze --deep`):
- **Entry points** — server starts, CLI entries, framework-specific entry files
- **API surface** — all routes/endpoints with HTTP methods (Express, Next.js, FastAPI, Django, Go, Rails, GraphQL, tRPC)
- **Complexity indicators** — large files, function counts, size distribution
- **Test coverage map** — which source files have tests, coverage ratio, untested directories
- **Config & environment** — env var references across the codebase, config files, .env patterns

Deep analysis feeds into an enhanced ARCHITECTURE.md that replaces stubs with real data — actual error handling patterns, auth flows, entry points, API surface, and environment variables.

### Deep Review

After scaffolding, `/deep-review` combines automated analysis with Claude's semantic understanding for a 7-phase assessment:

1. **Automated Analysis** — structural data from the analyzer
2. **Architecture Assessment** — layering, data flows, coupling, separation of concerns
3. **Code Quality** — anti-patterns, consistency, large file review
4. **Security Posture** — auth coverage per endpoint, input validation, secrets
5. **Testing Health** — coverage ratio, test quality, critical gaps
6. **Tech Debt & Documentation** — TODO/FIXME counts, doc coverage, staleness
7. **Report** — `docs/project-review.md` with health score, findings, and prioritized recommendations

---

## Learning & Evolution

Most tools are static — install once, never improve. Launchpad's config evolves with your project:

```
Analyze → Rules → Claude works → You correct → /learn → /evolve → Better rules
```

**`/learn`** — Claude makes a mistake? Teach it once:
```
/learn "Always use zod schemas from src/schemas/, never manual validation"
/learn "Use AppError, not generic Error"
```

**`/evolve`** — Re-analyzes the codebase with learned corrections merged, updates stale rules, runs the auditor to verify. The auditor also detects staleness automatically — if rules reference deleted files or analysis is >60 days old, it suggests `/evolve`.

---

## Config Auditor

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

Scores structure, token efficiency, freshness (stale references), and best practices. Reports specific issues with fix recommendations.

---

## Three Ways to Use It

### New Project (Full Interview)

```
You: "Bootstrap this project using claude-launchpad"
Claude: Asks about your stack in 4 phases
→ Generates complete .claude/ config
```

### New Project (Preset)

```
You: "Bootstrap with the fastapi preset using claude-launchpad"
→ Instant scaffolding, no questions
```

Available presets: `nextjs-fullstack`, `nextjs-supabase`, `react-express`, `fastapi`, `go-api`, `sveltekit-fullstack`, `rails`

### Existing Project

```
You: "Set up Claude Code for this project using claude-launchpad"
Claude: Analyzes your code first, asks about gaps
→ Project-specific rules based on your actual patterns
→ Then: /deep-review for comprehensive assessment
```

---

## Domain & Compliance

For regulated industries:

- **Finance** — UK accounting rules, SOX controls, decimal-only money
- **Healthcare** — HIPAA PHI rules, consent management, de-identification
- **E-commerce** — PCI-DSS card handling, pricing rules
- **Legal** — Document retention, privilege tagging
- **HR** — Employee data handling, GDPR rights
- **Education** — Student data protection, WCAG accessibility

Compliance frameworks (GDPR, SOX, HIPAA, PCI-DSS) can be combined. A UK fintech gets GDPR + SOX + PCI-DSS rules automatically. Each generates domain-specific auditor agents that review code against curated rule sets.

---

## Supported Stacks

| Category | Options |
|----------|---------|
| **Frontend** | Next.js, React+Vite, Vue 3/Nuxt, SvelteKit |
| **Backend** | Express, Fastify, FastAPI, Django, Go, Rust/Actix, Rails, integrated |
| **Database** | PostgreSQL, MongoDB, Supabase, SQLite, MySQL (basic), DynamoDB (basic) |
| **ORM** | Prisma, Drizzle, SQLAlchemy, Mongoose, TypeORM, Sequelize, ActiveRecord |
| **Auth** | Clerk, NextAuth/Auth.js, Supabase Auth, custom JWT |
| **Hosting** | Vercel, Railway, AWS, Fly.io, self-hosted |
| **CI/CD** | GitHub Actions, GitLab CI |
| **Events** | Kafka, BullMQ, RabbitMQ, Celery, NATS, Redis Streams, Temporal |
| **MCP** | GitHub, GitLab, PostgreSQL, SQLite, Filesystem, Sentry, Context7 |

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
- `--deep` — Deep analysis for enhanced ARCHITECTURE.md (use with `--analyze`)
- `--update` — Merge into existing config
- `--dry-run` — Preview without writing
- `--verify` — Post-scaffold verification
- `--migrate-ai-configs` — Import .cursorrules etc.
- `--agent-teams` — Use Agent Teams for `/build` pipeline (experimental)

</details>

<details>
<summary>Analyzer</summary>

```bash
python scripts/analyze.py /path/to/project                      # Print report
python scripts/analyze.py /path/to/project --deep               # Deep analysis (entry points, API, complexity, coverage)
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
# Run all tests (588 tests, stdlib only)
cd scripts/
python -m pytest test_scaffold.py test_audit.py test_analyze.py test_learn.py -v
```

## License

MIT
