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
    collect_source_files,
    detect_api_patterns,
    detect_auth_patterns,
    detect_database_patterns,
    detect_data_fetching,
    detect_error_handling,
    detect_file_organization,
    detect_key_abstractions,
    detect_stack,
    detect_testing_patterns,
    detect_validation,
    format_report,
    generate_rules_from_analysis,
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


if __name__ == "__main__":
    unittest.main()
