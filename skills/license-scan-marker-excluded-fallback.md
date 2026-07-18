---
name: license-scan-marker-excluded-fallback
description: "Classify PEP 508 marker-excluded distributed dependencies in a single-leg CI license scan with a fail-closed fallback license map. Use when: (1) a platform- or Python-version-gated dependency is skipped because it is not installable on the CI leg, (2) a scan claims another matrix row will classify a dependency but no such row exists, (3) adding an unreachable dependency or validating fallback-map coverage and values against metadata or NOTICE."
category: ci-cd
date: 2026-07-17
version: "3.0.0"
user-invocable: false
verification: verified-ci
tags: ["license", "pep508", "markers", "fallback", "ci-coverage", "fail-closed", "static-map", "staleness-mitigation", "notice"]
history: license-scan-marker-excluded-fallback.history
---

# License Scan Marker-Excluded Fallback

## Overview

| Field | Value |
|-------|-------|
| **Date** | 2026-07-17 |
| **Objective** | Eliminate license-coverage holes for distributed dependencies excluded from a single CI environment by PEP 508 markers |
| **Outcome** | A single fail-closed fallback-map workflow with source-specific tests for coverage and value staleness |
| **Verification** | verified-ci — ProjectHephaestus issues #1256/#1258, PRs #1303/#1304 |
| **History** | [prior canonical and absorbed source snapshots](./license-scan-marker-excluded-fallback.history) |

## When to Use

- A CI license job runs on one Python/OS combination and `distributed_requirements(None)` reports `installable_now=False` for a distributed dependency
- A dependency is gated by a Python-version or platform marker and `importlib.metadata` cannot inspect it on the current CI leg
- Existing code silently skips the dependency or promises another matrix row will classify it without verifying that row exists
- A new marker-excluded dependency needs an SPDX fallback and a regression guard against missing or stale entries

## Verified Workflow

### Quick Reference

```python
# Keep names and SPDX identifiers in the same representation used by the
# existing compatibility checker. NOTICE is authoritative when the dependency
# is not installed on this CI platform.
FALLBACK_LICENSES: dict[str, list[str]] = {
    "tomli": ["MIT"],
    "tzdata": ["Apache-2.0"],
}

# In the PackageNotFoundError branch for a distributed dependency:
if not installable_now:
    fallback = FALLBACK_LICENSES.get(pkg)
    if fallback is None:
        print(
            f"FATAL: {pkg!r} is marker-excluded and has no fallback license entry",
            file=sys.stderr,
        )
        sys.exit(2)
    ids = fallback
    # Fall through to the existing is_compatible() check.
else:
    raise
```

### Detailed Steps

1. Run `distributed_requirements(None)` in the CI environment and identify every distributed dependency where `installable_now=False`.
2. Derive each fallback SPDX value from the repository's authoritative `NOTICE` entry; do not use `pip show` for a dependency that is deliberately unavailable on this platform.
3. Add the package to one module-level fallback map using the naming and license-ID representation already used by the compatibility checker.
4. Replace only the marker-excluded silent-skip path. Set `ids` from the fallback and fall through to the existing compatibility check; do not duplicate `is_compatible()` in the exception branch.
5. If the package has no fallback entry, print a diagnostic to stderr and exit nonzero. A missing fallback is a CI configuration error, not a warning or a skip.
6. Add tests for the success path, the missing-entry `SystemExit(2)` path, an incompatible fallback value, and completeness of the fallback map for all currently marker-excluded distributed dependencies.
7. Update any module documentation that described the old skip behavior, then verify that the CI job now reports the formerly skipped dependencies.

### Worked Example — ProjectHephaestus single-leg CI

On Python 3.13/Linux, `tomli` (`python_version < '3.11'`) and `tzdata`
(`platform_system == 'Windows'`) are distributed but unavailable. The fallback map uses
`MIT` and `Apache-2.0`, respectively, from `NOTICE`.

- Patch `distributed_requirements` and metadata lookup to prove a known excluded package is classified rather than skipped.
- Patch the map with a synthetic incompatible value such as `GPL-3.0` and assert the ordinary compatibility path reports a violation.
- Assert `excluded - set(FALLBACK_LICENSES)` is empty. Skip that live check only when package metadata is unavailable in the test environment.
- Confirm the `tomli` entry comes from the distributed `toml` runtime extra, not an unrelated development extra.

### Worked Example — Static-map staleness validation

Membership coverage does not prove that an SPDX value is still correct. Add both checks below
when a fallback map is expected to live across dependency updates:

```python
@pytest.mark.parametrize("pkg", FALLBACK_LICENSES)
def test_fallback_values_match_installed_metadata_when_available(pkg):
    if importlib.util.find_spec(pkg) is None:
        pytest.skip(f"{pkg!r} is marker-excluded on this platform")
    assert set(FALLBACK_LICENSES[pkg]) & set(resolve_license(md.metadata(pkg)))


def test_fallback_values_match_notice_per_package():
    notice_text = NOTICE_PATH.read_text(encoding="utf-8")
    for pkg, spdx_ids in FALLBACK_LICENSES.items():
        pkg_lines = [line for line in notice_text.splitlines() if pkg.lower() in line.lower()]
        assert pkg_lines
        for spdx_id in spdx_ids:
            assert any(spdx_id in line for line in pkg_lines)
```

Scope the NOTICE assertion to lines that name the package. A whole-file SPDX search gives false
confidence when another package has the same license (for example, `packaging` and `tzdata` both
use `Apache-2.0`).

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
|---------|----------------|---------------|----------------|
| Add a second Python CI leg | Cover old-Python dependencies through matrix expansion | It increases wall-clock time and still cannot classify a Windows-only dependency on Linux | Use a fallback map for marker dimensions that the chosen CI matrix does not cover |
| Trust a skip message | Continue after claiming another CI row will classify the dependency | The named row did not exist, leaving a permanent coverage hole | Never skip a distributed dependency without classification or a nonzero failure |
| Duplicate the compatibility check in the fallback branch | Validate fallback licenses separately before returning | Later compatibility-rule changes can diverge between the two paths | Set `ids` and fall through to the existing common check |
| Validate only map keys or search all NOTICE text | Assert a package is present or that an SPDX string appears somewhere | A stale or wrong per-package value can pass accidentally | Validate metadata when available and scope NOTICE checks to the target package's lines |

## Results & Parameters

### Required invariants

```text
installable_now=False for a distributed dependency
    => dependency is present in FALLBACK_LICENSES
    => fallback IDs pass through the normal compatibility check

missing fallback entry => stderr diagnostic + exit(2)
```

### Test matrix

| Behavior | Expected result |
|----------|-----------------|
| Known marker-excluded dependency | Classified with fallback IDs; never silently skipped |
| Unknown marker-excluded dependency | `SystemExit(2)` |
| Incompatible fallback ID | Reported by the existing compatibility path |
| New marker-excluded dependency | Completeness lock fails until a fallback entry is added |
| Installed fallback dependency changes license metadata | Metadata cross-check fails |
| NOTICE value drifts or is attached to another package | Per-package NOTICE cross-check fails |

## Verified On

| Project | Context | Details |
|---------|---------|---------|
| ProjectHephaestus | Issues #1256/#1258, PRs #1303/#1304 | Verified in CI; the NOTICE staleness check was corrected to scope SPDX assertions per package. |
