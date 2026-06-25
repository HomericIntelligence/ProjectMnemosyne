---
name: mcp-boundary-missing-argument-keyerror-translation
description: "Translate bare KeyError from missing MCP tool arguments into a typed, actionable ValueError subclass. Use when: (1) an MCP tool handler accesses arguments['key'] without a guard and a client omits that argument, (2) the mcp>=1.0 SDK does NOT validate arguments against inputSchema before calling the handler so bare dict access raises KeyError whose str() is just \"'key_name'\" — opaque to clients, (3) you want the error path to be symmetric with UnknownToolError (raise ValueError subclass, let SDK convert to structured isError response) rather than returning a TextContent error manually, (4) any MCP dispatcher that uses call_tool() decorator patterns where KeyError would surface as an opaque string."
category: architecture
date: 2026-06-20
version: "1.0.0"
user-invocable: false
verification: verified-local
tags:
  - mcp
  - stdio
  - dispatcher
  - keyerror
  - valueerror
  - missing-argument
  - error-handling
  - python
  - testability
---

# MCP Boundary: Missing Required Argument — KeyError to ValueError Translation

## Overview

| Field | Value |
| ------- | ------- |
| **Date** | 2026-06-20 |
| **Objective** | Make MCP tool handlers that require specific arguments fail with a clear, actionable error when an argument is omitted, instead of a bare opaque `KeyError`. |
| **Pattern** | Define a `MissingArgumentError(ValueError)` class mirroring `UnknownToolError(ValueError)`. Wrap dict access in `try/except KeyError as exc: raise MissingArgumentError("...") from exc`. The MCP SDK's `@server.call_tool()` decorator converts any `Exception` to a structured `isError` response — clients receive the human-readable message instead of `"'team_id'"`. |
| **Outcome** | Client receives actionable message: `"agamemnon_list_team_tasks requires a 'team_id' argument"`. Cause chain preserved via `raise ... from exc`. SDK does NOT crash. |
| **Verification** | verified-local — 9 `test_mcp_server.py` tests passing; 73/73 full suite; ruff lint clean. ProjectTelemachy issue #283, PR #284. |

## When to Use

Trigger phrases that should route to this skill:

- "MCP tool handler crashes on missing argument"
- "KeyError when argument omitted in call_tool"
- "opaque error from MCP tool — client sees just the key name"
- "MCP SDK doesn't validate against inputSchema"
- "add argument guard to MCP dispatcher"
- "missing required argument in MCP tool raises KeyError"
- "MissingArgumentError for MCP tool"
- "raise ValueError instead of returning TextContent error"

Trigger situations:

- MCP tool handler does `value = str(arguments["key"])` with no guard
- A client omits a required argument that appears in `inputSchema` but the SDK does not enforce it
- `str(KeyError("team_id"))` produces `"'team_id'"` — opaque to the MCP client
- You want error handling symmetric with an existing `UnknownToolError(ValueError)` pattern
- Tool dispatch uses the `@server.call_tool()` decorator (mcp>=1.0 SDK pattern)

## Verified Workflow

### Quick Reference

```python
# exceptions.py or top of mcp_server.py
class UnknownToolError(ValueError):
    """Raised when a tool name is not recognised by the dispatcher."""

class MissingArgumentError(ValueError):
    """Raised when a required argument is absent from the MCP tool call."""


# In Dispatcher.dispatch() or equivalent handler
async def dispatch(self, name: str, arguments: dict) -> str:
    if name == "agamemnon_list_team_tasks":
        try:
            team_id = str(arguments["team_id"])
        except KeyError as exc:
            raise MissingArgumentError(
                "agamemnon_list_team_tasks requires a 'team_id' argument"
            ) from exc
        result = await self._client.get_tasks(team_id)
        return json.dumps(result)
    raise UnknownToolError(name)
```

The `@server.call_tool()` decorator wraps the handler in `try/except Exception` and converts any exception to a structured MCP error response with `isError: true` and the exception message as the content. No explicit `TextContent` error construction is needed.

### Detailed Steps

#### 1. Audit all `arguments["key"]` accesses in the dispatcher

Find every place the handler does bare dict access:

```bash
grep -n 'arguments\[' src/telemachy/mcp_server.py
```

For each access, ask: is this argument listed in `inputSchema` as required? If yes, add a guard.

#### 2. Define `MissingArgumentError` adjacent to `UnknownToolError`

Keep both error types in the same file (or a shared exceptions module) so the error taxonomy is a single source of truth:

```python
class UnknownToolError(ValueError):
    """Raised when a tool name is not recognised by the dispatcher."""

class MissingArgumentError(ValueError):
    """Raised when a required argument is absent from the MCP tool call."""
```

Both inherit `ValueError` — the SDK converts any `Exception` to `isError`, so this is purely a semantic/diagnostic choice. `ValueError` clearly signals "caller fault" to developers reading the traceback.

#### 3. Wrap dict access with `try/except KeyError`

Replace:
```python
team_id = str(arguments["team_id"])
```

With:
```python
try:
    team_id = str(arguments["team_id"])
except KeyError as exc:
    raise MissingArgumentError(
        "agamemnon_list_team_tasks requires a 'team_id' argument"
    ) from exc
```

The message should name the tool AND the missing argument. `raise ... from exc` preserves the original `KeyError` as `__cause__` for debugging.

#### 4. Write tests that assert the client is never called

The test must verify that when the argument is missing, the underlying client method is not invoked at all:

```python
@pytest.mark.asyncio
async def test_dispatch_missing_team_id_raises(mock_client: AsyncMock) -> None:
    dispatcher = Dispatcher(mock_client)
    with pytest.raises(MissingArgumentError, match="requires a 'team_id' argument"):
        await dispatcher.dispatch("agamemnon_list_team_tasks", {})
    mock_client.get_tasks.assert_not_awaited()
```

The `assert_not_awaited()` assertion confirms the guard fires before any I/O.

#### 5. Verify lint and full test suite

```bash
pixi run ruff check src/ tests/ --fix
pixi run ruff format src/ tests/
pixi run pytest -v
```

Expected: all tests pass; ruff reports no issues.

### SDK Behavior Clarification: Does the Server Crash?

The issue description "crashes the stdio server process" is incorrect. The MCP SDK's `@server.call_tool()` decorator wraps the handler body in:

```python
try:
    result = await handler(name, arguments)
except Exception as e:
    return self._make_error_result(str(e))
```

So an unhandled `KeyError` does NOT crash the server process. The server remains running. However, `str(KeyError("team_id"))` produces `"'team_id'"` — just the quoted key name, with no context about which tool or what the argument means. This is the actual defect: the error message is opaque, not that the server crashes.

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
| --------- | ---------------- | --------------- | ---------------- |
| Return `TextContent` error response manually | Handler catches `KeyError` and returns `[TextContent(type="text", text="missing team_id")]` instead of raising | Inconsistent with `UnknownToolError` pattern (which raises); forces the happy-path return type to be `Union[str, list[TextContent]]`; requires branching callers; SDK already handles raised exceptions uniformly | Raise `ValueError` subclass instead — the SDK converts it to `isError` either way; keeps the dispatch path symmetric |
| Bare `except Exception` catch-and-re-raise as generic ValueError | `except Exception: raise ValueError("missing argument")` | Loses the cause chain (`__cause__` is `None`); traceback does not show the original `KeyError` location | Always use `raise ... from exc` to preserve the cause chain |
| Write commit message before choosing implementation approach | Issue body described two options ("return TextContent" or "raise ValueError"); commit message was drafted upfront using the TextContent wording | Reviewer caught that the actual implementation used `raise MissingArgumentError`, making the commit message inaccurate | Write the commit message after implementing, not before. Never copy the issue description verbatim when the issue presents multiple options. |
| Assume MCP SDK validates `inputSchema` before calling handler | Expected that omitting a required argument would be caught at the protocol layer | `mcp>=1.0` SDK does NOT validate `arguments` against `inputSchema` before invoking the handler; validation is the handler's responsibility | Always guard required argument access explicitly in the handler; do not rely on SDK validation |

## Results & Parameters

### Implementation in ProjectTelemachy issue #283

**File**: `src/telemachy/mcp_server.py`

**Error classes added**:

```python
class UnknownToolError(ValueError):
    """Raised when a tool name is not recognised by the dispatcher."""

class MissingArgumentError(ValueError):
    """Raised when a required argument is absent from the MCP tool call."""
```

**Guard pattern** (in `Dispatcher.dispatch`):

```python
try:
    team_id = str(arguments["team_id"])
except KeyError as exc:
    raise MissingArgumentError(
        "agamemnon_list_team_tasks requires a 'team_id' argument"
    ) from exc
```

**Test added** (`tests/test_mcp_server.py`):

```python
@pytest.mark.asyncio
async def test_dispatch_missing_team_id_raises(mock_client: AsyncMock) -> None:
    dispatcher = Dispatcher(mock_client)
    with pytest.raises(MissingArgumentError, match="requires a 'team_id' argument"):
        await dispatcher.dispatch("agamemnon_list_team_tasks", {})
    mock_client.get_tasks.assert_not_awaited()
```

### Verification commands

```bash
# Run MCP server tests only
pixi run pytest tests/test_mcp_server.py -v

# Run full suite to confirm no regressions
pixi run pytest -v

# Lint check
pixi run ruff check src/ tests/
```

Expected output:

- All 9 `test_mcp_server.py` tests pass (including the new missing-argument test)
- 73/73 full suite passes
- ruff reports 0 issues

### Error message quality comparison

| Before (bare KeyError) | After (MissingArgumentError) |
| ----------------------- | ----------------------------- |
| `"'team_id'"` | `"agamemnon_list_team_tasks requires a 'team_id' argument"` |
| Opaque — just the quoted key name | Actionable — names the tool and the missing argument |
| Client cannot distinguish missing-arg from other errors | Client receives clear, tool-specific guidance |

## Verified On

| Project | Context | Details |
| --------- | --------- | --------- |
| ProjectTelemachy | Issue #283, PR #284 | 9 unit tests passing; 73/73 full suite; ruff lint clean; `verified-local` |

## References

- [MCP Python SDK — mcp.server.Server call_tool decorator](https://github.com/modelcontextprotocol/python-sdk)
- [Related skill: architecture-mcp-server-dispatcher-seam](./architecture-mcp-server-dispatcher-seam.md) — initial MCP dispatcher seam design
- [ProjectTelemachy issue #283 — MCP server missing argument handling](https://github.com/HomericIntelligence/ProjectTelemachy/issues/283)
