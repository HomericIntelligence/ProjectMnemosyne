---
name: conan-2-profile-all-and-gcc-version-docker-chain
description: "Two-step Conan-2 + Docker failure chain hit during the 2026-05-10 multi-repo CI sweep in ProjectCharybdis PR #219. Stage 1: Conan 2 requires both host and build profiles, so `--profile=` (host only) blows up with 'default build profile doesn't exist' in a freshly-built image; fix is `--profile:all=`. Stage 2: after the profile fix, Conan dependencies (e.g. gtest) fail with 'CMAKE_C_COMPILER not set' because the profile pins `compiler.version=14` while Ubuntu 24.04 ships gcc-13 by default. Use when: (1) containerized C++ build using Conan 2 fails with 'default build profile doesn’t exist', (2) after fixing the profile chain a Conan dep fails with 'CMAKE_C_COMPILER not set', (3) Conan profile declares `compiler.version=14` but the base image is Ubuntu 24.04, (4) migrating from Conan 1 to Conan 2 in CI."
category: ci-cd
date: 2026-05-10
version: "1.0.0"
user-invocable: false
verification: verified-ci
tags:
  - conan
  - conan-2
  - docker
  - gcc
  - gcc-14
  - cmake
  - gtest
  - ubuntu-24.04
  - ci
  - profile
  - charybdis
  - homeric-intelligence
---

# Conan 2 `--profile:all=` and gcc Version Mismatch in Docker Chain

## Overview

| Field | Value |
|-------|-------|
| **Date** | 2026-05-10 |
| **Objective** | Get the containerized Conan-2 C++ build in ProjectCharybdis (PR #219, multi-repo CI sweep) past two cascading failures so dependency install + build succeeds end-to-end. |
| **Outcome** | Stage 1 fix (`--profile:all=`) shipped to main and verified to make the configure stage pass. Stage 2 (gcc-14 missing on Ubuntu 24.04) was hit but only the apt+`update-alternatives` workaround was attempted in-session and FAILED inside the Conan build sandbox; PR #219 was merged with a manual override and Stage 2 left as documented next steps (options B and C below). |
| **Verification** | `verified-ci` for the Stage 1 `--profile:all=` fix; `unverified` for Stage 2 options B (`tools.build:compiler_executables`) and C (downgrade `compiler.version=13`). The `update-alternatives` approach (Stage 2 option A) was attempted and confirmed insufficient. |

## When to Use

- A containerized C++ build using Conan 2 fails with:
  `ERROR: The default build profile '/home/builder/.conan2/profiles/default' doesn't exist.`
- After fixing the build-profile error, a Conan dependency such as `gtest/1.14.0` fails with:
  `CMake Error: CMAKE_C_COMPILER not set, after EnableLanguage`
  `CMake Error: CMAKE_CXX_COMPILER not set, after EnableLanguage`
- The Conan profile under `conan/profiles/` declares `compiler.version=14` and the Dockerfile base image is `ubuntu:24.04` (gcc-13.3 default).
- Migrating an existing Conan 1 CI job to Conan 2 and the previously-working `--profile=` flag now errors out.
- The freshly-built image has never run `conan profile detect` and there is no `~/.conan2/profiles/default` for the build user.

## Verified Workflow

### Quick Reference

```dockerfile
# --- Stage 1 fix: use --profile:all= so the in-repo profile applies to BOTH
#     host and build contexts in a single arg. Verified on Charybdis PR #219.

# Before (Conan 1 style; FAILS on Conan 2 in a fresh image):
RUN conan install . \
    --profile=conan/profiles/default \
    --build=missing

# After (Conan 2; PASSES the configure stage):
RUN conan install . \
    --profile:all=conan/profiles/default \
    --build=missing
```

```dockerfile
# --- Stage 2 option A (ATTEMPTED, FAILED in this session) ---
# Install gcc-14 + g++-14 and make them the system default via update-alternatives.
# Conan's build sandbox (run as the `builder` user) did NOT pick these up at
# sub-shell invocation time, so gtest still failed with CMAKE_C_COMPILER not set.

RUN apt-get update && apt-get install -y --no-install-recommends \
        gcc-14 g++-14 \
    && update-alternatives --install /usr/bin/gcc gcc /usr/bin/gcc-14 100 \
    && update-alternatives --install /usr/bin/g++ g++ /usr/bin/g++-14 100 \
    && rm -rf /var/lib/apt/lists/*
# Result: NOT sufficient on its own. Use option B or C below.
```

```ini
# --- Stage 2 option B (RECOMMENDED, UNVERIFIED in this session) ---
# Add tools.build:compiler_executables to the Conan profile so Conan passes
# the absolute compiler paths explicitly into every sub-shell it spawns.
# Documented Conan 2 mechanism; works regardless of update-alternatives state.

# conan/profiles/default
[settings]
arch=x86_64
build_type=Release
compiler=gcc
compiler.cppstd=gnu17
compiler.libcxx=libstdc++11
compiler.version=14
os=Linux

[conf]
tools.build:compiler_executables={"c": "/usr/bin/gcc-14", "cpp": "/usr/bin/g++-14"}
```

```ini
# --- Stage 2 option C (LOWEST-RISK, UNVERIFIED in this session) ---
# Downgrade the profile to match what Ubuntu 24.04 ships out of the box.
# Skips needing gcc-14 entirely; no apt install, no compiler_executables needed.

# conan/profiles/default
[settings]
compiler=gcc
compiler.version=13      # was 14
compiler.cppstd=gnu17
compiler.libcxx=libstdc++11
```

### Detailed Steps

1. **Stage 1 — fix the build-profile error.** In every Dockerfile (and any CI shell snippet) that invokes `conan install`, `conan create`, or `conan build`, replace `--profile=conan/profiles/default` with `--profile:all=conan/profiles/default`. The `:all` suffix is Conan 2's shorthand for "apply this profile to both host and build contexts in one go" and removes the dependency on `~/.conan2/profiles/default` ever existing. This is the only Stage 1 change required and was confirmed in PR #219 to make the configure stage pass.
2. **Stage 1 sanity check.** Re-run the build. The original error
   `ERROR: The default build profile '/home/builder/.conan2/profiles/default' doesn't exist.`
   should disappear. If it does not, search the repo for any other Conan invocation still using bare `--profile=` (Makefiles, justfiles, scripts, GHA inline shells, sub-Dockerfiles).
3. **Stage 2 — diagnose the compiler error.** If Conan now proceeds and a dependency such as `gtest/1.14.0` fails with `CMAKE_C_COMPILER not set, after EnableLanguage`, inspect `conan/profiles/default` (or whichever profile is being used) and check `compiler.version`. If it says `14` and the Dockerfile base is `ubuntu:24.04`, you have the version-mismatch chain: Ubuntu 24.04 ships gcc-13.3 only.
4. **Stage 2 — choose a fix.**
   - **Option A (NOT recommended on its own).** apt install gcc-14 + update-alternatives. Attempted in this session inside ProjectCharybdis; the `builder` user inside Conan's build sandbox did not see the alternatives at sub-shell invocation time. Do not rely on this alone.
   - **Option B (recommended).** Add the `tools.build:compiler_executables` `[conf]` entry to the Conan profile (snippet above). This is the documented Conan 2 mechanism for forcing specific compiler paths into every sub-process Conan spawns and bypasses the alternatives system entirely. Combine with option A's apt install step so the binaries actually exist. UNVERIFIED in this session — verify against your local build before merging.
   - **Option C (lowest-risk).** Edit the profile to set `compiler.version=13`. No apt install, no compiler_executables, no Dockerfile change. The trade-off is loss of any C++23 / gcc-14 features; if the project does not need them, this is the cleanest fix. UNVERIFIED in this session.
5. **Verify Stage 2.** With option B or C in place, re-run `conan install . --profile:all=conan/profiles/default --build=missing` and confirm gtest (or whichever dep tripped first) reaches `Build succeeded`.

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
|---------|----------------|---------------|----------------|
| Original Conan 1 invocation | `conan install . --profile=conan/profiles/default --build=missing` in a freshly built Dockerfile stage | Conan 2 requires BOTH a host profile and a build profile. Bare `--profile=` only sets the host profile; the build profile defaults to `~/.conan2/profiles/default`, which does not exist because `conan profile detect` was never run in the image. Fails with `ERROR: The default build profile ... doesn't exist.` | On Conan 2, always prefer `--profile:all=` for in-repo profile files unless you have a deliberate split. |
| Stage 2 option A (apt + update-alternatives) | apt installed `gcc-14` / `g++-14` and ran `update-alternatives --install /usr/bin/gcc gcc /usr/bin/gcc-14 100` (and the `g++` equivalent) inside the Dockerfile | Conan ran its compiler probe as the `builder` user inside its own build sandbox; the alternatives appear not to propagate into the sub-shell that CMake's `EnableLanguage` triggers, so `CMAKE_C_COMPILER` stayed empty and gtest failed with `CMAKE_C_COMPILER not set, after EnableLanguage`. | `update-alternatives` is not enough for Conan 2 sub-shells — pass the compiler paths explicitly via `tools.build:compiler_executables`, or downgrade `compiler.version` to match the distro default. |

## Results & Parameters

```yaml
# --- Stage 1 fix (verified on PR #219, shipped to main) ---
before: "conan install . --profile=conan/profiles/default --build=missing"
after:  "conan install . --profile:all=conan/profiles/default --build=missing"
reason: "Conan 2 needs host AND build profiles; --profile:all= sets both."
verification: "verified-ci"

# --- Stage 2 option A (attempted, failed) ---
dockerfile_snippet: |
  RUN apt-get update && apt-get install -y --no-install-recommends \
          gcc-14 g++-14 \
      && update-alternatives --install /usr/bin/gcc gcc /usr/bin/gcc-14 100 \
      && update-alternatives --install /usr/bin/g++ g++ /usr/bin/g++-14 100 \
      && rm -rf /var/lib/apt/lists/*
status: "FAILED — Conan build sandbox does not honor alternatives at sub-shell invocation."

# --- Stage 2 option B (recommended, untested in this session) ---
profile_conf_addition: |
  [conf]
  tools.build:compiler_executables={"c": "/usr/bin/gcc-14", "cpp": "/usr/bin/g++-14"}
docs: "https://docs.conan.io/2/reference/config_files/profiles.html"
status: "unverified — try this next; combine with apt install of gcc-14/g++-14."

# --- Stage 2 option C (lowest-risk, untested in this session) ---
profile_settings_change: |
  compiler.version=13     # was 14, matches Ubuntu 24.04 default
status: "unverified — cleanest fix if the project does not need gcc-14 features."

# --- Context ---
project: ProjectCharybdis
pr: 219
sweep_date: "2026-05-10"
base_image: "ubuntu:24.04"
ubuntu_default_gcc: "13.3"
conan_version: "Conan 2.x"
failing_dep_at_stage2: "gtest/1.14.0"
```

## References

- ProjectCharybdis PR #219 — multi-repo CI sweep where this chain was first exercised end-to-end.
- Conan 2 profiles reference: https://docs.conan.io/2/reference/config_files/profiles.html
- Conan 2 `tools.build:compiler_executables` `[conf]` setting (documented mechanism for forcing compiler paths into Conan sub-shells).

## Verified On

| Project | Context | Details |
|---------|---------|---------|
| ProjectCharybdis | PR #219, Docker build stage in CI, 2026-05-10 | Stage 1 fix (`--profile:all=`) verified to make the Conan configure stage pass; PR merged to main with manual override after Stage 2 option A failed. Stage 2 options B and C documented but untested. |
