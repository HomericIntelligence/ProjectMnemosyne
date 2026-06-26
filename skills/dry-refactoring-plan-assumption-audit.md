---
name: dry-refactoring-plan-assumption-audit
description: "Checklist of hidden assumptions that bite DRY module-consolidation plans before implementation starts. Use when: (1) planning to merge two modules into one canonical, (2) replacing a module with a delegation shim that re-exports from the canonical, (3) porting tests from one file to another, (4) extending a main() function with new sub-checks, (5) consolidating two functions with the same name but different signatures, (6) centralizing duplicated argparse setup across validation CLIs, including parse_known_args paths."
category: architecture
date: 2026-06-26
version: "2.2.0"
user-invocable: false
verification: unverified
history: dry-refactoring-plan-assumption-audit.history
tags: [dry, refactoring, module-consolidation, planning, assumptions, shim, __all__, packaging, test-delegation, signature-collision, argparse, validation-cli, repo-root, parse-known-args, behavioral-tests]
---

# DRY Refactoring — Plan Assumption Audit

## Overview

| Field | Value |
|-------|-------|
| **Date** | 2026-06-26 |
| **Objective** | Capture hidden assumptions that invalidate DRY refactoring plans before implementation, including module consolidation and validation CLI parser centralization |
| **Outcome** | Planning-only checklist extended for ProjectHephaestus issue #1409: centralize duplicated validation parser setup with `create_validation_parser()` while preserving `--repo-root`, `--json`, `--version`, `parse_known_args`, optional path, and multi-entry-point semantics |
| **Verification** | unverified — #1409 workflow was captured from an implementation plan; no code, tests, CLI runs, or CI validated it |
| **History** | [changelog](./dry-refactoring-plan-assumption-audit.history). v2.2.0 adds validation CLI parser centralization planning risks. |

## When to Use

- Planning to merge two modules into one canonical module (DRY consolidation)
- Replacing an existing module with a delegation shim that re-exports from the canonical
- Porting test classes from one file to another during a refactor
- Adding new public functions to an existing module within a package
- Extending a `main()` function with new sub-checks
- Adding a `from packaging.version import Version` (or any ecosystem dependency) to a new function
- Two modules share a function name with different signatures
- Extracting values from structured config files (TOML, YAML) using regex — always verify section-boundary behavior with a cross-section test case
- Centralizing duplicated `argparse.ArgumentParser` setup across validation entry points
- Adding or migrating a shared validation CLI parser that owns `--repo-root`, `--json`, and `--version`
- A validation script uses `parse_known_args()` to forward unknown tool arguments, such as mypy flags, and the refactor must preserve that unknown list exactly
- A module contains multiple CLI entry points or wrapper functions; each entry point must be inventoried and migrated independently

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

# 7. Inventory validation parser construction and known/unknown parsing
rg -n "ArgumentParser\\(|add_json_arg|add_version_arg|parse_args\\(|parse_known_args\\(" hephaestus/validation hephaestus/cli

# 8. Find every validation entry point, including argv-aware wrappers
rg -n "^def main\\(|argv|parse_known_args\\(" hephaestus/validation
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

6. **For validation CLI parser centralization, inventory current entry points at planning time.**
   Do not rely on a stale `rg` snapshot embedded in a prompt or prior review. Re-run the search in the
   current checkout and record both parser setup helpers and parsing mode (`parse_args` vs `parse_known_args`).
   Adjacent modules near the issue boundary are review risk; explicitly include or exclude them by name.

7. **Normalize `repo_root` after both `parse_args()` and `parse_known_args()`.**
   If the shared helper returns a parser subclass or factory, prove that both parsing APIs apply the same
   `repo_root` normalization. For `parse_known_args`, preserve the unknown argument list byte-for-byte:
   normalization must only mutate `args.repo_root`, never filter, reorder, or reinterpret forwarded tool args.

8. **Preserve optional path semantics when adding `--repo-root`.**
   If a validation script accepts an explicit file/path argument, only derive the default repo-relative path from
   `args.repo_root` when that explicit argument is omitted. A central parser must not silently override an
   operator-provided path.

9. **Migrate every entry point independently.**
   Some validation modules expose more than one CLI entry point or `argv`-aware wrapper. A plan that migrates only
   the obvious `main()` can leave a second parser path with duplicated flags or divergent behavior.

10. **Prefer behavioral tests over structural text checks.**
    Structural assertions such as "source contains `create_validation_parser`" are useful smoke checks, not proof.
    Add tests that call each entry point with representative argv and assert normalized `repo_root`, JSON/version flag
    behavior, optional path defaults, and exact preservation of unknown forwarded args.

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
| #1409 — Stale validation parser inventory | Planned from an `rg` snapshot of `add_json_arg`, `add_version_arg`, and `parse_known_args` without re-running it in the final planning turn | Dynamic parser setup, adjacent validation modules, or future drift can be missed, especially when one module has multiple entry points | Re-run the inventory in the current checkout and state the inclusion/exclusion boundary for every adjacent validation module |
| #1409 — `parse_known_args` treated like `parse_args` | Proposed parser subclass normalization without executing it against a forwarded-args CLI | Unknown mypy/tool args could be filtered, reordered, or interpreted by the shared parser while `repo_root` normalization appears to work | Add a behavioral test proving `args.repo_root` is normalized and the returned unknown list is exactly unchanged |
| #1409 — Optional explicit path semantics inferred | Planned `audit.py`/`coverage.py` repo-root defaults from line references rather than re-reading behavior | A shared parser can accidentally apply `args.repo_root` even when the operator provided an explicit path | Test both cases: omitted path derives from repo root; explicit path wins unchanged |
| #1409 — Only the obvious entry point migrated | Treated a validation module as having one parser path when it had two entry points/wrappers | One path keeps duplicated `--json`/`--version` flags or skips `--repo-root` normalization | Inventory `def main`, `argv`, and parser calls together; migrate every entry point independently |
| #1409 — Structural tests only | Planned text-shape checks for helper usage without enough CLI behavior coverage | Code can satisfy string checks while breaking call semantics, unknown forwarding, or optional path defaults | Keep structural tests as a supplement; require argv-level behavior tests for each migrated CLI |

## Results & Parameters

### Assumption Audit Checklist (copy-paste into plan PR description)

```
## Pre-implementation assumption audit

- [ ] Read `hephaestus/<package>/__init__.py` — does `__all__` exist? New symbols listed?
- [ ] Traced all `return`/`sys.exit` in target `main()` — do all output modes reach new checks?
- [ ] Counted test classes in source test file (`grep "^class Test" | wc -l`) — shim imports test classes (not symbols)?
- [ ] Verified `packaging` in `pyproject.toml [project.dependencies]`
- [ ] Same-name collision resolved: path-vs-string identified, `_extract_versions_from_text` helper added, shim aliases new name?
- [ ] Validation CLI parser inventory re-run in current checkout (`rg` over parser construction and parsing calls)
- [ ] `parse_known_args()` path tested: normalized `args.repo_root`, exact unknown-args preservation
- [ ] Optional explicit path behavior tested: repo-root default only applies when path is omitted
- [ ] Multi-entry-point modules checked independently; no secondary `main()`/wrapper left unmigrated
- [ ] Tests cover CLI behavior through argv, not only source text shape
```

### Issue #1189 Specific Findings

| Assumption | Status | Correct Answer |
|------------|--------|----------------|
| `validation/__init__.py __all__` doesn't need updating | WRONG | Has explicit `__all__`; 9 new symbols must be added |
| `scripts_lib` test shim satisfies coverage | WRONG | Shim must import test classes; zero tests collected from symbol-only imports |
| JSON mode runs all checks | WRONG | `if args.json: ... return 0` exits before new CI sub-checks; move checks before branch |
| `packaging` is a declared dependency | UNVERIFIED | Not checked against `pyproject.toml` before plan was written |
| Same-name `extract_pyproject_versions` collision is safe to shim | WRONG | `path: Path` vs `content: str` — shim at wrong layer returns `{}` silently; fix = `extract_pyproject_versions_str` + `_extract_versions_from_text` helper |

### Issue #1409 Specific Findings

| Assumption | Status | Correct Answer |
|------------|--------|----------------|
| Validation parser inventory is complete from a prior `rg` snapshot | UNVERIFIED | Re-run parser and entry-point inventory in the current checkout before implementation |
| `parse_args()` and `parse_known_args()` can share normalization without dedicated tests | UNVERIFIED | Test both APIs; `parse_known_args` must normalize `repo_root` while preserving unknown args exactly |
| `audit.py` and `coverage.py` default files can always be made repo-relative | UNVERIFIED | Use `args.repo_root` only when the optional explicit path is omitted |
| `markdown.py` can be treated as one migration site | WRONG RISK | It has two entry points in the plan context; migrate and test each independently |
| A CLI barrel export is harmless | UNVERIFIED | Check for import cycles before adding exports through `hephaestus/cli/__init__.py` or similar barrels |
| Structural source tests are enough for parser migration | WRONG RISK | Add behavioral argv tests for flags, version handling, repo-root normalization, and unknown forwarding |

### #1409 Unverified Inputs To Re-open

| Input | Why It Must Be Re-opened |
|-------|--------------------------|
| GitHub issue #1409 text and prior NOGO review | They were referenced from prompt context, not fetched in the final planning turn |
| `utils.py:75`, `audit.py:31`, `coverage.py:31`, `markdown.py:474/708`, `mypy_per_file.py:151` | Line references came from an earlier/current inventory and were not re-opened during final plan authoring |
| `rg -n "add_json_arg|add_version_arg|parse_known_args" hephaestus/validation` | Cited as evidence but not re-run in the final message |
| No tests or CLI commands executed | The workflow is planning-only and remains unverified |

## Verified On

| Project | Context | Details |
|---------|---------|---------|
| ProjectHephaestus | Planning phase for issue #1189 (python-version-consistency consolidation) | v1.0.0 plan NOGO'd; v2.0.0 revised plan addresses all 5 failure modes; implementation pending |
| ProjectHephaestus | Planning phase for issue #1409 (validation CLI parser centralization) | v2.2.0 capture; implementation plan only. No issue fetch, file re-open, `rg`, tests, CLI command, or CI run validated the proposed workflow. |
