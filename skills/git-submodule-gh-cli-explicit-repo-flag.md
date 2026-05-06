---
name: git-submodule-gh-cli-explicit-repo-flag
description: "Always pass --repo <owner/submodule-repo> to every gh invocation when working on a git submodule from inside a parent meta-repo, and use git -C <submodule-path> for git operations. The gh CLI auto-detects repos from CWD/origin (which resolves to the parent meta-repo, not the submodule), and Bash tool calls do not preserve CWD between invocations so `cd submodule && gh pr create` silently targets the parent. Use when: (1) working on a git submodule from inside its parent meta-repo, (2) gh pr create fails with 'No commits between' or 'Base ref must be a branch', (3) gh pr view returns 'no pull requests found' for a PR you just opened, (4) git status from the parent shows a submodule as modified after submodule branch ops, (5) stacked PR workflows in submodule repos, (6) Bash-tool environments where CWD does not persist between calls (Claude Code, Cursor, etc.)."
category: tooling
date: 2026-05-05
version: "1.0.0"
user-invocable: false
verification: verified-ci
tags:
  - submodule
  - meta-repo
  - gh-cli
  - github-cli
  - bash-cwd
  - explicit-repo-flag
  - stacked-prs
  - claude-code
  - cursor
---

# Git Submodule + gh CLI: Always Pass --repo Explicitly

## Overview

| Field | Value |
|-------|-------|
| **Date** | 2026-05-05 |
| **Objective** | Eliminate the silent wrong-repo footgun where `gh pr create` (and every other `gh` subcommand) auto-detects the parent meta-repo instead of the submodule when the working directory's `origin` remote resolves to the parent. |
| **Outcome** | Successful. After adopting the explicit `--repo` rule, the Atlas v0.2.0 ship cycle (PRs #444, #445, #446, #447, #448, #456 in ProjectArgus and #272 in Odysseus) had zero further wrong-repo errors. |
| **Verification** | verified-ci — applied to a 7-PR release cycle across two repositories, all PRs landed on the correct repo. |

## When to Use

- You are working on a git submodule from inside its parent meta-repo (e.g., `Odysseus/infrastructure/ProjectArgus/`)
- `gh pr create` fails with a confusing error like `No commits between <base> and <head>`, `Base ref must be a branch`, or `Head sha can't be blank`
- `gh pr view <num>` returns `no pull requests found` immediately after you "successfully" opened one
- `gh run view`, `gh pr checks`, `gh api repos/...` all return data that does not match what you just pushed
- `git status` from the parent meta-repo shows the submodule as `modified` after you run any branch op inside the submodule
- You are in a Bash-tool harness (Claude Code, Cursor, Aider, etc.) where each shell command runs in a fresh subshell and CWD does **not** persist between calls
- Stacked PR workflows: rebasing `feat/B` onto `feat/A` after `feat/A` was squash-merged

## Verified Workflow

### Quick Reference

Every `gh` and `git` command form that needs explicit targeting when working on a submodule.

```bash
# ----------------------------------------------------------------------
# Convention used below:
#   PARENT      = absolute path to the parent meta-repo (e.g., Odysseus)
#   SUBMODULE   = absolute path to the submodule checkout
#                 (e.g., $PARENT/infrastructure/ProjectArgus)
#   SUB_REPO    = the submodule's GitHub slug
#                 (e.g., HomericIntelligence/ProjectArgus)
#   PARENT_REPO = the parent's GitHub slug (e.g., HomericIntelligence/Odysseus)
#   BR          = the feature branch you are working on in the submodule
# ----------------------------------------------------------------------

# --- Git operations: ALWAYS use `git -C $SUBMODULE` ---
git -C "$SUBMODULE" status
git -C "$SUBMODULE" checkout -b "$BR"
git -C "$SUBMODULE" add path/to/file
git -C "$SUBMODULE" commit -m "..."
git -C "$SUBMODULE" push -u origin "$BR"
git -C "$SUBMODULE" log --oneline -10
git -C "$SUBMODULE" diff origin/main...HEAD
git -C "$SUBMODULE" fetch origin
git -C "$SUBMODULE" rebase origin/main
git -C "$SUBMODULE" push --force-with-lease origin "$BR"

# Stacked PRs: skip a now-squashed-away commit by giving rebase an explicit base
git -C "$SUBMODULE" rebase --onto origin/main <merged-base-sha> "$BR"

# --- gh PR lifecycle: ALWAYS pass --repo $SUB_REPO ---
gh pr create   --repo "$SUB_REPO" --base main --head "$BR" \
               --title "..." --body "..."
gh pr view     --repo "$SUB_REPO" <num>
gh pr view     --repo "$SUB_REPO" <num> --json state,mergeable,statusCheckRollup
gh pr list     --repo "$SUB_REPO" --head "$BR" --json number --jq '.[0].number'
gh pr edit     --repo "$SUB_REPO" <num> --add-label ready
gh pr merge    --repo "$SUB_REPO" <num> --auto --rebase    # or --squash
gh pr close    --repo "$SUB_REPO" <num>
gh pr checks   --repo "$SUB_REPO" <num>
gh pr comment  --repo "$SUB_REPO" <num> --body "..."
gh pr review   --repo "$SUB_REPO" <num> --approve

# --- gh CI / Actions on the submodule's repo ---
gh run list    --repo "$SUB_REPO" --branch "$BR" --limit 5
gh run view    --repo "$SUB_REPO" <run_id>
gh run view    --repo "$SUB_REPO" <run_id> --log-failed
gh run rerun   --repo "$SUB_REPO" <run_id> --failed
gh workflow run --repo "$SUB_REPO" <workflow.yml>

# --- gh API (lowest-level — same rule applies) ---
gh api repos/"$SUB_REPO"/branches/main
gh api repos/"$SUB_REPO"/pulls/<num>
gh api repos/"$SUB_REPO"/commits/main/check-runs
gh api repos/"$SUB_REPO"/actions/runs --jq '.workflow_runs[0]'

# --- gh issues / labels / releases on the submodule ---
gh issue create   --repo "$SUB_REPO" --title "..." --body "..."
gh issue list     --repo "$SUB_REPO" --state open
gh release create --repo "$SUB_REPO" v0.2.0 --notes "..."
gh label list     --repo "$SUB_REPO"

# --- After submodule branch ops, bump the parent's pin ---
git -C "$PARENT" status                        # submodule shows as modified
git -C "$PARENT" add path/to/submodule         # stages the new SHA
git -C "$PARENT" commit -m "chore: bump <Submodule> to <new-sha>"
git -C "$PARENT" push -u origin <parent-branch>
gh pr create --repo "$PARENT_REPO" --base main --head <parent-branch> \
             --title "chore: bump <Submodule>" --body "..."
```

### Detailed Steps

1. **Set absolute-path variables once at the top of the session.** Never rely on
   relative paths or `cd` to "navigate into" the submodule — they will not survive
   the next Bash tool invocation.

   ```bash
   PARENT=/home/me/Projects/Odysseus
   SUBMODULE="$PARENT/infrastructure/ProjectArgus"
   SUB_REPO=HomericIntelligence/ProjectArgus
   PARENT_REPO=HomericIntelligence/Odysseus
   BR=feat/atlas-nats-spine
   ```

2. **All git ops in the submodule use `git -C "$SUBMODULE"`.** This is the
   git equivalent of explicit `--repo`: it tells git which working tree to act on
   regardless of the shell's CWD.

3. **All gh ops on the submodule's repo use `--repo "$SUB_REPO"`.** This is
   non-negotiable: even if you believe the shell is in the submodule directory,
   it is not (in Bash-tool harnesses), and even if it were, `gh` may still pick
   up a stray `origin` from a parent worktree under some configurations.

4. **Push, then open the PR with `--repo` explicitly:**

   ```bash
   git -C "$SUBMODULE" push -u origin "$BR"
   gh pr create --repo "$SUB_REPO" --base main --head "$BR" \
                --title "feat: ..." --body "..."
   ```

5. **Enable auto-merge on the correct repo:**

   ```bash
   PR_NUM=$(gh pr list --repo "$SUB_REPO" --head "$BR" \
                       --json number --jq '.[0].number')
   gh pr merge --repo "$SUB_REPO" "$PR_NUM" --auto --rebase
   ```

6. **After the submodule PR merges, bump the parent's pin** in a separate
   parent-repo PR. This is a normal `git status` in the parent that shows the
   submodule as `modified` because the parent tracks a specific commit and the
   submodule is now pointing at a newer one.

7. **For stacked PRs** where `feat/A` was squash-merged and `feat/B` was stacked
   on top, rebase `feat/B` with an explicit `--onto` base so git skips the
   now-squashed-away commits, then push with `--force-with-lease`:

   ```bash
   MERGED_BASE_SHA=$(git -C "$SUBMODULE" merge-base feat/A feat/B)
   git -C "$SUBMODULE" rebase --onto origin/main "$MERGED_BASE_SHA" feat/B
   git -C "$SUBMODULE" push --force-with-lease origin feat/B
   ```

### Why The Bash Tool's CWD Non-Persistence Is The Meta-Cause

In Bash-tool harnesses (Claude Code, Cursor, Aider, and similar), each
`Bash(...)` tool call runs in a **fresh subshell**. The user-visible `cwd` is
reset to the project root between calls. This means:

```bash
# Call 1
cd /home/me/Odysseus/infrastructure/ProjectArgus
# Call 2  -- starts back at /home/me/Odysseus/, NOT inside ProjectArgus
gh pr create --base main --head feat/x --body "..."
# gh now reads /home/me/Odysseus/.git/config, finds the Odysseus origin,
# and creates a PR against HomericIntelligence/Odysseus where feat/x
# does not exist.
```

Two robust workarounds, both of which the Quick Reference uses:

1. **`git -C <path> ...` for git** — git's `-C` flag changes directory for the
   single command without touching the shell.
2. **`gh ... --repo <slug>` for gh** — bypasses gh's CWD-based repo auto-detection
   entirely.

Avoid the brittle `cd $SUBMODULE && gh ...` chain. Even if it works in one tool
call, the next call in the conversation will start in the wrong directory and
silently target the wrong repo.

### Symptoms Decoder

If you see one of these, suspect the `--repo` footgun first:

| Error / Symptom | What's Actually Happening |
|---|---|
| `pull request create failed: GraphQL: No commits between <base> and <head>` | The branch does not exist on the auto-detected (wrong) repo. |
| `pull request create failed: GraphQL: Base ref must be a branch` | Same as above — repo lookup landed on the parent which has neither branch. |
| `Head sha can't be blank, Base sha can't be blank` | Same root cause; `gh` cannot resolve either ref because it is querying the wrong repo. |
| `gh pr view <num>` returns `no pull requests found` even though you "just opened it" | The PR opened on a different repo (or did not actually open at all and gh swallowed the error). |
| `gh run view` shows runs that have nothing to do with your branch | You're listing runs for the parent meta-repo. |
| `git status` in the parent shows the submodule as `modified` | Normal: the parent tracks one SHA, the submodule HEAD has moved. Bump the pin in the parent. |

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
|---------|----------------|---------------|----------------|
| 1 | `cd /home/.../Odysseus/infrastructure/ProjectArgus && gh pr create --base main --head feat/atlas-nats-spine --body "..."` | The Bash tool runs each command in a fresh subshell. The `cd` did not persist. `gh pr create` ran from `/home/.../Odysseus`, where `gh` auto-detected the `HomericIntelligence/Odysseus` remote and tried to open the PR there. The branch did not exist on Odysseus, producing a misleading "No commits between" error. | Never rely on `cd` in Bash-tool harnesses. Use `git -C <path>` and `gh --repo <slug>`. |
| 2 | After the first failure, retried `gh pr create` without `--repo` thinking it was a transient API issue | Same wrong-repo lookup; same misleading error message. Lost ~15 minutes chasing a phantom "branches diverged" theory. | "No commits between" almost always means wrong-repo lookup, not literal empty diff. Suspect repo targeting first. |
| 3 | Pushed the submodule branch with `git push -u origin <branch>` from inside what appeared to be the submodule directory | Inside a submodule, `origin` is correctly the submodule's remote — this part actually works in many harnesses. The trap is that gh does NOT use the same logic; gh walks up to find a `.git` directory and may pick the parent. So git can succeed while gh silently fails on the next line. | git's submodule semantics (`origin` per submodule) are not the same as gh's repo auto-detection. Treat them independently — always use `-C` and `--repo`. |
| 4 | After a squash-merge of stacked PR `feat/A`, rebased `feat/B` (stacked on top of A) onto `origin/main` with plain `git rebase origin/main` | The stacked branch contained the now-squashed-away commits from `feat/A`, so the rebase replayed them and produced merge conflicts and duplicate work. | After a squash-merge, use `git rebase --onto origin/main <merged-base-sha> <branch>` to skip the squashed-away commits, then push with `--force-with-lease`. |
| 5 | After bumping the submodule pin in the parent, ran `gh pr create` (no `--repo`) from the parent worktree to open the parent PR | This one happened to work because CWD was the parent. But the success was coincidental — relying on it normalizes the brittle pattern. | Even when CWD "happens to be" the right repo, pass `--repo` explicitly. Robust scripts do not depend on shell state. |

## Results & Parameters

### Concrete copy-paste-able submodule workflow (full release cycle)

```bash
# --- one-time per session: set absolute paths and slugs ---
export PARENT=/home/me/Projects/Odysseus
export SUBMODULE="$PARENT/infrastructure/ProjectArgus"
export SUB_REPO=HomericIntelligence/ProjectArgus
export PARENT_REPO=HomericIntelligence/Odysseus
export BR=feat/atlas-nats-spine

# --- 1. branch + commit + push in the submodule ---
git -C "$SUBMODULE" fetch origin
git -C "$SUBMODULE" checkout -b "$BR" origin/main
# ... edit files via your editor or tool ...
git -C "$SUBMODULE" add -A
git -C "$SUBMODULE" commit -m "feat: add NATS spine"
git -C "$SUBMODULE" push -u origin "$BR"

# --- 2. open the PR on the SUBMODULE repo (not the parent) ---
gh pr create --repo "$SUB_REPO" --base main --head "$BR" \
  --title "feat: add NATS spine" \
  --body "$(cat <<'EOF'
## Summary
- Adds the NATS spine for Atlas v0.2.0
EOF
)"

# --- 3. enable auto-merge on the correct repo ---
PR_NUM=$(gh pr list --repo "$SUB_REPO" --head "$BR" --json number --jq '.[0].number')
gh pr merge --repo "$SUB_REPO" "$PR_NUM" --auto --rebase

# --- 4. wait for CI / merge, then bump the parent pin ---
gh pr view --repo "$SUB_REPO" "$PR_NUM" --json state,mergedAt
NEW_SHA=$(git -C "$SUBMODULE" rev-parse origin/main)

git -C "$PARENT" checkout -b chore/bump-projectargus
git -C "$PARENT" add infrastructure/ProjectArgus
git -C "$PARENT" commit -m "chore: bump ProjectArgus to ${NEW_SHA:0:12}"
git -C "$PARENT" push -u origin chore/bump-projectargus

gh pr create --repo "$PARENT_REPO" --base main --head chore/bump-projectargus \
  --title "chore: bump ProjectArgus to ${NEW_SHA:0:12}" \
  --body "Tracks ${SUB_REPO}#${PR_NUM}"
PARENT_PR_NUM=$(gh pr list --repo "$PARENT_REPO" --head chore/bump-projectargus \
                           --json number --jq '.[0].number')
gh pr merge --repo "$PARENT_REPO" "$PARENT_PR_NUM" --auto --rebase
```

### Verified across (Atlas v0.2.0 release cycle, 2026-05)

| Repo | PRs | Result |
|---|---|---|
| `HomericIntelligence/ProjectArgus` | #444, #445, #446, #447, #448, #456 | All landed on the correct repo with `--repo` explicit |
| `HomericIntelligence/Odysseus` | #272 | Parent submodule pin bump landed cleanly |

Time lost before adopting the rule: ~15 min (single misdiagnosed `gh pr create`).
Time lost after adopting the rule: 0 min across 7 PRs.

## Verified On

| Project | Context | Details |
|---------|---------|---------|
| ProjectArgus / Odysseus | Atlas v0.2.0 release cycle (PRs #444 #445 #446 #447 #448 #456 in ProjectArgus, #272 in Odysseus), 2026-05-05 | Submodule PR cycle from inside the Odysseus meta-repo using Claude Code's Bash tool. |
