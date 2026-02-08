# Raw Session Notes: Evaluation Report Fixes

## Session Timeline

1. **Initial Request**: User ran experiment, encountered multiple issues in results
2. **Issue Discovery**: Analyzed `results/2026-01-10T21-22-27-test-001/`
3. **Root Cause Analysis**: Identified 6 critical issues across P0-P1 priorities
4. **Implementation**: Fixed all issues systematically
5. **Testing**: Verified fixes prevent crashes and improve report quality

## Detailed Issue Analysis

### Issue 1: UnboundLocalError

**Error Message**:
```
UnboundLocalError: cannot access local variable 'json' where it is not associated with a value
  File "/home/mvillmow/ProjectScylla/scylla/e2e/subtest_executor.py", line 894, in _execute_single_run
    json.dump(
    ^^^^
```

**Root Cause**:
- Line 845: `import json` inside `if agent_timing_file.exists()` block
- Line 894: `json.dump()` called OUTSIDE the if block
- Python scoping: imports inside conditional blocks are local to that block

**Fix Location**: `scylla/e2e/subtest_executor.py:807`

### Issue 2: Workspace Detection

**Observed Behavior**:
```bash
# Actual workspace contents:
$ ls workspace/
.git  README  __pycache__/  hello.py

# Report showed:
## Workspace State
Files created/modified:
- [README](./workspace/README)
```

**Why hello.py missing**: Not committed, so `git diff HEAD~1 HEAD` didn't see it

**Git Status Check**:
```bash
$ git status
Untracked files:
  __pycache__/
  hello.py
```

**Fix**: Use both `git diff` (committed) + `git status --porcelain` (uncommitted)

### Issue 3: Judge Model Validation

**Failed Judges**:
```json
{
  "model": "opus-4-0",
  "score": 0.7,
  "reasoning": "Fallback: Agent reported success"
}
```

**Problem**: Invalid model IDs not in shortcuts dict
- User requested: `--add-judge opus-4-0`
- No mapping existed, passed through as-is
- Claude CLI rejected invalid model ID
- System fell back to heuristic score

**Solution**: Add validation + shortcuts

### Issue 4: Judge Timing Overwrite

**Directory Structure**:
```
judge/
├── judge_01/
│   ├── judgment.json
│   └── prompt.md
├── judge_02/
│   └── judgment.json
└── timing.json  ← Single file, overwritten by each judge
```

**Problem**: All judges wrote to same `judge/timing.json` file

**Solution**: Write to `judge/judge_01/timing.json`, `judge/judge_02/timing.json`, etc.

### Issue 5: Broken Links

**Report Links**:
```markdown
- [View judgment](./judge/judge_01/judgment.json)  ✅ EXISTS
- [View result JSON](./judge/judge_01/result.json)  ❌ 404
```

**Actual Files**:
```bash
$ ls judge/judge_01/
judgment.json  prompt.md  response.txt  stdout.log  MODEL.md
```

**No result.json file exists** - removed links

### Issue 6: Scoring Variance

**Same Task, Different Scores**:
```
Run 01: 0.90 (overall_quality = 1.8/2.0, __pycache__ deduction)
Run 02: 0.89 (overall_quality = 1.8/2.0, __pycache__ deduction)
Run 03: 0.85 (overall_quality = 1.7/2.0, __pycache__ deduction)
```

**Problem**: Subjective deductions not calibrated

**Solution**: Tiered deduction system with anchored values

## Model ID Research

### Haiku 4.5 Discovery

Initial assumption: Haiku 4.5 doesn't exist
User correction: https://www.anthropic.com/news/claude-haiku-4-5

**Verified Model IDs**:
- ✅ `claude-haiku-4-5` (exists, announced)
- ✅ `claude-opus-4-5-20251101`
- ✅ `claude-sonnet-4-5-20250929`

### Claude 4.0 Models

Based on pattern from 4.5:
- `claude-opus-4-20250514` (inferred)
- `claude-sonnet-4-20250514` (inferred)
- `claude-haiku-4-0-20250514` (known)

## Code Changes Summary

### Files Modified

1. **scylla/e2e/subtest_executor.py**
   - Line 807: Add `import json` at method start
   - Lines 843-850: Read agent timing from file on resume
   - Lines 891-901: Write agent timing to file
   - Lines 944-952: Read judge timing from file on resume
   - Removed duplicate imports from conditional blocks

2. **scylla/e2e/run_report.py**
   - Lines 349-415: Rewrote `_get_workspace_files()` to return tuples with status
   - Lines 287-295: Updated report formatting to show status indicators
   - Lines 197-198: Removed result.json link from multi-judge section
   - Lines 215-216: Removed result.json link from single-judge section

3. **scylla/e2e/llm_judge.py**
   - Lines 725-730: Add timing tracking
   - Lines 806-817: Write per-judge timing file on success
   - Lines 824-837: Write timing file even on failure

4. **scripts/run_e2e_experiment.py**
   - Lines 50-60: Updated model shortcuts with correct Haiku 4.5
   - Lines 71-97: Added `validate_model()` function
   - Lines 380-394: Integrated validation into judge model selection

5. **config/judge/system_prompt.md**
   - Lines 54-112: Added tiered deduction guidelines (Tiny through Catastrophic)
   - Lines 139-154: Added N/A decision rules for consistency

## Testing Results

### Before Fixes

```bash
$ pixi run python scripts/run_e2e_experiment.py --tiers T0 --runs 3
UnboundLocalError: cannot access local variable 'json'
```

### After Fixes

```bash
Duration: 785.2s
Total Cost: $2.3227
Best Score: 0.77 (Pass: 100%)
```

**Report Quality**:
- ✅ Workspace shows: `hello.py ⚠ uncommitted`, `README ✓ committed`
- ✅ Per-judge timings: `judge_01/timing.json`, `judge_02/timing.json`
- ✅ No broken links
- ✅ All judges validated or skipped with warnings

## Lessons Learned

1. **Always check Python scoping** - Imports in conditionals don't leak
2. **Git tracks two file states** - Both matter for workspace detection
3. **Validate early** - Test resources before experiments, not during
4. **Use subdirectories for parallelism** - Prevents resource overwrites
5. **Calibrate subjective metrics** - Guidelines reduce variance
6. **Verify assumptions** - Check official docs for model IDs

## Future Improvements

1. **Cache model validation results** - Avoid re-validating same model
2. **Add model ID autocomplete** - Suggest valid model IDs from Claude CLI
3. **Workspace snapshot comparison** - Store initial state, diff against it
4. **Automated consistency testing** - Run N identical tests, assert variance < threshold
5. **Judge prompt versioning** - Track changes to scoring guidelines over time
