# Skill: Unit Tests for WorkspaceManager RuntimeError Guards

## Overview

| Field | Value |
|-------|-------|
| Date | 2026-03-02 |
| Project | ProjectScylla |
| Objective | Add unit tests covering all `raise RuntimeError` guards in `workspace_manager.py` |
| Outcome | Success — 3 new tests pass, all 25 tests in module pass, pre-commit clean |
| Issue | HomericIntelligence/ProjectScylla#1215 |
| PR | HomericIntelligence/ProjectScylla#1310 |

## When to Use

Use this skill when:
- Adding `raise RuntimeError(...)` guards to classes that wrap subprocess calls (git, docker, etc.)
- Testing guards that have sequential subprocess calls (fetch then checkout, etc.)
- Testing state-based guards (`_is_setup = False` → raises before touching subprocess)
- Verifying guards with `side_effect` lists for multi-call subprocess mocking

## Key Patterns in This Session

### Pattern 1: State Guard (No Subprocess Needed)

When a guard fires before any subprocess is called (e.g., checking `_is_setup`), no subprocess mock is needed:

```python
def test_create_worktree_raises_if_not_setup(self, tmp_path: Path) -> None:
    """create_worktree raises RuntimeError when _is_setup is False."""
    manager = WorkspaceManager(
        experiment_dir=tmp_path,
        repo_url="https://github.com/test/repo.git",
    )
    # _is_setup defaults to False — no mock needed
    with pytest.raises(RuntimeError, match="Base repo not set up"):
        manager.create_worktree(tmp_path / "workspace")
```

**Key**: Check the default constructor state — if the guard fires before the first subprocess call, no patching is required at all.

### Pattern 2: Sequential Subprocess Guard (side_effect list)

When the guard fires after a successful earlier call, use `side_effect=[first_ok, second_fail]`:

```python
def test_checkout_commit_raises_if_checkout_fails(self, tmp_path: Path) -> None:
    """_checkout_commit raises RuntimeError when git checkout returns non-zero."""
    manager = WorkspaceManager(
        experiment_dir=tmp_path,
        repo_url="https://github.com/test/repo.git",
        commit="abc123",
    )
    fetch_ok = MagicMock()
    fetch_ok.returncode = 0
    fetch_ok.stderr = ""

    checkout_fail = MagicMock()
    checkout_fail.returncode = 1
    checkout_fail.stderr = "error: pathspec 'abc123' did not match any file"

    with patch("subprocess.run", side_effect=[fetch_ok, checkout_fail]):
        with pytest.raises(RuntimeError, match="Failed to checkout commit abc123"):
            manager._checkout_commit()
```

**Key**: Read the method's source to count subprocess.run calls in order. `side_effect` fires them in sequence. Include the exact commit hash in `match=` if the error message is f-string formatted.

### Pattern 3: Bypass Earlier Guard, Test Later Guard

When a guard follows another guard (e.g., `_is_setup` check then worktree creation):

```python
def test_create_worktree_raises_if_worktree_cmd_fails(self, tmp_path: Path) -> None:
    """create_worktree raises RuntimeError when git worktree add returns non-zero."""
    manager = WorkspaceManager(
        experiment_dir=tmp_path,
        repo_url="https://github.com/test/repo.git",
    )
    manager._is_setup = True  # Bypass first guard

    worktree_fail = MagicMock()
    worktree_fail.returncode = 1
    worktree_fail.stderr = "fatal: 'workspace' already exists"

    workspace = tmp_path / "workspace"
    with patch("subprocess.run", return_value=worktree_fail):
        with pytest.raises(RuntimeError, match="Failed to create worktree at"):
            manager.create_worktree(workspace)
```

**Key**: Directly set private attributes (`manager._is_setup = True`) to bypass earlier guards. This is acceptable in unit tests targeting a specific guard.

## Guard Discovery Workflow

```bash
# Find all RuntimeError guards in the module under test
grep -n "raise RuntimeError" scylla/e2e/workspace_manager.py

# Cross-reference with existing tests to find uncovered guards
grep -n "RuntimeError" tests/unit/e2e/test_workspace_manager.py
```

Then for each uncovered guard:
1. Read the method body to understand prerequisites (what must be true before the guard fires)
2. Identify how many `subprocess.run` calls precede the guard
3. Identify any state flags (`_is_setup`, `_base_path`, etc.) that gate execution
4. Choose Pattern 1, 2, or 3 above accordingly

## Guards Covered in This Session (ProjectScylla #1215)

| Line | Guard Message | Test Method | Pattern Used |
|------|---------------|-------------|--------------|
| 237 | `Failed to checkout commit {commit}` | `test_checkout_commit_raises_if_checkout_fails` | Sequential subprocess |
| 283 | `Base repo not set up. Call setup_base_repo() first.` | `test_create_worktree_raises_if_not_setup` | State guard (no mock) |
| 319 | `Failed to create worktree at {path}` | `test_create_worktree_raises_if_worktree_cmd_fails` | Bypass earlier guard |

Pre-existing coverage (not added in this session):
| Line | Guard Message | Covered By |
|------|---------------|------------|
| 172 | `Failed to clone repository` | Pre-existing tests (lines 131, 152, 174 in test file) |
| 199 | `commit must be set before calling _checkout_commit` | Pre-existing test (line 443–453) |
| 246 | `commit must be set before calling _ensure_commit_available` | Pre-existing test (line 482–492) |

## Failed Attempts

None — the implementation was correct on the first attempt. The review plan confirmed no fixes were needed. The key insight: the issue stated "four RuntimeError guards" but grep revealed 6 total, with 3 already covered by pre-existing tests.

## Results & Parameters

### Test class added
```python
class TestWorkspaceManagerGuards:
    """Guard tests for WorkspaceManager RuntimeError precondition paths."""
    # 3 test methods, appended after last existing test class in module
```

### Full module result
```
25 passed in 2.83s
```

### Pre-commit result
```
All hooks passed (ruff, mypy, markdown, yaml, shellcheck, etc.)
```

### Match pattern for f-string guards
When the guard message includes runtime values (e.g., commit hash, path), include a unique fragment:
```python
# Guard: raise RuntimeError(f"Failed to checkout commit {commit}")
match="Failed to checkout commit abc123"  # Use the actual commit value from test setup

# Guard: raise RuntimeError(f"Failed to create worktree at {path}")
match="Failed to create worktree at"  # Partial match is fine (no need for full path)
```

## Related Skills

- `runtime-error-guard-tests` — Original skill for `stages.py` and `runner.py` guard patterns (issue #1144, PR #1210)
