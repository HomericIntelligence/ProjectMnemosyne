---
name: worktree-integration-test-pattern
description: 'Pattern for writing integration tests against real SKILL.md files in
  git worktrees. Use when: adding regression tests for SKILL.md transformation scripts,
  importing build/ artifacts from a worktree, or verifying fix functions are idempotent
  on production files.'
category: testing
date: 2026-03-15
version: 1.0.0
user-invocable: false
---
# Worktree Integration Test Pattern

## Overview

| Field | Value |
|-------|-------|
| Date | 2026-03-15 |
| Objective | Add regression tests that exercise transformation scripts against real SKILL.md files |
| Outcome | 6 integration tests passing, guarding against real-world shape regressions |

## When to Use

- Adding integration tests for scripts that transform or validate SKILL.md files
- Test module needs to import from `build/ProjectMnemosyne/scripts/` which lives only in the main repo, not in git worktrees
- Verifying that fix functions are idempotent (second pass returns `modified=False`)
- Guarding against regressions on real-world file shapes vs. synthetic fixtures

## Verified Workflow

### Quick Reference

```python
# Minimal pattern for a worktree-aware integration test
import subprocess
import sys
from pathlib import Path

def _find_scripts_dir() -> Path:
    worktree_root = Path(__file__).parent.parent
    try:
        result = subprocess.run(
            ["git", "rev-parse", "--git-common-dir"],
            cwd=worktree_root, capture_output=True, text=True, check=True,
        )
        main_repo_root = Path(result.stdout.strip()).parent
    except (subprocess.CalledProcessError, FileNotFoundError):
        main_repo_root = worktree_root
    candidate = main_repo_root / "build" / "ProjectMnemosyne" / "scripts"
    if candidate.is_dir():
        return candidate
    return worktree_root / "build" / "ProjectMnemosyne" / "scripts"

sys.path.insert(0, str(_find_scripts_dir()))
from fix_remaining_warnings import fix_skill_file, has_orphan_quick_reference
```

### Step 1 — Identify the real fixture file

Point the test at an actual committed SKILL.md rather than a synthetic string:

```python
WORKTREE_CREATE_SKILL = (
    Path(__file__).parent.parent
    / ".claude" / "skills" / "worktree-create" / "SKILL.md"
)
```

The fixture must be committed to the repo so CI can find it.

### Step 2 — Add a fixture-exists guard

Always include a sanity test first, so a missing fixture gives a clear failure
message rather than a cryptic import/open error:

```python
def test_fixture_file_exists(self) -> None:
    assert WORKTREE_CREATE_SKILL.exists(), (
        f"Fixture not found: {WORKTREE_CREATE_SKILL}"
    )
```

### Step 3 — Test before-state (read-only, no copy)

Assert the initial condition directly on the real file (read-only):

```python
def test_real_file_has_orphan_quick_reference(self) -> None:
    content = WORKTREE_CREATE_SKILL.read_text(encoding="utf-8")
    assert has_orphan_quick_reference(content) is True
```

### Step 4 — Test fix in a tmp_path copy

Always copy to `tmp_path` before calling mutating functions:

```python
def test_fix_skill_file_returns_modified_true(self, tmp_path: Path) -> None:
    target = tmp_path / "SKILL.md"
    shutil.copy2(WORKTREE_CREATE_SKILL, target)
    modified, fixes = fix_skill_file(target)
    assert modified is True
    assert len(fixes) > 0
```

### Step 5 — Assert after-state

```python
def test_fix_skill_file_removes_orphan_quick_reference(self, tmp_path: Path) -> None:
    target = tmp_path / "SKILL.md"
    shutil.copy2(WORKTREE_CREATE_SKILL, target)
    fix_skill_file(target)
    assert has_orphan_quick_reference(target.read_text(encoding="utf-8")) is False
```

### Step 6 — Assert content round-trip (no data loss)

Check that key content survives the transformation:

```python
def test_round_trip_no_data_loss(self, tmp_path: Path) -> None:
    original = WORKTREE_CREATE_SKILL.read_text(encoding="utf-8")
    target = tmp_path / "SKILL.md"
    shutil.copy2(WORKTREE_CREATE_SKILL, target)
    fix_skill_file(target)
    result = target.read_text(encoding="utf-8")
    assert result != original   # file was actually changed
    for snippet in ["create_worktree.sh", "git worktree list"]:
        assert snippet in result
```

### Step 7 — Assert idempotency

```python
def test_fix_skill_file_is_idempotent(self, tmp_path: Path) -> None:
    target = tmp_path / "SKILL.md"
    shutil.copy2(WORKTREE_CREATE_SKILL, target)
    fix_skill_file(target)
    content_after_first = target.read_text(encoding="utf-8")
    modified, _ = fix_skill_file(target)
    assert modified is False
    assert target.read_text(encoding="utf-8") == content_after_first
```

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
|---------|----------------|---------------|----------------|
| `sys.path.insert(0, str(Path(__file__).parent.parent / "build" / "ProjectMnemosyne" / "scripts"))` | Relative path from worktree root | `build/` directory does not exist in worktrees — only in the main repo checkout | Use `git rev-parse --git-common-dir` to resolve the main repo root first |
| Read real file directly in mutating test | Calling `fix_skill_file(WORKTREE_CREATE_SKILL)` directly | Modifies the committed fixture file, making the before-state test fail on second run | Always copy to `tmp_path` before calling any mutating function |
| Single broad test | One test that checks before + fix + after in sequence | Test failure is hard to diagnose; unclear which assertion broke | Use separate focused test methods per assertion |

## Results & Parameters

### Six-test checklist for any SKILL.md transformer

```python
class TestRealFileIntegration:
    def test_fixture_file_exists(self) -> None: ...
    def test_real_file_has_condition_before_fix(self) -> None: ...
    def test_fix_returns_modified_true(self, tmp_path) -> None: ...
    def test_fix_removes_condition(self, tmp_path) -> None: ...
    def test_round_trip_no_data_loss(self, tmp_path) -> None: ...
    def test_fix_is_idempotent(self, tmp_path) -> None: ...
```

### `_find_scripts_dir()` for worktree-aware imports

```python
def _find_scripts_dir() -> Path:
    """Resolve build/ProjectMnemosyne/scripts/ from any worktree."""
    worktree_root = Path(__file__).parent.parent
    try:
        result = subprocess.run(
            ["git", "rev-parse", "--git-common-dir"],
            cwd=worktree_root, capture_output=True, text=True, check=True,
        )
        git_common_dir = Path(result.stdout.strip())
        main_repo_root = git_common_dir.parent
    except (subprocess.CalledProcessError, FileNotFoundError):
        main_repo_root = worktree_root
    candidate = main_repo_root / "build" / "ProjectMnemosyne" / "scripts"
    if candidate.is_dir():
        return candidate
    return worktree_root / "build" / "ProjectMnemosyne" / "scripts"
```

Run tests with:

```bash
pixi run python -m pytest tests/test_quick_reference_transform.py -v
# Expected: 6 passed
```
