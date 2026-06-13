---
name: license-scan-marker-excluded-fallback
description: "Documents how to fix CI license-scan blind spots for PEP 508 marker-excluded deps. Use when: (1) CI scans licenses on a single Python/OS matrix leg and silently skips marker-gated deps, (2) a dep has platform_system or python_version markers that exclude the CI environment, (3) you need fail-closed behavior for ungated deps, (4) adding a new gated dep and need a coverage-completeness lock test."
category: ci-cd
date: 2026-06-13
version: "2.0.0"
user-invocable: false
verification: verified-ci
tags: ["license", "pep508", "markers", "fallback", "ci-coverage", "tomli", "tzdata", "fail-closed", "coverage-completeness", "patch-dict"]
history: license-scan-marker-excluded-fallback.history
---

# License Scan Marker-Excluded Fallback

## Overview

| Field | Value |
|-------|-------|
| **Date** | 2026-06-13 |
| **Objective** | Fix CI license-scan blind spot for PEP 508 marker-excluded distributed deps (`tomli`, `tzdata`) |
| **Outcome** | `FALLBACK_LICENSES` dict added to scan script; marker-excluded deps now classified from authoritative literals; unknown gated deps cause `sys.exit(2)` instead of silent skip; coverage-completeness lock test prevents future regressions |
| **Verification** | verified-ci — PR #1303 on ProjectHephaestus, all 29 tests pass (4 skipped: dep not installed locally, expected) |
| **History** | v1.0.0 archived in `license-scan-marker-excluded-fallback.history` |

## When to Use

- A CI license-scan job runs on a single Python version/OS matrix leg (e.g., Python 3.13 / Ubuntu 24.04)
- Some distributed deps have PEP 508 markers that exclude the CI environment (e.g., `python_version < '3.11'`, `platform_system == 'Windows'`)
- Those deps are silently skipped with a note claiming "another CI row will classify them" — but no such row exists
- A new gated dep is added to `pyproject.toml` and you need to ensure it gets license-classified
- The `_installable_in_current_env` function returns `False` for a dep that is part of the distributed package

## Verified Workflow

### Quick Reference

```python
# In scripts/check_license_compatibility.py, after ALLOWED_EXTRA_COPYLEFT:

FALLBACK_LICENSES: dict[str, list[str]] = {
    "tomli": ["MIT"],        # NOTICE: "toml extra / tomli  MIT"
    "tzdata": ["Apache-2.0"],  # NOTICE: "tzdata  Apache-2.0"
}

# In scan(), when PackageNotFoundError fires with installable_now=False:
#   Replace the silent-skip-with-note block entirely.
fallback = FALLBACK_LICENSES.get(pkg)
if fallback is None:
    print(
        f"FATAL: distributed dependency {pkg!r} is not installable "
        "in this environment (marker excludes it) AND has no entry in "
        "FALLBACK_LICENSES. Add its NOTICE-documented license to "
        "FALLBACK_LICENSES in scripts/check_license_compatibility.py.",
        file=sys.stderr,
    )
    sys.exit(2)
print(
    f"note: {pkg!r} not installable here (marker excluded); "
    f"classifying from FALLBACK_LICENSES: {fallback}",
    file=sys.stderr,
)
ids = fallback
# falls through to the existing is_compatible() check -- do NOT duplicate it
```

### Detailed Steps

1. **Identify marker-excluded distributed deps**: Run `distributed_requirements(None)` and collect entries where `installable_now=False`. In ProjectHephaestus, these are `tomli` (`python_version < '3.11'`) and `tzdata` (`platform_system == 'Windows'`) on Python 3.13 / Linux.

2. **Look up licenses from NOTICE file**: Check the `NOTICE` file for the license of each excluded dep. Do NOT rely on `pip show` — the dep is not installed. NOTICE is the authoritative source per the script's own docstring.

3. **Add `FALLBACK_LICENSES` dict**: Add a module-level `FALLBACK_LICENSES: dict[str, list[str]]` constant after `ALLOWED_EXTRA_COPYLEFT` in `check_license_compatibility.py`, keyed by package name, values as SPDX identifiers.

4. **Replace silent-skip branch in `scan()`**: When `PackageNotFoundError` fires for an `installable_now=False` dep, look up the fallback. Set `ids = fallback` and fall through to the existing `is_compatible()` call. Do NOT duplicate `is_compatible()` in the branch — falling through reuses the same code path and avoids divergence risk.

5. **Call `sys.exit(2)` when no fallback entry exists**: Fail closed. `exit(2)` (not a warning, not a skip) breaks CI loudly when a gated dep has no entry.

6. **Add `TestLoudFailure` test class** with three targeted tests:
   - `test_marker_excluded_dep_classified_from_fallback` — `installable_now=False` + dep in `FALLBACK_LICENSES` → classified, not skipped
   - `test_marker_excluded_dep_not_in_fallback_exits_nonzero` — `installable_now=False` + dep NOT in map → `SystemExit(2)`
   - `test_marker_excluded_dep_with_incompatible_fallback_is_violation` — `FALLBACK_LICENSES` entry with incompatible license (e.g., `GPL-3.0`) surfaces as a violation

7. **Add `TestFallbackLicenses` test class** with a coverage-completeness lock test:
   - `test_fallback_covers_all_marker_excluded_deps` — calls `distributed_requirements(None)` to get all `installable_now=False` deps and asserts every one is in `FALLBACK_LICENSES`

8. **Run CI**: Confirm the license-scan job passes on Python 3.13 / Ubuntu 24.04 and that previously-skipped deps now appear in the scan output.

### Copy-paste ready tests

```python
# TestLoudFailure -- three targeted tests:

def test_marker_excluded_dep_classified_from_fallback(self):
    with patch("check_license_compatibility.distributed_requirements", return_value=[("tomli", False)]):
        with patch("check_license_compatibility.md.metadata", side_effect=md.PackageNotFoundError("tomli")):
            result = scan(None)
    assert result == []

def test_marker_excluded_dep_not_in_fallback_exits_nonzero(self):
    with patch("check_license_compatibility.distributed_requirements", return_value=[("unknown-gated-pkg", False)]):
        with patch("check_license_compatibility.md.metadata", side_effect=md.PackageNotFoundError("unknown-gated-pkg")):
            with pytest.raises(SystemExit) as exc:
                scan(None)
    assert exc.value.code == 2

def test_marker_excluded_dep_with_incompatible_fallback_is_violation(self):
    with patch.dict("check_license_compatibility.FALLBACK_LICENSES", {"bad-pkg": ["GPL-3.0"]}):
        with patch("check_license_compatibility.distributed_requirements", return_value=[("bad-pkg", False)]):
            with patch("check_license_compatibility.md.metadata", side_effect=md.PackageNotFoundError("bad-pkg")):
                result = scan(None)
    assert result == [("bad-pkg", ["GPL-3.0"])]

# TestFallbackLicenses -- coverage-completeness lock:

def test_fallback_covers_all_marker_excluded_deps(self):
    try:
        excluded = {name for name, installable_now in distributed_requirements(None) if not installable_now}
    except (md.PackageNotFoundError, SystemExit):
        pytest.skip("HomericIntelligence-Hephaestus not installed in this env")
        return
    missing = excluded - set(FALLBACK_LICENSES)
    assert not missing, (
        f"Distributed deps excluded from this interpreter have no FALLBACK_LICENSES "
        f"entry: {sorted(missing)}. Add each to FALLBACK_LICENSES in "
        "scripts/check_license_compatibility.py with its NOTICE-documented license."
    )
```

### Patching notes

- `patch.dict("check_license_compatibility.FALLBACK_LICENSES", {"bad-pkg": ["GPL-3.0"]})` injects synthetic entries without modifying the real map — safe for isolation.
- `test_tomli_in_fallback_on_py311_plus` skips on Python < 3.11 (where tomli is installable and the fallback is not exercised), runs on 3.11+ where tomli is marker-excluded.
- `tzdata` is always excluded on Linux so the completeness test always exercises at least tzdata in CI.

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
|---------|----------------|---------------|----------------|
| CI matrix expansion for `tzdata` | Add a Python 3.10 CI leg to cover `tomli` | Covers `tomli` but still cannot classify `tzdata` (`platform_system == 'Windows'`) on Linux CI; a Windows runner would be disproportionate for one dep | A single static fallback map is simpler and more maintainable than matrix expansion for platform-specific deps |
| Trusting the skip message | Rely on the original `scan()` code which printed "classified on the matching CI matrix row" | No such matching CI row existed — the promise was hollow; the dep was silently unclassified | Never rely on a skip message that claims "another row will handle it" without verifying the other row exists |

## Results & Parameters

### Known Gated Deps (ProjectHephaestus, as of 2026-06-13)

| Package | Marker | SPDX License | Source |
|---------|--------|--------------|--------|
| `tomli` | `python_version < '3.11'` | `MIT` | NOTICE (toml extra / tomli MIT) |
| `tzdata` | `platform_system == 'Windows'` | `Apache-2.0` | NOTICE (tzdata Apache-2.0) |

### Key invariant enforced by coverage-completeness test

```
all pkg: installable_now=False => pkg in FALLBACK_LICENSES
```

This test runs in CI on every future PR, so a new gated dep added without a fallback entry fails immediately.

### Critical gotcha — `tomli` extra placement

The `tomli` dep that matters is in the `toml` **runtime** extra, NOT the `dev` extra. The `dev` extra copy is excluded from the distributed package. Confusing these two is an easy mistake during review.

### Files changed

- `scripts/check_license_compatibility.py`: +`FALLBACK_LICENSES` dict after `ALLOWED_EXTRA_COPYLEFT`; replaced silent-skip branch with fallback lookup + fall-through; updated module docstring `FAILS LOUDLY` section
- `tests/unit/scripts/test_check_license_compatibility.py`: +`TestLoudFailure` (3 tests) and `TestFallbackLicenses` (1 coverage-completeness lock test); renamed `test_uninstalled_other_python_dep_skipped_not_failed` to `test_uninstalled_other_python_dep_with_fallback_classifies_not_fails`

## Verified On

| Project | Context | Details |
|---------|---------|---------|
| ProjectHephaestus | Issue #1256, PR #1303 | All 29 tests pass (4 skipped: dep not installed locally, expected and intentional). Commit signature verified. All policy checks pass. |
