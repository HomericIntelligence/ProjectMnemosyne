---
name: mypy-narrow-cast-not-assert-ruff-s101
description: "In production code, narrow a sentinel-union to drop a `# type: ignore[assignment]` with `typing.cast`, NOT `assert` — `assert` trips ruff bandit S101 'Use of assert detected' (tests are per-file-exempt, production is not). Use when: (1) auditing `# type: ignore` comments to remove unjustified suppressions, (2) mypy needs you to narrow a `Path | None | _UnsetType` (or any sentinel union) after an `is _UNSET` check and the obvious `assert not isinstance(...)` fails `ruff check`, (3) deciding whether a suppression is justified (platform/backport) vs deletable, leveraging mypy `warn_unused_ignores`."
category: tooling
date: 2026-06-29
version: "1.0.0"
user-invocable: false
verification: verified-local
tags:
  - mypy
  - ruff
  - bandit
  - S101
  - type-ignore
  - typing-cast
  - assert
  - union-narrowing
  - warn_unused_ignores
  - suppression-audit
  - production-hardening
---

# Narrow With `cast`, Not `assert` (ruff S101 vs mypy in Production Code)

## Overview

| Field | Value |
| ------- | ------- |
| **Date** | 2026-06-29 |
| **Category** | tooling |
| **Objective** | Audit `# type: ignore` comments — remove unjustified suppressions, document justified ones — without trading one lint failure for another. The non-obvious trap: the obvious narrowing fix (`assert`) for an `[assignment]` ignore on a sentinel-union parameter fails ruff's bandit **S101** in production code. |
| **Outcome** | Use `typing.cast("Path \| None", x)` to narrow for mypy with no runtime check and no S101 hit; reserve `assert`-narrowing for test code where S101 is per-file-ignored. Audited 23 `# type: ignore` comments: removed unjustified ones, documented justified platform/backport suppressions with inline `# WHY justified:` comments. |
| **Verification** | verified-local — mypy 0 errors, `ruff check` all passed, `ruff format` clean, 404 unit tests passed locally. CI not observed at capture time. |
| **Toolchain** | mypy (`warn_unused_ignores = true`), ruff (bandit `S101`), pytest, pixi |

## When to Use

- You are **auditing `# type: ignore` comments** (e.g. a "fix unjustified, document justified" production-hardening pass) and need a principled, two-sided process.
- mypy demands you **narrow a sentinel-union** — a parameter typed `Path | None | _UnsetType` after an `if x is _UNSET:` branch handles the sentinel — and you reach for `assert not isinstance(x, _UnsetType)` to drop `# type: ignore[assignment]`.
- That `assert` then fails `ruff check` with **`S101` "Use of `assert` detected"** because it is in **production (non-test) code** (tests are exempt via per-file ignores; production code is not).
- You need to decide whether an existing suppression is **deletable** (stale / fixable) or **justified** (platform/backport gap) and want a self-verifying mechanism.

## Verified Workflow

> **Verification level:** verified-local — confirmed locally via `pixi run mypy` (0 errors), `pixi run ruff check` (all passed), `pixi run ruff format --check` (clean), and 404 unit tests passing. CI validation pending — a remote CI run was not observed at capture time.

### Core rule: narrow with `cast`, not `assert`, in production code

When mypy cannot narrow a sentinel-union and you want to remove a
`# type: ignore[assignment]`, the choice of narrowing mechanism depends on
**whether the file is production or test code**:

```python
# Setup: a param carries a sentinel so callers can distinguish
# "not passed" from "passed None".
class _UnsetType: ...
_UNSET = _UnsetType()

def configure(path: Path | None | _UnsetType = _UNSET) -> None:
    if path is _UNSET:
        path = _default_path()      # handle the sentinel branch
    # else-branch: mypy still sees `Path | None | _UnsetType`, not `Path | None`
```

```python
# ❌ WRONG in production code — narrows for mypy but ruff S101 fails `ruff check`:
assert not isinstance(path, _UnsetType)   # S101 Use of assert detected
_store(path)                              # type: ignore[assignment]  (now removable, but S101 blocks)
```

```python
# ✅ CORRECT in production code — narrows for mypy, no runtime check, no S101:
from typing import cast
_store(cast("Path | None", path))   # ignore removed; ruff clean; mypy clean
```

- `cast` narrows the static type **only**; it inserts **no runtime check**, so bandit's `S101` never fires.
- Add `from typing import cast` if the module does not already import it.
- Use `assert`-narrowing **only** in test code, where `S101` is exempted by a per-file ignore (e.g. `[tool.ruff.lint.per-file-ignores] "tests/**" = ["S101"]`).

### Two-sided audit with `warn_unused_ignores`

`warn_unused_ignores = true` makes the audit self-verifying:

- A **stale / over-broad** `# type: ignore` now reports `[unused-ignore]` → you know it is safe to delete.
- A **missed underlying fix** reports the original error code → you know the ignore was load-bearing and the real bug is still there.

Establish a baseline FIRST: confirm the committed tree is mypy-clean, and filter
untracked-file noise when grepping mypy output so you compare like-for-like.

### Distinguish real suppressions from data

`"type: ignore"` appearing as a **string literal** (e.g. a validator that scans
source for the marker) is **not** a suppression — exclude it from the audit. Grep
for the marker as a trailing comment, not as quoted data.

### Scope discipline

Ignores under **relaxed mypy overrides** (`module = ["tests.*", "scripts.*"]`
with `disallow_untyped_defs` off) are test/script-mock ergonomics, **not**
type-system gaps — out of scope for a production-hardening audit.

### Document justified suppressions instead of deleting

For genuinely justified platform/backport suppressions, add an inline
`# WHY justified:` comment (mirroring the `# pragma: no cover` convention) rather
than deleting the ignore. Justified examples observed this session:

| Suppression | Why justified |
|-------------|---------------|
| POSIX-only `import fcntl` | absent on Windows |
| Windows-absent `import curses` | platform-gated import |
| `backports.zoneinfo` `[no-redef]` | conditional backport fallback |
| `tomllib` / `tomli` fallback | stdlib-vs-backport shim |
| `logging.LoggerAdapter` `[type-arg]` | not generic at runtime on Python 3.10 |

### Concrete fixes that removed unjustified ignores

- Add a missing return annotation `-> Iterator[str]` to a
  `@contextlib.contextmanager` → removes `[no-untyped-def]`.
- Type a binary stream parameter as `typing.BinaryIO` so `.read()` resolves →
  removes `[attr-defined]`.

### Quick Reference

```python
# DECISION: how to narrow a sentinel-union to drop `# type: ignore[assignment]`?
#   Production (non-test) code  -> typing.cast (NO assert; assert => ruff S101 failure)
#   Test code (S101 per-file-ignored) -> assert is fine

from typing import cast
result = cast("Path | None", maybe_unset_value)   # mypy narrows, no runtime check, no S101
```

```bash
# Two-sided, self-verifying audit (warn_unused_ignores = true in mypy config):
pixi run mypy                 # [unused-ignore] => delete it; original code => ignore is load-bearing
pixi run ruff check           # catches S101 if you used assert in production code
pixi run ruff format --check  # keep formatting clean
```

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
|---------|----------------|---------------|----------------|
| 1 | Used `assert not isinstance(x, _UnsetType)` to narrow the sentinel-union and drop `# type: ignore[assignment]` in production code | ruff bandit **S101** "Use of `assert` detected" failed `ruff check` — production code is not exempt from S101 (only tests are, via per-file ignores) | Use `typing.cast` to narrow in production code; assert-narrowing is only safe in test code where S101 is per-file-ignored |
| 2 | Treated every `"type: ignore"` hit from grep as a suppression to audit | Some hits were **string literals** (a validator searching source for the marker), not real suppressions, inflating the audit surface with false positives | Distinguish trailing-comment suppressions from quoted data; exclude string-literal occurrences |
| 3 | Considered deleting justified platform suppressions (POSIX `fcntl`, Windows `curses`, `backports.zoneinfo`, `tomllib`/`tomli`, `LoggerAdapter [type-arg]`) to reach "zero ignores" | Deleting them reintroduces real cross-platform / backport type errors — the ignore is load-bearing, not stale | Document justified suppressions with an inline `# WHY justified:` comment (mirrors `# pragma: no cover`) instead of deleting |
| 4 | Planned to audit ignores under relaxed mypy overrides (`tests.*`, `scripts.*` with `disallow_untyped_defs` off) | Those are test/script-mock ergonomics permitted by the override, not production type-system gaps — out of scope and would churn benign code | Scope a production-hardening audit to production modules; skip ignores covered by relaxed overrides |

## Results & Parameters

### The exact narrowing fix

```text
# Before — mypy can't narrow the else-branch of a sentinel check, ignore present:
def _store(path: Path | None | _UnsetType): ...   # call site carries # type: ignore[assignment]
```

```python
# After — cast narrows for mypy, no runtime check, ruff S101 never fires:
from typing import cast
_store(cast("Path | None", path))   # ignore removed
```

### Mechanism comparison

| Mechanism | mypy narrows? | runtime check? | ruff S101 in production? | Use where |
|-----------|---------------|----------------|--------------------------|-----------|
| `assert not isinstance(x, _UnsetType)` | yes | yes | **fails** | test code only (S101 exempt) |
| `typing.cast("Path \| None", x)` | yes | no | passes | **production code** |

### Verification commands and outputs

| Command | Result |
|---------|--------|
| `pixi run mypy` | 0 errors (`warn_unused_ignores = true` baseline clean) |
| `pixi run ruff check` | All checks passed (no S101) |
| `pixi run ruff format --check` | Clean |
| `pixi run pytest tests/unit` | 404 passed |

### Verified On

- **Repo / issue:** ProjectHephaestus, issue #1423 ("audit 23 `# type: ignore` comments — fix unjustified, document justified").
- **Files touched (fixes):**
  - `hephaestus/version/manager.py` — `typing.cast` narrowing (the core S101-vs-mypy fix).
  - `hephaestus/forensics/coredump_handler.py` — typed a binary stream param as `typing.BinaryIO` (removes `[attr-defined]`).
  - `hephaestus/automation/github_api.py` — added `-> Iterator[str]` to a `@contextlib.contextmanager` (removes `[no-untyped-def]`).
- **Files touched (documented justified suppressions):**
  `hephaestus/automation/advise_runner.py`, `hephaestus/automation/curses_ui.py`,
  `hephaestus/github/rate_limit.py`, `scripts_lib/check_cli_table_sync.py`,
  `hephaestus/logging/utils.py` — each annotated with an inline `# WHY justified:` comment.

### Generalizable lesson

- When mypy forces a narrowing in **production** code, default to `typing.cast`;
  reach for `assert` only inside test code where ruff `S101` is per-file-ignored.
- Set `warn_unused_ignores = true` to turn a `# type: ignore` audit into a
  two-sided, self-verifying pass: stale ignores surface as `[unused-ignore]`,
  load-bearing ones keep masking a real error.
- Document a justified platform/backport suppression in place with
  `# WHY justified:` rather than deleting it and reintroducing a real error.
