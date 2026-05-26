---
name: precommit-scope-full-pr-diff-not-current-edit
description: "Before `git push` for a PR, run pre-commit against the full PR diff (every file changed since the merge-base with the target branch), not just the files of the most recent edit. `pre-commit run --files X Y Z` only checks X, Y, Z; a sub-agent's earlier commit can carry stale-formatter content that no one re-checks locally and that only fails in CI. Use when: (1) handing off work between sub-agents that each ran their own per-file pre-commit, (2) making fixup commits after a delegated change and preparing to push, (3) any time `pre-commit run --all-files` is considered too slow and you reach for `--files`, (4) diagnosing CI mojo-format / ruff-format / formatter failures on files you did not personally edit in this session, (5) writing a pre-push checklist for any repo where formatter hooks rewrite files."
category: ci-cd
date: 2026-05-25
version: "1.0.0"
user-invocable: false
verification: verified-ci
tags:
  - pre-commit
  - mojo-format
  - sub-agent-handoff
  - pr-diff
  - ci-parity
  - formatter
  - pre-push
---

# Pre-commit Scope: Full PR Diff, Not Current Edit

## Overview

| Field | Value |
| ------- | ------- |
| **Date** | 2026-05-25 |
| **Objective** | Stop CI formatter failures caused by files committed by an earlier sub-agent that the human's fixup pre-commit invocation never re-checked, by scoping the pre-push pre-commit run to the entire PR diff rather than the most recent edit. |
| **Outcome** | One round-trip saved per delegated-work PR; verified-ci on ProjectOdyssey PR #5453. |
| **Verification** | verified-ci - the failure mode happened on PR #5453; after applying `pixi run pre-commit run --from-ref origin/main --to-ref HEAD`, the next push went green. |

## When to Use

- Handing off work between sub-agents that each ran their own per-file `pre-commit run --files ...`
- Making fixup commits after a delegated change and preparing to push
- Any time `pre-commit run --all-files` is considered too slow and you reach for `--files`
- Diagnosing CI mojo-format / ruff-format / formatter failures on files you did not personally edit this session
- Writing a pre-push checklist for any repo where formatter hooks rewrite files
- Reviewing a sub-agent's "pre-commit passed" report before trusting it for push readiness

## Verified Workflow

### Quick Reference

```bash
# --- CANONICAL PRE-PUSH CHECK (ref-based, cleanest) ---
pixi run pre-commit run --from-ref origin/main --to-ref HEAD

# --- ALTERNATIVE: explicit file list spanning the whole PR diff ---
git diff --name-only "$(git merge-base HEAD origin/main)" HEAD \
  | xargs pixi run pre-commit run --files

# --- WHAT NOT TO DO BEFORE PUSH ---
# Checks ONLY the files you list — sub-agent's earlier files are skipped:
pixi run pre-commit run --files train.sh analyze_phases.py README.md  # WRONG SCOPE

# --- AFTER PUSH: catch CI-only hooks ---
gh pr checks --watch
```

### Detailed Steps

#### Pre-push protocol when sub-agents have committed in this PR

1. Identify the target branch (usually `origin/main`).
2. Run `pixi run pre-commit run --from-ref origin/main --to-ref HEAD`.
   - This covers EVERY file changed in the PR diff, not just files in the working tree or in HEAD.
   - It catches formatter drift on files committed by earlier sub-agents.
3. If hooks rewrite files, `git add` the rewrites and create a NEW commit (never `--no-verify`, never `--amend` once the original commit is shared).
4. Push.
5. Run `gh pr checks --watch` to catch CI-only hooks (test-coverage validators, license checks) that the local pre-commit framework cannot run.

#### Why the per-file invocation gives false confidence

- `pre-commit run --files X Y Z` runs each hook on the literal list `[X, Y, Z]`. Hooks do not auto-expand to staged or recently changed files.
- The repo's installed pre-commit hook (`.git/hooks/pre-commit`) runs only on staged files. If a sub-agent staged + committed file `A`, then you stage + commit file `B`, neither commit's hook ever saw the other file under the current formatter baseline.
- `pre-commit run --all-files` is the only built-in that is guaranteed safe, but it is often skipped because it is slow on large repos. `--from-ref/--to-ref` is the targeted equivalent for a PR.

#### Detecting a sub-agent's `SKIP=hook-id` bypass

- Read the sub-agent's transcript for `SKIP=` in any `git commit` invocation.
- If found, re-run that hook explicitly on the sub-agent's files: `pixi run pre-commit run <hook-id> --from-ref origin/main --to-ref HEAD`.
- The most common offender is `SKIP=mojo-format` from sub-agents running on GLIBC-older hosts (see `mojo-glibc-compatibility.md` in ProjectOdyssey).

#### Formatter version drift between sub-agent runs

- Even with full-diff scope, a sub-agent running in a slightly different pixi env can produce different formatter output. If the pre-push run rewrites files, that is the symptom — commit the rewrites.
- If you suspect persistent drift, run `pixi run mojo format --version` (or analog) in both envs and reconcile via `pixi.lock` before any future delegation.

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
| --------- | ---------------- | --------------- | ---------------- |
| Trust sub-agent's "pre-commit passed" report | Sub-agent ran `pre-commit run --files <its own files>`, reported pass, committed, and pushed responsibility back to the orchestrator | The sub-agent's invocation only covered the files it edited; the orchestrator's later fixup invocation only covered the orchestrator's files. Two non-overlapping partial checks do not equal full coverage. | Aggregate pre-commit scope across ALL commits in the PR, not per-commit. The orchestrator owns the pre-push check. |
| `pre-commit run --files X Y Z` on the fixup-edit files | Ran pre-commit on the three files the orchestrator personally edited in the fixup commit (train.sh, analyze_phases.py, README.md) | Caught the orchestrator's issues; missed the sub-agent's `model.mojo` and `run_train.mojo` because `--files` is a literal list, not a "files I might care about" heuristic | Scope the pre-push invocation to the full PR diff: `--from-ref origin/main --to-ref HEAD` |
| Push and let CI catch it | Skipped any local pre-push pre-commit run; relied on `gh pr checks --watch` | Did catch the failure, but cost a 3-5 minute CI round-trip plus an extra style-only commit polluting PR history | One local `--from-ref/--to-ref` invocation upstream is dramatically cheaper than a CI round-trip |
| `pre-commit run --all-files` as the pre-push gate | Used the universal "safe" invocation | Slow on large repos (multi-minute), discouraging consistent use. Engineers drop back to `--files` and the gap reappears. | `--from-ref/--to-ref` gives full PR-diff coverage at PR-diff cost, not whole-repo cost. Preferred over `--all-files` for routine pre-push. |
| Assume the installed git `pre-commit` hook on commit covered everything | Relied on `.git/hooks/pre-commit` firing during each `git commit` to enforce hygiene | The installed hook only runs against STAGED files. Sub-agent's stage + commit of file A does not retroactively re-check file B after the orchestrator commits B. | The installed hook is a per-commit-staged-files gate, not a per-PR gate. Pre-push needs an explicit full-diff invocation. |
| `--amend` the sub-agent's commit to apply formatting | Tried to fix the formatter drift without polluting history with a style-only commit | The sub-agent's commit was already pushed (or about to be), and amending shared history requires force-push, which is forbidden on shared branches per the org's git safety protocol | Create a NEW commit with the formatter fixes. Style-noise in PR history is acceptable; rewriting shared history is not. |
| `SKIP=mojo-format` on a host without Mojo, expecting CI to fix it later | Sub-agent ran on an older-GLIBC host where mojo-format would not execute, set `SKIP=mojo-format`, committed, and reported "pre-commit passed (mojo-format skipped due to environment)" | The orchestrator did not re-run `mojo-format` on the sub-agent's files because the orchestrator's `--files` list did not include them. CI then failed mojo-format. | When a sub-agent reports a `SKIP=`, the orchestrator MUST run that specific hook against the sub-agent's files (or, simpler, the full PR diff) before pushing. |
| Add `pre-commit run --all-files` to a git pre-push hook | Tried to enforce the gate locally via a pre-push hook calling `--all-files` | Multi-minute push delay killed adoption; engineers disabled the hook within a week | Use `pre-commit run --from-ref @{push} --to-ref HEAD` in pre-push hooks, not `--all-files`. PR-diff scope is both correct and fast. |

## Results & Parameters

### Canonical Pre-Push Command

```bash
# For any PR targeting main:
pixi run pre-commit run --from-ref origin/main --to-ref HEAD

# Generalized (works for any base):
pixi run pre-commit run --from-ref "$(git merge-base HEAD @{u})" --to-ref HEAD
```

### Optional: Git pre-push Hook Snippet

Add to `.git/hooks/pre-push` (do NOT commit to the repo unless the team agrees; this is a personal-machine convenience):

```bash
#!/usr/bin/env bash
set -euo pipefail
# Run pre-commit against the PR diff vs the upstream branch.
# Far faster than --all-files; far more correct than --files <recent edits>.
remote_ref="$(git rev-parse --abbrev-ref --symbolic-full-name '@{u}' 2>/dev/null || echo origin/main)"
exec pixi run pre-commit run --from-ref "${remote_ref}" --to-ref HEAD
```

### Decision Matrix: Which `pre-commit run` Variant to Use When

| Scenario | Command | Why |
| ---------- | --------- | ----- |
| During development, after editing one file | `pre-commit run --files <file>` | Fast, scoped to the change you just made |
| Before `git commit` of staged changes | (installed hook fires automatically on staged files) | Default mechanism |
| Before `git push` of a PR | `pre-commit run --from-ref origin/main --to-ref HEAD` | Covers full PR diff including sub-agent commits |
| After upgrading a formatter or hook version | `pre-commit run --all-files` | Formatter baseline changed; whole repo must be re-checked |
| Onboarding to a new repo | `pre-commit run --all-files` | Establish baseline before first contribution |

### Expected Outputs

- `pixi run pre-commit run --from-ref origin/main --to-ref HEAD` exits 0 with no diff output when the PR is push-ready.
- If a formatter hook rewrites files, exit code is non-zero AND the working tree shows modifications; `git status` lists the rewritten files. Stage and commit the rewrites before pushing.

## Verified On

| Project | Context | Details |
| --------- | --------- | --------- |
| ProjectOdyssey | PR #5453 ([link](https://github.com/HomericIntelligence/ProjectOdyssey/pull/5453)) — Mojo refactor delegated to sub-agent; sub-agent's `model.mojo` and `run_train.mojo` passed the sub-agent's per-file pre-commit, failed CI mojo-format after orchestrator's fixup push. Applying `pixi run pre-commit run --from-ref origin/main --to-ref HEAD` before the next push produced a green CI run. | verified-ci |

## References

- [pre-commit docs: `run` command](https://pre-commit.com/#pre-commit-run)
- [`pre-commit-hooks-and-linting-config`](pre-commit-hooks-and-linting-config.md) — canonical pre-commit configuration guide; this skill is a narrow companion focused on invocation scope
- [ProjectOdyssey `.claude/shared/pr-workflow.md`](https://github.com/HomericIntelligence/ProjectOdyssey/blob/main/.claude/shared/pr-workflow.md) — PR workflow that this skill supplements
