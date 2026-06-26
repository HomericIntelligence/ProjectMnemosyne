---
name: deprecated-api-removal-plan-review
description: "Plan-review checklist for removing deprecated public APIs without trusting a grep-only caller inventory. Use when: (1) a plan deletes deprecated shims or aliases, (2) public exports, lazy imports, __all__, or subpackage surfaces change, (3) warning tests become removal guards, (4) the plan cites session memory, file paths, line numbers, or issue scope without a current freshness pass."
category: architecture
date: 2026-06-26
version: "1.0.0"
user-invocable: false
verification: unverified
tags:
  - planning
  - plan-review
  - deprecated-api
  - api-removal
  - public-api
  - compatibility
  - lazy-imports
  - exports
  - grep-inventory
  - unverified-assumptions
  - migration-docs
---

# Deprecated API Removal: Plan Review Risk Capture

## Overview

| Field | Value |
|-------|-------|
| **Date** | 2026-06-26 |
| **Objective** | Capture how to review plans that remove deprecated public API shims, aliases, or compatibility wrappers, with special focus on caller-inventory risk, public-surface completeness, semver/policy compatibility, and replacing deprecation-warning tests with absence guards plus canonical API coverage. |
| **Outcome** | Planning guidance only. The source plan proposed removing deprecated shims and updating exports, tests, and docs, but the implementation was not executed and no CI result was observed. |
| **Verification** | unverified - produced from an implementation plan, not from an executed implementation or CI result. |

This skill is about the **plan-review risk surface** for removing deprecated APIs. It is not a
general deprecation policy and it is not proof that any specific deprecated symbol is safe to
delete. Treat every caller count, file path, and line number in a removal plan as stale until
the current checkout proves it.

## When to Use

- Reviewing or authoring an implementation plan that deletes deprecated functions, classes,
  constants, shims, aliases, or warning wrappers from a public package.
- The plan claims "zero production callers", "only exports/tests/docs remain", or similar based
  on grep output.
- The change touches package public surfaces: implementation modules, subpackage `__init__.py`
  files, top-level lazy imports, `_LAZY_IMPORTS`, `_LAZY_EXPORTS`, `__all__`, `__getattr__`, or
  generated API docs.
- Deprecation-warning tests are being deleted or rewritten because the symbol should no longer
  exist.
- The plan relies on issue text, remembered session context, previously cited file paths, line
  numbers, docs, or API names without opening the current files in the current run.
- Downstream compatibility matters: CLI users, plugin consumers, integration imports, or external
  packages may import names that do not appear in the obvious in-repo production grep.

## Proposed Workflow

> **Warning:** This workflow has not been validated end-to-end. Treat as a hypothesis until CI confirms.

### Quick Reference

```bash
# Replace OLD_NAME and NEW_NAME with the deprecated and canonical API names.
OLD_NAME="retry_with_jitter"
NEW_NAME="retry_with_backoff"

# 1. Capture an auditable caller inventory. Do not rely on an unscoped grep snippet.
git grep -n "$OLD_NAME" -- '*.py' '*.pyi' 'pyproject.toml' 'docs/**' 'tests/**' 'scripts/**'
git grep -n "from .* import .*${OLD_NAME}\\|import .*${OLD_NAME}" -- '*.py' '*.pyi'

# 2. Check every public surface, not just the implementation module.
git grep -n "$OLD_NAME" -- '*/__init__.py' '**/__init__.py' '*.pyi'
git grep -n "$OLD_NAME" -- '*README*' 'docs/**' 'CHANGELOG*' 'COMPATIBILITY*' 'MIGRATION*'
git grep -n "__all__\\|_LAZY_IMPORTS\\|_LAZY_EXPORTS\\|__getattr__\\|__dir__" -- '*.py'

# 3. After removal, prove the old name is absent from Python surfaces and import paths.
git grep -n "$OLD_NAME" -- '*.py' '*.pyi' 'tests/**' 'docs/**' ':!docs/changelog/**'
python - <<'PY'
import importlib

checks = [
    ("pkg.module", "retry_with_jitter"),
    ("pkg.subpackage", "retry_with_jitter"),
    ("pkg", "retry_with_jitter"),
]
for module_name, attr in checks:
    module = importlib.import_module(module_name)
    assert not hasattr(module, attr), f"{module_name}.{attr} still exists"
PY

# 4. Keep canonical behavior pinned while adding absence guards for removed names.
python -m pytest tests/test_config.py tests/test_retry.py tests/test_package_imports.py
ruff check path/to/touched/files.py tests/test_touched_files.py
python -m pytest
```

### Detailed Steps

1. **Treat grep-only caller inventories as the highest-risk assumption.** A plan that says
   "grep found no production callers" is not review-ready until it states the exact commands,
   root directory, tracked/untracked status, include globs, exclude globs, and whether generated
   files, docs, examples, scripts, tests, integration packages, plugin entry points, and type stubs
   were included. Require the reviewer to see the actual command scope, not a summarized count.

2. **Audit dynamic and lazy public surfaces explicitly.** Deprecated APIs often survive through
   a package surface even after the implementation symbol is removed. Review all of these before
   accepting the plan: implementation module, subpackage `__init__.py`, top-level package
   `__init__.py`, lazy import maps, module `__getattr__`, `__dir__`, `__all__`, `.pyi` stubs,
   integration import tests, and docs that list public symbols.

3. **Separate "removed from implementation" from "removed from public contract."** A name can be
   absent from the old implementation file but still importable through a shim, alias, star export,
   namespace package, compatibility module, or docs-generated import path. The plan should name
   every public import path where the old name used to work and require direct absence assertions
   for each one.

4. **Mark memory-derived details as unverified until refreshed.** If the plan uses file paths,
   line numbers, issue scope, docs state, or API names from memory or earlier session context
   without opening the current files, mark those facts unverified. Require a freshness pass before
   implementation so stale issue text or prior review notes do not become the edit script.

5. **Review semver and policy compatibility before reviewing mechanics.** Deprecated does not
   automatically mean removable. The plan should cite the project's compatibility policy, release
   phase, deprecation window, changelog/migration guidance, and any external promises. If the policy
   does not permit removal yet, the correct review result is NOGO even if the code edit is simple.

6. **Replace warning tests with absence guards plus canonical coverage.** Removing a deprecated
   symbol usually means deprecation-warning tests should not simply disappear. Require tests that
   assert the old name is absent from every public surface, and keep or add canonical API tests for
   the replacement behavior. Otherwise a plan can delete behavior coverage while claiming it only
   deleted compatibility coverage.

7. **Check downstream and operational consumers.** In-repo production imports are not the whole
   audience. Search CLI entry points, plugin examples, generated docs, notebooks, integration tests,
   packaging metadata, and any repo-local compatibility policy. If the project has sibling repos or
   published plugin surfaces, the plan should state whether they were checked or explicitly out of
   scope.

8. **Make verification prove absence and replacement behavior.** A strong plan includes a no-reference
   grep over Python surfaces, direct import/`hasattr` assertions for the removed names across
   module/subpackage/top-level packages, focused tests for affected config/retry/import behavior,
   lint on touched files, and the full suite when feasible.

## Verified Workflow

Not applicable. This skill is `verification: unverified` and the executable guidance is intentionally
under **Proposed Workflow**. The heading exists only because the current ProjectMnemosyne validator
requires a literal `## Verified Workflow` section for flat skill files.

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
|---------|----------------|---------------|----------------|
| Trust a summarized caller grep | Plan stated no production callers beyond exports/tests/docs, without making the exact grep scope and exclusions reviewable | Grep can miss dynamic imports, lazy exports, type stubs, docs-generated import paths, scripts, examples, plugins, or excluded directories | Require exact commands, globs, exclusions, and candidate-surface classification before accepting a removal plan |
| Delete deprecation-warning tests only | Warning tests were replaced conceptually by removal guards, but the risk is that behavior coverage disappears with the deprecated name | A warning test often covers both the compatibility shim and the canonical behavior it delegates to | Convert warning tests into absence guards for the removed name and keep focused canonical API coverage for the replacement |
| Update only the implementation module | Removal plan focused on deleting shim functions and obvious exports | Public importability may persist through subpackage `__init__`, top-level lazy imports, `__all__`, `__getattr__`, `.pyi` stubs, or docs | Treat public API removal as a surface audit, not a function deletion |
| Rely on remembered file paths or line numbers | Plan used issue/session context and prior file locations as if they were current facts | Files, docs, line numbers, and even issue scope drift while planning branches are open | Mark memory-derived facts unverified and require a freshness pass in the current checkout before implementation |
| Treat zero in-repo callers as policy approval | A plan inferred that no callers means removal is semver-safe | External users, CLI/plugin consumers, and documented compatibility windows are not visible in an in-repo grep | Review compatibility policy, release notes, migration docs, and downstream import surfaces separately from caller count |

## Results & Parameters

### Reviewer Acceptance Criteria

```text
Deprecated API removal plan is reviewable only if it answers:

1. Caller inventory:
   - exact grep/search commands
   - tracked file scope and include/exclude globs
   - dynamic/lazy surfaces checked
   - tests/docs/examples/scripts/integration/plugin paths classified

2. Public surfaces:
   - implementation module
   - subpackage __init__.py
   - top-level package __init__.py
   - __all__
   - lazy import/export maps and __getattr__
   - type stubs
   - integration import tests
   - docs and migration/compatibility pages

3. Policy:
   - semver or release-policy basis for removal
   - deprecation window satisfied or explicitly waived
   - downstream or external consumer risk stated

4. Tests:
   - absence guards for removed names on every public path
   - canonical API coverage for the replacement
   - docs no longer promise removed names
   - full or focused suite named with fallback if full suite is infeasible
```

### Verification Command Set

```bash
# No-reference grep after implementation.
git grep -n 'get_config_value\|retry_with_jitter' -- '*.py' '*.pyi' 'tests/**' 'docs/**'

# Focused behavior and import-surface checks. Adjust filenames to the repo.
python -m pytest \
  tests/test_config.py \
  tests/test_retry.py \
  tests/test_package_imports.py \
  tests/test_import_surface.py

# Direct absence assertions for removed public names.
python - <<'PY'
import importlib

removed = {
    "package.config": ["get_config_value"],
    "package.retry": ["retry_with_jitter"],
    "package": ["get_config_value", "retry_with_jitter"],
}
for module_name, names in removed.items():
    module = importlib.import_module(module_name)
    for name in names:
        assert name not in getattr(module, "__all__", ()), f"{name} still in {module_name}.__all__"
        assert not hasattr(module, name), f"{module_name}.{name} still resolves"
PY

# Lint touched files, then run the full suite when feasible.
ruff check path/to/touched/files.py tests/test_touched_files.py
python -m pytest
```

### Source Context

| Field | Value |
|-------|-------|
| **Source project** | ProjectHephaestus |
| **Source issue** | GitHub issue #1420 implementation plan |
| **Plan topic** | Remove deprecated API shims `get_config_value()` and `retry_with_jitter()` in favor of canonical `get_setting()` and `retry_with_backoff()`; update exports, tests, and docs. |
| **Plan-specific note** | The plan's claim that `retry_with_exponential_backoff` was out of scope because it had zero matches is itself a grep-derived assumption and should be refreshed before implementation. |
| **Verification level** | unverified - this learning came from the plan, not from executed code or CI. |

## Verified On

| Project | Context | Details |
|---------|---------|---------|
| ProjectHephaestus | Issue #1420 planning context | Planning-only capture. No implementation, local test run, or CI result was used to validate the workflow. |
