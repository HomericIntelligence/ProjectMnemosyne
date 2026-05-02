---
name: odysseus-submodule-symlink-to-gitlink
description: "Convert absolute-path symlinks masquerading as git submodules into real git submodules (mode 160000 gitlinks). Use when: (1) git ls-tree shows mode 120000 entries that should be submodules, (2) submodule paths resolve to local absolute symlinks instead of remote-cloned repos, (3) git submodule update --init fails to clone repos because entries are symlinks not gitlinks."
category: architecture
date: 2026-03-29
version: "2.0.0"
user-invocable: false
verification: verified-local
history: odysseus-submodule-symlink-to-gitlink.history
tags: [submodule, symlink, gitlink, git, meta-repo, gitmodules]
---

# Odysseus: Convert Symlinks to Real Submodules

## Overview

| Field | Value |
| ------- | ------- |
| **Date** | 2026-03-29 |
| **Objective** | Fix submodules that were absolute-path symlinks (mode 120000) pointing to local paths instead of real git submodules (mode 160000) |
| **Outcome** | Successful. PR #66 converted all 11 symlinks to real submodules cloned from `https://github.com/HomericIntelligence/<RepoName>.git`, pinned to main HEAD SHA, normalized `.gitmodules` to `HomericIntelligence` URL casing and 4-space indentation. |
| **Verification** | verified-local — submodule conversion and PR workflow were verified end-to-end locally |
| **Split Note** | BUILD_ROOT meta-repo justfile pattern moved to `meta-repo-build-root-pattern`. Rebase full-file-rewrite conflict strategy moved to `rebase-full-file-rewrite-conflict`. |

## When to Use

- `git ls-tree HEAD <path>` shows mode `120000` (symlink) where you expected mode `160000` (gitlink/submodule)
- `git submodule status` shows `-<sha>` or reports submodules as uninitialized even after `git submodule update --init`
- Submodule directories resolve to local absolute paths instead of remote-cloned repos (non-portable, breaks CI)
- `.gitmodules` entries use incorrect URL casing (`homericintelligence` vs `HomericIntelligence`)

## Verified Workflow

### Quick Reference

```bash
# 1. Diagnose: spot mode 120000 entries
git ls-tree HEAD --name-only -r | xargs -I{} git ls-tree HEAD {} 2>/dev/null | grep "^120000"
# OR: check each declared submodule path
git ls-tree HEAD infrastructure/AchaeanFleet control/ProjectAgamemnon  # look for 120000 vs 160000

# 2. Convert a single symlink to a real submodule
git rm infrastructure/AchaeanFleet                         # removes symlink from index (and disk)
git submodule add https://github.com/HomericIntelligence/AchaeanFleet.git infrastructure/AchaeanFleet
git -C infrastructure/AchaeanFleet checkout main           # pin to main HEAD SHA

# 3. Normalize .gitmodules (tabs→spaces, correct URL casing)
# Edit .gitmodules manually: ensure all URLs use HomericIntelligence (capital H, I)
# and use 4-space indentation throughout

# 4. Commit and push
git add .gitmodules
git commit -m "fix(submodules): convert symlinks to real gitlinks, normalize .gitmodules"
```

### Detailed Steps

#### Phase 1: Diagnosis

1. Run `git ls-tree HEAD` on each directory declared in `.gitmodules` and verify the mode is `160000`. Mode `120000` means git is tracking a symlink, not a submodule.

2. Check whether the symlink target is an absolute local path:
   ```bash
   ls -la infrastructure/AchaeanFleet  # shows -> /home/mvillmow/AchaeanFleet
   ```
   Absolute symlinks are non-portable and break on any machine except the author's.

3. Verify `.gitmodules` URL casing matches the actual GitHub org name. GitHub URLs are case-insensitive for cloning but the canonical form must match the org's actual casing (e.g., `HomericIntelligence` not `homericintelligence`).

#### Phase 2: Conversion (repeat for each symlink)

4. Remove the symlink from the git index. This also removes the directory from disk:
   ```bash
   git rm infrastructure/AchaeanFleet
   ```
   **Expect the directory to disappear from disk entirely.** This is normal — `git rm` on a symlink removes both the index entry and the symlink file itself.

5. Add the real submodule. The directory must NOT exist at this point (step 4 guarantees this):
   ```bash
   git submodule add https://github.com/HomericIntelligence/AchaeanFleet.git infrastructure/AchaeanFleet
   ```
   This clones the repo and updates `.gitmodules` automatically.

6. Pin the submodule to a specific commit (use current `main` HEAD):
   ```bash
   git -C infrastructure/AchaeanFleet checkout main
   ```
   The parent repo will stage the new commit SHA automatically.

7. Repeat steps 4-6 for all remaining symlinks. Process them one at a time.

#### Phase 3: Normalize `.gitmodules`

8. Open `.gitmodules` and verify:
   - All `url =` values use correct org-name casing (`HomericIntelligence`)
   - Indentation is consistent (prefer 4-space; avoid tabs which cause POSIX parsing issues)
   - Each submodule block has `path`, `url`, and optionally `branch = main`

9. Stage and commit everything together:
   ```bash
   git add .gitmodules infrastructure/ control/ provisioning/ ci-cd/ research/ testing/ shared/
   git commit -m "fix(submodules): convert 11 symlinks to real gitlinks, normalize .gitmodules"
   ```

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
| --------- | ---------------- | --------------- | ---------------- |
| git submodule add before git rm | Attempted `git submodule add` with the symlink still on disk | `git submodule add` fails if the destination path already exists, even as a symlink | Always `git rm` the symlink first; confirm the directory is gone from disk before running `git submodule add` |
| Relative symlinks in .gitmodules url | Left the original `url = ../AchaeanFleet` relative paths in .gitmodules after conversion | Relative URLs in `.gitmodules` resolve relative to the remote origin, not the local filesystem; CI failed to clone submodules | Use full `https://github.com/OrgName/RepoName.git` absolute URLs in every `.gitmodules` entry |
| Wrong URL casing (`homeric-intelligence` vs `HomericIntelligence`) | Used lowercase or hyphenated org name in `.gitmodules` url | Submodule clone fails silently or resolves to wrong repo; breaks `git submodule update --init` on case-sensitive filesystems | Always verify the exact org/repo casing on GitHub and use the canonical form in every `.gitmodules` entry |

## Results & Parameters

### Conversion Summary

```yaml
repo: HomericIntelligence/Odysseus
branch_converted: fix/convert-symlinks-to-submodules
pr: "#66"

before:
  total_submodule_entries: 14
  real_gitlinks_mode_160000: 3   # ProjectAgamemnon, ProjectNestor, ProjectCharybdis
  symlinks_mode_120000: 11       # all others

after:
  real_gitlinks_mode_160000: 14
  symlinks_mode_120000: 0
  gitmodules_url_pattern: "https://github.com/HomericIntelligence/<RepoName>.git"
  gitmodules_indentation: "4-space"

submodules_converted:
  infrastructure: [AchaeanFleet, ProjectArgus, ProjectHermes]
  provisioning: [ProjectTelemachy, ProjectKeystone, Myrmidons]
  ci-cd: [ProjectProteus]
  research: [ProjectOdyssey, ProjectScylla]
  shared: [ProjectMnemosyne, ProjectHephaestus]
```

### Diagnostic Commands

```bash
# Check all declared submodule paths for symlink vs gitlink mode
git ls-files --stage | grep "^120000"      # prints symlinks tracked by git
git ls-files --stage | grep "^160000"      # prints real gitlinks

# Verify a submodule was cloned correctly after conversion
git submodule status control/ProjectAgamemnon
# Should show: " <sha> control/ProjectAgamemnon (heads/main)"
# NOT: "-<sha>" (missing) or "U<sha>" (merge conflict)

# Check .gitmodules URL casing
grep "url" .gitmodules | grep -v "HomericIntelligence"   # should return nothing
```

### Related PRs / Issues

```yaml
pr_66: "fix: convert symlinks to real submodules — fixes #4 (symlinks non-functional), #39 (URL casing)"
issue_4: "Submodule paths are absolute symlinks, non-functional outside author's machine"
issue_39: "gitmodules URL casing inconsistency (homericintelligence vs HomericIntelligence)"
```

## Verified On

| Project | Context | Details |
| --------- | --------- | --------- |
| HomericIntelligence/Odysseus | PR #66 (symlink conversion) — 2026-03-29 session | 11 symlinks converted, 14 .gitmodules entries normalized |
