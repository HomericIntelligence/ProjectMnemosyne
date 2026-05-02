# Raw Session Notes: Python Subprocess Terminal Corruption Fix

## Session Overview
- **Date**: 2026-02-13
- **Context**: Fixing 3 bugs in batch runner: crashes, terminal corruption, poor UX
- **File**: `/home/mvillmow/Scylla2/scripts/run_e2e_batch.py` (928 lines)

## Original Issues

### Issue 1: Crash at the end
```
TypeError: unsupported format string passed to NoneType.__format__
```
- **Location**: `print_summary_table()` line 672
- **Symptom**: Summary table never renders
- **Root cause**: f-string formatting on None values

### Issue 2: Terminal corruption
- **Symptom**: After script exits, typed characters not echoed
- **Impact**: Terminal unusable, requires `stty sane` or `reset`
- **Root cause**: 6 concurrent child processes inherit stdin, Node.js CLI alters terminal settings

### Issue 3: Poor UX
- **Symptom**: Raw numbers, no test names, no guidance
- **Impact**: Developer-focused output, not user-friendly

## Debugging Process

### Step 1: Analyze JSON structure
Read `scylla/e2e/run_report.py:1015-1039` to understand actual JSON structure:
```json
{
  "summary": {
    "best_tier": "T0",
    "frontier_cop": 0.016,
    "total_cost": 0.48,
    "total_duration": 273
  },
  "children": [
    {"tier": "T0", "best_score": 1.0}
  ]
}
```

Old code tried to read:
- `report.get("best_overall_tier")` ❌ (doesn't exist)
- `report.get("frontier_cop")` ❌ (nested under summary)

### Step 2: Identify None-safety issues
Pattern that fails:
```python
best_tier = result.get("best_tier", "N/A")  # Returns None if key exists!
f"{best_tier:<10}"  # TypeError when best_tier is None
```

Solution:
```python
best_tier = result.get("best_tier") or "N/A"  # Coalesces None to "N/A"
```

### Step 3: Trace terminal corruption
- `subprocess.run()` at line 284 missing `stdin=subprocess.DEVNULL`
- 6 parallel threads each spawn `claude` CLI (Node.js)
- Node.js sets terminal to raw mode for interactive features
- If child crashes/times out, terminal settings not restored

Solution:
1. Add `stdin=subprocess.DEVNULL` to subprocess call
2. Add `_restore_terminal()` helper calling `stty sane`
3. Call from `finally` block in `main()`

## Implementation Strategy

### Phase 1: Bug Fixes
1. Fix `extract_metrics()` to read nested structure
2. Fix None-safety in `print_summary_table()`
3. Fix None-safety in status determination
4. Fix terminal corruption

### Phase 2: UX Improvements
1. Add `format_duration()` helper
2. Add test name column to summary table
3. Add aggregate metrics section
4. Add "What to Do Next" guidance
5. Add progress updates during execution

### Phase 3: Verification
1. Syntax check: `python -m py_compile`
2. Unit tests for `format_duration()`
3. None-safety test with mock data
4. `extract_metrics` test with real JSON structure
5. Pre-commit hooks

## Key Code Patterns

### Pattern 1: None-Safe Dictionary Access
```python
# WRONG
value = dict.get("key", "default")  # Returns None if key exists with None value

# RIGHT
value = dict.get("key") or "default"  # Coalesces None to default
```

### Pattern 2: Subprocess stdin Isolation
```python
# WRONG
subprocess.run(cmd, stdout=f, stderr=subprocess.STDOUT)

# RIGHT
subprocess.run(cmd, stdout=f, stderr=subprocess.STDOUT, stdin=subprocess.DEVNULL)
```

### Pattern 3: Best-Effort Cleanup
```python
def _restore_terminal():
    if sys.stdin.isatty():
        try:
            subprocess.run(["stty", "sane"], stdin=sys.stdin, check=False)
        except Exception:
            pass  # Don't crash on cleanup

def main():
    try:
        # ... work ...
    finally:
        _restore_terminal()
```

### Pattern 4: Extract from Nested JSON
```python
# Read nested structure explicitly
summary = report.get("summary", {})
best_tier = summary.get("best_tier")

# Iterate children to find matching tier
for child in report.get("children", []):
    if child.get("tier") == best_tier:
        best_score = child.get("best_score", 0.0) or 0.0
        break
```

## Testing Results

### Test 1: format_duration()
```
format_duration(0) → "N/A"
format_duration(45) → "45s"
format_duration(323) → "5m 23s"
format_duration(8123) → "2h 15m"
```
✅ All pass

### Test 2: None-safety
```python
test_result = {
    'test_id': 'test-001',
    'test_name': 'Test with None values',
    'status': 'error',
    'best_tier': None,
    'best_score': None,
    'frontier_cop': None,
    'total_cost': None,
    'total_duration': None,
}
print_summary_table([test_result])
```
✅ Displays "N/A" instead of crashing

### Test 3: extract_metrics with nested structure
```json
{
  "summary": {"best_tier": "T0", "frontier_cop": 0.016, ...},
  "children": [{"tier": "T0", "best_score": 1.0}]
}
```
```python
result = extract_metrics(Path('/tmp/test_extract_metrics'))
# {'best_tier': 'T0', 'best_score': 1.0, 'frontier_cop': 0.016, ...}
```
✅ Correct extraction

### Test 4: Pre-commit hooks
```bash
pre-commit run --files scripts/run_e2e_batch.py
```
✅ All checks pass (Ruff format, Ruff check, trailing whitespace, etc.)

## Lessons Learned

1. **Always read authoritative source**: Don't guess JSON structure, read the code that writes it
2. **None vs missing are different**: `.get("key", "default")` doesn't work when key exists with None value
3. **Subprocess isolation is critical**: Always use `stdin=subprocess.DEVNULL` for non-interactive subprocesses
4. **Cleanup must be non-fatal**: Use try/except in cleanup code, don't crash on cleanup failures
5. **Test edge cases explicitly**: Create mock data with None values to verify None-safety
6. **Progressive enhancement**: Fix bugs first, then add UX improvements
7. **Verify with real data**: Create mock JSON matching actual structure for testing

## Tool Usage

### Effective Tools
- `Read` tool: Read reference implementations (run_report.py, models.py)
- `Edit` tool: Make surgical changes to large file (928 lines)
- `Bash` tool: Run verification commands (syntax check, unit tests, pre-commit)
- Direct testing: Create mock data to verify fixes

### Avoided Pitfalls
- Didn't use Task tool: Simple, focused changes in single file
- Didn't create new files: All changes in one existing file
- Didn't skip verification: Ran all tests before declaring success

## Impact

### Before
- Crash at end: No summary table
- Terminal corruption: Unusable terminal after exit
- Poor UX: Raw numbers, no context

### After
- ✅ Summary table renders correctly with None values
- ✅ Terminal stays clean on all exit paths
- ✅ Human-friendly output: test names, readable durations, aggregate metrics, next steps guidance
- ✅ Progress updates during execution
- ✅ All pre-commit hooks pass
- ✅ All verification tests pass

## Timeline

1. Read plan and understand requirements (3 fixes + 5 UX improvements)
2. Read reference files to understand JSON structure
3. Apply 9 edits to fix all issues
4. Run syntax check → Pass
5. Test format_duration() → Pass
6. Run pre-commit → 2 errors (missing import, long line)
7. Fix errors (add timedelta import, split long line)
8. Re-run pre-commit → Pass
9. Test None-safety with mock data → Pass
10. Test extract_metrics with real structure → Pass
11. Verify help output and terminal state → Pass

**Total time**: ~10-15 minutes for all fixes, tests, and verification
