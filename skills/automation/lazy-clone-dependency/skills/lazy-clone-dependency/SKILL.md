---
name: lazy-clone-dependency
description: Pattern for lazy-cloning a missing external git repository dependency instead of skipping a workflow step
category: tooling
date: 2026-03-03
tags: [automation, clone, dependency, planner, mnemosyne, race-condition, fcntl, threading, gh]
user-invocable: false
---

# Lazy-Clone Dependency Pattern

## Overview

| Attribute | Value |
|-----------|-------|
| **Date** | 2026-03-03 |
| **Objective** | Fix planner silently skipping the advise step when `build/ProjectMnemosyne` was not present locally |
| **Outcome** | ✅ `_ensure_mnemosyne()` clones the repo on first use; advise step proceeds normally |
| **Project** | ProjectScylla |
| **Issue** | [#1324](https://github.com/HomericIntelligence/ProjectScylla/issues/1324) |
| **PR** | [#1326](https://github.com/HomericIntelligence/ProjectScylla/pull/1326) |

## When to Use

Use this skill when:

- An automation step logs `"<dependency> not found at <path>, skipping <step>"` and silently degrades instead of failing or recovering
- The missing resource is a **git repository** that can be cloned with `gh repo clone`
- Multiple parallel workers may trigger the missing-resource check simultaneously (race-condition risk)
- You want the first invocation to transparently clone the repo and subsequent invocations to be no-ops

Concrete trigger: `ProjectMnemosyne not found at build/ProjectMnemosyne, skipping advise step`

## Root Cause

The original `_run_advise()` checked `mnemosyne_root.exists()` and immediately returned `""` (empty) if missing:

```python
if not mnemosyne_root.exists():
    logger.warning("ProjectMnemosyne not found at build/ProjectMnemosyne, skipping advise step")
    return ""
```

This meant any fresh checkout or new machine would silently produce degraded planning output with no indication that the advise step was skipped due to a recoverable condition.

## Verified Workflow

### 1. Identify the skip condition

Find all `logger.warning(...skipping...)` patterns that guard an optional step against a missing external resource:

```python
if not some_external_resource.exists():
    logger.warning("Resource missing, skipping step")
    return ""
```

### 2. Extract a `_ensure_<resource>()` helper

Add a method to the class that:
1. Acquires a **class-level `threading.Lock`** (prevents double-clone across parallel threads in the same process)
2. Re-checks existence inside the lock (TOCTOU guard)
3. Acquires an **`fcntl` file lock** (prevents double-clone across parallel processes on the same machine)
4. Re-checks existence again inside the file lock
5. Runs `gh repo clone <org>/<repo> <dest>` via `subprocess.run(check=True)`
6. Returns `True` on success, `False` on `CalledProcessError` (with a warning log)

```python
class Planner:
    _mnemosyne_lock: threading.Lock = threading.Lock()

    def _ensure_mnemosyne(self, mnemosyne_root: Path) -> bool:
        """Clone ProjectMnemosyne if it does not exist locally."""
        with Planner._mnemosyne_lock:
            if mnemosyne_root.exists():
                return True

            lock_path = mnemosyne_root.parent / ".mnemosyne.lock"
            lock_path.parent.mkdir(parents=True, exist_ok=True)

            with open(lock_path, "w") as lock_file:
                fcntl.flock(lock_file, fcntl.LOCK_EX)
                try:
                    if mnemosyne_root.exists():
                        return True

                    logger.info(f"Cloning ProjectMnemosyne to {mnemosyne_root}...")
                    subprocess.run(
                        ["gh", "repo", "clone",
                         "HomericIntelligence/ProjectMnemosyne", str(mnemosyne_root)],
                        check=True, capture_output=True, text=True,
                    )
                    logger.info("ProjectMnemosyne cloned successfully")
                    return True

                except subprocess.CalledProcessError as e:
                    logger.warning(f"Failed to clone ProjectMnemosyne: {e.stderr or e}")
                    return False

                finally:
                    fcntl.flock(lock_file, fcntl.LOCK_UN)
```

### 3. Replace the skip guard with a clone-or-skip guard

```python
# BEFORE:
if not mnemosyne_root.exists():
    logger.warning("... skipping advise step")
    return ""

# AFTER:
if not mnemosyne_root.exists():
    if not self._ensure_mnemosyne(mnemosyne_root):
        return ""
```

### 4. Required imports

```python
import fcntl
import subprocess
import threading
from pathlib import Path
```

### 5. Write tests

| Test | What to assert |
|------|----------------|
| `test_clone_success` | `subprocess.run` called with correct `gh repo clone` args; returns `True` |
| `test_clone_failure` | `CalledProcessError` → returns `False` |
| `test_no_clone_if_exists` | directory present → `subprocess.run` NOT called; returns `True` |
| `test_concurrent_clone_only_once` | two threads race; clone called exactly once |
| `test_skips_when_mnemosyne_missing_and_clone_fails` | `_ensure_mnemosyne` returns `False` → `_run_advise` returns `""` |
| `test_clones_mnemosyne_when_missing` | `_ensure_mnemosyne` returns `True` → advise proceeds normally |

## Failed Attempts

| Approach | Why It Failed |
|----------|---------------|
| `threading.Lock` alone (no `fcntl`) | Only prevents races within one process; parallel `plan_issues.py` invocations across separate processes can still double-clone |
| Single `fcntl` lock without threading lock | `fcntl` locks are per-process, not per-thread; two threads in the same process share the file descriptor and the lock is re-entrant, allowing both through simultaneously |
| Checking `mnemosyne_root.exists()` outside the lock | Classic TOCTOU: both threads pass the check before either acquires the lock, leading to a double-clone attempt |

## Results & Parameters

### Files Changed

| File | Change |
|------|--------|
| `scylla/automation/planner.py` | Added `_mnemosyne_lock`, `_ensure_mnemosyne()`; updated `_run_advise()` |
| `tests/unit/automation/test_planner.py` | Added 4 new tests for `_ensure_mnemosyne`, updated 1 existing test |

### Clone Command Used

```bash
gh repo clone HomericIntelligence/ProjectMnemosyne <dest_path>
```

Requires `gh` CLI authenticated with repo access.

### Lock File Location

```
<mnemosyne_root.parent>/.mnemosyne.lock
```

The lock file is created alongside (not inside) the clone destination so it persists across clone attempts.

## Key Learnings

1. **Degrade gracefully but recover first**: "skip if missing" is appropriate only after a recovery attempt has failed. Silently skipping a recoverable condition hides problems from users.

2. **Double-locking for multi-process + multi-thread safety**: Use `threading.Lock` (thread-level) + `fcntl.flock(LOCK_EX)` (process-level) together. Neither alone is sufficient when parallel workers may span both.

3. **TOCTOU re-check pattern**: Always re-check the existence condition inside every lock level. The check-then-act race can happen between acquiring the threading lock and the file lock, and again after acquiring the file lock.

4. **`CalledProcessError` stderr**: Access `e.stderr` for diagnostic info; fall back to `str(e)` when stderr is empty.

5. **Test concurrency with real threads**: A `threading.Event` start gate makes concurrent unit tests deterministic without `time.sleep`.

## Verified On

| Project | Context |
|---------|---------|
| ProjectScylla | PR #1326 — issue #1324 reported skipping; fixed 2026-03-03 |
