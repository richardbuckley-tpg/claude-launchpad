#!/usr/bin/env python3
"""
Validates a CLAUDE.md file against best practices.

Checks:
- File exists and is readable
- Line count is under 200 (golden rule from Anthropic docs)
- Contains required sections (Tech Stack, Commands, Mistakes to Avoid)
- No overly long lines (readability)
- No common anti-patterns (file-by-file descriptions, standard conventions restated)
- Has project context in the first few lines

Usage:
    python validate_claude_md.py [path/to/CLAUDE.md]
    python validate_claude_md.py  # defaults to ./CLAUDE.md
"""

import sys
import re
from pathlib import Path


class ValidationResult:
    def __init__(self):
        self.errors = []      # Must fix
        self.warnings = []    # Should fix
        self.info = []        # Good to know
        self.passed = []      # Things that look good

    def error(self, msg):
        self.errors.append(msg)

    def warn(self, msg):
        self.warnings.append(msg)

    def add_info(self, msg):
        self.info.append(msg)

    def ok(self, msg):
        self.passed.append(msg)

    @property
    def is_valid(self):
        return len(self.errors) == 0

    def report(self):
        lines = []
        lines.append("=" * 60)
        lines.append("CLAUDE.md Validation Report")
        lines.append("=" * 60)

        if self.passed:
            lines.append(f"\n✅ PASSED ({len(self.passed)})")
            for msg in self.passed:
                lines.append(f"   ✓ {msg}")

        if self.info:
            lines.append(f"\nℹ️  INFO ({len(self.info)})")
            for msg in self.info:
                lines.append(f"   • {msg}")

        if self.warnings:
            lines.append(f"\n⚠️  WARNINGS ({len(self.warnings)})")
            for msg in self.warnings:
                lines.append(f"   ⚠ {msg}")

        if self.errors:
            lines.append(f"\n❌ ERRORS ({len(self.errors)})")
            for msg in self.errors:
                lines.append(f"   ✗ {msg}")

        lines.append("")
        if self.is_valid:
            lines.append("Result: VALID ✅")
            if self.warnings:
                lines.append(f"  ({len(self.warnings)} warnings to consider)")
        else:
            lines.append(f"Result: INVALID ❌ ({len(self.errors)} errors to fix)")

        lines.append("=" * 60)
        return "\n".join(lines)


def validate(filepath: Path) -> ValidationResult:
    result = ValidationResult()

    # ── File exists ────────────────────────────────────────────
    if not filepath.exists():
        result.error(f"File not found: {filepath}")
        return result

    content = filepath.read_text(encoding="utf-8")
    lines = content.split("\n")
    line_count = len(lines)

    # ── Line count ─────────────────────────────────────────────
    if line_count <= 100:
        result.ok(f"Line count: {line_count} (well under 200 limit)")
    elif line_count <= 150:
        result.ok(f"Line count: {line_count} (within recommended range)")
    elif line_count <= 200:
        result.warn(f"Line count: {line_count} (approaching 200 limit — consider pruning)")
    else:
        result.error(
            f"Line count: {line_count} (exceeds 200 limit). "
            "Quality of instruction-following degrades significantly above 200 lines. "
            "Move detailed rules to .claude/rules/ and detailed docs to separate files."
        )

    # ── Has project context ────────────────────────────────────
    first_10 = "\n".join(lines[:10]).lower()
    if any(word in first_10 for word in ["project", "app", "application", "platform", "system", "service"]):
        result.ok("Project context found in opening lines")
    else:
        result.warn(
            "No clear project context in the first 10 lines. "
            "Start with a 1-2 sentence description: 'This is a [type] app that [does what].'"
        )

    # ── Required sections ──────────────────────────────────────
    content_lower = content.lower()
    headings = re.findall(r'^#+\s+(.+)$', content, re.MULTILINE)
    headings_lower = [h.lower() for h in headings]
    all_headings_text = " ".join(headings_lower)

    required_sections = {
        "tech stack": ["tech stack", "stack", "technology", "framework"],
        "commands": ["command", "script", "how to run", "build", "test command"],
        "mistakes to avoid": ["mistake", "avoid", "never", "don't", "pitfall", "anti-pattern"],
    }

    for section_name, keywords in required_sections.items():
        if any(kw in all_headings_text for kw in keywords):
            result.ok(f"Has '{section_name}' section")
        elif any(kw in content_lower for kw in keywords):
            result.add_info(f"'{section_name}' content exists but not as a clear heading")
        else:
            result.warn(f"Missing '{section_name}' section — this is high-value content for Claude")

    # ── Recommended sections ───────────────────────────────────
    recommended = {
        "architecture": ["architecture", "how components connect", "structure"],
        "code conventions": ["convention", "code style", "pattern"],
    }

    for section_name, keywords in recommended.items():
        if any(kw in all_headings_text for kw in keywords):
            result.ok(f"Has '{section_name}' section")

    # ── Long lines ─────────────────────────────────────────────
    long_lines = [(i + 1, len(line)) for i, line in enumerate(lines) if len(line) > 200]
    if long_lines:
        result.warn(
            f"{len(long_lines)} lines exceed 200 characters. "
            f"Longest: line {long_lines[0][0]} ({long_lines[0][1]} chars). "
            "Long lines reduce readability."
        )
    else:
        result.ok("No overly long lines")

    # ── Anti-patterns ──────────────────────────────────────────
    # File-by-file descriptions
    file_desc_pattern = r'[-•]\s*`[^`]+\.(ts|js|py|go|rs)`\s*[-—:]\s*.{10,}'
    file_descriptions = re.findall(file_desc_pattern, content)
    if len(file_descriptions) > 5:
        result.warn(
            f"Found {len(file_descriptions)} file-by-file descriptions. "
            "Claude can figure these out by reading the code. "
            "Only document files where the purpose is non-obvious."
        )

    # Restating standard conventions
    standard_restates = [
        (r'use camelCase', "camelCase is standard JS/TS — Claude knows this"),
        (r'use PascalCase for components', "PascalCase for components is standard React"),
        (r'indent with \d+ spaces', "Indentation should be enforced by linters, not CLAUDE.md"),
        (r'use strict mode', "Strict mode is standard — no need to state"),
        (r'always use const', "const vs let preference is standard — linter enforces this"),
    ]

    for pattern, reason in standard_restates:
        if re.search(pattern, content, re.IGNORECASE):
            result.warn(f"Restating standard convention: {reason}")

    # ── Emphasis markers ───────────────────────────────────────
    emphasis_count = len(re.findall(r'\b(NEVER|ALWAYS|CRITICAL|IMPORTANT|MUST)\b', content))
    if emphasis_count == 0:
        result.add_info(
            "No emphasis markers (NEVER, ALWAYS, CRITICAL) found. "
            "Consider adding these for non-negotiable rules."
        )
    elif emphasis_count > 15:
        result.warn(
            f"{emphasis_count} emphasis markers found. "
            "When everything is CRITICAL, nothing is. Use sparingly for maximum effect."
        )
    else:
        result.ok(f"{emphasis_count} emphasis markers — good usage level")

    # ── Empty sections ─────────────────────────────────────────
    empty_sections = []
    for i, line in enumerate(lines):
        if re.match(r'^#+\s', line):
            # Look at next non-empty line
            next_content = ""
            for j in range(i + 1, min(i + 5, len(lines))):
                if lines[j].strip():
                    next_content = lines[j].strip()
                    break
            if next_content.startswith("#") or not next_content:
                empty_sections.append(line.strip())

    if empty_sections:
        result.warn(f"Empty sections found: {', '.join(empty_sections[:3])}")

    return result


def main():
    filepath = Path(sys.argv[1]) if len(sys.argv) > 1 else Path("CLAUDE.md")
    result = validate(filepath)
    print(result.report())
    sys.exit(0 if result.is_valid else 1)


if __name__ == "__main__":
    main()
