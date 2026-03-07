# Audit Rules — What the Auditor Checks and Why

The `/audit` command runs `scripts/audit.py` to score any `.claude/` configuration.

## Scoring Rubric (100 points total)

### Structure (30 points)
| Check | Points | Pass Condition |
|-------|--------|----------------|
| CLAUDE.md exists | 10 | File exists and has content |
| CLAUDE.md line count | 10 | ≤100 lines (warn >80, fail >150) |
| Agents have frontmatter | 5 | All agents have `name`, `description`, `tools` in YAML |
| Settings.json valid | 5 | Valid JSON, known hook structure |

### Token Efficiency (30 points)
| Check | Points | Pass Condition |
|-------|--------|----------------|
| Total config tokens | 15 | ≤3,500 estimated tokens |
| Agent line counts | 10 | Each agent ≤30 lines (warn >25) |
| Rule line counts | 5 | Each rule ≤20 lines |

### Freshness (20 points)
| Check | Points | Pass Condition |
|-------|--------|----------------|
| Rules reference valid paths | 10 | All glob patterns in rules match existing paths |
| CLAUDE.md commands exist | 5 | Commands mentioned in CLAUDE.md are installed |
| Hooks call existing scripts | 5 | Shell commands in hooks resolve to real files |

### Best Practices (20 points)
| Check | Points | Pass Condition |
|-------|--------|----------------|
| No duplicate agents | 5 | No two agents with same scope |
| No overlapping rules | 5 | No two rules targeting the same path pattern |
| Hooks not overly restrictive | 5 | No hooks that block common operations (e.g., all .md writes) |
| Has handoff document | 5 | `.claude/handoff.md` exists |

## Token Estimation

Heuristic: **~4 tokens per line** (conservative estimate for markdown with code).

Components counted:
- CLAUDE.md (full file)
- All files in `.claude/agents/`
- All files in `.claude/rules/`
- `.claude/settings.json`
- `.claude/handoff.md`

Not counted (loaded on demand, not per-message):
- `.claude/commands/` (only loaded when invoked)
- `.claude/skills/` (only loaded when invoked)

## Target Budgets

| Component | Ideal | Warning | Fail |
|-----------|-------|---------|------|
| CLAUDE.md | ≤80 lines | >80 lines | >150 lines |
| Single agent | ≤25 lines | >25 lines | >50 lines |
| Total agents | ≤180 lines | >180 lines | >300 lines |
| Single rule | ≤15 lines | >15 lines | >30 lines |
| Total rules | ≤60 lines | >60 lines | >100 lines |
| settings.json | ≤50 lines | >50 lines | >100 lines |
| **Total config** | **≤400 lines** | **>400 lines** | **>600 lines** |
| **Est. tokens** | **≤1,600** | **>1,600** | **>2,400** |

## Anti-Patterns Detected

1. **Bloated CLAUDE.md** — Over 150 lines. Move detailed patterns to ARCHITECTURE.md or rules.
2. **Verbose agents** — Over 50 lines. Agent definitions should be directives, not tutorials.
3. **Aggressive hooks** — Hooks that block legitimate operations (e.g., blocking all .md file writes).
4. **Stale rules** — Rules referencing `src/pages/` when project uses `src/app/` (Next.js migration).
5. **Phantom hooks** — Hooks calling scripts that don't exist.
6. **Duplicate coverage** — Two agents or rules covering the same scope.
7. **Missing handoff** — No `.claude/handoff.md` means context is lost between sessions.

## Comparison Baselines

Used by `audit.py --compare` to contextualize scores:

| Config Source | Estimated Tokens | Notes |
|---------------|-----------------|-------|
| ECC (default) | ~7,200 | 13 agents, extensive CLAUDE.md |
| Starter Kit | ~5,100 | 9 agents, standard profile |
| Launchpad | ~2,800 | 6 agents, optimized |
| Hand-crafted (typical) | ~1,200–4,000 | Varies wildly |
