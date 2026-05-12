---
name: mojo-sanitizer-build-scope-and-tcmalloc-incompat
description: "Scope Mojo ASAN/TSAN builds to shared-library-only + per-test compile, not full binary AOT. Document the known TSAN/tcmalloc startup abort. Use when: (1) adding --sanitize modes to a Mojo build, (2) sanitizer sweeps OOM partway through, (3) TSAN binaries abort with `FATAL: ThreadSanitizer: unexpected memory mapping`."
category: testing
date: 2026-05-11
version: "1.0.0"
user-invocable: false
verification: verified-ci
tags:
  - mojo
  - sanitizer
  - asan
  - tsan
  - tcmalloc
  - build-scope
  - oom
  - justfile
  - mojo-1-0
---

# Mojo Sanitizer Build Scope and tcmalloc/TSAN Runtime Incompatibility

## Overview

| Field | Value |
| --- | --- |
| **Date** | 2026-05-11 |
| **Objective** | Define the correct *build scope* for Mojo `--sanitize=address` / `--sanitize=thread` modes on memory-constrained hosts, and document that TSAN currently aborts at startup due to tcmalloc / ThreadSanitizer shadow-memory incompatibility (a Modular-side issue, not user code). |
| **Outcome** | Verified in ProjectOdyssey PR #5389: sanitizer modes package the shared library only, then run sanitized tests one process at a time. ASAN sweep ran 298/298 tests and surfaced 46 real leaks in `shared/`. TSAN sweep ran 298/298 binaries but every binary aborted at startup with the tcmalloc/ThreadSanitizer error — confirming the runtime incompatibility is the blocker, not the recipe. |
| **Verification** | verified-ci |

## When to Use

- You are adding `--sanitize=address` or `--sanitize=thread` modes to a Mojo build
  system (justfile, Makefile, CI matrix) and need to decide which artifacts to compile.
- A sanitizer build sweep OOM-kills partway through on a memory-constrained host
  (e.g., ≤16 GiB RAM workstation); the container or shell dies after ~4 `mojo build`
  invocations.
- TSAN binaries abort at startup with
  `FATAL: ThreadSanitizer: unexpected memory mapping` and tcmalloc `MmapAligned()`
  / `Arena::Alloc` `CHECK` failures.
- You are tempted to set `ODYSSEY_MEM_LIMIT > physical RAM` or restart the container
  between builds to "free memory" — see Failed Attempts below for why neither works.
- Companion skills:
  [`mojo-sanitizer-support-matrix`](./mojo-sanitizer-support-matrix.md) (which
  `--sanitize=X` flags are accepted by the compiler / link / run),
  [`mojo-jit-crash-retry`](./mojo-jit-crash-retry.md) (`-j1` workaround for
  modular/modular#6413), [`tcmalloc`](https://github.com/google/tcmalloc) (the
  allocator inside Mojo's runtime).

## Verified Workflow

### Quick Reference

The verified pattern is **two-phase**: (A) always package the shared library; (B) for
sanitizer modes, **stop there** — defer per-binary instrumentation to test time, where
each test compiles and runs one process at a time.

```just
# justfile recipe (excerpt — exact pattern shipped in ProjectOdyssey PR #5389)

build mode="debug":
    @just _run "just _build-inner {{mode}}"

[private]
_build-inner mode="debug":
    #!/usr/bin/env bash
    set -euo pipefail
    MODE="{{mode}}"
    STRICT="--max-notes 0"
    JOBS=""

    case "$MODE" in
        debug)   FLAGS="-g $STRICT" ;;
        release) FLAGS="-O3 $STRICT" ;;
        asan)    FLAGS="-g1 --sanitize address $STRICT" ;;
        tsan)    FLAGS="-g1 --sanitize thread  $STRICT" ; JOBS="-j1" ;;
        *) echo "unknown mode: $MODE" >&2; exit 2 ;;
    esac

    # Phase A: package the shared library (ALWAYS — sanitizer or not)
    pixi run mojo package $STRICT -I "$REPO_ROOT" shared \
        -o ".build/$MODE/shared.mojopkg"

    # Phase B: sanitizer modes SKIP example/benchmark AOT compile (OOM-prone)
    if [ "$MODE" = "asan" ] || [ "$MODE" = "tsan" ]; then
        echo "✅ Sanitizer build complete (shared package only)"
        echo "  Run sanitized tests: just test-mojo-${MODE}"
        exit 0
    fi

    # Non-sanitizer modes continue here with per-binary AOT compile:
    # pixi run mojo build $FLAGS $JOBS examples/lenet5/main.mojo -o .build/$MODE/lenet5
    # ... 45 more binaries ...
```

Companion test recipe (sketch):

```just
test-mojo-asan:
    # Compile + run each test under ASAN, one process at a time.
    # Each test is its own `mojo build --sanitize address` + execution.
    # Memory pressure is bounded by single-process residency, not 46 parallel builds.
    @for t in tests/**/test_*.mojo; do \
        pixi run mojo build -g1 --sanitize address -I shared -o "$$t.bin" "$$t" && \
        ASAN_OPTIONS=halt_on_error=0:abort_on_error=0:detect_leaks=1 "$$t.bin"; \
    done

test-mojo-tsan:
    # Same shape as asan, but every binary will currently abort at startup
    # with the tcmalloc/ThreadSanitizer error documented below.
    # Recipe is correct — runtime is the blocker.
```

### Detailed Steps

1. **Phase A: package shared library.** `mojo package` on `shared/` builds the
   `.mojopkg` reusable artifact. This is the only build step that produces a
   shippable artifact for sanitizer modes; per-binary AOT compiles of `examples/`
   and `benchmarks/` are pure validation that already happens in non-sanitizer
   `debug` / `release` builds.

2. **Phase B: short-circuit for sanitizer modes.** A `case "$MODE" in asan|tsan)
   exit 0` after Phase A. This is the load-bearing decision — see "Failed
   Attempts" row about full-AOT sanitizer sweeps. Sanitizers are useful for
   *runtime* leak/race detection, not compile-time validation of binaries that
   will never run in production.

3. **Test-time per-binary compile.** `just test-mojo-asan` and
   `just test-mojo-tsan` compile and run each test under the sanitizer, one
   process at a time. Memory pressure is bounded by the residency of one
   `mojo build` + one running test, not by 46 parallel AOT builds.

4. **For TSAN: add `-j1`.** Mojo TSAN compiles tickle `modular/modular#6413`
   (parallel-JIT crashes). `-j1` forces serial compilation and avoids the JIT
   crash. **This does not fix the runtime tcmalloc abort** — see next step.

5. **Acknowledge the TSAN runtime blocker.** Every TSAN-built Mojo binary
   currently aborts at startup with the tcmalloc/ThreadSanitizer error in the
   next section. The recipe and codegen are correct; the abort happens in the
   runtime initializer before `main()`. This is a Modular-side issue (see
   `mojo-sanitizer-support-matrix` for the support-matrix view); the build-scope
   pattern is still correct because once Modular ships a fix, the same recipe
   produces working TSAN test runs without changes.

### TSAN runtime: tcmalloc shadow-memory abort (verbatim signature)

Future searches must grep this in. Full text observed on every TSAN binary
launch in PR #5389's CI run (298/298 binaries aborted with this signature
before reaching user code):

```text
FATAL: ThreadSanitizer: unexpected memory mapping 0x<addr>-0x<addr>
<pid> external/tcmalloc+/tcmalloc/internal/system_allocator.h:585]
  MmapAligned() failed - unable to allocate with tag
  (hint=0x<addr>, size=1073741824, alignment=1073741824)
<pid> external/tcmalloc+/tcmalloc/arena.cc:59] CHECK in Alloc: FATAL ERROR:
  Out of memory trying to allocate internal tcmalloc data
Aborted (core dumped)
```

**Root cause (not a code bug):** tcmalloc (the allocator bundled with Mojo's
runtime) requests 48-bit address regions for its internal arenas. Under
ThreadSanitizer, those regions overlap TSAN's shadow-memory map, and TSAN
refuses the mapping. tcmalloc has no fallback path and aborts. Fix must come
from Modular — either rebuild tcmalloc with `TCMALLOC_ADDRESS_BITS` matching
the runtime VA, or link sanitizer builds against the system allocator
(`libc` malloc) instead of tcmalloc.

**What you can do today:** ship the recipe (it's correct), document the
runtime abort, and run the TSAN sweep so the failure surface is captured. Do
not chase user-code changes — they cannot move the abort because it happens
before user code runs.

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
| --- | --- | --- | --- |
| Full `--sanitize=address` AOT of examples/benchmarks | Compiled all 46 example/benchmark binaries under `--sanitize address` as part of `just build asan`, expecting it to validate "code under sanitizer mode" | Each `mojo build --sanitize=address` peaks at ~3-6 GB; the container OOM-killed after ~4 binaries on a 15 GiB RAM workstation. Even when memory held, the resulting binaries were never run — sanitizers are for *runtime* leak/race detection, not compile-time validation. ~4 hours of compile time produced zero usable signal. | Scope sanitizer mode to the shared-library package only; do per-binary instrumentation at *test time* (one process at a time), not at build time (46 parallel AOTs). |
| Raise `ODYSSEY_MEM_LIMIT` above physical RAM | Set `ODYSSEY_MEM_LIMIT=24g` in `docker-compose` overrides hoping cgroups would let `mojo build` use swap | cgroups caps the effective memory at physical RAM regardless of the configured limit when the host doesn't have backing swap configured for the slice. Setting limit > RAM just delays the OOM kill; it doesn't add memory. | Don't try to grow the memory ceiling above hardware. Reduce demand (Phase B short-circuit) instead. |
| `-j1` to "fix" TSAN | Added `JOBS="-j1"` for TSAN mode citing `modular/modular#6413` (parallel-JIT crashes under TSAN) | `-j1` did fix the JIT crash on TSAN compiles — but every resulting binary still aborts at startup with the tcmalloc/ThreadSanitizer shadow-memory error before reaching user code. `-j1` is necessary for the compile to succeed, but not sufficient for the binary to run. | Keep `-j1` in the TSAN recipe (correct workaround for compile-time JIT crash) but understand it is *not* a fix for the runtime abort. The runtime abort needs a Modular-side tcmalloc fix. |
| `podman compose restart` between sanitizer builds | Restarted the dev container between `just build asan` and `just build tsan` to "free memory" | (a) cgroups memory counters are not reset by `podman compose restart`; the new container hits the same effective RAM cap. (b) Restart lost the workspace bind mount (separate issue — the compose file's volume spec evaluates relative paths at first run only), breaking the next build with `file not found`. | Memory pressure is bounded by the recipe (Phase A only for sanitizer modes), not by container lifecycle tricks. Don't restart the container to "reset memory" — diagnose the recipe instead. |

## Results & Parameters

### Verified justfile snippet (full)

The pattern shipped in [ProjectOdyssey PR #5389](https://github.com/HomericIntelligence/ProjectOdyssey/pull/5389)
— this is the load-bearing structure. The case-statement short-circuit at the end
of Phase A is what prevents OOM:

```just
[private]
_build-inner mode="debug":
    #!/usr/bin/env bash
    set -euo pipefail
    MODE="{{mode}}"
    STRICT="--max-notes 0"
    JOBS=""

    case "$MODE" in
        debug)   FLAGS="-g $STRICT" ;;
        release) FLAGS="-O3 $STRICT" ;;
        asan)    FLAGS="-g1 --sanitize address $STRICT" ;;
        tsan)    FLAGS="-g1 --sanitize thread  $STRICT" ; JOBS="-j1" ;;
        *) echo "unknown mode: $MODE" >&2; exit 2 ;;
    esac

    # Phase A: shared library package — runs for every mode
    pixi run mojo package $STRICT -I "$REPO_ROOT" shared \
        -o ".build/$MODE/shared.mojopkg"

    # Phase B: sanitizer modes stop after Phase A (load-bearing short-circuit)
    if [ "$MODE" = "asan" ] || [ "$MODE" = "tsan" ]; then
        echo "✅ Sanitizer build complete (shared package only)"
        echo "  Run sanitized tests: just test-mojo-${MODE}"
        exit 0
    fi

    # debug / release modes continue with per-binary AOT compile here
    # for f in examples/*/main.mojo benchmarks/*/main.mojo; do
    #     pixi run mojo build $FLAGS $JOBS -I shared "$f" -o ".build/$MODE/$(basename $(dirname $f))"
    # done
```

### Environment-variable caveat

| Setting | Effect | Recommendation |
| --- | --- | --- |
| `ODYSSEY_MEM_LIMIT=24g` (on 15 GiB-RAM host) | cgroups still caps at physical RAM; OOM kills still occur, just later. | Set it equal to physical RAM at most. Don't use it to "grow" memory. |
| `JOBS="-j1"` for TSAN | Fixes `modular/modular#6413` parallel-JIT crashes during TSAN compile. | **Required** for TSAN compile to succeed. Does not fix runtime tcmalloc abort. |
| `ASAN_OPTIONS=halt_on_error=0:abort_on_error=0:detect_leaks=1` | Collect all ASAN reports per test run (don't stop at first error). | Use this for `just test-mojo-asan`. |

### Expected outputs

**ASAN sweep success criterion** (PR #5389 observed):

```text
✅ 298 tests passed under ASAN
⚠️  46 leaks reported in shared/  (real leaks — file as separate issues)
```

**TSAN sweep current behavior** (PR #5389 observed):

```text
❌ 298 binaries aborted at startup with:
    FATAL: ThreadSanitizer: unexpected memory mapping ...
    Aborted (core dumped)
```

This is the *expected* TSAN behavior in Mojo 1.0 today; do not interpret it as
a recipe bug. Once Modular ships a tcmalloc fix, the same recipe should produce
real TSAN reports without changes.

### Cross-references

- `mojo-sanitizer-support-matrix` — which `--sanitize=X` flags the compiler/linker
  accepts, and the broader sanitizer support matrix.
- `mojo-jit-crash-retry` — context for the `-j1` workaround and
  `modular/modular#6413`.
- `tcmalloc/arena.cc`, `tcmalloc/internal/system_allocator.h:585` — upstream
  source lines referenced in the abort trace.

## Verified On

| Project | Context | Details |
| --- | --- | --- |
| ProjectOdyssey | PR #5389 — Mojo 1.0 sanitizer build system | ASAN sweep ran 298/298 tests and surfaced 46 real leaks in `shared/`. TSAN sweep compiled 298/298 binaries (with `-j1`) and every binary aborted at startup with the tcmalloc/ThreadSanitizer shadow-memory error. Recipe is correct; TSAN runtime requires Modular-side fix. |
