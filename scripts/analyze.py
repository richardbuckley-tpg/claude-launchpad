#!/usr/bin/env python3
"""
Claude Launchpad Codebase Analyzer

Reads an existing codebase to extract real patterns, conventions, and architecture.
Generates targeted rules based on what the code actually does, not generic framework advice.

Usage:
    python analyze.py <project-root>                # Analyze and print findings
    python analyze.py <project-root> --write-rules  # Write rule files to .claude/rules/
    python analyze.py <project-root> --json          # JSON output
"""

import argparse
import json
import os
import re
import sys
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path

# ── Data Structures ──────────────────────────────────────────────────────


@dataclass
class Pattern:
    """A detected codebase pattern."""
    category: str          # error-handling, auth, validation, etc.
    description: str       # Human-readable description
    evidence: list         # File paths where pattern was found
    rule_lines: list       # Rule bullet points to generate
    globs: list            # File patterns this rule applies to
    confidence: float      # 0.0-1.0


@dataclass
class AnalysisResult:
    """Complete analysis output."""
    project_dir: str
    stack: dict                    # detected stack info
    patterns: list                 # Pattern objects
    key_abstractions: list         # {name, file, type, description}
    file_organization: dict        # {style, test_location, etc.}
    entry_points: list = field(default_factory=list)
    api_surface: dict = field(default_factory=dict)
    complexity: dict = field(default_factory=dict)
    test_coverage_map: dict = field(default_factory=dict)
    config_env: dict = field(default_factory=dict)


# ── Constants ────────────────────────────────────────────────────────────

SKIP_DIRS = {
    "node_modules", ".next", ".nuxt", ".svelte-kit", ".output",
    "dist", "build", ".git", "__pycache__", ".venv", "venv",
    "vendor", "target", ".claude", ".idea", ".vscode",
    "coverage", ".nyc_output", "htmlcov", ".pytest_cache",
}

SOURCE_EXTENSIONS = {
    ".ts", ".tsx", ".js", ".jsx",  # JavaScript/TypeScript
    ".py",                          # Python
    ".go",                          # Go
    ".rs",                          # Rust
    ".rb",                          # Ruby
}

MAX_FILE_SIZE = 50_000  # Skip files >50KB
MAX_FILES = 500


# ── Helpers ──────────────────────────────────────────────────────────────

def collect_source_files(project_dir: Path) -> list:
    """Collect source files for analysis, respecting limits."""
    files = []
    for root, dirs, filenames in os.walk(project_dir):
        dirs[:] = [d for d in dirs if d not in SKIP_DIRS]
        root_path = Path(root)
        for fname in filenames:
            if len(files) >= MAX_FILES:
                return files
            fp = root_path / fname
            if fp.suffix in SOURCE_EXTENSIONS:
                try:
                    if fp.stat().st_size <= MAX_FILE_SIZE:
                        files.append(fp)
                except OSError:
                    pass
    return files


def read_file_safe(fp: Path) -> str:
    """Read file contents, returning empty string on error."""
    try:
        return fp.read_text(errors="replace")
    except (OSError, UnicodeDecodeError):
        return ""


# ── Monorepo Detection ──────────────────────────────────────────────────


def detect_monorepo(project_dir: Path):
    """Detect monorepo tooling and enumerate workspace packages.

    Returns None if the project is not a monorepo, or a dict with keys:
        tool      – "turborepo", "nx", "pnpm-workspaces", "yarn-workspaces", "lerna"
        packages  – list of {"name": ..., "path": ...} for each workspace package
    """

    def _expand_workspace_patterns(base: Path, patterns: list) -> list:
        """Expand glob patterns like 'apps/*' into concrete packages."""
        packages = []
        seen = set()
        for pattern in patterns:
            pattern = pattern.strip()
            if not pattern:
                continue
            # Remove trailing slash if present
            pattern = pattern.rstrip("/")
            for pkg_dir in sorted(base.glob(pattern)):
                if not pkg_dir.is_dir():
                    continue
                pkg_json = pkg_dir / "package.json"
                rel = str(pkg_dir.relative_to(base))
                if rel in seen:
                    continue
                seen.add(rel)
                name = pkg_dir.name  # fallback
                if pkg_json.exists():
                    try:
                        data = json.loads(pkg_json.read_text())
                        name = data.get("name", name)
                    except (json.JSONDecodeError, UnicodeDecodeError):
                        pass
                packages.append({"name": name, "path": rel})
        return packages

    # 1. Turborepo
    turbo_json = project_dir / "turbo.json"
    if turbo_json.exists():
        tool = "turborepo"
        # Turborepo uses workspace patterns from package.json or pnpm-workspace.yaml
        patterns = []
        # Try pnpm-workspace.yaml first
        pnpm_ws = project_dir / "pnpm-workspace.yaml"
        if pnpm_ws.exists():
            try:
                content = pnpm_ws.read_text()
                for line in content.splitlines():
                    line = line.strip()
                    if line.startswith("- "):
                        pat = line[2:].strip().strip("'\"")
                        if pat:
                            patterns.append(pat)
            except UnicodeDecodeError:
                pass
        # Fallback to package.json workspaces
        if not patterns:
            pkg_json = project_dir / "package.json"
            if pkg_json.exists():
                try:
                    data = json.loads(pkg_json.read_text())
                    ws = data.get("workspaces", [])
                    if isinstance(ws, dict):
                        ws = ws.get("packages", [])
                    patterns = ws if isinstance(ws, list) else []
                except (json.JSONDecodeError, UnicodeDecodeError):
                    pass
        packages = _expand_workspace_patterns(project_dir, patterns)
        return {"tool": tool, "packages": packages}

    # 2. Nx
    if (project_dir / "nx.json").exists():
        tool = "nx"
        # Nx commonly uses apps/* and packages/* (or libs/*)
        patterns = []
        pkg_json = project_dir / "package.json"
        if pkg_json.exists():
            try:
                data = json.loads(pkg_json.read_text())
                ws = data.get("workspaces", [])
                if isinstance(ws, dict):
                    ws = ws.get("packages", [])
                patterns = ws if isinstance(ws, list) else []
            except (json.JSONDecodeError, UnicodeDecodeError):
                pass
        if not patterns:
            # Nx default conventions
            patterns = ["apps/*", "packages/*", "libs/*"]
        packages = _expand_workspace_patterns(project_dir, patterns)
        return {"tool": tool, "packages": packages}

    # 3. pnpm workspaces (without turbo)
    pnpm_ws = project_dir / "pnpm-workspace.yaml"
    if pnpm_ws.exists():
        tool = "pnpm-workspaces"
        patterns = []
        try:
            content = pnpm_ws.read_text()
            for line in content.splitlines():
                line = line.strip()
                if line.startswith("- "):
                    pat = line[2:].strip().strip("'\"")
                    if pat:
                        patterns.append(pat)
        except UnicodeDecodeError:
            pass
        packages = _expand_workspace_patterns(project_dir, patterns)
        return {"tool": tool, "packages": packages}

    # 4. yarn/npm workspaces
    pkg_json = project_dir / "package.json"
    if pkg_json.exists():
        try:
            data = json.loads(pkg_json.read_text())
            ws = data.get("workspaces")
            if ws is not None:
                if isinstance(ws, dict):
                    ws = ws.get("packages", [])
                if isinstance(ws, list) and ws:
                    tool = "yarn-workspaces"
                    packages = _expand_workspace_patterns(project_dir, ws)
                    return {"tool": tool, "packages": packages}
        except (json.JSONDecodeError, UnicodeDecodeError):
            pass

    # 5. Lerna
    if (project_dir / "lerna.json").exists():
        tool = "lerna"
        patterns = ["packages/*"]
        lerna_json = project_dir / "lerna.json"
        try:
            data = json.loads(lerna_json.read_text())
            lerna_patterns = data.get("packages")
            if isinstance(lerna_patterns, list) and lerna_patterns:
                patterns = lerna_patterns
        except (json.JSONDecodeError, UnicodeDecodeError):
            pass
        packages = _expand_workspace_patterns(project_dir, patterns)
        return {"tool": tool, "packages": packages}

    return None


# ── Event Pattern Detection ──────────────────────────────────────────────


def detect_event_patterns(project_dir: Path) -> list[str]:
    """Detect event-driven architectural patterns from source code."""
    patterns = []

    # Scan source directories for pattern indicators
    src_dirs = ["src", "app", "lib", "pkg", "internal", "server"]
    files_to_scan = []
    for sd in src_dirs:
        d = project_dir / sd
        if d.exists():
            files_to_scan.extend(d.rglob("*.ts"))
            files_to_scan.extend(d.rglob("*.py"))
            files_to_scan.extend(d.rglob("*.go"))
            files_to_scan.extend(d.rglob("*.java"))

    # Limit scanning to first 100 files to keep it fast
    content_sample = ""
    for f in list(files_to_scan)[:100]:
        try:
            content_sample += f.read_text(errors="ignore") + "\n"
        except (OSError, UnicodeDecodeError):
            pass

    content_lower = content_sample.lower()

    # Event sourcing indicators
    if any(term in content_lower for term in ["eventsource", "event_source", "eventstore", "event_store", "aggregate_root", "aggregateroot", "apply_event", "applyevent"]):
        patterns.append("event-sourcing")

    # CQRS indicators
    if any(term in content_lower for term in ["commandhandler", "command_handler", "queryhandler", "query_handler", "readmodel", "read_model", "projection"]):
        patterns.append("cqrs")

    # Saga indicators
    if any(term in content_lower for term in ["saga", "compensat", "orchestrat"]) and any(term in content_lower for term in ["step", "transaction", "rollback"]):
        patterns.append("saga")

    # Outbox pattern indicators
    if any(term in content_lower for term in ["outbox", "outbox_events", "outboxevent"]):
        patterns.append("outbox")

    # DLQ indicators
    if any(term in content_lower for term in ["deadletter", "dead_letter", "dlq", "dead letter"]):
        patterns.append("dlq")

    return patterns


# ── Stack Detection ──────────────────────────────────────────────────────

def detect_stack(project_dir: Path) -> dict:
    """Detect the project's tech stack from manifest files."""
    stack = {}

    # Node/TypeScript detection
    pkg_json = project_dir / "package.json"
    if pkg_json.exists():
        try:
            pkg = json.loads(pkg_json.read_text())
            deps = {**pkg.get("dependencies", {}), **pkg.get("devDependencies", {})}

            # Language
            stack["language"] = "typescript" if "typescript" in deps else "javascript"

            # Package manager
            if (project_dir / "pnpm-lock.yaml").exists():
                stack["package_manager"] = "pnpm"
            elif (project_dir / "yarn.lock").exists():
                stack["package_manager"] = "yarn"
            elif (project_dir / "bun.lockb").exists():
                stack["package_manager"] = "bun"
            else:
                stack["package_manager"] = "npm"

            # Frontend
            if "next" in deps:
                stack["frontend"] = "nextjs"
                stack["backend"] = "integrated"
            elif "svelte" in deps or "@sveltejs/kit" in deps:
                stack["frontend"] = "sveltekit"
                stack["backend"] = "integrated"
            elif "vue" in deps or "nuxt" in deps:
                stack["frontend"] = "vue"
            elif "react" in deps:
                stack["frontend"] = "react-vite"

            # Backend (if not already set)
            if "backend" not in stack:
                if "express" in deps:
                    stack["backend"] = "node-express"
                elif "fastify" in deps:
                    stack["backend"] = "node-fastify"

            # ORM
            if "prisma" in deps or "@prisma/client" in deps:
                stack["orm"] = "prisma"
            elif "drizzle-orm" in deps:
                stack["orm"] = "drizzle"
            elif "typeorm" in deps:
                stack["orm"] = "typeorm"
            elif "sequelize" in deps:
                stack["orm"] = "sequelize"
            elif "mongoose" in deps:
                stack["orm"] = "mongoose"

            # Auth
            if "@clerk/nextjs" in deps or "@clerk/express" in deps:
                stack["auth"] = "clerk"
            elif "next-auth" in deps or "@auth/core" in deps:
                stack["auth"] = "nextauth"
            elif "@supabase/supabase-js" in deps:
                stack["auth"] = "supabase-auth"

            # Event systems
            event_systems = []
            if "kafkajs" in deps or "node-rdkafka" in deps:
                event_systems.append("kafka")
            if "bullmq" in deps or "bull" in deps:
                event_systems.append("bullmq")
            if "amqplib" in deps or "amqp-connection-manager" in deps:
                event_systems.append("rabbitmq")
            if "@temporalio/client" in deps or "@temporalio/worker" in deps:
                event_systems.append("temporal")
                stack["workflow_orchestration"] = "temporal"
            if "nats" in deps or "nats.ws" in deps:
                event_systems.append("nats")
            if "@aws-sdk/client-sqs" in deps or "@aws-sdk/client-eventbridge" in deps:
                event_systems.append("aws-events")
            if "ioredis" in deps and "bullmq" not in deps:
                event_systems.append("redis-streams")
            if "@nestjs/microservices" in deps:
                event_systems.append("nestjs-microservices")
            if event_systems:
                stack["event_systems"] = event_systems

            # Schema format
            if "@kafkajs/confluent-schema-registry" in deps or "avsc" in deps:
                stack["schema_format"] = "avro"
            elif "protobufjs" in deps or "google-protobuf" in deps:
                stack["schema_format"] = "protobuf"

            # Database from ORM
            if stack.get("orm") in ("prisma", "drizzle", "typeorm", "sequelize"):
                stack["database"] = "postgresql"  # most common default
            elif stack.get("orm") == "mongoose":
                stack["database"] = "mongodb"

            # Testing
            if "vitest" in deps:
                stack["test_framework"] = "vitest"
            elif "jest" in deps:
                stack["test_framework"] = "jest"
            elif "@playwright/test" in deps:
                stack["test_framework"] = "playwright"

            # Command detection from package.json scripts
            scripts = pkg.get("scripts", {})
            pm = stack.get("package_manager", "npm")
            pm_run = f"{pm} run" if pm == "npm" else pm
            cmd_map = {
                "test": "test_cmd",
                "lint": "lint_cmd",
                "dev": "dev_cmd",
                "build": "build_cmd",
            }
            for script_name, stack_key in cmd_map.items():
                if script_name in scripts and stack_key not in stack:
                    stack[stack_key] = f"{pm_run} {script_name}"

        except (json.JSONDecodeError, UnicodeDecodeError):
            pass

    # Python detection
    requirements = project_dir / "requirements.txt"
    pyproject = project_dir / "pyproject.toml"
    if requirements.exists() or pyproject.exists():
        stack["language"] = "python"
        try:
            content = ""
            if requirements.exists():
                content = requirements.read_text().lower()
            if pyproject.exists():
                content += "\n" + pyproject.read_text().lower()

            if "fastapi" in content:
                stack["backend"] = "python-fastapi"
            elif "django" in content:
                stack["backend"] = "python-django"
            elif "flask" in content:
                stack["backend"] = "python-flask"
            if "sqlalchemy" in content:
                stack["orm"] = "sqlalchemy"
                stack["database"] = "postgresql"
            if "pytest" in content:
                stack["test_framework"] = "pytest"

            # Event systems
            event_systems = stack.get("event_systems", [])
            if "confluent-kafka" in content or "confluent_kafka" in content:
                event_systems.append("kafka")
            if "faust" in content or "faust-streaming" in content:
                event_systems.append("faust")
            if "celery" in content:
                event_systems.append("celery")
            if "pika" in content or "kombu" in content:
                event_systems.append("rabbitmq")
            if "dramatiq" in content:
                event_systems.append("dramatiq")
            if "temporalio" in content:
                event_systems.append("temporal")
                stack["workflow_orchestration"] = "temporal"
            if "nats" in content and "nats-py" in content:
                event_systems.append("nats")
            if "boto3" in content:
                # Check for specific AWS event services - we only flag if sqs/eventbridge specifically
                pass  # Can't distinguish from generic boto3 usage
            if "redis" in content and "redis-py" in content and "celery" not in content:
                event_systems.append("redis-streams")
            if "apache-flink" in content or "pyflink" in content:
                event_systems.append("flink")
            if "pyspark" in content:
                event_systems.append("spark-streaming")
            if event_systems:
                stack["event_systems"] = event_systems

            if "avro" in content:
                stack["schema_format"] = "avro"
            elif "protobuf" in content or "grpcio" in content:
                stack["schema_format"] = "protobuf"

            # Command detection from pyproject.toml
            if pyproject.exists():
                pyproject_content = pyproject.read_text()
                if ("[tool.pytest]" in pyproject_content
                        or "[tool.pytest.ini_options]" in pyproject_content):
                    if "test_cmd" not in stack:
                        stack["test_cmd"] = "pytest"
                if "[tool.ruff]" in pyproject_content:
                    if "lint_cmd" not in stack:
                        stack["lint_cmd"] = "ruff check ."
                if "[tool.mypy]" in pyproject_content:
                    if "lint_cmd" not in stack:
                        stack["lint_cmd"] = "mypy"
                    elif "mypy" not in stack["lint_cmd"]:
                        stack["lint_cmd"] += " && mypy"

        except UnicodeDecodeError:
            pass

    # Go detection
    if (project_dir / "go.mod").exists():
        stack["language"] = "go"
        stack["backend"] = "go"
        stack["test_framework"] = "go-test"

        try:
            go_mod_content = (project_dir / "go.mod").read_text().lower()
            event_systems = stack.get("event_systems", [])
            if "sarama" in go_mod_content or "confluent-kafka-go" in go_mod_content:
                event_systems.append("kafka")
            if "watermill" in go_mod_content:
                event_systems.append("watermill")
            if "amqp091-go" in go_mod_content or "streadway/amqp" in go_mod_content:
                event_systems.append("rabbitmq")
            if "go.temporal.io" in go_mod_content:
                event_systems.append("temporal")
                stack["workflow_orchestration"] = "temporal"
            if "nats.go" in go_mod_content or "nats-io/nats.go" in go_mod_content:
                event_systems.append("nats")
            if "go-redis" in go_mod_content and "bullmq" not in str(event_systems):
                event_systems.append("redis-streams")
            if event_systems:
                stack["event_systems"] = event_systems
        except (UnicodeDecodeError, FileNotFoundError):
            pass

    # Rust detection
    cargo_toml = project_dir / "Cargo.toml"
    if cargo_toml.exists():
        stack["language"] = "rust"
        try:
            content = cargo_toml.read_text().lower()
            if "actix" in content:
                stack["backend"] = "rust-actix"
            elif "axum" in content:
                stack["backend"] = "rust-axum"
        except UnicodeDecodeError:
            pass

    # Ruby/Rails detection
    if (project_dir / "Gemfile").exists():
        stack["language"] = "ruby"
        stack["backend"] = "ruby-rails"
        stack["orm"] = "activerecord"

    # Database refinement from env files
    # Only read .env.example (safe) — never read .env or .env.local which contain real secrets
    for env_file in [".env.example"]:
        env_path = project_dir / env_file
        if env_path.exists():
            try:
                env_content = env_path.read_text()
                if "postgresql" in env_content or "postgres" in env_content:
                    stack["database"] = "postgresql"
                elif "mysql" in env_content:
                    stack["database"] = "mysql"
                elif "mongodb" in env_content:
                    stack["database"] = "mongodb"
                elif "sqlite" in env_content:
                    stack["database"] = "sqlite"
            except UnicodeDecodeError:
                pass

    # Makefile command detection
    makefile = project_dir / "Makefile"
    if makefile.exists():
        try:
            makefile_content = makefile.read_text()
            makefile_targets = re.findall(r'^(\w+)\s*:', makefile_content, re.MULTILINE)
            make_cmd_map = {
                "test": "test_cmd",
                "lint": "lint_cmd",
                "dev": "dev_cmd",
                "build": "build_cmd",
            }
            for target, stack_key in make_cmd_map.items():
                if target in makefile_targets and stack_key not in stack:
                    stack[stack_key] = f"make {target}"
        except UnicodeDecodeError:
            pass

    # Migration command detection (based on ORM already detected)
    if "migrate_cmd" not in stack:
        orm = stack.get("orm", "")
        if orm == "prisma":
            stack["migrate_cmd"] = "npx prisma migrate dev"
        elif orm == "drizzle":
            stack["migrate_cmd"] = "npx drizzle-kit push"
        elif orm == "sqlalchemy":
            stack["migrate_cmd"] = "alembic upgrade head"
        elif orm == "activerecord":
            stack["migrate_cmd"] = "rails db:migrate"

    # Git platform detection
    git_config = project_dir / ".git" / "config"
    if git_config.exists():
        try:
            git_content = git_config.read_text()
            if "github.com" in git_content:
                stack["git_platform"] = "github"
            elif "gitlab.com" in git_content:
                stack["git_platform"] = "gitlab"
            elif "bitbucket.org" in git_content:
                stack["git_platform"] = "bitbucket"
        except UnicodeDecodeError:
            pass

    # CI/CD detection
    if (project_dir / ".github" / "workflows").is_dir():
        stack["ci_cd"] = "github-actions"
    elif (project_dir / ".gitlab-ci.yml").exists():
        stack["ci_cd"] = "gitlab-ci"

    # Hosting detection
    if (project_dir / "vercel.json").exists() or (project_dir / ".vercel").is_dir():
        stack["hosting"] = "vercel"
    elif (project_dir / "fly.toml").exists():
        stack["hosting"] = "fly"
    elif (project_dir / "railway.toml").exists() or (project_dir / "railway.json").exists():
        stack["hosting"] = "railway"
    elif (project_dir / "serverless.yml").exists() or (project_dir / "sam-template.yml").exists():
        stack["hosting"] = "aws"
    elif (project_dir / "Dockerfile").exists() and "hosting" not in stack:
        stack["hosting"] = "self-hosted"

    # Event system detection from docker-compose
    for compose_file in ["docker-compose.yml", "docker-compose.yaml", "compose.yml", "compose.yaml"]:
        compose_path = project_dir / compose_file
        if compose_path.exists():
            try:
                compose_content = compose_path.read_text().lower()
                event_systems = stack.get("event_systems", [])
                if "kafka" in compose_content or "confluent" in compose_content:
                    if "kafka" not in event_systems:
                        event_systems.append("kafka")
                if "rabbitmq" in compose_content:
                    if "rabbitmq" not in event_systems:
                        event_systems.append("rabbitmq")
                if "redis" in compose_content and ("bullmq" in str(stack.get("event_systems", [])) or "streams" in compose_content):
                    pass  # Redis already detected via package deps
                if "nats" in compose_content:
                    if "nats" not in event_systems:
                        event_systems.append("nats")
                if "temporal" in compose_content:
                    if "temporal" not in event_systems:
                        event_systems.append("temporal")
                    stack["workflow_orchestration"] = "temporal"
                if "pulsar" in compose_content:
                    if "pulsar" not in event_systems:
                        event_systems.append("pulsar")
                if event_systems:
                    stack["event_systems"] = event_systems
            except UnicodeDecodeError:
                pass
            break  # Only read first found compose file

    # Schema format detection from files
    if "schema_format" not in stack:
        # Check common schema directories
        for schema_dir in ["schemas", "schema", "avro", "proto", "protobuf", "src/schemas", "src/proto"]:
            sd = project_dir / schema_dir
            if sd.exists():
                if list(sd.glob("*.avsc"))[:1]:
                    stack["schema_format"] = "avro"
                    break
                if list(sd.glob("*.proto"))[:1]:
                    stack["schema_format"] = "protobuf"
                    break

    # Event pattern detection
    event_patterns = detect_event_patterns(project_dir)
    if event_patterns:
        stack["event_patterns"] = event_patterns

    # Monorepo detection
    monorepo = detect_monorepo(project_dir)
    if monorepo:
        stack["monorepo"] = monorepo

    return stack


def snapshot_dependencies(project_dir: Path) -> dict:
    """Read current dependencies from manifest files and return a snapshot.

    Returns a dict keyed by ecosystem (node, python, go, ruby) with
    package-name -> version mappings.  Only ecosystems that have packages
    are included.  Version is "*" when not easily parseable.
    """
    snapshot = {}

    # ── Node (package.json) ──────────────────────────────────────────
    pkg_json = project_dir / "package.json"
    if pkg_json.exists():
        try:
            pkg = json.loads(pkg_json.read_text())
            merged = {}
            merged.update(pkg.get("dependencies", {}))
            merged.update(pkg.get("devDependencies", {}))
            if merged:
                snapshot["node"] = {k: str(v) for k, v in merged.items()}
        except (json.JSONDecodeError, UnicodeDecodeError):
            pass

    # ── Python (requirements.txt / pyproject.toml) ───────────────────
    py_deps = {}
    requirements = project_dir / "requirements.txt"
    if requirements.exists():
        try:
            for line in requirements.read_text().splitlines():
                line = line.strip()
                if not line or line.startswith("#") or line.startswith("-"):
                    continue
                # Handle package==version, package>=version, package~=version, bare package
                match = re.match(r'^([A-Za-z0-9_][A-Za-z0-9._-]*)\s*(?:[=~!<>]=?\s*(.+))?', line)
                if match:
                    name = match.group(1).lower()
                    version = match.group(2).strip() if match.group(2) else "*"
                    py_deps[name] = version
        except UnicodeDecodeError:
            pass

    pyproject = project_dir / "pyproject.toml"
    if pyproject.exists():
        try:
            content = pyproject.read_text()
            # Look for [project] dependencies = [...] section
            in_deps = False
            for line in content.splitlines():
                stripped = line.strip()
                if stripped.startswith("dependencies") and "=" in stripped:
                    in_deps = True
                    # Handle inline list on same line
                    bracket_content = stripped.split("=", 1)[1].strip()
                    if bracket_content.startswith("["):
                        items = re.findall(r'"([^"]+)"', bracket_content)
                        for item in items:
                            dep_match = re.match(r'^([A-Za-z0-9_][A-Za-z0-9._-]*)', item)
                            if dep_match:
                                py_deps[dep_match.group(1).lower()] = "*"
                        if "]" in bracket_content:
                            in_deps = False
                    continue
                if in_deps:
                    if "]" in stripped:
                        items = re.findall(r'"([^"]+)"', stripped)
                        for item in items:
                            dep_match = re.match(r'^([A-Za-z0-9_][A-Za-z0-9._-]*)', item)
                            if dep_match:
                                py_deps[dep_match.group(1).lower()] = "*"
                        in_deps = False
                        continue
                    items = re.findall(r'"([^"]+)"', stripped)
                    for item in items:
                        dep_match = re.match(r'^([A-Za-z0-9_][A-Za-z0-9._-]*)', item)
                        if dep_match:
                            py_deps[dep_match.group(1).lower()] = "*"
                    # Stop if we hit a new section
                    if stripped.startswith("["):
                        in_deps = False
        except UnicodeDecodeError:
            pass

    if py_deps:
        snapshot["python"] = py_deps

    # ── Go (go.mod) ──────────────────────────────────────────────────
    go_mod = project_dir / "go.mod"
    if go_mod.exists():
        try:
            content = go_mod.read_text()
            go_deps = {}
            in_require = False
            for line in content.splitlines():
                stripped = line.strip()
                if stripped.startswith("require ("):
                    in_require = True
                    continue
                if in_require:
                    if stripped == ")":
                        in_require = False
                        continue
                    parts = stripped.split()
                    if len(parts) >= 2:
                        go_deps[parts[0]] = parts[1]
                # Single-line require
                elif stripped.startswith("require "):
                    parts = stripped.split()
                    if len(parts) >= 3:
                        go_deps[parts[1]] = parts[2]
            if go_deps:
                snapshot["go"] = go_deps
        except UnicodeDecodeError:
            pass

    # ── Ruby (Gemfile) ───────────────────────────────────────────────
    gemfile = project_dir / "Gemfile"
    if gemfile.exists():
        try:
            content = gemfile.read_text()
            ruby_deps = {}
            for line in content.splitlines():
                stripped = line.strip()
                if stripped.startswith("#"):
                    continue
                gem_match = re.match(r'''gem\s+['"]([^'"]+)['"](?:\s*,\s*['"]([^'"]+)['"])?''', stripped)
                if gem_match:
                    name = gem_match.group(1)
                    version = gem_match.group(2) if gem_match.group(2) else "*"
                    ruby_deps[name] = version
            if ruby_deps:
                snapshot["ruby"] = ruby_deps
        except UnicodeDecodeError:
            pass

    return snapshot


# ── AI Config Migration ─────────────────────────────────────────────────

AI_CONFIG_FILES = [
    {"source": "cursor", "path": ".cursorrules"},
    {"source": "copilot", "path": ".github/copilot-instructions.md"},
    {"source": "windsurf", "path": ".windsurfrules"},
    {"source": "aider", "path": ".aider.conf.yml"},
]


def detect_ai_configs(project_dir: Path) -> list:
    """Detect other AI tool configuration files in the project."""
    found = []
    for cfg in AI_CONFIG_FILES:
        filepath = project_dir / cfg["path"]
        if filepath.exists() and filepath.is_file():
            try:
                content = filepath.read_text(encoding="utf-8")
                found.append({
                    "source": cfg["source"],
                    "path": cfg["path"],
                    "content": content,
                })
            except (UnicodeDecodeError, PermissionError, OSError):
                pass
    return found


def migrate_ai_configs(project_dir: Path, configs: list) -> list:
    """Convert detected AI configs to .claude/rules/migrated-{source}.md files.

    Returns list of created file paths. Skips files that already exist.
    """
    rules_dir = project_dir / ".claude" / "rules"
    rules_dir.mkdir(parents=True, exist_ok=True)

    created = []
    for cfg in configs:
        source = cfg["source"]
        content = cfg["content"]
        dest = rules_dir / f"migrated-{source}.md"

        # Don't overwrite existing migrated files
        if dest.exists():
            continue

        source_title = source.capitalize()

        # Build the migrated file content
        lines = []
        lines.append("---")
        lines.append(f"description: Rules migrated from {source}")
        lines.append("---")
        lines.append("")
        lines.append(f"# Migrated from {source_title}")
        lines.append("")
        lines.append("> Auto-migrated by Claude Launchpad. Review and adjust.")
        lines.append("")

        if source == "cursor":
            lines.append("> Note: These were Cursor-specific rules and may need adaptation for Claude.")
            lines.append("")
        elif source == "aider":
            lines.append("> Note: These were Aider-specific settings and may need adaptation for Claude.")
            lines.append("")

        lines.append(content)

        dest.write_text("\n".join(lines), encoding="utf-8")
        created.append(str(dest.relative_to(project_dir)))

    return created


# ── Pattern Detectors ────────────────────────────────────────────────────

def detect_error_handling(project_dir: Path, files: list, stack: dict) -> list:
    """Detect error handling patterns."""
    patterns = []
    lang = stack.get("language", "")

    # Custom error classes
    custom_errors = []
    error_class_re = None

    if lang in ("typescript", "javascript"):
        error_class_re = re.compile(r'class\s+(\w+Error)\s+extends\s+(\w+)')
    elif lang == "python":
        error_class_re = re.compile(r'class\s+(\w+(?:Error|Exception))\s*\((\w+)\)')
    elif lang == "go":
        error_class_re = re.compile(r'type\s+(\w+Error)\s+struct')

    if error_class_re:
        for fp in files:
            content = read_file_safe(fp)
            matches = error_class_re.findall(content)
            for match in matches:
                name = match[0] if isinstance(match, tuple) else match
                rel = str(fp.relative_to(project_dir))
                custom_errors.append({"name": name, "file": rel})

    if custom_errors:
        error_files = list(set(e["file"] for e in custom_errors))
        error_names = list(set(e["name"] for e in custom_errors))

        rules = [f"- Use custom error classes: {', '.join(error_names)}"]
        if len(error_files) <= 3:
            rules.append(f"- Error definitions in: {', '.join(error_files)}")
        rules.append("- Never throw generic Error/Exception — use the project's error types")

        ext = "ts" if lang in ("typescript", "javascript") else lang[:2]
        patterns.append(Pattern(
            category="error-handling",
            description="Custom error classes",
            evidence=error_files,
            rule_lines=rules,
            globs=[f"**/*.{ext}", f"**/*.{ext}x"] if ext == "ts" else [f"**/*.{ext}"],
            confidence=0.8 if len(custom_errors) >= 2 else 0.5,
        ))

    # Centralized error handler (Express/Fastify)
    if lang in ("typescript", "javascript"):
        for fp in files:
            content = read_file_safe(fp)
            if re.search(r'(?:err|error)\s*,\s*req\s*,\s*res\s*,\s*next|\.setErrorHandler', content):
                rel = str(fp.relative_to(project_dir))
                patterns.append(Pattern(
                    category="error-handling",
                    description="Centralized error handler",
                    evidence=[rel],
                    rule_lines=[
                        f"- Centralized error handler in `{rel}`",
                        "- Route handlers throw errors — the middleware formats responses",
                        "- Never send error responses directly from route handlers",
                    ],
                    globs=["src/routes/**/*.ts", "src/controllers/**/*.ts"],
                    confidence=0.8,
                ))
                break

    return patterns


def detect_auth_patterns(project_dir: Path, files: list, stack: dict) -> list:
    """Detect authentication/authorization patterns."""
    patterns = []
    lang = stack.get("language", "")

    auth_middleware = []

    for fp in files:
        content = read_file_safe(fp)
        rel = str(fp.relative_to(project_dir))

        if lang in ("typescript", "javascript"):
            auth_funcs = re.findall(
                r'(?:export\s+)?(?:function|const)\s+(withAuth|requireAuth|isAuthenticated|authMiddleware|protect|authenticate|requireRole)\b',
                content
            )
            for func in auth_funcs:
                auth_middleware.append({"name": func, "file": rel})

        elif lang == "python":
            if re.search(r'Depends\(\s*(?:get_current_user|verify_token|require_auth)', content):
                auth_middleware.append({"name": "dependency-injection", "file": rel})
            auth_decorators = re.findall(r'@(login_required|require_auth|permission_required|requires_auth)', content)
            for dec in auth_decorators:
                auth_middleware.append({"name": dec, "file": rel})

    if auth_middleware:
        unique = {}
        for am in auth_middleware:
            if am["name"] not in unique:
                unique[am["name"]] = am["file"]

        rules = []
        for name, filepath in unique.items():
            rules.append(f"- Auth pattern: `{name}` from `{filepath}`")
        rules.append("- ALL routes handling user data must use the project's auth pattern")
        rules.append("- Never implement custom auth checks — use existing middleware")

        globs = ["src/**/*.ts", "src/**/*.tsx", "app/**/*.ts"] if lang in ("typescript", "javascript") else ["**/*.py"]
        patterns.append(Pattern(
            category="auth",
            description="Authentication middleware",
            evidence=[am["file"] for am in auth_middleware[:5]],
            rule_lines=rules,
            globs=globs,
            confidence=0.9,
        ))

    return patterns


def detect_validation(project_dir: Path, files: list, stack: dict) -> list:
    """Detect input validation patterns."""
    patterns = []
    lang = stack.get("language", "")

    validation_libs = {}
    schema_dirs = set()

    for fp in files:
        content = read_file_safe(fp)
        rel = str(fp.relative_to(project_dir))

        if lang in ("typescript", "javascript"):
            if re.search(r'from\s+[\'"]zod[\'"]|require\([\'"]zod[\'"]\)', content):
                validation_libs.setdefault("zod", []).append(rel)
                if re.search(r'z\.object|z\.string|z\.number', content):
                    parts = rel.split("/")
                    if len(parts) > 1:
                        for kw in ("schema", "schemas", "validation", "validators"):
                            if kw in rel.lower():
                                schema_dirs.add("/".join(parts[:-1]))
            elif re.search(r'from\s+[\'"]joi[\'"]', content):
                validation_libs.setdefault("joi", []).append(rel)
            elif re.search(r'from\s+[\'"]yup[\'"]', content):
                validation_libs.setdefault("yup", []).append(rel)

        elif lang == "python":
            if re.search(r'from\s+pydantic\s+import|class\s+\w+\(BaseModel\)', content):
                validation_libs.setdefault("pydantic", []).append(rel)

    if validation_libs:
        primary = max(validation_libs, key=lambda k: len(validation_libs[k]))
        lib_files = validation_libs[primary]

        rules = [f"- Validate ALL input using **{primary}**"]
        if schema_dirs:
            rules.append(f"- Schemas in: {', '.join(sorted(schema_dirs))}")
        rules.append(f"- Never write manual validation when {primary} can express it")

        if len(validation_libs) > 1:
            others = [k for k in validation_libs if k != primary]
            rules.append(f"- Also uses {', '.join(others)} — migrate to {primary} when touching those files")

        patterns.append(Pattern(
            category="validation",
            description=f"{primary} validation",
            evidence=lib_files[:5],
            rule_lines=rules,
            globs=["**/*.ts", "**/*.tsx"] if lang in ("typescript", "javascript") else ["**/*.py"],
            confidence=0.9 if len(lib_files) >= 3 else 0.6,
        ))

    return patterns


def detect_data_fetching(project_dir: Path, files: list, stack: dict) -> list:
    """Detect data fetching and state management patterns."""
    patterns = []
    lang = stack.get("language", "")
    frontend = stack.get("frontend", "")

    if lang not in ("typescript", "javascript"):
        return patterns

    fetching = {}
    state_mgmt = {}

    for fp in files:
        content = read_file_safe(fp)
        rel = str(fp.relative_to(project_dir))

        # Data fetching
        if re.search(r'useQuery|useMutation|useInfiniteQuery|@tanstack/react-query', content):
            fetching.setdefault("tanstack-query", []).append(rel)
        if re.search(r'from\s+[\'"]swr[\'"]|useSWR', content):
            fetching.setdefault("swr", []).append(rel)
        if frontend == "nextjs" and ('"use server"' in content or "'use server'" in content):
            fetching.setdefault("server-actions", []).append(rel)
        if re.search(r'trpc|createTRPCRouter|api\.\w+\.useQuery', content):
            fetching.setdefault("trpc", []).append(rel)

        # State management
        if re.search(r'from\s+[\'"]zustand[\'"]|create\(\s*\(set', content):
            state_mgmt.setdefault("zustand", []).append(rel)
        elif re.search(r'from\s+[\'"]@reduxjs/toolkit[\'"]|createSlice|configureStore', content):
            state_mgmt.setdefault("redux-toolkit", []).append(rel)
        elif re.search(r'from\s+[\'"]jotai[\'"]|atom\(', content):
            state_mgmt.setdefault("jotai", []).append(rel)

    for name, using in fetching.items():
        if len(using) >= 2:
            rules = [f"- Data fetching: use **{name}** (found in {len(using)} files)"]
            if name == "tanstack-query":
                rules.append("- All API calls through useQuery/useMutation hooks")
                rules.append("- Define query keys consistently for cache management")
            elif name == "server-actions":
                rules.append("- Use Server Actions for mutations, not API routes")
            elif name == "trpc":
                rules.append("- All API communication through tRPC — no raw fetch calls")
            patterns.append(Pattern(
                category="data-fetching",
                description=f"{name} data fetching",
                evidence=using[:5],
                rule_lines=rules,
                globs=["src/**/*.ts", "src/**/*.tsx", "app/**/*.ts", "app/**/*.tsx"],
                confidence=0.8 if len(using) >= 3 else 0.5,
            ))

    for name, using in state_mgmt.items():
        if len(using) >= 2:
            rules = [f"- Client state: **{name}**"]
            rules.append("- Keep server state (API data) separate from client state")

            # Find store directories
            store_dirs = set()
            for f in using:
                for kw in ("store", "stores", "state", "atoms", "slices"):
                    if kw in f.lower():
                        store_dirs.add("/".join(f.split("/")[:-1]))
            if store_dirs:
                rules.append(f"- Stores in: {', '.join(sorted(store_dirs))}")

            patterns.append(Pattern(
                category="state-management",
                description=f"{name} state management",
                evidence=using[:5],
                rule_lines=rules,
                globs=["src/**/*.ts", "src/**/*.tsx"],
                confidence=0.7,
            ))

    return patterns


def detect_testing_patterns(project_dir: Path, files: list, stack: dict) -> list:
    """Detect testing conventions."""
    patterns = []
    lang = stack.get("language", "")

    test_files = [fp for fp in files
                  if re.search(r'\.(?:test|spec)\.[jt]sx?$|^test_|_test\.go|_test\.py', fp.name)]

    if not test_files:
        return patterns

    mock_patterns = {}
    fixture_files = []

    for fp in test_files:
        content = read_file_safe(fp)
        rel = str(fp.relative_to(project_dir))

        if lang in ("typescript", "javascript"):
            if "jest.mock" in content or "vi.mock" in content:
                mock_patterns.setdefault("module-mock", []).append(rel)
            if "nock" in content or "msw" in content:
                mock_patterns.setdefault("http-mock", []).append(rel)
            if "factory" in content.lower() or "fixture" in content.lower():
                fixture_files.append(rel)
        elif lang == "python":
            if "@pytest.fixture" in content:
                mock_patterns.setdefault("pytest-fixtures", []).append(rel)
            if "conftest.py" in fp.name:
                fixture_files.append(rel)

    rules = []
    test_framework = stack.get("test_framework", "unknown")
    rules.append(f"- Test framework: **{test_framework}**")

    for pname, pfiles in mock_patterns.items():
        if len(pfiles) >= 2:
            rules.append(f"- Mocking: use {pname} pattern ({len(pfiles)} files)")

    if fixture_files:
        rules.append(f"- Fixtures in: {', '.join(fixture_files[:3])}")

    # File naming convention
    names = [fp.name for fp in test_files]
    if any(".test." in n for n in names):
        rules.append("- Test file naming: `*.test.{ts,tsx}`")
    elif any(".spec." in n for n in names):
        rules.append("- Test file naming: `*.spec.{ts,tsx}`")
    elif any(n.startswith("test_") for n in names):
        rules.append("- Test file naming: `test_*.py`")

    if rules:
        patterns.append(Pattern(
            category="testing",
            description="Testing conventions",
            evidence=[str(fp.relative_to(project_dir)) for fp in test_files[:5]],
            rule_lines=rules,
            globs=["**/*.test.*", "**/*.spec.*", "**/test_*"],
            confidence=0.8,
        ))

    return patterns


def detect_api_patterns(project_dir: Path, files: list, stack: dict) -> list:
    """Detect API response and routing patterns."""
    patterns = []
    lang = stack.get("language", "")
    backend = stack.get("backend", "")

    if not backend or backend == "none":
        return patterns

    response_wrappers = []
    pagination_found = False

    for fp in files:
        content = read_file_safe(fp)
        rel = str(fp.relative_to(project_dir))

        is_route = any(kw in rel.lower() for kw in ["route", "controller", "handler", "api", "endpoint", "view"])
        if not is_route:
            continue

        if lang in ("typescript", "javascript"):
            if re.search(r'(?:successResponse|apiResponse|formatResponse|sendSuccess)\s*\(', content):
                response_wrappers.append(rel)
        elif lang == "python":
            if re.search(r'(?:JSONResponse|make_response|success_response)\s*\(', content):
                response_wrappers.append(rel)

        if re.search(r'(?:page|offset|cursor|limit|skip|take)\s*[=:]', content):
            pagination_found = True

    rules = []
    if response_wrappers:
        rules.append(f"- API responses use a consistent wrapper (see {', '.join(response_wrappers[:3])})")
        rules.append("- Always use the response wrapper — never return raw objects")
    if pagination_found:
        rules.append("- List endpoints must support pagination — never return unbounded results")

    if rules:
        globs = (["src/routes/**", "src/controllers/**", "app/api/**"]
                 if lang in ("typescript", "javascript")
                 else ["app/api/**/*.py", "**/views.py"])
        patterns.append(Pattern(
            category="api",
            description="API conventions",
            evidence=response_wrappers[:5],
            rule_lines=rules,
            globs=globs,
            confidence=0.7,
        ))

    return patterns


def detect_database_patterns(project_dir: Path, files: list, stack: dict) -> list:
    """Detect database access patterns."""
    patterns = []
    lang = stack.get("language", "")
    orm = stack.get("orm", "")

    if not orm:
        return patterns

    repo_files = []
    direct_orm_in_routes = []

    for fp in files:
        content = read_file_safe(fp)
        rel = str(fp.relative_to(project_dir))

        if "repository" in rel.lower() or "repo" in rel.lower():
            repo_files.append(rel)

        is_route = any(kw in rel.lower() for kw in ["route", "controller", "handler", "api", "view"])
        if is_route:
            if lang in ("typescript", "javascript"):
                if re.search(r'prisma\.\w+\.|db\.\w+\.|await\s+\w+Model\.', content):
                    direct_orm_in_routes.append(rel)
            elif lang == "python":
                if re.search(r'session\.\w+\(|\.query\(|\.filter\(', content):
                    direct_orm_in_routes.append(rel)

    rules = []
    if repo_files:
        rules.append(f"- Repository pattern: DB access through {', '.join(repo_files[:3])}")
        rules.append("- Route handlers NEVER call the ORM directly — use repositories")
        if direct_orm_in_routes:
            rules.append(f"- Direct ORM in routes (should refactor): {', '.join(direct_orm_in_routes[:3])}")
    elif direct_orm_in_routes:
        rules.append("- DB access is direct in routes — consider extracting a repository layer")

    if rules:
        patterns.append(Pattern(
            category="database",
            description="Database access pattern",
            evidence=repo_files[:5] or direct_orm_in_routes[:5],
            rule_lines=rules,
            globs=["**/*.ts", "**/*.py"],
            confidence=0.7 if repo_files else 0.5,
        ))

    return patterns


def detect_event_handling_patterns(project_dir: Path, files: list, stack: dict) -> list:
    """Detect event-driven handling patterns (idempotency, retry, DLQ, schema validation)."""
    patterns = []
    lang = stack.get("language", "")
    event_systems = stack.get("event_systems", [])

    if not event_systems:
        return patterns

    consumer_files = []
    producer_files = []
    idempotency_files = []
    retry_files = []
    dlq_files = []
    schema_validation_files = []

    for fp in files:
        content = read_file_safe(fp)
        rel = str(fp.relative_to(project_dir))
        content_lower = content.lower()

        is_consumer = any(kw in rel.lower() for kw in ["consumer", "handler", "subscriber", "listener", "worker", "processor"])
        is_producer = any(kw in rel.lower() for kw in ["producer", "publisher", "emitter", "dispatcher", "sender"])

        if is_consumer:
            consumer_files.append(rel)
        if is_producer:
            producer_files.append(rel)

        # Idempotency checks
        if is_consumer and any(term in content_lower for term in [
            "idempoten", "dedup", "already_processed", "alreadyprocessed",
            "message_id", "messageid", "idempotency_key", "idempotencykey",
        ]):
            idempotency_files.append(rel)

        # Retry / backoff configurations
        if any(term in content_lower for term in [
            "retry", "backoff", "exponential_backoff", "exponentialbackoff",
            "max_retries", "maxretries", "retry_count", "retrycount",
            "retry_policy", "retrypolicy",
        ]):
            retry_files.append(rel)

        # DLQ setup
        if any(term in content_lower for term in [
            "deadletter", "dead_letter", "dlq", "dead letter queue",
            "failed_messages", "failedmessages", "poison",
        ]):
            dlq_files.append(rel)

        # Schema validation in producers
        if is_producer and any(term in content_lower for term in [
            "schema", "validate", "avro", "protobuf", "serialize", "encode",
        ]):
            schema_validation_files.append(rel)

    rules = []
    evidence = []

    if consumer_files:
        rules.append(f"- Event consumers in: {', '.join(consumer_files[:3])}")
        evidence.extend(consumer_files[:3])

    if producer_files:
        rules.append(f"- Event producers in: {', '.join(producer_files[:3])}")
        evidence.extend(producer_files[:3])

    if idempotency_files:
        rules.append(f"- Idempotency checks found in: {', '.join(idempotency_files[:3])}")
        rules.append("- ALL event consumers MUST implement idempotency — follow existing patterns")
    elif consumer_files:
        rules.append("- WARNING: No idempotency checks detected in consumers — add deduplication")

    if retry_files:
        rules.append(f"- Retry/backoff configured in: {', '.join(retry_files[:3])}")
        rules.append("- Use existing retry configuration patterns — never implement custom retry loops")

    if dlq_files:
        rules.append(f"- Dead letter queue handling in: {', '.join(dlq_files[:3])}")
        rules.append("- Failed messages must route to DLQ — never silently drop events")

    if schema_validation_files:
        rules.append(f"- Schema validation in producers: {', '.join(schema_validation_files[:3])}")
        rules.append("- All produced events MUST be schema-validated before publishing")

    if rules:
        globs = ["**/*.ts", "**/*.py", "**/*.go"] if lang == "" else [f"**/*.{lang[:2]}"]
        if lang in ("typescript", "javascript"):
            globs = ["**/*.ts", "**/*.tsx", "**/*.js"]
        elif lang == "python":
            globs = ["**/*.py"]
        elif lang == "go":
            globs = ["**/*.go"]

        patterns.append(Pattern(
            category="event-handling",
            description="Event-driven patterns",
            evidence=evidence[:5],
            rule_lines=rules,
            globs=globs,
            confidence=0.8 if len(evidence) >= 3 else 0.6,
        ))

    return patterns


# ── Deep Analysis Detectors ──────────────────────────────────────────────


def detect_entry_points(project_dir: Path, files: list, stack: dict) -> list:
    """Detect application entry points (main files, server starts, CLI entries)."""
    entries = []
    lang = stack.get("language", "")

    # Check package.json for main/bin fields (Node/TS/JS)
    pkg_json = project_dir / "package.json"
    if pkg_json.exists():
        try:
            pkg = json.loads(pkg_json.read_text())
            main_field = pkg.get("main")
            if main_field:
                entries.append({
                    "type": "package-main",
                    "file": main_field,
                    "description": f"package.json main: {main_field}",
                })
            bin_field = pkg.get("bin")
            if isinstance(bin_field, str):
                entries.append({
                    "type": "cli-entry",
                    "file": bin_field,
                    "description": f"package.json bin: {bin_field}",
                })
            elif isinstance(bin_field, dict):
                for name, path in bin_field.items():
                    entries.append({
                        "type": "cli-entry",
                        "file": path,
                        "description": f"package.json bin '{name}': {path}",
                    })
        except (json.JSONDecodeError, UnicodeDecodeError):
            pass

    for fp in files:
        content = read_file_safe(fp)
        rel = str(fp.relative_to(project_dir))

        # TS/JS: app.listen / server.listen
        if lang in ("typescript", "javascript") or fp.suffix in (".ts", ".tsx", ".js", ".jsx"):
            if re.search(r'(?:app|server)\.listen\s*\(', content):
                entries.append({
                    "type": "server-start",
                    "file": rel,
                    "description": "Server listen call",
                })

        # Python: FastAPI app, manage.py, __main__
        if lang == "python" or fp.suffix == ".py":
            if re.search(r'app\s*=\s*FastAPI\s*\(', content):
                entries.append({
                    "type": "server-start",
                    "file": rel,
                    "description": "FastAPI application instance",
                })
            if fp.name == "manage.py":
                entries.append({
                    "type": "cli-entry",
                    "file": rel,
                    "description": "Django manage.py",
                })
            if re.search(r'if\s+__name__\s*==\s*[\'"]__main__[\'"]\s*:', content):
                entries.append({
                    "type": "script-entry",
                    "file": rel,
                    "description": "Python __main__ guard",
                })

        # Go: func main() and cmd/*/main.go
        if lang == "go" or fp.suffix == ".go":
            if re.search(r'\bfunc\s+main\s*\(\s*\)', content):
                entries.append({
                    "type": "cli-entry" if "cmd/" in rel else "server-start",
                    "file": rel,
                    "description": "Go main function",
                })

        # Rust: src/main.rs
        if lang == "rust" or fp.suffix == ".rs":
            if fp.name == "main.rs":
                entries.append({
                    "type": "cli-entry",
                    "file": rel,
                    "description": "Rust main entry point",
                })

        # Ruby: config.ru, routes.rb
        if lang == "ruby" or fp.suffix == ".rb":
            if fp.name == "config.ru":
                entries.append({
                    "type": "server-start",
                    "file": rel,
                    "description": "Rack config (config.ru)",
                })
            if rel == "config/routes.rb":
                entries.append({
                    "type": "router",
                    "file": rel,
                    "description": "Rails routes",
                })

    # Next.js specific: app/layout.tsx, middleware.ts
    for special in ["app/layout.tsx", "app/layout.ts", "app/layout.jsx", "app/layout.js",
                     "middleware.ts", "middleware.js"]:
        if (project_dir / special).exists():
            desc = "Next.js root layout" if "layout" in special else "Next.js middleware"
            entries.append({
                "type": "framework-entry",
                "file": special,
                "description": desc,
            })

    # Deduplicate by file
    seen = set()
    unique = []
    for e in entries:
        if e["file"] not in seen:
            seen.add(e["file"])
            unique.append(e)

    return unique[:20]


def detect_api_surface(project_dir: Path, files: list, stack: dict) -> dict:
    """Detect API endpoints and routing patterns."""
    endpoints = []
    route_files = set()
    api_style = "rest"
    has_graphql = False
    has_trpc = False
    lang = stack.get("language", "")

    for fp in files:
        content = read_file_safe(fp)
        rel = str(fp.relative_to(project_dir))

        # Express/Fastify: app.get('/path') or router.post('/path')
        if lang in ("typescript", "javascript") or fp.suffix in (".ts", ".tsx", ".js", ".jsx"):
            express_re = re.compile(
                r'(?:app|router)\.(get|post|put|patch|delete)\s*\(\s*[\'"]([^\'"]+)',
                re.IGNORECASE,
            )
            for match in express_re.finditer(content):
                method = match.group(1).upper()
                path = match.group(2)
                endpoints.append({"method": method, "path": path, "file": rel})
                route_files.add(rel)

            # tRPC detection
            if "createTRPCRouter" in content:
                has_trpc = True
                route_files.add(rel)

            # GraphQL schema/typeDefs
            if re.search(r'(?:typeDefs|@Query|@Mutation|gql`)', content):
                has_graphql = True
                route_files.add(rel)

        # Next.js App Router: app/api/**/route.{ts,js}
        if re.match(r'app/api/.+/route\.[jt]sx?$', rel):
            route_files.add(rel)
            # Derive path from file path: app/api/users/route.ts → /api/users
            url_path = "/" + "/".join(rel.split("/")[1:-1])  # strip "app" prefix and "route.ts"
            for method_name in ("GET", "POST", "PUT", "DELETE", "PATCH"):
                if re.search(rf'export\s+(?:async\s+)?function\s+{method_name}\b', content):
                    endpoints.append({"method": method_name, "path": url_path, "file": rel})

        # FastAPI: @app.get("/path") or @router.post("/path")
        if lang == "python" or fp.suffix == ".py":
            fastapi_re = re.compile(
                r'@(?:app|router)\.(get|post|put|patch|delete)\s*\(\s*[\'"]([^\'"]+)',
                re.IGNORECASE,
            )
            for match in fastapi_re.finditer(content):
                method = match.group(1).upper()
                path = match.group(2)
                endpoints.append({"method": method, "path": path, "file": rel})
                route_files.add(rel)

            # Django: path('users/', ...) in urls.py
            if fp.name == "urls.py":
                django_re = re.compile(r'path\(\s*[\'"]([^\'"]+)')
                for match in django_re.finditer(content):
                    path = match.group(1)
                    endpoints.append({"method": "ANY", "path": path, "file": rel})
                    route_files.add(rel)

        # Go: http.HandleFunc and chi/gin/echo
        if lang == "go" or fp.suffix == ".go":
            handle_re = re.compile(r'HandleFunc\(\s*[\'"]([^\'"]+)')
            for match in handle_re.finditer(content):
                endpoints.append({"method": "ANY", "path": match.group(1), "file": rel})
                route_files.add(rel)

            go_router_re = re.compile(
                r'r\.(Get|Post|Put|Delete)\(\s*[\'"]([^\'"]+)',
                re.IGNORECASE,
            )
            for match in go_router_re.finditer(content):
                method = match.group(1).upper()
                path = match.group(2)
                endpoints.append({"method": method, "path": path, "file": rel})
                route_files.add(rel)

        # Rails: routes.rb
        if (lang == "ruby" or fp.suffix == ".rb") and "routes" in fp.name:
            rails_route_re = re.compile(
                r'(get|post|put|patch|delete)\s+[\'"]([^\'"]+)',
                re.IGNORECASE,
            )
            for match in rails_route_re.finditer(content):
                method = match.group(1).upper()
                path = match.group(2)
                endpoints.append({"method": method, "path": path, "file": rel})
                route_files.add(rel)

            resources_re = re.compile(r'resources\s+:(\w+)')
            for match in resources_re.finditer(content):
                resource = match.group(1)
                endpoints.append({"method": "RESOURCE", "path": f"/{resource}", "file": rel})
                route_files.add(rel)

    # GraphQL file detection
    for fp in files:
        if fp.suffix in (".graphql", ".gql"):
            has_graphql = True
            route_files.add(str(fp.relative_to(project_dir)))

    # Determine api_style
    has_rest = len(endpoints) > 0
    if has_graphql and has_trpc:
        api_style = "mixed"
    elif has_graphql and has_rest:
        api_style = "mixed"
    elif has_trpc and has_rest:
        api_style = "mixed"
    elif has_graphql:
        api_style = "graphql"
    elif has_trpc:
        api_style = "trpc"
    elif has_rest:
        api_style = "rest"
    else:
        api_style = "none"

    # Cap endpoints
    total = len(endpoints)
    endpoints = endpoints[:100]

    return {
        "endpoints": endpoints,
        "route_files": sorted(route_files),
        "api_style": api_style,
        "total_endpoints": total,
    }


def detect_complexity_indicators(project_dir: Path, files: list, stack: dict) -> dict:
    """Detect code complexity indicators: large files, function counts, size distribution."""
    func_re = re.compile(
        r'(?:function\s+\w+|def\s+\w+|func\s+\w+|fn\s+\w+|(?:const|let|var)\s+\w+\s*=\s*(?:async\s+)?\()'
    )

    file_stats = []
    total_functions = 0

    for fp in files:
        content = read_file_safe(fp)
        if not content:
            continue
        rel = str(fp.relative_to(project_dir))
        lines = content.count("\n") + (1 if content and not content.endswith("\n") else 0)
        funcs = len(func_re.findall(content))
        total_functions += funcs
        file_stats.append({"file": rel, "lines": lines, "functions": funcs})

    # Size classification
    small = sum(1 for s in file_stats if s["lines"] < 100)
    medium = sum(1 for s in file_stats if 100 <= s["lines"] <= 300)
    large = sum(1 for s in file_stats if 300 < s["lines"] <= 600)
    very_large = sum(1 for s in file_stats if s["lines"] > 600)

    # Large files (>300 lines), sorted by line count desc
    large_files = sorted(
        [s for s in file_stats if s["lines"] > 300],
        key=lambda s: s["lines"],
        reverse=True,
    )[:20]

    # Average file lines
    total_lines = sum(s["lines"] for s in file_stats)
    avg = total_lines / max(1, len(file_stats))

    return {
        "large_files": large_files,
        "avg_file_lines": round(avg, 1),
        "total_functions": total_functions,
        "files_by_size": {
            "small": small,
            "medium": medium,
            "large": large,
            "very_large": very_large,
        },
    }


def assess_test_coverage_map(project_dir: Path, files: list, stack: dict) -> dict:
    """Assess which source files have corresponding test files."""
    test_re = re.compile(r'\.(?:test|spec)\.[jt]sx?$|^test_|_test\.go$|_test\.py$|_test\.rs$')
    utility_names = {
        "index.ts", "index.js", "index.tsx", "index.jsx",
        "types.ts", "types.js", "constants.ts", "constants.js",
        "config.ts", "config.js",
        "__init__.py", "conftest.py", "setup.py",
    }

    test_files = []
    source_files = []
    for fp in files:
        if test_re.search(fp.name):
            test_files.append(fp)
        else:
            source_files.append(fp)

    # Filter out __pycache__ files
    source_files = [fp for fp in source_files if "__pycache__" not in str(fp)]

    # Build set of test basenames for quick lookup
    test_basenames = {}
    for tf in test_files:
        rel = str(tf.relative_to(project_dir))
        test_basenames[tf.name] = rel
        # Also index by parent dir for __tests__ lookups
        test_basenames[(str(tf.parent), tf.name)] = rel

    covered = []
    uncovered = []

    for fp in source_files:
        rel = str(fp.relative_to(project_dir))
        stem = fp.stem
        suffix = fp.suffix
        parent = fp.parent

        # Skip utility files from "uncovered"
        is_utility = fp.name in utility_names

        found_test = False

        if suffix in (".ts", ".tsx", ".js", ".jsx"):
            # foo.ts → foo.test.ts, foo.spec.ts
            base = stem.replace(".d", "")  # handle .d.ts
            for test_suffix in [".test", ".spec"]:
                for ext in [".ts", ".tsx", ".js", ".jsx"]:
                    candidate = f"{base}{test_suffix}{ext}"
                    # Same dir
                    if candidate in test_basenames:
                        found_test = True
                        covered.append({"source": rel, "test": test_basenames[candidate]})
                        break
                    # __tests__ subdir
                    tests_key = (str(parent / "__tests__"), candidate)
                    if tests_key in test_basenames:
                        found_test = True
                        covered.append({"source": rel, "test": test_basenames[tests_key]})
                        break
                if found_test:
                    break

        elif suffix == ".py":
            # foo.py → test_foo.py
            candidate = f"test_{fp.name}"
            if candidate in test_basenames:
                found_test = True
                covered.append({"source": rel, "test": test_basenames[candidate]})
            else:
                # Check tests/ dir
                tests_key = (str(project_dir / "tests"), candidate)
                if tests_key in test_basenames:
                    found_test = True
                    covered.append({"source": rel, "test": test_basenames[tests_key]})

        elif suffix == ".go":
            # foo.go → foo_test.go
            candidate = f"{stem}_test.go"
            if candidate in test_basenames:
                found_test = True
                covered.append({"source": rel, "test": test_basenames[candidate]})

        elif suffix == ".rs":
            # foo.rs → foo_test.rs
            candidate = f"{stem}_test.rs"
            if candidate in test_basenames:
                found_test = True
                covered.append({"source": rel, "test": test_basenames[candidate]})

        if not found_test and not is_utility:
            uncovered.append(rel)

    # Coverage ratio
    coverage_ratio = len(covered) / max(1, len(covered) + len(uncovered))

    # Untested dirs: directories with source files but zero coverage
    dir_has_source = {}
    dir_has_coverage = set()
    for fp in source_files:
        if fp.name not in utility_names:
            d = str(fp.parent.relative_to(project_dir))
            dir_has_source[d] = True
    for c in covered:
        d = str(Path(c["source"]).parent)
        dir_has_coverage.add(d)
    untested_dirs = sorted([d for d in dir_has_source if d not in dir_has_coverage])

    return {
        "covered": covered,
        "uncovered": uncovered,
        "test_files": [str(tf.relative_to(project_dir)) for tf in test_files],
        "coverage_ratio": round(coverage_ratio, 2),
        "untested_dirs": untested_dirs,
    }


def detect_config_and_env(project_dir: Path, files: list, stack: dict) -> dict:
    """Detect environment files, env var references, and config files."""
    lang = stack.get("language", "")

    # Scan for .env* files in project root
    env_files = []
    for item in sorted(project_dir.iterdir()):
        if item.is_file() and item.name.startswith(".env"):
            env_files.append(item.name)

    # Check for .env.example
    has_env_example = (project_dir / ".env.example").exists()

    # Read .env.example for variable names (safe to read)
    example_vars = set()
    if has_env_example:
        try:
            content = (project_dir / ".env.example").read_text(errors="replace")
            for line in content.splitlines():
                line = line.strip()
                if line and not line.startswith("#"):
                    match = re.match(r'^([A-Za-z_][A-Za-z0-9_]*)\s*=', line)
                    if match:
                        example_vars.add(match.group(1))
        except OSError:
            pass

    # Scan source files for env var references
    env_var_refs = {}  # name -> set of files

    ts_env_re = re.compile(r'process\.env\.(\w+)')
    ts_meta_re = re.compile(r'import\.meta\.env\.(\w+)')
    py_environ_re = re.compile(r'os\.environ\[[\'"](\w+)[\'"]\]')
    py_getenv_re = re.compile(r'os\.getenv\([\'"](\w+)[\'"]\)')
    go_getenv_re = re.compile(r'os\.Getenv\([\'"](\w+)[\'"]\)')
    rust_env_re = re.compile(r'env::var\([\'"](\w+)[\'"]\)')

    config_files = []

    for fp in files:
        content = read_file_safe(fp)
        if not content:
            continue
        rel = str(fp.relative_to(project_dir))

        # Detect config files
        if re.match(r'(?:.*[/\\])?config\.[jt]sx?$|(?:.*[/\\])?config\.py$|(?:.*[/\\])?config\.go$|(?:.*[/\\])?config\.rs$|(?:.*[/\\])?settings\.py$', rel):
            config_files.append(rel)
        elif re.match(r'.*\.config\.[jt]sx?$', rel):
            config_files.append(rel)

        # Env var patterns
        regexes = []
        if fp.suffix in (".ts", ".tsx", ".js", ".jsx"):
            regexes = [ts_env_re, ts_meta_re]
        elif fp.suffix == ".py":
            regexes = [py_environ_re, py_getenv_re]
        elif fp.suffix == ".go":
            regexes = [go_getenv_re]
        elif fp.suffix == ".rs":
            regexes = [rust_env_re]

        for regex in regexes:
            for match in regex.finditer(content):
                var_name = match.group(1)
                env_var_refs.setdefault(var_name, set()).add(rel)

    # Format env var references
    env_vars_referenced = [
        {"name": name, "files": sorted(ref_files)}
        for name, ref_files in sorted(env_var_refs.items())
    ]

    return {
        "env_files": env_files,
        "env_vars_referenced": env_vars_referenced,
        "config_files": sorted(config_files),
        "has_env_example": has_env_example,
    }


# ── File Organization ────────────────────────────────────────────────────

def detect_file_organization(project_dir: Path, files: list, stack: dict) -> dict:
    """Detect how the project organizes files."""
    org = {
        "style": "unknown",
        "test_location": "unknown",
        "barrel_exports": False,
        "src_dir": None,
    }

    if (project_dir / "src").exists():
        org["src_dir"] = "src"
    elif (project_dir / "app").exists():
        org["src_dir"] = "app"

    # Barrel exports
    barrel_count = 0
    for fp in files:
        if fp.name in ("index.ts", "index.js", "index.tsx"):
            content = read_file_safe(fp)
            if re.search(r'export\s+(?:\*|\{)', content):
                barrel_count += 1
    org["barrel_exports"] = barrel_count >= 3

    # Test location
    test_files = [fp for fp in files if re.search(r'\.(?:test|spec)\.[jt]sx?$|^test_|_test\.', fp.name)]
    co_located = 0
    separate = 0
    tests_dir = 0

    for tf in test_files:
        rel = str(tf.relative_to(project_dir))
        if "__tests__" in rel:
            tests_dir += 1
        elif "test/" in rel or "tests/" in rel:
            separate += 1
        else:
            co_located += 1

    if co_located > separate and co_located > tests_dir:
        org["test_location"] = "co-located"
    elif tests_dir > 0:
        org["test_location"] = "__tests__"
    elif separate > 0:
        org["test_location"] = "separate"

    # Organization style
    feature_dirs = set()
    layer_dirs = set()

    for fp in files:
        rel = str(fp.relative_to(project_dir))
        parts = rel.split("/")
        if len(parts) >= 3:
            if parts[1] in ("features", "modules", "domains"):
                feature_dirs.add(parts[2])
            elif parts[1] in ("controllers", "services", "models", "repositories", "utils", "lib", "middleware"):
                layer_dirs.add(parts[1])

    if len(feature_dirs) >= 2:
        org["style"] = "feature-based"
    elif len(layer_dirs) >= 2:
        org["style"] = "layer-based"

    return org


# ── Key Abstractions ─────────────────────────────────────────────────────

def detect_key_abstractions(project_dir: Path, files: list, stack: dict) -> list:
    """Find important abstractions that should be reused."""
    abstractions = []
    lang = stack.get("language", "")

    # Built-in hooks to ignore
    react_hooks = {"useState", "useEffect", "useRef", "useCallback", "useMemo",
                   "useContext", "useReducer", "useLayoutEffect", "useId",
                   "useTransition", "useDeferredValue", "useImperativeHandle"}

    for fp in files:
        content = read_file_safe(fp)
        rel = str(fp.relative_to(project_dir))

        if lang in ("typescript", "javascript"):
            # Custom hooks
            hooks = re.findall(r'export\s+(?:function|const)\s+(use[A-Z]\w+)', content)
            for hook in hooks:
                if hook not in react_hooks:
                    abstractions.append({"name": hook, "file": rel, "type": "hook"})

            # Service/repository classes
            services = re.findall(r'export\s+class\s+(\w+(?:Service|Client|Repository|Store))', content)
            for svc in services:
                abstractions.append({"name": svc, "file": rel, "type": "service"})

            # Utility functions in lib/utils
            if any(d in rel for d in ["lib/", "utils/", "helpers/"]):
                exports = re.findall(r'export\s+(?:function|const)\s+(\w+)', content)
                for exp in exports:
                    if not exp.startswith("_") and len(exp) > 3:
                        abstractions.append({"name": exp, "file": rel, "type": "utility"})

        elif lang == "python":
            classes = re.findall(r'class\s+(\w+(?:Service|Repository|Client|Manager|Handler))\b', content)
            for cls in classes:
                abstractions.append({"name": cls, "file": rel, "type": "service"})

    # Deduplicate
    seen = set()
    unique = []
    for a in abstractions:
        key = (a["name"], a["file"])
        if key not in seen:
            seen.add(key)
            unique.append(a)

    return unique[:50]


# ── Main Analysis ────────────────────────────────────────────────────────

def analyze(project_dir: Path, deep: bool = False) -> AnalysisResult:
    """Run full codebase analysis. When deep=True, includes entry points, API surface, complexity, test coverage, and config/env."""
    stack = detect_stack(project_dir)
    files = collect_source_files(project_dir)

    all_patterns = []
    all_patterns.extend(detect_error_handling(project_dir, files, stack))
    all_patterns.extend(detect_auth_patterns(project_dir, files, stack))
    all_patterns.extend(detect_validation(project_dir, files, stack))
    all_patterns.extend(detect_data_fetching(project_dir, files, stack))
    all_patterns.extend(detect_testing_patterns(project_dir, files, stack))
    all_patterns.extend(detect_api_patterns(project_dir, files, stack))
    all_patterns.extend(detect_database_patterns(project_dir, files, stack))
    all_patterns.extend(detect_event_handling_patterns(project_dir, files, stack))

    # Filter by confidence
    confident = [p for p in all_patterns if p.confidence >= 0.5]

    result = AnalysisResult(
        project_dir=str(project_dir),
        stack=stack,
        patterns=confident,
        key_abstractions=detect_key_abstractions(project_dir, files, stack),
        file_organization=detect_file_organization(project_dir, files, stack),
    )

    if deep:
        result.entry_points = detect_entry_points(project_dir, files, stack)
        result.api_surface = detect_api_surface(project_dir, files, stack)
        result.complexity = detect_complexity_indicators(project_dir, files, stack)
        result.test_coverage_map = assess_test_coverage_map(project_dir, files, stack)
        result.config_env = detect_config_and_env(project_dir, files, stack)

    return result


# ── Rule Generation ──────────────────────────────────────────────────────

def generate_rules_from_analysis(result: AnalysisResult) -> list:
    """Convert analysis results into rule files. Returns [(name, content), ...]."""
    rules = []

    # Group patterns by category
    categories = {}
    for pattern in result.patterns:
        categories.setdefault(pattern.category, []).append(pattern)

    for category, cat_patterns in categories.items():
        all_globs = set()
        all_rules = []

        for p in cat_patterns:
            all_globs.update(p.globs)
            all_rules.extend(p.rule_lines)

        globs_str = json.dumps(sorted(all_globs))
        desc = f"{category.replace('-', ' ').title()} conventions (auto-detected)"
        content = f"---\nglobs: {globs_str}\ndescription: {desc}\n---\n\n"
        for rule_line in all_rules:
            content += rule_line + "\n"
        rules.append((f"project-{category}", content))

    # File organization rule
    org = result.file_organization
    if org["style"] != "unknown" or org["test_location"] != "unknown":
        org_rules = []
        if org["style"] != "unknown":
            org_rules.append(f"- Project uses **{org['style']}** organization")
        if org["test_location"] != "unknown":
            org_rules.append(f"- Tests are **{org['test_location']}** with source files")
        if org["barrel_exports"]:
            org_rules.append("- Uses barrel exports (index.ts) — update them when adding new modules")
        if org["src_dir"]:
            org_rules.append(f"- Source root: `{org['src_dir']}/`")

        content = '---\nglobs: ["**/*"]\ndescription: File organization conventions (auto-detected)\n---\n\n'
        for rule in org_rules:
            content += rule + "\n"
        rules.append(("project-organization", content))

    # Key abstractions rule
    if result.key_abstractions:
        by_type = {}
        for a in result.key_abstractions:
            by_type.setdefault(a["type"], []).append(a)

        abs_lines = []
        for atype, items in by_type.items():
            items = items[:10]
            if atype == "hook":
                abs_lines.append("\n**Custom Hooks** — reuse instead of reimplementing:")
                for item in items:
                    abs_lines.append(f"- `{item['name']}` from `{item['file']}`")
            elif atype == "service":
                abs_lines.append("\n**Services/Repositories** — use for data access:")
                for item in items:
                    abs_lines.append(f"- `{item['name']}` from `{item['file']}`")
            elif atype == "utility" and len(items) <= 8:
                abs_lines.append("\n**Shared Utilities:**")
                for item in items:
                    abs_lines.append(f"- `{item['name']}` from `{item['file']}`")

        if abs_lines:
            content = '---\nglobs: ["**/*"]\ndescription: Key project abstractions to reuse (auto-detected)\n---\n'
            for line in abs_lines:
                content += line + "\n"
            rules.append(("project-abstractions", content))

    return rules


# ── Feedback Loop ───────────────────────────────────────────────────

# Map keywords in learned corrections to pattern categories
CATEGORY_KEYWORDS = {
    "error-handling": ["error", "exception", "throw", "catch", "try", "apperror", "httperror"],
    "auth": ["auth", "login", "token", "session", "permission", "role", "middleware", "jwt"],
    "validation": ["valid", "schema", "zod", "yup", "joi", "pydantic", "input", "sanitize"],
    "data-fetching": ["fetch", "query", "usequery", "useswr", "trpc", "api call", "server action"],
    "state-management": ["state", "store", "zustand", "redux", "jotai", "atom"],
    "testing": ["test", "mock", "fixture", "jest", "vitest", "pytest", "spec", "assert"],
    "api": ["endpoint", "route", "controller", "handler", "response", "pagination", "rest"],
    "database": ["database", "db", "query", "repository", "orm", "prisma", "migration", "model"],
    "event-handling": ["event", "kafka", "rabbitmq", "bullmq", "celery", "consumer", "producer", "queue", "message", "saga", "cqrs", "dlq", "idempoten", "temporal"],
}


def match_correction_to_category(correction: str) -> str | None:
    """Match a learned correction to a pattern category by keyword overlap."""
    text = correction.lower()
    best_category = None
    best_score = 0
    for category, keywords in CATEGORY_KEYWORDS.items():
        score = sum(1 for kw in keywords if kw in text)
        if score > best_score:
            best_score = score
            best_category = category
    return best_category if best_score > 0 else None


def incorporate_learned(result: AnalysisResult, project_dir: Path) -> AnalysisResult:
    """Enhance analysis results with learned corrections from learn.py.

    Reads .claude/learn-log.json and matches corrections to detected pattern
    categories. Adds matched corrections as extra rule lines to existing patterns,
    or creates new patterns for unmatched categories.
    """
    log_path = project_dir / ".claude" / "learn-log.json"
    if not log_path.exists():
        return result

    try:
        log = json.loads(log_path.read_text())
    except (json.JSONDecodeError, UnicodeDecodeError):
        return result

    if not log:
        return result

    # Group corrections by matched category (deduplicate)
    by_category: dict[str | None, list[str]] = {}
    seen_corrections: set[str] = set()
    for entry in log:
        correction = entry.get("correction", "")
        if not correction or correction in seen_corrections:
            continue
        seen_corrections.add(correction)
        category = match_correction_to_category(correction)
        by_category.setdefault(category, []).append(correction)

    # Build index of existing pattern categories
    existing_categories = {p.category for p in result.patterns}

    for category, corrections in by_category.items():
        if category is None:
            continue

        if category in existing_categories:
            # Append learned corrections to existing pattern's rule lines
            for p in result.patterns:
                if p.category == category:
                    for correction in corrections:
                        rule = correction if correction.startswith("- ") else f"- {correction}"
                        if rule not in p.rule_lines:
                            p.rule_lines.append(f"{rule} *(learned)*")
                    break
        else:
            # Create new pattern from learned corrections
            rule_lines = []
            for correction in corrections:
                rule = correction if correction.startswith("- ") else f"- {correction}"
                rule_lines.append(f"{rule} *(learned)*")
            result.patterns.append(Pattern(
                category=category,
                description=f"{category.replace('-', ' ').title()} (from learned corrections)",
                evidence=[],
                rule_lines=rule_lines,
                globs=["**/*"],
                confidence=0.6,
            ))

    return result


def check_stale_rules(project_dir: Path) -> list[dict]:
    """Check if project-*.md rules reference files/patterns that no longer exist.

    Returns list of {file, issue, suggestion} dicts.
    """
    stale = []
    rules_dir = project_dir / ".claude" / "rules"
    if not rules_dir.exists():
        return stale

    for rf in rules_dir.glob("project-*.md"):
        try:
            content = rf.read_text()
        except UnicodeDecodeError:
            continue

        # Check backtick-quoted file paths like `src/lib/errors.ts`
        referenced_files = re.findall(r'`([a-zA-Z0-9_./-]+\.[a-zA-Z]+)`', content)
        for ref in referenced_files:
            ref_path = project_dir / ref
            if not ref_path.exists() and not any(c in ref for c in ['*', '?', '{']):
                stale.append({
                    "file": rf.name,
                    "issue": f"References `{ref}` which no longer exists",
                    "suggestion": f"Re-run analyzer to update {rf.name}",
                })

        # Check backtick-quoted identifiers like `AppError` — verify they exist in source
        identifiers = re.findall(r'`([A-Z][a-zA-Z]+(?:Error|Service|Client|Repository|Handler|Manager))`', content)
        if identifiers:
            # Quick scan: do these identifiers still exist in the codebase?
            source_files = collect_source_files(project_dir)
            all_content = ""
            for sf in source_files[:100]:  # limit scan
                all_content += read_file_safe(sf)
            for ident in identifiers:
                if ident not in all_content:
                    stale.append({
                        "file": rf.name,
                        "issue": f"References `{ident}` which was not found in codebase",
                        "suggestion": f"Re-run analyzer to update {rf.name}",
                    })

    return stale


def get_last_analysis_time(project_dir: Path) -> str | None:
    """Read last_analysis timestamp from launchpad-config.json."""
    config_path = project_dir / ".claude" / "launchpad-config.json"
    if not config_path.exists():
        return None
    try:
        config = json.loads(config_path.read_text())
        return config.get("last_analysis")
    except (json.JSONDecodeError, UnicodeDecodeError):
        return None


def set_last_analysis_time(project_dir: Path):
    """Record current time as last_analysis in launchpad-config.json."""
    config_path = project_dir / ".claude" / "launchpad-config.json"
    if not config_path.exists():
        return
    try:
        config = json.loads(config_path.read_text())
        config["last_analysis"] = datetime.now().isoformat()
        config_path.write_text(json.dumps(config, indent=2) + "\n")
    except (json.JSONDecodeError, UnicodeDecodeError):
        pass


# ── Output ───────────────────────────────────────────────────────────────

def format_report(result: AnalysisResult) -> str:
    """Format analysis results as a human-readable report."""
    lines = []
    lines.append("Codebase Analysis Report")
    lines.append("=" * 50)

    lines.append("\nDetected Stack:")
    for key, value in result.stack.items():
        lines.append(f"  {key}: {value}")

    org = result.file_organization
    lines.append(f"\nFile Organization:")
    lines.append(f"  Style: {org['style']}")
    lines.append(f"  Tests: {org['test_location']}")
    lines.append(f"  Barrel exports: {'yes' if org['barrel_exports'] else 'no'}")

    lines.append(f"\nPatterns Detected ({len(result.patterns)}):")
    for p in result.patterns:
        conf = "high" if p.confidence >= 0.8 else "medium" if p.confidence >= 0.6 else "low"
        lines.append(f"\n  [{conf}] {p.category}: {p.description}")
        for rule in p.rule_lines:
            lines.append(f"    {rule}")
        if p.evidence:
            lines.append(f"    Evidence: {', '.join(p.evidence[:3])}")

    if result.key_abstractions:
        lines.append(f"\nKey Abstractions ({len(result.key_abstractions)}):")
        by_type = {}
        for a in result.key_abstractions:
            by_type.setdefault(a["type"], []).append(a)
        for atype, items in sorted(by_type.items()):
            lines.append(f"  {atype}s:")
            for item in items[:5]:
                lines.append(f"    {item['name']} ({item['file']})")
            if len(items) > 5:
                lines.append(f"    ... and {len(items) - 5} more")

    # Deep analysis sections
    if result.entry_points:
        lines.append(f"\nEntry Points ({len(result.entry_points)}):")
        for ep in result.entry_points:
            lines.append(f"  [{ep['type']}] {ep['file']}: {ep['description']}")

    if result.api_surface:
        surface = result.api_surface
        lines.append(f"\nAPI Surface (style: {surface.get('api_style', 'unknown')}, {surface.get('total_endpoints', 0)} endpoints):")
        for ep in surface.get("endpoints", [])[:20]:
            lines.append(f"  {ep['method']} {ep['path']}  ({ep['file']})")
        if surface.get("total_endpoints", 0) > 20:
            lines.append(f"  ... and {surface['total_endpoints'] - 20} more")
        if surface.get("route_files"):
            lines.append(f"  Route files: {', '.join(surface['route_files'][:5])}")

    if result.complexity:
        cx = result.complexity
        lines.append(f"\nComplexity Indicators:")
        lines.append(f"  Average file size: {cx.get('avg_file_lines', 0)} lines")
        lines.append(f"  Total functions: {cx.get('total_functions', 0)}")
        sizes = cx.get("files_by_size", {})
        lines.append(f"  Size distribution: {sizes.get('small', 0)} small, {sizes.get('medium', 0)} medium, {sizes.get('large', 0)} large, {sizes.get('very_large', 0)} very large")
        if cx.get("large_files"):
            lines.append(f"  Large files:")
            for lf in cx["large_files"][:10]:
                lines.append(f"    {lf['file']}: {lf['lines']} lines, {lf['functions']} functions")

    if result.test_coverage_map:
        tcm = result.test_coverage_map
        lines.append(f"\nTest Coverage Map:")
        lines.append(f"  Coverage ratio: {tcm.get('coverage_ratio', 0):.0%}")
        lines.append(f"  Covered: {len(tcm.get('covered', []))} files")
        lines.append(f"  Uncovered: {len(tcm.get('uncovered', []))} files")
        if tcm.get("untested_dirs"):
            lines.append(f"  Untested directories: {', '.join(tcm['untested_dirs'][:5])}")

    if result.config_env:
        ce = result.config_env
        lines.append(f"\nConfig & Environment:")
        if ce.get("env_files"):
            lines.append(f"  Env files: {', '.join(ce['env_files'])}")
        lines.append(f"  Has .env.example: {'yes' if ce.get('has_env_example') else 'no'}")
        if ce.get("env_vars_referenced"):
            lines.append(f"  Env vars referenced ({len(ce['env_vars_referenced'])}):")
            for var in ce["env_vars_referenced"][:10]:
                lines.append(f"    {var['name']} (in {', '.join(var['files'][:3])})")
        if ce.get("config_files"):
            lines.append(f"  Config files: {', '.join(ce['config_files'][:5])}")

    gen_rules = generate_rules_from_analysis(result)
    lines.append(f"\nWould generate {len(gen_rules)} rule files:")
    for name, _ in gen_rules:
        lines.append(f"  .claude/rules/{name}.md")

    return "\n".join(lines)


def write_rules(project_dir: Path, result: AnalysisResult, force: bool = False) -> list:
    """Write generated rules to .claude/rules/. Returns list of created file paths."""
    gen_rules = generate_rules_from_analysis(result)
    rules_dir = project_dir / ".claude" / "rules"
    rules_dir.mkdir(parents=True, exist_ok=True)

    created = []
    for name, content in gen_rules:
        fp = rules_dir / f"{name}.md"
        if fp.exists() and not force:
            print(f"  Skipped {fp.name} (exists, use --force to overwrite)")
            continue
        fp.write_text(content)
        created.append(f".claude/rules/{name}.md")
        print(f"  Created {fp.name}")

    # Record analysis timestamp
    set_last_analysis_time(project_dir)

    return created


# ── CLI ──────────────────────────────────────────────────────────────────

def main():
    p = argparse.ArgumentParser(description="Claude Launchpad Codebase Analyzer")
    p.add_argument("project_dir", help="Path to the project root")
    p.add_argument("--write-rules", action="store_true", help="Write rule files to .claude/rules/")
    p.add_argument("--json", action="store_true", help="JSON output")
    p.add_argument("--force", action="store_true", help="Overwrite existing rule files")
    p.add_argument("--incorporate-learned", action="store_true", dest="incorporate_learned",
                   help="Enhance analysis with learned corrections from /learn")
    p.add_argument("--check-stale", action="store_true", dest="check_stale",
                   help="Check for stale project-*.md rules")
    p.add_argument("--migrate-ai-configs", action="store_true", dest="migrate_ai_configs",
                   help="Detect and migrate other AI tool configs (.cursorrules, copilot, etc.)")
    p.add_argument("--deep", action="store_true",
                   help="Include deep analysis: entry points, API surface, complexity, test coverage, config/env")
    args = p.parse_args()

    project_dir = Path(args.project_dir).resolve()
    if not project_dir.exists():
        print(f"Error: {project_dir} does not exist", file=sys.stderr)
        sys.exit(1)

    if args.check_stale:
        stale = check_stale_rules(project_dir)
        if args.json:
            print(json.dumps(stale, indent=2))
        elif stale:
            print(f"Found {len(stale)} stale references in analyzer rules:\n")
            for s in stale:
                print(f"  {s['file']}: {s['issue']}")
                print(f"    → {s['suggestion']}")
        else:
            print("No stale references found in analyzer rules.")
        sys.exit(0)

    if args.migrate_ai_configs:
        configs = detect_ai_configs(project_dir)
        if configs:
            print(f"Found {len(configs)} AI config(s):")
            for c in configs:
                print(f"  {c['source']}: {c['path']}")
            migrated = migrate_ai_configs(project_dir, configs)
            for m in migrated:
                print(f"  Created {m}")
            if not migrated:
                print("  All configs already migrated (files exist)")
        else:
            print("No AI tool configs found")
        sys.exit(0)

    result = analyze(project_dir, deep=args.deep)

    if args.incorporate_learned:
        result = incorporate_learned(result, project_dir)

    if args.json:
        output = {
            "project_dir": result.project_dir,
            "stack": result.stack,
            "patterns": [
                {
                    "category": p.category,
                    "description": p.description,
                    "evidence": p.evidence,
                    "rule_lines": p.rule_lines,
                    "globs": p.globs,
                    "confidence": p.confidence,
                }
                for p in result.patterns
            ],
            "key_abstractions": result.key_abstractions,
            "file_organization": result.file_organization,
        }
        if result.entry_points:
            output["entry_points"] = result.entry_points
        if result.api_surface:
            output["api_surface"] = result.api_surface
        if result.complexity:
            output["complexity"] = result.complexity
        if result.test_coverage_map:
            output["test_coverage_map"] = result.test_coverage_map
        if result.config_env:
            output["config_env"] = result.config_env
        print(json.dumps(output, indent=2))
    elif args.write_rules:
        created = write_rules(project_dir, result, force=args.force)
        if created:
            print(f"\n{len(created)} rule files written to .claude/rules/")
        else:
            print("\nNo rules generated — codebase may be too small or patterns unclear")
    else:
        print(format_report(result))

    sys.exit(0)


if __name__ == "__main__":
    main()
