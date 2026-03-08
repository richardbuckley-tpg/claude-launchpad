#!/usr/bin/env python3
"""
Claude Launchpad Codebase Analyzer

Reads an existing codebase to extract real patterns, conventions, and architecture.
Generates targeted rules based on what the code actually does, not generic framework advice.

Usage:
    python analyze.py <project-root>                # Analyze and print findings
    python analyze.py <project-root> --write-rules  # Write rule files to .claude/rules/
    python analyze.py <project-root> --json          # JSON output
"""

import argparse
import json
import os
import re
import sys
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path

# ── Data Structures ──────────────────────────────────────────────────────


@dataclass
class Pattern:
    """A detected codebase pattern."""
    category: str          # error-handling, auth, validation, etc.
    description: str       # Human-readable description
    evidence: list         # File paths where pattern was found
    rule_lines: list       # Rule bullet points to generate
    globs: list            # File patterns this rule applies to
    confidence: float      # 0.0-1.0


@dataclass
class AnalysisResult:
    """Complete analysis output."""
    project_dir: str
    stack: dict                    # detected stack info
    patterns: list                 # Pattern objects
    key_abstractions: list         # {name, file, type, description}
    file_organization: dict        # {style, test_location, etc.}


# ── Constants ────────────────────────────────────────────────────────────

SKIP_DIRS = {
    "node_modules", ".next", ".nuxt", ".svelte-kit", ".output",
    "dist", "build", ".git", "__pycache__", ".venv", "venv",
    "vendor", "target", ".claude", ".idea", ".vscode",
    "coverage", ".nyc_output", "htmlcov", ".pytest_cache",
}

SOURCE_EXTENSIONS = {
    ".ts", ".tsx", ".js", ".jsx",  # JavaScript/TypeScript
    ".py",                          # Python
    ".go",                          # Go
    ".rs",                          # Rust
    ".rb",                          # Ruby
}

MAX_FILE_SIZE = 50_000  # Skip files >50KB
MAX_FILES = 500


# ── Helpers ──────────────────────────────────────────────────────────────

def collect_source_files(project_dir: Path) -> list:
    """Collect source files for analysis, respecting limits."""
    files = []
    for root, dirs, filenames in os.walk(project_dir):
        dirs[:] = [d for d in dirs if d not in SKIP_DIRS]
        root_path = Path(root)
        for fname in filenames:
            if len(files) >= MAX_FILES:
                return files
            fp = root_path / fname
            if fp.suffix in SOURCE_EXTENSIONS:
                try:
                    if fp.stat().st_size <= MAX_FILE_SIZE:
                        files.append(fp)
                except OSError:
                    pass
    return files


def read_file_safe(fp: Path) -> str:
    """Read file contents, returning empty string on error."""
    try:
        return fp.read_text(errors="replace")
    except (OSError, UnicodeDecodeError):
        return ""


# ── Stack Detection ──────────────────────────────────────────────────────

def detect_stack(project_dir: Path) -> dict:
    """Detect the project's tech stack from manifest files."""
    stack = {}

    # Node/TypeScript detection
    pkg_json = project_dir / "package.json"
    if pkg_json.exists():
        try:
            pkg = json.loads(pkg_json.read_text())
            deps = {**pkg.get("dependencies", {}), **pkg.get("devDependencies", {})}

            # Language
            stack["language"] = "typescript" if "typescript" in deps else "javascript"

            # Package manager
            if (project_dir / "pnpm-lock.yaml").exists():
                stack["package_manager"] = "pnpm"
            elif (project_dir / "yarn.lock").exists():
                stack["package_manager"] = "yarn"
            elif (project_dir / "bun.lockb").exists():
                stack["package_manager"] = "bun"
            else:
                stack["package_manager"] = "npm"

            # Frontend
            if "next" in deps:
                stack["frontend"] = "nextjs"
                stack["backend"] = "integrated"
            elif "svelte" in deps or "@sveltejs/kit" in deps:
                stack["frontend"] = "sveltekit"
                stack["backend"] = "integrated"
            elif "vue" in deps or "nuxt" in deps:
                stack["frontend"] = "vue"
            elif "react" in deps:
                stack["frontend"] = "react-vite"

            # Backend (if not already set)
            if "backend" not in stack:
                if "express" in deps:
                    stack["backend"] = "node-express"
                elif "fastify" in deps:
                    stack["backend"] = "node-fastify"

            # ORM
            if "prisma" in deps or "@prisma/client" in deps:
                stack["orm"] = "prisma"
            elif "drizzle-orm" in deps:
                stack["orm"] = "drizzle"
            elif "typeorm" in deps:
                stack["orm"] = "typeorm"
            elif "sequelize" in deps:
                stack["orm"] = "sequelize"
            elif "mongoose" in deps:
                stack["orm"] = "mongoose"

            # Auth
            if "@clerk/nextjs" in deps or "@clerk/express" in deps:
                stack["auth"] = "clerk"
            elif "next-auth" in deps or "@auth/core" in deps:
                stack["auth"] = "nextauth"
            elif "@supabase/supabase-js" in deps:
                stack["auth"] = "supabase-auth"

            # Database from ORM
            if stack.get("orm") in ("prisma", "drizzle", "typeorm", "sequelize"):
                stack["database"] = "postgresql"  # most common default
            elif stack.get("orm") == "mongoose":
                stack["database"] = "mongodb"

            # Testing
            if "vitest" in deps:
                stack["test_framework"] = "vitest"
            elif "jest" in deps:
                stack["test_framework"] = "jest"
            elif "@playwright/test" in deps:
                stack["test_framework"] = "playwright"

        except (json.JSONDecodeError, UnicodeDecodeError):
            pass

    # Python detection
    requirements = project_dir / "requirements.txt"
    pyproject = project_dir / "pyproject.toml"
    if requirements.exists() or pyproject.exists():
        stack["language"] = "python"
        try:
            content = ""
            if requirements.exists():
                content = requirements.read_text().lower()
            if pyproject.exists():
                content += "\n" + pyproject.read_text().lower()

            if "fastapi" in content:
                stack["backend"] = "python-fastapi"
            elif "django" in content:
                stack["backend"] = "python-django"
            elif "flask" in content:
                stack["backend"] = "python-flask"
            if "sqlalchemy" in content:
                stack["orm"] = "sqlalchemy"
                stack["database"] = "postgresql"
            if "pytest" in content:
                stack["test_framework"] = "pytest"
        except UnicodeDecodeError:
            pass

    # Go detection
    if (project_dir / "go.mod").exists():
        stack["language"] = "go"
        stack["backend"] = "go"
        stack["test_framework"] = "go-test"

    # Rust detection
    cargo_toml = project_dir / "Cargo.toml"
    if cargo_toml.exists():
        stack["language"] = "rust"
        try:
            content = cargo_toml.read_text().lower()
            if "actix" in content:
                stack["backend"] = "rust-actix"
            elif "axum" in content:
                stack["backend"] = "rust-axum"
        except UnicodeDecodeError:
            pass

    # Ruby/Rails detection
    if (project_dir / "Gemfile").exists():
        stack["language"] = "ruby"
        stack["backend"] = "ruby-rails"
        stack["orm"] = "activerecord"

    # Database refinement from env files
    for env_file in [".env", ".env.local", ".env.example"]:
        env_path = project_dir / env_file
        if env_path.exists():
            try:
                env_content = env_path.read_text()
                if "postgresql" in env_content or "postgres" in env_content:
                    stack["database"] = "postgresql"
                elif "mysql" in env_content:
                    stack["database"] = "mysql"
                elif "mongodb" in env_content:
                    stack["database"] = "mongodb"
                elif "sqlite" in env_content:
                    stack["database"] = "sqlite"
            except UnicodeDecodeError:
                pass

    return stack


# ── Pattern Detectors ────────────────────────────────────────────────────

def detect_error_handling(project_dir: Path, files: list, stack: dict) -> list:
    """Detect error handling patterns."""
    patterns = []
    lang = stack.get("language", "")

    # Custom error classes
    custom_errors = []
    error_class_re = None

    if lang in ("typescript", "javascript"):
        error_class_re = re.compile(r'class\s+(\w+Error)\s+extends\s+(\w+)')
    elif lang == "python":
        error_class_re = re.compile(r'class\s+(\w+(?:Error|Exception))\s*\((\w+)\)')
    elif lang == "go":
        error_class_re = re.compile(r'type\s+(\w+Error)\s+struct')

    if error_class_re:
        for fp in files:
            content = read_file_safe(fp)
            matches = error_class_re.findall(content)
            for match in matches:
                name = match[0] if isinstance(match, tuple) else match
                rel = str(fp.relative_to(project_dir))
                custom_errors.append({"name": name, "file": rel})

    if custom_errors:
        error_files = list(set(e["file"] for e in custom_errors))
        error_names = list(set(e["name"] for e in custom_errors))

        rules = [f"- Use custom error classes: {', '.join(error_names)}"]
        if len(error_files) <= 3:
            rules.append(f"- Error definitions in: {', '.join(error_files)}")
        rules.append("- Never throw generic Error/Exception — use the project's error types")

        ext = "ts" if lang in ("typescript", "javascript") else lang[:2]
        patterns.append(Pattern(
            category="error-handling",
            description="Custom error classes",
            evidence=error_files,
            rule_lines=rules,
            globs=[f"**/*.{ext}", f"**/*.{ext}x"] if ext == "ts" else [f"**/*.{ext}"],
            confidence=0.8 if len(custom_errors) >= 2 else 0.5,
        ))

    # Centralized error handler (Express/Fastify)
    if lang in ("typescript", "javascript"):
        for fp in files:
            content = read_file_safe(fp)
            if re.search(r'(?:err|error)\s*,\s*req\s*,\s*res\s*,\s*next|\.setErrorHandler', content):
                rel = str(fp.relative_to(project_dir))
                patterns.append(Pattern(
                    category="error-handling",
                    description="Centralized error handler",
                    evidence=[rel],
                    rule_lines=[
                        f"- Centralized error handler in `{rel}`",
                        "- Route handlers throw errors — the middleware formats responses",
                        "- Never send error responses directly from route handlers",
                    ],
                    globs=["src/routes/**/*.ts", "src/controllers/**/*.ts"],
                    confidence=0.8,
                ))
                break

    return patterns


def detect_auth_patterns(project_dir: Path, files: list, stack: dict) -> list:
    """Detect authentication/authorization patterns."""
    patterns = []
    lang = stack.get("language", "")

    auth_middleware = []

    for fp in files:
        content = read_file_safe(fp)
        rel = str(fp.relative_to(project_dir))

        if lang in ("typescript", "javascript"):
            auth_funcs = re.findall(
                r'(?:export\s+)?(?:function|const)\s+(withAuth|requireAuth|isAuthenticated|authMiddleware|protect|authenticate|requireRole)\b',
                content
            )
            for func in auth_funcs:
                auth_middleware.append({"name": func, "file": rel})

        elif lang == "python":
            if re.search(r'Depends\(\s*(?:get_current_user|verify_token|require_auth)', content):
                auth_middleware.append({"name": "dependency-injection", "file": rel})
            auth_decorators = re.findall(r'@(login_required|require_auth|permission_required|requires_auth)', content)
            for dec in auth_decorators:
                auth_middleware.append({"name": dec, "file": rel})

    if auth_middleware:
        unique = {}
        for am in auth_middleware:
            if am["name"] not in unique:
                unique[am["name"]] = am["file"]

        rules = []
        for name, filepath in unique.items():
            rules.append(f"- Auth pattern: `{name}` from `{filepath}`")
        rules.append("- ALL routes handling user data must use the project's auth pattern")
        rules.append("- Never implement custom auth checks — use existing middleware")

        globs = ["src/**/*.ts", "src/**/*.tsx", "app/**/*.ts"] if lang in ("typescript", "javascript") else ["**/*.py"]
        patterns.append(Pattern(
            category="auth",
            description="Authentication middleware",
            evidence=[am["file"] for am in auth_middleware[:5]],
            rule_lines=rules,
            globs=globs,
            confidence=0.9,
        ))

    return patterns


def detect_validation(project_dir: Path, files: list, stack: dict) -> list:
    """Detect input validation patterns."""
    patterns = []
    lang = stack.get("language", "")

    validation_libs = {}
    schema_dirs = set()

    for fp in files:
        content = read_file_safe(fp)
        rel = str(fp.relative_to(project_dir))

        if lang in ("typescript", "javascript"):
            if re.search(r'from\s+[\'"]zod[\'"]|require\([\'"]zod[\'"]\)', content):
                validation_libs.setdefault("zod", []).append(rel)
                if re.search(r'z\.object|z\.string|z\.number', content):
                    parts = rel.split("/")
                    if len(parts) > 1:
                        for kw in ("schema", "schemas", "validation", "validators"):
                            if kw in rel.lower():
                                schema_dirs.add("/".join(parts[:-1]))
            elif re.search(r'from\s+[\'"]joi[\'"]', content):
                validation_libs.setdefault("joi", []).append(rel)
            elif re.search(r'from\s+[\'"]yup[\'"]', content):
                validation_libs.setdefault("yup", []).append(rel)

        elif lang == "python":
            if re.search(r'from\s+pydantic\s+import|class\s+\w+\(BaseModel\)', content):
                validation_libs.setdefault("pydantic", []).append(rel)

    if validation_libs:
        primary = max(validation_libs, key=lambda k: len(validation_libs[k]))
        lib_files = validation_libs[primary]

        rules = [f"- Validate ALL input using **{primary}**"]
        if schema_dirs:
            rules.append(f"- Schemas in: {', '.join(sorted(schema_dirs))}")
        rules.append(f"- Never write manual validation when {primary} can express it")

        if len(validation_libs) > 1:
            others = [k for k in validation_libs if k != primary]
            rules.append(f"- Also uses {', '.join(others)} — migrate to {primary} when touching those files")

        patterns.append(Pattern(
            category="validation",
            description=f"{primary} validation",
            evidence=lib_files[:5],
            rule_lines=rules,
            globs=["**/*.ts", "**/*.tsx"] if lang in ("typescript", "javascript") else ["**/*.py"],
            confidence=0.9 if len(lib_files) >= 3 else 0.6,
        ))

    return patterns


def detect_data_fetching(project_dir: Path, files: list, stack: dict) -> list:
    """Detect data fetching and state management patterns."""
    patterns = []
    lang = stack.get("language", "")
    frontend = stack.get("frontend", "")

    if lang not in ("typescript", "javascript"):
        return patterns

    fetching = {}
    state_mgmt = {}

    for fp in files:
        content = read_file_safe(fp)
        rel = str(fp.relative_to(project_dir))

        # Data fetching
        if re.search(r'useQuery|useMutation|useInfiniteQuery|@tanstack/react-query', content):
            fetching.setdefault("tanstack-query", []).append(rel)
        if re.search(r'from\s+[\'"]swr[\'"]|useSWR', content):
            fetching.setdefault("swr", []).append(rel)
        if frontend == "nextjs" and ('"use server"' in content or "'use server'" in content):
            fetching.setdefault("server-actions", []).append(rel)
        if re.search(r'trpc|createTRPCRouter|api\.\w+\.useQuery', content):
            fetching.setdefault("trpc", []).append(rel)

        # State management
        if re.search(r'from\s+[\'"]zustand[\'"]|create\(\s*\(set', content):
            state_mgmt.setdefault("zustand", []).append(rel)
        elif re.search(r'from\s+[\'"]@reduxjs/toolkit[\'"]|createSlice|configureStore', content):
            state_mgmt.setdefault("redux-toolkit", []).append(rel)
        elif re.search(r'from\s+[\'"]jotai[\'"]|atom\(', content):
            state_mgmt.setdefault("jotai", []).append(rel)

    for name, using in fetching.items():
        if len(using) >= 2:
            rules = [f"- Data fetching: use **{name}** (found in {len(using)} files)"]
            if name == "tanstack-query":
                rules.append("- All API calls through useQuery/useMutation hooks")
                rules.append("- Define query keys consistently for cache management")
            elif name == "server-actions":
                rules.append("- Use Server Actions for mutations, not API routes")
            elif name == "trpc":
                rules.append("- All API communication through tRPC — no raw fetch calls")
            patterns.append(Pattern(
                category="data-fetching",
                description=f"{name} data fetching",
                evidence=using[:5],
                rule_lines=rules,
                globs=["src/**/*.ts", "src/**/*.tsx", "app/**/*.ts", "app/**/*.tsx"],
                confidence=0.8 if len(using) >= 3 else 0.5,
            ))

    for name, using in state_mgmt.items():
        if len(using) >= 2:
            rules = [f"- Client state: **{name}**"]
            rules.append("- Keep server state (API data) separate from client state")

            # Find store directories
            store_dirs = set()
            for f in using:
                for kw in ("store", "stores", "state", "atoms", "slices"):
                    if kw in f.lower():
                        store_dirs.add("/".join(f.split("/")[:-1]))
            if store_dirs:
                rules.append(f"- Stores in: {', '.join(sorted(store_dirs))}")

            patterns.append(Pattern(
                category="state-management",
                description=f"{name} state management",
                evidence=using[:5],
                rule_lines=rules,
                globs=["src/**/*.ts", "src/**/*.tsx"],
                confidence=0.7,
            ))

    return patterns


def detect_testing_patterns(project_dir: Path, files: list, stack: dict) -> list:
    """Detect testing conventions."""
    patterns = []
    lang = stack.get("language", "")

    test_files = [fp for fp in files
                  if re.search(r'\.(?:test|spec)\.[jt]sx?$|^test_|_test\.go|_test\.py', fp.name)]

    if not test_files:
        return patterns

    mock_patterns = {}
    fixture_files = []

    for fp in test_files:
        content = read_file_safe(fp)
        rel = str(fp.relative_to(project_dir))

        if lang in ("typescript", "javascript"):
            if "jest.mock" in content or "vi.mock" in content:
                mock_patterns.setdefault("module-mock", []).append(rel)
            if "nock" in content or "msw" in content:
                mock_patterns.setdefault("http-mock", []).append(rel)
            if "factory" in content.lower() or "fixture" in content.lower():
                fixture_files.append(rel)
        elif lang == "python":
            if "@pytest.fixture" in content:
                mock_patterns.setdefault("pytest-fixtures", []).append(rel)
            if "conftest.py" in fp.name:
                fixture_files.append(rel)

    rules = []
    test_framework = stack.get("test_framework", "unknown")
    rules.append(f"- Test framework: **{test_framework}**")

    for pname, pfiles in mock_patterns.items():
        if len(pfiles) >= 2:
            rules.append(f"- Mocking: use {pname} pattern ({len(pfiles)} files)")

    if fixture_files:
        rules.append(f"- Fixtures in: {', '.join(fixture_files[:3])}")

    # File naming convention
    names = [fp.name for fp in test_files]
    if any(".test." in n for n in names):
        rules.append("- Test file naming: `*.test.{ts,tsx}`")
    elif any(".spec." in n for n in names):
        rules.append("- Test file naming: `*.spec.{ts,tsx}`")
    elif any(n.startswith("test_") for n in names):
        rules.append("- Test file naming: `test_*.py`")

    if rules:
        patterns.append(Pattern(
            category="testing",
            description="Testing conventions",
            evidence=[str(fp.relative_to(project_dir)) for fp in test_files[:5]],
            rule_lines=rules,
            globs=["**/*.test.*", "**/*.spec.*", "**/test_*"],
            confidence=0.8,
        ))

    return patterns


def detect_api_patterns(project_dir: Path, files: list, stack: dict) -> list:
    """Detect API response and routing patterns."""
    patterns = []
    lang = stack.get("language", "")
    backend = stack.get("backend", "")

    if not backend or backend == "none":
        return patterns

    response_wrappers = []
    pagination_found = False

    for fp in files:
        content = read_file_safe(fp)
        rel = str(fp.relative_to(project_dir))

        is_route = any(kw in rel.lower() for kw in ["route", "controller", "handler", "api", "endpoint", "view"])
        if not is_route:
            continue

        if lang in ("typescript", "javascript"):
            if re.search(r'(?:successResponse|apiResponse|formatResponse|sendSuccess)\s*\(', content):
                response_wrappers.append(rel)
        elif lang == "python":
            if re.search(r'(?:JSONResponse|make_response|success_response)\s*\(', content):
                response_wrappers.append(rel)

        if re.search(r'(?:page|offset|cursor|limit|skip|take)\s*[=:]', content):
            pagination_found = True

    rules = []
    if response_wrappers:
        rules.append(f"- API responses use a consistent wrapper (see {', '.join(response_wrappers[:3])})")
        rules.append("- Always use the response wrapper — never return raw objects")
    if pagination_found:
        rules.append("- List endpoints must support pagination — never return unbounded results")

    if rules:
        globs = (["src/routes/**", "src/controllers/**", "app/api/**"]
                 if lang in ("typescript", "javascript")
                 else ["app/api/**/*.py", "**/views.py"])
        patterns.append(Pattern(
            category="api",
            description="API conventions",
            evidence=response_wrappers[:5],
            rule_lines=rules,
            globs=globs,
            confidence=0.7,
        ))

    return patterns


def detect_database_patterns(project_dir: Path, files: list, stack: dict) -> list:
    """Detect database access patterns."""
    patterns = []
    lang = stack.get("language", "")
    orm = stack.get("orm", "")

    if not orm:
        return patterns

    repo_files = []
    direct_orm_in_routes = []

    for fp in files:
        content = read_file_safe(fp)
        rel = str(fp.relative_to(project_dir))

        if "repository" in rel.lower() or "repo" in rel.lower():
            repo_files.append(rel)

        is_route = any(kw in rel.lower() for kw in ["route", "controller", "handler", "api", "view"])
        if is_route:
            if lang in ("typescript", "javascript"):
                if re.search(r'prisma\.\w+\.|db\.\w+\.|await\s+\w+Model\.', content):
                    direct_orm_in_routes.append(rel)
            elif lang == "python":
                if re.search(r'session\.\w+\(|\.query\(|\.filter\(', content):
                    direct_orm_in_routes.append(rel)

    rules = []
    if repo_files:
        rules.append(f"- Repository pattern: DB access through {', '.join(repo_files[:3])}")
        rules.append("- Route handlers NEVER call the ORM directly — use repositories")
        if direct_orm_in_routes:
            rules.append(f"- Direct ORM in routes (should refactor): {', '.join(direct_orm_in_routes[:3])}")
    elif direct_orm_in_routes:
        rules.append("- DB access is direct in routes — consider extracting a repository layer")

    if rules:
        patterns.append(Pattern(
            category="database",
            description="Database access pattern",
            evidence=repo_files[:5] or direct_orm_in_routes[:5],
            rule_lines=rules,
            globs=["**/*.ts", "**/*.py"],
            confidence=0.7 if repo_files else 0.5,
        ))

    return patterns


# ── File Organization ────────────────────────────────────────────────────

def detect_file_organization(project_dir: Path, files: list, stack: dict) -> dict:
    """Detect how the project organizes files."""
    org = {
        "style": "unknown",
        "test_location": "unknown",
        "barrel_exports": False,
        "src_dir": None,
    }

    if (project_dir / "src").exists():
        org["src_dir"] = "src"
    elif (project_dir / "app").exists():
        org["src_dir"] = "app"

    # Barrel exports
    barrel_count = 0
    for fp in files:
        if fp.name in ("index.ts", "index.js", "index.tsx"):
            content = read_file_safe(fp)
            if re.search(r'export\s+(?:\*|\{)', content):
                barrel_count += 1
    org["barrel_exports"] = barrel_count >= 3

    # Test location
    test_files = [fp for fp in files if re.search(r'\.(?:test|spec)\.[jt]sx?$|^test_|_test\.', fp.name)]
    co_located = 0
    separate = 0
    tests_dir = 0

    for tf in test_files:
        rel = str(tf.relative_to(project_dir))
        if "__tests__" in rel:
            tests_dir += 1
        elif "test/" in rel or "tests/" in rel:
            separate += 1
        else:
            co_located += 1

    if co_located > separate and co_located > tests_dir:
        org["test_location"] = "co-located"
    elif tests_dir > 0:
        org["test_location"] = "__tests__"
    elif separate > 0:
        org["test_location"] = "separate"

    # Organization style
    feature_dirs = set()
    layer_dirs = set()

    for fp in files:
        rel = str(fp.relative_to(project_dir))
        parts = rel.split("/")
        if len(parts) >= 3:
            if parts[1] in ("features", "modules", "domains"):
                feature_dirs.add(parts[2])
            elif parts[1] in ("controllers", "services", "models", "repositories", "utils", "lib", "middleware"):
                layer_dirs.add(parts[1])

    if len(feature_dirs) >= 2:
        org["style"] = "feature-based"
    elif len(layer_dirs) >= 2:
        org["style"] = "layer-based"

    return org


# ── Key Abstractions ─────────────────────────────────────────────────────

def detect_key_abstractions(project_dir: Path, files: list, stack: dict) -> list:
    """Find important abstractions that should be reused."""
    abstractions = []
    lang = stack.get("language", "")

    # Built-in hooks to ignore
    react_hooks = {"useState", "useEffect", "useRef", "useCallback", "useMemo",
                   "useContext", "useReducer", "useLayoutEffect", "useId",
                   "useTransition", "useDeferredValue", "useImperativeHandle"}

    for fp in files:
        content = read_file_safe(fp)
        rel = str(fp.relative_to(project_dir))

        if lang in ("typescript", "javascript"):
            # Custom hooks
            hooks = re.findall(r'export\s+(?:function|const)\s+(use[A-Z]\w+)', content)
            for hook in hooks:
                if hook not in react_hooks:
                    abstractions.append({"name": hook, "file": rel, "type": "hook"})

            # Service/repository classes
            services = re.findall(r'export\s+class\s+(\w+(?:Service|Client|Repository|Store))', content)
            for svc in services:
                abstractions.append({"name": svc, "file": rel, "type": "service"})

            # Utility functions in lib/utils
            if any(d in rel for d in ["lib/", "utils/", "helpers/"]):
                exports = re.findall(r'export\s+(?:function|const)\s+(\w+)', content)
                for exp in exports:
                    if not exp.startswith("_") and len(exp) > 3:
                        abstractions.append({"name": exp, "file": rel, "type": "utility"})

        elif lang == "python":
            classes = re.findall(r'class\s+(\w+(?:Service|Repository|Client|Manager|Handler))\b', content)
            for cls in classes:
                abstractions.append({"name": cls, "file": rel, "type": "service"})

    # Deduplicate
    seen = set()
    unique = []
    for a in abstractions:
        key = (a["name"], a["file"])
        if key not in seen:
            seen.add(key)
            unique.append(a)

    return unique[:50]


# ── Main Analysis ────────────────────────────────────────────────────────

def analyze(project_dir: Path) -> AnalysisResult:
    """Run full codebase analysis."""
    stack = detect_stack(project_dir)
    files = collect_source_files(project_dir)

    all_patterns = []
    all_patterns.extend(detect_error_handling(project_dir, files, stack))
    all_patterns.extend(detect_auth_patterns(project_dir, files, stack))
    all_patterns.extend(detect_validation(project_dir, files, stack))
    all_patterns.extend(detect_data_fetching(project_dir, files, stack))
    all_patterns.extend(detect_testing_patterns(project_dir, files, stack))
    all_patterns.extend(detect_api_patterns(project_dir, files, stack))
    all_patterns.extend(detect_database_patterns(project_dir, files, stack))

    # Filter by confidence
    confident = [p for p in all_patterns if p.confidence >= 0.5]

    return AnalysisResult(
        project_dir=str(project_dir),
        stack=stack,
        patterns=confident,
        key_abstractions=detect_key_abstractions(project_dir, files, stack),
        file_organization=detect_file_organization(project_dir, files, stack),
    )


# ── Rule Generation ──────────────────────────────────────────────────────

def generate_rules_from_analysis(result: AnalysisResult) -> list:
    """Convert analysis results into rule files. Returns [(name, content), ...]."""
    rules = []

    # Group patterns by category
    categories = {}
    for pattern in result.patterns:
        categories.setdefault(pattern.category, []).append(pattern)

    for category, cat_patterns in categories.items():
        all_globs = set()
        all_rules = []

        for p in cat_patterns:
            all_globs.update(p.globs)
            all_rules.extend(p.rule_lines)

        globs_str = json.dumps(sorted(all_globs))
        desc = f"{category.replace('-', ' ').title()} conventions (auto-detected)"
        content = f"---\nglobs: {globs_str}\ndescription: {desc}\n---\n\n"
        for rule_line in all_rules:
            content += rule_line + "\n"
        rules.append((f"project-{category}", content))

    # File organization rule
    org = result.file_organization
    if org["style"] != "unknown" or org["test_location"] != "unknown":
        org_rules = []
        if org["style"] != "unknown":
            org_rules.append(f"- Project uses **{org['style']}** organization")
        if org["test_location"] != "unknown":
            org_rules.append(f"- Tests are **{org['test_location']}** with source files")
        if org["barrel_exports"]:
            org_rules.append("- Uses barrel exports (index.ts) — update them when adding new modules")
        if org["src_dir"]:
            org_rules.append(f"- Source root: `{org['src_dir']}/`")

        content = '---\nglobs: ["**/*"]\ndescription: File organization conventions (auto-detected)\n---\n\n'
        for rule in org_rules:
            content += rule + "\n"
        rules.append(("project-organization", content))

    # Key abstractions rule
    if result.key_abstractions:
        by_type = {}
        for a in result.key_abstractions:
            by_type.setdefault(a["type"], []).append(a)

        abs_lines = []
        for atype, items in by_type.items():
            items = items[:10]
            if atype == "hook":
                abs_lines.append("\n**Custom Hooks** — reuse instead of reimplementing:")
                for item in items:
                    abs_lines.append(f"- `{item['name']}` from `{item['file']}`")
            elif atype == "service":
                abs_lines.append("\n**Services/Repositories** — use for data access:")
                for item in items:
                    abs_lines.append(f"- `{item['name']}` from `{item['file']}`")
            elif atype == "utility" and len(items) <= 8:
                abs_lines.append("\n**Shared Utilities:**")
                for item in items:
                    abs_lines.append(f"- `{item['name']}` from `{item['file']}`")

        if abs_lines:
            content = '---\nglobs: ["**/*"]\ndescription: Key project abstractions to reuse (auto-detected)\n---\n'
            for line in abs_lines:
                content += line + "\n"
            rules.append(("project-abstractions", content))

    return rules


# ── Feedback Loop ───────────────────────────────────────────────────

# Map keywords in learned corrections to pattern categories
CATEGORY_KEYWORDS = {
    "error-handling": ["error", "exception", "throw", "catch", "try", "apperror", "httperror"],
    "auth": ["auth", "login", "token", "session", "permission", "role", "middleware", "jwt"],
    "validation": ["valid", "schema", "zod", "yup", "joi", "pydantic", "input", "sanitize"],
    "data-fetching": ["fetch", "query", "usequery", "useswr", "trpc", "api call", "server action"],
    "state-management": ["state", "store", "zustand", "redux", "jotai", "atom"],
    "testing": ["test", "mock", "fixture", "jest", "vitest", "pytest", "spec", "assert"],
    "api": ["endpoint", "route", "controller", "handler", "response", "pagination", "rest"],
    "database": ["database", "db", "query", "repository", "orm", "prisma", "migration", "model"],
}


def match_correction_to_category(correction: str) -> str | None:
    """Match a learned correction to a pattern category by keyword overlap."""
    text = correction.lower()
    best_category = None
    best_score = 0
    for category, keywords in CATEGORY_KEYWORDS.items():
        score = sum(1 for kw in keywords if kw in text)
        if score > best_score:
            best_score = score
            best_category = category
    return best_category if best_score > 0 else None


def incorporate_learned(result: AnalysisResult, project_dir: Path) -> AnalysisResult:
    """Enhance analysis results with learned corrections from learn.py.

    Reads .claude/learn-log.json and matches corrections to detected pattern
    categories. Adds matched corrections as extra rule lines to existing patterns,
    or creates new patterns for unmatched categories.
    """
    log_path = project_dir / ".claude" / "learn-log.json"
    if not log_path.exists():
        return result

    try:
        log = json.loads(log_path.read_text())
    except (json.JSONDecodeError, UnicodeDecodeError):
        return result

    if not log:
        return result

    # Group corrections by matched category (deduplicate)
    by_category: dict[str | None, list[str]] = {}
    seen_corrections: set[str] = set()
    for entry in log:
        correction = entry.get("correction", "")
        if not correction or correction in seen_corrections:
            continue
        seen_corrections.add(correction)
        category = match_correction_to_category(correction)
        by_category.setdefault(category, []).append(correction)

    # Build index of existing pattern categories
    existing_categories = {p.category for p in result.patterns}

    for category, corrections in by_category.items():
        if category is None:
            continue

        if category in existing_categories:
            # Append learned corrections to existing pattern's rule lines
            for p in result.patterns:
                if p.category == category:
                    for correction in corrections:
                        rule = correction if correction.startswith("- ") else f"- {correction}"
                        if rule not in p.rule_lines:
                            p.rule_lines.append(f"{rule} *(learned)*")
                    break
        else:
            # Create new pattern from learned corrections
            rule_lines = []
            for correction in corrections:
                rule = correction if correction.startswith("- ") else f"- {correction}"
                rule_lines.append(f"{rule} *(learned)*")
            result.patterns.append(Pattern(
                category=category,
                description=f"{category.replace('-', ' ').title()} (from learned corrections)",
                evidence=[],
                rule_lines=rule_lines,
                globs=["**/*"],
                confidence=0.6,
            ))

    return result


def check_stale_rules(project_dir: Path) -> list[dict]:
    """Check if project-*.md rules reference files/patterns that no longer exist.

    Returns list of {file, issue, suggestion} dicts.
    """
    stale = []
    rules_dir = project_dir / ".claude" / "rules"
    if not rules_dir.exists():
        return stale

    for rf in rules_dir.glob("project-*.md"):
        try:
            content = rf.read_text()
        except UnicodeDecodeError:
            continue

        # Check backtick-quoted file paths like `src/lib/errors.ts`
        referenced_files = re.findall(r'`([a-zA-Z0-9_./-]+\.[a-zA-Z]+)`', content)
        for ref in referenced_files:
            ref_path = project_dir / ref
            if not ref_path.exists() and not any(c in ref for c in ['*', '?', '{']):
                stale.append({
                    "file": rf.name,
                    "issue": f"References `{ref}` which no longer exists",
                    "suggestion": f"Re-run analyzer to update {rf.name}",
                })

        # Check backtick-quoted identifiers like `AppError` — verify they exist in source
        identifiers = re.findall(r'`([A-Z][a-zA-Z]+(?:Error|Service|Client|Repository|Handler|Manager))`', content)
        if identifiers:
            # Quick scan: do these identifiers still exist in the codebase?
            source_files = collect_source_files(project_dir)
            all_content = ""
            for sf in source_files[:100]:  # limit scan
                all_content += read_file_safe(sf)
            for ident in identifiers:
                if ident not in all_content:
                    stale.append({
                        "file": rf.name,
                        "issue": f"References `{ident}` which was not found in codebase",
                        "suggestion": f"Re-run analyzer to update {rf.name}",
                    })

    return stale


def get_last_analysis_time(project_dir: Path) -> str | None:
    """Read last_analysis timestamp from launchpad-config.json."""
    config_path = project_dir / ".claude" / "launchpad-config.json"
    if not config_path.exists():
        return None
    try:
        config = json.loads(config_path.read_text())
        return config.get("last_analysis")
    except (json.JSONDecodeError, UnicodeDecodeError):
        return None


def set_last_analysis_time(project_dir: Path):
    """Record current time as last_analysis in launchpad-config.json."""
    config_path = project_dir / ".claude" / "launchpad-config.json"
    if not config_path.exists():
        return
    try:
        config = json.loads(config_path.read_text())
        config["last_analysis"] = datetime.now().isoformat()
        config_path.write_text(json.dumps(config, indent=2) + "\n")
    except (json.JSONDecodeError, UnicodeDecodeError):
        pass


# ── Output ───────────────────────────────────────────────────────────────

def format_report(result: AnalysisResult) -> str:
    """Format analysis results as a human-readable report."""
    lines = []
    lines.append("Codebase Analysis Report")
    lines.append("=" * 50)

    lines.append("\nDetected Stack:")
    for key, value in result.stack.items():
        lines.append(f"  {key}: {value}")

    org = result.file_organization
    lines.append(f"\nFile Organization:")
    lines.append(f"  Style: {org['style']}")
    lines.append(f"  Tests: {org['test_location']}")
    lines.append(f"  Barrel exports: {'yes' if org['barrel_exports'] else 'no'}")

    lines.append(f"\nPatterns Detected ({len(result.patterns)}):")
    for p in result.patterns:
        conf = "high" if p.confidence >= 0.8 else "medium" if p.confidence >= 0.6 else "low"
        lines.append(f"\n  [{conf}] {p.category}: {p.description}")
        for rule in p.rule_lines:
            lines.append(f"    {rule}")
        if p.evidence:
            lines.append(f"    Evidence: {', '.join(p.evidence[:3])}")

    if result.key_abstractions:
        lines.append(f"\nKey Abstractions ({len(result.key_abstractions)}):")
        by_type = {}
        for a in result.key_abstractions:
            by_type.setdefault(a["type"], []).append(a)
        for atype, items in sorted(by_type.items()):
            lines.append(f"  {atype}s:")
            for item in items[:5]:
                lines.append(f"    {item['name']} ({item['file']})")
            if len(items) > 5:
                lines.append(f"    ... and {len(items) - 5} more")

    gen_rules = generate_rules_from_analysis(result)
    lines.append(f"\nWould generate {len(gen_rules)} rule files:")
    for name, _ in gen_rules:
        lines.append(f"  .claude/rules/{name}.md")

    return "\n".join(lines)


def write_rules(project_dir: Path, result: AnalysisResult, force: bool = False) -> list:
    """Write generated rules to .claude/rules/. Returns list of created file paths."""
    gen_rules = generate_rules_from_analysis(result)
    rules_dir = project_dir / ".claude" / "rules"
    rules_dir.mkdir(parents=True, exist_ok=True)

    created = []
    for name, content in gen_rules:
        fp = rules_dir / f"{name}.md"
        if fp.exists() and not force:
            print(f"  Skipped {fp.name} (exists, use --force to overwrite)")
            continue
        fp.write_text(content)
        created.append(f".claude/rules/{name}.md")
        print(f"  Created {fp.name}")

    # Record analysis timestamp
    set_last_analysis_time(project_dir)

    return created


# ── CLI ──────────────────────────────────────────────────────────────────

def main():
    p = argparse.ArgumentParser(description="Claude Launchpad Codebase Analyzer")
    p.add_argument("project_dir", help="Path to the project root")
    p.add_argument("--write-rules", action="store_true", help="Write rule files to .claude/rules/")
    p.add_argument("--json", action="store_true", help="JSON output")
    p.add_argument("--force", action="store_true", help="Overwrite existing rule files")
    p.add_argument("--incorporate-learned", action="store_true", dest="incorporate_learned",
                   help="Enhance analysis with learned corrections from /learn")
    p.add_argument("--check-stale", action="store_true", dest="check_stale",
                   help="Check for stale project-*.md rules")
    args = p.parse_args()

    project_dir = Path(args.project_dir).resolve()
    if not project_dir.exists():
        print(f"Error: {project_dir} does not exist", file=sys.stderr)
        sys.exit(1)

    if args.check_stale:
        stale = check_stale_rules(project_dir)
        if args.json:
            print(json.dumps(stale, indent=2))
        elif stale:
            print(f"Found {len(stale)} stale references in analyzer rules:\n")
            for s in stale:
                print(f"  {s['file']}: {s['issue']}")
                print(f"    → {s['suggestion']}")
        else:
            print("No stale references found in analyzer rules.")
        sys.exit(0)

    result = analyze(project_dir)

    if args.incorporate_learned:
        result = incorporate_learned(result, project_dir)

    if args.json:
        output = {
            "project_dir": result.project_dir,
            "stack": result.stack,
            "patterns": [
                {
                    "category": p.category,
                    "description": p.description,
                    "evidence": p.evidence,
                    "rule_lines": p.rule_lines,
                    "globs": p.globs,
                    "confidence": p.confidence,
                }
                for p in result.patterns
            ],
            "key_abstractions": result.key_abstractions,
            "file_organization": result.file_organization,
        }
        print(json.dumps(output, indent=2))
    elif args.write_rules:
        created = write_rules(project_dir, result, force=args.force)
        if created:
            print(f"\n{len(created)} rule files written to .claude/rules/")
        else:
            print("\nNo rules generated — codebase may be too small or patterns unclear")
    else:
        print(format_report(result))

    sys.exit(0)


if __name__ == "__main__":
    main()
