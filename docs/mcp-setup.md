# EgoVault MCP Setup Guide

EgoVault exposes its tools via the [Model Context Protocol (MCP)](https://modelcontextprotocol.io).
Connect your LLM client to `mcp/server.py` to let it orchestrate note creation autonomously.

## Prerequisites

1. EgoVault installed and configured (`uv sync`, `init_user_dir.py` run, `config/install.yaml` filled)
2. Ollama running with `nomic-embed-text` model pulled: `ollama pull nomic-embed-text`
3. At least one source ingested via the API: `POST /api/v1/ingest/youtube`

## Claude Desktop

Config file location:
- macOS: `~/Library/Application Support/Claude/claude_desktop_config.json`
- Windows: `%APPDATA%\Claude\claude_desktop_config.json`

Add to the `mcpServers` section:

```json
{
  "mcpServers": {
    "egovault": {
      "command": "C:/path/to/egovault/.venv/Scripts/python",
      "args": ["C:/path/to/egovault/mcp/server.py"]
    }
  }
}
```

Replace `C:/path/to/egovault` with the absolute path to your egovault repository.

On macOS/Linux:
```json
{
  "mcpServers": {
    "egovault": {
      "command": "/path/to/egovault/.venv/bin/python",
      "args": ["/path/to/egovault/mcp/server.py"]
    }
  }
}
```

Restart Claude Desktop after saving. You should see "egovault" appear in the MCP tools panel.

## Cursor

Create or edit `.cursor/mcp.json` at the project root or `~/.cursor/mcp.json` globally:

```json
{
  "mcpServers": {
    "egovault": {
      "command": "/path/to/egovault/.venv/bin/python",
      "args": ["/path/to/egovault/mcp/server.py"]
    }
  }
}
```

## Windsurf / Codeium

Windsurf uses the same format as Cursor. Create `~/.codeium/windsurf/mcp_config.json`:

```json
{
  "mcpServers": {
    "egovault": {
      "command": "/path/to/egovault/.venv/bin/python",
      "args": ["/path/to/egovault/mcp/server.py"]
    }
  }
}
```

## Generic stdio (any MCP client)

EgoVault's MCP server communicates over stdio. Launch it with:

```bash
/path/to/egovault/.venv/bin/python /path/to/egovault/mcp/server.py
```

Any MCP client that supports stdio transport can connect to this process.

## Testing the connection

Once connected, ask your LLM:

> "Call get_workflow_guide() to explain how EgoVault works."

The LLM should return the EgoVault workflow guide. Then try:

> "List my sources with status rag_ready."

## Troubleshooting

**"No module named 'core'"** → Run from the egovault repo root, or ensure the venv python is used.

**"FileNotFoundError: config/install.yaml"** → Run `scripts/setup/init_user_dir.py` first and fill in `config/install.yaml`.

**"Connection refused" (Ollama)** → Start Ollama: `ollama serve`

**Tool calls silently fail** → Check that `egovault-user/data/vault.db` exists and is initialized.
