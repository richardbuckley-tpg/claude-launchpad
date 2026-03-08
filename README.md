# claude-launchpad

Lean, token-optimized Claude Code bootstrapper with a built-in Config Auditor.

**ECC gives you 65 skills. We give you 8 that actually work.**

## What Makes This Different

| | Launchpad | ECC | Starter Kit |
|---|---|---|---|
| **Est. token cost** | ~2,800 | ~7,200 | ~5,100 |
| **Agents** | 5-6 (real, parameterized) | 13 (verbose) | 9 |
| **Rules** | Path-scoped, stack-specific | Generic | None |
| **Skills** | 8-10 (stack-specific) | 65+ | 11 |
| **Config Auditor** | ✓ (unique) | ✗ | ✗ |
| **Community MCP** | Context7, Sequential Thinking | ✗ | ✗ |
| **Token budget tracking** | ✓ (context % estimate) | ✗ | ✗ |
| **Discoverability-first** | ✓ (ETH Zurich research) | ✗ | ✗ |
| **Fully rendered output** | ✓ (real values) | Partial | Presets |

Three things set Launchpad apart:

1. **Config Auditor** — `/audit` scans any `.claude/` setup (yours, ECC, hand-crafted) and scores it for health, token cost, and staleness. No one else does this.
2. **Token-optimized** — Strict line limits: CLAUDE.md ≤100 lines, agents ≤30 lines. Every generated file is lean by design.
3. **Fully rendered** — The interview captures your actual commands, paths, and patterns. Generated files contain real values, not `{placeholders}`.

## Install

Clone into your Claude Code skills directory:

```bash
# Global (available to all projects)
git clone https://github.com/yourusername/claude-launchpad.git ~/.claude/skills/claude-launchpad

# Per-project (lives in the project repo)
git clone https://github.com/yourusername/claude-launchpad.git .claude/skills/claude-launchpad
```

Trigger phrases: "bootstrap", "scaffold", "set up Claude Code", "init project", "start a project", "new app", "audit my config"

## Quick Start

### Bootstrap a New Project
Open Claude Code and say: **"Bootstrap a new project"** or **"Set up Claude Code for my project"**

Launchpad will:
1. Interview you about your stack (4 short phases)
2. Scaffold the `.claude/` directory with agents, skills, commands, hooks, rules
3. Generate CLAUDE.md and ARCHITECTURE.md with your actual values
4. Run the auditor to verify quality

### Audit an Existing Setup
Say: **"Audit my Claude Code config"** or run `/audit`

Works on any `.claude/` configuration — not just Launchpad-generated ones.

## What Gets Generated

```
your-project/
├── CLAUDE.md                     # ≤100 lines, real values
├── ARCHITECTURE.md               # Design decisions + data flow
├── .claude/
│   ├── agents/                   # 6 agents, ≤30 lines each
│   │   ├── architect.md
│   │   ├── security.md
│   │   ├── testing.md
│   │   ├── reviewer.md
│   │   ├── debugger.md
│   │   └── push.md
│   ├── rules/                    # Path-scoped, stack-specific
│   ├── commands/                 # 5-7 slash commands
│   │   ├── status.md
│   │   ├── handoff.md
│   │   ├── new-feature.md
│   │   ├── fix-bug.md
│   │   └── audit.md
│   ├── skills/                   # 8-10 stack-specific skills
│   ├── settings.json             # Hooks: lint, test, secret detection
│   ├── handoff.md                # Session context preservation
│   └── launchpad-config.json     # Interview answers
├── .claudeignore
└── .env.example
```

## Supported Stacks

**Frontend**: Next.js, React+Vite, Vue 3/Nuxt, SvelteKit
**Backend**: Express, Fastify, FastAPI, Django, Go, Rust/Actix, Ruby/Rails, integrated (Next.js/SvelteKit)
**Database**: PostgreSQL, MongoDB, Supabase, SQLite, MySQL, DynamoDB
**ORM**: Prisma, Drizzle, SQLAlchemy, Mongoose, TypeORM, Sequelize, ActiveRecord
**Auth**: Clerk, NextAuth/Auth.js, Supabase Auth, custom JWT
**Hosting**: Vercel, Railway, AWS, Fly.io, self-hosted
**MCP**: GitHub, GitLab, PostgreSQL, SQLite, Filesystem, Sentry, Context7, Sequential Thinking

## The Auditor

Run on any project:

```bash
python scripts/audit.py /path/to/project
```

Output:
```
Claude Launchpad Audit Report
────────────────────────────────────────
Health Score: 82/100

Token Budget
  CLAUDE.md              89 lines    ~356 tokens  ✓ within budget
  Agents (6)            168 lines    ~672 tokens  ✓ lean
  Rules (3)              57 lines    ~228 tokens  ✓ focused
  Settings               42 lines    ~168 tokens  ✓ clean
  ───────────────────────────────────────────────────────
  Total                 356 lines  ~1,424 tokens

Issues (0 errors, 2 warnings)
  ⚠ Rule frontend.md references src/pages/ but project uses src/app/
  ⚠ CLAUDE.md mentions "pytest" but package.json has Jest

Comparison
  ECC default:         ~7,200 tokens
  Starter Kit default: ~5,100 tokens
  Your config:         ~1,424 tokens
  (80% more efficient than ECC)
```

## File Structure

```
claude-launchpad/
├── SKILL.md              # The skill definition (~200 lines)
├── README.md
├── LICENSE
├── reference/
│   ├── stacks.md         # All stack knowledge in one file
│   ├── agents.md         # 6 agent templates
│   └── audit-rules.md    # Auditor scoring rubric
├── scripts/
│   ├── scaffold.py       # Project scaffolder
│   └── audit.py          # Config auditor
└── templates/
    ├── claude-md.md      # CLAUDE.md template
    └── architecture.md   # ARCHITECTURE.md template
```

## License

MIT
