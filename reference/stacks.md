# Stack Reference — Condensed Knowledge

Quick-reference for stack-specific patterns. Read the section matching the user's choices.

## Frontend Frameworks

### Next.js (App Router)
- **Key paths**: `src/app/` (routes), `src/components/ui/` (shared), `src/lib/` (utils), `src/server/actions/` (mutations)
- **Commands**: `npm run dev`, `npm run build`, `npm run test`, `npm run lint`, `npx tsc --noEmit`
- **Conventions**: Server Components by default. `"use client"` only when needed. Server Actions for mutations. Zod for all input validation in `src/lib/validations/`. `next/image` for images, `next/link` for links.
- **Mistakes**: Never `"use client"` at page level without reason. Never import server code in client components. Never put secrets without `NEXT_PUBLIC_` prefix. Always add `loading.tsx` + `error.tsx` + `not-found.tsx` per route.
- **Testing**: Vitest + React Testing Library + Playwright. Mock `next/navigation`, `next/headers`.
- **Rules target**: `src/app/api/**/*.ts` (route handlers must validate with zod, return NextResponse), `src/server/actions/**/*.ts` (must start with `"use server"`, validate input, use revalidatePath)

### React + Vite
- **Key paths**: `src/pages/` (routes), `src/components/` (UI), `src/hooks/`, `src/stores/` (Zustand), `src/lib/api.ts`
- **Commands**: `npm run dev`, `npm run build`, `npm run test`, `npm run lint`, `npx tsc --noEmit`
- **Conventions**: Feature-based component organization. React Query for server state, Zustand for app state. API calls through `src/lib/api.ts`. Lazy-load route components.
- **Mistakes**: Never store server state in Zustand. Never make API calls in components directly. Always handle loading/error states.
- **Testing**: Vitest + jsdom + @testing-library/react. MSW for API mocks.

### Vue 3 / Nuxt 3
- **Key paths**: `app/components/` (auto-imported), `app/composables/`, `app/pages/`, `server/api/`, `stores/` (Pinia)
- **Commands**: `npm run dev`, `npm run build`, `npm run test`, `npm run lint`, `npx nuxi typecheck`
- **Conventions**: Composition API with `<script setup>` exclusively. Composables prefixed with `use`. Pinia for global state. `useFetch`/`useAsyncData` for data.
- **Mistakes**: Never use Options API. Never mutate props directly. Use `ref()` not `reactive()` for primitives.

### SvelteKit
- **Key paths**: `src/routes/` (file routing), `src/lib/components/`, `src/lib/server/` (server-only), `src/lib/stores/`
- **Commands**: `npm run dev`, `npm run build`, `npm run test`, `npm run check`
- **Conventions**: `+page.server.ts` for server data loading. Form actions for mutations. `$lib` alias. Svelte 5 runes (`$state`, `$derived`, `$effect`).
- **Mistakes**: Never import `$lib/server` in client code. Always use form actions for mutations. Always add `+error.svelte`.

## Backend Frameworks

### Node.js / Express
- **Key paths**: `src/routes/`, `src/controllers/`, `src/services/`, `src/middleware/`, `src/models/`, `src/validations/`
- **Commands**: `npm run dev` (tsx watch), `npm run build` (tsc), `npm run test`, `npm run lint`
- **Conventions**: Controller → Service → Model. Validate all input via zod middleware. Centralized error handler. Structured logging (pino). Environment validated at startup.
- **Mistakes**: Never put business logic in controllers. Never use `console.log`. Always validate ALL input. Never catch errors in routes — let them bubble.
- **Rules target**: `src/routes/**/*.ts` (only route definitions + middleware), `src/services/**/*.ts` (no Express types, return typed results)

### Node.js / Fastify
- **Key paths**: `src/routes/`, `src/plugins/`, `src/services/`, `src/schemas/`, `src/hooks/`, `src/decorators/`
- **Commands**: `npm run dev` (tsx watch), `npm run build` (tsc), `npm run test`, `npm run lint`
- **Conventions**: Plugin architecture — register routes, hooks, and decorators as plugins. Use Fastify's built-in schema validation (JSON Schema/TypeBox) on every route. Encapsulate with `fastify.register()`. Structured logging built-in (pino). Use `fastify.decorate()` for shared utilities. Prefer `@fastify/autoload` for route registration.
- **Mistakes**: Never use Express middleware directly (use `@fastify/express` adapter only when necessary). Never skip schema validation — it's free performance (serialization). Never mutate `request`/`reply` outside hooks. Always use async handlers (no callbacks).
- **Testing**: `@fastify/inject` for in-process testing (no network overhead). Vitest or tap.
- **Rules target**: `src/routes/**/*.ts` (must define JSON Schema for input/output), `src/plugins/**/*.ts` (must use fp pattern or `fastify-plugin`)

### Python / FastAPI
- **Key paths**: `app/api/v1/`, `app/core/` (config, security), `app/models/`, `app/schemas/`, `app/services/`, `app/db/`
- **Commands**: `uvicorn app.main:app --reload`, `pytest`, `ruff check .`, `ruff format .`, `mypy app/`
- **Conventions**: Async everywhere. Pydantic for all schemas. `Depends()` for DI. Separate models (DB) from schemas (API). Type hints on everything.
- **Mistakes**: Never return SQLAlchemy models directly. Never use sync DB operations. Always use `Depends()`. Never modify applied migrations. Never use `print()`.
- **Rules target**: `app/api/**/*.py` (type-annotated Pydantic schemas, Depends for auth), `app/db/migrations/**/*.py` (never modify existing migrations)

### Python / Django
- **Key paths**: `manage.py`, `config/settings/`, `apps/` (or top-level app dirs), `templates/`, `static/`, `api/`
- **Commands**: `python manage.py runserver`, `python manage.py test`, `ruff check .`, `python manage.py migrate`, `python manage.py makemigrations`
- **Conventions**: Apps as self-contained modules. Fat models, thin views. Class-based views for CRUD, function views for custom logic. Django REST Framework for APIs. Settings split by environment (base/dev/prod). Custom user model from day one. Signals sparingly — prefer explicit calls.
- **Mistakes**: Never put business logic in views (use model methods or services). Never use `select_related`/`prefetch_related` lazily (causes N+1). Never modify applied migrations. Never use `DEBUG=True` in production. Always use `get_user_model()` not direct User import.
- **Testing**: `pytest-django` + factory_boy. Use `TestCase` for DB tests, `SimpleTestCase` for unit tests. `APITestCase` for DRF endpoints.
- **Rules target**: `apps/*/views.py` (thin views, delegate to models/services), `apps/*/models.py` (validations, managers, no view logic), `apps/*/serializers.py` (DRF validation)

### Go
- **Key paths**: `cmd/server/main.go`, `internal/handler/`, `internal/service/`, `internal/repository/`, `internal/model/`, `pkg/`
- **Commands**: `go run cmd/server/main.go`, `go test ./...`, `golangci-lint run`, Makefile for common tasks
- **Conventions**: Standard Go layout (cmd/internal/pkg). Handler → Service → Repository. Interfaces defined by consumer. Context propagation. Errors wrapped with `%w`. Table-driven tests.
- **Mistakes**: Never ignore errors. Never use global state. Never put business logic in handlers. Always use `context.Context`. Always `defer` close resources.

## Databases

### PostgreSQL + Prisma
- **Commands**: `npx prisma generate`, `npx prisma migrate dev --name <desc>`, `npx prisma migrate deploy`, `npx prisma studio`, `npx prisma db seed`
- **Conventions**: PascalCase models, camelCase fields, `@map`/`@@map` for snake_case DB. Always include `createdAt`/`updatedAt`. `@@index` for common queries.
- **Mistakes**: Never edit applied migrations. Always run `prisma generate` after schema changes. Always create migrations (not `db push` in prod).

### PostgreSQL + Drizzle
- **Commands**: `npx drizzle-kit generate`, `npx drizzle-kit migrate`, `npx drizzle-kit studio`
- **Key paths**: `src/db/schema.ts`, `src/db/migrations/`, `drizzle.config.ts`

### PostgreSQL + SQLAlchemy/Alembic
- **Commands**: `alembic revision --autogenerate -m "desc"`, `alembic upgrade head`, `alembic downgrade -1`
- **Key paths**: `app/db/session.py`, `app/db/migrations/versions/`

### PostgreSQL + Go (pgx/sqlx)
- **Commands**: `migrate -path migrations -database $DATABASE_URL up`, `migrate create -ext sql -dir migrations -seq <name>`

### MongoDB + Mongoose
- **Conventions**: TypeScript interfaces alongside Mongoose schemas. `lean()` for read-only. `timestamps: true`. Indexes in schema definitions. Embed 1:few, reference 1:many.

### Supabase
- **Commands**: `supabase start`, `supabase migration new <name>`, `supabase db push`, `supabase gen types typescript --local > src/lib/database.types.ts`
- **Conventions**: RLS on ALL tables. Server client for SSR, browser client for components. Service role only in trusted server code. Regenerate types after schema changes.
- **Mistakes**: Never expose service role key to client. Never disable RLS on user data tables.

## Authentication

### Clerk
- **Key paths**: `src/middleware.ts` (clerkMiddleware), `src/app/sign-in/`, `src/app/sign-up/`, `src/app/api/webhooks/clerk/`
- **Conventions**: `auth()` in Server Components, `useUser()` in Client Components. Route groups: `(protected)` and `(public)`. Sync users via webhooks. Store `clerk_user_id` as FK.
- **Env**: `NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY`, `CLERK_SECRET_KEY`

### NextAuth / Auth.js v5
- **Key paths**: `src/auth.ts`, `src/auth.config.ts`, `src/middleware.ts`, `src/app/api/auth/[...nextauth]/route.ts`
- **Conventions**: JWT strategy default. PrismaAdapter for DB sessions. Callbacks for custom JWT/session content. `signIn()`/`signOut()` server actions.
- **Mistakes**: Never store sensitive data in JWT. Always use database adapter for user profiles.
- **Env**: `AUTH_SECRET`, `AUTH_GOOGLE_ID`, `AUTH_GOOGLE_SECRET`

### Custom JWT
- **Conventions**: Stateless tokens with short expiry (15min access, 7d refresh). Refresh token rotation. Store refresh tokens in DB. httpOnly cookies for web, Authorization header for API.

### Rust / Actix-web
- **Key paths**: `src/main.rs`, `src/routes/`, `src/handlers/`, `src/models/`, `src/db/`, `src/errors.rs`
- **Commands**: `cargo run`, `cargo test`, `cargo clippy`, `cargo fmt`, `cargo build --release`
- **Conventions**: Handler → Service → Repository. `Result<T, AppError>` everywhere. Derive macros for serialization (serde). Sqlx for async DB. Tower middleware.
- **Mistakes**: Never `.unwrap()` in production code. Never block the async runtime. Always propagate errors with `?`. Always use `#[derive(Debug)]`.

### Ruby on Rails
- **Key paths**: `app/controllers/`, `app/models/`, `app/views/`, `app/services/`, `config/routes.rb`, `db/migrate/`
- **Commands**: `rails server`, `rails test`, `bundle exec rubocop`, `rails db:migrate`, `rails console`
- **Conventions**: MVC + service objects for business logic. Strong params for input. ActiveRecord validations. RESTful routes. Convention over configuration.
- **Mistakes**: Never put logic in controllers (use services). Never N+1 queries (use `includes`). Never modify applied migrations. Always add database indexes for foreign keys.
- **Rules target**: `app/controllers/**/*.rb` (thin controllers), `app/models/**/*.rb` (validations, scopes, no business logic)

## Monorepo Patterns

### Turborepo / pnpm workspaces
- **Key paths**: `apps/` (deployable apps), `packages/` (shared libraries), `turbo.json`, `pnpm-workspace.yaml`
- **Commands**: `pnpm turbo run build`, `pnpm turbo run test`, `pnpm turbo run lint`, `pnpm --filter <app> dev`
- **Conventions**: Shared packages in `packages/`. Internal packages use `"main": "./src/index.ts"`. Turborepo caches build artifacts. `tsconfig` extends from root.
- **Mistakes**: Never import between apps directly (use packages). Always declare dependencies explicitly. Never skip turbo caching in CI.

### Nx
- **Key paths**: `apps/`, `libs/`, `nx.json`, `project.json` per project
- **Commands**: `nx serve <app>`, `nx test <project>`, `nx build <project>`, `nx affected --target=test`
- **Conventions**: Libraries categorized as feature/data-access/ui/util. Module boundary rules via tags. Affected commands for CI efficiency.

## Mobile

### React Native / Expo
- **Key paths**: `app/` (Expo Router), `src/components/`, `src/hooks/`, `src/stores/`, `src/services/`
- **Commands**: `npx expo start`, `npx expo run:ios`, `npx expo run:android`, `npm run test`, `npm run lint`
- **Conventions**: Expo Router for navigation. React Native Paper or NativeWind for styling. React Query for server state. Platform-specific files with `.ios.ts`/`.android.ts`.
- **Mistakes**: Never use `window` or DOM APIs. Never import web-only packages. Always handle safe area insets. Always test on both platforms.

### Flutter
- **Key paths**: `lib/main.dart`, `lib/screens/`, `lib/widgets/`, `lib/models/`, `lib/services/`, `lib/providers/`
- **Commands**: `flutter run`, `flutter test`, `flutter analyze`, `flutter build apk`, `flutter build ios`
- **Conventions**: Provider or Riverpod for state. Repository pattern for data. Separate UI from logic. Dart null safety everywhere.
- **Mistakes**: Never setState in complex widgets (use state management). Never hardcode strings (use l10n). Always dispose controllers.

## Deployment

### Vercel
- **Conventions**: Preview auto-deploys on PR branches. Production on push to main. Env vars in Dashboard. `vercel env pull .env.local` to sync.
- **Gotchas**: 10s default timeout (30s Pro). Edge functions can't use Node native modules. ISR only works on Vercel.

### Railway
- **Conventions**: Dockerfile or Nixpacks. `railway up` or git push. `railway status` for state. Environment-based deploy targets.

### AWS
- **Conventions**: Verify credentials with `aws sts get-caller-identity`. Build before deploy. Check CloudWatch for deployment logs.

## MCP Servers

MCP (Model Context Protocol) servers extend Claude Code with external tool access. Configure in `.claude/settings.json` under `mcpServers`.

### GitHub MCP
- **Package**: `@modelcontextprotocol/server-github`
- **Env**: `GITHUB_PERSONAL_ACCESS_TOKEN` — needs `repo`, `read:org` scopes
- **Capabilities**: Create/read issues, PRs, branches, file contents, search repos
- **When to add**: Any project hosted on GitHub (most projects)
- **Anti-pattern**: Don't add if project uses GitLab or Bitbucket

### GitLab MCP
- **Package**: `@modelcontextprotocol/server-gitlab`
- **Env**: `GITLAB_PERSONAL_ACCESS_TOKEN`, `GITLAB_API_URL`
- **Capabilities**: Issues, merge requests, pipelines, file operations
- **When to add**: GitLab-hosted projects or GitLab CI users

### PostgreSQL MCP
- **Package**: `@modelcontextprotocol/server-postgres`
- **Env**: `DATABASE_URL` — standard connection string
- **Capabilities**: Run read-only queries, inspect schema, list tables
- **When to add**: Projects with PostgreSQL. Great for debugging data issues
- **Anti-pattern**: Don't use for write operations — read-only by design. Use read-only DB credentials

### SQLite MCP
- **Package**: `@modelcontextprotocol/server-sqlite`
- **Capabilities**: Query SQLite databases, inspect schema
- **When to add**: SQLite projects, local dev databases, Turso

### Filesystem MCP
- **Package**: `@modelcontextprotocol/server-filesystem`
- **Args**: Pass allowed directories (e.g., `./docs`, `./specs`)
- **Capabilities**: Read/write files in allowed directories
- **When to add**: Team projects with docs/specs outside the main codebase
- **Anti-pattern**: Don't add root `/` — scope to specific directories

### Sentry MCP
- **Package**: `@modelcontextprotocol/server-sentry`
- **Env**: `SENTRY_AUTH_TOKEN`
- **Capabilities**: Query issues, events, releases, performance data
- **When to add**: Projects using Sentry for error monitoring

### Selection Logic
- **Always**: GitHub/GitLab MCP (match git platform)
- **If database**: PostgreSQL/SQLite MCP for schema inspection
- **If team**: Filesystem MCP for shared docs
- **If monitoring**: Sentry MCP for error context
- **Total**: Aim for 1-3 MCP servers. More adds startup latency

## Event Brokers & Message Queues

### Apache Kafka
- **Dependencies**: Node.js: `kafkajs`; Python: `confluent-kafka`, `faust-streaming`; Go: `confluent-kafka-go`, `sarama`
- **Key commands**: `kafka-topics.sh --create`, `kafka-consumer-groups.sh --list`, `kafka-console-consumer.sh`, Schema Registry API for schema management
- **Rules target**: `**/consumers/**`, `**/producers/**`, `**/handlers/**/*.{ts,py,go}`
- **Conventions**: Always use `acks=all` for producer reliability. Disable auto topic creation in production. Consumer group IDs must be meaningful and tied to the consuming service. Use Cooperative Sticky assignor to prevent unnecessary rebalances. Schema Registry with backward compatibility enforced. Dead letter topics for every consumer group.
- **Mistakes**: Never under-partition (creates throughput bottleneck). Never auto-acknowledge before processing completes. Never send giant payloads — store data externally, pass references. Never use record-based subject name strategy in Schema Registry.

### BullMQ
- **Dependencies**: `bullmq` (Node.js), requires Redis
- **Rules target**: `**/jobs/**`, `**/queues/**`, `**/workers/**/*.ts`
- **Conventions**: Workers MUST run in separate processes from the API server. Job processors must be idempotent (retries are normal). Keep job data small — store payloads externally, pass IDs. Configure dead letter queues for failed jobs. Use sandboxed processors for isolation. Set appropriate concurrency limits.
- **Mistakes**: Never use infinite concurrency (overwhelms downstream services). Never run workers in the API process. Always handle stalled jobs.

### RabbitMQ
- **Dependencies**: Node.js: `amqplib`; Python: `pika`, `celery`; Go: `amqp091-go`
- **Rules target**: `**/consumers/**`, `**/publishers/**`, `**/handlers/**`
- **Conventions**: One TCP connection per process, multiple channels within it. Configure prefetch per consumer (never unlimited). Queues must be durable, messages persistent. Dead letter exchanges (DLX) on every queue. Manual acknowledge only — never auto-ack. Retry with exponential backoff, max attempts before DLX.
- **Mistakes**: Never create a new connection per request (catastrophic at scale). Never use unlimited prefetch (one consumer gets all messages, OOM). Never requeue rejected messages without retry limit (self-inflicted DoS).

### Celery (Python)
- **Dependencies**: `celery`, `kombu`, optional: `celery[redis]`, `celery[rabbitmq]`
- **Rules target**: `**/tasks/**`, `**/celery/**/*.py`
- **Conventions**: Tasks must be idempotent. Use `task_acks_late = True` (acknowledge after processing). Configure dead letter queue for failed tasks. Set `task_reject_on_worker_lost = True`. Use `bind=True` for access to retry mechanism. Keep task arguments serializable and small.
- **Mistakes**: Never pass ORM objects as task arguments (not serializable across workers). Always set time limits (tasks run forever otherwise). Never use pickle serializer in production (security risk) — use JSON.

### AWS EventBridge / SQS / SNS
- **Dependencies**: `@aws-sdk/client-eventbridge`, `@aws-sdk/client-sqs`, `@aws-sdk/client-sns`, Python: `boto3`
- **Rules target**: `**/events/**`, `**/handlers/**`, `**/lambdas/**`
- **Conventions**: EventBridge: always have a catch-all rule to archive/audit queue (unmatched events are silently dropped). Use SNS→SQS→Lambda (never SNS→Lambda directly — throttled messages are lost). SQS FIFO when ordering matters (standard is best-effort ordering). Configure DLQ on every SQS queue and SNS subscription. Implement idempotent consumers (SQS delivers at-least-once). Lambda handlers should be thin — delegate to service layer.
- **Mistakes**: Never omit DLQ on SQS queues. Never use over-broad EventBridge patterns (causes unnecessary invocations). Never ignore visibility timeout (causes duplicate processing).

### NATS
- **Dependencies**: Node.js: `nats`; Go: `nats.go`; Python: `nats-py`
- **Rules target**: `**/messaging/**`, `**/subscribers/**`, `**/publishers/**`
- **Conventions**: Distinguish Core NATS (at-most-once) from JetStream (at-least-once/exactly-once). Subject hierarchies mirror service/domain boundaries (e.g., `orders.created`). Keep JetStream consumers below ~100K per server. Keep disjoint subject filters per consumer below ~300. Connection management centralized with reconnection logic.

### Redis Streams
- **Dependencies**: `ioredis` (Node.js), `redis-py` (Python), `go-redis` (Go)
- **Rules target**: `**/streams/**`, `**/consumers/**`
- **Conventions**: Always configure stream trimming (MAXLEN/MINID) — untrimmed streams grow unboundedly. Acknowledge processed messages (XACK) — PEL grows indefinitely otherwise. Use XAUTOCLAIM for automatic recovery of stale pending messages. Make handlers idempotent (re-delivery is normal). Isolate critical streams from cache data.

## Stream Processing

### Apache Flink
- **Dependencies**: Java: `flink-streaming-java`; Python: `apache-flink` (PyFlink)
- **Rules target**: `**/pipelines/**`, `**/jobs/**`, `**/transformations/**`
- **Conventions**: Use RocksDB state backend in production (not HashMap). Enable incremental checkpointing for large state. Start checkpoint interval at 10-15 minutes, tune from there. Checkpoint storage on reliable distributed storage (S3, HDFS), never local disk. Align Kafka partition count with Flink parallelism. Separate job JARs per pipeline — no monolithic uber jobs. Clear expired state to prevent memory pressure.
- **Mistakes**: Never use HashMap state backend in production with large state. Never use large watermark thresholds (causes excessive state retention). Always manage state size (clear expired state).

### Apache Spark Streaming
- **Dependencies**: `pyspark`, `spark-streaming-kafka`
- **Rules target**: `**/pipelines/**`, `**/streaming/**`
- **Conventions**: Use Structured Streaming API (not legacy DStreams). Schema definitions explicit, never inferred in production. Checkpoint directory on reliable distributed storage. Use `foreachPartition` for database writes (not per-record connections). Configure `maxFilesPerTrigger` for file-based sources. Align Kafka partition count with Spark parallelism.

## Workflow Orchestration

### Temporal
- **Dependencies**: Node.js: `@temporalio/client`, `@temporalio/worker`, `@temporalio/workflow`, `@temporalio/activity`; Python: `temporalio`; Go: `go.temporal.io/sdk`
- **Rules target**: `**/workflows/**/*.ts`, `**/activities/**/*.ts`
- **Conventions**: **Workflow code MUST be deterministic** — NO I/O, NO `Date.now()`, NO `Math.random()`, NO network calls, NO file access, NO database queries. ALL side effects go in activities. One file per workflow, one file per activity group. Strict separation: workflow definitions (orchestration only) vs activity implementations (all I/O). Use workflow versioning when changing workflow code (prevents non-determinism on replay). Use `continue-as-new` for long-running workflows (prevents unbounded history). Don't set maximum retry limits on activities — use appropriate timeouts instead. Workflows should never "fail" with valid input — return error results, don't throw.
- **Mistakes**: Never put non-deterministic code in workflows (the #1 Temporal mistake). Never bundle multiple transactions in a single activity. Never use more than one input/output value for workflows and activities. Never use short schedule-to-close timeouts.

## Cross-Cutting Event Patterns

### Event Sourcing
- **Conventions**: Store state changes as immutable events, not current state. Events immutable once written; schema versioning essential. Implement snapshots for long event histories (rebuilding from scratch is slow). Use infinite retention topics so read models can be rebuilt. Test aggregate rebuilding from event log.

### CQRS
- **Conventions**: Separate write model (commands) from read model (queries). Read model uses eventual consistency — verify this is acceptable for the use case. Projection/materialization logic must be idempotent. Read models must be rebuildable from event log.

### Saga Pattern
- **Conventions**: Orchestration (central coordinator) for complex workflows; choreography (event-based) for simple, loosely coupled. Every step MUST have a compensating transaction. Order: retryable transactions after compensable ones. Compensating transactions must also be idempotent. Handle isolation anomalies (concurrent sagas reading dirty data).

### Outbox Pattern
- **Conventions**: Outbox write in the SAME database transaction as the state change. Separate publisher process reads outbox and publishes to broker. Events have unique IDs for deduplication. Clean outbox table periodically.

### Idempotency
- **Conventions**: EVERY consumer/worker must be idempotent — this is the single most universal requirement. Track processed message IDs with appropriate TTL. Use database upserts or conditional writes. Exactly-once = idempotent producers + transactional writes + idempotent consumers.

### Dead Letter Queues
- **Conventions**: Configure DLQ on EVERY consumer/queue — never silently drop messages. Monitor and alert on DLQ depth. Distinguish retryable errors (retry with backoff) from poison messages (DLQ immediately). DLQ messages must include original context (headers, timestamps, error details). Have a process for investigating and replaying DLQ messages.

### Schema Evolution
- **Conventions**: Use Avro or Protobuf with Schema Registry. Enforce backward compatibility (default and recommended mode). New fields must have defaults; never remove required fields. Test schema compatibility in CI before merge. Consumer-driven contract testing between producer and consumer teams.
