---
name: architecture-getattr-delegate-collapse-mypy-regressions
description: >-
  Use when: (1) collapsing pure-forward delegate/wrapper methods (each just
  `return self._inner._same_name(...)`) on a facade class into the class's
  existing `__getattr__` + dynamic-delegate frozenset machinery, (2) replacing
  typed facade shims with dynamic `__getattr__` forwarding, (3) after deleting
  typed delegate methods a mypy run surfaces `[no-any-return]` ("Returning Any
  from function declared to return X") or `[attr-defined]`/`[unused-ignore]`
  errors, (4) auditing every internal call site and every test `# type: ignore`
  code before claiming a delegate-collapse refactor is type-clean. Runtime
  test-seam safety (patch.object, instance-assignment shadowing, shared-stdlib
  subprocess patching) survives the collapse, but `__getattr__ -> Any` is
  type-checker-visible and creates static regressions the runtime audit misses.
category: architecture
date: 2026-06-30
version: "1.0.0"
user-invocable: false
tags:
  - python
  - refactoring
  - __getattr__
  - delegate
  - facade
  - dynamic-forwarding
  - mypy
  - no-any-return
  - attr-defined
  - unused-ignore
  - method-assign
  - type-ignore
  - test-seams
  - patch-object
  - frozenset-delegate-table
---

# Getattr Delegate-Collapse mypy Regressions

## Overview

| Field | Value |
| ------- | ------- |
| **Date** | 2026-06-30 |
| **Category** | architecture |
| **Objective** | Collapse 17 explicit byte-for-byte pure-forward delegate methods on a facade class into its existing `__getattr__` + `ClassVar[frozenset[str]]` dynamic-forwarding machinery, and document the two classes of mypy regressions the naive plan misses |
| **Outcome** | `IssueImplementer` (hephaestus/automation/implementer.py) shrank 639L → 450L; 17 typed methods replaced by one frozenset entry each; mypy + 2274 automation unit tests green locally |
| **Verification** | verified-local — mypy + 2274 automation unit tests passed locally; CI validation pending |
| **Trigger** | A facade class with `__getattr__` dynamic forwarding plus many typed methods that just `return self._inner._same_name(...)` |

CI validation is pending; this skill is `verified-local` (mypy + the full automation
unit suite were run locally and passed, but the change has not yet been validated
through a CI run).

## When to Use

Apply this skill when any of the following is true:

- You are **collapsing pure-forward delegate/wrapper methods** — each just
  `return self._inner._same_name(...)` — into a class's already-existing
  `__getattr__` + dynamic-delegate frozenset (`_PHASE_RUNNER_DYNAMIC_DELEGATES:
  ClassVar[frozenset[str]]`-style) machinery.
- You are **replacing typed facade shims with dynamic `__getattr__` forwarding**.
- After **deleting typed delegate methods**, a mypy run surfaces
  `[no-any-return]` ("Returning Any from function declared to return X") or
  `[attr-defined]` / `[unused-ignore]` errors.
- You need to **audit call sites + test `# type: ignore` codes** before claiming
  a delegate-collapse refactor is type-clean.

Do NOT use this for moving whole modules into sub-packages with re-export *files*
(that is `automation-god-package-shim-first-decomposition`). This skill is about
collapsing *typed methods* into `__getattr__`, not moving *files*.

## Verified Workflow

> **Verification level: verified-local** — mypy and the full automation unit suite
> (2274 tests) passed locally on ProjectHephaestus issue #1438. CI validation is
> pending; no "Verified On" CI entry exists yet.

### Quick Reference

```text
Collapsing typed pure-forward delegates into __getattr__:

  Facade class with __getattr__ + DYNAMIC_DELEGATES frozenset,
  and N typed methods that just `return self._inner._same(...)`?
  └─ YES → Delegate-Collapse (this skill)
       ├─ Step 1 (RED first): add the N names to the TEST-MIRROR frozenset
       │    (e.g. PHASE_DELEGATES in the test file) and run the guard tests
       │    — they MUST FAIL (source frozenset lacks them; methods still in
       │    __dict__). This proves the tests guard the change.
       ├─ Step 2: add the N names to the SOURCE frozenset; delete the N
       │    typed methods. Guard tests go GREEN.
       ├─ Step 3: run mypy — expect TWO regression classes (below), NOT clean.
       ├─ Step 4 (call-site audit): for every deleted method, find internal
       │    callers. Any `return <call>` from a typed `-> X` function now hits
       │    [no-any-return] (since __getattr__ -> Any). Fix: pin a local
       │    annotation `name: X = impl._method(...)` at the call site.
       ├─ Step 5 (test-ignore audit): tests that mock by INSTANCE ASSIGNMENT
       │    (`impl._method = MagicMock()`) carried `# type: ignore[method-assign]`.
       │    The method no longer exists statically → mypy reports BOTH
       │    [unused-ignore] AND [attr-defined]. Fix: switch the code to
       │    `# type: ignore[attr-defined]` (matches the existing convention
       │    for already-dynamic delegates in the same file).
       └─ Step 6: re-run mypy + full unit suite — only now claim type-clean.

Runtime-safe ≠ mypy-clean. __getattr__ returns Any: invisible at runtime,
visible to the type checker.
```

### Step 1: RED-First — extend the test-mirror frozenset BEFORE touching source

The guard tests typically mirror the source frozenset (e.g. a `PHASE_DELEGATES`
constant in the test file) and assert two invariants:

- `test_dynamic_delegate_tables_are_exact` — the source frozenset equals the
  expected set of delegate names.
- `test_removed_delegates_are_not_class_methods` — none of those names appear in
  the class `__dict__` (they must be dynamic-only).

Add the N names to the **test-mirror** frozenset first and run both tests. They
MUST FAIL: the source frozenset does not yet contain them, and the methods are
still in `__dict__`. A failing RED here proves the tests actually guard the
change before you edit the source.

### Step 2: Collapse — add names to the source frozenset, delete the methods

```python
# Source frozenset (ClassVar) gains the N names:
_PHASE_RUNNER_DYNAMIC_DELEGATES: ClassVar[frozenset[str]] = frozenset({
    "_commit_changes",      # was already dynamic
    "_ensure_pr_created",   # newly collapsed
    # ... + 16 more
})

# __getattr__ forwards any name in the frozenset to the inner phase_runner:
def __getattr__(self, name: str) -> Any:
    if name in self._PHASE_RUNNER_DYNAMIC_DELEGATES:
        return getattr(self.phase_runner, name)
    raise AttributeError(name)
```

Delete the N typed wrapper methods. The guard tests now go GREEN.

### Step 3: Run mypy — expect TWO regression classes, not clean

`__getattr__` is annotated `-> Any`. Every formerly-typed access now resolves to
`Any` for mypy. Two distinct failures appear:

**Regression 1 — internal call-site return-type degradation `[no-any-return]`.**
A caller that did `pr_number = impl._ensure_pr_created(...)` then
`return pr_number` from a `-> int` function now returns `Any`:

```text
hephaestus/automation/_pr_create_phase.py:71: error:
  Returning Any from function declared to return "int"  [no-any-return]
```

**Regression 2 — test instance-assignment `# type: ignore` churn.**
Tests that mocked a delegate by instance assignment carried
`# type: ignore[method-assign]` (assigning over a real method). The method is now
dynamic-only, so mypy reports BOTH:

```text
error: unused "type: ignore" comment  [unused-ignore]
error: "IssueImplementer" has no attribute "_ensure_pr_created"  [attr-defined]
```

### Step 4: Call-site audit — re-pin the return type with a local annotation

For Regression 1, do NOT re-introduce the wrapper. Pin the type at the call site:

```python
# hephaestus/automation/_pr_create_phase.py — before
pr_number = impl._ensure_pr_created(...)
return pr_number          # -> [no-any-return]

# after — explicit local annotation re-pins the type, no wrapper needed
pr_number: int = impl._ensure_pr_created(...)
return pr_number          # OK
```

Audit EVERY call site of EVERY collapsed method for this `return <Any-call>` from
a typed function pattern before claiming mypy-clean.

### Step 5: Test-ignore audit — switch to `[attr-defined]`

For Regression 2, switch the ignore code from `method-assign` to `attr-defined`:

```python
# before — assigning over a real (now-deleted) method
ctx.impl._ensure_pr_created = mock.MagicMock(...)  # type: ignore[method-assign]

# after — the attribute is dynamic-only; match the established convention
ctx.impl._ensure_pr_created = mock.MagicMock(...)  # type: ignore[attr-defined]
```

This is NOT a new hack: other already-dynamic delegates in the same file (e.g.
`_commit_changes`) already used `[attr-defined]`. You are making the newly
collapsed methods consistent with the existing convention.

### Step 6: Re-run mypy + full unit suite, THEN claim type-clean

```bash
pixi run mypy
pixi run pytest tests/unit/automation/ -q
```

Only after both are green is the delegate-collapse refactor type-clean.

### Test-seam safety facts that DID hold (the "what worked" baseline)

These runtime seams survive the collapse — they are why the change is
behaviorally safe and only the static checker regressed:

- **`patch.object(impl, "_method")`** works through `__getattr__`: patch.object
  does a `getattr` to fetch the original (served by `__getattr__`), sets an
  instance attribute that shadows on the next lookup (since `__getattr__` only
  fires on lookup FAILURE), then deletes it on teardown.
- **Instance assignment** `impl._method = MagicMock()` shadows `__getattr__` at
  runtime — an instance `__dict__` entry wins over `__getattr__`.
- **`patch("module.subprocess.run")`** survives even when the real method body
  lives in a DIFFERENT module, because `subprocess` is a shared stdlib module
  object; patching it mutates the shared object every importer sees.

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
| --------- | ---------------- | --------------- | ---------------- |
| Run mypy only after deleting wrappers, assume clean | Deleted 17 typed delegate methods, expected no type fallout since runtime seams were verified | mypy raised `[no-any-return]` at an internal call site and `[unused-ignore]`+`[attr-defined]` at 6 test instance-assignment lines | Collapsing typed methods into `__getattr__ -> Any` ALWAYS needs a call-site + test-ignore audit; runtime-safe ≠ mypy-clean |
| Leave `# type: ignore[method-assign]` on instance-assignment test mocks | Kept the existing ignore codes after the methods became dynamic | mypy: the method no longer exists statically, so `method-assign` is `[unused-ignore]` and the assignment is now `[attr-defined]` | Switch dynamic-delegate instance-mock ignores to `[attr-defined]` to match the established convention for other dynamic delegates in the same file |

## Results & Parameters

### Scale Parameters (ProjectHephaestus issue #1438)

| Parameter | Value |
| ---------- | ----- |
| Facade class | `IssueImplementer` |
| Source file | `hephaestus/automation/implementer.py` |
| Typed delegate methods collapsed | 17 (each a byte-for-byte pure forward) |
| Class size before | 639 lines |
| Class size after | 450 lines |
| Replacement per method | 1 frozenset entry |
| Dynamic-delegate frozenset | `_PHASE_RUNNER_DYNAMIC_DELEGATES: ClassVar[frozenset[str]]` |
| Forwarding machinery | pre-existing `__getattr__` |
| Tests passing locally | 2274 automation unit tests |
| Verification level | verified-local (CI pending) |

### mypy Regression Classes (the load-bearing learning)

| # | Regression | mypy code(s) | Trigger | Fix |
| --- | ---------- | ------------ | ------- | --- |
| 1 | Internal call-site return-type degradation | `[no-any-return]` | `return <deleted-method-call>` from a typed `-> X` function; `__getattr__ -> Any` poisons the return | Pin a local annotation at the call site: `name: X = impl._method(...)` |
| 2 | Test instance-assignment ignore churn | `[unused-ignore]` + `[attr-defined]` | `impl._method = MagicMock()  # type: ignore[method-assign]` where `_method` is now dynamic-only | Switch the ignore code to `[attr-defined]` (matches existing dynamic-delegate convention) |

### Why these are easy to miss

The plan review for #1438 explicitly verified the test SEAMS survive at runtime
(patch.object via `__getattr__`, instance-assignment shadowing, subprocess-patch
routing — all behaviorally fine) but did NOT predict the STATIC type-checker
fallout. `__getattr__` returns `Any`, which is runtime-invisible but
type-checker-visible. Runtime correctness ≠ mypy-clean.

## Verified On

| Project | Context | Details |
| --------- | --------- | --------- |
| ProjectHephaestus | issue #1438 — delegate collapse executed | verified-local: mypy + 2274 automation unit tests green locally; CI validation pending |

## References

- ProjectHephaestus issue #1438 — source issue for this skill
- [python-type-hints-and-mypy-patterns.md](python-type-hints-and-mypy-patterns.md) — call-site annotation placement and manager-proxy generics (does NOT cover `__getattr__ -> Any` delegate collapse)
- [automation-god-package-shim-first-decomposition.md](automation-god-package-shim-first-decomposition.md) — moving *files* into sub-packages with re-export shims (distinct from collapsing *methods* into `__getattr__`)
- [architecture-god-function-decomposition-planning-risks.md](architecture-god-function-decomposition-planning-risks.md) — AST-measurement planning for decomposition (does NOT cover the mypy fallout)
