# Slash Commands Template

Generate custom slash commands in `.claude/commands/` based on the user's project needs.
Slash commands are markdown files with YAML frontmatter that Claude executes as reusable workflows.

## Command File Format

```markdown
---
description: Brief description shown in command picker
---

Instructions for Claude to follow when this command is invoked.
Can reference $ARGUMENTS for user-provided parameters.
```

## Core Commands (Always Generate)

### /handoff
See `handoff-template.md` for full details.

### /status
```markdown
---
description: Show project status — what's working, what's in progress, recent changes
---

Give me a quick project status report:

1. Check `git status` and `git log --oneline -5` for recent activity
2. Read `.claude/handoff.md` for current state
3. Check for any failing tests by running the test suite
4. Look for TODO/FIXME comments in recently changed files

Present a concise status with:
- Recent changes (last 5 commits)
- Current branch and any uncommitted work
- Test health (passing/failing)
- Open TODOs in recently changed files
- Next recommended action
```

## Stack-Specific Commands

### /deploy (Generate based on hosting platform)

**Vercel:**
```markdown
---
description: Deploy to Vercel with pre-flight checks
---

Before deploying to Vercel:
1. Run the full test suite
2. Run the linter and fix any issues
3. Check for any TODO/FIXME that should be addressed before deploy
4. Verify environment variables are set in Vercel dashboard
5. Run `vercel --prod` or push to the deploy branch

If any step fails, stop and report the issue.
```

**Railway:**
```markdown
---
description: Deploy to Railway with pre-flight checks
---

Before deploying to Railway:
1. Run the full test suite
2. Run the linter and fix any issues
3. Verify Dockerfile or nixpacks config is correct
4. Check `railway status` for current deployment state
5. Run `railway up` or push to deploy branch

If any step fails, stop and report the issue.
```

**AWS:**
```markdown
---
description: Deploy to AWS with pre-flight checks
---

Before deploying:
1. Run the full test suite
2. Run the linter
3. Build the project and verify no build errors
4. Check AWS credentials are configured (`aws sts get-caller-identity`)
5. Run the deployment command for this project's AWS setup

Report the deployment status when complete.
```

### /db-migrate (Generate based on ORM)

**Prisma:**
```markdown
---
description: Create and run a database migration with Prisma
---

To create a database migration:
1. Review the current `prisma/schema.prisma` for pending changes
2. Run `npx prisma migrate dev --name $ARGUMENTS`
3. Verify the migration SQL looks correct
4. Run `npx prisma generate` to update the client
5. Check if any seed data needs updating

If $ARGUMENTS is empty, ask what the migration should be named.
```

**Drizzle:**
```markdown
---
description: Create and run a database migration with Drizzle
---

1. Run `npx drizzle-kit generate` to create migration from schema changes
2. Review the generated SQL in `drizzle/` directory
3. Run `npx drizzle-kit migrate` to apply
4. Verify the migration applied correctly
```

**SQLAlchemy (Python):**
```markdown
---
description: Create and run a database migration with Alembic
---

1. Run `alembic revision --autogenerate -m "$ARGUMENTS"`
2. Review the generated migration in `alembic/versions/`
3. Run `alembic upgrade head`
4. Verify the migration applied correctly
```

### /new-feature
```markdown
---
description: Start a new feature with proper branching and planning
---

Starting a new feature: $ARGUMENTS

1. Create a feature branch: `git checkout -b feature/$ARGUMENTS`
2. Read ARCHITECTURE.md to understand current system design
3. Read `.claude/handoff.md` for current project state
4. Create a brief plan:
   - What files need to change?
   - What new files are needed?
   - What tests should be written?
   - Any database changes needed?
5. Present the plan for approval before writing code
```

### /fix-bug
```markdown
---
description: Systematically diagnose and fix a bug
---

Investigating bug: $ARGUMENTS

Follow the debugger agent methodology:
1. **Reproduce**: Understand how to trigger the bug
2. **Isolate**: Find the minimal reproduction case
3. **Diagnose**: Read relevant code and identify root cause
4. **Fix**: Make the minimal fix needed
5. **Test**: Write a regression test that fails without the fix
6. **Verify**: Run the full test suite to ensure no regressions

Never guess at fixes. Always investigate first.
```

## AI-Specific Commands (if AI/LLM integration)

### /prompt-test
```markdown
---
description: Test and iterate on an AI prompt
---

Testing prompt for: $ARGUMENTS

1. Find the relevant prompt in the codebase
2. Analyze the current prompt structure
3. Run a test with sample inputs
4. Suggest improvements based on results
5. Apply changes and re-test
```

## Generation Rules

1. Always generate `/handoff`, `/status`, and `/new-feature`
2. Generate `/deploy` customized for their hosting platform
3. Generate `/db-migrate` customized for their ORM
4. Generate `/fix-bug` only if they have a testing framework configured
5. Generate `/prompt-test` only if they're using AI/LLM integration
6. Commands go in `.claude/commands/` directory
7. Each command is a separate `.md` file named after the command (e.g., `handoff.md`)
8. Keep command instructions actionable and specific to their stack
