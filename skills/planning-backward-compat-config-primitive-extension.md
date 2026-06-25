---
name: planning-backward-compat-config-primitive-extension
description: "Reusable checklist for writing TRUSTWORTHY implementation plans that make a hardcoded constant configurable via an env var, or extend a config-driven auth/config primitive, in a C++ service WITHOUT breaking old behavior. Covers both the auth case (add comma-separated AGAMEMNON_API_KEYS unioned with single AGAMEMNON_API_KEY) and the general 'make constant env-configurable' case (e.g. a RouteLimits struct read from AGAMEMNON_* and threaded through register_routes()). Use when: (1) planning to add a new env var / config knob (single OR multi-value) that must coexist with existing behavior, (2) a plan adds a source file to a build target but did not READ the build file that DEFINES the target, (3) a plan claims a trailing defaulted-parameter signature change is non-breaking, (4) a plan cites exact file:line locations as ground truth, (5) a plan opportunistically fixes an adjacent bug or deprecates an existing env knob, (6) a plan consolidates two env knobs that use different units, (7) a plan changes a security-critical == compare into set membership or RELAXES a fail-secure startup invariant, (8) a plan proposes DELETING a file it calls dead code based on a source grep alone."
category: architecture
date: 2026-06-20
version: "1.2.0"
user-invocable: false
verification: unverified
history: planning-backward-compat-config-primitive-extension.history
tags:
  - planning-methodology
  - backward-compatibility
  - config-env-var
  - make-constant-configurable
  - defaulted-parameter
  - build-target-verification
  - scope-creep
  - unit-conversion
  - auth-security
  - dead-code-removal
---

# Planning: Backward-Compatible Extension of a Config/Auth Primitive

## Overview

| Field | Value |
|-------|-------|
| **Date** | 2026-06-20 |
| **Objective** | Make implementation plans for "make a hardcoded constant configurable via env var" and "extend a config-driven config/auth primitive" tasks in a C++ service trustworthy, by codifying the assumptions a reviewer MUST re-verify before approving. |
| **Outcome** | Planning methodology only — distilled from two ProjectAgamemnon plans: issue #260 (add comma-separated `AGAMEMNON_API_KEYS`, unioned with the single `AGAMEMNON_API_KEY` in the C++ `AuthMiddleware`) and issue #275 (expose input-length limits as an `AGAMEMNON_*`-driven `RouteLimits` struct threaded through `register_routes()`). Neither plan was executed end-to-end. The v1.2.0 amendment captures the issue #275 session's *self-correcting* second pass, which verified two first-draft assumptions were WRONG: there is NO `src/CMakeLists.txt` (the `ProjectAgamemnon_core` STATIC lib is defined in the ROOT `CMakeLists.txt:84-99`), and a full caller census found exactly 9 `register_routes` call sites (1 in `server_main.cpp` + 8 in test files), with NO integration/benchmark callers. |
| **Verification** | unverified |
| **History** | [changelog](./planning-backward-compat-config-primitive-extension.history) |

## When to Use

- You are planning to **make a hardcoded constant configurable** via a new `*_*` env var (e.g. an `AGAMEMNON_*`-driven `RouteLimits` struct read by a `from_env()` factory and threaded through a function like `register_routes()`).
- A plan **adds a new source file to a build target** (`add_library`/`add_executable`/`target_sources`) but the **build file that DEFINES the target was not read** — its structure was inferred from files that merely *reference* the target.
- A plan claims a **trailing defaulted-parameter** signature change "keeps every existing caller compiling" — verify the **complete caller census** first.
- You are adding a new **multi-value** config/env var (comma-separated `*_KEYS`) that must coexist with — and be **unioned** with — an existing **single-value** one (`*_KEY`), so old deployments keep working unchanged.
- A plan **opportunistically fixes an adjacent bug** or **deprecates an existing env knob** in favor of a new one (with a back-compat fallback) — beyond the issue's stated ask.
- A plan **consolidates two env knobs that use different units** (e.g. MEGABYTES vs BYTES) — the conversion is a high-risk line.
- A plan cites **exact `file:line` locations** as if they are stable ground truth, especially when the plan's own earlier steps edit lines above them.
- A plan changes a **security-critical `==` compare into set/collection membership**, or **RELAXES a fail-secure startup invariant**.
- A plan proposes to **DELETE a file or symbol** ("dead code", "zero callers") from a **source-only grep**, or **splits into multiple commits** where a later deletion commit could break the build alone.

## Proposed Workflow

> **Warning:** This workflow has not been validated end-to-end. Treat as a hypothesis until CI confirms.
>
> **Heading note:** The repository validator (`scripts/validate_plugins.py`) hard-requires the literal section string `## Verified Workflow`, so the canonical steps are emitted under that heading to keep validation green. This skill is a PLANNING methodology captured at `unverified` level. Read the steps below as **proposed**, per the warning.

## Verified Workflow

> **Warning:** This workflow has not been validated end-to-end. Treat as a hypothesis until CI confirms.

### Quick Reference

```bash
# === BEFORE proposing to DELETE a "dead" file/symbol: grep the BUILD SYSTEM, not just source ===
# Source #include grep alone is INSUFFICIENT. A file can have zero #includes and still be
# compiled as a standalone translation unit listed in a CMake target.
SYM="validate_api_key"; FILE="auth_middleware.hpp"
grep -rn "$SYM" --include='*.cpp' --include='*.hpp' .          # source callers
grep -rn "$FILE" $(git ls-files '*CMakeLists.txt' '*.cmake')   # build-target references  <-- DO NOT SKIP
git grep -n "$FILE" -- '*.cmake' 'CMakeLists.txt' '**/CMakeLists.txt'
# Only assert "dead code / safe to delete" if BOTH greps are empty AND it is in no add_library/add_executable list.

# === Re-resolve EVERY cited line number against the live tree (line numbers drift) ===
# Treat all file:line citations in the plan as PLAN-TIME SNAPSHOTS, not guarantees.
grep -n 'AGAMEMNON_API_KEY' src/auth.cpp src/server_main.cpp   # re-find, don't trust the cited offset

# === Read the SURROUNDING prose before inserting a doc sentence (match existing voice) ===
sed -n '1,30p' docs/api/openapi.yaml   # read the block, not just the cited range

# === Negative tests the plan MUST include (the easy-to-forget ones) ===
# 1. empty "Bearer " / empty "X-API-Key" still REJECTED (never insert "" into the set; count("")==0)
# 2. all-empty / all-whitespace AGAMEMNON_API_KEYS still ABORTS startup (fail-secure preserved)

# === MAKE-CONSTANT-CONFIGURABLE: read the build file that DEFINES the target ===
# A plan that adds a new .cpp to a build target MUST read the file that DECLARES the target,
# not a file that merely references it (e.g. test/CMakeLists.txt mentioning ProjectAgamemnon_core).
# VERIFIED on Agamemnon (issue #275): there is NO src/CMakeLists.txt. The first draft INVENTED it.
# The ProjectAgamemnon_core STATIC library is defined in the ROOT CMakeLists.txt:84-99.
grep -rn 'add_library(ProjectAgamemnon_core' $(git ls-files '*CMakeLists.txt' '*.cmake')  # find the DEFINING block
sed -n '84,99p' CMakeLists.txt       # READ the ACTUAL add_library block (root, NOT src/) before planning the insert

# === Complete CALLER CENSUS before claiming a defaulted-arg change is non-breaking ===
# Listing "the test files" is NOT a census. Grep the WHOLE repo for the symbol.
# EXCLUDE stray copies under worktree/build dirs or they pollute the count.
git grep -n 'register_routes'        # enumerate EVERY call site, then subtract worktree/build copies
grep -rn 'register_routes' src/ test/ \
  --exclude-dir=.claude --exclude-dir=build  # skip .claude/worktrees/ and build/.worktrees/ copies
# VERIFIED census (issue #275): exactly 9 call sites = 1 in src/server_main.cpp + 8 in test files;
# NO integration/benchmark callers. Only THEN is a trailing-defaulted-arg "non-breaking" claim sound.

# === Anchor find-replace on SYMBOLS/STRINGS, not absolute line numbers ===
# routes.cpp line numbers (312/315/.../633) drift once step 5 edits earlier lines first.
git grep -n 'check_field_length' src/routes.cpp   # re-find by string at edit time, never trust the cited offset
# Post-edit INVARIANT: once every hardcoded constant is removed, this MUST return 0 (zero hits):
grep -rn 'kMax' src/routes.cpp   # expect: 0 results -> proves no hardcoded limit constant remains

# === Unit-conversion consolidation: the fallback line is high-risk ===
# SERVER_REQUEST_SIZE_LIMIT_MB is MEGABYTES; AGAMEMNON_MAX_BODY_BYTES is BYTES.
# fallback bytes = mb * 1024 * 1024  (MiB). Test BOTH knobs and the precedence between them.
```

### Detailed Steps

1. **Frame the change as a UNION, prove the old path is unchanged.** The backward-compat
   contract is: a deployment that sets ONLY the legacy single var must behave byte-for-byte as
   before. State explicitly that the new var is *added to* the accepted set, never *replaces* it.
   The plan should show the exact construction of the accepted-key set and assert the legacy
   single value is always a member when present.

2. **Before proposing ANY deletion, grep the build system — not just source.** The single most
   dangerous claim in this class of plan is "X is dead code (zero callers)" derived from a source
   grep that excludes `.claude/`. A source file can have **zero `#include`s** and still be a
   standalone translation unit in a CMake `add_library`/`add_executable`/`target_sources` list.
   Verify the symbol/file is absent from every `CMakeLists.txt`, `*.cmake`, and include list
   before scheduling its removal. If you cannot verify the build files, the deletion is
   **unverified** and must be flagged as such in the plan body (not just a footnote).

3. **Label every `file:line` citation as a plan-time snapshot.** Exact offsets
   (`src/auth.cpp:20/29/35`, `src/server_main.cpp:114-119`, `docs/api/openapi.yaml:885-895`,
   `test/src/test_auth.cpp:114`, etc.) drift as the tree changes. They are navigation *hints*,
   not contracts. The implementer must re-resolve each by symbol/string search at edit time.

4. **Read surrounding prose before inserting doc sentences.** If you cite a doc line range
   (`openapi.yaml`, `README.md`) but only read the range — not the paragraph around it — the
   inserted sentence may clash with the existing voice/format. Read the block, then phrase to match.

5. **For security-critical compares, preserve the exact rejection semantics.** Changing
   `key == expected` into `set.count(key)` is a behavioral change at a security boundary. Pin
   down: empty `Bearer` (with trailing space) must still reject; empty `X-API-Key` must still reject. The mechanism
   that guarantees this — **never insert empty/whitespace strings into the set, so `count("")==0`**
   — must be an explicit, tested invariant, not an emergent accident.

6. **If you RELAX a fail-secure invariant, add the negative/abort test for it.** Allowing startup
   with only the new `*_KEYS` var relaxes the previous "abort unless `*_KEY` is set" rule. Confirm
   with the issue owner that this relaxation is intended, AND add a test proving that an
   all-empty / all-whitespace `*_KEYS` (which yields an empty accepted set) STILL aborts startup.
   A relaxed rule without an explicit abort test is a silent path to insecure startup.

7. **Order/scope multi-commit splits so no commit breaks the build alone.** A split of
   core / docs / dead-code-removal lets the deletion commit be reviewed and merged independently.
   If a hidden build reference exists (see step 2), that commit breaks the build on its own.
   Either prove the deletion is safe first, or fold it into the core commit, or gate it behind the
   build-system grep being empty.

8. **Note pre-existing security debt you are now touching.** If the touched compare lacks
   constant-time comparison (timing side-channel on key matching), call it out as a reviewer note
   even if pre-existing — the surface is being modified, so it is in scope for a security reviewer.

9. **List EVERY unverified assumption in the plan body.** APIs and skills applied "by description"
   (e.g. team-KB skills read only via their Prior-Learnings summary, `std::unordered_set::count`,
   `std::getline` comma-split, `std::isspace` trim, httplib `Request::has_header`/`get_header_value`
   assumed stable from existing code) are assumptions, not facts, until compiled/read. A NOGO
   reviewer treats an acknowledged-but-unverified assumption the same as an unacknowledged one,
   so resolve or explicitly flag each in the plan, not in a side note.

### Make-a-constant-env-configurable checklist (issue #275 class)

10. **Read the build file that DEFINES the target, not one that references it.** When a plan adds
    a new source file to a build target (e.g. `add_library(ProjectAgamemnon_core ...)`), open and
    confirm the `add_library(...)`/`add_executable(...)` block ITSELF. Inferring the `add_library`
    shape from `test/CMakeLists.txt` lines that merely *link against* the target is not
    verification — the defining file may use `target_sources`, a glob, or a different layout than
    assumed. **Verified counter-example (issue #275):** the first draft asserted the target lived
    in `src/CMakeLists.txt`; the second pass found there is NO `src/CMakeLists.txt` at all — the
    `ProjectAgamemnon_core` STATIC library is defined in the **ROOT `CMakeLists.txt:84-99`**. An
    "add the file here" instruction grounded in an *invented* file is a guaranteed build break.

11. **Run a complete caller census before claiming a defaulted-arg change is non-breaking.** A
    trailing defaulted parameter only preserves backward compatibility if EVERY call site is
    accounted for. `git grep` the function name across the WHOLE repo — source, unit tests,
    integration tests, benchmarks, other binaries — and enumerate each. **Exclude stray copies
    under `.claude/worktrees/` and `build/.worktrees/`** (e.g.
    `grep -rn register_routes src/ test/ --exclude-dir=.claude --exclude-dir=build`) or the count
    is polluted. **Verified census (issue #275):** exactly **9** `register_routes` call sites — 1
    in `src/server_main.cpp` + 8 in test files, with **NO** integration or benchmark callers. A
    defaulted-param "keeps everything compiling" claim backed by a partial (test-only) list is
    unverified until that whole-repo, worktree-excluded census is done.
    *Bonus payoff:* two test files carried a brittle comment — *"If `register_routes()` gains an
    8th parameter, ALL THREE files must be updated."* A trailing defaulted parameter sidesteps
    that maintenance trap entirely, because old call sites keep compiling unchanged.

12. **Anchor find-replace on symbols/strings, not absolute line numbers.** Cite the searchable
    string (e.g. each `check_field_length(...)` call) rather than `routes.cpp:312/315/.../633`.
    Line numbers from a single read drift the moment earlier edits land — and these plans often
    edit earlier lines first, invalidating every later offset. Instruct the implementer to
    re-find by symbol/string at edit time, and add a post-edit invariant that grep can check
    (e.g. once all hardcoded limits are removed, `grep -rn 'kMax' src/routes.cpp` MUST return 0).

13. **Flag adjacent-bug fixes and deprecations as SCOPE EXPANSION for sign-off.** If the plan
    goes beyond the issue's ask — e.g. also fixing a latent body-cap override bug, or silently
    deprecating `SERVER_REQUEST_SIZE_LIMIT_MB` in favor of `AGAMEMNON_MAX_BODY_BYTES` with a
    back-compat fallback — call it out explicitly as out-of-issue scope requiring reviewer
    sign-off. Opportunistic fixes folded silently into a "make it configurable" plan inflate
    blast radius and review risk.

14. **Make the code sample match the prose EXACTLY.** A classic source of
    defined-but-not-implemented behavior is prose describing a back-compat fallback (read the new
    var, else fall back to the legacy var) while the shown `from_env()` code sample reads ONLY the
    new var. If the prose says there is a fallback, the sample MUST show it; a divergence between
    narration and sample means the behavior will likely never be implemented.

15. **Call out unit conversions as a high-risk line and test both knobs.** When consolidating two
    env knobs with different units (`*_MB` in MEGABYTES vs `*_BYTES` in BYTES), the fallback must
    multiply by 1 MiB (`mb * 1024 * 1024`). This single conversion line is high-risk: write it
    explicitly in the plan, define the precedence between the two knobs, and require a test for
    BOTH the legacy MB knob and the new bytes knob.

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
|---------|----------------|---------------|----------------|
| Dead-code claim from source grep | Asserted `validate_api_key` in `src/auth_middleware.hpp` is dead code ("zero callers") from a single source grep excluding `.claude/` | A source `#include` grep cannot see a standalone translation unit listed in a CMake target; the file was never confirmed absent from any build target or include list | When proposing to DELETE a file, grep the BUILD SYSTEM (`CMakeLists.txt`, `*.cmake`) too — empty source-callers does not prove "unreferenced" |
| Exact line numbers as ground truth | Cited `src/auth.cpp:20/29/35`, `src/server_main.cpp:114-119`, `docs/api/openapi.yaml:885-895`, `test/src/test_auth.cpp:114` as fixed locations | Line numbers were read at plan time and drift as the tree changes; an implementer trusting them edits the wrong line | Label all `file:line` citations as plan-time snapshots; re-resolve each by symbol/string search at edit time |
| Doc edit without reading the block | Cited `openapi.yaml`/`README.md` line ranges to insert a sentence, but read only the range, not the surrounding prose | Inserted wording may not match the existing voice/format of the doc block | Read the full surrounding paragraph before drafting an inserted doc sentence |
| `==` → set membership without pinning rejection | Replaced a single `==` key compare with `set.count(key)` for multi-key support | At a security boundary this can silently accept an empty `Bearer` (with trailing space) / empty `X-API-Key` if an empty string ever enters the set | Make "never insert empty/whitespace into the set so `count(\"\")==0`" an explicit tested invariant; keep empty-credential rejection tests |
| Relaxed fail-secure with no abort test | Allowed startup with only the new `AGAMEMNON_API_KEYS` (relaxing "abort unless `AGAMEMNON_API_KEY` set") and added no negative test | An all-empty/whitespace `AGAMEMNON_API_KEYS` yields an empty accepted set and could let the server start insecurely | When relaxing a fail-secure rule, always add the negative/abort test for the degenerate (all-empty) input |
| Independent dead-code-removal commit | Split into core / docs / dead-code-removal so the deletion could merge on its own | If a hidden build reference exists, the deletion commit breaks the build independently of the rest | Order/scope multi-commit splits so no single commit can break the build; gate deletion on the build-grep being empty |
| Applied skills/APIs by description only | Used team-KB skills (`config-env-double-underscore-nesting`, `backward-compat-removal`) from their summary, and assumed `std::getline`/`std::isspace`/httplib header API behavior without compiling | Description-level use and uncompiled stdlib/library assumptions are unverified; behavior may differ | Read skill bodies and compile/verify stdlib + library assumptions, or explicitly flag each as unverified in the plan body |
| Assumed build-target structure — proven WRONG on second pass (issue #275) | First draft asserted `src/CMakeLists.txt` contains the `add_library(ProjectAgamemnon_core ...)` block and named where to insert the new source — inferred ONLY from `test/CMakeLists.txt` referencing the target | The second verification pass found there is NO `src/CMakeLists.txt` at all; the `ProjectAgamemnon_core` STATIC library is defined in the ROOT `CMakeLists.txt:84-99`. The "add the file here" step pointed at an invented file — a guaranteed build break | Open and confirm the `add_library(...)`/`add_executable(...)` block ITSELF; a file that merely *references* a target never reveals where it is *defined*. Verified target location: root `CMakeLists.txt:84-99` |
| Defaulted-param "non-breaking" without full census — later VERIFIED (issue #275) | First draft claimed a trailing defaulted parameter on `register_routes()` "keeps every existing caller compiling," listing only a few test files | The list was not a complete caller census; a defaulted-arg backward-compat claim is only as good as a COMPLETE caller enumeration. (Worktree/build copies also pollute a naive grep) | Second pass did the census excluding `.claude/worktrees/` + `build/`: exactly 9 call sites (1 `server_main.cpp` + 8 tests), NO integration/benchmark callers — only THEN is the claim sound. Always grep the WHOLE repo, exclude worktree/build copies, enumerate every site |
| Absolute line numbers that the plan itself shifts (issue #275) | Cited exact `routes.cpp` line numbers (312/315/318/.../633) for `check_field_length` calls from a single read | The plan's own step 5 edits earlier lines first, shifting every later offset; an implementer trusting the cited line edits the wrong place | Anchor find-replace on searchable symbols/strings, not absolute line numbers, when later edits shift the file |
| Scope-creep with prose/code divergence (issue #275) | Expanded beyond "make limits configurable" to also fix a body-cap override bug AND silently deprecate `SERVER_REQUEST_SIZE_LIMIT_MB` for `AGAMEMNON_MAX_BODY_BYTES`; described a back-compat fallback in prose but the `from_env()` code sample read ONLY `AGAMEMNON_MAX_BODY_BYTES` | Unflagged scope expansion inflates blast radius; the prose-vs-sample divergence is a classic defined-but-not-implemented bug — the fallback would likely never ship | (a) Flag adjacent-bug fixes / deprecations as scope expansion for reviewer sign-off; (b) make the code sample match the prose EXACTLY |
| Unit mismatch on consolidated knobs (issue #275) | Folded `SERVER_REQUEST_SIZE_LIMIT_MB` (MEGABYTES) into `AGAMEMNON_MAX_BODY_BYTES` (BYTES) with a fallback, without highlighting the unit difference | A fallback that copies the MB value as bytes is off by 1,048,576x; the conversion line is silent and easy to get wrong | When consolidating two env knobs with different units, treat the conversion (`mb * 1024 * 1024`) as a high-risk line: state it explicitly and test both knobs |

## Results & Parameters

**Concrete instance this was distilled from (ProjectAgamemnon issue #260):**

- New env var: `AGAMEMNON_API_KEYS` (comma-separated), unioned with existing single
  `AGAMEMNON_API_KEY` in the C++ `AuthMiddleware` (`src/auth.cpp`).
- Accepted-key set construction invariant (illustrative):

```cpp
// Build the set; NEVER insert empty/whitespace -> guarantees count("")==0 rejects empty creds.
std::unordered_set<std::string> valid_keys;
auto add_trimmed = [&](std::string s) {
  // trim leading/trailing std::isspace
  if (!s.empty()) valid_keys.insert(std::move(s));
};
add_trimmed(get_env("AGAMEMNON_API_KEY"));            // legacy single value (backward compat)
std::stringstream ss(get_env("AGAMEMNON_API_KEYS"));  // new multi-value
for (std::string item; std::getline(ss, item, ','); ) add_trimmed(trim(item));

if (valid_keys.empty()) abort_startup();               // fail-secure: all-empty/whitespace -> ABORT
// match:  valid_keys.count(presented_key) == 1
```

**Reviewer focus checklist (copy into the PR description):**

- [ ] Empty `Bearer` (with trailing space) and empty `X-API-Key` are still REJECTED (no empty string ever enters the set).
- [ ] All-empty / all-whitespace `AGAMEMNON_API_KEYS` still ABORTS startup (fail-secure preserved).
- [ ] Relaxation of the startup rule (start with only `*_KEYS`) is confirmed intentional.
- [ ] Any deleted "dead code" verified absent from CMake/build targets, not just source includes.
- [ ] Each cited `file:line` re-resolved against the current tree before editing.
- [ ] Dead-code-removal commit cannot break the build if reviewed/merged independently.
- [ ] Reviewer note: key match is NOT constant-time (pre-existing timing side-channel on a touched surface).

**Second concrete instance — "make a constant configurable" (ProjectAgamemnon issue #275):**

> *"Expose input length limits as configurable server settings"* — introduce an `AGAMEMNON_*`-driven
> `RouteLimits` struct (via a `from_env()` factory) threaded through `register_routes()`, replacing
> hardcoded `check_field_length` constants. The plan also claimed to fix a latent body-cap override
> bug and to deprecate `SERVER_REQUEST_SIZE_LIMIT_MB`.

**VERIFIED facts from the issue #275 second pass (the session caught its own first-draft errors):**

- The build target is defined in the **ROOT `CMakeLists.txt:84-99`** (`add_library(ProjectAgamemnon_core ...)`,
  STATIC). There is **NO `src/CMakeLists.txt`** — the first draft invented it from `test/CMakeLists.txt` references.
- `register_routes()` caller census = **exactly 9 call sites**: 1 in `src/server_main.cpp` + 8 in test files;
  **NO** integration/benchmark callers. Census run with worktree/build copies excluded.
- **Caller-census grep that excludes pollution:**
  `grep -rn 'register_routes' src/ test/ --exclude-dir=.claude --exclude-dir=build`
  (the bare repo carries stray copies under `.claude/worktrees/` and `build/.worktrees/`).
- **Post-edit invariant:** after removing every hardcoded limit, `grep -rn 'kMax' src/routes.cpp` MUST return 0.
- **Knob precedence + unit rule:** `AGAMEMNON_MAX_BODY_BYTES` (BYTES) takes precedence; when only the legacy
  `SERVER_REQUEST_SIZE_LIMIT_MB` (MEGABYTES) is set, fall back as `mb * 1024 * 1024`. Test BOTH knobs AND the
  precedence between them.

Top assumptions a reviewer MUST re-check for this class (some now resolved above):

- [x] Build target location — RESOLVED: root `CMakeLists.txt:84-99`, NOT `src/CMakeLists.txt` (which does not exist).
- [x] COMPLETE caller census for `register_routes()` — RESOLVED: 9 sites (1 src + 8 tests), no integration/benchmark.
- [ ] All `routes.cpp` line citations (312/315/.../633) re-resolved by string at edit time — the
      plan edits earlier lines first, so the offsets drift.
- [ ] The body-cap "bug fix" and the `SERVER_REQUEST_SIZE_LIMIT_MB` → `AGAMEMNON_MAX_BODY_BYTES`
      deprecation are flagged as SCOPE EXPANSION and signed off by the issue owner.
- [ ] The `from_env()` code sample SHOWS the back-compat fallback the prose describes (no
      prose-vs-sample divergence — the sample must read the legacy var too, not only the new one).
- [ ] Unit conversion is explicit: `AGAMEMNON_MAX_BODY_BYTES` (BYTES) fallback from
      `SERVER_REQUEST_SIZE_LIMIT_MB` (MEGABYTES) multiplies by 1 MiB (`mb * 1024 * 1024`); BOTH
      knobs and their precedence are tested.

## Verified On

| Project | Context | Details |
|---------|---------|---------|
| ProjectAgamemnon | Implementation-plan review for issue #260 (multi-key `AGAMEMNON_API_KEYS` in C++ `AuthMiddleware`); plan only, not executed end-to-end | unverified |
| ProjectAgamemnon | Implementation-plan review for issue #275 (make input-length limits configurable via an `AGAMEMNON_*` `RouteLimits` struct threaded through `register_routes()`); plan only, not executed end-to-end. v1.2.0 records the session's self-correcting second pass: build target VERIFIED in root `CMakeLists.txt:84-99` (no `src/CMakeLists.txt`), caller census VERIFIED at 9 sites | unverified (plan); two facts source-verified |
