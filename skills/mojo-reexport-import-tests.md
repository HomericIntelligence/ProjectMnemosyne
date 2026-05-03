---
name: mojo-reexport-import-tests
description: "Mojo re-export: add import tests for package re-exports, wire structs\
  \ through multi-level __init__.mojo chains with canonical aliases, and audit submodule\
  \ __init__.mojo files for re-export limitations. Use when: (1) adding exports to\
  \ __init__.mojo and verifying package public API, (2) a struct exists in a leaf\
  \ module but is missing from parent package imports, (3) a follow-up issue asks\
  \ to check if re-export limitations affect sibling submodules, (4) a docstring audit\
  \ reveals undocumented submodules."
category: testing
date: 2026-03-07
version: 2.0.0
user-invocable: false
tags:
  - mojo
  - reexport
  - imports
  - __init__.mojo
  - package-api
  - alias
  - docstring
  - audit
---
## Overview

| Field | Value |
| ------- | ------- |
| **Skill** | mojo-reexport-import-tests |
| **Category** | testing |
| **Trigger** | Adding re-exports to `__init__.mojo`, package API verification, re-export chain wiring, submodule limitation audits |
| **Output** | Test functions in `test_imports*.mojo`; wired `__init__.mojo` re-export chain; audited submodule docstrings |
| **Constraint** | ≤10 `fn test_` functions per file |
| **Absorbed** | mojo-reexport-chain-wiring (v1.0.0), mojo-reexport-limitation-audit (v1.0.0) on 2026-05-03 |

### Merge History

| Date | Version | Event |
| ------ | --------- | ------- |
| 2026-03-15 | v1.0.0 | Initial — import-test workflow for DataLoader/DataBatch (ProjectOdyssey #3851 / PR #4814) |
| 2026-03-07 | — | mojo-reexport-chain-wiring v1.0.0 — LossTracker/AccuracyMetric chain wiring (ProjectOdyssey #3221 / PR #3748) |
| 2026-03-07 | — | mojo-reexport-limitation-audit v1.0.0 — shared/training submodule audit (ProjectOdyssey #3210) |
| 2026-05-03 | v2.0.0 | Consolidated all three Mojo re-export skills |

## When to Use

1. A GitHub issue requests exporting a type from a submodule via `__init__.mojo`
2. A package's public API has been extended and needs import test coverage
3. Verifying that re-exported symbols are importable at the parent package level
4. Validating both `from pkg import Symbol` and `from pkg.sub import Symbol` paths
5. A Mojo struct is implemented in `pkg/subpkg/module.mojo` but not importable as `from pkg import Struct`
6. A `shared/__init__.mojo` has a commented-out line like `# from .training.metrics import Accuracy, LossTracker`
7. A plan specifies a canonical name (e.g. `Accuracy`) but the implementation uses a different name (`AccuracyMetric`)
8. You need to add symbols to an intermediate `__init__.mojo` (e.g. `shared/training/__init__.mojo`) before the root
9. A GitHub issue is a follow-up to a re-export limitation fix ("check if the same limitation affects sibling submodules")
10. A cleanup sweep requires auditing all `__init__.mojo` files in a package for re-export limitations
11. Some submodules are documented about import limitations but sibling submodules are silent on the topic

**Do NOT use** when the struct itself is missing — the chain-wiring workflow is only for wiring existing implementations.

## Verified Workflow

### Quick Reference — Import Tests

```
1. Check __init__.mojo for existing re-export (often already done)
2. Verify source module has the struct/fn
3. Check function count in split test files (≤10 per file)
4. Add test_<type>_imports() to test_imports_part1.mojo (if count ≤9)
5. Add test_<type>_imports() + test_<type>_direct_imports() to test_imports.mojo
6. Add both calls to main() in each file
7. Commit with "Closes #<issue>" in message
```

### Quick Reference — Chain Wiring

```
1. Confirm leaf module exports the symbol (grep __init__.mojo)
2. Add re-exports to intermediate __init__.mojo (shared/training/__init__.mojo)
3. Add re-exports + alias to root __init__.mojo (import from leaf, not intermediate)
4. Verify pre-commit passes
5. Commit and PR
```

### Quick Reference — Limitation Audit

```
1. Read the issue and prior context (gh issue view)
2. Locate all __init__.mojo files in the package (glob)
3. Grep for existing re-export limitation NOTEs
4. Read each __init__.mojo; categorize: has-limitation vs. clean
5. Add Note: sections documenting findings
6. Run pre-commit; commit and PR
```

---

### Step 1: Check existing re-exports (Import Tests)

Read `shared/<pkg>/__init__.mojo`. The export is often **already present** but
lacking test coverage — check for a comment like `# Issue #NNNN`:

```bash
grep -n "DataLoader\|DataBatch\|<TypeName>" shared/<pkg>/__init__.mojo
```

If missing, add:

```mojo
# Export <type> (Issue #NNNN)
from shared.<pkg>.<submodule> import (
    TypeName,
)
```

### Step 2: Verify source struct exists

```bash
grep -n "struct TypeName" shared/<pkg>/<submodule>.mojo
```

### Step 3: Check function count

```bash
grep -c "^fn test_" tests/shared/test_imports_part1.mojo
# Must be ≤ 9 before adding (limit is 10)
```

### Step 4: Add to test_imports_part1.mojo

Add the new function **before** the `# Main Test Runner` comment block:

```mojo
fn test_training_<typename>_imports() raises:
    """Test <TypeName> is importable from shared.<pkg> package.

    Verifies Issue #NNNN: <TypeName> exported from
    shared/<pkg>/__init__.mojo via the <submodule> submodule.
    """
    from shared.<pkg> import TypeName, OtherType

    print("✓ Training <TypeName> package imports test passed")
```

Add the call in `main()`:

```mojo
    test_training_<typename>_imports()
```

### Step 5: Add two functions to test_imports.mojo

Add both a package-level and a direct-submodule test:

```mojo
fn test_training_<typename>_imports() raises:
    """Test <TypeName> is importable from shared.<pkg> package.

    Verifies Issue #NNNN: <TypeName> exported from
    shared/<pkg>/__init__.mojo via the <submodule> submodule.
    """
    from shared.<pkg> import TypeName, OtherType

    print("✓ Training <TypeName> package imports test passed")


fn test_training_<typename>_direct_imports() raises:
    """Test <TypeName> is importable directly from <submodule>.

    Validates the direct import path as documented fallback:
        from shared.<pkg>.<submodule> import TypeName
    """
    from shared.<pkg>.<submodule> import TypeName, OtherType

    print("✓ Training <TypeName> direct imports test passed")
```

Add both calls to `main()`:

```mojo
    test_training_<typename>_imports()
    test_training_<typename>_direct_imports()
```

### Step 6: Commit and push (Import Tests)

```bash
git add tests/shared/test_imports.mojo tests/shared/test_imports_part1.mojo
git commit -m "test(<pkg>): add import tests for <TypeName> package export

Add test coverage verifying <TypeName> are correctly exported
from shared.<pkg> package (via __init__.mojo re-export from <submodule>).

Tests added:
- test_imports_part1.mojo: test_training_<typename>_imports() - package import
- test_imports.mojo: test_training_<typename>_imports() - package import
- test_imports.mojo: test_training_<typename>_direct_imports() - direct submodule import

Closes #NNNN

Co-Authored-By: Claude Sonnet 4.6 <noreply@anthropic.com>"

git push -u origin <branch>
gh pr create --title "test(<pkg>): add import tests for <TypeName> package export" \
  --body "Closes #NNNN"
```

---

### Chain Wiring — Step 1: Confirm the leaf module exports the symbol

```bash
grep -n "^struct\|^from\|^alias" shared/training/metrics/__init__.mojo
```

Verify `LossTracker`, `AccuracyMetric` etc. are already exported from the metrics `__init__.mojo`.

### Chain Wiring — Step 2: Add re-exports to the intermediate `__init__.mojo`

In `shared/training/__init__.mojo`, add a block near other exports:

```mojo
# Export training metrics (Issue #XXXX)
from shared.training.metrics import (
    LossTracker,
    Statistics,
    ComponentTracker,
    AccuracyMetric,
    top1_accuracy,
    topk_accuracy,
    per_class_accuracy,
)
```

**Placement**: After other `from shared.training.X import ...` blocks, before any struct definitions.

### Chain Wiring — Step 3: Add re-exports + alias to the root `__init__.mojo`

In `shared/__init__.mojo`, replace any commented-out metrics line:

```mojo
# Training metrics (most commonly used) — Issue #XXXX
from shared.training.metrics import LossTracker, AccuracyMetric

# Expose plan-canonical alias: Accuracy = AccuracyMetric
alias Accuracy = AccuracyMetric
```

**Key**: Import directly from the leaf (`shared.training.metrics`), not from the intermediate
(`shared.training`), to avoid Mojo re-export resolution issues with deeply nested chains.

### Chain Wiring — Step 4: Verify pre-commit passes

```bash
pixi run pre-commit run --files shared/__init__.mojo shared/training/__init__.mojo
```

Mojo format and syntax hooks will catch any issues. If `mojo build` is unavailable locally
(GLIBC mismatch on older hosts), rely on CI Docker for compilation verification.

### Chain Wiring — Step 5: Commit and PR

```bash
git add shared/__init__.mojo shared/training/__init__.mojo
git commit -m "feat(shared): add LossTracker and AccuracyMetric as top-level shared exports

Closes #XXXX"
gh pr create --title "feat(shared): ..." --body "Closes #XXXX" --label "implementation"
gh pr merge --auto --rebase
```

---

### Limitation Audit — Step 1: Read the issue and prior context

```bash
gh issue view <number> --comments
```

Also read the parent issue (e.g., the original re-export fix) to understand what was already documented.

### Limitation Audit — Step 2: Locate all `__init__.mojo` files in the package

```
Glob pattern="<package>/**/__init__.mojo"
```

### Limitation Audit — Step 3: Grep for re-export limitation NOTEs

```
Grep pattern="# NOTE.*[Rr]e-export|# NOTE.*submodule|# NOTE.*[Ii]mport.*[Ll]imitation"
     glob="__init__.mojo"
     output_mode="content"
```

### Limitation Audit — Step 4: Read each `__init__.mojo`

Read all submodule init files to understand their current docstrings and what they export.

### Limitation Audit — Step 5: Categorize findings

Two outcomes per submodule:
- **Has limitation** → Add a `Note:` section documenting the broken/working import pattern
  (follow `mojo-module-docstring-limitation` skill for this case)
- **No limitation (clean re-export)** → Add a `Note:` section confirming clean export and
  cross-referencing the submodule that does have a limitation

### Limitation Audit — Step 6: Add `Note:` sections to clean submodules

For submodules with no re-export limitation, add this template to the module docstring:

```mojo
"""
[Existing docstring content]

Note:
    All symbols in this module are re-exported cleanly through the parent
    `<parent.package>` package. You may import directly from either location:

    ```mojo
    from <parent.package.submodule> import <Symbol>
    from <parent.package> import <Symbol>  # also works
    ```

    No Mojo re-export limitation applies here (unlike `<parent.package.limited_submodule>`).
"""
```

Key elements:
- Show both valid import forms
- Explicitly name the one submodule that *does* have a limitation (cross-reference)
- Use a concrete symbol example from that submodule

### Limitation Audit — Step 7: Run pre-commit hooks

```bash
pixi run pre-commit run --all-files
```

All hooks should pass for documentation-only changes.

### Limitation Audit — Step 8: Commit, push, create PR

```bash
git add <changed files>
git commit -m "docs(<scope>): document import limitations audit for <package> submodules

Closes #<number>"
git push -u origin <branch>
gh pr create --title "..." --body "Closes #<number>"
gh pr merge --auto --rebase
```

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
| --------- | ---------------- | --------------- | ---------------- |
| Modifying `__init__.mojo` | Tried to add re-exports from scratch | Export was already present (added in prior work with `# Issue #3851` comment) | Always check `__init__.mojo` first — the re-export is often done, only tests are missing |
| Callback re-export pattern | Assumed same limitation applied to all types | Callbacks have a specific Mojo v0.26.1 re-export limitation; `DataLoader`/`DataBatch` work fine | Check the docstring in `__init__.mojo` for existing limitation notes before assuming failure |
| Adding to test_imports.mojo only | Added tests to monolithic file only | Split files exist for a reason — part1 also needs coverage for CI split runs | Always update both `test_imports.mojo` AND `test_imports_part1.mojo` |
| Running `mojo build shared/` locally | Executed `pixi run mojo build shared/` | GLIBC version mismatch on host (requires 2.32+, host has older) | Mojo compiler requires modern GLIBC; local build only works in Docker/CI environment |
| Using `just` command runner | Ran `just build` or `just pre-commit-all` | `just` not in PATH on this host | Always use `pixi run <cmd>` prefix (e.g. `pixi run pre-commit run --all-files`); fall back to CI for compilation |
| Broad `# NOTE` grep on all files | Initial grep for any NOTE in `__init__.mojo` | Returned too many irrelevant NOTEs (method-level notes, inline comments) | Narrow to `# NOTE.*[Rr]e-export` or `# NOTE.*submodule` patterns |

## Results & Parameters

### Issue #3851 — DataLoader/DataBatch export

- **Export location**: `shared/training/__init__.mojo` lines 93–97
- **Source module**: `shared/training/trainer_interface.mojo`
- **Types exported**: `DataLoader`, `DataBatch`
- **Test files modified**: `tests/shared/test_imports.mojo`, `tests/shared/test_imports_part1.mojo`
- **PR**: https://github.com/HomericIntelligence/ProjectOdyssey/pull/4814
- **Test counts after**: part1 = 9 functions (within ≤10 limit)

### File placement pattern (Import Tests)

```
tests/shared/
├── test_imports.mojo          # Full suite (all packages, 37 fns after)
├── test_imports_part1.mojo    # Split: Core + Training (9 fns, ≤10 fn test_ limit)
├── test_imports_part2.mojo    # Split: additional sections
└── test_imports_part3.mojo    # Split: additional sections
```

### Files modified in ProjectOdyssey#3748 (Chain Wiring)

| File | Change |
| ------ | -------- |
| `shared/training/__init__.mojo` | Added 10-line re-export block for metrics symbols |
| `shared/__init__.mojo` | Replaced 1 commented line with 3 live lines (import + alias) |

### Alias pattern for plan-canonical names

When a plan specifies `Accuracy` but the struct is `AccuracyMetric`:

```mojo
# In shared/__init__.mojo
from shared.training.metrics import AccuracyMetric

alias Accuracy = AccuracyMetric  # plan-canonical name, zero breaking changes
```

This exposes BOTH names — existing callers using `AccuracyMetric` are unaffected.

### Import depth decision

| Approach | Works? | Notes |
| ---------- | -------- | ------- |
| `from shared.training.metrics import X` in root `__init__.mojo` | Yes | Direct — bypasses intermediate chain |
| `from shared.training import X` in root `__init__.mojo` | Sometimes | May fail if Mojo re-export resolution is incomplete for that chain |

Prefer direct leaf imports at the root to avoid resolution surprises.

### Template for clean re-export Note (Limitation Audit)

```mojo
Note:
    All symbols in this module are re-exported cleanly through the parent
    `<parent.package>` package. You may import directly from either location:

    ```mojo
    from <parent.package.submodule> import <ExampleSymbol>
    from <parent.package> import <ExampleSymbol>  # also works
    ```

    No Mojo re-export limitation applies here (unlike `<parent.package.limited_submodule>`).
```

### Grep patterns for limitation audit

- Find re-export limitation NOTEs: `# NOTE.*[Rr]e-export|# NOTE.*submodule`
- Find any NOTE in init files: `# NOTE` with `glob="__init__.mojo"`
- Find import limitation patterns: `# NOTE.*directly.*import|# NOTE.*cannot.*import`

### Scope of ProjectOdyssey issue #3210 (Limitation Audit)

- `shared/training/__init__.mojo` — callbacks limitation already documented (#3091) ✅
- `shared/training/optimizers/__init__.mojo` — no limitation, confirmation note added ✅
- `shared/training/schedulers/__init__.mojo` — no limitation, confirmation note added ✅
- `shared/training/metrics/__init__.mojo` — no limitation, confirmation note added ✅
- `shared/training/loops/__init__.mojo` — no limitation, confirmation note added ✅

### Pre-commit behavior

- `mojo-format` passes (documentation changes don't introduce format violations)
- All other hooks (trailing-whitespace, end-of-file, yaml, markdown) pass for `.mojo` docstring edits

## Verified On

| Project | Context | Details |
| --------- | --------- | --------- |
| ProjectOdyssey | Issue #3221, PR #3748 — LossTracker/AccuracyMetric chain wiring | Absorbed from mojo-reexport-chain-wiring |

## Key Insights

- The re-export is often **already present** in `__init__.mojo` — check first before adding it; tests are usually what's missing
- Callbacks have a specific Mojo v0.26.1 re-export limitation; simple structs like `DataLoader`/`DataBatch` typically work fine
- Always update **both** `test_imports.mojo` AND `test_imports_part1.mojo` for CI split-run coverage
- Import from the **leaf** module directly in the root `__init__.mojo` (e.g. `from shared.training.metrics import X`), not from the intermediate (`from shared.training import X`), to avoid resolution surprises in deeply nested chains
- Use `alias Canonical = ActualStruct` in the root `__init__.mojo` to expose plan-canonical names without breaking existing callers
- Mojo compiler requires modern GLIBC (≥2.32); use `pixi run` prefix and rely on CI Docker for compilation verification
- Always use `pixi run pre-commit run --all-files`; `just` is not available in all environments
- When auditing `__init__.mojo` for NOTEs, narrow grep patterns to `# NOTE.*[Rr]e-export` — broad `# NOTE` returns too many irrelevant hits
- For clean-re-export submodules, add a `Note:` section cross-referencing the one sibling that *does* have a limitation

## See Also

- `mojo-module-docstring-limitation` — documenting a known re-export limitation
- `mojo-limitation-note-standardization` — standardizing NOTE format across modules
