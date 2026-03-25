---
name: judge-empty-response-file-path-bug
description: "Fix judge producing empty responses when temp file path passed as CLI prompt after tool access removed. Use when: (1) all judges return empty responses across all models, (2) judge_prompt was passed as file path without Read tool access, (3) judge invocation uses --allowedTools empty string."
category: debugging
date: 2026-03-25
version: "1.0.0"
user-invocable: false
tags: []
---

# Judge Empty Response File Path Bug

## Overview

| Field | Value |
|-------|-------|
| **Date** | 2026-03-25 |
| **Objective** | Fix LLM judge returning empty responses causing "Judge response does not contain valid JSON" failures across all models |
| **Outcome** | ✅ Root cause identified and fixed in PR #1543 — temp file path passed as CLI positional arg after tool access removed |

## When to Use

- All 3 judge models (Opus, Sonnet, Haiku) return empty responses simultaneously
- Error message: `Judge response does not contain valid JSON.\nResponse:` (nothing after "Response:")
- Judge invocation uses `--allowedTools ""` (no tool access)
- Judge prompt was written to temp file and file PATH passed as positional CLI argument
- Bimodal failure: entire subtests fail uniformly, not individual runs

## Verified Workflow

### Quick Reference

```bash
# Diagnostic: test if Claude CLI receives prompt content vs file path
# Run OUTSIDE of Claude Code (CLAUDECODE=1 interferes with nested invocations)

# Test 1: Content as positional arg (correct approach)
claude --print --output-format text --model claude-haiku-4-5 \
  --dangerously-skip-permissions --allowedTools "" \
  'Return ONLY this JSON: {"test": true}' \
  > /tmp/judge_test1.txt 2>&1 < /dev/null
echo "Bytes: $(wc -c < /tmp/judge_test1.txt)"
cat /tmp/judge_test1.txt
# Expected: non-empty response with JSON

# Test 2: File path as positional arg (broken approach)
echo 'Return ONLY this JSON: {"test": true}' > /tmp/test_prompt.md
claude --print --output-format text --model claude-haiku-4-5 \
  --dangerously-skip-permissions --allowedTools "" \
  "/tmp/test_prompt.md" \
  > /tmp/judge_test2.txt 2>&1 < /dev/null
echo "Bytes: $(wc -c < /tmp/judge_test2.txt)"
cat /tmp/judge_test2.txt
# Expected: empty or confused response (model sees literal path string)
```

### Detailed Steps

#### Root Cause Analysis

1. **Identify the pattern**: All models fail identically → systemic CLI invocation issue, not model-specific
2. **Check error logs**: `Response:` followed by nothing → `result.stdout` is empty string
3. **Compare invocation patterns**: Adapter (`claude_code.py:221`) passes content directly; judge was passing file path

#### The Bug

The `_call_claude_judge()` function wrote evaluation context to a temp file and passed the **file path** as the CLI positional `[prompt]` argument:

```python
# BROKEN: passes file PATH, not content
cmd = [..., "-p", prompt_file_path]
# "-p" is --print (redundant), prompt_file_path is the [prompt] positional arg
# Model receives literal string "/tmp/judge_prompt_abc123.md"
```

This worked historically because the judge had `--allowedTools Read,Glob,Grep` and `cwd=workspace`, so the model could use the `Read` tool to open the temp file.

When commit `2c97efc3` (2026-03-22) removed tool access (`--allowedTools ""`) and `cwd`, the model could no longer read the file. It received only a file path string as its user message, with no way to access the actual content.

#### The Fix (PR #1543, commit 9421614c)

Pass evaluation context content directly as the positional argument, matching the adapter pattern:

```python
# FIXED: passes content directly
cmd = [
    "claude", "--model", model, "--print", "--output-format", "text",
    "--dangerously-skip-permissions", "--allowedTools", "",
    "--system-prompt-file", str(JUDGE_SYSTEM_PROMPT_FILE),
]

# For very large prompts (T5/T6), pipe via stdin to avoid ARG_MAX
max_arg_length = 1_000_000
stdin_input = None
if len(evaluation_context) < max_arg_length:
    cmd.append(evaluation_context)  # Content as positional arg
else:
    stdin_input = evaluation_context  # Pipe via stdin

result = subprocess.run(
    cmd, capture_output=True, text=True, timeout=1200,
    env={k: v for k, v in os.environ.items() if k != "CLAUDECODE"},
    input=stdin_input,
)
```

#### Resume Trap

**Critical**: If resuming an existing experiment checkpoint, already-completed subtests have their zero-score results baked in. The fix only applies to subtests still in `pending` state. To re-judge failed subtests, either:
- Start a fresh experiment run
- Use `rerun_judges.py` to re-judge specific subtests
- Manually reset subtest states in the checkpoint to `pending`

#### Diagnostics Added

- `_JudgeParseError` class preserves stdout/stderr when judge parsing fails
- `_save_judge_failure()` writes stdout.log and stderr.log to judge-specific directories
- Retry warning now logs `stdout_len` and `stderr_len` for debugging

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
|---------|----------------|---------------|----------------|
| Initial diagnosis | Suspected `--output-format text` vs `json` mismatch | Testing from within Claude Code gave misleading results (CLAUDECODE=1 env var interferes) | Always test CLI invocations outside of Claude Code sessions |
| Verify from shell | Ran `claude -p "hello"` from within Claude Code bash | All invocations returned empty due to nested session interference | Cannot reliably test Claude CLI from within a Claude Code session |
| Resume old run | Applied fix and resumed old checkpoint | Already-completed subtests won't re-judge — results baked into checkpoint | Code fixes don't retroactively fix completed checkpoint states |

## Results & Parameters

### Files Modified (PR #1543)

| File | Change |
|------|--------|
| `scylla/e2e/llm_judge.py` | Pass content directly as positional arg, stdin fallback for >1MB, empty-response guard |
| `scylla/e2e/stage_finalization.py` | `_JudgeParseError` with stdout/stderr, `_save_judge_failure()` helper, retry logging |

### Key Patterns

**Claude Code CLI prompt passing**:
- Positional arg is literal text content, NOT a file path reader
- `-p` is `--print` flag, NOT `--prompt`
- No `--prompt` or `--message` flag exists
- For file-based prompts: model needs Read tool access OR content must be piped/passed directly
- `stdin=subprocess.DEVNULL` prevents stdin-waiting issues
- `input=content` pipes content via stdin for large prompts

**Adapter reference** (`claude_code.py:221`):
```python
cmd.append(prompt)  # prompt is text CONTENT, not file path
```

### Test Results

- 4782 unit tests pass
- All pre-commit hooks pass (ruff, mypy, complexity, bandit)
- Manual validation pending (must run outside Claude Code)

## Verified On

| Project | Context | Details |
|---------|---------|---------|
| ProjectScylla | haiku-2 fullrun T0 judge failures | 21/24 subtests failed, fix in PR #1543 |
