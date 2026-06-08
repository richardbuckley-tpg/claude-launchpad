# Changelog

All notable changes to Claude Launchpad are documented here.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased] — v8 (in progress)

Flagship release in development (see `docs/ROADMAP-v8.md`). Landed so far:

### Added — Pillar 4: semantic codebase analysis
- `/semantic-analyze` workflow (`get_workflows`) — hybrid analysis: runs the cheap
  `analyze.py` regex pass for structural signals, then fans out one agent per
  subsystem to extract the IMPLICIT conventions a regex misses (how errors are
  wrapped, inputs validated, auth applied, data accessed, naming/layering idioms),
  then synthesizes `.claude/rules/project-semantic.md` and refreshes ARCHITECTURE.md.
- `/deep-analyze` prose command (`cmd_deep_analyze`) — the always-available
  subagent-based fallback when dynamic workflows are off.
- `get_workflows` now takes `skill_path` so the workflow can invoke the project's
  analyzer; the generated script is validated as real JS (`node --check`).

### Added — Pillar 1: native workflow orchestration
- `get_workflows(args)` generates dynamic-workflow scripts into `.claude/workflows/`:
  - `/ultra-build "<feature>"` — parallel design → spec → implement → review → verify,
    dispatching to the project's architect/testing/reviewer/pre-push (and security/
    compliance) agents, with conditional stages by stack/auth/domain.
  - `/ultra-review ["<scope>"]` — multi-dimension review (stack-aware lenses) with every
    finding adversarially verified before it's reported.
  - `/security-sweep ["<scope>"]` — multi-lens security audit with a refutation pass.
- Named `/ultra-*` so they never collide with the always-available prose commands
  (`/build`, `/deep-review`), which remain the fallback when workflows are off. Scripts
  cost ~0 context (executed, not loaded). Skip with `--no-workflows`.
- Generated scripts are validated as real JavaScript (`node --check`) in the test suite.

### Added — Pillar 2: plugin + marketplace distribution
- `.claude-plugin/marketplace.json` — Launchpad is now an installable plugin:
  `claude plugin marketplace add richardbuckley-tpg/claude-launchpad` then
  `claude plugin install claude-launchpad@launchpad`.
- Standardized `.claude-plugin/plugin.json` to the current manifest spec (author object,
  homepage, keywords); the root `SKILL.md` auto-loads as the single-skill plugin.
- `scripts/test_plugin.py` validates both manifests (required fields, source resolution,
  version lockstep with the scaffolder).

### Removed
- The divergent, non-standard root `plugin.json` (Claude Code reads `.claude-plugin/plugin.json`).

## [7.0.0] - 2026-06-08

Modernization for 2026-era Claude Code. Two of these changes fix correctness bugs
that prevented generated configs from working on recent Claude Code versions, so
re-run the scaffolder (or `--update`) on existing projects.

### Fixed
- **Skills are now generated as `.claude/skills/<name>/SKILL.md` directories** with a
  `name:` frontmatter field, per the Agent Skills standard. Flat `.claude/skills/<name>.md`
  files were no longer loaded as skills. `safe_write()` now creates parent directories.
- **MCP server packages refreshed.** Removed the deprecated/archived
  `@modelcontextprotocol/server-github`, `server-postgres`, and `server-sqlite`
  packages and their fabricated version pins. GitHub and Sentry now use the official
  **remote HTTP** servers (`type: http`); PostgreSQL uses Postgres MCP Pro
  (`crystaldba/postgres-mcp`); Context7 uses the correct `@upstash/context7-mcp`
  package. No SQLite MCP is generated (the reference server is archived and vulnerable).

### Changed
- **Project MCP servers are written to a project-root `.mcp.json`** (`{"mcpServers": {...}}`),
  the version-controlled, team-shared convention — no longer embedded in `settings.json`.
- **`VALID_SETTINGS_KEYS` widened to the full current settings.json schema** (statusLine,
  outputStyle, fallbackModel, modelOverrides, requiredMinimumVersion, attribution,
  disableWorkflows, and ~90 more), and the hook-event allowlist refreshed (SessionEnd,
  UserPromptSubmit, TeammateIdle, TaskCreated, TaskCompleted, Elicitation, …). Modern
  hand-authored configs are no longer false-flagged by the auditor.
- **Model & effort awareness.** The architect agent runs `effort: xhigh`. `reference/agents.md`
  gains a "Model & Effort Selection" section covering the Opus 4.8 / Sonnet 4.6 / Haiku 4.5
  lineup, the `low → medium → high → xhigh → max` effort spectrum, 1M-context `[1m]` aliases,
  and adaptive reasoning.
- MCP secrets (env values and HTTP headers) are validated against `.env.example`; the
  scaffolder documents `GITHUB_PERSONAL_ACCESS_TOKEN` / `GITLAB_PERSONAL_ACCESS_TOKEN`.
- `reference/stacks.md` MCP section rewritten for the new packages, transports, and `.mcp.json`.
- Bumped to v7.0.0; refreshed SKILL.md, README, and CLAUDE.md.

### Added
- **`settings.json` now includes `fallbackModel: ["sonnet"]`** (graceful degradation when the
  primary model is overloaded) and a **defensive `statusLine`** (`dir @ branch | model`, never
  errors, degrades without jq/git).
- **Agent Teams quality-gate hooks.** With `--agent-teams`, the scaffold generates
  `TaskCompleted` and `TeammateIdle` hooks (inert outside a team session).
- Documentation of native **dynamic workflows / `ultracode`** and the **commands → skills**
  merge in SKILL.md.

### Tests
- 628 passing (up from 618). Replaced the test asserting fabricated MCP version pins with
  one ensuring no deprecated packages or fabricated pins appear; added coverage for the skill
  directory layout, `.mcp.json` generation/merge, modern settings keys/hook events, the new
  `statusLine`/`fallbackModel`, and the agent-team hooks.

## [6.0.0] - earlier

Prior major release (see `git log` for exact commit history). Highlights:

- Deep project review with enhanced analysis and the `/deep-review` command.
- Agent Teams support for the parallel multi-agent `/build` pipeline.
- Smart handoff, new agents, technical-debt tracking, pipeline resume, and ADRs.
- Plugin format, agent frontmatter, additional hooks, LSP config, and `/cloud-fix`.
- Git worktree isolation and subagent parallelism in `/build`.
- Event-driven system support (Kafka, BullMQ, RabbitMQ, Celery, Temporal, NATS, …).
- Enhanced auto-detection, monorepo support, AI-config migration, and dependency drift.

[7.0.0]: https://github.com/richardbuckley-tpg/claude-launchpad/releases/tag/v7.0.0
