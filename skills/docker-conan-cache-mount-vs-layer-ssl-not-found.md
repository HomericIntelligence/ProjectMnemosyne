---
name: docker-conan-cache-mount-vs-layer-ssl-not-found
description: "Fix a Docker C++/Conan build that fails at cmake configure with 'Library ssl not found in package' (OpenSSL-Target-release.cmake conan_package_library_targets) even though conanfile.py and CMakeLists are correct. Use when: (1) a Dockerfile builder stage fails at cmake configure with 'Library <x> not found in package', (2) the conan-install RUN uses --mount=type=cache for /root/.conan2, (3) the cmake step fails suspiciously fast (~0.2s) after a buildx cache-from hit, (4) a fix works on a native/local build but the Docker build stays broken, (5) deciding whether to bake Conan packages into an image layer vs a cache mount."
category: ci-cd
date: 2026-07-13
version: "1.0.0"
user-invocable: false
verification: verified-ci
tags:
  - docker
  - buildx
  - conan
  - cmake
  - cmakedeps
  - openssl
  - cache-mount
  - image-layer
  - gha-cache
---

# Docker Conan Cache-Mount vs Image-Layer SSL-Not-Found

## Overview

| Field | Value |
| ------- | ------- |
| **Date** | 2026-07-13 |
| **Objective** | Fix a Docker builder stage failing at cmake configure with `Library 'ssl' not found in package`, despite a correct conanfile.py and CMakeLists |
| **Outcome** | Successful — removed `--mount=type=cache` from the conan-install RUN so packages bake into the image layer; `Found OpenSSL: 3.6.2`, `Configuring done`, `[81/81] Linking CXX executable` |
| **Verification** | verified-ci — reproduced both states locally (warm mount → fails; mount removed → builds), then `build (agamemnon)` leg went GREEN on real CI after the fixed Dockerfile landed |

## When to Use

- A Dockerfile builder stage fails at `cmake` configure with `CMake Error: Library 'ssl' not found in package` (or any Conan lib), pointing at `build/OpenSSL-Target-release.cmake:23 (conan_package_library_targets)`
- The conan-install `RUN` mounts the package store as an ephemeral cache: `RUN --mount=type=cache,target=/root/.conan2/p ... conan install --output-folder=build`
- The cmake step fails suspiciously **fast (~0.2s)** — a tell that `conan install` did NOT re-run (a layer cache hit against an empty mount), rather than genuinely resolving packages
- A fix (e.g. adding an explicit `requires`) makes the **native/local** build pass but the **Docker** build stays broken
- You use buildx `cache-from: type=gha` and a fresh runner cache-hits the conan-install layer
- You are deciding whether Conan packages belong in a `--mount=type=cache` or baked into the image layer

## Root Cause

The reusable insight is a **lifetime mismatch between a cache mount and the image layer**:

- The Dockerfile put the Conan package store on `RUN --mount=type=cache,target=/root/.conan2/p`. A cache mount is **ephemeral per build** — its contents are NOT part of the resulting image layer.
- But `conan install --output-folder=build` **also** writes the CMakeDeps generator files (`build/OpenSSL-Target-release.cmake`, etc.) into the **image layer**, with **absolute package-lib paths baked in** (e.g. `/root/.conan2/p/<hash>/lib/libssl.a`).

So the generated `.cmake` files and the package store they point at have **different lifetimes**. On a fresh CI runner where buildx **cache-hits the `conan install` layer** (via `cache-from: type=gha`), the `build/*.cmake` files come back from the layer cache, but the mounted package store is **empty** → `conan install` never re-ran to repopulate it → cmake resolves `OpenSSL-Target-release.cmake`, looks for `libssl.a` at the baked absolute path, and reports **`Library 'ssl' not found in package`**. The ~0.2s cmake failure is the fingerprint: the resolve step is instant because nothing was actually installed.

## Verified Workflow

### Quick Reference

```dockerfile
# BROKEN — package store is ephemeral, but generated .cmake files land in the layer
COPY conanfile.py .
RUN --mount=type=cache,target=/root/.conan2/p \
    conan install . --output-folder=build --build=missing

# FIXED — drop the cache mount so resolved packages bake into the SAME layer as build/*.cmake
COPY conanfile.py .
RUN conan install . --output-folder=build --build=missing
```

Keep `COPY conanfile.py .` immediately above the `RUN` so the layer is invalidated only when dependencies change (preserving most of the cache benefit without the lifetime mismatch).

### Detailed Steps

1. **Recognize the fingerprint.** cmake configure dies at `OpenSSL-Target-release.cmake` (or another `*-Target-*.cmake`) with `Library '<x>' not found in package`, AND the cmake step finished in a fraction of a second — meaning `conan install` did not actually run this build.

2. **Confirm the mount.** Grep the Dockerfile for the conan-install RUN:

   ```bash
   grep -n 'mount=type=cache.*conan\|conan install' Dockerfile
   ```

   If the conan store (`/root/.conan2` or `.../p`) is on `--mount=type=cache`, you have the lifetime mismatch.

3. **Fix.** Remove `--mount=type=cache` from the conan-install RUN so the resolved package binaries bake into the same image layer as the generated `build/*.cmake` files:

   ```dockerfile
   COPY conanfile.py .
   RUN conan install . --output-folder=build --build=missing
   ```

4. **Reproduce both states locally** before trusting CI (see Verification Method below).

5. **Verify on real CI.** After the fixed Dockerfile lands (often via a submodule pin bump), confirm the Docker leg goes green — the native build is NOT sufficient evidence (see Failed Attempt #1).

### Verification Method (reproduce the layer-cache hit locally)

- **Warm state (matches CI failure):** with the Conan cache warm and the mount in place, build → cmake fails with `ssl not found` in ~0.2s (the mount is populated on your machine but the failure mode mirrors CI's empty-mount + cached-layer path).
- **Fixed state:** remove the mount, rebuild → OpenSSL is built/resolved from the layer and the server links cleanly (`[81/81] Linking CXX executable`).
- Do NOT verify a fresh Docker build through a pipe. `podman build ... | grep ...` exits with **grep's** status, not the build's — a build that actually FAILED can look like exit 0. Read the build's own final conclusion (`Configuring done`, `Linking`, or the error), not a grep of its log.

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
| --------- | ---------------- | --------------- | ---------------- |
| Add explicit `requires("openssl/3.6.2")` | openssl was only transitive via libcurl, so added it explicitly to conanfile.py | Fixed the NATIVE build but NOT the Docker build — the repo's CI never builds the Dockerfile (it's tag-gated in a separate workflow), so this went green natively while Docker stayed broken | A native-build green is NOT evidence a Docker-build bug is fixed. Confirm the actual failing leg; know which workflow builds the Dockerfile. |
| Salt the buildx GHA cache scope | Bumped `scope=component` → `scope=component-r2` assuming stale layer cache | Still `ssl not found`. A scope bump invalidates the cache ONCE, but the mount/layer lifetime mismatch **recurs** on the next cache-hit build | A stale-cache bump can't fix a structural lifetime mismatch — it just delays the recurrence by one build. |
| `podman build ... \| grep` "passed" | A `--no-cache` build appeared to exit 0 through a grep pipeline | The grep pipeline masked the real result: the pipeline exit code is grep's, not the build's, and the build had actually FAILED | Never gate a build's success on `build | grep`. Check the build command's own exit code / final conclusion. |

## Results & Parameters

```yaml
# Symptom
error: "CMake Error: Library 'ssl' not found in package"
location: "build/OpenSSL-Target-release.cmake:23 (conan_package_library_targets)"
fingerprint: cmake configure fails in ~0.2s (conan install did not re-run)
trigger: fresh CI runner cache-hits the conan-install layer via cache-from type=gha

# Root cause
conan_store_on: "RUN --mount=type=cache,target=/root/.conan2/p"   # ephemeral per build
generated_cmakedeps: "build/OpenSSL-Target-release.cmake"          # baked into image layer
baked_abs_path: "/root/.conan2/p/<hash>/lib/libssl.a"
mismatch: "generated .cmake files (layer) point at a package store (cache mount) with a different lifetime"

# Fix
action: remove --mount=type=cache from the conan-install RUN
keep: "COPY conanfile.py . directly above RUN (layer invalidated only when deps change)"

# After fix
found: "Found OpenSSL: 3.6.2"
configure: "Configuring done"
link: "[81/81] Linking CXX executable"
ci_leg: "build (agamemnon) — GREEN after pin bump landed the fixed Dockerfile"
```

## Verified On

| Project | Context | Details |
| --------- | --------- | --------- |
| ProjectAgamemnon | C++/Conan builder-stage Dockerfile; `build (agamemnon)` CI leg | 2026-07-13 — reproduced locally (warm mount fails, mount removed builds); CI green after the fixed Dockerfile landed via pin bump |

## See Also

- [`conan-cmakeuserpresets-duplicate-preset-collision`](./conan-cmakeuserpresets-duplicate-preset-collision.md) — a different Conan/CMake failure mode (duplicate preset names from two output-folders)
- [`natsc-fetchcontent-cpp20-integration`](./natsc-fetchcontent-cpp20-integration.md) — OpenSSL/libssl as a build dependency in C++20 CMake projects
