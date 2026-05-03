---
name: mypy-per-directory-baseline
description: "Use when: (1) tracking mypy error counts per-directory with a living baseline (scripts/, tests/, scylla/); (2) removing ignore_errors = true overrides from pyproject.toml; (3) fixing quick-win single-violation mypy error codes (override, no-redef, exit-return, return-value, call-overload); (4) extending mypy coverage from a blanket-suppressed directory to full enforcement; (5) adding or updating a pre-commit validation script for mypy count enforcement."
category: testing
date: 2026-01-01
version: 2.0.0
user-invocable: false
tags:
  - mypy
  - type-checking
  - baseline
  - pre-commit
  - per-directory
  - quick-wins
  - scripts-coverage
---
# Mypy Per-Directory Baseline Skill

## Overview

| Field | Value |
| ------- | ------- |
| **Date** | 2026-02-20 (initial); 2026-02-22 (extended) |
| **Issues** | #768 (living baseline), #889 (per-directory), #767 (quick wins), #765 (scripts coverage) |
| **Objective** | Define and enforce a living mypy baseline with per-directory tracking, quick-win error code removal, and safe extension of mypy coverage to previously suppressed directories |
| **Outcome** | ✅ Success — per-directory sections in MYPY_KNOWN_ISSUES.md, 26 unit tests, all hooks passing; 5 quick-win error codes removed; scripts/ coverage extended |

Absorbed: mypy-living-baseline (v1.0.0), mypy-quick-win-fixes (v1.0.0), mypy-scripts-coverage-extension (v1.0.0) on 2026-05-03

## When to Use

Use this skill when:

- A project has incrementally-adopted mypy (some error codes disabled) and you need to track
  progress as errors are fixed over time
- You want to enforce that PRs update a "known issues" document whenever they fix type errors
- You need a self-updating markdown table that reflects actual mypy output counts per error code
- You are adding a new pre-commit validation script following the `check_type_alias_shadowing.py`
  pattern in ProjectScylla
- You have a flat `MYPY_KNOWN_ISSUES.md` baseline and want to track error counts per-directory
  (scylla/, tests/, scripts/) independently
- You are removing `ignore_errors = true` overrides from `pyproject.toml` and need to document
  per-directory baselines before CI will pass
- You need the regression guard to detect regressions in one directory without being confused
  by fixes in another
- MYPY_KNOWN_ISSUES.md shows single-violation error codes (count = 1) that are candidates for
  quick-win removal
- You want to remove error codes from `disable_error_code` in `pyproject.toml`
- You need to fix specific mypy error patterns: `override`, `no-redef`, `exit-return`,
  `return-value`, `call-overload`
- You want to extend mypy coverage from a module with a blanket `ignore_errors = true` override
  to full enforcement
- You have a `[[tool.mypy.overrides]]` block in `pyproject.toml` that suppresses a whole directory
  (e.g., `scripts.*`, `tests.*`) and want to promote it to full checking
- You need to verify whether scripts are already type-clean before removing an override

## Key Insight: Count Drift After Adding New Files

When you first measure error counts and then add new Python files (e.g., the validation script
itself), the counts will increase. Always run `--update` after the full implementation is staged
to capture the final accurate baseline before committing.

```bash
# After writing the validation script itself, re-capture counts
pixi run python scripts/check_mypy_counts.py --update
# Commit the updated MYPY_KNOWN_ISSUES.md along with the new script
```

## Key Insight: Cross-Directory Contamination in mypy Output

When running `pixi run mypy scripts/`, mypy still reports errors from `scylla/` files because
`scripts/` imports from `scylla/`. The raw mypy output mixes errors from all transitively-checked
files.

**Fix**: Filter error lines by file path prefix before counting:

```python
_FILE_PATH_RE = re.compile(r"^([^:]+\.py):\d+")

for line in proc.stdout.splitlines():
    file_match = _FILE_PATH_RE.match(line)
    if not file_match:
        continue
    file_path = file_match.group(1)
    if not file_path.startswith(path):   # path = "scripts/" etc.
        continue
    # only now count the error code
```

Without this filter, running mypy on `scripts/` produces ~67 errors (including 50+ from `scylla/`),
inflating the per-directory count dramatically.

## Key Insight: MYPY_PATHS Order Affects subprocess.run Mock Order

`MYPY_PATHS = ["scripts/", "scylla/", "tests/"]` — the order matters when mocking `subprocess.run`
in unit tests. Each call to `run_mypy_per_dir` iterates this list, so `side_effects` must be
provided in the **same order** or tests will assert against the wrong directory's counts.

```python
# CORRECT: side_effects in MYPY_PATHS order
side_effects = [scripts_mock, scylla_mock, tests_mock]

# WRONG: will assign scylla output to scripts key
side_effects = [scylla_mock, tests_mock, scripts_mock]
```

## Key Insight: Pre-commit Stash Conflict with pixi.lock

When `pixi.lock` is modified (unstaged) alongside staged Python files, pre-commit's stash/unstash
cycle conflicts with pixi's own lock file updates during hook execution. This causes the
`ruff-format-python` hook to report "Failed" even when all files are already formatted.

**Fix**: Stage `pixi.lock` as part of the commit, even if it wasn't intentionally changed:

```bash
# Add pixi.lock to avoid stash conflict during pre-commit
git add MYPY_KNOWN_ISSUES.md pyproject.toml scripts/check_mypy_counts.py \
    tests/unit/test_check_mypy_counts.py pixi.lock
git commit -m "feat(mypy): ..."
```

## Key Insight: Triage First, Then Remove Override

Always run mypy against the directory **before** removing the override to measure actual error count:

```bash
# Temporarily remove the override from pyproject.toml, then:
pixi run mypy scripts/ 2>&1
# If "Success: no issues found" — just commit the removal, no script fixes needed
# If errors appear — fix them incrementally before removing the override
```

In many cases the scripts/tests directories are already clean — the override was a precautionary
placeholder from when mypy was first adopted, not the result of actual errors.

## Key Insight: Violations May Differ from MYPY_KNOWN_ISSUES.md

When doing quick-win fixes, the actual violations may differ from what MYPY_KNOWN_ISSUES.md
documented. Always re-run mypy to get the ground truth before making changes:

```bash
pixi run python -m mypy scylla/ \
  --enable-error-code override \
  --enable-error-code no-redef \
  --enable-error-code exit-return \
  --enable-error-code return-value \
  --enable-error-code call-overload \
  2>&1 | grep "error:"
```

## Verified Workflow

### Phase 0: Establish Living Baseline (mypy-living-baseline)

#### 0.1 Measure Actual Counts by Error Code

Mypy's `disable_error_code` in `pyproject.toml` suppresses errors; to see the real baseline,
re-enable all disabled codes:

```bash
# Get per-code error counts (each flag must be separate)
pixi run mypy scripts/ scylla/ tests/ \
  --enable-error-code assignment \
  --enable-error-code operator \
  ... \
  2>&1 | grep 'error:' | grep -oP '\[([a-z][a-z0-9-]*)\]$' | sort | uniq -c | sort -rn
```

**Critical**: Use `-oP '\[([a-z][a-z0-9-]*)\]$'` (anchored at end-of-line) to avoid counting
error codes appearing in message text. An unanchored `\[[a-z][a-z0-9-]*\]` will over-count
codes like `[arg-type]` when the message contains words like `[str]`.

#### 0.2 Create MYPY_KNOWN_ISSUES.md

Include:
- A blockquote convention banner at the top
- Baseline date and roadmap issue reference
- Update instructions with `--update` flag usage
- A well-formed markdown table: `| error-code | count | description |`
- A `| **Total** | **N** | |` row
- A note explaining any error codes that appear in raw output but are excluded (e.g., codes
  from modules with `ignore_errors = true`)

#### 0.3 Write the Validation Script (scripts/check_mypy_counts.py)

Follow the `check_type_alias_shadowing.py` pattern:

```python
DISABLED_ERROR_CODES = ["assignment", "operator", ...]  # matches pyproject.toml

def parse_known_issues_table(md_path: Path) -> dict[str, int]:
    """Parse markdown table rows matching '| error-code | N | description |'."""
    ...

def run_mypy_and_count(repo_root: Path) -> dict[str, int]:
    """Run mypy with all codes re-enabled, count per code (filtered to DISABLED_ERROR_CODES)."""
    cmd = ["pixi", "run", "mypy"] + MYPY_PATHS
    for code in DISABLED_ERROR_CODES:
        cmd += ["--enable-error-code", code]
    ...

def diff_counts(documented, actual) -> list[str]:
    """Return human-readable mismatch messages."""
    ...

def update_table(md_path: Path, actual: dict[str, int]) -> None:
    """Rewrite count cells and Total row in-place."""
    ...
```

**Key regex patterns**:
- Parse table rows: `r"^\|\s*([a-z][a-z0-9-]+)\s*\|\s*(\d+)\s*\|"` (lowercase codes only, skips `**Total**`)
- Parse error lines: `r"\berror:.*\[([a-z][a-z0-9-]*)\]$"` (anchored to end of line)
- Update total row: `r"(\|\s*\*\*Total\*\*\s*\|\s*\*\*)\d+(\*\*\s*\|)"`

#### 0.4 Add Pre-commit Hook

```yaml
- id: check-mypy-counts
  name: Check Mypy Known Issue Counts
  description: >-
    Validate that MYPY_KNOWN_ISSUES.md table counts match actual mypy output.
    Update the table when fixing type errors by running:
    python scripts/check_mypy_counts.py --update
  entry: python scripts/check_mypy_counts.py
  language: system
  files: ^(scripts|scylla|tests)/.*\.py$|^MYPY_KNOWN_ISSUES\.md$
  types_or: [python, markdown]
  pass_filenames: false
```

**Note**: Use `types_or` (not `types`) to trigger on both Python files and the markdown file.

#### 0.5 Write Unit Tests

Test all four public functions. For `run_mypy_and_count`, mock `subprocess.run`:

```python
from unittest.mock import MagicMock, patch

def test_run_mypy_and_count_parses_output(tmp_path: Path) -> None:
    mock_result = MagicMock()
    mock_result.stdout = "scylla/foo.py:10: error: Msg  [arg-type]\n"
    with patch("subprocess.run", return_value=mock_result):
        counts = check_mypy_counts.run_mypy_and_count(tmp_path)
    assert counts["arg-type"] == 1
```

**Coverage note**: Tests for scripts in `scripts/` do not contribute to `--cov=scylla` coverage.
Run the full test suite (not just the new file) to verify the coverage threshold is still met.

#### 0.6 Fix Ruff D401 on Fixtures

Pytest fixture docstrings must use imperative mood (D401). Write:

```python
# WRONG - D401 violation
def valid_md(tmp_path: Path) -> Path:
    """A minimal MYPY_KNOWN_ISSUES.md..."""

# CORRECT
def valid_md(tmp_path: Path) -> Path:
    """Create a minimal MYPY_KNOWN_ISSUES.md..."""
```

### Phase 1: Remove ignore_errors Overrides (mypy-per-directory-baseline)

In `pyproject.toml`, delete both override blocks:

```toml
# DELETE these two blocks:
[[tool.mypy.overrides]]
module = "tests.*"
ignore_errors = true

[[tool.mypy.overrides]]
module = "scripts.*"
ignore_errors = true
```

### Phase 2: Extend check_mypy_counts.py with Per-Directory Logic

Add three new functions and a helper regex:

```python
# Regex to filter by file path prefix
_FILE_PATH_RE = re.compile(r"^([^:]+\.py):\d+")

# Section heading: "## Error Count Table — scylla/"
_SECTION_HEADING_RE = re.compile(r"^##\s+Error Count Table\s+—\s+(.+?)\s*$")


def run_mypy_per_dir(repo_root: Path) -> dict[str, dict[str, int]]:
    """Run mypy once per MYPY_PATH, filter errors by file prefix."""
    result: dict[str, dict[str, int]] = {}
    for path in MYPY_PATHS:
        cmd = ["pixi", "run", "mypy", path]
        for code in DISABLED_ERROR_CODES:
            cmd += ["--enable-error-code", code]
        proc = subprocess.run(cmd, capture_output=True, text=True, cwd=repo_root)
        counts: dict[str, int] = {}
        for line in proc.stdout.splitlines():
            file_match = _FILE_PATH_RE.match(line)
            if not file_match or not file_match.group(1).startswith(path):
                continue
            error_match = _ERROR_LINE_RE.search(line)
            if error_match:
                code = error_match.group(1)
                if code in DISABLED_ERROR_CODES:
                    counts[code] = counts.get(code, 0) + 1
        result[path] = counts
    return result


def parse_known_issues_per_dir(md_path: Path) -> dict[str, dict[str, int]]:
    """Parse per-directory sections from MYPY_KNOWN_ISSUES.md."""
    content = md_path.read_text(encoding="utf-8")
    result: dict[str, dict[str, int]] = {}
    current_dir: str | None = None
    for line in content.splitlines():
        heading_match = _SECTION_HEADING_RE.match(line)
        if heading_match:
            current_dir = heading_match.group(1)
            result[current_dir] = {}
            continue
        if current_dir is not None:
            row_match = _TABLE_ROW_RE.match(line)
            if row_match:
                result[current_dir][row_match.group(1)] = int(row_match.group(2))
    return result


def update_table_per_dir(md_path: Path, actual_per_dir: dict[str, dict[str, int]]) -> None:
    """Rewrite count cells per section in MYPY_KNOWN_ISSUES.md."""
    content = md_path.read_text(encoding="utf-8")
    lines = content.splitlines(keepends=True)
    new_lines: list[str] = []
    current_dir: str | None = None
    current_actual: dict[str, int] = {}
    for line in lines:
        heading_match = _SECTION_HEADING_RE.match(line)
        if heading_match:
            current_dir = heading_match.group(1)
            current_actual = actual_per_dir.get(current_dir, {})
            new_lines.append(line)
            continue
        row_match = _TABLE_ROW_RE.match(line)
        if row_match and current_dir is not None:
            code = row_match.group(1)
            new_count = current_actual.get(code, 0)
            line = re.sub(
                r"(\|\s*" + re.escape(code) + r"\s*\|\s*)\d+(\s*\|)",
                lambda m, c=new_count: f"{m.group(1)}{c}{m.group(2)}",
                line,
            )
        elif _TOTAL_ROW_RE.search(line) and current_dir is not None:
            total = sum(current_actual.get(c, 0) for c in DISABLED_ERROR_CODES)
            line = _TOTAL_ROW_RE.sub(rf"\g<1>{total}\g<2>", line)
        new_lines.append(line)
    md_path.write_text("".join(new_lines), encoding="utf-8")
```

### Phase 3: Update run_mypy_and_count for Backward Compatibility

```python
def run_mypy_and_count(repo_root: Path) -> dict[str, int]:
    """Aggregate per-directory counts for backward compat."""
    counts_per_dir = run_mypy_per_dir(repo_root)
    merged: dict[str, int] = {}
    for dir_counts in counts_per_dir.values():
        for code, count in dir_counts.items():
            merged[code] = merged.get(code, 0) + count
    return merged
```

### Phase 4: Restructure MYPY_KNOWN_ISSUES.md

Replace the single `## Error Count Table` heading with per-directory sections:

```markdown
## Error Count Table — scylla/

| Error Code    | Count | Description |
|---------------|-------|-------------|
| arg-type      | 0     | ...         |
| **Total**     | **0** |             |

## Error Count Table — tests/

| Error Code    | Count | Description |
|---------------|-------|-------------|
| arg-type      | 0     | ...         |
| **Total**     | **0** |             |

## Error Count Table — scripts/

| Error Code    | Count | Description |
|---------------|-------|-------------|
| arg-type      | 0     | ...         |
| **Total**     | **0** |             |
```

Then run `--update` to populate the actual counts:

```bash
pixi run python scripts/check_mypy_counts.py --update
```

### Phase 5: Quick-Win Single-Violation Error Code Fixes

#### `exit-return` — `__exit__` return type

```python
# WRONG: bool return type triggers exit-return when method always returns False
def __exit__(self, exc_type, exc_val, exc_tb) -> bool:
    ...
    return False  # mypy: "bool" is invalid as return type for "__exit__"

# CORRECT: Use None (never suppresses exceptions) or Literal[False]
def __exit__(self, exc_type, exc_val, exc_tb) -> None:
    ...
    # Return None (False-y) to not suppress exceptions
```

#### `override` — pydantic `model_validate` incompatible override

Do NOT try to match pydantic's exact `model_validate` signature — it uses complex keyword-only
params that are hard to replicate. Instead, **rename the method** to avoid the override entirely:

```python
# WRONG: Incompatible override of pydantic BaseModel.model_validate
class MyModel(BaseModel):
    @classmethod
    def model_validate(cls, data: dict[str, Any]) -> MyModel:  # override error
        ...

# CORRECT: Rename to a custom method name
class MyModel(BaseModel):
    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> MyModel:
        ...
        return super().model_validate(data)  # still delegates to pydantic
```

Update all call sites (including tests) to use `from_dict()` instead of `model_validate()`.

#### `no-redef` — import shadowing a local variable

```python
# WRONG: 'config' is already a function parameter on line 237
def my_func(config: ExperimentConfig) -> None:
    ...
    from scylla.e2e.models import config  # no-redef: "config" already defined
    print(config.language)  # actually works but is wrong/confusing

# CORRECT: Remove the erroneous import; use the parameter
def my_func(config: ExperimentConfig) -> None:
    ...
    print(config.language)  # use the parameter directly
```

#### `return-value` — bare `dict` return annotation

```python
# WRONG: bare dict is not a valid generic type annotation
def my_validator(cls, v: Any) -> dict:  # return-value warning
    return v if v else {}

# CORRECT: Specify generic parameters
def my_validator(cls, v: Any) -> dict[str, Any]:
    return v if v else {}
```

#### `call-overload` in tests — mypy `ignore_errors = true` limitation

In mypy 1.19, `ignore_errors = true` in `[[tool.mypy.overrides]]` for `tests.*` does NOT suppress
`call-overload` errors that arise from `Any`-typed dict access. Use a targeted inline ignore:

```python
# When accessing nested dict values typed as Any:
assert set(my_dict["key"]["subkey"]) == expected  # call-overload: no overload matches "object"

# CORRECT: Add targeted ignore comment
assert set(my_dict["key"]["subkey"]) == expected  # type: ignore[call-overload]
```

**Note**: Wrapping in `list()` does NOT help — `list(Any)` has the same overload problem.

#### Remove Fixed Error Codes from pyproject.toml

```toml
# Before
disable_error_code = [
    ...
    "override",        # 1 violation - incompatible method override
    "no-redef",        # 1 violation - name redefinition
    "exit-return",     # 1 violation - context manager __exit__ return type
    ...
    "return-value",    # 1 violation - incompatible return value type
    "call-overload",   # 1 violation - no matching overload variant
]

# After (remove the 5 lines)
disable_error_code = [
    ...
    # only remaining codes
]
```

### Phase 6: Validate and Commit

```bash
pixi run python scripts/check_mypy_counts.py   # must exit 0
pixi run python -m pytest tests/ -v             # all tests pass
pre-commit run --all-files                      # all hooks pass

### Run Full Pre-commit

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
| --------- | ---------------- | --------------- | ---------------- |
| Per-directory count without path filtering | Ran `pixi run mypy scripts/` and counted all output lines | Scripts import from scylla/, so mypy also checks scylla/ files transitively — inflates count by ~50+ errors | Filter output lines by file path prefix (`file_path.startswith(path)`) before counting; raw output is not directory-scoped |
| Regex anchoring for error code extraction | Used unanchored `\[[a-z][a-z0-9-]*\]` to parse error codes | Over-counts codes like `[arg-type]` when the message body itself contains bracketed words like `[str]` | Anchor the regex to end-of-line: `\[([a-z][a-z0-9-]*)\]$` to only match the trailing error code |
| Overriding pydantic `model_validate` with custom signature | Tried to match pydantic's exact `model_validate` signature in a subclass | Pydantic's signature uses complex keyword-only params that are hard to replicate, causing persistent override errors | Rename the method (e.g., `from_dict`) and delegate internally to `super().model_validate()` to avoid the override conflict entirely |
| Suppressing `call-overload` via `ignore_errors = true` in tests override | Relied on the `[[tool.mypy.overrides]] ignore_errors = true` block for `tests.*` to silence call-overload | In mypy 1.19, `ignore_errors = true` does NOT suppress `call-overload` errors from `Any`-typed dict access | Use targeted `# type: ignore[call-overload]` inline at each specific call site; `ignore_errors = true` is not a universal suppressor |
## Results & Parameters

```
Living baseline (2026-02-20):
  Total errors: 152
  Files checked: 262 (scripts/, scylla/, tests/)
  Error codes tracked: 15
  Tests written: 16 (all pass, coverage 73.35%)
  Pre-commit hooks: all 13 pass

Per-directory baselines (2026-02-22):
  scylla/:  61 errors
  tests/:   85 errors
  scripts/: 13 errors
  Total:   159 errors
  Unit tests: 26 (added 12 new per-directory tests)
  Full test suite: 2446 passed, 74.16% coverage
  Pre-commit hooks: all 15 pass

Quick-win fixes (2026-02-22, PR #946):
  Error codes fixed: 5 (override, no-redef, exit-return, return-value, call-overload)
  Suppressed error count: 63 → 58
  Files modified: 6 source files + 3 test files
  Tests: 2396 passed, 74.16% coverage (≥73% threshold)
  Pre-commit: all hooks pass
  Mypy 1.19 (compiled: yes)

Scripts coverage extension (2026-02-22, PR #939):
  Files checked (scripts/): 37 source files
  Mypy result: Success: no issues found
  pyproject.toml lines removed: 4
  Script files modified: 0
  Tests: 2396 passed, coverage 74.15% (above 73% threshold)
```

## Scripts Coverage Extension (from mypy-scripts-coverage-extension)

### Triage Before Removing Override

```bash
# Temporarily remove the override from pyproject.toml, then:
pixi run mypy scripts/ 2>&1
# If "Success: no issues found" — just commit the removal, no script fixes needed
# If errors appear — fix them incrementally before removing the override
```

### Read the Issue and Understand Scope

```bash
gh issue view 765 --comments
```

### Find the Override in pyproject.toml

```bash
grep -n "scripts" pyproject.toml
# Output: module = "scripts.*"  and  ignore_errors = true
```

The full block to remove:

```toml
[[tool.mypy.overrides]]
module = "scripts.*"
# Skip type checking for scripts - focus on source code first
ignore_errors = true
```

### Remove Override and Triage

```bash
pixi run mypy scripts/
```

If the output is `Success: no issues found in N source files`, no script modifications are needed.

### Verify with Pre-commit Hook

```bash
pre-commit run mypy-check-python --all-files
# Expected: Passed
```

### Run the Full Test Suite

```bash
pixi run python -m pytest tests/ -v
# Verify: all tests pass, coverage still above threshold (73%)
```

### Commit and PR

```bash
git add pyproject.toml pixi.lock
git commit -m "feat(mypy): Extend mypy coverage to scripts/ by removing blanket override"
gh pr create --title "feat(mypy): Extend mypy coverage to scripts/ ..." \
  --body "Closes #765"
gh pr merge --auto --rebase
```

## Living Baseline Setup (from mypy-living-baseline)

### Measure Actual Counts by Error Code

Mypy's `disable_error_code` in `pyproject.toml` suppresses errors; to see the real baseline,
re-enable all disabled codes:

```bash
# Get per-code error counts (each flag must be separate)
pixi run mypy scripts/ scylla/ tests/ \
  --enable-error-code assignment \
  --enable-error-code operator \
  ... \
  2>&1 | grep 'error:' | grep -oP '\[([a-z][a-z0-9-]*)\]$' | sort | uniq -c | sort -rn
```

**Critical**: Use `-oP '\[([a-z][a-z0-9-]*)\]$'` (anchored at end-of-line) to avoid counting
error codes appearing in message text.

### Count Drift After Adding New Files

When you first measure error counts and then add new Python files (e.g., the validation script
itself), the counts will increase. Always run `--update` after the full implementation is staged:

```bash
# After writing the validation script itself, re-capture counts
pixi run python scripts/check_mypy_counts.py --update
# Commit the updated MYPY_KNOWN_ISSUES.md along with the new script
```

### Validation Script Pattern (scripts/check_mypy_counts.py)

```python
DISABLED_ERROR_CODES = ["assignment", "operator", ...]  # matches pyproject.toml

def parse_known_issues_table(md_path: Path) -> dict[str, int]:
    """Parse markdown table rows matching '| error-code | N | description |'."""
    ...

def run_mypy_and_count(repo_root: Path) -> dict[str, int]:
    """Run mypy with all codes re-enabled, count per code (filtered to DISABLED_ERROR_CODES)."""
    cmd = ["pixi", "run", "mypy"] + MYPY_PATHS
    for code in DISABLED_ERROR_CODES:
        cmd += ["--enable-error-code", code]
    ...

def diff_counts(documented, actual) -> list[str]:
    """Return human-readable mismatch messages."""
    ...

def update_table(md_path: Path, actual: dict[str, int]) -> None:
    """Rewrite count cells and Total row in-place."""
    ...
```

**Key regex patterns**:
- Parse table rows: `r"^\|\s*([a-z][a-z0-9-]+)\s*\|\s*(\d+)\s*\|"` (lowercase codes only, skips `**Total**`)
- Parse error lines: `r"\berror:.*\[([a-z][a-z0-9-]*)\]$"` (anchored to end of line)
- Update total row: `r"(\|\s*\*\*Total\*\*\s*\|\s*\*\*)\d+(\*\*\s*\|)"`

### Pre-commit Hook for Baseline Enforcement

```yaml
- id: check-mypy-counts
  name: Check Mypy Known Issue Counts
  description: >-
    Validate that MYPY_KNOWN_ISSUES.md table counts match actual mypy output.
    Update the table when fixing type errors by running:
    python scripts/check_mypy_counts.py --update
  entry: python scripts/check_mypy_counts.py
  language: system
  files: ^(scripts|scylla|tests)/.*\.py$|^MYPY_KNOWN_ISSUES\.md$
  types_or: [python, markdown]
  pass_filenames: false
```

**Note**: Use `types_or` (not `types`) to trigger on both Python files and the markdown file.

### Unit Tests for Validation Script

```python
from unittest.mock import MagicMock, patch

def test_run_mypy_and_count_parses_output(tmp_path: Path) -> None:
    mock_result = MagicMock()
    mock_result.stdout = "scylla/foo.py:10: error: Msg  [arg-type]\n"
    with patch("subprocess.run", return_value=mock_result):
        counts = check_mypy_counts.run_mypy_and_count(tmp_path)
    assert counts["arg-type"] == 1
```

**Coverage note**: Tests for scripts in `scripts/` do not contribute to `--cov=scylla` coverage.
Run the full test suite (not just the new file) to verify the coverage threshold is still met.

### Fix Ruff D401 on Fixtures

```python
# WRONG - D401 violation
def valid_md(tmp_path: Path) -> Path:
    """A minimal MYPY_KNOWN_ISSUES.md..."""

# CORRECT
def valid_md(tmp_path: Path) -> Path:
    """Create a minimal MYPY_KNOWN_ISSUES.md..."""
```

## Quick-Win Error Code Fixes (from mypy-quick-win-fixes)

### Identify Actual Violations Before Touching Code

```bash
pixi run python -m mypy scylla/ \
  --enable-error-code override \
  --enable-error-code no-redef \
  --enable-error-code exit-return \
  --enable-error-code return-value \
  --enable-error-code call-overload \
  2>&1 | grep "error:"
```

**Critical**: The actual violations may differ from what MYPY_KNOWN_ISSUES.md documented. Always
re-run mypy to get the ground truth before making changes.

### Fix Each Error Code Pattern

#### `exit-return` — `__exit__` return type

```python
# WRONG: bool return type triggers exit-return when method always returns False
def __exit__(self, exc_type, exc_val, exc_tb) -> bool:
    ...
    return False  # mypy: "bool" is invalid as return type for "__exit__"

# CORRECT: Use None (never suppresses exceptions) or Literal[False]
def __exit__(self, exc_type, exc_val, exc_tb) -> None:
    ...
    # Return None (False-y) to not suppress exceptions
```

#### `override` — pydantic `model_validate` incompatible override

```python
# WRONG: Incompatible override of pydantic BaseModel.model_validate
class MyModel(BaseModel):
    @classmethod
    def model_validate(cls, data: dict[str, Any]) -> MyModel:  # override error
        ...

# CORRECT: Rename to a custom method name
class MyModel(BaseModel):
    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> MyModel:
        ...
        return super().model_validate(data)  # still delegates to pydantic
```

#### `no-redef` — import shadowing a local variable

```python
# WRONG: 'config' is already a function parameter on line 237
def my_func(config: ExperimentConfig) -> None:
    ...
    from scylla.e2e.models import config  # no-redef: "config" already defined
    print(config.language)  # actually works but is wrong/confusing

# CORRECT: Remove the erroneous import; use the parameter
def my_func(config: ExperimentConfig) -> None:
    ...
    print(config.language)  # use the parameter directly
```

#### `return-value` — bare `dict` return annotation

```python
# WRONG: bare dict is not a valid generic type annotation
def my_validator(cls, v: Any) -> dict:  # return-value warning
    return v if v else {}

# CORRECT: Specify generic parameters
def my_validator(cls, v: Any) -> dict[str, Any]:
    return v if v else {}
```

#### `call-overload` in tests — targeted inline ignore

```python
# When accessing nested dict values typed as Any:
assert set(my_dict["key"]["subkey"]) == expected  # call-overload: no overload matches "object"

# CORRECT: Add targeted ignore comment
assert set(my_dict["key"]["subkey"]) == expected  # type: ignore[call-overload]
```

**Note**: In mypy 1.19, `ignore_errors = true` in `[[tool.mypy.overrides]]` for `tests.*` does NOT
suppress `call-overload` errors from `Any`-typed dict access. Wrapping in `list()` does NOT help.

### Remove Error Codes from pyproject.toml

```toml
# Before
disable_error_code = [
    ...
    "override",        # 1 violation - incompatible method override
    "no-redef",        # 1 violation - name redefinition
    "exit-return",     # 1 violation - context manager __exit__ return type
    ...
    "return-value",    # 1 violation - incompatible return value type
    "call-overload",   # 1 violation - no matching overload variant
]

# After (remove the 5 lines)
disable_error_code = [
    ...
    # only remaining codes
]
```

### Verify Clean Mypy

```bash
pixi run python -m mypy scylla/
# Expected: Success: no issues found in N source files
```

### Run Full Pre-commit

```bash
pre-commit run --all-files
```

## Scripts Coverage Extension (from mypy-scripts-coverage-extension)

### Triage Before Removing Override

```bash
# Temporarily remove the override from pyproject.toml, then:
pixi run mypy scripts/ 2>&1
# If "Success: no issues found" — just commit the removal, no script fixes needed
# If errors appear — fix them incrementally before removing the override
```

### Read the Issue and Understand Scope

```bash
gh issue view 765 --comments
```

### Find the Override in pyproject.toml

```bash
grep -n "scripts" pyproject.toml
# Output: module = "scripts.*"  and  ignore_errors = true
```

The full block to remove:

```toml
[[tool.mypy.overrides]]
module = "scripts.*"
# Skip type checking for scripts - focus on source code first
ignore_errors = true
```

### Remove Override and Triage

```bash
pixi run mypy scripts/
```

If the output is `Success: no issues found in N source files`, no script modifications are needed.

### Verify with Pre-commit Hook

```bash
pre-commit run mypy-check-python --all-files
# Expected: Passed
```

### Run the Full Test Suite

```bash
pixi run python -m pytest tests/ -v
# Verify: all tests pass, coverage still above threshold (73%)
```

### Commit and PR

```bash
git add pyproject.toml pixi.lock
git commit -m "feat(mypy): Extend mypy coverage to scripts/ by removing blanket override"
gh pr create --title "feat(mypy): Extend mypy coverage to scripts/ ..." \
  --body "Closes #765"
gh pr merge --auto --rebase
```

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
| --------- | ---------------- | --------------- | ---------------- |
| Per-directory count without path filtering | Ran `pixi run mypy scripts/` and counted all output lines | Scripts import from scylla/, so mypy also checks scylla/ files transitively — inflates count by ~50+ errors | Filter output lines by file path prefix (`file_path.startswith(path)`) before counting; raw output is not directory-scoped |
| Regex anchoring for error code extraction | Used unanchored `\[[a-z][a-z0-9-]*\]` to parse error codes | Over-counts codes like `[arg-type]` when the message body itself contains bracketed words like `[str]` | Anchor the regex to end-of-line: `\[([a-z][a-z0-9-]*)\]$` to only match the trailing error code |
| Overriding pydantic `model_validate` with custom signature | Tried to match pydantic's exact `model_validate` signature in a subclass | Pydantic's signature uses complex keyword-only params that are hard to replicate, causing persistent override errors | Rename the method (e.g., `from_dict`) and delegate internally to `super().model_validate()` to avoid the override conflict entirely |
| Suppressing `call-overload` via `ignore_errors = true` in tests override | Relied on the `[[tool.mypy.overrides]] ignore_errors = true` block for `tests.*` to silence call-overload | In mypy 1.19, `ignore_errors = true` does NOT suppress `call-overload` errors from `Any`-typed dict access | Use targeted `# type: ignore[call-overload]` inline at each specific call site; `ignore_errors = true` is not a universal suppressor |

## Results & Parameters

```
Living baseline (2026-02-20):
  Total errors: 152
  Files checked: 262 (scripts/, scylla/, tests/)
  Error codes tracked: 15
  Tests written: 16 (all pass, coverage 73.35%)
  Pre-commit hooks: all 13 pass

Per-directory baselines (2026-02-22):
  scylla/:  61 errors
  tests/:   85 errors
  scripts/: 13 errors
  Total:   159 errors
  Unit tests: 26 (added 12 new per-directory tests)
  Full test suite: 2446 passed, 74.16% coverage
  Pre-commit hooks: all 15 pass

Quick-win fixes (2026-02-22, PR #946):
  Error codes fixed: 5 (override, no-redef, exit-return, return-value, call-overload)
  Suppressed error count: 63 → 58
  Files modified: 6 source files + 3 test files
  Tests: 2396 passed, 74.16% coverage (≥73% threshold)
  Pre-commit: all hooks pass
  Mypy 1.19 (compiled: yes)

Scripts coverage extension (2026-02-22, PR #939):
  Files checked (scripts/): 37 source files
  Mypy result: Success: no issues found
  pyproject.toml lines removed: 4
  Script files modified: 0
  Tests: 2396 passed, coverage 74.15% (above 73% threshold)
```

Error count breakdown at initial baseline (2026-02-20):

| Error Code | Count |
| --------------- | ------- |
| arg-type | 30 |
| call-arg | 28 |
| operator | 20 |
| var-annotated | 17 |
| union-attr | 16 |
| assignment | 14 |
| index | 10 |
| misc | 6 |
| attr-defined | 4 |
| valid-type | 2 |
| return-value | 1 |
| override | 1 |
| no-redef | 1 |
| exit-return | 1 |
| call-overload | 1 |
| **Total** | **152** |

### Quick-Win: Files Modified

| File | Change |
| ------ | -------- |
| `scylla/executor/capture.py` | `__exit__` return `bool` → `None`, remove `return False` |
| `scylla/e2e/checkpoint.py` | Rename `model_validate` → `from_dict`, update internal caller |
| `scylla/e2e/models.py` | `-> dict` → `-> dict[str, Any]` on field validator |
| `scylla/e2e/regenerate.py` | Remove erroneous `from scylla.e2e.models import config` import |
| `tests/unit/e2e/test_checkpoint.py` | Update 3 call sites to `from_dict()` |
| `tests/unit/e2e/test_resume.py` | Update 1 call site to `from_dict()` |
| `tests/unit/e2e/test_tier_manager.py` | Add `# type: ignore[call-overload]` |
| `pyproject.toml` | Remove 5 error codes from `disable_error_code` |

### Scripts Override Block Removed (PR #939)

```toml
[[tool.mypy.overrides]]
module = "scripts.*"
# Skip type checking for scripts - focus on source code first
ignore_errors = true
```

## Quick-Win Error Code Fixes

### 1. Identify Actual Violations Before Touching Code

```bash
pixi run python -m mypy scylla/ \
  --enable-error-code override \
  --enable-error-code no-redef \
  --enable-error-code exit-return \
  --enable-error-code return-value \
  --enable-error-code call-overload \
  2>&1 | grep "error:"
```

### 2. Fix Each Error Code

#### `exit-return` — `__exit__` return type

```python
# WRONG: bool return type triggers exit-return when method always returns False
def __exit__(self, exc_type, exc_val, exc_tb) -> bool:
    return False  # mypy: "bool" is invalid as return type for "__exit__"

# CORRECT: Use None (never suppresses exceptions)
def __exit__(self, exc_type, exc_val, exc_tb) -> None:
    ...
```

#### `override` — pydantic `model_validate` incompatible override

```python
# WRONG: Incompatible override of pydantic BaseModel.model_validate
class MyModel(BaseModel):
    @classmethod
    def model_validate(cls, data: dict[str, Any]) -> MyModel:  # override error
        ...

# CORRECT: Rename to a custom method name
class MyModel(BaseModel):
    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> MyModel:
        ...
        return super().model_validate(data)
```

#### `no-redef` / `return-value` / `call-overload`

```python
# no-redef: remove erroneous import that shadows a parameter
def my_func(config: ExperimentConfig) -> None:
    ...
    print(config.language)  # use parameter directly, no import needed

# return-value: specify generic parameters
def my_validator(cls, v: Any) -> dict[str, Any]:  # not bare dict
    return v if v else {}

# call-overload: add targeted ignore for Any-typed dict access
assert set(my_dict["key"]["subkey"]) == expected  # type: ignore[call-overload]
```

#### Remove error codes from pyproject.toml

```toml
# Remove from disable_error_code list:
"override",    # incompatible method override
"no-redef",    # name redefinition
"exit-return", # context manager __exit__ return type
"return-value",# incompatible return value type
"call-overload"# no matching overload variant
```

#### Verify clean

```bash
pixi run python -m mypy scylla/
# Expected: Success: no issues found in N source files
pre-commit run --all-files
```

## Scripts Coverage Extension

### Triage First, Then Remove Override

```bash
# Temporarily remove scripts.* override from pyproject.toml, then:
pixi run mypy scripts/ 2>&1
# If "Success: no issues found" — commit removal directly, no script fixes needed
# If errors appear — fix incrementally before removing override
```

### Pre-commit mypy hook for scripts

```bash
pre-commit run mypy-check-python --all-files
# Expected: Passed
```

### Full workflow (gh issue → remove override → verify → PR)

```bash
gh issue view 765 --comments
grep -n "scripts" pyproject.toml
# Remove the [[tool.mypy.overrides]] block for scripts.*
pixi run mypy scripts/
pixi run python -m pytest tests/ -v
git add pyproject.toml pixi.lock
git commit -m "feat(mypy): Extend mypy coverage to scripts/ by removing blanket override"
```

## Living Baseline: Validation Script Pattern

### 1. Measure actual counts per error code

```bash
pixi run mypy scripts/ scylla/ tests/ \
  --enable-error-code assignment \
  --enable-error-code operator \
  2>&1 | grep 'error:' | grep -oP '\[([a-z][a-z0-9-]*)\]$' | sort | uniq -c | sort -rn
```

### 2. Validation script structure (check_mypy_counts.py)

```python
DISABLED_ERROR_CODES = ["assignment", "operator", ...]  # matches pyproject.toml

def parse_known_issues_table(md_path: Path) -> dict[str, int]:
    """Parse markdown table rows matching '| error-code | N | description |'."""
    ...

def run_mypy_and_count(repo_root: Path) -> dict[str, int]:
    """Run mypy with all codes re-enabled, count per code."""
    cmd = ["pixi", "run", "mypy"] + MYPY_PATHS
    for code in DISABLED_ERROR_CODES:
        cmd += ["--enable-error-code", code]
    ...
```

**Key regex**: parse error lines with `r"\berror:.*\[([a-z][a-z0-9-]*)\]$"` (anchored to EOL).

### 3. Pre-commit hook definition

```yaml
- id: check-mypy-counts
  name: Check Mypy Known Issue Counts
  entry: python scripts/check_mypy_counts.py
  language: system
  files: ^(scripts|scylla|tests)/.*\.py$|^MYPY_KNOWN_ISSUES\.md$
  types_or: [python, markdown]
  pass_filenames: false
```

### 4. Unit test pattern (mock subprocess)

```python
from unittest.mock import MagicMock, patch

def test_run_mypy_and_count_parses_output(tmp_path: Path) -> None:
    mock_result = MagicMock()
    mock_result.stdout = "scylla/foo.py:10: error: Msg  [arg-type]\n"
    with patch("subprocess.run", return_value=mock_result):
        counts = check_mypy_counts.run_mypy_and_count(tmp_path)
    assert counts["arg-type"] == 1
```

### 5. D401 ruff fix for fixture docstrings

```python
# WRONG - D401 violation
def valid_md(tmp_path: Path) -> Path:
    """A minimal MYPY_KNOWN_ISSUES.md..."""

# CORRECT - imperative mood
def valid_md(tmp_path: Path) -> Path:
    """Create a minimal MYPY_KNOWN_ISSUES.md..."""
```

### Living Baseline Results (2026-02-20)

```
Total errors at baseline (2026-02-20): 152
Files checked: 262 (scripts/, scylla/, tests/)
Error codes tracked: 15 (matching pyproject.toml disable_error_code list)
Tests written: 16 (all pass, coverage unchanged at 73.35%)
Pre-commit hooks: all 13 pass
```

### Quick-Win Fix Results

```
Error codes fixed: 5 (override, no-redef, exit-return, return-value, call-overload)
Suppressed error count: 63 → 58
Files modified: 6 source files + 3 test files
Tests: 2396 passed, 74.16% coverage (≥73% threshold)
Pre-commit: all hooks pass
Mypy 1.19 (compiled: yes)
```

### Scripts Coverage Extension Results

```
Files checked (scripts/): 37 source files
Mypy result: Success: no issues found
pyproject.toml lines removed: 4
Script files modified: 0
Pre-commit result: Passed
Tests: 2396 passed, coverage 74.15% (above 73% threshold)
```

### pyproject.toml Block Removed (scripts coverage)

```toml
[[tool.mypy.overrides]]
module = "scripts.*"
# Skip type checking for scripts - focus on source code first
ignore_errors = true
```
