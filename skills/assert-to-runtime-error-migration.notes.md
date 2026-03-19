# Raw Session Notes — assert-to-runtime-error-migration

## Session Context

- **Date**: 2026-02-27
- **Project**: ProjectScylla
- **Branch**: `1143-auto-impl`
- **Issue**: #1143 — Replace assert guards with RuntimeError

## Discovery

```bash
grep -rn "noqa: S101" scylla/
```

Found 4 sites:
1. `scylla/executor/runner.py:486` — `assert self._state is not None`
2. `scylla/e2e/llm_judge.py:930` — `assert last_parse_error is not None`
3. `scylla/e2e/workspace_manager.py:198` — `assert self.commit is not None`
4. `scylla/e2e/workspace_manager.py:244` — `assert self.commit is not None`

## Edits Applied

### scylla/e2e/workspace_manager.py line 198 (_checkout_commit)

```python
# BEFORE:
assert self.commit is not None  # noqa: S101
# Try to fetch the specific commit

# AFTER:
if self.commit is None:
    raise RuntimeError("commit must be set before calling _checkout_commit")
# Try to fetch the specific commit
```

### scylla/e2e/workspace_manager.py line 244 (_ensure_commit_available)

```python
# BEFORE:
assert self.commit is not None  # noqa: S101
# Check if commit already exists in object store

# AFTER:
if self.commit is None:
    raise RuntimeError("commit must be set before calling _ensure_commit_available")
# Check if commit already exists in object store
```

### scylla/e2e/llm_judge.py line 930 (retry loop else)

```python
# BEFORE:
    assert last_parse_error is not None  # noqa: S101
    raise last_parse_error

# AFTER:
    if last_parse_error is None:
        raise RuntimeError("Judge retry loop exhausted but last_parse_error is None")
    raise last_parse_error
```

### scylla/executor/runner.py line 486 (_finalize_test_summary)

```python
# BEFORE:
            assert self._state is not None  # noqa: S101
            save_state(self._state, self.config.state_file)

# AFTER:
            if self._state is None:
                raise RuntimeError("_state must be initialized before finalizing test summary")
            save_state(self._state, self.config.state_file)
```

## Tests Added

### tests/unit/e2e/test_workspace_manager.py (class TestCentralizedRepos)

```python
def test_checkout_commit_raises_if_commit_none(self, tmp_path: Path) -> None:
    manager = WorkspaceManager(experiment_dir=tmp_path, repo_url="...", commit=None)
    with pytest.raises(RuntimeError, match="commit must be set before calling _checkout_commit"):
        manager._checkout_commit()

def test_ensure_commit_available_raises_if_commit_none(self, tmp_path: Path) -> None:
    manager = WorkspaceManager(experiment_dir=tmp_path, repo_url="...", commit=None)
    with pytest.raises(RuntimeError, match="commit must be set before calling _ensure_commit_available"):
        manager._ensure_commit_available()
```

### tests/unit/e2e/test_llm_judge.py (class TestRunLlmJudgeRetry)

```python
def test_raises_value_error_not_runtime_error_when_parse_fails(self, tmp_path: Path) -> None:
    bad = "Not valid JSON at all"
    with pytest.raises(ValueError):
        self._run_with_call_side_effects(tmp_path, [(bad, "", bad)] * 3)
```

### tests/unit/executor/test_runner.py (new class TestFinalizeTestSummaryGuard)

Also required adding `EvalSummary` to the import block.

```python
class TestFinalizeTestSummaryGuard:
    def test_raises_runtime_error_when_state_is_none_and_state_file_configured(self, tmp_path):
        config = RunnerConfig(state_file=tmp_path / "state.json")
        runner = EvalRunner(mock_docker, mock_tier_loader, config)
        assert runner._state is None
        summary = EvalSummary(test_id="test-001", started_at="2026-01-01T00:00:00+00:00")
        with pytest.raises(RuntimeError, match="_state must be initialized"):
            runner._finalize_test_summary(summary)
```

## Issues Encountered

1. **Missing import**: `EvalSummary` not in `test_runner.py` imports → `NameError` on first run. Fixed by adding to import block.
2. **Ruff formatter**: Pre-commit reformatted 2 files (line wrapping). Required second `pre-commit run --all-files` to confirm clean.
3. **For-else guard test**: First attempt tried `StopIteration` trick to test the unreachable guard path. Abandoned in favor of testing observable adjacent behavior.

## Final State

```
grep -rn "noqa: S101" scylla/  # → empty (0 results)
3261 tests pass
78.39% coverage
All pre-commit hooks pass
PR #1211 created, auto-merge enabled
```