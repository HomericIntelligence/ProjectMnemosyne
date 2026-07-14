---
name: rename-propagation-unexercised-paths-break-later
description: "A deliberately PARTIAL rename (references renamed now, directory/path renames DEFERRED) is a latent landmine: consumers that were rewritten to the aspirational future name pass the rename PR's CI only because they aren't in the required-check set, then detonate LATER on unrelated PRs. Use when: (1) planning or reviewing a 'drop the prefix' / dir-rename PR where the on-disk path rename is upstream-gated or deferred, (2) some references now point at a short/new name while .gitmodules (or the real dir) still uses the old name, (3) install/build/deploy scripts or non-required matrix legs fail LATER with 'submodule failed to initialize / still empty', a missing conan profile, or a path that resolves to nothing, (4) you're tempted to trust a green rename PR as proof the rename is complete, (5) you fixed ONE consumer (e.g. a justfile recipe) as a follow-up without grepping siblings for the same class of bug."
category: tooling
date: 2026-07-13
version: "1.0.0"
user-invocable: false
verification: verified-ci
tags:
  - rename
  - submodule-path
  - gitmodules
  - partial-rename
  - deferred-rename
  - not-exercised
  - surfaces-later
  - latent
  - install-scripts
  - conan-profile
  - required-checks
  - odysseus
---

# Rename Propagation: Unexercised Paths Break Later

## Overview

| Field | Value |
| ------- | ------- |
| **Date** | 2026-07-13 |
| **Objective** | Explain why a deliberately PARTIAL rename (references renamed, on-disk paths deferred) leaves latent breakage that a green rename PR does not catch, and how to audit for it BEFORE it detonates on an unrelated PR. |
| **Outcome** | Root cause identified: consumers rewritten to the aspirational post-cutover name (`control/Nestor`, `testing/Charybdis`) while `.gitmodules` still records the pre-cutover paths (`control/ProjectNestor`, `testing/ProjectCharybdis`). Nothing failed at merge because those consumers (install scripts, build recipes) were not in the required-check set. Breakage surfaced later, piecemeal, on innocent PRs. |
| **Verification** | verified-ci — HomericIntelligence/Odysseus PR #385 ("chore: drop 'Project' prefix …") merged green; the mismatch was later observed as `11 submodule(s) failed to initialize — still empty after submodule update` (install.sh exit 1) and a `_build-nestor` recipe pointing at a nonexistent conan profile. |

## When to Use

- You are planning or reviewing a rename that is INTENTIONALLY partial — references renamed now, the directory / on-disk path rename deferred (upstream-gated, staged cutover, "we'll flip the dirs later").
- `.gitmodules` (or the actual directory) still uses the OLD path while some consumers already reference the SHORT/new name.
- An install/build/deploy script or a non-required CI matrix leg fails LATER with:
  - `N submodule(s) failed to initialize — still empty after submodule update` → `install.sh` exits 1,
  - a missing/renamed conan profile (`--profile=conan/profiles/debug` when the real profiles are `nestor-debug` / `nestor-release`),
  - any path/profile reference that resolves to nothing on disk.
- Someone says "the rename PR is green, so the rename is done." (It isn't — green only covers exercised paths.)
- You just fixed ONE consumer (a justfile recipe, one script) as a follow-up and are about to move on WITHOUT grepping sibling scripts for the identical bug.

## Verified Workflow

The canonical source of truth is what is ACTUALLY on disk (here `.gitmodules` / the real
directory names), NOT the aspirational future name. Reconcile every consumer to the source of
truth, then prove each referenced path/profile resolves to a real target — do not trust the
rename PR's green CI.

### Quick Reference

```bash
# 1. Establish the source of truth (what paths REALLY exist on disk right now).
grep -E '^\s*path = ' .gitmodules           # canonical submodule dir names
# (or: git ls-files -- '<area>/' | head; ls -d <area>/*/ )

# 2. Grep the WHOLE repo for BOTH the old and the new/short forms.
OLD='ProjectNestor'; NEW='control/Nestor'   # example: prefix-dropped short form
grep -rnE "control/Nestor|testing/Charybdis|control/ProjectNestor|testing/ProjectCharybdis" \
  scripts/ justfile .github/ 2>/dev/null

# 3. Reconcile EVERY consumer to the source of truth (the real dir), not the future name.

# 4. Prove each referenced path/profile resolves to a real on-disk target.
for p in $(grep -rhoE '(control|testing)/[A-Za-z]+' scripts/install/ | sort -u); do
  [ -d "$p" ] || echo "MISSING DIR: $p"
done
[ -f control/ProjectNestor/conan/profiles/nestor-debug ] || echo "MISSING PROFILE"

# 5. Syntax-check every script the rename touched (bash -n catches nothing about paths,
#    but confirms you didn't corrupt the file while reconciling).
for f in scripts/install/*.sh scripts/install/dev/*.sh; do bash -n "$f" || echo "SYNTAX: $f"; done

# 6. Audit the UNEXERCISED legs explicitly — install/build/deploy scripts and non-required
#    matrix legs are exactly where a partial rename hides. Don't stop at "9/10 jobs green."
```

### Detailed Steps

1. **Decide the source of truth and write it down.** For a deferred directory rename, the truth
   is the directory that exists on disk TODAY (recorded in `.gitmodules` for submodules). Every
   consumer must reference THAT, not the name the dir will eventually have. The aspirational name
   is not a fact yet.

2. **Grep the whole repo for BOTH forms and enumerate every consumer.** Old form AND new/short
   form. Include the low-visibility surfaces: `scripts/install/*.sh`, `scripts/install/dev/*.sh`,
   `justfile`/`Makefile` recipes, `Dockerfile` COPY lines, `.github/workflows/*` matrix legs,
   deploy manifests. These are the consumers a rename PR's required checks usually do NOT run.

3. **Reconcile each consumer to the source of truth.** Rewrite short/aspirational references back
   to the real on-disk path. If the future name is genuinely coming, the ONLY place it belongs is
   the deferred dir-rename PR itself — not scattered ahead of it in unexercised scripts.

4. **Prove resolution, not just spelling.** For every referenced path assert `[ -d "$p" ]` /
   `[ -f "$file" ]`; for every profile / config selector assert the named target exists
   (e.g. `conan/profiles/nestor-debug`, not `conan/profiles/debug`). A reference that is spelled
   consistently but points at a nonexistent target is still broken.

5. **Treat the rename PR's green CI as covering ONLY exercised paths.** Required checks are the
   set of jobs gating merge; a consumer not in that set can be arbitrarily broken and still merge
   green. Explicitly run or read-through the install / build / deploy scripts and any non-required
   matrix legs.

6. **When you find one instance of the bug, grep for the WHOLE class.** The justfile recipe and
   the install scripts had the IDENTICAL mismatch. Fixing one and filing the rest as "later"
   guarantees the siblings surface on the next innocent PR. Fix the class in one sweep.

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
| --------- | ---------------- | --------------- | ---------------- |
| Trust the rename PR's green CI as "rename complete" | Merged the "drop 'Project' prefix" PR (#385) after all required checks passed; assumed the prefix drop was fully propagated | Green only covered EXERCISED paths. The renamed-ahead consumers (install scripts, `_build-nestor` recipe) were not in the required-check set, so they were never run — they stayed broken and detonated later on unrelated PRs | A rename PR's green CI proves nothing about consumers outside the required-check set. Audit install/build/deploy scripts and non-required matrix legs explicitly before calling a rename done. |
| Rename references ahead of the deferred directory rename | Rewrote consumers to the short post-cutover names (`control/Nestor`, `testing/Charybdis`) while `.gitmodules` still recorded `control/ProjectNestor`, `testing/ProjectCharybdis` (the dir rename was deliberately deferred/upstream-gated) | The references pointed at directories that did not exist on disk yet. `git submodule update` left them empty → `11 submodule(s) failed to initialize — still empty after submodule update`, and `install.sh` exited 1 | For a PARTIAL rename, reconcile every consumer to the CURRENT source of truth (`.gitmodules` / the real dir), NOT the aspirational future name. The future name belongs only in the deferred dir-rename PR. |
| Fix one consumer, defer the siblings | Fixed the `justfile` `_build-nestor` recipe (filed as a follow-up) without grepping sibling scripts for the same class | `scripts/install/30-submodules.sh`, `40-pixi-envs.sh`, `50-cpp-builds.sh` (and dev scripts) had the IDENTICAL short-path bug; found only when a later PR's Install legs failed | On finding one instance, grep the WHOLE repo for the class (both old and new forms) and fix all of them in one sweep. Piecemeal fixes leave the siblings to surface on the next innocent PR. |
| Assume a consistently-spelled reference resolves | Left `_build-nestor` using `--profile=conan/profiles/debug` because it "looked right" | Nestor's real profiles are `nestor-debug` / `nestor-release`; `conan/profiles/debug` does not exist, so the build recipe pointed at a nonexistent profile | Verify each referenced path/profile RESOLVES to a real on-disk target (`[ -d ]` / file exists), not merely that it is spelled consistently. |

## Results & Parameters

### The mismatch (HomericIntelligence/Odysseus, after PR #385)

```text
# Source of truth — .gitmodules still records the PRE-cutover (deferred) paths:
path = control/ProjectNestor
path = testing/ProjectCharybdis

# But consumers were rewritten to the SHORT post-cutover names:
scripts/install/30-submodules.sh:  ["control/Nestor"]="control/Nestor/CMakeLists.txt"
scripts/install/30-submodules.sh:  ["testing/Charybdis"]="testing/Charybdis/CMakeLists.txt"
scripts/install/40-pixi-envs.sh:   "control/Nestor"   "testing/Charybdis"
scripts/install/50-cpp-builds.sh:  "control/Nestor"   "testing/Charybdis"
```

### Later symptoms on unrelated PRs (NOT on the rename PR)

```text
# Install phase:
11 submodule(s) failed to initialize — still empty after submodule update
install.sh: exit 1

# Build recipe:
_build-nestor used --profile=conan/profiles/debug
# real profiles: conan/profiles/nestor-debug, conan/profiles/nestor-release
```

### Why it slipped the rename PR

| Fact | Consequence |
| ------ | ------------- |
| The dir rename was deliberately DEFERRED (upstream-gated) | References got ahead of the on-disk truth |
| Install/build scripts + non-required matrix legs are NOT in the required-check set | The broken consumers were never run at merge time |
| Green CI == exercised paths only | The rename PR was green while the rename was incomplete |
| The author even flagged the risk in their report | Flagging is not fixing — it still shipped and bit later |

### Companion cross-references

- [tooling-bulk-rename-relative-path-trap.md](tooling-bulk-rename-relative-path-trap.md) — same
  "9/10 CI green, only a validator/unexercised leg catches it" signature, different mechanism
  (a lexical relative-path perl trap rather than a deferred directory rename).
- [logical-model-family-rename-with-storage-exceptions.md](logical-model-family-rename-with-storage-exceptions.md)
  — the logical-vs-physical split; there the rule is DON'T over-rename real paths, here the failure
  is references renamed AHEAD of the real path. Both hinge on "reconcile to what's actually on disk."
- [tooling-plugin-command-codebase-rename.md](tooling-plugin-command-codebase-rename.md) — the
  COMPLETE-rename counterpart ("zero stale references"); this skill is its partial-rename inverse.
- [odysseus-multi-branch-submodule-pin-management.md](odysseus-multi-branch-submodule-pin-management.md)
  — sibling Odysseus submodule-path/pin foot-guns; consult when the affected paths are submodules.

## Verified On

| Project | Context | Details |
| --------- | --------- | --------- |
| Odysseus | PR #385 — "chore: drop 'Project' prefix …" (merged 2026-07-13). Dir renames deliberately deferred (upstream-gated); `.gitmodules` kept `control/ProjectNestor` / `testing/ProjectCharybdis` while install scripts + `_build-nestor` used the short names. | Rename PR merged green (unexercised consumers not in required checks); mismatch surfaced later as `11 submodule(s) failed to initialize` / install.sh exit 1 and a nonexistent conan profile in `_build-nestor`. verified-ci. |
