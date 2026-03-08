#!/usr/bin/env python3
"""
Claude Launchpad Learning System

Captures corrections and builds rules from developer feedback.
Two modes:
  1. Explicit: Record a correction directly
  2. Git analysis: Detect correction patterns from commit history

Usage:
    python learn.py <project-dir> --capture "Always use AppError for HTTP errors"
    python learn.py <project-dir> --from-git
    python learn.py <project-dir> --show
"""

import argparse
import json
import re
import subprocess
import sys
from datetime import datetime
from pathlib import Path

LEARNED_RULES_FILE = ".claude/rules/learned.md"
LEARN_LOG_FILE = ".claude/learn-log.json"


# ── Log Management ───────────────────────────────────────────────────────

def load_learn_log(project_dir: Path) -> list:
    """Load the learning log."""
    log_path = project_dir / LEARN_LOG_FILE
    if log_path.exists():
        try:
            return json.loads(log_path.read_text())
        except (json.JSONDecodeError, UnicodeDecodeError):
            return []
    return []


def save_learn_log(project_dir: Path, log: list):
    """Save the learning log."""
    log_path = project_dir / LEARN_LOG_FILE
    log_path.parent.mkdir(parents=True, exist_ok=True)
    log_path.write_text(json.dumps(log, indent=2) + "\n")


# ── Rule Generation ──────────────────────────────────────────────────────

def regenerate_learned_rules(project_dir: Path, log: list):
    """Regenerate the learned rules file from the log."""
    rules_path = project_dir / LEARNED_RULES_FILE
    rules_path.parent.mkdir(parents=True, exist_ok=True)

    corrections = []
    for entry in log:
        correction = entry.get("correction", "")
        if correction:
            corrections.append(correction)

    if not corrections:
        # Remove the rules file if no corrections remain
        if rules_path.exists():
            rules_path.unlink()
        return

    content = """---
globs: ["**/*"]
description: Learned rules from developer corrections (auto-maintained by /learn)
---

"""
    for correction in corrections:
        if not correction.startswith("- "):
            correction = f"- {correction}"
        content += correction + "\n"

    rules_path.write_text(content)


# ── Capture ──────────────────────────────────────────────────────────────

def capture_correction(project_dir: Path, correction: str, context: str = "") -> dict:
    """Record an explicit correction. Returns the entry."""
    entry = {
        "type": "explicit",
        "correction": correction,
        "context": context,
        "timestamp": datetime.now().isoformat(),
    }

    log = load_learn_log(project_dir)

    # Duplicate check
    for existing in log:
        if existing.get("correction", "").lower() == correction.lower():
            return existing

    log.append(entry)
    save_learn_log(project_dir, log)
    regenerate_learned_rules(project_dir, log)

    return entry


# ── Git Analysis ─────────────────────────────────────────────────────────

def run_git(project_dir: Path, *args) -> str:
    """Run a git command and return stdout."""
    try:
        result = subprocess.run(
            ["git", "-C", str(project_dir)] + list(args),
            capture_output=True, text=True, timeout=30
        )
        return result.stdout
    except (subprocess.TimeoutExpired, FileNotFoundError):
        return ""


def analyze_git_corrections(project_dir: Path, max_commits: int = 100) -> list:
    """Analyze git history for correction patterns.

    Looks for:
    - Files modified in consecutive commits (quick fix pattern)
    - Revert commits
    - Common replacement patterns in diffs
    """
    corrections = []

    # Get recent commit log with files
    log_output = run_git(project_dir, "log", f"--max-count={max_commits}",
                         "--format=%H|%s|%ai", "--name-only")
    if not log_output:
        return corrections

    # Parse commits
    commits = []
    current_commit = None
    for line in log_output.strip().split("\n"):
        if "|" in line and len(line.split("|")) >= 3:
            parts = line.split("|", 2)
            current_commit = {
                "hash": parts[0],
                "message": parts[1],
                "date": parts[2],
                "files": [],
            }
            commits.append(current_commit)
        elif line.strip() and current_commit:
            current_commit["files"].append(line.strip())

    if len(commits) < 2:
        return corrections

    # Pattern 1: Quick corrections — same file in consecutive commits
    correction_keywords = ["fix", "revert", "correct", "oops", "typo",
                           "actually", "should be", "wrong", "mistake",
                           "forgot", "missing", "broken"]

    for i in range(len(commits) - 1):
        current = commits[i]
        previous = commits[i + 1]

        common_files = set(current["files"]) & set(previous["files"])
        if common_files:
            msg = current["message"].lower()
            if any(kw in msg for kw in correction_keywords):
                corrections.append({
                    "type": "git-correction",
                    "message": current["message"],
                    "files": list(common_files),
                    "timestamp": current["date"],
                })

    # Pattern 2: Revert commits
    for commit in commits:
        if commit["message"].lower().startswith("revert"):
            corrections.append({
                "type": "git-revert",
                "message": commit["message"],
                "files": commit["files"],
                "timestamp": commit["date"],
            })

    # Pattern 3: Common replacement patterns in recent diffs
    recent_diff = run_git(project_dir, "log", "-10", "-p", "--diff-filter=M")
    replacement_patterns = [
        (r'^\-.*console\.log.*\n\+.*(?:logger|log)\.',
         "Use structured logging instead of console.log"),
        (r'^\-.*new Error\(.*\n\+.*new \w+Error\(',
         "Use project's custom error classes, not generic Error"),
        (r'^\-.*\bany\b.*\n\+.*(?:string|number|boolean|\w+\[\])',
         "Avoid 'any' type — use specific types"),
    ]

    existing_log = load_learn_log(project_dir)
    existing_corrections = {e.get("correction", "") for e in existing_log}

    for pattern, lesson in replacement_patterns:
        if re.search(pattern, recent_diff, re.MULTILINE):
            if lesson not in existing_corrections:
                corrections.append({
                    "type": "git-pattern",
                    "correction": lesson,
                    "timestamp": datetime.now().isoformat(),
                })

    return corrections


# ── Show / Forget ────────────────────────────────────────────────────────

def show_learned(project_dir: Path) -> str:
    """Return formatted display of all learned rules."""
    log = load_learn_log(project_dir)
    if not log:
        return "No learned rules yet. Use --capture or --from-git to add some."

    lines = [f"Learned Rules ({len(log)} entries)", "=" * 40]
    for entry in log:
        entry_type = entry.get("type", "unknown")
        correction = entry.get("correction", entry.get("message", ""))
        timestamp = entry.get("timestamp", "")[:10]
        lines.append(f"  [{entry_type}] {correction} ({timestamp})")

    return "\n".join(lines)


def forget(project_dir: Path, query: str) -> int:
    """Remove learned rules matching the query. Returns count removed."""
    log = load_learn_log(project_dir)
    original_len = len(log)

    log = [e for e in log
           if query.lower() not in e.get("correction", "").lower()
           and query.lower() not in e.get("message", "").lower()]

    removed = original_len - len(log)
    if removed > 0:
        save_learn_log(project_dir, log)
        regenerate_learned_rules(project_dir, log)

    return removed


# ── CLI ──────────────────────────────────────────────────────────────────

def main():
    p = argparse.ArgumentParser(description="Claude Launchpad Learning System")
    p.add_argument("project_dir", help="Path to the project root")
    p.add_argument("--capture", metavar="RULE", help="Record a correction/rule explicitly")
    p.add_argument("--context", default="", help="Additional context for --capture")
    p.add_argument("--from-git", action="store_true", dest="from_git",
                   help="Analyze git history for corrections")
    p.add_argument("--show", action="store_true", help="Show all learned rules")
    p.add_argument("--forget", metavar="QUERY", help="Remove learned rules matching query")
    p.add_argument("--json", action="store_true", help="JSON output")
    p.add_argument("--max-commits", type=int, default=100,
                   help="Max commits to analyze for --from-git")
    args = p.parse_args()

    project_dir = Path(args.project_dir).resolve()
    if not project_dir.exists():
        print(f"Error: {project_dir} does not exist", file=sys.stderr)
        sys.exit(1)

    if args.capture:
        entry = capture_correction(project_dir, args.capture, args.context)
        if args.json:
            print(json.dumps(entry, indent=2))
        else:
            print(f"Learned: {args.capture}")
            print(f"  Saved to {LEARNED_RULES_FILE}")

    elif args.from_git:
        corrections = analyze_git_corrections(project_dir, args.max_commits)
        if args.json:
            print(json.dumps(corrections, indent=2))
        elif corrections:
            print(f"Found {len(corrections)} correction patterns in git history:\n")
            for c in corrections:
                correction = c.get("correction", c.get("message", ""))
                print(f"  [{c['type']}] {correction}")
                if c.get("files"):
                    print(f"    Files: {', '.join(c['files'][:3])}")

            # Auto-capture git-pattern corrections
            captured = 0
            for c in corrections:
                if c["type"] == "git-pattern" and c.get("correction"):
                    capture_correction(project_dir, c["correction"])
                    captured += 1
            if captured:
                print(f"\nAuto-captured {captured} patterns as learned rules")
        else:
            print("No correction patterns found in recent git history.")

    elif args.show:
        if args.json:
            print(json.dumps(load_learn_log(project_dir), indent=2))
        else:
            print(show_learned(project_dir))

    elif args.forget:
        removed = forget(project_dir, args.forget)
        if removed > 0:
            print(f"Removed {removed} learned rule(s) matching '{args.forget}'")
        else:
            print(f"No rules found matching '{args.forget}'")

    else:
        p.print_help()

    sys.exit(0)


if __name__ == "__main__":
    main()
