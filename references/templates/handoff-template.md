# Session Handoff Template

Generate a `.claude/handoff.md` file and a `/handoff` command for context preservation between
Claude Code sessions. This is critical for long-running projects where work spans multiple sessions.

## .claude/handoff.md

This file is the "session state" document. It should be updated at the end of every session
and read at the start of every new session.

### Template

```markdown
# Session Handoff — {project_name}

Last updated: {timestamp}
Last session focus: {brief description}

## Current State

### What's Working
- {list of completed features/systems that are stable}

### What's In Progress
- {feature/task}: {current status, what's done, what's remaining}
- {feature/task}: {current status, blockers if any}

### What's Blocked
- {issue}: {why it's blocked, what's needed to unblock}

## Architecture Decisions Made This Session
- {decision}: {rationale} (date)

## Key Files Changed
- `{filepath}` — {what changed and why}
- `{filepath}` — {what changed and why}

## Known Issues
- {issue description} — {severity: low/medium/high}

## Next Steps (Priority Order)
1. {next task with enough context to pick up cold}
2. {next task}
3. {next task}

## Environment Notes
- {any env-specific things to remember: versions, configs, running services}
```

## /handoff Slash Command

Generate `.claude/commands/handoff.md`:

```markdown
---
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
```

## Auto-Handoff Hook (Optional)

If the user wants automatic handoff updates, generate a hook in `.claude/settings.json`:

```json
{
  "hooks": {
    "PostToolUse": [
      {
        "matcher": "Bash",
        "hooks": [
          {
            "type": "command",
            "command": "# Auto-handoff is manual — use /handoff before ending your session"
          }
        ]
      }
    ]
  }
}
```

Note: True auto-handoff on session end isn't possible via hooks. Instead, instruct the user
to run `/handoff` before ending each session, or configure the push agent to include handoff
updates as part of the commit workflow.

## Generation Rules

1. Always generate `.claude/handoff.md` with the template pre-filled with project context from the interview
2. Always generate `.claude/commands/handoff.md` slash command
3. Pre-populate "What's Working" with "Project scaffolded with claude-bootstrap"
4. Pre-populate "Next Steps" with the first 3 logical steps for the project
5. Add a note in CLAUDE.md: "Run `/handoff` at the end of each session to preserve context"
