---
name: badge-count-drift-prevention
description: 'Automate README badge count validation to prevent drift. Use when: README
  badge reflects a file count that grows over time, badge has drifted from actual
  count, or adding pre-commit enforcement for badge accuracy.'
category: ci-cd
date: 2026-03-07
version: 1.0.0
user-invocable: false
---
## Overview

| Field | Value |
| ------- | ------- |
| **Problem** | README badges encoding counts (e.g. test file count) drift as files are added without automation |
| **Solution** | Python script + pre-commit hook scoped to README changes |
| **Trigger** | Badge value diverges from actual count by more than a configurable tolerance |
| **Language** | Python (subprocess find + regex) |
| **Hook scope** | `files: ^README\.md$` — only runs when README is staged |

## When to Use

- A shields.io badge in README encodes a count that grows over time (test files, source files, etc.)
- The badge has already drifted (was updated manually in the past)
- You want CI to catch drift automatically without running an expensive scan on every commit
- You need a `--fix` mode so developers can self-service badge updates

## Verified Workflow

### 1. Count files with subprocess (not glob)

Use `subprocess.run(["find", ...])` to mirror project conventions and handle large trees:

```python
def count_test_files(repo_root: Path) -> int:
    cmd = ["find", str(repo_root), "-name", "test_*.mojo", "-type", "f"]
    result = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
    repo_prefix = str(repo_root) + "/"
    count = 0
    for path in result.stdout.splitlines():
        rel = path[len(repo_prefix):] if path.startswith(repo_prefix) else path
        if any(excl in rel for excl in _EXCLUDE_DIRS):
            continue
        count += 1
    return count
```

**Critical**: Use **relative paths** for exclusion checks. When the repo root itself contains
an excluded segment (e.g. `.worktrees/issue-3307/`), absolute-path exclusion silently zeros
out all results. Strip the `repo_root` prefix first.

### 2. Parse badge count with regex

```python
_BADGE_COUNT_RE = re.compile(r"tests-(\d[\d,]*?)(?:%2B|-brightgreen|\+|\.svg|-[a-z])")

def parse_badge_count(readme_path: Path) -> Optional[int]:
    content = readme_path.read_text(encoding="utf-8")
    match = _BADGE_COUNT_RE.search(content)
    if not match:
        return None
    return int(match.group(1).replace(",", ""))
```

### 3. Check drift with tolerance

```python
def check_badge_drift(actual: int, badge: int, tolerance: float = 0.10) -> bool:
    if actual == 0:
        return badge == 0
    return abs(actual - badge) / actual <= tolerance
```

Use 10% tolerance — approximately one sprint's worth of new tests — to avoid nagging on every commit.

### 4. Auto-update badge with --fix

```python
_BADGE_LINE_RE = re.compile(r"(https://img\.shields\.io/badge/tests-)(\d[\d,]*)(%2B-brightgreen\.svg)")

def update_badge(readme_path: Path, new_count: int) -> None:
    content = readme_path.read_text(encoding="utf-8")
    updated = _BADGE_LINE_RE.sub(rf"\g<1>{new_count}\g<3>", content)
    readme_path.write_text(updated, encoding="utf-8")
```

### 5. Add pre-commit hook scoped to README

```yaml
- id: check-test-count-badge
  name: Check Test Count Badge
  description: Validate README.md test count badge matches actual test_*.mojo count
  entry: python3 scripts/check_test_count_badge.py
  language: system
  files: ^README\.md$
  pass_filenames: false
```

`files: ^README\.md$` limits the hook to commits that touch README — avoids running
an expensive `find` on every Mojo file commit.

### 6. Before committing: apply ruff formatting

Pre-commit runs ruff-format as a hook. If ruff modifies staged files, the stash/restore
cycle rolls back fixes and the commit fails. Fix sequence:

```bash
pixi run ruff format scripts/check_test_count_badge.py tests/scripts/test_*.py
git add scripts/check_test_count_badge.py tests/scripts/test_*.py
git commit -m "..."
```

Always format *before* staging to prevent the pre-commit stash-rollback loop.

### 7. Update stale badge before first hook run

Check current count and correct the badge so the initial hook run passes:

```bash
find . -name 'test_*.mojo' \
  -not -path './.pixi/*' \
  -not -path './worktrees/*' | wc -l
# Then update README manually or: python3 scripts/check_test_count_badge.py --fix
```

## Results & Parameters

| Parameter | Value | Notes |
| ----------- | ------- | ------- |
| Tolerance | 10% | ~1 sprint of test additions before alarm |
| Find excludes | `.pixi/`, `build/`, `dist/`, `.git/`, `worktrees/` | Match `validate_test_coverage.py` |
| Hook trigger | `^README\.md$` | Only on README changes |
| Auto-fix flag | `--fix` | Rewrites badge in-place |
| Custom tolerance | `--tolerance 0.05` | Override via CLI |
| Tests | 22 pytest unit tests | All functions + `main()` integration |

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
| --------- | ---------------- | --------------- | ---------------- |
| Absolute-path exclusion | `if any(excl in path for excl in _EXCLUDE_DIRS)` where `path` is the full absolute path | Repo root was `.worktrees/issue-3307/`, so `worktrees/` appeared in every absolute path, zeroing out all results | Always compute relative path from `repo_root` before checking exclusions |
| Staging then formatting | Stage files → commit → pre-commit runs ruff → stash conflict rolls back ruff's fixes | pre-commit stashes unstaged files; when ruff modifies staged content the stash restore undoes the ruff fix | Run `ruff format` on the files *before* `git add`, not after |
| First commit attempt without ruff | Committed un-formatted files; pre-commit auto-formatted but the commit failed | Stash rollback mechanism | Format first, stage second, commit third |
