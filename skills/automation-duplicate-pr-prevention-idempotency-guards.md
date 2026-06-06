---
name: automation-duplicate-pr-prevention-idempotency-guards
description: "Use when: (1) an automation pipeline creates duplicate PRs for one issue, (2) two PRs land on the same branch, (3) a worktree manager rebuilds a branch from base and discards remote history, (4) gh pr create runs unconditionally without checking for an existing PR, (5) making issue->branch->PR creation idempotent"
category: tooling
date: 2026-06-05
version: "1.0.0"
user-invocable: false
verification: verified-ci
tags: [automation, duplicate-pr, idempotency, git-worktree, gh-pr-create, ls-remote, pr-creation]
---

# Automation Duplicate-PR Prevention via Idempotency Guards

## Overview

| Field | Value |
| ------- | ------- |
| **Date** | 2026-06-05 |
| **Objective** | Stop an issue-implementation pipeline from creating duplicate PRs for a single issue by adding idempotency guards at the worktree, PR-creation, and prompt boundaries |
| **Outcome** | Success — three root causes fixed in PR HomericIntelligence/ProjectHephaestus#1022 (Closes #1018); full automation suite (1091 tests) green; dependency-scan passed after rebase |
| **Category** | tooling |

The real failure: ProjectHephaestus's issue-implementation pipeline created
**three** PRs for issue #768 — #942 (CLOSED), #962 (MERGED), #967 (OPEN) — two of
them on the **same branch** `768-auto-impl`, with divergent history. The pipeline
had no idempotency at any of the three creation chokepoints.

## When to Use

Use this skill when:

- An automation pipeline emits more than one PR for the same issue
- Two PRs target the same head branch (often `<issue>-auto-impl`)
- A worktree/branch manager rebuilds a branch from base and silently discards
  commits that exist only on `origin`
- `gh pr create` is called unconditionally with no "does a PR already exist?" check
- You are making the `issue -> branch -> PR` flow idempotent so re-runs (including
  re-runs from a different machine) converge instead of duplicating

## Verified Workflow

The minimal robust guard set installs an idempotency check at **each** of the three
creation chokepoints. All three are needed — fixing only one leaves the others able
to duplicate.

### 1. Worktree manager: detect remote-only branches before rebuilding from base

Root cause: `worktree_manager.create_worktree` checked branch existence
**locally only** (`git rev-parse --verify <branch>`) and never consulted the
remote. A remote-only `<issue>-auto-impl` branch (pushed by a prior loop on another
machine) was rebuilt from BASE, **discarding the remote commits** → divergent
branch → a second, divergent PR.

Fix: add `_remote_branch_exists(branch)` using
`git ls-remote --heads origin <branch>` and check for the `refs/heads/<branch>`
substring. Be defensive: any failure (non-zero exit, parse error) → treat the
branch as absent and fall back to base. When the branch is absent locally but
present on origin, **extend** the remote history instead of overwriting it:

```bash
git fetch origin <branch>
git worktree add <path> -b <branch> origin/<branch>
```

Extract `_add_worktree_for_branch` / `_local_branch_exists` helpers so
`create_worktree` stays under the C901 complexity limit (≤10).

### 2. gh_pr_create: check for an existing open PR at the single creation chokepoint

Root cause: `github_api.gh_pr_create` ran `gh pr create` **unconditionally** — no
existing-PR check at the one place every caller funnels through.

Fix: add `_find_open_pr_for_head(branch)` that runs:

```bash
gh pr list --head <branch> --json number,state
```

Parse the JSON for **any** state, return the first OPEN PR number, and return
`None` on parse failure. Call it right after the policy asserts; if an OPEN PR
already exists, log it and **return that PR** instead of creating a duplicate.
Because every caller routes through this one chokepoint, the guard protects them
all at once.

### 3. Implementation prompt: instruct the agent to reuse an existing PR

Root cause: the implementation prompt's "Create a pull request" step gave **no**
instruction to check for or reuse an existing PR.

Fix: in `prompts/implementation.py`, instruct the agent to run
`gh pr list --head <branch>` FIRST and reuse an existing open PR rather than
opening a second one.

### Quick Reference

| Chokepoint | File | Guard added | Mechanism |
| ----------- | ----- | ----------- | --------- |
| Worktree creation | `worktree_manager.py` | `_remote_branch_exists` | `git ls-remote --heads origin <branch>`; extend via `git fetch` + `worktree add -b <branch> origin/<branch>` |
| PR creation | `github_api.py` | `_find_open_pr_for_head` | `gh pr list --head <branch> --json number,state`; return OPEN PR instead of creating |
| Agent prompt | `prompts/implementation.py` | reuse instruction | `gh pr list --head <branch>` first, reuse open PR |

**Key design decision (KISS tradeoff):** keep `find_pr_for_issue` **OPEN-only**
(`--state open`). Do NOT broaden it to skip on closed/merged PRs. A closed/merged
prior PR legitimately means the issue may need fresh work; broadening adds a
false-skip failure mode without fixing the confirmed bug (duplicate OPEN PRs +
divergent branches), which guards (1) and (2) fully address.

**Testing insight:** when you prepend a pre-flight subprocess call
(`ls-remote`, or `pr list`) ahead of existing calls, existing tests that assert
`mock.call_count == N` or use ordered `side_effect = [...]` BREAK — update the
counts and prepend the new call's mocked result. Also, lazy attributes matter: in
`WorktreeManager` the base-branch detection is lazy (only fires when
`self.base_branch` is accessed), so the run-call ORDER differs per code path — the
remote-extend path never accesses `base_branch`, so it never triggers a detect
call. Tests must set `side_effect` in the exact order each path triggers.

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
| --------- | ---------------- | --------------- | ---------------- |
| Local-only branch existence check | `create_worktree` used `git rev-parse --verify <branch>` only | A remote-only `<issue>-auto-impl` branch (pushed by another machine's loop) was invisible, so the branch was rebuilt from BASE and the remote commits were discarded → divergent duplicate PR | Always consult `git ls-remote --heads origin <branch>` before rebuilding from base; extend remote history with `git fetch` + `worktree add -b <branch> origin/<branch>` |
| Unconditional PR creation | `gh_pr_create` always ran `gh pr create` | A re-run opened a second PR on the same head branch | Guard the single creation chokepoint with `gh pr list --head <branch>` and return the existing OPEN PR |
| Broaden `find_pr_for_issue` to skip on closed PRs | Make the existing issue->PR lookup also skip when a closed/merged PR exists | False skips when an issue legitimately needs fresh work after an abandoned PR; adds a new failure mode without fixing the duplicate-OPEN-PR + divergent-branch bug | Keep `find_pr_for_issue` OPEN-only; enforce idempotency at the creation/worktree boundaries instead |

## Results & Parameters

| Parameter | Value |
| ----------- | ------- |
| Source files changed | `hephaestus/automation/worktree_manager.py`, `hephaestus/automation/github_api.py`, `hephaestus/automation/prompts/implementation.py` |
| Helpers added | `_remote_branch_exists`, `_find_open_pr_for_head`, `_add_worktree_for_branch`, `_local_branch_exists` |
| Test files updated | `tests/.../test_worktree_manager.py`, `tests/.../test_github_api.py`, `tests/.../test_prompts.py` |
| Verification | Full automation suite (1091 tests) green; dependency-scan passed after rebase |
| PR | https://github.com/HomericIntelligence/ProjectHephaestus/pull/1022 |
| Issue | #1018 (root duplicate-PR example: issue #768 → PRs #942 CLOSED, #962 MERGED, #967 OPEN) |

## Key Insight

Idempotency for an `issue -> branch -> PR` pipeline must be enforced at **every**
creation chokepoint, not just one. Duplicate PRs arose from three independent gaps:
a worktree manager blind to remote-only branches, an unconditional `gh pr create`,
and a prompt that never told the agent to reuse an existing PR. Guard each boundary
with a cheap pre-flight check (`git ls-remote`, `gh pr list --head`), and resist the
temptation to "fix" it by broadening the open-PR lookup to also skip closed/merged
PRs — that trades a duplicate bug for a false-skip bug. KISS: guard at the
boundaries that actually create the duplicates.
