#!/usr/bin/env python3
"""
claude-bootstrap scaffold script

Creates the base directory structure for a new project, including the .claude/
configuration directory with agents, rules, hooks, and skills.

Usage:
    python scaffold.py --project-name "my-app" --architecture monolith \
        --frontend nextjs --backend node --database postgresql --output-dir .

This script handles the deterministic parts (creating directories, writing boilerplate).
Claude customizes the content of generated files based on the interview answers.
"""

import argparse
import json
import os
import sys
from datetime import datetime
from pathlib import Path


# ── Directory structures by architecture type ──────────────────────────────

MONOLITH_NEXTJS = {
    "src/app/(auth)/login": {},
    "src/app/(auth)/register": {},
    "src/app/(dashboard)": {},
    "src/app/api": {},
    "src/components/ui": {},
    "src/components/layout": {},
    "src/lib/validations": {},
    "src/hooks": {},
    "src/types": {},
    "src/server/actions": {},
    "src/server/queries": {},
    "tests/e2e": {},
    "tests/integration": {},
    "public": {},
    "docs": {},
}

MONOLITH_REACT_VITE = {
    "src/components/ui": {},
    "src/components/layout": {},
    "src/pages": {},
    "src/hooks": {},
    "src/lib/validations": {},
    "src/stores": {},
    "src/types": {},
    "src/routes": {},
    "src/assets": {},
    "src/styles": {},
    "tests/e2e": {},
    "tests/integration": {},
    "public": {},
    "docs": {},
}

MONOLITH_VUE = {
    "src/components/ui": {},
    "src/components/layout": {},
    "src/composables": {},
    "src/views": {},
    "src/router": {},
    "src/stores": {},
    "src/lib": {},
    "src/types": {},
    "src/assets": {},
    "tests/e2e": {},
    "tests/unit": {},
    "public": {},
    "docs": {},
}

MONOLITH_SVELTEKIT = {
    "src/lib/components/ui": {},
    "src/lib/server": {},
    "src/lib/stores": {},
    "src/lib/utils": {},
    "src/lib/types": {},
    "src/routes/(auth)/login": {},
    "src/routes/(auth)/register": {},
    "src/routes/(app)": {},
    "src/routes/api": {},
    "src/params": {},
    "tests/e2e": {},
    "tests/unit": {},
    "static": {},
    "docs": {},
}

MONOLITH_NODE_EXPRESS = {
    "src/routes": {},
    "src/controllers": {},
    "src/services": {},
    "src/middleware": {},
    "src/models": {},
    "src/lib": {},
    "src/validations": {},
    "src/types": {},
    "src/utils": {},
    "tests/unit": {},
    "tests/integration": {},
    "tests/e2e": {},
    "docs": {},
}

MONOLITH_PYTHON_FASTAPI = {
    "app/api/v1": {},
    "app/core": {},
    "app/models": {},
    "app/schemas": {},
    "app/services": {},
    "app/db/migrations/versions": {},
    "app/utils": {},
    "tests/api": {},
    "tests/services": {},
    "tests/conftest": {},
    "docs": {},
}

MONOLITH_GO = {
    "cmd/server": {},
    "internal/config": {},
    "internal/handler": {},
    "internal/service": {},
    "internal/repository": {},
    "internal/model": {},
    "internal/dto": {},
    "internal/middleware": {},
    "pkg/logger": {},
    "pkg/validator": {},
    "pkg/errors": {},
    "migrations": {},
    "tests/integration": {},
    "tests/e2e": {},
    "docs": {},
}

MICROSERVICES_TEMPLATE = {
    "services/api-gateway/src": {},
    "services/user-service/src": {},
    "services/user-service/tests": {},
    "packages/shared-types/src": {},
    "packages/logger/src": {},
    "packages/errors/src": {},
    "infrastructure": {},
    "docs": {},
}

# ── Claude configuration structure ─────────────────────────────────────────

CLAUDE_DIR = {
    ".claude/agents": {},
    ".claude/rules": {},
    ".claude/skills": {},
    ".claude/commands": {},
}

MONOREPO_TURBOREPO = {
    "apps/web/src": {},
    "apps/admin/src": {},
    "packages/ui/src": {},
    "packages/config": {},
    "packages/db/src": {},
    "packages/types/src": {},
    "tooling": {},
    "docs": {},
}


# ── Boilerplate file contents ──────────────────────────────────────────────

def get_claudeignore(frontend: str, backend: str, monorepo: str = "none") -> str:
    """Generate comprehensive .claudeignore content based on stack."""
    lines = [
        "# ── Dependencies ────────────────────────────────",
        "node_modules/",
        ".pnp/",
        ".pnp.js",
        ".yarn/cache/",
        ".yarn/unplugged/",
        "",
        "# ── Build outputs ───────────────────────────────",
        "dist/",
        "build/",
        ".output/",
        "out/",
        "*.min.js",
        "*.min.css",
        "*.bundle.js",
        "",
        "# ── Caches ──────────────────────────────────────",
        ".cache/",
        ".turbo/",
        ".eslintcache",
        ".stylelintcache",
        ".parcel-cache/",
        "",
        "# ── Environment & secrets ───────────────────────",
        ".env",
        ".env.local",
        ".env.*.local",
        ".env.production",
        "*.pem",
        "*.key",
        "*.cert",
        "",
        "# ── IDE & editor ────────────────────────────────",
        ".idea/",
        ".vscode/",
        "*.swp",
        "*.swo",
        "*~",
        ".project",
        ".settings/",
        "",
        "# ── OS files ────────────────────────────────────",
        ".DS_Store",
        "Thumbs.db",
        "desktop.ini",
        "",
        "# ── Test & coverage outputs ─────────────────────",
        "coverage/",
        "test-results/",
        ".playwright/",
        ".nyc_output/",
        "junit.xml",
        "lcov.info",
        "",
        "# ── Logs ────────────────────────────────────────",
        "*.log",
        "npm-debug.log*",
        "yarn-debug.log*",
        "yarn-error.log*",
        "pnpm-debug.log*",
    ]

    # Framework-specific
    if frontend == "nextjs":
        lines.extend([
            "", "# ── Next.js ─────────────────────────────────",
            ".next/",
            ".vercel/",
            "next-env.d.ts",
        ])
    elif frontend in ("nuxt", "vue"):
        lines.extend([
            "", "# ── Nuxt/Vue ────────────────────────────────",
            ".nuxt/",
            ".output/",
            ".vue-ssg-temp/",
        ])
    elif frontend == "sveltekit":
        lines.extend([
            "", "# ── SvelteKit ───────────────────────────────",
            ".svelte-kit/",
            ".netlify/",
        ])
    elif frontend == "react-vite":
        lines.extend([
            "", "# ── Vite ────────────────────────────────────",
            ".vite/",
        ])

    # Backend-specific
    if backend in ("python-fastapi", "python-django"):
        lines.extend([
            "", "# ── Python ──────────────────────────────────",
            "__pycache__/",
            "*.py[cod]",
            "*$py.class",
            ".venv/",
            "venv/",
            "env/",
            "*.egg-info/",
            ".eggs/",
            ".mypy_cache/",
            ".ruff_cache/",
            ".pytest_cache/",
            "htmlcov/",
            "*.whl",
        ])
    elif backend == "go":
        lines.extend([
            "", "# ── Go ──────────────────────────────────────",
            "bin/",
            "vendor/",
            "*.exe",
            "*.test",
            "*.prof",
        ])

    # Monorepo-specific
    if monorepo and monorepo != "none":
        lines.extend([
            "", "# ── Monorepo ────────────────────────────────",
            ".nx/",
            "*.tsbuildinfo",
        ])

    # Database & storage
    lines.extend([
        "", "# ── Database ────────────────────────────────",
        "*.sqlite",
        "*.sqlite3",
        "*.db",
    ])

    # Large files & media
    lines.extend([
        "", "# ── Large files & media ─────────────────────",
        "*.zip",
        "*.tar.gz",
        "*.rar",
        "*.7z",
        "*.mp4",
        "*.mp3",
        "*.wav",
        "*.avi",
        "*.mov",
        "*.pdf",
        "*.iso",
        "*.dmg",
    ])

    # Generated / vendor code
    lines.extend([
        "", "# ── Generated & lock files ──────────────────",
        "*.generated.*",
        "package-lock.json",
        "pnpm-lock.yaml",
        "yarn.lock",
    ])

    # Docker
    lines.extend([
        "", "# ── Docker ──────────────────────────────────",
        "docker-data/",
        ".docker/",
    ])

    return "\n".join(lines) + "\n"


def get_mcp_config(git_platform: str = "none", database: str = "none", monitoring: str = "none") -> str:
    """Generate .mcp.json content based on integrations."""
    servers = {}

    if git_platform == "github":
        servers["github"] = {
            "command": "npx",
            "args": ["-y", "@modelcontextprotocol/server-github"],
            "env": {
                "GITHUB_PERSONAL_ACCESS_TOKEN": "${GITHUB_TOKEN}"
            }
        }

    if database == "postgresql":
        servers["postgres"] = {
            "command": "npx",
            "args": ["-y", "@modelcontextprotocol/server-postgres", "${DATABASE_URL}"]
        }
    elif database == "supabase":
        servers["supabase"] = {
            "command": "npx",
            "args": ["-y", "@supabase/mcp-server-supabase@latest", "--read-only"],
            "env": {
                "SUPABASE_ACCESS_TOKEN": "${SUPABASE_ACCESS_TOKEN}"
            }
        }

    if monitoring == "sentry":
        servers["sentry"] = {
            "command": "npx",
            "args": ["-y", "@sentry/mcp-server"],
            "env": {
                "SENTRY_AUTH_TOKEN": "${SENTRY_AUTH_TOKEN}"
            }
        }

    if not servers:
        return ""

    config = {"mcpServers": servers}
    return json.dumps(config, indent=2) + "\n"


def get_handoff_template(project_name: str) -> str:
    """Generate initial .claude/handoff.md content."""
    return f"""# Session Handoff — {project_name}

Last updated: {datetime.now().strftime("%Y-%m-%d")}
Last session focus: Initial project scaffold

## Current State

### What's Working
- Project scaffolded with claude-bootstrap
- Claude Code configuration (.claude/) in place

### What's In Progress
- Initial project setup and configuration

### What's Blocked
- (nothing yet)

## Architecture Decisions Made This Session
- (decisions from bootstrap interview will be documented here)

## Key Files Changed
- All files — initial scaffold

## Known Issues
- (none yet)

## Next Steps (Priority Order)
1. Review CLAUDE.md and customize for your specific needs
2. Install dependencies and verify the project builds
3. Start your first feature with `/new-feature`

## Environment Notes
- (add any environment-specific notes here)
"""


def get_status_command() -> str:
    """Generate .claude/commands/status.md content."""
    return """---
description: Show project status — what's working, what's in progress, recent changes
---

Give me a quick project status report:

1. Check `git status` and `git log --oneline -5` for recent activity
2. Read `.claude/handoff.md` for current state
3. Check for any failing tests by running the test suite
4. Look for TODO/FIXME comments in recently changed files

Present a concise status with:
- Recent changes (last 5 commits)
- Current branch and any uncommitted work
- Test health (passing/failing)
- Open TODOs in recently changed files
- Next recommended action
"""


def get_handoff_command() -> str:
    """Generate .claude/commands/handoff.md content."""
    return """---
description: Update the handoff document with current session state for the next session
---

Read the current `.claude/handoff.md` file if it exists.

Review all changes made in this session by examining:
1. `git diff` — what code changed
2. `git log --oneline -10` — recent commits
3. Any open TODOs or FIXMEs in recently changed files

Update `.claude/handoff.md` with:
- Move completed items from "In Progress" to "What's Working"
- Update "In Progress" with current status
- Add any new architecture decisions
- List key files changed with brief descriptions
- Update "Next Steps" based on what was accomplished
- Add any new known issues discovered

Keep it concise — this is a handoff doc, not a journal. Focus on what the next session
needs to know to pick up without re-reading the entire codebase.
"""


def get_new_feature_command() -> str:
    """Generate .claude/commands/new-feature.md content."""
    return """---
description: Start a new feature with proper branching and planning
---

Starting a new feature: $ARGUMENTS

1. Create a feature branch: `git checkout -b feature/$ARGUMENTS`
2. Read ARCHITECTURE.md to understand current system design
3. Read `.claude/handoff.md` for current project state
4. Create a brief plan:
   - What files need to change?
   - What new files are needed?
   - What tests should be written?
   - Any database changes needed?
5. Present the plan for approval before writing code
"""


def get_tdd_command() -> str:
    """Generate .claude/commands/tdd.md content."""
    return """---
description: Start a TDD cycle for a feature or behavior
---

Starting TDD cycle for: $ARGUMENTS

1. Read the relevant spec, ticket, or requirement
2. List all testable behaviors for this feature
3. For each behavior, follow red-green-refactor:
   a. Write a failing test (RED)
   b. Run tests to confirm failure
   c. Write minimum code to pass (GREEN)
   d. Run tests to confirm passing
   e. Refactor if needed
   f. Run tests to confirm still passing
4. After all behaviors are covered, run full test suite
5. Report: tests written, coverage change, any issues

Use worktree isolation for this work.
"""


def get_pipeline_command() -> str:
    """Generate .claude/commands/pipeline.md content."""
    return """---
description: Run the full feature implementation pipeline from spec to PR
---

Running feature pipeline for: $ARGUMENTS

## Phase 1: Architecture (CTO Agent)
- Read the feature requirement
- Produce a technical blueprint with data models, API contracts, and component designs
- Save blueprint to `docs/blueprints/`

## Phase 2: Work Breakdown
- Break blueprint into implementation phases
- Sequence tasks with dependencies
- Identify parallelizable work
- Save plan to `docs/plans/`

## Phase 3: Security Review (Pre-implementation)
- Review the proposed architecture for vulnerabilities
- Flag security concerns BEFORE code is written

## Phase 4: Implementation
For each task in the work breakdown:
1. Write tests first (if TDD enabled)
2. Implement the code
3. Run tests to verify

## Phase 5: Code Review
- Check correctness, performance, maintainability
- Verify test coverage and architectural fit

## Phase 6: Push
- Create branch, stage, commit with conventional message, push
- Create PR with blueprint context
"""


def get_fix_bug_command() -> str:
    """Generate .claude/commands/fix-bug.md content."""
    return """---
description: Systematically diagnose and fix a bug
---

Investigating bug: $ARGUMENTS

Follow the debugger agent methodology:
1. **Reproduce**: Understand how to trigger the bug
2. **Isolate**: Find the minimal reproduction case
3. **Diagnose**: Read relevant code and identify root cause
4. **Fix**: Make the minimal fix needed
5. **Test**: Write a regression test that fails without the fix
6. **Verify**: Run the full test suite to ensure no regressions

Never guess at fixes. Always investigate first.
"""


def get_env_example(database: str, auth: str, ai: bool = False, storage: str = "none") -> str:
    """Generate .env.example content."""
    lines = [
        "# ── Application ──────────────────────────────",
        "NODE_ENV=development",
        "PORT=3000",
        "APP_URL=http://localhost:3000",
        "",
    ]

    if database in ("postgresql", "supabase"):
        lines.extend([
            "# ── Database ─────────────────────────────────",
            "DATABASE_URL=postgresql://user:password@localhost:5432/dbname",
            "",
        ])
    elif database == "mongodb":
        lines.extend([
            "# ── Database ─────────────────────────────────",
            "MONGODB_URI=mongodb://localhost:27017/dbname",
            "",
        ])
    elif database == "dynamodb":
        lines.extend([
            "# ── Database (DynamoDB) ──────────────────────",
            "AWS_REGION=us-east-1",
            "AWS_ACCESS_KEY_ID=local",
            "AWS_SECRET_ACCESS_KEY=local",
            "DYNAMODB_ENDPOINT=http://localhost:8000  # Remove in production (uses AWS default)",
            "DYNAMODB_TABLE_NAME=your-table-name",
            "",
        ])

    if database == "supabase":
        lines.extend([
            "# ── Supabase ─────────────────────────────────",
            "NEXT_PUBLIC_SUPABASE_URL=https://your-project.supabase.co",
            "NEXT_PUBLIC_SUPABASE_ANON_KEY=your-anon-key",
            "SUPABASE_SERVICE_ROLE_KEY=your-service-role-key",
            "",
        ])

    if auth == "clerk":
        lines.extend([
            "# ── Authentication (Clerk) ──────────────────",
            "NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY=pk_...",
            "CLERK_SECRET_KEY=sk_...",
            "CLERK_WEBHOOK_SECRET=whsec_...",
            "",
        ])
    elif auth == "nextauth":
        lines.extend([
            "# ── Authentication (Auth.js) ────────────────",
            "AUTH_SECRET=generate-with-openssl-rand-base64-32",
            "AUTH_GOOGLE_ID=",
            "AUTH_GOOGLE_SECRET=",
            "",
        ])
    elif auth == "custom-jwt":
        lines.extend([
            "# ── Authentication (JWT) ────────────────────",
            "JWT_SECRET=generate-a-long-random-string",
            "JWT_EXPIRES_IN=15m",
            "JWT_REFRESH_SECRET=generate-a-different-long-random-string",
            "JWT_REFRESH_EXPIRES_IN=7d",
            "",
        ])

    if storage == "s3":
        lines.extend([
            "# ── Object Storage (S3) ─────────────────────",
            "S3_BUCKET=your-bucket-name",
            "S3_REGION=us-east-1",
            "S3_ACCESS_KEY_ID=",
            "S3_SECRET_ACCESS_KEY=",
            "# S3_ENDPOINT=  # Only for S3-compatible (R2, MinIO)",
            "# CDN_URL=https://cdn.yourdomain.com",
            "",
        ])
    elif storage == "r2":
        lines.extend([
            "# ── Object Storage (Cloudflare R2) ──────────",
            "R2_BUCKET=your-bucket-name",
            "R2_ACCOUNT_ID=your-account-id",
            "R2_ACCESS_KEY_ID=",
            "R2_SECRET_ACCESS_KEY=",
            "R2_ENDPOINT=https://<account-id>.r2.cloudflarestorage.com",
            "",
        ])
    elif storage == "minio":
        lines.extend([
            "# ── Object Storage (MinIO) ──────────────────",
            "MINIO_ENDPOINT=http://localhost:9000",
            "MINIO_ACCESS_KEY=minioadmin",
            "MINIO_SECRET_KEY=minioadmin",
            "MINIO_BUCKET=your-bucket-name",
            "",
        ])

    if ai:
        lines.extend([
            "# ── AI/LLM ─────────────────────────────────",
            "ANTHROPIC_API_KEY=sk-ant-...",
            "# OPENAI_API_KEY=sk-...",
            "",
        ])

    lines.extend([
        "# ── External Services ────────────────────────",
        "# STRIPE_SECRET_KEY=sk_test_...",
        "# STRIPE_WEBHOOK_SECRET=whsec_...",
        "# RESEND_API_KEY=re_...",
        "# S3_BUCKET=",
        "# S3_REGION=",
        "# REDIS_URL=redis://localhost:6379",
    ])

    return "\n".join(lines) + "\n"


def get_readme(project_name: str, description: str) -> str:
    """Generate a minimal README.md."""
    return f"""# {project_name}

{description}

## Getting Started

1. Clone the repository
2. Copy `.env.example` to `.env` and fill in the values
3. Install dependencies: `npm install` (or `pnpm install`)
4. Start the development server: `npm run dev`

## Architecture

See [ARCHITECTURE.md](./ARCHITECTURE.md) for detailed architecture documentation.

## Claude Code

This project is optimized for development with [Claude Code](https://claude.ai/claude-code).
The `.claude/` directory contains agents, rules, hooks, and skills tailored to this project.

To get started with Claude Code:
1. Open the project in your terminal
2. Run `claude` to start a session
3. Claude will automatically read the CLAUDE.md and .claude/ configuration
"""


# ── Main scaffold logic ───────────────────────────────────────────────────

def get_structure(architecture: str, frontend: str, backend: str) -> dict:
    """Select the appropriate directory structure."""
    if architecture == "microservices":
        return MICROSERVICES_TEMPLATE

    # Map frontend/backend to structure
    structure_map = {
        "nextjs": MONOLITH_NEXTJS,
        "react-vite": MONOLITH_REACT_VITE,
        "vue": MONOLITH_VUE,
        "sveltekit": MONOLITH_SVELTEKIT,
        "node-express": MONOLITH_NODE_EXPRESS,
        "python-fastapi": MONOLITH_PYTHON_FASTAPI,
        "go": MONOLITH_GO,
    }

    # Use frontend structure if available, otherwise backend
    if frontend in structure_map:
        return structure_map[frontend]
    elif backend in structure_map:
        return structure_map[backend]
    else:
        # Fallback to a generic structure
        return MONOLITH_NEXTJS


def create_directories(base_path: Path, structure: dict):
    """Recursively create directories from a structure dict."""
    for name, children in structure.items():
        dir_path = base_path / name
        dir_path.mkdir(parents=True, exist_ok=True)
        if children:
            create_directories(dir_path, children)


def scaffold(args):
    """Main scaffold function."""
    output_dir = Path(args.output_dir).resolve()
    project_dir = output_dir / args.project_name if args.create_root else output_dir

    if args.create_root:
        project_dir.mkdir(parents=True, exist_ok=True)

    print(f"Scaffolding {args.project_name} in {project_dir}")
    print(f"  Architecture: {args.architecture}")
    print(f"  Frontend: {args.frontend}")
    print(f"  Backend: {args.backend}")
    print(f"  Database: {args.database}")
    if args.monorepo and args.monorepo != "none":
        print(f"  Monorepo: {args.monorepo}")

    # 1. Create project structure
    if args.monorepo and args.monorepo != "none":
        structure = MONOREPO_TURBOREPO
        print("  Using monorepo structure")
    else:
        structure = get_structure(args.architecture, args.frontend, args.backend)
    create_directories(project_dir, structure)
    print(f"  Created {len(structure)} directories")

    # 2. Create .claude/ configuration structure
    create_directories(project_dir, CLAUDE_DIR)
    print("  Created .claude/ directory structure")

    # 3. Create .claudeignore
    claudeignore = get_claudeignore(
        args.frontend, args.backend,
        args.monorepo if args.monorepo else "none"
    )
    (project_dir / ".claudeignore").write_text(claudeignore)
    print("  Created .claudeignore")

    # 4. Create .env.example
    env_example = get_env_example(
        args.database,
        args.auth if args.auth else "none",
        args.ai,
        args.storage if args.storage else "none"
    )
    (project_dir / ".env.example").write_text(env_example)
    print("  Created .env.example")

    # 5. Create README.md
    description = args.description if args.description else f"A {args.frontend} project"
    readme = get_readme(args.project_name, description)
    (project_dir / "README.md").write_text(readme)
    print("  Created README.md")

    # 6. Create placeholder files for Claude to customize
    # These are created empty — Claude fills them with customized content
    placeholders = [
        "CLAUDE.md",
        "ARCHITECTURE.md",
        ".claude/settings.json",
    ]
    for placeholder in placeholders:
        filepath = project_dir / placeholder
        if not filepath.exists():
            if placeholder.endswith(".json"):
                filepath.write_text("{}\n")
            else:
                filepath.write_text(f"<!-- Generated by claude-bootstrap — customize this file -->\n")
    print("  Created placeholder files for Claude to customize")

    # 7. Create slash commands
    commands_dir = project_dir / ".claude" / "commands"
    commands_dir.mkdir(parents=True, exist_ok=True)

    (commands_dir / "status.md").write_text(get_status_command())
    (commands_dir / "handoff.md").write_text(get_handoff_command())
    (commands_dir / "new-feature.md").write_text(get_new_feature_command())
    (commands_dir / "fix-bug.md").write_text(get_fix_bug_command())
    cmds_created = ["/status", "/handoff", "/new-feature", "/fix-bug"]

    if args.tdd:
        (commands_dir / "tdd.md").write_text(get_tdd_command())
        cmds_created.append("/tdd")

    if args.team:
        (commands_dir / "pipeline.md").write_text(get_pipeline_command())
        cmds_created.append("/pipeline")

    print(f"  Created slash commands: {', '.join(cmds_created)}")

    # 7b. Create docs directories for agent coordination
    docs_dir = project_dir / "docs"
    docs_dir.mkdir(parents=True, exist_ok=True)
    if args.team:
        (docs_dir / "blueprints").mkdir(exist_ok=True)
        (docs_dir / "plans").mkdir(exist_ok=True)
        (docs_dir / "security-reviews").mkdir(exist_ok=True)
        (docs_dir / "code-reviews").mkdir(exist_ok=True)
        print("  Created docs/ subdirectories for agent coordination")

    # 8. Create session handoff document
    handoff = get_handoff_template(args.project_name)
    (project_dir / ".claude" / "handoff.md").write_text(handoff)
    print("  Created .claude/handoff.md (session handoff)")

    # 9. Create MCP configuration (if applicable)
    git_platform = args.git_platform if args.git_platform else "none"
    monitoring = args.monitoring if args.monitoring else "none"
    mcp_config = get_mcp_config(git_platform, args.database, monitoring)
    if mcp_config:
        if args.team:
            # For teams: .mcp.json.example (not committed directly)
            (project_dir / ".mcp.json.example").write_text(mcp_config)
            print("  Created .mcp.json.example (copy to .mcp.json and fill in values)")
        else:
            (project_dir / ".mcp.json").write_text(mcp_config)
            print("  Created .mcp.json (MCP server configuration)")

    # 10. Write scaffold metadata (for Claude to reference)
    metadata = {
        "project_name": args.project_name,
        "description": description,
        "architecture": args.architecture,
        "frontend": args.frontend,
        "backend": args.backend,
        "database": args.database,
        "auth": args.auth if args.auth else "none",
        "storage": args.storage if args.storage else "none",
        "ai_enabled": args.ai,
        "git_platform": git_platform,
        "monitoring": monitoring,
        "team": args.team,
        "monorepo": args.monorepo if args.monorepo else "none",
        "tdd": args.tdd,
        "conventional_commits": args.conventional_commits,
        "scaffolded_at": datetime.now().isoformat(),
        "scaffold_version": "3.0.0",
    }
    metadata_path = project_dir / ".claude" / "bootstrap-config.json"
    metadata_path.write_text(json.dumps(metadata, indent=2) + "\n")
    print("  Saved bootstrap configuration to .claude/bootstrap-config.json")

    print(f"\nScaffolding complete! {args.project_name} is ready for Claude to customize.")
    print("Next: Claude will generate CLAUDE.md, agents, rules, hooks, MCP config, and architecture docs.")

    return 0


def main():
    parser = argparse.ArgumentParser(
        description="Scaffold a new project for Claude Code development"
    )
    parser.add_argument("--project-name", required=True, help="Project name")
    parser.add_argument("--description", default="", help="Project description")
    parser.add_argument(
        "--architecture",
        choices=["monolith", "microservices"],
        default="monolith",
        help="Architecture type"
    )
    parser.add_argument(
        "--frontend",
        choices=["nextjs", "react-vite", "vue", "sveltekit", "none"],
        default="nextjs",
        help="Frontend framework"
    )
    parser.add_argument(
        "--backend",
        choices=["node-express", "node-fastify", "python-fastapi", "python-django", "go", "integrated", "none"],
        default="integrated",
        help="Backend framework (use 'integrated' for full-stack frameworks like Next.js)"
    )
    parser.add_argument(
        "--database",
        choices=["postgresql", "mongodb", "supabase", "sqlite", "mysql", "dynamodb", "none"],
        default="postgresql",
        help="Database"
    )
    parser.add_argument(
        "--storage",
        choices=["s3", "r2", "minio", "supabase-storage", "uploadthing", "none"],
        default="none",
        help="Object storage provider"
    )
    parser.add_argument(
        "--auth",
        choices=["clerk", "nextauth", "supabase-auth", "custom-jwt", "none"],
        default="none",
        help="Authentication provider"
    )
    parser.add_argument("--ai", action="store_true", help="Project uses AI/LLM integration")
    parser.add_argument(
        "--git-platform",
        choices=["github", "gitlab", "bitbucket", "none"],
        default="none",
        help="Git hosting platform (enables MCP server config)"
    )
    parser.add_argument(
        "--monitoring",
        choices=["sentry", "datadog", "none"],
        default="none",
        help="Monitoring platform (enables MCP server config)"
    )
    parser.add_argument(
        "--monorepo",
        choices=["turborepo", "nx", "pnpm-workspaces", "none"],
        default="none",
        help="Monorepo tool (changes directory structure)"
    )
    parser.add_argument("--team", action="store_true", help="Team project (affects permissions, shared config)")
    parser.add_argument("--tdd", action="store_true", help="Enable TDD loop configuration and /tdd command")
    parser.add_argument("--conventional-commits", action="store_true", help="Enforce conventional commits format")
    parser.add_argument("--output-dir", default=".", help="Output directory")
    parser.add_argument(
        "--create-root",
        action="store_true",
        help="Create project root directory (default: scaffold into output-dir directly)"
    )

    args = parser.parse_args()
    sys.exit(scaffold(args))


if __name__ == "__main__":
    main()
