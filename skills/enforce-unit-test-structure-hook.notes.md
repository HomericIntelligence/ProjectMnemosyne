# Session Notes — enforce-unit-test-structure-hook

**Session date**: 2026-02-27
**Issue**: HomericIntelligence/ProjectScylla#967
**PR**: HomericIntelligence/ProjectScylla#1122
**Branch**: `967-auto-impl`

## Raw Session Details

### Objective
Add a pre-commit hook (follow-up from issue #849 quality audit) that automatically detects
and blocks commits where `test_*.py` files are placed directly under `tests/unit/` instead
of in the correct sub-package.

### Implementation

Three files changed:
1. `scripts/check_unit_test_structure.py` — 63 lines Python hook
2. `tests/unit/scripts/test_check_unit_test_structure.py` — 13 tests
3. `.pre-commit-config.yaml` — 7-line hook registration

Additional 3 pre-existing test fixes required to make the pre-push hook pass in the worktree.

### Worktree Environment Issues Encountered

The pre-push hook uses `pixi run pytest -x` (stop-at-first-failure). Running the full test
suite from inside a git worktree exposed 3 pre-existing bugs that didn't affect `main`:

#### Bug 1: Wrong mock patch target in test_orchestrator.py

```
# orchestrator.py imports:
from scylla.executor import checkout_hash, clone_repo

# Tests patched (WRONG):
patch("scylla.executor.workspace.checkout_hash")

# Tests patched (CORRECT):
patch("scylla.e2e.orchestrator.checkout_hash")
```

In the worktree, `git checkout <hash>` inside tmp dirs fails (git object store not accessible
the same way), so the unpatched real function raises `WorkspaceError`. On `main`, git happens
to find the hash via the parent repo's objects, masking the bug.

#### Bug 2: Git-aware tmp directories in test_run_report.py

```python
# WRONG: bare tmp_path is inside worktree, git ls-files succeeds
workspace = tmp_path / "workspace"
workspace.mkdir()
result = _get_workspace_files(workspace)
assert result == []  # FAILS — returns 1943 files from the repo!

# CORRECT: mock subprocess.run
@patch("subprocess.run")
def test_git_error_returns_empty_list(self, mock_run, tmp_path):
    mock_run.return_value = MagicMock(returncode=128, stdout="", stderr="not a git repository")
    result = _get_workspace_files(tmp_path / "workspace")
    assert result == []
```

#### Bug 3: Wall-clock timing assertion in test_retry.py

```python
# WRONG: fails under load (got 1.09s when system busy)
start = time.time()
result = decorated()
elapsed = time.time() - start
assert elapsed >= 2.0

# CORRECT: mock sleep and assert argument
with patch("time.sleep") as mock_sleep:
    result = decorated()
    mock_sleep.assert_called_once_with(2.0)
```

### Commits Created

1. `feat(hooks): add pre-commit hook to enforce tests/unit/ mirroring convention`
2. `fix(tests): fix mock patch paths in test_orchestrator.py`
3. `fix(tests): fix test_git_error_returns_empty_list for worktree environments`
4. `fix(tests): replace timing assertion with sleep mock in test_retry.py`

### Test Results

- Before: pre-push hook failed on 3 pre-existing tests
- After: 3185 passed, 78.36% coverage, push succeeded