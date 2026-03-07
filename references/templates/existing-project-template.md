# Existing Project Analysis Template

When the user says "I want to add Claude Code to an existing project" (detected in Phase 1),
switch from the greenfield scaffolding flow to this analysis-first flow.

## Analysis Phase

Before asking most interview questions, analyze the existing codebase to pre-fill answers.

### Step 1: Detect Stack Automatically

Run these commands to detect the project's technology stack:

```bash
# Package managers and languages
ls package.json pyproject.toml go.mod Cargo.toml composer.json Gemfile *.csproj 2>/dev/null

# Read package.json for JS/TS projects
cat package.json 2>/dev/null | head -50

# Check for frameworks
ls next.config.* nuxt.config.* svelte.config.* vite.config.* angular.json 2>/dev/null

# Check for databases
ls prisma/ drizzle/ alembic/ migrations/ 2>/dev/null
cat docker-compose.yml 2>/dev/null | grep -i 'postgres\|mongo\|redis\|mysql'

# Check for existing Claude config
ls CLAUDE.md .claude/ .claudeignore .mcp.json 2>/dev/null

# Check for CI/CD
ls .github/workflows/ .gitlab-ci.yml .circleci/ Jenkinsfile 2>/dev/null

# Check for Docker
ls Dockerfile docker-compose.yml 2>/dev/null

# Check for testing frameworks
cat package.json 2>/dev/null | grep -i 'jest\|vitest\|playwright\|cypress\|mocha'
cat pyproject.toml 2>/dev/null | grep -i 'pytest'

# Check project structure
find . -maxdepth 2 -type d | head -40
```

### Step 2: Present Findings and Confirm

Present what you detected in a clear table:

```
I've analyzed your project. Here's what I found:

| Category        | Detected                     | Confidence |
|-----------------|------------------------------|------------|
| Language        | TypeScript                   | High       |
| Frontend        | Next.js (App Router)         | High       |
| Backend         | API Routes (integrated)      | High       |
| Database        | PostgreSQL via Prisma         | High       |
| Auth            | Clerk                        | High       |
| Testing         | Vitest + Playwright           | High       |
| CI/CD           | GitHub Actions               | High       |
| Deployment      | Vercel                       | Medium     |
| Docker          | Yes (docker-compose for dev) | High       |
| Existing Claude | No CLAUDE.md found           | High       |

Does this look correct? Let me know if anything is wrong or missing.
```

### Step 3: Fill Gaps

Only ask interview questions for things you couldn't detect:
- Project description (can't be detected from code)
- Team size and workflow preferences
- Architecture decisions that aren't obvious
- Planned integrations not yet in the codebase
- Testing philosophy / TDD preference

### Step 4: Audit Existing Configuration

If the project already has Claude Code configuration:

**Existing CLAUDE.md:**
```bash
# Validate it
python <skill-path>/scripts/validate_claude_md.py CLAUDE.md
```
- Report issues found
- Suggest improvements based on best practices
- Offer to enhance rather than replace

**Existing agents:**
```bash
# Validate them
python <skill-path>/scripts/validate_agents.py .claude/agents/
```
- Report which agents exist and their quality
- Suggest missing agents from the standard set of 8
- Offer to add missing ones without disrupting existing ones

**Existing rules and hooks:**
- Review for completeness
- Suggest additions based on the detected stack

## Generation Phase (Existing Projects)

The generation phase differs from greenfield:

1. **NEVER overwrite existing files** without explicit permission
2. **Merge, don't replace** — if CLAUDE.md exists, enhance it
3. **Add missing pieces** — generate only what's not already present
4. **Respect existing conventions** — match the project's existing naming, structure, and style
5. **Create a backup** — before modifying any existing config:
   ```bash
   mkdir -p .claude/backups/$(date +%Y%m%d)
   cp CLAUDE.md .claude/backups/$(date +%Y%m%d)/ 2>/dev/null || true
   cp -r .claude/ .claude/backups/$(date +%Y%m%d)/claude-config/ 2>/dev/null || true
   ```

### Generation Checklist for Existing Projects

- [ ] CLAUDE.md — create or enhance (respect existing content)
- [ ] .claude/agents/ — add missing agents
- [ ] .claude/rules/ — add stack-specific rules
- [ ] .claude/commands/ — add useful slash commands
- [ ] .claude/handoff.md — create with current project state
- [ ] .claude/settings.json — add hooks (merge with existing)
- [ ] .mcp.json — generate if not present
- [ ] .claudeignore — create or enhance
- [ ] ARCHITECTURE.md — create if not present

### Final Verification

After adding Claude Code configuration to an existing project:
1. Run the healthcheck script
2. Verify CLAUDE.md doesn't exceed 200 lines
3. Ensure agents reference actual files/paths in the project
4. Test that hooks work with the project's actual tools
5. Show a diff of all changes made
