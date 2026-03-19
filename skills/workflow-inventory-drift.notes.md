# Session Notes — workflow-inventory-drift

## Context

- **Issue**: ProjectOdyssey #3981 — "Add automation to detect README/workflow inventory drift"
- **Repo**: HomericIntelligence/ProjectOdyssey
- **Branch**: 3981-auto-impl
- **Date**: 2026-03-15

## Objective

The `.github/workflows/README.md` inventory table had drifted from the actual workflow files
on disk because there was no enforcement mechanism. A stale row (`build-validation.yml`) was
documented in the table but the file did not exist on disk.

The fix adds a CI check that:
1. Parses the workflow table in README.md
2. Compares listed filenames against actual `.github/workflows/*.yml` files on disk
3. Fails if any file exists on disk but is not documented, or is documented but does not exist

## Files Created / Modified

- `scripts/check_workflow_inventory.py` — new stdlib-only Python script
- `tests/test_check_workflow_inventory.py` — 24 unit tests (all passing)
- `.pre-commit-config.yaml` — added `check-workflow-inventory` local hook
- `.github/workflows/script-validation.yml` — added "Check workflow inventory drift" step
- `.github/workflows/README.md` — removed stale `build-validation.yml` row

## Script Structure

```python
# scripts/check_workflow_inventory.py
_TABLE_FILENAME_RE = re.compile(r"\|\s*\[?([a-zA-Z0-9_.-]+\.yml)\]?[^|]*\|")

def collect_yml_files(repo_root: Path) -> set: ...
def parse_readme_table(readme_path: Path) -> set: ...
def check_inventory(repo_root: Path) -> tuple: ...  # returns (undocumented, missing_files)
def main() -> None: ...  # --repo-root arg, exit 0/1
```

## Test Results

```text
24 passed
```

All pre-commit hooks passed on final commit.

## Key Bug Fixed During Development

**Worktree path exclusion**: Initial implementation used `if "worktrees" in str(f)` on the
absolute path. When the repo is checked out under `.worktrees/issue-3981/`, every absolute path
contains "worktrees" as a substring, causing all files to be excluded and the check to report
false negatives.

Fix: compute a relative path from `repo_root` and check `any(part == "worktrees" for part in rel.parts)`
on the path parts rather than doing a substring match on the full absolute path.

## Stale Row Found at Enforcement Time

`build-validation.yml` was listed in the README table but did not exist on disk. Removed the
row as part of this implementation to make the initial hook run pass.

## Pre-commit Hook Configuration

```yaml
- id: check-workflow-inventory
  name: Check Workflow Inventory
  description: Validate .github/workflows/README.md matches actual workflow files
  entry: python3 scripts/check_workflow_inventory.py
  language: system
  files: ^\.github/workflows/(README\.md|.*\.yml)$
  pass_filenames: false
```

## CI Integration

Added as a step in `.github/workflows/script-validation.yml`:

```yaml
- name: Check workflow inventory drift
  run: python3 scripts/check_workflow_inventory.py --repo-root .
```