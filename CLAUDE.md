# Claude Launchpad

Lean, token-aware Claude Code bootstrapping skill with codebase analysis, learning system, and agent orchestration.

## Build & Test

```
cd scripts/
python -m pytest test_scaffold.py test_audit.py test_analyze.py test_learn.py test_plugin.py -v
```

No external dependencies — stdlib only (Python 3.10+).

## Architecture

- `SKILL.md` — The Claude Code skill definition (entry point)
- `scripts/scaffold.py` — Core scaffolding engine. Generates commands, skills, agents, rules, hooks, MCP configs, settings.json
- `scripts/analyze.py` — Codebase analyzer. Reads source code to extract patterns, conventions, key abstractions. Generates project-specific rules.
- `scripts/learn.py` — Learning system. Captures corrections, analyzes git history, maintains learned rules.
- `scripts/audit.py` — Config auditor. Scores any .claude/ setup for health, tokens, staleness, discoverability
- `reference/` — Stack-specific knowledge (stacks.md, agents.md, audit-rules.md)
- `templates/` — Lean templates for CLAUDE.md (discoverability-first), ARCHITECTURE.md

## Key Conventions

- All generated files use real values from the interview, never `{placeholders}`
- Token budgets: CLAUDE.md ≤100 lines, agents ≤30 lines, rules ≤20 lines, skills ≤40 lines
- `safe_write()` handles skip/force/dry-run modes (and creates parent dirs) for all file operations
- User-provided commands validated against `SAFE_CMD_PATTERN` allowlist (injection prevention)
- Skills follow the Agent Skills standard: `.claude/skills/<name>/SKILL.md` with `name:`+`description:` frontmatter (not flat `<name>.md`)
- Project MCP servers are written to a project-root `.mcp.json` (`{"mcpServers": {...}}`), NOT settings.json
- MCP uses maintained packages/remotes: GitHub & Sentry via official remote HTTP servers, Postgres via `crystaldba/postgres-mcp`, Context7 via `@upstash/context7-mcp`; deprecated `@modelcontextprotocol/server-*` packages and version pins removed (`MCP_PACKAGES`/`MCP_REMOTE`)
- MCP secrets use `${VAR}` syntax in env or HTTP headers, never hardcoded; documented in `.env.example`
- `settings.json` carries hooks + `statusLine` + `fallbackModel: ["sonnet"]` via `get_settings()`; `VALID_SETTINGS_KEYS`/hook-event list track the current schema
- Models/effort: agents use `opus`/`sonnet` aliases (Opus 4.8 / Sonnet 4.6); architect runs `effort: xhigh`; lineup, effort levels, and 1M-context guidance in `reference/agents.md`
- Agent Teams (`--agent-teams`): generates `TaskCompleted`/`TeammateIdle` quality-gate hooks (inert outside team sessions)
- Dynamic workflows (`get_workflows(args, skill_path)`): generates `.claude/workflows/*.js` (`/ultra-build`, `/ultra-review`, `/security-sweep`, `/semantic-analyze`) — parameterized scripts that orchestrate the project's agents with adversarial verification. Named to avoid colliding with the prose fallbacks; ~0 context cost; skip with `--no-workflows`
- Semantic analysis (P4): `/semantic-analyze` workflow + `/deep-analyze` prose command (`cmd_deep_analyze`) do hybrid analysis — cheap `analyze.py` regex signals first, then per-subsystem agents extract conventions a regex misses → write `.claude/rules/project-semantic.md` + refresh ARCHITECTURE.md
- Living config health (P3): `audit.py --drift` is a high-signal, low-noise freshness scan (`drift_check()` — only analyzer-generated `project-*.md` drift + stale analysis, so a fresh scaffold stays silent). A rate-limited (`.claude/.drift-last`, daily) `SessionStart` hook runs it non-blocking; `/config-health` (`cmd_config_health`) is the on-demand report
- Hooks use `jq` for stdin JSON parsing with `command -v jq` fallback
- Agents are parameterized with real stack/commands/STOP conditions via `get_agents()`
- Domain auditor agents (compliance, frontend, architecture) generated when `--domain`/`--compliance` set
- Domain knowledge skills contain curated rule sets (finance, GDPR, HIPAA, SOX, PCI-DSS, etc.)
- Agents pass context through blueprints in `docs/blueprints/` (`/build` pipeline)
- Rules are path-scoped with globs via `get_rules()`, plus project-specific from `analyze.py`
- Learned rules from `/learn` stored in `.claude/rules/learned.md` and `.claude/learn-log.json`
- Feedback loop: `/evolve` re-analyzes with learned corrections merged, updates rules, audits result
- `last_analysis` timestamp in `launchpad-config.json` tracks when codebase was last analyzed
- Enhanced auto-detection: commands (test/lint/dev/build/migrate), git platform, CI/CD, hosting from project files
- Monorepo support: Turborepo, Nx, pnpm/yarn workspaces, Lerna detection with per-package rules
- AI config migration: `.cursorrules`, copilot-instructions.md, `.windsurfrules` → `.claude/rules/migrated-*.md`
- Dependency drift: snapshots deps during `--analyze`, auditor flags significant package changes
- Token budget summary shows context window % after scaffolding

## File Layout

```
scripts/scaffold.py    — Scaffolder (generates .claude/ tree)
scripts/analyze.py     — Codebase analyzer (extracts patterns → rules)
scripts/learn.py       — Learning system (captures corrections)
scripts/audit.py       — Auditor (scores config health)
scripts/test_*.py      — Test suites (656 tests)
reference/stacks.md    — Stack patterns (Next.js, FastAPI, Go, Rails, Rust, etc.)
reference/agents.md    — Agent templates and selection logic
reference/audit-rules.md — Scoring rubric documentation
```

## Testing

Tests use `unittest` with `tempfile` for isolation. Run with:
```
python -m pytest scripts/ -v
```

Key test areas: stack detection, pattern detection (error handling, auth, validation, data fetching, testing, API, database), file organization, key abstractions, rule generation, capture/forget/git-analysis, feedback loop (incorporate learned, stale rules, reanalysis suggestion, analysis timestamps), command injection blocking, hook scoping, settings merge, dry-run mode, staleness detection, secret detection, agent/rule generation, community MCP, discoverability checks, context percentage, enhanced auto-detection (commands/git/CI/hosting), monorepo detection, AI config migration, dependency drift, deep review (entry points, API surface, complexity, test coverage map, config/env, enhanced ARCHITECTURE.md), performance-optimizer agent, search-first skill, quality-gate command, context-budget command, build pipeline cleanup pass.
