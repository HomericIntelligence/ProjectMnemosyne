---
name: dry-refactoring-plan-assumption-audit
description: "Checklist of hidden assumptions that bite DRY module-consolidation plans before implementation starts. Use when: (1) planning to merge two modules into one canonical, (2) replacing a module with a delegation shim that re-exports from the canonical, (3) porting tests from one file to another, (4) extending a main() function with new sub-checks, (5) consolidating two functions with the same name but different signatures, (6) removing thin wrapper methods around a canonical helper and migrating tests to patch the canonical module seam."
category: architecture
date: 2026-06-26
version: "2.2.0"
user-invocable: false
verification: unverified
history: dry-refactoring-plan-assumption-audit.history
tags: [dry, refactoring, module-consolidation, planning, assumptions, shim, __all__, packaging, test-delegation, signature-collision, canonical-helper, mock-seam, wrapper-removal]
---

# DRY Refactoring — Plan Assumption Audit

## Overview

| Field | Value |
|-------|-------|
| **Date** | 2026-06-26 |
| **Objective** | Capture the hidden assumptions that invalidated parts of the plan for consolidating `hephaestus/scripts_lib/check_python_version_consistency.py` into `hephaestus/validation/python_version.py` (issue #1189) |
| **Outcome** | Plan produced; NOGO on first version; revised plan addresses all 5 original failure modes; v2.2 adds wrapper-removal / canonical-helper mock-seam risks from a planning-only refactor |
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
- Removing thin instance-method wrappers that only delegate to a canonical helper
- Updating tests from `patch.object(instance, "_wrapper", ...)` to patch a canonical module function
- Changing imports so a test patch targets the real runtime lookup seam instead of a stale local binding

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

# 7. If deleting wrapper methods, audit every production lookup and every test patch target
rg -n "_wrapper_name|canonical_helper_name" hephaestus/ tests/

# 8. If tests will patch the canonical helper, ensure production calls use the module namespace
rg -n "from .* import canonical_helper_name|import .*_review_utils|canonical_helper_name\\(" hephaestus/

# 9. Re-read any call site with wrapper-specific kwargs before replacing it
rg -n "extra_strategies|_load_.*_fn|canonical_helper_name\\(" hephaestus/ tests/
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

6. **When deleting thin wrappers, migrate both runtime lookup and tests to the same canonical seam.**
   Removing wrapper methods is only safe if every runtime call site now resolves the helper through the same
   module object that tests patch. A direct import like `from ._review_utils import find_pr_for_issue`
   creates a local binding inside the importing module; `patch("package._review_utils.find_pr_for_issue")`
   does not replace that already-bound local name. If the desired seam is the canonical helper module, switch
   production code to module-qualified calls, for example `from . import _review_utils` followed by
   `_review_utils.find_pr_for_issue(...)`.

7. **Classify wrapper-patching tests before rewriting them.**
   Some tests patch the wrapper because they exercise discovery; those should patch the canonical module seam
   after the refactor. Other tests pass a resolved resource identifier directly, so the old wrapper patch is
   dead setup and should be removed instead of migrated. Do not bulk-replace every wrapper patch mechanically.

8. **Preserve wrapper-specific behavior at the direct canonical call site.**
   Thin wrappers often carry the last non-obvious argument differences. Before deleting one, inspect its full
   body and move every behavior-bearing argument to the new direct call. Examples include optional discovery
   strategies, state-loader callbacks, log/context arguments, timeouts, or error-handling toggles.

9. **Move search/body assertions only if they still observe the lower-level call shape.**
   If a wrapper-level test asserted a GitHub search invocation, moving it into the canonical helper suite is valid
   only when the assertion still observes the helper's actual `_gh_call` / API invocation shape. A test that only
   proves the caller passed an issue number no longer protects the body-search query.

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
| Wrapper deletion with direct helper imports | Planned to delete instance wrappers and patch the canonical helper module, while affected modules imported the helper function directly | Direct imports keep a stale local binding, so the canonical-module patch would not affect the runtime call | If the canonical module is the patch seam, production code must call through the module namespace (`_review_utils.find_pr_for_issue`) |
| Bulk-migrating wrapper patches | Treated every `patch.object(obj, "_find_pr_for_issue", ...)` as a real discovery test | Some tests pass a PR number directly and never call discovery, so the patch is dead setup | Split tests into real discovery coverage versus stale no-op mocks; migrate only the former |
| Inlining a wrapper without carrying its extra args | Replaced a wrapper call with the canonical helper but risked dropping wrapper-only options | Optional strategy flags and callback arguments are behavior, not incidental wrapper noise | Read the wrapper body and preserve every non-default argument at the new direct call site |
| Moving body-search assertions to the wrong layer | Planned to move a wrapper-level assertion into the canonical helper suite without re-checking what the assertion observes | The relocated test is only useful if it still sees the lower-level API call shape and query text | Keep body-search query assertions adjacent to the helper/API boundary that actually builds the search call |

## Results & Parameters

### Assumption Audit Checklist (copy-paste into plan PR description)

```
## Pre-implementation assumption audit

- [ ] Read `hephaestus/<package>/__init__.py` — does `__all__` exist? New symbols listed?
- [ ] Traced all `return`/`sys.exit` in target `main()` — do all output modes reach new checks?
- [ ] Counted test classes in source test file (`grep "^class Test" | wc -l`) — shim imports test classes (not symbols)?
- [ ] Verified `packaging` in `pyproject.toml [project.dependencies]`
- [ ] Same-name collision resolved: path-vs-string identified, `_extract_versions_from_text` helper added, shim aliases new name?
- [ ] Wrapper deletion audited: every runtime call now uses the same canonical module seam that tests patch?
- [ ] Test patches classified: real discovery tests migrated; direct-ID tests have dead wrapper patches removed?
- [ ] Wrapper-specific kwargs/callbacks preserved at the direct canonical call site?
- [ ] Any moved search/body assertion still observes the helper's actual API invocation shape?
- [ ] Plan line numbers and grep results revalidated against current `main` before implementation?
```

### Issue #1189 Specific Findings

| Assumption | Status | Correct Answer |
|------------|--------|----------------|
| `validation/__init__.py __all__` doesn't need updating | WRONG | Has explicit `__all__`; 9 new symbols must be added |
| `scripts_lib` test shim satisfies coverage | WRONG | Shim must import test classes; zero tests collected from symbol-only imports |
| JSON mode runs all checks | WRONG | `if args.json: ... return 0` exits before new CI sub-checks; move checks before branch |
| `packaging` is a declared dependency | UNVERIFIED | Not checked against `pyproject.toml` before plan was written |
| Same-name `extract_pyproject_versions` collision is safe to shim | WRONG | `path: Path` vs `content: str` — shim at wrong layer returns `{}` silently; fix = `extract_pyproject_versions_str` + `_extract_versions_from_text` helper |

### Wrapper-removal / canonical-helper plan findings

| Assumption | Status | Reviewer focus |
|------------|--------|----------------|
| Exact file:line references and `rg` results are still current | UNVERIFIED | Re-run the grep on current `main`; treat line numbers as planning snapshots |
| Patching the canonical helper module will affect runtime calls | CONDITIONAL | Confirm affected modules call through the module namespace, not a direct imported function binding |
| Deleting thin wrappers preserves all behavior | CONDITIONAL | Compare wrapper bodies and carry through every option, callback, and context argument |
| Every wrapper patch in tests should be migrated | WRONG | Remove no-op patches in tests that pass a resolved identifier directly; migrate only discovery-path tests |
| Body-search coverage can move to the helper suite | CONDITIONAL | Ensure the test still asserts the lower-level search/API invocation shape and query text |
| Planned verification targets are current | UNVERIFIED | Confirm targeted pytest names plus lint/mypy commands exist before relying on them |

## Verified On

| Project | Context | Details |
|---------|---------|---------|
| ProjectHephaestus | Planning phase for issue #1189 (python-version-consistency consolidation) | v1.0.0 plan NOGO'd; v2.0.0 revised plan addresses all 5 failure modes; implementation pending |
| ProjectHephaestus | Planning phase for issue #1398 (remove duplicated PR discovery wrappers and route callers to a canonical review helper) | Planning-only capture; no implementation, tests, lint, or CI were executed for this learning. Reviewer should revalidate grep results, import binding behavior, AddressReviewer-specific arguments, and test mock seams before approval. |
