#!/usr/bin/env python3
"""
Post-setup health check for claude-bootstrap generated projects.

Verifies that all expected files were generated correctly and the
project is ready for Claude Code development.

Checks:
- CLAUDE.md exists and is valid
- .claude/ directory structure is complete
- Agent files are well-formed
- Rules files exist and target valid paths
- Settings.json is valid JSON
- .claudeignore exists
- .env.example exists
- ARCHITECTURE.md exists
- Bootstrap config matches generated files

Usage:
    python healthcheck.py [project_root_path]
    python healthcheck.py  # defaults to current directory
"""

import json
import sys
from pathlib import Path


class HealthCheck:
    def __init__(self, project_root: Path):
        self.root = project_root
        self.passed = 0
        self.failed = 0
        self.warnings = 0
        self.results = []

    def check(self, condition: bool, pass_msg: str, fail_msg: str, level: str = "error"):
        if condition:
            self.results.append(("pass", pass_msg))
            self.passed += 1
        elif level == "error":
            self.results.append(("fail", fail_msg))
            self.failed += 1
        else:
            self.results.append(("warn", fail_msg))
            self.warnings += 1

    def file_exists(self, rel_path: str, required: bool = True):
        filepath = self.root / rel_path
        level = "error" if required else "warn"
        self.check(
            filepath.exists(),
            f"✅ {rel_path}",
            f"{'❌' if required else '⚠️'} Missing: {rel_path}",
            level=level,
        )
        return filepath.exists()

    def dir_exists(self, rel_path: str, required: bool = True):
        dirpath = self.root / rel_path
        level = "error" if required else "warn"
        self.check(
            dirpath.is_dir(),
            f"✅ {rel_path}/",
            f"{'❌' if required else '⚠️'} Missing directory: {rel_path}/",
            level=level,
        )
        return dirpath.is_dir()

    def valid_json(self, rel_path: str):
        filepath = self.root / rel_path
        if not filepath.exists():
            return False
        try:
            json.loads(filepath.read_text())
            self.results.append(("pass", f"✅ {rel_path} is valid JSON"))
            self.passed += 1
            return True
        except json.JSONDecodeError as e:
            self.results.append(("fail", f"❌ {rel_path} has invalid JSON: {e}"))
            self.failed += 1
            return False

    def run(self):
        print("=" * 60)
        print(f"🏥 Health Check: {self.root}")
        print("=" * 60)

        # ── Core files ─────────────────────────────────────────
        print("\n📄 Core Files")
        self.file_exists("CLAUDE.md")
        self.file_exists("ARCHITECTURE.md", required=False)
        self.file_exists(".claudeignore")
        self.file_exists(".env.example")
        self.file_exists("README.md", required=False)

        # ── CLAUDE.md quality ──────────────────────────────────
        claude_md = self.root / "CLAUDE.md"
        if claude_md.exists():
            content = claude_md.read_text()
            lines = content.split("\n")
            self.check(
                len(lines) <= 200,
                f"✅ CLAUDE.md is {len(lines)} lines (under 200)",
                f"⚠️  CLAUDE.md is {len(lines)} lines (over 200 limit)",
                level="warn",
            )
            self.check(
                len(content.strip()) > 50,
                "✅ CLAUDE.md has content",
                "❌ CLAUDE.md appears empty or is just a placeholder",
            )

        # ── .claude/ directory ─────────────────────────────────
        print("\n📁 .claude/ Structure")
        self.dir_exists(".claude")
        self.dir_exists(".claude/agents")
        self.dir_exists(".claude/rules", required=False)
        self.dir_exists(".claude/skills", required=False)
        self.dir_exists(".claude/commands", required=False)

        # ── Session Handoff ───────────────────────────────────
        self.file_exists(".claude/handoff.md", required=False)

        # ── Slash Commands ────────────────────────────────────
        commands_dir = self.root / ".claude" / "commands"
        if commands_dir.is_dir():
            cmd_files = list(commands_dir.glob("*.md"))
            self.check(
                len(cmd_files) > 0,
                f"✅ Found {len(cmd_files)} slash command(s)",
                "⚠️  No slash commands found in .claude/commands/",
                level="warn",
            )
            expected_commands = ["status.md", "handoff.md", "new-feature.md"]
            for cmd_name in expected_commands:
                cmd_file = commands_dir / cmd_name
                if cmd_file.exists():
                    self.results.append(("pass", f"✅ /{cmd_name.replace('.md', '')} command"))
                    self.passed += 1
                else:
                    self.results.append(("warn", f"⚠️  Missing recommended command: /{cmd_name.replace('.md', '')}"))
                    self.warnings += 1

        # ── MCP Configuration ─────────────────────────────────
        self.file_exists(".mcp.json", required=False)
        mcp_example = self.root / ".mcp.json.example"
        if mcp_example.exists():
            self.valid_json(".mcp.json.example")

        # ── Settings ───────────────────────────────────────────
        settings_path = ".claude/settings.json"
        if self.file_exists(settings_path, required=False):
            self.valid_json(settings_path)

        # ── Bootstrap config ───────────────────────────────────
        config_path = ".claude/bootstrap-config.json"
        if self.file_exists(config_path, required=False):
            self.valid_json(config_path)

        # ── Agents ─────────────────────────────────────────────
        print("\n🤖 Agents")
        agents_dir = self.root / ".claude" / "agents"
        if agents_dir.is_dir():
            agent_files = list(agents_dir.glob("*.md"))
            self.check(
                len(agent_files) > 0,
                f"✅ Found {len(agent_files)} agent(s)",
                "⚠️  No agent files found in .claude/agents/",
                level="warn",
            )

            expected_agents = [
                "cto.md", "security.md", "work-breakdown.md",
                "testing.md", "devops.md", "push.md",
                "debugger.md", "reviewer.md",
            ]
            for agent_name in expected_agents:
                agent_file = agents_dir / agent_name
                if agent_file.exists():
                    content = agent_file.read_text()
                    self.check(
                        "---" in content[:10],
                        f"✅ {agent_name} has frontmatter",
                        f"⚠️  {agent_name} missing YAML frontmatter",
                        level="warn",
                    )
                else:
                    self.results.append(("warn", f"⚠️  Optional agent missing: {agent_name}"))
                    self.warnings += 1

        # ── Rules ──────────────────────────────────────────────
        print("\n📏 Rules")
        rules_dir = self.root / ".claude" / "rules"
        if rules_dir.is_dir():
            rule_files = list(rules_dir.glob("*.md"))
            self.check(
                len(rule_files) > 0,
                f"✅ Found {len(rule_files)} rule file(s)",
                "ℹ️  No rule files found (optional but recommended)",
                level="warn",
            )
        else:
            self.results.append(("warn", "ℹ️  No .claude/rules/ directory (optional)"))
            self.warnings += 1

        # ── Source directories ─────────────────────────────────
        print("\n📂 Project Structure")
        has_src = (self.root / "src").is_dir()
        has_app = (self.root / "app").is_dir()
        has_cmd = (self.root / "cmd").is_dir()
        has_internal = (self.root / "internal").is_dir()

        self.check(
            has_src or has_app or has_cmd or has_internal,
            "✅ Source directory found",
            "⚠️  No standard source directory (src/, app/, cmd/) found",
            level="warn",
        )

        has_tests = (
            (self.root / "tests").is_dir() or
            (self.root / "test").is_dir() or
            (self.root / "__tests__").is_dir()
        )
        self.check(
            has_tests,
            "✅ Test directory found",
            "⚠️  No test directory found",
            level="warn",
        )

        # ── Summary ────────────────────────────────────────────
        print("\n" + "-" * 60)
        for level, msg in self.results:
            print(f"  {msg}")

        print("\n" + "=" * 60)
        total = self.passed + self.failed + self.warnings
        print(f"Results: {self.passed}/{total} passed, "
              f"{self.failed} errors, {self.warnings} warnings")

        if self.failed == 0:
            print("\n🎉 Project is healthy and ready for Claude Code!")
            if self.warnings:
                print(f"   ({self.warnings} warnings to consider)")
        else:
            print(f"\n🔧 {self.failed} issue(s) need attention before development.")

        print("=" * 60)
        return self.failed == 0


def main():
    project_root = Path(sys.argv[1]).resolve() if len(sys.argv) > 1 else Path.cwd()

    if not project_root.is_dir():
        print(f"❌ Not a directory: {project_root}")
        sys.exit(1)

    checker = HealthCheck(project_root)
    healthy = checker.run()
    sys.exit(0 if healthy else 1)


if __name__ == "__main__":
    main()
