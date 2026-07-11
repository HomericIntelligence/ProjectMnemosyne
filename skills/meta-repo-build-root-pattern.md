---
name: meta-repo-build-root-pattern
description: "Orchestrate out-of-tree CMake builds in a meta-repo justfile without importing build tool dependencies into the root pixi.toml. Use when: (1) adding a just build recipe to a meta-repo that coordinates multiple C++/CMake submodules, (2) redirecting all build artifacts into a single root build/ directory, (3) the meta-repo should stay lean — each submodule manages its own pixi environment."
category: architecture
date: 2026-03-29
version: "1.2.0"
user-invocable: false
verification: verified-local
history: meta-repo-build-root-pattern.history
tags: [cmake, justfile, meta-repo, build-root, out-of-tree, pixi, submodule, mojo, compose, dashboard, planning, reviewer-risk]
---

# Meta-Repo BUILD_ROOT Pattern for CMake Submodules

## Overview

| Field | Value |
| ------- | ------- |
| **Date** | 2026-03-29 |
| **Objective** | Add `just build` to the Odysseus meta-repo that compiles C++/CMake submodules into `<root>/build/<Name>/` using CMake's native out-of-tree support, without adding cmake/ninja/etc. to root pixi.toml |
| **Outcome** | Successful. PR #67 added just build/test/lint/clean recipes. PR #68 fixed e2e gaps. All 5 targets build; 489/489 Keystone tests pass. |
| **Verification** | verified-local — CI only validates configs/YAML, not actual cmake execution |
| **History** | [changelog](./meta-repo-build-root-pattern.history) |

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

# Mojo repos: pass BUILD_ROOT as env var so artifacts land in root build/
# ProjectOdyssey reads BUILD_ROOT via env_var_or_default — no NATIVE=1 needed
_build-odyssey:
    cd research/ProjectOdyssey && BUILD_ROOT="{{BUILD_ROOT}}/ProjectOdyssey" just build

clean:
    rm -rf "{{BUILD_ROOT}}"
```

### Detailed Steps

1. Declare `BUILD_ROOT := justfile_directory() / "build"` at the top of the root justfile — this is the only build-related variable in the root repo.

2. For each C++/CMake submodule, add a private recipe using `cmake -S <submodule_path> -B {{BUILD_ROOT}}/<Name>`. The `-B` flag overrides whatever `binaryDir` is set in the submodule's `CMakePresets.json` — the command-line flag always wins.

3. For Mojo repos: delegate with `BUILD_ROOT="{{BUILD_ROOT}}/<Name>" just build` from within the submodule directory. The submodule must declare `BUILD_ROOT := env_var_or_default("BUILD_ROOT", repo_root / "build")` and use it throughout. When `BUILD_ROOT` is outside the repo and Podman is used, the `_run` helper mounts it into the container at `/ext-build` and rewrites paths in the command — so the same recipe works whether the container is running or not, and whether called from the project directory or the meta-repo.

4. Do NOT add cmake, ninja, cxx-compiler, or any build tool to the root `pixi.toml`. Each submodule runs `pixi install` in its own directory to get its own tools.

5. Add `just test` using `ctest --test-dir {{BUILD_ROOT}}/<Name>` — ctest supports external build dirs natively.

6. Add `just clean` as `rm -rf "{{BUILD_ROOT}}"` — clean only the root build dir; submodule builds in their own dirs are not affected.

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
| --------- | ---------------- | --------------- | ---------------- |
| Add cmake/ninja to root pixi.toml | Added `cmake`, `ninja`, `cxx-compiler` as root-level pixi dependencies | Violates meta-repo principle: Odysseus should not own build tool deps — each submodule manages its own pixi env | Root `pixi.toml` is for meta-repo tooling only (just, gh, etc.). Submodule build tools stay in each submodule's `pixi.toml`. |
| Override CMake binaryDir in CMakePresets.json | Set `binaryDir` in submodule's CMakePresets.json to `${sourceDir}/../../build/${sourceDirName}` | CMake presets `binaryDir` is relative to sourceDir; path traversal with `../..` is unreliable and not portable | Use `cmake -S <srcdir> -B <external_builddir>` at the call site. The `-B` CLI flag always overrides presets. |
| Pass BUILD_ROOT through just -d delegation | Called `just -d <submodule_path> build BUILD_ROOT=<root>/build/<Name>` hoping sub-repo justfile would use it | Sub-repo justfiles don't declare a BUILD_ROOT variable; the override is silently ignored | Call cmake directly from the meta-repo justfile rather than delegating through the submodule's own build recipe. |
| Re-adding recipes verbatim from the issue snippet (#154 planning, unverified) | The issue #154 body listed `atlas-review-dispatch`/`atlas-review-aggregate` in the justfile snippet to show the full target set | Those recipes ALREADY existed at justfile:704-709 — adding them again is a hard `just` duplicate-recipe parse error | An issue's code snippet is a desired END STATE, not a literal diff. grep each recipe/env key for prior existence before adding; treat the snippet as illustrative. |
| Assuming `dashboard/` build context exists (#154 planning, unverified) | Plan references `build: ./dashboard`, volume `../../shared/Mnemosyne/skills`, and `scripts/atlas-review-*.sh` | The `dashboard/` dir does NOT exist yet — it is created by the dependency issue #153 (still OPEN) | `docker compose config` validates structure but cannot build until the dependency merges; scope verification to structure-only and state the dependency explicitly. |
| Re-declaring `NATS_URL`/`AGAMEMNON_URL` in `.env.example` (#154 planning, unverified) | Added the issue's 15-entry Atlas block which re-lists keys already present (lines 21,25) with different (cross-host Tailscale) values | Not a build failure, but a SILENT-OVERRIDE risk: dotenv last-assignment-wins means the later Atlas block (service-name defaults) overrides the earlier cross-host values for any consumer that loads the whole file | When an env block duplicates existing keys with different values, call out the override explicitly; don't assume "harmless". |

## Reviewer-risk / planning learnings (unverified)

> **Proposed planning catalogue — verification level: `unverified`.** Captured while writing an implementation plan for Odysseus issue #154 (Atlas dashboard Compose registration + justfile targets). The plan was NOT executed: no code run, no `just`/`docker compose` parse, no CI. The verified-local workflow above is unaffected; the items below are uncertain assumptions a reviewer must confirm before this plan is trusted.

When wiring a new Compose service + justfile targets into the Odysseus meta-repo from an issue snippet, catalogue these most-uncertain assumptions:

1. **`.env.example` key collision.** A new env block re-declaring `NATS_URL`/`AGAMEMNON_URL` with compose-service-name values overrides the existing cross-host Tailscale values via dotenv last-wins. Confirm no consumer (e.g. `e2e/start-crosshost.sh`) sources the whole file and breaks.
2. **Sibling-issue dependency contract.** Build context `./dashboard`, volume source `../../shared/Mnemosyne/skills`, the `tests/e2e` Go layout, `templ`/`golangci-lint` tooling, and `scripts/atlas-review-*.sh` are ALL assumed delivered by the OPEN dependency #153 — none verified to exist. If #153's actual layout differs, the compose block, `dashboard-test`, `dashboard-gen`, and the existing `atlas-review-*` recipes break.
3. **Line-number drift.** Cited line numbers (justfile:289-290 argus-start, :704-709 atlas-review, docker-compose.yml:179, argus justfile:80, .env.example:48) were read once and may drift — re-grep before editing.
4. **Distroless + wget healthcheck.** A healthcheck array form like `["CMD","wget","-qO-",...]` is structurally safe (single binary, matches existing services), but a **distroless** runtime image (per the #153 "distroless runtime" title) may LACK `wget`, making the healthcheck always fail. Confirm `wget`/busybox exists in the runtime image — a REAL unverified risk.
5. **`depends_on: { condition: service_healthy }`.** Requires the dependency services to define healthchecks (verified for prometheus/argus-exporter) AND the compose runtime to support condition syntax — podman-compose support is version-dependent.
6. **Env-count mismatch in acceptance criterion.** The criterion counts "15 entries" but the compose service references ~19 env vars (LISTEN_ADDR, NESTOR_URL, HERMES_URL, EXPORTER_URL, WORKER_HOST_IP, CONTROL_HOST_IP not all in the .env block) — confirm "15" matches the documented set, not the full compose env surface.

### Meta planning lessons (project-agnostic)

- An issue body's fenced code block is a target END STATE, not an apply-this-diff. Grep for prior existence of every recipe name and env key before adding; verbatim addition risks duplicate-definition errors (a hard `just` parse failure for recipes).
- A "distroless runtime" dependency makes shell/wget-based healthchecks suspect — flag the busybox/wget availability assumption whenever the image is distroless.
- When a plan depends on an unmerged sibling issue, every path/layout/tooling claim sourced from that sibling is an assumption to label UNVERIFIED, not a fact.

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
    - shared/Mnemosyne

root_pixi_toml_deps: [just]  # only just — no cmake, ninja, compilers
```

## Verified On

| Project | Context | Details |
| --------- | --------- | --------- |
| HomericIntelligence/Odysseus | PR #67, 2026-03-29 session | just build/test/lint/clean recipes added; all C++/CMake repos build into root build/ directory |
