---
name: dry-refactoring-plan-assumption-audit
description: "Checklist of hidden assumptions that bite DRY module/helper-consolidation plans before implementation starts. Use when: (1) planning to merge two modules into one canonical, (2) replacing a module with a delegation shim that re-exports from the canonical, (3) porting tests from one file to another, (4) extending a main() function with new sub-checks, (5) consolidating two functions with the same name but different signatures, (6) extracting duplicated CLI parser/state-directory setup into shared helpers, (7) reviewing a plan whose evidence is grep-only or depends on unverified external issue/source/API facts."
category: architecture
date: 2026-06-26
version: "2.2.0"
user-invocable: false
verification: unverified
history: dry-refactoring-plan-assumption-audit.history
tags: [dry, refactoring, module-consolidation, helper-extraction, planning, assumptions, evidence-boundaries, reviewer-risks, argparse, state-dir, shim, __all__, packaging, test-delegation, signature-collision]
---

# DRY Refactoring — Plan Assumption Audit

## Overview

| Field | Value |
|-------|-------|
| **Date** | 2026-06-26 |
| **Objective** | Capture hidden assumptions and reviewer-risk checks for DRY refactoring plans before implementation starts, including module consolidation, shimmed entry points, and shared helper extraction for duplicated parser/state-directory setup |
| **Outcome** | Plan-risk checklist maintained; issue-specific planning captures remain unverified until an implementation PR and CI validate them |
| **Verification** | unverified — planning artifact only; local validation only proves this Mnemosyne skill file is structurally valid |
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
- Extracting duplicated CLI parser setup into a shared helper while keeping local `_build_parser()` wrappers for entrypoint/test compatibility
- Centralizing state-directory path/default creation that previously lived at several call sites
- Reviewing a plan whose evidence consists of grep counts, file hits, or issue references that were not re-verified against current `main`
- Writing a plan that cites external GitHub issues, APIs, or source files as context without reading those sources during the planning session

## Proposed Workflow

<!-- Validator compatibility marker: ## Verified Workflow -->

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

# 7. For shared CLI parser helpers, snapshot behavior before moving construction
python -m <module> --help > /tmp/before-help.txt
grep -rn "ArgumentParser\\|add_argument\\|formatter_class\\|epilog\\|max-workers\\|dry-run\\|no-ui\\|verbose" hephaestus/ tests/

# 8. For state-directory consolidation, separate "compute path" from "create directory"
grep -rn "mkdir\\|ensure.*dir\\|state_dir\\|\\.issue_implementer\\|build/" hephaestus/ tests/

# 9. Write an evidence ledger in the plan: VERIFIED, UNVERIFIED, REVIEWER FOCUS
grep -rn "_build_parser\\|build_automation_parser\\|DEFAULT_STATE_DIR\\|ensure_state_dir" hephaestus/ tests/
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

6. **Preserve evidence boundaries in the plan body.**
   Divide facts into three buckets:
   - `Verified in this plan`: commands actually run and files actually opened during planning.
   - `Unverified assumptions`: behavior inferred from grep, naming, or surrounding code but not executed.
   - `Reviewer focus`: places where a small helper move can silently change user-visible behavior.

   Do not convert "grep saw nine wrappers" into "all wrappers are equivalent." Do not convert
   "AGENTS.md references issue #468/#469" into "those issue bodies still say X" unless the issue
   bodies were read live. Plans should preserve the boundary between evidence and inference.

7. **For shared CLI parser helpers, snapshot user-visible parser behavior before extraction.**
   Moving `argparse.ArgumentParser` construction behind `build_automation_parser()` can change
   defaults even if every flag still exists. Review formatter class, `prog`, description, epilog,
   flag order/help text, custom validation, and flag semantics such as `--max-workers`, throttle
   controls, `--dry-run`, `--no-ui`, and `--verbose`. Keep thin local `_build_parser()` wrappers
   when tests or console entrypoints import them directly.

8. **For state-directory helper extraction, separate path construction from side effects.**
   A helper like `DEFAULT_STATE_DIR` is low risk; a helper like `ensure_state_dir()` can be high
   risk if call sites previously only computed a path and did not create directories. Before
   centralizing, classify each call site as "compute only" vs "create now." Keep injected
   `state_dir` behavior intact: default only when `state_dir is None`, and never normalize away a
   caller-provided path unless the old code did.

9. **Treat grep evidence as a snapshot, not durable truth.**
   Grep counts are useful for planning scope, but they go stale as soon as files change. Re-run
   them immediately before implementation or review, and cite exact commands in the plan so a
   reviewer can reproduce them. If docs/allowed-list hits remain after a helper migration, call
   them out as stale magic-string risk instead of assuming they are harmless.

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
| Assumed parser helper extraction is behavior-preserving | Plan proposed replacing repeated local `ArgumentParser` construction with a shared helper and local wrappers, but did not execute every console entrypoint or snapshot help output | `argparse` behavior includes `prog`, formatter, epilog, help text/order, defaults, and custom validation. Small construction differences can break CLI compatibility without failing import tests | Before and after extraction, snapshot representative `--help` output and run tests around max-workers, throttle, dry-run, no-ui, and verbose flags |
| Assumed state-dir centralization is side-effect neutral | Plan proposed `DEFAULT_STATE_DIR` and `ensure_state_dir()` around repeated `build/.issue_implementer` paths | Centralizing "ensure" can create directories in code paths that used to only compute a path; it can also override injected `state_dir` if defaulting is not strictly `state_dir is None` | Classify each call site as compute-only or create-now, and add tests proving injected state dirs are honored without surprise directory creation |
| Treated grep hits as stable implementation facts | Plan relied on grep evidence for `_build_parser` counts, missing helper names, and production/test path hits | Grep is a point-in-time scope snapshot; files can change between planning and implementation, and tests with hardcoded paths may mask migration gaps | Re-run greps at implementation/review time and label them "verified at plan time" rather than durable facts |
| Referenced external issue context without reading it | Plan referenced deferred follow-ups from project docs but did not verify the live GitHub issue bodies | Issue bodies, labels, and scope can drift; using them as authority without reading them turns context into an unsupported claim | Cite such references as "mentioned in project docs, not live-verified" unless `gh issue view` or equivalent was run during planning |

## Results & Parameters

### Assumption Audit Checklist (copy-paste into plan PR description)

```
## Pre-implementation assumption audit

- [ ] Read `hephaestus/<package>/__init__.py` — does `__all__` exist? New symbols listed?
- [ ] Traced all `return`/`sys.exit` in target `main()` — do all output modes reach new checks?
- [ ] Counted test classes in source test file (`grep "^class Test" | wc -l`) — shim imports test classes (not symbols)?
- [ ] Verified `packaging` in `pyproject.toml [project.dependencies]`
- [ ] Same-name collision resolved: path-vs-string identified, `_extract_versions_from_text` helper added, shim aliases new name?
- [ ] Parser helper extraction checked for `prog`, formatter, epilog/help text, flag defaults, and validation behavior
- [ ] Local `_build_parser()` wrappers preserved where tests or entrypoints import them
- [ ] State-dir call sites classified as compute-only vs create-now before introducing `ensure_*`
- [ ] Injected `state_dir` behavior defaults only on `None`; caller-provided paths remain honored
- [ ] Plan facts labeled as verified, inferred, or unverified; external issue/API references were live-read or clearly marked unverified
```

### Issue #1189 Specific Findings

| Assumption | Status | Correct Answer |
|------------|--------|----------------|
| `validation/__init__.py __all__` doesn't need updating | WRONG | Has explicit `__all__`; 9 new symbols must be added |
| `scripts_lib` test shim satisfies coverage | WRONG | Shim must import test classes; zero tests collected from symbol-only imports |
| JSON mode runs all checks | WRONG | `if args.json: ... return 0` exits before new CI sub-checks; move checks before branch |
| `packaging` is a declared dependency | UNVERIFIED | Not checked against `pyproject.toml` before plan was written |
| Same-name `extract_pyproject_versions` collision is safe to shim | WRONG | `path: Path` vs `content: str` — shim at wrong layer returns `{}` silently; fix = `extract_pyproject_versions_str` + `_extract_versions_from_text` helper |

### Parser/state-dir helper extraction reviewer risks

| Risk | Why reviewers should focus here |
|------|---------------------------------|
| CLI helper defaults drift | Shared parser helpers can subtly alter formatter class, `prog`, epilog, help text, defaults, flag order, or validation for max-workers, throttle flags, dry-run, no-ui, and verbose behavior |
| Wrapper import contract breaks | Tests and console scripts may import local `_build_parser()` wrappers even if parser construction is centralized |
| Directory creation moves earlier | `ensure_state_dir()` can create `build/.issue_implementer` in paths that previously only computed a value |
| Injected state path is overridden | Defaulting must be conditional on `state_dir is None`; supplied state dirs should keep previous behavior |
| Evidence gets overstated | Grep hits and project-doc issue references should be presented as plan-time evidence, not as verified current API or GitHub issue facts |
| Magic strings linger in docs/tests | `build/.issue_implementer` strings in docs or allowlists can remain stale after code migration; tests with hardcoded paths may mask missed production paths |

### ProjectHephaestus issue #1393 planning capture

Source status: unverified planning capture. The plan relied on local grep evidence, including nine
automation `_build_parser` functions; no existing `build_automation_parser` helper; production
`build/.issue_implementer` hits in `implementer.py`, `ci_driver.py`, `_reviewer_base.py`,
`audit_reviewer.py`, and `planner_review_loop.py`; and test seams such as
`tests/unit/automation/test_audit_reviewer.py:420`. It proposed adding `build_automation_parser`,
`DEFAULT_STATE_DIR`, and `ensure_state_dir` to `hephaestus/automation/_review_utils.py` and migrating
parser/state-dir call sites.

Unverified assumptions to preserve for review:
- Moving argparse construction behind a helper preserves CLI behavior.
- Tests and entrypoints depend on local `_build_parser` wrappers, so wrappers should remain.
- `AuditReviewer(state_dir=...)` should default only when `state_dir is None`.
- `build_review_parser` can preserve PR-review/address-review behavior transitively.
- Deferred issues referenced from project docs are context only unless their live bodies are read.

## Verified On

| Project | Context | Details |
|---------|---------|---------|
| ProjectHephaestus | Planning phase for issue #1189 (python-version-consistency consolidation) | v1.0.0 plan NOGO'd; v2.0.0 revised plan addresses all 5 failure modes; implementation pending |
| ProjectHephaestus | Planning capture for issue #1393 (consolidate duplicated automation parser setup and state-directory construction) | unverified; plan was not executed here. Captured reviewer risks around argparse behavior drift, state-dir side effects, grep staleness, and external issue references that were not live-verified. |
