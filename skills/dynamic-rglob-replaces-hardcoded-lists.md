---
name: dynamic-rglob-replaces-hardcoded-lists
description: "Replace hardcoded file lists with Path.rglob() dynamic discovery for self-maintaining scripts. Use when: (1) a script iterates a manually maintained list of files, (2) new files are silently skipped unless someone updates the list, (3) porting fix scripts across repos with different directory conventions."
category: tooling
date: 2026-03-25
version: "1.0.0"
user-invocable: false
verification: verified-local
supersedes: []
tags:
  - rglob
  - dynamic-discovery
  - hardcoded-lists
  - pathlib
  - cross-repo-porting
---

# Dynamic rglob Replaces Hardcoded Lists

## Overview

| Field | Value |
| ------- | ------- |
| **Date** | 2026-03-25 |
| **Objective** | Replace hardcoded plugin lists in `fix_remaining_warnings.py` with `Path.rglob("SKILL.md")` dynamic discovery |
| **Outcome** | Script is now self-maintaining — new skills are fixed automatically without manual list updates |
| **Verification** | verified-local (13 pytest tests pass locally, CI pending on PR #5113) |

## When to Use

- A script iterates over a manually maintained list of file paths (e.g., `plugins_with_workflow_warning = [...]`)
- New files matching the pattern are silently skipped unless someone remembers to update the list
- Porting a fix/migration script to a different repo with different directory conventions
- Adding `--dry-run` support to an existing batch-fix script

## Verified Workflow

### Quick Reference

```python
# Replace this:
plugins_with_workflow_warning = ["plugin-a", "plugin-b", "plugin-c"]
plugins_with_table_warning = ["plugin-d", "plugin-e"]
all_plugins = set(plugins_with_workflow_warning) | set(plugins_with_table_warning)

# With this:
skill_files = sorted(skills_dir.rglob("SKILL.md"))
```

```bash
# Dry run to preview changes
python3 scripts/fix_remaining_warnings.py --dry-run

# Run against custom directory
python3 scripts/fix_remaining_warnings.py --skills-dir .claude/skills/
```

### Detailed Steps

1. **Replace hardcoded lists with `Path.rglob()`**: Use `sorted(root_dir.rglob("PATTERN"))` for deterministic, reproducible output. Remove all manually maintained file lists.

2. **Add `argparse` for configurability**: Add `--skills-dir` (default to repo-relative path like `.claude/skills`) and `--dry-run` flags. Accept `argv` parameter in `main()` for testability.

3. **Add `dry_run` parameter to fix functions**: Pass `dry_run: bool = False` into the per-file fix function; skip `write_file()` when True but still return the list of fixes that would apply.

4. **Adapt conventions when porting cross-repo**:
   - Change default paths (e.g., absolute `/home/user/ProjectX/skills` → relative `.claude/skills`)
   - Match test import patterns (e.g., `sys.path.insert` → `importlib.util.spec_from_file_location`)
   - Match test directory structure (e.g., `tests/` → `tests/scripts/`)

5. **Write comprehensive tests**: Cover dynamic discovery, dry-run semantics, empty directories, nested directories, clean file idempotency, and output format verification using `tmp_path` fixtures.

### Cross-Repo Convention Adaptation Checklist

| Convention | ProjectMnemosyne | ProjectOdyssey |
| ------------ | ----------------- | ---------------- |
| Default skills dir | `/home/user/ProjectMnemosyne/skills` | `.claude/skills` |
| Test imports | `sys.path.insert(0, ...)` | `importlib.util.spec_from_file_location()` |
| Test location | `tests/test_*.py` | `tests/scripts/test_*.py` |
| Module fixture | Direct import | `@pytest.fixture(name="mod")` with dynamic load |

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
| --------- | ---------------- | --------------- | ---------------- |
| Direct copy without adaptation | Copied script verbatim from ProjectMnemosyne | Default `--skills-dir` path pointed to wrong location; test import pattern didn't match repo conventions | Always check target repo's conventions for default paths, test imports, and directory structure before porting |
| Ruff format on first commit | Pre-commit hooks reformatted files | Commit failed, had to re-stage and create new commit | Always run `just precommit` or formatters before first commit attempt to avoid the re-stage cycle |

## Results & Parameters

### Key Parameters

```python
# Dynamic discovery pattern
skill_files = sorted(skills_dir.rglob("SKILL.md"))

# Testable main() signature
def main(argv: List[str] | None = None) -> None:

# Dry-run support in fix function
def fix_skill_file(skill_path: Path, dry_run: bool = False) -> Tuple[bool, List[str]]:
```

### Expected Test Output

```text
13 passed in 0.20s
```

### Test Coverage

- 5 tests for `fix_skill_file()` dry-run parameter
- 8 tests for `main()` dynamic discovery
- Covers: empty dirs, nested dirs, clean files, multiple categories, output format

## Verified On

| Project | Context | Details |
| --------- | --------- | --------- |
| ProjectOdyssey | Issue #3779, PR #5113 | Ported `fix_remaining_warnings.py` with dynamic scan, 13 tests pass locally |
