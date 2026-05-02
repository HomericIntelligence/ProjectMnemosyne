---
name: cross-repo-python-utility-port
description: "Use when porting a Python utility (class, module, tests) from one repo to another
  that already has a related implementation. Covers: (1) diff analysis between source and
  destination implementations, (2) identifying which features to cherry-pick vs skip, (3)
  merging test suites without duplication, (4) finding and fixing bugs exposed during porting,
  (5) creating a re-export shim in the source repo and filing a cleanup issue."
category: tooling
date: 2026-04-12
version: "1.0.0"
user-invocable: false
verification: verified-local
tags: [porting, cross-repo, python, circuit-breaker, re-export, test-merge, shim]
---

# Cross-Repo Python Utility Port

## Overview

| Field | Value |
| ------- | ------- |
| **Date** | 2026-04-12 |
| **Objective** | Port `CircuitBreaker` from an orphaned Scylla worktree to ProjectHephaestus, which already had its own implementation |
| **Outcome** | `success_threshold` feature added to Hephaestus; 10 new tests merged; bug found and fixed during porting; re-export shim issue filed in Scylla |
| **Verification** | verified-local — 29/29 tests passing; PR pushed; CI pending |

## When to Use

- A file found in a worktree (orphaned, abandoned, or uncommitted) implements something similar to what exists in a shared utilities repo
- Two repos have diverged implementations of the same pattern (circuit breaker, retry, rate limiter)
- The destination repo already has the utility but is missing features the source has
- The source file is to be replaced with a re-export shim pointing to the destination

## Verified Workflow

### Quick Reference

```bash
# 1. Read both implementations side by side
Read <source_file>
Read <destination_file>

# 2. Diff feature sets
# Source has: X, Y, Z
# Destination has: X, W, V
# → Port: Y, Z (missing from destination); skip repo-specific things

# 3. Create branch in destination repo
cd ~/DestinationRepo
git checkout -b port-<feature-name>

# 4. Edit destination implementation + tests
# 5. Run tests
pixi run python -m pytest tests/unit/<module>/ -v --no-cov

# 6. Commit, push, file cleanup issue in source repo
gh issue create --repo <source-repo> --title "cleanup: replace <file> with re-export from <dest>"
```

### Phase 1 — Side-by-Side Feature Analysis

Read both files completely. Build a feature matrix:

| Feature | Source | Destination | Action |
| --------- | -------- | ------------- | -------- |
| Core state machine | ✓ | ✓ | Skip (exists) |
| `success_threshold` | ✓ | ✗ | **Port** |
| `half_open_max_calls` | ✗ | ✓ | Skip (dest is better) |
| Global registry | ✗ | ✓ | Skip |
| `CircuitBreakerOpenError.time_until_recovery` | ✗ | ✓ | Skip |
| Logging | ✗ | ✓ | Skip |

**Rule**: Port features the source has that the destination lacks. Never downgrade the destination to match a weaker source.

Also check the test files — source tests often cover edge cases that destination tests miss.

### Phase 2 — Implement in Destination

Add parameters as backward-compatible additions (new params with defaults matching old behavior):

```python
def __init__(
    self,
    name: str,
    failure_threshold: int = 5,
    recovery_timeout: float = 60.0,
    half_open_max_calls: int = 1,
    success_threshold: int = 1,   # NEW — default 1 = old behavior
) -> None:
```

Track new state in `__init__`:
```python
self._half_open_successes = 0
```

In `_record_success`: count toward threshold before closing:
```python
if self._state == CircuitBreakerState.HALF_OPEN:
    self._half_open_successes += 1
    if self._half_open_successes < self.success_threshold:
        self._half_open_calls = 0   # reset probe counter so next probe gets through
        return
```

Clear the new counter in every state-reset path (`_effective_state` transition, `reset()`, `_record_failure` in HALF_OPEN).

### Phase 3 — Merge Test Suites

Don't duplicate tests that already exist in the destination. Add only:
- Tests for the new feature (`success_threshold`)
- Time-mocking tests if destination is missing them (more deterministic than `time.sleep`)
- Parametrized threshold configs (good for regression coverage)

```python
# Add to existing test file — do not create a parallel file
class TestCircuitBreakerSuccessThreshold:
    def test_success_threshold_two_requires_two_successes(self) -> None: ...

class TestCircuitBreakerTimeMocking:
    @patch("dest.module.circuit_breaker.time.monotonic")
    def test_open_to_half_open_exactly_at_timeout(self, mock_monotonic): ...

@pytest.mark.parametrize(...)
def test_parametrized_thresholds_full_cycle(...): ...
```

### Phase 4 — Run Tests and Fix Bugs

```bash
pixi run python -m pytest tests/unit/<module>/test_circuit_breaker.py -v --no-cov
```

**Watch for bugs exposed by new tests** — porting often reveals gaps in the original logic.

In this session: `success_threshold=2` with `half_open_max_calls=1` failed because after the first successful probe, the call counter was exhausted so the second probe was rejected. Fix: reset `_half_open_calls = 0` between probes while success count hasn't reached threshold yet.

### Phase 5 — Commit and Push

```bash
cd ~/DestinationRepo
git add <impl-file> <test-file>
# Allow pre-commit to reformat, re-stage if needed
git commit -m "feat(<module>): add <feature> to <Class> for configurable <behavior>

Ports <feature> from <SourceRepo>. <Description of what changed and why>.

Co-Authored-By: Claude Sonnet 4.6 <noreply@anthropic.com>"
git push -u origin <branch>
```

### Phase 6 — File Cleanup Issue in Source Repo

The source file should become a re-export shim (same pattern as other backward-compat shims):

```python
"""<Module> — re-exports from <dest-package>.<module>."""
from dest_package.module import (
    MainClass,
    ErrorClass,
    StateEnum,
    factory_func,
    reset_func,
)
__all__ = ["MainClass", "ErrorClass", "StateEnum", "factory_func", "reset_func"]
```

File the issue in the source repo:

```bash
gh issue create \
  --repo <source-org>/<source-repo> \
  --title "cleanup: replace <path> with re-export from <dest-package>" \
  --body "## Objective
...
## Dependencies
- <dest-repo> branch <name> must merge first (provides the new feature)
..."
```

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
| --------- | ---------------- | --------------- | ---------------- |
| Port the entire source implementation over destination | Replace destination `circuit_breaker.py` wholesale | Destination had more features (`time_until_recovery`, registry, logging, `half_open_max_calls`) | Never replace destination with source — do a feature diff first; only port what's missing |
| `success_threshold=2` test with `half_open_max_calls=1` | First success probe left `_half_open_calls` exhausted, blocking second probe | `CircuitBreakerOpenError` raised on second call instead of passing through | When `success_threshold > 1`, reset `_half_open_calls = 0` after each non-final success so subsequent probes can pass |
| Run tests with coverage | `pixi run python -m pytest ... -v` (no `--no-cov`) | Coverage measured whole project → 3.88% (far below 80% floor) → exit 1 | Use `--no-cov` for targeted test runs; full coverage run only at CI step |
| Commit without allowing pre-commit to run | First commit attempt failed with `ruff-format-python` hook | Ruff reformatted the test file | Re-stage the reformatted file and re-commit; this is a normal 2-commit pattern |

## Results & Parameters

### Feature diff template

```markdown
| Feature | Source | Dest | Action |
|---------|--------|------|--------|
| success_threshold | ✓ | ✗ | Port |
| half_open_max_calls | ✗ | ✓ | Skip |
| Global registry | ✗ | ✓ | Skip |
| Logging | ✗ | ✓ | Skip |
```

### The `success_threshold` fix (critical pattern)

When `success_threshold > 1`, `_record_success` must reset the call counter between probes or the circuit self-blocks:

```python
if self._half_open_successes < self.success_threshold:
    self._half_open_calls = 0   # ← this line is the fix
    return
```

Without it: `half_open_max_calls=1`, probe 1 succeeds (counter=1), counter exhausted → probe 2 raises `CircuitBreakerOpenError` before reaching `_record_success`.

### Re-export shim pattern

```python
"""<description> — re-exports from <package>.<module>."""
from package.module import ClassA, ClassB, EnumC, func_d, func_e

__all__ = ["ClassA", "ClassB", "EnumC", "func_d", "func_e"]
```

### Test count reference (this session)

| Before port | After port | New tests |
| ------------- | ------------ | ----------- |
| 19 tests | 29 tests | +10 (4 success_threshold, 2 time-mock, 4 parametrized) |

## Verified On

| Project | Context | Details |
| --------- | --------- | --------- |
| ProjectHephaestus | `CircuitBreaker.success_threshold` ported from Scylla orphaned worktree | Branch `port-circuit-breaker-success-threshold`; 29/29 local; CI pending |
| ProjectScylla | Cleanup issue filed | HomericIntelligence/ProjectScylla#1805 |
