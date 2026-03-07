# Python / FastAPI Stack Reference

## Directory Structure

```
app/
├── api/
│   ├── __init__.py
│   ├── deps.py           # Shared dependencies (get_db, get_current_user)
│   └── v1/
│       ├── __init__.py
│       ├── router.py     # Main router aggregating all endpoints
│       ├── auth.py
│       ├── users.py
│       └── [resource].py
├── core/
│   ├── __init__.py
│   ├── config.py         # Settings with pydantic-settings
│   ├── security.py       # JWT/auth utilities
│   └── exceptions.py     # Custom exception handlers
├── models/
│   ├── __init__.py
│   └── user.py           # SQLAlchemy/SQLModel models
├── schemas/
│   ├── __init__.py
│   └── user.py           # Pydantic request/response schemas
├── services/
│   ├── __init__.py
│   └── user.py           # Business logic
├── db/
│   ├── __init__.py
│   ├── session.py        # Database session management
│   └── migrations/       # Alembic migrations
│       ├── versions/
│       └── env.py
├── utils/
├── tests/
│   ├── conftest.py       # Fixtures (test client, test db)
│   ├── api/
│   └── services/
├── main.py               # FastAPI app creation
└── alembic.ini
```

## CLAUDE.md Additions

```markdown
## Tech Stack
- Language: Python 3.12+
- Framework: FastAPI
- ORM: SQLAlchemy 2.0 (async) or SQLModel
- Migration: Alembic
- Validation: Pydantic v2
- Testing: pytest + httpx (async)

## Commands
- Dev: uvicorn app.main:app --reload
- Test: pytest
- Test verbose: pytest -v --tb=short
- Lint: ruff check .
- Format: ruff format .
- Type check: mypy app/
- Migration create: alembic revision --autogenerate -m "description"
- Migration run: alembic upgrade head

## Code Conventions
- Async everywhere — use async def for all endpoints and DB operations
- Pydantic models for ALL request/response schemas (never return raw dicts)
- Dependencies via FastAPI's Depends() for DB sessions, auth, etc.
- Settings loaded via pydantic-settings with .env file support
- Type hints on ALL functions (enforced by mypy)
- Use Path, Query, Body parameter types for documentation
- Separate models (DB) from schemas (API) — never expose DB models directly

## Mistakes to Avoid
- NEVER return SQLAlchemy models directly from endpoints — use Pydantic schemas
- NEVER use sync database operations — use async sessions
- ALWAYS use Depends() for cross-cutting concerns, not middleware
- NEVER modify migration files after they've been applied
- ALWAYS run alembic upgrade head before and after creating migrations
- NEVER use print() — use Python's logging module with structured output
```

## Agent Customizations

### test-writer.md
- Use pytest with async support (pytest-asyncio)
- Use httpx.AsyncClient as test client
- Create conftest.py fixtures for test database, client, and auth tokens
- Use factory_boy or custom factories for test data

## Rules

### app/api/**/*.py
```
Endpoint files must:
- Use type-annotated Pydantic schemas for all inputs and outputs
- Use Depends() for authentication and authorization
- Return Pydantic response models, not dicts
- Use status_code parameter on route decorators
- Include docstrings (these become OpenAPI descriptions)
```

### app/db/migrations/versions/**/*.py
```
NEVER modify existing migration files.
ALWAYS create new migrations for schema changes.
Test migrations with: alembic upgrade head && alembic downgrade -1 && alembic upgrade head
```
