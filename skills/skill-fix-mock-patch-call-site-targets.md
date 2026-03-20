---
name: 'Skill: Fix Mock Patch Call-Site Targets'
description: Fix unittest.mock.patch targets that point to the wrong namespace (definition-site
  instead of call-site), causing mocks to have no effect in isolated environments
category: testing
date: 2026-03-03
version: 1.0.0
user-invocable: false
---
# Skill: Fix Mock Patch Call-Site Targets

## Overview

| Property | Value |
|----------|-------|
| **Date** | 2026-03-03 |
| **Objective** | Fix `unittest.mock.patch` targets pointing to wrong namespace (definition-site vs. call-site) |
| **Outcome** | ✅ 30 patches corrected across 5 adapter test files; 3796 tests passing |
| **Context** | ProjectScylla #1124 — follow-up from #967 pre-push failures in worktree environments |

## When to Use This Skill

Use this skill when:
- Tests pass in the main repo but fail in worktree / isolated environments
- A mock has no visible effect (real function still executes, causing side-effects or timeouts)
- Grep reveals `patch("subprocess.run"` or other stdlib-global patch targets in test files
- Adding new adapter tests that call external processes via `subprocess.run`
- CI failures report unexpected subprocess calls despite mock setup

## The Core Rule

> **Patch where the name is used, not where it is defined.**

Python's `unittest.mock.patch` replaces a name in a specific namespace. The correct target depends on how the calling module imports the name:

| Import Style | Call Style | Correct Patch Target |
|---|---|---|
| `import subprocess` | `subprocess.run(...)` | `"<calling_module>.subprocess.run"` |
| `from subprocess import run` | `run(...)` | `"<calling_module>.run"` |
| `import time` | `time.sleep(...)` | `"time.sleep"` ✅ (module object attr, works globally) |

## Verified Workflow

### Step 1: Audit incorrect patches

```bash
# Find patches using stdlib global namespace (likely wrong for module-level imports)
grep -rn 'patch("subprocess\.' tests/
grep -rn 'patch("os\.' tests/
grep -rn 'patch("shutil\.' tests/
grep -rn 'patch("pathlib\.' tests/
```

### Step 2: Check the import style in the module under test

```bash
grep -n 'import subprocess' scylla/adapters/base_cli.py
grep -n 'subprocess.run' scylla/adapters/base_cli.py
```

### Step 3: Determine the correct call-site target

For `base_cli.py` (base class for Cline, Goose, OpenAI Codex, OpenCode):
```python
# WRONG
with patch("subprocess.run", return_value=mock_result):

# CORRECT
with patch("scylla.adapters.base_cli.subprocess.run", return_value=mock_result):
```

For adapters with their own direct `subprocess.run` call (`claude_code.py`):
```python
# CORRECT
with patch("scylla.adapters.claude_code.subprocess.run", return_value=mock_result):
```

### Step 4: Apply fix using replace_all

Use `Edit` with `replace_all=true` to fix all occurrences in each file at once:
```
old_string: patch("subprocess.run",
new_string: patch("scylla.adapters.base_cli.subprocess.run",
```

### Step 5: Verify

```bash
pixi run pytest tests/unit/adapters/ -v --no-cov
pixi run pytest tests/unit/ --no-cov
```

## Exceptions: When Global Patches ARE Correct

### `time.sleep`
```python
patch("time.sleep", ...)  # CORRECT — no fix needed
```
When a module uses `import time; time.sleep(...)`, patching `"time.sleep"` patches the attribute on the `time` module object. Since Python caches module objects in `sys.modules`, all callers see the same patched attribute. This works correctly in all environments.

### `sys.path`-inserted script modules
When `conftest.py` inserts a script directory into `sys.path` at collection time, the script is importable as a named module (e.g., `export_data`). Patching `"export_data.function_name"` is the correct call-site target — no `create=True` needed if `sys.path.insert` occurs before fixture invocation.

## Results (ProjectScylla #1124)

| File | Patches Fixed | Old Target | New Target |
|------|:---:|---|---|
| `tests/unit/adapters/test_claude_code.py` | 6 | `subprocess.run` | `scylla.adapters.claude_code.subprocess.run` |
| `tests/unit/adapters/test_cline.py` | 6 | `subprocess.run` | `scylla.adapters.base_cli.subprocess.run` |
| `tests/unit/adapters/test_goose.py` | 6 | `subprocess.run` | `scylla.adapters.base_cli.subprocess.run` |
| `tests/unit/adapters/test_openai_codex.py` | 6 | `subprocess.run` | `scylla.adapters.base_cli.subprocess.run` |
| `tests/unit/adapters/test_opencode.py` | 6 | `subprocess.run` | `scylla.adapters.base_cli.subprocess.run` |

**Total**: 30 patches corrected — all 3796 tests passing.

## Results & Parameters

Copy-paste ready configurations and expected outputs.

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
|---------|----------------|---------------|----------------|
| N/A | Direct approach worked | N/A | Solution was straightforward |
## Future Prevention

Add this to adapter test review checklist: any `patch("subprocess.run"` should be `patch("<module>.subprocess.run"`. Consider a ruff/grep CI check:

```bash
# Add to pre-commit or CI quality gate
grep -rn 'patch("subprocess\.run"' tests/ && echo "ERROR: Use call-site patch targets" && exit 1 || true
```
