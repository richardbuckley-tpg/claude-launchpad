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
import json
import os
import re
import sys
from pathlib import Path


# ── Token estimation ────────────────────────────────────────────────────

TOKENS_PER_LINE = 4  # Conservative heuristic for markdown with code

# Comparison baselines (estimated from default configs as of 2025)
BASELINE_ECC_TOKENS = 7200
BASELINE_STARTER_KIT_TOKENS = 5100


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
    """Tracks audit score across four weighted categories (100 points total).

    Categories (from audit-rules.md):
      - structure:  30 points — CLAUDE.md exists/sized, agents have frontmatter, valid settings
      - efficiency: 30 points — token budgets for each component and total
      - freshness:  20 points — stale paths, stale command references
      - practices:  20 points — no duplicates, hooks not aggressive, handoff exists
    """

    CATEGORY_BUDGETS = {"structure": 30, "efficiency": 30, "freshness": 20, "practices": 20}

    def __init__(self):
        self.score = 100
        self.components = {}  # name -> {lines, tokens, status}
        self.issues = []      # {level: error|warning, message, fix, category}
        self.total_lines = 0
        self.total_tokens = 0
        self._deductions = {"structure": 0, "efficiency": 0, "freshness": 0, "practices": 0}

    def _deduct(self, category: str, points: int):
        """Deduct points from a category, capped at the category's budget."""
        budget = self.CATEGORY_BUDGETS.get(category, 10)
        self._deductions[category] = min(self._deductions[category] + points, budget)
        self.score = 100 - sum(self._deductions.values())

    def add_component(self, name, lines, budget_warn, budget_fail):
        tokens = estimate_tokens(lines)
        status = "✓"
        if lines > budget_fail:
            status = "✗ over budget"
            self.issues.append({
                "level": "error",
                "message": f"{name}: {lines} lines (max {budget_fail})",
                "fix": f"Reduce {name} to ≤{budget_warn} lines",
                "category": "efficiency",
            })
            self._deduct("efficiency", 10)
        elif lines > budget_warn:
            status = "⚠ nearing limit"
            self.issues.append({
                "level": "warning",
                "message": f"{name}: {lines} lines (target ≤{budget_warn})",
                "fix": f"Consider trimming {name}",
                "category": "efficiency",
            })
            self._deduct("efficiency", 3)
        self.components[name] = {"lines": lines, "tokens": tokens, "status": status}
        self.total_lines += lines
        self.total_tokens += tokens

    def add_issue(self, level, message, fix="", category="practices"):
        self.issues.append({"level": level, "message": message, "fix": fix, "category": category})
        self._deduct(category, 10 if level == "error" else 3)

    def to_dict(self):
        return {
            "score": max(0, self.score),
            "total_lines": self.total_lines,
            "total_tokens": self.total_tokens,
            "components": self.components,
            "issues": self.issues,
            "categories": {k: self.CATEGORY_BUDGETS[k] - v for k, v in self._deductions.items()},
        }


def check_claude_md(project_dir: Path, result: AuditResult):
    """Check CLAUDE.md exists and is within budget."""
    claude_md = project_dir / "CLAUDE.md"
    if not claude_md.exists():
        result.add_issue("error", "CLAUDE.md not found", "Create a CLAUDE.md file", category="structure")
        return
    lines = count_lines(claude_md)
    result.add_component("CLAUDE.md", lines, budget_warn=80, budget_fail=150)


def check_agents(project_dir: Path, result: AuditResult):
    """Check agents directory for valid agent files."""
    agents_dir = project_dir / ".claude" / "agents"
    if not agents_dir.exists():
        result.add_issue("warning", "No .claude/agents/ directory", "Create agents for common workflows", category="structure")
        return

    agent_files = list(agents_dir.glob("*.md"))
    if not agent_files:
        result.add_issue("warning", "No agent files found in .claude/agents/", "Add agents for your workflow", category="structure")
        return

    total_agent_lines = 0
    names_seen = set()

    for af in agent_files:
        lines = count_lines(af)
        total_agent_lines += lines
        name = af.stem

        # Check for duplicate agent names in frontmatter
        try:
            agent_content = af.read_text()
            fm_name_match = re.search(r'^name:\s*(.+)$', agent_content, re.MULTILINE)
            fm_name = fm_name_match.group(1).strip() if fm_name_match else name
            if fm_name in names_seen:
                result.add_issue("warning", f"Duplicate agent name '{fm_name}' in {af.name}", f"Remove or rename duplicate agent", category="practices")
            names_seen.add(fm_name)
        except UnicodeDecodeError:
            names_seen.add(name)

        # Check individual agent size
        if lines > 50:
            result.add_issue("warning",
                f"Agent {af.name}: {lines} lines (target ≤30)",
                f"Trim {af.name} — agents should be directives, not tutorials",
                category="efficiency")
        elif lines > 30:
            result.add_issue("warning",
                f"Agent {af.name}: {lines} lines (target ≤30)",
                f"Consider trimming {af.name}",
                category="efficiency")

        # Check for YAML frontmatter
        try:
            content = af.read_text()
            if not content.startswith("---"):
                result.add_issue("warning",
                    f"Agent {af.name} missing YAML frontmatter",
                    f"Add --- header with name, description, tools fields",
                    category="structure")
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
                f"Trim {rf.name} — rules should be concise directives",
                category="efficiency")

    if rule_files:
        result.add_component(f"Rules ({len(rule_files)})", total_rule_lines, budget_warn=60, budget_fail=100)


def check_settings(project_dir: Path, result: AuditResult):
    """Check settings.json is valid."""
    settings = project_dir / ".claude" / "settings.json"
    if not settings.exists():
        return

    lines = count_lines(settings)
    result.add_component("settings.json", lines, budget_warn=80, budget_fail=150)

    try:
        data = json.loads(settings.read_text())
    except (json.JSONDecodeError, UnicodeDecodeError):
        result.add_issue("error", "settings.json is not valid JSON", "Fix JSON syntax", category="structure")
        return

    # Check for overly aggressive hooks
    hooks = data.get("hooks", {})
    for hook_type, hook_list in hooks.items():
        if isinstance(hook_list, list):
            for hook in hook_list:
                if isinstance(hook, dict):
                    matcher = hook.get("matcher", "")
                    hook_items = hook.get("hooks", [])
                    for h in hook_items:
                        if isinstance(h, dict) and h.get("type") == "block":
                            pattern = h.get("pattern", "")
                            if ".md" in str(pattern) and "Write" in str(matcher):
                                result.add_issue("warning",
                                    f"Hook blocks .md file writes — may be overly restrictive",
                                    "Consider narrowing the block pattern",
                                    category="practices")


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
                        f"Either create .claude/commands/{cmd}.md or remove the reference",
                        category="freshness")
        except UnicodeDecodeError:
            pass

    # Check rules reference valid paths (deep validation)
    rules_dir = project_dir / ".claude" / "rules"
    if rules_dir.exists():
        for rf in rules_dir.glob("*.md"):
            try:
                content = rf.read_text()
                # Look for path patterns like src/app/, src/pages/, etc.
                path_patterns = re.findall(r'(?:src|app|lib|internal|packages|services|tools|components|pages|api|cmd|pkg)/[\w/]+', content)
                warned = False
                for pattern in path_patterns:
                    if warned:
                        break
                    # Validate path segments progressively deeper
                    parts = pattern.split('/')
                    check_path = project_dir
                    for i, part in enumerate(parts):
                        check_path = check_path / part
                        if not check_path.exists():
                            stale_segment = '/'.join(parts[:i+1])
                            result.add_issue("warning",
                                f"Rule {rf.name} references '{pattern}' but '{stale_segment}/' doesn't exist",
                                f"Update path references in {rf.name}",
                                category="freshness")
                            warned = True
                            break
            except UnicodeDecodeError:
                pass


def check_mcp_servers(project_dir: Path, result: AuditResult):
    """Check MCP server configuration for issues."""
    settings = project_dir / ".claude" / "settings.json"
    if not settings.exists():
        return

    try:
        data = json.loads(settings.read_text())
    except (json.JSONDecodeError, UnicodeDecodeError):
        return  # Already caught by check_settings

    mcp = data.get("mcpServers", {})
    if not mcp:
        # Not an error — many projects don't need MCP
        return

    server_count = len(mcp)

    # Warn if too many MCP servers (startup latency)
    if server_count > 5:
        result.add_issue("warning",
            f"{server_count} MCP servers configured — may slow startup",
            "Remove unused MCP servers. Aim for 1-3",
            category="practices")

    for name, config in mcp.items():
        if not isinstance(config, dict):
            result.add_issue("error",
                f"MCP server '{name}' has invalid config (expected object)",
                f"Fix mcpServers.{name} in settings.json",
                category="structure")
            continue

        # Check required fields
        if "command" not in config:
            result.add_issue("error",
                f"MCP server '{name}' missing 'command' field",
                f"Add 'command' to mcpServers.{name}",
                category="structure")

        # Check for hardcoded secrets — pattern + heuristic based
        SECRET_PATTERNS = [
            r'^sk-[a-zA-Z0-9]{20,}',      # Anthropic/OpenAI keys
            r'^ghp_[a-zA-Z0-9]{36}',       # GitHub PAT
            r'^gho_[a-zA-Z0-9]{36}',       # GitHub OAuth
            r'^glpat-[a-zA-Z0-9\-]{20,}',  # GitLab PAT
            r'^AKIA[0-9A-Z]{16}',          # AWS access key
            r'^eyJ[a-zA-Z0-9]{20,}',       # JWT token
            r'^[a-f0-9]{32,}$',            # Hex strings (generic secrets)
        ]
        env = config.get("env", {})
        for env_key, env_val in env.items():
            if not isinstance(env_val, str) or env_val.startswith("${"):
                continue
            is_secret_key = any(word in env_key.upper() for word in ["TOKEN", "SECRET", "KEY", "PASSWORD", "CREDENTIAL"])
            is_secret_pattern = any(re.match(p, env_val) for p in SECRET_PATTERNS)
            if is_secret_key and (len(env_val) > 20 or is_secret_pattern):
                result.add_issue("error",
                    f"MCP server '{name}' has hardcoded secret in {env_key}",
                    f"Use ${{ENV_VAR}} syntax: \"{env_key}\": \"${{{env_key}}}\"",
                    category="practices")
            elif is_secret_pattern:
                result.add_issue("warning",
                    f"MCP server '{name}': {env_key} value looks like a secret",
                    f"Use ${{ENV_VAR}} syntax instead of hardcoding",
                    category="practices")

    result.add_component(f"MCP Servers ({server_count})", server_count * 3, budget_warn=15, budget_fail=30)


def check_discoverability(project_dir: Path, result: AuditResult):
    """Check CLAUDE.md for auto-discoverable content that wastes tokens."""
    claude_md = project_dir / "CLAUDE.md"
    if not claude_md.exists():
        return

    try:
        content = claude_md.read_text().lower()
    except UnicodeDecodeError:
        return

    # Patterns that indicate auto-discoverable content
    discoverable_patterns = [
        (r'(?:directory|folder)\s+structure', "directory structure listing (Claude reads the filesystem)"),
        (r'(?:project|file)\s+(?:layout|tree|structure)\s*[:\n]', "file tree (Claude reads the filesystem)"),
        (r'```\n(?:├|└|│)', "ASCII tree diagram (Claude reads the filesystem)"),
        (r'import\s+(?:from|{)', "import patterns (visible in source files)"),
    ]

    for pattern, reason in discoverable_patterns:
        if re.search(pattern, content):
            result.add_issue("warning",
                f"CLAUDE.md contains {reason}",
                "Remove auto-discoverable content — it wastes tokens and can reduce task success",
                category="efficiency")
            break  # One warning is enough


def check_context_percentage(project_dir: Path, result: AuditResult):
    """Check if total config + MCP context exceeds recommended percentage of 200k window."""
    settings = project_dir / ".claude" / "settings.json"
    mcp_count = 0
    if settings.exists():
        try:
            data = json.loads(settings.read_text())
            mcp_count = len(data.get("mcpServers", {}))
        except (json.JSONDecodeError, UnicodeDecodeError):
            pass

    mcp_tokens = mcp_count * 3000
    config_tokens = result.total_tokens
    total = config_tokens + mcp_tokens
    pct = round(total / 200000 * 100, 1)

    if pct > 10:
        result.add_issue("error",
            f"Config + MCP uses ~{pct}% of 200k context ({total:,d} tokens)",
            "Reduce MCP servers or trim config files — aim for <5%",
            category="efficiency")
    elif pct > 5:
        result.add_issue("warning",
            f"Config + MCP uses ~{pct}% of 200k context ({total:,d} tokens)",
            "Consider trimming — aim for <5% of context window",
            category="efficiency")


def check_handoff(project_dir: Path, result: AuditResult):
    """Check handoff document exists."""
    handoff = project_dir / ".claude" / "handoff.md"
    if not handoff.exists():
        result.add_issue("warning",
            "No .claude/handoff.md — context will be lost between sessions",
            "Create a handoff document or run /handoff",
            category="practices")


def check_total_budget(result: AuditResult):
    """Check overall token budget."""
    if result.total_tokens > 2400:
        result.add_issue("warning",
            f"Total config: ~{result.total_tokens} tokens (target ≤1,600)",
            "Consider trimming the largest components",
            category="efficiency")
    if result.total_tokens > 4000:
        result.add_issue("error",
            f"Total config: ~{result.total_tokens} tokens — significant per-message overhead",
            "Reduce CLAUDE.md and agent sizes to lower token burn",
            category="efficiency")


# ── Main audit ──────────────────────────────────────────────────────────

def audit(project_dir: Path) -> AuditResult:
    """Run full audit on a project directory."""
    result = AuditResult()

    check_claude_md(project_dir, result)
    check_agents(project_dir, result)
    check_rules(project_dir, result)
    check_settings(project_dir, result)
    check_staleness(project_dir, result)
    check_mcp_servers(project_dir, result)
    check_skills_content(project_dir, result)
    check_commands_content(project_dir, result)
    check_discoverability(project_dir, result)
    check_handoff(project_dir, result)
    check_total_budget(result)
    check_context_percentage(project_dir, result)

    result.score = max(0, result.score)
    return result


def format_report(result: AuditResult) -> str:
    """Format audit result as human-readable report."""
    cats = result.to_dict().get("categories", {})
    lines = [
        "Claude Launchpad Audit Report",
        "─" * 40,
        f"Health Score: {max(0, result.score)}/100",
        f"  Structure: {cats.get('structure', 30)}/30  Efficiency: {cats.get('efficiency', 30)}/30  Freshness: {cats.get('freshness', 20)}/20  Practices: {cats.get('practices', 20)}/20",
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
        f"  ECC default:         ~{BASELINE_ECC_TOKENS:,d} tokens",
        f"  Starter Kit default: ~{BASELINE_STARTER_KIT_TOKENS:,d} tokens",
        f"  Your config:         ~{result.total_tokens:,d} tokens",
    ])

    if result.total_tokens > 0:
        pct = round((1 - result.total_tokens / BASELINE_ECC_TOKENS) * 100)
        if pct > 0:
            lines.append(f"  ({pct}% more efficient than ECC)")

    return "\n".join(lines)


def check_skills_content(project_dir: Path, result: AuditResult):
    """Check skills directory for content quality issues."""
    skills_dir = project_dir / ".claude" / "skills"
    if not skills_dir.exists():
        return

    skill_files = list(skills_dir.glob("*.md"))
    if not skill_files:
        return

    total_skill_lines = 0
    for sf in skill_files:
        lines = count_lines(sf)
        total_skill_lines += lines
        if lines > 50:
            result.add_issue("warning",
                f"Skill {sf.name}: {lines} lines (target ≤40)",
                f"Trim {sf.name} — skills should be concise directives",
                category="efficiency")

        # Check for YAML frontmatter with description
        try:
            content = sf.read_text()
            if not content.startswith("---"):
                result.add_issue("warning",
                    f"Skill {sf.name} missing YAML frontmatter",
                    f"Add --- header with description field",
                    category="structure")
            elif content.count("---") >= 2 and "description:" not in content.split("---")[1]:
                result.add_issue("warning",
                    f"Skill {sf.name} missing description in frontmatter",
                    f"Add description: field to frontmatter",
                    category="structure")
        except (UnicodeDecodeError, IndexError):
            pass


def check_commands_content(project_dir: Path, result: AuditResult):
    """Check commands directory for content quality issues."""
    commands_dir = project_dir / ".claude" / "commands"
    if not commands_dir.exists():
        return

    cmd_files = list(commands_dir.glob("*.md"))
    for cf in cmd_files:
        try:
            content = cf.read_text()
            if not content.startswith("---"):
                result.add_issue("warning",
                    f"Command {cf.name} missing YAML frontmatter",
                    f"Add --- header with description field",
                    category="structure")
            elif content.count("---") >= 2 and "description:" not in content.split("---")[1]:
                result.add_issue("warning",
                    f"Command {cf.name} missing description in frontmatter",
                    f"Add description: field to frontmatter",
                    category="structure")
        except (UnicodeDecodeError, IndexError):
            pass


# ── Auto-fix ───────────────────────────────────────────────────────────

def apply_fixes(project_dir: Path, result: AuditResult) -> list[str]:
    """Apply safe, non-destructive fixes. Returns list of actions taken."""
    actions = []

    # Fix 1: Create missing handoff.md
    handoff = project_dir / ".claude" / "handoff.md"
    if not handoff.exists() and (project_dir / ".claude").exists():
        handoff.write_text("# Session Handoff\n\n## What's Working\n- (not yet populated)\n\n## In Progress\n- (nothing yet)\n\n## Known Issues\n- (none)\n\n## Next Steps\n1. Run /status\n")
        actions.append("Created .claude/handoff.md")

    # Fix 2: Add missing YAML frontmatter to agents
    agents_dir = project_dir / ".claude" / "agents"
    if agents_dir.exists():
        for af in agents_dir.glob("*.md"):
            try:
                content = af.read_text()
                if not content.startswith("---"):
                    name = af.stem
                    new_content = f"---\nname: {name}\ndescription: {name} agent\n---\n{content}"
                    af.write_text(new_content)
                    actions.append(f"Added frontmatter to agent {af.name}")
            except UnicodeDecodeError:
                pass

    # Fix 3: Add missing YAML frontmatter to skills
    skills_dir = project_dir / ".claude" / "skills"
    if skills_dir.exists():
        for sf in skills_dir.glob("*.md"):
            try:
                content = sf.read_text()
                if not content.startswith("---"):
                    name = sf.stem.replace("-", " ").title()
                    new_content = f"---\ndescription: {name}\n---\n{content}"
                    sf.write_text(new_content)
                    actions.append(f"Added frontmatter to skill {sf.name}")
            except UnicodeDecodeError:
                pass

    # Fix 4: Add missing YAML frontmatter to commands
    commands_dir = project_dir / ".claude" / "commands"
    if commands_dir.exists():
        for cf in commands_dir.glob("*.md"):
            try:
                content = cf.read_text()
                if not content.startswith("---"):
                    name = cf.stem.replace("-", " ").title()
                    new_content = f"---\ndescription: {name}\n---\n{content}"
                    cf.write_text(new_content)
                    actions.append(f"Added frontmatter to command {cf.name}")
            except UnicodeDecodeError:
                pass

    # Fix 5: Fix invalid settings.json
    settings = project_dir / ".claude" / "settings.json"
    if settings.exists():
        try:
            json.loads(settings.read_text())
        except json.JSONDecodeError:
            # Back up and create empty valid JSON
            backup = settings.with_suffix(".json.bak")
            settings.rename(backup)
            settings.write_text("{}\n")
            actions.append(f"Fixed invalid settings.json (backup: {backup.name})")

    return actions


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

    if args.fix:
        # Run audit first to identify issues
        result = audit(project_dir)
        print(format_report(result))
        print()

        # Apply fixes
        actions = apply_fixes(project_dir, result)
        if actions:
            print(f"Applied {len(actions)} fixes:")
            for a in actions:
                print(f"  ✓ {a}")
            # Re-audit to show improvement
            result2 = audit(project_dir)
            print(f"\nScore: {result.score}/100 → {result2.score}/100")
        else:
            print("No auto-fixable issues found.")

        sys.exit(0 if result.score >= 60 else 1)

    result = audit(project_dir)

    if args.json:
        print(json.dumps(result.to_dict(), indent=2))
    else:
        print(format_report(result))

    # Exit code: 0 if score >= 60, 1 if below
    sys.exit(0 if result.score >= 60 else 1)


if __name__ == "__main__":
    main()
