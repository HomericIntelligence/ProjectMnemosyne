---
name: architecture-metaclass-threadlocal-thread-safety
description: "Two complementary thread-safety shapes for shared Python state. (A) VERIFIED: make class-level attribute access thread-safe with a metaclass __getattr__ + threading.local() so each thread gets isolated state. (B) PROPOSED/plan-only: retrofit a module-global shared cache (set/dict) for a ThreadPoolExecutor by replacing it with a threading.Lock-guarded, repo-keyed dict. Use when: (1) a class uses mutable class attributes shared across threads, (2) you need per-thread enable/disable state while preserving the Class.ATTR access pattern, (3) a process-global cache (e.g. a gh label cache) is read/written unguarded from a multi-threaded coordinator and one thread's cache masks another's, (4) you are planning to key a shared cache per-repo and must decide between threading.local() and a lock-guarded keyed dict, (5) you need to reason about whether a per-key cache is a NO-OP under a shared-CWD thread pool where the real isolation comes from the lock."
category: architecture
date: 2026-07-05
version: "1.1.0"
user-invocable: false
verification: unverified
history: architecture-metaclass-threadlocal-thread-safety.history
tags:
  - thread-safety
  - metaclass
  - threading-local
  - threading-lock
  - shared-cache
  - repo-keyed-cache
  - module-global-state
  - thread-pool-executor
  - gil-not-atomic
  - load-bearing-lock
  - planning-risks
  - python
  - immutable-state
---

# Thread-Safe Shared State: Metaclass + threading.local() (verified) and Lock-Guarded Repo-Keyed Cache (proposed)

## Overview

| Field | Value |
| ------- | ------- |
| **Date** | 2026-07-05 |
| **Objective** | Capture two complementary thread-safety shapes: (A) per-thread isolated class state via metaclass + `threading.local()`; (B) shared-across-threads-but-keyed-per-repo cache via a `threading.Lock`-guarded dict |
| **Outcome** | (A) Success — backward-compatible, thread-safe, 15 tests pass (verified-local). (B) Plan-only — a fix design for a module-global label-cache bug; NOT applied, NOT tested, CI NOT confirmed |
| **Verification** | Mixed: pattern (A) is **verified-local** (see `## Verified Workflow`); pattern (B) is **unverified** / plan-only (see `## Proposed Workflow`). Top-level frontmatter is `unverified` because the newest material is unvalidated — do not treat pattern (B) as proven |
| **History** | [changelog](./architecture-metaclass-threadlocal-thread-safety.history) |

## When to Use

**Pattern (A) — per-thread isolated class state (verified):**

- A class stores configuration as **mutable class attributes** (e.g., ANSI color codes, feature flags)
- Methods like `disable()` **mutate class attributes**, affecting all threads and modules simultaneously
- You need **per-thread state isolation** (one thread disabling doesn't affect others)
- You want to preserve the **`Class.ATTR` access pattern** (no API change for consumers)
- Python 3.10+ (no `__class_getattr__` available until 3.12)

**Pattern (B) — shared-but-repo-keyed cache under a thread pool (proposed / plan-only):**

- A **module-global cache** (bare `set[str] | None`, or a `dict`) is read AND written **without a lock** and is now touched by a `ThreadPoolExecutor` (e.g. a pipeline coordinator running stages across repos)
- The cache must be **shared** across threads (per-thread caches would defeat caching) but its entries are **partitioned by a key that is NOT the thread** — e.g. per repo
- Thread A's cache entry masks thread B's → dropped durable writes → crash/restart re-seeds at the wrong state
- You are deciding between `threading.local()` (wrong here — gives each thread an empty cache) and a `threading.Lock`-guarded, key-partitioned `dict` (correct)
- You are about to key the cache by the *current-directory* repo and need to check whether that key actually varies per thread under a **shared-CWD** thread pool

## Verified Workflow

> Pattern (A) below is **verified-local** (ProjectHephaestus issue #30 / PR #68, 15/15 tests, full suite 394/394). Pattern (B) is under `## Proposed Workflow` and is unverified.

### Quick Reference

```python
import threading

_state = threading.local()

_CODES: dict[str, str] = {"OKGREEN": "\033[92m", "FAIL": "\033[91m"}

class _Meta(type):
    def __getattr__(cls, name: str) -> str:
        if name in _CODES:
            return _CODES[name] if getattr(_state, "enabled", True) else ""
        raise AttributeError(f"type object {cls.__name__!r} has no attribute {name!r}")

class Colors(metaclass=_Meta):
    @staticmethod
    def disable() -> None:
        _state.enabled = False

    @staticmethod
    def enable() -> None:
        _state.enabled = True
```

### Detailed Steps

1. **Extract values to an immutable dict**: Move all mutable class attributes into a module-level `dict[str, str]` that is never mutated.

2. **Add `threading.local()` state**: Create a module-level `_state = threading.local()` to hold per-thread boolean flags.

3. **Create a metaclass with `__getattr__`**: The metaclass intercepts attribute access on the class itself (not instances). Since the color names are no longer class attributes, Python falls through to `__getattr__` on every access.

4. **Compute on access**: In `__getattr__`, check the thread-local flag and return either the real value or an empty string.

5. **Replace mutating methods**: `disable()` and `enable()` now just set `_state.enabled = False/True` instead of overwriting 9+ class attributes.

6. **Default to enabled**: Use `getattr(_state, "enabled", True)` so new threads that haven't called `disable()` get colors by default.

### Why Metaclass (Not Other Approaches)

| Approach | Problem |
| ---------- | --------- |
| `threading.Lock` around mutations | Still global state — all threads share one enable/disable flag |
| Instance-based `Colors()` | Breaks the `Colors.ATTR` class-level access pattern used everywhere |
| `__class_getattr__` (PEP 657) | Python 3.12+ only, not available in 3.10 |
| Module-level `__getattr__` | Changes API from `Colors.ATTR` to `colors.ATTR` (module access) |
| **Metaclass `__getattr__`** | Works on 3.10+, preserves `Colors.ATTR`, per-thread via `threading.local()` |

### threading.local() vs Lock-Guarded Keyed Cache — which shape?

The two patterns in this skill are **opposites**, and picking wrong is the core mistake:

| You want… | Tool | Why |
| ----------- | ------ | ----- |
| Each thread to have **its own** isolated value (colors on/off) | `threading.local()` | Per-thread storage; no lock needed; one thread's write is invisible to others |
| A cache **shared** across threads but partitioned by a **non-thread** key (repo) | `threading.Lock` + keyed `dict` | `threading.local()` would give each thread an empty cache and defeat caching; the lock serializes read-modify-write of the shared dict |

If the partition key is "the thread," use `threading.local()`. If the partition key is anything else (repo, tenant, URL), use a lock-guarded keyed dict — see Proposed Workflow.

### Testing Thread Safety

```python
import threading

def test_disable_does_not_affect_other_thread():
    barrier = threading.Barrier(2)
    results = {}

    def disabler():
        Colors.disable()
        barrier.wait(timeout=5)
        results["disabler"] = Colors.OKGREEN

    def reader():
        barrier.wait(timeout=5)
        results["reader"] = Colors.OKGREEN

    t1 = threading.Thread(target=disabler)
    t2 = threading.Thread(target=reader)
    t1.start(); t2.start()
    t1.join(timeout=5); t2.join(timeout=5)

    assert results["disabler"] == ""
    assert results["reader"] == "\033[92m"
```

Use `threading.Barrier` to synchronize threads so the reader checks *after* the disabler has called `disable()`.

## Proposed Workflow

> **Warning:** This workflow has not been validated end-to-end. It is a plan-only design
> for a module-global shared-cache bug (ProjectHephaestus issue #1858). No code was
> applied, no tests were run, and CI was not confirmed. Treat every step — and especially
> the risks below — as a hypothesis until CI confirms it. Line numbers cited were read
> once and will drift; **re-grep before relying on any coordinate.**

### The bug shape (module-global unguarded cache under a thread pool)

`github_api/labels.py` `gh_list_labels()` reads/writes an unguarded module global
`_api._label_cache` (a bare `set[str] | None`) that is neither repo-keyed nor
lock-protected. Once a pipeline coordinator runs stages **multi-threaded across repos**
(`ThreadPoolExecutor` in `worker_pool.py`; one `PipelineGitHub` per repo in
`coordinator.py`), thread A's cache masks thread B's labels → dropped durable `state:*`
label writes → a crash-restart re-seed lands at the wrong stage.

### Proposed fix (two parts)

1. **Make the org-scoped path always refresh.** Have `PipelineGitHub._label_names()`
   call `gh_list_labels(refresh=True)` so the org-scoped `_gh --repo` path (which is
   already per-repo safe) never serves a stale process-global cache.

2. **Replace the global with a lock-guarded, repo-keyed dict.** Swap
   `_label_cache: set[str] | None` for `_label_cache: dict[str | None, set[str]]`
   guarded by a module-level `threading.Lock`. Resolve the repo slug via
   `get_repo_info()` (wrapped in `try/except → None`). Return **defensive copies**
   (`set(cached)`) so callers cannot mutate cached entries.

```python
import threading

_label_cache: dict[str | None, set[str]] = {}
_label_cache_lock = threading.Lock()

def _repo_key() -> str | None:
    try:
        info = get_repo_info()               # may shell out — SEE RISK 2
        return f"{getattr(info, 'owner', None)}/{getattr(info, 'name', None)}"
    except Exception:
        return None

def gh_list_labels(refresh: bool = False) -> set[str]:
    key = _repo_key()
    with _label_cache_lock:                  # LOAD-BEARING — read-modify-write is NOT atomic
        if not refresh and key in _label_cache:
            return set(_label_cache[key])    # defensive copy
    labels = _fetch_labels_from_gh(key)      # do slow I/O OUTSIDE the lock
    with _label_cache_lock:
        _label_cache[key] = set(labels)
        return set(_label_cache[key])
```

### Risks & Load-Bearing Assumptions (plan-only — the reviewer must focus here)

1. **The per-repo KEY may be a NO-OP under a shared-CWD `ThreadPoolExecutor` (deepest
   risk).** `get_repo_info()` reads the *current-directory* repo. If all worker threads
   share ONE process CWD (they do not `chdir` per repo), the key does NOT differ per
   thread, so the **`threading.Lock` — not the key — is doing all the isolation work**,
   and the "repo-keyed" framing is illusory. Verify whether worker threads `chdir`
   per-repo or share CWD **before** claiming the key isolates anything. If they share
   CWD, the truly structural fix is to make every path repo-SCOPED (`_gh --repo <slug>`,
   already safe) rather than keying a process-global cache at all — that may be preferable
   to this design.

2. **The repo-slug resolver's cost/safety per call is UNVERIFIED.** `get_repo_info()`
   may shell out to `git`/`gh`. Calling it on **every** `gh_list_labels` / `gh_create_label`
   invocation (including cache hits) could add latency or introduce its own failure mode,
   and the plan did NOT verify that it never itself mutates shared state. The `try/except
   → None` fallback hides failures but does not address cost. Measure/confirm before
   wiring it into the hot path.

3. **"The GIL makes bare dict writes mostly safe" is a HAZARD, not a reassurance.**
   Read-modify-write (`entry.add(...)`, get-then-set) is **NOT atomic** even under the
   GIL — a thread can be suspended between the read and the write. The `threading.Lock`
   is **load-bearing, not decorative**. Do all mutation inside the lock; do slow I/O
   (the actual `gh` fetch) *outside* it to avoid serializing network calls.

4. **Cited line numbers and attribute names are unverified.** Coordinates
   (`labels.py:24-31,52-53`, `pipeline_github.py:192,204-215`, `__init__.py:28,42-44`,
   test reset sites `test_github_api.py:1115,1167,1179,1235`) were read once and will
   drift — re-grep. The slug assumes the repo-info object exposes `.owner`/`.name`;
   this used defensive `getattr` but did NOT confirm the attribute names — verify them.

5. **Test-seam migration touches multiple sites.** Tests reset the cache with
   `_label_cache = None`; migrating to a dict means every reset site must become
   `_label_cache = {}` (or `_label_cache.clear()`). Missing one leaves a test resetting
   to the wrong type and silently poisoning later tests.

### Proposed test plan (unvalidated)

- A `ThreadPoolExecutor` test that concurrently calls `gh_list_labels` for two different
  repo slugs and asserts neither masks the other (guards against the RISK-1 no-op key —
  set distinct keys explicitly rather than relying on CWD).
- A test that mutates a returned label set and asserts the cached entry is unchanged
  (guards the defensive-copy contract).
- A concurrent add/read stress test under the lock to catch the non-atomic
  read-modify-write of RISK 3.

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
| --------- | ---------------- | --------------- | ---------------- |
| `typing.Dict` import | Used `from typing import Dict` for type annotation | Ruff UP035/UP006 flags it as deprecated in 3.10+ | Use builtin `dict[str, str]` directly |
| Import ordering | Put `from hephaestus... import Colors, _CODES, _state` | Ruff I001 wants underscore-prefixed names sorted first | Ruff sorts `_CODES` before `Colors` (leading underscore sorts before uppercase) |
| `threading.local()` for a shared cache | (Plan-only, considered) Give each thread its own label cache to "avoid the lock" | `threading.local()` gives every thread an EMPTY cache — it defeats caching entirely and never shares a fetched label set across threads; wrong tool when the partition key is the repo, not the thread | If the partition key is anything other than "the thread," use a `threading.Lock`-guarded keyed `dict`, not `threading.local()` |
| Repo-key a process-global cache under a shared-CWD pool | (Plan-only) Key `_label_cache` by `get_repo_info()` (current-dir repo) assuming it differs per worker thread | If all worker threads share one process CWD, the CWD-derived key does NOT vary per thread — the key is a no-op and only the lock isolates; the "per-repo cache" is illusory | Verify threads `chdir` per-repo before claiming the key isolates; if they share CWD, prefer making every path repo-SCOPED (`_gh --repo <slug>`) over keying a global cache |
| Rely on the GIL for "mostly safe" bare dict writes | (Plan-only, tempting aside) Skip the lock because "CPython dict writes are atomic under the GIL" | Read-modify-write (`entry.add()`, get-then-set) is NOT atomic — a thread can be preempted between read and write, corrupting the shared dict | The `threading.Lock` is load-bearing; do mutation inside the lock and slow I/O outside it |

## Results & Parameters

**Pattern (A) — verified-local:**

- **Files changed**: 2
  - `hephaestus/cli/colors.py`: Replaced 9 mutable class attributes + `disable()` mutation with metaclass + `threading.local()` pattern
  - `tests/unit/cli/test_colors.py`: Rewrote 5 existing tests, added 5 thread-safety tests (15 total)
- **Test results**: 15/15 pass, 100% coverage on `colors.py`, full suite 394/394 pass
- **PR**: HomericIntelligence/ProjectHephaestus#68

**Pattern (B) — unverified / plan-only (ProjectHephaestus issue #1858):**

- **Proposed files to change** (coordinates unverified — re-grep):
  - `github_api/labels.py` — replace `_label_cache: set[str] | None` with a
    `threading.Lock`-guarded `dict[str | None, set[str]]`; return defensive copies
  - `github_api/pipeline_github.py` (~`:192`) — `_label_names()` calls
    `gh_list_labels(refresh=True)`
  - `github_api/__init__.py` (~`:28`) — `get_repo_info()` import already present
  - `tests/.../test_github_api.py` — migrate `_label_cache = None` reset sites to `{}`
- **Status**: NO code applied, NO tests run, CI NOT confirmed. This is a design + risk
  register only.

## Verified On

| Project | Context | Details |
| --------- | --------- | --------- |
| ProjectHephaestus | Issue #30 — thread-safe Colors class (pattern A) | PR #68, all 394 tests pass (verified-local) |
| ProjectHephaestus | Issue #1858 — module-global label-cache corruption under multithreaded coordinator (pattern B) | Plan-only; unverified, no PR yet |
