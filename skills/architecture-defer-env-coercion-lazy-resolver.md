---
name: architecture-defer-env-coercion-lazy-resolver
description: "Defer env/config coercion+validation OUT of module import into a single lazy validating resolver, so a malformed env value surfaces through a handled (acked) boundary instead of crashing the process at import. The module global stays a RAW string (default \"\"), and ALL coercion/validation routes through one lazy function already inside a try/except boundary. Use when: (1) a module top-level does int()/float()/json.loads() of an env var (e.g. `int(os.environ.get(\"ISSUE_NUMBER\", \"0\"))`), (2) a worker/daemon/CLI crashes at import on a bad config value before main() or any consumer loop can ack it, (3) converting an eager parse into a lazy resolver call, (4) a config global is flipping from int to string and you must re-check truthiness sentinels (`0 or None` vs `\"0\" or None`)."
category: architecture
date: 2026-06-20
version: "1.0.0"
user-invocable: false
verification: unverified
tags: [python, env-vars, config-parsing, import-time, lazy-evaluation, fail-safe, architecture]
---

# Defer Env/Config Coercion Out of Module Import to a Single Lazy Validating Resolver

## Overview

| Field | Value |
|-------|-------|
| **Date** | 2026-06-20 |
| **Objective** | Plan a fix for a worker that crashes at IMPORT time when an env var is malformed — `int(os.environ.get("ISSUE_NUMBER", "0"))` evaluated at module top-level dies on `ISSUE_NUMBER=foo` / `ISSUE_NUMBER=12.5` before any try/except or consumer-loop ack can handle it. |
| **Outcome** | Plan written: keep the module global as the RAW string (default `""`), defer ALL coercion+validation to the single existing `resolve_issue_number()` resolver (which already lives inside a handled, acked boundary), so the bad value surfaces as a recoverable `ValueError` instead of a fatal import. The plan was NOT executed. |
| **Verification** | unverified — planning session only; no code executed, no tests run, CI not confirmed. |

## When to Use

- A module's TOP LEVEL does eager coercion of an env var or config value — `int(...)`, `float(...)`, `json.loads(...)` — e.g. `ISSUE_NUMBER = int(os.environ.get("ISSUE_NUMBER", "0"))`.
- A worker / daemon / CLI crashes at IMPORT on a bad config value, before `main()` or any consumer loop runs, so no in-process try/except can catch it and no per-task ack can recover.
- You are converting an eager top-level parse into a lazy resolver call and need the pattern done safely.
- A config global is flipping from an `int` to a `str` and you must re-audit every truthiness sentinel (`0` vs `"0"`, `0 or None` vs `"0" or None`).
- Any externally-sourced value (env, JSON, CLI) is parsed where you'd rather a bad input be observable and acked than fatal-at-import.

## Proposed Workflow

> **Warning:** This workflow has not been validated end-to-end. Treat as a hypothesis until CI confirms.

### Quick Reference

```bash
# 1. Find eager module-level coercion of env/config (the import-time landmine)
grep -rnE '^\s*[A-Z_]+\s*=\s*(int|float|json\.loads)\(\s*os\.environ' src/ e2e/

# 2. Confirm the single resolver already lives inside a handled (acked) boundary
#    Re-read the consumer loop / except boundary; verify a raised ValueError is logged + acked + continued.
grep -rn 'def resolve_issue_number' src/ e2e/

# 3. Reproduce the import-time crash (proves it's NOT catchable by main()'s try/except)
ISSUE_NUMBER=foo  python3 -c 'import importlib.util,sys; ...'   # crashes at exec_module, before main
ISSUE_NUMBER=12.5 python3 -c '...'                              # same: float string -> int() raises
```

```python
# BEFORE — eager coercion at module top-level: a bad env value is FATAL at import.
#          No try/except below this line can catch it; the process dies before main().
ISSUE_NUMBER = int(os.environ.get("ISSUE_NUMBER", "0"))   # ISSUE_NUMBER=foo -> ValueError at import

# AFTER — keep the global a RAW string (default "" so the falsy-skip still works),
#         and route ALL coercion+validation through the one lazy resolver.
ISSUE_NUMBER = os.environ.get("ISSUE_NUMBER", "")          # never raises at import

def resolve_issue_number(task_data: dict) -> int:
    """The single lazy boundary where the env value is coerced + validated.
    Called from inside the consumer loop's existing try/except, so a bad value
    is raised as ValueError, logged, and acked — never fatal-at-import."""
    raw = task_data.get("issue_number") or ISSUE_NUMBER or None
    if raw is None or raw == "":
        raise ValueError("issue_number missing from task_data and env")
    try:
        n = int(raw)                       # bad env value surfaces HERE, inside a handled boundary
    except (TypeError, ValueError):
        raise ValueError(f"issue_number not an integer: {raw!r}")
    if n <= 0:
        raise ValueError(f"issue_number must be >= 1, got {n}")
    return n
```

### Detailed Steps

1. **Find every eager top-level coercion.** grep for module-level `int()/float()/json.loads()` wrapping `os.environ`/config reads. Each one is an import-time landmine: a malformed value kills the process during `import`/`exec_module`, before `main()` or any consumer loop exists to catch or ack it.

2. **Keep the global a RAW string; do NOT coerce at module level.** Replace `int(os.environ.get("ISSUE_NUMBER", "0"))` with `os.environ.get("ISSUE_NUMBER", "")`. Importing the module must never raise on a bad env value.

3. **Default the string to `""`, not `"0"`.** This is the most error-prone part. When the global was an int, `0 or None` evaluated to `None` (the "skip / unset" path). After the type flips to string, `"0" or None` evaluates to `"0"` — a TRUTHY non-empty string that is NOT skipped, silently changing behavior. Default to `""` so the existing `... or None` falsy-skip keeps working exactly as before.

4. **Route ALL coercion+validation through the ONE existing lazy resolver.** `resolve_issue_number()` already lives inside the consumer loop's handled `except` boundary. Move coercion (`int(raw)`), the empty/None check, and range validation there. The bad value now surfaces as a `ValueError` that is logged and acked — recoverable, not fatal.

5. **Do NOT add a second try/except-default at the import line.** Wrapping the import-time parse in `try: int(...) except: 0` keeps the validation at import, duplicates the resolver's checks, and silently swallows/masks the bad value (worker runs against a wrong/zero issue). The fix is deferral, not a second guard.

6. **Re-confirm the boundary acks a raised `ValueError`.** Re-read the consumer loop's `except Exception` and verify it logs loudly AND ack/continues specifically on a raised `ValueError`, so one malformed task can't crash the worker.

## Verified Workflow

_Not applicable._ This skill was captured from a planning session and is `unverified`: no code was applied, no tests were run, and CI was not confirmed, so there is no verified workflow. The actionable, hypothesis-level methodology lives under **Proposed Workflow** above and must be treated as unvalidated until CI confirms it. (This placeholder section exists only because `scripts/validate_plugins.py` requires the literal `## Verified Workflow` heading; it makes no verification claim.)

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
|---------|----------------|---------------|----------------|
| try/except-default-to-0 at the import line | Wrap the top-level parse: `try: ISSUE_NUMBER = int(os.environ.get("ISSUE_NUMBER","0")) except (TypeError,ValueError): ISSUE_NUMBER = 0` | Duplicates the resolver's validation and SILENTLY masks the bad value — the worker proceeds against issue `0`/wrong target with no error; coercion still happens at import where it can't be acked per-task | Defer coercion to the single lazy resolver; do not add a second import-time try/except-default that swallows the bad input |
| Leave the default as `"0"` after switching the global to a string | Change only the type (`int` -> `str`) but keep `os.environ.get("ISSUE_NUMBER", "0")` | Subtle behavior shift: when the global was int, `0 or None` -> `None` (skipped); now `"0" or None` -> `"0"` (truthy, NOT skipped), so the unset/skip path silently stops working | Default the string sentinel to `""` so the `... or None` falsy-skip keeps its original meaning — scrutinize every truthiness check when a global changes type |
| Catch the exception at the import site with a module-level guard | Add a module-level `try/except` around the parse to "make import safe" | The coercion still RUNS at import time, so it cannot be acked per-task; a module-level guard has no task context to log/ack/continue against, and one global decision can't represent per-message recovery | Move coercion INTO the lazy resolver that already runs inside the per-task handled boundary — import must stay coercion-free |

## Results & Parameters

**Most uncertain assumptions a reviewer should focus on (all UNVERIFIED):**

- **Plan never executed.** No code applied, no tests run, CI not confirmed (verification = unverified). Everything here is a hypothesis.
- **Truthiness sentinel is the riskiest change.** Defaulting the string to `""` (not `"0"`) is what keeps the `... or None` falsy-skip working after the int -> str flip. A reviewer should verify every read of the global treats `""` as "unset".
- **Resolver boundary behavior is assumed.** The plan assumes `resolve_issue_number()` runs inside the consumer loop's `except Exception`, which logs + acks + continues on a *raised* `ValueError`. Re-read that boundary in full before relying on it.
- **Anchor on the literal expression, not line numbers.** Re-grep the eager-coercion expression before editing; line numbers drift.

**Verified On / Integration point:** Captured from a planning session for **Odysseus issue #325** (the import-time crash on a malformed `ISSUE_NUMBER`). The integration point is the resolver introduced for **Odysseus issue #187** (`resolve_issue_number()`); this plan moves env coercion into that already-acked resolver rather than adding a new boundary. Plan-stage only — **unverified**.

**Generalization (the durable pattern):** Any worker/daemon/CLI that parses env or config at import should DEFER coercion+validation to a single lazy resolver inside a handled boundary. Eager top-level `int()/float()/json.loads()` converts a recoverable bad-input error into an uncatchable import-time crash. Keep the module global a raw string (default `""`), validate lazily once, and watch the truthiness sentinel when a global changes type.

## Related Skills

- `pola-consolidate-duplicated-silent-default-resolver` — same Odysseus worker and `resolve_issue_number()` resolver; covers consolidating duplicated silent-defaults across call sites and raise-vs-sentinel (POLA). This skill is the complementary import-time-safety case: deferring eager coercion out of import into that resolver.
- `pola-consolidate-duplicated-silent-default-resolver` is the place to look for the call-site/duplication angle; this skill owns the "don't coerce at module import" angle.
- `pydantic-none-coercion-pattern` — related coercion/None-handling for externally-sourced fields.
