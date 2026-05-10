---
name: mojo-sanitizer-support-matrix
description: "Use when: (1) running `mojo build --sanitize=thread` and hitting `'DW.ref.__gcc_personality_v0' is already defined` linker error, (2) trying `--sanitize=memory` or `--sanitize=undefined` and getting `invalid sanitizer 'X', expected one of: 'address' or 'thread'`, (3) deciding which sanitizer to use to escalate a non-deterministic Mojo runtime crash, (4) interpreting a clean ASAN run alongside a persistent libKGEN crash, (5) writing an upstream issue and wondering whether to attach TSAN/MSAN/UBSAN evidence (don't — they don't run in 1.0.0b2), (6) filing or referencing modular/modular#6512 (TSan personality-symbol duplicate definition)."
category: debugging
date: 2026-05-09
version: "1.0.0"
user-invocable: false
verification: verified-local
tags:
  - mojo
  - sanitizer
  - asan
  - tsan
  - msan
  - ubsan
  - debugging
  - mojo-1-0
  - upstream-issue
---

# Mojo 1.0.0b2 Sanitizer Support Matrix

## Overview

| Field | Value |
| --- | --- |
| **Date** | 2026-05-09 |
| **Objective** | Document the actual sanitizer support state of `mojo build --sanitize=<X>` in Mojo 1.0.0b2: which flags work, which fail at link time, which are explicitly rejected. Set realistic expectations for sanitizer-based escalation of runtime crashes. |
| **Outcome** | Verified locally on Mojo 1.0.0b2: only `--sanitize=address` produces a runnable binary. `--sanitize=thread` fails at link time. `--sanitize=memory` and `--sanitize=undefined` are rejected by the compiler before linking. Filed as `modular/modular#6512`. |
| **Verification** | verified-local |

## When to Use

- You're escalating a non-deterministic Mojo crash and the `mojo-jit-crash-retry` skill
  recommends "dispatch sanitizer agents (ASAN; TSAN+MSAN+UBSAN)" — this skill tells you
  which of those will actually run
- `mojo build --sanitize=thread` fails with
  `ld.lld: error: duplicate symbol: DW.ref.__gcc_personality_v0`
- `mojo build --sanitize=memory` or `--sanitize=undefined` fails with
  `error: invalid sanitizer 'memory', expected one of: 'address' or 'thread'`
- You're filing an upstream issue and need to know what sanitizer evidence is achievable

## Verified Workflow

### Quick Reference

```bash
# WORKS — produces a runnable ASAN-instrumented binary
pixi run mojo build --sanitize=address -g -I "$(pwd)" -I . -o /tmp/repro <file.mojo>
ASAN_OPTIONS=halt_on_error=0:abort_on_error=0 /tmp/repro

# FAILS at link time (modular/modular#6512)
pixi run mojo build --sanitize=thread -g -I "$(pwd)" -I . -o /tmp/repro <file.mojo>
# ld.lld: error: duplicate symbol: DW.ref.__gcc_personality_v0

# REJECTED by compiler before linking
pixi run mojo build --sanitize=memory    ...   # invalid sanitizer 'memory'
pixi run mojo build --sanitize=undefined ...   # invalid sanitizer 'undefined'
```

### Support Matrix (Mojo 1.0.0b2)

| Flag | Compiler accepts? | Links? | Runs? | Notes |
| --- | --- | --- | --- | --- |
| `--sanitize=address` | YES | YES | YES | Catches user-code heap/stack UB. **Does NOT instrument `libKGEN*` / `libAsync*` / `libMSupport*`** (statically linked, pre-built; no source-level instrumentation possible). Clean ASAN + persistent crash = bug is in Mojo runtime. |
| `--sanitize=thread` | YES | NO | — | Linker error: `duplicate symbol: DW.ref.__gcc_personality_v0`. Filed upstream as `modular/modular#6512`. The personality symbol is defined both by Mojo's own runtime and by libtsan; lld refuses to merge. No workaround in user code. |
| `--sanitize=memory` | NO | — | — | Compiler rejects: `invalid sanitizer 'memory', expected one of: 'address' or 'thread'`. MSAN is not supported in 1.0.0b2 at all. |
| `--sanitize=undefined` | NO | — | — | Compiler rejects: `invalid sanitizer 'undefined', expected one of: 'address' or 'thread'`. UBSan is not supported in 1.0.0b2 at all. |

### Implications for crash investigation

#### 1. ASAN is the only currently-available sanitizer

If the `mojo-jit-crash-retry` 4-hypothesis disproof produced 0 local repros and the
recommended next step is "dispatch sanitizer agents", you can dispatch **only the ASAN
agent**. The TSAN/MSAN/UBSAN agents will fail to produce a binary in Mojo 1.0.0b2.

#### 2. A clean ASAN run does NOT clear Mojo

ASAN instruments **user code** — your `.mojo` source compiled by `mojo build`. It does
**not** instrument the pre-built shared libraries (`libKGENCompilerRTShared.so`,
`libAsyncRTMojoBindings.so`, `libMSupport.so`, etc.) because those are statically
shipped and not rebuilt with `-fsanitize=address`.

```text
User code (your .mojo files) ────[--sanitize=address rebuilds]──→ ASAN-instrumented
libKGEN*, libAsync*, libMSupport* ──[shipped pre-built, NOT rebuilt]──→ NOT instrumented
```

**Decision rule:**

```text
If user code looks ASAN-clean but the libKGEN crash persists:
  → The bug is in libKGEN* itself (statically linked, not ASAN-instrumented).
  → Stop looking at user code; file upstream with the dynsym fingerprint.
```

#### 3. Don't promise sanitizer evidence you can't deliver

When writing an upstream issue or a "Mojo bug, here's our investigation" report, list
the sanitizers you actually ran. Do not list TSAN/MSAN/UBSAN as "ran clean" if you
never built a sanitizer binary — `mojo build` rejected those flags.

### Repro of the TSan link error (for filing/referencing modular/modular#6512)

```bash
cat > /tmp/tsan_repro.mojo <<'EOF'
def main():
    print("hello")
EOF

pixi run mojo build --sanitize=thread -g -o /tmp/tsan_repro /tmp/tsan_repro.mojo 2>&1 | head -5
# Expected output:
# ld.lld: error: duplicate symbol: DW.ref.__gcc_personality_v0
# >>> defined at <...>/libMSupport.so
# >>> defined at <...>/libtsan.a(...)
```

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
| --- | --- | --- | --- |
| Dispatch a TSAN sanitizer agent for race-condition hypothesis | Sub-agent ran `mojo build --sanitize=thread -g -o /tmp/repro <file>` | Linker error: `duplicate symbol: DW.ref.__gcc_personality_v0` between libMSupport.so and libtsan.a; agent could not produce a runnable binary | TSAN is currently broken in Mojo 1.0.0b2 (filed `modular/modular#6512`); do not include it in escalation playbooks until upstream fixes it |
| Run `--sanitize=memory` to chase uninitialized-memory hypothesis | `pixi run mojo build --sanitize=memory ...` | Compiler rejected with `invalid sanitizer 'memory', expected one of: 'address' or 'thread'` | MSAN is not implemented in Mojo 1.0.0b2; remove from any escalation matrix |
| Run `--sanitize=undefined` to chase signed-overflow / null-deref / alignment hypotheses | `pixi run mojo build --sanitize=undefined ...` | Compiler rejected with `invalid sanitizer 'undefined', expected one of: 'address' or 'thread'` | UBSan is not implemented in Mojo 1.0.0b2; remove from any escalation matrix |
| Conclude "Mojo runtime is fine" from a clean ASAN run | After ASAN reported 0 errors on user code, considered closing the investigation | ASAN does not instrument the pre-built `libKGEN*`/`libAsync*`/`libMSupport*` shared libs; those are shipped statically pre-built and not rebuilt with `-fsanitize=address`. A clean user-code ASAN run does not clear runtime-internal bugs | Clean ASAN + persistent libKGEN crash = bug is in Mojo runtime itself; escalate upstream |
| Pass ASAN_OPTIONS to halt at first error | `ASAN_OPTIONS=halt_on_error=1` for fast-fail | Default ASAN halt-on-error mode masks how many distinct issues exist | Use `halt_on_error=0:abort_on_error=0` to collect ALL ASAN reports per run, then triage |

## Results & Parameters

### Recommended ASAN invocation

```bash
pixi run mojo build --sanitize=address -g -I "$(pwd)" -I . -o /tmp/repro <file.mojo>

ASAN_OPTIONS=halt_on_error=0:abort_on_error=0:detect_leaks=1:symbolize=1 \
  /tmp/repro 2>&1 | tee /tmp/asan_report.log
```

### Updated escalation matrix (replaces v4.0.0 sanitizer recommendation in `mojo-jit-crash-retry`)

| Sanitizer | 1.0.0b2 status | Use it? | Notes |
| --- | --- | --- | --- |
| ASAN | works | YES | Only sanitizer that produces a runnable binary; instruments user code only |
| TSAN | linker error | NO (until #6512) | Reference `modular/modular#6512` in upstream issues |
| MSAN | compiler rejects | NO | Not implemented in 1.0.0b2 |
| UBSAN | compiler rejects | NO | Not implemented in 1.0.0b2 |

### Companion skills

- `mojo-jit-crash-retry` v4.1.0+: parallel-hypothesis disproof methodology and dynsym/objdump
  forensic procedure (the reason this support matrix matters)
- `mojo-binary-closed-source-debugging`: why ASAN cannot reach `libKGEN*` (closed-source,
  shipped pre-built)
- `gha-mojo-coredump-capture`: alternative escalation when sanitizers don't apply

## Verified On

| Project | Context | Details |
| --- | --- | --- |
| ProjectOdyssey | PR #5364 — Mojo 1.0.0b2 KGEN crash sanitizer escalation | Confirmed: ASAN works; TSAN linker error; MSAN/UBSAN rejected. Filed `modular/modular#6512` for the TSAN personality-symbol duplicate-definition issue. |
