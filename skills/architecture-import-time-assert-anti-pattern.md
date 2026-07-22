---
name: architecture-import-time-assert-anti-pattern
description: "Use when: (1) you wrote `assert len(REGISTRY) == EXPECTED_LEN` at the top of a Python module to enforce a single-source-of-truth count, (2) the module is loaded both in tests (where asserts run) and in production via `python -O ...` (where asserts are stripped), (3) you want the SSoT-length contract to hold *always*, not only under the developer's default interpreter, (4) you are about to add a drift-catcher assertion and want to know the canonical CI-test-only shape."
category: architecture
date: 2026-07-22
version: "1.0.0"
user-invocable: false
tags:
  - python
  - python-O
  - assert
  - sso
  - drift-catcher
  - import-time-validation
  - tuple-literal
  - contract-defer
  - test-driven-validation
---

# Architecture: Import-time `assert ...` is an Anti-pattern

## Overview

| Field | Value |
| ------- | ------- |
| **Date** | 2026-07-22 |
| **Category** | architecture |
| **Objective** | Codify why `assert` statements at module-import time are *not* a valid enforcement layer for single-source-of-truth (SSoT) registries / catalogs / inventories, and what to use instead. |
| **Outcome** | Operational — the SSoT-length contract still holds but is enforced where it cannot be silently disabled (a pytest module), not where it can (`-O` strips `assert`). |
| **Verification** | verified-exercise |
| **Applies to** | Any Python module that exports a registry, list of names, list of CLI subcommands, list of optimizer classes, list of supported architectures, ... — particularly those loaded both at test time and at production-binary time via different interpreter modes. |

## When to Use

Use this skill when **all** of these are true:

1. There is a `module.py` exporting a registry-shaped global:

   ```python
   NAMES = ("adam", "muon", "sophia", ...)  # 24 entries
   assert len(NAMES) == 24, "SSoT drift — see scripts/optimizers.py"
   ```

2. The module is consumed by both:
   - a pytest suite (default interpreter; asserts run), **and**
   - a production process that may run under `python -O` or a frozen/AOT-build
     interpreter (asserts stripped).

3. The intent was to *fail-fast* on drift between the SSoT list and another
   consumer (a dispatch table, a CLI flag table, a documentation table).

Conversely, use this entry **to push back** on a code review that asks for
"more `assert` statements at import time" — the answer is *add a test*, not add
another `assert`.

**Do not** use this entry to recommend *removing all* `assert` statements.
`assert` is fine for *internal invariants that should only fire when the
programmer made a mistake* (`assert isinstance(x, int)` inside a private
helper). It is *not* fine for *cross-module contracts that must hold under
all interpreter modes*.

## Verified Workflow

### Quick Reference

| Field | Value |
| ----- | ----- |
| **Anti-pattern** | `assert len(REGISTRY) == EXPECTED_LEN` at module-import time. |
| **Why broken** | `python -O` (and any frozen-binary or `python -OO` runtime) strips `assert` statements entirely. The SSoT-length contract silently rots. |
| **Replacement shape** | Import-time **tuple-literal assignment** with no `assert`. |
| **Where the contract lives** | A dedicated pytest module (`tests/test_<registry>_ssot.py`) whose existence is the contract. |
| **Test shape** | A single `def test_<registry>_length()` plus optional `def test_<registry>_names_match_dispatch()` that imports the production registry and asserts the exact length + element membership. |
| **Why pytest not `assert`** | pytest *runs* the test suite — narrow to the project's test runner. If CI doesn't run the test, fix CI, not the module. |
| **Side benefit** | Tuple literal assignment lets the runtime import the registry without executing any branch; minimal import-time overhead. |

### Step 1: Identify the import-time `assert`

Search the package for top-level `assert` statements:

```bash
rg -n '^[A-Za-z_]+\.py' -e '^assert ' --multiline -g '*.py'
```

For each hit, ask:

- *What contract does this enforce?*
- *Who depends on this contract?*
- *Does the consumer ever run under `python -O`?*

If the answer to the third question is "yes, possibly" or "I don't know" →
the contract belongs in a test, not in the module.

### Step 2: Replace the `assert` with a literal

```python
# BEFORE (anti-pattern):
NAMES = ("adam", "muon", "sophia", "adan", ...)
assert len(NAMES) == 24, "Registry drift"

# AFTER (correct):
NAMES = ("adam", "muon", "sophia", "adan", ...)  # contract lives in tests/test_<registry>_ssot.py
```

The annotation is allowed and recommended: a `# 24 entries; see tests/test_<registry>_ssot.py`
comment makes the contract *findable* without making it *executable in two modes*.

### Step 3: Author the drift-catcher test

```python
# tests/test_<registry>_ssot.py
from <package>.<module> import NAMES

EXPECTED_LEN = 24

def test_registry_length():
    """The SSoT registry has the expected element count.

    This is the canonical enforcement site for the 'exactly N names' contract.
    Do not move this back to a module-level assert — `python -O` strips those
    silently, and the SSoT-length contract then rots.
    """
    assert len(NAMES) == EXPECTED_LEN, f"registry drift: {len(NAMES)} != {EXPECTED_LEN}"
```

The test's job is to *fail loudly* at pytest-collection time when the registry
drifts. It is allowed to use `assert` — pytest does not run its assertions
under `python -O` because pytest imports the test module itself, not the
production registry, under optimized mode.

If the registry also has to match a *consumer* (e.g. `dispatch_step.mojo`
elif-keys), the drift-catcher may need to *also* compare element-by-element:

```python
EXPECTED = ("adam", "muon", "sophia", ...)  # repeated intentionally; see also dispatch step keys

def test_registry_matches_dispatch():
    from <package>.dispatch import SUPPORTED_OPTIMIZERS  # the consumer
    assert set(NAMES) == set(SUPPORTED_OPTIMIZERS), (
        f"drift between registry and dispatch: missing={set(SUPPORTED_OPTIMIZERS)-set(NAMES)}, extra={set(NAMES)-set(SUPPORTED_OPTIMIZERS)}"
    )
```

This is the canonical shape that turns "the contract rots silently under
`python -O`" into "the contract fails at the next CI run."

### Step 4: Verify by running both interpreter modes

Run the suite under both `python` and `python -O` and confirm the same tests
succeed — and the same tests fail when the registry is intentionally broken:

```bash
pytest tests/test_<registry>_ssot.py -q
python -O -m pytest tests/test_<registry>_ssot.py -q

# Now introduce drift and confirm both modes fail:
#   sed -i 's/"muon"/"MUON_BROKEN"/' scripts/optimizers.py
#   pytest tests/test_<registry>_ssot.py -q   -> must FAIL
#   python -O -m pytest tests/test_<registry>_ssot.py -q   -> must FAIL (same)
```

If `python -O` somehow *passes* after drift, your test still routes through an
import-time `assert`. Re-check Step 1.

### Step 5: Profile import-time cost (nice-to-have)

The replacement shape (tuple-literal assignment) has *zero* import-time cost
beyond the literal construction. If you were using `assert` to do runtime-
branching logic, *moving that logic to a function* is the cleaner fix — the
test enforces the contract; the module exposes pure data.

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
| ------- | -------------- | ------------- | -------------- |
| 1 | `assert len(REGISTRY) == N` at module-load time | `python -O` strips the assert; the SSoT-length contract silently rots in any optimized-mode process; the failure surfaces only when a downstream consumer breaks — usually in production, far from the SSoT module | Import-time asserts are *not* a contract layer; they are *developer hint* at best |
| 2 | Replace the `assert` with a `raise ValueError` at module-load | The `ValueError` *does* fire under `python -O`, raising on every production import; the developer experience degrades — every process that imports the SSoT pays an import-time branch + signal-handler cost | Import-time `raise` is too eager; defer the contract to the test runner, let the module expose pure data |
| 3 | Use `sys.flags.optimize` to gate the assert | Re-implements the same problem (under `python -O`, the check still disappears); adds a `sys`-import to a module that should be pure data | Use the interpreter mode signal *only* in a one-time check at the test boundary, not at every registry import |
| 4 | Move the check to the dispatch-table module, run it on dispatch | The dispatch module is imported later than the registry, so import-time drift is detected but the error message is far from the SSoT location; users see "dispatch failure" and grep for the wrong file | The contract belongs *next to the SSoT* in a test file; the test file is the *findable* location |
| 5 | `if __debug__: assert len(REGISTRY) == N` | `__debug__` is `False` under `python -O`, so the assert is again stripped; this is exactly the same anti-pattern in ceremonial dress | If you find yourself writing `if __debug__: assert ...`, you want a test instead |
| 6 | Catch all `AssertionError` at process startup and re-raise as `RuntimeError` | The catch was bypassed for module-level executes (the `exec` runs *during* import, before the process-startup hook is registered) and added a non-trivial import-time side effect | Per-process wrapping is too late; per-test wrapping is the right layer |

## Results & Parameters

| Field | Value |
| ----- | ----- |
| **Module shape (after)** | `REGISTRY: tuple[str, ...] = (...)` (no import-time `assert`; one-line comment pointing at the test file). |
| **Test shape** | `tests/test_<registry>_ssot.py` with `test_registry_length()` (and optional `test_registry_matches_<consumer>()`). |
| **Critical anti-patterns** | `assert ...` at module top, `if __debug__: assert ...` at module top, `sys.flags.optimize`-gated asserts; import-time `raise ValueError` (over-eager). |
| **Verifier parity** | The contract must fail under *both* `python -m pytest` and `python -O -m pytest`. If only one fails, the contract is still routed through an assert. |
| **Co-rule** | Tuple literals out-perform `assert` calls at import time on cold caches (no branch, no signal handler); preference for literals is not just correctness, it's also a perf win. |
| **Frozen-binary caveat** | `PyInstaller`, `Nuitka`, and similar frozen-binary toolchains default to `-O`-equivalent mode; assume any production deployment downstream may be running optimized, *unless you control the interpreter invocation*. |

## Verified On

| Project | Context | Details |
| ------- | ------- | ------- |
| `<project-root>` (a 24-name SSoT registry loaded via `pytest pythonpath`) | A code-review pass on a rebase PR caught `assert len(REGISTRY) == N` at module top, where the registry was also imported in production under `python -O`. | The prior implementation used an import-time `assert`; replaced with a tuple-literal concatenation.<br>The companion `<registry>-ssot` drift-catcher contract test is the recommended follow-up; until it lands, the contract is convention-only. See [`architecture-import-time-assert-anti-pattern.notes.md`](./architecture-import-time-assert-anti-pattern.notes.md). |

## Cross-references

- [`testing-dynamic-import-sys-path-resolution`](./testing-dynamic-import-sys-path-resolution.md) — the `pythonpath = scripts` plumbing that surfaces the SSoT registry to pytest in the first place; the contract test must import through the same path.
- [`training-hyperparam-lr-scale-depth-transfer`](./training-hyperparam-lr-scale-depth-transfer.md) — the per-optimizer LR screen that relies on the SSoT registry being trustworthy at the target scale.
