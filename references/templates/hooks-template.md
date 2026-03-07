# Hooks Generation Template

Generate hooks in `.claude/settings.json` based on the project's needs.
Hooks provide deterministic guarantees — use them for actions that must happen every time.

## settings.json Structure

```json
{
  "hooks": {
    "PreToolUse": [],
    "PostToolUse": [],
    "Stop": []
  },
  "permissions": {
    "deny": [],
    "allowlist": []
  }
}
```

## Core Safety Hooks (Always Generate)

### Block dangerous commands

```json
{
  "PreToolUse": [
    {
      "matcher": "Bash",
      "hooks": [
        {
          "type": "command",
          "command": "if echo \"$CLAUDE_TOOL_INPUT\" | grep -qE 'git push.*--force|git reset --hard|rm -rf /|DROP TABLE|DROP DATABASE'; then echo 'BLOCKED: Dangerous command detected. Use a safer alternative.' >&2; exit 1; fi"
        }
      ]
    }
  ]
}
```

### Block production database access (if staging/prod environments)

```json
{
  "PreToolUse": [
    {
      "matcher": "Bash",
      "hooks": [
        {
          "type": "command",
          "command": "if echo \"$CLAUDE_TOOL_INPUT\" | grep -qiE 'DATABASE_URL.*production|PROD_DB|production\\.database'; then echo 'BLOCKED: Production database access is not allowed from development.' >&2; exit 1; fi"
        }
      ]
    }
  ]
}
```

### Block secrets from being committed

```json
{
  "PreToolUse": [
    {
      "matcher": "Bash",
      "hooks": [
        {
          "type": "command",
          "command": "if echo \"$CLAUDE_TOOL_INPUT\" | grep -qE 'git add.*\\.env$|git add -A|git add \\.'; then echo 'WARNING: Be careful with broad git adds. Use specific file paths to avoid committing .env files.' >&2; fi"
        }
      ]
    }
  ]
}
```

## Auto-Formatting Hooks

### Auto-lint after file edits

```json
{
  "PostToolUse": [
    {
      "matcher": "Edit|Write",
      "hooks": [
        {
          "type": "command",
          "command": "{lint_command} $CLAUDE_FILE_PATH 2>/dev/null || true"
        }
      ]
    }
  ]
}
```

**Lint commands by stack:**
- Next.js/React/Vue/Svelte: `npx eslint --fix`
- Python (ruff): `ruff check --fix`
- Python (black): `black`
- Go: `gofmt -w`

### Auto-format with Prettier (JS/TS projects)

```json
{
  "PostToolUse": [
    {
      "matcher": "Edit|Write",
      "hooks": [
        {
          "type": "command",
          "command": "if echo \"$CLAUDE_FILE_PATH\" | grep -qE '\\.(ts|tsx|js|jsx|json|css|md)$'; then npx prettier --write \"$CLAUDE_FILE_PATH\" 2>/dev/null || true; fi"
        }
      ]
    }
  ]
}
```

## Testing Hooks

### Auto-run tests after code changes (TDD projects)

```json
{
  "PostToolUse": [
    {
      "matcher": "Edit|Write",
      "hooks": [
        {
          "type": "command",
          "command": "if echo $CLAUDE_FILE_PATH | grep -qE '\\.(ts|tsx|js|jsx)$' && ! echo $CLAUDE_FILE_PATH | grep -q 'test'; then {test_command} --run 2>/dev/null || true; fi"
        }
      ]
    }
  ]
}
```

**Test commands by stack:**
- Vitest: `npx vitest --run`
- Jest: `npx jest --passWithNoTests`
- pytest: `python -m pytest -x -q`
- Go: `go test ./...`

### Run related tests only (smart matching)

```json
{
  "PostToolUse": [
    {
      "matcher": "Edit|Write",
      "hooks": [
        {
          "type": "command",
          "command": "FILE=\"$CLAUDE_FILE_PATH\"; TEST_FILE=$(echo \"$FILE\" | sed 's/\\.\\(ts\\|js\\)/.test.\\1/; s/src\\//tests\\//' ); if [ -f \"$TEST_FILE\" ]; then npx vitest run \"$TEST_FILE\" 2>/dev/null || true; fi"
        }
      ]
    }
  ]
}
```

## Commit Quality Hooks

### Enforce commit size limits

```json
{
  "PreToolUse": [
    {
      "matcher": "Bash",
      "hooks": [
        {
          "type": "command",
          "command": "if echo \"$CLAUDE_TOOL_INPUT\" | grep -q 'git commit'; then CHANGED=$(git diff --cached --stat | tail -1 | grep -oP '\\d+(?= file)' || echo 0); if [ \"$CHANGED\" -gt 10 ]; then echo 'WARNING: Committing more than 10 files. Consider breaking this into smaller, atomic commits.' >&2; fi; fi"
        }
      ]
    }
  ]
}
```

### Enforce conventional commits

```json
{
  "PreToolUse": [
    {
      "matcher": "Bash",
      "hooks": [
        {
          "type": "command",
          "command": "if echo \"$CLAUDE_TOOL_INPUT\" | grep -qP 'git commit.*-m'; then MSG=$(echo \"$CLAUDE_TOOL_INPUT\" | grep -oP '(?<=-m [\"\\x27]).*?(?=[\"\\x27])' || true); if [ -n \"$MSG\" ] && ! echo \"$MSG\" | grep -qP '^(feat|fix|docs|style|refactor|perf|test|build|ci|chore|revert)(\\(.+\\))?!?:'; then echo 'WARNING: Commit message does not follow conventional commits format (feat|fix|docs|etc: message)' >&2; fi; fi"
        }
      ]
    }
  ]
}
```

## Session Management Hooks

### Stop hook — remind to update handoff

```json
{
  "Stop": [
    {
      "hooks": [
        {
          "type": "command",
          "command": "echo 'Reminder: Run /handoff to save your session context before ending.'"
        }
      ]
    }
  ]
}
```

## Security Hooks

### Block secret patterns in code files

```json
{
  "PreToolUse": [
    {
      "matcher": "Write|Edit",
      "hooks": [
        {
          "type": "command",
          "command": "if echo \"$CLAUDE_TOOL_INPUT\" | grep -qiE '(sk-[a-zA-Z0-9]{20,}|AKIA[A-Z0-9]{16}|ghp_[a-zA-Z0-9]{36}|password\\s*=\\s*[\"\\x27][^\"\\x27]{8,})'; then echo 'BLOCKED: Possible secret or credential detected in code. Use environment variables instead.' >&2; exit 1; fi"
        }
      ]
    }
  ]
}
```

### Validate file permissions on sensitive files

```json
{
  "PostToolUse": [
    {
      "matcher": "Write",
      "hooks": [
        {
          "type": "command",
          "command": "if echo \"$CLAUDE_FILE_PATH\" | grep -qE '\\.(env|pem|key)$'; then chmod 600 \"$CLAUDE_FILE_PATH\" 2>/dev/null || true; fi"
        }
      ]
    }
  ]
}
```

## Smart Validation (Advanced — Prompt Hooks)

### AI-powered command safety check

```json
{
  "PreToolUse": [
    {
      "matcher": "Bash",
      "hooks": [
        {
          "type": "prompt",
          "prompt": "Evaluate if this command is safe to run in a development environment. Consider: could it affect production data, delete important files, or expose secrets? If safe, respond with just 'safe'. If unsafe, respond with 'unsafe: [reason]'."
        }
      ]
    }
  ]
}
```

## Permission Settings

### Solo developer (relaxed)
```json
{
  "permissions": {
    "deny": ["Bash(rm -rf /)", "Bash(git push --force origin main)"]
  }
}
```

### Team (controlled)
```json
{
  "permissions": {
    "deny": [
      "Bash(git push --force)",
      "Bash(DROP TABLE)",
      "Bash(DROP DATABASE)"
    ]
  }
}
```

### Subagent (least privilege)
```json
{
  "permissions": {
    "allowlist": ["Read", "Grep", "Glob"]
  }
}
```

## Hook Selection Logic

Generate hooks based on these conditions:

| Condition | Hook Type | Hook |
|-----------|-----------|------|
| All projects | PreToolUse | Block dangerous commands |
| All projects | PreToolUse | Block secrets in code |
| All projects | Stop | Handoff reminder |
| Has linter | PostToolUse | Auto-lint |
| Has Prettier | PostToolUse | Auto-format |
| TDD philosophy | PostToolUse | Auto-run tests |
| Has staging/prod | PreToolUse | Block production access |
| Team project | PreToolUse | Commit size limits |
| Conventional commits | PreToolUse | Commit format enforcement |
| Has .env files | PreToolUse | Block broad git adds |
| Sensitive files | PostToolUse | File permission enforcement |

## Composing Multiple Hooks

When a project needs multiple hooks on the same event, merge them into a single array:

```json
{
  "hooks": {
    "PreToolUse": [
      { "matcher": "Bash", "hooks": [{ "type": "command", "command": "...safety..." }] },
      { "matcher": "Bash", "hooks": [{ "type": "command", "command": "...commit quality..." }] }
    ],
    "PostToolUse": [
      { "matcher": "Edit|Write", "hooks": [{ "type": "command", "command": "...lint..." }] },
      { "matcher": "Edit|Write", "hooks": [{ "type": "command", "command": "...test..." }] }
    ],
    "Stop": [
      { "hooks": [{ "type": "command", "command": "...handoff reminder..." }] }
    ]
  }
}
```
