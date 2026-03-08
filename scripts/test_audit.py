#!/usr/bin/env python3
"""Tests for claude-launchpad audit.py"""

import json
import shutil
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from audit import (
    AuditResult,
    TOKENS_PER_LINE,
    apply_fixes,
    audit,
    check_agents,
    check_claude_md,
    check_commands_content,
    check_context_percentage,
    check_discoverability,
    check_handoff,
    check_mcp_servers,
    check_rules,
    check_settings,
    check_skills_content,
    check_staleness,
    check_total_budget,
    count_lines,
    estimate_tokens,
    format_report,
    format_recommendations,
    generate_recommendations,
)


class TestTokenEstimation(unittest.TestCase):
    """Test token counting and estimation."""

    def test_count_lines_excludes_empty(self):
        tmpdir = Path(tempfile.mkdtemp())
        try:
            f = tmpdir / "test.md"
            f.write_text("line 1\n\nline 3\n   \nline 5\n")
            self.assertEqual(count_lines(f), 3)
        finally:
            shutil.rmtree(tmpdir)

    def test_count_lines_missing_file(self):
        self.assertEqual(count_lines(Path("/nonexistent/file.md")), 0)

    def test_estimate_tokens(self):
        self.assertEqual(estimate_tokens(10), 10 * TOKENS_PER_LINE)
        self.assertEqual(estimate_tokens(0), 0)


class TestAuditResult(unittest.TestCase):
    """Test AuditResult scoring and issue tracking."""

    def test_starts_at_100(self):
        r = AuditResult()
        self.assertEqual(r.score, 100)

    def test_error_deducts_10(self):
        r = AuditResult()
        r.add_issue("error", "test error")
        self.assertEqual(r.score, 90)

    def test_warning_deducts_3(self):
        r = AuditResult()
        r.add_issue("warning", "test warning")
        self.assertEqual(r.score, 97)

    def test_component_within_budget(self):
        r = AuditResult()
        r.add_component("test", 50, budget_warn=80, budget_fail=150)
        self.assertEqual(r.score, 100)
        self.assertEqual(r.components["test"]["status"], "✓")

    def test_component_nearing_limit(self):
        r = AuditResult()
        r.add_component("test", 100, budget_warn=80, budget_fail=150)
        self.assertEqual(r.score, 97)  # -3 for warning
        self.assertIn("nearing", r.components["test"]["status"])

    def test_component_over_budget(self):
        r = AuditResult()
        r.add_component("test", 200, budget_warn=80, budget_fail=150)
        self.assertEqual(r.score, 90)  # -10 for error
        self.assertIn("over", r.components["test"]["status"])

    def test_score_never_below_zero(self):
        r = AuditResult()
        for i in range(20):
            r.add_issue("error", f"error {i}")
        self.assertGreaterEqual(r.to_dict()["score"], 0)

    def test_to_dict_structure(self):
        r = AuditResult()
        r.add_component("test", 10, 20, 30)
        r.add_issue("warning", "test")
        d = r.to_dict()
        self.assertIn("score", d)
        self.assertIn("total_lines", d)
        self.assertIn("total_tokens", d)
        self.assertIn("components", d)
        self.assertIn("issues", d)


def make_project(tmpdir, **kwargs):
    """Create a minimal project structure for testing."""
    project_dir = tmpdir / "project"
    project_dir.mkdir()

    # CLAUDE.md
    if kwargs.get("claude_md", True):
        claude_md = project_dir / "CLAUDE.md"
        claude_md.write_text(kwargs.get("claude_md_content", "# Project\nBuild commands here\n"))

    # .claude directory
    claude_dir = project_dir / ".claude"
    claude_dir.mkdir()

    # Agents
    if kwargs.get("agents", False):
        agents_dir = claude_dir / "agents"
        agents_dir.mkdir()
        for name, content in kwargs["agents"].items():
            (agents_dir / f"{name}.md").write_text(content)

    # Rules
    if kwargs.get("rules", False):
        rules_dir = claude_dir / "rules"
        rules_dir.mkdir()
        for name, content in kwargs["rules"].items():
            (rules_dir / f"{name}.md").write_text(content)

    # Commands
    if kwargs.get("commands", False):
        commands_dir = claude_dir / "commands"
        commands_dir.mkdir()
        for name, content in kwargs["commands"].items():
            (commands_dir / f"{name}.md").write_text(content)

    # Settings
    if kwargs.get("settings", None) is not None:
        (claude_dir / "settings.json").write_text(
            json.dumps(kwargs["settings"], indent=2) if isinstance(kwargs["settings"], dict)
            else kwargs["settings"]
        )

    # Handoff
    if kwargs.get("handoff", False):
        (claude_dir / "handoff.md").write_text("# Handoff\nSession state here\n")

    return project_dir


class TestCheckClaudeMd(unittest.TestCase):
    """Test CLAUDE.md checks."""

    def setUp(self):
        self.tmpdir = Path(tempfile.mkdtemp())

    def tearDown(self):
        shutil.rmtree(self.tmpdir)

    def test_missing_claude_md_is_error(self):
        project_dir = make_project(self.tmpdir, claude_md=False)
        r = AuditResult()
        check_claude_md(project_dir, r)
        errors = [i for i in r.issues if i["level"] == "error"]
        self.assertTrue(any("CLAUDE.md not found" in e["message"] for e in errors))

    def test_claude_md_within_budget(self):
        project_dir = make_project(self.tmpdir, claude_md_content="line\n" * 50)
        r = AuditResult()
        check_claude_md(project_dir, r)
        self.assertEqual(len(r.issues), 0)

    def test_claude_md_over_budget(self):
        project_dir = make_project(self.tmpdir, claude_md_content="line\n" * 200)
        r = AuditResult()
        check_claude_md(project_dir, r)
        errors = [i for i in r.issues if i["level"] == "error"]
        self.assertTrue(len(errors) > 0)


class TestCheckAgents(unittest.TestCase):
    """Test agent directory checks."""

    def setUp(self):
        self.tmpdir = Path(tempfile.mkdtemp())

    def tearDown(self):
        shutil.rmtree(self.tmpdir)

    def test_no_agents_dir_is_warning(self):
        project_dir = make_project(self.tmpdir)
        r = AuditResult()
        check_agents(project_dir, r)
        self.assertTrue(any("agents" in i["message"].lower() for i in r.issues))

    def test_empty_agents_dir_is_warning(self):
        project_dir = make_project(self.tmpdir, agents={})
        # agents={} creates the dir but no files — wait, our helper only creates files
        # Let me manually create empty dir
        (project_dir / ".claude" / "agents").mkdir(exist_ok=True)
        r = AuditResult()
        check_agents(project_dir, r)
        self.assertTrue(any("No agent files" in i["message"] for i in r.issues))

    def test_valid_agent(self):
        project_dir = make_project(self.tmpdir, agents={
            "architect": "---\nname: architect\ndescription: Plans features\ntools: Read,Grep\n---\nPlan the implementation.\n"
        })
        r = AuditResult()
        check_agents(project_dir, r)
        # Should have no errors about agent content (might have size warning depending on line count)
        missing_fm = [i for i in r.issues if "frontmatter" in i["message"]]
        self.assertEqual(len(missing_fm), 0)

    def test_agent_missing_frontmatter(self):
        project_dir = make_project(self.tmpdir, agents={
            "bad-agent": "This agent has no frontmatter at all.\nJust raw text.\n"
        })
        r = AuditResult()
        check_agents(project_dir, r)
        fm_warnings = [i for i in r.issues if "frontmatter" in i["message"]]
        self.assertTrue(len(fm_warnings) > 0)

    def test_large_agent_warning(self):
        project_dir = make_project(self.tmpdir, agents={
            "big-agent": "---\nname: big\n---\n" + "line\n" * 60
        })
        r = AuditResult()
        check_agents(project_dir, r)
        size_warnings = [i for i in r.issues if "lines" in i["message"] and "big-agent" in i["message"]]
        self.assertTrue(len(size_warnings) > 0)

    def test_duplicate_agent_names(self):
        project_dir = make_project(self.tmpdir, agents={
            "agent-a": "---\nname: duplicated\n---\nFirst agent\n",
            "agent-b": "---\nname: duplicated\n---\nSecond agent\n",
        })
        r = AuditResult()
        check_agents(project_dir, r)
        dup_warnings = [i for i in r.issues if "Duplicate" in i["message"]]
        self.assertTrue(len(dup_warnings) > 0)


class TestCheckSettings(unittest.TestCase):
    """Test settings.json validation."""

    def setUp(self):
        self.tmpdir = Path(tempfile.mkdtemp())

    def tearDown(self):
        shutil.rmtree(self.tmpdir)

    def test_invalid_json_is_error(self):
        project_dir = make_project(self.tmpdir, settings="not json {{{")
        r = AuditResult()
        check_settings(project_dir, r)
        errors = [i for i in r.issues if i["level"] == "error"]
        self.assertTrue(any("not valid JSON" in e["message"] for e in errors))

    def test_valid_settings_no_issues(self):
        project_dir = make_project(self.tmpdir, settings={
            "hooks": {"PreToolUse": [{"matcher": "Bash", "hooks": [{"type": "block", "pattern": "rm -rf"}]}]}
        })
        r = AuditResult()
        check_settings(project_dir, r)
        errors = [i for i in r.issues if i["level"] == "error"]
        self.assertEqual(len(errors), 0)


class TestCheckMcpServers(unittest.TestCase):
    """Test MCP server configuration checks."""

    def setUp(self):
        self.tmpdir = Path(tempfile.mkdtemp())

    def tearDown(self):
        shutil.rmtree(self.tmpdir)

    def test_no_mcp_is_fine(self):
        project_dir = make_project(self.tmpdir, settings={"hooks": {}})
        r = AuditResult()
        check_mcp_servers(project_dir, r)
        self.assertEqual(len(r.issues), 0)

    def test_hardcoded_secret_is_error(self):
        project_dir = make_project(self.tmpdir, settings={
            "mcpServers": {
                "github": {
                    "command": "npx",
                    "args": ["-y", "server"],
                    "env": {"GITHUB_TOKEN": "ghp_abcdefghijklmnopqrstuvwxyz1234567890"}
                }
            }
        })
        r = AuditResult()
        check_mcp_servers(project_dir, r)
        errors = [i for i in r.issues if i["level"] == "error"]
        self.assertTrue(any("hardcoded secret" in e["message"] for e in errors))

    def test_env_var_reference_is_fine(self):
        project_dir = make_project(self.tmpdir, settings={
            "mcpServers": {
                "github": {
                    "command": "npx",
                    "args": ["-y", "server"],
                    "env": {"GITHUB_TOKEN": "${GITHUB_TOKEN}"}
                }
            }
        })
        r = AuditResult()
        check_mcp_servers(project_dir, r)
        errors = [i for i in r.issues if i["level"] == "error" and "secret" in i["message"]]
        self.assertEqual(len(errors), 0)

    def test_too_many_servers_warning(self):
        servers = {f"server{i}": {"command": "npx", "args": []} for i in range(7)}
        project_dir = make_project(self.tmpdir, settings={"mcpServers": servers})
        r = AuditResult()
        check_mcp_servers(project_dir, r)
        warnings = [i for i in r.issues if "slow startup" in i["message"]]
        self.assertTrue(len(warnings) > 0)

    def test_missing_command_is_error(self):
        project_dir = make_project(self.tmpdir, settings={
            "mcpServers": {"broken": {"args": ["-y", "server"]}}
        })
        r = AuditResult()
        check_mcp_servers(project_dir, r)
        errors = [i for i in r.issues if "command" in i["message"]]
        self.assertTrue(len(errors) > 0)


class TestCheckStaleness(unittest.TestCase):
    """Test staleness detection in config files."""

    def setUp(self):
        self.tmpdir = Path(tempfile.mkdtemp())

    def tearDown(self):
        shutil.rmtree(self.tmpdir)

    def test_stale_command_reference(self):
        project_dir = make_project(
            self.tmpdir,
            claude_md_content="Use /deploy to push to production\n",
            commands={"status": "---\ndescription: check status\n---\nCheck status.\n"}
        )
        r = AuditResult()
        check_staleness(project_dir, r)
        stale = [i for i in r.issues if "/deploy" in i["message"]]
        self.assertTrue(len(stale) > 0)

    def test_valid_command_reference(self):
        project_dir = make_project(
            self.tmpdir,
            claude_md_content="Use /status to check project state\n",
            commands={"status": "---\ndescription: check status\n---\nCheck status.\n"}
        )
        r = AuditResult()
        check_staleness(project_dir, r)
        stale = [i for i in r.issues if "/status" in i["message"]]
        self.assertEqual(len(stale), 0)

    def test_stale_path_in_rules(self):
        project_dir = make_project(self.tmpdir, rules={
            "api-rules": "Always validate inputs in src/api/handlers\n"
        })
        # src/ directory doesn't exist
        r = AuditResult()
        check_staleness(project_dir, r)
        stale = [i for i in r.issues if "src" in i["message"]]
        self.assertTrue(len(stale) > 0)

    def test_valid_path_in_rules(self):
        project_dir = make_project(self.tmpdir, rules={
            "api-rules": "Always validate inputs in src/api/handlers\n"
        })
        (project_dir / "src" / "api" / "handlers").mkdir(parents=True)
        r = AuditResult()
        check_staleness(project_dir, r)
        stale = [i for i in r.issues if "src" in i["message"]]
        self.assertEqual(len(stale), 0)

    def test_deep_path_validation(self):
        """Staleness check should verify deeper path segments, not just first dir."""
        project_dir = make_project(self.tmpdir, rules={
            "deep-rule": "Check files in src/api/v2/handlers for validation\n"
        })
        (project_dir / "src").mkdir()
        (project_dir / "src" / "api").mkdir()
        # src/api/v2 does NOT exist
        r = AuditResult()
        check_staleness(project_dir, r)
        stale = [i for i in r.issues if "v2" in i.get("message", "")]
        self.assertTrue(len(stale) > 0, "Should warn about non-existent deep path src/api/v2")


class TestCheckHandoff(unittest.TestCase):
    """Test handoff document checks."""

    def setUp(self):
        self.tmpdir = Path(tempfile.mkdtemp())

    def tearDown(self):
        shutil.rmtree(self.tmpdir)

    def test_missing_handoff_is_warning(self):
        project_dir = make_project(self.tmpdir, handoff=False)
        r = AuditResult()
        check_handoff(project_dir, r)
        warnings = [i for i in r.issues if "handoff" in i["message"].lower()]
        self.assertTrue(len(warnings) > 0)

    def test_present_handoff_no_warning(self):
        project_dir = make_project(self.tmpdir, handoff=True)
        r = AuditResult()
        check_handoff(project_dir, r)
        warnings = [i for i in r.issues if "handoff" in i["message"].lower()]
        self.assertEqual(len(warnings), 0)


class TestFullAudit(unittest.TestCase):
    """Test full audit pipeline."""

    def setUp(self):
        self.tmpdir = Path(tempfile.mkdtemp())

    def tearDown(self):
        shutil.rmtree(self.tmpdir)

    def test_healthy_project_scores_high(self):
        project_dir = make_project(
            self.tmpdir,
            claude_md_content="# Project\nBuild: npm run build\nTest: npm test\n",
            agents={
                "architect": "---\nname: architect\ndescription: Plans\ntools: Read\n---\nPlan.\n",
            },
            commands={
                "status": "---\ndescription: status\n---\nShow status.\n",
            },
            settings={"hooks": {}, "mcpServers": {}},
            handoff=True,
        )
        result = audit(project_dir)
        self.assertGreaterEqual(result.score, 80)

    def test_empty_project_scores_low(self):
        project_dir = self.tmpdir / "empty"
        project_dir.mkdir()
        result = audit(project_dir)
        self.assertLess(result.score, 100)  # Missing CLAUDE.md at minimum

    def test_format_report_includes_score(self):
        project_dir = make_project(self.tmpdir, handoff=True)
        result = audit(project_dir)
        report = format_report(result)
        self.assertIn("Health Score:", report)
        self.assertIn("/100", report)

    def test_format_report_includes_context_impact(self):
        project_dir = make_project(self.tmpdir, handoff=True)
        result = audit(project_dir)
        report = format_report(result)
        self.assertIn("Context Window Impact", report)
        self.assertIn("200k", report)

    def test_json_output_valid(self):
        project_dir = make_project(self.tmpdir, handoff=True)
        result = audit(project_dir)
        d = result.to_dict()
        # Should be JSON-serializable
        json_str = json.dumps(d)
        parsed = json.loads(json_str)
        self.assertEqual(parsed["score"], d["score"])


class TestCheckSkillsContent(unittest.TestCase):
    """Test skills content quality checks."""

    def setUp(self):
        self.tmpdir = Path(tempfile.mkdtemp())

    def tearDown(self):
        shutil.rmtree(self.tmpdir)

    def test_skill_missing_frontmatter(self):
        project_dir = make_project(self.tmpdir)
        skills_dir = project_dir / ".claude" / "skills"
        skills_dir.mkdir()
        (skills_dir / "test.md").write_text("Just raw text\n")
        r = AuditResult()
        check_skills_content(project_dir, r)
        fm_warnings = [i for i in r.issues if "frontmatter" in i["message"]]
        self.assertTrue(len(fm_warnings) > 0)

    def test_skill_with_frontmatter_ok(self):
        project_dir = make_project(self.tmpdir)
        skills_dir = project_dir / ".claude" / "skills"
        skills_dir.mkdir()
        (skills_dir / "test.md").write_text("---\ndescription: Test skill\n---\nDo the thing.\n")
        r = AuditResult()
        check_skills_content(project_dir, r)
        fm_warnings = [i for i in r.issues if "frontmatter" in i["message"]]
        self.assertEqual(len(fm_warnings), 0)

    def test_oversized_skill_warning(self):
        project_dir = make_project(self.tmpdir)
        skills_dir = project_dir / ".claude" / "skills"
        skills_dir.mkdir()
        (skills_dir / "big.md").write_text("---\ndescription: Big\n---\n" + "line\n" * 60)
        r = AuditResult()
        check_skills_content(project_dir, r)
        size_warnings = [i for i in r.issues if "lines" in i["message"]]
        self.assertTrue(len(size_warnings) > 0)


class TestCheckCommandsContent(unittest.TestCase):
    """Test commands content quality checks."""

    def setUp(self):
        self.tmpdir = Path(tempfile.mkdtemp())

    def tearDown(self):
        shutil.rmtree(self.tmpdir)

    def test_command_missing_frontmatter(self):
        project_dir = make_project(self.tmpdir, commands={
            "bad-cmd": "No frontmatter here\n"
        })
        r = AuditResult()
        check_commands_content(project_dir, r)
        fm_warnings = [i for i in r.issues if "frontmatter" in i["message"]]
        self.assertTrue(len(fm_warnings) > 0)

    def test_command_with_frontmatter_ok(self):
        project_dir = make_project(self.tmpdir, commands={
            "good-cmd": "---\ndescription: Good command\n---\nDo stuff.\n"
        })
        r = AuditResult()
        check_commands_content(project_dir, r)
        fm_warnings = [i for i in r.issues if "frontmatter" in i["message"]]
        self.assertEqual(len(fm_warnings), 0)


class TestApplyFixes(unittest.TestCase):
    """Test audit --fix auto-fixes."""

    def setUp(self):
        self.tmpdir = Path(tempfile.mkdtemp())

    def tearDown(self):
        shutil.rmtree(self.tmpdir)

    def test_fix_creates_missing_handoff(self):
        project_dir = make_project(self.tmpdir, handoff=False)
        result = audit(project_dir)
        actions = apply_fixes(project_dir, result)
        self.assertTrue(any("handoff" in a.lower() for a in actions))
        self.assertTrue((project_dir / ".claude" / "handoff.md").exists())

    def test_fix_adds_agent_frontmatter(self):
        project_dir = make_project(self.tmpdir, agents={
            "naked-agent": "This agent has no frontmatter.\n"
        })
        result = audit(project_dir)
        actions = apply_fixes(project_dir, result)
        self.assertTrue(any("frontmatter" in a and "agent" in a for a in actions))
        content = (project_dir / ".claude" / "agents" / "naked-agent.md").read_text()
        self.assertTrue(content.startswith("---"))

    def test_fix_repairs_invalid_settings_json(self):
        project_dir = make_project(self.tmpdir, settings="not json {{{")
        result = audit(project_dir)
        actions = apply_fixes(project_dir, result)
        self.assertTrue(any("settings.json" in a for a in actions))
        data = json.loads((project_dir / ".claude" / "settings.json").read_text())
        self.assertEqual(data, {})
        # Backup should exist
        self.assertTrue((project_dir / ".claude" / "settings.json.bak").exists())

    def test_fix_does_nothing_for_healthy_project(self):
        project_dir = make_project(
            self.tmpdir,
            agents={"good": "---\nname: good\n---\nGood agent.\n"},
            settings={"hooks": {}},
            handoff=True,
        )
        result = audit(project_dir)
        actions = apply_fixes(project_dir, result)
        self.assertEqual(len(actions), 0)


class TestCategoryScoring(unittest.TestCase):
    """Test weighted category scoring system."""

    def test_categories_in_to_dict(self):
        r = AuditResult()
        d = r.to_dict()
        self.assertIn("categories", d)
        self.assertEqual(d["categories"]["structure"], 30)
        self.assertEqual(d["categories"]["efficiency"], 30)
        self.assertEqual(d["categories"]["freshness"], 20)
        self.assertEqual(d["categories"]["practices"], 20)

    def test_category_deductions_capped(self):
        r = AuditResult()
        # Add more errors than the category budget allows
        for i in range(10):
            r.add_issue("error", f"freshness error {i}", category="freshness")
        d = r.to_dict()
        # Freshness budget is 20, so max deduction is 20
        self.assertEqual(d["categories"]["freshness"], 0)
        # Score should be 100 - 20 = 80 (not lower)
        self.assertEqual(d["score"], 80)

    def test_format_report_includes_categories(self):
        project_dir = make_project(self.tmpdir, handoff=True)
        result = audit(project_dir)
        report = format_report(result)
        self.assertIn("Structure:", report)
        self.assertIn("Efficiency:", report)
        self.assertIn("Freshness:", report)
        self.assertIn("Practices:", report)

    def setUp(self):
        self.tmpdir = Path(tempfile.mkdtemp())

    def tearDown(self):
        shutil.rmtree(self.tmpdir)


class TestRecommendations(unittest.TestCase):
    """Test audit --recommend mode."""

    def setUp(self):
        self.tmpdir = Path(tempfile.mkdtemp())

    def tearDown(self):
        shutil.rmtree(self.tmpdir)

    def test_recommends_missing_agents(self):
        project_dir = make_project(self.tmpdir, handoff=True)
        recs = generate_recommendations(project_dir)
        agent_recs = [r for r in recs if r["category"] == "agents"]
        self.assertTrue(len(agent_recs) > 0)

    def test_recommends_missing_claudeignore(self):
        project_dir = make_project(self.tmpdir, handoff=True)
        recs = generate_recommendations(project_dir)
        perf_recs = [r for r in recs if r["category"] == "performance"]
        self.assertTrue(len(perf_recs) > 0)

    def test_no_recommendations_for_complete_project(self):
        project_dir = make_project(
            self.tmpdir,
            agents={"architect": "---\nname: a\n---\n", "testing": "---\nname: t\n---\n",
                    "reviewer": "---\nname: r\n---\n", "debugger": "---\nname: d\n---\n",
                    "push": "---\nname: p\n---\n"},
            commands={"status": "---\ndescription: s\n---\n", "handoff": "---\ndescription: h\n---\n"},
            settings={"mcpServers": {"gh": {"command": "npx"}}},
            handoff=True,
        )
        # Create .claudeignore, skills, rules
        (project_dir / ".claudeignore").write_text("node_modules/\n")
        skills_dir = project_dir / ".claude" / "skills"
        skills_dir.mkdir()
        (skills_dir / "simplify.md").write_text("---\ndescription: s\n---\nSimplify.\n")
        rules_dir = project_dir / ".claude" / "rules"
        rules_dir.mkdir()
        (rules_dir / "frontend.md").write_text("---\nglobs: [\"*.ts\"]\n---\nRules.\n")
        # Add Commands section to CLAUDE.md
        (project_dir / "CLAUDE.md").write_text("# Project\n## Commands\nnpm run dev\n")

        recs = generate_recommendations(project_dir)
        self.assertEqual(len(recs), 0, f"Expected no recommendations, got: {recs}")

    def test_format_recommendations_output(self):
        recs = [{"category": "agents", "priority": "high", "message": "Missing agents", "action": "Add them"}]
        output = format_recommendations(recs)
        self.assertIn("Missing agents", output)
        self.assertIn("Add them", output)

    def test_format_empty_recommendations(self):
        output = format_recommendations([])
        self.assertIn("comprehensive", output.lower())


class TestCheckDiscoverability(unittest.TestCase):
    """Test CLAUDE.md discoverability checks."""

    def setUp(self):
        self.tmpdir = Path(tempfile.mkdtemp())

    def tearDown(self):
        shutil.rmtree(self.tmpdir)

    def test_directory_structure_flagged(self):
        project_dir = make_project(self.tmpdir, claude_md_content="# Project\n\n## Directory Structure\nsrc/\n  app/\n  lib/\n")
        r = AuditResult()
        check_discoverability(project_dir, r)
        warnings = [i for i in r.issues if "directory structure" in i["message"].lower() or "discoverable" in i.get("fix", "").lower()]
        self.assertTrue(len(warnings) > 0)

    def test_file_tree_ascii_flagged(self):
        project_dir = make_project(self.tmpdir, claude_md_content="# Project\n\n```\n├── src/\n│   ├── app/\n│   └── lib/\n```\n")
        r = AuditResult()
        check_discoverability(project_dir, r)
        warnings = [i for i in r.issues if "discoverable" in i.get("fix", "").lower() or "tree" in i.get("message", "").lower()]
        self.assertTrue(len(warnings) > 0)

    def test_clean_claude_md_no_warning(self):
        project_dir = make_project(self.tmpdir, claude_md_content="# Project\n\n## Commands\nnpm run dev\nnpm run test\n")
        r = AuditResult()
        check_discoverability(project_dir, r)
        warnings = [i for i in r.issues if "discoverable" in i.get("fix", "").lower()]
        self.assertEqual(len(warnings), 0)


class TestCheckContextPercentage(unittest.TestCase):
    """Test context window percentage checks."""

    def setUp(self):
        self.tmpdir = Path(tempfile.mkdtemp())

    def tearDown(self):
        shutil.rmtree(self.tmpdir)

    def test_many_mcp_servers_warns(self):
        servers = {f"server{i}": {"command": "npx", "args": []} for i in range(7)}
        project_dir = make_project(self.tmpdir, settings={"mcpServers": servers})
        r = AuditResult()
        r.total_tokens = 2000
        check_context_percentage(project_dir, r)
        # 7 servers × 3000 + 2000 = 23000 tokens = 11.5% > 10%
        issues = [i for i in r.issues if "context" in i["message"].lower()]
        self.assertTrue(len(issues) > 0)

    def test_minimal_config_no_warning(self):
        project_dir = make_project(self.tmpdir, settings={"mcpServers": {"gh": {"command": "npx"}}})
        r = AuditResult()
        r.total_tokens = 500
        check_context_percentage(project_dir, r)
        # 1 server × 3000 + 500 = 3500 tokens = 1.75%
        issues = [i for i in r.issues if "context" in i["message"].lower()]
        self.assertEqual(len(issues), 0)


if __name__ == "__main__":
    unittest.main()
