# Multi-Judge Consensus Implementation - Raw Notes

## Session Context

**Date:** 2026-01-08
**Duration:** ~3 hours
**Starting point:** User request to fix Ctrl+C stack traces and add multi-judge support
**Repository:** ProjectScylla
**PR:** https://github.com/HomericIntelligence/ProjectScylla/pull/160

## User Requirements

1. **Clean Ctrl+C exit** - Currently showing stack traces from ProcessPoolExecutor child processes
2. **Multi-judge support** - Ability to run multiple judges with different models:
   - Default: 1 judge (Opus 4.5)
   - `--add-judge` adds additional judges
   - `--add-judge` (no arg): adds default Opus 4.5
   - `--add-judge sonnet-4-5`: adds Sonnet 4.5
   - `--add-judge haiku-4-5`: adds Haiku 4.5
   - Multiple `--add-judge` flags should stack
3. **Per-judge reporting** - Each judge displayed in separate table in leaf report
4. **Consensus voting** - Aggregate score used for the 'total' score
5. **Link to outputs** - Leaf report should link to each judge's output
6. **Explain deductions** - Judge prompt should explain why points are deducted

## Implementation Timeline

### Phase 1: Planning (Plan Mode)
- Used Explore subagent to understand codebase structure
- Searched skills registry for prior learnings
- Read architecture docs and judge protocol
- Created detailed implementation plan

### Phase 2: Ctrl+C Clean Exit
1. Added `BrokenProcessPool` import
2. Wrapped `ProcessPoolExecutor` in try/except in `subtest_executor.py`
3. Hit massive indentation issue - lines 1333-1449 needed 4 extra spaces
4. Fixed using Python script to add spaces
5. Added exception handlers in `runner.py`
6. Added future cancellation logic

### Phase 3: Multi-Judge CLI
1. Added `--add-judge` argument with `nargs="?"` and `action="append"`
2. Created `resolve_judge_model()` function for shortcuts
3. Updated config building to assemble judge list

### Phase 4: Data Models
1. Changed `ExperimentConfig.judge_model` → `judge_models: list[str]`
2. Created `JudgeResultSummary` dataclass
3. Updated `RunResult` to include `judges: list[JudgeResultSummary]`
4. **CRITICAL ERROR:** Hit dataclass field ordering issue - optional fields must come after required fields
5. Fixed by moving `judges` field after `workspace_path` and `logs_path`

### Phase 5: Judge Execution
1. Implemented `_compute_judge_consensus()` method
2. Modified `_run_judge()` to loop through multiple judges
3. Updated call sites to handle tuple return `(consensus_dict, judges)`
4. Added `judges` parameter to `save_run_report()` call

### Phase 6: Report Generation
1. Updated `generate_run_report()` to accept `judges` parameter
2. Added conditional logic: multi-judge vs single-judge
3. Generated consensus summary table
4. Generated per-judge tables with links to judge_XX/ directories
5. Updated `save_run_report()` to pass `judges` through

### Phase 7: Judge Prompt Update
1. Updated Phase 3 instructions to require deduction explanations
2. Updated JSON schema examples to emphasize explanation requirement

### Phase 8: Import Fixes
1. **CRITICAL ERROR:** `ImportError: cannot import name 'BrokenProcessPool' from 'concurrent.futures'`
2. Fixed: `BrokenProcessPool` is in `concurrent.futures.process`, not top-level
3. Updated both `runner.py` and `subtest_executor.py`

### Phase 9: Testing
1. Tested basic experiment startup - works correctly
2. Verified no import errors
3. Confirmed clean shutdown handling in place

### Phase 10: Unit Test Fixes
1. **CRITICAL ERROR:** Tests failed with `TypeError: ExperimentConfig.__init__() got an unexpected keyword argument 'judge_model'`
2. Root cause: `ExperimentConfig.load()` was still using old `judge_model` parameter
3. Fixed by adding backward compatibility in `load()` method:
   ```python
   if "judge_model" in data and "judge_models" not in data:
       judge_models = [data["judge_model"]]
   else:
       judge_models = data.get("judge_models", ["claude-opus-4-5-20251101"])
   ```
4. Updated `test_resume.py` fixture to use `judge_models`
5. All tests now pass

### Phase 11: Skill Documentation
1. Created comprehensive SKILL.md with workflow, failed attempts, key insights
2. Created references/notes.md with raw implementation details
3. Created .claude-plugin/plugin.json with metadata
4. Initially committed to ProjectScylla, then moved to ProjectMnemosyne

## Code Snippets

### Consensus Algorithm
```python
def _compute_judge_consensus(
    self, judges: list[JudgeResultSummary]
) -> tuple[float | None, bool | None, str | None]:
    if not judges:
        return (None, None, None)

    valid = [j for j in judges if j.score is not None]
    if not valid:
        return (None, None, None)

    # Simple average
    consensus_score = sum(j.score for j in valid) / len(valid)

    # Majority vote
    passed_votes = sum(1 for j in valid if j.passed)
    passed = passed_votes > len(valid) / 2

    # Grade from score
    if consensus_score >= 0.95:
        grade = "S"
    elif consensus_score >= 0.80:
        grade = "A"
    elif consensus_score >= 0.60:
        grade = "B"
    elif consensus_score >= 0.40:
        grade = "C"
    elif consensus_score >= 0.20:
        grade = "D"
    else:
        grade = "F"

    return (consensus_score, passed, grade)
```

### CLI Argument Pattern
```python
parser.add_argument(
    "--add-judge",
    action="append",
    nargs="?",  # Optional value
    const="claude-opus-4-5-20251101",  # Default if flag given without value
    metavar="MODEL",
    help="Add additional judge model. Use multiple times for more judges. "
         "Without argument, adds opus-4-5. Examples: --add-judge, "
         "--add-judge sonnet-4-5, --add-judge haiku-4-5",
)
```

### Clean Shutdown Pattern
```python
try:
    with ProcessPoolExecutor(max_workers=self.config.parallel_subtests) as executor:
        # Execute subtests
        for future in as_completed(futures):
            # Process results
except (KeyboardInterrupt, BrokenProcessPool):
    logger.warning("Experiment interrupted, cleaning up...")
    for future in futures:
        if not future.done():
            future.cancel()
```

### Backward Compatibility Pattern
```python
# Backward compatibility: convert old judge_model to judge_models
if "judge_model" in data and "judge_models" not in data:
    judge_models = [data["judge_model"]]
else:
    judge_models = data.get("judge_models", ["claude-opus-4-5-20251101"])
```

## Error Messages Encountered

1. **Indentation Error** (lines 1333-1449 in subtest_executor.py)
   - Symptom: Lines not indented under `with ProcessPoolExecutor` block
   - Fix: Added 4 spaces to all non-empty lines in range

2. **Dataclass Field Ordering**
   ```
   TypeError: non-default argument 'workspace_path' follows default argument 'judges'
   ```
   - Symptom: Optional field before required field
   - Fix: Move `judges` field after all required fields

3. **Import Error**
   ```
   ImportError: cannot import name 'BrokenProcessPool' from 'concurrent.futures'
   ```
   - Symptom: Wrong import location
   - Fix: `from concurrent.futures.process import BrokenProcessPool`

4. **Unit Test Failures**
   ```
   TypeError: ExperimentConfig.__init__() got an unexpected keyword argument 'judge_model'
   ```
   - Symptom: Backward compatibility missing in load() method
   - Fix: Add migration logic to convert old `judge_model` to `judge_models`

## Design Decisions

### Why Simple Average + Majority Vote?
- **Simple to understand:** No complex weighting or confidence adjustments
- **Robust:** Works even if judges disagree significantly
- **Extensible:** Can add confidence weighting later if needed

### Why Sequential Judge Execution?
- **Rate limit safety:** Running judges in parallel could hit API rate limits
- **Debugging:** Easier to trace issues when judges run sequentially
- **Cost transparency:** Clear per-judge cost tracking

### Why Separate Directories?
- **Clean organization:** Each judge has isolated output
- **Backward compatible:** Single judge still uses `judge/` directory
- **Easy linking:** Report can link to specific judge outputs

### Why Check `len(judges) > 1`?
- **Backward compatibility:** Single-judge behavior unchanged
- **Report clarity:** Don't show "consensus" for single judge
- **Zero risk:** No code paths change for existing users

## Performance Considerations

- **Sequential judges:** ~30-60s per judge (3 judges = 90-180s total)
- **Parallel subtests:** Still parallelized across subtests
- **Token usage:** Linear increase with number of judges
- **Cost impact:** 3x cost for 3 judges (expected, acceptable)

## Future Enhancements

1. **Weighted consensus:** Allow confidence-weighted averaging
2. **Tiebreaker judge:** Automatically add third judge if first two disagree
3. **Judge disagreement metrics:** Track and report inter-judge variance
4. **Parallel judge execution:** Add flag for parallel judges (with rate limit handling)
5. **Judge specialization:** Different judges for different criteria

## Commands Used

```bash
# Test experiment startup
pixi run python scripts/run_e2e_experiment.py \
    --tiers-dir tests/fixtures/tests/test-001 \
    --tiers T0 --runs 1

# Multi-judge example
pixi run python scripts/run_e2e_experiment.py \
    --tiers-dir tests/fixtures/tests/test-001 \
    --tiers T0 --runs 1 \
    --add-judge sonnet-4-5 \
    --add-judge haiku-4-5

# Check import location
python3 -c "from concurrent.futures.process import BrokenProcessPool; print('Found')"

# Run specific tests
pixi run pytest tests/unit/e2e/test_models.py::TestExperimentConfig::test_save_and_load -v
pixi run pytest tests/unit/e2e/test_resume.py::TestResumeConfigMismatch::test_config_hash_mismatch_raises_error -v
```

## Validation Status

- [x] Code compiles without errors
- [x] Experiment startup works correctly
- [x] All imports resolve successfully
- [x] Dataclass field ordering correct
- [x] Clean shutdown handling in place
- [x] Unit tests pass
- [x] Backward compatibility verified
- [ ] Full E2E test with multiple judges (needs API keys)
- [ ] Report generation with multi-judge (needs complete run)
- [ ] Consensus calculation verified (needs complete run)
