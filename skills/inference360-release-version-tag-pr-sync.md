---
name: inference360-release-version-tag-pr-sync
description: "Inference360 release version bump and annotated tag workflow, including uv.lock refresh behavior and the GitHub PR head synchronization caveat. Use when: (1) preparing an Inference360 SemVer tag, (2) bumping pyproject.toml with uv.lock, (3) verifying annotated tag object vs commit SHA, (4) deciding whether PR checks actually ran against the release commit."
category: ci-cd
date: 2026-07-04
version: "1.0.0"
user-invocable: false
verification: verified-local
tags:
  - inference360
  - release
  - semver
  - git-tag
  - annotated-tags
  - uv-lock
  - pyproject
  - github-pr
  - pr-head-sha
  - local-validation
---

# Inference360 Release Version Tag PR Sync

## Overview

| Field | Value |
|-------|-------|
| **Date** | 2026-07-04 |
| **Objective** | Capture the Inference360 release/version/tag workflow used for tagging version `0.3.0`, including the package-version bump, uv lockfile refresh, local validation, annotated tag verification, and GitHub PR head synchronization caveat. |
| **Outcome** | Release commit and tag refs were verified locally/remotely, but PR checks were not claimed for the release commit because the PR API still reported an older head SHA after branch push. |
| **Verification** | verified-local: local validation passed and branch/tag refs were verified; CI/PR checks were not confirmed against the release commit. |

## When to Use

- You are preparing an Inference360 tagged release and need to keep `pyproject.toml`, `uv.lock`, release notes, and tag refs consistent.
- `uv lock --check` fails after a package-version-only edit and you need to decide whether regenerating `uv.lock` is expected.
- You need to create or verify an annotated release tag and distinguish the tag object SHA from the commit SHA.
- GitHub shows green PR checks, but `gh pr view` or the Pulls API still reports an older `headRefOid`; you need to avoid overclaiming CI coverage for the release commit.
- You need to document validation honestly as local plus branch/tag evidence when PR head synchronization lags.

## Verified Workflow

Verified locally only. CI validation was pending for the release commit because GitHub PR metadata did not synchronize to the pushed branch head.

### Quick Reference

```bash
# 1. Read release process before editing release state.
sed -n '1,220p' docs/release-process.md

# 2. Check existing local and remote tags before choosing the release version.
git tag --list --sort=-v:refname
git ls-remote --tags origin refs/tags/0.3.0 refs/tags/v0.3.0

# 3. Bump [project] version in pyproject.toml, then check the lockfile.
env UV_CACHE_DIR=.tmp/uv-cache uv lock --check

# If the only source edit is the package version and the check fails, refresh uv.lock.
env UV_CACHE_DIR=.tmp/uv-cache uv lock
env UV_CACHE_DIR=.tmp/uv-cache uv lock --check

# 4. Run focused local validation.
env UV_CACHE_DIR=.tmp/uv-cache just pre-commit
env UV_CACHE_DIR=.tmp/uv-cache just _validate-host

# 5. Commit the synchronized version files.
git add pyproject.toml uv.lock
git commit -m "chore(release): bump version to 0.3.0"

# 6. Create and push an annotated tag for the requested version.
git tag -a 0.3.0 -m "Inference360 0.3.0"
git push origin refs/tags/0.3.0

# 7. Verify the tag ref and the dereferenced commit.
git ls-remote --tags origin 'refs/tags/0.3.0*'
git show --no-patch --format='%H %D %s' 0.3.0^{}

# 8. If PR metadata looks stale, compare the old PR head to the branch head.
gh api repos/<owner>/<repo>/compare/<old-pr-head>...<branch-head> \
  --jq '{status: .status, ahead_by: .ahead_by, behind_by: .behind_by}'
```

### Detailed Steps

1. **Read the release process first.** Inference360 release work should start with `docs/release-process.md`. The durable constraints from that document are: keep the Python package version in `pyproject.toml` synchronized with release notes/tooling behavior, use SemVer for tagged releases, and run `just validate` or the closest available validation before finalizing.

2. **Check for existing tags before editing.** Inspect local and remote tags before creating a release tag. Check both bare and `v`-prefixed forms when the requested version is bare:

   ```bash
   git tag --list --sort=-v:refname
   git ls-remote --tags origin refs/tags/0.3.0 refs/tags/v0.3.0
   ```

3. **Bump the package version and handle `uv.lock` honestly.** Update `[project] version` in `pyproject.toml`. Then run:

   ```bash
   env UV_CACHE_DIR=.tmp/uv-cache uv lock --check
   ```

   If the only source edit is the package version, a lock-check failure is expected because `uv.lock` embeds the editable package version. Regenerate and re-check:

   ```bash
   env UV_CACHE_DIR=.tmp/uv-cache uv lock
   env UV_CACHE_DIR=.tmp/uv-cache uv lock --check
   ```

4. **Run local validation with a repo-local UV cache.** For the `0.3.0` release bump, the local validation path was:

   ```bash
   env UV_CACHE_DIR=.tmp/uv-cache just pre-commit
   env UV_CACHE_DIR=.tmp/uv-cache just _validate-host
   ```

   Observed host validation result: `1151 passed, 1 skipped`, coverage `81.99%`.

5. **Commit only the synchronized version artifacts.**

   ```bash
   git add pyproject.toml uv.lock
   git commit -m "chore(release): bump version to 0.3.0"
   ```

6. **Create an annotated tag for the requested version and push the exact ref.** For version `0.3.0`, the tag command was:

   ```bash
   git tag -a 0.3.0 -m "Inference360 0.3.0"
   git push origin refs/tags/0.3.0
   ```

7. **Verify both tag object and target commit.** Annotated tags have a tag object SHA that differs from the commit SHA. Use the dereference suffix to verify the commit being released:

   ```bash
   git ls-remote --tags origin 'refs/tags/0.3.0*'
   git show --no-patch --format='%H %D %s' 0.3.0^{}
   ```

   Observed for this release: tag object `77a33d23a8eaf65f02f18364126ced8164d3dd5c`, dereferenced commit `48e8b6e5d257146a36ec3134dcd3739e9f077735`. Branch/tag ref evidence showed the release commit, and local validation passed.

8. **Confirm PR checks are for the commit being released before citing them.** In this session, after pushing the branch, the raw branch ref reported commit `48e8b6e5d257146a36ec3134dcd3739e9f077735`, but `gh pr view` and the Pulls API for PR #339 continued to report older head `ccc9dd108e1ca821814c4cbf2d8d4b8749e83b8f`. A compare API call from `ccc9dd1` to `48e8b6e` returned `ahead_by=1`, `behind_by=0`.

   The correct conclusion was: validation is local plus branch/tag evidence. Do not claim PR checks validated the release commit until the PR head SHA synchronizes and check runs are confirmed against `48e8b6e5d257146a36ec3134dcd3739e9f077735`.

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
|---------|----------------|---------------|----------------|
| Treating `uv lock --check` failure as unexpected after only a version bump | Changed `[project] version` in `pyproject.toml`, then ran `env UV_CACHE_DIR=.tmp/uv-cache uv lock --check` | `uv.lock` embeds the editable package version, so the lock check can fail even when no dependency constraints changed | If the only edit is the package version, run `env UV_CACHE_DIR=.tmp/uv-cache uv lock`, then re-run the lock check and commit both `pyproject.toml` and `uv.lock` |
| Using the annotated tag SHA as the release commit SHA | Looked at the pushed tag object SHA from `git ls-remote --tags` | Annotated tags have a tag object that points to a commit; the tag object SHA is not the released commit | Use `git show --no-patch --format='%H %D %s' <tag>^{}` or an equivalent dereference to verify the commit |
| Claiming PR checks validated the release commit from green PR state alone | Branch push showed the release commit, but `gh pr view` and the Pulls API still reported the older PR head | GitHub PR head metadata lagged or failed to synchronize; green checks may belong to the older head SHA | Confirm check runs against the exact release commit SHA. If PR head does not match branch head, state validation as local plus branch/tag evidence only |
| Checking only one tag spelling | Looked for the requested bare version form without checking the `v`-prefixed form | Repos may use either bare `0.3.0` or `v0.3.0`; missing one form can hide an existing release tag | Check both `refs/tags/<version>` and `refs/tags/v<version>` before tagging |

## Results & Parameters

- Release version: `0.3.0`.
- Release commit: `48e8b6e5d257146a36ec3134dcd3739e9f077735`.
- Annotated tag object: `77a33d23a8eaf65f02f18364126ced8164d3dd5c`.
- Local validation commands:

  ```bash
  env UV_CACHE_DIR=.tmp/uv-cache just pre-commit
  env UV_CACHE_DIR=.tmp/uv-cache just _validate-host
  ```

- Local host validation observed: `1151 passed, 1 skipped`, coverage `81.99%`.
- PR synchronization caveat: PR #339 still reported head `ccc9dd108e1ca821814c4cbf2d8d4b8749e83b8f` while the branch ref reported `48e8b6e5d257146a36ec3134dcd3739e9f077735`; compare from old head to branch head returned `ahead_by=1`, `behind_by=0`.
- Reporting rule: release evidence may cite local validation and branch/tag refs; do not cite PR checks unless their head SHA equals the release commit.

## Verified On

| Project | Context | Details |
|---------|---------|---------|
| Inference360 | Version `0.3.0` release/tag workflow | Local validation passed; branch and tag refs verified; PR checks not confirmed against release commit because PR metadata still reported an older head SHA |
