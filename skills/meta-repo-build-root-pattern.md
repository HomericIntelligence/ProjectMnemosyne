---
name: meta-repo-build-root-pattern
description: "Orchestrate out-of-tree CMake builds in a meta-repo justfile without importing build tool dependencies into the root pixi.toml. Use when: (1) adding a just build recipe to a meta-repo that coordinates multiple C++/CMake submodules, (2) redirecting all build artifacts into a single root build/ directory, (3) the meta-repo should stay lean — each submodule manages its own pixi environment."
category: architecture
date: 2026-03-29
version: "1.0.0"
user-invocable: false
verification: verified-local
tags: [cmake, justfile, meta-repo, build-root, out-of-tree, pixi, submodule, mojo]
---

# Meta-Repo BUILD_ROOT Pattern for CMake Submodules

## Overview

| Field | Value |
|-------|-------|
| **Date** | 2026-03-29 |
| **Objective** | Add `just build` to the Odysseus meta-repo that compiles C++/CMake submodules into `<root>/build/<Name>/` using CMake's native out-of-tree support, without adding cmake/ninja/etc. to root pixi.toml |
| **Outcome** | Successful. PR #67 added just build/test/lint/clean recipes. All C++/CMake repos build into root build/ directory. Mojo repo delegates to submodule's own just build. |
| **Verification** | verified-local — CI only validates configs/YAML, not actual cmake execution |

## When to Use

- Meta-repo (e.g., Odysseus) coordinates multiple submodules with different build systems
- Want all build artifacts in one place (`<root>/build/`) for easier cross-repo tooling
- Must NOT add build tool deps (cmake, ninja, compilers) to the root pixi.toml — each submodule owns its own environment
- Some submodules use CMake presets that hardcode `binaryDir` inside their source tree — need to override at call site
- One or more submodules use Mojo (which doesn't support external build directories like CMake)

## Verified Workflow

### Quick Reference

```just
# Root justfile — meta-repo (e.g., Odysseus)
BUILD_ROOT := justfile_directory() / "build"

# Build all C++/CMake submodules out-of-tree into build/<Name>/
build: _build-agamemnon _build-nestor _build-charybdis _build-keystone _build-odyssey
    @echo "=== Build complete. Artifacts in {{BUILD_ROOT}}/ ==="

_build-agamemnon:
    cmake -S control/ProjectAgamemnon -B "{{BUILD_ROOT}}/ProjectAgamemnon" \
        -DCMAKE_BUILD_TYPE=Debug -G Ninja
    cmake --build "{{BUILD_ROOT}}/ProjectAgamemnon"

# Mojo repos cannot redirect build dir — delegate to submodule's own just
_build-odyssey:
    cd research/ProjectOdyssey && just build

clean:
    rm -rf "{{BUILD_ROOT}}"
```

### Detailed Steps

1. Declare `BUILD_ROOT := justfile_directory() / "build"` at the top of the root justfile — this is the only build-related variable in the root repo.

2. For each C++/CMake submodule, add a private recipe using `cmake -S <submodule_path> -B {{BUILD_ROOT}}/<Name>`. The `-B` flag overrides whatever `binaryDir` is set in the submodule's `CMakePresets.json` — the command-line flag always wins.

3. For Mojo repos: delegate with `cd <path> && just build`. Mojo doesn't support `-B` style external build dirs; artifacts stay in the submodule's own `build/`. This is acceptable.

4. Do NOT add cmake, ninja, cxx-compiler, or any build tool to the root `pixi.toml`. Each submodule runs `pixi install` in its own directory to get its own tools.

5. Add `just test` using `ctest --test-dir {{BUILD_ROOT}}/<Name>` — ctest supports external build dirs natively.

6. Add `just clean` as `rm -rf "{{BUILD_ROOT}}"` — clean only the root build dir; submodule builds in their own dirs are not affected.

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
|---------|----------------|---------------|----------------|
| Add cmake/ninja to root pixi.toml | Added `cmake`, `ninja`, `cxx-compiler` as root-level pixi dependencies | Violates meta-repo principle: Odysseus should not own build tool deps — each submodule manages its own pixi env | Root `pixi.toml` is for meta-repo tooling only (just, gh, etc.). Submodule build tools stay in each submodule's `pixi.toml`. |
| Override CMake binaryDir in CMakePresets.json | Set `binaryDir` in submodule's CMakePresets.json to `${sourceDir}/../../build/${sourceDirName}` | CMake presets `binaryDir` is relative to sourceDir; path traversal with `../..` is unreliable and not portable | Use `cmake -S <srcdir> -B <external_builddir>` at the call site. The `-B` CLI flag always overrides presets. |
| Pass BUILD_ROOT through just -d delegation | Called `just -d <submodule_path> build BUILD_ROOT=<root>/build/<Name>` hoping sub-repo justfile would use it | Sub-repo justfiles don't declare a BUILD_ROOT variable; the override is silently ignored | Call cmake directly from the meta-repo justfile rather than delegating through the submodule's own build recipe. |

## Results & Parameters

```yaml
repo: HomericIntelligence/Odysseus
pr: "#67"
pattern: BUILD_ROOT meta-repo orchestration

build_coverage:
  cmake_repos:
    - control/ProjectAgamemnon    # C++20, Ninja, debug preset
    - control/ProjectNestor       # C++20, Ninja, debug preset
    - testing/ProjectCharybdis    # C++20, Ninja, debug preset
    - provisioning/ProjectKeystone # C++, CMake (has Makefile too)
  mojo_repos:
    - research/ProjectOdyssey     # delegates to submodule's own just build
  excluded_repos:
    # Python repos — no compile step
    - infrastructure/ProjectHermes
    - provisioning/ProjectTelemachy
    - research/ProjectScylla
    - shared/ProjectHephaestus
    # Docker/YAML — no compile step
    - infrastructure/AchaeanFleet
    - infrastructure/ProjectArgus
    - provisioning/Myrmidons
    - ci-cd/ProjectProteus
    # Markdown only
    - shared/ProjectMnemosyne

root_pixi_toml_deps: [just]  # only just — no cmake, ninja, compilers
```

## Verified On

| Project | Context | Details |
|---------|---------|---------|
| HomericIntelligence/Odysseus | PR #67, 2026-03-29 session | just build/test/lint/clean recipes added; all C++/CMake repos build into root build/ directory |
