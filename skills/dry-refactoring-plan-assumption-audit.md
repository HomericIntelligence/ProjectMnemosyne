---
name: dry-refactoring-plan-assumption-audit
description: "Checklist of hidden assumptions that bite DRY module-consolidation plans before implementation starts. Use when: (1) planning to merge two modules into one canonical, (2) replacing a module with a delegation shim that re-exports from the canonical, (3) porting tests from one file to another, (4) extending a main() function with new sub-checks, (5) consolidating two functions with the same name but different signatures, (6) moving first-party callers from a compatibility alias to a canonical helper while preserving the old import path."
category: architecture
date: 2026-06-26
version: "2.2.0"
user-invocable: false
verification: unverified
history: dry-refactoring-plan-assumption-audit.history
tags: [dry, refactoring, module-consolidation, planning, assumptions, shim, __all__, packaging, test-delegation, signature-collision, write-secure, compatibility-alias, canonical-import, import-boundary, ast-guard, public-api]
---

# DRY Refactoring — Plan Assumption Audit

## Overview

| Field | Value |
|-------|-------|
| **Date** | 2026-06-26 |
| **Objective** | Capture the hidden assumptions that invalidate DRY module-consolidation and compatibility-alias plans before implementation, including the ProjectHephaestus issue #1402 plan to move first-party `write_secure` callers from `hephaestus.automation.github_api.write_secure` to `hephaestus.io.utils.write_secure` while keeping the old import path as an alias |
| **Outcome** | Plan guidance remains unverified until implementation and CI. The skill now includes a reviewer checklist for alias-to-canonical migrations: re-check plan-time grep snapshots, verify behavior and permissions rather than identity alone, audit `__all__` and direct-import compatibility assumptions, and confirm AST import guards catch the intended boundary without overclaiming dynamic coverage |
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
- Moving first-party callers away from an old module-level helper toward a canonical helper while keeping the old module path as a compatibility alias for external imports, test patch paths, or downstream automation

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

# 7. For compatibility-alias migrations, re-check the plan-time snapshot in the
#    implementation checkout before editing.
rg -n "\bwrite_secure\b|retry_with_exponential_backoff" hephaestus tests scripts
python -c "from hephaestus.io.utils import write_secure as c; from hephaestus.automation.github_api import write_secure as a; assert a is c"
python -c "import hephaestus.io.utils as u; import inspect; print(inspect.getsource(u.write_secure))"
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

6. **For compatibility-alias migrations, verify the alias contract and the canonical behavior separately.**
   A plan that says "keep `old_module.write_secure = canonical.write_secure`" proves only one narrow
   compatibility path: direct imports from the old module can still resolve the name. It does not prove
   that the canonical helper preserves secure mode bits, atomic write behavior, parent-directory handling,
   test patch targets, or star-import behavior. Before editing, re-run the grep in the implementation
   checkout, then test both levels:
   - Identity: `old_module.write_secure is canonical_module.write_secure`.
   - Behavior: secure file permissions and atomic write semantics still hold through the production call path.
   - Public surface: `__all__` and documented compatibility tables either intentionally exclude the alias or
     are updated with tests that pin the intended import surface.
   - Patch paths: tests that patch an indirection such as `github_api.io_write_secure` must line up with the
     name production code actually calls at the payload-write site.
   - Import-boundary guards: AST checks for forbidden first-party imports should be verified on both absolute
     and relative `ImportFrom` nodes, and should not imply coverage for dynamic imports unless separately tested.

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
| Plan-time grep treated as implementation fact | The issue #1402 plan relied on grep output claiming no `retry_with_exponential_backoff` symbol exists and that `write_secure` call sites were only `_reviewer_base.py`, `implementer_state.py`, and `github_api.py` | That was a planning snapshot; another branch can add a call site or symbol before implementation starts | Re-run the full grep in the implementation checkout and scope the PR from current code, not the plan transcript |
| Alias identity used as a proxy for behavior | The plan assumed `hephaestus.io.utils.write_secure` is canonical and that `github_api.write_secure = io_write_secure` preserves the contract | Identity does not prove secure permissions, atomic replacement, parent-directory creation, or error behavior through the real caller | Add behavior tests for state persistence and payload writes, not only `is` identity assertions |
| `__all__` left unchanged without a surface audit | The plan assumed external compatibility only requires direct imports and that star-import did not previously include `write_secure` | Public API assumptions are reviewer-sensitive; downstreams may rely on direct import, star import, docs, or compatibility tables differently | Grep for `__all__`, compatibility docs, and import-surface tests; make the intended surface explicit |
| Test patch target assumed to match production call target | Review-posting tests were expected to patch `hephaestus.automation.github_api.io_write_secure` while production used `io_write_secure` near the payload-write site | File and line references drift, and a patch target only works if production still calls that bound name | Verify the exact production call before editing tests; prefer a regression that fails if the wrong indirection is used |
| Structural AST guard overclaimed import coverage | The proposed guard exempted `github_api.py` and checked `ImportFrom` nodes for forbidden first-party imports | A narrow AST guard can miss dynamic imports, aliasing patterns, or relative import shapes if the test data is incomplete | Include positive and negative fixtures for absolute and relative imports, and document that dynamic imports remain out of scope unless explicitly parsed |

## Results & Parameters

### Assumption Audit Checklist (copy-paste into plan PR description)

```
## Pre-implementation assumption audit

- [ ] Read `hephaestus/<package>/__init__.py` — does `__all__` exist? New symbols listed?
- [ ] Traced all `return`/`sys.exit` in target `main()` — do all output modes reach new checks?
- [ ] Counted test classes in source test file (`grep "^class Test" | wc -l`) — shim imports test classes (not symbols)?
- [ ] Verified `packaging` in `pyproject.toml [project.dependencies]`
- [ ] Same-name collision resolved: path-vs-string identified, `_extract_versions_from_text` helper added, shim aliases new name?
- [ ] Re-ran plan-time greps in the implementation checkout; no stale `write_secure` or retry-helper assumptions
- [ ] Proved canonical helper behavior with permissions and atomic-write tests, not only alias identity
- [ ] Audited `__all__`, docs, and import-surface tests before claiming compatibility
- [ ] Verified test patch targets match the production names used at the write site
- [ ] AST import-boundary guard has fixtures for absolute and relative `ImportFrom` cases and states any dynamic-import limits
```

### Issue #1189 Specific Findings

| Assumption | Status | Correct Answer |
|------------|--------|----------------|
| `validation/__init__.py __all__` doesn't need updating | WRONG | Has explicit `__all__`; 9 new symbols must be added |
| `scripts_lib` test shim satisfies coverage | WRONG | Shim must import test classes; zero tests collected from symbol-only imports |
| JSON mode runs all checks | WRONG | `if args.json: ... return 0` exits before new CI sub-checks; move checks before branch |
| `packaging` is a declared dependency | UNVERIFIED | Not checked against `pyproject.toml` before plan was written |
| Same-name `extract_pyproject_versions` collision is safe to shim | WRONG | `path: Path` vs `content: str` — shim at wrong layer returns `{}` silently; fix = `extract_pyproject_versions_str` + `_extract_versions_from_text` helper |

### Issue #1402 Write-Secure Alias Migration Snapshot

This section is a planning-risk capture from the ProjectHephaestus issue #1402 plan. Treat every
file path, line number, and grep result as drift-prone until checked in the implementation branch.

| Assumption | Status | Reviewer Focus |
|------------|--------|----------------|
| No `retry_with_exponential_backoff` symbol exists, and `write_secure` call sites are only `hephaestus/automation/_reviewer_base.py`, `hephaestus/automation/implementer_state.py`, and `hephaestus/automation/github_api.py` | PLAN-TIME SNAPSHOT | Re-run repo-wide grep before implementation; do not rely on stale call-site lists |
| `hephaestus.io.utils.write_secure` is canonical and preserves secure permissions and atomic behavior | UNVERIFIED | Inspect the helper and add behavior tests that exercise the real state/payload write paths |
| Keeping `github_api.write_secure = io_write_secure` is enough external compatibility, while `__all__` stays unchanged because star import allegedly did not expose `write_secure` | PUBLIC API RISK | Verify old `__all__`, docs, import-surface tests, and direct-import behavior; make the intended compatibility surface explicit |
| Review-posting tests should patch `hephaestus.automation.github_api.io_write_secure`, and production writes request payload files through that name near `github_api.py:1688` | DRIFT-PRONE LINE REFERENCE | Verify the current call target before editing tests; line numbers are not stable anchors |
| Structural AST guard exempts `github_api.py` and flags forbidden first-party `ImportFrom` nodes elsewhere | LIMITED GUARD | Confirm it catches absolute and relative imports without implying coverage for dynamic imports or all aliasing patterns |
| Regression tests for canonical import identity and secure file permissions prove the migration | INCOMPLETE | Add/import-surface compatibility tests too; behavior tests do not prove external import users remain compatible |

## Verified On

| Project | Context | Details |
|---------|---------|---------|
| ProjectHephaestus | Planning phase for issue #1189 (python-version-consistency consolidation) | v1.0.0 plan NOGO'd; v2.0.0 revised plan addresses all 5 failure modes; implementation pending |
| ProjectHephaestus | Planning phase for issue #1402 (move first-party `write_secure` callers to `hephaestus.io.utils.write_secure` while preserving `hephaestus.automation.github_api.write_secure` as a compatibility alias) | Plan produced, NOT executed; this skill records the unverified assumptions and reviewer risks for implementation. |
