# Mypy Per-Directory Baseline Skill

## Overview

| Field | Value |
|-------|-------|
| **Date** | 2026-02-22 |
| **Issue** | #889 — Enable mypy checking for tests/ and scripts/ directories |
| **Objective** | Remove `ignore_errors = true` overrides for `tests.*` and `scripts.*`, extend the regression guard to track baselines per-directory, and populate initial counts |
| **Outcome** | ✅ Success — per-directory sections in MYPY_KNOWN_ISSUES.md, 26 unit tests, all hooks passing |
| **Prerequisite** | `mypy-living-baseline` skill (flat baseline + pre-commit guard) |

## When to Use

Use this skill when:

- You have a flat `MYPY_KNOWN_ISSUES.md` baseline (from `mypy-living-baseline`) and want to
  track error counts per-directory (scylla/, tests/, scripts/) independently
- You are removing `ignore_errors = true` overrides from `pyproject.toml` and need to document
  per-directory baselines before CI will pass
- You need the regression guard to detect regressions in one directory without being confused
  by fixes in another

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

## Verified Workflow

### 1. Remove ignore_errors Overrides

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

### 2. Extend check_mypy_counts.py with Per-Directory Logic

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

### 3. Update run_mypy_and_count for Backward Compatibility

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

### 4. Restructure MYPY_KNOWN_ISSUES.md

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

### 5. Validate and Commit

```bash
pixi run python scripts/check_mypy_counts.py   # must exit 0
pixi run python -m pytest tests/ -v             # all tests pass
pre-commit run --all-files                      # all hooks pass

# Stage pixi.lock alongside other files to prevent stash conflict
git add MYPY_KNOWN_ISSUES.md pyproject.toml scripts/check_mypy_counts.py \
    tests/unit/test_check_mypy_counts.py pixi.lock
git commit -m "feat(mypy): Enable type checking for tests/ and scripts/ directories"
```

## Failed Attempts

### Running mypy per-directory without file-path filtering

**Attempt**: Run `pixi run mypy scripts/` and count all error lines in the output.

**Failure**: `mypy scripts/` transitively checks `scylla/` imports and reports 60+ errors from
`scylla/` files in the output, inflating `scripts/` counts from ~13 to ~67.

**Fix**: Filter each output line by the file path prefix before counting:
```python
if not file_match.group(1).startswith(path):
    continue
```

### Mocking subprocess.run with a single return_value

**Attempt**: `with patch("subprocess.run", return_value=mock_result)` in tests for
`run_mypy_and_count`.

**Failure**: After refactoring `run_mypy_and_count` to delegate to `run_mypy_per_dir` (which calls
mypy 3 times), a single `return_value` is returned for all 3 calls, tripling the counts.

**Fix**: Use `side_effect` with a list of 3 mocks, one per MYPY_PATH:
```python
with patch("subprocess.run", side_effect=[scripts_mock, scylla_mock, tests_mock]):
    counts = check_mypy_counts.run_mypy_and_count(tmp_path)
```

### Providing side_effects in wrong directory order

**Attempt**: Ordered side_effects as `[scylla_mock, tests_mock, scripts_mock]`.

**Failure**: `run_mypy_per_dir` iterates `MYPY_PATHS = ["scripts/", "scylla/", "tests/"]`, so the
first mock is consumed by the `scripts/` run. The test asserted `result["scripts/"]["arg-type"] == 1`
but `scripts/` got the scylla output and found 0 errors (different format).

**Fix**: Always match side_effects order to `MYPY_PATHS` order.

### Stashing pixi.lock separately before commit

**Attempt**: `git stash -- pixi.lock` then `git commit`.

**Failure**: Pre-commit's internal stash conflicted with pixi re-modifying pixi.lock during hook
execution, causing ruff-format to report "Failed" with "Stashed changes conflicted with hook
auto-fixes... Rolling back fixes."

**Fix**: Include pixi.lock in the staged files before committing.

## Results & Parameters

```
Per-directory baselines (2026-02-22):
  scylla/:  61 errors
  tests/:   85 errors
  scripts/: 13 errors
  Total:   159 errors

Unit tests: 26 (added 12 new per-directory tests)
Full test suite: 2446 passed, 74.16% coverage
Pre-commit hooks: all 15 pass
```
