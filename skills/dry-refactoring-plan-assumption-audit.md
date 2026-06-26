---
name: dry-refactoring-plan-assumption-audit
description: "Checklist of hidden assumptions that bite behavior-preserving DRY refactor plans before implementation starts. Use when: (1) planning to merge two modules into one canonical, (2) replacing a module with a delegation shim that re-exports from the canonical, (3) porting tests from one file to another, (4) extending a main() function with new sub-checks, (5) consolidating two functions with the same name but different signatures, (6) extracting duplicated typed option-model defaults into a shared Pydantic hierarchy while preserving public field names, constructor kwargs, and argparse defaults."
category: architecture
date: 2026-06-26
version: "2.2.0"
user-invocable: false
verification: unverified
history: dry-refactoring-plan-assumption-audit.history
tags: [dry, refactoring, module-consolidation, planning, assumptions, shim, __all__, packaging, test-delegation, signature-collision, pydantic, option-models, argparse, constructor-compatibility]
---

# DRY Refactoring — Plan Assumption Audit

## Overview

| Field | Value |
|-------|-------|
| **Date** | 2026-06-26 |
| **Objective** | Capture hidden assumptions that can invalidate behavior-preserving DRY refactor plans before implementation starts, including module consolidation and typed option-model default consolidation |
| **Outcome** | Plan-risk checklist extended with option-model hierarchy hazards: field-name compatibility, parser/model default drift, stale fields, inherited Pydantic behavior, and constructor call-site compatibility |
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
- Refactoring duplicated typed option models into a shared base hierarchy while promising no public schema or runtime behavior change
- Moving duplicated Pydantic field defaults into base classes where inherited field order, `model_dump()` output, and constructor keyword compatibility must be tested rather than assumed
- Centralizing worker-count defaults shared by model fields and `argparse` parser defaults
- Reviewing a plan that might accidentally propagate a newly inherited option into constructor paths that previously omitted it

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

# 7. For typed option-model hierarchy refactors, re-anchor public field names and parser defaults.
grep -rn "class .*Options" hephaestus/automation/ tests/
grep -rn "max_workers\|parallel\|DEFAULT_MAX_WORKERS\|state_dir\|verbose" hephaestus/automation/ tests/
grep -rn "add_argument(.*--.*workers\|default=.*workers" hephaestus/automation/

# 8. Guard omitted constructor kwargs. These paths must stay absent unless behavior intentionally changes.
grep -rn "verbose=args.verbose" hephaestus/automation/planner.py hephaestus/automation/implementer.py hephaestus/automation/pr_reviewer.py
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

6. **For option-model hierarchies, treat field names and constructor kwargs as public API.**
   A shared worker-options base is safe only for fields that truly have the same public contract. Preserve
   distinct field names when the public surface differs: for example, one stage may expose `parallel` while
   other worker stages expose `max_workers`. Do not "normalize" those names merely because the default value
   and type are the same.

7. **Centralize defaults without duplicating or drifting parser defaults.**
   If a worker-count default is shared, introduce one exported `DEFAULT_MAX_WORKERS` constant and use it in
   both Pydantic model field defaults and `argparse` parser defaults. Add a CLI parse-level test that proves
   omitted flags produce the same value as model construction. Do not settle for checking only the model class.

8. **Keep non-worker concerns out of the worker base.**
   Do not put `agent` in a shared worker base if it is not part of the worker-count abstraction, even if many
   classes happen to carry it. Do not add stale or runtime-only fields such as `state_dir` to option models
   just because adjacent runtime classes have that attribute.

9. **Inherited fields must not change constructor call-site behavior.**
   When a field such as `verbose` becomes inherited, the constructor paths that previously did not pass it
   must continue not passing it unless the issue explicitly asks for that runtime behavior change. Add a grep
   guard for omitted paths (for example, no new `verbose=args.verbose` in planner, implementer, or PR-reviewer
   constructors) so the review checks the negative invariant, not just the new base class.

10. **Make Pydantic inheritance assumptions executable.**
   Pydantic inherited field ordering, schema/model-dump compatibility, and constructor keyword compatibility
   are implementation details until tests pin them down. Write RED tests first for inherited fields,
   `model_dump()` compatibility, constructor kwargs, parser defaults, and absence of stale fields such as
   `state_dir`.

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
| Option-model DRY plan assumes inherited Pydantic fields are behavior-neutral | Plan refactors duplicated option-model defaults into a shared hierarchy and assumes public schema, field order, `model_dump()`, and constructor kwargs stay compatible | Pydantic inheritance behavior and downstream expectations can differ from intuition; a behavior-preserving refactor is only preserved once tests pin the inherited field surface | Add RED tests for inherited model fields, `model_dump()` compatibility, constructor keyword compatibility, and absence of stale fields before changing the hierarchy |
| Normalize worker option field names too aggressively | A shared worker base tempts the plan to collapse `parallel` and `max_workers` into one public name | The field names are part of each stage's public model/CLI contract; planner-style `parallel` and worker-stage `max_workers` may intentionally differ | Share only the default constant/implementation mechanics; preserve distinct public field names unless the issue explicitly asks for an API change |
| Let parser defaults drift from model defaults | Plan centralizes model defaults but leaves `argparse` defaults copied inline | The CLI path can silently diverge from direct model construction, so one entrypoint changes behavior while another does not | Use one `DEFAULT_MAX_WORKERS` constant for both model fields and parser defaults, and test at the CLI parse level |
| Add runtime-only or stale fields during consolidation | Because runtime classes carry `state_dir`, the plan may add `state_dir` to option models while building a shared base | Adds a public option field that the objective did not request and may serialize through `model_dump()` | Add an explicit absence test/grep for `state_dir`; keep runtime state out of option models |
| Accidentally propagate newly inherited `verbose` at constructor call sites | Once `verbose` lives on a base model, implementers may start passing `args.verbose` in constructor paths that previously omitted it | That changes runtime behavior under the cover of a DRY refactor, especially in planner/implementer/reviewer paths where verbose was intentionally not threaded | Add a grep guard against new `verbose=args.verbose` in the previously omitted constructor paths, and require an explicit issue/acceptance criterion before changing that behavior |

## Results & Parameters

### Assumption Audit Checklist (copy-paste into plan PR description)

```
## Pre-implementation assumption audit

- [ ] Read `hephaestus/<package>/__init__.py` — does `__all__` exist? New symbols listed?
- [ ] Traced all `return`/`sys.exit` in target `main()` — do all output modes reach new checks?
- [ ] Counted test classes in source test file (`grep "^class Test" | wc -l`) — shim imports test classes (not symbols)?
- [ ] Verified `packaging` in `pyproject.toml [project.dependencies]`
- [ ] Same-name collision resolved: path-vs-string identified, `_extract_versions_from_text` helper added, shim aliases new name?
- [ ] Public option field names preserved (`parallel` remains distinct from `max_workers` when both exist)?
- [ ] Shared worker default is a single `DEFAULT_MAX_WORKERS` constant used by model fields and parser defaults?
- [ ] Parser defaults verified by parsing the CLI, not only by model construction?
- [ ] Inherited Pydantic fields covered by RED tests for `model_dump()` and constructor kwargs?
- [ ] Negative invariants tested: no `state_dir` option field and no new `verbose=args.verbose` in omitted constructor paths?
```

### Issue #1189 Specific Findings

| Assumption | Status | Correct Answer |
|------------|--------|----------------|
| `validation/__init__.py __all__` doesn't need updating | WRONG | Has explicit `__all__`; 9 new symbols must be added |
| `scripts_lib` test shim satisfies coverage | WRONG | Shim must import test classes; zero tests collected from symbol-only imports |
| JSON mode runs all checks | WRONG | `if args.json: ... return 0` exits before new CI sub-checks; move checks before branch |
| `packaging` is a declared dependency | UNVERIFIED | Not checked against `pyproject.toml` before plan was written |
| Same-name `extract_pyproject_versions` collision is safe to shim | WRONG | `path: Path` vs `content: str` — shim at wrong layer returns `{}` silently; fix = `extract_pyproject_versions_str` + `_extract_versions_from_text` helper |

### Option-Model Defaults Specific Findings

| Assumption | Status | What a reviewer must do |
|------------|--------|-------------------------|
| Line numbers and `rg` evidence in the plan are current | UNVERIFIED / DRIFT-PRONE | Re-run symbol-based `rg` before implementation; do not edit by stale line coordinates |
| Pydantic inherited field order/schema/model-dump behavior is neutral | UNVERIFIED | Require tests for inherited fields, `model_dump()`, constructor keyword compatibility, and public schema expectations |
| Parser defaults stay aligned with model defaults | UNVERIFIED | Parse each affected CLI with omitted flags and compare against direct model construction / `DEFAULT_MAX_WORKERS` |
| Prior guidance to keep `agent` out of the base is authoritative | CONTEXTUAL, NOT SOURCE-VERIFIED | Treat it as review guidance from conversation context; verify against issue scope and current code rather than presenting it as an external source |
| Distinct worker field names can be flattened | RISK | Preserve planner `parallel` separately from worker-stage `max_workers`; field-name changes are public behavior changes |
| `state_dir` belongs in options because runtime classes have it | WRONG DIRECTION | Keep runtime state out of option models and test/grep that `state_dir` was not added |
| Inherited `verbose` should now be passed everywhere | RISK | Preserve constructor call-site behavior; grep that planner, implementer, and PR-reviewer paths did not gain `verbose=args.verbose` unless explicitly required |

## Verified On

| Project | Context | Details |
|---------|---------|---------|
| ProjectHephaestus | Planning phase for issue #1189 (python-version-consistency consolidation) | v1.0.0 plan NOGO'd; v2.0.0 revised plan addresses all 5 failure modes; implementation pending |
| ProjectHephaestus | Planning-review phase for issue #1386 (automation option-model default hierarchy) | v2.2.0 adds unverified reviewer-risk checklist for behavior-preserving Pydantic option-model DRY refactor; implementation pending |
