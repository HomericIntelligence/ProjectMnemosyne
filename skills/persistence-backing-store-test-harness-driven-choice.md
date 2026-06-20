---
name: persistence-backing-store-test-harness-driven-choice
description: "Choosing a persistence/backing-store technology for a C++ service (Agamemnon/Nestor Store API) when the obvious reuse-the-stack answer (JetStream KV) conflicts with the CI test harness, AND de-risking the plan's external-dependency assumptions by inspecting the repo's actual config before building. Use when: (1) planning to add durable backing behind an existing in-memory Store/repository in ProjectAgamemnon or ProjectNestor, (2) deciding between an in-process embedded store (SQLite) vs a networked store (NATS JetStream KV), (3) a plan introduces a new third-party C/C++ lib and you must pick a dependency mechanism (Conan vs hand-written FetchContent URL), (4) a plan adds raw C-API to a repo with -Werror + clang-tidy + cppcheck, (5) reviewing a persistence plan whose tests must stay deterministic and run with NO live NATS server in ctest."
category: architecture
date: 2026-06-20
version: "1.1.0"
user-invocable: false
verification: unverified
history: persistence-backing-store-test-harness-driven-choice.history
tags: [persistence, backing-store, sqlite, wal, jetstream, in-memory, test-harness, ci, embedded, conan, find-package, imported-target, package-manager, clang-tidy, cppcheck, werror, nolint, store-api, cpp, planning]
---

# Persistence Backing-Store Selection: Let the Test Harness Pick the Store, and De-Risk the Plan Against the Repo's Actual Config

## Overview

| Field | Value |
| ------- | ------- |
| **Date** | 2026-06-20 |
| **Objective** | Capture the durable PLANNING methodology for adding file-backed persistence behind the existing in-memory `Store` C++ API in ProjectAgamemnon and ProjectNestor (Odysseus issue #71), AND the R1 re-plan methodology for turning a plan's flagged-unverified external-dependency assumptions into decisions grounded in the repo's actual config. |
| **Outcome** | Plan only. R0 proposed SQLite (WAL) behind an unchanged `Store` API. R1 switched the SQLite dependency from a guessed hand-written FetchContent URL to the repo's existing Conan path (`self.requires("sqlite3/3.46.0")` + `find_package(SQLite3 REQUIRED)` + `SQLite::SQLite3`), and verified the CI gates and build constraints against the actual cmake files. No code was compiled or run in either pass. |
| **Verification** | unverified (planning-stage methodology / hypothesis — nothing built or run) |

> **Warning:** This workflow has not been validated end-to-end. Treat as a hypothesis until CI confirms. None of the proposed code below was built or run; the R1 decisions are grounded in inspected config files and in-repo precedent, not in an executed `conan install` / `just lint` / `ctest`.

## When to Use

- Planning to give an in-memory C++ `Store` (or repository/cache) durable backing in ProjectAgamemnon or ProjectNestor.
- A teammate or audit says "you already have a working JetStream context — just use JetStream KV." Reach for this skill before agreeing.
- Deciding between an **in-process embedded store** (SQLite) and a **networked store** (NATS JetStream KV, Redis, Postgres).
- A plan introduces a **new third-party C/C++ library** and you must pick how to bring it in — a hand-written `FetchContent`/URL fetch vs the project's existing package manager (Conan/vcpkg).
- A plan adds **raw C-API or unusual constructs** to a repo that may have `-Werror` + clang-tidy + cppcheck — before assuming the new code passes the gates.
- A plan worries about a **build-system constraint** (e.g. "don't add this source to the library target") that you only vaguely remember — verify the real exclusion/guard first.
- A test asserts on an **API's JSON response shape** and you need a confirmed source for that shape.
- Reviewing a persistence plan where the existing unit/ctest suite must stay deterministic and dependency-free.

## Verified Workflow

> **Status:** unverified. This is a **Proposed Workflow** — a planning heuristic, not an executed recipe. The `## Verified Workflow` heading is retained only because the skill validator requires that exact section name; the content is a hypothesis. Do not treat any step as confirmed until CI builds and runs it.

### Quick Reference

```
DECISION HEURISTIC (backing store)
  Does the service's existing test suite run WITHOUT the networked dependency?
    YES -> in-process / embedded store (SQLite + WAL). Server-less, deterministic.
    NO  -> the networked store is already a test prerequisite; reuse is defensible.
  NOTE: JetStream DOES persist (js_FileStorage) but to the EVENT STREAM, not the
        Store maps, and needs a LIVE server CI does not have -> wrong for unit tests.

DEPENDENCY MECHANISM (de-risk the most-uncertain external dep)
  ANTI-PATTERN (R0): hand-written FetchContent URL guessed from memory
      https://www.sqlite.org/2024/sqlite-amalgamation-3460000.zip   # never verified
      + a self-compiled `sqlite3_amalg` STATIC target                # -Werror liability
  PREFERRED (R1): use the repo's EXISTING package-manager path (verified in conanfile.py)
      conanfile.py:  self.requires("sqlite3/3.46.0")                 # like cpp-httplib, nlohmann_json
      CMake:         find_package(SQLite3 REQUIRED)                  # like the other deps
      link:          target_link_libraries(... SQLite::SQLite3)      # prebuilt imported target

CI-GATE STRICTNESS (verify ON before assuming pass)
  cmake/StaticAnalyzers.cmake  -> clang-tidy ON + cppcheck --enable=all ON (per-source)
  cmake/CompilerWarnings.cmake -> -Werror
  cmake/StandardSettings.cmake -> WARNINGS_AS_ERRORS=ON
  Raw sqlite3 C-API (owning sqlite3_stmt*, reinterpret_cast on column_text) WILL trip them.
  PRECEDENT: nats_client.cpp already carries NOLINT(...) (lines 3, 177, 184) for C-API pressure.
  -> mirror that NOLINT style; add `just lint` + `ctest --preset ci` verification.

API PRESERVATION
  Store(const std::string& db_path = default_db_path());  // default arg => `Store store;` still compiles
  Store(":memory:")                                       // private in-mem DB for isolated tests

JSON RESPONSE SHAPE (cite a confirmed source)
  create_team(...)["team"]["id"]   create_task(...)["task"]["id"]   # .team.id / .task.id wrap
  source: team skill homeric-crosshost-deployment-and-mesh-topology -> jq -r '.team.id'  # NOT .id
```

### Proposed Steps

1. **Inventory how the existing test suite runs.** For Agamemnon/Nestor, ctest links the library but runs with NO live NATS server: `server_main.cpp` prints a warning and continues (graceful degradation), and test targets never open a connection. This single fact is the decision driver.

2. **Reject the "reuse the stack" answer when it breaks step 1.** JetStream KV looks obvious because a JetStream context already works. But note the nuance: JetStream **does** persist (`nats_client.cpp:90 cfg.Storage = js_FileStorage`) — to the EVENT STREAM, not the Store maps — and it needs a LIVE NATS server CI does not have. So a JetStream-backed Store would make unit tests non-deterministic or force live infra into CI. Generalizable rule: **prefer in-process/embedded persistence over a networked store when the service's existing tests run without that network dependency. Let the available test infra, not the richest stack component, pick the backing store.** (Cross-checked against `homeric-crosshost-deployment-and-mesh-topology`.)

3. **Choose the in-process embedded store.** SQLite (WAL mode) keeps unit tests deterministic and dependency-free: no server, no socket, no flakiness.

4. **De-risk the plan's single most-uncertain external dependency by using the repo's already-proven dependency mechanism.** R0 proposed adding SQLite via a hand-written FetchContent URL (`https://www.sqlite.org/2024/sqlite-amalgamation-3460000.zip`) guessed from memory — never verified to download or build. **Inspect `conanfile.py` first:** the repo ALREADY pulls every dep via Conan (`self.requires("cpp-httplib/...")`, `self.requires("nlohmann_json/...")`, resolved by `find_package(... REQUIRED)`). Decision: add `self.requires("sqlite3/3.46.0")` + `find_package(SQLite3 REQUIRED)` and link the prebuilt `SQLite::SQLite3` imported target. This eliminates the guessed URL entirely AND removes the self-compiled `sqlite3_amalg` static-lib target. **General lesson:** when a plan introduces a new third-party lib, prefer the project's existing package-manager path (Conan/vcpkg/etc.) over a hand-written FetchContent/URL fetch — it removes an unverifiable assumption and inherits the project's pinning/caching.

5. **Verify the CI gate's strictness BEFORE assuming new code will pass it.** Read `cmake/StaticAnalyzers.cmake` (clang-tidy ON + cppcheck `--enable=all` ON by default; `CMAKE_CXX_CLANG_TIDY` applied to every project source), `cmake/CompilerWarnings.cmake` (`-Werror`), and `cmake/StandardSettings.cmake` (`WARNINGS_AS_ERRORS=ON`). Conclusion: raw SQLite C-API calls (owning `sqlite3_stmt*`, `reinterpret_cast` on `sqlite3_column_text`) WILL trip clang-tidy/cppcheck under `-Werror`. Mitigation grounded in precedent: `nats_client.cpp` already carries `NOLINT(...)` comments (lines 3, 177, 184) for the same C-API pressure — mirror that exact pattern, and add a `just lint` + `ctest --preset ci` verification step. **General lesson:** a plan that adds raw C-API or unusual constructs to a repo with `-Werror` + clang-tidy + cppcheck must (a) confirm those gates are actually ON, and (b) point to an in-repo precedent for the suppression style, not invent one.

6. **Prefer a package-manager imported target over a self-compiled dependency target — a self-built target is a warnings-as-errors liability.** Switching SQLite from a self-built `sqlite3_amalg` STATIC target to Conan's prebuilt `SQLite::SQLite3` sidesteps `-Werror`/`WARNINGS_AS_ERRORS` entirely for the dependency's own code (you never compile `sqlite3.c` yourself). Only YOUR `store.cpp` (which merely CALLS the API) remains subject to the gates.

7. **Preserve the `Store` public API with a defaulted constructor.** Add `Store(const std::string& db_path = default_db_path())`. All existing call sites (`Store store;`) compile unchanged; tests pass `":memory:"` for a private in-memory DB while still exercising the full persistence code path.

8. **Verify a stated build-system constraint's premise against the actual file before designing around it.** R0 worried that adding `store.cpp` to the Agamemnon *library* target (previously server-only) might clash with `gtest_main`. R1 confirmed `cmake/SourcesAndHeaders.cmake`'s exclusion comment is specifically about `main.cpp`'s `main()` symbol — `store.cpp` has no `main()`, so linking it into the library is safe. **Lesson:** read the actual exclusion/guard and its rationale; don't treat a vaguely-remembered constraint as binding.

9. **Persist incrementally, inside the lock.** Load on construction (`load_all_`) to warm the in-memory maps as a hot read cache; call `upsert_row_`/`erase_row_` on every mutator while the existing mutex is already held. Do NOT batch a save at shutdown — save-at-end loses everything on crash (see checkpoint-recovery skill).

10. **Never trust persisted derived state.** Recompute atomic/derived counters from the source rows during load. (Nestor's pending/completed counters are recomputed from item status in `load_all_`, not read back verbatim.)

11. **Hold the handle as a member, per object lifetime.** Keep `sqlite3*` as a `Store` member, opened once in the constructor and closed in the destructor — same lifetime rule as the cpp-http-client-wrapper-lifetime skill (resource lives with the object, not per-call).

12. **Write restart-survival tests, and cite the API JSON shape from a verified source.** Open a temp-file DB, create entities, destroy the `Store`, reopen the same path, assert state persisted. The test reads `create_team(...)["team"]["id"]` and `create_task(...)["task"]["id"]` — the `.team.id` / `.task.id` wrap shape — cross-checked against the team skill `homeric-crosshost-deployment-and-mesh-topology` (documents `jq -r '.team.id'  # NOT .id`). Clean up `.db`, `-wal`, and `-shm` files between tests — leftover sidecars cause flaky cross-test state. **Lesson:** when a test asserts on an API's JSON shape, cite a confirmed source for that shape rather than guessing.

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
| --------- | ---------------- | --------------- | ---------------- |
| JetStream KV as the backing store | Reuse the working JetStream context for durable Store backing | JetStream's `js_FileStorage` persists the EVENT STREAM, not the Store maps, and needs a LIVE NATS server; CI/ctest runs with NO live NATS (`server_main.cpp` degrades gracefully; tests never connect), so a JetStream store makes unit tests non-deterministic or forces live infra into CI | Let the test harness's available infra pick the store; prefer in-process/embedded over networked when existing tests run without the network dep |
| Guessed SQLite amalgamation FetchContent URL (R0 anti-pattern) | Wrote `https://www.sqlite.org/2024/sqlite-amalgamation-3460000.zip` from memory and a self-compiled `sqlite3_amalg` STATIC target | The sqlite.org year-path + version were never verified to download/build (may 404); and the self-compiled target compiles `sqlite3.c` under `-Werror`/`WARNINGS_AS_ERRORS`, a guaranteed liability | De-risk the most-uncertain external dep by switching to the repo's existing package manager: `conanfile.py` already does `self.requires(...)` + `find_package(... REQUIRED)`; add `self.requires("sqlite3/3.46.0")` + `find_package(SQLite3 REQUIRED)` + link `SQLite::SQLite3`. Prefer the package-manager path over hand-written FetchContent — it removes an unverifiable assumption and inherits pinning/caching |
| Self-compiled `sqlite3_amalg` STATIC target under -Werror | Build sqlite3.c ourselves and link it | A self-built dependency target is subject to `-Werror`/`WARNINGS_AS_ERRORS`/clang-tidy on the dependency's own code | Use a prebuilt package-manager imported target (`SQLite::SQLite3`); you never compile sqlite3.c, so only your `store.cpp` (which CALLS the API) stays subject to the gates |
| Assuming the CI gates without verifying them | Planned raw sqlite3 C-API calls without checking whether the strict gates were actually ON | clang-tidy + cppcheck `--enable=all` + `-Werror` + `WARNINGS_AS_ERRORS=ON` ARE on (per `cmake/StaticAnalyzers.cmake`, `cmake/CompilerWarnings.cmake`, `cmake/StandardSettings.cmake`); owning `sqlite3_stmt*` and `reinterpret_cast` on `sqlite3_column_text` trip them | Confirm the gates are ON, then mirror an in-repo suppression precedent (`nats_client.cpp` NOLINT lines 3/177/184) rather than inventing one; add a `just lint` + `ctest --preset ci` step |
| Designing around a vaguely-remembered build constraint | Feared adding `store.cpp` to the Agamemnon library target would clash with `gtest_main` (the lib excludes `main.cpp`) | The exclusion in `cmake/SourcesAndHeaders.cmake` is specifically about `main.cpp`'s `main()` symbol; `store.cpp` has no `main()`, so linking it into the lib is safe | Read the actual exclusion/guard and its rationale; don't treat a vaguely-remembered constraint as binding |
| Unconfirmed Conan recipe version `sqlite3/3.46.0` (still UNVERIFIED in R1) | Chose `sqlite3/3.46.0` from knowledge of ConanCenter | The recipe exists on ConanCenter, but the specific pinned version's availability in THIS profile was not exercised (`conan install` / `just deps` not run this pass) | Run `conan install` / `just deps` to confirm the pinned version resolves in this profile before committing the `conanfile.py` line |
| Assumed `SQLite::SQLite3` imported-target name (still UNVERIFIED in R1) | Assumed `find_package(SQLite3 REQUIRED)` yields the `SQLite::SQLite3` imported target from the Conan-generated CMake config | CMake's FindSQLite3 module uses that target name and Conan's cmake_find_package generator generally matches, but this was not built/verified | Build once and confirm the exact imported-target name the Conan config exports before relying on it in `target_link_libraries` |
| Assumed the exact NOLINT categories (still UNVERIFIED in R1) | Assumed the NOLINT categories that clang-tidy/cppcheck will emit for these SQLite calls, by analogy to `nats_client.cpp` | The nats_client.cpp precedent is suggestive, not a guarantee the SAME check names fire for these specific SQLite calls; `just lint` was not run | Run `just lint` and read the actual emitted check names before pinning the NOLINT categories |
| Nothing compiled or run (R1 overall caveat) | Reasoned the restart-survival behavior, `:memory:` per-instance isolation, and WAL-mode file behavior from knowledge | No code was compiled or executed this pass; overall verification remains `unverified` | Treat the entire workflow as a hypothesis; build + run (`just deps`, `just lint`, `ctest --preset ci`, the restart-survival test) before claiming any of it green |
| Save-at-end (batch persist on shutdown) | Considered persisting the in-memory maps once at process exit instead of per-mutation | Documented crash-loss failure mode (checkpoint-recovery skill): a crash before shutdown loses all writes | Persist incrementally on every mutation inside the already-held lock; keep maps as a hot read cache only |
| Trusting persisted atomic/derived counters | Considered reading back Nestor's pending/completed counters from storage on load | Persisted derived state drifts from source rows and is a silent-corruption risk | Recompute derived counters from the source rows during `load_all_`; never trust them as stored |
| Designing for shared multi-writer locking | Audit asserted "multi-writer needs JetStream/locking" and nearly drove the design | Premise was false: each service constructs its OWN `Store` (separate DB file); no file is shared, so single-process atomic durability suffices | Verify a stated concern's premise against the actual code before letting it drive the design |

## Results & Parameters

### Verification Status

| Item | Status |
| ------ | -------- |
| Plan authored (Odysseus issue #71), R0 + R1 | yes |
| Any code compiled | NO |
| Any test run | NO |
| `conanfile.py` / cmake gate files inspected (R1) | YES — config read, not built |
| Conan recipe version `sqlite3/3.46.0` resolves in profile | NO (chosen from ConanCenter knowledge) |
| `SQLite::SQLite3` imported-target name from Conan config | NO (assumed, not built) |
| Exact NOLINT categories for the SQLite calls | NO (`just lint` not run; nats_client.cpp precedent only) |
| store.cpp library-target link confirmed | NO (premise verified safe by reading SourcesAndHeaders.cmake; not built) |
| Overall verification level | **unverified** (theoretical/proposed) |

### Proposed Persistence Parameters

| Parameter | Proposed Value | Notes |
| ----------- | ---------------- | ------- |
| Backing store | SQLite, WAL journal mode | `PRAGMA journal_mode=WAL` in `init_schema_` |
| Dependency mechanism | **Conan** (R1 — replaces R0 FetchContent) | `self.requires("sqlite3/3.46.0")` in `conanfile.py`; `find_package(SQLite3 REQUIRED)`; link `SQLite::SQLite3` (prebuilt imported target — never self-compile sqlite3.c) |
| Schema shape | one table per entity: `id TEXT PRIMARY KEY, doc TEXT` | `doc` holds `json.dump()` of the entity |
| Constructor | `Store(const std::string& db_path = default_db_path())` | default arg keeps `Store store;` compiling; `":memory:"` for tests |
| Persistence model | load-on-construction + save-on-mutation, inside existing lock | NOT save-at-end |
| Handle lifetime | `sqlite3*` member, open in ctor / close in dtor | per cpp-http-client-wrapper-lifetime skill |
| Derived counters | recomputed from rows on load | Nestor pending/completed; never trusted as stored |
| Lint suppression | targeted `NOLINT(...)` mirroring `nats_client.cpp` (lines 3/177/184) | only on `store.cpp` C-API call sites; verify exact check names via `just lint` |
| CI verification | `just deps` + `just lint` + `ctest --preset ci` + restart-survival test | none run this pass |

### Key Heuristics (the durable takeaways)

1. **Test-harness-driven store choice:** prefer in-process/embedded persistence over a networked store when the service's existing test suite already runs without that network dependency. The available test infra picks the store, not the richest stack component. (JetStream persists the event stream, not the Store maps, and needs a live server CI lacks.)
2. **De-risk the most-uncertain external dependency via the repo's existing package manager.** Replace a guessed hand-written FetchContent/URL fetch with the project's Conan/vcpkg path — it removes an unverifiable assumption and inherits pinning/caching, and a prebuilt imported target dodges `-Werror` on the dep's own code.
3. **Verify CI-gate strictness before assuming new code passes.** Confirm clang-tidy/cppcheck/`-Werror`/`WARNINGS_AS_ERRORS` are ON in the actual cmake files, and mirror an in-repo suppression precedent rather than inventing one.
4. **Verify a stated build constraint's premise against the real file** (here: the lib exclusion is about `main()`, so `store.cpp` is safe).
5. **Cite a confirmed source for any asserted API/JSON shape** (here: `.team.id` / `.task.id` from `homeric-crosshost-deployment-and-mesh-topology`).
6. **Preserve the public API with a defaulted ctor; save-on-mutation not save-at-end; recompute derived state on load; verify a concern's premise (services do NOT share a Store file) before designing for it.**

## Verified On

| Project | Context | Details |
| --------- | --------- | --------- |
| (none) | Odysseus issue #71 planning session (R0 + R1) | unverified — methodology captured at plan stage; R1 inspected `conanfile.py`, `cmake/StaticAnalyzers.cmake`, `cmake/CompilerWarnings.cmake`, `cmake/StandardSettings.cmake`, `cmake/SourcesAndHeaders.cmake`, but no build/run performed in ProjectAgamemnon or ProjectNestor |

## References

- ProjectMnemosyne skill: `checkpoint-recovery` (incremental save vs save-at-end failure mode)
- ProjectMnemosyne skill: `cpp-http-client-wrapper-lifetime-equals-object-not-per-call` (member-held native handle lifetime)
- ProjectMnemosyne skill: `cpp-cmake-ci-build-and-test-fixes` (FetchContent C lib + -Werror, clang-tidy vendor floods, lib-with-main vs gtest_main)
- Team skill: `homeric-crosshost-deployment-and-mesh-topology` (`.team.id` / `.task.id` JSON shape; JetStream `js_FileStorage` persists the event stream)
- ProjectMnemosyne skill: `state-machine-and-resource-lifecycle-patterns` / `checkpoint-state-machine-resume` (in-flight status reloaded, not forced FAILED)
- [SQLite WAL mode](https://www.sqlite.org/wal.html)
- [Conan sqlite3 recipe](https://conan.io/center/recipes/sqlite3)
