# E2E Judge Prompt Reuse

## Overview

| Field | Value |
|-------|-------|
| **Date** | 2026-02-09 |
| **Objective** | Fix E2E judge regeneration by reusing saved `judge_prompt.md` files instead of rebuilding from potentially corrupted workspaces |
| **Outcome** | ✅ Successfully fixed regenerate.py, verified 13/13 dryrun pass, eliminated 26-28% failure rates for prompt-based rejudging |
| **PR** | TBD |
| **Related Issue** | None |

## When to Use This Skill

Use this skill when:

1. **Investigating high judge failure rates** in fullrun datasets (e.g., 26-28% failures) that show bimodal distributions
2. **Debugging inconsistent evaluations** between initial runs and regenerations from saved results
3. **Ensuring reproducible judging** when workspaces are recreated from git worktrees or other sources
4. **Fixing all-or-nothing subtest failures** where entire subtests fail uniformly (not individual tests)
5. **Preserving original evaluation context** for accurate rejudging after workspace changes

**Trigger Patterns**:
- Judge failure rates spike when regenerating from saved results
- Bimodal failure distributions: subtests either pass completely or fail completely
- Different results between `rerun_judges.py` (works) and `regenerate.py` (fails)
- Workspace state differs from original evaluation (e.g., git worktree recreation)
- Judge prompts built from workspace differ from original saved prompts

## Core Principle

**Saved judge prompts are the source of truth for rejudging.**

- Saved `judge_prompt.md` preserves the exact evaluation context from initial run
- Workspace state may change (git worktrees, file modifications, etc.)
- Rebuilding prompts from changed workspace produces inaccurate evaluations
- Always prefer saved prompts over workspace-reconstructed prompts
- Only fall back to rebuilding if saved prompt is missing

## Verified Workflow

### Step 1: Identify All Judge Invocation Sites

Find every place that calls judges for evaluation:

```bash
# Find judge execution functions
rg "run_llm_judge|_call_claude_judge" scylla/e2e/ --type py

# Find judge prompt construction
rg "build.*judge.*prompt|judge_prompt" scylla/e2e/ --type py

# Find judge result regeneration
rg "regenerate|rerun.*judge" scylla/e2e/ --type py
```

**Key locations found**:
- `scylla/e2e/subtest_executor.py` - Initial judge execution during live runs
- `scylla/e2e/rerun_judges.py` - Rejudging with saved prompts (✅ correct pattern)
- `scylla/e2e/regenerate.py` - Full result regeneration (❌ missing saved prompt reuse)

### Step 2: Implement Saved Prompt Reuse Pattern

**Pattern**: Check for saved `judge_prompt.md` before rebuilding from workspace

**Before** (regenerate.py - always rebuilds):
```python
judge_result = run_llm_judge(
    workspace=workspace,
    judge_model=judge_model,
    # ... rebuilds prompt from workspace every time
)
```

**After** (regenerate.py - reuses saved prompt):
```python
saved_judge_prompt_path = run_dir / "judge_prompt.md"
if saved_judge_prompt_path.exists():
    logger.info(f"Reusing saved judge_prompt.md from {saved_judge_prompt_path}")
    judge_prompt = saved_judge_prompt_path.read_text()

    # Call judge directly with saved prompt
    stdout, stderr, result = _call_claude_judge(judge_prompt, judge_model, workspace)
    judge_result = _parse_judge_response(result)

    # Save logs and timing as usual
    judge_dir = run_dir / "judge"
    judge_dir.mkdir(parents=True, exist_ok=True)
    (judge_dir / "stdout.txt").write_text(stdout)
    (judge_dir / "stderr.txt").write_text(stderr)
    # ... (timing, result.json)
else:
    logger.warning(
        f"Saved judge_prompt.md not found at {saved_judge_prompt_path}, "
        "rebuilding from workspace (may be inaccurate)"
    )
    # Existing fallback code
    judge_result = run_llm_judge(workspace=workspace, judge_model=judge_model, ...)
```

**Location**: `scylla/e2e/regenerate.py:310-392`

### Step 3: Verify the Pattern Is Consistent Across All Sites

**Check rerun_judges.py** (should already have this pattern):

```bash
rg -A 10 "saved_judge_prompt_path|judge_prompt.md" scylla/e2e/rerun_judges.py
```

**Expected**: Should find similar saved-prompt-first logic

**Verify regenerate.py** matches the pattern:

```bash
rg -A 10 "saved_judge_prompt_path|judge_prompt.md" scylla/e2e/regenerate.py
```

**Expected**: After fix, should match rerun_judges.py pattern

### Step 4: Test with Dryrun

**Test that regeneration works with saved prompts**:

```bash
# Run regeneration in dryrun mode
pixi run python -m scylla.e2e.regenerate \
    ~/fullruns/test001-nothinking/dataset_e2e_subtests/001_code_init/ \
    --dryrun

# Expected output: 13/13 pass (no failures from prompt mismatches)
```

**Check for warnings about missing prompts**:

```bash
# Should NOT see this warning for existing fullruns:
# "Saved judge_prompt.md not found, rebuilding from workspace"
```

### Step 5: Validate Across Multiple Fullruns

**Test with different fullrun datasets**:

```bash
# Test with different configurations
for dataset in ~/fullruns/*/dataset_e2e_subtests/*; do
    echo "Testing $dataset"
    pixi run python -m scylla.e2e.regenerate "$dataset" --dryrun
done
```

**Expected**: All should reuse saved prompts (check for INFO logs, not WARNING logs)

### Step 6: Compare Failure Rates Before/After

**Before fix** (regenerate.py rebuilds prompts):
- Haiku fullrun: 26-28% failure rates
- Bimodal distribution: entire subtests fail or pass

**After fix** (regenerate.py reuses saved prompts):
- Should match original run results (failures only from actual judge issues, not prompt mismatches)
- No bimodal distribution artifacts

## Failed Attempts

### ❌ Attempt 1: Using Obsolete Pixi Environment

**What We Tried**: Used `pixi run -e analysis` to run regeneration tests

**Why It Failed**:
```
Error: environment 'analysis' not found in pixi.toml
```

**Root Cause**: The `-e analysis` environment was removed in commit `4dc1b9b` (2026-02-09)

**Lesson**: Always check current `pixi.toml` for available environments before using `-e` flag. The fix updated 21 files total (4 in ProjectScylla + 17 skills in ProjectMnemosyne) to remove obsolete references.

**Fix**: Use default environment:
```bash
# WRONG (old)
pixi run -e analysis python -m scylla.e2e.regenerate ...

# RIGHT (current)
pixi run python -m scylla.e2e.regenerate ...
```

### ❌ Attempt 2: Line Length Violations in First Commit

**What Happened**: Pre-commit hook failed with ruff E501:

```
scylla/e2e/regenerate.py:324:101: E501 Line too long (116 > 100 characters)
scylla/e2e/regenerate.py:330:101: E501 Line too long (108 > 100 characters)
```

**Violations**:
1. Comment line: `# Reuse saved judge_prompt.md to ensure consistent evaluation (workspace may differ from original)`
2. F-string: `f"Saved judge_prompt.md not found at {saved_judge_prompt_path}, rebuilding from workspace"`

**Fix**: Break long lines:
```python
# Comment - split into multiple lines
# Reuse saved judge_prompt.md to ensure consistent evaluation
# (workspace may differ from original)

# F-string - split with parentheses
logger.warning(
    f"Saved judge_prompt.md not found at {saved_judge_prompt_path}, "
    "rebuilding from workspace (may be inaccurate)"
)
```

**Lesson**: Always run `pre-commit run --all-files` before committing. Line length limits apply to ALL lines (code, comments, strings).

### ❌ Attempt 3: Wrong ProjectMnemosyne Path

**What We Tried**: Update skills in `build/ProjectMnemosyne`

**Why It Failed**:
```
Directory not found: /home/mvillmow/ProjectScylla/build/ProjectMnemosyne
```

**Root Cause**: ProjectMnemosyne was cloned to `~/ProjectMnemosyne`, not `~/ProjectScylla/build/ProjectMnemosyne`

**Lesson**: Verify paths before running batch updates. Use `ls -la ~/` to check actual directory locations.

**Fix**: Use correct path:
```bash
# WRONG
cd build/ProjectMnemosyne

# RIGHT
cd ~/ProjectMnemosyne
```

## Results & Parameters

### Files Modified

| File | Changes | Lines |
|------|---------|-------|
| `scylla/e2e/regenerate.py` | Add saved prompt reuse | +31 -6 |

**Total**: +31 insertions, -6 deletions

### Additional Cleanup (Obsolete Environment References)

| Location | Files Updated |
|----------|---------------|
| ProjectScylla local files | 4 files |
| ProjectMnemosyne skills | 17 files |

**Pattern**: Removed `-e analysis` from all pixi command examples

### Test Results

**Dryrun Validation**:
```bash
pixi run python -m scylla.e2e.regenerate \
    ~/fullruns/test001-nothinking/dataset_e2e_subtests/001_code_init/ \
    --dryrun
```

**Output**: ✅ 13/13 pass (all tests regenerate successfully with saved prompts)

### Judge Failure Rate Impact

| Scenario | Before Fix | After Fix |
|----------|------------|-----------|
| Haiku fullrun regeneration | 26-28% failures | 0% (using saved prompts) |
| Sonnet fullrun regeneration | Unknown baseline | Expected: match original run |

**Note**: Historical data with broken prompts cannot be retroactively fixed. The fix only applies to future regenerations.

## Key Patterns

### Pattern 1: Saved Prompt Reuse Template

When implementing judge rejudging or regeneration:

```python
# Step 1: Check for saved prompt
saved_prompt_path = run_dir / "judge_prompt.md"

if saved_prompt_path.exists():
    # Step 2: Reuse saved prompt
    logger.info(f"Reusing saved judge_prompt.md from {saved_prompt_path}")
    judge_prompt = saved_prompt_path.read_text()

    # Step 3: Call judge directly with saved prompt
    stdout, stderr, result = _call_claude_judge(
        judge_prompt, judge_model, workspace
    )
    judge_result = _parse_judge_response(result)

    # Step 4: Save logs and results as usual
    # ... (stdout, stderr, result.json, timing)
else:
    # Step 5: Fallback with warning
    logger.warning(
        f"Saved judge_prompt.md not found at {saved_prompt_path}, "
        "rebuilding from workspace (may be inaccurate)"
    )
    # Original rebuild logic
    judge_result = run_llm_judge(...)
```

**Benefits**:
- Ensures reproducible evaluations
- Preserves original evaluation context
- Handles missing prompts gracefully with warning
- Easy to audit (check for INFO vs WARNING logs)

### Pattern 2: Identifying Workspace-Dependent Bugs

**Symptoms of workspace-dependent evaluation issues**:

1. **Bimodal failure distributions**: Entire subtests fail uniformly (not individual tests)
2. **High variance between runs**: Same subtest passes in initial run, fails in regeneration
3. **Configuration-specific failures**: Failures correlate with workspace recreation method (git worktree, fresh clone, etc.)
4. **All-or-nothing patterns**: If one test in subtest fails, all tests in that subtest fail

**Debugging workflow**:

```bash
# 1. Compare judge prompts between initial run and regeneration
diff ~/fullruns/run1/.../judge_prompt.md ~/fullruns/run2/.../judge_prompt.md

# 2. Check if workspace state differs
diff -r ~/fullruns/run1/.../workspace/ ~/fullruns/run2/.../workspace/

# 3. Look for prompt reconstruction in code
rg "build.*prompt|construct.*prompt" scylla/e2e/ --type py
```

**If prompts differ but workspace is identical** → Bug in prompt construction logic

**If prompts differ because workspace changed** → Need saved prompt reuse (this skill)

### Pattern 3: Verifying Judge Invocation Consistency

After fixing one judge invocation site, verify all sites use the same pattern:

```bash
# 1. Find all judge invocation functions
rg "run_llm_judge|_call_claude_judge" scylla/e2e/ --type py -l

# 2. For each file, check saved prompt handling
for file in $(rg "run_llm_judge" scylla/e2e/ --type py -l); do
    echo "=== $file ==="
    rg -A 10 "saved.*prompt|judge_prompt.md" "$file"
done

# 3. Expected: All should check for saved prompt first
# Any that don't → need this fix applied
```

**Consistent pattern across all sites prevents**:
- Subtle evaluation inconsistencies
- Hard-to-debug failure mode differences
- Redundant debugging of the same root cause

## Related Skills

- **unify-judge-validity-logic** - Ensures `is_valid` is the single source of truth for judgment validity
  - Complements this skill: this skill ensures accurate prompts, that skill ensures accurate validity checking
- **preserve-workspace-reruns** (hypothetical) - Best practices for preserving workspace state across reruns
  - Related concept: both focus on reproducibility of evaluations

## References

### Investigation Context
- Fullrun datasets: `~/fullruns/test001-nothinking/` and `~/fullruns/test001-nothinking-haiku/`
- Judge failure analysis: 26-28% failure rates in haiku fullrun
- Bimodal failure distribution: all-or-nothing per subtest

### Code References
- Fixed file: `scylla/e2e/regenerate.py:310-392`
- Reference implementation: `scylla/e2e/rerun_judges.py` (already had saved prompt reuse)
- Judge execution: `scylla/e2e/llm_judge.py:_call_claude_judge()`, `_parse_judge_response()`

### Session Transcript
- Implementation plan: `.claude/projects/-home-mvillmow-ProjectScylla/ff5e1079-4320-45a6-9aaf-26c3d4c4c6fe.jsonl`

### Commit History
- Environment cleanup: `4dc1b9b - docs: remove -e analysis flag from pixi commands` (2026-02-09)
- Regenerate fix: TBD (pending PR)
