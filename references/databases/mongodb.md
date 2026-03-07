# MongoDB Database Reference

## With Mongoose (Node.js/TypeScript)

### Directory additions
```
src/models/
├── user.model.ts
├── [resource].model.ts
└── index.ts              # Model exports
src/lib/
└── db.ts                 # Connection setup
```

### CLAUDE.md additions
```markdown
## Database
- Database: MongoDB (Atlas or self-hosted)
- ODM: Mongoose
- Connection: MONGODB_URI in .env

## DB Rules
- ALWAYS define TypeScript interfaces alongside Mongoose schemas
- Use lean() for read-only queries (better performance)
- Define indexes in schema definitions, not separately
- Use populate() sparingly — prefer denormalization for frequently accessed data
- Always validate with Mongoose schema validators AND zod for API input
- Use transactions for multi-document operations
- Set connection options: retryWrites=true, w=majority
```

### Rules for src/models/**/*.ts
```
Model files must:
- Export both the TypeScript interface and Mongoose model
- Define indexes on the schema
- Include timestamps: true in schema options
- Use virtuals for computed fields, not methods that query the DB
```

## With Motor (Python async)

### CLAUDE.md additions
```markdown
## Database
- Database: MongoDB
- Driver: Motor (async)
- ODM: Beanie (optional, recommended)

## DB Rules
- Use Beanie document models for type safety
- Always await motor operations (they're async)
- Use aggregation pipelines for complex queries
```

## General MongoDB Rules

```
- Design schemas for your access patterns, not your data relationships
- Embed related data when: it's always fetched together, it's 1:few, updates are rare
- Reference (normalize) when: data is shared across documents, it's 1:many, it changes frequently
- Always create compound indexes for common query patterns
- Use MongoDB change streams for real-time features instead of polling
- Set read/write concerns appropriately for your consistency needs
```
