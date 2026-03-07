# DynamoDB Database Reference

## Best For
High-throughput, low-latency workloads with predictable access patterns. Serverless architectures
on AWS. Projects where you know your query patterns upfront and want zero database management.

## Directory Additions

```
src/
├── lib/
│   └── dynamodb/
│       ├── client.ts         # DynamoDB client singleton
│       ├── tables.ts         # Table definitions and key schemas
│       └── mappers.ts        # Entity ↔ DynamoDB item mappers
├── models/                   # Domain entities
├── repositories/             # Data access (single-table or per-table)
infrastructure/
├── dynamodb-tables.yml       # CloudFormation/SAM table definitions
└── seed-data/                # Local seed data (JSON)
```

## CLAUDE.md Additions

```markdown
## Database
- Engine: Amazon DynamoDB
- Access: AWS SDK v3 (@aws-sdk/client-dynamodb + @aws-sdk/lib-dynamodb)
- Design: Single-table design (recommended) or multi-table
- Local dev: DynamoDB Local (Docker) or LocalStack

## DB Commands
- Start local DynamoDB: docker run -p 8000:8000 amazon/dynamodb-local
- Create tables: aws dynamodb create-table --cli-input-json file://infrastructure/dynamodb-tables.json --endpoint-url http://localhost:8000
- Seed data: node scripts/seed-dynamodb.js
- Scan table: aws dynamodb scan --table-name TableName --endpoint-url http://localhost:8000

## DynamoDB Conventions
- Design access patterns FIRST, then model the table schema
- Use single-table design: one table with composite keys (PK/SK) for most use cases
- Use GSIs (Global Secondary Indexes) for alternative access patterns (max 20 per table)
- Use DynamoDB Document Client (lib-dynamodb) not the low-level client
- Prefix partition keys with entity type: USER#123, ORDER#456
- Use sort key patterns: METADATA, ORDER#2024-01-15, ITEM#abc

## Mistakes to Avoid
- NEVER perform full table scans in production — always use Query or GetItem
- NEVER model DynamoDB like a relational database (no JOINs, no normalization)
- NEVER use FilterExpressions as your primary access pattern (they scan first, then filter)
- ALWAYS design your key schema around your access patterns
- ALWAYS use batch operations (BatchGetItem, BatchWriteItem) for bulk operations
- ALWAYS set TTL on temporary/session data to auto-delete
- NEVER exceed 400KB per item — if data is large, store in S3 and reference by key
```

## Key Schema Patterns

### Single-Table Design
```
| PK            | SK              | Data            |
|---------------|-----------------|-----------------|
| USER#123      | METADATA        | name, email...  |
| USER#123      | ORDER#001       | order details   |
| USER#123      | ORDER#002       | order details   |
| ORG#abc       | METADATA        | org details     |
| ORG#abc       | MEMBER#123      | role, joined_at |
```

### Access Patterns → Key Design
```
Get user by ID          → PK=USER#id, SK=METADATA
Get user's orders       → PK=USER#id, SK begins_with ORDER#
Get org members         → PK=ORG#id, SK begins_with MEMBER#
Get order by ID (GSI)   → GSI1PK=ORDER#id, GSI1SK=METADATA
```

## Local Development

```yaml
# docker-compose.yml addition
services:
  dynamodb-local:
    image: amazon/dynamodb-local:latest
    ports:
      - "8000:8000"
    volumes:
      - dynamodb-data:/home/dynamodblocal/data
    command: "-jar DynamoDBLocal.jar -sharedDb -dbPath /home/dynamodblocal/data"
```

## Cost Optimization
- Use On-Demand pricing for unpredictable workloads, Provisioned for steady-state
- Set TTL on session/cache data
- Use DAX (DynamoDB Accelerator) only if you need microsecond reads
- Monitor ConsumedCapacity to optimize batch sizes
