---
name: config-explicit-path-fail-closed
description: "Layered config resolvers (CLI > env > file > auto-discovery) must fail closed when an EXPLICITLY passed config path does not exist, instead of silently falling through to env/defaults — while keeping silent fall-through for auto-discovery (path=None). Includes the companion test migration: existing tests that pass a nonexistent path as an isolation trick to bypass file config break under fail-closed and must be migrated to disable discovery explicitly (patch the discovery helper, pass path=None). Use when: (1) an audit flags 'explicit nonexistent config path is silently ignored and defaults are used', (2) adding an existence check to a config loader with auto-discovery, (3) tests start failing with the new file-not-found error because they used fake paths for isolation, (4) deciding which exception type a config resolver should raise."
category: architecture
date: 2026-07-17
version: "1.0.0"
user-invocable: false
verification: unverified
tags:
  - config-resolution
  - fail-closed
  - silent-fallback
  - auto-discovery
  - pola
  - test-isolation
  - monkeypatch
  - layered-config
  - runtime-error
  - fleet-sync
---

# Explicit Config Path Must Fail Closed; Auto-Discovery May Fall Through

## Overview

| Field | Value |
|-------|-------|
| **Date** | 2026-07-17 |
| **Objective** | Fix the MAJOR audit finding "explicit nonexistent config path silently ignored, defaults used" in a layered config resolver without breaking the auto-discovery and env-only flows |
| **Outcome** | Plan for ProjectHephaestus issue #2170: existence check gated on `config_path is not None` before discovery runs; six tests migrated off the nonexistent-path isolation trick |
| **Verification** | unverified — pattern grounded in direct code inspection of `hephaestus/github/fleet_sync/config.py` and its test suite; implementation PR pending |

## When to Use

- An audit or review flags: "an explicit nonexistent config path is silently ignored and defaults are used — return a clear error instead"
- A config resolver layers CLI args > env vars > config file > auto-discovered default, and the file layer wraps its load in `if path.exists():`
- After adding fail-closed behavior, previously green tests raise the new file-not-found error because they passed `str(tmp_path / "nope.yml")` purely to bypass the file layer
- Deciding whether the resolver should raise `FileNotFoundError`, `ValueError`, or the module's established error type

## Verified Workflow

> **Status:** unverified. Derived from the reviewed implementation plan for ProjectHephaestus
> issue #2170, grounded in reading the live resolver and test suite; not yet executed as a
> merged PR with green CI. Amend to `verified-ci` once the #2170 PR merges.

### 1. Gate the check on explicitness, before discovery runs

The key distinction is *who chose the path*. An operator-supplied path that does not exist is
an operator error and must stop the program; a discovery probe that finds nothing is normal.
Put the existence check at the top of the loader, gated on `path is not None`, so the
auto-discovery branch (`path=None`) is untouched:

```python
def _load_fleet_config(config_path: str | None) -> tuple[str | None, list[str] | None]:
    if config_path is not None and not Path(config_path).exists():
        raise RuntimeError(
            f"fleet config file not found: {config_path}. "
            f"Pass an existing file to --config, or omit it to auto-discover "
            f"{DEFAULT_FLEET_CONFIG_FILENAME}"
        )
    if config_path is None:
        found = _find_default_config()  # already .exists()-checked internally
        ...
```

Then delete the now-redundant inner `if path_obj.exists():` guard around the actual load:
every path reaching it either passed the explicit check or was discovered as existing.

### 2. Match the module's established exception type, and check the CLI seam

Do not introduce a new exception type reflexively. In the fleet-sync case every failure in the
resolver already raises `RuntimeError` with an actionable message, and the CLI entry point
already catches `RuntimeError`, logs it, and exits 2 — so raising `RuntimeError` surfaces the
new error cleanly with zero CLI changes. Grep the callers before choosing the type.

### 3. Migrate tests that used nonexistent paths as an isolation trick

This is the non-obvious half. Tests for the env/CLI layers commonly pass
`config_path=str(tmp_path / "nope.yml")` *only* to keep the file layer out of the way. Under
fail-closed, every one of those now raises. Do not delete them and do not keep the fake paths:

- Migrate each to `config_path=None` **plus** patching the discovery helper to return `None`
  (e.g. `patch("pkg.config._find_default_config", return_value=None)`), ideally via one shared
  fixture. Plain `config_path=None` is NOT enough when the repo root contains a real default
  config file that discovery would find.
- Replace any test that asserts the old behavior by name (e.g.
  `test_missing_config_file_falls_through_to_env`) with two tests: explicit-missing-path
  raises even when env vars are set, and discovery-finds-nothing still falls through to env.

### 4. Keep the load-time error wrapper

Retain the existing `except FileNotFoundError` (or equivalent) around the actual file load: it
still covers the discovery TOCTOU race where a discovered file vanishes between the existence
probe and the read.

### Quick Reference

| Situation | Behavior |
|-----------|----------|
| Explicit path, file missing | Raise module's established error type with the path and a remediation hint |
| Explicit path, file exists but malformed | Existing wrapped load error (unchanged) |
| `path=None`, discovery finds a file | Load it (unchanged) |
| `path=None`, discovery finds nothing | Silent fall-through to env/CLI layers (unchanged) |
| Test needs file layer out of the way | `path=None` + patch discovery helper to `None` — never a fake path |

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
|---------|----------------|---------------|----------------|
| Rely on `path=None` alone for test isolation | Dropping the fake path without patching discovery | Repo root contains a real default config; auto-discovery finds it and the test asserts against the wrong org/repos | Isolation requires patching the discovery helper, not just omitting the path |
| Raise for every missing path including discovered ones | A single unconditional existence check after discovery | Would be dead code for discovery (helper pre-checks existence) and blurs the explicit-vs-discovered distinction the fix depends on | Gate the raise on `path is not None` *before* the discovery branch |
| Treat the old fall-through test as still valid | Keeping `test_missing_config_file_falls_through_to_env` as-is | It pins the exact defect the issue reports | A test asserting the buggy behavior by name must be replaced, not massaged |

## Results & Parameters

- **Origin:** ProjectHephaestus issue #2170 ("[majo] Fail closed for an explicit missing fleet-sync config file"), Section 14 MAJOR audit finding
- **Resolver:** `hephaestus/github/fleet_sync/config.py` — `_load_fleet_config()` / `resolve_fleet_config()`
- **Tests:** `tests/unit/github/test_fleet_sync_config.py` — six tests migrated off fake-path isolation; one behavior-pinning test replaced by a raises-test plus a discovery-empty fall-through test
- **Error type:** `RuntimeError`, matching the module's existing errors and the CLI's existing `except RuntimeError` → exit 2 seam
- **Generalizes to:** any loader with the shape `explicit_path_or_none` → `discover_default()` → layered merge; the same two-part fix (gated raise + test-isolation migration) applies
