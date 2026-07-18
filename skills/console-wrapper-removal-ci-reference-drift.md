---
name: console-wrapper-removal-ci-reference-drift
description: "Use when deleting redundant Python scripts/ wrapper files after moving functionality to package modules or pyproject console scripts: update every CI, pre-commit, shell, docs, fallback, and tracked-file test reference to the canonical entry point before removing the wrapper."
category: ci-cd
date: 2026-06-30
version: "1.0.0"
user-invocable: false
verification: verified-ci
tags:
  - ci-cd
  - console-scripts
  - wrapper-removal
  - pre-commit
  - shell-scripts
  - project-hephaestus
---

# Console Wrapper Removal CI Reference Drift

## Overview

| Field | Value |
| ----- | ----- |
| **Date** | 2026-06-30 |
| **Objective** | Remove duplicate `scripts/*.py` console wrappers without leaving CI, hooks, shell tooling, docs, or tests pointing at deleted paths. |
| **Outcome** | ProjectHephaestus issue #1445 / PR #1713 went green after every wrapper caller moved to a pyproject console script or importable `python -m` module entry point. |
| **Verification** | verified-ci, based on the completed PR #1713 outcome reported by the operator plus local evidence from commit `52703ae7d34e65e00f3a1a57b759d2a1fe912eff`. |

## When to Use

- You are deleting `scripts/*.py` wrappers because package modules or `[project.scripts]` already provide the canonical CLI.
- CI, pre-commit, shell scripts, docs, or runtime fallbacks still invoke raw `scripts/<name>.py` paths.
- A regression appears only after wrapper deletion because `git ls-files` or a test fixture still sees deleted tracked paths during the commit under test.
- You need a focused checklist before converting a repository from path-based script execution to console-script or `python -m` execution.

## Verified Workflow

### Quick Reference

```bash
# 1. Inventory wrappers scheduled for deletion.
git diff --name-status main...HEAD -- scripts/

# 2. Search every caller before deleting the files.
rg "scripts/(audit_doc_policy|check_cli_table_sync|check_python_version_consistency|check_tier_labels|check_version_single_source|drive_prs_green|implement_issues|merge_prs|plan_issues)\\.py"

# 3. Replace hook/CI/doc/shell references with canonical entry points.
# Examples from ProjectHephaestus #1445 / #1713:
python3 -m hephaestus.scripts_lib.check_cli_table_sync
hephaestus-check-python-version
python3 -m hephaestus.scripts_lib.check_version_single_source
python -m hephaestus.automation.ci_driver

# 4. Add regression coverage for runtime fallbacks that used deleted wrappers.
pixi run pytest tests/unit/automation/test_loop_runner.py::test_resolve_phase_bin_drive_green_uses_canonical_module -q

# 5. Re-run the repo's hook/CI path after reference migration.
pre-commit run --files .pre-commit-config.yaml hephaestus/automation/loop_runner.py scripts/shell/drive_prs_green_ecosystem.sh
```

### Detailed Steps

1. **Inventory the wrappers and their canonical replacements.** For each deleted `scripts/<name>.py`, identify whether the supported replacement is a pyproject console script or an importable module command. Do this before touching callers so every replacement is intentional.
2. **Search all reference surfaces, not only Python imports.** Check `.github/workflows/`, `.pre-commit-config.yaml`, shell scripts, docs, skill docs, test fixtures, and runtime fallback code. Wrapper deletion fails CI when even one path-based caller remains.
3. **Move pre-commit hooks to canonical commands.** In PR #1713, hooks moved from raw `scripts/check_*` paths to `python3 -m hephaestus.scripts_lib.check_cli_table_sync`, `hephaestus-check-python-version`, and `python3 -m hephaestus.scripts_lib.check_version_single_source`.
4. **Replace runtime fallbacks with modules.** `loop_runner._resolve_phase_bin("drive-green")` could no longer return `scripts/drive_prs_green.py`; it now returns `sys.executable` plus `["-m", "hephaestus.automation.ci_driver"]`. Add a direct regression test for this fallback.
5. **Replace shell driver paths with module invocation.** `scripts/shell/drive_prs_green_ecosystem.sh` stopped checking for `$PROJECT_ROOT/scripts/drive_prs_green.py`, uses `pyproject.toml` as the root marker, and invokes `pixi ... python -m hephaestus.automation.ci_driver`.
6. **Update docs and skill references in the same change.** Any user-facing command snippets that mention removed wrappers should point to the console script or module form, or they will reintroduce bad operational guidance.
7. **Make tracked-file tests tolerate in-flight deletions.** Tests that iterate `git ls-files -z` should ignore tracked paths that no longer exist in the working tree; during the deletion commit, removed wrappers are still tracked in git metadata but absent on disk.

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
| ------- | -------------- | ------------- | -------------- |
| Delete wrappers before migrating every caller | Removed `scripts/*.py` files while hooks and shell tooling still referenced those paths | CI and pre-commit fail with missing-file errors as soon as the path-based caller runs | Treat wrapper deletion as a reference-migration change, not just `git rm` cleanup |
| Leave `drive-green` fallback on `scripts/drive_prs_green.py` | Kept `loop_runner._resolve_phase_bin("drive-green")` pointing at the deleted wrapper | Agent-stage fallback breaks when the console script is absent from `PATH` | Runtime fallbacks must target the importable canonical module, and need direct regression tests |
| Keep ecosystem shell driver path-based | `drive_prs_green_ecosystem.sh` checked for and invoked `$PROJECT_ROOT/scripts/drive_prs_green.py` | The shell helper fails its own sanity check after the wrapper disappears | Shell helpers should root-check the project and invoke `python -m <module>` through the repo environment |
| Trust `git ls-files` paths all exist | A git metadata safety test converted every tracked path to a filesystem path without checking existence | During a deletion commit, `git ls-files` can still report tracked files removed from the worktree | Filter `git ls-files` candidates with `.exists()` when the test inspects on-disk metadata |

## Results & Parameters

### ProjectHephaestus issue #1445 / PR #1713

- Commit: `52703ae7d34e65e00f3a1a57b759d2a1fe912eff` (`refactor(scripts): remove duplicate console wrappers`).
- Deleted wrappers: `scripts/audit_doc_policy.py`, `scripts/check_cli_table_sync.py`, `scripts/check_python_version_consistency.py`, `scripts/check_tier_labels.py`, `scripts/check_version_single_source.py`, `scripts/drive_prs_green.py`, `scripts/implement_issues.py`, `scripts/merge_prs.py`, and `scripts/plan_issues.py`.
- Key hook migrations: `.pre-commit-config.yaml` now calls `python3 -m hephaestus.scripts_lib.check_cli_table_sync`, `hephaestus-check-python-version`, and `python3 -m hephaestus.scripts_lib.check_version_single_source`.
- Key runtime migration: `hephaestus.automation.loop_runner._resolve_phase_bin("drive-green")` now falls back to `sys.executable -m hephaestus.automation.ci_driver`, covered by `test_resolve_phase_bin_drive_green_uses_canonical_module`.
- Key shell migration: `scripts/shell/drive_prs_green_ecosystem.sh` now invokes the CI driver module via `pixi ... python -m hephaestus.automation.ci_driver` and validates the root with `pyproject.toml`.
- Key test migration: tracked-file metadata checks filter out non-existent tracked paths so deleted wrappers do not produce false failures during the deletion commit.

## Verified On

| Project | Context | Details |
| ------- | ------- | ------- |
| ProjectHephaestus | Issue #1445 / PR #1713 | CI was driven green after replacing deleted wrapper references with canonical console-script or module entry points. Local evidence came from commit `52703ae7d34e65e00f3a1a57b759d2a1fe912eff`; CI result was reported by the operator for the completed PR. |
