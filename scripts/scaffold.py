#!/usr/bin/env python3
"""
claude-launchpad scaffold script v4.0.0

Creates the .claude/ configuration directory with agents, rules, hooks, skills,
commands, and supporting files — all with real values from the interview.

Usage:
    python scaffold.py --project-name "my-app" --frontend nextjs --backend integrated \
        --database postgresql --auth clerk --output-dir .
"""

import argparse
import json
import re
import sys
from datetime import datetime
from pathlib import Path

PROJECT_NAME_PATTERN = re.compile(r'^[a-zA-Z0-9][a-zA-Z0-9._-]*$')

# Allowlist for user-provided commands (--lint-cmd, --test-cmd)
# Only permit known safe command patterns to prevent injection
# Supports `--` arg separator (e.g., `npm run lint -- --fix`)
SAFE_CMD_PATTERN = re.compile(
    r'^(?:npm|npx|pnpm|yarn|bun) (?:run |exec |dlx )?[a-zA-Z0-9:_-]+(?:\s+(?:--|--[a-zA-Z0-9_-]+(?:=[a-zA-Z0-9_./-]+)?))*$'
    r'|^(?:pytest|ruff|mypy|black|flake8|pylint|isort)(?:\s+[a-zA-Z0-9_./-]+)*(?:\s+(?:--|--[a-zA-Z0-9_-]+(?:=[a-zA-Z0-9_./-]+)?))*$'
    r'|^(?:go (?:test|vet|fmt)|golangci-lint run)(?:\s+[./a-zA-Z0-9_-]+)*$'
    r'|^(?:cargo (?:test|clippy|fmt|check))(?:\s+--[a-zA-Z0-9_-]+)*$'
    r'|^(?:bundle exec (?:rubocop|rspec|rails test))(?:\s+[a-zA-Z0-9_./-]+)*$'
    r'|^(?:rails (?:test|db:migrate))(?:\s+[a-zA-Z0-9_./-]+)*$'
    r'|^(?:flutter (?:test|analyze|build))(?:\s+[a-zA-Z0-9_./-]+)*$'
    r'|^make\s+[a-zA-Z0-9_-]+$'
)


# Pinned MCP package versions (update periodically)
MCP_VERSIONS = {
    "server-github": "@modelcontextprotocol/server-github@2025.1.1",
    "server-gitlab": "@modelcontextprotocol/server-gitlab@2025.1.1",
    "server-postgres": "@modelcontextprotocol/server-postgres@2025.1.1",
    "server-sqlite": "@modelcontextprotocol/server-sqlite@2025.1.1",
    "server-filesystem": "@modelcontextprotocol/server-filesystem@2025.1.1",
    "server-sentry": "@modelcontextprotocol/server-sentry@2025.1.1",
}

# Valid top-level keys in settings.json
VALID_SETTINGS_KEYS = {"hooks", "mcpServers", "permissions", "env", "model", "apiKey"}

# ── Slash Commands ───────────────────────────────────────────────────────

def cmd_status():
    return """---
description: Show project status — recent changes, test health, open TODOs
---

Give me a quick project status report:
1. Check `git status` and `git log --oneline -5` for recent activity
2. Read `.claude/handoff.md` for current state
3. Run the test suite to check health
4. Look for TODO/FIXME in recently changed files

Present: recent changes, branch state, test health, open TODOs, next action.
"""

def cmd_handoff():
    return """---
description: Update session handoff document for context preservation
---

Update `.claude/handoff.md` with the current session state:
1. Read the current handoff document
2. Update "What's Working" with completed items
3. Update "In Progress" with current work
4. Update "Known Issues" with any problems found
5. Update "Next Steps" with recommended actions
6. Save the file

This preserves context for the next session.
"""

def cmd_new_feature():
    return """---
description: Start a new feature with proper branching and planning
---

Starting new feature: $ARGUMENTS

1. Create branch: `git checkout -b feature/$ARGUMENTS`
2. Read ARCHITECTURE.md for current design
3. Read `.claude/handoff.md` for project state
4. Plan: what files change, what's new, what tests needed, any DB changes?
5. Present plan for approval before writing code.
"""

def cmd_fix_bug():
    return """---
description: Systematically diagnose and fix a bug
---

Investigating: $ARGUMENTS

Follow the debugger methodology:
1. **Reproduce**: Trigger the bug
2. **Isolate**: Trace data flow, find the boundary where it breaks
3. **Diagnose**: Identify root cause (don't guess)
4. **Fix**: Minimal fix for root cause
5. **Test**: Write regression test that fails without fix
6. **Verify**: Run full test suite
"""

def cmd_audit():
    return """---
description: Audit Claude Code config for health, token cost, and issues
---

Run the Claude Launchpad auditor on this project:
1. Run the audit script against the current project
2. Display the health report with token estimates
3. For each issue, suggest the specific fix
4. If $ARGUMENTS contains "--fix", apply safe fixes automatically
"""

def cmd_tdd():
    return """---
description: Start a TDD red-green-refactor cycle
---

TDD cycle for: $ARGUMENTS

1. **Red**: Write a failing test that describes the desired behavior
2. **Green**: Write the minimum code to make the test pass
3. **Refactor**: Clean up without changing behavior, re-run tests
4. Repeat until the feature is complete

Run tests after every change. Never skip the refactor step.
"""

def cmd_pipeline():
    return """---
description: Run full feature pipeline from spec to PR
---

Feature: $ARGUMENTS

Pipeline:
1. **Architect**: Design the solution (use architect agent)
2. **Security**: Review the design (use security agent)
3. **Implement**: Build it following the blueprint
4. **Test**: Write tests (use testing agent)
5. **Review**: Code review (use reviewer agent)
6. **Push**: Branch, commit, PR (use push agent)
"""


# ── Skills ───────────────────────────────────────────────────────────────

def get_skills(args):
    """Return list of (name, content) tuples for skills based on interview answers."""
    skills = []
    fe = args.frontend
    be = args.backend
    db = args.database

    # Always generated
    skills.append(("simplify", f"""---
description: Review code for unnecessary complexity and suggest simpler alternatives
---

Review $ARGUMENTS for complexity:
1. Over-engineered patterns, unnecessary abstractions, premature optimization
2. Dead code, unused imports, redundant assertions
3. Functions >50 lines that could decompose
4. Stack-specific anti-patterns ({fe}/{be})

Prioritize: high-impact simplifications first. Don't sacrifice readability for cleverness.
"""))

    skills.append(("generate-feature", f"""---
description: Scaffold a complete feature module with all layers
---

Generate feature: $ARGUMENTS

1. Read ARCHITECTURE.md for current patterns
2. Identify layers needed (UI, API, DB, types, tests)
3. Generate each file following existing conventions
4. Include imports, types, error handling, validation
5. Add tests for core logic
6. Update barrel exports or route registrations

Stack: {fe} / {be} / {db}. Follow existing patterns — don't invent new ones.
"""))

    # Frontend skills
    if fe and fe != "none":
        lib = {"nextjs": "React TSX", "react-vite": "React TSX", "vue": "Vue SFC", "sveltekit": "Svelte"}.get(fe, "component")

        skills.append(("generate-component", f"""---
description: Scaffold a {lib} component with types and tests
---

Create {lib} component: $ARGUMENTS

1. Component file in the right directory (check existing components)
2. TypeScript types/props interface
3. Default export, proper styling (match project approach)
4. Co-located test file
5. Add to barrel export if one exists

Framework: {fe}. Keep under 150 lines — split if larger.
"""))

        skills.append(("generate-page", f"""---
description: Scaffold a new page/route with data fetching and SEO
---

Create page: $ARGUMENTS

1. Page file in routing directory
2. Metadata/SEO (title, description)
3. Data fetching (match project pattern)
4. Loading and error states
5. Auth protection if needed
6. Basic test

Framework: {fe}. Follow existing page patterns.
"""))

    # Backend / API skills
    if be and be not in ("none", "integrated"):
        api = {"node-express": "Express", "node-fastify": "Fastify", "python-fastapi": "FastAPI", "python-django": "Django", "go": "Go", "rust-actix": "Actix-web", "ruby-rails": "Rails"}.get(be, "API")
        skills.append(("generate-endpoint", f"""---
description: Scaffold a {api} endpoint with validation and tests
---

Create {api} endpoint: $ARGUMENTS

1. Route/handler following existing patterns
2. Input validation (project's validation library)
3. Error handling with proper HTTP status codes
4. Auth/authz checks if needed
5. Request/response types
6. Integration tests

Framework: {be}. Follow RESTful conventions.
"""))
    elif fe in ("nextjs", "sveltekit"):
        rt = "Next.js API route" if fe == "nextjs" else "SvelteKit endpoint"
        skills.append(("generate-endpoint", f"""---
description: Scaffold a {rt} with validation and tests
---

Create {rt}: $ARGUMENTS

1. Route file in API directory
2. Input validation and type checking
3. Error handling with proper status codes
4. Auth checks if needed
5. Request/response types
6. Tests

Framework: {fe} (integrated API).
"""))

    # Database skills
    if db and db != "none":
        skills.append(("generate-model", f"""---
description: Define a database model with migration and seed data
---

Create model: $ARGUMENTS

1. Check ORM/schema tool in project
2. Define schema with proper types and constraints
3. Add relationships to existing models if needed
4. Generate migration
5. Create seed data
6. Add TypeScript types / Python dataclasses
7. Create basic CRUD query layer

Database: {db}. Follow existing schema patterns.
"""))

        skills.append(("generate-crud", f"""---
description: Generate complete CRUD operations for a model
---

CRUD for: $ARGUMENTS

1. Find model definition
2. Create: create, getById, getAll (paginated), update, delete
3. Input validation for create/update
4. Error handling (not found, validation, conflicts)
5. Filtering and sorting for list
6. Tests for each operation
7. API routes exposing operations

Database: {db}. Follow existing data access patterns.
"""))

    # Auth skills
    auth = args.auth or "none"
    if auth != "none":
        skills.append(("add-protected-route", f"""---
description: Add auth protection to a route using {auth}
---

Protect: $ARGUMENTS

1. Check existing auth middleware/guards ({auth})
2. Add authentication check (redirect if not authenticated)
3. Add authorization if role-based access needed
4. Handle loading states during auth check
5. Handle expired sessions
6. Test both authenticated and unauthenticated cases

Auth: {auth}. Follow existing auth patterns.
"""))

    # AI skills
    if args.ai:
        skills.append(("prompt-engineer", """---
description: Design, test, and iterate on an AI/LLM prompt
---

Design prompt for: $ARGUMENTS

1. Define task: what input, what output expected
2. Write initial prompt: system instructions, I/O format, examples
3. Create 5 test cases (normal, edge, adversarial)
4. Run tests and evaluate
5. Iterate on failures
6. Document final prompt with usage notes

Version prompts. Explain changes in comments.
"""))

        skills.append(("add-ai-feature", """---
description: Add an AI feature with streaming, error handling, and fallbacks
---

Add AI feature: $ARGUMENTS

1. Design prompt (use prompt-engineer skill if complex)
2. Create API route/handler
3. Implement streaming if user-facing
4. Error handling: rate limits, timeouts, service unavailable
5. Input validation and output parsing
6. Caching if responses are deterministic
7. Cost tracking/logging
8. Tests with mocked AI responses
"""))

    return skills


# ── MCP Servers ─────────────────────────────────────────────────────────

def get_mcp_servers(args):
    """Return MCP server configurations based on interview answers."""
    servers = {}

    git = args.git_platform or "none"

    # GitHub MCP — most common, high value
    if git == "github":
        servers["github"] = {
            "command": "npx",
            "args": ["-y", MCP_VERSIONS["server-github"]],
            "env": {"GITHUB_PERSONAL_ACCESS_TOKEN": "${GITHUB_TOKEN}"}
        }

    # GitLab MCP
    if git == "gitlab":
        servers["gitlab"] = {
            "command": "npx",
            "args": ["-y", MCP_VERSIONS["server-gitlab"]],
            "env": {
                "GITLAB_PERSONAL_ACCESS_TOKEN": "${GITLAB_TOKEN}",
                "GITLAB_API_URL": "https://gitlab.com/api/v4"
            }
        }

    # Database MCP servers
    db = args.database or "none"
    if db in ("postgresql", "sqlite"):
        pkg = MCP_VERSIONS["server-postgres"] if db == "postgresql" else MCP_VERSIONS["server-sqlite"]
        servers["database"] = {
            "command": "npx",
            "args": ["-y", pkg],
            "env": {"DATABASE_URL": "${DATABASE_URL}"} if db != "sqlite" else {}
        }
    # Note: MySQL MCP not included — no verified official package yet

    # Filesystem MCP — useful for docs-heavy projects
    # Only add if docs/ or specs/ directories actually exist (checked at generation time)
    if args.team:
        output_dir = Path(args.output_dir).resolve()
        project_dir = output_dir / args.project_name if args.create_root else output_dir
        fs_paths = []
        for d in ["docs", "specs", "design"]:
            if (project_dir / d).exists():
                fs_paths.append(f"./{d}")
        if not fs_paths:
            fs_paths = ["./docs"]  # Default — will be created by scaffold
        servers["filesystem"] = {
            "command": "npx",
            "args": ["-y", MCP_VERSIONS["server-filesystem"]] + fs_paths
        }

    # Sentry MCP — if user specified sentry in their monitoring
    if getattr(args, 'sentry', False):
        servers["sentry"] = {
            "command": "npx",
            "args": ["-y", MCP_VERSIONS["server-sentry"]],
            "env": {"SENTRY_AUTH_TOKEN": "${SENTRY_AUTH_TOKEN}"}
        }

    return servers


# ── Hooks ───────────────────────────────────────────────────────────────

def get_hooks(args):
    """Return hooks configuration based on interview answers."""
    hooks = {}

    # PreToolUse hooks
    pre_hooks = []

    # All projects: block force-push to main
    pre_hooks.append({
        "matcher": "Bash",
        "hooks": [{
            "type": "block",
            "pattern": "git push.*--force.*main|git push.*--force.*master|git push -f.*main|git push -f.*master"
        }]
    })

    # All projects: block committing secrets via git
    # Scoped to Bash + git add/commit to avoid false positives in source code edits
    pre_hooks.append({
        "matcher": "Bash",
        "hooks": [{
            "type": "block",
            "pattern": "git\\s+(?:add|commit).*(?:sk-[a-zA-Z0-9]{20,}|ghp_[a-zA-Z0-9]{36}|AKIA[0-9A-Z]{16})"
        }]
    })

    # Conventional commits: validate commit message format
    # Only blocks `git commit -m` with non-conventional prefix; allows --amend, -F, editor mode
    if args.conventional_commits:
        pre_hooks.append({
            "matcher": "Bash",
            "hooks": [{
                "type": "block",
                "pattern": "git commit\\s+-m\\s+['\"](?!(feat|fix|refactor|test|docs|chore|ci|style|perf|build|revert)[(:!])"
            }]
        })

    if pre_hooks:
        hooks["PreToolUse"] = pre_hooks

    # PostToolUse hooks
    post_hooks = []

    # Auto-lint on source file edits (skip config/docs via jq + file extension check)
    # Claude Code pipes JSON to stdin: { "tool_input": { "file_path": "..." }, ... }
    # Falls back to running on all files if jq is not installed
    SKIP_FILTER = (
        'if command -v jq >/dev/null 2>&1; then '
        'F=$(cat | jq -r \'.tool_input.file_path // empty\'); '
        'case "$F" in *.md|*.json|*.yaml|*.yml|*.txt|*.env*|*.lock|*ignore) exit 0 ;; esac; '
        'else cat >/dev/null; fi; '
    )

    lint_cmd = getattr(args, 'lint_cmd', None)
    if lint_cmd and SAFE_CMD_PATTERN.match(lint_cmd):
        post_hooks.append({
            "matcher": "Write|Edit",
            "hooks": [{
                "type": "command",
                "command": f"{SKIP_FILTER}{lint_cmd}"
            }]
        })
    elif lint_cmd:
        print(f"  ⚠ Skipping --lint-cmd: '{lint_cmd}' doesn't match allowed patterns.", file=sys.stderr)
        print(f"    Allowed: npm/pnpm/yarn run <script>, pytest, ruff, mypy, go test, cargo test, make <target>", file=sys.stderr)

    # Auto-test on source file edits (TDD mode, skip non-source files)
    test_cmd = getattr(args, 'test_cmd', None)
    if args.tdd and test_cmd and SAFE_CMD_PATTERN.match(test_cmd):
        post_hooks.append({
            "matcher": "Write|Edit",
            "hooks": [{
                "type": "command",
                "command": f"{SKIP_FILTER}{test_cmd}"
            }]
        })
    elif args.tdd and test_cmd:
        print(f"  ⚠ Skipping --test-cmd: '{test_cmd}' doesn't match allowed patterns.", file=sys.stderr)

    if post_hooks:
        hooks["PostToolUse"] = post_hooks

    # Stop hook: remind to update handoff (only if handoff.md hasn't been updated recently)
    hooks["Stop"] = [{
        "matcher": "",
        "hooks": [{
            "type": "command",
            "command": "if [ -f .claude/handoff.md ] && [ $(find .claude/handoff.md -mmin +30 2>/dev/null | wc -l) -gt 0 ]; then echo '💡 Handoff is >30min old — consider running /handoff'; fi"
        }]
    }]

    return hooks


# ── Supporting file generators ───────────────────────────────────────────

def get_claudeignore(frontend, backend):
    """Generate .claudeignore."""
    lines = [
        "# Dependencies",
        "node_modules/", "vendor/", ".venv/", "__pycache__/",
        "",
        "# Build output",
        "dist/", "build/", ".next/", ".nuxt/", ".svelte-kit/", ".output/",
        "*.pyc", "*.pyo",
        "",
        "# Environment & secrets",
        ".env", ".env.local", ".env.*.local", "*.pem", "*.key",
        "",
        "# IDE & OS",
        ".idea/", ".vscode/", "*.swp", ".DS_Store", "Thumbs.db",
        "",
        "# Package locks",
        "package-lock.json", "pnpm-lock.yaml", "yarn.lock", "poetry.lock",
        "",
        "# Large/binary files",
        "*.min.js", "*.min.css", "*.map",
        "*.png", "*.jpg", "*.jpeg", "*.gif", "*.ico", "*.svg",
        "*.woff", "*.woff2", "*.ttf", "*.eot",
        "",
        "# Test artifacts",
        "coverage/", ".nyc_output/", "htmlcov/", ".pytest_cache/",
        "test-results/", "playwright-report/",
    ]
    return "\n".join(lines) + "\n"


def get_env_example(database, auth, ai):
    """Generate .env.example."""
    lines = ["# Environment Variables", "# Copy to .env and fill in values", ""]

    db_vars = {
        "postgresql": ["DATABASE_URL=postgresql://user:password@localhost:5432/dbname"],
        "mongodb": ["MONGODB_URI=mongodb://localhost:27017/dbname"],
        "supabase": [
            "NEXT_PUBLIC_SUPABASE_URL=https://your-project.supabase.co",
            "NEXT_PUBLIC_SUPABASE_ANON_KEY=your-anon-key",
            "SUPABASE_SERVICE_ROLE_KEY=your-service-role-key",
        ],
        "sqlite": ["DATABASE_URL=file:./dev.db"],
    }
    lines.extend(db_vars.get(database, []))
    lines.append("")

    auth_vars = {
        "clerk": ["NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY=pk_...", "CLERK_SECRET_KEY=sk_..."],
        "nextauth": ["AUTH_SECRET=generate-with-openssl-rand-base64-32", "AUTH_GOOGLE_ID=", "AUTH_GOOGLE_SECRET="],
    }
    lines.extend(auth_vars.get(auth, []))

    if ai:
        lines.extend(["", "ANTHROPIC_API_KEY=sk-ant-...", "# OPENAI_API_KEY=sk-..."])

    # MCP-related env vars
    mcp_vars = []
    if database in ("postgresql", "mysql"):
        pass  # DATABASE_URL already added above
    if auth == "none":
        pass  # No additional env vars

    return "\n".join(lines) + "\n"


def get_handoff(project_name):
    """Generate initial handoff document."""
    return f"""# Session Handoff — {project_name}

## What's Working
- Project scaffolded with Claude Launchpad
- .claude/ configuration generated

## In Progress
- (first session — nothing yet)

## Known Issues
- (none)

## Next Steps
1. Review CLAUDE.md and ARCHITECTURE.md
2. Run `/status` to verify setup
3. Start first feature with `/new-feature <feature-name>`

## Architecture Decisions
(Record key decisions here as the project evolves)
"""


# ── Main scaffold logic ─────────────────────────────────────────────────

def safe_write(filepath: Path, content: str, force: bool = False, update: bool = False, dry_run: bool = False) -> str:
    """Write a file safely with multiple modes.

    Modes:
        default:  Skip if file exists
        force:    Always overwrite
        dry_run:  Report what would happen, write nothing

    Returns: 'created', 'skipped', or 'overwritten'
    """
    existed = filepath.exists()
    if existed and not force:
        return "skipped"
    if dry_run:
        return "overwritten" if existed else "created"
    try:
        filepath.write_text(content)
    except OSError as e:
        print(f"  ✗ Failed to write {filepath.name}: {e}", file=sys.stderr)
        return "skipped"
    return "overwritten" if existed else "created"


def merge_settings(existing_path: Path, new_settings: dict) -> tuple[dict, list[str]]:
    """Merge new settings into existing settings.json without losing user config.

    Returns: (merged_dict, list_of_changes)
    """
    changes = []
    try:
        existing = json.loads(existing_path.read_text())
    except (json.JSONDecodeError, FileNotFoundError):
        return new_settings, ["Created new settings.json"]

    # Merge MCP servers — add missing, don't touch existing
    if "mcpServers" in new_settings:
        if "mcpServers" not in existing:
            existing["mcpServers"] = {}
        for name, config in new_settings["mcpServers"].items():
            if name not in existing["mcpServers"]:
                existing["mcpServers"][name] = config
                changes.append(f"Added MCP server: {name}")

    # Merge hooks — add missing hook types, don't duplicate existing matchers
    if "hooks" in new_settings:
        if "hooks" not in existing:
            existing["hooks"] = {}
        for hook_type, hook_list in new_settings["hooks"].items():
            if hook_type not in existing["hooks"]:
                existing["hooks"][hook_type] = hook_list
                changes.append(f"Added {hook_type} hooks ({len(hook_list)} rules)")
            else:
                # Add hooks with matchers that don't already exist
                existing_matchers = {h.get("matcher", "") for h in existing["hooks"][hook_type] if isinstance(h, dict)}
                for hook in hook_list:
                    if isinstance(hook, dict) and hook.get("matcher", "") not in existing_matchers:
                        existing["hooks"][hook_type].append(hook)
                        changes.append(f"Added {hook_type} hook: {hook.get('matcher', 'default')}")

    return existing, changes


def validate_settings(settings: dict) -> list[str]:
    """Validate generated settings.json structure. Returns list of warnings."""
    warnings = []
    unknown_keys = set(settings.keys()) - VALID_SETTINGS_KEYS
    if unknown_keys:
        warnings.append(f"Unknown top-level keys: {', '.join(sorted(unknown_keys))}")

    # Validate hooks structure
    hooks = settings.get("hooks", {})
    valid_hook_types = {"PreToolUse", "PostToolUse", "Stop", "Notification"}
    for hook_type in hooks:
        if hook_type not in valid_hook_types:
            warnings.append(f"Unknown hook type: {hook_type}")
        if not isinstance(hooks[hook_type], list):
            warnings.append(f"hooks.{hook_type} should be an array")
            continue
        for i, entry in enumerate(hooks[hook_type]):
            if not isinstance(entry, dict):
                warnings.append(f"hooks.{hook_type}[{i}] should be an object")
                continue
            if "hooks" not in entry:
                warnings.append(f"hooks.{hook_type}[{i}] missing 'hooks' array")

    # Validate MCP servers structure
    mcp = settings.get("mcpServers", {})
    for name, config in mcp.items():
        if not isinstance(config, dict):
            warnings.append(f"mcpServers.{name} should be an object")
            continue
        if "command" not in config:
            warnings.append(f"mcpServers.{name} missing 'command'")

    return warnings


def scaffold(args):
    """Main scaffold function."""
    output_dir = Path(args.output_dir).resolve()
    project_dir = output_dir / args.project_name if args.create_root else output_dir
    force = args.force
    update = args.update
    dry_run = getattr(args, 'dry_run', False)

    if force and update:
        print("Error: --force and --update are mutually exclusive.", file=sys.stderr)
        return 1

    if dry_run:
        print(f"DRY RUN — no files will be created or modified.\n")

    if args.create_root and not dry_run:
        project_dir.mkdir(parents=True, exist_ok=True)

    # Detect existing .claude/ and warn
    existing_claude = (project_dir / ".claude").exists()
    if existing_claude and not force and not update:
        print(f"⚠  Existing .claude/ detected in {project_dir}")
        print("   Existing files will NOT be overwritten. Only missing files will be created.")
        print("   Use --update to merge new config into existing files.")
        print("   Use --force to overwrite everything (backs up nothing — use git).\n")
    elif update:
        print(f"📦  Update mode: merging new config into existing .claude/ in {project_dir}\n")

    # Track all created files for manifest
    created_files = []

    print(f"Scaffolding {args.project_name} in {project_dir}")
    print(f"  Frontend: {args.frontend}, Backend: {args.backend}, DB: {args.database}")

    # 1. Create .claude/ structure (only create directories that don't exist)
    if not dry_run:
        for subdir in ["agents", "rules", "skills", "commands"]:
            d = project_dir / ".claude" / subdir
            if not d.exists():
                d.mkdir(parents=True, exist_ok=True)
        docs_dir = project_dir / "docs" / "blueprints"
        if not docs_dir.exists():
            docs_dir.mkdir(parents=True, exist_ok=True)
    print("  Created .claude/ directory structure")

    # 2. Slash commands
    cmds_dir = project_dir / ".claude" / "commands"
    commands = {
        "status": cmd_status(), "handoff": cmd_handoff(),
        "new-feature": cmd_new_feature(), "fix-bug": cmd_fix_bug(), "audit": cmd_audit(),
    }
    if args.tdd:
        commands["tdd"] = cmd_tdd()
    if args.team:
        commands["pipeline"] = cmd_pipeline()
    created_cmds, skipped_cmds = 0, 0
    for name, content in commands.items():
        fp = cmds_dir / f"{name}.md"
        result = safe_write(fp, content, force, dry_run=dry_run)
        if result == "skipped":
            skipped_cmds += 1
        else:
            created_cmds += 1
            created_files.append(str(fp.relative_to(project_dir)) if project_dir.exists() else f".claude/commands/{name}.md")
    msg = f"  Created {created_cmds} commands"
    if skipped_cmds:
        msg += f" (skipped {skipped_cmds} existing)"
    print(msg)

    # 3. Skills
    skills_dir = project_dir / ".claude" / "skills"
    skills = get_skills(args)
    created_skills, skipped_skills = 0, 0
    for name, content in skills:
        fp = skills_dir / f"{name}.md"
        result = safe_write(fp, content, force, dry_run=dry_run)
        if result == "skipped":
            skipped_skills += 1
        else:
            created_skills += 1
            created_files.append(f".claude/skills/{name}.md")
    msg = f"  Created {created_skills} skills"
    if skipped_skills:
        msg += f" (skipped {skipped_skills} existing)"
    print(msg)

    # 4. Supporting files
    support_files = [
        ("claudeignore", ".claudeignore", get_claudeignore(args.frontend, args.backend)),
        ("env.example", ".env.example", get_env_example(args.database, args.auth or "none", args.ai)),
        ("handoff.md", ".claude/handoff.md", get_handoff(args.project_name)),
    ]
    results = []
    for label, rel_path, content in support_files:
        result = safe_write(project_dir / rel_path, content, force, dry_run=dry_run)
        results.append((label, result))
        if result != "skipped":
            created_files.append(rel_path)
    created = [n for n, r in results if r != "skipped"]
    skipped = [n for n, r in results if r == "skipped"]
    if created:
        print(f"  Created {', '.join(created)}")
    if skipped:
        print(f"  Skipped existing: {', '.join(skipped)}")

    # 5. MCP servers + hooks
    mcp_servers = get_mcp_servers(args)
    hooks = get_hooks(args)

    # 6. settings.json with hooks + MCP
    settings = {}
    if hooks:
        settings["hooks"] = hooks
    if mcp_servers:
        settings["mcpServers"] = mcp_servers
    # Validate before writing
    schema_warnings = validate_settings(settings)
    for w in schema_warnings:
        print(f"  ⚠ Settings validation: {w}", file=sys.stderr)

    settings_path = project_dir / ".claude" / "settings.json"
    if dry_run:
        if mcp_servers:
            print(f"  Would configure {len(mcp_servers)} MCP servers: {', '.join(mcp_servers.keys())}")
        else:
            print("  No MCP servers to configure")
        created_files.append(".claude/settings.json")
    elif not settings_path.exists():
        settings_path.write_text(json.dumps(settings, indent=2) + "\n")
        created_files.append(".claude/settings.json")
        if mcp_servers:
            print(f"  Configured {len(mcp_servers)} MCP servers: {', '.join(mcp_servers.keys())}")
        else:
            print("  No MCP servers configured (add later in .claude/settings.json)")
    elif update:
        merged, changes = merge_settings(settings_path, settings)
        if changes:
            settings_path.write_text(json.dumps(merged, indent=2) + "\n")
            created_files.append(".claude/settings.json")
            for c in changes:
                print(f"  ✓ {c}")
        else:
            print("  settings.json already up to date (no new MCP servers to add)")
    elif force:
        settings_path.write_text(json.dumps(settings, indent=2) + "\n")
        created_files.append(".claude/settings.json")
        if mcp_servers:
            print(f"  Configured {len(mcp_servers)} MCP servers: {', '.join(mcp_servers.keys())}")
    else:
        print("  Skipped existing settings.json (use --update to merge, --force to overwrite)")

    # 7. Placeholder files for Claude to customize with real values
    for name in ["CLAUDE.md", "ARCHITECTURE.md"]:
        fp = project_dir / name
        result = safe_write(fp, "<!-- Generated by Claude Launchpad — Claude will customize -->\n", force, dry_run=dry_run)
        if result == "skipped":
            print(f"  Skipped existing {name}")
        else:
            created_files.append(name)
            print(f"  Created placeholder {name}")

    # 8. Config metadata (routed through safe_write for consistency)
    metadata = {
        "project_name": args.project_name,
        "frontend": args.frontend, "backend": args.backend,
        "database": args.database, "auth": args.auth or "none",
        "ai": args.ai, "hosting": args.hosting or "none",
        "git_platform": args.git_platform or "none",
        "team": args.team, "tdd": args.tdd,
        "conventional_commits": args.conventional_commits,
        "scaffolded_at": datetime.now().isoformat(),
        "version": "4.0.0",
    }
    config_path = project_dir / ".claude" / "launchpad-config.json"
    if not dry_run:
        if update and config_path.exists():
            try:
                existing_meta = json.loads(config_path.read_text())
                metadata["scaffolded_at"] = existing_meta.get("scaffolded_at", metadata["scaffolded_at"])
                metadata["updated_at"] = datetime.now().isoformat()
            except (json.JSONDecodeError, FileNotFoundError):
                pass
        result = safe_write(config_path, json.dumps(metadata, indent=2) + "\n", force=True, dry_run=False)
        if result != "skipped":
            created_files.append(".claude/launchpad-config.json")

    # 9. Write manifest of created files
    if created_files and not dry_run:
        manifest_path = project_dir / ".claude" / "launchpad-manifest.json"
        manifest = {
            "version": "4.0.0",
            "created_at": datetime.now().isoformat(),
            "files": sorted(created_files),
        }
        manifest_path.write_text(json.dumps(manifest, indent=2) + "\n")

    print(f"\nDone! {len(commands)} commands, {len(skills)} skills generated.")
    if created_files:
        print(f"  {len(created_files)} files created/updated (manifest: .claude/launchpad-manifest.json)")
    print("Next: Claude generates CLAUDE.md, agents, rules, hooks, ARCHITECTURE.md with real values.")
    return 0


def main():
    p = argparse.ArgumentParser(description="Claude Launchpad scaffolder")
    p.add_argument("--project-name", required=True)
    p.add_argument("--frontend", choices=["nextjs", "react-vite", "vue", "sveltekit", "none"], default="nextjs")
    p.add_argument("--backend", choices=["node-express", "node-fastify", "python-fastapi", "python-django", "go", "rust-actix", "ruby-rails", "integrated", "none"], default="integrated")
    p.add_argument("--database", choices=["postgresql", "mongodb", "supabase", "sqlite", "mysql", "dynamodb", "none"], default="postgresql")
    p.add_argument("--auth", choices=["clerk", "nextauth", "supabase-auth", "custom-jwt", "none"], default="none")
    p.add_argument("--hosting", choices=["vercel", "railway", "aws", "fly", "self-hosted", "none"], default="none")
    p.add_argument("--git-platform", choices=["github", "gitlab", "bitbucket", "none"], default="none")
    p.add_argument("--ai", action="store_true")
    p.add_argument("--team", action="store_true")
    p.add_argument("--tdd", action="store_true")
    p.add_argument("--conventional-commits", action="store_true")
    p.add_argument("--lint-cmd", default=None, help="Lint command (e.g., 'npm run lint')")
    p.add_argument("--test-cmd", default=None, help="Test command (e.g., 'npm run test')")
    p.add_argument("--sentry", action="store_true", help="Add Sentry MCP server")
    p.add_argument("--force", action="store_true", help="Overwrite existing files (default: skip existing)")
    p.add_argument("--update", action="store_true", help="Merge new config into existing files (add missing commands/skills/MCP)")
    p.add_argument("--dry-run", action="store_true", help="Show what would be created without writing any files")
    p.add_argument("--output-dir", default=".")
    p.add_argument("--create-root", action="store_true")
    args = p.parse_args()

    # M1: Validate project name
    if not PROJECT_NAME_PATTERN.match(args.project_name):
        print(f"Error: Invalid project name '{args.project_name}'. Use letters, numbers, dots, hyphens, underscores.", file=sys.stderr)
        sys.exit(1)

    sys.exit(scaffold(args))


if __name__ == "__main__":
    main()
