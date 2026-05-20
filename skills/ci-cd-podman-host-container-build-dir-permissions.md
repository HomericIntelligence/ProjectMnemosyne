---
name: ci-cd-podman-host-container-build-dir-permissions
description: "Fix 'mkdir: Permission denied' / PermissionError [Errno 13] when a justfile recipe runs ON THE HOST but writes into build/ or dist/ that a prior rootless-Podman container recipe populated as a subuid-mapped uid. Use when: (1) a just recipe fails writing to build/ or dist/ after another recipe ran in-container, (2) rootless Podman left files owned by a high subuid (e.g. 524288) the host user cannot write, (3) 'pixi: not found' on a CI runner because a recipe ran host-side instead of in-container, (4) chmod -R fails with EPERM on foreign-owned sibling files in a shared dir, (5) deciding whether a justfile recipe belongs host-side or in the container _run wrapper."
category: ci-cd
date: 2026-05-19
version: "1.0.0"
user-invocable: false
verification: verified-ci
tags: [podman, rootless, subuid, justfile, permissions, build-dir, dist, container-host-boundary, chmod, pixi]
---

# Podman Host/Container build/ Directory Permission Mismatches in justfile Recipes

## Overview

| Field | Value |
|-------|-------|
| **Date** | 2026-05-19 |
| **Objective** | Fix the repeating bug class where a justfile recipe runs on the HOST but writes into `build/` or `dist/` that a prior rootless-Podman container recipe populated as a subuid-mapped uid the host user cannot write |
| **Outcome** | Successful — all 4 occurrences in ProjectOdyssey's packaging pipeline fixed (PRs #5422, #5424, #5425, #5426), each with green CI |
| **Verification** | verified-ci — all 4 permission fixes merged with passing CI; the packaging pipeline ran end-to-end |
| **History** | n/a (initial version) |

## When to Use

- A `just` recipe fails with `mkdir: Permission denied` or `PermissionError: [Errno 13] Permission denied`
  when writing into `build/` (or `dist/`)
- The failing recipe runs **on the host**, and a *different* recipe previously populated that directory
  **inside a rootless Podman container**
- `ls -ln build/` shows files owned by a very high uid (e.g. `524288`, `100000+`) — a subuid mapping,
  not your host uid
- A CI runner fails with `pixi: not found` because a recipe that needs the pixi environment ran
  host-side instead of through the container
- `chmod -R …` fails with `Operation not permitted` (EPERM) on files inside a shared directory that
  the recipe did not create itself
- You are deciding whether a new justfile recipe should run host-side or be wrapped in the `_run`
  container wrapper

## Why This Happens

ProjectOdyssey uses **rootless Podman**. When a recipe runs inside the container (e.g.
`just package-release` populating `build/release/`), files written from inside the container land on
the host bind mount owned by the container user's **subuid-mapped uid** — a number far outside the
host's normal range (the kernel maps container uid → host subuid via `/etc/subuid`). The host user
cannot write (or even `chmod`) those files: `chmod` on a file you do not own is `EPERM`, full stop.

So any justfile recipe that **runs on the host** and then writes into `build/` or `dist/` will hit
`Permission denied` the moment a prior in-container recipe touched the same tree. This bug class hit
**four times** in one packaging session.

## Verified Workflow

### Quick Reference

```bash
# FIX A — recipe must run in the container: wrap it in the _run wrapper
# Before (runs host-side, hits Permission denied + 'pixi: not found' on CI):
build-recipe:
    pixi exec --spec rattler-build -- rattler-build build --recipe conda.recipe/recipe.yaml
# After (runs inside the container where pixi exists and uids are consistent):
build-recipe:
    @just _run "pixi exec --spec rattler-build -- rattler-build build --recipe conda.recipe/recipe.yaml"

# FIX B — host creates a dir that an in-container recipe will write into: chmod 777 it first
mkdir -p dist
chmod 777 dist          # do this on the side that OWNS the dir, BEFORE the other side writes
just wheel              # in-container recipe can now write into dist/

# FIX C — an in-container recipe must chmod only the files IT created (never -R over the tree)
# Before (fails — recurses over host-owned sibling files the recipe does not own):
chmod -R o+rX dist
# After (narrow to exactly the artifacts this recipe produced):
chmod o+rX dist/projectodyssey-*.whl

# FIX D — reclaim a stale build dir from a prior run with a different uid mapping
# Host can mv a dir within a writable PARENT even if it cannot write the dir's CONTENTS:
mv build build.stale.$(date +%s)   # move the foreign-owned tree aside
mkdir build                         # recreate fresh, host-owned
```

### Detailed Steps

1. **Diagnose ownership.** `ls -ln build/` — if files are owned by a uid like `524288` or `100000+`,
   that is a Podman subuid mapping and the host user cannot write them.

2. **Decide where the recipe belongs.**
   - Needs the pixi environment, or writes into a tree the container also writes → **wrap in `_run`**
     so it runs in-container. This also fixes `pixi: not found` on CI runners.
   - Genuinely host-only → ensure it never writes into a container-shared directory.

3. **Apply Fix A — wrap host-only recipes in `_run`.** A recipe like `build-recipe` (rattler-build)
   or `wheel` that needs pixi and writes build artifacts must run in the container. Wrapping it also
   resolves `pixi: not found`, because the CI runner host has no pixi but the container does.

4. **Apply Fix B — `chmod 777` a shared dir on the owning side, before the other side writes.**
   When a host step creates `dist/` and then hands off to an in-container `just wheel`, the host must
   `chmod 777 dist` immediately after `mkdir dist` so the container user can write into it.

5. **Apply Fix C — narrow `chmod` to only the files the recipe created.** An in-container recipe
   doing `chmod -R o+rX dist` fails with `EPERM` because the recursion walks **foreign-owned sibling
   files** (host-created) that the recipe does not own. `chmod` on a file you do not own is always
   `EPERM`. Replace the `-R` tree walk with an explicit glob of just this recipe's own artifacts
   (`chmod o+rX dist/projectodyssey-*.whl`).

6. **Apply Fix D — reclaim a stale build dir via `mv`, not `chmod`.** A leftover `build/` from a
   prior run with a *different* uid mapping cannot be written or `chmod`'d by the host. But the host
   **can `mv` the whole directory aside** as long as it can write the *parent* — moving a directory
   only needs write permission on the parent, not on the directory's contents. Move it aside (or
   reclaim it) and recreate a fresh host-owned `build/`.

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
|---------|----------------|---------------|----------------|
| `just build-recipe` run host-side | The rattler-build recipe ran directly on the host | The host user cannot write into `build/` once an in-container recipe owns it (subuid mapping); also `pixi: not found` on CI runners which have no host pixi | Wrap recipes that need pixi or write build artifacts in the `_run` container wrapper (PR #5422) |
| `just wheel` run host-side | The wheel-build recipe ran on the host | Same `build/`/`dist/` permission failure plus `pixi: not found` on the CI runner | Wrap `wheel` in `_run` so it runs in-container where pixi exists and uids are consistent (PR #5424) |
| Host creates `dist/`, in-container `just wheel` writes into it | `release.yml` did `mkdir dist` host-side, then invoked the in-container `just wheel` | The host-created `dist/` is owned by the host uid; the container user (subuid-mapped) cannot write into it | After `mkdir dist`, `chmod 777 dist` on the host side BEFORE the in-container recipe writes (PR #5425) |
| `chmod -R o+rX dist` inside the in-container recipe | The recipe tried to make its output world-readable with a recursive chmod | `-R` recursed onto host-owned sibling files the recipe did not own → `chmod` on a non-owned file is `EPERM` → recipe failed | Never `chmod -R` over a tree that may contain foreign-owned siblings; narrow the chmod to only the specific files the recipe itself created (PR #5426) |

## Results & Parameters

### Decision rule: host-side vs `_run`

```text
Does the recipe need pixi / the Mojo toolchain?            → _run (in-container)
Does the recipe write into build/ or dist/?                → _run, OR chmod 777 the dir first
Is it pure host shell (git, gh, file moves outside build/) → host-side is fine
```

### chmod ownership rule

```text
chmod on a file you OWN          → OK
chmod on a file you do NOT own   → EPERM (always — even +r, even as the same group)
mv a directory                   → needs write on the PARENT only, not on the dir's contents
```

So: to make foreign-owned artifacts readable, do the `chmod` on the side that **created** them; to
get rid of a foreign-owned directory, `mv` it aside from a writable parent.

### ProjectOdyssey packaging session — the 4 fixes

| PR | Recipe | Problem | Fix |
|----|--------|---------|-----|
| #5422 | `build-recipe` (rattler-build) | ran host-side → Permission denied + `pixi: not found` | wrapped in `_run` |
| #5424 | `wheel` | ran host-side → Permission denied + `pixi: not found` | wrapped in `_run` |
| #5425 | `release.yml` → `dist/` | host created `dist/`, in-container `just wheel` could not write | `chmod 777 dist` after `mkdir` |
| #5426 | in-container wheel recipe | `chmod -R o+rX dist` hit EPERM on host-owned siblings | narrowed to `chmod o+rX dist/projectodyssey-*.whl` |

## Verified On

| Project | Context | Details |
|---------|---------|---------|
| ProjectOdyssey | Issue #5413 packaging verification session — rootless Podman, host/container `build/` and `dist/` boundary | PRs #5422, #5424, #5425, #5426 — all merged with green CI |

## See Also

- `docker-mojo-uid-mismatch-crash-fix` — a *different* uid-mismatch failure (a deterministic `mojo run` crash, exit 134, `filesystem_error` on `$HOME/.modular`); this skill is about justfile-recipe `build/`/`dist/` write permissions, a distinct search surface
- `ci-cd-verify-merged-prs-end-to-end` — this permission class was 4 of the 12 defects that pass surfaced
- `tooling-justfile-pixi-ecosystem-wrapping` — broader justfile/pixi wrapping patterns
