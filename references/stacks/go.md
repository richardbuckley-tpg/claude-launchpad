# Go Stack Reference

## Directory Structure

```
├── cmd/
│   └── server/
│       └── main.go           # Entry point
├── internal/
│   ├── config/
│   │   └── config.go         # Configuration loading (env/yaml)
│   ├── handler/              # HTTP handlers (controllers)
│   │   ├── auth.go
│   │   ├── users.go
│   │   └── middleware.go
│   ├── service/              # Business logic
│   │   ├── auth.go
│   │   └── users.go
│   ├── repository/           # Data access layer
│   │   ├── user.go
│   │   └── interfaces.go    # Repository interfaces
│   ├── model/                # Domain models
│   │   └── user.go
│   ├── dto/                  # Request/response types
│   │   └── user.go
│   └── middleware/           # HTTP middleware
│       ├── auth.go
│       ├── logging.go
│       └── cors.go
├── pkg/                      # Public shared packages
│   ├── logger/
│   ├── validator/
│   └── errors/               # Custom error types
├── migrations/               # SQL migration files
├── docs/                     # API documentation
├── tests/
│   ├── integration/
│   └── e2e/
├── go.mod
├── go.sum
├── Makefile
└── Dockerfile
```

## CLAUDE.md Additions

```markdown
## Tech Stack
- Language: Go 1.22+
- Router: Chi (or Gin, Echo)
- Database: PostgreSQL with pgx or sqlx
- Migration: golang-migrate
- Testing: Go standard testing + testify

## Commands
- Dev: go run cmd/server/main.go (or air for hot reload)
- Build: go build -o bin/server cmd/server/main.go
- Test: go test ./...
- Test verbose: go test -v ./...
- Test coverage: go test -cover ./...
- Lint: golangci-lint run
- Migration up: migrate -path migrations -database $DATABASE_URL up
- Migration create: migrate create -ext sql -dir migrations -seq <name>

## Code Conventions
- Follow standard Go project layout (cmd/, internal/, pkg/)
- Handler → Service → Repository pattern
- Interfaces defined by consumer, not implementer
- Context propagation through all layers
- Errors wrapped with fmt.Errorf("operation: %w", err) for stack traces
- Use structured logging (slog or zerolog)
- Table-driven tests as default testing pattern
- Makefile for common commands

## Mistakes to Avoid
- NEVER ignore errors — handle every error explicitly
- NEVER use global state — pass dependencies through constructors
- NEVER put business logic in handlers — handlers only do HTTP
- ALWAYS use context.Context as first parameter in service/repo methods
- ALWAYS close resources (DB connections, HTTP bodies) with defer
- NEVER use panic for error handling — return errors
```

## Agent Customizations

### test-writer.md
- Use table-driven tests as default pattern
- Use testify for assertions and mocks
- Create test fixtures with helper functions, not global state
- Use testcontainers-go for integration tests with real databases
- Test interfaces, not implementations

## Rules

### internal/handler/**/*.go
```
Handlers must:
- Accept http.ResponseWriter and *http.Request (or framework equivalent)
- Decode request, call service, encode response
- Not contain business logic
- Return appropriate HTTP status codes
- Log errors with request context
```

### internal/repository/**/*.go
```
Repositories must:
- Accept context.Context as first parameter
- Return domain models, not database types
- Use prepared statements or query builders
- Handle database-specific errors and wrap them
```
