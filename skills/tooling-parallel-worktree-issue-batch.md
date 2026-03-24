---
name: tooling-parallel-worktree-issue-batch
description: "Batch-resolve GitHub issues using parallel sub-agents in isolated git worktrees, then cherry-pick results. Use when: (1) triaging and executing multiple independent issues simultaneously, (2) coordinating parallel agent work that touches different files."
category: tooling
date: 2026-03-24
version: "1.0.0"
user-invocable: false
tags: [parallel-agents, worktrees, cherry-pick, issue-triage, batch-execution]
---

# Parallel Worktree Issue Batch Resolution

## Overview

| Field | Value |
|-------|-------|
| **Date** | 2026-03-24 |
| **Objective** | Triage 34 open GitHub issues by complexity (LOW/MEDIUM/HIGH), then execute all LOW-complexity items in parallel using isolated worktree agents |
| **Outcome** | Successful — 19 issues resolved (16 implemented + 3 closed as already-resolved), all tests/lint/mypy pass |

## When to Use

- You need to resolve multiple independent GitHub issues in a single session
- Issues are small enough to be handled by individual sub-agents (single-file fixes, test additions, config changes)
- You want to maximize throughput by running agents in parallel without merge conflicts
- The repository has a CI/pre-commit setup that needs verification after merging changes

## Verified Workflow

### Quick Reference

```bash
# 1. Fetch all open issues
gh issue list --repo OWNER/REPO --state open --json number,title,labels --limit 100

# 2. Launch 3 parallel classification agents (split issues into batches)
# Each agent runs: gh issue view N --repo OWNER/REPO
# Returns: issue number, title, complexity (LOW/MEDIUM/HIGH), justification

# 3. Launch N parallel implementation agents with worktree isolation
# Agent tool params: isolation: "worktree"
# Each agent commits its own changes in the worktree

# 4. Cherry-pick all worktree commits into main branch
git cherry-pick <commit-hash>  # for each agent's commit

# 5. Fix any conflicts, run verification
pixi run pytest tests/ -v
pixi run ruff check hephaestus/ tests/
pixi run mypy hephaestus/
```

### Detailed Steps

1. **Classify issues in parallel** — Launch 3 Explore/general-purpose agents, each handling a batch of issues. Classification criteria:
   - **LOW**: Single-file changes, regex fixes, test additions, doc updates, config changes
   - **MEDIUM**: Multi-file changes, new features, refactoring with risk, security-sensitive
   - **HIGH**: Architectural changes, cross-repo coordination, full directory restructures

2. **Deduplicate** — Before launching agents, identify overlapping issues (e.g., two issues both requesting a justfile, or two issues both requesting CI matrix expansion). Group duplicates into single agent tasks.

3. **Check pre-existing state** — Some issues may already be resolved. Verify with file existence checks, `git ls-files`, etc. Close these with `gh issue close N --comment "reason"`.

4. **Stash uncommitted work** — Before cherry-picking, stash any uncommitted changes: `git stash push -m "description" -- file1 file2`

5. **Launch parallel agents with `isolation: "worktree"`** — Group related issues into ~10 agents. Each agent:
   - Reads relevant source files
   - Makes the fix
   - Runs targeted tests
   - Commits with conventional commit message including `Closes #N`

6. **Cherry-pick sequentially** — Chain cherry-picks: `git cherry-pick <hash1> && git cherry-pick <hash2> && ...`

7. **Resolve conflicts** — Read conflicted files, edit to resolve, `git add`, `git cherry-pick --continue`

8. **Run full verification** — Unit tests, integration tests, ruff, mypy, pre-commit

9. **Fixup commit** — If verification reveals formatting or type issues introduced by agents, fix and commit separately.

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
|---------|----------------|---------------|----------------|
| Cherry-pick pixi.toml | Agent removed `version` line from pixi.toml, but the base branch had a different version of pixi.toml | CONFLICT in pixi.toml because both sides modified the same region | When agents modify config files that other agents also touch (even indirectly via lockfile changes), expect cherry-pick conflicts. Resolve by reading the conflict markers and choosing the correct resolution. |
| git stash pop after cherry-picks | Stashed SECURITY.md changes conflicted with the cherry-picked SECURITY.md update from the docs agent | Both the stash and the cherry-pick modified SECURITY.md's version table | Stash before cherry-picking, but be aware that stashed files may conflict with cherry-picked changes. Use `git add` to mark resolution, not `git checkout --` (blocked by safety net). |
| `assert tomllib is not None` for mypy fix | Used `assert` to narrow the type of a `Module | None` variable | ruff S101 rule forbids `assert` in production code | Use `if x is None: raise ImportError(msg)` instead of `assert` for type narrowing in production code |

## Results & Parameters

**Agent grouping strategy** (10 agents for 19 issues):

```yaml
# Group by theme/file overlap to minimize conflicts
agent-1: CI/CD (issues #44, #55, #56, #58) → .github/workflows/test.yml, pyproject.toml
agent-2: Justfile (issues #35, #48) → justfile (new)
agent-3: Docs (issues #23, #47) → CLAUDE.md, SECURITY.md
agent-4: Logging fix (issue #59) → logging/utils.py, tests/
agent-5: IO fix (issue #53) → io/utils.py, tests/
agent-6: Validation fix (issue #64) → validation/config_lint.py, tests/
agent-7: Security fix (issue #62) → utils/helpers.py, tests/
agent-8: Test coverage (issues #27, #61) → tests/ only
agent-9: Integration tests (issue #52) → tests/ only
agent-10: Housekeeping (issues #42, #46, #57, #63) → pixi.toml, gh issue close
```

**Key metrics:**
- 10 agents launched in single message (maximum parallelism)
- All agents completed in ~60-210 seconds
- 596 unit tests + 105 integration tests pass
- 0 ruff errors, 0 mypy errors
- 14 total commits (3 original + 10 agents + 1 fixup)

**Critical: Agent prompt requirements:**
- Tell agents to READ files before editing
- Tell agents to RUN targeted tests after changes
- Tell agents to COMMIT with conventional commit messages including `Closes #N`
- Include specific file paths and line numbers in the prompt

## Verified On

| Project | Context | Details |
|---------|---------|---------|
| ProjectHephaestus | Batch resolution of 19 LOW-complexity GitHub issues | [notes.md](./skills/tooling-parallel-worktree-issue-batch.notes.md) |
