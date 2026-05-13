---
name: mojo-print-effective-target-codegen-diagnostic
description: "First-line no-compile diagnostic for 'wrong instructions emitted on this host' Mojo reports: `mojo build --print-effective-target <some.mojo>` prints the driver-resolved `--target-cpu` and `--target-features` list without actually compiling the program. Run on each suspect host and diff. The Mojo driver populates the `!kgen.target` MLIR attribute from `llvm::sys::getHostCPUFeatures()`; that attribute drives every `target_has_feature[\"...\"]` query in stdlib (e.g. `has_avx512f`). If the driver fingerprints the CPU and applies a static AVX-512 feature list but the kernel/hypervisor doesn't expose AVX-512, codegen will emit AVX-512 ops that SIGILL at runtime. Use when: (1) triaging a Mojo SIGILL where you suspect the JIT picked the wrong ISA, (2) pre-flighting a Mojo binary across a mixed-CPU fleet, (3) differentiating 'wrong CPU name picked' from 'right CPU name, wrong static feature table', (4) gathering evidence before opening a modular/modular CPU-detection bug."
category: debugging
date: 2026-05-12
version: "1.0.0"
user-invocable: false
verification: verified-local
tags:
  - mojo
  - target-cpu
  - target-features
  - print-effective-target
  - codegen
  - host-fingerprinting
  - cpu-detection
  - avx-512
  - sigill
  - modular-6413
  - diagnostic
---

# Mojo `--print-effective-target`: No-Compile Codegen-Target Diagnostic

## Overview

| Field | Value |
| --- | --- |
| **Date** | 2026-05-12 |
| **Objective** | Document `mojo build --print-effective-target <some.mojo>` as the first diagnostic to run when investigating "Mojo emitted wrong instructions on this host" reports. The flag prints the driver-resolved `--target-cpu` + `--target-features` list **without compiling** the program, so it's safe to run on hosts where actually executing the binary would SIGILL. |
| **Outcome** | Verified output captured on two distinct Intel hosts (Lunar Lake Core Ultra 7 258V and Skylake i5-6600K) — both correctly resolve to non-AVX-512 feature sets. A GHA Azure-runner capture is pending PR #5401 merge; if that runner resolves to `znver4`/`sapphirerapids` with `+avx512f` while `/proc/cpuinfo` lists no `avx512f`, the discrepancy is the root cause of modular/modular#6413. |
| **Verification** | verified-local (hermes Lunar Lake + epimetheus Skylake) |
| **Companion skills** | `mojo-jit-emits-avx512-on-non-avx512-cpu` (modular/modular#6413, the specific bug class this diagnostic reveals), `cross-cpu-survey-gha-only-crash` (multi-host survey methodology) |

## When to Use

- Investigating any "wrong instruction emitted" / "SIGILL on this host but works on
  others" Mojo report — run this before any other diagnostic
- Validating CPU-feature-detection assumptions before opening an upstream
  modular/modular issue (so the report includes driver-resolved evidence, not just
  `/proc/cpuinfo`)
- Differentiating "driver picked the wrong CPU name" from "driver knows the right CPU
  but applied the wrong static feature table"
- Pre-flight check before deploying a Mojo binary to a fleet of mixed-CPU hosts: if
  the build-time effective target includes ISA extensions the deployment hosts lack,
  the binary will SIGILL on those hosts
- Confirming whether a "rebased and now it works" Mojo JIT story actually changed
  the resolved target on the affected runner, or whether it was just GHA cache
  eviction luck (compare effective target captures before/after)

## Verified Workflow

### Quick Reference

```bash
# 1. Confirm the flag exists and prints driver-resolved target without compiling
podman run --rm -v "$(pwd):/workspace:Z" -w /workspace projectodyssey:dev \
  bash -c 'pixi run mojo build --print-effective-target /workspace/REPRO.mojo'

# 2. Run on each suspect machine and diff
for host in machine1 machine2 GHA_runner; do
  echo "=== $host ==="
  <invocation-per-host> mojo build --print-effective-target REPRO.mojo
done

# 3. Look for divergences in:
#    a. --target-cpu name (e.g. lunarlake vs skylake vs znver4 vs sapphirerapids)
#    b. AVX-512 features (+avx512f, +avx512vl, +avx512bw, +avx512dq, +avx512cd,
#       +avx512vnni, +avx512bf16) — these should be ABSENT on hosts where
#       /proc/cpuinfo doesn't list avx512f
#    c. Other "should-be-present-but-isn't" or "shouldn't-be-but-is" feature flags
#       (e.g. +sha, +vaes, +avxvnni, +amx-*)
```

### Detailed Steps

1. **Pick a representative source file.** Any `.mojo` file that imports the symbols
   you care about will do — the driver only resolves the target, it does not emit
   code for the file. A 1-line `def main() -> None: pass` is sufficient. Save as
   `REPRO.mojo`.

2. **Run on the "good" host first.** This establishes the baseline driver-resolved
   target for a CPU that you know works. Save the output verbatim — the
   `--target-features` list is long (60+ flags) and order is stable across runs on
   the same host, so a textual diff is reliable.

3. **Run on the "bad" host (or each suspect host).** Use the same Mojo version, the
   same source file, and the same invocation path (host vs container vs CI). If the
   bad host is a CI runner where you can't get an interactive shell, add a workflow
   step that runs `mojo build --print-effective-target` and uploads the output as an
   artifact.

4. **Diff the two outputs.** Three categories of divergence matter:
   - **`--target-cpu` differs** → the driver fingerprinted the CPUs differently. If
     one names a CPU family that historically has AVX-512 in its static table
     (`znver4`, `sapphirerapids`, `icelake-server`, `skylake-avx512`) and the other
     names one that doesn't (`skylake`, `lunarlake`, `znver3`-without-AVX-512), the
     AVX-512-named host is the likely SIGILL victim.
   - **`--target-features` adds `+avx512*` on the bad host** → the driver applied a
     static feature table that includes AVX-512 ops the silicon (or hypervisor mask)
     doesn't support. This is the modular/modular#6413 bug class.
   - **`--target-features` order differs but content matches** → not a bug; orderings
     can shift between Mojo versions.

5. **Cross-check against `/proc/cpuinfo`.** On the host whose effective target
   includes `+avx512f`, run `grep -o 'avx512[a-z0-9]*' /proc/cpuinfo | sort -u`. If
   that grep is empty but the effective target says `+avx512f`, you have a confirmed
   driver-vs-silicon mismatch — the codegen path will emit instructions the runtime
   CPU can't decode.

6. **Capture the evidence for upstream.** Paste both effective-target outputs +
   `/proc/cpuinfo` extracts into the modular/modular issue. This is the minimal
   reproducible evidence: it's textual, deterministic, and doesn't require running
   any user code.

### Diagnostic interpretation table

| `--target-cpu` | `--target-features` includes `+avx512f`? | Kernel `/proc/cpuinfo` has `avx512f`? | Verdict |
| --- | --- | --- | --- |
| `lunarlake` / `skylake` / `haswell` | No | No | Consistent — driver correctly avoided AVX-512 |
| `znver4` / `sapphirerapids` / `icelake-server` | Yes | Yes | Consistent — silicon advertises and uses AVX-512 |
| `znver4` / `sapphirerapids` | **Yes** | **No** | **BUG: driver fingerprinted the CPU and applied a static AVX-512 feature list, but the kernel/hypervisor doesn't expose AVX-512. Codegen will SIGILL.** |
| `znver3` / `skylake-avx512` etc. | mixed | check both | Investigate per-feature; the static table for the named CPU is the source of truth for what the driver "knows" about that chip |

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
| --- | --- | --- | --- |
| `mojo run --print-effective-target` | Tried the flag on the `run` subcommand to investigate a `mojo run` SIGILL | The flag is documented under `mojo build`, not `mojo run` | Use the `build` invocation even when investigating a `mojo run` crash — the driver-resolved target is the same path |
| `mojo --version` to compare hosts | Hoped version output would include per-host CPU info | `--version` only prints the Mojo version string; no per-host fingerprint | Need `--print-effective-target` against an actual source file (or `--print-supported-targets` / `--print-supported-cpus` for the static tables) |
| Read `__mlir_attr.target_has_feature` from inside Mojo | Wrote a small Mojo program that introspects the target attribute and prints features | Works but requires running code on the suspect host, which defeats the "no-compile diagnostic" goal — on a SIGILL-prone host the introspection program may itself crash | For inspection-only on hostile hosts, use `--print-effective-target`; save the runtime-introspection trick for later evidence-gathering on a known-good host |
| `MOJO_TARGET_FEATURES` env var override | Hoped an env var would let us mask off `+avx512f` without rebuilding | Not documented in Mojo 1.0.0b2; no propagation to in-process JIT confirmed | Only `--target-features="-feat,..."` on the `mojo build` CLI is supported; in-process JIT override is unconfirmed and shouldn't be assumed |

## Results & Parameters

### Pinned versions

| Artifact | Identifier |
| --- | --- |
| Mojo version under test | `1.0.0b2.dev2026050805` (from `projectodyssey:dev` container) |
| Container image | `projectodyssey:dev` |
| Source file used | 1-line `def main() -> None: pass` saved as `REPRO.mojo` |
| Invocation pattern | `pixi run mojo build --print-effective-target /workspace/REPRO.mojo` inside the container |

### Captured effective-target outputs

#### hermes (Intel Core Ultra 7 258V — Lunar Lake, no AVX-512 silicon)

```text
Effective target configuration:
  --target-triple x86_64-unknown-linux-gnu
  --target-cpu lunarlake
  --target-features +adx,+aes,+avx,+avx2,+avxifma,+avxneconvert,+avxvnni,
                    +avxvnniint16,+avxvnniint8,+bmi,+bmi2,+clflushopt,+clwb,
                    +cmov,+cmpccxadd,+crc32,+cx16,+cx8,+enqcmd,+f16c,+fma,
                    +fsgsbase,+fxsr,+gfni,+hreset,+invpcid,+kl,+lzcnt,+mmx,
                    +movbe,+movdir64b,+movdiri,+pclmul,+pconfig,+pku,+popcnt,
                    +prfchw,+ptwrite,+rdpid,+rdrnd,+rdseed,+sahf,+serialize,
                    +sgx,+sha,+sha512,+shstk,+sm3,+sm4,+sse,+sse2,+sse3,
                    +sse4.1,+sse4.2,+ssse3,+uintr,+vaes,+vpclmulqdq,+waitpkg,
                    +widekl,+x87,+xsave,+xsavec,+xsaveopt,+xsaves
```

No `+avx512*` flags — consistent with Lunar Lake silicon. Cross-reference: also has
`+avxvnni`, `+sha`, `+vaes` — the Lunar Lake discriminator vs older Intel desktop CPUs.

#### epimetheus (Intel i5-6600K — Skylake desktop, no AVX-512 silicon)

```text
Effective target configuration:
  --target-triple x86_64-unknown-linux-gnu
  --target-cpu skylake
  --target-features +adx,+aes,+avx,+avx2,+bmi,+bmi2,+clflushopt,+cmov,+crc32,
                    +cx16,+cx8,+f16c,+fma,+fsgsbase,+fxsr,+invpcid,+lzcnt,+mmx,
                    +movbe,+pclmul,+popcnt,+prfchw,+rdrnd,+rdseed,+sahf,+sgx,
                    +sse,+sse2,+sse3,+sse4.1,+sse4.2,+ssse3,+x87,+xsave,
                    +xsavec,+xsaveopt,+xsaves
```

No `+avx512*` flags — consistent with Skylake desktop silicon. Also no `+avxvnni`,
`+sha`, `+vaes` — confirming the Lunar Lake discriminator.

#### Predicted: GHA Azure runner (AMD EPYC 9V74 Zen 4 under Hyper-V, AVX-512 masked)

```text
Effective target configuration:
  --target-cpu znver4
  --target-features +avx512f,+avx512vl,+avx512bw,+avx512dq,...
                    (despite /proc/cpuinfo on the runner not listing avx512f)
```

If this prediction holds when PR #5401 lands the GHA capture, it confirms
modular/modular#6413: the driver fingerprints the EPYC as `znver4` and applies the
static `znver4` AVX-512 feature table, ignoring that the Hyper-V layer masks AVX-512
out of CPUID. The runtime then SIGILLs on `vmovdqu64`/`vpternlogd`/`vcmpltss → %k1` /
`{1to4}` broadcast / `vpbroadcastb r,xmm`.

### What the flag does internally

- The Mojo driver calls `llvm::sys::getHostCPUName()` and `llvm::sys::getHostCPUFeatures()`
- Result populates the `!kgen.target` MLIR attribute (closed-source `CLOptions.h:118`)
- That attribute drives every `target_has_feature["..."]` query in stdlib, including
  `has_avx512f`, `has_avx_vnni`, `has_sha`, etc.
- Codegen then specializes intrinsics based on those feature queries
- `--print-effective-target` prints the resolved attribute before invoking the
  compile pipeline, so it's safe to run even when actually compiling/running would
  produce a bad binary

### Upstream references

- Issue: [modular/modular#6413](https://github.com/modular/modular/issues/6413)
- Companion skill: `mojo-jit-emits-avx512-on-non-avx512-cpu` (the bug class this
  diagnostic reveals)
- Companion methodology: `cross-cpu-survey-gha-only-crash` (multi-host survey
  protocol that uses this diagnostic as step 1)

## Verified On

| Project | Context | Details |
| --- | --- | --- |
| ProjectOdyssey | modular/modular#6413 cross-CPU survey | Verified output on hermes (Lunar Lake Core Ultra 7 258V) and epimetheus (Skylake i5-6600K) — both correctly avoid AVX-512 in `--target-features`. Confirms the diagnostic flag works and produces deterministic, diffable output. |
| ProjectOdyssey | PR #5401 (GHA runner capture, pending merge) | Will add the third data point — Azure GHA Skylake/Zen-4-class runner — to confirm whether the driver-resolved target there includes `+avx512f` despite `/proc/cpuinfo` masking. Outcome will either confirm or refute the surviving hypothesis for modular/modular#6413. |
