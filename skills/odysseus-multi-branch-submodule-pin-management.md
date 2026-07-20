---
name: odysseus-multi-branch-submodule-pin-management
description: >-
  Manage submodule pins across multiple Odysseus branches with rebase, cherry-pick avoidance,
  and justfile recipe collision resolution. Use when: (1) updating a submodule SHA on a feature
  branch while main has a different pin, (2) rebasing an Odysseus feature branch onto main after
  justfile changes on both sides, (3) cherry-picking a submodule pointer update between branches
  fails with CONFLICT (submodule), (4) CI "Harden checks" job fails with justfile recipe
  redefinition error after rebase, (5) branch-switching causes missing files/directories in the
  working tree, (6) running `git submodule update --remote <path>` produces unexpected
  modifications to OTHER submodules in `git status` (the selective-vs-all foot-gun), (7) doing
  a partial pin bump where only some submodules are eligible because others have open PRs,
  (8) a `git cherry-pick` of a pin-bump commit onto a fresh branch off main fails with
  `CONFLICT (submodule): ... commits don't follow merge-base` and you WANT to keep the
  cherry-picked commit (not abort) — resolve by checking out the target SHA inside the
  submodule and `git add`-ing it, since it is a pointer that cannot fast-forward, not a code merge.
category: ci-cd
date: 2026-07-18
version: "1.2.0"
user-invocable: false
verification: verified-ci
history: odysseus-multi-branch-submodule-pin-management.history
tags:
  - odysseus
  - submodule
  - pin
  - rebase
  - justfile
  - multi-branch
  - cherry-pick
  - force-with-lease
  - submodule-update-remote
  - selective-pin-bump
  - merge-base
  - cherry-pick-conflict-resolution
---

# Odysseus Multi-Branch Submodule Pin Management

## Overview

| Field | Value |
| ------- | ------- |
| **Date** | 2026-07-18 (v1.2.0); 2026-05-16 (v1.1.0); originally 2026-05-04 (v1.0.0) |
| **Objective** | Manage submodule pins across Odysseus branches: rebase, cherry-pick avoidance AND in-place cherry-pick pointer-conflict resolution, justfile recipe collisions, AND safe selective `--remote` pin bumps on long-lived clones |
| **Outcome** | Successful — original 2026-05-04 CI hardening shipped; 2026-05-16 partial pin-bump PR #284 shipped with EXACTLY the 5 intended bumps (8 unintended rewinds caught); 2026-07-18 cherry-pick pointer-conflict resolution produced a clean commit bumping all 15 pins as intended |
| **Verification** | verified-ci for the established workflow (Odysseus PR #284, 2026-05-16); the 2026-07-18 cherry-pick pointer-conflict resolution is verified-local (executed this session, clean commit produced; its own skill-PR gate not yet observed green) |

## When to Use

- A submodule's upstream PR (e.g., ProjectHephaestus adding `install.sh`) merges to main while your Odysseus feature branch still pins the old SHA
- You need to cherry-pick a submodule pointer update between branches but get `CONFLICT (submodule)`
- A `git cherry-pick <pin-bump-sha>` onto a fresh branch off main fails with `CONFLICT (submodule): ... commits don't follow merge-base` and you want to KEEP the cherry-picked commit (a dedicated pins PR), not abort it
- Rebasing an Odysseus feature branch fails because both main and your branch added justfile recipes
- CI "Harden checks" fails with `Recipe 'X' first defined on line N is redefined on line M`
- Switching branches in the same Odysseus worktree causes `ls tests/install/` or similar to fail with "no such file or directory"
- You need to force-push a rebased branch without clobbering concurrent remote changes
- Running `git submodule update --remote <path>` and seeing unexpected modifications to OTHER submodules in `git status` (the selective-vs-all foot-gun)
- Partial pin bumps (some submodules have open PRs blocking the bump; only bumping the ones with empty queues)

## Verified Workflow

### Quick Reference

```bash
# --- Submodule pin update on feature branch ---
git -C <submodule-path> fetch origin
git -C <submodule-path> checkout main
git -C <submodule-path> pull --ff-only origin main
git -C <submodule-path> log --oneline -3   # verify the right commits are present
git add <submodule-path>
git commit -m "chore(deps): update <submodule> submodule to include <feature>"
git push origin <feature-branch>

# --- Safe rebase + push workflow ---
git fetch origin main
git rebase origin/main
# resolve conflicts (justfile most common), then:
git add <resolved-files>
git rebase --continue
git push --force-with-lease origin <feature-branch>
# wait for GitHub to re-evaluate merge status
sleep 15 && gh pr view <PR> --repo HomericIntelligence/Odysseus --json mergeable,mergeStateStatus

# --- Check for justfile recipe collisions before adding ---
just --list 2>&1 | grep "redefined\|error"
grep "^<recipe-name>" justfile   # check if name already exists
```

### Detailed Steps

#### Step 1: Confirm working branch before any file operations

```bash
git branch --show-current
```

**Why:** Branch switching causes `scripts/install/` and `tests/install/` directories to appear/disappear. Always confirm the active branch before running `ls`, `podman build`, or other path-dependent commands.

#### Step 2: Avoid cherry-picking submodule pointer updates

When a submodule's feature branch merges to main and you want that SHA on your feature branch, **do not** cherry-pick the submodule commit from another branch. Instead, directly advance the submodule on the target branch:

```bash
# On your feature branch:
git -C shared/ProjectHephaestus fetch origin
git -C shared/ProjectHephaestus checkout main
git -C shared/ProjectHephaestus pull --ff-only origin main

# Verify the new SHA has what you need
git -C shared/ProjectHephaestus log --oneline -3

# Pin the new SHA in Odysseus
git add shared/ProjectHephaestus
git commit -m "chore(deps): update ProjectHephaestus submodule to include install.sh"
git push origin <feature-branch>
```

#### Step 3: Detect justfile recipe collisions before adding new recipes

Before adding a new recipe to `justfile`, check for name collisions:

```bash
# Show all defined recipe names
just --list 2>&1

# Check if your intended name is already defined
grep "^install\b\|^install-dev\b\|^install-check\b" justfile
```

If the name exists, prefix with a scope. For Odysseus ecosystem recipes: use `ecosystem-` prefix (e.g., `ecosystem-install`, `ecosystem-install-dev`, `ecosystem-install-check`).

#### Step 4: Rebase feature branch onto main

```bash
git fetch origin main
git rebase origin/main
```

If the justfile has conflicts from both sides adding content at the end:

```bash
# The conflict markers show two completely new blocks
# Resolution: keep BOTH, with their own section comments
# Edit the file to remove conflict markers and keep all content
git add justfile
git rebase --continue
```

#### Step 5: Force-push with safety

After a rebase, the branch history has changed so a regular push is rejected:

```bash
git push --force-with-lease origin <feature-branch>
```

`--force-with-lease` refuses if the remote has commits you haven't fetched, preventing accidental overwrites of concurrent work.

#### Step 6: Wait for GitHub merge status re-evaluation

After a force-push, GitHub shows `mergeStateStatus: DIRTY` for 10-30 seconds while it re-evaluates:

```bash
sleep 15 && gh pr view <PR-number> --repo HomericIntelligence/Odysseus --json mergeable,mergeStateStatus
```

### Safe Selective Pin Bump

When bumping a SUBSET of submodule pins in a meta-repo (e.g., only the submodules whose bundle PRs have merged; deferring others that still have open PRs), `git submodule update --remote <path1> <path2>` is NOT safely selective on a long-lived working clone. Other submodules whose working-tree HEADs have drifted from their pinned SHAs (from prior session work, fetches, or branch checkouts) will surface as modified in `git status` — and `--remote` may initialize them as a side effect, producing unintended pin rewinds if blindly staged.

**The 6-step verified-safe procedure** (used successfully on Odysseus PR #284, 2026-05-16):

```bash
cd ~/Odysseus
git fetch origin main
git checkout -b chore/refresh-pins-partial-<date> origin/main

# 1. Reset ALL submodules to the meta-repo's pinned SHAs FIRST.
#    This puts the working clone in a known state before --remote touches anything.
git submodule update --init --recursive

# 2. Run --remote ONLY on the submodules you intend to bump.
for sub in infrastructure/ProjectHermes control/ProjectNestor provisioning/ProjectKeystone provisioning/ProjectTelemachy shared/Mnemosyne; do
  git submodule update --remote "$sub"
done

# 3. Confirm git status shows EXACTLY the submodules you bumped (and nothing else).
git status --short

# 4. If status shows other submodules modified (foot-gun!), reset them individually
#    — NEVER `git add .` to hide the surprise.
for unintended in <list>; do
  git submodule update --init "$unintended"
done

# 5. Verify each bumped pin is on origin/main of the target submodule.
for sub in infrastructure/ProjectHermes control/ProjectNestor ...; do
  sha=$(git -C "$sub" rev-parse HEAD)
  git -C "$sub" branch -r --contains "$sha" | grep -E "origin/main$" || echo "FAIL: $sub not on origin/main"
done

# 6. Stage + commit ONLY the intended paths — never `git add .`.
git add control/ProjectNestor infrastructure/ProjectHermes provisioning/ProjectKeystone provisioning/ProjectTelemachy shared/Mnemosyne
git status --short  # confirm only those are staged
git commit -m "chore(submodules): refresh pins ..."
```

**Critical rules:**

1. **ALWAYS** `git submodule update --init --recursive` BEFORE `--remote` on a long-lived clone — never trust the working tree to be on pinned SHAs.
2. **ALWAYS** inspect `git status --short` before staging — if you see modified entries you didn't intend to bump, reset them individually.
3. **NEVER** `git add .` for submodule bumps. Always stage explicit paths.
4. Cross-reference [[multi-repo-pr-orchestration-swarm-pattern]] for the broader guardrail: do NOT bump a submodule pin while that submodule has an open PR in flight (defer it).

### Resolve a Cherry-Pick Submodule Pointer Conflict (keep the commit)

> _(verified-local — executed this session on Odysseus; the clean commit was produced, but
> this skill PR's own CI gate has not yet been observed green.)_

Step 2 above says to AVOID cherry-picking a submodule pointer when you can just advance the pin
directly. But sometimes you genuinely want the **cherry-picked commit itself** — e.g. a pin-bump
commit was accidentally made on a feature branch (that also carries other, unrelated submodule
bumps) and you want a clean, dedicated pins PR: `git checkout -b <new> origin/main && git
cherry-pick <bump-sha>`.

That cherry-pick fails with:

```text
CONFLICT (submodule): Merge conflict in provisioning/Myrmidons
Failed to merge submodule provisioning/Myrmidons (commits don't follow merge-base)
```

**Why:** the source branch recorded the submodule at commit `A` (a bump NOT present on main);
main records it at commit `B`. The cherry-picked diff is "`A` → target", which git cannot replay
onto main's `B` because `A` is not an ancestor of `B` — there is no linear merge-base for the
submodule POINTER. This is **not** a text/content conflict; there is nothing to hand-merge.

For a "bump pins to latest/target" intent, the correct resolution is always "take the target SHA
recorded in the commit you are cherry-picking". Resolve it in place — do NOT abort, do NOT hunt
for text conflict markers:

```bash
# 1. Read the TARGET submodule SHA straight out of the commit being cherry-picked.
git ls-tree <bump-sha> provisioning/Myrmidons
#    -> 160000 commit <target-sha>    provisioning/Myrmidons  (SHA is the 3rd field)

# 2. Check that exact SHA out INSIDE the submodule.
git -C provisioning/Myrmidons checkout <target-sha>

# 3. Stage the resolved pointer in the superproject.
git add provisioning/Myrmidons

# 4. Continue the cherry-pick. If a non-executable / noisy pre-commit hook blocks it,
#    bypass hooks ONLY for the continue (the content is already correct):
git cherry-pick --continue --no-edit
# git -c core.hooksPath=/dev/null cherry-pick --continue   # only if hook noise blocks it

# 5. Verify the final pins BEFORE pushing — all intended bumps, nothing rewound.
git submodule status
git diff origin/main --stat   # confirms exactly the pins you intended (e.g. all 15) changed
```

**Key insight:** treat every `CONFLICT (submodule)` as "pick the right SHA, then `git add`",
never as a code merge. When the intent is "bump to latest", the right SHA is the one recorded in
the cherry-picked commit's tree (`git ls-tree <bump-sha> <path>`), so step 1 resolves it exactly.

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
|---------|----------------|---------------|----------------|
| Cherry-pick submodule pointer update | `git cherry-pick <sha>` to copy submodule pin from one branch to another | Submodule pointer conflicts when both branches have different SHAs: `CONFLICT (submodule): Merge conflict in shared/ProjectHephaestus` | Abort cherry-pick; on target branch, run `git -C <submodule> pull --ff-only origin main` then `git add <submodule> && git commit` directly |
| Standard push after rebase | `git push origin <branch>` after `git rebase origin/main` | Rejected as non-fast-forward — rebase rewrites history | Use `git push --force-with-lease origin <branch>` |
| Using `install` as justfile recipe name | Named ecosystem installer recipe `install` | Existing justfile already had `install PREFIX` (cmake binary install recipe) — CI "Harden checks" caught the collision | Check `just --list` for name collisions first; use namespaced prefix like `ecosystem-install` |
| Assuming branch is stable during background tasks | Ran background `podman build` while performing git operations in the foreground | Git checkout in the foreground changed working tree; subsequent `ls tests/install/` failed with "no such file" because the branch switched away | Always run `git checkout <branch>` before any branch-specific file operations; treat the working tree as volatile during multi-branch git sessions |
| Checking GitHub merge status immediately after force-push | `gh pr view --json mergeable` right after `git push --force-with-lease` | Shows `CONFLICTING` / `DIRTY` for 10-30 seconds while GitHub re-evaluates | `sleep 15 && gh pr view <PR> --json mergeable,mergeStateStatus` |
| Trust `git submodule update --remote <path1> <path2>` to be selective | Ran `git submodule update --remote infrastructure/ProjectHermes control/ProjectNestor ...` on a long-lived working clone; expected only the 5 listed submodules to show modified in `git status` | 8 OTHER submodules showed modified because their working-tree HEADs had drifted from pinned SHAs in prior session work; `--remote` (and the implicit `--init`) surfaced/advanced them as a side effect | ALWAYS run `git submodule update --init --recursive` to reset the working clone FIRST, then `--remote` only on intended paths; inspect `git status --short` before staging |
| `git add .` after `git submodule update --remote` | Staged everything visible in `git status` after bumping pins, including unintended submodule rewinds | Would have shipped 8 incorrect pin downgrades in the Odysseus PR #284 pin-bump (caught only by manual inspection) | NEVER `git add .` for submodule bumps — always `git add <explicit-path-1> <explicit-path-2> ...` and re-run `git status --short` to confirm only intended paths staged |
| Plain cherry-pick of a pin-bump commit onto a branch off main | `git checkout -b <new> origin/main && git cherry-pick <bump-sha>` to move an accidental pin-bump commit to a dedicated PR | `CONFLICT (submodule): ... commits don't follow merge-base` — the source branch's submodule SHA is not an ancestor of main's, so the pointer cannot fast-forward | Do NOT abort; resolve in place: `git ls-tree <bump-sha> <path>` for the target SHA, `git -C <path> checkout <target-sha>`, `git add <path>`, then `git cherry-pick --continue` |
| Assumed the submodule conflict was a file-content clash | Searched the working tree for text conflict markers / tried to hand-merge after `CONFLICT (submodule)` | It is purely a submodule POINTER that cannot fast-forward — there is no text to merge; time wasted looking for `<<<<<<<` markers | Treat every `CONFLICT (submodule)` as "pick the right SHA, then `git add`", not a code merge; for a bump-to-latest intent the right SHA is the cherry-picked commit's tree entry |

## Results & Parameters

### Submodule pin facts

- Odysseus has 13+ submodules, each pinned to a SHA **per branch**
- When a submodule's upstream PR merges to main: the local working copy advances, but the Odysseus branch still records the old SHA
- `git add <submodule-path>` + commit updates the recorded SHA on the **current** branch only
- Other branches retain their own submodule SHAs — each branch is independent

### Harden checks CI job validates

- markdownlint on all `.md` files
- pixi.toml consistency
- justfile syntax (`just --list`) — catches recipe redefinition collisions
- symlink validity

### Rebase conflict: keep both justfile sections

When both main and the feature branch added recipes at the end of `justfile`, conflict markers show two complete new blocks. Resolution: keep ALL content from both sides, separated by section headers:

```justfile
# === Recipes from main ===
main-recipe:
    ...

# === Recipes from feature branch ===
ecosystem-install:
    ...
```

### Rename collision pattern

| Original name (collided) | Renamed to |
|--------------------------|------------|
| `install` | `ecosystem-install` |
| `install-dev` | `ecosystem-install-dev` |
| `install-check` | `ecosystem-install-check` |

## Verified On

| Project | Context | Details |
|---------|---------|---------|
| Odysseus | feat/issue-22-ci-hardening — CI hardening PR with justfile extensions and submodule updates | Session 2026-05-04 |
| Odysseus | PR #284 — partial pin bump sweep (5 of 10 in-scope submodules bumped: Nestor, Hermes, Keystone, Telemachy, Mnemosyne; 5 deferred because their bundle PRs were still open). Caught 8 unintended pin rewinds via manual `git status` inspection before staging. | Session 2026-05-16 — verified the 6-step Safe Selective Pin Bump procedure |
| Odysseus | Cherry-picked a pin-bump commit onto a fresh branch off main; hit `CONFLICT (submodule): ... commits don't follow merge-base` on `provisioning/Myrmidons`; resolved via `git ls-tree` target SHA + `git -C <path> checkout` + `git add` + `cherry-pick --continue`. Final `git diff origin/main --stat` showed all 15 pins bumped as intended. | Session 2026-07-18 (verified-local) — clean commit produced; skill-PR CI gate not yet observed green |
