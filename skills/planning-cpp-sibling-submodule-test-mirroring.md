---
name: planning-cpp-sibling-submodule-test-mirroring
description: "The uncertain assumptions and reviewer risks baked into a PLAN that adds C++ GTest unit tests to one HomericIntelligence submodule by mirroring a sibling submodule that already solved the same problem (ProjectAgamemnon mirroring ProjectNestor). Planning done by reading source files only — nothing built or run. Use when: (1) planning to add GTest tests for store/routes/NATS-client code in a C++ submodule because a sibling repo already has them, (2) an issue says 'apply the same test pattern to repo X' and you must check X does not already have it, (3) the test binary cannot link the code under test because store/routes/nats compile only into the _server executable not a library, (4) you are about to copy a sibling repo's HTTP response-shape assertions (error/detail JSON, empty-body status) verbatim, (5) the meta-repo (Odysseus) builds submodules with cmake -S/-B bypassing CMakePresets so you must verify two build contexts."
category: testing
date: 2026-06-20
version: "1.0.0"
user-invocable: false
verification: unverified
tags: [planning, cpp, gtest, cmake, submodule, sibling-mirroring, agamemnon, nestor, core-library-extraction, response-shape-drift, reviewer-risks, unverified, odysseus-meta-repo, natsc, two-build-contexts]
---

# Planning C++ GTest Test Additions by Mirroring a Sibling Submodule — Unverified Assumptions & Reviewer Risks

## Overview

| Field | Value |
|-------|-------|
| **Date** | 2026-06-20 |
| **Objective** | Capture the uncertain assumptions and reviewer risks in a PLAN to add C++ GTest unit tests (store/routes/nats_client) to `control/ProjectAgamemnon` by mirroring `control/ProjectNestor`, which already shipped the identical test suite — for GitHub issue #73 in the Odysseus meta-repo. Planning was done by reading source files only; nothing was built or run. |
| **Outcome** | Plan produced; NOT executed. These are the things a reviewer must verify and an implementer must not take on faith. |
| **Verification** | unverified — read-only planning artifact; nothing was built or run end-to-end |
| **History** | v1.0.0: initial capture of the structural `::core` blocker, sibling response-shape drift, two-build-context requirement, and 6 uncertain assumptions for issue #73. |

> This skill is about the **PLANNING-RISK / mirror-a-sibling** angle, not the mechanics of
> *how* to fix a C++/CMake build. For the build/CI mechanics see
> `cpp-cmake-ci-build-and-test-fixes` (the main()-in-library / GTest-not-found / -Werror-on-nats.c
> fixes), `ci-cd-cpp-asan-gtest-discovery-branch-protection` (ASan discovery aborts),
> `cpp-logger-init-race` (spdlog singleton SIGABRT under coverage/TSan), and
> `natsc-fetchcontent-cpp20-integration` (nats.c FetchContent). This skill is specifically about
> what silently breaks when you assume "the sibling already solved it, so copy its plan."

## When to Use

- Planning to add GTest unit tests to a C++ HomericIntelligence submodule because a sibling submodule already has an equivalent suite, and you intend to mirror it.
- An issue lists multiple repos and says "apply the same pattern to repo X" — you must verify X does not ALREADY have it before scoping work for it.
- The test binary cannot link the code under test because store/routes/nats_client compile only into the `_server` executable, not into a linkable library target.
- You are about to reuse a sibling repo's HTTP handler test assertions (error-JSON shape, empty-body status code) verbatim.
- The work spans the Odysseus meta-repo, which builds submodules via `cmake -S <submodule> -B {{BUILD_ROOT}}/...` bypassing each submodule's `CMakePresets.json` — so the test step must be verified in BOTH the submodule-local and meta-repo build contexts.

## Verified Workflow

<!-- Section title per honest verification level: PROPOSED WORKFLOW (unverified). The
"## Verified Workflow" heading is retained only because scripts/validate_plugins.py requires that
literal token; this content is a PROPOSAL, not a verified procedure. See the warning banner below. -->

### Proposed Workflow (UNVERIFIED — planning artifact only)

> **Warning:** This workflow has not been validated end-to-end. No code was built or run. It is the
> reviewer/implementer checklist distilled from an *unexecuted* plan produced by reading source
> files only. Treat every item as a hypothesis until CI confirms.

### Quick Reference

```bash
# === Pre-flight for a "mirror the sibling submodule's C++ GTest suite" plan ===
# Example: adding tests to control/ProjectAgamemnon by mirroring control/ProjectNestor (issue #73).

SUB_NEW="control/ProjectAgamemnon"   # submodule getting the new tests
SUB_REF="control/ProjectNestor"      # sibling that already solved it (reference)

# 0. PREMISE CHECK — does the "also apply to repo X" target ALREADY have the suite?
#    Issue #73 said "apply same pattern to Nestor" — but Nestor already has it. Don't scope work twice.
ls "$SUB_REF"/test/src/test_store.cpp "$SUB_REF"/test/src/test_routes.cpp "$SUB_REF"/test/src/test_nats_client.cpp

# 1. STRUCTURAL BLOCKER — can the test binary even LINK the code under test?
#    If the library target holds only version_info.cpp and store/routes/nats compile into _server,
#    tests get undefined references. You MUST extract a STATIC ::core lib (see Nestor's CMake).
grep -n "version_info.cpp" "$SUB_NEW"/cmake/SourcesAndHeaders.cmake
grep -n "_server" "$SUB_NEW"/CMakeLists.txt
sed -n '58,84p' "$SUB_REF"/CMakeLists.txt   # the ::core STATIC lib pattern to mirror

# 2. ENTRY-POINT TU — MANDATORY read before the ::core refactor. Does server_main.cpp call
#    register_routes and is it a clean TU separate from main.cpp's conflicting main()?
sed -n '1,40p' "$SUB_NEW"/src/server_main.cpp   # if this differs, the ::core link breaks

# 3. RESPONSE-SHAPE DRIFT — NEVER copy sibling assertions verbatim. Read each handler.
sed -n '29,45p' "$SUB_NEW"/src/routes.cpp   # Agamemnon: 400 {"error":"invalid JSON: ..."}, empty body -> 201 {}
grep -n "detail\|Invalid JSON" "$SUB_REF"/src/routes.cpp   # Nestor: {"detail":"Invalid JSON"} — DIFFERENT

# 4. TWO BUILD CONTEXTS — submodule-local AND meta-repo (Odysseus bypasses CMakePresets).
sed -n '85,95p' justfile     # meta-repo: cmake -S <submodule> -B {{BUILD_ROOT}}/... (no presets)
sed -n '171p' justfile       # _test-agamemnon currently lacks --no-tests=error -> passes vacuously

# 5. nats.c version scope — repo pins v3.9.1; team KB recommends v3.12.0. Surface as a scope decision.
grep -n "3.9.1\|v3.9" "$SUB_NEW"/CMakeLists.txt
```

### Detailed Steps

1. **Verify the premise before scoping.** Issue #73 said "apply the same pattern to Nestor too,"
   but `control/ProjectNestor/test/src/` ALREADY contains `test_store.cpp`, `test_routes.cpp`,
   and `test_nats_client.cpp`. That AC is already satisfied — only Agamemnon needs work. Before
   planning to "apply pattern to repo X," check whether X already has it.

2. **Identify the structural link blocker first.** Agamemnon's `ProjectAgamemnon` library target
   holds ONLY `version_info.cpp` (`cmake/SourcesAndHeaders.cmake:7-8`); `store.cpp`, `routes.cpp`,
   and `nats_client.cpp` compile only into the `_server` executable (`CMakeLists.txt:59-64`), so a
   test binary cannot link them. The fix is to extract a `ProjectAgamemnon::core` STATIC library —
   exactly as Nestor already does (`control/ProjectNestor/CMakeLists.txt:58-84`) — and link it into
   BOTH the server executable and the test binary. Do NOT add `src/*.cpp` directly to
   `test/CMakeLists.txt` (that double-lists sources and yields undefined references).

3. **Read the entry-point TU before the refactor.** The plan ASSUMES `src/server_main.cpp` calls
   `register_routes` and is a clean translation unit separate from `main.cpp` (which owns the
   conflicting `main()`). This was inferred from the file listing, not confirmed. Read
   `server_main.cpp` first; if it differs, the `::core` link breaks (main() conflict / missing
   `register_routes`).

4. **Read every handler — do NOT copy sibling assertions verbatim.** Agamemnon's `parse_body`
   returns `400 {"error":"invalid JSON: ..."}` (`src/routes.cpp:29-45`), whereas Nestor returns
   `{"detail":"Invalid JSON"}`. Agamemnon treats an EMPTY POST body as a valid empty object
   (`src/routes.cpp:35-37`), so `POST /v1/teams ""` returns **201, not 400**. Sibling repos drift;
   assert against the real handler in each repo.

5. **Plan the NATS test for the disconnected path only.** No NATS server runs in CI; the fixture
   `NatsClient nats_{"nats://localhost:1"}` never connects, so tests exercise the graceful-degradation
   path. Mirror Nestor's disconnected-path expectations.

6. **Verify BOTH build contexts.** The Odysseus meta-repo builds submodules with
   `cmake -S <submodule> -B {{BUILD_ROOT}}/...` (`justfile:87-93`), BYPASSING each submodule's
   `CMakePresets.json`. Verify the test step works under (a) the submodule-local `just build` /
   `just test`, and (b) the meta-repo `just _build-agamemnon` / `just _test-agamemnon`. Also add the
   `--no-tests=error` guard to Odysseus `_test-agamemnon` (`justfile:171`) — Nestor's `_test-nestor`
   has it; Agamemnon's currently passes vacuously without it.

7. **Apply the team-knowledge C-library corrections.** Because nats.c is a C library pulled via
   FetchContent, project `-Werror` must be CXX-scoped with
   `$<$<COMPILE_LANGUAGE:CXX>:...>` generator expressions or the nats.c `.c` files fail to compile.
   Conan installs GTest+GMock together, so `find_package(GTest REQUIRED)` resolves under the Conan
   path (the Ubuntu apt gtest/gmock split does NOT affect Conan). See
   `cpp-cmake-ci-build-and-test-fixes` for the exact fixes.

8. **Hold the high-risk items as explicit reviewer gates** (see Results & Parameters): the
   `::core` refactor itself is unproven; `gtest_discover_tests` may need `DISCOVERY_MODE PRE_TEST`
   under the ASan matrix; the nats.c v3.9.1-vs-v3.12.0 mismatch is an in-scope/out-of-scope
   decision; the 8-thread concurrency store test can SIGABRT on a lazy spdlog singleton under TSan
   (real race — see `cpp-logger-init-race`), not flakiness.

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
|---------|----------------|---------------|----------------|
| Copy malformed-JSON assertion from sibling | Reused Nestor's `{"detail":"Invalid JSON"}` assertion for Agamemnon's malformed-body test | Agamemnon's `parse_body` returns `400 {"error":"invalid JSON: ..."}` (`src/routes.cpp:29-45`) — a different shape | Read each repo's handler; sibling repos that look parallel drift in error contracts. Never copy response-shape assertions verbatim. |
| Assume empty POST body → 400 like sibling | Wrote a test expecting `POST /v1/teams ""` to return 400, mirroring Nestor | Agamemnon parses an empty body as `{}` and returns **201** (`src/routes.cpp:35-37`) | Verify edge-case contracts per repo — empty-body handling is a per-handler decision, not a shared convention. |
| Add src/*.cpp directly to test/CMakeLists.txt | Planned to compile store/routes/nats sources straight into the test target | Undefined references / duplicate-source build; those TUs only build into `_server`, and double-listing them is fragile | Extract a shared `ProjectAgamemnon::core` STATIC library that BOTH the server and tests link — don't list sources twice. |
| Assume server_main.cpp links with ::core unread | Planned the `::core` extraction assuming `server_main.cpp` calls `register_routes` and is TU-separate from `main.cpp` | Inferred from the file listing only; never opened `server_main.cpp` — risks a `main()` conflict or missing `register_routes` | Read the entry-point translation unit BEFORE refactoring its build target. |
| Leave nats.c at repo's v3.9.1 silently | Kept Agamemnon's pinned nats.c `v3.9.1` (`CMakeLists.txt:32-34`) without flagging it | Team KB recommends `v3.12.0`; an unflagged version mismatch is a likely reviewer NOGO | Surface version mismatches as an explicit in-scope/out-of-scope decision, not a silent status-quo choice. |
| Plan whole CMake refactor by static reading | Produced the `::core` refactor (move store/routes/nats out of `_server`, relink server, edit install rule) without building | Nothing was compiled or run; verification is `unverified` — the refactor is the single biggest unproven risk | A read-only plan for a build-system refactor is a hypothesis; mark it `unverified` and make the refactor a mandatory build-and-run gate before merge. |

## Results & Parameters

### Core facts verified by READING source during planning

- **Sibling already satisfied an AC**: `control/ProjectNestor/test/src/{test_store,test_routes,test_nats_client}.cpp` exist → issue #73's "apply to Nestor" item is done; scope only Agamemnon.
- **Structural blocker**: `cmake/SourcesAndHeaders.cmake:7-8` (library = version_info.cpp only); `CMakeLists.txt:59-64` (store/routes/nats → `_server`). Mirror Nestor `CMakeLists.txt:58-84` for the `::core` STATIC lib.
- **Response-shape drift**: Agamemnon `src/routes.cpp:29-45` → `400 {"error":"invalid JSON: ..."}`; `:35-37` empty body → `201 {}`. Nestor → `{"detail":"Invalid JSON"}`.
- **NATS**: disconnected/graceful-degradation path only; fixture `NatsClient nats_{"nats://localhost:1"}` never connects (no NATS server in CI).
- **Two build contexts**: meta-repo `justfile:87-93` uses `cmake -S <submodule> -B {{BUILD_ROOT}}/...` (bypasses CMakePresets); `justfile:171` `_test-agamemnon` lacks `--no-tests=error` that Nestor's `_test-nestor` has → currently vacuous-pass.
- **C-lib corrections**: `-Werror` must be CXX-scoped via `$<$<COMPILE_LANGUAGE:CXX>:...>` (else nats.c .c files fail); Conan ships GTest+GMock together (apt split is irrelevant on the Conan path).

### The `::core` STATIC library pattern (mirror Nestor CMakeLists.txt:58-84)

```cmake
# Extract a static core library that BOTH the server executable and the test binary link.
add_library(ProjectAgamemnon_core STATIC
    src/store.cpp
    src/routes.cpp
    src/nats_client.cpp
    src/version_info.cpp
)
add_library(ProjectAgamemnon::core ALIAS ProjectAgamemnon_core)
# CXX-scope warnings so FetchContent'd nats.c (a C library) is not hit by -Werror:
target_compile_options(ProjectAgamemnon_core PRIVATE
    $<$<COMPILE_LANGUAGE:CXX>:-Wall -Wextra -Werror>)
target_link_libraries(ProjectAgamemnon_core PUBLIC nats)

# Server links ::core (server_main.cpp must call register_routes — READ IT FIRST):
target_link_libraries(ProjectAgamemnon_server PRIVATE ProjectAgamemnon::core)

# Tests link ::core + GTest (Conan provides GTest+GMock):
find_package(GTest REQUIRED)
target_link_libraries(ProjectAgamemnon_tests PRIVATE ProjectAgamemnon::core GTest::gtest_main GTest::gmock)
```

### Odysseus meta-repo `_test-agamemnon` guard (justfile:171)

```just
# Add the guard Nestor already has so the test step cannot pass vacuously:
_test-agamemnon:
    ctest --test-dir {{BUILD_ROOT}}/agamemnon --output-on-failure --no-tests=error
```

### Verification commands (BOTH build contexts)

```bash
# Submodule-local (uses CMakePresets):
just -d control/ProjectAgamemnon build
just -d control/ProjectAgamemnon test

# Meta-repo (Odysseus — bypasses CMakePresets via cmake -S/-B):
just _build-agamemnon
just _test-agamemnon

# Store concurrency / race surfacing (8 threads x N create_agent; see cpp-logger-init-race):
ctest --test-dir <build> --timeout 120 --repeat until-fail:50
```

### Most uncertain assumptions — reviewer gates

1. **`unverified`**: nothing built/run. The `::core` refactor (move store/routes/nats out of `_server` into a STATIC lib, relink server, edit install rule) is the biggest unproven risk.
2. **`server_main.cpp` unread**: assumed it calls `register_routes` and is TU-separate from `main.cpp`'s `main()`. Mandatory pre-step: read it; if it differs, the `::core` link breaks.
3. **Conan→GTest unproven for Agamemnon**: `find_package(GTest REQUIRED)` assumed to resolve (saw "gtest" in justfile deps comment; did NOT read conanfile.py). Corroborated by Nestor's identical CMake, not proven for Agamemnon's conan profile.
4. **`gtest_discover_tests` discovery mode**: default assumed fine; under the ASan/sanitizer CI matrix it can abort at configure time and need `DISCOVERY_MODE PRE_TEST` — flagged as fallback, not applied.
5. **nats.c version**: repo pins `v3.9.1` (`CMakeLists.txt:32-34`); team KB recommends `v3.12.0`. Plan kept v3.9.1 (status quo); reviewer must decide if the upgrade is in scope.
6. **Concurrency store test (8 threads × N create_agent)**: assumes `Store::mutex_` makes it safe, but under TSan a lazy spdlog/logger singleton can SIGABRT — a real race (see `cpp-logger-init-race`), not flakiness.

## Verified On

| Project | Context | Details |
|---------|---------|---------|
| Odysseus (control/ProjectAgamemnon, control/ProjectNestor) | Planning GitHub issue #73 "Add unit tests for ProjectAgamemnon routes, store, and NATS client" by mirroring Nestor; read-only, nothing built or run | unverified — assumptions captured for the reviewer/implementer |
