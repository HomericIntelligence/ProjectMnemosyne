# State Machine Wiring — Session Notes

## Session date: 2026-02-22
## Branch: 1008-state-machine-refactor
## Commit: aa936c9

## Key insight: pre-seed scheduler before action map

The tricky part was resume behavior. When resuming from TIERS_RUNNING,
`action_dir_created` is skipped (state already past DIR_CREATED). But
`action_tiers_running` reads `scheduler` which was set by `action_dir_created`.

Solution: detect resume state BEFORE building the action map and pre-seed scheduler:
```python
if _current_exp_state in _resume_states:
    scheduler = self._setup_workspace_and_scheduler()
else:
    scheduler = None
```

## Ruff violations encountered

1. N814: `import X as _X` where X is a camelcase class — don't alias classes to SCREAMING constants
2. D401: inner function docstrings must be imperative — use comments instead for transition docs
3. E402: `warnings.warn()` between imports breaks ruff's E402 exemption for sys.path.insert patterns
4. F401: unused import after extracting functions to new module

## Subprocess mock path

Must patch at the module's own namespace, not globally:
- Wrong: `patch("subprocess.run", ...)`
- Right: `patch("scylla.e2e.model_validation.subprocess.run", ...)`

## Duplicate type annotation fix

```python
# Wrong:
scheduler: Any = None
if condition:
    scheduler: Any = other_value  # mypy: duplicate annotation

# Right:
scheduler: Any
if condition:
    scheduler = other_value
else:
    scheduler = None
```