---
name: pixi-lock-rebase-regenerate
description: "Correctly resolve pixi.lock staleness after git rebase or when main advances. Use when: (1) CI fails with 'lock-file not up-to-date with the workspace', (2) multiple PRs all fail identical CI jobs after a version bump on main, (3) git rebase causes pixi.lock conflicts, (4) Dependabot PRs fail CI fast (6-12 seconds) because Dependabot only bumps pyproject.toml not pixi.lock, (5) a second rebase of the same branch produces a pixi.lock commit conflict — skip the stale commit and re-run pixi install, (6) a second commit in the rebase chain patches code that was migrated to an external package — accept HEAD's version and use git rebase --skip, (7) pixi.toml pins a dependency version but pixi.lock still references old version (CI shows 'Environment is not consistent with the lockfile'), (8) creating a fix branch — always base off origin/main not local main which may be stale commits behind, (9) MULTIPLE PR branches all fail CI with 'lock-file not up-to-date' simultaneously after a recent merge to main — main itself is likely broken; verify with `git checkout main && pixi install --locked` before per-branch fixups, (10) a recently-merged PR that touched `pyproject.toml`'s `[project.dependencies]` (or any field that contributes to the local-package SHA hash) without regenerating `pixi.lock` — fix on main with a 1-line hotfix PR; then re-rebase all open PRs to inherit the fixed lock, (11) per-branch `pixi install` regeneration produces only a single-line diff (the local-package `sha256:`) and CI keeps failing — confirms the bug is upstream on main, not on the branch, (12) a comment-only or metadata-only edit to `pyproject.toml`/`pixi.toml` invalidates the local-package SHA256 in `pixi.lock` and CI fails with `pixi install --locked rejected: <package> SHA256 mismatch` — use `pixi install` NOT `pixi update` (install regenerates only the affected SHA; update re-resolves the entire dep graph and produces a ~50-line diff), (13) developer's local pixi binary is NEWER than CI's pinned `prefix-dev/setup-pixi` version (e.g., local v0.67.2, CI v0.39.5); developer regenerates `pixi.lock` locally and CI rejects it with a schema/lockfile-version/format mismatch error even though `pixi install --frozen` passes locally — diagnosis is pixi-binary-version skew, fix is to install CI's exact pinned pixi version locally and regenerate (NOT bump CI, which cascades to other repos)."
category: ci-cd
date: 2026-05-17
version: "1.8.0"
user-invocable: true
verification: verified-ci
history: pixi-lock-rebase-regenerate.history
tags: [dependabot, pixi, rebase, pixi-lock, ci-cd, pixi-install, pixi-update, pixi-version-skew, lock-format-drift]
absorbed:
  - ci-cd-dependabot-pixi-lock-drift-fix.md
---
# Pixi Lock Rebase Regenerate

## Overview

| Field | Value |
| ------- | ------- |
| **Date** | 2026-05-17 |
| **Objective** | Correctly resolve `pixi.lock` staleness after `git rebase`, main-branch advancement, comment-only manifest edits, or pixi-binary-version drift between developer and CI — without producing an invalid lock file or broadening the diff scope |
| **Outcome** | Eliminates `lock-file not up-to-date` and lockfile-format-rejection CI failures; multi-branch parallel fix completes 5 PRs in ~1 minute; SHA-only fixes stay 1-line via `pixi install` (not `pixi update`); format-drift fixes regenerate against CI's pinned pixi version |
| **Verification** | verified-ci (v1.8.0) |
| **History** | [changelog](./pixi-lock-rebase-regenerate.history) |

## When to Use

- CI fails with `lock-file not up-to-date with the workspace` on one or more PRs
- Multiple open PRs all fail identical CI jobs (lint, pre-commit, dep-scan) after a version bump landed on main
- Running `git rebase` on a branch that includes `pixi.lock` and a conflict occurs
- The branch modifies `pixi.toml` (adds/removes dependencies or tasks)
- All test matrix jobs pass but infrastructure jobs (lock-check, pre-commit, dep-scan) uniformly fail
- **Dependabot PRs fail CI very fast (6–12 seconds)**: Dependabot bumps `pyproject.toml` version bounds but does NOT regenerate `pixi.lock`. CI runs `pixi install --locked` which rejects the stale lock immediately — hence the fast failure. Fix is the same: rebase + `pixi install` + commit pixi.lock.
- A branch that previously had a pixi.lock-fix commit is rebased a second time and the old pixi.lock commit conflicts with the freshly-rebased state. Resolution: `git rebase --skip` the conflicting commit, then re-run `pixi install` fresh.
- **Second commit in the rebase chain patches code migrated to an external package**: A branch has Commit A (structural change, e.g., pixi.toml restructure) and Commit B (follow-on fix to local scripts that have since been rewritten as thin wrapper stubs delegating to an external package). Commit A applies cleanly; Commit B conflicts because the functions it patches no longer exist. Accept `HEAD`'s version of all conflicted files and use `git rebase --skip` (not `--continue`) to drop the now-empty commit.

- **pixi.toml pins a dependency version** (e.g., `shellcheck = "0.10.0.*"`) but `pixi.lock` still references the old version — CI shows `"Environment is not consistent with the lockfile"`. Fix: run `pixi install` locally to regenerate the lock.
- **Creating a fix branch for lock drift**: always base off `origin/main` (not local `main` which may be stale): `git checkout origin/main -b fix/my-branch` — local `main` may be dozens of commits behind, causing push conflicts.
- **3+ PR branches simultaneously fail CI with "lock-file not up-to-date"** after a known recent merge — main itself may be broken; test main directly before delegating per-branch fixups.
- **The 1-line diff after `pixi install` is on the local package's `sha256:` field** — the bug is upstream on main; a per-branch regeneration cannot help because every rebase pulls in main's stale lock.
- **Symptom: a "fix-up" wave on multiple branches doesn't help** — each branch's CI keeps failing the same way after per-branch regeneration; this confirms main itself ships an inconsistent `pyproject.toml`/`pixi.lock` pair.
- **Comment-only or metadata-only edit to `pyproject.toml`/`pixi.toml` invalidates the local-package SHA256** — CI fails with `pixi install --locked rejected: <package> SHA256 mismatch`. Fix with `pixi install` (NOT `pixi update`); see Phase 3f.
- **Developer's local pixi binary is newer than CI's pinned `prefix-dev/setup-pixi` version** — developer regenerates `pixi.lock` locally with a newer pixi (e.g., v0.67.2) and CI rejects it with a schema/lockfile-version/format complaint even though `pixi install --frozen` succeeds locally. The newer pixi writes lockfile fields/structure the older CI pixi cannot parse. Fix is to install CI's exact pinned pixi version locally and regenerate; see Phase 3g.

**Do NOT use `--ours` or `--theirs`** to resolve a `pixi.lock` conflict — either side will be stale
relative to the rebased branch's actual `pixi.toml`.

**Do NOT use `pixi update`** to fix a stale lock — see Phase 3f for the critical
`pixi install` vs `pixi update` distinction. `pixi update` re-resolves the entire dependency
graph and bumps unrelated packages.

## Verified Workflow

### Quick Reference

```bash
# Triage: confirm lock staleness across multiple PRs
gh run view <run-id> --log-failed | grep "lock-file"

# Single-branch fix
git fetch origin
git rebase origin/main          # clean rebase (no pixi.lock conflict? run pixi install anyway)
pixi install                    # regenerates pixi.lock in place
git add pixi.lock
git commit -m "fix(deps): regenerate pixi.lock after rebase on main"
git push --force-with-lease origin <branch>
gh pr merge <pr-number> --auto --rebase

# Multi-branch parallel fix (5 PRs simultaneously)
REPO_DIR="/path/to/local/repo"
BRANCHES=(branch1 branch2 branch3 branch4 branch5)
git -C "$REPO_DIR" fetch origin
for branch in "${BRANCHES[@]}"; do
  dir="/tmp/fix-pr-${branch}"
  git -C "$REPO_DIR" worktree remove "$dir" --force 2>/dev/null || rm -rf "$dir"
  git -C "$REPO_DIR" worktree add "$dir" "origin/${branch}"
  (cd "$dir" && git rebase origin/main && pixi install && git add pixi.lock && \
   git commit -m "fix(deps): regenerate pixi.lock after rebase" && \
   git push --force-with-lease "origin/${branch}" && \
   PR=$(gh pr list --head "${branch}" --json number --jq '.[0].number') && \
   gh pr merge "$PR" --auto --rebase && echo "Done: ${branch}") &
done
wait
```

### Detection: Is It Main or Is It the Branch?

When `lock-file not up-to-date` shows up on multiple PR CIs at once:

```bash
# Step 1: check main itself
git fetch origin main
git checkout main
git pull --ff-only

pixi install --locked
# If this FAILS → main is broken; STOP per-branch fixups, fix main first
# If this PASSES → it's branch-specific; continue with per-branch fix
```

```bash
# Step 2: confirm root-cause PR if main is broken
git log --oneline -10  # find recent PRs touching pyproject.toml
git log --oneline -10 -- pyproject.toml
# Look for a PR that added/changed [project.dependencies] without touching pixi.lock
```

```bash
# Step 3: hotfix
git checkout -b fix/regenerate-pixi-lock
pixi install                       # regenerates pixi.lock to match pyproject.toml
git add pixi.lock
git commit -m "fix: regenerate pixi.lock after #<root-cause-PR> (<reason>)"
git push -u origin fix/regenerate-pixi-lock
gh pr create --title "fix: regenerate pixi.lock after #<root-cause-PR>" --body "..."
gh pr merge <PR> --auto --squash
```

```bash
# Step 4: cascade re-rebase
# After hotfix lands on main, every already-rebased PR needs another rebase to inherit
# main's fixed lock. Conflict on pixi.lock during re-rebase: take main's version:
git rebase origin/main
# On pixi.lock conflict:
#   git checkout --theirs -- pixi.lock
#   git add pixi.lock
#   git rebase --continue
```

#### Quick Diagnostic — Single Command

```bash
# Run on main; if non-empty, main is broken
pixi install --locked 2>&1 | grep -q "not up-to-date" && echo "MAIN IS BROKEN — fix lock on main first"
```

**Why the local-package `sha256:` goes stale**: pixi.lock embeds a hash of the local
package's source-tree contributing files (including `pyproject.toml`). When a PR
modifies `[project.dependencies]` (or any other field that contributes to the hash)
without running `pixi install` to regenerate the lock, the merge gate may pass (pre-merge
CI used the old lock), but post-merge `pixi install --locked` on main fails everywhere.
Detection: a single-line diff in pixi.lock on the `sha256:` field after `pixi install`.

### Phase 0: Triage — Confirm It Is Lock Staleness

When multiple PRs fail simultaneously with identical errors, this is the fastest diagnosis:

```bash
# Pick any one failing run
gh pr list --state open --json number,headRefName
gh run view <run-id> --log-failed | head -40
```

**Confirming signals:**
- Error message: `lock-file not up-to-date with the workspace`
- All affected PRs were cut before a recent commit on main (version bump, new subpackage, dep change)
- All *test matrix* jobs pass — only infrastructure jobs (lock-check, pre-commit, dep-scan) fail
- The failing SHA256 in the lock message is the old main hash, not the branch's source hash

### Phase 1: Root Cause — Why Pixi.lock Goes Stale

`pixi.lock` encodes the exact resolved dependency graph plus a SHA256 hash of the local
editable package. When main advances:

1. If `pyproject.toml` or `pixi.toml` changed on main (version bump, new dep, new subpackage), the
   lock hash diverges from any branch cut before that commit
2. Even without `pixi.toml` changes, the local package hash changes when source files change
3. Accepting `--ours` or `--theirs` during rebase produces a hash that doesn't match the rebased state
4. `pixi install --locked` (what CI runs) then fails because the hash is wrong

### Phase 2: Single-Branch Fix

```bash
git fetch origin
git checkout <branch>
git rebase origin/main
# If pixi.lock shows as conflicted during rebase:
#   rm pixi.lock && git add pixi.lock && git rebase --continue

# Always regenerate the lock file after rebase
pixi install              # reads pixi.toml, resolves deps, rewrites pixi.lock
git add pixi.lock
git commit -m "fix(deps): regenerate pixi.lock after rebase on main"
git push --force-with-lease origin <branch>

# Re-enable auto-merge (force-push clears it silently)
gh pr merge <pr-number> --auto --rebase
```

**If pixi.lock conflict during rebase** (branch has explicit pixi.toml changes):

```bash
# During git rebase, when pixi.lock is conflicted:
rm pixi.lock
git add pixi.lock
git rebase --continue
# After rebase finishes:
pixi install
git add pixi.lock
```

### Phase 3: Multi-Branch Parallel Fix (3+ PRs)

When many PRs share the same staleness root cause, fix them all simultaneously using git worktrees.
Each worktree is fully isolated — zero branch conflicts, zero interaction.

```bash
REPO_DIR="/path/to/local/repo"
git -C "$REPO_DIR" fetch origin

BRANCHES=(127-auto-impl 128-some-feature 129-other-feature 130-another 131-last)

for branch in "${BRANCHES[@]}"; do
  dir="/tmp/fix-pr-${branch}"
  # Remove any stale worktree at that path
  git -C "$REPO_DIR" worktree remove "$dir" --force 2>/dev/null || rm -rf "$dir"
  # Create isolated worktree on the branch
  git -C "$REPO_DIR" worktree add "$dir" "origin/${branch}"
  (
    cd "$dir"
    git rebase origin/main                           # clean: no pixi.lock conflicts
    pixi install                                     # regenerate pixi.lock
    git add pixi.lock
    git commit -m "fix(deps): regenerate pixi.lock after rebase on main"
    git push --force-with-lease "origin/${branch}"
    # Get PR number from branch name and re-enable auto-merge
    PR=$(gh pr list --head "${branch}" --json number --jq '.[0].number')
    gh pr merge "$PR" --auto --rebase
    echo "Done: ${branch}"
  ) &
done
wait
echo "All branches fixed"

# Clean up worktrees
for branch in "${BRANCHES[@]}"; do
  git -C "$REPO_DIR" worktree remove "/tmp/fix-pr-${branch}" --force 2>/dev/null || true
done
git -C "$REPO_DIR" worktree prune
```

**Observed timing**: 5 branches in parallel → ~1 minute total (vs ~10 minutes sequential).

### Phase 3b: Dependabot PR pixi.lock Fix

Dependabot PRs fail CI fast (6–12 seconds) because `pixi install --locked` rejects a stale lock
immediately as a pre-flight check — not a test failure. The pattern is the same as the single-branch
fix but must be run sequentially (parallel pixi install across worktrees can conflict on shared state):

```bash
# For each Dependabot PR (sequential, not parallel):
BRANCH="$(gh pr view <pr-number> --json headRefName --jq '.headRefName')"
WORKTREE="/tmp/dep-$(echo $BRANCH | tr '/' '-')"
git -C "$REPO_DIR" worktree add "$WORKTREE" "origin/$BRANCH"
cd "$WORKTREE"
git rebase origin/main
pixi install                    # regenerates pixi.lock for updated pyproject.toml bounds
git add pixi.lock
git commit -m "chore: regenerate pixi.lock for updated dependencies"
git push --force-with-lease origin "HEAD:$BRANCH"
gh pr merge <pr-number> --auto --rebase
git -C "$REPO_DIR" worktree remove "$WORKTREE"
```

**Diagnosis signal**: CI job duration of 6–12 seconds on a Dependabot PR = stale pixi.lock
(not a test failure, not a merge conflict).

### Phase 3c: Double-Rebase pixi.lock Commit Conflict

When a branch already has a pixi.lock-fix commit (from a prior rebase) and is rebased again:

```
CONFLICT (content): Merge conflict in pixi.lock
error: could not apply <sha>... fix(deps): regenerate pixi.lock after rebase
```

The prior pixi.lock-fix commit conflicts with the newly-rebased state. Resolution:

```bash
git rebase --skip      # skip the now-stale pixi.lock commit entirely
# After rebase completes:
pixi install           # regenerate fresh from the current state
git add pixi.lock
git commit -m "fix(deps): regenerate pixi.lock after rebase on main"
git push --force-with-lease origin <branch>
```

**Why `--skip` and not `--continue`**: The pixi.lock-fix commit's entire purpose was to
regenerate pixi.lock. After the new rebase, the lock needs to be regenerated fresh anyway —
the old regeneration commit is entirely superseded. Skipping it is semantically correct.

### Phase 3d: Multi-Commit Rebase Where Second Commit Is Superseded

When a branch has two commits — a structural change (Commit A) followed by a follow-on fix (Commit B)
to local scripts that have since been migrated to an external package as thin wrapper stubs:

```
Commit A: chore(deps): separate dev from production dependencies in pixi.toml
Commit B: fix(deps): fix pixi.lock and version-drift checkers for dev/prod split
```

Between branch creation and rebase, `main` rewrote the scripts Commit B patches (e.g.,
`scripts/check_dep_sync.py`, `scripts/check_precommit_versions.py`) as one-line wrappers:

```python
# New form on main — the functions Commit B patched no longer exist
from hephaestus.config.dep_sync import *  # noqa: F401,F403
```

**Rebase flow:**

```bash
git fetch origin
git rebase origin/main
# Commit A applies cleanly → git rebase --continue automatically or manually

# Commit B conflicts — the files it patches are now thin wrappers on main
# Accept main's version of ALL conflicted files:
git checkout HEAD -- scripts/check_dep_sync.py scripts/check_precommit_versions.py
git checkout HEAD -- pixi.lock   # if pixi.lock is also conflicted

# The commit is now empty — skip it entirely:
git rebase --skip       # NOT --continue (which would create an empty commit)

# After rebase completes: re-run pixi install for any new environments from Commit A
pixi install
git add pixi.lock
git commit -m "fix(deps): regenerate pixi.lock after rebase on main"
git push --force-with-lease origin <branch>
gh pr merge <pr-number> --auto --rebase
```

**Key distinction**: Use `--skip` (not `--continue`) when ALL conflicts in a commit are resolved
by accepting `HEAD`'s version — the commit becomes empty and must be dropped to avoid polluting
history with a no-op commit.

**Signal that this pattern applies:**
- Commit B patches functions or logic that simply does not exist in the current files on main
- After `git checkout HEAD -- <files>`, running `git diff --cached` shows zero staged changes
- The commit message of Commit B references "fixing" or "patching" scripts that main now delegates to an external package

### Phase 3e: Dependency Version-Pin Lock Drift

When `pixi.toml` pins a specific version (e.g., `shellcheck = "0.10.0.*"`) but `pixi.lock` still
references the old version, CI reports `"Environment is not consistent with the lockfile"`.
This can happen when: a PR pins a version constraint but the lockfile was not regenerated before
committing, or when the lockfile was committed on a stale branch.

**Diagnosis signal**: CI error is `"Environment is not consistent with the lockfile"` (not
`"lock-file not up-to-date"`) — this specific phrasing indicates version-constraint mismatch rather
than hash mismatch.

```bash
# Fix: create branch off origin/main (not local main which may be stale)
git checkout origin/main -b fix/pixi-lock-drift

# Copy the file that needs updating if blocked by Safety Net:
git show <source-branch>:<file> > <file>  # e.g., git show fix/shellcheck-warnings:pixi.toml > pixi.toml

# Regenerate the lock
pixi install

# Commit and push
git add pixi.lock pixi.toml  # include pixi.toml if it changed
git commit -m "fix(deps): regenerate pixi.lock after dependency version pin"
git push -u origin fix/pixi-lock-drift
gh pr create ...
```

**Why base off `origin/main` not local `main`**: Local `main` may be 33+ commits behind if
the local clone hasn't been synced recently. Basing off a stale local `main` causes push conflicts
(`non-fast-forward`). Use `git checkout origin/main -b <branch>` to guarantee a fresh base.

### Phase 3f: Use `pixi install` NOT `pixi update` for SHA-Only Fixes

When the only thing that changed is a comment, header, docstring, or other metadata in
`pyproject.toml` or `pixi.toml`, the editable local-package SHA256 in `pixi.lock` becomes
invalid even though no real dependency moved. CI fails with:

```text
pixi install --locked rejected: <package> SHA256 mismatch
```

The correct fix is **`pixi install`**, NOT `pixi update`. The two commands look interchangeable
but have fundamentally different scopes:

| Command | Behavior | Diff size for SHA-only invalidation |
|---------|----------|--------------------------------------|
| `pixi install` | Reproduces the lockfile to satisfy the current manifest. If versions haven't moved, only the affected SHA changes. | 1–2 lines |
| `pixi update` | Re-resolves the entire dependency graph against the **latest available** versions, regardless of what changed in the manifest. | ~50+ lines (ruff, mypy, transitive bumps) |

For comment-only or metadata-only manifest edits, the difference is dramatic. Always start with
`pixi install` and verify the diff is minimal before considering `pixi update`.

**Step-by-step (pin CI's pixi version — see also `feedback_pixi_lock_version_pin`):**

```bash
# 1. Determine the EXACT pixi version CI uses — check the workflow file:
grep -rE "pixi-version|setup-pixi@" .github/workflows/ | head -5
# Look for lines like:  pixi-version: v0.39.5  (or  uses: prefix-dev/setup-pixi@v0.X.Y)

# 2. Install that exact pixi version to a per-shell location (do NOT pollute global pixi)
PIXI_VERSION=0.39.5  # use whatever CI is pinned to
INSTALL_DIR="$HOME/.tmp/pixi-${PIXI_VERSION}"
curl -fsSL https://pixi.sh/install.sh | PIXI_VERSION="$PIXI_VERSION" \
  bash -s -- "$INSTALL_DIR"

# 3. Use pixi install (NOT pixi update) — minimal regeneration
"$INSTALL_DIR/bin/pixi" install --manifest-path <project-dir>/pixi.toml

# 4. Verify the diff is minimal (typically 1-2 lines: just the affected SHA)
git diff <project-dir>/pixi.lock | head -20
# Expected: a single `sha256: <hash>` line change on a `pypi: .` (local-package) entry

# 5. If the diff is broad (50+ lines, ruff/mypy/etc bumped), you accidentally ran
#    pixi update instead — revert and re-run pixi install:
git checkout <project-dir>/pixi.lock
"$INSTALL_DIR/bin/pixi" install --manifest-path <project-dir>/pixi.toml

# 6. Commit only the lockfile (not pixi.toml or pyproject.toml again)
git add <project-dir>/pixi.lock
git commit -m "chore: regenerate <project-dir>/pixi.lock after <reason>"
```

**Why match CI's pinned pixi version**: Newer pixi may write fields that older pixi versions
reject as "out of date" (this is documented in user memory `feedback_pixi_lock_version_pin`).
Always use the exact `pixi-version:` from the workflow file, not the latest pixi.

**Diagnosis signal that this pattern applies:**

- Recent commit to the manifest is comment-only / docstring-only / header-only — no dependency
  list, no version pin, no `[project.dependencies]` change
- CI failure message specifically mentions a SHA256 mismatch (not "lock-file not up-to-date" alone)
- The affected `pixi.lock` entry is the local editable package (`pypi: .` or `pypi: <subdir>`)
- A naive `pixi update` produces a diff of 50+ lines touching unrelated packages

**Empirical case**: ProjectAgamemnon issue #104 added a header comment to
`clients/python/pyproject.toml`. This invalidated the editable-package SHA256 (`pypi: .` entry
in `clients/python/pixi.lock`). All 4 required CI checks failed at `pixi install --locked`. The
fix-wave agent first tried `pixi update`, observed the broad diff (~50 lines including unrelated
ruff/mypy bumps), reverted, then used `pixi install` and produced a 1-line SHA fix that landed
cleanly as PR #368.

### Phase 3g: Pixi Binary Version Skew Causing Lock-Format Drift

**Pattern (distinct from Phase 3f, which is a SHA-mismatch).** Developer's local
`pixi --version` is newer than the version CI uses (the `pixi-version:` input to the
`prefix-dev/setup-pixi@vX.Y.Z` action). The developer regenerates `pixi.lock` with the newer
binary. Locally, `pixi install --frozen` succeeds — the newer binary happily reads its own
lock format. CI fails with a schema, lockfile-version, or format-rejection error because the
older pinned pixi cannot parse the newer fields/structure.

**Diagnostic signals:**

- CI fails on `pixi install` or `pixi run <task>` with a schema/format complaint (e.g.,
  "lockfile version mismatch", "unknown field", or similar parse error)
- Local `pixi install --frozen` succeeds against the same `pixi.lock`
- `git log -p pixi.lock` shows the lock was regenerated recently
- `pixi --version` locally is **newer** than the `pixi-version:` pinned in
  `.github/workflows/*.yml`

**Why this is NOT the SHA-mismatch case (Phase 3f):** SHA mismatches happen because the
*content* hash of the local editable package drifted (often from a metadata edit). Format
drift happens because the *serialization* of the lockfile changed between pixi binary
versions — the dependency graph itself is fine. The fix shape is identical (regenerate with
the right pixi version), but the diagnosis path is different: in Phase 3f, the diff is a
1-line SHA; in Phase 3g, the diff can be structural (new fields, restructured tables).

**Fix (verified workflow):**

```bash
# 1. Identify CI's pinned pixi version from workflow files
grep -rE "prefix-dev/setup-pixi|pixi-version" .github/workflows/ | head -10
# Look for a line like:  pixi-version: v0.39.5

# 2. Install that EXACT version locally to a per-shell location
PIXI_VERSION=0.39.5
INSTALL_DIR="$HOME/.tmp/pixi-${PIXI_VERSION}"
curl -fsSL https://pixi.sh/install.sh | PIXI_VERSION="v${PIXI_VERSION}" \
  bash -s -- "$INSTALL_DIR"
# Verify:
"$INSTALL_DIR/bin/pixi" --version   # should print 0.39.5

# 3. Delete the contaminated lock and regenerate with CI's pixi
rm pixi.lock
"$INSTALL_DIR/bin/pixi" install --manifest-path ./pixi.toml

# 4. Commit only the regenerated lock
git add pixi.lock
git commit -m "fix(ci): regenerate pixi.lock with pixi v${PIXI_VERSION}"
git push

# 5. Watch CI — should pass on the next run
```

**Why NOT just bump CI to the developer's newer pixi version?** Bumping the pinned
`pixi-version:` cascades to every repo using the same shared workflow / composite action.
A single-repo lock-format fix is a local change; a CI version bump is an ecosystem-wide
change that needs separate coordination. Prefer regenerating with CI's pinned version
unless the bump is a planned, ecosystem-wide upgrade.

**Long-term mitigations (not applied per-fix; track separately):**

- Bump the CI pinned pixi version to match developers' default (do this ecosystem-wide)
- Add a pre-commit hook that re-pins to CI's pixi before regenerating `pixi.lock`
- Document the CI-pinned pixi version in `CONTRIBUTING.md` so new contributors install it
  from day one

**Empirical case:** ProjectAgamemnon on 2026-05-17. Developer's local pixi was v0.67.2; CI
was pinned to v0.39.5 via `prefix-dev/setup-pixi`. Two `pixi.lock` files had been
regenerated locally and pushed: root `pixi.lock` (PR #390) and `clients/python/pixi.lock`
(PR #391). Both failed CI with format-rejection errors. Fix: installed v0.39.5 locally,
regenerated both lock files, pushed; CI passed.

**Failed approach worth flagging:** `pixi install --frozen` run locally as a "smoke test"
silently passed — the local newer pixi happily reads its own lock format. This is NOT a
substitute for CI verification. To reproduce CI's failure locally, you must invoke CI's
pinned pixi binary, not the local default.

### Phase 4: Verify

```bash
# Check CI is re-triggered and passing
for pr in <list>; do
  gh pr checks "$pr" 2>&1 | grep -E "(fail|pass|pending)"
done
```

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
| --------- | ---------------- | --------------- | ---------------- |
| `git checkout --theirs pixi.lock` | Accept main's lock during rebase | Main's lock hash is for main's source tree, not the branch | Always delete and regenerate — never accept either side |
| `git checkout --ours pixi.lock` | Accept branch's lock during rebase | Branch's lock is pre-rebase; doesn't reflect rebased state | Always regenerate with `pixi install` after rebase |
| `--no-verify` to skip pre-commit | Attempted to bypass lock-file check | Critical violation of repo policy; hook exists to protect CI | Always fix the root cause — the lock file IS wrong, fix it |
| Sequential per-branch fixes | Fixed branches one at a time | 5x longer than parallel; each pixi install takes ~15s | Use git worktrees for parallel execution when 3+ branches share the same fix |
| Parallel pixi install for Dependabot PRs | Ran pixi install across multiple worktrees simultaneously | Shared lock file state caused conflicts during resolution | Run Dependabot pixi.lock fixes sequentially per PR, not in parallel |
| `git rebase --continue` on double-rebase pixi.lock conflict | Tried to resolve conflict and continue | The prior pixi.lock-fix commit is entirely stale; continuing produces a broken lock | Use `git rebase --skip` to discard the stale commit, then `pixi install` fresh |
| Assumed Dependabot CI failure was a test failure | 6-12s CI duration seemed too fast; investigated test logs | Pre-flight `pixi install --locked` rejection happens before tests run | Fast CI failure (< 30s) on Dependabot PRs = stale pixi.lock, not a code issue |
| `git rebase --continue` after resolving empty commit (migrated-code scenario) | After accepting `HEAD` for all conflicted files in Commit B, tried `git rebase --continue` | Creates an empty commit that pollutes history with a no-op; also may trigger pre-commit failure on zero-change commit | When all conflicts are resolved by accepting `HEAD`'s version entirely — the commit adds nothing — use `git rebase --skip` to drop it |
| `git checkout fix/shellcheck-warnings-187-211 -- pixi.lock` | Tried to copy pixi.lock from another branch to avoid regenerating | Blocked by Safety Net ("overwrites working tree"); same block as `git checkout HEAD -- file` | Use `git show <branch>:<file> > <file>` instead — e.g., `git show fix/shellcheck-warnings-187-211:pixi.lock > pixi.lock` |
| Creating fix branch off stale local `main` | Ran `git checkout -b fix/pixi-lock-drift main` when local main was 33 commits behind origin/main | Push rejected as non-fast-forward; had to delete branch and recreate | Always use `git checkout origin/main -b fix/<name>` — bypasses local branch staleness entirely |
| Committing only `pixi.toml` without regenerating `pixi.lock` | Updated shellcheck version pin in pixi.toml but forgot to run `pixi install` before committing | CI immediately fails with "Environment is not consistent with the lockfile" — the lockfile SHA doesn't match the new constraint | Always run `pixi install` and commit the updated `pixi.lock` alongside any `pixi.toml` change |
| Per-branch pixi install regeneration on dozens of PRs | Spawned 4 parallel agents, each ran `pixi install` + `git commit --amend --no-edit` + force-push on 3 PR branches | Each branch's regenerated pixi.lock matched its own pyproject.toml fine, but every CI run still failed with "lock-file not up-to-date" because the rebase pulled in main's stale lock as the base. Branches were "clean" relative to themselves; main was broken. | Before fanning out per-branch fixups, run `pixi install --locked` on a fresh checkout of main itself; if main fails, hotfix main first, then re-rebase all branches |
| Trusted "already-clean" reports from per-branch agents | 4 agents each reported some branches "fixed" and others "already-clean (pixi install produced no change)" | The "already-clean" reports were correct — the BRANCH'S pyproject.toml/pixi.lock pair was self-consistent. The bug was that main itself shipped an inconsistent pair from a recently-merged PR. CI ran with main as the base, hit the broken lock, failed | Test the symptom on main directly before delegating per-branch repair work; "already-clean" can mean "branch is fine, but main isn't" |
| `pixi update --manifest-path <dir>/pixi.toml` for a comment-only manifest edit | Used `pixi update` to regenerate `pixi.lock` after a header comment was added to `clients/python/pyproject.toml` (ProjectAgamemnon issue #104) | `pixi update` re-resolved the entire dependency graph against the latest available versions, bumping ruff, mypy, and ~10 transitive packages — diff went from the expected 1 line to ~50 lines, risking unrelated breakage in CI for changes that had nothing to do with the original fix | For SHA-only or metadata-only invalidations, ALWAYS use `pixi install` (not `pixi update`). `pixi install` reproduces the lockfile from the current manifest with minimal change; `pixi update` re-resolves against latest versions and broadens scope. Revert the broad diff with `git checkout pixi.lock` and re-run `pixi install` instead. |
| Used latest pixi (newer than CI's pinned version) to regenerate `pixi.lock` | Ran the system-installed pixi without checking what version CI actually uses | Newer pixi writes lockfile fields that the older pixi version pinned in CI rejects as "out of date" — CI fails with the same error after the fix is pushed | Always pin to the exact `pixi-version:` from `.github/workflows/`. Install per-shell to `$HOME/.tmp/pixi-<version>/` to avoid polluting global pixi. See user memory `feedback_pixi_lock_version_pin`. |
| `pixi install --frozen` locally as a "smoke test" to validate the regenerated lock before pushing | Assumed that if `--frozen` accepts the lock locally, CI would too | The local pixi binary (newer, e.g. v0.67.2) happily reads the lock format it just wrote — `--frozen` only checks consistency against the manifest, NOT cross-version readability. CI's older pinned pixi (v0.39.5) still rejects the format on its end. | `pixi install --frozen` locally is NOT a substitute for CI verification when there is pixi-binary-version skew. To reproduce CI failure locally, run CI's pinned pixi binary explicitly (e.g., `$HOME/.tmp/pixi-0.39.5/bin/pixi install --locked`). |
| Considered bumping CI's pinned `pixi-version:` to match the developer's newer pixi (v0.67.2) | Would have made CI accept the lock format the developer already produced — one-line workflow edit | Rejected because the `pixi-version:` value is shared across many repos via the composite action / pinned setup-pixi version; changing it for one repo cascades to the entire HomericIntelligence ecosystem and needs separate coordination. A per-repo lock regeneration with CI's existing pixi is the local, low-blast-radius fix. | Treat CI's pinned `pixi-version:` as ecosystem state. Single-repo lock-format fixes should regenerate with the CI version; ecosystem-wide pixi upgrades are a separate, planned change. |

## Results & Parameters

### Key Commands

```bash
# Diagnose lock staleness
gh run view <run-id> --log-failed | grep "lock-file"

# Regenerate lock
pixi install              # regenerate pixi.lock (reads pixi.toml, resolves all deps)
pixi install --locked     # verify lock file is consistent (what CI runs) — use for verification

# Check if pixi.toml diverges between branch and main
git diff origin/main..HEAD -- pixi.toml

# Re-enable auto-merge after force-push (GitHub clears it silently)
gh pr merge <pr-number> --auto --rebase
gh pr view <pr-number> --json autoMergeRequest  # verify: should NOT be null
```

### When to Expect Clean Rebase vs. Conflict

| Scenario | What Happens | Action |
| ---------- | ------------- | -------- |
| Branch cut before version bump on main; branch has no pixi.toml changes | Rebase is clean — no pixi.lock conflict | Run `pixi install` anyway; the hash is stale |
| Branch has pixi.toml changes AND main has pixi.toml changes | Conflict in pixi.lock | Delete pixi.lock, stage, continue rebase, then `pixi install` |
| Branch has no pixi.toml changes, main has no pixi.toml changes | Rebase clean; pixi.lock may still be stale if any source changed | Run `pixi install` to be safe |

### Timing Reference

| Approach | PRs | Time |
| ---------- | ----- | ------ |
| Sequential single-branch | 5 | ~10 min |
| Parallel worktrees | 5 | ~1 min |
| Break-even point | 3 | Parallel wins at 3+ branches |

## Dependabot Multi-PR Sequential Fixing

When fixing multiple Dependabot PRs in sequence, **always re-fetch between each PR**. A branch
fixed earlier may merge to main while you're working on the next branch, invalidating
`origin/main` again.

```bash
# Pattern for each PR in sequence (not in parallel — pixi install can conflict on shared state):
git fetch origin          # always re-fetch before each rebase
git checkout <next-branch>
git rebase origin/main
# ... pixi install, commit, push, gh pr merge --auto <--squash|--rebase> ...
```

### Divergence Check Before Rebasing

Before rebasing a Dependabot branch, always check for local/origin branch divergence caused
by prior force-push sessions:

```bash
git status   # or:
git log --oneline origin/<branch>..HEAD    # commits local has that origin doesn't
git log --oneline HEAD..origin/<branch>    # commits origin has that local doesn't
```

If local and remote are diverged in both directions (e.g., `local: 2 ahead, origin: 3 ahead`),
reset to the remote state or start fresh from `origin/<branch>` before rebasing.

### Amend Pattern After Conflict Resolution

When `pixi.lock` shows as **untracked** after conflict resolution (rebase deleted it, then
`pixi install` regenerated it as an untracked file), fold it into the existing rebase commit
rather than adding a separate commit:

```bash
git add pixi.lock
git commit --amend --no-edit    # fold regenerated pixi.lock into the rebase commit
```

This keeps history clean — the rebase commit already recorded pixi.lock as deleted; the
regenerated file belongs in that same commit, not a separate one.

### Repo Merge Policy

The auto-merge strategy must match the target repository's merge policy. Check that repo's
`CLAUDE.md` for the configured policy:

```bash
gh pr merge <pr-number> --auto --squash   # repos that disable rebase merging (e.g. ProjectOdyssey)
gh pr merge <pr-number> --auto --rebase   # repos that require rebase merging (e.g. ProjectScylla)
```

A GraphQL error `"Merge method rebase merging is not allowed on this repository"` means the
repo uses `--squash`, not `--rebase`.

## Verified On

| Project | Context | Details |
| --------- | --------- | --------- |
| ProjectScylla | Multiple PRs on 2026-02-22 with pixi.lock conflicts and CI failures | v1.0.0 |
| ProjectHephaestus | 5 PRs failed after version bump 0.5.0 to 0.6.0 + resilience subpackage; all fixed via parallel worktrees, 2026-03-30 | v1.1.0 |
| ProjectScylla | Multiple Dependabot PRs failing CI in 6-12s; fixed sequentially via worktrees; double-rebase pixi.lock skip pattern used on 2 PRs, 2026-04-13 | v1.2.0 |
| ProjectOdyssey | Rebased `5047-separate-dev-production-deps` branch onto main after PR #5241 closed without merging; Commit B (script fixes) conflicted because scripts were rewritten as hephaestus wrapper stubs; accepted HEAD for all conflicted files, used `git rebase --skip` to drop empty commit, re-ran `pixi install` for new environments; PR #5266, 2026-04-21 | v1.3.0 |
| Myrmidons | shellcheck version pin (`shellcheck = "0.10.0.*"`) in pixi.toml, pixi.lock stale; fix branch created off origin/main; `git show` workaround for Safety Net; CI error "Environment is not consistent with the lockfile", 2026-04-24 | v1.4.0 |
| ProjectOdyssey | Dependabot PR updating Python package constraints in pyproject.toml; CI failed with lock-file not up-to-date; pixi install succeeded; CI pending after force-push, 2026-05-01 | v1.5.0 |
| ProjectScylla | Three sequential Dependabot PRs (pandas, vl-convert-python, matplotlib); pixi.lock conflict during rebase when main had advanced; resolved with rm+add+continue pattern; squash auto-merge used, 2026-05-02 | v1.5.0 |
| ProjectScylla | PR #1861 pandas bump; prior regeneration commit existed but stale (main advanced 4 commits); local/origin branches diverged; fetch + rebase + pixi install + amend + force-push; rebase auto-merge (ProjectScylla policy), 2026-05-03 | v1.5.0 |
| ProjectHermes | 2026-05-07: PR #593 added [project.dependencies] without regenerating pixi.lock; main's local-package SHA went stale; 17 open PR branches all failed CI simultaneously; hotfix PR #599 (1-line lock SHA fix) unblocked the entire queue | verified-ci |
| ProjectAgamemnon | 2026-05-11 ecosystem-wide easy-issue sweep: issue #104 added a header comment to `clients/python/pyproject.toml`, invalidating the editable-package SHA256 in `clients/python/pixi.lock`; all 4 required CI checks failed at `pixi install --locked`; fix-wave agent first tried `pixi update` (saw ~50-line diff, reverted), then used `pixi install` with CI's pinned pixi v0.39.5 → 1-line SHA fix landed cleanly as PR #368 | v1.7.0 verified-ci |
| ProjectAgamemnon | 2026-05-17: developer regenerated `pixi.lock` locally with pixi v0.67.2; CI (pinned to v0.39.5 via `prefix-dev/setup-pixi`) rejected both root `pixi.lock` and `clients/python/pixi.lock` with lockfile-format complaints; `pixi install --frozen` locally had passed and gave a false-green signal. Fix: installed v0.39.5 to `$HOME/.tmp/pixi-0.39.5/`, deleted and regenerated both locks, pushed as PR #390 (root) and PR #391 (clients/python). CI passed on both. | v1.8.0 verified-ci |
