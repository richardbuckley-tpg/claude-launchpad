#!/usr/bin/env python3
"""
claude-bootstrap project analyzer

Analyzes an existing project's tech stack, structure, and Claude Code configuration.
Outputs a JSON report of detected technologies and missing Claude Code features.

Usage:
    python analyze_project.py /path/to/project

This script is used in "existing project" mode to auto-detect the stack before
asking the user interview questions.
"""

import json
import os
import re
import sys
from pathlib import Path


class ProjectAnalyzer:
    """Analyzes an existing project and reports findings."""

    def __init__(self, root: str):
        self.root = Path(root).resolve()
        self.findings = {
            "language": {"value": None, "confidence": "none"},
            "frontend": {"value": None, "confidence": "none"},
            "backend": {"value": None, "confidence": "none"},
            "database": {"value": None, "confidence": "none"},
            "orm": {"value": None, "confidence": "none"},
            "auth": {"value": None, "confidence": "none"},
            "testing": {"value": None, "confidence": "none"},
            "ci_cd": {"value": None, "confidence": "none"},
            "deployment": {"value": None, "confidence": "none"},
            "docker": {"value": None, "confidence": "none"},
            "monorepo": {"value": None, "confidence": "none"},
            "claude_config": {
                "claude_md": False,
                "claude_dir": False,
                "agents": [],
                "rules": [],
                "commands": [],
                "settings_json": False,
                "handoff_md": False,
                "mcp_json": False,
                "claudeignore": False,
            },
        }

    def detect(self, name: str, value: str, confidence: str = "high"):
        """Record a detection."""
        self.findings[name] = {"value": value, "confidence": confidence}

    def file_exists(self, *paths) -> bool:
        """Check if any of the given paths exist."""
        for p in paths:
            if (self.root / p).exists():
                return True
        return False

    def read_file(self, path: str, max_lines: int = 100) -> str:
        """Read a file, return empty string if not found."""
        try:
            filepath = self.root / path
            if filepath.is_file():
                with open(filepath, "r", errors="ignore") as f:
                    return "".join(f.readlines()[:max_lines])
        except Exception:
            pass
        return ""

    def detect_language(self):
        """Detect primary programming language."""
        if self.file_exists("tsconfig.json"):
            self.detect("language", "TypeScript")
        elif self.file_exists("package.json"):
            self.detect("language", "JavaScript")
        elif self.file_exists("pyproject.toml", "setup.py", "requirements.txt"):
            self.detect("language", "Python")
        elif self.file_exists("go.mod"):
            self.detect("language", "Go")
        elif self.file_exists("Cargo.toml"):
            self.detect("language", "Rust")
        elif self.file_exists("composer.json"):
            self.detect("language", "PHP")
        elif self.file_exists("Gemfile"):
            self.detect("language", "Ruby")
        elif any((self.root).glob("*.csproj")):
            self.detect("language", "C#/.NET")

    def detect_frontend(self):
        """Detect frontend framework."""
        pkg = self.read_file("package.json")

        if self.file_exists("next.config.js", "next.config.ts", "next.config.mjs"):
            # Detect App Router vs Pages
            if self.file_exists("src/app", "app"):
                self.detect("frontend", "Next.js (App Router)")
            else:
                self.detect("frontend", "Next.js (Pages Router)")
        elif self.file_exists("nuxt.config.ts", "nuxt.config.js"):
            self.detect("frontend", "Nuxt 3")
        elif self.file_exists("svelte.config.js", "svelte.config.ts"):
            self.detect("frontend", "SvelteKit")
        elif self.file_exists("angular.json"):
            self.detect("frontend", "Angular")
        elif "vue" in pkg:
            self.detect("frontend", "Vue 3")
        elif self.file_exists("vite.config.ts", "vite.config.js"):
            if "react" in pkg:
                self.detect("frontend", "React + Vite")
            else:
                self.detect("frontend", "Vite", "medium")
        elif "react" in pkg:
            self.detect("frontend", "React", "medium")

    def detect_backend(self):
        """Detect backend framework."""
        pkg = self.read_file("package.json")
        pyproject = self.read_file("pyproject.toml")

        if "express" in pkg:
            self.detect("backend", "Node.js/Express")
        elif "fastify" in pkg:
            self.detect("backend", "Node.js/Fastify")
        elif "hono" in pkg:
            self.detect("backend", "Hono")
        elif "fastapi" in pyproject or self.file_exists("app/main.py"):
            self.detect("backend", "Python/FastAPI")
        elif "django" in pyproject:
            self.detect("backend", "Python/Django")
        elif "flask" in pyproject:
            self.detect("backend", "Python/Flask")
        elif self.file_exists("go.mod"):
            gomod = self.read_file("go.mod")
            if "gin-gonic" in gomod:
                self.detect("backend", "Go/Gin")
            elif "echo" in gomod:
                self.detect("backend", "Go/Echo")
            elif "fiber" in gomod:
                self.detect("backend", "Go/Fiber")
            else:
                self.detect("backend", "Go", "medium")
        elif self.file_exists("Gemfile"):
            gemfile = self.read_file("Gemfile")
            if "rails" in gemfile:
                self.detect("backend", "Ruby on Rails")

        # Check if it's integrated (e.g., Next.js API routes)
        frontend = self.findings.get("frontend", {}).get("value", "")
        if frontend and "Next.js" in str(frontend):
            if self.file_exists("src/app/api", "pages/api", "app/api"):
                if not self.findings["backend"]["value"]:
                    self.detect("backend", "API Routes (integrated)")

    def detect_database(self):
        """Detect database."""
        pkg = self.read_file("package.json")
        docker_compose = self.read_file("docker-compose.yml")
        docker_compose += self.read_file("docker-compose.yaml")

        # Check ORM first
        if "prisma" in pkg or self.file_exists("prisma/schema.prisma"):
            self.detect("orm", "Prisma")
            schema = self.read_file("prisma/schema.prisma")
            if "postgresql" in schema or "postgres" in schema:
                self.detect("database", "PostgreSQL")
            elif "mongodb" in schema:
                self.detect("database", "MongoDB")
            elif "mysql" in schema:
                self.detect("database", "MySQL")
            elif "sqlite" in schema:
                self.detect("database", "SQLite")
        elif "drizzle" in pkg or self.file_exists("drizzle.config.ts"):
            self.detect("orm", "Drizzle")
        elif self.file_exists("alembic/", "alembic.ini"):
            self.detect("orm", "SQLAlchemy/Alembic")

        # Check docker-compose for DB services
        if not self.findings["database"]["value"]:
            if "postgres" in docker_compose.lower():
                self.detect("database", "PostgreSQL", "medium")
            elif "mongo" in docker_compose.lower():
                self.detect("database", "MongoDB", "medium")
            elif "mysql" in docker_compose.lower() or "mariadb" in docker_compose.lower():
                self.detect("database", "MySQL", "medium")
            elif "dynamodb" in docker_compose.lower():
                self.detect("database", "DynamoDB", "medium")

        # Check for Supabase
        if "@supabase" in pkg or self.file_exists(".supabase/"):
            self.detect("database", "Supabase (PostgreSQL)")

    def detect_auth(self):
        """Detect authentication provider."""
        pkg = self.read_file("package.json")
        env_example = self.read_file(".env.example")
        env_local = self.read_file(".env.local")

        if "@clerk" in pkg or "CLERK" in env_example or "CLERK" in env_local:
            self.detect("auth", "Clerk")
        elif "next-auth" in pkg or "AUTH_SECRET" in env_example:
            self.detect("auth", "NextAuth/Auth.js")
        elif "lucia" in pkg:
            self.detect("auth", "Lucia")
        elif "@supabase/auth" in pkg or "supabase" in pkg:
            if self.findings["database"]["value"] and "Supabase" in self.findings["database"]["value"]:
                self.detect("auth", "Supabase Auth")
        elif "firebase" in pkg:
            self.detect("auth", "Firebase Auth")
        elif "jsonwebtoken" in pkg or "jose" in pkg:
            self.detect("auth", "Custom JWT", "medium")

    def detect_testing(self):
        """Detect testing frameworks."""
        pkg = self.read_file("package.json")
        pyproject = self.read_file("pyproject.toml")
        frameworks = []

        if "vitest" in pkg:
            frameworks.append("Vitest")
        if "jest" in pkg and "vitest" not in pkg:
            frameworks.append("Jest")
        if "playwright" in pkg:
            frameworks.append("Playwright")
        if "cypress" in pkg:
            frameworks.append("Cypress")
        if "pytest" in pyproject or self.file_exists("pytest.ini", "conftest.py"):
            frameworks.append("pytest")
        if "mocha" in pkg:
            frameworks.append("Mocha")

        if frameworks:
            self.detect("testing", " + ".join(frameworks))

    def detect_cicd(self):
        """Detect CI/CD setup."""
        if self.file_exists(".github/workflows"):
            workflows = list((self.root / ".github/workflows").glob("*.yml"))
            workflows += list((self.root / ".github/workflows").glob("*.yaml"))
            self.detect("ci_cd", f"GitHub Actions ({len(workflows)} workflow(s))")
        elif self.file_exists(".gitlab-ci.yml"):
            self.detect("ci_cd", "GitLab CI")
        elif self.file_exists(".circleci/config.yml"):
            self.detect("ci_cd", "CircleCI")
        elif self.file_exists("Jenkinsfile"):
            self.detect("ci_cd", "Jenkins")
        elif self.file_exists("bitbucket-pipelines.yml"):
            self.detect("ci_cd", "Bitbucket Pipelines")

    def detect_deployment(self):
        """Detect deployment platform."""
        if self.file_exists("vercel.json", ".vercel/"):
            self.detect("deployment", "Vercel")
        elif self.file_exists("railway.json", "railway.toml"):
            self.detect("deployment", "Railway")
        elif self.file_exists("fly.toml"):
            self.detect("deployment", "Fly.io")
        elif self.file_exists("netlify.toml"):
            self.detect("deployment", "Netlify")
        elif self.file_exists("render.yaml"):
            self.detect("deployment", "Render")
        elif self.file_exists("Procfile"):
            self.detect("deployment", "Heroku-compatible", "medium")
        elif self.file_exists("serverless.yml", "serverless.ts"):
            self.detect("deployment", "AWS (Serverless Framework)")
        elif self.file_exists("cdk.json", "template.yaml"):
            self.detect("deployment", "AWS (CDK/SAM)")
        elif self.file_exists("app.yaml"):
            self.detect("deployment", "Google Cloud", "medium")

    def detect_docker(self):
        """Detect Docker setup."""
        has_dockerfile = self.file_exists("Dockerfile")
        has_compose = self.file_exists("docker-compose.yml", "docker-compose.yaml")

        if has_dockerfile and has_compose:
            self.detect("docker", "Docker + Compose")
        elif has_dockerfile:
            self.detect("docker", "Dockerfile only")
        elif has_compose:
            self.detect("docker", "Docker Compose only")

    def detect_monorepo(self):
        """Detect monorepo setup."""
        if self.file_exists("turbo.json"):
            self.detect("monorepo", "Turborepo")
        elif self.file_exists("nx.json"):
            self.detect("monorepo", "Nx")
        elif self.file_exists("lerna.json"):
            self.detect("monorepo", "Lerna")
        elif self.file_exists("pnpm-workspace.yaml"):
            self.detect("monorepo", "pnpm workspaces")

    def detect_claude_config(self):
        """Detect existing Claude Code configuration."""
        cc = self.findings["claude_config"]

        cc["claude_md"] = self.file_exists("CLAUDE.md")
        cc["claude_dir"] = self.file_exists(".claude/")
        cc["settings_json"] = self.file_exists(".claude/settings.json")
        cc["handoff_md"] = self.file_exists(".claude/handoff.md")
        cc["mcp_json"] = self.file_exists(".mcp.json")
        cc["claudeignore"] = self.file_exists(".claudeignore")

        # Detect agents
        agents_dir = self.root / ".claude" / "agents"
        if agents_dir.is_dir():
            cc["agents"] = [f.stem for f in agents_dir.glob("*.md")]

        # Detect rules
        rules_dir = self.root / ".claude" / "rules"
        if rules_dir.is_dir():
            cc["rules"] = [f.stem for f in rules_dir.glob("*.md")]

        # Detect commands
        commands_dir = self.root / ".claude" / "commands"
        if commands_dir.is_dir():
            cc["commands"] = [f.stem for f in commands_dir.glob("*.md")]

    def analyze(self) -> dict:
        """Run all detections and return findings."""
        if not self.root.is_dir():
            print(f"Error: {self.root} is not a directory", file=sys.stderr)
            sys.exit(1)

        self.detect_language()
        self.detect_frontend()
        self.detect_backend()
        self.detect_database()
        self.detect_auth()
        self.detect_testing()
        self.detect_cicd()
        self.detect_deployment()
        self.detect_docker()
        self.detect_monorepo()
        self.detect_claude_config()

        return self.findings

    def print_report(self):
        """Print a human-readable analysis report."""
        findings = self.analyze()
        cc = findings["claude_config"]

        print(f"\n{'='*60}")
        print(f"  Project Analysis: {self.root.name}")
        print(f"{'='*60}\n")

        # Tech stack table
        print("Tech Stack Detection")
        print("-" * 50)
        categories = [
            "language", "frontend", "backend", "database", "orm",
            "auth", "testing", "ci_cd", "deployment", "docker", "monorepo"
        ]
        for cat in categories:
            info = findings[cat]
            if info["value"]:
                conf_icon = {"high": "✅", "medium": "⚠️ ", "low": "❓"}.get(info["confidence"], "  ")
                print(f"  {conf_icon} {cat:15s} {info['value']:30s} ({info['confidence']})")
            else:
                print(f"  ❌ {cat:15s} Not detected")

        # Claude config
        print(f"\nClaude Code Configuration")
        print("-" * 50)
        print(f"  {'✅' if cc['claude_md'] else '❌'} CLAUDE.md")
        print(f"  {'✅' if cc['claude_dir'] else '❌'} .claude/ directory")
        print(f"  {'✅' if cc['settings_json'] else '❌'} .claude/settings.json")
        print(f"  {'✅' if cc['handoff_md'] else '❌'} .claude/handoff.md")
        print(f"  {'✅' if cc['mcp_json'] else '❌'} .mcp.json")
        print(f"  {'✅' if cc['claudeignore'] else '❌'} .claudeignore")

        if cc["agents"]:
            print(f"  ✅ Agents ({len(cc['agents'])}): {', '.join(cc['agents'])}")
        else:
            print(f"  ❌ No agents found")

        if cc["rules"]:
            print(f"  ✅ Rules ({len(cc['rules'])}): {', '.join(cc['rules'])}")
        else:
            print(f"  ❌ No rules found")

        if cc["commands"]:
            print(f"  ✅ Commands ({len(cc['commands'])}): {', '.join(cc['commands'])}")
        else:
            print(f"  ❌ No commands found")

        # Missing Claude features
        standard_agents = {"cto", "security", "work-breakdown", "testing", "devops", "push", "debugger", "reviewer"}
        existing_agents = set(cc["agents"])
        missing_agents = standard_agents - existing_agents
        if missing_agents:
            print(f"\n  Missing recommended agents: {', '.join(sorted(missing_agents))}")

        standard_commands = {"status", "handoff", "new-feature"}
        existing_commands = set(cc["commands"])
        missing_commands = standard_commands - existing_commands
        if missing_commands:
            print(f"  Missing recommended commands: {', '.join(sorted(missing_commands))}")

        print(f"\n{'='*60}\n")

    def to_json(self) -> str:
        """Return findings as JSON string."""
        return json.dumps(self.findings, indent=2)


def main():
    if len(sys.argv) < 2:
        print("Usage: python analyze_project.py <project-path> [--json]")
        sys.exit(1)

    project_path = sys.argv[1]
    json_output = "--json" in sys.argv

    analyzer = ProjectAnalyzer(project_path)

    if json_output:
        findings = analyzer.analyze()
        print(json.dumps(findings, indent=2))
    else:
        analyzer.print_report()


if __name__ == "__main__":
    main()
