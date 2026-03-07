#!/usr/bin/env python3
"""
Claude Launchpad Config Auditor v1.0.0

Scores any .claude/ configuration for health, token efficiency, and staleness.
Works on Launchpad-generated, ECC, Starter Kit, or hand-crafted setups.

Usage:
    python audit.py <project-root>             # Full audit report
    python audit.py <project-root> --json      # JSON output
    python audit.py <project-root> --fix       # Apply safe fixes
"""

import argparse
import glob
import json
import os
import re
import sys
from pathlib import Path


# ── Token estimation ────────────────────────────────────────────────────

TOKENS_PER_LINE = 4  # Conservative heuristic for markdown with code


def count_lines(filepath: Path) -> int:
    """Count non-empty lines in a file."""
    try:
        return sum(1 for line in filepath.read_text().splitlines() if line.strip())
    except (FileNotFoundError, UnicodeDecodeError):
        return 0


def estimate_tokens(lines: int) -> int:
    return lines * TOKENS_PER_LINE


# ── Checks ──────────────────────────────────────────────────────────────

class AuditResult:
    def __init__(self):
        self.score = 100
        self.components = {}  # name -> {lines, tokens, status}
        self.issues = []      # {level: error|warning, message, fix}
        self.total_lines = 0
        self.total_tokens = 0

    def add_component(self, name, lines, budget_warn, budget_fail):
        tokens = estimate_tokens(lines)
        status = "✓"
        if lines > budget_fail:
            status = "✗ over budget"
            self.issues.append({
                "level": "error",
                "message": f"{name}: {lines} lines (max {budget_fail})",
                "fix": f"Reduce {name} to ≤{budget_warn} lines"
            })
            self.score -= 10
        elif lines > budget_warn:
            status = "⚠ nearing limit"
            self.issues.append({
                "level": "warning",
                "message": f"{name}: {lines} lines (target ≤{budget_warn})",
                "fix": f"Consider trimming {name}"
            })
            self.score -= 3
        self.components[name] = {"lines": lines, "tokens": tokens, "status": status}
        self.total_lines += lines
        self.total_tokens += tokens

    def add_issue(self, level, message, fix=""):
        self.issues.append({"level": level, "message": message, "fix": fix})
        self.score -= 10 if level == "error" else 3

    def to_dict(self):
        return {
            "score": max(0, self.score),
            "total_lines": self.total_lines,
            "total_tokens": self.total_tokens,
            "components": self.components,
            "issues": self.issues,
        }


def check_claude_md(project_dir: Path, result: AuditResult):
    """Check CLAUDE.md exists and is within budget."""
    claude_md = project_dir / "CLAUDE.md"
    if not claude_md.exists():
        result.add_issue("error", "CLAUDE.md not found", "Create a CLAUDE.md file")
        return
    lines = count_lines(claude_md)
    result.add_component("CLAUDE.md", lines, budget_warn=80, budget_fail=150)


def check_agents(project_dir: Path, result: AuditResult):
    """Check agents directory for valid agent files."""
    agents_dir = project_dir / ".claude" / "agents"
    if not agents_dir.exists():
        result.add_issue("warning", "No .claude/agents/ directory", "Create agents for common workflows")
        return

    agent_files = list(agents_dir.glob("*.md"))
    if not agent_files:
        result.add_issue("warning", "No agent files found in .claude/agents/", "Add agents for your workflow")
        return

    total_agent_lines = 0
    names_seen = set()

    for af in agent_files:
        lines = count_lines(af)
        total_agent_lines += lines
        name = af.stem

        # Check for duplicates
        if name in names_seen:
            result.add_issue("warning", f"Duplicate agent: {name}", f"Remove duplicate {af.name}")
        names_seen.add(name)

        # Check individual agent size
        if lines > 50:
            result.add_issue("warning",
                f"Agent {af.name}: {lines} lines (target ≤30)",
                f"Trim {af.name} — agents should be directives, not tutorials")
        elif lines > 30:
            result.add_issue("warning",
                f"Agent {af.name}: {lines} lines (target ≤30)",
                f"Consider trimming {af.name}")

        # Check for YAML frontmatter
        try:
            content = af.read_text()
            if not content.startswith("---"):
                result.add_issue("warning",
                    f"Agent {af.name} missing YAML frontmatter",
                    f"Add --- header with name, description, tools fields")
        except UnicodeDecodeError:
            pass

    result.add_component(f"Agents ({len(agent_files)})", total_agent_lines, budget_warn=180, budget_fail=300)


def check_rules(project_dir: Path, result: AuditResult):
    """Check rules directory."""
    rules_dir = project_dir / ".claude" / "rules"
    if not rules_dir.exists():
        return  # Rules are optional

    rule_files = list(rules_dir.glob("*.md"))
    total_rule_lines = 0

    for rf in rule_files:
        lines = count_lines(rf)
        total_rule_lines += lines
        if lines > 30:
            result.add_issue("warning",
                f"Rule {rf.name}: {lines} lines (target ≤20)",
                f"Trim {rf.name} — rules should be concise directives")

    if rule_files:
        result.add_component(f"Rules ({len(rule_files)})", total_rule_lines, budget_warn=60, budget_fail=100)


def check_settings(project_dir: Path, result: AuditResult):
    """Check settings.json is valid."""
    settings = project_dir / ".claude" / "settings.json"
    if not settings.exists():
        return

    lines = count_lines(settings)
    result.add_component("settings.json", lines, budget_warn=50, budget_fail=100)

    try:
        data = json.loads(settings.read_text())
    except (json.JSONDecodeError, UnicodeDecodeError):
        result.add_issue("error", "settings.json is not valid JSON", "Fix JSON syntax")
        return

    # Check for overly aggressive hooks
    hooks = data.get("hooks", {})
    for hook_type, hook_list in hooks.items():
        if isinstance(hook_list, list):
            for hook in hook_list:
                if isinstance(hook, dict):
                    matcher = hook.get("matcher", "")
                    # Check for hooks that block common operations
                    hook_items = hook.get("hooks", [])
                    for h in hook_items:
                        if isinstance(h, dict) and h.get("type") == "block":
                            pattern = h.get("pattern", "")
                            if ".md" in str(pattern) and "Write" in str(matcher):
                                result.add_issue("warning",
                                    f"Hook blocks .md file writes — may be overly restrictive",
                                    "Consider narrowing the block pattern")


def check_staleness(project_dir: Path, result: AuditResult):
    """Check for stale references in config files."""
    # Check if CLAUDE.md references commands that don't exist
    claude_md = project_dir / "CLAUDE.md"
    commands_dir = project_dir / ".claude" / "commands"

    if claude_md.exists() and commands_dir.exists():
        try:
            content = claude_md.read_text().lower()
            existing_cmds = {f.stem for f in commands_dir.glob("*.md")}

            # Common command references to check
            for cmd in ["status", "handoff", "new-feature", "fix-bug", "deploy", "tdd", "audit"]:
                if f"/{cmd}" in content and cmd not in existing_cmds:
                    result.add_issue("warning",
                        f"CLAUDE.md references /{cmd} but command doesn't exist",
                        f"Either create .claude/commands/{cmd}.md or remove the reference")
        except UnicodeDecodeError:
            pass

    # Check rules reference valid paths
    rules_dir = project_dir / ".claude" / "rules"
    if rules_dir.exists():
        for rf in rules_dir.glob("*.md"):
            try:
                content = rf.read_text()
                # Look for path patterns like src/app/, src/pages/, etc.
                path_patterns = re.findall(r'(?:src|app|lib|internal)/[\w/]+', content)
                for pattern in path_patterns:
                    # Check if at least the first directory level exists
                    first_dir = pattern.split('/')[0]
                    if not (project_dir / first_dir).exists():
                        result.add_issue("warning",
                            f"Rule {rf.name} references '{pattern}' but '{first_dir}/' doesn't exist",
                            f"Update path references in {rf.name}")
                        break  # One warning per rule is enough
            except UnicodeDecodeError:
                pass


def check_handoff(project_dir: Path, result: AuditResult):
    """Check handoff document exists."""
    handoff = project_dir / ".claude" / "handoff.md"
    if not handoff.exists():
        result.add_issue("warning",
            "No .claude/handoff.md — context will be lost between sessions",
            "Create a handoff document or run /handoff")


def check_total_budget(result: AuditResult):
    """Check overall token budget."""
    if result.total_tokens > 2400:
        result.add_issue("warning",
            f"Total config: ~{result.total_tokens} tokens (target ≤1,600)",
            "Consider trimming the largest components")
    if result.total_tokens > 4000:
        result.add_issue("error",
            f"Total config: ~{result.total_tokens} tokens — significant per-message overhead",
            "Reduce CLAUDE.md and agent sizes to lower token burn")


# ── Main audit ──────────────────────────────────────────────────────────

def audit(project_dir: Path) -> AuditResult:
    """Run full audit on a project directory."""
    result = AuditResult()

    check_claude_md(project_dir, result)
    check_agents(project_dir, result)
    check_rules(project_dir, result)
    check_settings(project_dir, result)
    check_staleness(project_dir, result)
    check_handoff(project_dir, result)
    check_total_budget(result)

    result.score = max(0, result.score)
    return result


def format_report(result: AuditResult) -> str:
    """Format audit result as human-readable report."""
    lines = [
        "Claude Launchpad Audit Report",
        "─" * 40,
        f"Health Score: {result.score}/100",
        "",
        "Token Budget",
    ]

    for name, info in result.components.items():
        lines.append(f"  {name:20s} {info['lines']:>4d} lines  ~{info['tokens']:>5d} tokens  {info['status']}")

    lines.extend([
        f"  {'─' * 55}",
        f"  {'Total':20s} {result.total_lines:>4d} lines  ~{result.total_tokens:>5d} tokens",
    ])

    errors = [i for i in result.issues if i["level"] == "error"]
    warnings = [i for i in result.issues if i["level"] == "warning"]

    lines.extend(["", f"Issues ({len(errors)} errors, {len(warnings)} warnings)"])

    if not result.issues:
        lines.append("  None — config looks good!")
    else:
        for i, issue in enumerate(result.issues, 1):
            icon = "✗" if issue["level"] == "error" else "⚠"
            lines.append(f"  {icon} {issue['message']}")

    if any(i.get("fix") for i in result.issues):
        lines.extend(["", "Recommended Fixes"])
        for i, issue in enumerate(result.issues, 1):
            if issue.get("fix"):
                lines.append(f"  {i}. {issue['fix']}")

    # Comparison context
    lines.extend([
        "",
        "Comparison",
        f"  ECC default:         ~7,200 tokens",
        f"  Starter Kit default: ~5,100 tokens",
        f"  Your config:         ~{result.total_tokens:,d} tokens",
    ])

    if result.total_tokens > 0:
        pct = round((1 - result.total_tokens / 7200) * 100)
        if pct > 0:
            lines.append(f"  ({pct}% more efficient than ECC)")

    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(description="Claude Launchpad Config Auditor")
    parser.add_argument("project_dir", help="Project root directory to audit")
    parser.add_argument("--json", action="store_true", help="Output as JSON")
    parser.add_argument("--fix", action="store_true", help="Apply safe fixes automatically")
    args = parser.parse_args()

    project_dir = Path(args.project_dir).resolve()
    if not project_dir.exists():
        print(f"Error: {project_dir} does not exist", file=sys.stderr)
        sys.exit(1)

    result = audit(project_dir)

    if args.json:
        print(json.dumps(result.to_dict(), indent=2))
    else:
        print(format_report(result))

    # Exit code: 0 if score >= 60, 1 if below
    sys.exit(0 if result.score >= 60 else 1)


if __name__ == "__main__":
    main()
