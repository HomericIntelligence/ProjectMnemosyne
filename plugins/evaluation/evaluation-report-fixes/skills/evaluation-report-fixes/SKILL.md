---
name: evaluation-report-fixes
description: "Fix critical issues in E2E evaluation reports. Use when encountering UnboundLocalError crashes, missing workspace files, or broken report links."
category: evaluation
date: 2026-01-10
user-invocable: false
---

# Skill: E2E Evaluation Report Fixes

| Attribute | Value |
|-----------|-------|
| **Date** | 2026-01-10 |
| **Objective** | Fix critical issues in E2E evaluation reports and add judge model validation |
| **Outcome** | ✅ Success - All P0/P1 issues resolved |
| **Context** | ProjectScylla E2E evaluation framework |

## When to Use This Skill

Use this skill when encountering these symptoms in E2E evaluation reports:

1. **UnboundLocalError crashes** during experiment execution
2. **Workspace files not showing** in reports (empty "Workspace State" section)
3. **Judge models failing** with invalid model IDs
4. **Broken links** in reports pointing to non-existent files
5. **Missing timing data** or timing files being overwritten
6. **Inconsistent judge scoring** across runs with identical outcomes

## Problem Summary

### Issues Fixed

| Priority | Issue | Impact |
|----------|-------|--------|
| P0 | `UnboundLocalError: cannot access local variable 'json'` | Experiment crashes immediately |
| P0 | Workspace detection broken - only shows README | Reports incomplete, missing actual deliverables |
| P0 | Invalid judge model IDs cause fallback scores | Incorrect evaluation results |
| P1 | Judge timing overwritten (parent dir instead of per-judge) | Loss of per-judge performance data |
| P1 | Broken result.json links in reports | User confusion, broken navigation |

## Verified Workflow

### Fix 1: UnboundLocalError in Timing Persistence

**Problem**: `import json` inside conditional block, but `json.dump()` called outside it

**Solution**: Move import to method level

```python
# In src/scylla/e2e/subtest_executor.py
def _execute_single_run(self, ...):
    import json  # ← Move to top of method

    # Track execution timing
    subtest_id = f"{tier_id.value}_{subtest.id}"
    ...
```

**Why it works**: Python scoping - imports inside `if` blocks are only available within that block.

### Fix 2: Workspace File Detection

**Problem**: Using only `git diff HEAD~1` or `git ls-files` missed uncommitted files

**Solution**: Combine two approaches with status indicators

```python
def _get_workspace_files(workspace_path: Path) -> list[tuple[str, str]]:
    files_with_status = []

    # 1. Get committed files via git diff
    result = subprocess.run(
        ["git", "diff", "--name-only", "HEAD~1", "HEAD"],
        cwd=workspace_path, ...
    )
    if result.returncode == 0:
        for line in result.stdout.strip().split("\n"):
            if file_path and not _is_test_config_file(file_path):
                files_with_status.append((file_path, "committed"))

    # 2. Get untracked/modified files via git status
    result = subprocess.run(
        ["git", "status", "--porcelain"],
        cwd=workspace_path, ...
    )
    if result.returncode == 0:
        for line in result.stdout.strip().split("\n"):
            file_path = line[3:].strip()  # Skip status code
            if file_path and not _is_test_config_file(file_path):
                # Skip if already added as committed
                if not any(f[0] == file_path for f in files_with_status):
                    files_with_status.append((file_path, "uncommitted"))

    return sorted(files_with_status, key=lambda x: x[0])
```

**Display in report**:
```python
for file_path, status in workspace_files:
    status_indicator = "✓" if status == "committed" else "⚠"
    lines.append(f"- [{file_path}](./workspace/{file_path}) {status_indicator} {status}")
```

### Fix 3: Judge Model Validation

**Problem**: Invalid model IDs (opus-4-0, sonnet-4-0) caused judge failures

**Solution**: Validate models before experiment + add shortcuts

```python
# In scripts/run_e2e_experiment.py

def validate_model(model_id: str) -> bool:
    """Test model availability with small prompt."""
    try:
        result = subprocess.run(
            ["claude", "--model", model_id, "--output-format", "json", "Say 'OK'"],
            capture_output=True,
            text=True,
            timeout=10,
        )
        return result.returncode == 0
    except (subprocess.TimeoutExpired, FileNotFoundError, Exception):
        return False

# Add model shortcuts
shortcuts = {
    # Claude 4.5 models
    "opus-4-5": "claude-opus-4-5-20251101",
    "sonnet-4-5": "claude-sonnet-4-5-20250929",
    "haiku-4-5": "claude-haiku-4-5",  # Correct ID
    # Claude 4.0 models
    "opus-4-0": "claude-opus-4-20250514",
    "sonnet-4-0": "claude-sonnet-4-20250514",
    "haiku-4-0": "claude-haiku-4-0-20250514",
}

# Validate before adding to config
for model in args.add_judge:
    resolved_model = resolve_judge_model(model)
    logger.info(f"Validating judge model: {resolved_model}")
    if not validate_model(resolved_model):
        logger.warning(f"⚠️  Judge model '{resolved_model}' not available. Skipping.")
        continue
    config_dict["judge_models"].append(resolved_model)
```

### Fix 4: Per-Judge Timing Files

**Problem**: Single `judge/timing.json` overwritten by each judge

**Solution**: Write timing to each judge's subdirectory

```python
# In src/scylla/e2e/llm_judge.py
def run_llm_judge(..., judge_run_number: int = 1):
    import json
    import time
    from datetime import UTC, datetime

    judge_start = time.time()

    # Create judge_{N}/ subdirectory
    actual_judge_dir = judge_dir / f"judge_{judge_run_number:02d}"
    actual_judge_dir.mkdir(parents=True, exist_ok=True)

    # ... run judge ...

    # Write per-judge timing
    if actual_judge_dir:
        judge_duration = time.time() - judge_start
        timing_file = actual_judge_dir / "timing.json"
        with open(timing_file, "w") as f:
            json.dump({
                "judge_duration_seconds": judge_duration,
                "measured_at": datetime.now(UTC).isoformat(),
            }, f, indent=2)
```

**Result**: `judge/judge_01/timing.json`, `judge/judge_02/timing.json`, etc.

### Fix 5: Remove Broken result.json Links

**Problem**: Reports linked to `./judge/judge_01/result.json` but file doesn't exist

**Solution**: Remove result.json links, keep only judgment.json

```python
# In src/scylla/e2e/run_report.py
# OLD:
f"- [View judgment](./judge/judge_{judge.judge_number:02d}/judgment.json)",
f"- [View result JSON](./judge/judge_{judge.judge_number:02d}/result.json)",

# NEW:
f"- [View judgment](./judge/judge_{judge.judge_number:02d}/judgment.json)",
# (removed result.json link)
```

### Fix 6: Tiered Deduction Guidelines

**Problem**: Inconsistent scoring for identical flaws (e.g., __pycache__)

**Solution**: Add calibrated deduction tiers to judge system prompt

```markdown
### Subjective Scoring: Deduction Guidelines

#### Tier: Tiny (0.0 - 0.1 points)
Issues outside agent's direct control:
- `__pycache__` directory (Python runtime artifact)
- `.pyc` files generated by interpreter
Example: "Agent left __pycache__/" → -0.05 to -0.1

#### Tier: Small (0.1 - 0.2 points)
Minor oversights that don't affect functionality:
- Missing trailing newline
- Verbose but correct solution
Example: "Code works but uses 8 lines where 3 would suffice" → -0.15

[... Medium, Large, XLarge, Catastrophic tiers ...]

**Important**: Environmental artifacts should be treated as Tiny issues at most.
```

## Failed Attempts

### ❌ Attempt 1: Using only `git diff HEAD~1`

**What we tried**: Compare HEAD against previous commit to find agent-created files

```python
result = subprocess.run(
    ["git", "diff", "--name-only", "HEAD~1", "HEAD"],
    cwd=workspace_path, ...
)
```

**Why it failed**: Agent didn't commit files - they remained untracked. `git diff` only shows committed changes between refs, not untracked files.

**Lesson**: Need both committed (git diff) AND uncommitted (git status) detection.

### ❌ Attempt 2: Using only `git ls-files`

**What we tried**: List all tracked files as fallback

```python
result = subprocess.run(["git", "ls-files"], cwd=workspace_path, ...)
```

**Why it failed**: Only shows tracked files. Untracked files like `hello.py` were invisible.

**Lesson**: Must use `git status --porcelain` to find untracked files.

### ❌ Attempt 3: Assuming Haiku 4.5 doesn't exist

**What we tried**: Mapped `haiku-4-5` → `claude-haiku-4-0-20250514` with warning

```python
"haiku-4-5": "claude-haiku-4-0-20250514",  # Note: Haiku 4.5 doesn't exist yet
if model_shorthand == "haiku-4-5":
    logger.warning("Haiku 4.5 doesn't exist yet. Using Haiku 4.0 instead.")
```

**Why it failed**: Haiku 4.5 DOES exist as `claude-haiku-4-5` (released recently)

**Lesson**: Always verify model IDs from official documentation before hardcoding assumptions.

### ❌ Attempt 4: Keeping unused `status_code` variable

**What we tried**: Parse git status with status code extraction

```python
status_code = line[:2]  # XY status codes
file_path = line[3:].strip()
```

**Why it failed**: Variable assigned but never used - pre-commit hook caught it with ruff

**Lesson**: Don't extract data you don't need. Status indicators come from separate logic.

## Results & Parameters

### Model ID Mappings (Copy-Paste Ready)

```python
shortcuts = {
    # Claude 4.5 models
    "opus-4-5": "claude-opus-4-5-20251101",
    "sonnet-4-5": "claude-sonnet-4-5-20250929",
    "haiku-4-5": "claude-haiku-4-5",
    # Claude 4.0 models
    "opus-4-0": "claude-opus-4-20250514",
    "sonnet-4-0": "claude-sonnet-4-20250514",
    "haiku-4-0": "claude-haiku-4-0-20250514",
}
```

### Validation Timeout

```python
timeout=10  # seconds for model validation test
```

### Test Command

```bash
pixi run python scripts/run_e2e_experiment.py \
  --tiers-dir tests/fixtures/tests/test-001 \
  --tiers T0 --max-subtests 1 \
  --add-judge sonnet-4-5 --add-judge haiku-4-5 \
  --runs 3 --parallel 7 -v
```

### Expected Outcomes

| Metric | Before | After |
|--------|--------|-------|
| Crashes | UnboundLocalError immediately | ✅ No crashes |
| Workspace detection | Only README shown | ✅ Shows hello.py + status |
| Invalid judges | 3/5 fallback scores (0.7) | ✅ All valid or skipped |
| Timing files | Overwritten parent file | ✅ Per-judge files |
| Broken links | result.json 404s | ✅ No broken links |
| Score variance | 0.90, 0.89, 0.85 (inconsistent) | ✅ Target < 0.03 |

## Key Insights

1. **Python scoping matters**: Imports inside conditional blocks don't leak to outer scope
2. **Git has two file states**: Committed (tracked) and uncommitted (untracked/modified)
3. **Model validation prevents silent failures**: Test before experiment, not during
4. **Per-resource timing prevents overwrites**: Use subdirectories for parallel resources
5. **Tiered guidelines reduce variance**: Anchored deductions improve judge consistency

## Related Files

- `src/scylla/e2e/subtest_executor.py` - Main executor with timing persistence
- `src/scylla/e2e/run_report.py` - Report generation with workspace detection
- `src/scylla/e2e/llm_judge.py` - Judge runner with per-judge timing
- `scripts/run_e2e_experiment.py` - Experiment orchestrator with validation
- `config/judge/system_prompt.md` - Judge guidelines with tiered deductions

## References

- PR: #172 on HomericIntelligence/ProjectScylla
- Commit: `476af08` - fix(evaluation): Fix report issues and add judge model validation
- Haiku 4.5 announcement: https://www.anthropic.com/news/claude-haiku-4-5
