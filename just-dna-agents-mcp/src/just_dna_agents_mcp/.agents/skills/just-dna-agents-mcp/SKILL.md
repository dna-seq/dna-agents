---
name: just-dna-agents-mcp
description: MCP server for DNA annotation module compiler tools. Use when configuring or running the just-dna-agents-mcp server, connecting it to Claude Code, Cursor, or other MCP clients.
---

# just-dna-agents-mcp — MCP Server

FastMCP server that exposes the just-dna-agents module compiler as MCP tools.
Lets AI coding assistants validate and compile genetics annotation modules
without importing the library directly.

## Running the server

### stdio transport (Claude Code, Cursor, Windsurf)

```bash
uv run just-dna-agents-mcp serve
# or explicitly:
uv run just-dna-agents-mcp serve --transport stdio
```

### HTTP transport (remote access, Antigravity)

```bash
uv run just-dna-agents-mcp serve --transport http --host 0.0.0.0 --port 8000
```

## Connecting to AI tools

### Claude Code / Cursor — `.mcp.json`

Add to your project's `.mcp.json`:

```json
{
  "mcpServers": {
    "just-dna-agents-mcp": {
      "type": "stdio",
      "command": "uv",
      "args": ["run", "just-dna-agents-mcp", "serve", "--transport", "stdio"]
    }
  }
}
```

### With BioContext KB (recommended)

For full variant research capabilities, also connect BioContext KB:

```json
{
  "mcpServers": {
    "biocontext-kb": {
      "type": "url",
      "url": "https://biocontext-kb.fastmcp.app/mcp"
    },
    "just-dna-agents-mcp": {
      "type": "stdio",
      "command": "uv",
      "args": ["run", "just-dna-agents-mcp", "serve", "--transport", "stdio"]
    }
  }
}
```

## Available tools

### validate_spec

Validate a module spec directory. Checks YAML structure, CSV row validity,
cross-row consistency, and weight/state directionality.

```
validate_spec(spec_dir="/path/to/my_module/")
→ {"valid": true, "errors": [], "warnings": [], "stats": {...}}
```

### compile_module

Compile a module spec directory into deployable parquet files. Validates the
spec, optionally resolves missing rsid/position via Ensembl, and produces
weights.parquet, annotations.parquet, and studies.parquet.

```
compile_module(spec_dir="/path/to/spec/", output_dir="/path/to/output/")
→ {"success": true, "output_dir": "...", "errors": [], "warnings": [], "stats": {...}}
```

### get_spec_format

Return the full module spec format reference — directory structure, file
formats, and field definitions.

### list_icons

Return valid Fomantic UI icon names and their semantic uses for
module_spec.yaml `icon` field.

### list_colors

Return valid hex colors and their semantic uses for module_spec.yaml
`color` field.

## Configuration

Environment variables (prefix `JUST_DNA_AGENTS_MCP_`):

| Variable                          | Default | Description |
|-----------------------------------|---------|-------------|
| `JUST_DNA_AGENTS_MCP_OUTPUT_DIR`       | `.`     | Default output directory for compiled modules |
| `JUST_DNA_AGENTS_MCP_RESOLVE_WITH_ENSEMBL` | `true` | Auto-resolve rsid/coordinates via Ensembl DuckDB |

Or use a `.env` file in the project root.

## CLI commands

The server also exposes direct CLI commands (no MCP needed):

```bash
# Validate a spec directory
uv run just-dna-agents-mcp validate /path/to/spec/

# Compile to parquet
uv run just-dna-agents-mcp compile /path/to/spec/ --output /path/to/output/
```
