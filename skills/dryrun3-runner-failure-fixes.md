---
name: dryrun3-runner-failure-fixes
description: Fix three E2E experiment runner failure modes discovered in dryrun3
category: debugging
date: 2026-03-07
version: 1.0.0
user-invocable: false
---
# Dryrun3 Runner Failure Fixes

## Overview

| Field | Value |
| ------- | ------- |
| **Date** | 2026-03-07 |
| **Objective** | Fix three distinct failure modes from dryrun3 (test-001/002/003 across T0-T6) |
| **Outcome** | ✅ All three fixed, 140 unit tests pass, pre-commit clean, PR #1469 |
| **Failures Addressed** | 57 judge failures, 22 T5 inheritance crashes |
| **PR** | HomericIntelligence/ProjectScylla#1469 |

## When to Use This Skill

Use this skill when you observe any of these patterns in experiment runs:

1. **High judge failure count** — many subtests score 0 with prose/explanation in judge output
   instead of JSON (e.g., "the file is empty" rather than `{"score": 0, ...}`)
2. **T5 `ValueError: Cannot build merged baseline`** — T5/T6 tiers crash on inheritance
   when dependent tiers (T0–T4) failed and didn't write `result.json`/`best_subtest.json`
3. **Resumed runs produce empty judge prompts** — a run resumed after `JUDGE_COMPLETE`
   state has no prompt text because the resume threshold was set too high

**Trigger signals**:
- `failure_log.txt` shows 50+ entries with prose in judge output
- T5 stack trace: `ValueError: Cannot build merged baseline: all required tiers failed`
- `judge_prompt` is empty string in `RunContext` after resume
- Zero-score consensus across many subtests despite agent completing work

## The Three Failure Modes

### Failure 1: Empty Judge Prompt on Resume

**Root cause**: `_restore_run_context()` in `subtest_executor.py` only reloaded
`judge_prompt.md` when state was past `JUDGE_COMPLETE`. But if a run crashed during
judging (after building the prompt, before finishing), the resumed run had an empty prompt
string and re-called the judge with no context.

**Fix** (`scylla/e2e/subtest_executor.py`):

Change the reload threshold from `JUDGE_COMPLETE` to `JUDGE_PROMPT_BUILT`:

```python
# BEFORE (wrong threshold — misses runs that crashed mid-judging)
if is_at_or_past_state(run_state, RunState.JUDGE_COMPLETE) and not ctx.judge_prompt:

# AFTER (correct — reload as soon as prompt exists on disk)
if is_at_or_past_state(run_state, RunState.JUDGE_PROMPT_BUILT) and not ctx.judge_prompt:
    saved_prompt = ctx.run_dir / "judge_prompt.md"
    if saved_prompt.exists():
        ctx.judge_prompt = saved_prompt.read_text()
```

**Defense-in-depth** (`scylla/e2e/stage_finalization.py`): Before entering the judge loop,
reload from disk if `ctx.judge_prompt` is still empty, and raise a clear `ValueError` if
the file is missing rather than silently calling the judge with no context.

### Failure 2: T5 Inheritance Hard-Crash

**Root cause**: `build_merged_baseline()` in `tier_manager.py` raised `ValueError`
immediately when any dependent tier lacked `result.json`/`best_subtest.json`. In a
partial-failure experiment where T1 or T2 failed, this aborted T5 entirely.

**Fix** (`scylla/e2e/tier_manager.py`):

Replace hard `ValueError` with `logger.warning + continue`, tracking failed tiers.
Raise only if ALL dependent tiers failed:

```python
# BEFORE (hard crash on first missing tier)
if not best_subtest_id:
    raise ValueError(f"Cannot inherit from {tier_id.value}: no best subtest found")

# AFTER (skip failed tiers, only crash if all failed)
failed_tier_ids: list[str] = []

if not best_subtest_id:
    logger.warning(
        f"Cannot inherit from {tier_id.value}: no best subtest found "
        f"(tier may have failed). Skipping inheritance from {tier_id.value}."
    )
    failed_tier_ids.append(tier_id.value)
    continue

# After loop:
if failed_tier_ids and len(failed_tier_ids) == len(inherit_from_tiers):
    raise ValueError(
        f"Cannot build merged baseline: all required tiers failed "
        f"({', '.join(failed_tier_ids)}). At least one must complete for T5."
    )
```

### Failure 3: Judge JSON Parse Failures (Prose Responses)

**Root cause A** (`scylla/judge/utils.py`): Code-block regex used non-greedy
`{[\s\S]*?}` which stopped at the **first** `}` in the response — parsing only the
opening line of a multi-key JSON object.

**Fix A**: Use the code-block extraction first, then brace-match the full content:

```python
# BEFORE (stops at first '}')
code_block = re.search(r"```(?:json)?\s*(\{[\s\S]*?\})\s*```", output)

# AFTER (extract full block, then parse)
code_block = re.search(r"```(?:json)?\s*([\s\S]*?)\s*```", output)
if code_block:
    block_text = code_block.group(1).strip()
    if block_text.startswith("{"):
        try:
            return cast(dict[str, Any], json.loads(block_text))
        except json.JSONDecodeError:
            pass  # Fall through to brace-matching
```

**Root cause B** (haiku prose responses): Even with correct parsing, Haiku sometimes
responds with natural language ("the file is empty") instead of JSON entirely.

**Fix B** (`scylla/e2e/stage_finalization.py`): Extract `_call_judge_with_retry()` that
retries once with a JSON reminder appended to the prompt:

```python
def _call_judge_with_retry(judge_prompt, model, workspace, judge_num):
    json_reminder = "\n\nIMPORTANT: Respond with ONLY a valid JSON object."
    for attempt in range(2):
        prompt = judge_prompt if attempt == 0 else judge_prompt + json_reminder
        stdout, stderr, result = _call_claude_judge(prompt, model, workspace)
        try:
            judge_result = _parse_judge_response(result)
            break
        except ValueError as e:
            last_parse_error = e
            if attempt == 0:
                logger.warning(f"Judge {judge_num} parse failed, retrying...")
    if last_parse_error:
        raise last_parse_error
    return stdout, stderr, result, judge_result
```

## Verified Workflow

### Step 1: Identify failures from failure_log.txt

```bash
# Count by failure type
grep -c "prose\|not valid JSON" failure_log.txt   # judge parse failures
grep -c "ValueError.*build_merged_baseline" failure_log.txt  # T5 inheritance
grep -c "judge_prompt.*empty\|empty.*judge_prompt" failure_log.txt  # resume
```

### Step 2: Apply fixes

1. `subtest_executor.py` — change `JUDGE_COMPLETE` → `JUDGE_PROMPT_BUILT` in
   `_restore_run_context()`
2. `stage_finalization.py` — add prompt reload defense + `_call_judge_with_retry()`
3. `tier_manager.py` — replace hard `ValueError` with warning + continue loop
4. `utils.py` — fix code-block regex to extract full block content

### Step 3: Write/update tests

Each fix needs test coverage:

- `test_subtest_executor.py`: test resume at `JUDGE_PROMPT_BUILT` state reads from disk
- `test_stage_finalization.py`: test empty prompt raises, test retry on parse failure
- `test_tier_manager.py`: test partial failure continues, test all-failed raises
- `test_utils.py`: test multi-key JSON in code block, test nested JSON parsing

### Step 4: Verify

```bash
pixi run python -m pytest tests/unit/e2e/ tests/unit/judge/ -v
pre-commit run --all-files
```

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
| --------- | ---------------- | --------------- | ---------------- |
| N/A | Direct approach worked | N/A | Solution was straightforward |
## Results & Parameters

### Files Modified

| File | Change | Tests |
| ------ | -------- | ------- |
| `scylla/e2e/subtest_executor.py` | `JUDGE_COMPLETE` → `JUDGE_PROMPT_BUILT` in `_restore_run_context` | +2 |
| `scylla/e2e/stage_finalization.py` | Prompt reload defense + `_call_judge_with_retry()` | +4 |
| `scylla/e2e/tier_manager.py` | Graceful T5 skip on partial failure | +5 |
| `scylla/judge/utils.py` | Code-block regex fix (full block extraction) | +2 |

### Test Results

```
140 passed in tests/unit/e2e/ tests/unit/judge/
pre-commit: all hooks pass
```

### Observed Failure Counts Fixed

| Failure Mode | Count in dryrun3 |
| --- | --- |
| Judge prose responses (zero-score) | 57 |
| T5 inheritance ValueError | 22 |
| "Judge pipeline: SOME FAILED" (informational) | 7 (not errors) |

## Verified On

| Project | Context | Details |
| --------- | --------- | --------- |
| ProjectScylla | dryrun3 (test-001/002/003, T0-T6) | [notes.md](references/notes.md) |

## Related Skills

- **e2e-judge-prompt-reuse** — Prior fix for `regenerate.py` reusing saved `judge_prompt.md`
  (complementary: this skill fixes the live-run resume path, that fixes regeneration path)
- **resume-checkpoint-bugs** — Broader resume state machine issues
- **e2e-framework-bug-fixes** — Earlier comprehensive bug fix session (dryrun1/2)
