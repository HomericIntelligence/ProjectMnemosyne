---
name: judge-empty-response-file-path-bug
description: "Fix judge producing empty responses when prompt consumed by variadic --allowedTools flag. Use when: (1) all judges return empty responses across all models, (2) CLI positional arg placed after variadic flag like --allowedTools, (3) checkpoint has invalid zero-score judge results needing reset."
category: debugging
date: 2026-03-25
version: "2.0.0"
user-invocable: false
tags: []
---

# Judge Empty Response — Variadic Flag Consuming Prompt

## Overview

| Field | Value |
|-------|-------|
| **Date** | 2026-03-25 |
| **Objective** | Fix LLM judge returning empty responses causing "Judge response does not contain valid JSON" across all models |
| **Outcome** | Root cause: --allowedTools variadic flag consumed positional prompt arg. Fixed in PR #1543 + #1544. Checkpoint reset procedure for invalidated results. |

## When to Use

- All judge models (Opus, Sonnet, Haiku) return empty responses simultaneously
- Error: `Judge response does not contain valid JSON.\nResponse:` (nothing after "Response:")
- CLI returns exit 1: `Error: Input must be provided either through stdin or as a prompt argument`
- Positional prompt arg placed after a variadic CLI flag (--allowedTools, --tools, etc.)
- Checkpoint has zero-score is_valid=False judge results that need re-running

## Verified Workflow

### Quick Reference

```bash
# DIAGNOSTIC: Test if CLI receives prompt (run OUTSIDE Claude Code)
# Test stdin (correct approach):
echo 'Return JSON: {"test": true}' | \
  claude --print --output-format text --model claude-haiku-4-5 \
  --dangerously-skip-permissions --allowedTools ""
# Expected: non-empty response

# Test positional arg AFTER --allowedTools (broken):
claude --print --output-format text --model claude-haiku-4-5 \
  --dangerously-skip-permissions --allowedTools "" \
  'Return JSON: {"test": true}' < /dev/null
# Expected: exit 1 "Input must be provided"
```

### Detailed Steps

#### 1. Root Cause: Variadic --allowedTools Consumes Positional Args

The Claude Code CLI flag `--allowedTools <tools...>` is variadic -- it consumes all subsequent non-flag arguments as tool names. When the evaluation context was placed as a positional arg after `--allowedTools ""`, the CLI parser consumed it as a tool argument, leaving no prompt for the model.

```python
# BROKEN: positional arg consumed by variadic --allowedTools
cmd = [
    "claude", "--print", "--output-format", "text",
    "--allowedTools", "",          # variadic: consumes everything after
    evaluation_context,            # eaten as a tool name, not the prompt!
]
# CLI error: "Input must be provided either through stdin or as a prompt argument"
```

User-confirmed tests:
- Test 1 (positional arg after --allowedTools): EXIT 1, 0 bytes stdout
- Test 2 (file path after --allowedTools): EXIT 1, 0 bytes stdout
- Test 3 (stdin pipe): EXIT 0, response received

#### 2. The Fix: Always Pipe Via Stdin (PR #1544)

```python
# FIXED: pipe via stdin, avoids variadic flag issue AND ARG_MAX limits
cmd = [
    "claude", "--print", "--output-format", "text",
    "--dangerously-skip-permissions",
    "--allowedTools", "",
    "--system-prompt-file", str(JUDGE_SYSTEM_PROMPT_FILE),
]

result = subprocess.run(
    cmd, capture_output=True, text=True, timeout=1200,
    env={k: v for k, v in os.environ.items() if k != "CLAUDECODE"},
    input=evaluation_context,  # stdin pipe -- always works
)
```

#### 3. Reset Checkpoint for Invalid Judge Results

After fixing the code, already-completed subtests have zero-score is_valid=False results baked into the checkpoint. Reset run states to re-run the judge stage. See Results section for the reset script.

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
|---------|----------------|---------------|----------------|
| Pass content as positional arg (PR #1543) | Replaced temp file path with prompt content as positional CLI arg | --allowedTools is variadic and consumed the positional arg | Variadic CLI flags consume all subsequent non-flag args; use stdin piping instead |
| Test CLI from within Claude Code | Ran claude -p "hello" from bash tool | All invocations returned empty due to CLAUDECODE=1 env var | Never test Claude CLI invocations from within a Claude Code session |
| Resume old checkpoint after code fix | Applied fix and resumed old experiment | Already-completed subtests had zero-score results baked in | Code fixes don't retroactively fix completed checkpoint states; must reset run states |
| Diagnose as output-format text issue | Initially suspected text vs json output format mismatch | Testing was unreliable inside Claude Code; actual issue was argument parsing | Get user confirmation with external tests before committing to a theory |

## Results & Parameters

### PRs

| PR | Change |
|----|--------|
| #1543 | Pass prompt content instead of temp file path + diagnostics |
| #1544 | Pipe via stdin instead of positional arg (fixes variadic flag) |

### CLI Patterns

| Pattern | Works? | Why |
|---------|--------|-----|
| `--allowedTools "" "prompt"` | No | Variadic flag consumes prompt as tool name |
| `echo "prompt" \| claude --allowedTools ""` | Yes | Stdin not affected by variadic flags |
| `subprocess.run(cmd, input=prompt)` | Yes | Python pipes via stdin |

### State Machine Reset Reference

| Current State | Reset To | Effect |
|---------------|----------|--------|
| worktree_cleaned (run) | judge_prompt_built | Re-runs judge stage |
| aggregated (subtest) | pending | Re-dispatches subtest |
| complete (tier) | config_loaded | Re-dispatches tier |
| complete (experiment) | tiers_dispatched | Resumes experiment |

## Verified On

| Project | Context | Details |
|---------|---------|---------|
| ProjectScylla | haiku-2 fullrun T0 judge failures | 21/24 subtests failed; PRs #1543 + #1544; checkpoint reset for 15 subtests |
