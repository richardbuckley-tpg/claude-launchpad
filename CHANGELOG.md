# Changelog

All notable changes to Claude Launchpad are documented here.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

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
