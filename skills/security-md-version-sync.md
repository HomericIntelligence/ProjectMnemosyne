---
name: security-md-version-sync
description: "Keep SECURITY.md release-support and Python-compatibility statements synchronized with the project's actual version authority and executable guards. Use when: (1) a release tag or static version changes, (2) a hatch-vcs project has no static version field, (3) a supported-versions table drifts, (4) a guard requires a specific number of supported series, (5) a CI interpreter matrix changes."
category: documentation
date: 2026-07-20
version: "3.0.0"
user-invocable: false
verification: verified-local
tags: ["security", "versioning", "documentation", "SECURITY.md", "hatch-vcs", "release-tags", "pre-commit", "ci-matrix", "compatibility"]
history: security-md-version-sync.history
---

# SECURITY.md Version and Compatibility Sync

## Overview

| Field | Value |
|-------|-------|
| **Date** | 2026-07-20 |
| **Objective** | Keep release-support rows and interpreter-support prose synchronized with the project's declared version authority, release tags, CI, and executable policy guards |
| **Outcome** | Source-aware workflow covers static versions and VCS-derived versions without overriding repository-specific support-series rules |
| **Verification** | verified-local — direct guard plus 19 targeted ProjectHephaestus tests passed; CI validation pending |
| **History** | [changelog](./security-md-version-sync.history) |

## When to Use

- A release tag or static package version advances and `SECURITY.md` may still name the previous minor series
- A project uses hatch-vcs or another dynamic version provider and intentionally has no static `[project].version`
- A repository guard rejects stale, missing, or multiple supported-version rows
- The main CI matrix adds or removes a Python version
- `SECURITY.md` or `COMPATIBILITY.md` may be reflecting each other rather than authoritative metadata

## Verified Workflow

> **Verification scope:** Verified locally only — CI validation pending.

### Quick Reference

```bash
# Discover whether version authority is static metadata or VCS tags.
rg -n 'dynamic = \["version"\]|^version\s*=|source\s*=\s*"vcs"' pyproject.toml
git tag --list 'v*' --sort=-version:refname | head

# Inspect policy and executable enforcement before choosing a table shape.
sed -n '/Supported Versions/,+8p' SECURITY.md
rg -n 'SECURITY\.md|supported.*version|version.*consisten' scripts .pre-commit-config.yaml tests

# ProjectHephaestus example; use the repository's equivalent guard and tests.
python3 scripts/check_security_version_consistency.py
uv run pytest tests/unit/scripts/test_check_security_version_consistency.py --no-cov -q
uv run pytest 'tests/unit/scripts/test_scripts_smoke.py::test_script_help_exits_zero' \
  -k check_security_version_consistency --no-cov -q
```

### Detailed Steps

1. Identify the repository's version authority before editing policy data:
   - For a static package version, read `[project].version` or the repository's declared equivalent.
   - For hatch-vcs or another VCS-derived version, keep static metadata absent and derive the current minor from version-sorted release tags.
2. Read the existing policy guard and its unit tests. Treat their accepted table shape as an executable repository invariant unless the task explicitly changes policy.
3. Compare the canonical current minor `X.Y` with the supported and end-of-life rows in `SECURITY.md`.
4. Make the smallest policy-data edit. Do not modify a correct guard or broaden test scope merely because the document drifted.
5. Run the guard directly against the real repository and available tags. A `--help` smoke test does not prove the policy is aligned.
6. Run the guard's focused unit suite, including aligned, drifted, missing-row, and multiple-row cases.
7. Run the affected script smoke test and the configured pre-commit hook when present.
8. Report `verified-local` until CI confirms the branch; only then promote the evidence level to `verified-ci`.

### Worked Example — VCS-derived single supported series

Suppose hatch-vcs derives the package version from tags, the latest version-sorted tag is
`v0.10.0`, and the guard accepts exactly one supported series. The policy data is:

```markdown
| Version | Supported      |
|---------|----------------|
| 0.10.x  | Supported      |
| < 0.10  | End of life    |
```

Do not add a static `version` field, preserve `0.9.x` as a second supported row, or edit a
correct guard. Those actions conflict with the repository's version model or executable policy.

### Worked Example — Static version with an explicit overlap policy

If the repository stores a static `X.Y.Z` version and explicitly supports the current and
preceding minor series, a two-series table can be correct:

```markdown
| Version   | Supported   |
|-----------|-------------|
| X.Y.x     | Supported   |
| X.(Y-1).x | Supported   |
| < X.(Y-1) | End of life |
```

The overlap is a project policy, not a universal default. Confirm it in the guard, release
policy, or tests before retaining the previous series.

### Python support provenance prose

For interpreter policy, derive the install-time floor from `requires-python` and the tested
range from all relevant CI matrices. Treat development-environment constraints as
corroborating information, and verify `SECURITY.md` and `COMPATIBILITY.md` independently.

```markdown
Project supports **Python 3.10–3.13** (`requires-python = ">=3.10"` in
`pyproject.toml`; CI exercises 3.10, 3.11, 3.12, and 3.13). See
[COMPATIBILITY.md](COMPATIBILITY.md) for the full compatibility policy.
```

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
|---------|----------------|---------------|----------------|
| Assume `[project].version` always exists | Used static package metadata as the universal release source | hatch-vcs projects intentionally declare `dynamic = ["version"]` and derive versions from tags | Discover the repository's version model first; do not introduce a static version field |
| Sort tags as plain text | Compared `v0.10.0` and `v0.9.9` lexicographically | Lexical ordering can place `0.9` after `0.10` | Use version-aware sorting such as `git tag --sort=-version:refname` |
| Keep the previous minor supported by default | Applied a generic two-series table | Some guards require exactly one supported series | Read the executable guard and tests before choosing the table shape |
| Edit the guard and tests with the policy row | Expanded a documentation-drift fix into enforcement changes | The existing guard already encoded the intended invariant | Change policy data only when enforcement is already correct |
| Run only the script help smoke test | Verified CLI startup but not tag-to-policy consistency | `--help` exits before evaluating the repository state | Run the real guard first, then focused unit and smoke tests |
| Read only one CI workflow | Treated a single job as the entire interpreter support matrix | Auxiliary jobs may use a narrower subset | Inspect all workflow files before stating a tested range |
| Trust `COMPATIBILITY.md` | Used one policy document to validate another | Both documents can drift together | Compare both with metadata, tags, and CI independently |
| Run an incompatible formatter unconditionally | Ran all hooks on a host lacking the formatter's runtime requirements | The formatter failed for the host, not the documentation | Skip only a known incompatible hook and baseline unrelated failures on main |

## Results & Parameters

| Source | Authority |
|--------|-----------|
| Static `[project].version` | Canonical release only when the repository declares a static version |
| Version-sorted release tags | Canonical release series for hatch-vcs/VCS-derived projects |
| Repository consistency guard and its tests | Executable table-shape and alignment invariant |
| `pyproject.toml` `requires-python` | Canonical install-time Python floor |
| Main CI matrices | Canonical tested interpreter range |
| Development environment constraint | Corroborating signal only |
| `SECURITY.md` and `COMPATIBILITY.md` | Policy outputs to validate, not independent sources of truth |

### Acceptance checks

- The current canonical minor appears in the supported-version table.
- The number and range of supported rows match the repository's explicit policy guard.
- The direct consistency guard passes against real tags or metadata.
- Focused tests cover aligned, drifted, missing, and multiple-row policies.
- The affected script smoke test passes.
- If interpreter prose changed, both ends of the CI-tested Python range are present and attributable.

ProjectHephaestus's observed commands and outputs are preserved in
[session notes](./security-md-version-sync.notes.md).

## Verified On

| Project | Context | Details |
|---------|---------|---------|
| ProjectHephaestus | `v0.10.*` supported-series correction, commit `31ed68e` | Direct guard, 18 guard unit tests, and 1 filtered smoke test passed locally on 2026-07-20; [notes](./security-md-version-sync.notes.md) |
| ProjectHephaestus | Issue #47, PR #76 | Supported release table updated and pre-commit verified |
| ProjectHephaestus | Issue #1204 | Python-range provenance prose verified with pre-commit |
