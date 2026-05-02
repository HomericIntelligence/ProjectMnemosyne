# Session Notes: mypy-roadmap-closure (2026-02-24)

## Session Context

- Project: ProjectScylla
- Trigger: User asked to "analyze the rest of #687 and finish the rest of the items so we can close it"
- Starting state: Phases 1-6 done (DISABLED_ERROR_CODES=[]), tracking infra just removed in PR #1082

## Key Discovery: `--enable-error-code` Doesn't Override Module Overrides

This was the critical failed attempt of the session.

Ran per-code checks on tests/ like:
```bash
for code in operator arg-type index ...; do
  count=$(pixi run mypy tests/ --enable-error-code "$code" 2>&1 | grep "error:" | wc -l)
  echo "$code: $count"
done
```

All returned 0, leading to the (wrong) conclusion that the tests/ override was dead weight.

Removed the override in pyproject.toml, ran mypy -- got 106 errors.

The `--enable-error-code` flag re-enables globally-disabled codes (via `disable_error_code = [...]` at the root level) but does NOT override a `[[tool.mypy.overrides]]` module section. The module section is applied *after* the global flags, so it still suppresses those codes even when you try to re-enable them via CLI.

**Correct approach**: To audit a `[[tool.mypy.overrides]]` section, you must edit `pyproject.toml` directly (comment out the override block), run mypy, then restore it.

## Why `warn_unused_ignores` Cascades Into Override Suppressors

When `warn_unused_ignores = true` is set globally:
1. mypy sees `# type: ignore[method-assign]` in tests/unit/
2. The `[[tool.mypy.overrides]]` section suppresses `method-assign` for `tests.*`
3. Since method-assign is suppressed, the explicit `# type: ignore` comment is "unused"
4. mypy emits `unused-ignore` for the comment itself

Fix: add `"unused-ignore"` to the same override block. This suppresses the circular warning until the override is fully removed.

## Issue Triage Summary

| Issue | Action | Reason |
| ------- | -------- | -------- |
| #952 | Closed | Scope was scylla/ suppressed errors -- all fixed |
| #1001 | Closed | DISABLED_ERROR_CODES=[]. No "next code" globally |
| #1002 | Closed | Tracking infra removed in #1082 |
| #1004 | Closed | scripts/ at 0; tests/ work in #940 |
| #951 | Kept open | Specific call-overload bug, still relevant for tests/ |
| #940 | Updated | Corrected from "0 errors" to 106 real errors |
| #687 | Closed | Roadmap done; remaining work individually tracked |

## New Issues Filed

- #1083: Phase 7a -- `check_untyped_defs` (26 errors, all in scripts/export_data.py)
- #1084: Phase 7b -- `disallow_untyped_defs` (32 missing annotations)
- #1085: Phase 7c -- `warn_return_any` (58 errors)
- #1086: Phase 9 -- `disallow_incomplete_defs` + `disallow_any_generics` (94 errors)

## PRs

- #1082: Remove mypy tracking infrastructure (MYPY_KNOWN_ISSUES.md, check_mypy_counts.py, etc.)
- #1087: Enable warn_redundant_casts + warn_unused_ignores; close #687
