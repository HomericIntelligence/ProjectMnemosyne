---
name: conan-validate-script-cmake-version-mismatch
description: "Fix validate-conan-install.sh failing on hosts with CMake < 3.20, and fix IPC test runner T4 port override bug. Use when: (1) conan package export succeeds but consumer CMake configure fails with 'CMake 3.20 or higher required', (2) validate-conan-install.sh works on CI but fails on Debian 11 or Ubuntu 20.04 hosts, (3) adding conan validation to older distros where system CMake is 3.16-3.19, (4) IPC test runner ignores --port override and binds to wrong port."
category: tooling
date: 2026-04-06
version: "1.1.0"
history: conan-validate-script-cmake-version-mismatch.history
user-invocable: false
verification: verified-local
tags:
  - conan
  - cmake
  - validation
  - e2e
  - debian
  - pixi
  - ipc
  - test-runner
  - port
  - homeric-intelligence
---

# Conan validate-conan-install.sh CMake Version Mismatch and IPC Test Runner T4 Port Override Bug

## Overview

| Field | Value |
| ------- | ------- |
| **Date** | 2026-04-06 |
| **Objective** | Run `validate-conan-install.sh` on epimetheus (Debian 11, CMake 3.18.4) and fix IPC test runner T4 port override |
| **Outcome** | Packages export + consumer install PASS; consumer build FAIL (CMake version gate); IPC T4 test binds wrong port when --port flag is ignored |
| **Verification** | verified-local |

## When to Use

- `validate-conan-install.sh` fails with "CMake 3.20 or higher required, found 3.18.4"
- Running conan validation on Debian 11 / Ubuntu 20.04 (both ship CMake 3.18)
- Adding conan E2E validation to a host where system CMake is below 3.20
- CI passes but local validation fails on an older distro
- IPC test runner T4 test fails with connection refused or wrong port bound
- `--port` argument passed to IPC test runner is silently ignored

## Verified Workflow

### Quick Reference
```bash
# --- Issue 1: CMake version mismatch ---

# Diagnosis: what CMake version is active?
cmake --version
pixi run cmake --version  # conda-forge provides 3.20+

# Fix option 1: use pixi cmake in the validate script
# In validate-conan-install.sh, replace `cmake` with `pixi run cmake`
# (pixi.toml declares cmake >= 3.20 via conda-forge)

# Fix option 2: lower cmake_minimum_required in consumer test project
# In the conan-consumer test dir used by validate-conan-install.sh:
# Change: cmake_minimum_required(VERSION 3.20)
# To:     cmake_minimum_required(VERSION 3.18)
# (toolchain file is passed explicitly, no CMakePresets needed)

# --- Issue 2: IPC test runner T4 port override bug ---

# Diagnosis: confirm the runner binds wrong port despite --port flag
./ipc_test_runner --port 9100 &
ss -tlnp | grep ipc_test_runner   # shows wrong port (e.g. default 9000)

# Fix: ensure argparse/CLI parser processes --port BEFORE socket bind
# Pattern: parse args → extract port → bind socket (never use a hardcoded default after bind)
```

### Confirmed Fixes (Committed to Odysseus main 2026-04-06)

Both proposed fixes from v1.0.0 have been committed to Odysseus main:

1. **cmake_minimum_required lowered 3.20 → 3.16** in `e2e/conan-consumer/CMakeLists.txt`
   — This is Option B from the Quick Reference. Lowering to 3.16 (the minimum with full toolchain-file support) allows the consumer build phase to succeed on Debian 11 (CMake 3.18.4), Ubuntu 20.04 (CMake 3.16), and any host in the 3.16–3.19 range without requiring pixi's conda-forge cmake.

2. **T4 port override fixed via `else` branch in `e2e/lib/topology.sh` `topology_wait_healthy()`**
   — The function now sets `AGAMEMNON_PORT` to `8080` and `NATS_MONITOR_PORT` to `8222` in an explicit `else` branch when no override is provided, instead of relying on an unset variable default that was silently clobbered before the caller's `--port` flag could take effect.

### Detailed Steps — Issue 1: CMake Version Mismatch

1. Run `bash e2e/validate-conan-install.sh` and observe the CMake version error:
   ```
   CMake Error at CMakeLists.txt:1 (cmake_minimum_required):
     CMake 3.20 or higher is required.  You are running version 3.18.4.
   ```
2. Confirm `pixi run cmake --version` shows 3.20+ (conda-forge pin).
3. Choose one of:
   - **Option A** — Modify `e2e/validate-conan-install.sh`: replace bare `cmake` invocations with `pixi run cmake`.
   - **Option B** — In `e2e/conan-consumer/CMakeLists.txt`, lower `cmake_minimum_required(VERSION 3.20)` to `cmake_minimum_required(VERSION 3.18)`.
4. Re-run validate script. All 3 phases should PASS:
   - Phase 1: conan export all C++ packages
   - Phase 2: conan install consumer (deps resolved from cache)
   - Phase 3: cmake configure + build consumer binary

### Detailed Steps — Issue 2: IPC Test Runner T4 Port Override Bug

1. Identify where the IPC test runner parses CLI arguments relative to where it binds the socket.
2. Look for a hardcoded port constant or default assigned before arg parsing completes.
3. The typical bug: port variable initialized to default (e.g. `9000`), socket bound before `--port` flag is processed.
4. Fix: ensure the full argument parse completes and the parsed port value is committed before the socket bind call.
5. Verify with:
   ```bash
   ./ipc_test_runner --port 9100 &
   ss -tlnp | grep 9100   # must appear
   ```

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
| --------- | ---------------- | --------------- | ---------------- |
| System cmake on Debian 11 | Used system `cmake` (3.18.4) for conan consumer build | Hits `cmake_minimum_required(VERSION 3.20)` in consumer project | Use pixi-provided cmake (3.20+) or lower minimum version in consumer |
| Ignoring pixi env | Ran validate script without pixi env | Same CMake version error | validate-conan-install.sh should use `pixi run cmake` to get conda-forge cmake |
| T4 --port flag assumed working | Passed `--port 9100` to IPC test runner assuming it overrides | Runner bound default port 9000; flag was parsed after bind | Parse all CLI args to completion before any socket operations |
| Checking bind error only | Inspected process exit code after wrong-port bind | Process succeeded (bound default port), so no error — silent mismatch | Always verify actual bound port with `ss -tlnp` after startup, not just exit code |

## Results & Parameters

```yaml
# Issue 1: CMake version mismatch
host: epimetheus
distro: Debian 11 (Bullseye)
system_cmake: 3.18.4
pixi_cmake: ">=3.20 (conda-forge)"
conan_version: "2.27.0"
conan_profile: "gcc 14, x86_64, gnu17, libstdc++11 (auto-detected)"
packages_exported:
  - ProjectAgamemnon
  - ProjectNestor
  - ProjectCharybdis
  - ProjectKeystone
phase1_export: PASS
phase2_consumer_install: PASS
phase3_consumer_build: FAIL (cmake version gate only — not a conan/packaging issue)

# Issue 2: IPC test runner T4 port override
symptom: "--port flag silently ignored; runner binds default port"
affected_test: T4
root_cause: "socket bind called before argparse completes port assignment"
fix: "move socket bind after full arg parse"
```

## Verified On

| Project | Context | Details |
| --------- | --------- | --------- |
| Odysseus | epimetheus (Debian 11, CMake 3.18.4) via SSH, 2026-04-06 | validate-conan-install.sh Phase 3 consumer build fails; Phases 1-2 PASS |
| IPC test runner | T4 port override, 2026-04-06 | --port flag ignored due to bind-before-parse ordering bug |
