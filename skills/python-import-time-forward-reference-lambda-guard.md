---
name: python-import-time-forward-reference-lambda-guard
description: "Diagnose and correctly fix the trap where a module-level call captures a name defined LATER in the same file via a lambda (deferring the lookup to call time), and a lint autofix that inlines the lambda into a direct reference turns it into an import-time NameError. Use when: (1) EVERY test job across ALL Python versions fails identically during collection with the SAME NameError right after a lint/Copilot-Autofix bot commit — the tell-tale signature of an import-time break (uniform red), not a logic bug (which fails a specific subset); (2) a module-level construction passes a callback as a keyword arg via `ignore=lambda exc: _predicate(exc)` where `_predicate` is defined below the construction — the lambda is LOAD-BEARING because `ignore=` is evaluated at import but the lambda body is not evaluated until call time; (3) an 'Unnecessary lambda' lint finding is autofixed to a direct reference (`ignore=_predicate`) and import breaks with `NameError: name '_predicate' is not defined`; (4) you need the CORRECT fix (not restoring the lambda): MOVE the predicate and any tables it consults ABOVE the construction, use the direct reference, add a comment that `ignore=` is import-time so a forward reference raises NameError; (5) you need a regression guard for an import-time break — NO in-process test can catch it because importing the test module already imported the module under test, so you need a SUBPROCESS import test (`subprocess.run([sys.executable, '-c', 'import the.module'])`, assert returncode==0), a SOURCE-ORDER assertion (read the file, assert `source.index('def _predicate') < source.index('_X = construct(')`), and an assertion that the constructed object actually carries the wiring (`_GH_BREAKER._ignore is not None`), not a stale None; (6) you need the process lesson: a lint-autofix bot's FINDING can be correct while its PATCH is WRONG — the removed construct may be load-bearing for a reason the linter cannot see (deferred evaluation, side effects, definition ordering); verify a bot autofix by actually importing/running, not by trusting 'it's just a lint fix'."
category: debugging
date: 2026-07-10
version: "1.0.0"
user-invocable: false
verification: verified-ci
tags:
  - import-time-error
  - forward-reference
  - lambda
  - deferred-evaluation
  - nameerror
  - lint-autofix
  - copilot-autofix
  - unnecessary-lambda
  - definition-order
  - circuit-breaker
  - subprocess-import-test
  - source-order-guard
  - ci-signature
  - uniform-failure
  - collection-error
  - regression-guard
  - load-bearing-construct
  - bot-patch-verification
---

# Python Import-Time Forward-Reference Lambda Guard

## Overview

| Field | Value |
|-------|-------|
| **Date** | 2026-07-10 |
| **Objective** | Diagnose "every test job failed with the same NameError after a lint-autofix bot commit", understand why a load-bearing lambda deferred an import-time forward-reference lookup, apply the correct fix (reorder the definition, do not restore the lambda), and add a regression guard that can actually catch an import-time break |
| **Outcome** | Successful — break and fix both reproduced with a runnable subprocess import; fix merged in ProjectHephaestus PR #2049 with all CI green |
| **Verification** | verified-ci |

## When to Use

- **Uniform CI red after a bot autofix**: EVERY test job on EVERY Python version fails identically during collection with the SAME `NameError`, and the failing commit is a lint / GitHub Copilot Autofix bot commit. Uniform-across-the-matrix failure is the tell-tale signature of an **import-time** error (the module can't even be imported), not a logic bug (which fails a specific subset of tests).
- **A module-level construction takes a callback keyword arg referencing a name defined LATER in the file**: e.g. `_GH_BREAKER = get_circuit_breaker(..., ignore=lambda exc: _breaker_should_ignore(exc))` where `_breaker_should_ignore` is defined ~130 lines *below*. The lambda is **load-bearing** — `ignore=` is evaluated at import (it's a keyword arg to a call that runs at import), but the lambda *body* isn't evaluated until the breaker actually invokes `ignore` at call time, so the forward reference resolves later and import succeeds.
- **An "Unnecessary lambda" lint finding is autofixed into a direct reference**: the bot rewrites `ignore=lambda exc: _breaker_should_ignore(exc)` → `ignore=_breaker_should_ignore`. Now the name resolves at import — and it doesn't exist yet: `NameError: name '_breaker_should_ignore' is not defined`. Because the module is imported by nearly everything, every test job fails.
- **You need the CORRECT fix, not a revert**: satisfy BOTH the lint finding AND import by MOVING the predicate (and any tables it consults) above the construction, then using the direct reference. Do not restore the lambda — it was masking a definition-order problem.
- **You need a regression guard for an import-time break**: no in-process test can catch it (importing the test file already imported the module under test). You need a subprocess-import test, a source-order assertion, and a wiring-not-None assertion.
- **A bot autofix looks trivial ("it's just a lint fix")**: a lint-autofix bot's *finding* can be correct while its *patch* is wrong. The removed construct may be load-bearing for a reason the linter can't see (deferred evaluation, side effects, definition ordering). Verify by importing/running, not by trusting the diff.

## Verified Workflow

### Quick Reference

```python
# THE TRAP — the lambda is LOAD-BEARING (defers a forward-reference lookup to call time)
# module top:
_GH_BREAKER = get_circuit_breaker(
    "github-api", ...,
    ignore=lambda exc: _breaker_should_ignore(exc),  # import OK: body not evaluated until call
)
# ~130 lines BELOW:
def _breaker_should_ignore(exc: Exception) -> bool: ...

# THE BOT AUTOFIX ("Unnecessary lambda") — breaks import:
_GH_BREAKER = get_circuit_breaker("github-api", ..., ignore=_breaker_should_ignore)
#   ignore= is evaluated at IMPORT → NameError: name '_breaker_should_ignore' is not defined

# THE CORRECT FIX — reorder, keep the direct reference (satisfies BOTH lint AND import):
def _breaker_should_ignore(exc: Exception) -> bool: ...   # MOVED ABOVE the construction
# ... plus any tables _breaker_should_ignore consults, also moved above ...
_GH_BREAKER = get_circuit_breaker(
    "github-api", ...,
    # The predicate is defined above on purpose: `ignore=` is evaluated at import,
    # so a forward reference here raises NameError.
    ignore=_breaker_should_ignore,
)
```

```bash
# CI SIGNATURE — all jobs red uniformly ⇒ suspect import-time before logic
# pytest reports a COLLECTION error, not a test failure:
pixi run python -m pytest hephaestus/ -q
#   → "Interrupted: N errors during collection"
#   → the SAME NameError on EVERY Python version = import-time, not logic
```

```python
# REGRESSION GUARD — the ONLY in-suite way to catch an import-time break: a SUBPROCESS import.
# (An in-process `import hephaestus.github.client` here would already have run at collection,
#  so it cannot fail the test the way CI fails.)
import subprocess, sys

def test_client_module_imports_in_a_fresh_interpreter() -> None:
    proc = subprocess.run(
        [sys.executable, "-c", "import hephaestus.github.client"],
        capture_output=True, text=True,
    )
    assert proc.returncode == 0, proc.stderr   # fails on the offending commit with the NameError
```

```python
# SOURCE-ORDER GUARD — fast, readable assertion on the ordering invariant.
from pathlib import Path
import hephaestus.github.client as client

def test_predicate_is_defined_before_the_breaker_construction() -> None:
    source = Path(client.__file__).read_text()
    assert source.index("def _breaker_should_ignore") < source.index("_GH_BREAKER = "), (
        "_breaker_should_ignore must be defined ABOVE the _GH_BREAKER construction; "
        "`ignore=` is evaluated at import, so a forward reference raises NameError."
    )

# WIRING GUARD — the constructed object must actually carry the callback, not a stale None.
def test_breaker_ignore_predicate_is_wired() -> None:
    assert client._GH_BREAKER._ignore is not None
```

### Detailed Steps

1. **Read the CI signature first.** When ALL test jobs across ALL Python versions fail identically during collection, suspect an **import-time error before a logic bug**. `pytest ... -q` shows `Interrupted: N errors during collection` and the same traceback everywhere. A logic bug fails a *specific subset* of tests; an import break fails *everything that imports the module* — uniformly.
2. **Find the offending commit.** If the uniform red starts at a lint / Copilot-Autofix bot commit, read that commit's diff. Do not assume "it's just a lint fix" — inspect what construct was removed.
3. **Identify the load-bearing deferral.** The autofix inlined a lambda: `ignore=lambda exc: _predicate(exc)` → `ignore=_predicate`. Confirm the referenced name is defined *below* the construction (`grep -n "def _predicate" file; grep -n "_X = construct(" file` and compare line numbers). The lambda was deferring the name lookup from import time to call time — that is why import used to succeed.
4. **Do NOT restore the lambda.** The lint finding was *correct* (the lambda was unnecessary as a wrapper); the lambda was merely masking a definition-order problem. Reverting re-introduces the lint finding and leaves the real defect (bad ordering) in place.
5. **Apply the correct fix: reorder.** Move the predicate function — and any module-level tables/constants it consults — ABOVE the construction. Then use the direct reference `ignore=_predicate`. This satisfies both the lint finding and import.
6. **Leave a comment at the construction site** explaining the invariant: e.g. `# The predicate is defined above on purpose: ignore= is evaluated at import, so a forward reference raises NameError.` This stops a future reader (or bot) from "tidying" the ordering back.
7. **Add three regression guards** (see Quick Reference): (a) a subprocess-import test that runs `import the.module` in a fresh interpreter and asserts `returncode == 0` — the ONLY in-suite way to catch an import-time break; (b) a source-order assertion that reads the module file and asserts the predicate is defined before the construction; (c) an assertion that the constructed object actually carries the wiring (`_GH_BREAKER._ignore is not None`), not a stale `None`.
8. **Mutation-test the guards against the offending commit.** All three should FAIL on the pre-fix commit and PASS on the fix. If a guard passes on the broken commit, it is vacuous — the classic in-process-import mistake fails silently this way.

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
|---------|----------------|---------------|----------------|
| Trust the bot's autofix | Accepted the "Unnecessary lambda" Copilot Autofix (`ignore=lambda exc: _breaker_should_ignore(exc)` → `ignore=_breaker_should_ignore`) as a harmless lint fix | `ignore=` is evaluated at IMPORT; the inlined name was defined ~130 lines below → `NameError: name '_breaker_should_ignore' is not defined`; the module is imported by nearly everything, so every test job on every Python version failed | A lint-autofix bot's FINDING can be correct while its PATCH is WRONG — the removed construct may be load-bearing (deferred evaluation) for a reason the linter can't see. Verify a bot autofix by actually importing/running, not by trusting "it's just a lint fix". |
| Assume a logic bug | Started debugging the circuit-breaker predicate logic when CI went red | The failure was import-time (collection error), not logic; the predicate never even ran. Chasing logic wastes time | When ALL test jobs across ALL Python versions fail identically, suspect an import-time error first. `pytest -q` shows "Interrupted: N errors during collection". Uniform red = import break; subset red = logic bug. |
| Restore the lambda | Reverted the autofix to bring back `ignore=lambda exc: _breaker_should_ignore(exc)` | Import works again, but the "Unnecessary lambda" lint finding returns AND the underlying definition-order defect remains (the lambda was only masking it) | Don't restore the deferral — MOVE the predicate (and any tables it consults) ABOVE the construction and use the direct reference. That satisfies BOTH the lint finding and import. |
| In-process import regression test | Added `import hephaestus.github.client` inside a test function to "guard" against the break | Importing the test module already imported the module under test during collection, so the guard is vacuous — it cannot reproduce the fresh-interpreter NameError and passes even on the broken commit | NO in-process test can catch an import-time break in the module under test. Use a SUBPROCESS import (`subprocess.run([sys.executable, "-c", "import the.module"])`, assert returncode==0). Mutation-test it against the offending commit to prove it actually fails there. |
| `git commit --amend` on the bot's pushed commit | Considered amending the Copilot Autofix commit to fix it in place | Amending a pushed commit that isn't yours rewrites shared history; the squash-merge collapses everything anyway | Prefer a follow-up commit over `--amend` on someone else's pushed commit; the squash-merge makes the extra commit invisible in history. |

## Results & Parameters

### The trap, the break, and the fix (verified in `hephaestus/github/client.py`)

```python
# ---- BEFORE (works at import; lambda defers the forward-reference lookup) ----
_GH_BREAKER = get_circuit_breaker(
    "github-api",
    failure_threshold=5,
    ...,
    ignore=lambda exc: _breaker_should_ignore(exc),   # body evaluated at CALL time
)
# ... ~130 lines later ...
_IGNORED_STATUS_CODES = frozenset({404, 422})           # table the predicate consults
def _breaker_should_ignore(exc: Exception) -> bool:
    return getattr(exc, "status_code", None) in _IGNORED_STATUS_CODES

# ---- BOT AUTOFIX (breaks import) ----
_GH_BREAKER = get_circuit_breaker("github-api", ..., ignore=_breaker_should_ignore)
#   NameError: name '_breaker_should_ignore' is not defined   (raised at IMPORT)

# ---- AFTER (correct fix: reorder, keep the direct reference) ----
_IGNORED_STATUS_CODES = frozenset({404, 422})           # table moved ABOVE too
def _breaker_should_ignore(exc: Exception) -> bool:
    return getattr(exc, "status_code", None) in _IGNORED_STATUS_CODES

_GH_BREAKER = get_circuit_breaker(
    "github-api",
    failure_threshold=5,
    ...,
    # The predicate is defined above on purpose: `ignore=` is evaluated at import,
    # so a forward reference here raises NameError.
    ignore=_breaker_should_ignore,
)
```

### Runnable subprocess-import reproduction (fails on the broken commit, passes on the fix)

```bash
# Reproduce the break directly — no pytest needed:
python3 -c "import hephaestus.github.client"
#   BEFORE fix: NameError: name '_breaker_should_ignore' is not defined  (exit 1)
#   AFTER  fix: (no output, exit 0)
echo "exit=$?"
```

```python
# The same thing as an in-suite regression test:
import subprocess, sys

def test_client_module_imports_in_a_fresh_interpreter() -> None:
    proc = subprocess.run(
        [sys.executable, "-c", "import hephaestus.github.client"],
        capture_output=True, text=True,
    )
    assert proc.returncode == 0, proc.stderr
```

### Source-order guard (fast, readable ordering invariant)

```python
from pathlib import Path
import hephaestus.github.client as client

def test_predicate_defined_before_breaker_construction() -> None:
    source = Path(client.__file__).read_text()
    assert source.index("def _breaker_should_ignore") < source.index("_GH_BREAKER = "), (
        "_breaker_should_ignore must be defined ABOVE the _GH_BREAKER construction; "
        "`ignore=` is evaluated at import, so a forward reference raises NameError."
    )
```

### Wiring guard (object actually carries the callback, not a stale None)

```python
def test_breaker_ignore_predicate_is_wired() -> None:
    import hephaestus.github.client as client
    assert client._GH_BREAKER._ignore is not None
```

### Diagnostic one-liners

```bash
# Confirm import-time vs logic: uniform collection error across the matrix ⇒ import-time
pixi run python -m pytest hephaestus/ -q 2>&1 | grep -i "errors during collection"

# Prove the ordering defect on disk (line number of def vs construction)
grep -n "def _breaker_should_ignore" hephaestus/github/client.py
grep -n "_GH_BREAKER = "            hephaestus/github/client.py
#   def line number > construction line number ⇒ forward reference ⇒ will break under a direct reference
```

Verified on: ProjectHephaestus, `hephaestus/github/client.py`, fix merged in PR #2049 to `main`, all CI green; break and fix both reproduced with a runnable subprocess import (`verified-ci`).

## Verified On

| Project | Context | Details |
|---------|---------|---------|
| ProjectHephaestus | `hephaestus/github/client.py` — Copilot Autofix inlined a load-bearing lambda in the `_GH_BREAKER` circuit-breaker construction, turning a deferred forward reference into an import-time NameError that failed every test job; fixed by reordering the predicate above the construction (PR #2049, CI green) | Break/fix reproduced via `python3 -c "import hephaestus.github.client"`; three regression guards (subprocess import, source-order, wiring) mutation-tested against the offending commit |
