---
name: architecture-cross-repo-migration-verify-issue-inventory
description: "Cross-repo/submodule migrations: verify a GitHub issue's file inventory and ADR cross-references against disk BEFORE the move, and sweep every orphaned CONSUMER (validators, tests, entry points, hooks, workflows, docs, frozen-count guards) AFTER the move — a migration isn't done when the source moves, it's done when every consumer is reconciled. Use when: (1) planning a file/package move named in an issue, (2) the move crosses submodule or repo boundaries, (3) the issue cites ADRs or file/test counts, (4) the destination repo's language/packaging capability is assumed, (5) you just removed migrated source and need main to stay green."
category: architecture
date: 2026-07-11
version: "1.1.0"
user-invocable: false
verification: verified-ci
history: architecture-cross-repo-migration-verify-issue-inventory.history
tags: [cross-repo, submodule, migration, planning, issue-inventory, stale-docs, adr, ground-truth, git-history, nats-contract, orphan-consumers, dangling-references, frozen-count-assertions, tree-wide-guards, entry-points, precommit-hooks, ci-workflows, incomplete-migration]
---

# Cross-Repo Migration: Verify Issue Inventory Before Planning

## Overview

| Field | Value |
|-------|-------|
| **Date** | 2026-06-20 |
| **Objective** | Two halves of one lifecycle: (a) plan a Python-layer move from ProjectKeystone→ProjectAgamemnon across submodule boundaries (issue #143); (b) execute a real cross-repo surface migration (ProjectHephaestus ADR-016 / #2063 — move skills/, plugins/, .claude-plugin/, .codex-plugin/, .agents/, assets/ out to a new "Athena" repo) and keep `main` green. |
| **Outcome** | (a) The issue's inventory/counts/ADR diverged from disk; the plan was rebuilt from verified ground truth. (b) Removing the source dirs alone turned `main` RED — every orphaned CONSUMER still referenced the moved surface; the systematic sweep (PR #2070, merged `7cc097d6`) reconciled all of them and main returned to green. |
| **Verification** | verified-ci — the post-move orphan-consumer sweep was executed end-to-end; PR #2070 merged as `7cc097d6`, main returned to green, subsequent PRs merged cleanly. (The pre-move inventory-check half remains a planning-derived hypothesis.) |
| **History** | [changelog](./architecture-cross-repo-migration-verify-issue-inventory.history) |

## When to Use

- You are planning a file or package move that a GitHub issue names explicitly ("Files to Modify", "modules to move").
- The move crosses a git-submodule or independent-repo boundary (e.g. inside an Odysseus-style meta-repo).
- The issue cites ADR numbers, doc paths, or file/test counts you are about to copy into the plan.
- The destination repo's language, build system, or packaging capability is assumed rather than verified.
- A test directory tree looks single-language by name but may hold mixed-language files (Python + C++ GoogleTest).
- A public string-literal contract (NATS subject, wire field) sits inside code that is being moved or renamed.
- **You just removed the migrated source directories and need `main` to stay green** — a migration is only done when every CONSUMER (validators, tests, entry points, pre-commit hooks, CI workflows, docs, frozen-count/membership guards, whole test dirs) is reconciled, not when the source moves.
- A repo has "frozen" guards that assert a NUMBER (console-script count, symbol count) or a membership SET (sanctioned-dir allowlist, phantom-dir guard) — these silently encode the old surface and won't be caught by grepping for module names.

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

> **Scope note:** The **pre-move inventory check** above (Proposed Workflow) is
> still planning-derived and unverified. The **post-move orphan-consumer sweep**
> below IS verified-ci: it was executed end-to-end on ProjectHephaestus ADR-016
> (issue #2063), landed as PR #2070 (merged `7cc097d6`), and returned `main` to
> green.

### After the move: chase EVERY dangling reference

A migration isn't done when the source moves — it's done when every CONSUMER of
the moved surface is reconciled. ProjectHephaestus ADR-016 moved the skill/plugin
surface (`skills/`, `plugins/`, `.claude-plugin/`, `.codex-plugin/`, `.agents/`,
`assets/`) out to a new "Athena" repo. Removing the source dirs alone turned
`main` RED because these consumer classes still pointed at the deleted surface.
After deleting the migrated dirs, sweep for ALL of them:

1. **Modules** that import/validate the moved surface — e.g. removed
   `hephaestus/validation/{skill_catalog,repo_analyze_skills,skill_merge_method}.py`.
2. **Test files** importing those modules — removed 5 orphaned test files, and
   *reconciled* 4 more that imported a now-deleted symbol
   (`test_validation_shim_parity.py`, `test_validation_parser_usage.py`,
   `test_validation_parser.py`, `test_validation_cli_contracts.py` — dropped the
   `skill_catalog` import + its one test each, rather than deleting the whole
   file).
3. **Entry points** in `pyproject.toml` — removed 2 console-script entries, then
   updated the frozen console-script COUNT assertion a test asserts (53 → 51).
4. **Pre-commit hooks** — removed 3 hooks that invoked deleted scripts.
5. **CI workflows** — removed `.github/workflows/hol-plugin-scanner.yml` + its
   `.plugin-scanner.toml` config + the workflow-README row that listed it.
6. **Docs** — removed `COMPATIBILITY.md` rows referencing the removed surface.
7. **Test-infrastructure allowlists** — `SANCTIONED_EXTRA_TEST_DIRS` in
   `tests/unit/validation/test_structure.py` still listed `"plugins"`; a
   *separate* phantom-test-dir guard then failed until that entry was removed.
8. **The whole removed test dir** — `tests/unit/plugins/`.

**Frozen-count / membership assertions are the sneaky ones.** They don't
reference the moved surface *by name*, so a grep for module identifiers misses
them — they assert a NUMBER (console-script count 53→51) or a membership SET
(`SANCTIONED_EXTRA_TEST_DIRS`, the phantom-dir guard) that the migration
silently changed. Search for them explicitly.

**Detection method that works:**

- After deleting the migrated dirs, grep the **ENTIRE tree** for the removed
  module names, script paths, workflow names, and directory names — not just the
  obvious call sites.
- Run the **FULL** test suite locally, not just the changed files: tree-wide
  guards (whole-tree `mypy`, structure tests, phantom-dir guards) fail *far from
  the deletion*, so a changed-files-only run reports green while `main` is red.

### Quick Reference

```bash
# After deleting the migrated dirs (skills/ plugins/ .claude-plugin/ ...),
# sweep the ENTIRE tree for every class of dangling reference:
DIRS='skills|plugins|.claude-plugin|.codex-plugin|.agents|assets'
MODS='skill_catalog|repo_analyze_skills|skill_merge_method'   # deleted module names
# 1. modules/tests importing deleted modules
grep -rn -E "$MODS" --include='*.py' .
# 2. deleted dir names referenced anywhere (allowlists, guards, docs, workflows)
grep -rn -E "\"($DIRS)\"|/($DIRS)/" .
# 3. entry points + the frozen COUNT that a test asserts
grep -n 'console_scripts\|\[project.scripts\]' pyproject.toml
grep -rn -E 'len\(.*scripts.*\)\s*==|== *5[0-9]' tests/    # frozen count assertion
# 4. pre-commit hooks invoking deleted scripts
grep -n -E "$MODS|$DIRS" .pre-commit-config.yaml
# 5. workflows scanning the moved surface
grep -rln -E "$DIRS" .github/workflows/
# 6. membership allowlists / phantom-dir guards
grep -rn 'SANCTIONED_EXTRA_TEST_DIRS' tests/
# 7. run the FULL suite (tree-wide guards fail far from the deletion)
pixi run mypy && pixi run pytest tests/unit
```

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
|---------|----------------|---------------|----------------|
| 1 | Trusted the issue's "10 modules / 12 tests" counts and wrote them straight into "Files to Modify". | Disk had 10 `.py` sources / 11 test files; the issue omitted `__main__.py` and `test_daemon.py` and invented `maestro_client.py`/`test_maestro_client.py`. | `ls`/`grep` every file the issue names; reconcile counts against disk before planning. |
| 2 | Cited "ADR-015" for the migration rationale, copying it from the issue and Keystone's CLAUDE.md. | `ls docs/adr/` showed only 001–008; ADR-015 does not exist. | Verify each cited ADR/doc exists; pick the next real sequential number and reference a real ADR. |
| 3 | Planned a whole-directory `git mv tests/ ...` to move the test suite. | `tests/{unit,integration,...}/` held C++ GoogleTest `.cpp`/`.hpp` that must stay; only top-level `tests/*.py` migrate. | Classify by file content, not directory name; scope moves and greps to verified `.py` files. |
| 4 | Assumed cross-repo `git mv` (Keystone→Agamemnon) would preserve `git log --follow` history. | `git mv` preserves `--follow` only within one repo; submodules are independent repos, so a copy-in commit breaks the chain. | Flag cross-repo history as not preserved by plain `git mv`; true preservation needs `git filter-repo`/subtree. |
| 5 | Assumed ProjectAgamemnon already hosts Python, so the move was "just add the package". | Agamemnon had zero Python: no `pyproject.toml`, no `[pypi-dependencies]`, `src/` all `.cpp`. | Verify the destination's language/build/packaging before assuming a simple edit; this was a from-scratch bootstrap. |
| 6 | (ADR-016) Removed the migrated source dirs (`skills/`, `plugins/`, validators) and considered the migration done. | `main` went RED — consumers still referenced the moved surface: validators importing deleted modules, tests importing deleted validators, pre-commit hooks invoking deleted scripts, a workflow scanning the deleted plugin surface, entry points pointing at deleted modules, docs counting the old surface. | A migration isn't done when the SOURCE moves; it's done when every CONSUMER is reconciled. Sweep modules, tests, entry points, hooks, workflows, docs, allowlists, and whole test dirs. |
| 7 | Grepped only for the deleted module identifiers to find the fallout. | Missed the frozen COUNT/membership assertions: the console-script count a test freezes (53→51) and `SANCTIONED_EXTRA_TEST_DIRS` still listing `"plugins"` (which then tripped a separate phantom-test-dir guard). | Guards that assert a NUMBER or a SET, not a name, silently encode the old surface. Search for count/membership assertions explicitly, not just module names. |
| 8 | Ran tests only on the edited files to confirm the removal. | Tree-wide guards (whole-tree `mypy`, structure tests, phantom-dir guard) failed elsewhere — the break was far from the deletion. | Run the FULL suite locally after a migration; tree-wide guards fail far from the change, so a changed-files-only run reports false-green. |

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

### Post-move orphan-consumer sweep (ADR-016 / PR #2070) — the checklist that turned main green

| Consumer class | What was orphaned | Action taken |
|----------------|-------------------|--------------|
| Modules | `hephaestus/validation/{skill_catalog,repo_analyze_skills,skill_merge_method}.py` imported/validated the moved surface | Removed all 3 |
| Test files (orphaned) | 5 test files imported the removed validators | Removed all 5 |
| Test files (reconciled) | `test_validation_shim_parity.py`, `test_validation_parser_usage.py`, `test_validation_parser.py`, `test_validation_cli_contracts.py` imported the deleted `skill_catalog` symbol | Dropped that import + its one test each (kept the file) |
| Entry points | 2 console-script entries in `pyproject.toml` pointed at deleted modules | Removed both; updated the frozen count assertion **53 → 51** |
| Pre-commit hooks | 3 hooks invoked deleted scripts | Removed all 3 |
| CI workflow | `.github/workflows/hol-plugin-scanner.yml` scanned the deleted plugin surface | Removed workflow + `.plugin-scanner.toml` config + workflow-README row |
| Docs | `COMPATIBILITY.md` rows referenced removed surface | Removed the rows |
| Test-infra allowlist | `SANCTIONED_EXTRA_TEST_DIRS` still listed `"plugins"`; a phantom-test-dir guard then failed | Removed the `"plugins"` entry |
| Whole test dir | `tests/unit/plugins/` | Removed the directory |

## Verified On

| Field | Value |
|-------|-------|
| Source repo (a) | ProjectKeystone |
| Destination repo (a) | ProjectAgamemnon |
| Meta-repo (a) | Odysseus (git-submodule boundaries) |
| Trigger (a) | Issue #143 — Python orchestration layer migration (planning session) |
| Verification (a) | unverified — plan not executed; no tests/CI ran |
| Source repo (b) | ProjectHephaestus (ADR-016 / issue #2063) |
| Destination repo (b) | Athena (new repo receiving the skill/plugin surface) |
| Trigger (b) | Post-move orphan-consumer sweep — PR #2070, merged as commit `7cc097d6` |
| Verification (b) | verified-ci — main returned to green; subsequent PRs merged cleanly |
