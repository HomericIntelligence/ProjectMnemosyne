---
name: dry-refactoring-plan-assumption-audit
description: "Checklist of hidden assumptions that bite DRY refactoring plans before implementation starts. Use when: (1) planning to merge two modules into one canonical, (2) replacing a module with a delegation shim that re-exports from the canonical, (3) porting tests from one file to another, (4) extending a main() function with new sub-checks, (5) consolidating two functions with the same name but different signatures, (6) consolidating duplicated Pydantic option-model fields through inheritance."
category: architecture
date: 2026-06-26
version: "2.2.0"
user-invocable: false
verification: unverified
history: dry-refactoring-plan-assumption-audit.history
tags: [dry, refactoring, module-consolidation, planning, assumptions, shim, __all__, packaging, test-delegation, signature-collision, pydantic, inheritance, model-fields, cli-defaults]
---

# DRY Refactoring — Plan Assumption Audit

## Overview

| Field | Value |
|-------|-------|
| **Date** | 2026-06-26 |
| **Objective** | Capture hidden assumptions that bite DRY refactoring plans, including module consolidation and Pydantic option-model field consolidation. |
| **Outcome** | Plans produced; not executed end-to-end. Reviewer-risk checklists identify the assumptions implementers must verify before preserving behavior claims. |
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
- Planning a behavior-preserving refactor of Pydantic option/config models that consolidates duplicated fields into base classes or mixins.
- Reviewing a plan that assumes inherited Pydantic fields preserve `model_fields`, public constructor arguments, defaults, serialization names, and CLI behavior.
- Designing structural tests for refactored models where AST assertions could overfit one class-body shape and block legitimate future designs.

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

# 7. For Pydantic option-model inheritance, verify inherited fields are public fields.
python - <<'PY'
from hephaestus.automation.models import PlannerOptions, CIDriverOptions
for cls in (PlannerOptions, CIDriverOptions):
    print(cls.__name__, cls.model_fields)
    print(cls())
PY

# 8. Re-check issue/review scope and current diff before trusting plan-time line references.
gh issue view 1387 --repo HomericIntelligence/ProjectHephaestus
git diff -- hephaestus/automation/models.py tests/unit/automation/
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

6. **For Pydantic model-field consolidation, prove the inherited field surface with the repo's Pydantic version.**
   A behavior-preserving refactor from repeated fields to a base-model hierarchy is only safe if inherited
   annotations remain visible in `model_fields`, constructor validation, defaults, model dumping, and CLI
   adapters exactly as before. Do not assume this from general Pydantic knowledge. Run a focused probe or
   tests against the actual repo environment and compare every affected option model's public field names,
   defaults, and serialized output before and after.

7. **Make structural tests check behavior and anti-drift intent, not a single AST spelling.**
   AST tests can catch duplicate field drift, but a brittle test that only accepts one class-body shape
   rejects legitimate future designs such as aliases, mixins, or non-`Annotated` declarations. Prefer tests
   that enforce the intended invariant: shared worker defaults live in one canonical place, Planner keeps
   `parallel`, non-planner workers keep `max_workers`, and model public fields remain unchanged.

8. **Re-query external issue/review context and current diff before reviewing an implementation.**
   Plan-time `rg` findings and line numbers are current-state snapshots, not durable truth. Before approving
   an implementation, re-check the actual diff, current `models.py`, issue #1387, and any latest review
   comments. Treat prior line references as breadcrumbs, not evidence.

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
| Assumed Pydantic inherited fields preserve the public option-model surface | Plan proposed consolidating six automation Options models by moving duplicated worker fields into base classes | Pydantic inheritance behavior, constructor acceptance, `model_fields`, defaults, and serialization must be verified against the repo's installed Pydantic version and call sites; reading the class definitions is not enough | Add tests/probes that compare field names, defaults, and dumped values before claiming behavior preservation |
| Overfit AST anti-duplication tests to one implementation shape | Plan proposed structural tests to prevent duplicated worker fields from returning | Tests that only accept direct class-body `Annotated` fields can reject aliases, mixins, or other valid refactors that preserve behavior | Test the anti-drift invariant, not incidental syntax: one canonical worker-default source, correct public fields, and no behavior change |
| Trusted plan-time line numbers and `rg` findings during implementation review | Plan cited current-state line numbers and search results from planning | The repo may have changed, and sequential edits make later line numbers stale | Re-check the live diff and repo state during review; do not approve based on stale plan coordinates |
| Treated proposed validation commands as already available | Plan listed `pixi run pytest ...` and `pixi run ruff ...` but no commands were run while writing the plan | Suite availability, task wiring, and failures are unknown until implementation validation runs | Keep validation status pending until those commands execute and their output is read |
| Treated issue body and prior review as full scope without re-querying | Planning relied on issue/review context already in the session | Latest issue #1387 edits or review comments may change scope or acceptance criteria | Reviewer must re-query issue #1387 and current review comments before judging alignment |

## Results & Parameters

### Assumption Audit Checklist (copy-paste into plan PR description)

```
## Pre-implementation assumption audit

- [ ] Read `hephaestus/<package>/__init__.py` — does `__all__` exist? New symbols listed?
- [ ] Traced all `return`/`sys.exit` in target `main()` — do all output modes reach new checks?
- [ ] Counted test classes in source test file (`grep "^class Test" | wc -l`) — shim imports test classes (not symbols)?
- [ ] Verified `packaging` in `pyproject.toml [project.dependencies]`
- [ ] Same-name collision resolved: path-vs-string identified, `_extract_versions_from_text` helper added, shim aliases new name?
- [ ] For Pydantic models, compared `model_fields`, constructor acceptance, defaults, and dumped values before/after inheritance
- [ ] Verified no new public field names were introduced and no existing serialized/model field names changed
- [ ] Confirmed structural tests enforce the anti-drift invariant without hard-coding one acceptable class-body spelling
```

### Issue #1189 Specific Findings

| Assumption | Status | Correct Answer |
|------------|--------|----------------|
| `validation/__init__.py __all__` doesn't need updating | WRONG | Has explicit `__all__`; 9 new symbols must be added |
| `scripts_lib` test shim satisfies coverage | WRONG | Shim must import test classes; zero tests collected from symbol-only imports |
| JSON mode runs all checks | WRONG | `if args.json: ... return 0` exits before new CI sub-checks; move checks before branch |
| `packaging` is a declared dependency | UNVERIFIED | Not checked against `pyproject.toml` before plan was written |
| Same-name `extract_pyproject_versions` collision is safe to shim | WRONG | `path: Path` vs `content: str` — shim at wrong layer returns `{}` silently; fix = `extract_pyproject_versions_str` + `_extract_versions_from_text` helper |

### Issue #1387 Specific Findings

| Assumption / risk | Status | What a reviewer must verify |
|-------------------|--------|-----------------------------|
| Pydantic inheritance preserves public `Options` surfaces | UNVERIFIED | Compare all six affected models' `model_fields`, constructor kwargs, defaults, dumps, and call-site behavior under the repo's installed Pydantic version |
| Worker-field consolidation is behavior preserving | UNVERIFIED | Ensure no new `state_dir` field appears; Planner keeps `parallel`; other worker commands keep `max_workers`; field names and CLI behavior do not change |
| `verbose` placement is unchanged | REVIEWER RISK | Confirm `verbose` remains only on `PlanReviewerOptions`, `AddressReviewOptions`, and `CIDriverOptions` |
| Defaults still route through `_DEFAULT_WORKERS` | REVIEWER RISK | Check inherited/default declarations still use `_DEFAULT_WORKERS` and do not bake stale literal defaults into subclasses |
| AST tests catch duplication without blocking valid designs | FRAGILE | Review tests for intent-level invariants rather than syntax-only class-body snapshots |
| Plan-time references are current | STALE UNTIL RECHECKED | Re-check the actual diff, live `models.py`, issue #1387, and latest review comments before approving |
| Proposed commands are available and green | PENDING | Run and read `pixi run pytest ...` and `pixi run ruff ...`; the planning session did not execute them |

## Verified On

| Project | Context | Details |
|---------|---------|---------|
| ProjectHephaestus | Planning phase for issue #1189 (python-version-consistency consolidation) | v1.0.0 plan NOGO'd; v2.0.0 revised plan addresses all 5 failure modes; implementation pending |
| ProjectHephaestus | Planning phase for issue #1387 (consolidate duplicated worker fields across six Pydantic automation Options models) | v2.2.0 amendment captures the plan's unverified Pydantic inheritance assumption, stale-reference risks, pending validation commands, and reviewer checklist. Implementation pending. |
