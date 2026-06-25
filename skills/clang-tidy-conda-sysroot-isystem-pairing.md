---
name: clang-tidy-conda-sysroot-isystem-pairing
description: "Use when clang-tidy fails with \"'stddef.h' file not found\" (or similar libc/compiler-builtin header errors) under a conda-forge / pixi GCC toolchain, or when deciding whether passing --extra-arg=--sysroot to clang-tidy fixes header resolution: clang-tidy needs BOTH --sysroot (conda cross sysroot, for libc headers like wchar.h) AND -isystem<gcc include dir> (for compiler builtins like stddef.h); --sysroot alone reproduces the error. Derive both from the live compiler via $CXX -print-sysroot / -print-file-name=include in StaticAnalyzers.cmake — never hardcode the pixi env path."
category: tooling
date: 2026-06-19
version: "1.0.0"
user-invocable: false
verification: verified-local
tags: []
---

# clang-tidy + conda-forge GCC: pair `--sysroot` with `-isystem<gcc include>`

## Overview

| Field | Value |
| --- | --- |
| Date | 2026-06-19 |
| Objective | Make clang-tidy resolve both libc headers (conda sysroot) and compiler builtins (GCC builtin include dir) under a conda-forge / pixi GCC toolchain, so `#include <cwchar>` → `wchar.h` → `#include <stddef.h>` does not fail with `'stddef.h' file not found` |
| Outcome | clang-tidy passes both `--extra-arg=--sysroot=<sysroot>` and `--extra-arg=-isystem<gcc_include>`, with both paths derived from the live `$CXX` and the `--sysroot` append guarded behind a non-empty check |
| Verification | verified-local — reproduced on conda-forge gcc 14.3.0 + clang-tidy 22.1.5 with a standalone clang-tidy invocation on a synthetic `#include <cwchar>` TU; NOT validated by a full `just build` end-to-end (verified-local, not verified-ci) |
| Context | ProjectAgamemnon issue #264 — "clang-tidy fails with conda sysroot stddef.h error on GCC 14 env"; planning artifact. Prior PR #385 / commit `7ec2cb9` already passed `-isystem` and made the reported symptom pass; this captures the robustness/coverage gap and the `--sysroot`-alone anti-pattern |

> **Warning:** Verification is verified-local. The clang-tidy command was confirmed in isolation on one conda-forge toolchain; the CMake `list(APPEND ...)` wiring and a real full-project `just build` were NOT executed end-to-end, and the `--sysroot` guard's behavior on CI (where `$CXX -print-sysroot` may be empty) is unverified.

## When to Use

Apply this skill when:

- **clang-tidy reports `'stddef.h' file not found` under a conda/pixi sysroot** — typically surfacing through `#include <cwchar>` → conda `wchar.h:35` → `#include <stddef.h>`.
- **The build fails when clang-tidy is on PATH with a conda-forge GCC toolchain** — i.e. clang-tidy is a different frontend than the conda-forge `cxx-compiler` GCC that the build otherwise uses, so clang-tidy does not inherit the GCC builtin include dir automatically.
- **You are deciding whether to pass `--sysroot` to clang-tidy** to fix header resolution — and need to know that `--sysroot` alone is insufficient (and actively re-breaks builtins).
- You are editing `cmake/StaticAnalyzers.cmake` (or equivalent) where the `CMAKE_CXX_CLANG_TIDY` / clang-tidy `--extra-arg` list is assembled.

**Key triggers:**

- An issue or reviewer *proposes* "just pass `--extra-arg=--sysroot=<sysroot>`" as the fix. Treat that as a hypothesis to reproduce, not a specification — here it makes things worse.
- The conda-forge `cxx-compiler` resolves headers against two distinct locations and clang-tidy only sees one of them.

## Verified Workflow

The conda-forge `cxx-compiler` toolchain resolves headers against **two distinct** locations:

1. **The conda cross sysroot** — `<pixi_env>/x86_64-conda-linux-gnu/sysroot`. Holds libc headers such as `wchar.h`. Crucially, `wchar.h` itself does `#include <stddef.h>`.
2. **The GCC builtin include dir** — `<...>/lib/gcc/x86_64-conda-linux-gnu/<ver>/include`. Holds compiler builtins such as `stddef.h`.

`stddef.h` lives in (2), the GCC builtin include dir — **not** in the sysroot (1). Therefore:

- `--sysroot` alone redirects libc header resolution into the conda sysroot but does **not** add the GCC builtin include dir, so `stddef.h` becomes unreachable → `'stddef.h' file not found`.
- `-isystem<gcc include>` alone (the prior #385 fix) makes builtins reachable and already passes the reported symptom today, but does not point libc resolution at the conda sysroot.
- The correct fix passes **both** `--sysroot` and `-isystem<gcc include>`.

Both paths must be derived from the **live** compiler (the pixi env name varies across machines/CI, so hardcoding is wrong), and the `--sysroot` append must be guarded behind a non-empty check so a stock/system toolchain (where `-print-sysroot` is empty) is not handed a bare `--sysroot=`.

### Quick Reference

Standalone clang-tidy invocation (the BOTH-flags command — this is what was verified-local):

```bash
GCC_INCLUDE_DIR="$($CXX -print-file-name=include)"   # GCC builtin include dir (has stddef.h)
SYSROOT="$($CXX -print-sysroot)"                      # conda cross sysroot (has wchar.h); may be empty on stock toolchains

clang-tidy some_tu.cpp -- \
  --extra-arg=-isystem"${GCC_INCLUDE_DIR}" \
  --extra-arg=--sysroot="${SYSROOT}"
```

CMake wiring in `StaticAnalyzers.cmake` — derive both paths from `${CMAKE_CXX_COMPILER}`, guard the `--sysroot` append:

```cmake
# Compiler builtins (stddef.h) live in the GCC builtin include dir.
execute_process(
  COMMAND ${CMAKE_CXX_COMPILER} -print-file-name=include
  OUTPUT_VARIABLE GCC_INCLUDE_DIR
  OUTPUT_STRIP_TRAILING_WHITESPACE)

# libc headers (wchar.h) live in the conda cross sysroot. Empty on stock/system toolchains.
execute_process(
  COMMAND ${CMAKE_CXX_COMPILER} -print-sysroot
  OUTPUT_VARIABLE COMPILER_SYSROOT
  OUTPUT_STRIP_TRAILING_WHITESPACE)

list(APPEND CMAKE_CXX_CLANG_TIDY "--extra-arg=-isystem${GCC_INCLUDE_DIR}")

# Guard: only append --sysroot when the toolchain actually reports one,
# so a stock toolchain is never handed a bare "--sysroot=".
if(COMPILER_SYSROOT)
  list(APPEND CMAKE_CXX_CLANG_TIDY "--extra-arg=--sysroot=${COMPILER_SYSROOT}")
endif()
```

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
| --- | --- | --- | --- |
| `--sysroot` alone | Passing only `--extra-arg=--sysroot=<sysroot>` to clang-tidy | Reproduced `'stddef.h' file not found` in conda `wchar.h` (e.g. `wchar.h:35:10`) | `--sysroot` redirects libc header resolution to the conda sysroot but does not add the GCC builtin include dir where `stddef.h` lives; must pair with `-isystem<gcc include>` |
| Hardcoded sysroot path | Hardcoding the pixi env path for the sysroot (or the GCC include dir) | Env name varies across machines/CI; the path is wrong elsewhere | Derive both from the live compiler: `$CXX -print-sysroot` and `$CXX -print-file-name=include` |
| Trusting the issue's proposed fix | Adopting the issue's literal proposal (`--sysroot` alone) without reproducing it | The proposal made the build *worse* (re-introduced the error) | Reproduce proposed fixes before adopting them; treat issue-body fix suggestions as hypotheses, not specifications |
| Unconditional `--sysroot` append | Appending `--sysroot=${COMPILER_SYSROOT}` without a non-empty check | A stock/system toolchain reports an empty `-print-sysroot`, yielding a bare `--sysroot=` argument | Guard the append behind a non-empty `if(COMPILER_SYSROOT)` check |
| Assuming the build is red | Planning a from-scratch fix assuming clang-tidy was currently broken | Prior PR #385 / commit `7ec2cb9` already passed `-isystem` and made the reported symptom pass | Check for a prior (partial) fix before planning; the real gap was robustness/coverage, not a broken build |

## Results & Parameters

Exact clang-tidy flags (both required):

- `--extra-arg=-isystem<GCC_INCLUDE_DIR>` — adds the GCC builtin include dir (compiler builtins: `stddef.h`, ...).
- `--extra-arg=--sysroot=<SYSROOT>` — points libc header resolution at the conda cross sysroot (`wchar.h`, ...). Append only when non-empty.

Path derivations (from the live compiler, never hardcoded):

- `GCC_INCLUDE_DIR = $($CXX -print-file-name=include)` — e.g. `<pixi_env>/lib/gcc/x86_64-conda-linux-gnu/<ver>/include`.
- `SYSROOT = $($CXX -print-sysroot)` — e.g. `<pixi_env>/x86_64-conda-linux-gnu/sysroot`; empty string on a stock/system toolchain.

Reproduction matrix (verified-local on conda-forge gcc 14.3.0, clang-tidy 22.1.5, synthetic `#include <cwchar>` TU):

| Flags passed to clang-tidy | Result |
| --- | --- |
| `-isystem${GCC_INCLUDE_DIR}` only (prior #385 fix) | CLEAN — already works today |
| `--sysroot` only (the issue's literal proposal) | REPRODUCES `wchar.h:35:10: error: 'stddef.h' file not found` |
| BOTH `--sysroot` + `-isystem` | CLEAN — this is the chosen change |

### Reviewer-risk notes (unverified assumptions to scrutinize)

- **verified-local, not verified-ci:** confirmed with a standalone clang-tidy run on a synthetic `#include <cwchar>` TU; the CMake `list(APPEND ...)` wiring and a real `just build` end-to-end were NOT executed.
- `$CXX -print-sysroot` returning a non-empty conda path is environment-specific; on CI or a different toolchain it could be empty. The guard handles that, but the guard's behavior on CI is unverified.
- Whether `--sysroot` interacts with conda headers beyond `wchar.h` / `stddef.h` was not exhaustively tested — only the reported repro path was checked.
- Cited line numbers (`StaticAnalyzers.cmake:7-13`, `CMakeLists.txt:170-172`) were from a snapshot and may drift; re-locate the clang-tidy `--extra-arg` list before editing.
