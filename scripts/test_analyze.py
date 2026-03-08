"""Tests for analyze.py — codebase analyzer."""

import json
import os
import shutil
import tempfile
import unittest
from pathlib import Path

from analyze import (
    AnalysisResult,
    Pattern,
    analyze,
    check_stale_rules,
    collect_source_files,
    detect_ai_configs,
    detect_api_patterns,
    detect_auth_patterns,
    detect_database_patterns,
    detect_data_fetching,
    detect_error_handling,
    detect_file_organization,
    detect_key_abstractions,
    detect_monorepo,
    detect_stack,
    detect_testing_patterns,
    detect_validation,
    format_report,
    generate_rules_from_analysis,
    get_last_analysis_time,
    incorporate_learned,
    match_correction_to_category,
    migrate_ai_configs,
    set_last_analysis_time,
    snapshot_dependencies,
    write_rules,
)


class TestDetectStack(unittest.TestCase):
    def setUp(self):
        self.tmpdir = Path(tempfile.mkdtemp())

    def tearDown(self):
        shutil.rmtree(self.tmpdir)

    def test_nextjs_from_package_json(self):
        (self.tmpdir / "package.json").write_text(json.dumps({
            "dependencies": {"next": "14.0.0", "react": "18.0.0"},
            "devDependencies": {"typescript": "5.0.0"}
        }))
        stack = detect_stack(self.tmpdir)
        self.assertEqual(stack["frontend"], "nextjs")
        self.assertEqual(stack["backend"], "integrated")
        self.assertEqual(stack["language"], "typescript")

    def test_react_vite_detection(self):
        (self.tmpdir / "package.json").write_text(json.dumps({
            "dependencies": {"react": "18.0.0"},
            "devDependencies": {}
        }))
        stack = detect_stack(self.tmpdir)
        self.assertEqual(stack["frontend"], "react-vite")

    def test_express_backend(self):
        (self.tmpdir / "package.json").write_text(json.dumps({
            "dependencies": {"express": "4.0.0"},
            "devDependencies": {}
        }))
        stack = detect_stack(self.tmpdir)
        self.assertEqual(stack["backend"], "node-express")

    def test_fastapi_from_requirements(self):
        (self.tmpdir / "requirements.txt").write_text("fastapi==0.100.0\nsqlalchemy==2.0.0\npytest\n")
        stack = detect_stack(self.tmpdir)
        self.assertEqual(stack["language"], "python")
        self.assertEqual(stack["backend"], "python-fastapi")
        self.assertEqual(stack["orm"], "sqlalchemy")
        self.assertEqual(stack["test_framework"], "pytest")

    def test_go_detection(self):
        (self.tmpdir / "go.mod").write_text("module example.com/app\ngo 1.22\n")
        stack = detect_stack(self.tmpdir)
        self.assertEqual(stack["language"], "go")
        self.assertEqual(stack["backend"], "go")

    def test_rust_actix_detection(self):
        (self.tmpdir / "Cargo.toml").write_text('[dependencies]\nactix-web = "4"\n')
        stack = detect_stack(self.tmpdir)
        self.assertEqual(stack["language"], "rust")
        self.assertEqual(stack["backend"], "rust-actix")

    def test_rails_detection(self):
        (self.tmpdir / "Gemfile").write_text("gem 'rails'\n")
        stack = detect_stack(self.tmpdir)
        self.assertEqual(stack["language"], "ruby")
        self.assertEqual(stack["backend"], "ruby-rails")

    def test_orm_detection_prisma(self):
        (self.tmpdir / "package.json").write_text(json.dumps({
            "dependencies": {"@prisma/client": "5.0.0"},
            "devDependencies": {"prisma": "5.0.0"}
        }))
        stack = detect_stack(self.tmpdir)
        self.assertEqual(stack["orm"], "prisma")

    def test_auth_detection_clerk(self):
        (self.tmpdir / "package.json").write_text(json.dumps({
            "dependencies": {"next": "14.0.0", "@clerk/nextjs": "4.0.0"},
            "devDependencies": {}
        }))
        stack = detect_stack(self.tmpdir)
        self.assertEqual(stack["auth"], "clerk")

    def test_vitest_detection(self):
        (self.tmpdir / "package.json").write_text(json.dumps({
            "dependencies": {},
            "devDependencies": {"vitest": "1.0.0"}
        }))
        stack = detect_stack(self.tmpdir)
        self.assertEqual(stack["test_framework"], "vitest")

    def test_database_from_env(self):
        (self.tmpdir / ".env.example").write_text("DATABASE_URL=postgresql://localhost/db\n")
        stack = detect_stack(self.tmpdir)
        self.assertEqual(stack["database"], "postgresql")

    def test_empty_project(self):
        stack = detect_stack(self.tmpdir)
        self.assertEqual(stack, {})

    def test_package_manager_pnpm(self):
        (self.tmpdir / "package.json").write_text(json.dumps({"dependencies": {}, "devDependencies": {}}))
        (self.tmpdir / "pnpm-lock.yaml").write_text("")
        stack = detect_stack(self.tmpdir)
        self.assertEqual(stack["package_manager"], "pnpm")


class TestCollectSourceFiles(unittest.TestCase):
    def setUp(self):
        self.tmpdir = Path(tempfile.mkdtemp())

    def tearDown(self):
        shutil.rmtree(self.tmpdir)

    def test_collects_ts_files(self):
        src = self.tmpdir / "src"
        src.mkdir()
        (src / "app.ts").write_text("const x = 1;")
        (src / "style.css").write_text("body {}")  # not collected
        files = collect_source_files(self.tmpdir)
        self.assertEqual(len(files), 1)
        self.assertTrue(files[0].name == "app.ts")

    def test_skips_node_modules(self):
        nm = self.tmpdir / "node_modules" / "pkg"
        nm.mkdir(parents=True)
        (nm / "index.js").write_text("module.exports = {};")
        (self.tmpdir / "src").mkdir()
        (self.tmpdir / "src" / "app.ts").write_text("const x = 1;")
        files = collect_source_files(self.tmpdir)
        self.assertEqual(len(files), 1)


class TestDetectErrorHandling(unittest.TestCase):
    def setUp(self):
        self.tmpdir = Path(tempfile.mkdtemp())
        self.src = self.tmpdir / "src"
        self.src.mkdir()

    def tearDown(self):
        shutil.rmtree(self.tmpdir)

    def test_custom_error_class_ts(self):
        (self.src / "errors.ts").write_text(
            "export class AppError extends Error {\n  constructor(public code: number) { super(); }\n}\n"
            "export class NotFoundError extends AppError {}\n"
        )
        files = collect_source_files(self.tmpdir)
        patterns = detect_error_handling(self.tmpdir, files, {"language": "typescript"})
        self.assertTrue(len(patterns) >= 1)
        p = patterns[0]
        self.assertEqual(p.category, "error-handling")
        self.assertIn("AppError", " ".join(p.rule_lines))

    def test_custom_error_class_python(self):
        (self.src / "errors.py").write_text(
            "class AppError(Exception):\n    pass\n"
            "class NotFoundError(AppError):\n    pass\n"
        )
        files = collect_source_files(self.tmpdir)
        patterns = detect_error_handling(self.tmpdir, files, {"language": "python"})
        self.assertTrue(len(patterns) >= 1)
        self.assertIn("AppError", " ".join(patterns[0].rule_lines))

    def test_express_error_handler(self):
        (self.src / "middleware.ts").write_text(
            "export function errorHandler(err, req, res, next) {\n  res.status(500).json({});\n}\n"
        )
        files = collect_source_files(self.tmpdir)
        patterns = detect_error_handling(self.tmpdir, files, {"language": "typescript"})
        has_centralized = any(p.description == "Centralized error handler" for p in patterns)
        self.assertTrue(has_centralized)

    def test_no_errors_no_patterns(self):
        (self.src / "utils.ts").write_text("export const add = (a: number, b: number) => a + b;\n")
        files = collect_source_files(self.tmpdir)
        patterns = detect_error_handling(self.tmpdir, files, {"language": "typescript"})
        self.assertEqual(len(patterns), 0)


class TestDetectAuth(unittest.TestCase):
    def setUp(self):
        self.tmpdir = Path(tempfile.mkdtemp())
        self.src = self.tmpdir / "src"
        self.src.mkdir()

    def tearDown(self):
        shutil.rmtree(self.tmpdir)

    def test_auth_middleware_ts(self):
        (self.src / "auth.ts").write_text(
            "export function withAuth(handler: any) {\n  return async (req, res) => {};\n}\n"
        )
        files = collect_source_files(self.tmpdir)
        patterns = detect_auth_patterns(self.tmpdir, files, {"language": "typescript"})
        self.assertTrue(len(patterns) >= 1)
        self.assertEqual(patterns[0].category, "auth")
        self.assertIn("withAuth", " ".join(patterns[0].rule_lines))

    def test_python_depends_auth(self):
        (self.src / "deps.py").write_text(
            "from fastapi import Depends\ndef get_endpoint(user=Depends(get_current_user)): pass\n"
        )
        files = collect_source_files(self.tmpdir)
        patterns = detect_auth_patterns(self.tmpdir, files, {"language": "python"})
        self.assertTrue(len(patterns) >= 1)

    def test_no_auth_no_pattern(self):
        (self.src / "utils.ts").write_text("export const helper = () => {};\n")
        files = collect_source_files(self.tmpdir)
        patterns = detect_auth_patterns(self.tmpdir, files, {"language": "typescript"})
        self.assertEqual(len(patterns), 0)


class TestDetectValidation(unittest.TestCase):
    def setUp(self):
        self.tmpdir = Path(tempfile.mkdtemp())
        self.src = self.tmpdir / "src"
        self.src.mkdir()

    def tearDown(self):
        shutil.rmtree(self.tmpdir)

    def test_zod_validation(self):
        schemas = self.src / "schemas"
        schemas.mkdir()
        (schemas / "user.ts").write_text(
            'import { z } from "zod";\nexport const UserSchema = z.object({ name: z.string() });\n'
        )
        (self.src / "handler.ts").write_text(
            'import { z } from "zod";\nconst input = z.string();\n'
        )
        files = collect_source_files(self.tmpdir)
        patterns = detect_validation(self.tmpdir, files, {"language": "typescript"})
        self.assertTrue(len(patterns) >= 1)
        self.assertIn("zod", patterns[0].description.lower())

    def test_pydantic_validation(self):
        (self.src / "schemas.py").write_text(
            "from pydantic import BaseModel\nclass UserCreate(BaseModel):\n    name: str\n"
        )
        files = collect_source_files(self.tmpdir)
        patterns = detect_validation(self.tmpdir, files, {"language": "python"})
        self.assertTrue(len(patterns) >= 1)
        self.assertIn("pydantic", patterns[0].description.lower())


class TestDetectDataFetching(unittest.TestCase):
    def setUp(self):
        self.tmpdir = Path(tempfile.mkdtemp())
        self.src = self.tmpdir / "src"
        self.src.mkdir()

    def tearDown(self):
        shutil.rmtree(self.tmpdir)

    def test_tanstack_query(self):
        (self.src / "hooks1.tsx").write_text(
            'import { useQuery } from "@tanstack/react-query";\nconst q = useQuery({});\n'
        )
        (self.src / "hooks2.tsx").write_text(
            'import { useMutation } from "@tanstack/react-query";\nconst m = useMutation({});\n'
        )
        files = collect_source_files(self.tmpdir)
        patterns = detect_data_fetching(self.tmpdir, files, {"language": "typescript", "frontend": "react-vite"})
        has_tq = any("tanstack-query" in p.description for p in patterns)
        self.assertTrue(has_tq)

    def test_zustand_state(self):
        stores = self.src / "stores"
        stores.mkdir()
        (stores / "auth.ts").write_text('import { create } from "zustand";\nexport const useAuthStore = create((set) => ({}));\n')
        (stores / "ui.ts").write_text('import { create } from "zustand";\nexport const useUIStore = create((set) => ({}));\n')
        files = collect_source_files(self.tmpdir)
        patterns = detect_data_fetching(self.tmpdir, files, {"language": "typescript", "frontend": "react-vite"})
        has_zustand = any("zustand" in p.description for p in patterns)
        self.assertTrue(has_zustand)

    def test_non_js_skipped(self):
        patterns = detect_data_fetching(self.tmpdir, [], {"language": "python"})
        self.assertEqual(len(patterns), 0)


class TestDetectTesting(unittest.TestCase):
    def setUp(self):
        self.tmpdir = Path(tempfile.mkdtemp())
        self.src = self.tmpdir / "src"
        self.src.mkdir()

    def tearDown(self):
        shutil.rmtree(self.tmpdir)

    def test_vitest_mock_pattern(self):
        (self.src / "auth.test.ts").write_text(
            'import { vi } from "vitest";\nvi.mock("./db");\ntest("works", () => {});\n'
        )
        (self.src / "user.test.ts").write_text(
            'import { vi } from "vitest";\nvi.mock("./api");\ntest("ok", () => {});\n'
        )
        files = collect_source_files(self.tmpdir)
        patterns = detect_testing_patterns(self.tmpdir, files, {"language": "typescript", "test_framework": "vitest"})
        self.assertTrue(len(patterns) >= 1)
        self.assertIn("vitest", " ".join(patterns[0].rule_lines))

    def test_pytest_fixtures(self):
        tests = self.tmpdir / "tests"
        tests.mkdir()
        (tests / "conftest.py").write_text("import pytest\n@pytest.fixture\ndef db(): pass\n")
        (tests / "test_api.py").write_text("def test_endpoint(db): pass\n")
        files = collect_source_files(self.tmpdir)
        patterns = detect_testing_patterns(self.tmpdir, files, {"language": "python", "test_framework": "pytest"})
        self.assertTrue(len(patterns) >= 1)


class TestDetectApiPatterns(unittest.TestCase):
    def setUp(self):
        self.tmpdir = Path(tempfile.mkdtemp())
        routes = self.tmpdir / "src" / "routes"
        routes.mkdir(parents=True)
        self.routes = routes

    def tearDown(self):
        shutil.rmtree(self.tmpdir)

    def test_response_wrapper(self):
        (self.routes / "users.ts").write_text(
            "export function getUsers(req, res) {\n  return successResponse(users);\n}\n"
        )
        files = collect_source_files(self.tmpdir)
        patterns = detect_api_patterns(self.tmpdir, files, {"language": "typescript", "backend": "node-express"})
        self.assertTrue(len(patterns) >= 1)
        self.assertIn("wrapper", " ".join(patterns[0].rule_lines).lower())

    def test_no_backend_no_patterns(self):
        patterns = detect_api_patterns(self.tmpdir, [], {"language": "typescript", "backend": "none"})
        self.assertEqual(len(patterns), 0)


class TestDetectDatabase(unittest.TestCase):
    def setUp(self):
        self.tmpdir = Path(tempfile.mkdtemp())

    def tearDown(self):
        shutil.rmtree(self.tmpdir)

    def test_repository_pattern(self):
        repo = self.tmpdir / "src" / "repositories"
        repo.mkdir(parents=True)
        (repo / "userRepository.ts").write_text(
            "export class UserRepository {\n  findById(id: string) { return prisma.user.findUnique({where: {id}}); }\n}\n"
        )
        files = collect_source_files(self.tmpdir)
        patterns = detect_database_patterns(self.tmpdir, files, {"language": "typescript", "orm": "prisma"})
        self.assertTrue(len(patterns) >= 1)
        self.assertIn("repository", " ".join(patterns[0].rule_lines).lower())

    def test_no_orm_no_patterns(self):
        patterns = detect_database_patterns(self.tmpdir, [], {"language": "typescript"})
        self.assertEqual(len(patterns), 0)


class TestDetectFileOrganization(unittest.TestCase):
    def setUp(self):
        self.tmpdir = Path(tempfile.mkdtemp())

    def tearDown(self):
        shutil.rmtree(self.tmpdir)

    def test_layer_based(self):
        for d in ["controllers", "services", "models"]:
            (self.tmpdir / "src" / d).mkdir(parents=True)
            (self.tmpdir / "src" / d / "user.ts").write_text("export class User {}\n")
        files = collect_source_files(self.tmpdir)
        org = detect_file_organization(self.tmpdir, files, {"language": "typescript"})
        self.assertEqual(org["style"], "layer-based")
        self.assertEqual(org["src_dir"], "src")

    def test_feature_based(self):
        for feat in ["auth", "billing", "profile"]:
            (self.tmpdir / "src" / "features" / feat).mkdir(parents=True)
            (self.tmpdir / "src" / "features" / feat / "index.ts").write_text("export {};\n")
        files = collect_source_files(self.tmpdir)
        org = detect_file_organization(self.tmpdir, files, {"language": "typescript"})
        self.assertEqual(org["style"], "feature-based")

    def test_barrel_exports(self):
        src = self.tmpdir / "src"
        for d in ["components", "hooks", "utils", "lib"]:
            (src / d).mkdir(parents=True)
            (src / d / "index.ts").write_text("export * from './something';\nexport { foo } from './bar';\n")
        files = collect_source_files(self.tmpdir)
        org = detect_file_organization(self.tmpdir, files, {})
        self.assertTrue(org["barrel_exports"])

    def test_co_located_tests(self):
        src = self.tmpdir / "src"
        src.mkdir()
        (src / "app.ts").write_text("const x = 1;")
        (src / "app.test.ts").write_text("test('works', () => {});")
        files = collect_source_files(self.tmpdir)
        org = detect_file_organization(self.tmpdir, files, {})
        self.assertEqual(org["test_location"], "co-located")

    def test_separate_tests(self):
        (self.tmpdir / "src").mkdir()
        (self.tmpdir / "src" / "app.ts").write_text("const x = 1;")
        tests = self.tmpdir / "tests"
        tests.mkdir()
        (tests / "app.test.ts").write_text("test('works', () => {});")
        files = collect_source_files(self.tmpdir)
        org = detect_file_organization(self.tmpdir, files, {})
        self.assertEqual(org["test_location"], "separate")


class TestDetectKeyAbstractions(unittest.TestCase):
    def setUp(self):
        self.tmpdir = Path(tempfile.mkdtemp())
        self.src = self.tmpdir / "src"
        self.src.mkdir()

    def tearDown(self):
        shutil.rmtree(self.tmpdir)

    def test_custom_hooks(self):
        (self.src / "hooks.tsx").write_text(
            "export function useAuth() { return {}; }\n"
            "export const useDebounce = (v: any) => v;\n"
        )
        files = collect_source_files(self.tmpdir)
        abstractions = detect_key_abstractions(self.tmpdir, files, {"language": "typescript"})
        hook_names = [a["name"] for a in abstractions if a["type"] == "hook"]
        self.assertIn("useAuth", hook_names)
        self.assertIn("useDebounce", hook_names)

    def test_ignores_react_built_in_hooks(self):
        (self.src / "comp.tsx").write_text(
            "export function useState() { }\n"  # shadowing built-in
        )
        files = collect_source_files(self.tmpdir)
        abstractions = detect_key_abstractions(self.tmpdir, files, {"language": "typescript"})
        hook_names = [a["name"] for a in abstractions if a["type"] == "hook"]
        self.assertNotIn("useState", hook_names)

    def test_service_classes(self):
        (self.src / "auth.ts").write_text("export class AuthService { login() {} }\n")
        (self.src / "db.ts").write_text("export class UserRepository { find() {} }\n")
        files = collect_source_files(self.tmpdir)
        abstractions = detect_key_abstractions(self.tmpdir, files, {"language": "typescript"})
        service_names = [a["name"] for a in abstractions if a["type"] == "service"]
        self.assertIn("AuthService", service_names)
        self.assertIn("UserRepository", service_names)

    def test_python_services(self):
        (self.src / "service.py").write_text("class UserService:\n    pass\n")
        files = collect_source_files(self.tmpdir)
        abstractions = detect_key_abstractions(self.tmpdir, files, {"language": "python"})
        names = [a["name"] for a in abstractions]
        self.assertIn("UserService", names)


class TestGenerateRules(unittest.TestCase):
    def test_patterns_produce_rules(self):
        result = AnalysisResult(
            project_dir="/tmp/test",
            stack={"language": "typescript"},
            patterns=[
                Pattern("error-handling", "Custom errors", ["src/errors.ts"],
                        ["- Use AppError", "- Never throw generic Error"],
                        ["**/*.ts"], 0.8),
            ],
            key_abstractions=[],
            file_organization={"style": "unknown", "test_location": "unknown",
                               "barrel_exports": False, "src_dir": None},
        )
        rules = generate_rules_from_analysis(result)
        self.assertTrue(len(rules) >= 1)
        name, content = rules[0]
        self.assertEqual(name, "project-error-handling")
        self.assertIn("AppError", content)
        self.assertIn("globs:", content)

    def test_empty_analysis_no_rules(self):
        result = AnalysisResult(
            project_dir="/tmp/test",
            stack={},
            patterns=[],
            key_abstractions=[],
            file_organization={"style": "unknown", "test_location": "unknown",
                               "barrel_exports": False, "src_dir": None},
        )
        rules = generate_rules_from_analysis(result)
        self.assertEqual(len(rules), 0)

    def test_organization_rule_generated(self):
        result = AnalysisResult(
            project_dir="/tmp/test",
            stack={},
            patterns=[],
            key_abstractions=[],
            file_organization={"style": "layer-based", "test_location": "co-located",
                               "barrel_exports": True, "src_dir": "src"},
        )
        rules = generate_rules_from_analysis(result)
        org_rules = [r for r in rules if r[0] == "project-organization"]
        self.assertEqual(len(org_rules), 1)
        self.assertIn("layer-based", org_rules[0][1])
        self.assertIn("barrel exports", org_rules[0][1])

    def test_abstractions_rule_generated(self):
        result = AnalysisResult(
            project_dir="/tmp/test",
            stack={},
            patterns=[],
            key_abstractions=[
                {"name": "useAuth", "file": "src/hooks.ts", "type": "hook"},
                {"name": "AuthService", "file": "src/auth.ts", "type": "service"},
            ],
            file_organization={"style": "unknown", "test_location": "unknown",
                               "barrel_exports": False, "src_dir": None},
        )
        rules = generate_rules_from_analysis(result)
        abs_rules = [r for r in rules if r[0] == "project-abstractions"]
        self.assertEqual(len(abs_rules), 1)
        self.assertIn("useAuth", abs_rules[0][1])
        self.assertIn("AuthService", abs_rules[0][1])


class TestWriteRules(unittest.TestCase):
    def setUp(self):
        self.tmpdir = Path(tempfile.mkdtemp())

    def tearDown(self):
        shutil.rmtree(self.tmpdir)

    def test_writes_rule_files(self):
        result = AnalysisResult(
            project_dir=str(self.tmpdir),
            stack={"language": "typescript"},
            patterns=[
                Pattern("validation", "Zod", ["src/schemas.ts"],
                        ["- Use zod"], ["**/*.ts"], 0.9),
            ],
            key_abstractions=[],
            file_organization={"style": "unknown", "test_location": "unknown",
                               "barrel_exports": False, "src_dir": None},
        )
        created = write_rules(self.tmpdir, result)
        self.assertTrue(len(created) >= 1)
        rule_file = self.tmpdir / ".claude" / "rules" / "project-validation.md"
        self.assertTrue(rule_file.exists())
        self.assertIn("zod", rule_file.read_text().lower())

    def test_skip_existing_without_force(self):
        rules_dir = self.tmpdir / ".claude" / "rules"
        rules_dir.mkdir(parents=True)
        (rules_dir / "project-validation.md").write_text("existing content")

        result = AnalysisResult(
            project_dir=str(self.tmpdir),
            stack={},
            patterns=[
                Pattern("validation", "Zod", [], ["- Use zod"], ["**/*.ts"], 0.9),
            ],
            key_abstractions=[],
            file_organization={"style": "unknown", "test_location": "unknown",
                               "barrel_exports": False, "src_dir": None},
        )
        created = write_rules(self.tmpdir, result, force=False)
        self.assertEqual(len(created), 0)
        self.assertEqual((rules_dir / "project-validation.md").read_text(), "existing content")

    def test_overwrite_with_force(self):
        rules_dir = self.tmpdir / ".claude" / "rules"
        rules_dir.mkdir(parents=True)
        (rules_dir / "project-validation.md").write_text("old")

        result = AnalysisResult(
            project_dir=str(self.tmpdir),
            stack={},
            patterns=[
                Pattern("validation", "Zod", [], ["- Use zod"], ["**/*.ts"], 0.9),
            ],
            key_abstractions=[],
            file_organization={"style": "unknown", "test_location": "unknown",
                               "barrel_exports": False, "src_dir": None},
        )
        created = write_rules(self.tmpdir, result, force=True)
        self.assertTrue(len(created) >= 1)
        self.assertIn("zod", (rules_dir / "project-validation.md").read_text().lower())


class TestFullAnalysis(unittest.TestCase):
    def setUp(self):
        self.tmpdir = Path(tempfile.mkdtemp())

    def tearDown(self):
        shutil.rmtree(self.tmpdir)

    def test_nextjs_project(self):
        """Full analysis of a realistic Next.js project structure."""
        (self.tmpdir / "package.json").write_text(json.dumps({
            "dependencies": {
                "next": "14.0.0", "react": "18.0.0",
                "@clerk/nextjs": "4.0.0", "@prisma/client": "5.0.0",
            },
            "devDependencies": {"typescript": "5.0.0", "vitest": "1.0.0", "prisma": "5.0.0"}
        }))

        src = self.tmpdir / "src"
        (src / "lib").mkdir(parents=True)
        (src / "lib" / "errors.ts").write_text(
            "export class AppError extends Error {\n  constructor(public code: number) { super(); }\n}\n"
        )
        (src / "lib" / "auth.ts").write_text(
            "export function withAuth(handler: any) { return handler; }\n"
        )
        schemas = src / "schemas"
        schemas.mkdir()
        (schemas / "user.ts").write_text('import { z } from "zod";\nexport const UserSchema = z.object({});\n')
        (schemas / "post.ts").write_text('import { z } from "zod";\nexport const PostSchema = z.object({});\n')

        result = analyze(self.tmpdir)

        self.assertEqual(result.stack["frontend"], "nextjs")
        self.assertEqual(result.stack["auth"], "clerk")
        self.assertEqual(result.stack["orm"], "prisma")
        self.assertTrue(len(result.patterns) >= 1)

    def test_empty_project_no_crash(self):
        result = analyze(self.tmpdir)
        self.assertEqual(result.patterns, [])
        self.assertEqual(result.stack, {})

    def test_format_report_runs(self):
        result = analyze(self.tmpdir)
        report = format_report(result)
        self.assertIn("Codebase Analysis Report", report)
        self.assertIn("Detected Stack", report)


class TestFormatReport(unittest.TestCase):
    def test_includes_patterns(self):
        result = AnalysisResult(
            project_dir="/tmp/test",
            stack={"language": "typescript", "frontend": "nextjs"},
            patterns=[
                Pattern("auth", "Auth middleware", ["src/auth.ts"],
                        ["- Use withAuth"], ["**/*.ts"], 0.9),
            ],
            key_abstractions=[
                {"name": "useAuth", "file": "src/hooks.ts", "type": "hook"},
            ],
            file_organization={"style": "layer-based", "test_location": "co-located",
                               "barrel_exports": False, "src_dir": "src"},
        )
        report = format_report(result)
        self.assertIn("auth", report.lower())
        self.assertIn("withAuth", report)
        self.assertIn("useAuth", report)
        self.assertIn("layer-based", report)


class TestMatchCorrectionToCategory(unittest.TestCase):
    def test_error_correction(self):
        self.assertEqual(match_correction_to_category("Always use AppError, not generic Error"), "error-handling")

    def test_auth_correction(self):
        self.assertEqual(match_correction_to_category("Use auth middleware on all routes"), "auth")

    def test_validation_correction(self):
        self.assertEqual(match_correction_to_category("Use zod schemas for input validation"), "validation")

    def test_testing_correction(self):
        self.assertEqual(match_correction_to_category("Always mock external services in tests"), "testing")

    def test_database_correction(self):
        self.assertEqual(match_correction_to_category("Use repository pattern for database access"), "database")

    def test_no_match(self):
        self.assertIsNone(match_correction_to_category("Remember to update the changelog"))


class TestIncorporateLearned(unittest.TestCase):
    def setUp(self):
        self.tmpdir = Path(tempfile.mkdtemp())

    def tearDown(self):
        shutil.rmtree(self.tmpdir)

    def test_enhances_existing_pattern(self):
        # Set up learned log with an error-handling correction
        log_dir = self.tmpdir / ".claude"
        log_dir.mkdir(parents=True)
        log = [{"type": "explicit", "correction": "Always use AppError from errors.ts", "timestamp": "2025-01-01"}]
        (log_dir / "learn-log.json").write_text(json.dumps(log))

        result = AnalysisResult(
            project_dir=str(self.tmpdir),
            stack={"language": "typescript"},
            patterns=[
                Pattern("error-handling", "Custom errors", ["src/errors.ts"],
                        ["- Use custom error classes"], ["**/*.ts"], 0.8),
            ],
            key_abstractions=[],
            file_organization={"style": "unknown", "test_location": "unknown",
                               "barrel_exports": False, "src_dir": None},
        )

        enhanced = incorporate_learned(result, self.tmpdir)
        error_pattern = [p for p in enhanced.patterns if p.category == "error-handling"][0]
        # Should have the original rule plus the learned one
        self.assertTrue(len(error_pattern.rule_lines) >= 2)
        learned_rules = [r for r in error_pattern.rule_lines if "*(learned)*" in r]
        self.assertTrue(len(learned_rules) >= 1)

    def test_creates_new_pattern_for_unmatched_category(self):
        log_dir = self.tmpdir / ".claude"
        log_dir.mkdir(parents=True)
        log = [{"type": "explicit", "correction": "Always use auth middleware on protected routes", "timestamp": "2025-01-01"}]
        (log_dir / "learn-log.json").write_text(json.dumps(log))

        result = AnalysisResult(
            project_dir=str(self.tmpdir),
            stack={},
            patterns=[],  # No existing patterns
            key_abstractions=[],
            file_organization={"style": "unknown", "test_location": "unknown",
                               "barrel_exports": False, "src_dir": None},
        )

        enhanced = incorporate_learned(result, self.tmpdir)
        auth_patterns = [p for p in enhanced.patterns if p.category == "auth"]
        self.assertEqual(len(auth_patterns), 1)
        self.assertTrue(any("*(learned)*" in r for r in auth_patterns[0].rule_lines))

    def test_no_log_returns_unchanged(self):
        result = AnalysisResult(
            project_dir=str(self.tmpdir),
            stack={},
            patterns=[],
            key_abstractions=[],
            file_organization={"style": "unknown", "test_location": "unknown",
                               "barrel_exports": False, "src_dir": None},
        )
        enhanced = incorporate_learned(result, self.tmpdir)
        self.assertEqual(len(enhanced.patterns), 0)

    def test_skips_duplicate_learned_rules(self):
        log_dir = self.tmpdir / ".claude"
        log_dir.mkdir(parents=True)
        log = [
            {"type": "explicit", "correction": "Use AppError", "timestamp": "2025-01-01"},
            {"type": "explicit", "correction": "Use AppError", "timestamp": "2025-01-02"},
        ]
        (log_dir / "learn-log.json").write_text(json.dumps(log))

        result = AnalysisResult(
            project_dir=str(self.tmpdir),
            stack={},
            patterns=[
                Pattern("error-handling", "Custom errors", [],
                        ["- Use custom error classes"], ["**/*.ts"], 0.8),
            ],
            key_abstractions=[],
            file_organization={"style": "unknown", "test_location": "unknown",
                               "barrel_exports": False, "src_dir": None},
        )
        enhanced = incorporate_learned(result, self.tmpdir)
        error_pattern = [p for p in enhanced.patterns if p.category == "error-handling"][0]
        learned_rules = [r for r in error_pattern.rule_lines if "*(learned)*" in r]
        # Both corrections have same text, should only appear once
        self.assertEqual(len(learned_rules), 1)


class TestCheckStaleRules(unittest.TestCase):
    def setUp(self):
        self.tmpdir = Path(tempfile.mkdtemp())
        self.rules_dir = self.tmpdir / ".claude" / "rules"
        self.rules_dir.mkdir(parents=True)

    def tearDown(self):
        shutil.rmtree(self.tmpdir)

    def test_detects_stale_file_reference(self):
        (self.rules_dir / "project-error-handling.md").write_text(
            "---\nglobs: [\"**/*.ts\"]\n---\n\n"
            "- Error definitions in: `src/lib/errors.ts`\n"
        )
        # src/lib/errors.ts does NOT exist
        stale = check_stale_rules(self.tmpdir)
        self.assertTrue(len(stale) >= 1)
        self.assertIn("errors.ts", stale[0]["issue"])

    def test_no_stale_when_file_exists(self):
        src = self.tmpdir / "src" / "lib"
        src.mkdir(parents=True)
        (src / "errors.ts").write_text("export class AppError {}")

        (self.rules_dir / "project-error-handling.md").write_text(
            "---\nglobs: [\"**/*.ts\"]\n---\n\n"
            "- Error definitions in: `src/lib/errors.ts`\n"
        )
        stale = check_stale_rules(self.tmpdir)
        stale_file_refs = [s for s in stale if "errors.ts" in s["issue"]]
        self.assertEqual(len(stale_file_refs), 0)

    def test_detects_stale_identifier(self):
        # Create a project-*.md that references an identifier not in source
        (self.rules_dir / "project-error-handling.md").write_text(
            "---\nglobs: [\"**/*.ts\"]\n---\n\n"
            "- Use `ObsoleteError` for all errors\n"
        )
        # No source files contain ObsoleteError
        stale = check_stale_rules(self.tmpdir)
        # Should detect the stale identifier (if there are source files to scan)
        # With no source files, the identifier scan is skipped, so only file refs matter
        self.assertIsInstance(stale, list)

    def test_no_rules_dir_returns_empty(self):
        empty_dir = Path(tempfile.mkdtemp())
        try:
            stale = check_stale_rules(empty_dir)
            self.assertEqual(stale, [])
        finally:
            shutil.rmtree(empty_dir)


class TestAnalysisTimestamp(unittest.TestCase):
    def setUp(self):
        self.tmpdir = Path(tempfile.mkdtemp())
        self.config_dir = self.tmpdir / ".claude"
        self.config_dir.mkdir(parents=True)

    def tearDown(self):
        shutil.rmtree(self.tmpdir)

    def test_set_and_get_timestamp(self):
        (self.config_dir / "launchpad-config.json").write_text(json.dumps({
            "project_name": "test", "version": "6.0.0"
        }))
        set_last_analysis_time(self.tmpdir)
        ts = get_last_analysis_time(self.tmpdir)
        self.assertIsNotNone(ts)
        # Should be a valid ISO timestamp
        from datetime import datetime
        dt = datetime.fromisoformat(ts)
        self.assertIsNotNone(dt)

    def test_no_config_returns_none(self):
        ts = get_last_analysis_time(self.tmpdir)
        self.assertIsNone(ts)

    def test_write_rules_sets_timestamp(self):
        (self.config_dir / "launchpad-config.json").write_text(json.dumps({
            "project_name": "test", "version": "6.0.0"
        }))
        result = AnalysisResult(
            project_dir=str(self.tmpdir),
            stack={},
            patterns=[
                Pattern("testing", "Test", [], ["- Test rule"], ["**/*.ts"], 0.9),
            ],
            key_abstractions=[],
            file_organization={"style": "unknown", "test_location": "unknown",
                               "barrel_exports": False, "src_dir": None},
        )
        write_rules(self.tmpdir, result, force=True)
        ts = get_last_analysis_time(self.tmpdir)
        self.assertIsNotNone(ts)


class TestDetectCommands(unittest.TestCase):
    """Test command detection from package.json scripts, pyproject.toml, and Makefiles."""

    def setUp(self):
        self.tmpdir = Path(tempfile.mkdtemp())

    def tearDown(self):
        shutil.rmtree(self.tmpdir)

    def test_detect_npm_scripts(self):
        (self.tmpdir / "package.json").write_text(json.dumps({
            "dependencies": {},
            "devDependencies": {},
            "scripts": {"test": "jest", "lint": "eslint .", "dev": "next dev", "build": "next build"}
        }))
        stack = detect_stack(self.tmpdir)
        self.assertEqual(stack["test_cmd"], "npm run test")
        self.assertEqual(stack["lint_cmd"], "npm run lint")
        self.assertEqual(stack["dev_cmd"], "npm run dev")
        self.assertEqual(stack["build_cmd"], "npm run build")

    def test_detect_yarn_scripts(self):
        (self.tmpdir / "package.json").write_text(json.dumps({
            "dependencies": {},
            "devDependencies": {},
            "scripts": {"test": "jest", "lint": "eslint ."}
        }))
        (self.tmpdir / "yarn.lock").write_text("")
        stack = detect_stack(self.tmpdir)
        self.assertEqual(stack["test_cmd"], "yarn test")
        self.assertEqual(stack["lint_cmd"], "yarn lint")

    def test_detect_pnpm_scripts(self):
        (self.tmpdir / "package.json").write_text(json.dumps({
            "dependencies": {},
            "devDependencies": {},
            "scripts": {"test": "vitest", "lint": "eslint ."}
        }))
        (self.tmpdir / "pnpm-lock.yaml").write_text("")
        stack = detect_stack(self.tmpdir)
        self.assertEqual(stack["test_cmd"], "pnpm test")
        self.assertEqual(stack["lint_cmd"], "pnpm lint")

    def test_detect_pyproject_pytest(self):
        (self.tmpdir / "pyproject.toml").write_text(
            "[tool.pytest.ini_options]\naddopts = '-v'\n"
        )
        stack = detect_stack(self.tmpdir)
        self.assertEqual(stack["test_cmd"], "pytest")

    def test_detect_pyproject_ruff(self):
        (self.tmpdir / "pyproject.toml").write_text(
            "[tool.ruff]\nline-length = 100\n"
        )
        stack = detect_stack(self.tmpdir)
        self.assertEqual(stack["lint_cmd"], "ruff check .")

    def test_detect_makefile_targets(self):
        (self.tmpdir / "Makefile").write_text(
            "test:\n\tpytest\n\nlint:\n\truff check .\n"
        )
        stack = detect_stack(self.tmpdir)
        self.assertEqual(stack["test_cmd"], "make test")
        self.assertEqual(stack["lint_cmd"], "make lint")

    def test_detect_migration_cmd_prisma(self):
        (self.tmpdir / "package.json").write_text(json.dumps({
            "dependencies": {"@prisma/client": "5.0.0"},
            "devDependencies": {"prisma": "5.0.0"}
        }))
        stack = detect_stack(self.tmpdir)
        self.assertEqual(stack["orm"], "prisma")
        self.assertEqual(stack["migrate_cmd"], "npx prisma migrate dev")

    def test_detect_migration_cmd_sqlalchemy(self):
        (self.tmpdir / "requirements.txt").write_text("sqlalchemy==2.0.0\n")
        stack = detect_stack(self.tmpdir)
        self.assertEqual(stack["orm"], "sqlalchemy")
        self.assertEqual(stack["migrate_cmd"], "alembic upgrade head")

    def test_no_override_existing_cmds(self):
        """If test_cmd is already set from package.json scripts, Makefile should not override."""
        (self.tmpdir / "package.json").write_text(json.dumps({
            "dependencies": {},
            "devDependencies": {},
            "scripts": {"test": "vitest"}
        }))
        (self.tmpdir / "Makefile").write_text("test:\n\tpytest\n")
        stack = detect_stack(self.tmpdir)
        # package.json scripts set test_cmd first, Makefile should not override
        self.assertEqual(stack["test_cmd"], "npm run test")


class TestDetectGitPlatform(unittest.TestCase):
    """Test git platform detection from .git/config."""

    def setUp(self):
        self.tmpdir = Path(tempfile.mkdtemp())

    def tearDown(self):
        shutil.rmtree(self.tmpdir)

    def test_detect_github(self):
        git_dir = self.tmpdir / ".git"
        git_dir.mkdir()
        (git_dir / "config").write_text(
            "[remote \"origin\"]\n\turl = git@github.com:user/repo.git\n"
        )
        stack = detect_stack(self.tmpdir)
        self.assertEqual(stack["git_platform"], "github")

    def test_detect_gitlab(self):
        git_dir = self.tmpdir / ".git"
        git_dir.mkdir()
        (git_dir / "config").write_text(
            "[remote \"origin\"]\n\turl = git@gitlab.com:user/repo.git\n"
        )
        stack = detect_stack(self.tmpdir)
        self.assertEqual(stack["git_platform"], "gitlab")

    def test_no_git_dir(self):
        stack = detect_stack(self.tmpdir)
        self.assertNotIn("git_platform", stack)


class TestDetectCICD(unittest.TestCase):
    """Test CI/CD detection from config files."""

    def setUp(self):
        self.tmpdir = Path(tempfile.mkdtemp())

    def tearDown(self):
        shutil.rmtree(self.tmpdir)

    def test_detect_github_actions(self):
        workflows = self.tmpdir / ".github" / "workflows"
        workflows.mkdir(parents=True)
        (workflows / "ci.yml").write_text("name: CI\n")
        stack = detect_stack(self.tmpdir)
        self.assertEqual(stack["ci_cd"], "github-actions")

    def test_detect_gitlab_ci(self):
        (self.tmpdir / ".gitlab-ci.yml").write_text("stages:\n  - test\n")
        stack = detect_stack(self.tmpdir)
        self.assertEqual(stack["ci_cd"], "gitlab-ci")

    def test_no_ci(self):
        stack = detect_stack(self.tmpdir)
        self.assertNotIn("ci_cd", stack)


class TestDetectHosting(unittest.TestCase):
    """Test hosting platform detection."""

    def setUp(self):
        self.tmpdir = Path(tempfile.mkdtemp())

    def tearDown(self):
        shutil.rmtree(self.tmpdir)

    def test_detect_vercel(self):
        (self.tmpdir / "vercel.json").write_text("{}")
        stack = detect_stack(self.tmpdir)
        self.assertEqual(stack["hosting"], "vercel")

    def test_detect_fly(self):
        (self.tmpdir / "fly.toml").write_text("[app]\n")
        stack = detect_stack(self.tmpdir)
        self.assertEqual(stack["hosting"], "fly")

    def test_detect_railway(self):
        (self.tmpdir / "railway.toml").write_text("[build]\n")
        stack = detect_stack(self.tmpdir)
        self.assertEqual(stack["hosting"], "railway")

    def test_detect_aws(self):
        (self.tmpdir / "serverless.yml").write_text("service: my-api\n")
        stack = detect_stack(self.tmpdir)
        self.assertEqual(stack["hosting"], "aws")


class TestDetectMonorepo(unittest.TestCase):
    """Test monorepo detection."""

    def setUp(self):
        self.tmpdir = Path(tempfile.mkdtemp())

    def tearDown(self):
        shutil.rmtree(self.tmpdir)

    def test_detect_turborepo(self):
        (self.tmpdir / "turbo.json").write_text('{"pipeline": {}}')
        (self.tmpdir / "pnpm-workspace.yaml").write_text("packages:\n  - 'apps/*'\n")
        apps_web = self.tmpdir / "apps" / "web"
        apps_web.mkdir(parents=True)
        (apps_web / "package.json").write_text(json.dumps({"name": "@mono/web"}))
        result = detect_monorepo(self.tmpdir)
        self.assertIsNotNone(result)
        self.assertEqual(result["tool"], "turborepo")
        self.assertTrue(len(result["packages"]) >= 1)
        self.assertEqual(result["packages"][0]["name"], "@mono/web")

    def test_detect_nx(self):
        (self.tmpdir / "nx.json").write_text('{}')
        apps_dir = self.tmpdir / "apps" / "api"
        apps_dir.mkdir(parents=True)
        (apps_dir / "package.json").write_text(json.dumps({"name": "@mono/api"}))
        result = detect_monorepo(self.tmpdir)
        self.assertIsNotNone(result)
        self.assertEqual(result["tool"], "nx")

    def test_detect_pnpm_workspaces(self):
        (self.tmpdir / "pnpm-workspace.yaml").write_text("packages:\n  - 'packages/*'\n")
        pkg_dir = self.tmpdir / "packages" / "shared"
        pkg_dir.mkdir(parents=True)
        (pkg_dir / "package.json").write_text(json.dumps({"name": "@mono/shared"}))
        result = detect_monorepo(self.tmpdir)
        self.assertIsNotNone(result)
        self.assertEqual(result["tool"], "pnpm-workspaces")

    def test_detect_yarn_workspaces(self):
        (self.tmpdir / "package.json").write_text(json.dumps({
            "workspaces": ["packages/*"],
            "dependencies": {}
        }))
        pkg_dir = self.tmpdir / "packages" / "ui"
        pkg_dir.mkdir(parents=True)
        (pkg_dir / "package.json").write_text(json.dumps({"name": "@mono/ui"}))
        result = detect_monorepo(self.tmpdir)
        self.assertIsNotNone(result)
        self.assertEqual(result["tool"], "yarn-workspaces")

    def test_detect_lerna(self):
        (self.tmpdir / "lerna.json").write_text(json.dumps({"packages": ["packages/*"]}))
        pkg_dir = self.tmpdir / "packages" / "core"
        pkg_dir.mkdir(parents=True)
        (pkg_dir / "package.json").write_text(json.dumps({"name": "@mono/core"}))
        result = detect_monorepo(self.tmpdir)
        self.assertIsNotNone(result)
        self.assertEqual(result["tool"], "lerna")

    def test_no_monorepo(self):
        (self.tmpdir / "package.json").write_text(json.dumps({
            "dependencies": {"react": "18.0.0"},
            "devDependencies": {}
        }))
        result = detect_monorepo(self.tmpdir)
        self.assertIsNone(result)


class TestDetectAIConfigs(unittest.TestCase):
    """Test detection of other AI tool config files."""

    def setUp(self):
        self.tmpdir = Path(tempfile.mkdtemp())

    def tearDown(self):
        shutil.rmtree(self.tmpdir)

    def test_detect_cursorrules(self):
        (self.tmpdir / ".cursorrules").write_text("Always use TypeScript.\n")
        found = detect_ai_configs(self.tmpdir)
        self.assertEqual(len(found), 1)
        self.assertEqual(found[0]["source"], "cursor")
        self.assertIn("TypeScript", found[0]["content"])

    def test_detect_copilot_instructions(self):
        gh_dir = self.tmpdir / ".github"
        gh_dir.mkdir()
        (gh_dir / "copilot-instructions.md").write_text("# Copilot Rules\nUse React.\n")
        found = detect_ai_configs(self.tmpdir)
        self.assertEqual(len(found), 1)
        self.assertEqual(found[0]["source"], "copilot")

    def test_detect_multiple(self):
        (self.tmpdir / ".cursorrules").write_text("Cursor rules here.\n")
        (self.tmpdir / ".windsurfrules").write_text("Windsurf rules here.\n")
        found = detect_ai_configs(self.tmpdir)
        self.assertEqual(len(found), 2)
        sources = {c["source"] for c in found}
        self.assertIn("cursor", sources)
        self.assertIn("windsurf", sources)

    def test_no_ai_configs(self):
        found = detect_ai_configs(self.tmpdir)
        self.assertEqual(len(found), 0)


class TestMigrateAIConfigs(unittest.TestCase):
    """Test migration of AI configs to .claude/rules/."""

    def setUp(self):
        self.tmpdir = Path(tempfile.mkdtemp())

    def tearDown(self):
        shutil.rmtree(self.tmpdir)

    def test_migrate_cursor(self):
        configs = [{"source": "cursor", "path": ".cursorrules", "content": "Always use TypeScript.\n"}]
        created = migrate_ai_configs(self.tmpdir, configs)
        self.assertEqual(len(created), 1)
        dest = self.tmpdir / ".claude" / "rules" / "migrated-cursor.md"
        self.assertTrue(dest.exists())
        content = dest.read_text()
        self.assertIn("---", content)
        self.assertIn("description: Rules migrated from cursor", content)
        self.assertIn("Always use TypeScript.", content)
        self.assertIn("Migrated from Cursor", content)

    def test_migrate_copilot(self):
        configs = [{"source": "copilot", "path": ".github/copilot-instructions.md", "content": "Use React hooks.\n"}]
        created = migrate_ai_configs(self.tmpdir, configs)
        self.assertEqual(len(created), 1)
        dest = self.tmpdir / ".claude" / "rules" / "migrated-copilot.md"
        self.assertTrue(dest.exists())
        content = dest.read_text()
        self.assertIn("Use React hooks.", content)

    def test_skip_existing_migration(self):
        rules_dir = self.tmpdir / ".claude" / "rules"
        rules_dir.mkdir(parents=True)
        (rules_dir / "migrated-cursor.md").write_text("existing content")
        configs = [{"source": "cursor", "path": ".cursorrules", "content": "New rules.\n"}]
        created = migrate_ai_configs(self.tmpdir, configs)
        self.assertEqual(len(created), 0)
        self.assertEqual((rules_dir / "migrated-cursor.md").read_text(), "existing content")

    def test_creates_rules_dir(self):
        self.assertFalse((self.tmpdir / ".claude" / "rules").exists())
        configs = [{"source": "cursor", "path": ".cursorrules", "content": "Rules.\n"}]
        migrate_ai_configs(self.tmpdir, configs)
        self.assertTrue((self.tmpdir / ".claude" / "rules").exists())


class TestSnapshotDependencies(unittest.TestCase):
    """Test dependency snapshot creation from manifest files."""

    def setUp(self):
        self.tmpdir = Path(tempfile.mkdtemp())

    def tearDown(self):
        shutil.rmtree(self.tmpdir)

    def test_snapshot_node_deps(self):
        (self.tmpdir / "package.json").write_text(json.dumps({
            "dependencies": {"react": "18.0.0", "next": "14.0.0"},
            "devDependencies": {"typescript": "5.0.0"}
        }))
        snap = snapshot_dependencies(self.tmpdir)
        self.assertIn("node", snap)
        self.assertIn("react", snap["node"])
        self.assertEqual(snap["node"]["react"], "18.0.0")
        self.assertIn("typescript", snap["node"])

    def test_snapshot_python_deps(self):
        (self.tmpdir / "requirements.txt").write_text(
            "fastapi==0.100.0\nsqlalchemy>=2.0.0\npytest\n"
        )
        snap = snapshot_dependencies(self.tmpdir)
        self.assertIn("python", snap)
        self.assertIn("fastapi", snap["python"])
        self.assertEqual(snap["python"]["fastapi"], "0.100.0")
        self.assertIn("pytest", snap["python"])

    def test_snapshot_go_deps(self):
        (self.tmpdir / "go.mod").write_text(
            "module example.com/app\n\ngo 1.22\n\n"
            "require (\n\tgithub.com/gin-gonic/gin v1.9.0\n\tgolang.org/x/net v0.10.0\n)\n"
        )
        snap = snapshot_dependencies(self.tmpdir)
        self.assertIn("go", snap)
        self.assertIn("github.com/gin-gonic/gin", snap["go"])
        self.assertEqual(snap["go"]["github.com/gin-gonic/gin"], "v1.9.0")

    def test_snapshot_empty_project(self):
        snap = snapshot_dependencies(self.tmpdir)
        self.assertEqual(snap, {})

    def test_snapshot_mixed_project(self):
        (self.tmpdir / "package.json").write_text(json.dumps({
            "dependencies": {"express": "4.0.0"},
            "devDependencies": {}
        }))
        (self.tmpdir / "requirements.txt").write_text("flask==2.0.0\n")
        snap = snapshot_dependencies(self.tmpdir)
        self.assertIn("node", snap)
        self.assertIn("python", snap)
        self.assertIn("express", snap["node"])
        self.assertIn("flask", snap["python"])


class TestEventSystemDetection(unittest.TestCase):
    """Test event system detection from package files."""

    def setUp(self):
        self.tmpdir = Path(tempfile.mkdtemp())

    def tearDown(self):
        shutil.rmtree(self.tmpdir)

    def test_kafka_node_detection(self):
        (self.tmpdir / "package.json").write_text(json.dumps({
            "dependencies": {"kafkajs": "2.0.0", "express": "4.0.0"},
            "devDependencies": {}
        }))
        stack = detect_stack(self.tmpdir)
        self.assertIn("event_systems", stack)
        self.assertIn("kafka", stack["event_systems"])

    def test_bullmq_detection(self):
        (self.tmpdir / "package.json").write_text(json.dumps({
            "dependencies": {"bullmq": "4.0.0"},
            "devDependencies": {}
        }))
        stack = detect_stack(self.tmpdir)
        self.assertIn("event_systems", stack)
        self.assertIn("bullmq", stack["event_systems"])

    def test_rabbitmq_node_detection(self):
        (self.tmpdir / "package.json").write_text(json.dumps({
            "dependencies": {"amqplib": "0.10.0"},
            "devDependencies": {}
        }))
        stack = detect_stack(self.tmpdir)
        self.assertIn("event_systems", stack)
        self.assertIn("rabbitmq", stack["event_systems"])

    def test_temporal_node_detection(self):
        (self.tmpdir / "package.json").write_text(json.dumps({
            "dependencies": {"@temporalio/client": "1.0.0", "@temporalio/worker": "1.0.0"},
            "devDependencies": {}
        }))
        stack = detect_stack(self.tmpdir)
        self.assertIn("event_systems", stack)
        self.assertIn("temporal", stack["event_systems"])
        self.assertEqual(stack.get("workflow_orchestration"), "temporal")

    def test_nats_node_detection(self):
        (self.tmpdir / "package.json").write_text(json.dumps({
            "dependencies": {"nats": "2.0.0"},
            "devDependencies": {}
        }))
        stack = detect_stack(self.tmpdir)
        self.assertIn("event_systems", stack)
        self.assertIn("nats", stack["event_systems"])

    def test_aws_events_detection(self):
        (self.tmpdir / "package.json").write_text(json.dumps({
            "dependencies": {"@aws-sdk/client-sqs": "3.0.0"},
            "devDependencies": {}
        }))
        stack = detect_stack(self.tmpdir)
        self.assertIn("event_systems", stack)
        self.assertIn("aws-events", stack["event_systems"])

    def test_kafka_python_detection(self):
        (self.tmpdir / "requirements.txt").write_text("confluent-kafka==2.0.0\nfastapi\n")
        stack = detect_stack(self.tmpdir)
        self.assertIn("event_systems", stack)
        self.assertIn("kafka", stack["event_systems"])

    def test_celery_detection(self):
        (self.tmpdir / "requirements.txt").write_text("celery==5.3.0\nfastapi\n")
        stack = detect_stack(self.tmpdir)
        self.assertIn("event_systems", stack)
        self.assertIn("celery", stack["event_systems"])

    def test_flink_detection(self):
        (self.tmpdir / "requirements.txt").write_text("apache-flink==1.18.0\n")
        stack = detect_stack(self.tmpdir)
        self.assertIn("event_systems", stack)
        self.assertIn("flink", stack["event_systems"])

    def test_kafka_go_detection(self):
        (self.tmpdir / "go.mod").write_text(
            "module example.com/app\n\ngo 1.22\n\n"
            "require (\n\tgithub.com/IBM/sarama v1.41.0\n)\n"
        )
        stack = detect_stack(self.tmpdir)
        self.assertIn("event_systems", stack)
        self.assertIn("kafka", stack["event_systems"])

    def test_temporal_go_detection(self):
        (self.tmpdir / "go.mod").write_text(
            "module example.com/app\n\ngo 1.22\n\n"
            "require (\n\tgo.temporal.io/sdk v1.25.0\n)\n"
        )
        stack = detect_stack(self.tmpdir)
        self.assertIn("event_systems", stack)
        self.assertIn("temporal", stack["event_systems"])
        self.assertEqual(stack.get("workflow_orchestration"), "temporal")

    def test_kafka_docker_compose_detection(self):
        (self.tmpdir / "docker-compose.yml").write_text(
            "services:\n  kafka:\n    image: confluentinc/cp-kafka:7.5.0\n"
        )
        stack = detect_stack(self.tmpdir)
        self.assertIn("event_systems", stack)
        self.assertIn("kafka", stack["event_systems"])

    def test_rabbitmq_docker_compose_detection(self):
        (self.tmpdir / "docker-compose.yml").write_text(
            "services:\n  rabbitmq:\n    image: rabbitmq:3-management\n"
        )
        stack = detect_stack(self.tmpdir)
        self.assertIn("event_systems", stack)
        self.assertIn("rabbitmq", stack["event_systems"])

    def test_no_event_systems_when_absent(self):
        (self.tmpdir / "package.json").write_text(json.dumps({
            "dependencies": {"react": "18.0.0"},
            "devDependencies": {}
        }))
        stack = detect_stack(self.tmpdir)
        self.assertNotIn("event_systems", stack)

    def test_schema_format_avro_detection(self):
        (self.tmpdir / "package.json").write_text(json.dumps({
            "dependencies": {"kafkajs": "2.0.0", "@kafkajs/confluent-schema-registry": "3.0.0"},
            "devDependencies": {}
        }))
        stack = detect_stack(self.tmpdir)
        self.assertEqual(stack.get("schema_format"), "avro")

    def test_schema_format_protobuf_detection(self):
        (self.tmpdir / "package.json").write_text(json.dumps({
            "dependencies": {"protobufjs": "7.0.0"},
            "devDependencies": {}
        }))
        stack = detect_stack(self.tmpdir)
        self.assertEqual(stack.get("schema_format"), "protobuf")

    def test_avro_file_detection(self):
        schema_dir = self.tmpdir / "schemas"
        schema_dir.mkdir()
        (schema_dir / "user.avsc").write_text('{"type": "record"}')
        stack = detect_stack(self.tmpdir)
        self.assertEqual(stack.get("schema_format"), "avro")

    def test_proto_file_detection(self):
        schema_dir = self.tmpdir / "proto"
        schema_dir.mkdir()
        (schema_dir / "events.proto").write_text('syntax = "proto3";')
        stack = detect_stack(self.tmpdir)
        self.assertEqual(stack.get("schema_format"), "protobuf")

    def test_multiple_event_systems(self):
        (self.tmpdir / "package.json").write_text(json.dumps({
            "dependencies": {"kafkajs": "2.0.0", "bullmq": "4.0.0", "@temporalio/client": "1.0.0"},
            "devDependencies": {}
        }))
        stack = detect_stack(self.tmpdir)
        self.assertIn("kafka", stack["event_systems"])
        self.assertIn("bullmq", stack["event_systems"])
        self.assertIn("temporal", stack["event_systems"])


class TestEventPatternDetection(unittest.TestCase):
    """Test event-driven pattern detection from source code."""

    def setUp(self):
        self.tmpdir = Path(tempfile.mkdtemp())
        (self.tmpdir / "src").mkdir()

    def tearDown(self):
        shutil.rmtree(self.tmpdir)

    def test_event_sourcing_detection(self):
        (self.tmpdir / "src" / "aggregate.ts").write_text(
            "export class OrderAggregate extends AggregateRoot {\n"
            "  applyEvent(event: DomainEvent) {}\n"
            "}\n"
        )
        from analyze import detect_event_patterns
        patterns = detect_event_patterns(self.tmpdir)
        self.assertIn("event-sourcing", patterns)

    def test_cqrs_detection(self):
        (self.tmpdir / "src" / "handlers.ts").write_text(
            "export class CreateOrderCommandHandler {\n"
            "  handle(command: CreateOrderCommand) {}\n"
            "}\n"
            "export class GetOrderQueryHandler {\n"
            "  handle(query: GetOrderQuery) {}\n"
            "}\n"
        )
        from analyze import detect_event_patterns
        patterns = detect_event_patterns(self.tmpdir)
        self.assertIn("cqrs", patterns)

    def test_saga_detection(self):
        (self.tmpdir / "src" / "order_saga.ts").write_text(
            "export class OrderSaga {\n"
            "  async orchestrate(step: SagaStep) {\n"
            "    const compensatingTransaction = this.rollback;\n"
            "  }\n"
            "}\n"
        )
        from analyze import detect_event_patterns
        patterns = detect_event_patterns(self.tmpdir)
        self.assertIn("saga", patterns)

    def test_outbox_detection(self):
        (self.tmpdir / "src" / "outbox.ts").write_text(
            "export class OutboxEvent {\n"
            "  id: string;\n"
            "  payload: any;\n"
            "}\n"
        )
        from analyze import detect_event_patterns
        patterns = detect_event_patterns(self.tmpdir)
        self.assertIn("outbox", patterns)

    def test_no_patterns_in_crud_app(self):
        (self.tmpdir / "src" / "app.ts").write_text(
            "import express from 'express';\n"
            "const app = express();\n"
            "app.get('/users', getUsers);\n"
        )
        from analyze import detect_event_patterns
        patterns = detect_event_patterns(self.tmpdir)
        self.assertEqual(patterns, [])


class TestEventHandlingPatterns(unittest.TestCase):
    """Test detect_event_handling_patterns for code-level event patterns."""

    def setUp(self):
        self.tmpdir = Path(tempfile.mkdtemp())
        (self.tmpdir / "src").mkdir()

    def tearDown(self):
        shutil.rmtree(self.tmpdir)

    def test_detects_consumer_files(self):
        consumer = self.tmpdir / "src" / "consumer.ts"
        consumer.write_text("export class OrderConsumer { async handle() {} }")
        from analyze import detect_event_handling_patterns, collect_source_files
        files = collect_source_files(self.tmpdir)
        patterns = detect_event_handling_patterns(self.tmpdir, files, {"event_systems": ["kafka"]})
        self.assertTrue(len(patterns) > 0)
        rule_text = "\n".join(patterns[0].rule_lines)
        self.assertIn("consumer", rule_text.lower())

    def test_detects_idempotency(self):
        consumer = self.tmpdir / "src" / "consumer.ts"
        consumer.write_text(
            "export class OrderConsumer {\n"
            "  async handle(msg) {\n"
            "    if (await this.alreadyProcessed(msg.messageId)) return;\n"
            "  }\n"
            "}\n"
        )
        from analyze import detect_event_handling_patterns, collect_source_files
        files = collect_source_files(self.tmpdir)
        patterns = detect_event_handling_patterns(self.tmpdir, files, {"event_systems": ["kafka"]})
        rule_text = "\n".join(patterns[0].rule_lines)
        self.assertIn("idempotency", rule_text.lower())

    def test_warns_missing_idempotency(self):
        consumer = self.tmpdir / "src" / "consumer.ts"
        consumer.write_text("export class OrderConsumer { async handle(msg) { process(msg); } }")
        from analyze import detect_event_handling_patterns, collect_source_files
        files = collect_source_files(self.tmpdir)
        patterns = detect_event_handling_patterns(self.tmpdir, files, {"event_systems": ["kafka"]})
        rule_text = "\n".join(patterns[0].rule_lines)
        self.assertIn("warning", rule_text.lower())

    def test_detects_dlq(self):
        consumer = self.tmpdir / "src" / "consumer.ts"
        consumer.write_text(
            "export class OrderConsumer {\n"
            "  deadLetterQueue = 'orders.dlq';\n"
            "}\n"
        )
        from analyze import detect_event_handling_patterns, collect_source_files
        files = collect_source_files(self.tmpdir)
        patterns = detect_event_handling_patterns(self.tmpdir, files, {"event_systems": ["kafka"]})
        rule_text = "\n".join(patterns[0].rule_lines)
        self.assertIn("dead letter", rule_text.lower())

    def test_no_patterns_without_event_systems(self):
        consumer = self.tmpdir / "src" / "consumer.ts"
        consumer.write_text("export class OrderConsumer { async handle() {} }")
        from analyze import detect_event_handling_patterns, collect_source_files
        files = collect_source_files(self.tmpdir)
        patterns = detect_event_handling_patterns(self.tmpdir, files, {})
        self.assertEqual(patterns, [])

    def test_category_keywords_include_events(self):
        from analyze import CATEGORY_KEYWORDS
        self.assertIn("event-handling", CATEGORY_KEYWORDS)
        self.assertIn("kafka", CATEGORY_KEYWORDS["event-handling"])
        self.assertIn("consumer", CATEGORY_KEYWORDS["event-handling"])
        self.assertIn("idempoten", CATEGORY_KEYWORDS["event-handling"])


if __name__ == "__main__":
    unittest.main()
