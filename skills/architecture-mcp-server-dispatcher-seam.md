---
name: architecture-mcp-server-dispatcher-seam
description: "Build a testable MCP server with a clean seam separating SDK internals from business logic. Use when: (1) adding an MCP server to a Python project using the mcp>=1.0 SDK and you need unit-testable tool dispatch, (2) deciding where to place the mcp dependency in pixi.toml (pypi-dependencies vs dependencies), (3) adding a project-scoped .mcp.json for a live MCP server (not an empty placeholder), (4) smoke-testing a stdio MCP server from the CLI without a full MCP client."
category: architecture
date: 2026-06-19
version: "1.0.0"
user-invocable: false
verification: verified-ci
tags: [mcp, dispatcher, seam, pixi, pypi-dependencies, stdio, testability, read-only, python]
---

# Architecture: MCP Server Dispatcher Seam

## Overview

| Field | Value |
| ------- | ------- |
| **Date** | 2026-06-19 |
| **Objective** | Add a read-only MCP server to ProjectTelemachy that exposes Agamemnon state queries, with unit tests that run cleanly without MCP SDK internals. |
| **Outcome** | Fully implemented and merged. 7 unit tests passing. `telemachy-mcp` console script registered. Project-scoped `.mcp.json` auto-discovered by Claude Code. |
| **Verification** | verified-ci |

## When to Use

- Adding an MCP server to any Python project using `mcp>=1.0` and needing unit-testable tool dispatch.
- Placing the `mcp` package in `pixi.toml` (must go in `[pypi-dependencies]`, not `[dependencies]`).
- Creating a live `.mcp.json` (not an empty placeholder) that registers a `stdio`-transport MCP server.
- Smoke-testing an MCP stdio server without spinning up a full MCP client.
- Enforcing a read-only invariant across an MCP module with a source-text inspection test.

## Verified Workflow

### Quick Reference

```python
# Dispatcher seam pattern (SDK-free, fully testable)
class Dispatcher:
    def __init__(self, client: AgamemnonClient) -> None:
        self._client = client

    async def dispatch(self, name: str, arguments: dict) -> str:
        if name == "list_agents":
            result = await self._client.list_agents()
            return json.dumps(result)
        raise UnknownToolError(name)

# MCP SDK adapter (thin wrapper, NOT imported by tests)
def build_server(dispatcher: Dispatcher) -> Server:
    server = Server("telemachy-mcp")

    @server.list_tools()
    async def _list_tools() -> list[Tool]:
        return _TOOLS

    @server.call_tool()
    async def _call_tool(name: str, arguments: dict) -> list[TextContent]:
        text = await dispatcher.dispatch(name, arguments)
        return [TextContent(type="text", text=text)]

    return server
```

```toml
# pixi.toml — mcp MUST go in [pypi-dependencies]
[pypi-dependencies]
mcp = ">=1.0,<2.0"
```

```json
// .mcp.json — project-scoped, checked in, env vars never hardcoded
{
  "mcpServers": {
    "telemachy": {
      "type": "stdio",
      "command": "telemachy-mcp",
      "env": {}
    }
  }
}
```

### Detailed Steps

1. Create `src/<pkg>/mcp_server.py` with three layers:

   a. `_TOOLS` — a module-level `list[Tool]` describing all tool schemas (plain dicts for `inputSchema`).

   b. `Dispatcher` class — takes only the underlying client(s) in `__init__`, no MCP SDK imports. Routes `(name, arguments)` pairs via `dispatch()`, raises `UnknownToolError` for unknown names.

   c. `build_server(dispatcher)` — imports `from mcp.server import Server`, `from mcp.types import Tool, TextContent`. Registers `@server.list_tools()` and `@server.call_tool()` decorators that delegate to `dispatcher.dispatch()`.

   d. `_run()` coroutine + `main()` entry point — `async with stdio_server() as (read, write): await server.run(read, write, ...)`.

2. Add `mcp = ">=1.0,<2.0"` to `[pypi-dependencies]` in `pixi.toml` (NOT `[dependencies]`).

3. Add `[project.scripts]` entry to `pyproject.toml`:

   ```toml
   [project.scripts]
   telemachy-mcp = "telemachy.mcp_server:main"
   ```

4. Create `.mcp.json` at repo root:

   ```json
   {
     "mcpServers": {
       "telemachy": {
         "type": "stdio",
         "command": "telemachy-mcp",
         "env": {}
       }
     }
   }
   ```

5. Write tests that only import `Dispatcher`, `UnknownToolError`, and `_TOOLS` — never `Server`, `Tool`, or `TextContent`. Mock the `AgamemnonClient` at the boundary. Include a read-only invariant test using source-text inspection.

6. Add a `justfile` recipe: `just mcp` to launch the server via `pixi run telemachy-mcp`.

### MCP SDK 1.x API Surface (Verified)

The following imports and call signatures were confirmed working with `mcp==1.x`:

```python
from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import Tool, TextContent

server = Server("server-name")

@server.list_tools()
async def _list_tools() -> list[Tool]:
    return [Tool(name="x", description="y", inputSchema={...})]

@server.call_tool()
async def _call_tool(name: str, arguments: dict) -> list[TextContent]:
    return [TextContent(type="text", text="result")]

async def _run() -> None:
    async with stdio_server() as (read, write):
        await server.run(read, write, server.create_initialization_options())
```

### Read-Only Invariant Test Pattern

```python
def test_mcp_server_has_no_write_paths():
    import inspect
    import telemachy.mcp_server as mod
    src = inspect.getsource(mod)
    forbidden = ["create_agent", "delete_agent", "start_agent", "create_team"]
    for name in forbidden:
        assert name not in src, f"Write-path symbol {name!r} found in mcp_server.py"
```

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
| --------- | ---------------- | --------------- | ---------------- |
| `pixi add 'mcp>=1.0,<2.0'` CLI | Used `pixi add` to add the mcp package | Placed it in `[dependencies]` (conda-forge channel lookup) instead of `[pypi-dependencies]`; mcp is a PyPI-only package | Always move PyPI-only packages to `[pypi-dependencies]` manually after `pixi add` |
| Pipe bare `tools/list` JSON to stdio server | Sent `{"jsonrpc":"2.0","id":1,"method":"tools/list"}` directly to `telemachy-mcp` for smoke testing | Server rejects with "Received request before initialization was complete" — MCP requires a full `initialize` handshake first | Use a proper MCP client for smoke testing, or test via `Dispatcher` unit tests; do not expect raw stdio to accept requests without handshake |
| Import `Server`/`Tool` in test files | Imported MCP SDK types directly in unit tests | Tests become brittle — any SDK install failure or API change breaks every test, even business logic tests | Only import `Dispatcher`, `UnknownToolError`, and `_TOOLS` in tests; keep SDK imports isolated to `build_server()` |
| Ruff ignored after file creation | Wrote the test file and assumed it was lint-clean | ruff flagged `I001` (unsorted imports) after the fact | Run `ruff check --fix && ruff format` immediately after writing any new Python file |

## Results & Parameters

### Configuration

`.mcp.json` at repo root with `env: {}` empty — endpoints come from the user's environment variables, never hardcoded:

```json
{
  "mcpServers": {
    "telemachy": {
      "type": "stdio",
      "command": "telemachy-mcp",
      "env": {}
    }
  }
}
```

`pixi.toml` placement:

```toml
[pypi-dependencies]
mcp = ">=1.0,<2.0"
```

`pyproject.toml` script entry:

```toml
[project.scripts]
telemachy-mcp = "telemachy.mcp_server:main"
```

### Expected Output

- `pixi run pytest tests/test_mcp_server.py -v` — all 7 tests pass (or N tests for your tool count).
- `pixi run telemachy-mcp` starts without error, waits on stdin for MCP protocol messages.
- Claude Code auto-discovers `.mcp.json` and prompts for approval before connecting.
- Source-text invariant test confirms no write-path symbols appear in `mcp_server.py`.

## Verified On

| Project | Context | Details |
| --------- | --------- | --------- |
| ProjectTelemachy | Issue #173, PR #244 | 7 unit tests passing; `telemachy-mcp` script registered; `.mcp.json` checked in |

## References

- [MCP SDK 1.x — mcp.server.Server](https://github.com/modelcontextprotocol/python-sdk)
- [Claude Code MCP docs — project-scoped .mcp.json](https://docs.anthropic.com/en/docs/claude-code/mcp)
- [Related skill: mcp-config-deliberate-absence-posture](./mcp-config-deliberate-absence-posture.md)
- [ProjectTelemachy docs/mcp.md operator guide](https://github.com/anthropics/ProjectTelemachy/blob/main/docs/mcp.md)
