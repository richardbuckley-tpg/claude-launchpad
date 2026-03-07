# Node.js / Express Stack Reference

## Directory Structure

```
src/
├── routes/               # Route definitions
│   ├── index.ts          # Route aggregator
│   ├── auth.routes.ts
│   ├── users.routes.ts
│   └── [resource].routes.ts
├── controllers/          # Request handlers
│   ├── auth.controller.ts
│   └── users.controller.ts
├── services/             # Business logic
│   ├── auth.service.ts
│   └── users.service.ts
├── middleware/
│   ├── auth.ts           # Authentication middleware
│   ├── validate.ts       # Request validation middleware
│   ├── error-handler.ts  # Global error handler
│   └── rate-limit.ts
├── models/               # Database models/schemas
├── lib/
│   ├── db.ts             # Database connection
│   ├── logger.ts         # Logging setup (pino/winston)
│   └── config.ts         # Environment config with validation
├── validations/          # Zod/Joi schemas for request validation
├── types/                # TypeScript type definitions
├── utils/
├── app.ts                # Express app setup
└── server.ts             # Server entry point
```

## CLAUDE.md Additions

```markdown
## Tech Stack
- Runtime: Node.js 20+
- Framework: Express (or Fastify)
- Language: TypeScript
- Database: [configured separately]
- Testing: Vitest + Supertest

## Commands
- Dev: npm run dev (tsx watch)
- Build: npm run build (tsc)
- Start: npm start (production)
- Test: npm run test
- Lint: npm run lint

## Code Conventions
- Controller → Service → Model pattern (controllers don't access DB directly)
- All request input validated via middleware using zod schemas
- Async route handlers wrapped with asyncHandler utility (no try/catch in routes)
- Centralized error handling via error-handler middleware
- Use HTTP status code constants, not magic numbers
- Environment variables validated at startup via zod schema in config.ts
- Structured logging with correlation IDs (pino recommended)

## Mistakes to Avoid
- NEVER put business logic in controllers — controllers only handle HTTP
- NEVER use console.log — use the structured logger
- ALWAYS validate ALL input (body, params, query) with zod middleware
- NEVER catch errors in individual routes — let them bubble to error handler
- NEVER store secrets in code — use environment variables validated at startup
```

## Agent Customizations

### test-writer.md
- Use Supertest for API endpoint testing
- Create test database or use in-memory SQLite for tests
- Test each layer independently: services with mocked repos, controllers with mocked services
- Use factory functions for test data

## Rules

### src/routes/**/*.ts
```
Route files must:
- Only define routes and apply middleware
- Not contain business logic
- Use validation middleware for all input
- Document each endpoint with a comment showing method, path, and purpose
```

### src/services/**/*.ts
```
Service files must:
- Contain business logic only
- Not import Express types (Request, Response)
- Return typed results
- Throw custom error classes (not generic Error)
```
