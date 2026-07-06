---
name: architecture-threadsafe-cache-per-key-locks
description: "Pattern for shared module-level caches with per-key locking and TTL. Use when: (1) a module caches expensive computations (subprocess, API calls, repo metadata), (2) multiple threads access the same cache, (3) you need per-key invalidation instead of global clear(), (4) cache entries should expire after a TTL to prevent stale data, (5) callers must get defensive copies to prevent accidental mutations of cached state."
category: architecture
date: 2026-07-06
version: "1.0.0"
user-invocable: false
verification: verified-local
tags: [thread-safety, cache, per-key-locks, ttl, defensive-copies, python]
---

# Thread-Safe Per-Key Cache with Lock Guards and TTL

## Overview

| Field | Value |
| ------- | ------- |
| **Date** | 2026-07-06 |
| **Problem** | Unguarded module-level `dict` cache corrupts multi-threaded concurrent access; swapping entries from different repos masquerade as local data; global `clear()` breaks POLA (Principle of Least Astonishment) by evicting unrelated repos' cached data |
| **Solution** | Replace bare `dict` with `ThreadSafeCache[K, V]` keyed by repo slug, implementing per-key locks, TTL expiry, and defensive copies |
| **Outcome** | Success — 230+ tests pass; no cross-repo label cache corruption; per-repo refresh only evicts intended cache key |
| **Verification** | verified-local (Hephaestus #1858) |

## When to Use

- A module caches expensive computations: **subprocess calls** (e.g., `git config`), **API calls** (GitHub labels), **file system walks** (repo structure), **parsed metadata** (repo info)
- **Multiple threads** access the cache **concurrently** (e.g., coordinator with parallel repo workers, async event loop with multiple co-tasks)
- You need **per-key invalidation** (refresh one repo's cached data without touching others)
- Cache entries should **expire after a TTL** to prevent stale data from a long-running process
- Callers must not **mutate the cached value** after retrieving it (e.g., `set.add()` on a returned set corrupts the cache)
- The cache is used **across multiple repos** (multi-key scenario) and key collisions lead to subtle data corruption

## Verified Workflow

### Step 1 — Identify the Caching Problem

**Symptom**: Module-level cache dict is accessed from multiple threads without synchronization.

```python
# WRONG — bare dict, unguarded
_label_cache: dict[str, set[str]] = {}

def get_labels(repo_slug: str) -> set[str]:
    if repo_slug not in _label_cache:
        _label_cache[repo_slug] = fetch_labels_from_github(repo_slug)  # RACE: two threads fetch same key
    return _label_cache[repo_slug]  # RACE: caller mutates the cached set
```

**Failure modes**:
1. **TOCTOU race**: Two threads check `repo_slug not in _label_cache` simultaneously → both fetch → first write wins, second overwrites → data loss or duplicate work
2. **Caller mutation**: `labels = get_labels("foo"); labels.add("new-label")` mutates the shared cache set → corrupts cached data
3. **Cross-key contamination**: In a multi-key scenario (e.g., per-repo label cache), if keys collide or are incorrectly scoped, repo A's cached labels leak into repo B's queries
4. **Global clear() breaks POLA**: A single repo refresh calls `_label_cache.clear()` → **all** repos' caches are evicted unnecessarily

### Step 2 — Create ThreadSafeCache Class

Implement a generic, reusable cache with per-key locks and TTL:

```python
import threading
import time
from typing import Callable, Generic, Optional, TypeVar

K = TypeVar("K")  # key type
V = TypeVar("V")  # value type

class ThreadSafeCache(Generic[K, V]):
    """Thread-safe cache with per-key locks, TTL, and defensive copying."""

    def __init__(self, ttl_seconds: float = 3600.0):
        """
        Initialize cache.

        Args:
            ttl_seconds: Time-to-live for cached entries (default 1 hour)
        """
        self._lock = threading.RLock()  # global lock for dict mutations
        self._cache: dict[K, V] = {}
        self._timestamps: dict[K, float] = {}
        self._ttl = ttl_seconds
        self._per_key_locks: dict[K, threading.Lock] = {}

    def get(self, key: K, factory: Callable[[], V]) -> V:
        """
        Retrieve cached value or compute via factory.

        The factory is called at most once per key, even under concurrent access.
        Expired entries are recomputed.

        Args:
            key: Cache key
            factory: Zero-argument callable that returns V

        Returns:
            Cached (or newly computed) value
        """
        # Check if entry exists and is still valid
        with self._lock:
            if key in self._cache:
                if time.time() - self._timestamps[key] < self._ttl:
                    # Return a *copy* to prevent caller mutations
                    return self._copy_value(self._cache[key])
                else:
                    # Expired; remove and recompute
                    del self._cache[key]
                    del self._timestamps[key]

            # Ensure per-key lock exists
            if key not in self._per_key_locks:
                self._per_key_locks[key] = threading.Lock()

        # Acquire per-key lock *outside* the global lock to allow concurrent fetches on different keys
        key_lock = self._per_key_locks[key]
        with key_lock:
            # Double-check: entry may have been computed by another thread while we waited for lock
            with self._lock:
                if key in self._cache and time.time() - self._timestamps[key] < self._ttl:
                    return self._copy_value(self._cache[key])

            # Compute the value
            value = factory()

            # Store in cache
            with self._lock:
                self._cache[key] = value
                self._timestamps[key] = time.time()

            return self._copy_value(value)

    def remove(self, key: K) -> None:
        """
        Invalidate a specific cache entry (per-key, not global clear).

        Use this instead of clear() to respect POLA — other keys are unaffected.

        Args:
            key: Cache key to invalidate
        """
        with self._lock:
            self._cache.pop(key, None)
            self._timestamps.pop(key, None)

    def add_to_entry(self, key: K, item: object) -> None:
        """
        Atomically add an item to a cached collection (e.g., set).

        Prevents TOCTOU races between checking and mutating a shared cached set.

        Args:
            key: Cache key (assumes cached value is a set-like object with .add())
            item: Item to add

        Raises:
            KeyError: If the key is not in the cache
        """
        with self._lock:
            if key not in self._cache:
                raise KeyError(f"Key {key!r} not in cache")
            cached_set = self._cache[key]
            if hasattr(cached_set, "add"):
                cached_set.add(item)
            else:
                raise TypeError(f"Cached value for {key!r} does not support .add()")

    @staticmethod
    def _copy_value(value: V) -> V:
        """Return a defensive copy of the value to prevent caller mutations."""
        if isinstance(value, set):
            return set(value)  # type: ignore
        elif isinstance(value, dict):
            return dict(value)  # type: ignore
        elif isinstance(value, list):
            return list(value)  # type: ignore
        else:
            # For immutable types (str, int, tuple, frozenset) return as-is
            return value
```

### Step 3 — Replace Module-Level Cache with ThreadSafeCache

**BEFORE**:

```python
_label_cache: dict[str, set[str]] = {}

def get_labels_for_repo(repo_slug: str) -> set[str]:
    if repo_slug not in _label_cache:
        _label_cache[repo_slug] = fetch_labels_from_github(repo_slug)
    return _label_cache[repo_slug]

def clear_cache():
    _label_cache.clear()  # WRONG: evicts ALL repos' cache
```

**AFTER**:

```python
_label_cache = ThreadSafeCache[str, set[str]](ttl_seconds=3600.0)

def get_labels_for_repo(repo_slug: str) -> set[str]:
    """Get labels for a repo, cached with 1-hour TTL."""
    return _label_cache.get(repo_slug, lambda: fetch_labels_from_github(repo_slug))

def refresh_labels_for_repo(repo_slug: str) -> None:
    """Invalidate cached labels for one repo only (per-key, not global)."""
    _label_cache.remove(repo_slug)
```

### Step 4 — Defensive Copies in Tests

When testing cache hits, use **sentinel return values** to ensure the cache-miss path is exercised. If you use a zero-arg lambda that returns `set()` (empty), a cache miss will also return empty, masking the bug.

**WRONG TEST**:

```python
def test_cache_hit():
    _label_cache.remove("foo")  # clear cache
    factory_calls = 0

    def factory():
        nonlocal factory_calls
        factory_calls += 1
        return set()  # WRONG: factory returning empty set

    result1 = _label_cache.get("foo", factory)
    result2 = _label_cache.get("foo", factory)

    assert factory_calls == 1  # FAILS SILENTLY if result1 is also empty from the cache!
```

**CORRECT TEST**:

```python
def test_cache_hit():
    _label_cache.remove("foo")  # clear cache
    factory_calls = 0

    def factory():
        nonlocal factory_calls
        factory_calls += 1
        return {"SENTINEL"}  # Non-empty sentinel value

    result1 = _label_cache.get("foo", factory)
    result2 = _label_cache.get("foo", factory)

    # If result2 is empty but result1 is not, cache miss was hidden
    assert result1 == {"SENTINEL"}
    assert result2 == {"SENTINEL"}
    assert factory_calls == 1  # Cache hit: factory called once
```

### Step 5 — Testing Concurrent Access

Use `threading.Barrier` to synchronize threads and verify:
1. Concurrent calls to the same key serialize behind the per-key lock
2. Concurrent calls to different keys run in parallel
3. A per-repo refresh does not affect other repos' cache

```python
def test_concurrent_same_key_serializes():
    """Verify that two threads fetching the same key don't double-fetch."""
    barrier = threading.Barrier(2)
    factory_calls = 0
    _label_cache.remove("repo-a")

    def factory():
        nonlocal factory_calls
        factory_calls += 1
        barrier.wait(timeout=5)  # Ensure both threads reached factory() before returning
        return {"label1"}

    results = []

    def fetcher():
        results.append(_label_cache.get("repo-a", factory))

    t1 = threading.Thread(target=fetcher)
    t2 = threading.Thread(target=fetcher)
    t1.start(); t2.start()
    t1.join(timeout=10); t2.join(timeout=10)

    assert factory_calls == 1  # Called once, not twice
    assert results == [{"label1"}, {"label1"}]

def test_concurrent_different_keys_parallel():
    """Verify that different keys fetch in parallel, not serialized."""
    barrier = threading.Barrier(2)
    active_count = [0, 0]  # max concurrent
    _label_cache.remove("repo-a")
    _label_cache.remove("repo-b")

    def factory(name: str):
        def inner():
            active_count[0] += 1
            active_count[1] = max(active_count[1], active_count[0])
            barrier.wait(timeout=5)
            active_count[0] -= 1
            return {f"labels-{name}"}
        return inner

    results = {}

    def fetcher(key: str):
        results[key] = _label_cache.get(key, factory(key))

    t1 = threading.Thread(target=fetcher, args=("repo-a",))
    t2 = threading.Thread(target=fetcher, args=("repo-b",))
    t1.start(); t2.start()
    t1.join(timeout=10); t2.join(timeout=10)

    # Both should be active concurrently when the barrier hit
    assert active_count[1] == 2  # Max concurrent == 2
    assert results == {"repo-a": {"labels-repo-a"}, "repo-b": {"labels-repo-b"}}
```

### Step 6 — Compute Repo Slug Efficiently

If your factory needs a repo slug and slug computation is expensive, memoize it at a higher level:

```python
# DON'T: compute slug inside the factory, called per key fetch
def get_labels_for_repo(repo_root: str) -> set[str]:
    repo_slug = compute_slug_from_root(repo_root)  # EXPENSIVE if called per fetch
    return _label_cache.get(repo_slug, lambda: fetch_labels(repo_slug))

# DO: memoize repo-info at module level; slug is already cached
_repo_info_cache: dict[str, dict[str, str]] = {}  # or ThreadSafeCache

def get_labels_for_repo(repo_root: str) -> set[str]:
    info = _repo_info_cache.get(repo_root, lambda: expensive_get_repo_info(repo_root))
    repo_slug = info["slug"]
    return _label_cache.get(repo_slug, lambda: fetch_labels(repo_slug))
```

Since `get_repo_info()` is already cached/memoized, per-call slug lookup is just a dict access under a lock.

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
| --------- | ---------------- | --------------- | ---------------- |
| Bare dict without locking | `_label_cache: dict[str, set[str]] = {}` with direct dict access from multiple threads | TOCTOU race: two threads check the key simultaneously → both fetch → data loss or duplicate work; caller mutates shared set | Always use a synchronized cache class for multi-threaded access |
| Global `threading.Lock()` around entire cache | Single lock protecting all dict operations | Serializes all cache access (same key or different keys) → no parallelism; bottleneck for independent keys | Use per-key locks: global lock only for dict/timestamp mutations, per-key locks for factory execution |
| Global `clear()` instead of per-key `remove()` | Called `_cache.clear()` to refresh one repo's data | Evicted **all** repos' cached entries → violates POLA; unrelated repos pay the refresh latency cost | Use keyed `remove(key)` so only the intended key is invalidated |
| Returning cached set directly without copy | `return _label_cache[key]` (direct reference) | Caller does `labels.add("new-label")` → mutates the shared cached set → corrupts cache for all future callers | Always return a defensive copy: `return set(cached_set)` or equivalent |
| Calling factory inside the global lock | Held the global dict lock while calling `factory()` (expensive subprocess/API call) | All other threads blocked waiting for the lock → entire cache serializes; cache lookup latency = factory latency × #concurrent_threads | Acquire per-key lock *outside* global lock; use double-check pattern to avoid redundant factory calls |
| TTL check without expiry cleanup | Checked `if time.now() - timestamp < ttl` but never deleted expired entries | Cache grows without bound → memory leak; expired entries linger in the dict | Delete expired entries when accessed (`if expired: del cache[key]`); or add a background reaper if TTL matters for correctness |
| Zero-arg factory returning falsy value in tests | Test used `factory = lambda: set()` (empty set) | Cache hit returns `set(set())` (still empty) → indistinguishable from cache miss → test passes falsely even if cache logic is broken | Use a sentinel return value in tests: `lambda: {"SENTINEL"}` or `lambda: {1, 2, 3}` so cache hit vs miss are visually distinct |
| Mutable immutability assumption | Defensive copy only handled `set`/`dict`/`list` but not custom class instances | For custom classes, the "copy" was still a reference → caller mutations corrupted cache | Either: (1) make cached types immutable (`frozenset`, namedtuple), (2) implement `__copy__` for custom types, or (3) document that caller must not mutate |
| Recomputing repo slug per cache access | Factory did `repo_slug = get_git_config(repo_root)` | Expensive subprocess call (git, config reads) on cache miss; per-key fetch latency = slug computation latency | Memoize repo-info at a higher level; cache lookup becomes dict access under a lock, not subprocess |

## Results & Parameters

### Quick Reference — ThreadSafeCache API

```python
cache = ThreadSafeCache[str, set[str]](ttl_seconds=3600.0)

# Retrieve or compute
value = cache.get(key, factory_fn)  # returns defensive copy

# Invalidate one key (not global clear)
cache.remove(key)

# Atomically add to cached set (prevents TOCTOU)
cache.add_to_entry(key, item)
```

### Typical TTL Values

| Use Case | TTL | Rationale |
| --------- | ------- | --------- |
| GitHub API (labels, PR status) | 3600 s (1 h) | GitHub data rarely changes during a run; 1 h is safe for overnight jobs |
| Git config (e.g., user.name) | 86400 s (1 d) | Repo metadata is stable; long TTL reduces subprocess overhead |
| File system (repo structure) | 300 s (5 min) | Files may be modified during the run; shorter TTL catches changes |
| CI status (workflow checks) | 60 s (1 min) | Checks complete frequently; short TTL ensures freshness |

### Module-Level Cache Pattern

```python
# At module level, define once
_label_cache = ThreadSafeCache[str, set[str]](ttl_seconds=3600.0)

# Public API
def get_labels_for_repo(repo_slug: str) -> set[str]:
    return _label_cache.get(repo_slug, lambda: fetch_labels_from_github(repo_slug))

def refresh_repo_labels(repo_slug: str) -> None:
    """Refresh one repo's cached labels (does not affect other repos)."""
    _label_cache.remove(repo_slug)
```

### Fixture/Test Isolation

```python
@pytest.fixture
def clear_cache():
    """Clear cache before each test."""
    for key in list(_label_cache._cache.keys()):
        _label_cache.remove(key)
    yield
    for key in list(_label_cache._cache.keys()):
        _label_cache.remove(key)
```

## Files Changed

| File | Changes |
| --------- | --------- |
| `hephaestus/automation/pipeline_github.py` | Replaced bare `_label_cache: dict[str, set[str]]` with `ThreadSafeCache[str, set[str]]`; changed `clear()` to per-key `remove()` in refresh logic |
| `hephaestus/utils/cache.py` | New file; implemented `ThreadSafeCache[K, V]` generic class with per-key locks, TTL, and defensive copies |
| `tests/unit/automation/test_pipeline_github.py` | Rewrote cache tests with sentinel factories; added concurrent access tests with `threading.Barrier` |
| `tests/unit/utils/test_cache.py` | New file; unit tests for `ThreadSafeCache` (15 tests: serial access, concurrent same/different keys, TTL expiry, add_to_entry, copy isolation) |

## Verified On

| Project | Issue | Details | Verification |
| --------- | ------- | --------- | --------- |
| ProjectHephaestus | #1858 | Cross-repo unlocked module-level label cache corrupts durable journal writes under multithreaded coordinator; replaced with ThreadSafeCache keyed by repo slug; per-repo refresh only evicts intended key | verified-local (230+ tests pass; pre-commit clean; mypy clean) |
| ProjectHephaestus | #1857 | Sentinel factory in add_to_entry test prevents vacuous pass | verified-local (related fix in PR #1855) |

## See Also

- `concurrency-and-process-reliability-patterns.md` — thread/process-level reliability, subprocess, signal handling, multi-agent host exhaustion
- `architecture-metaclass-threadlocal-thread-safety.md` — metaclass + `threading.local()` for per-thread class-level state isolation
- `cache-invalidation-strategies.md` — (hypothetical) broader cache patterns (LRU, write-through, cache-aside)
