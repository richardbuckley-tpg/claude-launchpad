#!/usr/bin/env python3
"""
Validates agent definition files in .claude/agents/.

Checks each agent file for:
- Valid YAML frontmatter (name, description, tools)
- Reasonable model selection
- Body content exists with instructions
- Tools list is valid
- No common mistakes (missing isolation for test agents, etc.)

Usage:
    python validate_agents.py [path/to/.claude/agents/]
    python validate_agents.py  # defaults to ./.claude/agents/
"""

import sys
import re
from pathlib import Path


VALID_TOOLS = {
    "Bash", "Read", "Write", "Edit", "Grep", "Glob",
    "WebFetch", "WebSearch", "Agent", "TodoWrite",
}

VALID_MODELS = {"opus", "sonnet", "haiku"}

VALID_ISOLATION = {"worktree", "none"}


def parse_frontmatter(content: str) -> tuple:
    """Extract YAML frontmatter and body from a markdown file."""
    match = re.match(r'^---\n(.*?)\n---\n?(.*)', content, re.DOTALL)
    if not match:
        return None, content
    return match.group(1), match.group(2)


def parse_yaml_simple(yaml_str: str) -> dict:
    """Simple YAML parser for frontmatter (no external dependencies)."""
    result = {}
    for line in yaml_str.strip().split("\n"):
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        if ":" in line:
            key, _, value = line.partition(":")
            key = key.strip()
            value = value.strip()
            # Handle list syntax: [item1, item2]
            if value.startswith("[") and value.endswith("]"):
                items = [i.strip().strip("'\"") for i in value[1:-1].split(",")]
                result[key] = [i for i in items if i]
            elif value.lower() in ("true", "false"):
                result[key] = value.lower() == "true"
            else:
                result[key] = value.strip("'\"")
    return result


def validate_agent(filepath: Path) -> list:
    """Validate a single agent file. Returns list of (level, message) tuples."""
    issues = []
    content = filepath.read_text(encoding="utf-8")

    # ── Has frontmatter ────────────────────────────────────────
    fm_str, body = parse_frontmatter(content)
    if fm_str is None:
        issues.append(("error", "No YAML frontmatter found (must start with ---)"))
        return issues

    fm = parse_yaml_simple(fm_str)

    # ── Required fields ────────────────────────────────────────
    if "name" not in fm:
        issues.append(("error", "Missing 'name' in frontmatter"))
    elif not re.match(r'^[a-z][a-z0-9_-]*$', fm["name"]):
        issues.append(("warn", f"Name '{fm['name']}' should be lowercase kebab-case (e.g., 'test-writer')"))

    if "description" not in fm:
        issues.append(("error", "Missing 'description' in frontmatter"))
    elif len(fm["description"]) < 20:
        issues.append(("warn", "Description is very short — add more detail for better auto-triggering"))

    if "tools" not in fm:
        issues.append(("warn", "No 'tools' field — agent will have default tool access"))
    elif isinstance(fm["tools"], list):
        unknown = set(fm["tools"]) - VALID_TOOLS
        if unknown:
            issues.append(("warn", f"Unknown tools: {unknown}. Valid: {VALID_TOOLS}"))

        # Check for sensible tool combos
        tools_set = set(fm["tools"])
        if "Write" in tools_set and "Read" not in tools_set:
            issues.append(("warn", "Has Write but not Read — agents that write should usually also read"))
        if "Edit" in tools_set and "Read" not in tools_set:
            issues.append(("warn", "Has Edit but not Read — agents that edit should read first"))

    # ── Model ──────────────────────────────────────────────────
    if "model" in fm:
        if fm["model"] not in VALID_MODELS:
            issues.append(("error", f"Invalid model '{fm['model']}'. Valid: {VALID_MODELS}"))
    else:
        issues.append(("info", "No model specified — will inherit from parent session"))

    # ── Isolation ──────────────────────────────────────────────
    if "isolation" in fm:
        if fm["isolation"] not in VALID_ISOLATION:
            issues.append(("warn", f"Unknown isolation mode '{fm['isolation']}'. Valid: {VALID_ISOLATION}"))

    # Test-related agents should probably use worktree isolation
    name = fm.get("name", "").lower()
    if any(word in name for word in ["test", "testing"]):
        if fm.get("isolation") != "worktree":
            issues.append(("warn",
                "Testing agents benefit from worktree isolation "
                "(separate context enforces genuine TDD). Consider adding 'isolation: worktree'"))

    # ── Body content ───────────────────────────────────────────
    body_stripped = body.strip()
    if not body_stripped:
        issues.append(("error", "No instructions in body — agent needs guidance below the frontmatter"))
    elif len(body_stripped) < 100:
        issues.append(("warn", "Body is very short (<100 chars). Agents need detailed instructions to be effective"))
    else:
        issues.append(("ok", f"Body has {len(body_stripped)} characters of instructions"))

    # ── Check for common patterns ──────────────────────────────
    if "## Rules" in body or "## rules" in body:
        issues.append(("ok", "Has explicit Rules section"))

    if "output" in body.lower() and ("format" in body.lower() or "template" in body.lower()):
        issues.append(("ok", "Has output format guidance"))

    if not issues or all(level == "ok" for level, _ in issues):
        issues.append(("ok", "Agent definition looks good"))

    return issues


def main():
    agents_dir = Path(sys.argv[1]) if len(sys.argv) > 1 else Path(".claude/agents")

    if not agents_dir.exists():
        print(f"❌ Directory not found: {agents_dir}")
        sys.exit(1)

    agent_files = sorted(agents_dir.glob("*.md"))
    if not agent_files:
        print(f"⚠️  No .md files found in {agents_dir}")
        sys.exit(0)

    print("=" * 60)
    print("Agent Validation Report")
    print("=" * 60)

    total_errors = 0
    total_warnings = 0

    for filepath in agent_files:
        print(f"\n📋 {filepath.name}")
        issues = validate_agent(filepath)

        for level, msg in issues:
            if level == "error":
                print(f"   ❌ {msg}")
                total_errors += 1
            elif level == "warn":
                print(f"   ⚠️  {msg}")
                total_warnings += 1
            elif level == "info":
                print(f"   ℹ️  {msg}")
            elif level == "ok":
                print(f"   ✅ {msg}")

    print("\n" + "=" * 60)
    print(f"Validated {len(agent_files)} agents: "
          f"{total_errors} errors, {total_warnings} warnings")
    if total_errors == 0:
        print("Result: ALL VALID ✅")
    else:
        print("Result: ISSUES FOUND ❌")
    print("=" * 60)

    sys.exit(1 if total_errors > 0 else 0)


if __name__ == "__main__":
    main()
