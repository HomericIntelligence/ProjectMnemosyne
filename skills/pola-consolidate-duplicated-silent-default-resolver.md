---
name: pola-consolidate-duplicated-silent-default-resolver
description: "Plan a fix for a magic-number/silent-default bug that is duplicated across many call sites by consolidating every duplicate into ONE shared fail-loud resolver, raising instead of substituting an arbitrary value (POLA), and reusing an existing broad except boundary instead of adding a new one. Use when: (1) the same silent-default expression (e.g. `task_data.get(\"issue_number\", ISSUE_NUMBER or 7)`) is copy-pasted across multiple handlers and one fix would leave the rest vulnerable, (2) deciding raise-vs-sentinel for missing/invalid input and a hardcoded default would silently target an unrelated resource, (3) a broad `except Exception` boundary already catches+logs+continues so a raised ValueError need not crash the worker, (4) validating JSON-sourced fields where presence checks miss 0/\"\"/null/non-numeric, (5) testing a hyphenated-filename module that cannot be imported normally and whose config globals are read from env at import time."
category: architecture
date: 2026-06-20
version: "1.0.0"
user-invocable: false
verification: unverified
tags: [pola, fail-loud, magic-number, silent-default, shared-resolver, replace-all, exception-boundary, json-validation, importlib, planning]
---

# POLA: Consolidate Duplicated Silent Defaults into One Fail-Loud Resolver

## Overview

| Field | Value |
|-------|-------|
| **Date** | 2026-06-20 |
| **Objective** | Produce an implementation plan to fix a magic-number/silent-default bug — `task_data.get("issue_number", ISSUE_NUMBER or 7)` — duplicated across 5 stage handlers in a task-consumer worker. |
| **Outcome** | Plan written: replace all 5 duplicates with one shared `resolve_issue_number` that raises on missing/invalid input, lean on the existing consumer-loop `except Exception` boundary, validate type+range, and make the hyphenated-filename module test-importable. The plan was NOT executed. |
| **Verification** | unverified — planning session only; the fix was not applied, tests were not run, and CI was not confirmed. |

## When to Use

- The same silent-default expression is copy-pasted across multiple handlers/call sites, and fixing only the one cited line leaves the other duplicates vulnerable.
- A bug report cites a hardcoded fallback (a "magic number") that, on missing input, silently targets an unrelated resource (e.g. defaults `issue_number` to `7`).
- You must decide raise-vs-sentinel for missing/invalid input — and substituting an arbitrary default would violate the Principle of Least Astonishment.
- A broad `except Exception` boundary already exists in the consumer/worker loop, and you are tempted to add a *new* top-level handler instead of reusing it.
- The field comes from JSON (task payload, API response) where `is not None` is not enough — `0`, `""`, `null`, or a non-numeric string can slip through.
- You need to unit-test a module whose filename is hyphenated (not importable via `import`), and whose config is read from environment variables at import time.

## Proposed Workflow

> **Warning:** This workflow has not been validated end-to-end. The plan's tests were never executed and CI was never confirmed. Treat every step — and especially the cited line numbers and the assumed behavior of the existing exception boundary — as a hypothesis until CI confirms.

### Quick Reference

```bash
# 1. grep the LITERAL duplicated expression to confirm every call site is byte-identical
grep -rn 'task_data.get("issue_number", ISSUE_NUMBER or 7)' src/
#    Only then is replace_all safe. Count the hits; expect all 5 (425/473/532/585/678 — UNVERIFIED, drift).

# 2. Re-read the existing consumer-loop boundary BEFORE relying on it (assumed lines 810-814 — UNVERIFIED)
#    Confirm it logs loudly AND ack/continues on a raised ValueError so one bad task can't crash the worker.

# 3. Run the new test (pixi runner for e2e/ is UNVERIFIED — plan hedged with a fallback)
pixi run pytest e2e/test_resolve_issue_number.py -q || python3 -m pytest e2e/test_resolve_issue_number.py -q
```

```python
# The single shared fail-loud resolver — replaces ALL 5 duplicated silent defaults.
def resolve_issue_number(task_data: dict) -> int:
    """Return a valid issue number from task_data, or raise. Never substitutes a default."""
    raw = task_data.get("issue_number")
    if raw is None:
        raise ValueError("issue_number missing from task_data")
    try:
        n = int(raw)  # JSON may deliver "12", 0, or null — coerce, don't assume int
    except (TypeError, ValueError):
        raise ValueError(f"issue_number not an integer: {raw!r}")
    if n <= 0:
        raise ValueError(f"issue_number must be >= 1, got {n}")
    return n
```

### Detailed Steps

1. **Replace ALL duplicated silent defaults with ONE shared resolver.** Five handlers each carried `task_data.get("issue_number", ISSUE_NUMBER or 7)`. Centralizing into `resolve_issue_number(task_data)` removes drift risk and yields a single tested unit. **grep the literal expression string first** and confirm every call site is byte-identical before using `replace_all` — a near-but-not-identical site silently won't be replaced.

2. **Fail LOUD: raise on missing/invalid input.** Raise `ValueError` rather than returning a sentinel or fabricating a default. Gate on presence and validity; never substitute an arbitrary value. A hardcoded default (`7`) silently targets an unrelated resource — the textbook POLA violation.

3. **Reuse the EXISTING broad `except Exception` boundary in the consumer loop.** Do NOT add a new top-level handler. First re-read the existing boundary (assumed at lines 810-814 — the durable anchor is the consumer `for` loop, not the number) and verify it (a) logs loudly and (b) ack/continues so one malformed task doesn't crash the worker. Cite the exact line range you depend on, and re-confirm it ack/continues on a *raised* `ValueError` specifically.

4. **Validate type, not just presence.** JSON-sourced fields may arrive as a string, `0`, or `null`. A bare `is not None` check passes `0`, `""`, and non-numeric strings. Coerce via `int()` inside a `try`, and reject non-positive values (`n <= 0`).

5. **Make the test importable for a hyphenated-filename module.** The module can't be imported normally (hyphen in filename), so load it via `importlib.util.spec_from_file_location`. Because env vars are read at import time, mutate the module-level config global directly in tests (e.g. `mod.ISSUE_NUMBER = 0`) rather than setting env vars after import.

```python
import importlib.util
from pathlib import Path

def _load(path: str):
    spec = importlib.util.spec_from_file_location("consumer_mod", path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod

def test_resolve_raises_when_missing(tmp_path):
    mod = _load("e2e/task-consumer.py")
    mod.ISSUE_NUMBER = 0  # config read from env at import; mutate the global directly
    import pytest
    with pytest.raises(ValueError):
        mod.resolve_issue_number({})
```

## Verified Workflow

_Not applicable._ This skill was captured from a planning session and is `unverified`: the fix was never applied, no tests were run, and CI was never confirmed, so there is no verified workflow. The actionable, hypothesis-level methodology lives under **Proposed Workflow** above and must be treated as unvalidated until CI confirms it. (This placeholder section exists only because `scripts/validate_plugins.py` requires the literal `## Verified Workflow` heading; it intentionally makes no verification claim.)

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
|---------|----------------|---------------|----------------|
| Default to a hardcoded constant when input missing | Keep `task_data.get("issue_number", ISSUE_NUMBER or 7)` — return `7` on absence | Silently targets an unrelated resource (issue #7); the worker "succeeds" against the wrong issue with no error | Fail loud — raise `ValueError`; never substitute an arbitrary default (POLA) |
| Fix only the cited line (one of five) | Patch the single line named in the bug report | The other 4 byte-identical call sites remain vulnerable; drift returns immediately | grep the WHOLE expression literal, confirm all sites identical, then `replace_all` into one shared resolver |
| Add a brand-new top-level try/except boundary | Wrap the dispatch in a fresh `except Exception` | Unnecessary duplication of an existing boundary; two overlapping catches obscure where errors are handled | Verify the existing consumer-loop boundary already catches + logs + continues before adding one; reuse it |
| Check presence only (`is not None`) | Gate on `task_data.get("issue_number") is not None` | JSON `0`, `""`, `null`, and non-numeric strings slip through and become a bad/zero issue number | Coerce with `int()` and validate type AND range (`n >= 1`), not just presence |
| `import module` for a hyphenated filename | `import task-consumer` / `from task-consumer import ...` in the test | `ImportError` / `SyntaxError` — hyphens are not valid in module identifiers | Use `importlib.util.spec_from_file_location`; mutate the module-level config global in tests since env is read at import time |

## Results & Parameters

**Most uncertain assumptions a reviewer should focus on (all UNVERIFIED):**

- **Plan never executed.** Tests were not run and CI was not confirmed (verification = unverified). Everything below is a hypothesis.
- **Line numbers are assumed and drift.** The five call sites (425/473/532/585/678) and the main-loop boundary (810-814) are guesses. The durable anchor is the **literal expression string** + the **consumer `for` loop**, NOT the numbers — re-grep before editing.
- **Existing `except Exception` boundary behavior is assumed.** The plan assumes it logs loudly, acks the message, and continues — but does NOT re-confirm it ack/continues on a *raised* `ValueError`. A reviewer should re-read that boundary in full.
- **Test-runner wiring is assumed.** `pixi run pytest` may not be wired for `e2e/`; the plan hedged with a `python3 -m pytest` fallback. Runner wiring for the e2e tests dir is unverified.
- **`0` as the "unset" sentinel is assumed safe.** The plan assumes issue numbers are always `>= 1`, so `0` is a safe "unset" marker — consistent with the existing `ISSUE_NUMBER=0` comment, but not independently verified.

**Shared resolver contract (copy-paste ready):**

```python
def resolve_issue_number(task_data: dict) -> int:
    raw = task_data.get("issue_number")
    if raw is None:
        raise ValueError("issue_number missing from task_data")
    try:
        n = int(raw)
    except (TypeError, ValueError):
        raise ValueError(f"issue_number not an integer: {raw!r}")
    if n <= 0:
        raise ValueError(f"issue_number must be >= 1, got {n}")
    return n
```

**Generalization (the durable pattern):** When a silent-default bug is duplicated, the fix is structural, not local — collapse every duplicate into one tested fail-loud resolver, raise instead of substituting, validate type+range for externally-sourced (JSON) fields, and reuse the existing broad boundary rather than adding a new one. Anchor every edit on the literal expression and the loop structure, never on line numbers.

## Related Skills

- `optional-scoped-discovery-pola-gate` — POLA for optional CLI flags gating *discovery scope* by presence vs value. This skill is the duplicated-silent-default consolidation case (raise-vs-sentinel across many call sites).
- `silent-boundary-observability-exception-classification` — how to make a broad `except Exception` boundary observable without changing its fail-safe contract; relevant to step 3's reused boundary.
- `architecture-executable-convention-guard-pattern` — fail-loud, read-only, prefix-anchored verification; shares the "don't fabricate the signal, fail loud" philosophy.
