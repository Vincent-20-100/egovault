# EgoVault MCP — Client Setup

Connect EgoVault to any MCP-compatible client so you can call all vault tools
(transcribe, ingest, search, generate notes…) directly from your LLM.

---

## Claude Desktop

Add the following block to your `claude_desktop_config.json`:

**Windows:** `%APPDATA%\Claude\claude_desktop_config.json`
**macOS:** `~/Library/Application Support/Claude/claude_desktop_config.json`

```json
{
  "mcpServers": {
    "egovault": {
      "command": "/absolute/path/to/egovault/.venv/Scripts/python.exe",
      "args": ["mcp/server.py"],
      "cwd": "/absolute/path/to/egovault"
    }
  }
}
```

Then **restart Claude Desktop**. The EgoVault tools appear automatically in the tool panel.

---

## Claude Code (CLI)

Add to your project or user `settings.json`:

```json
{
  "mcpServers": {
    "egovault": {
      "command": "/absolute/path/to/egovault/.venv/Scripts/python.exe",
      "args": ["mcp/server.py"],
      "cwd": "/absolute/path/to/egovault"
    }
  }
}
```

---

## Cursor / other MCP clients

Same config block — adapt the JSON key name to your client's format.
The server speaks standard MCP over stdio.

---

## Verify the connection

Once connected, ask your LLM:

> "List the EgoVault tools available."

You should see tools like `transcribe`, `search_notes`, `ingest_youtube`, `create_note`, etc.

To run a quick smoke test:

```
search_notes(query="test", limit=1)
```

If it returns without error, the server and vault are wired up correctly.

---

## Troubleshooting

**Server won't start** — make sure `config/user.yaml` and `config/install.yaml` exist.
Copy from the `.example` files and set your paths.

**`FastMCP not installed`** — run `uv sync` inside the repo to install dependencies.

**Tools not appearing** — restart the MCP client after editing the config.
