---
name: license-scan-static-fallback-marker-excluded-deps
description: "Static fallback license map for deps excluded by platform/version markers in CI. Use when: (1) a license-scan gate skips marker-gated deps silently, (2) adding a new Windows-only or old-Python-only dep to a project with a single-leg CI license job, (3) extending check_license_compatibility.py to classify unreachable deps."
category: ci-cd
date: 2026-06-13
version: "2.0.0"
user-invocable: false
verification: verified-ci
tags: ["license", "pep508", "markers", "fallback", "ci-coverage", "tomli", "tzdata", "fail-closed", "static-map", "staleness-mitigation"]
history: license-scan-static-fallback-marker-excluded-deps.history
---

# License Scan Static Fallback for Marker-Excluded Deps

## Overview

| Field | Value |
|-------|-------|
| **Date** | 2026-06-13 |
| **Objective** | Classify distributed deps whose platform/version markers exclude them from the single CI leg (Python 3.13 / Linux), preventing silent license-coverage holes |
| **Outcome** | `STATIC_FALLBACK_LICENSES` dict added to scan script; unknown marker-excluded deps now exit(2) instead of silently skipping; staleness-mitigation tests added with correct per-package NOTICE scoping |
| **Verification** | verified-ci — PR #1304 on ProjectHephaestus, all tests pass |
| **History** | v1.0.0 and v1.1.0 archived in `license-scan-static-fallback-marker-excluded-deps.history` |

## When to Use

- A license-scan CI job runs on a single Python version x single OS and silently skips `installable_now=False` deps with a "classified on another matrix row" note — but no such row exists
- Adding a new dep gated by `python_version < 'X'` (e.g. `tomli`) or `platform_system == 'Windows'` (e.g. `tzdata`) to a project with single-leg license CI
- Extending `scripts/check_license_compatibility.py` pattern to ensure all distributed deps are always classified, never silently dropped

## Verified Workflow

### Quick Reference

```python
# In scripts/check_license_compatibility.py, after ALLOWED_EXTRA_COPYLEFT:

STATIC_FALLBACK_LICENSES: dict[str, list[str]] = {
    "tomli": ["MIT"],        # python_version < '3.11'
    "tzdata": ["Apache-2.0"],  # platform_system == 'Windows'; see NOTICE:28
}

# In scan(), replace the silent-skip branch:
# OLD (silent skip -- coverage hole):
#   print(f"note: skipping {pkg!r} -- classified on another CI row")
#   continue
#
# NEW (classify or loud-fail):
fallback = STATIC_FALLBACK_LICENSES.get(pkg)
if fallback is not None:
    ids = fallback  # sets ids, falls through to existing is_compatible() check
else:
    print(f"FATAL: {pkg!r} has no static fallback -- add to STATIC_FALLBACK_LICENSES", file=sys.stderr)
    sys.exit(2)
# NOTE: do NOT duplicate the is_compatible() call here -- set ids=fallback and
# let control fall through to the existing check below. Duplicating the call
# creates a divergence risk when is_compatible() is later extended.
```

### Detailed Steps

1. Identify which deps get `installable_now=False` on the CI leg by running `distributed_requirements(None)` under the CI Python version.
2. For each such dep, look up its SPDX license in `NOTICE` (the authoritative source per the script's own docstring). Confirm line numbers: `tomli` at NOTICE:58 (MIT), `tzdata` at NOTICE:28 (Apache-2.0).
3. Add `STATIC_FALLBACK_LICENSES` dict after `ALLOWED_EXTRA_COPYLEFT` in `check_license_compatibility.py`.
4. Replace the silent-skip `continue` in `scan()` with: set `ids = fallback` and fall through to existing `is_compatible()` call (do not duplicate it).
5. Update module docstring's `FAILS LOUDLY` section to document the new exit path.
6. Add `TestStaticFallback` test class with:
   - `test_tomli_fallback_classifies_correctly` -- patches `distributed_requirements` to return `[("tomli", False)]`, patches `md.metadata` to raise `PackageNotFoundError`, asserts `scan(None) == []`
   - `test_tzdata_fallback_classifies_correctly` -- same pattern for tzdata/Apache-2.0
   - `test_unknown_markered_dep_exits_nonzero` -- unknown dep with no fallback -> `SystemExit(2)`
   - `test_static_fallback_covers_all_markered_out_distributed_deps` -- live coverage assertion: every `installable_now=False` dep in `distributed_requirements(None)` is in `STATIC_FALLBACK_LICENSES`
7. Add **staleness-mitigation tests** — both are required:
   - `test_static_values_match_installed_metadata` — parametrized over `STATIC_FALLBACK_LICENSES` keys; decorated with `@pytest.mark.skipif(not importlib.util.find_spec(pkg), ...)` so it skips when dep not installed (marker excludes it on the CI leg); when installed (e.g. Python 3.10 / Windows), asserts `set(STATIC_FALLBACK_LICENSES[pkg]) & set(resolve_license(md.metadata(pkg)))` is non-empty. Catches license drift when the dep IS available.
   - `test_static_values_match_notice` — runs unconditionally on every Python/platform; reads the `NOTICE` file from the repo root; **scope the SPDX value assertion to lines mentioning the package** (see Critical Gotcha below). Enforces NOTICE as authoritative source without needing the dep installed.
8. Rename existing `test_uninstalled_other_python_dep_skipped_not_failed` -> `test_uninstalled_other_python_dep_with_fallback_classifies_not_fails` (behavior changed: no longer silently skips).

### Critical Gotcha — Scope NOTICE value assertion to per-package lines

The naive `assert spdx_id in notice_text` is **too loose**: the same SPDX ID can appear on a *different* package's NOTICE line, causing false passes.

**Example bug**: `tzdata`'s static fallback is `Apache-2.0`. `packaging` also carries `Apache-2.0` and appears earlier in NOTICE. The full-file check `assert "Apache-2.0" in notice_text` passes even if tzdata's NOTICE entry is wrong or deleted.

```python
# WRONG — too loose: Apache-2.0 from `packaging` satisfies tzdata's check
assert spdx_id in notice_text

# RIGHT — scope to lines mentioning the package
pkg_lines = [line for line in notice_text.splitlines() if pkg.lower() in line.lower()]
assert any(spdx_id in line for line in pkg_lines), (
    f"STATIC_FALLBACK_LICENSES[{pkg!r}] = {spdx_ids!r} but SPDX id "
    f"{spdx_id!r} not found on any NOTICE line mentioning {pkg!r} — "
    "update one to match the other."
)
```

Always scope cross-check assertions to lines associated with the target entity, never to the full file text.

### Copy-paste ready staleness-mitigation tests

```python
class TestStaticFallbackStaleness:
    """Staleness-mitigation tests that catch value drift in STATIC_FALLBACK_LICENSES."""

    @pytest.mark.parametrize("pkg", list(STATIC_FALLBACK_LICENSES.keys()))
    def test_static_values_match_installed_metadata(self, pkg):
        """Skip when dep not installed; assert intersection non-empty when installed."""
        if importlib.util.find_spec(pkg) is None:
            pytest.skip(f"{pkg!r} not installed on this platform/Python (marker excluded)")
        actual_ids = set(resolve_license(md.metadata(pkg)))
        static_ids = set(STATIC_FALLBACK_LICENSES[pkg])
        assert static_ids & actual_ids, (
            f"STATIC_FALLBACK_LICENSES[{pkg!r}] = {static_ids!r} but "
            f"installed metadata reports {actual_ids!r} — update STATIC_FALLBACK_LICENSES "
            "or check if the dep changed its license declaration."
        )

    def test_static_values_match_notice(self):
        """Unconditional: each key and its SPDX values must appear on a NOTICE line mentioning the package."""
        notice_path = Path(__file__).parent.parent.parent / "NOTICE"
        notice_text = notice_path.read_text(encoding="utf-8")
        for pkg, spdx_ids in STATIC_FALLBACK_LICENSES.items():
            # Scope to lines mentioning this package — full-file check is too loose
            # (e.g. "Apache-2.0" appears on packaging's line, would satisfy tzdata's check)
            pkg_lines = [line for line in notice_text.splitlines() if pkg.lower() in line.lower()]
            assert pkg_lines, (
                f"STATIC_FALLBACK_LICENSES key {pkg!r} not found in NOTICE — "
                "add the package to NOTICE or remove it from the fallback map."
            )
            for spdx_id in spdx_ids:
                assert any(spdx_id in line for line in pkg_lines), (
                    f"STATIC_FALLBACK_LICENSES[{pkg!r}] = {spdx_ids!r} but SPDX id "
                    f"{spdx_id!r} not found on any NOTICE line mentioning {pkg!r} — "
                    "update one to match the other."
                )
```

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
|---------|----------------|---------------|----------------|
| Option A: second CI matrix leg | Add python-version: "3.10" leg to license-scan job | Adds ~3 min CI wall-clock; still leaves tzdata/Windows gap (no Windows runner) | A second Python leg handles `tomli` but cannot classify Windows-only deps on Linux CI -- static map is necessary for platform markers |
| Silent skip with note | Print "classified on another CI matrix row" and `continue` | No such row exists; silent skip is a permanent coverage hole for future license changes | Never skip a distributed dep without classifying it; if not installable, classify via static map or exit(2) |
| Validated only keys not values | Coverage test asserted `pkg in STATIC_FALLBACK_LICENSES` but did not cross-check SPDX values | Wrong SPDX values (e.g. `"BSD-3-Clause"` instead of `"MIT"`) would pass the membership test silently | Also validate values: `test_static_values_match_installed_metadata` (when dep available) and `test_static_values_match_notice` (always) |
| NOTICE check too loose: `assert spdx_id in notice_text` | Full-file SPDX check in `test_static_values_match_notice` | `packaging`'s Apache-2.0 entry in NOTICE satisfied tzdata's check — false pass | Scope value assertions to lines mentioning the package name; full-file text search decouples value from key |

## Results & Parameters

**Deps with `installable_now=False` on Python 3.13 / Linux CI:**

| Package | Marker | License (SPDX) | Source |
|---------|--------|----------------|--------|
| `tomli` | `python_version < '3.11'` | `MIT` | NOTICE:58 |
| `tzdata` | `platform_system == 'Windows'` | `Apache-2.0` | NOTICE:28 |

**Key invariant enforced by coverage test:**

```
all pkg: installable_now=False => pkg in STATIC_FALLBACK_LICENSES
```

**Staleness-mitigation invariants (v2.0.0 — per-package scoped):**

```
# Values correct when dep is installed (Python 3.10 / Windows):
set(STATIC_FALLBACK_LICENSES[pkg]) & set(resolve_license(md.metadata(pkg))) != {}

# NOTICE is authoritative; value must appear on a line mentioning the package:
for pkg, spdx_ids in STATIC_FALLBACK_LICENSES.items():
    pkg_lines = [line for line in notice_text.splitlines() if pkg.lower() in line.lower()]
    for spdx_id in spdx_ids:
        assert any(spdx_id in line for line in pkg_lines)
```

**Files changed:**

- `scripts/check_license_compatibility.py`: +`STATIC_FALLBACK_LICENSES` dict, modified `scan()` silent-skip branch (set `ids=fallback`, fall through), updated docstring
- `tests/unit/scripts/test_check_license_compatibility.py`: +`TestStaticFallback` (6 tests: 4 unit + 2 staleness-mitigation with per-package NOTICE scoping), renamed existing test

## Verified On

| Project | Context | Details |
|---------|---------|---------|
| ProjectHephaestus | Issue #1258, PR #1304 | All tests pass. Reviewer-caught fix: `test_static_values_match_notice` scoped to per-package NOTICE lines (commit d9dcde04). |
