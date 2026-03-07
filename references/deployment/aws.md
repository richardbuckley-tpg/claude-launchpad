# AWS Deployment Reference

## Common Architectures

### Serverless (recommended for most new projects)
- **Lambda** + API Gateway for backend
- **S3** + CloudFront for frontend static assets
- **RDS** (PostgreSQL) or DynamoDB for database
- **Cognito** for auth (or use Clerk/Auth.js)
- **SST** or **AWS CDK** for infrastructure as code

### Container-based
- **ECS Fargate** for containerized services
- **ALB** for load balancing
- **ECR** for container registry
- **RDS** for database

### Amplify (simplest)
- **Amplify Hosting** for Next.js/React apps
- Auto-deploys from Git
- Built-in CI/CD, previews, and environment management

## CLAUDE.md Additions

```markdown
## Deployment
- Platform: AWS (Serverless/ECS/Amplify)
- IaC: SST v3 (or AWS CDK / Terraform)
- Region: [configured region]

## Deploy Commands (SST)
- Dev: npx sst dev
- Deploy staging: npx sst deploy --stage staging
- Deploy production: npx sst deploy --stage production
- Remove: npx sst remove --stage <stage>

## AWS Conventions
- All infrastructure defined in code (never click-ops)
- Use SSM Parameter Store for secrets, not env files
- Tag all resources with: project, environment, owner
- Use least-privilege IAM roles for each service
- Enable CloudWatch logging for all services
```

## Environment Management

```
environments/
├── .env.development      # Local dev defaults
├── .env.staging          # Staging overrides (non-secret)
└── .env.production       # Production overrides (non-secret)
```

Secrets go in AWS SSM Parameter Store or Secrets Manager, never in env files.

## Skill: /deploy

```markdown
---
name: deploy
description: Deploy to AWS with SST
---
1. Run all tests
2. Run build locally
3. Run `npx sst deploy --stage <target>`
4. Verify health endpoint responds
5. Run smoke tests against deployed URL
```

## Common Gotchas
- Lambda cold starts: use provisioned concurrency for latency-sensitive endpoints
- RDS in VPC: Lambda needs VPC config and NAT Gateway for internet access
- API Gateway has a 30s timeout (hard limit)
- S3 bucket names are globally unique
- Always use the AWS SDK v3 (not v2)
