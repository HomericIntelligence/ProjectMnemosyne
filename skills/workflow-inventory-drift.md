---
name: workflow-inventory-drift
description: 'Detect drift between .github/workflows/*.yml files on disk and the workflow
  inventory table in README.md. Use when: adding or removing workflow files, setting
  up enforcement to keep workflow docs in sync, or diagnosing CI failures from inventory
  mismatch.'
category: ci-cd
date: 2026-03-15
version: 1.0.0
user-invocable: false
---
## Overview

| Field | Value |
|-------|-------|
| **Problem** | `.github/workflows/README.md` inventory table drifts from actual `.yml` files because there is no enforcement mechanism |
| **Solution** | stdlib-only Python script + pre-commit hook + CI step scoped to workflow directory changes |
| **Trigger** | A `.yml` file exists on disk but is absent from the README table, or a README row references a file that does not exist |
| **Language** | Python (stdlib only: `re`, `pathlib`, `argparse`) |
| **Hook scope** | `^\.github/workflows/(README\.md\|.*\.yml)$` — only runs when workflow files are staged |

## When to Use

- Adding or removing a GitHub Actions workflow file from `.github/workflows/`
- Setting up a new repo where the workflow README table must stay in sync with disk
- A CI check is failing with "undocumented workflows" or "documented but missing" errors
- You need a pre-commit gate that runs only when workflow-related files are staged

## Verified Workflow

### 1. Collect workflow files from disk (exclude worktrees)

```python
import re
from pathlib import Path

def collect_yml_files(repo_root: Path) -> set:
    """Return basenames of all *.yml files under .github/workflows/, excluding worktrees."""
    workflows_dir = repo_root / ".github" / "workflows"
    result = set()
    for f in workflows_dir.glob("*.yml"):
        rel = f.relative_to(repo_root)
        if any(part == "worktrees" for part in rel.parts):
            continue
        result.add(f.name)
    return result
```

**Critical**: Check `any(part == "worktrees" ...)` on the relative path parts, not a substring
match on the absolute path — the worktree root itself may contain "worktrees" as a path segment
that would cause false exclusions with a substring approach.

### 2. Parse the README inventory table with regex

```python
_TABLE_FILENAME_RE = re.compile(r"\|\s*\[?([a-zA-Z0-9_.-]+\.yml)\]?[^|]*\|")

def parse_readme_table(readme_path: Path) -> set:
    """Return set of .yml filenames found in the README pipe-delimited table."""
    content = readme_path.read_text(encoding="utf-8")
    return set(_TABLE_FILENAME_RE.findall(content))
```

The regex `\[?([a-zA-Z0-9_.-]+\.yml)\]?` handles two forms:

- Plain: `| ci.yml | ... |`
- Hyperlinked: `| [ci.yml](#anchor) | ... |`

It does **not** match bold category header rows like `| **Test Workflows** | | |` because
`[a-zA-Z0-9_.-]` excludes `*`.

### 3. Compute and report drift

```python
def check_inventory(repo_root: Path):
    """Return (undocumented, missing_files) sets."""
    readme_path = repo_root / ".github" / "workflows" / "README.md"
    on_disk = collect_yml_files(repo_root)
    in_readme = parse_readme_table(readme_path)
    undocumented = on_disk - in_readme   # on disk but not in README
    missing = in_readme - on_disk        # in README but not on disk
    return undocumented, missing
```

### 4. CLI with --repo-root and exit codes

```python
def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo-root", default=".", type=Path)
    args = parser.parse_args()
    undocumented, missing = check_inventory(args.repo_root)
    if undocumented:
        print("Undocumented workflows (add to README):")
        for f in sorted(undocumented):
            print(f"  {f}")
    if missing:
        print("Documented but missing (remove from README):")
        for f in sorted(missing):
            print(f"  {f}")
    sys.exit(1 if (undocumented or missing) else 0)
```

### 5. Pre-commit hook scoped to workflow directory

```yaml
- id: check-workflow-inventory
  name: Check Workflow Inventory
  description: Validate .github/workflows/README.md matches actual workflow files
  entry: python3 scripts/check_workflow_inventory.py
  language: system
  files: ^\.github/workflows/(README\.md|.*\.yml)$
  pass_filenames: false
```

`files:` regex limits hook execution to commits that touch the workflow directory —
avoids running the check on every source-code commit.

### 6. CI step in script-validation workflow

```yaml
- name: Check workflow inventory drift
  run: python3 scripts/check_workflow_inventory.py --repo-root .
```

Add this step to an existing validation workflow (e.g. `script-validation.yml`) so drift
is caught in PRs even when the pre-commit hook was not run locally.

### 7. Fixing a stale README before enabling the hook

When first enabling enforcement, check for existing drift and fix it:

```bash
python3 scripts/check_workflow_inventory.py --repo-root .
# Read output, then edit .github/workflows/README.md to match disk state
```

## Results & Parameters

| Parameter | Value | Notes |
|-----------|-------|-------|
| Glob pattern | `*.yml` in `.github/workflows/` | Excludes `*.md` and subdirs automatically |
| Worktree exclusion | `any(part == "worktrees" for part in rel.parts)` | Checks path segments, not substring |
| README regex | `\|\s*\[?([a-zA-Z0-9_.-]+\.yml)\]?[^|]*\|` | Handles plain and hyperlinked filenames |
| Hook trigger | `^\.github/workflows/(README\.md\|.*\.yml)$` | Only on workflow directory changes |
| Exit code | 0 = clean, 1 = drift detected | Compatible with pre-commit and CI |
| Tests | 24 pytest unit tests | All functions + main() integration |
| Dependencies | stdlib only (`re`, `pathlib`, `argparse`) | No pip install required |

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
|---------|----------------|---------------|----------------|
| Substring worktree exclusion | `if "worktrees" in str(f)` on absolute path | When repo root path itself contains "worktrees" (e.g. `.worktrees/issue-3981/`), every file matched and was excluded | Use `any(part == "worktrees" for part in rel.parts)` on the relative path parts |
| Regex matching header rows | Initial regex without anchoring on `[a-zA-Z0-9_.-]` | Matched `**Test**` tokens from bold category headers like `\| **Test Workflows** \| \| \|` | Character class `[a-zA-Z0-9_.-]` naturally excludes `*`, no extra anchoring needed |
| Glob `**/*.yml` from repo root | Used recursive glob instead of direct `workflows_dir.glob("*.yml")` | Picked up workflow files nested under `.pixi/` and other vendor dirs | Glob directly from `workflows_dir` so only the immediate workflow directory is scanned |

## Verified On

| Project | Context | Details |
|---------|---------|---------|
| ProjectOdyssey | Issue #3981, PR implementing drift detection | [notes.md](../../references/notes.md) |
