# Raw Session Notes: Issue Triage and Bulk Fix

**Date**: 2026-02-22
**Project**: ProjectScylla
**Session type**: Bulk issue triage and parallel PR creation

## Session Summary

**Objective**: Bulk-close duplicate GitHub issues and create parallel PRs for ~20 simple open issues
in ProjectScylla, one PR per issue, using isolated git worktrees.

**Outcome**: SUCCESS — 5 issues closed as duplicates/already-done, 16 PRs created across 4 waves,
all with auto-merge enabled. Most PRs merged within minutes.

---

## What Worked

1. **Wave-based parallel execution**: Grouping issues by complexity/risk and launching 5 agents in
   parallel per wave was efficient and safe.

2. **Isolated worktrees** (`isolation: "worktree"`): Each agent got its own copy of the repo — no
   conflicts between parallel agents working on different files.

3. **Step 0 first**: Closing duplicates before doing any coding work prevents wasted effort.

4. **File conflict pre-analysis**: Identifying which issues touch the same files before execution
   allowed merging #896+#1006 into a single PR.

5. **Targeted pre-commit**: Running `pre-commit run ruff --all-files` +
   `pre-commit run mypy-check-python --all-files` instead of `--all-files` prevented unrelated
   pyproject.toml/pixi.lock modifications from contaminating PRs.

6. **Investigate-first for risky changes**: #977 required reading code + YAML config before deciding
   which constant to use — saved from making wrong fix.

7. **Conventional commits + `gh pr merge --auto --rebase`**: Every PR got auto-merge enabled
   immediately after creation.

---

## What Failed / Pitfalls

1. **`pre-commit run --all-files` contaminates PRs**: The #978 agent ran `--all-files` which caused
   pyproject.toml/pixi.lock to be auto-modified by the S101 hook (which #973 was simultaneously
   adding). The agent tried to commit these unrelated changes.
   **Fix**: Use targeted hooks only.

2. **PR #1013 (#961) was closed without merging**: The worktree branch for #961 was cleaned up
   (worktree isolation means branches may be deleted after agent exits). Had to re-create as #1028.

3. **Background agents lose task IDs**: Two agents were launched as background tasks; their IDs
   couldn't be looked up via `TaskOutput` later. Always prefer foreground agents or capture IDs
   immediately.

4. **#892 (audit asserts) and #893 (audit /tmp)**: Both required audit-first approach — the "fix"
   was trivial or zero because the code was already clean. These audits should be done before
   writing the issue title as a code change.

---

## Parameters / Config

- Agent type: `Bash` with `isolation: "worktree"`
- Wave size: 5 parallel agents max
- Sequential constraint: issues touching same file must be in same agent or sequential waves
- PR auto-merge: `gh pr merge --auto --rebase` immediately after `gh pr create`
- Pre-commit strategy: targeted hooks only (`ruff`, `mypy-check-python`) to avoid side effects
- Test command: `pixi run python -m pytest tests/unit/ -q --no-cov`

---

## Issue Disposition Summary

| Category | Count |
|----------|-------|
| Closed as duplicate | 3 |
| Closed as already fixed | 2 |
| PRs created (Wave 1) | 5 |
| PRs created (Wave 2) | 5 |
| PRs created (Wave 3) | 3 |
| PRs created (Wave 4) | 3 |
| **Total PRs** | **16** |

---

## Notable Issue Patterns

- **#892, #893** — "Audit and fix" issues where the actual fix was zero changes needed
- **#896 + #1006** — Two issues touching the same file, merged into a single PR
- **#977** — Required YAML config audit before determining correct constant to use
- **#961 / #1013 / #1028** — Worktree branch cleanup caused PR loss; re-created successfully
