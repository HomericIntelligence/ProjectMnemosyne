---
name: architecture-cross-repo-migration-verify-issue-inventory
description: "Verify a GitHub issue's file inventory and ADR cross-references against disk before planning a cross-repo or git-submodule migration; issue bodies and docs drift from reality. Use when: (1) planning a file/package move named in an issue, (2) the move crosses submodule or repo boundaries, (3) the issue cites ADRs or file/test counts, (4) the destination repo's language/packaging capability is assumed."
category: architecture
date: 2026-06-20
version: "1.0.0"
user-invocable: false
verification: unverified
tags: [cross-repo, submodule, migration, planning, issue-inventory, stale-docs, adr, ground-truth, git-history, nats-contract]
---

# Cross-Repo Migration: Verify Issue Inventory Before Planning

## Overview

| Field | Value |
|-------|-------|
| **Date** | 2026-06-20 |
| **Objective** | Produce an implementation plan for issue #143 — move a Python orchestration layer from ProjectKeystone to ProjectAgamemnon across git-submodule boundaries in the Odysseus meta-repo. |
| **Outcome** | Plan written, but the issue's file inventory, counts, and cited ADR all diverged from on-disk reality; the plan had to be rebuilt from verified ground truth. |
| **Verification** | unverified — planning session only; the migration was not executed and no tests/CI ran. |

## When to Use

- You are planning a file or package move that a GitHub issue names explicitly ("Files to Modify", "modules to move").
- The move crosses a git-submodule or independent-repo boundary (e.g. inside an Odysseus-style meta-repo).
- The issue cites ADR numbers, doc paths, or file/test counts you are about to copy into the plan.
- The destination repo's language, build system, or packaging capability is assumed rather than verified.
- A test directory tree looks single-language by name but may hold mixed-language files (Python + C++ GoogleTest).
- A public string-literal contract (NATS subject, wire field) sits inside code that is being moved or renamed.

## Proposed Workflow

> **Warning:** This workflow has not been validated end-to-end. Treat as a hypothesis until CI confirms.

### Quick Reference

```bash
# 1. Verify every file the issue names actually exists
for f in src/keystone/maestro_client.py tests/test_maestro_client.py; do ls "$f" 2>&1; done
grep -rln 'maestro\|Maestro' src/ tests/ --include='*.py'   # confirm absence
# 2. Confirm cited ADRs exist; pick the next real number
ls docs/adr/
# 3. Classify test dirs by CONTENT, not name
ls tests/unit/   # .py or .cpp/.hpp?
# 4. Verify the destination can host the package
ls <dest>/pyproject.toml 2>&1; grep -n 'pypi-dependencies' <dest>/pixi.toml
# 5. Guard a frozen public contract literal
grep -rn '"hi.tasks.>"' <dest>/src
# 6. Scope acceptance grep to exclude same-named C++/build dirs
find <src>/src <src>/tests -name '*.py' -not -path '*/build*/*' -not -path '*/.worktrees/*'
```

### Detailed Steps (pre-planning checklist)

Treat the issue body's file inventory and ADR cross-references as a **hypothesis**. Verify every named file, ADR, and capability against disk *before* writing "Files to Modify". Flag every assumption you could not verify.

1. **`ls`/`grep` every file the issue names before writing it into the plan.** Issue inventories drift from disk. Issue #143 named `maestro_client.py` + `test_maestro_client.py` — neither exists. It said "10 modules / 12 tests"; disk had 10 `.py` source files (issue omitted `__main__.py`, invented `maestro_client.py`) and 11 test files (`test_daemon.py` existed but was unlisted; `test_maestro_client.py` listed but absent).
2. **Verify each cited ADR/doc exists; pick the next REAL sequential number.** The issue AND ProjectKeystone's own CLAUDE.md cited "ADR-015"; `ls docs/adr/` showed only 001–008. Use the next real number (009) and reference an ADR that actually exists (006).
3. **Classify mixed-language test dirs by file CONTENT, not directory name.** `tests/{unit,integration,e2e,load,fixtures,mocks}/` looked Pythonic but held C++ GoogleTest `.cpp`/`.hpp` that must STAY. Only top-level `tests/*.py` migrate. A naive `find tests -name '*.py'` or whole-dir `git mv` would mis-sweep or strand files.
4. **Verify the destination's build system/language/packaging before assuming "just add the package."** ProjectAgamemnon had ZERO Python (no `pyproject.toml`, no `[pypi-dependencies]` in `pixi.toml`, `src/` all `.cpp`) — so this was a from-scratch bootstrap, not an edit.
5. **Explicitly flag cross-repo history as NOT preserved by plain `git mv`.** `git mv` preserves `git log --follow` only WITHIN one repo. Keystone and Agamemnon are independent repos (submodules), so a copy-in + provenance commit does not give `--follow` across the boundary. True preservation needs `git filter-repo`/subtree — left out of scope, so flag it as the top unverified risk.
6. **Identify public string-literal contracts and add a grep-guard.** The NATS subject literal `hi.tasks.{team_id}.{task_id}.{event}` / `"hi.tasks.>"` must survive byte-for-byte (downstream Argus/AI-Maestro must not redeploy), and the dot-count parse arithmetic in `_parse_subject` must not change (`hi.tasks.team.task.event` = 5 parts). Guard these separately from the identifier rename.

## Verified Workflow

_Not applicable._ This skill was captured from a planning session and is `unverified`: the migration plan was never executed and no tests or CI ran, so there is no verified workflow. The actionable, hypothesis-level methodology lives under **Proposed Workflow** above and must be treated as unvalidated until CI confirms it. (This placeholder section exists only because `scripts/validate_plugins.py` requires the literal `## Verified Workflow` heading; it intentionally makes no verification claim.)

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
|---------|----------------|---------------|----------------|
| 1 | Trusted the issue's "10 modules / 12 tests" counts and wrote them straight into "Files to Modify". | Disk had 10 `.py` sources / 11 test files; the issue omitted `__main__.py` and `test_daemon.py` and invented `maestro_client.py`/`test_maestro_client.py`. | `ls`/`grep` every file the issue names; reconcile counts against disk before planning. |
| 2 | Cited "ADR-015" for the migration rationale, copying it from the issue and Keystone's CLAUDE.md. | `ls docs/adr/` showed only 001–008; ADR-015 does not exist. | Verify each cited ADR/doc exists; pick the next real sequential number and reference a real ADR. |
| 3 | Planned a whole-directory `git mv tests/ ...` to move the test suite. | `tests/{unit,integration,...}/` held C++ GoogleTest `.cpp`/`.hpp` that must stay; only top-level `tests/*.py` migrate. | Classify by file content, not directory name; scope moves and greps to verified `.py` files. |
| 4 | Assumed cross-repo `git mv` (Keystone→Agamemnon) would preserve `git log --follow` history. | `git mv` preserves `--follow` only within one repo; submodules are independent repos, so a copy-in commit breaks the chain. | Flag cross-repo history as not preserved by plain `git mv`; true preservation needs `git filter-repo`/subtree. |
| 5 | Assumed ProjectAgamemnon already hosts Python, so the move was "just add the package". | Agamemnon had zero Python: no `pyproject.toml`, no `[pypi-dependencies]`, `src/` all `.cpp`. | Verify the destination's language/build/packaging before assuming a simple edit; this was a from-scratch bootstrap. |

## Results & Parameters

### Issue-said-X vs disk-had-Y reconciliation

| Claim in issue #143 | On-disk reality |
|---------------------|-----------------|
| `src/keystone/maestro_client.py` to move | Does not exist (`ls` → "No such file or directory") |
| `tests/test_maestro_client.py` to move | Does not exist |
| "10 modules" | 10 `.py` source files, but `__main__.py` omitted and `maestro_client.py` invented |
| "12 tests" | 11 test files; `test_daemon.py` present but unlisted, `test_maestro_client.py` listed but absent |
| `grep -rln 'maestro\|Maestro'` | No matches in `src/`/`tests/` `.py` files |
| Cites ADR-015 (issue + Keystone CLAUDE.md) | `docs/adr/` has only 001–008; next real number is 009; reference ADR-006 |
| Destination ProjectAgamemnon hosts the package | Zero Python: no `pyproject.toml`, no `[pypi-dependencies]` in `pixi.toml`, `src/` all `.cpp` |

### Grep-guard commands (frozen public contract)

```bash
# NATS subject literal must survive byte-for-byte after the move/rename
grep -rn '"hi.tasks.>"' <dest>/src
grep -rn 'hi.tasks.{team_id}.{task_id}.{event}' <dest>/src
# _parse_subject dot-count arithmetic unchanged: hi.tasks.team.task.event == 5 parts
grep -n '_parse_subject' <dest>/src/**/*.py
```

### Acceptance-criterion scoping

```bash
# Only verified top-level Python migrates; exclude same-named C++ test dirs + build artifacts
find <src>/src <src>/tests -name '*.py' \
  -not -path '*/build*/*' -not -path '*/.worktrees/*'
# Confirm the absence the issue got wrong, as a guard
grep -rln 'maestro\|Maestro' <src>/src <src>/tests --include='*.py'   # expect: no output
```

## Verified On

| Field | Value |
|-------|-------|
| Source repo | ProjectKeystone |
| Destination repo | ProjectAgamemnon |
| Meta-repo | Odysseus (git-submodule boundaries) |
| Trigger | Issue #143 — Python orchestration layer migration (planning session) |
| Verification | unverified — plan not executed; no tests/CI ran |
