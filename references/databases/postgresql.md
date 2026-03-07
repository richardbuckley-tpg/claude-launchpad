# PostgreSQL Database Reference

## With Prisma (Node.js/TypeScript)

### Directory additions
```
prisma/
├── schema.prisma         # Schema definition
├── migrations/           # Migration history
└── seed.ts               # Seed data
```

### CLAUDE.md additions
```markdown
## Database
- Database: PostgreSQL
- ORM: Prisma
- Connection: DATABASE_URL in .env

## DB Commands
- Generate client: npx prisma generate
- Create migration: npx prisma migrate dev --name <description>
- Apply migrations: npx prisma migrate deploy
- Reset database: npx prisma migrate reset
- Open studio: npx prisma studio
- Seed: npx prisma db seed

## DB Rules
- NEVER edit migration files after they've been applied
- ALWAYS create migrations for schema changes (don't use db push in production)
- ALWAYS run prisma generate after schema changes
- Use Prisma's relation syntax for joins, not raw SQL
- Index frequently queried columns in schema.prisma
```

### Rules for prisma/schema.prisma
```
Schema conventions:
- Model names: PascalCase singular (User, not users)
- Field names: camelCase
- Always include createdAt and updatedAt timestamps
- Use @map and @@map for snake_case database naming
- Define explicit relation names when a model has multiple relations to the same target
- Add @@index for commonly queried field combinations
```

### Agent additions (test-writer)
```
For database tests:
- Use a separate test database (DATABASE_URL_TEST)
- Reset database before each test suite
- Use Prisma's transaction API for test isolation
- Create factory functions for test data
```

## With Drizzle (Node.js/TypeScript)

### Directory additions
```
src/db/
├── schema.ts             # Drizzle schema definitions
├── migrations/           # SQL migration files
├── index.ts              # Database client export
└── seed.ts
drizzle.config.ts
```

### CLAUDE.md additions
```markdown
## Database
- Database: PostgreSQL
- ORM: Drizzle
- Connection: DATABASE_URL in .env

## DB Commands
- Generate migrations: npx drizzle-kit generate
- Apply migrations: npx drizzle-kit migrate
- Open studio: npx drizzle-kit studio
```

## With SQLAlchemy (Python)

### Directory additions
```
app/db/
├── session.py            # Async session factory
├── base.py               # Base model class
└── migrations/
    ├── env.py
    ├── versions/
    └── alembic.ini
```

### CLAUDE.md additions
```markdown
## Database
- Database: PostgreSQL
- ORM: SQLAlchemy 2.0 (async)
- Migration: Alembic

## DB Commands
- Create migration: alembic revision --autogenerate -m "description"
- Apply migrations: alembic upgrade head
- Rollback: alembic downgrade -1
```

## With pgx/sqlx (Go)

### CLAUDE.md additions
```markdown
## Database
- Database: PostgreSQL
- Driver: pgx (or sqlx)
- Migration: golang-migrate

## DB Commands
- Migration up: migrate -path migrations -database $DATABASE_URL up
- Migration down: migrate -path migrations -database $DATABASE_URL down 1
- Create migration: migrate create -ext sql -dir migrations -seq <name>
```

## General PostgreSQL Rules

```
- Always use parameterized queries (never string concatenation)
- Use transactions for multi-step operations
- Add indexes for foreign keys and commonly filtered columns
- Use ENUM types sparingly — prefer text with application-level validation
- Set connection pool limits appropriate to your hosting (e.g., Supabase has limits)
- Use UUID for primary keys in multi-tenant or distributed systems
```
