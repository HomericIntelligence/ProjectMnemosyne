---
name: constant-centralization
description: "Centralize shared constants to their canonical module and update importers. Use when: duplicate constants exist across modules, or a higher-level module defines values that belong in a lower-level dependency."
category: architecture
date: 2026-03-07
user-invocable: false
---

## Overview

| Field | Value |
|-------|-------|
| **Category** | architecture |
| **Effort** | Low (minutes) |
| **Risk** | Very Low (no logic changes) |
| **Languages** | Mojo, Python, any |

Moves constant definitions from a higher-level module (e.g., a test utility) to the
lower-level module that owns the concept (e.g., the core utility it configures). The
higher-level module then imports from the canonical source.

## When to Use

- Two or more modules define the same constant with the same value
- A utility module (e.g., `layer_testers.mojo`) defines constants that semantically
  belong in a dependency (e.g., `gradient_checker.mojo`)
- Issue/PR asks to "centralize", "deduplicate", or "move" constants
- Refactoring to clarify ownership before adding new callers of the constant

## Verified Workflow

1. **Identify the canonical module** — the one that owns the concept. For gradient
   checking epsilon, that is `gradient_checker.mojo` (defines `compute_numerical_gradient`),
   not `layer_testers.mojo` (a consumer).

2. **Read both files** to understand current definitions and all usage sites.

3. **Add constants to canonical module** — insert after imports, before first struct/fn,
   with a comment block explaining the values.

   ```mojo
   # ============================================================================
   # Gradient Checking Constants
   # ============================================================================

   # Epsilon for float32 gradient checking in matmul-heavy layers.
   alias GRADIENT_CHECK_EPSILON_FLOAT32: Float64 = 3e-4

   # Epsilon for non-float32 dtypes (BF16, FP16).
   alias GRADIENT_CHECK_EPSILON_OTHER: Float64 = 1e-3
   ```

4. **Update importers** — add the constants to the existing import block from the
   canonical module; remove the local `alias` definitions.

   ```mojo
   # Before
   from shared.testing.gradient_checker import (
       check_gradients,
       compute_numerical_gradient,
   )
   alias GRADIENT_CHECK_EPSILON_FLOAT32: Float64 = 3e-4
   alias GRADIENT_CHECK_EPSILON_OTHER: Float64 = 1e-3

   # After
   from shared.testing.gradient_checker import (
       check_gradients,
       compute_numerical_gradient,
       GRADIENT_CHECK_EPSILON_FLOAT32,
       GRADIENT_CHECK_EPSILON_OTHER,
   )
   ```

5. **Verify no remaining local definitions** — grep for the constant name in the
   importer file to confirm removal.

6. **Run pre-commit** — Mojo format, trailing whitespace, and other hooks should all pass.

7. **Commit and PR** — purely a refactor commit; no logic or value changes.

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
|---------|----------------|---------------|----------------|
| Local compiler build | Ran `pixi run mojo build` to verify compilation | GLIBC version mismatch on local host (CI uses Docker) | Mojo compilation can only be verified in CI Docker environment; syntactic changes are safe to push without local compile verification |
| N/A | No other approaches tried | N/A | Straightforward refactor with no ambiguity |

## Results & Parameters

**Commit message format**:
```
refactor(testing): move <CONSTANT_NAME> constants to <canonical_module>

Centralizes <CONST_A> and <CONST_B> in <canonical_module> (the canonical
source), and imports them in <importer_module> to avoid duplication and
clarify ownership.

Closes #<issue>
```

**Search command to find duplicate constants**:
```bash
grep -rn "alias GRADIENT_CHECK_EPSILON" shared/
```

**Validation grep after refactor**:
```bash
# Should show constants only in canonical module
grep -rn "^alias GRADIENT_CHECK_EPSILON" shared/testing/
# Should show import only in importer
grep -n "GRADIENT_CHECK_EPSILON" shared/testing/layer_testers.mojo
```

**Pre-commit result**: All hooks pass (mojo format, trailing whitespace,
end-of-file-fixer, check-large-files, mixed-line-endings).
