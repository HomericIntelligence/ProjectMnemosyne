---
name: dry-refactoring-plan-assumption-audit
description: "Checklist of hidden assumptions that bite DRY module/helper-consolidation plans before implementation starts. Use when: (1) planning to merge two modules into one canonical, (2) replacing a module with a delegation shim that re-exports from the canonical, (3) switching a local wrapper to a canonical helper while preserving wrapper-only semantics, (4) extending a main() function with new sub-checks, (5) consolidating two functions with the same name but different signatures."
category: architecture
date: 2026-06-26
version: "2.2.0"
history: dry-refactoring-plan-assumption-audit.history
user-invocable: false
verification: unverified
tags: [dry, refactoring, module-consolidation, helper-consolidation, planning, assumptions, shim, wrapper-semantics, package-boundary, completedprocess, __all__, packaging, test-delegation, signature-collision]
---

# DRY Refactoring — Plan Assumption Audit

## Overview

| Field | Value |
|-------|-------|
| **Date** | 2026-06-26 |
| **Objective** | Capture the hidden assumptions that invalidate DRY refactor plans before implementation: module consolidation, delegation shims, local wrapper-to-canonical-helper migration, package boundary preservation, and behavior tests at the seam |
| **Outcome** | Planning guidance only; v2.2.0 extends the checklist for stale issue claims, canonical helper imports, local wrapper semantics, package layering, and return-shape assumptions |
| **Verification** | unverified — plan not yet implemented or CI-confirmed |
| **History** | [changelog](./dry-refactoring-plan-assumption-audit.history) |

## When to Use

- Planning to merge two modules into one canonical module (DRY consolidation)
- Replacing an existing module with a delegation shim that re-exports from the canonical
- Porting test classes from one file to another during a refactor
- Adding new public functions to an existing module within a package
- Extending a `main()` function with new sub-checks
- Adding a `from packaging.version import Version` (or any ecosystem dependency) to a new function
- Two modules share a function name with different signatures
- Extracting values from structured config files (TOML, YAML) using regex — always verify section-boundary behavior with a cross-section test case
- Refactoring a local subprocess/shell/Git wrapper to use a canonical helper while keeping the wrapper because it owns dry-run, logging, command-shaping, or presentation semantics
- The issue body says a module does not use the canonical helper, but the current source may already import it; re-grep before planning edits
- A planned helper swap depends on the canonical helper returning an object with `stdout`, `stderr`, and `returncode` semantics compatible with the local wrapper's callers
- A helper lives across package layers, and the plan must avoid introducing a reverse dependency from a lower-level package into a product/automation package
- Regression tests need to exercise behavior at the seam, not only assert that a source string or import statement changed

## Verified Workflow

> **Warning:** This workflow has not been validated end-to-end. Treat as a hypothesis until CI confirms.

### Quick Reference

```bash
# Before writing the plan, run these audits:

# 1. Check __all__ in affected __init__.py files
grep -n "__all__" hephaestus/<package>/__init__.py

# 2. Find early-exit paths in the target main()
grep -n "return\|sys.exit" hephaestus/<module>.py | head -30

# 3. Count test classes in the file being replaced/shimmed
grep -n "^class Test" tests/unit/<path>/test_<module>.py | wc -l

# 4. Verify dependency is declared
grep "packaging" pyproject.toml

# 5. Find all callers of the function being renamed/consolidated
grep -rn "from hephaestus.scripts_lib import\|from hephaestus.validation import" hephaestus/ tests/ scripts/

# 6. Find same-name functions across both modules
grep -rn "^def <function_name>" hephaestus/<module_a>.py hephaestus/<module_b>.py

# 7. Re-check stale issue claims and current helper imports before implementation
rg -n "canonical_helper|local_wrapper|run_subprocess|subprocess.run" src/ tests/

# 8. Audit wrapper-only semantics before deleting or bypassing local code
rg -n "dry_run|log|timeout|log_on_error|stdout|stderr|returncode|CompletedProcess" src/<package>/ tests/

# 9. Verify package layering: lower-level packages must not import product layers
rg -n "from <product_package>|import <product_package>" src/<library_package>/ tests/
```

### Detailed Steps

1. **Audit `__all__` in every `__init__.py` that re-exports from the canonical module.**
   Before adding functions to `validation/python_version.py`, read `hephaestus/validation/__init__.py` in full.
   If it has an explicit `__all__`, the new symbols MUST be added or `from hephaestus.validation import new_function` will raise `AttributeError`.

2. **Trace every early-return path in `main()` before extending it.**
   Open the target `main()` function and list every `return` / `sys.exit` statement.
   Any new sub-checks added must not be gated behind an early exit that already existed (e.g., `if args.json: ... return 0`).
   Fix: move ALL check calls before the format-branching block, then use results in both JSON and text paths.
   Each output-mode branch (JSON, plain text, quiet) must invoke the same set of checks.

3. **Test delegation shims must import test CLASSES, not just symbols.**
   If replacing a test file with an import-only shim, the shim must import the test **classes** themselves:
   ```python
   # CORRECT: pytest re-discovers imported test classes at module scope
   from tests.unit.validation.test_python_version import TestFoo, TestBar

   # WRONG: pytest collects zero tests from import-only shims of non-test symbols
   from hephaestus.scripts_lib.check_python_version_consistency import extract_pyproject_versions
   ```
   Count `grep "^class Test" | wc -l` in the source test file; verify they all exist in the destination before shimming.

4. **Verify runtime dependencies before adding new imports.**
   For any `import X` inside a new function, confirm `X` appears in `[project.dependencies]` in `pyproject.toml`.
   `packaging` is common in the Python ecosystem but not universal — check before assuming.

5. **When two modules share a function name with incompatible signatures, add a new name — do not alias.**
   If the canonical module has `extract_pyproject_versions(path: Path)` and the source module has
   `extract_pyproject_versions(content: str)`, a shim alias re-exporting the path version under the
   string name causes silent behavioral regression: `"".is_file()` returns `False`, so every
   string-content call returns `{}`.

   Fix pattern:
   - Keep `extract_pyproject_versions(path: Path)` unchanged for existing callers in the canonical module.
   - Extract a private helper `_extract_versions_from_text(content: str)` that both implementations delegate to.
   - Add a new public function `extract_pyproject_versions_str(content: str)` in the canonical module that
     calls `_extract_versions_from_text`.
   - In the shim, alias `extract_pyproject_versions_str as extract_pyproject_versions` so the source module's
     callers get the string-based version without renaming their calls.
   - Add both names to `__all__` in `validation/__init__.py`.

   ```python
   # canonical module (validation/python_version.py)
   def _extract_versions_from_text(content: str) -> dict[str, ...]:
       """Shared implementation — used by both public entry points."""
       ...

   def extract_pyproject_versions(path: Path) -> dict[str, ...]:
       """Existing callers use this; unchanged."""
       content = path.read_text()
       return _extract_versions_from_text(content)

   def extract_pyproject_versions_str(content: str) -> dict[str, ...]:
       """New entry point for callers that already have the file content."""
       return _extract_versions_from_text(content)

   # shim (scripts_lib/check_python_version_consistency.py)
   from hephaestus.validation.python_version import (
       extract_pyproject_versions_str as extract_pyproject_versions,  # preserve caller contract
       ...
   )
   ```

6. **Re-grep the premise immediately before implementation.**
   If the issue or plan says "module X still calls the old helper" or "module Y does not import the
   canonical helper," treat that as a stale snapshot until proven current. Grep for both the old and
   canonical helper names in source and tests. If the canonical import already exists, the real work
   may be narrower: change the local wrapper internals, add regression tests, or close the issue as
   already addressed. Do not plan around old line numbers without re-deriving stable anchors.

7. **Classify what the local wrapper owns before consolidating it.**
   A wrapper that merely forwards arguments can often disappear. A wrapper that owns dry-run behavior,
   structured logging, command display, retry/timeout choices, redaction, or output normalization is
   not duplicate code in the same sense. Keep the wrapper when those semantics belong to the caller's
   workflow, and delegate only the low-level process execution to the canonical helper.

8. **Check helper return-shape compatibility with behavior tests.**
   Plans often say "the canonical helper returns a `CompletedProcess`-like value" without proving the
   caller's exact expectations. Write tests for blank stdout, nonzero return codes, raised timeouts, and
   whatever the wrapper does with `stdout.strip()` / `stderr` / `returncode`. Avoid source-string tests
   that only assert an import changed; they do not prove the seam still behaves.

9. **Preserve package layering while moving helper calls.**
   When the canonical helper lives in a lower-level package, product/automation modules may import it.
   The reverse dependency is the hazard: do not move dry-run/logging semantics into the lower-level
   helper if doing so forces it to import product-layer concepts. Add or update static import-boundary
   tests when the package already has a one-way dependency contract.

10. **Confirm helper policy knobs instead of inheriting them accidentally.**
    If the canonical helper has timeout, logging-on-error, environment, or capture-output defaults,
    compare them to the wrapper's existing behavior. Either pass explicit values at the call site or
    document that the behavior intentionally changes. A plan that says "use canonical helper" without
    naming the policy knobs is incomplete.

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
|---------|----------------|---------------|----------------|
| Plan claimed "no signature change needed" | Shim re-exported `extract_pyproject_versions(path)` under the same name as the source module's `extract_pyproject_versions(content)` | `"".is_file()` returns `False`; every string-content caller received `{}` silently | When same-name collision exists, a shim alias at the wrong layer is a silent regression — add a new name instead |
| Import-only test shim | Replaced test file body with `from hephaestus.scripts_lib import extract_pyproject_versions` | pytest collects zero tests; 400+ lines of test classes do not teleport via non-test symbol imports | Test delegation shims must import test classes: `from tests.unit.validation.test_python_version import TestFoo, TestBar` |
| Added new sub-checks after `if args.json:` | Placed new `check_*` calls after an existing `if args.json: ...; return 0` block | JSON callers exit before reaching the new checks; CI never sees the new coverage | List all early exits in `main()` first; move check calls above the format-branching block |
| Did not update `validation/__init__.py __all__` | Added 8+ new functions to `python_version.py` without updating the package's `__init__.py` | `from hephaestus.validation import new_function` raises `AttributeError` even though the function exists | Grep all `__init__.py` files that import from the modified module; add every new symbol to `__all__` |
| Assumed `packaging` is a declared dependency | Used `from packaging.version import Version` in a new function | `packaging` may not be in `[project.dependencies]`; runtime `ImportError` on CI | `grep packaging pyproject.toml` before adding the import |
| R2 — DOTALL regex crosses TOML sections | Ported `_extract_versions_from_text` inherited `re.DOTALL` from `_extract_via_regex:113`. With DOTALL, `\[tool\.mypy\].*?python_version` lazy-matches past blank lines and `[tool.other]` headers — `test_mypy_version_not_crossed_from_other_section` fails. | Fix: use scripts_lib's section-bounded negative-lookahead `\[tool\.mypy\]\n(?:(?!\[).+\n)*?python_version` instead. `_extract_via_regex` now delegates to `_extract_versions_from_text`, eliminating the DOTALL regex entirely. | Always use section-bounded negative-lookahead `(?:(?!\[).+\n)*?` for TOML section extraction — never `re.DOTALL` across sections. |
| R0/R1 — Wrong test count stated as "44" | Plans stated "44 test functions" but actual scripts_lib test file has 35 functions / 9 classes. | Count test functions by direct grep before writing the plan (`grep -c "def test_" file`). | Verify counts by reading the actual file before stating them in a plan. |
| Treated an issue-body helper claim as current | Plan relied on the issue's claim that a module still needed migration to the canonical helper, while current source may already import it | The plan can over-scope or target stale line numbers when the issue body is older than the code | Re-grep the current tree for both old and canonical helper names immediately before implementation; plan against disk reality |
| Removed or bypassed a local wrapper because a canonical helper exists | Consolidation focused on duplicate subprocess execution and ignored wrapper-owned dry-run/logging behavior | The low-level execution may be duplicate, but the local wrapper's caller-facing semantics can be real product behavior | Delegate process execution to the canonical helper while keeping the wrapper if it owns dry-run, logging, redaction, or output normalization |
| Verified helper migration with source-string assertions only | Tests asserted that the new import appeared or the old call disappeared | Source strings do not prove blank stdout handling, command failure handling, timeouts, or wrapper output contracts | Add behavior tests around the seam: successful stdout, blank stdout, nonzero result, timeout/error behavior, and dry-run/logging paths |
| Moved wrapper semantics across a package boundary | Proposed absorbing higher-level dry-run/logging semantics into the lower-level canonical helper | This risks a reverse dependency or product-layer concepts leaking into the library/helper layer | Keep package arrows one-way; only the product layer should know product semantics, while the canonical helper stays low-level |

## Results & Parameters

### Assumption Audit Checklist (copy-paste into plan PR description)

```
## Pre-implementation assumption audit

- [ ] Read `hephaestus/<package>/__init__.py` — does `__all__` exist? New symbols listed?
- [ ] Traced all `return`/`sys.exit` in target `main()` — do all output modes reach new checks?
- [ ] Counted test classes in source test file (`grep "^class Test" | wc -l`) — shim imports test classes (not symbols)?
- [ ] Verified `packaging` in `pyproject.toml [project.dependencies]`
- [ ] Same-name collision resolved: path-vs-string identified, `_extract_versions_from_text` helper added, shim aliases new name?
- [ ] Re-grepped the current tree for stale issue claims and helper imports before planning edits
- [ ] Classified local wrapper semantics: pure delegation vs dry-run/logging/redaction/output normalization
- [ ] Confirmed canonical helper return shape and policy knobs (`stdout`, `stderr`, `returncode`, timeout, log-on-error)
- [ ] Checked package dependency direction; lower-level helpers do not import product-layer modules
- [ ] Added behavior regression tests around the helper seam, not only source-string assertions
```

### Boundary-Aware Helper Consolidation Checklist

```
## Canonical helper migration review checklist

- [ ] What exact current call sites still use the old helper? Evidence from grep, not issue text.
- [ ] Does the local wrapper own user-visible behavior such as dry-run logging, command display,
      redaction, timeout policy, or output normalization?
- [ ] Is the canonical helper imported from an allowed lower-level package without adding a reverse
      dependency?
- [ ] Do tests cover successful output, blank output, failure return, timeout/exception, and dry-run/logging?
- [ ] Are helper policy knobs explicit where behavior must stay stable?
- [ ] Are line numbers and test locations re-derived from stable anchors immediately before implementation?
```

### Issue #1189 Specific Findings

| Assumption | Status | Correct Answer |
|------------|--------|----------------|
| `validation/__init__.py __all__` doesn't need updating | WRONG | Has explicit `__all__`; 9 new symbols must be added |
| `scripts_lib` test shim satisfies coverage | WRONG | Shim must import test classes; zero tests collected from symbol-only imports |
| JSON mode runs all checks | WRONG | `if args.json: ... return 0` exits before new CI sub-checks; move checks before branch |
| `packaging` is a declared dependency | UNVERIFIED | Not checked against `pyproject.toml` before plan was written |
| Same-name `extract_pyproject_versions` collision is safe to shim | WRONG | `path: Path` vs `content: str` — shim at wrong layer returns `{}` silently; fix = `extract_pyproject_versions_str` + `_extract_versions_from_text` helper |

## Verified On

| Project | Context | Details |
|---------|---------|---------|
| ProjectHephaestus | Planning phase for issue #1189 (python-version-consistency consolidation) | v1.0.0 plan NOGO'd; v2.0.0 revised plan addresses all 5 failure modes; implementation pending |
| ProjectHephaestus | Planning phase for issue #1414 (canonical subprocess helper migration) | v2.2.0 adds unverified planning guidance for stale issue claims, `run_git_cmd` wrapper semantics, package layering, `CompletedProcess` stdout assumptions, and behavior regression tests. No implementation or CI run was performed for this capture. |
