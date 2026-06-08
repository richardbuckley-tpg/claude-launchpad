# Claude Launchpad v8 — Flagship Roadmap

> Status: planning. Target: a landmark major release that turns Launchpad from a
> static `.claude/` generator into a **self-maintaining, natively-orchestrated dev
> system you can install in two commands.**

## Thesis

v7 made the generated output correct for 2026 Claude Code. v8 changes *what the
plugin is*. Claude Code's 2026 primitives — dynamic workflows, agent teams, the
plugin/marketplace standard, 1M context, effort levels — opened a gap: the best
tooling now **orchestrates work** and **keeps config alive**, not just emits files.

v8 keeps the moat (analyzer + auditor + learn/evolve loop — nothing else does this)
and builds four pillars on top. Big-bang scope, with a heavy verification phase
because the surface is large and workflows are a research preview.

**Non-negotiables**
- **Zero regressions** on v7 output. Everything is additive or behind a flag/fallback.
- **Graceful degradation.** Workflows → prose pipeline; semantic → regex; remote → local.
- **Token discipline preserved.** New power must not bloat the per-project context cost.

---

## Pillar 1 — Native workflow orchestration

Replace the hand-rolled `/build` prose pipeline with **real Workflow scripts** (the
native JS orchestration engine: `agent()`, `pipeline()`, `parallel()`, adversarial
verify, loop-until-dry).

**Deliverables**
- `get_workflows(args)` in `scaffold.py` → generates parameterized scripts into
  `.claude/workflows/`:
  - `build.js` — architect → (security ∥ testing) → implement → cleanup → (domain-audit ∥ review, each adversarially verified) → pre-push → ship.
  - `deep-review.js` — fan-out readers per subsystem → synthesize → verify findings.
  - `audit-fix.js` — audit → fan-out fixers per issue class → re-audit.
  - `migrate.js` — discover sites → transform each in a worktree → verify.
  - `security-sweep.js` — multi-lens finders → adversarial verification → report.
- `/build`, `/deep-review`, `/audit` updated to *prefer* the workflow and fall back
  to the existing prose pipeline when `disableWorkflows` is set or the engine is absent.
- "Ultra" variants surfaced (`/ultra-review`, large fan-out) for thorough runs.

**Key design decisions**
- Workflows are generated with the project's real agents, commands, and STOP conditions
  (same parameterization discipline as agents — no placeholders).
- Every workflow returns a structured result; the prose fallback stays in the command file.
- Detect availability at run time; never hard-fail if workflows are off.

**Risks / mitigations**
- Research-preview API churn → keep scripts thin, centralize shared helpers, pin nothing exotic.
- Cost blow-up on big fan-outs → bounded fleet sizes, budget-aware loops, `log()` any caps.

**Acceptance**: `/build <feature>` runs as a deterministic parallel workflow with
adversarial review; disabling workflows still produces a working build via the fallback.

---

## Pillar 2 — Plugin + marketplace distribution

Make Launchpad **`claude plugin install`-able** instead of "clone into `~/.claude/skills`".

**Deliverables**
- `.claude-plugin/marketplace.json` + a current-spec `plugin.json` manifest.
- Restructure the repo so the plugin bundles its *own* reusable agents, commands,
  skills, hooks, and (optional) MCP — distinct from the per-project config the
  scaffolder generates.
- Versioning, `defaultEnabled`, hot-reload (`/reload-plugins`) support.
- Install path documented: `claude plugin marketplace add <repo>` → `claude plugin install claude-launchpad`.

**Key design decisions**
- The scaffolder remains the engine; the plugin is the *delivery vehicle*. Both ship together.
- Plugin-provided skills use the `name@plugin` namespace; no collision with project skills.
- Respect plugin-subagent restrictions (no `hooks`/`mcpServers`/`permissionMode` in plugin agents).

**Risks / mitigations**: marketplace spec drift → validate against docs at build; keep the
clone-install path working as a fallback during transition.

**Acceptance**: a clean machine installs Launchpad in two commands and `/` shows its commands.

---

## Pillar 3 — Living config health

Turn the one-shot auditor into a **continuous, self-maintaining** system.

**Deliverables**
- Incremental drift detection (extend `audit.py` or new `health.py`): rules referencing
  deleted/renamed paths, CLAUDE.md commands missing from `package.json`/manifest,
  dependency changes since last analyze, analysis staleness.
- `SessionStart` hook: fast, rate-limited drift check → concise summary + offer `/evolve`.
- `PostToolUse` hook on renames/moves: flag newly-stale rules.
- `/config-health` command for an on-demand report.

**Key design decisions**
- **Noise is the enemy.** Only surface on meaningful drift; debounce; easy opt-out via setting.
- Reuse the auditor's scoring; health is "audit deltas over time," not a new engine.

**Risks / mitigations**: annoyance → conservative thresholds + a single-line nudge, never a wall of text.

**Acceptance**: rename a watched directory → next session the hook flags the stale rule and suggests `/evolve`.

---

## Pillar 4 — Semantic codebase analysis

Upgrade `analyze.py` from regex pattern-matching to **LLM-powered understanding**.

**Deliverables**
- `/deep-analyze` (and `analyze.py --semantic`): orchestrates reader agents per subsystem
  (using 1M context for whole-repo passes) → synthesizes real conventions → richer project
  rules + an ARCHITECTURE.md with an accurate mermaid map.
- Hybrid pipeline: cheap regex signals first, agent pass for conventions a regex can't see
  (e.g. "all handlers return `Result<T>`", "errors always wrap `AppError`").
- Built **as a workflow** (reuses Pillar 1 infrastructure).

**Key design decisions**
- Opt-in and cached — semantic passes cost real tokens. Default stays fast/regex.
- Bounded scope (changed subsystems, or explicit targets) to control cost.
- Output feeds the *same* rule files, so learn/evolve and the auditor compose unchanged.

**Risks / mitigations**: cost/latency/nondeterminism → opt-in, cache by content hash, cap fleet size.

**Acceptance**: generated rules capture conventions the regex analyzer provably misses, with
no degradation when semantic mode is off.

---

## Sequencing (dependency order, even for big-bang)

1. **P2 — Plugin/marketplace** (substrate; low risk; everything ships through it).
2. **P1 — Workflows** (the flagship; depends on agents existing).
3. **P4 — Semantic analysis** (built as a workflow; reuses P1).
4. **P3 — Living health** (wires hooks; integrates the auditor; lands last).
5. **Hardening** — cross-cutting verification, fallbacks, docs, `CHANGELOG`, bump to 8.0.0.

## Testing strategy

- Keep stdlib `unittest`; add suites for `get_workflows`, marketplace manifest validity,
  drift detection, and semantic-mode *scaffolding* (generation, not LLM runtime).
- Runtime-LLM behavior (workflows, semantic passes) is verified by smoke runs + acceptance
  scripts, not unit tests — assert the generated artifacts and fallbacks, not model output.
- Hard gate: full v7 suite must stay green; add regression tests proving fallbacks work.

## Success metrics

- Install friction: clone-and-configure → **two commands**.
- `/build` wall-clock: measurable reduction from parallel workflow vs serial prose.
- Config-drift catch rate on a seeded "rename a path" test.
- Rule quality: semantic vs regex on a fixture repo (conventions captured).
- Zero v7 regressions; test count up materially.

## Open questions

- Workflow availability detection + the cleanest fallback UX when `disableWorkflows` is set.
- Cost ceiling and caching strategy for semantic analysis.
- How much of the plugin's *own* agent set to ship vs. generate per-project.
- Marketplace hosting: self-hosted repo vs. a shared community marketplace.
