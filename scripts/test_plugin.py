"""Tests for plugin distribution manifests (.claude-plugin/).

Validate the plugin.json manifest and marketplace.json catalog against the
Claude Code plugin spec so distribution can't silently break.
"""
import json
import re
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
PLUGIN_DIR = REPO_ROOT / ".claude-plugin"


def _load(name):
    return json.loads((PLUGIN_DIR / name).read_text())


def _scaffold_version():
    text = (REPO_ROOT / "scripts" / "scaffold.py").read_text()
    return re.search(r'VERSION\s*=\s*"([^"]+)"', text).group(1)


class TestPluginManifest(unittest.TestCase):
    def setUp(self):
        self.pj = _load("plugin.json")

    def test_required_name(self):
        # `name` is the only required field in plugin.json.
        self.assertEqual(self.pj["name"], "claude-launchpad")

    def test_author_is_object(self):
        # Current spec uses an author object ({name, email?, url?}), not a string.
        self.assertIsInstance(self.pj["author"], dict)
        self.assertIn("name", self.pj["author"])

    def test_no_legacy_nonstandard_fields(self):
        # Fields from the old/custom schema must be gone (tolerated but misleading).
        for legacy in ("scope", "requiredTools", "minClaudeCodeVersion", "entry",
                       "scripts", "triggers", "domains", "compliance", "stacks", "presets"):
            self.assertNotIn(legacy, self.pj, f"legacy field still present: {legacy}")

    def test_version_matches_scaffold(self):
        # Keep the published plugin version in lockstep with the scaffolder.
        self.assertEqual(self.pj["version"], _scaffold_version())

    def test_root_skill_present_for_single_skill_plugin(self):
        # A root SKILL.md (no skills/ dir, no skills field) auto-loads as the plugin's skill.
        self.assertTrue((REPO_ROOT / "SKILL.md").exists())
        self.assertNotIn("skills", self.pj)

    def test_no_root_plugin_json_duplicate(self):
        # The canonical manifest lives in .claude-plugin/; no divergent root copy.
        self.assertFalse((REPO_ROOT / "plugin.json").exists())


class TestMarketplaceCatalog(unittest.TestCase):
    def setUp(self):
        self.mp = _load("marketplace.json")

    def test_required_top_level(self):
        self.assertIn("name", self.mp)
        self.assertIn("owner", self.mp)
        self.assertIn("name", self.mp["owner"])
        self.assertIsInstance(self.mp["plugins"], list)
        self.assertTrue(self.mp["plugins"])

    def test_lists_launchpad_plugin(self):
        names = [p["name"] for p in self.mp["plugins"]]
        self.assertIn("claude-launchpad", names)

    def test_plugin_entries_have_name_and_source(self):
        for p in self.mp["plugins"]:
            self.assertIn("name", p)
            self.assertIn("source", p)

    def test_root_source_resolves_to_plugin_dir(self):
        # source "./" means the repo root is the plugin; its manifest must exist there.
        entry = next(p for p in self.mp["plugins"] if p["name"] == "claude-launchpad")
        self.assertEqual(entry["source"], "./")
        self.assertTrue((PLUGIN_DIR / "plugin.json").exists())


if __name__ == "__main__":
    unittest.main()
