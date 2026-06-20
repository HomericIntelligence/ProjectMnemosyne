---
name: persistence-backing-store-test-harness-driven-choice
description: "Choosing a persistence/backing-store technology for a C++ service (Agamemnon/Nestor Store API) when the obvious reuse-the-stack answer (JetStream KV) conflicts with the CI test harness, AND de-risking the plan against the repo's actual config and the durability/audit goal before building. Use when: (1) planning to add durable backing behind an existing in-memory Store/repository in ProjectAgamemnon or ProjectNestor, (2) deciding between an in-process embedded store (SQLite) vs a networked store (NATS JetStream KV), (3) a plan introduces a new third-party C/C++ lib and you must pick a dependency mechanism (Conan vs hand-written FetchContent URL), (4) a plan adds raw C-API to a repo with -Werror + clang-tidy + cppcheck — ESPECIALLY if it proposes NOLINT to silence COMPILER warnings (NOLINT does not do that; it suppresses static analysis only), (5) reviewing a persistence plan whose tests must stay deterministic and run with NO live NATS server in ctest, (6) fixing reviewer NOGO findings about silent write failures, partial state recompute on load, or cwd-relative durable file paths."
category: architecture
date: 2026-06-20
version: "1.2.0"
user-invocable: false
verification: unverified
history: persistence-backing-store-test-harness-driven-choice.history
tags: [persistence, backing-store, sqlite, wal, jetstream, in-memory, test-harness, ci, embedded, conan, find-package, imported-target, package-manager, clang-tidy, cppcheck, werror, nolint, set-project-warnings, wno, per-target-warnings, error-checking, durability, xdg-state-home, store-api, cpp, planning]
---

# Persistence Backing-Store Selection: Let the Test Harness Pick the Store, and De-Risk the Plan Against the Repo's Actual Config

## Overview

| Field | Value |
| ------- | ------- |
| **Date** | 2026-06-20 |
| **Objective** | Capture the durable PLANNING methodology for adding file-backed persistence behind the existing in-memory `Store` C++ API in ProjectAgamemnon and ProjectNestor (Odysseus issue #71): R0+R1 store-choice + dependency de-risking, AND the R2 lessons learned from FIXING a reviewer NOGO — separating compiler-warning gates from static-analysis gates, error-checking every storage call, and making load/path logic total over the durability goal. |
| **Outcome** | Plan only, three passes. R0 proposed SQLite (WAL) behind an unchanged `Store` API. R1 switched the SQLite dependency to the repo's Conan path and verified the CI gates against the actual cmake files. R1 got a NOGO. R2 fixes the NOGO: a dedicated `_store` static-lib target with scoped `-Wno-*` (NOLINT cannot silence compiler warnings), check every SQLite rc and `throw`, total counter recompute incl. `active_`, an absolute cwd-independent default DB path, and concrete per-AC checks. No code was compiled or run in any pass. |
| **Verification** | unverified (planning-stage methodology / hypothesis — nothing built or run) |

> **Warning:** This workflow has not been validated end-to-end. Treat as a hypothesis until CI confirms. None of the proposed code below was built or run; the R2 decisions are reasoned from the reviewer's NOGO findings and in-repo precedent, not from an executed `conan install` / `just deps` / `just lint` / `ctest`.

## When to Use

- Planning to give an in-memory C++ `Store` (or repository/cache) durable backing in ProjectAgamemnon or ProjectNestor.
- A teammate or audit says "you already have a working JetStream context — just use JetStream KV." Reach for this skill before agreeing.
- Deciding between an **in-process embedded store** (SQLite) and a **networked store** (NATS JetStream KV, Redis, Postgres).
- A plan introduces a **new third-party C/C++ library** and you must pick how to bring it in — a hand-written `FetchContent`/URL fetch vs the project's existing package manager (Conan/vcpkg).
- A plan adds **raw C-API or unusual constructs** to a repo that may have `-Werror` + clang-tidy + cppcheck — before assuming the new code passes the gates.
- A plan proposes **NOLINT to "mitigate" warnings** in a target built with strict compiler flags — NOLINT suppresses static analysis ONLY, never `-Wxxx`/`-Werror`. Reach for this skill before agreeing the plan is consistent.
- A plan worries about a **build-system constraint** (e.g. "don't add this source to the library target") that you only vaguely remember — verify the real exclusion/guard first.
- A test asserts on an **API's JSON response shape** and you need a confirmed source for that shape.
- Reviewing a persistence plan where the existing unit/ctest suite must stay deterministic and dependency-free.
- **Fixing a reviewer NOGO** on a durability feature: silent write failures, partial state recompute on load, cwd-relative default file paths, or AC checks asserted by inference instead of an observable test.

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
      conanfile.py:  self.requires("sqlite3/3.45.3")                 # PLACEHOLDER - verify-first
      CMake:         find_package(SQLite3 REQUIRED)                  # like the other deps
      link:          SQLite::SQLite3  (or sqlite3::sqlite3?)         # exact name UNVERIFIED

TWO INDEPENDENT GATE FAMILIES (do NOT conflate their suppression) -- R2 CRITICAL
  (a) COMPILER warnings  -Wxxx / -Werror   set by set_project_warnings()
        suppressed ONLY by: -Wno-xxx compile options, OR code change / casts
        NOLINT does NOTHING here.
  (b) STATIC-ANALYSIS lint  clang-tidy / cppcheck
        suppressed by: NOLINT(...) / inline-suppr
  A plan that "mitigates -Werror with NOLINT" is internally contradictory.

WARNING STRICTNESS IS PER-TARGET, not per-repo -- R2
  set_project_warnings() applied to: main ${PROJECT_NAME} lib + _server exe
  _server exe ALSO carries its own -Wno-* block (C-API / external-header noise)
  other libs (Nestor _core) get NEITHER -> verify which target your file builds into
  FIX: raw SQLite C-API -> DEDICATED _store static lib carrying the SAME -Wno-* block
       the server uses; link it into both server and tests; main lib stays strict.

DURABILITY CORRECTNESS (R2 NOGO fixes)
  check EVERY rc: prepare_v2 / bind / step / finalize -> throw with sqlite3_errmsg
       (silent success on a failed write voids the audit-trail guarantee)
  load is TOTAL over the read API: map EVERY get_stats() counter (pending/completed/
       ACTIVE) -> persist a per-item `status`; partial recompute = silent corruption
  default path is ABSOLUTE + cwd-independent: $XDG_STATE_HOME or $HOME/.local/state
       (bare "agamemnon.db" reopens a different/empty file from another cwd)
  every AC -> an observable check, incl. ABSENCE (AC3: no apply-all in restart path)

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

4. **De-risk the plan's single most-uncertain external dependency by using the repo's already-proven dependency mechanism.** R0 proposed adding SQLite via a hand-written FetchContent URL (`https://www.sqlite.org/2024/sqlite-amalgamation-3460000.zip`) guessed from memory — never verified to download or build. **Inspect `conanfile.py` first:** the repo ALREADY pulls every dep via Conan (`self.requires("cpp-httplib/...")`, `self.requires("nlohmann_json/...")`, resolved by `find_package(... REQUIRED)`). Decision: add `self.requires("sqlite3/3.45.3")` (PLACEHOLDER — see step 1a) + `find_package(SQLite3 REQUIRED)` and link the prebuilt imported target. This eliminates the guessed URL entirely AND removes the self-compiled `sqlite3_amalg` static-lib target. **General lesson:** when a plan introduces a new third-party lib, prefer the project's existing package-manager path (Conan/vcpkg/etc.) over a hand-written FetchContent/URL fetch — it removes an unverifiable assumption and inherits the project's pinning/caching.

   1a. **VERIFY-FIRST (front-loaded R2 step 1):** the Conan recipe version (`sqlite3/3.45.3`) and the exact imported-target name the CMakeDeps generator exports (`SQLite::SQLite3` vs `sqlite3::sqlite3`) are SHIPPED AS PLACEHOLDERS — run `just deps` / `conan install` and read the generated config to confirm BOTH before relying on them in `conanfile.py` / `target_link_libraries`.

5. **Distinguish the TWO independent gate families before proposing any suppression — this was the R2 CRITICAL NOGO finding.** There are two unrelated mechanisms and they need unrelated fixes:
   - **(a) Compiler warnings** (`-Wxxx`/`-Werror`) — applied here by `set_project_warnings()` (`-Wold-style-cast -Wcast-align -Wconversion -Wsign-conversion …`). Suppressed ONLY by `-Wno-xxx` compile options OR by changing the code/adding explicit casts. **`NOLINT` does NOTHING for these.**
   - **(b) Static-analysis lint** (clang-tidy / cppcheck `--enable=all`) — suppressed by `NOLINT(...)` / inline-suppr.
   R1's NOGO: it proposed putting raw SQLite C-API (`reinterpret_cast` on `sqlite3_column_text`, C-string handling) into a CMake *library* target carrying the full `-Werror` set and "mitigating" the resulting compiler warnings with NOLINT — internally contradictory; those `-Wxxx` fire as hard errors regardless. **General lesson:** a plan that conflates the two suppression mechanisms is broken; name which family each warning belongs to and apply the matching fix.

6. **Compiler-warning strictness is PER-TARGET — verify which target your new file compiles into.** Here `set_project_warnings()` is applied only to the main `${PROJECT_NAME}` library and the `_server` exe; the `_server` exe ALSO carries its OWN `-Wno-*` block to tame C-API/external-header noise, while other libs (Nestor's `_core`) get neither. **Fix (the NOGO remediation): put the raw-C-API `store.cpp` in a DEDICATED `_store` static-lib target that carries the SAME `-Wno-*` block the server already uses, then link that lib into both the server and the tests — leaving the strict main library untouched.** **General lesson:** when adding code with unavoidable warning noise (third-party C APIs), isolate it in its own target with scoped `-Wno-*` options rather than relaxing the whole project or fighting NOLINT; find the existing precedent target that already suppresses the same warnings and mirror its option list. (clang-tidy/cppcheck noise on the same lines is still handled with `NOLINT` — that's family (b).)

7. **Prefer a package-manager imported target over a self-compiled dependency target — a self-built target is a warnings-as-errors liability.** Switching SQLite from a self-built `sqlite3_amalg` STATIC target to Conan's prebuilt imported target sidesteps `-Werror`/`WARNINGS_AS_ERRORS` entirely for the dependency's own code (you never compile `sqlite3.c` yourself). Only YOUR `store.cpp` (which CALLS the API) remains subject to the gates — which is exactly why step 6 isolates it in its own `-Wno-*` target.

8. **Check EVERY backend return code and propagate failures — silent success on a failed write voids the durability guarantee (R2 NOGO fix).** R1's `upsert_`/`erase_row_`/`load_all_` ignored `sqlite3_prepare_v2`/`bind`/`step`/`finalize` return codes: a failed write (disk full, locked WAL) would still mutate the in-memory cache and return success — exactly the "no audit trail" harm issue #71 is about. Fix: check every rc and `throw` with `sqlite3_errmsg` (a shared `throw_sqlite` helper). **General lesson (ties to checkpoint-recovery's "never silently swallow" rule):** for a durability/audit feature, error-checking the storage calls is correctness, not polish.

9. **Preserve the `Store` public API with a defaulted constructor.** Add `Store(const std::string& db_path = default_db_path())`. All existing call sites (`Store store;`) compile unchanged; tests pass `":memory:"` for a private in-memory DB while still exercising the full persistence code path.

10. **Make the default DB path ABSOLUTE and cwd-independent (R2 NOGO fix).** R1's `default_db_path()` returned a bare `"agamemnon.db"` (cwd-relative); a service restarted from a different working directory would silently open a different/empty file and "lose" its state — re-introducing the very loss-of-state bug the feature is meant to fix. Fix: resolve an ABSOLUTE path under `$XDG_STATE_HOME` (fallback `$HOME/.local/state`) and create the parent directory. **CAVEAT (R2 unverified):** do NOT use `std::system("mkdir -p …")` with a string-interpolated path — that is a shell-injection / portability smell that itself may trip cert-env / shell-escaping static-analysis gates; prefer `std::filesystem::create_directories` (this substitution was NOT made/verified this pass). **General lesson:** durable-state file paths must be absolute and location-stable across restarts/cwd, or the durability is illusory.

11. **Verify a stated build-system constraint's premise against the actual file before designing around it.** R0 worried that adding store sources to the Agamemnon *library* target might clash with `gtest_main`. R1 confirmed `cmake/SourcesAndHeaders.cmake`'s exclusion comment is specifically about `main.cpp`'s `main()` symbol — store sources have no `main()`, so the library link is safe. **Lesson:** read the actual exclusion/guard and its rationale; don't treat a vaguely-remembered constraint as binding.

12. **Persist incrementally, inside the lock.** Load on construction (`load_all_`) to warm the in-memory maps as a hot read cache; call `upsert_row_`/`erase_row_` on every mutator while the existing mutex is already held. Do NOT batch a save at shutdown — save-at-end loses everything on crash (see checkpoint-recovery skill).

13. **When reconstructing derived state on load, account for EVERY field the read API exposes — partial recompute is silent state corruption (R2 NOGO fix).** R1's Nestor `load_all_()` recomputed only `pending`/`completed`, but the `get_stats()` API ALSO exposes `active`; any "active" item would silently reload as `pending`, breaking AC4 (in-flight state preserved). Fix: an explicit N-way mapping covering ALL exposed counters, persist a per-item `status` field, and assert each counter in the restart test. Still recompute derived counters from rows (never trust them stored) — but make the recompute TOTAL over the API surface. **General lesson:** a read API returning a value the load path cannot reconstruct is a POLA violation; enumerate the API surface and make load total over it.

14. **Hold the handle as a member, per object lifetime.** Keep `sqlite3*` as a `Store` member, opened once in the constructor and closed in the destructor — same lifetime rule as the cpp-http-client-wrapper-lifetime skill (resource lives with the object, not per-call).

15. **Make every acceptance-criterion check concrete, not inferred (R2 NOGO fix).** AC3 ("recovery does not require manual apply-all") was only asserted by inference in R1; R2 states explicitly that the restart-test code path contains NO apply-all / manifest re-application call. **General lesson:** each AC should map to an observable check — even when the criterion is the ABSENCE of an action, prove the absence in the test path.

16. **Write restart-survival tests, and cite the API JSON shape from a verified source.** Open a temp-file DB, create entities, destroy the `Store`, reopen the same path, assert state persisted — and assert EACH `get_stats()` counter (pending/completed/active) round-trips (step 13). The test reads `create_team(...)["team"]["id"]` and `create_task(...)["task"]["id"]` — the `.team.id` / `.task.id` wrap shape — cross-checked against the team skill `homeric-crosshost-deployment-and-mesh-topology` (documents `jq -r '.team.id'  # NOT .id`). Clean up `.db`, `-wal`, and `-shm` files between tests — leftover sidecars cause flaky cross-test state. **Lesson:** when a test asserts on an API's JSON shape, cite a confirmed source for that shape rather than guessing.

17. **Acknowledge forced duplication across independently-versioned submodules — don't ship it silently.** The `throw_sqlite`/`upsert_`/`load_all_` boilerplate is copied into two separate submodule `store.cpp` files (Agamemnon and Nestor); there is no shared build location, and consolidating would couple two independently-versioned repos. Name this trade-off in the plan rather than leaving the reviewer to flag it. **General lesson:** when DRY is intentionally violated due to a structural boundary (separate repos/submodules), say so and why.

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
| --------- | ---------------- | --------------- | ---------------- |
| JetStream KV as the backing store | Reuse the working JetStream context for durable Store backing | JetStream's `js_FileStorage` persists the EVENT STREAM, not the Store maps, and needs a LIVE NATS server; CI/ctest runs with NO live NATS (`server_main.cpp` degrades gracefully; tests never connect), so a JetStream store makes unit tests non-deterministic or forces live infra into CI | Let the test harness's available infra pick the store; prefer in-process/embedded over networked when existing tests run without the network dep |
| Guessed SQLite amalgamation FetchContent URL (R0 anti-pattern) | Wrote `https://www.sqlite.org/2024/sqlite-amalgamation-3460000.zip` from memory and a self-compiled `sqlite3_amalg` STATIC target | The sqlite.org year-path + version were never verified to download/build (may 404); and the self-compiled target compiles `sqlite3.c` under `-Werror`/`WARNINGS_AS_ERRORS`, a guaranteed liability | De-risk the most-uncertain external dep by switching to the repo's existing package manager: `conanfile.py` already does `self.requires(...)` + `find_package(... REQUIRED)`; add the SQLite require + `find_package(SQLite3 REQUIRED)` + link the prebuilt imported target. Prefer the package-manager path over hand-written FetchContent — it removes an unverifiable assumption and inherits pinning/caching |
| Self-compiled `sqlite3_amalg` STATIC target under -Werror | Build sqlite3.c ourselves and link it | A self-built dependency target is subject to `-Werror`/`WARNINGS_AS_ERRORS`/clang-tidy on the dependency's own code | Use a prebuilt package-manager imported target; you never compile sqlite3.c, so only your `store.cpp` (which CALLS the API) stays subject to the gates |
| **(R2 CRITICAL) NOLINT to suppress COMPILER `-W`/`-Werror` warnings** | R1 proposed adding raw SQLite C-API (`reinterpret_cast` on `sqlite3_column_text`, C-string handling) into a CMake *library* target built with `set_project_warnings()` (`-Wold-style-cast -Wcast-align -Wconversion -Wsign-conversion …`) and "mitigating" the resulting compiler warnings with `NOLINT` comments | NOLINT suppresses static analysis (clang-tidy/cppcheck) ONLY — it does NOTHING for compiler `-Wxxx`/`-Werror`, which fire as hard errors regardless; the plan was internally contradictory and got a NOGO | Distinguish the two gate families: (a) compiler warnings — suppress ONLY via `-Wno-xxx` compile options or code/casts; (b) static-analysis lint — suppress via `NOLINT`/inline-suppr. Never claim NOLINT "mitigates" a `-Werror` warning |
| **(R2) Assuming repo-wide warning strictness instead of per-target** | Assumed any new file inherits (or escapes) the strict flags uniformly across the repo | `set_project_warnings()` is applied PER-TARGET (main `${PROJECT_NAME}` lib + `_server` exe only); the `_server` exe ALSO carries its own `-Wno-*` block, while other libs (Nestor `_core`) get neither — so "where does my file compile" decides which flags apply | Verify which target your new file builds into; isolate raw-C-API source in a DEDICATED `_store` static-lib carrying the SAME `-Wno-*` block the server uses (linked into server + tests), leaving the strict main lib untouched — find the precedent target that already suppresses the same warnings and mirror its option list |
| **(R2) Ignoring SQLite return codes** | R1's `upsert_`/`erase_row_`/`load_all_` ignored `sqlite3_prepare_v2`/`bind`/`step`/`finalize` rc | A failed write (disk full, locked WAL) would still mutate the in-memory cache and return success — silently voiding the durability/audit guarantee that issue #71 exists to provide | Check EVERY rc and `throw` with `sqlite3_errmsg` (shared `throw_sqlite` helper); for a durability feature, error-checking the storage calls is correctness, not polish (ties to checkpoint-recovery's never-silently-swallow rule) |
| **(R2) Partial counter recompute dropping `active_`** | R1's Nestor `load_all_()` recomputed only `pending`/`completed`, but `get_stats()` ALSO exposes `active` | Any "active" item would silently reload as `pending`, breaking AC4 (in-flight state preserved) — silent state corruption | Make load TOTAL over the read API: explicit N-way mapping covering all exposed counters, persist a per-item `status`, and assert each counter in the restart test. A value the load path cannot reconstruct is a POLA violation |
| **(R2) cwd-relative default DB path** | R1's `default_db_path()` returned a bare `"agamemnon.db"` (cwd-dependent) | A service restarted from a different working directory silently opens a different/empty file and "loses" its state — re-introducing the exact loss-of-state bug the persistence feature is meant to fix | Resolve an ABSOLUTE, location-stable path (`$XDG_STATE_HOME` / `$HOME/.local/state`) and create the parent dir; durable-state paths must be cwd-independent or the durability is illusory |
| **(R2 STILL-UNVERIFIED) `std::system("mkdir -p …")` injection/portability smell** | R2 proposed creating the parent dir for the absolute DB path via `std::system("mkdir -p " + path)` (string-interpolated) | A string-interpolated shell call is a shell-injection / portability smell that may itself trip the very static-analysis gates the plan must satisfy (cert-env, shell-escaping); a cleaner `std::filesystem::create_directories` was NOT substituted/verified this pass | Use `std::filesystem::create_directories` instead of shelling out; verify it clears the `ci` static-analysis preset before relying on it |
| **(R2 STILL-UNVERIFIED) Conan version `sqlite3/3.45.3` + imported-target name** | Shipped `self.requires("sqlite3/3.45.3")` and `SQLite::SQLite3` (vs `sqlite3::sqlite3` from the CMakeDeps generator) as PLACEHOLDERS | Neither the recipe version's resolution in THIS profile nor the exact imported-target name the generator exports was confirmed by running `just deps` / `conan install` | Front-loaded as verify-first step 1a: run `just deps` and read the generated config to confirm BOTH the pinned version and the exact `target_link_libraries` name before committing |
| **(R2 STILL-UNVERIFIED) Dedicated `_store` lib with `-Wno-*` clears the gates** | Reasoned that a `_store` static lib carrying the server's `-Wno-*` block clears the full `-Werror` + clang-tidy + cppcheck `ci` preset on the raw SQLite C-API | This is reasoned from the `_server` target's existing precedent, NOT built/run; the same `-Wno-*` set may not cover every warning the SQLite calls emit, and the clang-tidy/cppcheck NOLINT categories were not confirmed | Build + run `just lint` + `ctest --preset ci`; read the actual emitted compiler warnings AND lint check names; widen the `-Wno-*` / NOLINT sets to the real output |
| **(R2) Nothing compiled or run (overall caveat)** | Reasoned restart-survival behavior, `:memory:` per-instance isolation, and WAL sidecar behavior from knowledge | No code was compiled or executed this pass; overall verification remains `unverified` | Treat the entire workflow as a hypothesis; build + run (`just deps`, `just lint`, `ctest --preset ci`, the restart-survival test asserting each counter) before claiming any of it green |
| Save-at-end (batch persist on shutdown) | Considered persisting the in-memory maps once at process exit instead of per-mutation | Documented crash-loss failure mode (checkpoint-recovery skill): a crash before shutdown loses all writes | Persist incrementally on every mutation inside the already-held lock; keep maps as a hot read cache only |
| Trusting persisted atomic/derived counters | Considered reading back Nestor's pending/completed counters from storage on load | Persisted derived state drifts from source rows and is a silent-corruption risk | Recompute derived counters from the source rows during `load_all_`; never trust them as stored |
| Designing for shared multi-writer locking | Audit asserted "multi-writer needs JetStream/locking" and nearly drove the design | Premise was false: each service constructs its OWN `Store` (separate DB file); no file is shared, so single-process atomic durability suffices | Verify a stated concern's premise against the actual code before letting it drive the design |

## Results & Parameters

### Verification Status

| Item | Status |
| ------ | -------- |
| Plan authored (Odysseus issue #71), R0 + R1 + R2 (post-NOGO) | yes |
| Any code compiled | NO |
| Any test run | NO |
| `conanfile.py` / cmake gate files inspected (R1) | YES — config read, not built |
| Conan recipe version `sqlite3/3.45.3` resolves in profile | NO (PLACEHOLDER; `just deps` not run — verify-first step 1a) |
| Imported-target name (`SQLite::SQLite3` vs `sqlite3::sqlite3`) | NO (PLACEHOLDER; not built) |
| Dedicated `_store` lib `-Wno-*` clears `-Werror`+clang-tidy+cppcheck `ci` preset | NO (reasoned from `_server` precedent; not built) |
| `std::filesystem::create_directories` vs `std::system("mkdir -p")` | NO (smell flagged; cleaner approach NOT substituted/verified) |
| Exact NOLINT categories / compiler `-Wno-*` set for the SQLite calls | NO (`just lint` not run; precedent only) |
| store sources library/`_store`-target link confirmed | NO (premise verified safe by reading SourcesAndHeaders.cmake; not built) |
| Overall verification level | **unverified** (theoretical/proposed) |

### Proposed Persistence Parameters

| Parameter | Proposed Value | Notes |
| ----------- | ---------------- | ------- |
| Backing store | SQLite, WAL journal mode | `PRAGMA journal_mode=WAL` in `init_schema_` |
| Dependency mechanism | **Conan** (R1 — replaces R0 FetchContent) | `self.requires("sqlite3/3.45.3")` PLACEHOLDER in `conanfile.py`; `find_package(SQLite3 REQUIRED)`; link the prebuilt imported target (`SQLite::SQLite3` vs `sqlite3::sqlite3` — verify via `just deps`); never self-compile sqlite3.c |
| Warning isolation (R2) | dedicated `_store` static-lib target carrying the SAME `-Wno-*` block as `_server` | keeps the strict main `${PROJECT_NAME}` lib untouched; linked into server + tests |
| Compiler-warning suppression (R2) | `-Wno-*` compile options on the `_store` target | NOLINT does NOT suppress `-Wxxx`/`-Werror`; these need `-Wno-*` or casts |
| Lint suppression (family b) | targeted `NOLINT(...)` on `store.cpp` C-API call sites | clang-tidy/cppcheck only; verify exact check names via `just lint` |
| Error checking (R2) | check rc on EVERY prepare/bind/step/finalize; `throw_sqlite` with `sqlite3_errmsg` | silent success on a failed write voids durability |
| Schema shape | one table per entity: `id TEXT PRIMARY KEY, status TEXT, doc TEXT` | `doc` holds `json.dump()`; `status` added (R2) so `active`/`pending`/`completed` all round-trip |
| Constructor | `Store(const std::string& db_path = default_db_path())` | default arg keeps `Store store;` compiling; `":memory:"` for tests |
| Default path (R2) | ABSOLUTE under `$XDG_STATE_HOME` / `$HOME/.local/state`; create parent dir | NOT cwd-relative `"agamemnon.db"`; prefer `std::filesystem::create_directories` over `std::system("mkdir -p")` |
| Persistence model | load-on-construction + save-on-mutation, inside existing lock | NOT save-at-end |
| Handle lifetime | `sqlite3*` member, open in ctor / close in dtor | per cpp-http-client-wrapper-lifetime skill |
| Derived counters | recomputed from rows on load, TOTAL over the read API (R2) | Nestor pending/completed/**active**; never trusted as stored; assert each in restart test |
| Cross-submodule duplication (R2) | `throw_sqlite`/`upsert_`/`load_all_` boilerplate copied into both `store.cpp` | acknowledged trade-off — consolidating would couple two independently-versioned submodules |
| CI verification | `just deps` + `just lint` + `ctest --preset ci` + restart-survival test | none run this pass |

### Key Heuristics (the durable takeaways)

1. **Test-harness-driven store choice:** prefer in-process/embedded persistence over a networked store when the service's existing test suite already runs without that network dependency. The available test infra picks the store, not the richest stack component. (JetStream persists the event stream, not the Store maps, and needs a live server CI lacks.)
2. **De-risk the most-uncertain external dependency via the repo's existing package manager.** Replace a guessed hand-written FetchContent/URL fetch with the project's Conan/vcpkg path — it removes an unverifiable assumption and inherits pinning/caching, and a prebuilt imported target dodges `-Werror` on the dep's own code.
3. **Verify CI-gate strictness before assuming new code passes — and keep the two gate families distinct (R2 CRITICAL).** Compiler warnings (`-Wxxx`/`-Werror` via `set_project_warnings()`) are suppressed ONLY by `-Wno-xxx` options or code/casts; static-analysis lint (clang-tidy/cppcheck) is suppressed by `NOLINT`. NOLINT does NOTHING for `-Werror`. A plan that "mitigates `-Werror` with NOLINT" is internally contradictory.
4. **Warning strictness is PER-TARGET (R2).** Verify which target your new file compiles into; isolate unavoidable C-API warning noise in a dedicated `_store` lib carrying the same `-Wno-*` block an existing precedent target (`_server`) already uses, rather than relaxing the whole project.
5. **For a durability/audit feature, error-checking the storage calls is correctness (R2).** Check every backend rc and propagate (`throw_sqlite`); silent success on a failed write voids the guarantee.
6. **Make load TOTAL over the read API and default paths ABSOLUTE (R2).** Recompute every exposed counter (pending/completed/active), persist a per-item `status`; resolve a cwd-independent absolute DB path — a value the load can't reconstruct, or a cwd-relative path, silently corrupts/loses state.
7. **Map every AC to an observable check, including the ABSENCE of an action (R2)** (AC3: assert no apply-all in the restart path).
8. **Verify a stated build constraint's premise against the real file** (the lib exclusion is about `main()`, so store sources are safe).
9. **Cite a confirmed source for any asserted API/JSON shape** (here: `.team.id` / `.task.id` from `homeric-crosshost-deployment-and-mesh-topology`).
10. **Preserve the public API with a defaulted ctor; save-on-mutation not save-at-end; acknowledge forced cross-submodule duplication; verify a concern's premise (services do NOT share a Store file) before designing for it.**

## Verified On

| Project | Context | Details |
| --------- | --------- | --------- |
| (none) | Odysseus issue #71 planning session (R0 + R1 + R2 post-NOGO) | unverified — methodology captured at plan stage; R1 inspected `conanfile.py`, `cmake/StaticAnalyzers.cmake`, `cmake/CompilerWarnings.cmake`, `cmake/StandardSettings.cmake`, `cmake/SourcesAndHeaders.cmake`; R2 fixes are reasoned from the reviewer's NOGO findings and the `_server` `-Wno-*`/`set_project_warnings()` precedent, but no build/run performed in ProjectAgamemnon or ProjectNestor |

## References

- ProjectMnemosyne skill: `checkpoint-recovery` (incremental save vs save-at-end failure mode)
- ProjectMnemosyne skill: `cpp-http-client-wrapper-lifetime-equals-object-not-per-call` (member-held native handle lifetime)
- ProjectMnemosyne skill: `cpp-cmake-ci-build-and-test-fixes` (FetchContent C lib + -Werror, clang-tidy vendor floods, lib-with-main vs gtest_main)
- Team skill: `homeric-crosshost-deployment-and-mesh-topology` (`.team.id` / `.task.id` JSON shape; JetStream `js_FileStorage` persists the event stream)
- ProjectMnemosyne skill: `state-machine-and-resource-lifecycle-patterns` / `checkpoint-state-machine-resume` (in-flight status reloaded, not forced FAILED)
- [SQLite WAL mode](https://www.sqlite.org/wal.html)
- [Conan sqlite3 recipe](https://conan.io/center/recipes/sqlite3)
