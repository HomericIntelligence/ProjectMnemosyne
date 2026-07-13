---
name: tooling-repo-rename-stale-remote-and-tag-refspec-push-failure
description: "After a GitHub repository is RENAMED, the local `origin` still points at the OLD URL; pushes get a `remote: This repository moved` redirect, and a TAG-source refspec force-push (`tag:branch`) fails through that redirect with `remote: fatal error in commit_refs` / `[remote rejected]` even though branch/HEAD-source pushes succeed in the same session. Fix: `git remote set-url origin` to the new location, then push a BRANCH source (materialize the tag into a temp branch first) instead of a tag source. Use when: (1) `remote: This repository moved` appears on push, (2) `fatal error in commit_refs` / `[remote rejected]` when pushing a tag to a branch, (3) some pushes work and others fail in the same session after a repo rename."
category: tooling
date: 2026-07-12
version: "1.0.0"
user-invocable: false
verification: verified-local
tags:
  - git
  - git-push
  - repo-rename
  - remote-url
  - set-url
  - refspec
  - tag
  - force-with-lease
  - commit_refs
  - redirect
---

# Repo Rename: Stale `origin` URL + Tag-Refspec Push Failure Through the Redirect

## Overview

| Field | Value |
| ------- | ------- |
| **Date** | 2026-07-12 |
| **Objective** | Explain why a force-push fails with `remote: fatal error in commit_refs` after a GitHub repo was renamed, when other pushes in the same session succeed, and how to fix it. |
| **Outcome** | Root cause: `origin` still pointed at the OLD repo URL, so pushes went through GitHub's rename redirect; a TAG-source refspec (`tag:branch`) is rejected at ref-update time through the redirect, while BRANCH/HEAD-source refspecs are tolerated. Fix: `git remote set-url origin <new-url>` and push a BRANCH source (materialize the tag into a temp branch first). |
| **Verification** | verified-local — reproduced the failure and fixed it live; the branch pushed successfully after `set-url` + branch-source refspec. |
| **Verified On** | ProjectHephaestus (renamed HomericIntelligence/ProjectHephaestus to HomericIntelligence/Hephaestus), 2026-07-12 |

## When to Use

- A push prints `remote: This repository moved. Please use the new location:` followed by the new URL.
- A force-push using a TAG as the source ref (`git push --force-with-lease origin <tag>:<branch>`) fails with `remote: fatal error in commit_refs` and `! [remote rejected]   <tag> -> <branch> (failure)`.
- Some pushes in the same session succeed (those using `HEAD:branch` or `branch:branch`) while only the tag-source push fails — a confusing "why does one work and the other not" signature.
- `git remote get-url origin` still returns the OLD repository name after you know the repo was renamed on GitHub.
- You are resigning/rebasing a tag and pushing the result to a branch ref on a repo that was recently renamed.

## Verified Workflow

The redirect that GitHub serves after a repo rename tolerates branch/HEAD source refspecs
but chokes on a tag-source (`tagname:branch`) ref update, failing it with `commit_refs`. Do
two things: fix the stale remote URL (good hygiene regardless), and convert the push to a
BRANCH source.

### Quick Reference

```bash
# 1. Point origin at the NEW location (the repo was renamed).
git remote set-url origin https://github.com/OWNER/NewName.git
git remote get-url origin   # confirm it shows NewName, not the old name

# 2. Materialize the tag into a local branch so the push uses a BRANCH source, not a tag source.
git branch -f <tmpbranch> <tag>

# 3. Push the BRANCH source; --force-with-lease still guards safety.
git push --force-with-lease=<remote-branch>:<lease-sha> origin <tmpbranch>:<remote-branch>
```

### Detailed Steps

1. **Confirm the stale remote.** Run `git remote get-url origin`. If it still returns the OLD
   repo name after a known rename, that is the redirect source. Heed the
   `remote: This repository moved` hint — it is a hard failure at ref-update time for the tag
   push, not merely advisory.

2. **Update the remote URL.** `git remote set-url origin https://github.com/OWNER/NewName.git`.
   This is correct hygiene regardless of the push method — do not rely on the redirect.

3. **Verify the lease still matches origin.** Before pushing, confirm the
   `--force-with-lease` expected sha still matches the current remote-branch tip
   (`git ls-remote origin <remote-branch>`), so the safety guard is meaningful.

4. **Convert the tag source to a branch source.** Create a local branch from the tag
   (`git branch -f <tmpbranch> <tag>`), then push `<tmpbranch>:<remote-branch>`. Branch-source
   refspecs update cleanly through the (now-updated) remote; tag-source ones are what failed.

5. **Push with `--force-with-lease`.** The lease still guards against clobbering concurrent
   work. Confirm the ref updated (no `[remote rejected]` line).

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
| --------- | ---------------- | --------------- | ---------------- |
| Push a tag as the source ref through the old URL | `git push --force-with-lease=... origin <tag>:<branch>` with `origin` still on the OLD repo name | `remote: fatal error in commit_refs` + `[remote rejected]` — the rename redirect could not apply a tag-to-branch ref update | After a repo rename, update `origin` to the new URL; do not rely on the redirect |
| Assume all refspecs behave the same through the redirect | Expected the tag push to work because `HEAD:branch` / `branch:branch` pushes did in the same session | Tag-source refspecs specifically fail with `commit_refs` through the redirect; branch/HEAD sources tolerate it | Use a BRANCH source — materialize the tag into a temp branch first |
| Ignore the "repository moved" hint | Treated `remote: This repository moved` as advisory | It is a hard failure at ref-update time for the tag push | Heed the moved-repo hint: `set-url` to the new location immediately |

## Results & Parameters

### Observed failure (ProjectHephaestus renamed to Hephaestus)

```text
remote: This repository moved. Please use the new location:
remote:   https://github.com/HomericIntelligence/Hephaestus.git
remote: fatal error in commit_refs
 ! [remote rejected]   resign-2056-rebased -> 2054-auto-impl (failure)
```

- `git remote get-url origin` returned `https://github.com/HomericIntelligence/ProjectHephaestus.git` (the OLD name).
- The push transferred data successfully but was REJECTED at ref update — because the source ref was a TAG.
- Other pushes in the same session using `HEAD:branch` or `branch:branch` refspecs SUCCEEDED through the redirect; only the tag-source (`tagname:branch`) refspec failed with `commit_refs`.

### The fix, applied

```bash
git remote set-url origin https://github.com/HomericIntelligence/Hephaestus.git
git branch -f resign-2056-branch resign-2056-rebased   # tag -> local branch
git push --force-with-lease=2054-auto-impl:<lease-sha> \
  origin resign-2056-branch:2054-auto-impl
# -> branch-source refspec updated cleanly; no [remote rejected]
```

### Key facts

- The redirect distinguishes source-ref TYPE: tag-source ref updates fail with `commit_refs`; branch/HEAD-source ref updates are tolerated.
- `git remote set-url origin <new-url>` is the durable fix — stop pushing through the redirect entirely.
- `--force-with-lease` is preserved throughout; converting to a branch source does not weaken the safety guard.

## Verified On

| Project | Context | Details |
| --------- | --------- | --------- |
| ProjectHephaestus | Repo renamed to Hephaestus; resign-tag push to `2054-auto-impl` failed with `commit_refs` until `set-url` + branch-source | 2026-07-12 session (verified-local) |
