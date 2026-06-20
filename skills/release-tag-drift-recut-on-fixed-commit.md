---
name: release-tag-drift-recut-on-fixed-commit
description: "Diagnose and fix a tag-time version-currency drift guard that silently skips PyPI publish, then re-cut the release tag on a fixed commit. Use when: (1) a vX.Y.Z git tag exists but the package was never published to PyPI even though main's push-CI is green; (2) a Release GitHub Actions run shows the `test` job failing and `build-and-publish` SKIPPED (not failed); (3) a drift-guard unit test (e.g. test_migration_md_version_does_not_trail_latest_git_tag) fails inside the tag-triggered Release workflow because a doc's 'latest released version' line trails the new tag; (4) you need to delete and re-create a release tag on a corrected commit without reproducing the same failure (land-on-main-then-recut, never recut-in-place); (5) a failing CI run's headBranch is a vX.Y.Z tag and you must tell a tag-triggered Release run apart from a push-to-main run; (6) an UNRELATED open PR (incl. a Dependabot PR) suddenly fails test_version_currency / required-checks-gate right after a vX.Y.Z tag was pushed — the stale tag's blast radius reaches every open PR, not just the Release run."
category: ci-cd
date: 2026-06-20
version: "1.1.0"
user-invocable: false
verification: verified-ci
history: release-tag-drift-recut-on-fixed-commit.history
tags:
  - release
  - git-tags
  - pypi-publish
  - github-actions
  - version-drift
  - drift-guard
  - re-cut-tag
  - chicken-and-egg
  - migration-md
  - signed-tags
  - blast-radius
  - pr-unblock
  - dependabot-rebase
---

# Release Tag Drift: Re-cut the Tag on a Fixed Commit

## Overview

| Field | Value |
|-------|-------|
| **Date** | 2026-06-20 |
| **Objective** | Diagnose why a `vX.Y.Z` tag existed but the package never reached PyPI, then re-cut the tag correctly so the Release workflow publishes — and recognize that a stale/premature tag blocks the CI of **every open PR**, not just the Release run. |
| **Outcome** | Successful — root cause was a tag-time version-currency drift guard failing the Release `test` job, which SKIPPED `build-and-publish`. Fixed `docs/MIGRATION.md` on main, then re-cut the tag on the fixed commit; the Release run re-triggered on the corrected commit. Verified twice (v0.9.6 original run published to PyPI; v0.9.7 re-application). |
| **Verification** | verified-ci — the procedure was executed end-to-end on the original v0.9.6 run (re-triggered Release passed all jobs incl. `build-and-publish`, PyPI publish succeeded) and confirmed by a second re-application on v0.9.7. |

## When to Use

- A `vX.Y.Z` tag exists, but PyPI has no matching release — yet main's regular push-CI is green.
- A linked failing CI run is the **Release** workflow with `headBranch` equal to a `vX.Y.Z` tag (a tag-triggered run), not a push to main.
- The Release `test` job failed and `build-and-publish` shows conclusion **skipped** — so the package is silently unpublished despite the tag existing.
- A "version-currency drift guard" test asserts a doc's "latest released version is **X.Y.Z**" line is not older than the newest `vX.Y.Z` tag, and the tag's own commit fails it (chicken-and-egg).
- **An unrelated open PR (including a Dependabot PR) suddenly fails `test_version_currency` / `required-checks-gate` right after a `vX.Y.Z` tag was pushed.** The stale tag is the cause — its drift guard fails on every PR whose checkout resolves tags, not just the Release run.
- You were told to "delete the tag and launch a new tag" and need to decide: re-create the same version on a fixed commit, or bump to the next patch.

## Verified Workflow

### Quick Reference

```bash
# 0. BLAST RADIUS FIRST: if the tag was cut prematurely / is stale, DELETE the remote
#    tag immediately. It is failing the drift guard on EVERY open PR, not just Release.
#    Deleting it unblocks all open PRs at once — do this before preparing the doc PR.
git push origin :refs/tags/vX.Y.Z    # outward-facing; confirm w/ user if published
# then re-run CI on any PR that already failed:
#   Dependabot PR:  comment "@dependabot rebase"
#   normal PR:      git commit --amend --no-edit && git push -f  (or re-run failed checks)

# 1. Identify it's the Release workflow on the TAG, not main CI
gh run view <run-id> --json name,workflowName,headBranch,headSha,conclusion
#   -> name=Release, headBranch=v0.9.6  (a tag, not a branch)

# 2. Confirm only the drift test failed AND publish was SKIPPED (not failed)
gh run view <run-id> --json jobs -q '.jobs[] | "\(.conclusion // .status)  \(.name)"'
#   -> failure  test          (drift guard)
#   -> skipped  build-and-publish   <-- package silently unpublished

# 3. Fix the doc on a NORMAL PR branch off main, verify locally
git checkout -b <issue>-fix-migration-version main
# edit docs/MIGRATION.md: bump "latest released version is X.Y.Z" to match the tag;
# also refresh any stale "as of YYYY-MM-DD" date
# NOTE: running a SINGLE test file trips the coverage-threshold gate (a coverage FAIL,
# NOT a real test failure). Use --no-cov and read the "N passed" line:
pytest tests/unit/docs/test_version_currency.py --no-cov   # must pass

# 4. PR per repo policy, signed commit, merge to MAIN first
git commit -S -m "docs(migration): bump version line to vX.Y.Z to clear release drift guard"
gh pr create --body "$(printf 'Fix release drift guard.\n\nCloses #<issue>\n')"
#   Pre-arming auto-merge is CONDITIONAL: check the `auto-merge-policy` check conclusion
#   on THIS PR first (gh pr checks <num>). If it is SUCCESS on the fresh PR you may
#   pre-arm `gh pr merge --auto --squash`. If it is red (repos gating behind a GO label),
#   do NOT pre-arm — apply the GO label / let the review flow arm it. Squash-only repos
#   must use --squash, never --rebase.

# 5. After merge, sync main and note the FIXED commit SHA
git checkout main && git pull --ff-only origin main
git rev-parse --short HEAD            # e.g. d3cef75  <- fixed commit
# Pre-tag sanity (while NO tag exists yet): passes via skip or "documented >= prior tag"
pytest tests/unit/docs/test_version_currency.py --no-cov

# 6. Delete the old tag (remote + local) and re-create on the FIXED commit
git push origin :refs/tags/vX.Y.Z    # delete remote (outward-facing; confirm w/ user)
git tag -d vX.Y.Z                    # delete local -- BLOCKED by CC Safety Net; USER runs this
git tag -s vX.Y.Z <fixed-sha> -m "$(printf 'Release vX.Y.Z\n\nRe-cut on fixed commit <sha>: clears the version-currency drift guard that previously skipped the PyPI publish.')"
git push origin vX.Y.Z               # re-triggers Release on the FIXED commit

# 7. Watch the new Release run; verify build-and-publish is NO LONGER skipped
gh run watch <new-run-id> --exit-status

# 8. Verify PyPI is live (JSON index lags a few minutes; publish-step success is authoritative)
curl -s https://pypi.org/pypi/<DistName>/<version>/json | head
```

### Blast Radius: a stale tag blocks ALL open PRs

The version-currency drift guard is **not** scoped to the tag-triggered Release run.
`test_version_currency.py::test_migration_md_version_does_not_trail_latest_git_tag`
resolves the *latest git tag visible to the checkout* and asserts
`documented_version >= canonical_tag_version`. So in **any** CI context where the
checkout resolves the stale tag — including ordinary PR CI — the test fails with the
identical signature:

```text
tests/unit/docs/test_version_currency.py::test_migration_md_version_does_not_trail_latest_git_tag FAILED
required-checks-gate: FAILURE
```

In this session a premature `v0.9.7` tag sat on `origin` while `MIGRATION.md` still
read `0.9.6`. An **unrelated Dependabot PR (#1540, an actions bump)** was blocked with
exactly that failure — its CI saw the latest tag as `v0.9.7` and the assertion
`0.9.6 >= 0.9.7` failed, cascading to `required-checks-gate: FAILURE`.

**The fast global unblock is to delete the stale remote tag immediately**
(`git push origin :refs/tags/vX.Y.Z`). The moment the tag is gone, every open PR's
checkout resolves the *prior* tag (`v0.9.6`) and the assertion passes
(`0.9.6 >= 0.9.6`), or — for a tagless/shallow checkout — the test skips. Either way
all open PRs are unblocked at once. Do this **before** you start preparing the doc-bump
PR; do not leave the stale tag sitting while you work. After deletion, re-run CI on any
PR that already failed: comment `@dependabot rebase` on Dependabot PRs; push an
empty/amend commit or re-run failed checks on normal PRs.

### How the drift test decides skip vs. fail

Verified by reading the test source this session:

- The test calls `_version_from_git_tag()`.
- If that returns **None** (a tagless or shallow checkout — e.g. `actions/checkout`
  WITHOUT `fetch-depth: 0` + fetch-tags), the test `pytest.skip`s with the rationale
  that "a missing-tags ENVIRONMENT is not a doc defect." It therefore cannot fail there.
- It only **runs (and can fail)** in checkouts where a tag resolves. The Release and
  required workflows fetch tags (`fetch-depth: 0`), so the guard always runs there.
- Implication: once the stale tag is deleted, a PR whose checkout resolves the prior
  tag (`v0.9.6`) passes (`0.9.6 >= 0.9.6`), and a truly tagless checkout skips — either
  way the PR is unblocked.

### Detailed Steps

1. **Identify the run is the Release workflow on the tag, not main CI.**
   `gh run view <id> --json name,workflowName,headBranch,headSha,conclusion`. A
   `headBranch` of `vX.Y.Z` means a tag-triggered Release run. Main's push-CI being
   green is a red herring — the drift guard only fails on the tag-triggered run
   because that run is the only context where the tag exists and the assertion
   `(doc_version) >= (latest_tag)` is evaluated against the new tag.

2. **Confirm the failure shape: drift test failed → publish SKIPPED.**
   `gh run view <id> --json jobs -q '.jobs[] | "\(.conclusion // .status)  \(.name)"'`.
   A failed `test` job causes the downstream `build-and-publish` job (which `needs: test`)
   to be **skipped**, not failed. So the package is silently unpublished even though the
   run's top-level conclusion looks like a plain test failure. Always check the
   `build-and-publish` job conclusion explicitly, not just the run conclusion.

3. **Check the blast radius and clear it fast.** If the tag was cut prematurely (the doc
   bump never landed first), the stale tag is failing the drift guard on **every open
   PR** whose checkout resolves tags, not just the Release run. Delete the remote tag
   immediately (`git push origin :refs/tags/vX.Y.Z`) to unblock all of them, then re-run
   CI on any PR that already failed (`@dependabot rebase` for Dependabot PRs; re-run /
   push for normal PRs). Do this before preparing the doc-bump PR.

4. **Fix the doc on a normal PR branch off main and verify locally.**
   Bump `docs/MIGRATION.md`'s "latest released version is **X.Y.Z**" line to match the
   tag, and refresh any stale "as of YYYY-MM-DD" date the same guard or a sibling test
   checks. Run `pytest tests/unit/docs/test_version_currency.py --no-cov` and confirm it
   passes before opening the PR. Use `--no-cov` because running a single test file trips
   the project coverage-threshold gate (a coverage FAIL, not a real test failure); read
   the `N passed` line as the source of truth.

5. **Open a PR per repo policy (`Closes #N`), signed commit, and merge to main FIRST.**
   The fix MUST land on main before re-tagging. Re-tagging on the still-buggy main would
   reproduce the identical drift-guard failure. Auto-merge pre-arming is **conditional**:
   check the `auto-merge-policy` check conclusion on the actual PR (`gh pr checks <num>`).
   If it is SUCCESS on the fresh PR you may pre-arm `gh pr merge --auto --squash`
   (squash-only repos use `--squash`, never `--rebase`). If it is red — repos that gate
   auto-merge behind a `state:implementation-go` (or equivalent) label — do NOT pre-arm;
   apply the GO label first or let the review flow arm it.

6. **Sync local main and capture the fixed commit SHA.**
   `git checkout main && git pull --ff-only origin main`, then
   `git rev-parse --short HEAD` to record the merge commit. This is the commit the new
   tag must point at. While no tag exists yet, you can sanity-check the guard with
   `pytest tests/unit/docs/test_version_currency.py --no-cov` — it passes (skip, or
   `documented >= prior_tag`).

7. **Delete the old tag and re-create it on the fixed commit.**
   - `git push origin :refs/tags/vX.Y.Z` deletes the remote tag (outward-facing — confirm
     with the user before deleting a published tag).
   - `git tag -d vX.Y.Z` deletes the local tag — **CC Safety Net blocks `git tag -d`**;
     hand this to the user to run manually. You cannot override the hook even with
     in-conversation approval.
   - `git tag -s vX.Y.Z <fixed-sha> -m "<descriptive message>"` creates a signed annotated
     tag on the fixed commit, matching the repo's tag convention. Use a descriptive message
     that explains the re-cut, not a bare `Release vX.Y.Z`.
   - `git push origin vX.Y.Z` re-triggers the Release workflow on the fixed commit.

8. **Watch the new Release run and confirm publish actually ran.**
   `gh run watch <new-id> --exit-status`. Verify all jobs pass, especially that
   `build-and-publish` is no longer skipped. Confirm the version-check step prints the
   right version and the publish step uploaded (look for the sigstore attestation /
   "Publish to PyPI" step output).

9. **Verify PyPI is live.**
   `curl -s https://pypi.org/pypi/<DistName>/<version>/json`. The PyPI JSON index lags a
   few minutes; the workflow's publish step succeeding with attestations is the
   authoritative "published" signal, not the JSON index appearing instantly.

### Gotchas

- **A stale/premature tag blocks the CI of EVERY open PR, not just the Release run.**
  The drift guard runs wherever the checkout resolves tags. Delete the stale remote tag
  first (`git push origin :refs/tags/vX.Y.Z`) to unblock all open PRs at once, then
  `@dependabot rebase` / re-run the PRs that already failed.
- **Running a single drift-test file trips the coverage gate.** `pytest <one_file>` can
  report a coverage-threshold FAIL even when the test itself passes. Use `--no-cov` and
  trust the `N passed` line, not the coverage line.
- **The drift test skips on tagless checkouts and only fails where tags resolve.** A
  shallow checkout (`actions/checkout` without `fetch-depth: 0` + fetch-tags) makes
  `_version_from_git_tag()` return None and the test `pytest.skip`s. Release/required
  workflows fetch tags, so the guard always runs there.
- **Tag-time drift guards are inherently chicken-and-egg.** The tag itself triggers the
  check that the tag's content fails. The only fix is land-on-main-then-recut — never
  recut-in-place on the buggy commit.
- **A failed Release `test` job SKIPS, not fails, `build-and-publish`.** The package is
  silently unpublished even though the tag exists and the run looks like an ordinary test
  failure. Check the `build-and-publish` job conclusion, not just the run conclusion.
- **Annotated/signed tags have a tag-object SHA distinct from the commit they point to.**
  `git rev-parse vX.Y.Z` returns the *tag object*. To get the underlying commit, use
  `git for-each-ref refs/tags/vX.Y.Z --format='%(*objectname:short)'`.
- **"Delete the tag and launch a new tag" is ambiguous.** Clarify with the user whether to
  RE-CREATE the same version (premature/bad tag redo) or BUMP to the next patch. This
  changes which version you write into `MIGRATION.md`.
- **Auto-merge pre-arming is repo- and gate-dependent.** It works on a fresh PR only when
  the `auto-merge-policy` check is already SUCCESS; in GO-label-gated repos pre-arming
  trips the gate. Check `gh pr checks <num>` before deciding. Squash-only repos use
  `--squash`.
- **CC Safety Net blocks `git tag -d`, `git worktree remove --force`, and `git checkout --`.**
  Hand these to the user to run manually; the hook cannot be overridden even with
  in-conversation approval.

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
|---------|----------------|---------------|----------------|
| 1 | Assumed the linked failing CI run was main's push-CI | Main push-CI was actually green; the failure was the tag-triggered Release workflow | Check `workflowName` + `headBranch` on the run — a `vX.Y.Z` headBranch means a tag-triggered release, not a branch |
| 2 | Considered re-cutting the tag immediately on current main | Current main still had the buggy `MIGRATION.md`; re-tag would fail the drift guard identically | The doc fix must merge to main BEFORE re-tagging; the re-tag must point at the fixed commit |
| 3 | `gh pr merge --auto --squash` armed immediately on the fix PR | Tripped the repo's auto-merge-policy gate (auto-merge only allowed after the `state:implementation-go` label) | Pre-arm only when the PR's `auto-merge-policy` check is already SUCCESS; otherwise apply the GO label first or let the review flow arm it |
| 4 | `git tag -d v0.9.6` run by the assistant | Blocked by CC Safety Net (destructive tag deletion) | Hand `git tag -d` / `git worktree remove --force` / `git checkout --` to the user to run manually |
| 5 | Left the stale remote tag in place while preparing the doc-bump PR | Every open PR's CI (incl. unrelated Dependabot PR #1540) failed `test_version_currency` → `required-checks-gate: FAILURE`, because their checkouts resolved the stale tag | Delete the stale remote tag FIRST — it unblocks all open PRs at once; don't leave it sitting while you prep the fix |
| 6 | Ran the single drift-test file and saw a coverage FAIL | Mistook the coverage-threshold gate failure for a real test failure | Run single test files with `--no-cov`; read the `N passed` line, not the coverage line |
| 7 | Assumed the drift guard only affects the tag-triggered Release run | It runs in ANY checkout that resolves tags — so it blocks every open PR, not just Release | The guard's reach is repo-wide; treat a stale tag as a fleet-wide blocker, not a Release-only one |

## Results & Parameters

**Diagnostic commands (copy-paste):**

```bash
# Was it the Release workflow on a tag?
gh run view <run-id> --json name,workflowName,headBranch,headSha,conclusion
# Expected on failure: name=Release, headBranch=v0.9.6

# Did the drift test fail and publish skip?
gh run view <run-id> --json jobs -q '.jobs[] | "\(.conclusion // .status)  \(.name)"'
# Expected: "failure  test"  and  "skipped  build-and-publish"

# Is an UNRELATED PR failing the same guard because of a stale tag? (blast-radius check)
gh pr checks <pr-num>
# Expected when a stale tag is live: test_version_currency FAILED, required-checks-gate FAILURE

# Underlying commit of an annotated/signed tag (NOT the tag-object SHA):
git for-each-ref refs/tags/v0.9.6 --format='%(*objectname:short)'
```

**The drift-guard assertion that fails (illustrative):**

```text
tests/unit/docs/test_version_currency.py::test_migration_md_version_does_not_trail_latest_git_tag
assert (0, 9, 5) >= (0, 9, 6)   # MIGRATION.md says 0.9.5, newest tag is v0.9.6  -> False -> FAIL
```

**Global unblock for a premature tag (do this FIRST):**

```bash
git push origin :refs/tags/vX.Y.Z    # delete stale remote tag -> all open PRs unblock
# re-run CI on PRs that already failed:
#   Dependabot:  gh pr comment <num> --body "@dependabot rebase"
#   normal PR:   re-run failed checks or push an amend/empty commit
```

**Re-cut sequence (verified, with real SHAs from the session):**

```bash
git push origin :refs/tags/v0.9.6                 # delete remote tag
git tag -d v0.9.6                                 # local delete — USER runs (CC Safety Net blocks)
git tag -s v0.9.6 d3cef75 -m "$(printf 'Release v0.9.6\n\nRe-cut on fixed commit d3cef75: clears the version-currency drift guard that skipped the PyPI publish on the original tag at f32f1ed.')"
git push origin v0.9.6                            # re-trigger Release on the fixed commit
gh run watch <new-run-id> --exit-status
curl -s https://pypi.org/pypi/<DistName>/0.9.6/json
```

**Expected outcome:** the re-triggered Release run passes all jobs including
`build-and-publish` (no longer skipped), the publish step uploads to PyPI with sigstore
attestations, and the package version becomes installable once the PyPI index catches up.

### Verified On

- **ProjectHephaestus v0.9.6** (2026-06-16, original run) — diagnosed the skipped
  `build-and-publish`, fixed `MIGRATION.md` on main, re-cut signed tag on commit
  `d3cef75`; the re-triggered Release run published to PyPI with attestations.
  **verification: verified-ci.**
- **ProjectHephaestus v0.9.7** (2026-06-20, confirming re-application) — same procedure:
  doc-bump PR **#1542** merged (commit `6512a62`), stale remote tag deleted (which
  unblocked an unrelated Dependabot PR **#1540** that had been failing the drift guard),
  re-cut signed tag `v0.9.7` on `6512a62`, and the **Release run (27882075453) was
  re-triggered** on the fixed commit per the v1.0.0 procedure. (Stated as re-cut +
  Release re-triggered; the PROCEDURE is verified-ci from the original v0.9.6 publish, and
  this is a confirming re-application.)
