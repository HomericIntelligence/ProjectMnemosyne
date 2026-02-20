# Mypy Living Baseline Skill

## Overview

| Field | Value |
|-------|-------|
| **Date** | 2026-02-20 |
| **Issue** | #768 - Update MYPY_KNOWN_ISSUES.md as part of mypy fix workflow |
| **Objective** | Define a convention + enforcement mechanism so MYPY_KNOWN_ISSUES.md stays current as type errors are fixed |
| **Outcome** | ✅ Success — validation script + pre-commit hook + 16 unit tests, all hooks passing |

## When to Use

Use this skill when:

- A project has incrementally-adopted mypy (some error codes disabled) and you need to track
  progress as errors are fixed over time
- You want to enforce that PRs update a "known issues" document whenever they fix type errors
- You need a self-updating markdown table that reflects actual mypy output counts per error code
- You are adding a new pre-commit validation script following the `check_type_alias_shadowing.py`
  pattern in ProjectScylla

## Key Insight: Count Drift After Adding New Files

When you first measure error counts and then add new Python files (e.g., the validation script
itself), the counts will increase. Always run `--update` after the full implementation is staged
to capture the final accurate baseline before committing.

```bash
# After writing the validation script itself, re-capture counts
pixi run python scripts/check_mypy_counts.py --update
# Commit the updated MYPY_KNOWN_ISSUES.md along with the new script
```

## Verified Workflow

### 1. Measure Actual Counts by Error Code

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

### 2. Create MYPY_KNOWN_ISSUES.md

Include:
- A blockquote convention banner at the top
- Baseline date and roadmap issue reference
- Update instructions with `--update` flag usage
- A well-formed markdown table: `| error-code | count | description |`
- A `| **Total** | **N** | |` row
- A note explaining any error codes that appear in raw output but are excluded (e.g., codes
  from modules with `ignore_errors = true`)

### 3. Write the Validation Script (scripts/check_mypy_counts.py)

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

### 4. Add Pre-commit Hook

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

### 5. Write Unit Tests

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

### 6. Fix Ruff D401 on Fixtures

Pytest fixture docstrings must use imperative mood (D401). Write:

```python
# WRONG - D401 violation
def valid_md(tmp_path: Path) -> Path:
    """A minimal MYPY_KNOWN_ISSUES.md..."""

# CORRECT
def valid_md(tmp_path: Path) -> Path:
    """Create a minimal MYPY_KNOWN_ISSUES.md..."""
```

## Failed Attempts

### Comma-separated `--enable-error-code` flag

**Attempt**: `pixi run mypy ... --enable-error-code assignment,operator,arg-type`

**Failure**: `mypy: error: Invalid error code(s): assignment,operator,arg-type`

**Fix**: Pass each code as a separate `--enable-error-code` flag.

### Unanchored regex for error code extraction

**Attempt**: `grep -o '\[[a-z][a-z0-9-]*\]'` on mypy output lines

**Failure**: Lines containing `[arg-type]` with messages mentioning types like `"list[str | None]"`
were double-counted because `[str]` inside the message also matched.

**Fix**: Use end-of-line anchor: `grep -oP '\[([a-z][a-z0-9-]*)\]$'`

### Initial count measurement before writing the validation script

**Attempt**: Measure counts, put them in the markdown, then write the script.

**Failure**: The new `scripts/check_mypy_counts.py` file introduces new `var-annotated` and `misc`
type errors (2 additional errors), making the documented counts immediately stale.

**Fix**: Always run `python scripts/check_mypy_counts.py --update` after all implementation files
are written, then commit the final updated markdown.

## Results & Parameters

```
Total errors at baseline (2026-02-20): 152
Files checked: 262 (scripts/, scylla/, tests/)
Error codes tracked: 15 (matching pyproject.toml disable_error_code list)
Tests written: 16 (all pass, coverage unchanged at 73.35%)
Pre-commit hooks: all 13 pass
```

Error count breakdown (2026-02-20):

| Error Code    | Count |
|---------------|-------|
| arg-type      | 30    |
| call-arg      | 28    |
| operator      | 20    |
| var-annotated | 17    |
| union-attr    | 16    |
| assignment    | 14    |
| index         | 10    |
| misc          | 6     |
| attr-defined  | 4     |
| valid-type    | 2     |
| return-value  | 1     |
| override      | 1     |
| no-redef      | 1     |
| exit-return   | 1     |
| call-overload | 1     |
| **Total**     | **152** |
