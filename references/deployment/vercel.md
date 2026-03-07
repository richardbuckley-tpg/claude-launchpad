# Vercel Deployment Reference

## Best For
Next.js, SvelteKit, Nuxt, and static sites. The default choice for frontend-focused projects.

## Environment Setup

### Environments
- **Preview**: auto-deployed on every PR branch
- **Production**: deployed on push to main

### Environment Variables
- Set via Vercel Dashboard > Settings > Environment Variables
- Scope to: Production, Preview, Development
- Use `vercel env pull .env.local` to sync to local

## CLAUDE.md Additions

```markdown
## Deployment
- Platform: Vercel
- Preview: automatic on PR branches
- Production: automatic on push to main
- Environment variables: Vercel Dashboard (never in code)

## Deploy Commands
- Deploy preview: vercel (or push to branch)
- Deploy production: vercel --prod (or push to main)
- Pull env vars: vercel env pull .env.local
```

## Project Config (vercel.json)

```json
{
  "framework": "nextjs",
  "buildCommand": "npm run build",
  "outputDirectory": ".next",
  "functions": {
    "api/**/*.ts": {
      "maxDuration": 30
    }
  },
  "headers": [
    {
      "source": "/api/(.*)",
      "headers": [
        { "key": "Cache-Control", "value": "no-store" }
      ]
    }
  ]
}
```

## Skill: /deploy

```markdown
---
name: deploy
description: Deploy to Vercel with pre-deployment checks
---
Before deploying:
1. Run the full test suite
2. Run type checking (tsc --noEmit)
3. Run the build locally to catch errors
4. Check for uncommitted changes
5. If all pass, push to the appropriate branch

For production:
- Ensure all tests pass
- Ensure the build succeeds
- Push to main (Vercel auto-deploys)
```

## Common Gotchas
- Serverless functions have a 10s default timeout (30s on Pro)
- Edge functions can't use Node.js native modules
- ISR revalidation only works on Vercel (not in local dev)
- Middleware runs on Edge Runtime — limited API surface
