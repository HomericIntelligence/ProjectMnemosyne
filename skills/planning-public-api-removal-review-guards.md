---
name: planning-public-api-removal-review-guards
description: "Use when planning or reviewing removal of deprecated public APIs: verify import surfaces, downstream/plugin callers, SemVer timing, migration-doc exceptions, stale-reference scans, and rollback paths before treating the plan as implementation-ready."
category: architecture
date: 2026-06-26
version: "1.0.0"
user-invocable: false
verification: unverified
tags:
  - planning
  - public-api-removal
  - deprecated-api
  - compatibility
  - migration-docs
  - lazy-imports
  - re-exports
  - removal-guards
  - stale-references
  - semver
  - rollback
---

# Planning: Public API Removal Review Guards

## Overview

| Field | Value |
|-------|-------|
| **Date** | 2026-06-26 |
| **Objective** | Preserve reusable planning and review guardrails for removing deprecated public APIs without silently breaking import surfaces, downstream consumers, documentation promises, or rollback paths. |
| **Outcome** | Planning guidance captured from an implementation-plan review context. The implementation was not executed by this workflow. |
| **Verification** | unverified - derived from planning inputs only; no end-to-end code removal, downstream scan, package install, or CI validation was run for this skill. |

## When to Use

- Planning removal of deprecated public functions, classes, shims, or aliases from a package.
- Reviewing a plan that says "no callers found" based only on a current-checkout grep.
- Removing symbols from a top-level package lazy loader, subpackage `__all__`, module definitions, or compatibility shim.
- Deciding whether migration documentation should keep the only remaining references to removed names.
- Checking whether SemVer, release notes, compatibility policy, or downstream/plugin imports are being assumed rather than verified.
- Designing removal guards that must fail before implementation and pass after implementation.

## Verified Workflow

> **Warning:** This workflow has not been validated end-to-end. Treat it as a hypothesis until CI, package-consumer checks, and reviewer confirmation validate the removal plan. This section is named "Verified Workflow" only to satisfy the marketplace validator; the workflow below is a proposed planning/review checklist.

### Quick Reference

```bash
# 1. Inventory public import surfaces before planning removal.
rg -n "__all__|_LAZY|__getattr__|from .* import|import .* as" <package>/ tests/
rg -n "def (old_symbol|replacement_symbol)\\b|class (OldSymbol|ReplacementSymbol)\\b" <package>/ tests/

# 2. Search callers beyond the obvious module definitions.
rg -n "\\b(old_symbol|OldSymbol)\\b" <package>/ tests/ docs/ scripts/ examples/
rg -n "from <package>(\\.[A-Za-z0-9_]+)? import .*\\b(old_symbol|OldSymbol)\\b" .

# 3. If the project has plugin/downstream checkouts, scan them separately.
#    A no-hit result in the current checkout does not prove no external consumers exist.
rg -n "\\b(old_symbol|OldSymbol)\\b" /path/to/plugins /path/to/downstream 2>/dev/null

# 4. Make stale-reference scans distinguish migration guidance from accidental stale docs.
rg -n "\\b(old_symbol|OldSymbol)\\b" docs/ README* CHANGELOG* COMPATIBILITY* \
  | rg -v "MIGRATION|migration|removed|deprecated|replacement"

# 5. Plan the guard sequence: fail before removal, pass after removal.
python -m pytest tests/unit/validation/test_import_surface.py -q
python -m pytest tests/unit -k "deprecated or import_surface or compatibility" -q
```

### Detailed Steps

1. **Classify the API surface before deleting code.** Record every place the deprecated name is exposed: top-level lazy imports, `__getattr__`, `_LAZY_IMPORTS`/`_LAZY_EXPORTS`, package `__all__`, subpackage re-exports, module definitions, docs, and tests. Removing only the function body while leaving a lazy export or `__all__` entry creates a broken public import path.

2. **Treat current-checkout grep as incomplete evidence.** A local `rg` that finds no runtime users is useful but not conclusive. Plans should say whether downstream repositories, plugin marketplaces, examples, generated docs, or released package consumers were scanned. If they were not scanned, mark the "no callers" claim as a risk for reviewer focus.

3. **Verify policy and release timing directly.** Read the compatibility policy, release notes guidance, and migration docs before asserting that removal is allowed. Do not infer the SemVer target from a tag or from issue text alone. If the release train is unclear, make reviewer confirmation explicit.

4. **Write removal guards before implementation.** The plan should include tests or checks that fail while the deprecated API still exists and pass only after the removal is complete. Useful guard classes include import-surface tests, stale-reference scans, package `dir()`/lazy-loader checks, and targeted docs scans.

5. **Delete deprecation-warning tests instead of preserving obsolete behavior.** Tests whose only purpose is to assert warnings for a removed API should be removed or replaced with tests that assert the symbol is no longer exported. Keeping warning tests after removal accidentally preserves the shim contract.

6. **Scope adjacent APIs deliberately.** If a similarly named or related API has no current hits, do not silently include or exclude it. The plan should state why it is in or out of scope and what evidence supports that boundary.

7. **Allow migration docs intentionally, not accidentally.** Stale-reference checks should fail on accidental references in normal docs/tests but allow explicit migration guidance that teaches users how to replace the removed symbol. The allowlist should be narrow and named in the plan.

8. **Keep a rollback path.** For public API removals, reviewers should be able to see how to restore the shim, lazy export, subpackage re-export, docs entry, and deprecation tests if downstream breakage appears after release.

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
|---------|----------------|---------------|----------------|
| Treating local caller grep as proof | Planned from a current-checkout `rg` that found no runtime users | The search did not cover downstream package consumers, plugins, generated docs, or other checkouts | Phrase it as "no callers in this checkout"; require downstream/plugin scans or reviewer risk callout |
| Trusting line-numbered plan references | Planned edits by specific file:line locations from a prior issue or plan | Line numbers drift as nearby PRs land, so exact locations may become stale | Locate by symbol and surrounding structure at implementation time |
| Assuming policy from issue text | Relied on issue intent and compatibility-policy summaries without re-opening the policy files | Public API removal depends on SemVer/release timing and documented stability promises | Read the compatibility/release/migration sources directly or mark them unverified |
| Preserving deprecation-warning tests | Kept tests that assert the deprecated API still warns | Those tests keep the removed shim alive and contradict the removal objective | Delete or replace warning tests with absence/import-surface guards |
| Blanket stale-reference deletion | Removed every mention of the old symbol from docs | Migration docs may be the only intentional references after removal | Use a narrow migration-doc exception and fail all other stale references |

## Results & Parameters

### Reviewer Focus Checklist

| Risk Area | Review Question | Guardrail |
|-----------|-----------------|-----------|
| Top-level lazy imports | Was the symbol removed from lazy-loader maps, `__getattr__` paths, `__all__`, and cached test expectations? | Import-surface tests and explicit grep of lazy-loader structures |
| Subpackage re-exports | Does any subpackage still expose the removed symbol? | `rg -n "__all__|from .* import" <package>/` plus targeted import tests |
| Module definitions | Was the actual implementation removed, not only hidden from package exports? | Symbol-definition grep across package code |
| Tests | Were deprecation-warning and backward-compat tests deleted or replaced with absence checks? | `pytest -k "deprecated or compatibility or import_surface"` |
| Docs | Are only migration-guide references left? | Stale-reference scan with a narrow migration-doc allowlist |
| External consumers | Were downstream repositories, plugins, generated docs, or examples scanned? | Separate documented scan or explicit reviewer risk callout |
| Release policy | Is the removal aligned with compatibility policy, SemVer, and release notes? | Direct citation to policy/release sources; reviewer confirms uncertain target version |
| Rollback | Can the shim and exports be restored quickly if consumers break? | Rollback section names every removed surface |

### Verified On

| Project | Context | Details |
|---------|---------|---------|
| ProjectHephaestus | Implementation plan for GitHub issue #1420 | Plan proposed removing deprecated public APIs `get_config_value()` and `retry_with_jitter()`. This skill captures planning/review risks only: caller grep scope, line drift, SemVer assumptions, lazy import surfaces, stale migration-doc references, removal guards, and rollback expectations. |
