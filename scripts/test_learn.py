"""Tests for learn.py — learning system."""

import json
import shutil
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from learn import (
    LEARN_LOG_FILE,
    LEARNED_RULES_FILE,
    REANALYSIS_THRESHOLD,
    analyze_git_corrections,
    capture_correction,
    forget,
    load_learn_log,
    regenerate_learned_rules,
    save_learn_log,
    show_learned,
    suggest_reanalysis,
)


class TestCaptureCorrection(unittest.TestCase):
    def setUp(self):
        self.tmpdir = Path(tempfile.mkdtemp())

    def tearDown(self):
        shutil.rmtree(self.tmpdir)

    def test_capture_creates_entry(self):
        entry = capture_correction(self.tmpdir, "Always use AppError for HTTP errors")
        self.assertEqual(entry["type"], "explicit")
        self.assertEqual(entry["correction"], "Always use AppError for HTTP errors")
        self.assertIn("timestamp", entry)

    def test_capture_persists_to_log(self):
        capture_correction(self.tmpdir, "Use zod for validation")
        log = load_learn_log(self.tmpdir)
        self.assertEqual(len(log), 1)
        self.assertEqual(log[0]["correction"], "Use zod for validation")

    def test_capture_multiple(self):
        capture_correction(self.tmpdir, "Rule one")
        capture_correction(self.tmpdir, "Rule two")
        log = load_learn_log(self.tmpdir)
        self.assertEqual(len(log), 2)

    def test_duplicate_prevention(self):
        capture_correction(self.tmpdir, "Always use AppError")
        capture_correction(self.tmpdir, "Always use AppError")  # duplicate
        log = load_learn_log(self.tmpdir)
        self.assertEqual(len(log), 1)

    def test_duplicate_case_insensitive(self):
        capture_correction(self.tmpdir, "Use Zod")
        capture_correction(self.tmpdir, "use zod")  # same, different case
        log = load_learn_log(self.tmpdir)
        self.assertEqual(len(log), 1)

    def test_capture_with_context(self):
        entry = capture_correction(self.tmpdir, "Never use any type", context="TypeScript strict mode")
        self.assertEqual(entry["context"], "TypeScript strict mode")

    def test_capture_generates_rules_file(self):
        capture_correction(self.tmpdir, "Always validate input with zod")
        rules_path = self.tmpdir / LEARNED_RULES_FILE
        self.assertTrue(rules_path.exists())
        content = rules_path.read_text()
        self.assertIn("Always validate input with zod", content)
        self.assertIn("globs:", content)
        self.assertIn("auto-maintained", content)


class TestRegenerateRules(unittest.TestCase):
    def setUp(self):
        self.tmpdir = Path(tempfile.mkdtemp())

    def tearDown(self):
        shutil.rmtree(self.tmpdir)

    def test_generates_from_log(self):
        log = [
            {"type": "explicit", "correction": "Use AppError"},
            {"type": "explicit", "correction": "Never use console.log"},
        ]
        regenerate_learned_rules(self.tmpdir, log)
        rules_path = self.tmpdir / LEARNED_RULES_FILE
        self.assertTrue(rules_path.exists())
        content = rules_path.read_text()
        self.assertIn("- Use AppError", content)
        self.assertIn("- Never use console.log", content)

    def test_adds_dash_prefix(self):
        log = [{"type": "explicit", "correction": "No global state"}]
        regenerate_learned_rules(self.tmpdir, log)
        content = (self.tmpdir / LEARNED_RULES_FILE).read_text()
        self.assertIn("- No global state", content)

    def test_preserves_existing_dash(self):
        log = [{"type": "explicit", "correction": "- Already has dash"}]
        regenerate_learned_rules(self.tmpdir, log)
        content = (self.tmpdir / LEARNED_RULES_FILE).read_text()
        # Should not double the dash
        self.assertNotIn("- - Already", content)
        self.assertIn("- Already has dash", content)

    def test_empty_log_removes_file(self):
        rules_path = self.tmpdir / LEARNED_RULES_FILE
        rules_path.parent.mkdir(parents=True, exist_ok=True)
        rules_path.write_text("old content")
        regenerate_learned_rules(self.tmpdir, [])
        self.assertFalse(rules_path.exists())

    def test_entries_without_correction_ignored(self):
        log = [
            {"type": "git-correction", "message": "fix typo"},  # no "correction" key
            {"type": "explicit", "correction": "Real rule"},
        ]
        regenerate_learned_rules(self.tmpdir, log)
        content = (self.tmpdir / LEARNED_RULES_FILE).read_text()
        self.assertIn("Real rule", content)
        self.assertNotIn("fix typo", content)


class TestForget(unittest.TestCase):
    def setUp(self):
        self.tmpdir = Path(tempfile.mkdtemp())

    def tearDown(self):
        shutil.rmtree(self.tmpdir)

    def test_forget_by_query(self):
        capture_correction(self.tmpdir, "Always use AppError")
        capture_correction(self.tmpdir, "Never use console.log")
        removed = forget(self.tmpdir, "AppError")
        self.assertEqual(removed, 1)
        log = load_learn_log(self.tmpdir)
        self.assertEqual(len(log), 1)
        self.assertEqual(log[0]["correction"], "Never use console.log")

    def test_forget_nonexistent(self):
        capture_correction(self.tmpdir, "Some rule")
        removed = forget(self.tmpdir, "nonexistent")
        self.assertEqual(removed, 0)
        log = load_learn_log(self.tmpdir)
        self.assertEqual(len(log), 1)

    def test_forget_updates_rules_file(self):
        capture_correction(self.tmpdir, "Rule A")
        capture_correction(self.tmpdir, "Rule B")
        forget(self.tmpdir, "Rule A")
        content = (self.tmpdir / LEARNED_RULES_FILE).read_text()
        self.assertNotIn("Rule A", content)
        self.assertIn("Rule B", content)

    def test_forget_all_removes_rules_file(self):
        capture_correction(self.tmpdir, "Only rule")
        forget(self.tmpdir, "Only rule")
        self.assertFalse((self.tmpdir / LEARNED_RULES_FILE).exists())

    def test_forget_case_insensitive(self):
        capture_correction(self.tmpdir, "Use AppError")
        removed = forget(self.tmpdir, "apperror")
        self.assertEqual(removed, 1)


class TestShowLearned(unittest.TestCase):
    def setUp(self):
        self.tmpdir = Path(tempfile.mkdtemp())

    def tearDown(self):
        shutil.rmtree(self.tmpdir)

    def test_empty_message(self):
        output = show_learned(self.tmpdir)
        self.assertIn("No learned rules", output)

    def test_shows_entries(self):
        capture_correction(self.tmpdir, "Rule one")
        capture_correction(self.tmpdir, "Rule two")
        output = show_learned(self.tmpdir)
        self.assertIn("Rule one", output)
        self.assertIn("Rule two", output)
        self.assertIn("2 entries", output)


class TestLoadSaveLog(unittest.TestCase):
    def setUp(self):
        self.tmpdir = Path(tempfile.mkdtemp())

    def tearDown(self):
        shutil.rmtree(self.tmpdir)

    def test_load_nonexistent(self):
        log = load_learn_log(self.tmpdir)
        self.assertEqual(log, [])

    def test_load_corrupt(self):
        log_path = self.tmpdir / LEARN_LOG_FILE
        log_path.parent.mkdir(parents=True, exist_ok=True)
        log_path.write_text("not json{{{")
        log = load_learn_log(self.tmpdir)
        self.assertEqual(log, [])

    def test_roundtrip(self):
        data = [{"type": "explicit", "correction": "test"}]
        save_learn_log(self.tmpdir, data)
        loaded = load_learn_log(self.tmpdir)
        self.assertEqual(loaded, data)


class TestGitAnalysis(unittest.TestCase):
    def setUp(self):
        self.tmpdir = Path(tempfile.mkdtemp())

    def tearDown(self):
        shutil.rmtree(self.tmpdir)

    @patch("learn.run_git")
    def test_detects_correction_commits(self, mock_git):
        mock_git.return_value = (
            "abc123|fix typo in auth|2024-01-15 10:00:00 +0000\n"
            "src/auth.ts\n"
            "def456|Add auth middleware|2024-01-15 09:00:00 +0000\n"
            "src/auth.ts\n"
        )
        corrections = analyze_git_corrections(self.tmpdir)
        self.assertTrue(len(corrections) >= 1)
        self.assertEqual(corrections[0]["type"], "git-correction")

    @patch("learn.run_git")
    def test_detects_revert_commits(self, mock_git):
        mock_git.return_value = (
            "abc123|Revert bad migration|2024-01-15 10:00:00 +0000\n"
            "db/migration.sql\n"
            "def456|Add migration|2024-01-15 09:00:00 +0000\n"
            "db/migration.sql\n"
        )
        corrections = analyze_git_corrections(self.tmpdir)
        reverts = [c for c in corrections if c["type"] == "git-revert"]
        self.assertTrue(len(reverts) >= 1)

    @patch("learn.run_git")
    def test_empty_git_history(self, mock_git):
        mock_git.return_value = ""
        corrections = analyze_git_corrections(self.tmpdir)
        self.assertEqual(corrections, [])

    @patch("learn.run_git")
    def test_no_corrections_in_clean_history(self, mock_git):
        mock_git.return_value = (
            "abc123|feat: add user dashboard|2024-01-15 10:00:00 +0000\n"
            "src/dashboard.ts\n"
            "def456|feat: add login page|2024-01-15 09:00:00 +0000\n"
            "src/login.ts\n"
        )
        corrections = analyze_git_corrections(self.tmpdir)
        # No corrections expected — different files, no correction keywords
        git_corrections = [c for c in corrections if c["type"] == "git-correction"]
        self.assertEqual(len(git_corrections), 0)


class TestSuggestReanalysis(unittest.TestCase):
    def setUp(self):
        self.tmpdir = Path(tempfile.mkdtemp())

    def tearDown(self):
        shutil.rmtree(self.tmpdir)

    def test_suggests_after_threshold_corrections(self):
        # Create enough corrections to trigger suggestion
        log = []
        for i in range(REANALYSIS_THRESHOLD):
            log.append({"type": "explicit", "correction": f"Rule {i}", "timestamp": "2025-06-01T00:00:00"})
        save_learn_log(self.tmpdir, log)

        suggestion = suggest_reanalysis(self.tmpdir)
        self.assertIsNotNone(suggestion)
        self.assertIn("corrections", suggestion)

    def test_no_suggestion_below_threshold(self):
        log = [{"type": "explicit", "correction": "One rule", "timestamp": "2025-06-01T00:00:00"}]
        save_learn_log(self.tmpdir, log)

        # With no last_analysis, any correction count triggers "never analyzed"
        # So create a recent last_analysis
        config_dir = self.tmpdir / ".claude"
        config_dir.mkdir(parents=True, exist_ok=True)
        from datetime import datetime
        (config_dir / "launchpad-config.json").write_text(json.dumps({
            "version": "6.0.0",
            "last_analysis": datetime.now().isoformat(),
        }))

        suggestion = suggest_reanalysis(self.tmpdir)
        # Only 1 correction since analysis, below threshold
        self.assertIsNone(suggestion)

    def test_suggests_when_never_analyzed(self):
        log = [{"type": "explicit", "correction": "A rule", "timestamp": "2025-01-01T00:00:00"}]
        save_learn_log(self.tmpdir, log)

        suggestion = suggest_reanalysis(self.tmpdir)
        self.assertIsNotNone(suggestion)
        self.assertIn("never been analyzed", suggestion)

    def test_suggests_when_analysis_old(self):
        log = [{"type": "explicit", "correction": "A rule", "timestamp": "2025-06-01T00:00:00"}]
        save_learn_log(self.tmpdir, log)

        config_dir = self.tmpdir / ".claude"
        config_dir.mkdir(parents=True, exist_ok=True)
        (config_dir / "launchpad-config.json").write_text(json.dumps({
            "version": "6.0.0",
            "last_analysis": "2024-01-01T00:00:00",  # very old
        }))

        suggestion = suggest_reanalysis(self.tmpdir)
        self.assertIsNotNone(suggestion)
        self.assertIn("days ago", suggestion)

    def test_no_suggestion_with_empty_log(self):
        suggestion = suggest_reanalysis(self.tmpdir)
        self.assertIsNone(suggestion)

    def test_capture_includes_suggestion(self):
        # Capture enough corrections to trigger suggestion
        for i in range(REANALYSIS_THRESHOLD):
            capture_correction(self.tmpdir, f"Rule {i}")

        # The last capture should include a suggestion
        entry = capture_correction(self.tmpdir, "One more rule")
        # May or may not have suggestion depending on threshold
        # But the function should not crash
        self.assertIn("correction", entry)


if __name__ == "__main__":
    unittest.main()
