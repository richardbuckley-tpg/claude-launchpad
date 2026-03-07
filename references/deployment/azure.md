# Azure Deployment Reference

## Common Architectures

### App Service (simplest)
- **Azure App Service** for web apps
- **Azure SQL** or **PostgreSQL Flexible Server** for database
- **Azure Blob Storage** for files
- **Azure AD B2C** for auth (or use Clerk/Auth.js)

### Container-based
- **Azure Container Apps** for containerized services
- **Azure Container Registry** for images
- **Azure Database for PostgreSQL** for database

### Serverless
- **Azure Functions** for backend
- **Azure Static Web Apps** for frontend
- **Azure Cosmos DB** for database

## CLAUDE.md Additions

```markdown
## Deployment
- Platform: Azure (App Service / Container Apps / Functions)
- IaC: Bicep (or Terraform)
- Region: [configured region]

## Deploy Commands
- Deploy: az webapp deploy (or via GitHub Actions)
- Logs: az webapp log tail
- SSH: az webapp ssh
- Config: az webapp config appsettings set

## Azure Conventions
- Infrastructure defined in Bicep templates or Terraform
- Use Azure Key Vault for secrets
- Use Managed Identity for service-to-service auth (no connection strings in code)
- Use Application Insights for monitoring and logging
- Tag all resources with: project, environment, cost-center
```

## GitHub Actions Deployment

```yaml
# .github/workflows/deploy.yml
name: Deploy
on:
  push:
    branches: [main]

jobs:
  deploy:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: azure/login@v2
        with:
          creds: ${{ secrets.AZURE_CREDENTIALS }}
      - run: npm ci && npm run build && npm test
      - uses: azure/webapps-deploy@v3
        with:
          app-name: ${{ vars.AZURE_APP_NAME }}
```

## Common Gotchas
- App Service has a 230s request timeout
- Azure Functions consumption plan has cold starts (use Premium for low latency)
- Use Connection Strings in App Settings for database connections
- Azure AD B2C configuration is complex — consider Clerk for simpler auth
