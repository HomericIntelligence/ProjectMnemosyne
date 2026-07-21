---
name: security-md-version-sync
description: "Keep SECURITY.md release-support and Python-compatibility statements synchronized with explicit project policy without mistaking release metadata for the support-policy authority. Use when: (1) a release tag or static version changes, (2) a hatch-vcs project has no static version field, (3) a supported-versions table drifts, (4) a guard requires a specific number of supported series, (5) a CI interpreter matrix changes, (6) a tag-coupled SECURITY.md guard should be retired because release cadence no longer defines the support window."
category: documentation
date: 2026-07-20
version: "3.1.0"
user-invocable: false
verification: verified-local
tags: ["security", "versioning", "documentation", "SECURITY.md", "hatch-vcs", "release-tags", "pre-commit", "ci-matrix", "compatibility", "support-policy", "guard-retirement"]
history: security-md-version-sync.history
---

# SECURITY.md Version and Compatibility Sync

## Overview

| Field | Value |
|-------|-------|
| **Date** | 2026-07-20 |
| **Objective** | Keep release-support rows and interpreter-support prose synchronized with explicit support policy, release facts, CI, and justified executable guards |
| **Outcome** | Source-aware workflow covers static and VCS-derived versions; v3.1.0 adds a proposed path for retiring a guard when latest-release identity is no longer the support-policy authority |
| **Verification** | verified-local — the v3.0.0 direct guard plus 19 targeted ProjectHephaestus tests passed; the v3.1.0 guard-retirement workflow is planning-only and unverified |
| **History** | [changelog](./security-md-version-sync.history) |

## When to Use

- A release tag or static package version advances and `SECURITY.md` may still name the previous minor series
- A project uses hatch-vcs or another dynamic version provider and intentionally has no static `[project].version`
- A repository guard rejects stale, missing, or multiple supported-version rows
- The main CI matrix adds or removes a Python version
- `SECURITY.md` or `COMPATIBILITY.md` may be reflecting each other rather than authoritative metadata
- A consistency script equates the latest release tag with the only supported series, but the repository's support policy no longer declares that coupling
- A policy guard, its unit suite, pre-commit hook, and script inventory entry must be retired together without removing independent documentation checks

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

# Before preserving or retiring a tag-coupled guard, locate every policy authority and consumer.
rg -n 'Supported Versions|support(ed)? series|release tag|version consistency' \
  SECURITY.md CONTRIBUTING.md docs scripts tests .pre-commit-config.yaml
```

### Detailed Steps

1. Identify the repository's version authority before editing policy data:
   - For a static package version, read `[project].version` or the repository's declared equivalent.
   - For hatch-vcs or another VCS-derived version, keep static metadata absent and derive the current minor from version-sorted release tags.
2. Identify the support-policy authority separately from the release-version authority. Read the existing guard and tests, but do not treat an implementation mechanism as policy evidence by itself. Preserve its accepted table shape only when repository policy explicitly says support follows the latest release series.
3. Compare the canonical current minor `X.Y` with the supported and end-of-life rows in `SECURITY.md`.
4. Make the smallest change at the correct layer. For ordinary drift, edit policy data without broadening the guard. When the task explicitly decouples support policy from release tags, retire the tag-coupled guard and all of its wiring rather than weakening it into a vague check.
5. Run the guard directly against the real repository and available tags. A `--help` smoke test does not prove the policy is aligned.
6. Run the guard's focused unit suite, including aligned, drifted, missing-row, and multiple-row cases.
7. Run the affected script smoke test and the configured pre-commit hook when present.
8. Report `verified-local` until CI confirms the branch; only then promote the evidence level to `verified-ci`.

### Retiring a tag-coupled support guard

> **Warning:** This workflow is proposed from ProjectHephaestus issue #2330 and has not been
> implemented or validated end-to-end. The live tree still contained the script and hook at capture
> time. Treat this as `unverified` until focused tests, the full suite, and CI pass after removal.

1. State the policy change explicitly: the latest release tag identifies released software, but it
   does not automatically define which release series receive security fixes.
2. Search the guard symbol and hook ID across scripts, tests, pre-commit configuration, docs, smoke
   inventories, and comments. A removal is incomplete while any invocation or claimed enforcement
   remains.
3. Delete the tag-coupled checker, its dedicated unit suite, its pre-commit hook, and its script
   inventory entry in one change.
4. Preserve independent checks. For example, a guard rejecting hard-coded `As of YYYY-MM-DD` dates
   in `SECURITY.md` can remain because it enforces freshness hygiene without deriving support policy
   from the latest Git tag.
5. Verify absence by parsing `.pre-commit-config.yaml` and asserting the old hook ID is gone, then
   search the repository for the script name. Run documentation, pre-commit, and full test suites.
6. Update this skill's verification only after the removal lands and CI proves the repository no
   longer depends on the deleted checker.

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
| Treat the latest release tag as the support-policy authority | Required `SECURITY.md` to name exactly the newest minor because that minor was latest | Release identity and support lifetime are different decisions; the coupling forces policy churn on every tag and prevents intentional overlap or independent support windows | Derive support rows from explicit security policy. Keep a tag-coupled guard only when that coupling is itself the declared policy; otherwise retire the checker and all wiring |

## Results & Parameters

| Source | Authority |
|--------|-----------|
| Static `[project].version` | Canonical release only when the repository declares a static version |
| Version-sorted release tags | Canonical release identity for hatch-vcs/VCS-derived projects; not automatically the support-window authority |
| Explicit repository security/support policy | Canonical supported-series and end-of-life decisions |
| Repository consistency guard and its tests | Enforcement mechanism only when it reflects the declared support policy |
| `pyproject.toml` `requires-python` | Canonical install-time Python floor |
| Main CI matrices | Canonical tested interpreter range |
| Development environment constraint | Corroborating signal only |
| `SECURITY.md` and `COMPATIBILITY.md` | Policy outputs to validate, not independent sources of truth |

### Acceptance checks

- The supported-version table matches explicit support policy; matching the current canonical minor is required only when policy says it is supported.
- If a tag-coupled guard remains policy-backed, the supported rows match it and its direct,
  focused, and smoke tests pass against real tags or metadata.
- If that guard is retired, its script, hook ID, dedicated tests, inventory entry, and claimed
  enforcement references are all absent while independent `SECURITY.md` checks still pass.
- If interpreter prose changed, both ends of the CI-tested Python range are present and attributable.

ProjectHephaestus's observed commands and outputs are preserved in
[session notes](./security-md-version-sync.notes.md).

## Verified On

| Project | Context | Details |
|---------|---------|---------|
| ProjectHephaestus | `v0.10.*` supported-series correction, commit `31ed68e` | Direct guard, 18 guard unit tests, and 1 filtered smoke test passed locally on 2026-07-20; [notes](./security-md-version-sync.notes.md) |
| ProjectHephaestus | Issue #47, PR #76 | Supported release table updated and pre-commit verified |
| ProjectHephaestus | Issue #1204 | Python-range provenance prose verified with pre-commit |
| ProjectHephaestus | Issue #2330 planning record | Proposed retirement of the tag-coupled checker, unit suite, hook, and inventory entry while retaining the independent no-hardcoded-date guard. Unverified: no removal or CI run occurred in this learning session. |
