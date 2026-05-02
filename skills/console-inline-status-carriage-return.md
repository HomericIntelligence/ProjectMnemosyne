---
name: console-inline-status-carriage-return
description: "Pattern for using carriage return (\\r) to overwrite transient terminal status lines instead of printing new lines. Use when: (1) a console tool prints repeated status updates that spam the terminal, (2) you need inline status for transient states (disconnected, reconnecting, retrying) while preserving permanent events on their own lines, (3) implementing a NATS event viewer or similar long-running console that cycles through connection states."
category: tooling
date: 2026-04-05
version: "1.0.0"
user-invocable: false
tags:
  - console
  - terminal
  - carriage-return
  - inline
  - nats
  - status
  - ansi
  - tui
---

# Console Inline Status with Carriage Return

## Overview

| Field | Value |
| ------- | ------- |
| **Date** | 2026-04-05 |
| **Objective** | Stop odysseus-console.py from printing a new line for every disconnect/reconnect/retry cycle, which spams the terminal when NATS is down |
| **Outcome** | Successful -- transient states overwrite in place via `\r`, permanent states (connected, events) print on new lines |
| **Verification** | verified-local |

## When to Use

- A console tool prints repeated transient status messages (disconnected, reconnecting, retrying) that create a wall of text when the upstream service is unavailable
- You want transient status to overwrite in place while permanent events (actual data, successful connection) each get their own line
- Building a NATS event viewer, log tailer, or any long-running terminal tool that cycles through connection states
- You need to avoid ANSI escape codes (pure `\r` carriage return works in all terminals)

## Verified Workflow

### Quick Reference

```python
import os

_last_was_inline: bool = False

def _term_width() -> int:
    """Get terminal width, fallback to 80 columns."""
    try:
        return os.get_terminal_size().columns
    except OSError:
        return 80

def print_status(state: str, detail: str = "", inline: bool = False) -> None:
    """Print a status line, optionally overwriting the current line.

    Args:
        state:  Tag like DISCONNECTED, RECONNECTING, CONNECTED
        detail: Optional detail string
        inline: If True, overwrite current line with \r instead of newline
    """
    global _last_was_inline
    line = f"[{state}]"
    if detail:
        line += f" {detail}"

    if inline:
        width = _term_width()
        padding = max(0, width - len(line))
        print(f"\r{line}{' ' * padding}", end="", flush=True)
        _last_was_inline = True
    else:
        if _last_was_inline:
            print()  # finish the inline line before printing a new one
        print(line, flush=True)
        _last_was_inline = False

def clear_inline() -> None:
    """If the last output was inline, emit a newline to finish it."""
    global _last_was_inline
    if _last_was_inline:
        print()
        _last_was_inline = False
```

### Usage in Event Loop

```python
# Transient states -- inline (overwrite in place)
print_status("DISCONNECTED", "ConnectionRefusedError", inline=True)
print_status("RECONNECTING", "Retrying in 5s...", inline=True)
print_status("DISCONNECTED", "Connection timed out", inline=True)
print_status("RECONNECTING", "Retrying in 5s...", inline=True)

# Permanent states -- newline (each gets its own line)
print_status("CONNECTED", "nats://host:4222")         # auto-finishes any inline
print_status("RECONNECTED", "nats://host:4222")

# Before printing actual events, clear any lingering inline status
clear_inline()
print(f"[event] {subject}: {payload}")
```

### Detailed Steps

1. **Add `_last_was_inline` global**: Tracks whether the last output was an inline (carriage-return) status line. This is needed so that the next non-inline print knows to emit a newline first.

2. **Add `_term_width()` helper**: Uses `os.get_terminal_size().columns` with a fallback to 80. The terminal width is needed to pad the status line with spaces so that a shorter line fully overwrites a previous longer line.

3. **Modify `print_status()` with `inline` parameter**:
   - When `inline=True`: Use `print(f"\r{line}{' ' * padding}", end="", flush=True)`. The `\r` moves the cursor to column 0, the padding fills to terminal width, `end=""` prevents a newline, and `flush=True` ensures immediate display.
   - When `inline=False`: If `_last_was_inline` is True, emit a bare `print()` first to finish the previous inline line, then print the status normally.

4. **Add `clear_inline()` helper**: Call this before printing any non-status output (e.g., actual NATS events in the `on_message` callback). It emits a newline if the last output was inline, preventing event text from being appended to or overwritten by a status line.

5. **Padding to terminal width is critical**: Without padding, if a previous inline status was 60 characters and the new one is 30 characters, the last 30 characters of the old line remain visible after `\r`. Padding with spaces to the full terminal width ensures complete overwrite.

### Which States Are Inline vs Newline

| State | Mode | Reason |
| ------- | ------ | -------- |
| DISCONNECTED | inline | Transient -- may repeat many times when NATS is down |
| RECONNECTING | inline | Transient -- immediately follows DISCONNECTED |
| "Retrying in Ns..." | inline | Transient -- countdown between attempts |
| Connection timed out | inline | Transient -- variant of disconnected |
| Connection lost | inline | Transient -- detected during operation |
| Connection closed | inline | Transient -- clean shutdown notification |
| CONNECTED | newline | Permanent -- successful connection is worth logging |
| RECONNECTED | newline | Permanent -- nats-py auto-reconnect success is worth logging |
| Actual NATS events | newline | Permanent -- these are the primary output of the tool |

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
| --------- | ---------------- | --------------- | ---------------- |
| Print every status on new line | Each state change (DISCONNECTED, RECONNECTING, etc.) printed via `print()` | Creates a wall of repeating status text when NATS is down -- hundreds of lines of `[DISCONNECTED]` / `[RECONNECTING]` / `[DISCONNECTED]` | Transient states should overwrite in place; only permanent states deserve their own line |
| Suppress transient states entirely | Skip printing DISCONNECTED/RECONNECTING, only show CONNECTED | Loses all visibility into what the console is doing during reconnection -- user sees nothing and thinks it is frozen | Transient states must be visible but should not accumulate; inline overwrite is the right balance |

## Results & Parameters

### Terminal Output When NATS Is Down

```
[RECONNECTING] Retrying in 5s...
```
(single line, overwriting in place every cycle)

### Terminal Output When NATS Comes Up

```
[RECONNECTING] Retrying in 5s...
[CONNECTED] nats://host:4222
[event] hmas.agent.heartbeat: {"agent": "agamemnon", ...}
[event] hmas.task.created: {"id": "task-42", ...}
```

### Terminal Output When NATS Goes Down During Operation

```
[event] hmas.agent.heartbeat: {"agent": "agamemnon", ...}
[DISCONNECTED] Connection lost
```
(DISCONNECTED overwrites in place, events continue on new lines when reconnected)

## Verified On

| Project | Context | Details |
| --------- | --------- | --------- |
| Odysseus | odysseus-console.py NATS event viewer | Syntax checked; inline status eliminates terminal spam during NATS downtime |

## References

- [nats-py-connection-resilience-patterns](nats-py-connection-resilience-patterns.md) -- Companion skill: clean connection lifecycle without tracebacks (prerequisite pattern)
- [python-subprocess-terminal-corruption](python-subprocess-terminal-corruption.md) -- Related: terminal state issues with subprocess (different problem, similar domain)
