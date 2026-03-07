# MCP Configuration Template

Generate a `.mcp.json` file in the project root based on the user's chosen integrations.
This file configures Model Context Protocol servers that extend Claude's capabilities.

## Structure

```json
{
  "mcpServers": {
    "<server-name>": {
      "command": "<executable>",
      "args": ["<arg1>", "<arg2>"],
      "env": {
        "ENV_VAR": "<value-or-placeholder>"
      }
    }
  }
}
```

## Common MCP Servers by Category

### Source Control
If user chose **GitHub**:
```json
"github": {
  "command": "npx",
  "args": ["-y", "@modelcontextprotocol/server-github"],
  "env": {
    "GITHUB_PERSONAL_ACCESS_TOKEN": "${GITHUB_TOKEN}"
  }
}
```

### Databases
If user chose **PostgreSQL**:
```json
"postgres": {
  "command": "npx",
  "args": ["-y", "@modelcontextprotocol/server-postgres", "${DATABASE_URL}"]
}
```

If user chose **Supabase**:
```json
"supabase": {
  "command": "npx",
  "args": ["-y", "@supabase/mcp-server-supabase@latest", "--read-only"],
  "env": {
    "SUPABASE_ACCESS_TOKEN": "${SUPABASE_ACCESS_TOKEN}"
  }
}
```

### Monitoring & Observability
If user mentioned **Sentry**:
```json
"sentry": {
  "command": "npx",
  "args": ["-y", "@sentry/mcp-server"],
  "env": {
    "SENTRY_AUTH_TOKEN": "${SENTRY_AUTH_TOKEN}"
  }
}
```

### File & Content
If user needs **filesystem access** beyond the project:
```json
"filesystem": {
  "command": "npx",
  "args": ["-y", "@modelcontextprotocol/server-filesystem", "/path/to/allowed/dir"]
}
```

### Search & Web
```json
"brave-search": {
  "command": "npx",
  "args": ["-y", "@anthropic-ai/mcp-server-brave-search"],
  "env": {
    "BRAVE_API_KEY": "${BRAVE_API_KEY}"
  }
}
```

### Design
If user mentioned **Figma**:
```json
"figma": {
  "command": "npx",
  "args": ["-y", "@anthropic-ai/mcp-server-figma"],
  "env": {
    "FIGMA_ACCESS_TOKEN": "${FIGMA_ACCESS_TOKEN}"
  }
}
```

## Generation Rules

1. Only include MCP servers for tools/services the user explicitly mentioned
2. Use environment variable references (`${VAR_NAME}`) — never hardcode secrets
3. Add corresponding variables to `.env.example` with descriptions
4. If the user chose Docker for local dev, note that MCP servers run on the host (not in containers)
5. For team projects, add `.mcp.json` to `.gitignore` and provide `.mcp.json.example` instead
6. Test that the npx packages are valid and current

## .env.example Additions

For each MCP server added, append to `.env.example`:
```bash
# MCP Server: <server-name>
# Required for Claude Code MCP integration with <service>
# Get your token at: <url-to-get-token>
<ENV_VAR>=
```
