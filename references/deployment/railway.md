# Railway Deployment Reference

## Best For
Full-stack apps needing backend services, databases, Redis, and workers in one place.

## Environment Setup

### Environments
- **Production**: main service
- **Staging**: create via Railway environments feature (shares config, separate deploys)
- **PR Environments**: auto-created for each PR (optional)

### Environment Variables
- Set via Railway Dashboard > Variables
- Shared variables across services with ${{shared.VAR_NAME}}
- Railway auto-provides: DATABASE_URL, REDIS_URL for provisioned services

## CLAUDE.md Additions

```markdown
## Deployment
- Platform: Railway
- Deploy: automatic on push to main
- Database: Railway-provisioned PostgreSQL
- Redis: Railway-provisioned Redis (if needed)
- Environment variables: Railway Dashboard

## Deploy Commands
- Deploy: push to main (auto-deploys)
- Logs: railway logs
- Shell: railway shell
- Run command: railway run <command>
- Link project: railway link
```

## railway.toml

```toml
[build]
builder = "nixpacks"
buildCommand = "npm run build"

[deploy]
startCommand = "npm start"
healthcheckPath = "/api/health"
healthcheckTimeout = 30
restartPolicyType = "on_failure"
restartPolicyMaxRetries = 3

[service]
internalPort = 3000
```

## Multi-Service Setup

For projects with separate frontend/backend:
```
project/
├── apps/
│   ├── web/          # Frontend (Railway service 1)
│   └── api/          # Backend (Railway service 2)
├── packages/         # Shared code
└── railway.toml      # Root config
```

Each service gets its own Railway service with its own environment variables.

## Common Gotchas
- Railway bills by resource usage, not requests
- Database backups are automatic but verify retention policy
- Use internal networking (${{service.RAILWAY_PRIVATE_DOMAIN}}) for service-to-service communication
- Nixpacks auto-detects runtime but you can override with Dockerfile
