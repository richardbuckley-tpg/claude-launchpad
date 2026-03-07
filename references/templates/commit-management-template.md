# Commit Size Management Template

Configure hooks and rules to enforce atomic, well-sized commits.
Prevents the common anti-pattern of massive commits that are hard to review and revert.

## Why This Matters

Large commits:
- Are harder to review (reviewers miss issues)
- Are harder to revert (reverting one thing reverts everything)
- Make `git bisect` less useful
- Create merge conflicts more often
- Make the git history harder to understand

## Commit Size Hooks

### Warning on large commits (soft limit)

Add to `.claude/settings.json`:
```json
{
  "PreToolUse": [
    {
      "matcher": "Bash",
      "hooks": [
        {
          "type": "command",
          "command": "if echo \"$CLAUDE_TOOL_INPUT\" | grep -q 'git commit'; then FILES=$(git diff --cached --numstat | wc -l | tr -d ' '); LINES=$(git diff --cached --stat | tail -1 | grep -oE '[0-9]+ insertion|[0-9]+ deletion' | grep -oE '[0-9]+' | paste -sd+ | bc 2>/dev/null || echo 0); if [ \"$FILES\" -gt 10 ]; then echo \"WARNING: Committing $FILES files. Consider splitting into smaller, focused commits.\" >&2; fi; if [ \"$LINES\" -gt 500 ]; then echo \"WARNING: $LINES lines changed. Large commits are harder to review. Consider splitting.\" >&2; fi; fi"
        }
      ]
    }
  ]
}
```

### Block on very large commits (hard limit)

```json
{
  "PreToolUse": [
    {
      "matcher": "Bash",
      "hooks": [
        {
          "type": "command",
          "command": "if echo \"$CLAUDE_TOOL_INPUT\" | grep -q 'git commit'; then FILES=$(git diff --cached --numstat | wc -l | tr -d ' '); if [ \"$FILES\" -gt 25 ]; then echo 'BLOCKED: Committing more than 25 files. This commit is too large. Break it into smaller, logical chunks.' >&2; exit 1; fi; fi"
        }
      ]
    }
  ]
}
```

## Conventional Commits Enforcement

### Format validation hook

```json
{
  "PreToolUse": [
    {
      "matcher": "Bash",
      "hooks": [
        {
          "type": "command",
          "command": "if echo \"$CLAUDE_TOOL_INPUT\" | grep -qP 'git commit.*-m'; then MSG=$(echo \"$CLAUDE_TOOL_INPUT\" | grep -oP '(?<=-m [\"'\\''']).*?(?=[\"'\\'''])' | head -1 || true); if [ -n \"$MSG\" ] && ! echo \"$MSG\" | grep -qP '^(feat|fix|docs|style|refactor|perf|test|build|ci|chore|revert)(\\(.+\\))?!?:'; then echo 'BLOCKED: Commit message must follow conventional commits: type(scope): message' >&2; echo 'Types: feat, fix, docs, style, refactor, perf, test, build, ci, chore, revert' >&2; exit 1; fi; fi"
        }
      ]
    }
  ]
}
```

## Branch Naming Enforcement

```json
{
  "PreToolUse": [
    {
      "matcher": "Bash",
      "hooks": [
        {
          "type": "command",
          "command": "if echo \"$CLAUDE_TOOL_INPUT\" | grep -q 'git checkout -b'; then BRANCH=$(echo \"$CLAUDE_TOOL_INPUT\" | grep -oP '(?<=checkout -b )\\S+' || true); if [ -n \"$BRANCH\" ] && ! echo \"$BRANCH\" | grep -qP '^(feature|fix|hotfix|chore|refactor|docs|test)/'; then echo 'WARNING: Branch name should follow pattern: type/description (e.g., feature/user-auth, fix/login-bug)' >&2; fi; fi"
        }
      ]
    }
  ]
}
```

## Push Agent Enhancement

When commit management is enabled, add these rules to the push agent:

```markdown
## Commit Guidelines

- Each commit should be ONE logical change
- If you need the word "and" in your commit message, it's probably two commits
- Aim for: 1-5 files per commit, under 200 lines changed
- Group related changes: schema + migration + model update = one commit
- Separate unrelated changes: formatting fix ≠ bug fix

## Commit Message Format (Conventional Commits)
- `feat(scope): add new feature` — new functionality
- `fix(scope): fix bug description` — bug fixes
- `refactor(scope): restructure code` — no behavior change
- `test(scope): add tests for feature` — test additions
- `docs(scope): update documentation` — documentation only
- `chore(scope): update dependencies` — maintenance tasks

## Before Pushing
1. Review `git log --oneline -5` — are commits logical and atomic?
2. Run `git diff --stat HEAD~1` — is the last commit a reasonable size?
3. Run full test suite — no regressions?
4. If any commit is too large, use `git reset HEAD~1` and re-commit in parts
```

## Rules File

Generate `.claude/rules/commits.md`:

```markdown
# Commit Rules

## Commit Size
- Soft limit: 10 files, 500 lines per commit
- Hard limit: 25 files per commit (blocked)
- If a change touches more than 10 files, consider:
  1. Is this truly one logical change?
  2. Can it be broken into sequential commits?
  3. Should the approach be simplified?

## Commit Messages
- Follow conventional commits: type(scope): description
- First line under 72 characters
- Use imperative mood: "add feature" not "added feature"
- Reference issue numbers when applicable: feat(auth): add SSO login (#123)

## Branch Names
- Pattern: type/description
- Types: feature, fix, hotfix, chore, refactor, docs, test
- Use kebab-case: feature/user-authentication
```

## Generation Rules

1. Generate commit size warning hook for ALL team projects
2. Generate conventional commit enforcement if user chose conventional commits
3. Generate branch naming hook for team projects with defined branch strategy
4. Enhance push agent with commit guidelines
5. Generate `.claude/rules/commits.md` for all projects
6. Thresholds are configurable — ask user during interview:
   - Soft limit (default: 10 files / 500 lines)
   - Hard limit (default: 25 files)
