---
name: architecture-mojo-import-ambiguity-alias-pattern
description: "Resolve Mojo 1.0 'import of X is ambiguous' errors by aliasing the wrapper import locally. Use when: (1) two modules export the same name (e.g., a wrapper struct and a re-exported lower-level type), (2) a consumer imports both in one file and Mojo 1.0 rejects the duplicate name, (3) you want to preserve the public API of both modules without renaming or splitting tests."
category: architecture
date: 2026-05-10
version: "1.0.0"
user-invocable: false
verification: verified-ci
tags:
  - mojo
  - mojo-1.0
  - imports
  - alias
  - namespace
  - api-design
  - layered-api
---

# Resolve Mojo Import Ambiguity with Local Alias

## Overview

| Field | Value |
| ------- | ------- |
| **Date** | 2026-05-10 |
| **Objective** | Allow a single Mojo source file to import the same name (`SGD`) from two distinct modules (a struct-based wrapper at `shared.training.SGD` and a re-export of the lower-level `shared.autograd.optimizers.SGD` at `shared.SGD`) without triggering Mojo 1.0's `error: import of 'SGD' is ambiguous`. |
| **Outcome** | Success — `from shared.training import SGD as TrainingSGD` plus `from shared import SGD` compiles; both names remain importable from their canonical locations; comprehensive import-coverage test stays intact. |
| **Verification** | verified-ci |
| **Project** | ProjectOdyssey, PR #5388 |

## When to Use

1. Mojo 1.0 compiler emits `error: import of '<Name>' is ambiguous` when a file imports the same identifier from two different modules
2. Two layers of a public API legitimately export the same name (typical in ML codebases: a high-level wrapper struct and a re-export of the underlying primitive)
3. You want a fix local to the consumer (test file, script) without breaking either module's documented public surface
4. Migrating Python code to Mojo where same-name imports silently shadowed each other and are now flagged at compile time
5. Refactoring a package's `__init__.mojo` to re-export submodule symbols and a downstream test starts failing with the ambiguity error

## Verified Workflow

### Quick Reference

```mojo
# In the consuming file (e.g., tests/shared/test_imports.mojo):

# shared.training.SGD is a struct-based wrapper around the autograd SGD
# optimizer (shared/training/__init__.mojo) while shared.SGD re-exports
# the lower-level shared.autograd.optimizers.SGD directly
# (shared/__init__.mojo). They are intentionally two distinct types with
# the same name, so we alias the training wrapper here to keep both
# importable in one module without a name collision.
from shared.training import (
    Callback,
    SGD as TrainingSGD,   # alias the wrapper
    # ...other names...
)
from shared import (
    AdaGrad,
    Adam,
    SGD,                  # keep the re-exported autograd SGD as SGD
    # ...other names...
)
```

### Detailed Steps

1. **Identify the colliding names.** Read the compiler error: `error: import of '<Name>' is ambiguous`. Mojo points at the second import line, but the conflict is between the two source modules.
2. **Determine which side is the "wrapper" and which is the "primitive."** Usually the higher-level module wraps the lower-level one. Alias the wrapper at the import site so the primitive keeps its short name.
3. **Apply `... as <PrefixedName>` to one import.** Convention: alias to `<ModuleName><TypeName>` (e.g., `SGD as TrainingSGD`) so the alias telegraphs where it came from.
4. **Add a comment block at the import site** explaining why the alias exists, citing both source paths. Mojo error messages and stack traces do not preserve aliases, so future readers need the breadcrumb.
5. **Verify in CI** (`just test-mojo` or the relevant test group). Local hosts may have GLIBC < 2.32; use Podman or CI for actual test execution.

### Why Aliasing Is the Right Fix

- **Renaming one struct** would break public API consumers that legitimately import either name.
- **Splitting the test file** would defeat the purpose of an import-coverage test that verifies all public names import cleanly from their canonical locations.
- **Local alias** has zero blast radius, documents the intentional duplication at the site that has to deal with it, and preserves both module APIs unchanged.

### How This Differs From Python

In Python, the second `from X import SGD` silently shadows the first — the program runs but the first import is lost. Mojo 1.0 elevates this to a compile-time error. The stricter rule catches a real class of bugs (subtle wrong-type usage where the developer thought they got module A's `SGD` but actually got module B's). Expect to hit this regularly when migrating Python-style layered APIs to Mojo.

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
| --------- | ---------------- | --------------- | ---------------- |
| Rename the wrapper struct | Considered renaming `shared.training.SGD` to something like `TrainingSGD` at its definition site | Would break every downstream consumer that imports `from shared.training import SGD` — both names are intentionally part of the documented public API | Public API stability outranks local import convenience; fix at the consumer, not the producer |
| Import a different symbol | Tried `from shared.training.optimizers import sgd_step` instead of `SGD` | `sgd_step` is a function, not a struct — it doesn't replace the type import the test needed to cover | Don't substitute a different shape (function vs struct) just to dodge the name collision; the coverage gap defeats the test |
| Split `test_imports.mojo` into two files | Considered separating the `shared.training` imports from the top-level `shared` imports | The test exists specifically to prove every public name imports cleanly side-by-side from every documented module; splitting it removes the regression signal | Don't shrink a test's scope to make it pass — alias instead |

## Results & Parameters

### Files Modified

| File | Change |
| ------ | -------- |
| Consumer test file (e.g., `tests/shared/test_imports.mojo`) | Added `SGD as TrainingSGD` alias on the `from shared.training import` line plus a comment block explaining the rationale |

No producer modules touched — both `shared/__init__.mojo` and `shared/training/__init__.mojo` keep their existing `SGD` exports.

### Pattern: When Two Same-Named Imports Are Intentional

This pattern applies when ALL of these are true:

1. Two modules export the same identifier
2. Both names are documented public API and have downstream consumers
3. The names refer to **different types** (not just two aliases of one type) — that's the whole point of having both
4. A single source file legitimately needs to reference both

If any of these fail, the right fix is usually de-duplication, not aliasing.

### Trigger Checklist

Watch for this pattern when:

- Refactoring an `__init__.mojo` to re-export submodule symbols
- Writing import-coverage tests that pull comprehensively from multiple submodules
- Migrating Python code to Mojo where same-name imports were tolerated
- Adding a high-level struct-based wrapper around a lower-level primitive (common in ML: optimizers, losses, layers)

## Verified On

| Project | Context | Details |
| --------- | --------- | --------- |
| ProjectOdyssey | PR #5388 (2026-05-10) | Resolved `error: import of 'SGD' is ambiguous` between `shared.training.SGD` (wrapper struct) and `shared.SGD` (re-export of `shared.autograd.optimizers.SGD`) by aliasing the wrapper as `TrainingSGD` at the consumer site; comprehensive `test_imports.mojo` coverage preserved |
