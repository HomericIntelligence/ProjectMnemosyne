---
name: security-md-version-sync
description: "Keep SECURITY.md release-support and Python-compatibility statements synchronized with canonical project metadata and CI. Use when: (1) a release version changes, (2) a supported-versions table is stale, (3) SECURITY.md states only a Python floor or omits the tested ceiling, (4) policy prose lacks pyproject.toml provenance or a COMPATIBILITY.md reference, (5) a CI matrix changes."
category: documentation
date: 2026-07-17
version: "2.0.0"
user-invocable: false
verification: verified-precommit
tags: ["security", "versioning", "documentation", "SECURITY.md", "pyproject.toml", "ci-matrix", "compatibility"]
history: security-md-version-sync.history
---

# SECURITY.md Version and Compatibility Sync

## Overview

| Field | Value |
|-------|-------|
| **Date** | 2026-07-17 |
| **Objective** | Keep release-support rows and interpreter-support prose in SECURITY.md accurate and attributable |
| **Outcome** | One verified documentation workflow with separate table and policy-prose branches |
| **Verification** | verified-precommit — ProjectHephaestus issues #47 and #1204 |
| **History** | [absorbed Python-range planning source](./security-md-version-sync.history) |

## When to Use

- A release version in `pyproject.toml` changes and the SECURITY.md supported-version rows may be stale
- SECURITY.md gives only a Python minimum, without the CI-tested ceiling or canonical source reference
- The main CI matrix adds or removes a Python version
- SECURITY.md or COMPATIBILITY.md may be reflecting each other rather than authoritative metadata

## Verified Workflow

### Quick Reference

```bash
# Release series and install-time Python floor
grep -n 'version\|requires-python' pyproject.toml

# Tested interpreter range and development constraint
rg -n 'python-version' .github/workflows
grep -n 'python' pixi.toml | head -5

# Existing policy statements
grep -A6 'Supported Versions' SECURITY.md
grep -n 'Python\|pyproject.toml\|COMPATIBILITY.md' SECURITY.md COMPATIBILITY.md

# Documentation validation; skip an environment-incompatible formatter if necessary.
SKIP=mojo-format pre-commit run --all-files
```

### Detailed Steps

1. Read `[project].version` and `requires-python` in `pyproject.toml`. They are the canonical release series and install-time Python floor.
2. Inspect all CI workflow matrices to establish the tested interpreter floor and ceiling. A narrower auxiliary job does not redefine the main test matrix.
3. Inspect the development-environment Python constraint as corroborating information, not as the canonical policy source.
4. Compare SECURITY.md and COMPATIBILITY.md independently with the sources above. Neither document proves the other is current.
5. Update the matching branch or branches below, then run formatting and flexible positive/negative text checks.

### Worked Example — Supported release table

When the release series changes, update the table immediately below the supported-versions heading:

```markdown
| Version | Supported |
|---------|-----------|
| X.Y.x   | Yes       |
| X.(Y-1).x | Yes     |
| < X.(Y-1) | No       |
```

Keep the preceding release supported unless it is explicitly end-of-life. Use `X.Y.x` notation
and commit the documentation update with the release change.

### Worked Example — Python support provenance prose

When the policy prose is floor-only or lacks attribution, surface the entire tested range and its
sources above the table:

```markdown
Project supports **Python 3.10–3.13** (`requires-python = ">=3.10"` in
`pyproject.toml`; CI exercises 3.10, 3.11, 3.12, and 3.13). See
[COMPATIBILITY.md](COMPATIBILITY.md) for the full compatibility policy.
```

Verify each endpoint separately rather than using an order-dependent multi-version regex. The
prose must identify the `pyproject.toml` field and cross-link COMPATIBILITY.md; do not update only
the release table when the interpreter policy is also stale.

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
|---------|----------------|---------------|----------------|
| Read only one CI workflow | Treated a single job as the entire support matrix | Auxiliary jobs may use a narrower subset | Inspect all workflow files before stating a tested range |
| Trust COMPATIBILITY.md | Used one policy document to validate the other | Both documents can drift together | Compare both with metadata and CI independently |
| Use an order-dependent grep | Required version endpoints to occur in a fixed textual order | Equivalent wording caused false failures | Check floor and ceiling separately |
| Run an incompatible formatter unconditionally | Ran all hooks on a GLIBC-mismatched host | `mojo-format` failed for the host, not the docs | Skip only the known incompatible hook and baseline unrelated failures on main |

## Results & Parameters

| Source | Authority |
|--------|-----------|
| `pyproject.toml` `[project].version` | Canonical release series |
| `pyproject.toml` `requires-python` | Canonical install-time floor |
| Main CI matrix | Canonical tested range |
| `pixi.toml` Python constraint | Development-environment signal only |
| SECURITY.md and COMPATIBILITY.md | Policy outputs to validate, not sources of truth |

### Acceptance checks

- The current release series appears in the supported-version table.
- SECURITY.md mentions both ends of the CI-tested Python range.
- The prose names `pyproject.toml` and links COMPATIBILITY.md.
- Stale floor-only text is absent.
- Markdown and repository documentation hooks pass.

## Verified On

| Project | Context | Details |
|---------|---------|---------|
| ProjectHephaestus | Issue #47, PR #76 | Supported release table updated and pre-commit verified. |
| ProjectHephaestus | Issue #1204 | Python-range provenance prose verified with pre-commit. |
