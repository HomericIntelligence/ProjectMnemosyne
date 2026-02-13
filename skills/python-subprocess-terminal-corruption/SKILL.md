# Skill: Fix Python Subprocess Terminal Corruption and None-Safe Error Handling

| Attribute | Value |
|-----------|-------|
| **Date** | 2026-02-13 |
| **Category** | debugging |
| **Objective** | Fix batch runner crashes from None values and terminal corruption from subprocess management |
| **Outcome** | ✅ All 3 bugs fixed, human-friendly output added, all tests pass |
| **Environment** | Python 3.10+, Linux/WSL2, concurrent.futures ThreadPoolExecutor |

## When to Use This Skill

Apply this skill when you encounter:

1. **Terminal corruption symptoms**:
   - After Python script exits, typed characters aren't echoed to screen
   - Terminal requires `stty sane` or `reset` to restore
   - Script spawns subprocess that may alter terminal settings (Node.js CLI, interactive tools)

2. **None-safe formatting crashes**:
   - `TypeError: unsupported format string passed to NoneType.__format__`
   - `.get("key", "default")` returns None when key exists but value is None
   - f-string formatting fails on None values

3. **JSON structure mismatch**:
   - Code reads flat keys but JSON has nested structure
   - `report.get("best_overall_tier")` returns None but data exists under `summary.best_tier`

## Root Causes

### 1. Terminal Corruption
**Cause**: `subprocess.run()` without `stdin=subprocess.DEVNULL` allows child processes to inherit terminal stdin. When child processes (like Node.js CLI tools) alter terminal settings (disable echo, raw mode) and crash/timeout, settings aren't restored.

### 2. None-Safe Formatting
**Cause**: `.get("key", "default")` returns None (not "default") when key exists but value is None:
```python
data = {"best_tier": None}
best_tier = data.get("best_tier", "N/A")  # Returns None, not "N/A"!
f"{best_tier:<10}"  # TypeError: unsupported format string
```

### 3. JSON Structure Mismatch
**Cause**: Code assumes flat structure but actual JSON is nested:
```python
# WRONG (old code)
report.get("best_overall_tier")  # None

# RIGHT (fixed code)
report.get("summary", {}).get("best_tier")  # Correct value
```

## Verified Workflow

### Fix 1: Prevent Terminal Corruption

**Add stdin isolation to subprocess calls**:
```python
import subprocess
import sys

# Add stdin=subprocess.DEVNULL to prevent child processes from inheriting terminal
result = subprocess.run(
    cmd,
    stdout=log_file,
    stderr=subprocess.STDOUT,
    stdin=subprocess.DEVNULL,  # ← KEY FIX
    text=True,
    check=False,
)
```

**Add terminal restoration on exit**:
```python
def _restore_terminal() -> None:
    """Restore terminal to sane state using stty.

    Call this on exit to fix terminal corruption from child processes.
    """
    if sys.stdin.isatty():
        try:
            subprocess.run(["stty", "sane"], stdin=sys.stdin, check=False)
        except Exception:
            pass  # Best effort, don't crash on cleanup


def main():
    try:
        # ... main logic ...
    finally:
        # Always restore terminal on exit
        _restore_terminal()
```

### Fix 2: None-Safe Dictionary Access

**Use `or` coalescing instead of `.get()` defaults**:
```python
# WRONG - Returns None when key exists with None value
best_tier = result.get("best_tier", "N/A")  # None if key exists but value is None

# RIGHT - Coalesce None to default
best_tier = result.get("best_tier") or "N/A"  # Always returns string
best_score = result.get("best_score") or 0.0  # Always returns float
```

**Special handling for values where None is meaningful**:
```python
# For values where None is distinct from missing, use explicit check
frontier_cop = result.get("frontier_cop")
cop_str = f"${frontier_cop:.4f}" if frontier_cop is not None else "N/A"
```

### Fix 3: Read Nested JSON Structure

**Match actual JSON structure in extraction logic**:
```python
def extract_metrics(result_dir: Path) -> dict | None:
    """Read report.json and extract summary metrics."""
    report_path = result_dir / "report.json"
    if not report_path.exists():
        return None

    try:
        with open(report_path) as f:
            report = json.load(f)

        # Read from nested structure: report["summary"] and report["children"]
        summary = report.get("summary", {})
        best_tier = summary.get("best_tier")
        best_score = 0.0

        # Find best_score from children array
        if best_tier:
            for child in report.get("children", []):
                if child.get("tier") == best_tier:
                    best_score = child.get("best_score", 0.0) or 0.0
                    break

        return {
            "best_tier": best_tier,
            "best_score": best_score,
            "frontier_cop": summary.get("frontier_cop"),
            "total_cost": summary.get("total_cost", 0.0),
            "total_duration": summary.get("total_duration", 0.0),
        }
    except Exception as e:
        logger.warning(f"Failed to extract metrics: {e}")
        return None
```

### Fix 4: Guard Comparisons with None Values

```python
# WRONG - Crashes if metrics.get("best_score") returns None
status = "pass" if metrics.get("best_score", 0) > 0.5 else "fail"

# RIGHT - Coalesce None before comparison
score = metrics.get("best_score") or 0.0
status = "pass" if score > 0.5 else "fail"
```

## Bonus: Human-Friendly Duration Formatting

```python
def format_duration(seconds: float) -> str:
    """Convert seconds to human-readable duration string.

    Args:
        seconds: Duration in seconds

    Returns:
        Formatted string like "5m 23s" or "2h 14m" or "N/A" for 0/None
    """
    if not seconds or seconds <= 0:
        return "N/A"

    hours = int(seconds // 3600)
    minutes = int((seconds % 3600) // 60)
    secs = int(seconds % 60)

    if hours > 0:
        return f"{hours}h {minutes}m"
    elif minutes > 0:
        return f"{minutes}m {secs}s"
    else:
        return f"{secs}s"
```

## Failed Attempts

### ❌ Attempt 1: Using `.get()` with defaults
**What we tried**: Using `.get("key", "default")` pattern throughout
**Why it failed**: When key exists but value is None, `.get()` returns None (not the default)
**Lesson**: Use `or` coalescing for None-safe defaults: `value = dict.get("key") or "default"`

### ❌ Attempt 2: Reading flat JSON structure
**What we tried**: `report.get("best_overall_tier")` and `report.get("frontier_cop")`
**Why it failed**: Actual JSON structure nests data under `summary` and `children` keys
**Lesson**: Always read reference implementation (e.g., `scylla/e2e/run_report.py`) to verify JSON structure before writing extraction logic

### ❌ Attempt 3: Relying on subprocess stdout/stderr capture
**What we tried**: Only capturing stdout/stderr, assuming terminal would stay clean
**Why it failed**: Child processes inherit stdin by default, can alter terminal settings
**Lesson**: Always use `stdin=subprocess.DEVNULL` for subprocess calls that don't need user input, especially in parallel/background execution

## Results & Parameters

### Files Modified
- `/home/mvillmow/Scylla2/scripts/run_e2e_batch.py` (only file changed)

### Key Changes
1. **Line 20**: Added `timedelta` import
2. **Lines 40-49**: Added `_restore_terminal()` helper
3. **Lines 39-63**: Added `format_duration()` helper
4. **Line 323**: Added `stdin=subprocess.DEVNULL` to subprocess.run()
5. **Lines 351-356**: None-safe status determination with `or 0.0` coalescing
6. **Lines 431-451**: Fixed `extract_metrics()` to read nested structure
7. **Lines 679-737**: None-safe `print_summary_table()` with `or` coalescing
8. **Line 1013**: Added `finally` block calling `_restore_terminal()`

### Verification Commands
```bash
# Syntax check
python -m py_compile scripts/run_e2e_batch.py

# Test format_duration
python -c "from scripts.run_e2e_batch import format_duration; \
  print('0s:', format_duration(0)); \
  print('45s:', format_duration(45)); \
  print('323s:', format_duration(323)); \
  print('8123s:', format_duration(8123))"

# Test None-safety
python -c "import sys; sys.path.insert(0, 'scripts'); \
  from run_e2e_batch import print_summary_table; \
  print_summary_table([{'test_id': 'test-001', 'test_name': 'Test', \
    'status': 'error', 'best_tier': None, 'best_score': None, \
    'frontier_cop': None, 'total_cost': None, 'total_duration': None}])"

# Test extract_metrics with nested structure
mkdir -p /tmp/test_extract_metrics
echo '{"summary": {"best_tier": "T0", "frontier_cop": 0.016, \
  "total_cost": 0.48, "total_duration": 273}, \
  "children": [{"tier": "T0", "best_score": 1.0}]}' \
  > /tmp/test_extract_metrics/report.json
python -c "import sys; sys.path.insert(0, 'scripts'); \
  from pathlib import Path; from run_e2e_batch import extract_metrics; \
  print(extract_metrics(Path('/tmp/test_extract_metrics')))"

# Pre-commit checks
pre-commit run --files scripts/run_e2e_batch.py
```

### Output
All tests pass ✅:
- `format_duration(0)` → `"N/A"`
- `format_duration(45)` → `"45s"`
- `format_duration(323)` → `"5m 23s"`
- `format_duration(8123)` → `"2h 15m"`
- None-safety test displays "N/A" instead of crashing
- extract_metrics correctly reads nested structure
- Pre-commit hooks all pass

## References

### Related Files
- Source file: `/home/mvillmow/Scylla2/scripts/run_e2e_batch.py`
- JSON structure reference: `/home/mvillmow/Scylla2/scylla/e2e/run_report.py:1015-1039`
- Test fixture model: `/home/mvillmow/Scylla2/scylla/e2e/models.py:584-614`

### Key Insights
1. **subprocess stdin inheritance**: Child processes inherit stdin by default, can corrupt terminal
2. **None vs missing distinction**: `.get("key", "default")` returns None when key exists with None value
3. **Always verify JSON structure**: Read authoritative implementation before writing extraction logic
4. **Best-effort cleanup**: Use `finally` blocks for cleanup, but make cleanup non-fatal
5. **Progressive enhancement**: Fix bugs first, then add UX improvements (human-friendly durations, progress updates)

### Documentation
- Python subprocess docs: https://docs.python.org/3/library/subprocess.html
- stty manual: `man stty`
- None coalescing pattern: https://peps.python.org/pep-0505/ (proposed but use `or` for now)
