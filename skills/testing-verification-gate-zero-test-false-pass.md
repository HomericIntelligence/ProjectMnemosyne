---
name: testing-verification-gate-zero-test-false-pass
description: "A name-filtered verification gate that selects ZERO tests still exits 0 (green) and silently gates nothing — a FALSE PASS. Happens with `pytest -k <expr>`, `ctest -R <regex>`, `go test -run <regex>` etc. when the filter matches nothing OR the test source is compiled into NO build target (orphaned file). The change then ships untested. Use when: (1) a plan modifies/wraps an 'existing' test, (2) a verification step relies on a NAME-FILTERED selection (`pytest -k`, `ctest -R`, `go test -run`), (3) you add net-new code and want a real gate, (4) you must enforce a DeprecationWarning rather than just allow it, (5) a plan cites `ctest -R <name>` as an acceptance gate — first prove the test source is wired into a CMake target."
category: testing
date: 2026-06-20
version: "1.1.0"
user-invocable: false
history: testing-verification-gate-zero-test-false-pass.history
tags: [testing, pytest, ctest, cmake, gtest, verification-gate, false-pass, deprecation-warning, test-count, collect-only, show-only, orphaned-test, target-file, planning, plan-review]
---

# Verification Gate: Zero-Test False Pass

## Overview

| Field | Value |
|-------|-------|
| Date | 2026-06-20 |
| Objective | Validate the test gates in R1 re-plans (after NOGO) on ProjectAgamemnon — both a pytest deprecation-shim gate (#143) and a C++/ctest healthcheck gate (#279) |
| Outcome | Planning-only (R1 re-plans after NOGO). Both plans cited a NAME-FILTERED gate that selected ZERO tests yet exited 0 — a false pass. pytest case: `pytest -k config` matched nothing; ctest case: `ctest -R Healthcheck` matched nothing because `test/src/test_healthcheck.cpp` was compiled into NO CMake target (orphaned). Fixes: prove the gate is non-empty before trusting it, wire the orphaned test into its own target, inject the binary-under-test path via `$<TARGET_FILE:...>` |
| Verification | unverified — gates not executed; no CI ran; facts from static source reading + plan-reviewer verification |
| History | [changelog](./testing-verification-gate-zero-test-false-pass.history) |

## When to Use

- A plan or issue says "wrap the existing `LegacyClass(...)` test in `pytest.warns`" or "modify test X" — before trusting it, confirm X actually exists.
- A verification step relies on a **name-filtered selection** (`pytest -k <expr>`, `ctest -R <regex>`, `go test -run <regex>`) to gate a change.
- **A plan cites `ctest -R <name>` (or any name-filtered runner) as an ACCEPTANCE GATE** — first prove the filter matches ≥1 registered test AND the test source is wired into a real build target. An orphaned test file (in no CMake target) makes the gate a silent no-op.
- You are adding **net-new** code (a deprecation shim, a new module, a new test file) and want a gate that actually exercises it.
- You need a DeprecationWarning to be **enforced** (failing the build if it regresses), not merely permitted.
- You are wiring an orphaned test that shells out to a built binary and need a robust, CWD-independent way to find that binary.

## Verified Workflow

> **Warning:** This workflow has not been validated end-to-end. Both gates were captured during R1 re-planning (after NOGO); neither was executed (no build, no `ctest`, no `pytest` run, no CI). Treat as a hypothesis until CI confirms. The ctest/CMake rows added in v1.1.0 are `unverified (plan-only)`.

The trap: a name-filtered runner returns exit code 0 when it collects **zero** matching tests. Green build, nothing tested. Two ways to get zero matches:

1. The filter expression simply doesn't match any registered test name (`pytest -k config`, a wrong `ctest -R` regex), or you wrapped `pytest.warns` around a call that never existed.
2. **The test source is compiled into no build target.** `test/src/test_healthcheck.cpp` not listed in `test/CMakeLists.txt` → no executable is built → `ctest -R Healthcheck` matches nothing and exits 0, *appearing* to pass while proving nothing. This is the C++/CMake-specific manifestation and is especially insidious because the file exists on disk and reads like a real test.

A verification step is only as real as the target it runs. The fix is to (a) prove the gate is non-empty before trusting it, (b) for C++ specifically, grep the build config to prove the test source is wired into a target, (c) add an explicit empty-match guard so a zero-match run FAILS, and (d) for orphaned-test wiring, inject the binary-under-test path via the build system's target-location primitive, never a hard-coded relative path.

### Quick Reference

```bash
# === pytest variant ===
# FALSE PASS to avoid — selects 0 tests, exits 0, gates nothing:
pytest -k config            # "no tests ran" but exit code 0  → green, untested

# BEFORE planning "wrap existing test X": confirm the assertions/tests exist.
grep -rnE 'setenv|os\.environ|KEYSTONE_|monkeypatch' tests/*.py
# Empty result + no tests/test_config.py ⇒ the "existing test to wrap" is PHANTOM.

# REAL gate — assert the expected COUNT and enforce the warning:
pytest tests/test_config_deprecation.py -W error::DeprecationWarning -q | tee /tmp/out.txt
grep -q "4 passed" /tmp/out.txt || { echo "FALSE PASS: expected 4 tests"; exit 1; }
pytest --collect-only -q | tail -1   # collection parity: must equal baseline + N-new

# === ctest / CMake variant (added v1.1.0, plan-only) ===
# FALSE PASS to avoid — orphaned test source ⇒ regex matches 0 tests, exits 0:
ctest -R Healthcheck        # "No tests were found" but exit 0 if no target built it

# STEP A — prove the test source is wired into a build target (else the gate is a no-op):
grep -q test_healthcheck test/CMakeLists.txt || { echo "ORPHANED: test in no target"; exit 1; }

# STEP B — empty-match guard: FAIL when the name filter matches zero registered tests:
ctest -R Healthcheck --show-only | grep -qE 'Test #' || { echo "FALSE PASS: 0 tests matched"; exit 1; }
```

```cmake
# STEP C — wire the orphaned test into its OWN executable and inject the
# binary-under-test path via $<TARGET_FILE:...>, NEVER a hard-coded literal path.
add_executable(ProjectAgamemnon_healthcheck_tests test/src/test_healthcheck.cpp)
target_link_libraries(ProjectAgamemnon_healthcheck_tests PRIVATE GTest::gtest_main)
# pass the real binary location into the test as a compile definition (build-time):
target_compile_definitions(ProjectAgamemnon_healthcheck_tests PRIVATE
  HEALTHCHECK_BINARY_PATH="$<TARGET_FILE:ProjectAgamemnon_healthcheck>")
add_dependencies(ProjectAgamemnon_healthcheck_tests ProjectAgamemnon_healthcheck)
gtest_discover_tests(ProjectAgamemnon_healthcheck_tests)
```

### Detailed Steps

1. **Classify every test command a plan cites as an acceptance gate.** Does it run a FIXED target (whole suite/binary), or a NAME-FILTERED subset (`-k` / `-R` / `-run`)? Name-filtered → treat as suspect until proven non-empty.
2. **For name-filtered gates, prove the source is wired into a target.** `grep <test_file_stem> <build-config>` (e.g. `test/CMakeLists.txt`). No match → the gate is a no-op and the plan is unsound until fixed.
3. **For pytest "wrap/modify existing test X":** grep-confirm X exists first. Empty result ⇒ phantom; net-new code needs a NET-NEW test, not a wrapped phantom assertion.
4. **Add an explicit empty-match guard** so the gate FAILS on zero matches: `ctest -R X --show-only | grep -qE 'Test #' || exit 1` or `grep -q "<N> passed"` for pytest. Never trust the bare exit code of a name-filtered run.
5. **When wiring an orphaned test that shells out to a built binary**, inject the binary's path via the build system's target-location primitive (CMake `$<TARGET_FILE:tgt>` + `add_dependencies`), never a hard-coded relative path — relative paths break when the binaryDir/output-dir differs from the assumed CWD (e.g. `./build/healthcheck` vs `build/debug/ProjectAgamemnon_healthcheck`).
6. **Enforce, don't merely permit** (pytest): run with `-W error::DeprecationWarning` and check `--collect-only` count parity so a missing or regressed test fails the build.

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
|---------|----------------|---------------|----------------|
| 1 | Plan: "wrap each legacy-var assertion in `pytest.warns`" to verify the new deprecation shim | `grep -rnE 'setenv\|os.environ\|KEYSTONE_\|monkeypatch' tests/*.py` returned nothing and no `test_config.py` existed — the assertions to wrap were phantom | Before writing "wrap/modify existing test X", grep-confirm X exists; net-new code needs a NET-NEW test, not a wrapped phantom |
| 2 | `pytest -k config` as the verification gate for the change | It matched 0 tests, exited 0 (green), and gated nothing — a FALSE PASS; net-new shim shipped untested | A `pytest -k` gate matching zero tests is a false pass; assert the expected pass COUNT (e.g. `grep -q "4 passed"`) so a zero-match run fails |
| 3 | Allowed the DeprecationWarning to merely fire (default filter) | A merely-allowed warning never fails the build, so a regression on the deprecation path would pass silently | Run with `-W error::DeprecationWarning` to enforce the warning, and use `--collect-only` count parity (baseline + N-new) so a missing test can't hide |
| 4 (plan-only) | Cited `ctest -R Healthcheck` as an acceptance gate without checking the test was wired into a target | `test/src/test_healthcheck.cpp` was in NO CMake target, so the regex matched 0 tests, exited 0, and proved nothing; the plan reviewer correctly NOGO'd it | Always guard name-filtered gates with an empty-match check AND verify the source is in a build target: `grep <stem> test/CMakeLists.txt` then `ctest -R X --show-only \| grep -qE 'Test #'` |
| 5 (plan-only) | Test hard-coded `./build/healthcheck` (wrong binary name AND wrong relative path) | Would never find the real binary under `build/debug/ProjectAgamemnon_healthcheck`; relative path assumes a specific CWD | Inject the binary path via CMake `$<TARGET_FILE:...>` (+ `add_dependencies`), not a literal — it resolves correctly regardless of output dir |
| 6 (plan-only) | Marked a plan's verification step "proves the binary still behaves correctly" while the underlying test was orphaned | False confidence — the gate ran zero tests | A verification step is only as real as the target it runs; an orphaned test file silently no-ops the gate |

## Results & Parameters

- **pytest false-pass command:** `pytest -k config` → "no tests ran", exit 0.
- **ctest false-pass command (plan-only):** `ctest -R Healthcheck` → "No tests were found", exit 0, when the source is in no target.
- **Phantom-detection grep (pytest):** `grep -rnE 'setenv|os\.environ|KEYSTONE_|monkeypatch' tests/*.py` (empty ⇒ no test to wrap).
- **Orphaned-target grep (ctest):** `grep -q test_healthcheck test/CMakeLists.txt` (no match ⇒ orphaned; gate is a no-op).
- **Empty-match guards:** pytest `grep -q "<N> passed"`; ctest `ctest -R X --show-only | grep -qE 'Test #' || exit 1`.
- **Orphaned-test wiring (CMake):** `add_executable` + `target_compile_definitions(... HEALTHCHECK_BINARY_PATH="$<TARGET_FILE:tgt>")` + `add_dependencies` + `gtest_discover_tests`.
- **Open reviewer risks (plan-only, ctest case):** (1) the new `ProjectAgamemnon_healthcheck_tests` target was written but NEVER compiled — `gtest_discover_tests` runs the binary at build time, so a segfault/missing runtime dep breaks discovery; (2) the suite name `HealthcheckTest.*` was read from `TEST_F(HealthcheckTest, …)` but not confirmed via `--show-only`; (3) `$<TARGET_FILE:...>` injected as a string into `system("PORT=… " + HEALTHCHECK_BINARY_PATH)` — shell-quoting/escaping for paths with spaces or metacharacters not considered; (4) the test shells out and binds real localhost ports under the `debug` preset (sanitizers ON) — subprocess + port-binding can be flaky/slow under ASan; unverified.
- **Externally-cited-but-unverified:** cpp-httplib Conan recipe `with_openssl=False` (from prior reviewer, not re-inspected); nats.c TLS build flags (deferred to a runtime `ldd` check — good, but causal claim unverified); team-KB `cpp-cmake-ci-build-and-test-fixes` Fix 2/Fix 4f cited as authority for the `$<TARGET_FILE>` approach (sound, but applied to an unbuilt target).
- **Rules:** (1) classify every gate as fixed-target vs name-filtered; (2) for name-filtered gates prove the source is in a build target; (3) add an empty-match guard that fails on zero tests; (4) inject binary paths via `$<TARGET_FILE:...>`, never literals; (5) for pytest, assert pass count and enforce warnings as errors.
- **Status:** unverified (planning-only); gates not executed, no CI run.

## Verified On

| Item | Value |
|------|-------|
| Project | ProjectAgamemnon |
| pytest case | #143 (R1 planning) — `pytest -k config` zero-match false pass; ProjectKeystone → ProjectAgamemnon deprecation shim; meta-repo Odysseus |
| ctest case | #279 (plan-only / unverified, R1 re-plan after NOGO) — `ctest -R Healthcheck` orphaned-target false pass; `test/src/test_healthcheck.cpp` in no CMake target |
| Verification | unverified — neither gate executed |
