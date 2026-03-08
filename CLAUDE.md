# Claude Launchpad

Lean, token-aware Claude Code bootstrapping skill. Scaffolds `.claude/` configuration with real values from an interactive interview.

## Build & Test

```
cd scripts/
python -m pytest test_scaffold.py test_audit.py -v
```

No external dependencies — stdlib only (Python 3.10+).

## Architecture

- `SKILL.md` — The Claude Code skill definition (entry point)
- `scripts/scaffold.py` — Core scaffolding engine. Generates commands, skills, agents, rules, hooks, MCP configs, settings.json
- `scripts/audit.py` — Config auditor. Scores any .claude/ setup for health, tokens, staleness, discoverability
- `reference/` — Stack-specific knowledge (stacks.md, agents.md, audit-rules.md)
- `templates/` — Lean templates for CLAUDE.md (discoverability-first), ARCHITECTURE.md

## Key Conventions

- All generated files use real values from the interview, never `{placeholders}`
- Token budgets: CLAUDE.md ≤100 lines, agents ≤30 lines, rules ≤20 lines, skills ≤40 lines
- `safe_write()` handles skip/force/dry-run modes for all file operations
- User-provided commands validated against `SAFE_CMD_PATTERN` allowlist (injection prevention)
- MCP env vars use `${VAR}` syntax, never hardcoded secrets. Community MCP (Context7, Sequential Thinking) supported.
- Hooks use `jq` for stdin JSON parsing with `command -v jq` fallback
- Agents are parameterized with real stack/commands/STOP conditions via `get_agents()`
- Rules are path-scoped with globs via `get_rules()`
- Token budget summary shows context window % after scaffolding

## File Layout

```
scripts/scaffold.py    — Scaffolder (generates .claude/ tree)
scripts/audit.py       — Auditor (scores config health)
scripts/test_*.py      — Test suites (156 tests)
reference/stacks.md    — Stack patterns (Next.js, FastAPI, Go, Rails, Rust, etc.)
reference/agents.md    — Agent templates and selection logic
reference/audit-rules.md — Scoring rubric documentation
```

## Testing

Tests use `unittest` with `tempfile` for isolation. Run with:
```
python -m pytest scripts/ -v
```

Key test areas: command injection blocking, hook scoping, settings merge, dry-run mode, staleness detection, secret detection, agent/rule generation, community MCP, discoverability checks, context percentage.
