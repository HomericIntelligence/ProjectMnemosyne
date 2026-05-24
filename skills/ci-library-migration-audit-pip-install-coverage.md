---
name: ci-library-migration-audit-pip-install-coverage
description: "After migrating a Python helper from a local module to a pip-installed library (e.g. `from common import X` → `from hephaestus.utils import X`), audit every CI job that invokes the migrated scripts to confirm each job either (a) installs the library via `pip install`, or (b) routes the invocation through an env-manager (`pixi run`, `poetry run`, `uv run`) that already has it. Use when: (1) a library migration PR was green in pre-commit/local but CI jobs crash with `ModuleNotFoundError: No module named '<lib>'`, (2) a workflow step calls `python3 scripts/...` directly even though the job ran `setup-pixi`/`setup-poetry` (env-manager bypass), (3) a workflow YAML pins `<lib>>=X,<Y` in a `pip install` line that has drifted from the version pin in `pixi.toml`/`pyproject.toml`."
category: ci-cd
date: 2026-05-24
version: "1.0.0"
user-invocable: false
verification: verified-ci
tags:
  - python
  - library-migration
  - pip-install
  - pixi
  - github-actions
  - module-not-found
  - env-manager-bypass
  - version-pin-drift
  - single-source-of-truth
---

# CI Library Migration Audit: pip install Coverage and Env-Manager Routing

## Overview

| Field | Value |
|-------|-------|
| **Date** | 2026-05-24 |
| **Objective** | After migrating Python call sites from a local helper module to a pip-installed library, prevent CI breakage by auditing every workflow job that invokes the migrated scripts |
| **Outcome** | 5 broken CI jobs on HomericIntelligence/ProjectOdyssey PR #5445 fixed in commit 702a5a2e — all checks SUCCESS after audit-driven fix |
| **Verification** | verified-ci |

## When to Use

- A migration PR replaced `from common import X` (or similar local-module helpers) with `from <package> import X` from a pip-installed library, and CI jobs now crash with `ModuleNotFoundError: No module named '<package>'`.
- A GitHub Actions job sets up `pixi`/`poetry`/`uv` but invokes the migrated script via plain `python3 scripts/...` (silently bypassing the env-manager).
- A workflow YAML still pins the old version (`>=0.7.0,<1`) in a `pip install` line while `pixi.toml`/`pyproject.toml` has been bumped (`>=0.9.0,<1`).
- Pre-merge: about to merge a library-migration PR and want a single grep query to catch the failure-prone jobs.
- Post-merge incident response: triaging a wave of `ModuleNotFoundError` failures across several seemingly unrelated workflows.

## Verified Workflow

### Quick Reference

```bash
# 1. Find every workflow step that runs a python script that may import the new library,
#    excluding invocations already routed through an env-manager.
grep -rnE "python3? .*scripts/" .github/workflows/ \
  | grep -vE "pixi run|poetry run|uv run"

# 2. For each hit, open the surrounding job and confirm one of:
#    (a) the job has `pip install "<package>>=X,<Y"` BEFORE the script runs, or
#    (b) rewrite the step to use the env-manager:  pixi run python3 scripts/...

# 3. Cross-check every pinned version against the single source of truth (pixi.toml):
grep -rnE '<package>[><=!~]' .github/workflows/   # workflow pins
grep -nE  '<package>[><=!~]' pixi.toml             # canonical pin
# Bump every workflow pin to match pixi.toml.
```

Fix shape — pick ONE per job:

```yaml
# Option A (lightweight job, only needs this one library)
- name: Install dependencies
  run: pip install "homericintelligence-hephaestus>=0.9.0,<1"
- name: Run script
  run: python3 scripts/validate_test_coverage.py

# Option B (job already runs setup-pixi — use the env it set up)
- uses: prefix-dev/setup-pixi@v0.9.6
- name: Run script
  run: pixi run python3 scripts/validate_readme_commands.py   # NOT `python3 scripts/...`
```

### Detailed Steps

1. **Inventory the migrated scripts.** From the migration diff, list every `scripts/*.py` (or equivalent) that gained a new third-party import. These are the call sites that will trigger the failure.

2. **Map scripts → workflow jobs.** For each script, find every workflow step that invokes it:
   ```bash
   grep -rn "scripts/<name>.py" .github/workflows/
   ```
   Don't trust memory; CI repos accumulate jobs and a single script is often invoked from 2–5 workflows.

3. **Classify each invocation site** as one of:
   - **OK — env-managed**: step is `pixi run python ...`, `poetry run ...`, `uv run ...`, or `pixi run -e <env> ...` AND the env-manager's manifest includes the new library.
   - **OK — pip-installed**: step (or a prior step in the same job) does `pip install "<package>..."` covering the new library.
   - **BROKEN — env bypass**: job ran `setup-pixi`/`setup-poetry` but invokes `python3 scripts/...` directly. Fix by prefixing `pixi run` (Option B).
   - **BROKEN — no install**: job has `setup-python` only, with either `pip install pyyaml` (and nothing else) or NO `Install dependencies` step at all. Fix by adding `pip install "<package>>=X,<Y"` (Option A).

4. **Pick the fix per job's weight, not uniformly.** Don't reflexively convert every lightweight job to `setup-pixi` — installing a full pixi env adds minutes per job for what may be a one-library dependency. Use Option A for jobs that need just this library; use Option B when the job already pays the env-manager cost.

5. **Eliminate version-pin drift.** ProjectOdyssey's CLAUDE.md states `pixi.toml` is the single source of truth. Every `pip install "<package>...>=X,<Y"` in `.github/workflows/` is a duplicated pin that will silently drift on the next version bump. Grep all workflow pins and update them to match the canonical pin in one commit:
   ```bash
   grep -rnE 'homericintelligence-hephaestus[><=]' .github/workflows/
   grep -nE  'homericintelligence-hephaestus[><=]' pixi.toml
   ```
   Consider adding a pre-commit hook (or CI guardrail) that fails when these diverge.

6. **Verify via CI.** Push the fix and confirm each previously-failing check goes from FAILURE → SUCCESS. Pre-commit/local green is NOT sufficient evidence — the failure mode is invisible outside CI because the local env already has the library installed.

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
|---------|----------------|---------------|----------------|
| Attempt 1 | Authored the migration PR, ran `pixi run pre-commit` locally, all green; merged-intent before CI finished | Pre-commit env had `hephaestus` already installed; CI's lightweight `setup-python` jobs did not. `ModuleNotFoundError` only surfaces in jobs that don't enter the project env. | Pre-commit success ≠ CI success when CI has multiple env contexts (pixi env vs. raw setup-python jobs). Always wait for CI before declaring a migration done. |
| Attempt 2 | Read only the failing job's `Set up Python` step to find the missing `pip install` | Two of the four broken jobs had NO `Install dependencies` step at all — easy to skim past when looking for "what's in the pip install line." | Always check whether a `pip install` step *exists*, not just what's in it. A missing step is the failure, not a wrong arg. |
| Attempt 3 | Considered switching all lightweight jobs to `setup-pixi` for uniformity | Would slow each job from ~30s to several minutes (pixi env install) for a single dependency. Wasteful for jobs that just need one library. | Match the install method to the job's weight. `pip install <pkg>` is the right fix for slim jobs; `pixi run` is the right fix for jobs already paying the env-manager cost. |
| Attempt 4 | Fixed `ModuleNotFoundError` jobs but ignored the pre-existing `>=0.7.0,<1` pins in 5 other workflow files | The pins were not currently breaking CI (still in-range) but had already drifted from `pixi.toml`'s `>=0.9.0,<1`. Next minor bump would silently break a different set of jobs. | When fixing pin drift in one place, grep for the package name across ALL workflows and bump in lockstep — defer-and-forget guarantees a future incident. |
| Attempt 5 | Job had `setup-pixi` then `run: python3 scripts/validate_readme_commands.py` | `python3` resolves to system Python (not the pixi env's interpreter), so `pip install` performed inside the pixi env is invisible to it. Identical `ModuleNotFoundError` as the no-install jobs. | Setting up an env-manager is only half the contract — every invocation must be prefixed (`pixi run python3 ...`). A job that runs `setup-pixi` and then `python3 ...` is a silent bypass. |

## Results & Parameters

Verified in HomericIntelligence/ProjectOdyssey on 2026-05-22 (commit `702a5a2e` on branch `5061-hephaestus-090-script-migration`, PR #5445):

- **Migration**: 19 Python scripts changed `from common import get_repo_root` → `from hephaestus.utils import get_repo_root`; `pixi.toml` bumped `homericintelligence-hephaestus` from `>=0.7.0,<1` to `>=0.9.0,<1`.
- **Failure surface**: 5 CI jobs broke with `ModuleNotFoundError: No module named 'hephaestus'`.
  - `comprehensive-tests.yml::validate-test-coverage` → `scripts/validate_test_coverage.py` (had `pip install pyyaml` only)
  - `validate-configs.yml::Validate Test Coverage` → `scripts/validate_test_coverage.py` (had `pip install pyyaml` only)
  - `comprehensive-tests.yml::audit-shared-links` → `scripts/audit_shared_links.py` (had NO install step)
  - `comprehensive-tests.yml::test-metrics` → `scripts/generate_test_metrics.py` (had NO install step)
  - `docs.yml::validate-readme-commands` → `scripts/validate_readme_commands.py` (env-manager bypass: had `setup-pixi` but ran `python3 scripts/...`)
- **Fix applied**:
  - 4 jobs: added `pip install "homericintelligence-hephaestus>=0.9.0,<1"` (Option A).
  - 1 job (`validate-readme-commands`): rewrote step to use `pixi run python3 scripts/...` (Option B).
  - 5 other pre-existing `pip install "...>=0.7.0,<1"` pins across workflows bumped to `>=0.9.0,<1` so all 9 workflow pin sites match `pixi.toml`.
- **Result**: All 5 previously-failing checks went from FAILURE → SUCCESS on commit `702a5a2e`.

**Decision guide**:

| Situation | Recommended Fix |
|-----------|----------------|
| Lightweight job, only needs the migrated library | Option A: `pip install "<package>>=X,<Y"` matching the canonical pin |
| Job already runs `setup-pixi`/`setup-poetry` | Option B: prefix every invocation with `pixi run` / `poetry run` |
| Multiple workflows pin the same package | Bump all pins together; consider a CI guardrail that diffs workflow pins vs. `pixi.toml` |
| About to merge a library-migration PR | Run the audit grep BEFORE merge; pre-commit/local green is not evidence for CI behavior |

## Verified On

| Project | Context | Details |
|---------|---------|---------|
| ProjectOdyssey | PR #5445 — hephaestus 0.7.0 → 0.9.0 helper migration (2026-05-22) | 5 workflow jobs broke with `ModuleNotFoundError`; fixed in commit `702a5a2e` via mix of `pip install` (4 jobs) and `pixi run python3` rewrite (1 job); plus pin-drift bump in 5 other workflow files |
