---
name: odysseus-submodule-symlink-to-gitlink
description: "Convert absolute-path symlinks masquerading as git submodules into real git submodules (mode 160000 gitlinks), and orchestrate out-of-tree CMake builds in a meta-repo without importing tool deps. Use when: (1) git ls-tree shows mode 120000 entries that should be submodules, (2) submodule paths resolve to local absolute symlinks instead of remote-cloned repos, (3) adding a BUILD_ROOT redirect pattern for a meta-repo justfile, (4) resolving a rebase conflict where one side is a full file rewrite."
category: architecture
date: 2026-03-29
version: "1.0.0"
user-invocable: false
verification: verified-local
tags: [odysseus, submodule, symlink, gitlink, cmake, build-root, meta-repo, justfile, rebase, conflict]
---

# Odysseus: Convert Symlinks to Real Submodules and BUILD_ROOT Orchestration

## Overview

| Field | Value |
|-------|-------|
| **Date** | 2026-03-29 |
| **Objective** | Fix 11 of 14 "submodules" that were absolute-path symlinks (mode 120000) pointing to `/home/mvillmow/<RepoName>` instead of real git submodules (mode 160000); add `just build` orchestration that redirects CMake output without importing tool deps into the root `pixi.toml` |
| **Outcome** | Successful. PR #66 converted all 11 symlinks to real submodules cloned from `https://github.com/HomericIntelligence/<RepoName>.git`, pinned to main HEAD SHA, normalized `.gitmodules` to `HomericIntelligence` URL casing and 4-space indentation. PR #67 added `just build/test/lint/clean` recipes with `BUILD_ROOT` pattern. Both PRs merged with CI passing. |
| **Verification** | verified-local — CI only validates configs/YAML, not the cmake build itself; the submodule conversion and PR workflow were verified end-to-end locally |

## When to Use

- `git ls-tree HEAD <path>` shows mode `120000` (symlink) where you expected mode `160000` (gitlink/submodule)
- `git submodule status` shows `-<sha>` or reports submodules as uninitialized even after `git submodule update --init`
- Submodule directories resolve to local absolute paths instead of remote-cloned repos (non-portable, breaks CI)
- `.gitmodules` entries use incorrect URL casing (`homericintelligence` vs `HomericIntelligence`)
- Adding a `BUILD_ROOT` pattern to a meta-repo `justfile` to redirect build artifacts without touching submodule files
- Resolving a rebase conflict where one branch is a complete file rewrite and the other has small targeted changes

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

# 5. BUILD_ROOT pattern in justfile
# BUILD_ROOT := join(justfile_directory(), "build")
# build NAME:
#     cmake -S {{justfile_directory()}}/control/Project{{NAME}} -B {{BUILD_ROOT}}/Project{{NAME}}
#     cmake --build {{BUILD_ROOT}}/Project{{NAME}} -- -j$(nproc)
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

#### Phase 4: BUILD_ROOT Pattern for Meta-Repo Justfile

10. Add a `BUILD_ROOT` variable at the top of `justfile` (NOT in `pixi.toml` — root deps are off-limits):
    ```just
    BUILD_ROOT := join(justfile_directory(), "build")
    ```

11. Add a build recipe per submodule type. CMake submodules use `-S` / `-B` flags to redirect output:
    ```just
    build-agamemnon:
        cmake -S {{justfile_directory()}}/control/ProjectAgamemnon -B {{BUILD_ROOT}}/ProjectAgamemnon
        cmake --build {{BUILD_ROOT}}/ProjectAgamemnon -- -j$(nproc)
    ```

12. For Mojo repos that do not support external build dirs, delegate to the submodule's own `just`:
    ```just
    build-odyssey:
        cd research/ProjectOdyssey && just build
    ```
    This keeps Mojo's local `build/` inside its own directory and does not try to override it.

13. Add `just clean` to remove the top-level `build/` directory:
    ```just
    clean:
        rm -rf {{BUILD_ROOT}}
    ```

#### Phase 5: Rebase Conflict — Full-File-Rewrite Strategy

14. When rebasing a branch where one side completely rewrote a file (e.g., `docs/architecture.md` was a post-migration rewrite) and the other side made small targeted additions:
    - **Take the full rewrite side entirely** (the PR branch's version)
    - **Manually identify the small delta** from the other side (e.g., a description update in one line)
    - **Apply that delta by hand** to the already-accepted rewrite
    - Do NOT attempt a 3-way merge of a file that was completely replaced — the merge result will be incoherent

    ```bash
    # During rebase conflict:
    git checkout --theirs docs/architecture.md   # take the rewrite (PR branch) version
    # Then manually edit the one line that main's commit changed
    git add docs/architecture.md
    git rebase --continue
    ```

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
|---------|----------------|---------------|----------------|
| Add cmake/ninja to root pixi.toml | Added `cmake`, `ninja`, and `pkg-config` as root-level pixi dependencies | Violates the meta-repo principle: Odysseus should not own build tool deps — each submodule manages its own pixi env | Root `pixi.toml` is for meta-repo tooling only (just, gh, etc.). Submodule build tools stay in each submodule's `pixi.toml`. |
| git submodule add before git rm | Attempted `git submodule add` with the symlink still on disk | `git submodule add` fails if the destination path already exists, even as a symlink | Always `git rm` the symlink first; confirm the directory is gone from disk before running `git submodule add` |
| Override CMake binaryDir via CMakePresets.json | Attempted to set `binaryDir` in the submodule's `CMakePresets.json` to `${sourceDir}/../../build/${sourceDirName}` | CMake presets hardcode `binaryDir` relative to `sourceDir`; the override is ignored by the CLI unless you pass `--preset` | Use `cmake -S <srcdir> -B <external_builddir>` at the call site in the justfile. The `-B` flag always wins over presets at the command line. |
| 3-way merge of post-migration architecture.md rewrite | Let `git rebase` auto-merge `docs/architecture.md` when one side was a full post-migration rewrite | The auto-merge produced a hybrid with duplicated sections, stale ai-maestro references mixed with new Agamemnon content, and broken markdown headings | When one side of a conflict is a complete file rewrite, always take the rewrite side explicitly (`git checkout --theirs`) and apply the other side's small delta manually |
| Relative symlinks in .gitmodules url | Left the original `url = ../AchaeanFleet` relative paths in .gitmodules after conversion | Relative URLs in `.gitmodules` resolve relative to the remote origin, not the local filesystem; CI failed to clone submodules | Use full `https://github.com/OrgName/RepoName.git` absolute URLs in every `.gitmodules` entry |

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

### BUILD_ROOT Justfile Pattern

```just
# Meta-repo justfile — root of Odysseus
BUILD_ROOT := join(justfile_directory(), "build")

# CMake submodules (C++ / CMake) — out-of-tree builds into BUILD_ROOT/<Name>/
build:
    #!/usr/bin/env bash
    set -euo pipefail
    CMAKE_REPOS=(ProjectAgamemnon ProjectNestor ProjectCharybdis ProjectKeystone)
    DIRS=(control control testing provisioning)
    for i in "${!CMAKE_REPOS[@]}"; do
        name="${CMAKE_REPOS[$i]}"
        dir="${DIRS[$i]}"
        cmake -S "{{justfile_directory()}}/${dir}/${name}" -B "{{BUILD_ROOT}}/${name}"
        cmake --build "{{BUILD_ROOT}}/${name}" -- -j$(nproc)
    done

# Mojo repos — cannot redirect build dir; delegate to submodule's own just
build-odyssey:
    cd research/ProjectOdyssey && just build

clean:
    rm -rf {{BUILD_ROOT}}
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
pr_67: "feat: E2E build recipe with BUILD_ROOT pattern"
issue_4: "Submodule paths are absolute symlinks, non-functional outside author's machine"
issue_39: "gitmodules URL casing inconsistency (homericintelligence vs HomericIntelligence)"
```

## Verified On

| Project | Context | Details |
|---------|---------|---------|
| HomericIntelligence/Odysseus | PR #66 (symlink conversion) and PR #67 (BUILD_ROOT) — 2026-03-29 session | 11 symlinks converted, 14 .gitmodules entries normalized, justfile build recipes added |
