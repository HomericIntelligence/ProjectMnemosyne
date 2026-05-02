---
name: judge-empty-response-file-path-bug
description: "Fix judge producing empty responses — variadic --allowedTools flag issue AND Claude CLI v2.1.83 empty result field bug. Use when: (1) all judges return empty responses across all models, (2) stdout_len=1 (single newline) from judge CLI calls, (3) --print mode returns empty result despite model generating tokens."
category: debugging
date: 2026-03-25
version: "3.0.0"
user-invocable: false
verification: verified-local
history: judge-empty-response-file-path-bug.history
tags:
  - judge
  - cli-bug
  - stream-json
  - empty-response
---

# Judge Empty Response — CLI Bugs and Workarounds

## Overview

| Field | Value |
| ------- | ------- |
| **Date** | 2026-03-25 |
| **Objective** | Fix LLM judge returning empty responses — two distinct root causes |
| **Outcome** | v2: stdin piping fixes variadic flag issue. v3: stream-json parsing works around CLI v2.1.83 result field bug. |
| **Verification** | verified-local (4901 tests pass, manual stream-json extraction confirmed) |
| **History** | [changelog](./judge-empty-response-file-path-bug.history) |

## When to Use

- All judge models (Opus, Sonnet, Haiku) return empty responses simultaneously
- `stdout_len=1` (single newline byte `0x0a`) from judge subprocess calls
- `--output-format json` shows `"result": ""` but `"output_tokens" > 0`
- Error: "Judge returned empty response. This may indicate the prompt was not delivered to the model."
- CLI returns exit 1: `Error: Input must be provided either through stdin or as a prompt argument`
- Positional prompt arg placed after a variadic CLI flag (--allowedTools, --tools, etc.)

## Verified Workflow

### Quick Reference

```python
# CURRENT FIX (v3.0.0): Use stream-json and parse assistant events
cmd = [
    "claude", "--model", model, "--print",
    "--output-format", "stream-json", "--verbose",
    "--dangerously-skip-permissions",
    "--allowedTools", "",
    "--system-prompt-file", str(JUDGE_SYSTEM_PROMPT_FILE),
]
result = subprocess.run(cmd, capture_output=True, text=True, timeout=1200,
                        env={k: v for k, v in os.environ.items() if k != "CLAUDECODE"},
                        input=evaluation_context)
response_text = _extract_response_from_stream(result.stdout)
```

```python
def _extract_response_from_stream(stream_output: str) -> str:
    """Extract assistant response text from stream-json output."""
    text_parts: list[str] = []
    result_text = ""
    for line in stream_output.strip().splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            event = json.loads(line)
        except json.JSONDecodeError:
            continue
        if event.get("type") == "assistant":
            message = event.get("message", {})
            for block in message.get("content", []):
                if block.get("type") == "text":
                    text_parts.append(block["text"])
        elif event.get("type") == "result":
            result_text = event.get("result", "")
    # Prefer result field if populated (CLI bug is fixed)
    if result_text.strip():
        return result_text
    return "".join(text_parts)
```

### Detailed Steps

#### Bug 1: Variadic --allowedTools Consumes Positional Args (v2.0.0)

The `--allowedTools <tools...>` flag is variadic — it consumes all subsequent non-flag arguments as tool names. When the evaluation context was placed as a positional arg after `--allowedTools ""`, the CLI parser consumed it as a tool argument, leaving no prompt.

**Fix**: Always pipe via stdin (`subprocess.run(..., input=evaluation_context)`).

#### Bug 2: CLI v2.1.83 Empty Result Field (v3.0.0)

Claude CLI v2.1.83 `--print` mode has a regression where the `result` field is always empty, despite the model generating tokens. Confirmed via:

```bash
# JSON shows result="" but output_tokens=7
claude -p "Say hello" --model claude-haiku-4-5 --output-format json < /dev/null
# → {"result":"", "output_tokens":7, "total_cost_usd":0.02}

# Stream-JSON proves the model IS responding
claude -p "Say hello" --model claude-haiku-4-5 --output-format stream-json --verbose < /dev/null
# → {"type":"assistant","message":{"content":[{"type":"text","text":"Hello!"}]}}
# → {"type":"result","result":""}  ← EMPTY
```

**Fix**: Switch to `--output-format stream-json --verbose` and extract text from `type:assistant` message events. Forward-compatible: falls back to `result` field when the CLI bug is fixed.

#### Reset Checkpoint After Failed Judges

After fixing the code, run the cleanup script to reset judge artifacts:

```bash
python3 ~/fullruns/haiku-2/reset_judges.py --apply
```

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
| --------- | ---------------- | --------------- | ---------------- |
| Pass content as positional arg (PR #1543) | Replaced temp file path with prompt content as positional CLI arg | --allowedTools is variadic and consumed the positional arg | Variadic CLI flags consume all subsequent non-flag args; use stdin piping instead |
| Test CLI from within Claude Code | Ran claude -p "hello" from bash tool | All invocations returned empty due to CLI bug (not CLAUDECODE env) | Cannot distinguish env issues from CLI bugs when testing inside Claude Code |
| Resume old checkpoint after code fix | Applied fix and resumed old experiment | Already-completed subtests had zero-score results baked in | Code fixes don't retroactively fix completed checkpoint states; must reset run states |
| Use --output-format text with stdin | Piped prompt via stdin with text output format | CLI v2.1.83 discards result content; stdout is just `\n` | Text output relies on the broken `result` field |
| Use --output-format json with stdin | Tried JSON format hoping result field works differently | Same bug: `"result": ""` with `output_tokens > 0` | The `result` field is empty regardless of output format in v2.1.83 |
| Initially blamed CLAUDECODE env var | Suspected nested Claude Code session caused empty output | Stripping CLAUDECODE didn't help; the bug is in the CLI itself | Verify with `--output-format stream-json --verbose` to see actual model output vs result field |

## Results & Parameters

### PRs

| PR | Change |
| ---- | -------- |
| #1543 | Pass prompt content instead of temp file path + diagnostics |
| #1544 | Pipe via stdin instead of positional arg (fixes variadic flag) |
| #1558 | Switch to stream-json parsing (works around CLI v2.1.83 result bug) |

### Upstream Bug

- anthropics/claude-code#39028: `--print` mode returns empty result in v2.1.83

### CLI Patterns

| Pattern | Works? | Why |
| --------- | -------- | ----- |
| `--allowedTools "" "prompt"` | No | Variadic flag consumes prompt as tool name |
| `echo "prompt" \| claude --output-format text` | No (v2.1.83) | Result field empty despite model responding |
| `echo "prompt" \| claude --output-format json` | No (v2.1.83) | Same empty result field |
| `echo "prompt" \| claude --output-format stream-json --verbose` | Yes | Parse type:assistant events for actual content |
| `subprocess.run(cmd, input=prompt)` + stream-json | Yes | Current recommended approach |

### Diagnostic Commands

```bash
# Quick test: does the CLI return content?
echo "Say hello" | env -u CLAUDECODE claude -p --model claude-haiku-4-5 \
  --output-format stream-json --verbose 2>/dev/null | \
  grep '"type":"assistant"'
# Should show content in message.content[].text

# Check result field specifically:
echo "Say hello" | env -u CLAUDECODE claude -p --model claude-haiku-4-5 \
  --output-format json 2>/dev/null | python3 -c \
  "import sys,json; d=json.load(sys.stdin); print(f'result={repr(d[\"result\"][:80])}, tokens={d[\"usage\"][\"output_tokens\"]}')"
# If result="" but tokens>0, the CLI bug is active
```

## Verified On

| Project | Context | Details |
| --------- | --------- | --------- |
| ProjectScylla | haiku-2 fullrun judge failures | v2: PRs #1543+#1544; v3: PR #1558; upstream bug anthropics/claude-code#39028 |
