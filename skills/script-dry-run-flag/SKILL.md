---
name: script-dry-run-flag
description: "TRIGGER CONDITIONS: Adding a --dry-run flag to a CLI script that exits 1 on errors. Use when developers need to preview all violations/errors across many files without blocking a pre-commit hook or CI step — especially during bulk config migrations or refactors."
user-invocable: false
category: tooling
date: 2026-03-07
---

# script-dry-run-flag

How to add a `--dry-run` flag to a validation script so all errors are printed but
the exit code is always 0, allowing developers to preview failures without blocking commits.

## Overview

| Item | Details |
|------|---------|
| Date | 2026-03-07 |
| Objective | Add `--dry-run` to `scripts/validate_config_schemas.py` |
| Outcome | Success — PR HomericIntelligence/ProjectScylla#1463 |
| Issue | HomericIntelligence/ProjectScylla#1442 |

## When to Use

- Any validation script that exits 1 on errors where you want a non-blocking preview mode
- Bulk config file migrations where you want to see all violations before fixing any
- Pre-commit hooks that should optionally run in advisory (non-blocking) mode
- Follows `precommit-schema-validation` skill when the base script is already in place

## Verified Workflow

### 1. Add `dry_run` parameter to the core function

Add `dry_run: bool = False` as a keyword argument. Keep the default `False` so existing
callers are unaffected. After collecting all failures, check the flag before returning:

```python
def check_files(
    files: list[Path],
    repo_root: Path,
    verbose: bool = False,
    dry_run: bool = False,
) -> int:
    """Validate each file against its matching schema.

    Args:
        files: List of file paths to check.
        repo_root: Repository root used for schema resolution.
        verbose: If True, print ``PASS:`` lines for valid files.
        dry_run: If True, print all errors but return 0 (do not block commits).

    Returns:
        0 if all files are valid or ``dry_run`` is True, 1 if any violations
        are found and ``dry_run`` is False.

    """
    # ... existing validation loop unchanged ...

    if any_failure and dry_run:
        return 0
    return 1 if any_failure else 0
```

**Key**: The `if any_failure and dry_run: return 0` check comes **after** the full loop,
so all files are always processed (all errors printed) before the exit code decision.

### 2. Add `--dry-run` argparse flag in `main()`

```python
parser.add_argument(
    "--dry-run",
    action="store_true",
    help="Print all errors but exit 0 — useful for previewing violations without blocking commits",  # noqa: E501
)

args = parser.parse_args()
return check_files(args.files, args.repo_root, verbose=args.verbose, dry_run=args.dry_run)
```

`argparse` converts `--dry-run` to `args.dry_run` (hyphen → underscore) automatically.

### 3. Update the module docstring exit codes section

```python
Exit codes:
    0: All files valid (or no matching schema found — warned, not failed)
    0: Violations found but --dry-run is set (errors printed, commit not blocked)
    1: One or more schema violations found (without --dry-run)
```

### 4. Write tests covering all four cases

```python
class TestDryRun:
    """Tests for --dry-run behaviour in check_files() and main()."""

    def test_dry_run_with_violations_returns_zero(self, tmp_path: Path) -> None:
        """dry_run=True should return 0 even when there are violations."""
        assert check_files([bad], repo_root, dry_run=True) == 0

    def test_dry_run_false_with_violations_returns_one(self, tmp_path: Path) -> None:
        """dry_run=False should return 1 when there are violations."""
        assert check_files([bad], repo_root, dry_run=False) == 1

    def test_dry_run_prints_errors(self, tmp_path, capsys) -> None:
        """dry_run=True should still print errors to stderr."""
        check_files([bad], repo_root, dry_run=True)
        assert "FAIL" in capsys.readouterr().err

    def test_dry_run_no_violations_returns_zero(self, tmp_path: Path) -> None:
        """dry_run=True with a valid file should still return 0."""
        assert check_files([good], repo_root, dry_run=True) == 0

    def test_dry_run_multiple_bad_files_all_reported(self, tmp_path, capsys) -> None:
        """dry_run=True should report all invalid files, not just the first."""
        result = check_files([bad_a, bad_b], repo_root, dry_run=True)
        assert result == 0
        assert "bad_a.yaml" in capsys.readouterr().err
        assert "bad_b.yaml" in capsys.readouterr().err

    def test_main_dry_run_flag_with_violations_exits_zero(
        self, tmp_path, capsys, monkeypatch
    ) -> None:
        """main() with --dry-run should exit 0 even when violations are found."""
        monkeypatch.setattr(
            "sys.argv",
            ["validate_config_schemas.py", "--dry-run", "--repo-root", str(repo_root), str(bad)],
        )
        assert main() == 0

    def test_main_no_dry_run_with_violations_exits_one(self, tmp_path, monkeypatch) -> None:
        """main() without --dry-run should exit 1 when violations are found."""
        monkeypatch.setattr(
            "sys.argv",
            ["validate_config_schemas.py", "--repo-root", str(repo_root), str(bad)],
        )
        assert main() == 1
```

Use `monkeypatch.setattr("sys.argv", [...])` to test `main()` without spawning a subprocess.
Include `--repo-root` so the test controls schema resolution via a `tmp_path`-based fake root.

### 5. Handle the line-length lint issue

The `--dry-run` help string will typically exceed 100 chars. Add `# noqa: E501` inline:

```python
help="Print all errors but exit 0 — useful for previewing violations without blocking commits",  # noqa: E501
```

## Failed Attempts

| Attempt | What Happened | Fix |
|---------|---------------|-----|
| Placed `if any_failure and dry_run` inside the loop | Would have returned early after the first failing file, skipping remaining files | Move the check **after** the loop so all files are always processed |

## Results & Parameters

- 7 new tests added in `TestDryRun` (33 total in the test module)
- No changes to `.pre-commit-config.yaml` — hook registration unchanged
- `argparse` hyphen-to-underscore: `--dry-run` → `args.dry_run` (built-in behaviour)
- Default `dry_run=False` preserves backward compatibility for all existing callers

## Verified On

| Project | Context | Details |
|---------|---------|---------|
| ProjectScylla | PR #1463, issue #1442 | Follow-up to precommit-schema-validation (#1382/#1439) |
