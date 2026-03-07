# Auto-Iterative TDD Loop Configuration

Configure Claude Code for autonomous test-driven development cycles. When enabled,
Claude follows a strict red-green-refactor loop automatically.

## How It Works

The TDD loop runs as a cycle:
1. **Write test** (RED) — Write a failing test from the spec
2. **Run test** — Verify it fails for the right reason
3. **Write code** (GREEN) — Write the minimum code to make the test pass
4. **Run test** — Verify it passes
5. **Refactor** — Clean up while keeping tests green
6. **Run test** — Verify nothing broke
7. **Repeat** — Next test case

## Testing Agent Enhancement for TDD

When the user chooses TDD philosophy, enhance the testing agent (`.claude/agents/testing.md`)
with these additions to the agent body:

```markdown
## TDD Loop Protocol

When asked to implement a feature using TDD:

1. Read the spec/requirement carefully
2. Break it into testable behaviors (list them out)
3. For each behavior, follow the red-green-refactor cycle:

### RED Phase
- Write ONE test that describes the expected behavior
- Run it: `{test_command}`
- Verify it FAILS (if it passes, the test is wrong or the feature already exists)
- If the failure message is unclear, improve the test

### GREEN Phase
- Write the MINIMUM code to make the test pass
- No extra features, no premature optimization
- Run: `{test_command}`
- If it fails, fix the implementation (not the test)

### REFACTOR Phase
- Look for duplication, unclear naming, or structural issues
- Refactor both test and implementation code
- Run: `{test_command}`
- If anything breaks, undo the refactor and try a smaller change

### Completion Check
- Run the FULL test suite: `{full_test_command}`
- Fix any regressions before moving to the next behavior
- Update the test count and coverage

## TDD Rules
- NEVER write implementation code before its test
- NEVER skip the RED phase (if the test passes immediately, investigate why)
- Keep each cycle small — one behavior at a time
- Tests describe WHAT, not HOW — test behavior, not implementation
- Use worktree isolation (`isolation: worktree`) to prevent test pollution
```

## TDD Hooks

### Auto-run tests on every file change (aggressive TDD)

For `.claude/settings.json`:
```json
{
  "hooks": {
    "PostToolUse": [
      {
        "matcher": "Edit|Write",
        "hooks": [
          {
            "type": "command",
            "command": "if echo \"$CLAUDE_FILE_PATH\" | grep -qE '\\.(ts|tsx|js|jsx|py|go)$'; then {test_command} 2>&1 | tail -5; fi"
          }
        ]
      }
    ]
  }
}
```

### Test coverage gate (blocks commit if coverage drops)

```json
{
  "PreToolUse": [
    {
      "matcher": "Bash",
      "hooks": [
        {
          "type": "command",
          "command": "if echo \"$CLAUDE_TOOL_INPUT\" | grep -q 'git commit'; then COVERAGE=$(npx vitest run --coverage --reporter=json 2>/dev/null | grep -oP '\"lines\":{\"total\":\\d+,\"covered\":\\d+,\"pct\":\\K[\\d.]+' || echo 0); if [ $(echo \"$COVERAGE < 80\" | bc -l 2>/dev/null || echo 1) -eq 1 ]; then echo \"WARNING: Test coverage is ${COVERAGE}%. Consider adding tests before committing.\" >&2; fi; fi"
        }
      ]
    }
  ]
}
```

## TDD Slash Command

Generate `.claude/commands/tdd.md`:

```markdown
---
description: Start a TDD cycle for a feature or behavior
---

Starting TDD cycle for: $ARGUMENTS

1. Read the relevant spec, ticket, or requirement
2. List all testable behaviors for this feature
3. For each behavior, follow red-green-refactor:
   a. Write a failing test
   b. Run tests to confirm RED
   c. Write minimum code to pass
   d. Run tests to confirm GREEN
   e. Refactor if needed
   f. Run tests to confirm still GREEN
4. After all behaviors are covered, run full test suite
5. Report: tests written, coverage change, any issues

Use worktree isolation for this work.
```

## Test Framework Commands by Stack

| Stack | Test Command | Full Suite | Coverage |
|-------|-------------|------------|----------|
| Vitest | `npx vitest run` | `npx vitest run` | `npx vitest run --coverage` |
| Jest | `npx jest --passWithNoTests` | `npx jest` | `npx jest --coverage` |
| Playwright | `npx playwright test` | `npx playwright test` | N/A |
| pytest | `python -m pytest -x -q` | `python -m pytest` | `python -m pytest --cov` |
| Go | `go test ./...` | `go test ./...` | `go test -cover ./...` |

## Generation Rules

1. Only generate TDD configuration if user chose "TDD" testing philosophy
2. Enhance the testing agent with TDD loop protocol
3. Add auto-test PostToolUse hook
4. Generate `/tdd` slash command
5. Optionally add coverage gate hook (ask user for coverage threshold, default 80%)
6. Add TDD-specific rules in `.claude/rules/testing.md`
