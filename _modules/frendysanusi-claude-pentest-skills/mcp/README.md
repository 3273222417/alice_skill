# MCP Server Integrations

This directory contains setup documentation for MCP (Model Context Protocol) servers used by the pentest skills.

## Configured Servers

| Server | Directory | Purpose |
|--------|-----------|---------|
| Burp Suite | [burp-suite/](burp-suite/) | Web proxy, traffic interception, scanning |

## Adding a New MCP Server

1. Create a subdirectory: `mcp/<server-name>/`
2. Add a `setup.md` with installation and configuration instructions
3. Add the server config to your local `.mcp.json` (copy from `.mcp.json.example` if starting fresh)
4. Update this README table

## Configuration

The active MCP configuration lives in `.mcp.json` at the project root. This file is **gitignored** because it contains local paths and potentially API keys.

To get started:
```bash
cp .mcp.json.example .mcp.json
# Edit .mcp.json with your local paths and keys
```
