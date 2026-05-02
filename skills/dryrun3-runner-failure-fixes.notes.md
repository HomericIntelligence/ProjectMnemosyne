# Dryrun3 Runner Failure Fixes — Raw Notes

## Session Context

- **Date**: 2026-03-07
- **Experiment**: dryrun3 (test-001/002/003 across T0-T6, 120 subtests)
- **PR**: HomericIntelligence/ProjectScylla#1469
- **Commit**: `af0bf9ab`

## Failure Counts from failure_log.txt

- 57 judge failures: judge responded with prose ("the file is empty") instead of JSON
- 22 T5 inheritance failures: `build_merged_baseline` raised `ValueError`
- 7 "Judge pipeline: SOME FAILED" — informational only (build pipeline checks, not errors)

## Exact Code Locations

### Fix 1: subtest_executor.py

File: `scylla/e2e/subtest_executor.py`
Line: ~150

```python
# Changed from:
if is_at_or_past_state(run_state, RunState.JUDGE_COMPLETE) and not ctx.judge_prompt:

# Changed to:
if is_at_or_past_state(run_state, RunState.JUDGE_PROMPT_BUILT) and not ctx.judge_prompt:
    saved_prompt = ctx.run_dir / "judge_prompt.md"
    if saved_prompt.exists():
        ctx.judge_prompt = saved_prompt.read_text()
```

### Fix 2: tier_manager.py

File: `scylla/e2e/tier_manager.py`
Lines: ~730-776

Key structure:
```python
failed_tier_ids: list[str] = []

for tier_id in inherit_from_tiers:
    # ... find result.json / best_subtest.json ...
    if not best_subtest_id:
        logger.warning(...)
        failed_tier_ids.append(tier_id.value)
        continue
    # ... find manifest ...
    if alternative is None:
        logger.warning(...)
        continue  # (no append here — manifest missing is different from tier failed)

# Post-loop:
if failed_tier_ids and len(failed_tier_ids) == len(inherit_from_tiers):
    raise ValueError(...)
```

Note: `failed_tier_ids` only tracks tiers with no `result.json`/`best_subtest.json`.
Tiers where best subtest had no manifest but an alternative was found are NOT counted
as failed — they still contribute to the merge.

### Fix 3: utils.py regex

File: `scylla/judge/utils.py`
Lines: 40-48

Old regex (wrong): `r"```(?:json)?\s*(\{[\s\S]*?\})\s*```"`
- `\{[\s\S]*?\}` is non-greedy and stops at the FIRST `}`
- For `{"score": 5, "reasoning": "..."}` this returns `{"score": 5`

New approach:
```python
code_block = re.search(r"```(?:json)?\s*([\s\S]*?)\s*```", output)
if code_block:
    block_text = code_block.group(1).strip()
    if block_text.startswith("{"):
        try:
            return cast(dict[str, Any], json.loads(block_text))
        except json.JSONDecodeError:
            pass  # Fall through to brace-matching
```
Extract the whole block content, then parse normally.
The brace-matching fallback below handles non-code-block responses.

### Fix 4: stage_finalization.py —_call_judge_with_retry

New helper extracted to reduce C901 complexity of `stage_execute_judge` and add retry:

```python
def _call_judge_with_retry(
    judge_prompt: str,
    model: str,
    workspace: Any,
    judge_num: int,
) -> tuple[str, str, str, Any]:
    json_reminder = "\n\nIMPORTANT: Respond with ONLY a valid JSON object."
    last_parse_error: Exception | None = None
    stdout = stderr = result = ""
    judge_result: Any = None
    for attempt in range(2):
        prompt = judge_prompt if attempt == 0 else judge_prompt + json_reminder
        stdout, stderr, result = _call_claude_judge(prompt, model, workspace)
        try:
            judge_result = _parse_judge_response(result)
            last_parse_error = None
            break
        except ValueError as e:
            last_parse_error = e
            if attempt == 0:
                logger.warning(
                    f"Judge {judge_num} parse failed (attempt {attempt + 1}), retrying..."
                )
    if last_parse_error:
        raise last_parse_error
    return stdout, stderr, result, judge_result
```

## Test Coverage Added

```
tests/unit/e2e/test_subtest_executor.py  +2 tests
tests/unit/e2e/test_stage_finalization.py  +4 tests
tests/unit/e2e/test_tier_manager.py  +5 tests (updated 2 + added 3)
tests/unit/judge/test_utils.py  +2 tests
```

## Pre-commit Results

All hooks passed cleanly:
- Ruff Format, Ruff Check, Mypy, C901 Complexity, Unit Test Structure
- No --no-verify used

## Partial-Failure Semantics Reminder

From CLAUDE.md:
> When multiple tiers run in parallel, a tier failure does NOT abort the experiment.
> Operators must check `tier_states` in the checkpoint, not just `experiment_state`,
> to determine whether all tiers succeeded.

The T5 fix aligns with this design: T5 should produce results even if some prerequisite
tiers failed, as long as at least one completed.