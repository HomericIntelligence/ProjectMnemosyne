# Skill: ci-deprecation-enforcement

## Overview

| Field     | Value                                                         |
|-----------|---------------------------------------------------------------|
| Date      | 2026-02-20                                                    |
| Issue     | #786                                                          |
| PR        | #834                                                          |
| Objective | Upgrade a non-blocking CI grep warning into a hard exit-1 gate |
| Outcome   | Success — count=0 confirmed, exit 1 added, all 2279 tests pass |

## When to Use

- Promoting a `::warning::` CI grep step to a `::error::` + `exit 1` enforcement gate
- Adding new `grep -v` exclusions to an existing deprecation-counting grep chain
- Verifying that the grep exclusion count is zero before turning on enforcement
- Docstring/comment references that contain the deprecated symbol but are not actual callers

## Verified Workflow

### 1. Confirm count is zero before switching to exit 1

Run the existing grep chain locally and verify it returns 0:

```bash
count=$(grep -rn "SomeDeprecatedSymbol" . \
  --include="*.py" \
  --exclude-dir=".pixi" \
  | grep -v "definition_file.py" \
  | grep -v "# deprecated" \
  | grep -v "test_file.py" \
  | wc -l)
echo "$count"
```

If count > 0, identify each hit and decide whether it is a legitimate caller
(must be removed first) or a safe reference (add a `grep -v` exclusion).

### 2. Audit remaining hits for safe-to-exclude patterns

Two categories of false positives in this session:

**Re-export files** (`__init__.py`) — the symbol is re-exported for backward
compatibility but no new code should import it directly. Exclude by path:

```bash
| grep -v "scylla/core/__init__.py" \
```

**Docstring "See also" mentions** — legacy docs list the deprecated name with
`(deprecated)` in parentheses. These are informational, not callers. Exclude
by inline annotation:

```bash
| grep -v "(deprecated)" \
```

Pattern in the source that triggers this:

```python
    # For other types in the hierarchy, see:
    # - BaseExecutionInfo (core/results.py) - Legacy dataclass (deprecated)
```

The existing `grep -v "# deprecated"` filter catches standalone comment lines
(`# deprecated`) but NOT inline annotations like `(deprecated)`. Both filters
are needed.

### 3. Update the CI step

```yaml
- name: Enforce no new deprecated BaseExecutionInfo usage
  run: |
    count=$(grep -rn "BaseExecutionInfo" . \
      --include="*.py" \
      --exclude-dir=".pixi" \
      | grep -v "scylla/core/results.py" \
      | grep -v "scylla/core/__init__.py" \
      | grep -v "# deprecated" \
      | grep -v "(deprecated)" \
      | grep -v "test_results.py" \
      | wc -l)
    echo "BaseExecutionInfo usage count (excluding definition, re-export, and tests): $count"
    if [ "$count" -gt "0" ]; then
      echo "::error::Found $count usages of deprecated BaseExecutionInfo — remove before merging"
      grep -rn "BaseExecutionInfo" . --include="*.py" --exclude-dir=".pixi" \
        | grep -v "scylla/core/results.py" \
        | grep -v "scylla/core/__init__.py" \
        | grep -v "# deprecated" \
        | grep -v "(deprecated)" \
        | grep -v "test_results.py"
      exit 1
    fi
```

Key changes from the warning step:

- Step name: "Track..." → "Enforce..."
- `::warning::` → `::error::`
- Added `exit 1` inside the `if` block
- Duplicated grep chain in the diagnostics block must also include the new exclusions

### 4. Verify tests still pass

```bash
pixi run python -m pytest tests/ -v
```

This CI change touches only `.github/workflows/test.yml` — no Python source
changes are needed and no new tests are required.

## Failed Attempts

### Relying on `grep -v "# deprecated"` to catch docstring mentions

The existing filter `grep -v "# deprecated"` only strips lines that literally
start with `# deprecated` (Python comment prefix). It does not match lines like:

```
    - BaseExecutionInfo (core/results.py) - Legacy dataclass (deprecated)
```

These are inside docstrings and use `(deprecated)` in parentheses at the end
of the line. A separate `grep -v "(deprecated)"` filter is required.

**Symptom**: count was 2 instead of 0 after adding `__init__.py` exclusion.
`grep` output showed the two docstring lines in `runner.py:70` and `result.py:21`.

## Results & Parameters

| Metric          | Value                                      |
|-----------------|--------------------------------------------|
| Tests total     | 2279                                       |
| Coverage        | 73.58% (threshold: 73%)                    |
| Count after fix | 0                                          |
| Files changed   | 1 (`.github/workflows/test.yml`)           |
| New exclusions  | `scylla/core/__init__.py`, `(deprecated)`  |

## Checklist for Deprecation Gate Promotion

- [ ] Run grep chain locally — confirm count is 0
- [ ] Identify any count > 0 hits; classify as caller (remove) or safe ref (exclude)
- [ ] Add `grep -v` exclusions for re-exports and docstring annotations
- [ ] Update step name from "Track..." to "Enforce..."
- [ ] Change `::warning::` to `::error::`
- [ ] Add `exit 1` inside the `if` block
- [ ] Mirror all new exclusions into the diagnostic grep block
- [ ] Run full test suite to confirm no regressions
