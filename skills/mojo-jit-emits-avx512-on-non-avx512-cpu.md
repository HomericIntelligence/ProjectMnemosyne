---
name: mojo-jit-emits-avx512-on-non-avx512-cpu
description: "Root cause of modular/modular#6413: Mojo 1.0.0b2.dev2026050805 JIT emits AVX-512 instructions (zmm registers, opmasks, {1to4} broadcast, vpternlogd, vpbroadcastb r→xmm) on Azure GHA runners whose CPU does NOT support AVX-512 — SIGILL at runtime. Bug is RUNTIME-CPU-dependent, not source-code-dependent: the same mojo conda artifact runs cleanly on a Lunar Lake laptop and crashes on Skylake-class Azure VMs. Use when: (1) triaging Mojo SIGILL on GHA, (2) a 'rebased and now it works' Mojo story needs to be checked for GHA-cache-eviction luck vs real fix, (3) file-content bisects of Mojo crashes come back all-green and you need to switch to a CPU-feature hypothesis, (4) capturing disassembly evidence from ELF cores to prove AVX-512 emission, (5) comparing crash reproducibility across Intel CPU generations (Skylake/Cascade Lake vs Lunar Lake), (6) reasoning about Mojo runtime CPU detection (CPUID consult, $HOME/.modular cache, default-to-generic-target fallback)."
category: debugging
date: 2026-05-12
version: "1.0.0"
user-invocable: false
verification: verified-ci
tags:
  - mojo
  - jit
  - avx-512
  - avx512
  - sigill
  - libKGEN
  - modular-6413
  - cpu-detection
  - azure-runner
  - gha
  - runtime-codegen
---

# Mojo JIT Emits AVX-512 on Non-AVX-512 CPUs (modular/modular#6413 root cause)

## Overview

| Field | Value |
| --- | --- |
| **Date** | 2026-05-12 |
| **Objective** | Document the surviving root-cause hypothesis for modular/modular#6413: Mojo 1.0.0b2.dev2026050805 emits AVX-512 instructions at JIT codegen time on Azure GHA runners whose host CPU does NOT advertise AVX-512, producing SIGILL via undefined-opcode decoding. The bug is gated on runtime CPU, not on source code. |
| **Outcome** | 12+ symbolicated ELF cores across 4 distinct backtraces, all firing AVX-512 family instructions. 5-PR experimental bisect ruled out every file-content variable (32 green negative-control outcomes, P ≈ 2e-29 by chance). Reproduces ~80% of the time on Azure GHA runners; 0/50 on Lunar Lake laptop with the same `mojo` binary. |
| **Verification** | verified-ci (PR #5399 on ProjectOdyssey + 4 negative-control PRs) |
| **Companion skills** | `mojo-runtime-crash-bisection` (general bisection methodology), `debugging-mojo-jit-crash-capture-gdb-wrapper` (gdb-wrapper that produced these cores), `modular-6433-vs-6413-failure-triage` (signature-based job classification) |

## When to Use

- Investigating a Mojo SIGILL crash on GitHub-Actions-hosted CI where ELF cores show
  AVX-512 mnemonics (`zmm0`, `{1to4}`, `vpternlogd`, `vcmpltss → %k1`, `vmovdqa64`,
  `vpbroadcastb r,xmm`) in the faulting frame
- A previous file-content bisect produced 8/8 green on every reverted suspect PR yet
  main remains red — you need to switch to a runtime-CPU hypothesis
- A teammate says "I rebased and now it works" for a Mojo JIT crash on GHA — verify
  via GHA cache key comparison whether the rebuild evicted a poisoned image cache,
  rather than treating the rebase as a real fix
- Comparing crash reproducibility across Intel CPU generations (Lunar Lake vs older
  Skylake-class Azure VMs) to confirm CPU-dependent codegen
- Filing or commenting on modular/modular#6413 with disassembly evidence
- Deciding whether to invest in a file-content bisect at all — if the crash signature
  is AVX-512 on Azure, file-content bisects are doomed; investigate the JIT codegen
  path instead

## Verified Workflow

### Quick Reference

```bash
# 1. Pull cores out of CI (relies on gha-mojo-coredump-capture infra)
gh run download <RUN_ID> -R HomericIntelligence/ProjectOdyssey -n coredump-capture

# 2. Symbolicate via gdb (must use SAME mojo binary version as CI)
gdb -batch \
  -ex "set confirm off" \
  -ex "core-file core.<pid>" \
  -ex "bt" \
  -ex "x/8i \$rip-32" \
  -ex "info all-registers" \
  /path/to/mojo

# 3. Check for AVX-512 mnemonics in disassembly
gdb-output | grep -E 'zmm[0-9]|\{1to[248]\}|vpternlog|vcmpltss.*%k[0-7]|vmovdqa64|vmovdqu64|vpbroadcastb +%[er].*xmm'

# 4. Confirm runner CPU lacks AVX-512
gh run view <RUN_ID> --log | grep -E "flags.*:" | grep -oE "avx512[a-z0-9]+|avx_vnni|sha_ni|vaes" || echo "no AVX-512 features advertised"

# 5. Local reproducer (recipe from modular#6413 comment-4436157861)
git clone https://github.com/HomericIntelligence/ProjectOdyssey
cd ProjectOdyssey && git checkout 1d294a7f
podman compose build projectodyssey-dev
podman run --rm -v "$(pwd):/workspace:Z" -w /workspace \
  --ulimit core=-1 projectodyssey:dev \
  bash -c 'pixi run mojo run -I /workspace repro/repro_6413_assert_almost_equal.mojo'
# Expect ~80% SIGILL on Azure-class CPU lacking AVX-512 + AVX-VNNI/SHA-NI/VAES; clean on Lunar Lake.
```

### Detailed Steps

1. **Confirm signature first.** Don't start a file-content bisect on a Mojo SIGILL
   without first inspecting the faulting instruction. Use the gdb wrapper from
   `debugging-mojo-jit-crash-capture-gdb-wrapper` to capture real ELF cores. Without
   that wrapper, libKGEN's in-process signal handler eats the signal and you get
   3-frame Crashpad noise.

2. **Disassemble around `$rip`.** `x/8i $rip-32` plus `x/8i $rip` shows the
   instruction stream. Look for AVX-512 markers:
   - 512-bit registers: `%zmm0`–`%zmm31`
   - Opmask registers: `%k1`–`%k7`, e.g. `vcmpltss ... %xmm0, %k1`
   - Masked moves with zeroing: `vmovss ... %xmm1{%k1}{z}`
   - Embedded broadcast: `{1to4}`, `{1to8}`, `{1to16}`
   - Ternary logic: `vpternlogd $imm, ...`
   - Unaligned 512-bit memory ops: `vmovdqu64 ..., %zmm0`
   - Reg-source byte broadcast (AVX-512BW): `vpbroadcastb %eax, %xmm0`
     (the GP-register-source form is AVX-512-only; memory-source form is AVX2)

3. **Confirm CPU absence of AVX-512.** `info all-registers` on the core MUST show
   only `xmm`/`ymm` and zero `zmm`/`k0..k7` entries. Cross-check
   `/proc/cpuinfo` flags in the CI job log: no `avx512*` flags. On Azure
   Skylake-class runners, also note the absence of `avx_vnni`, `sha_ni`, `vaes` —
   these are the discriminator vs Lunar Lake (which also lacks AVX-512 but has those
   newer ISA extensions and does not reproduce the bug).

4. **Negative-control file-content bisect (one-shot, then stop).** Run ONE PR that
   reverts the most suspicious file-level commit and rerun CI 8 times with the
   crash-prone job. If all 8 are green AND the signature stays AVX-512 on main,
   stop bisecting file contents — the bug is in JIT codegen, not in the source.
   At 87% historical crash rate, P(8/8 green by chance) ≈ 2.3e-7.

5. **Image-cache poisoning check.** Before declaring a "rebase fixed it" story
   real, compare `gh actions-cache list` entries before/after. The bad cache key
   in this investigation was
   `container-image-uid1001-ab0290811d2e7f7979c17d7c115fa41c6cce25bed01fcf8e329ed32a7f9a9ed8`
   (good was `…8f28e14581a46d4510c3beb68e9df14a277b4656024648…`). The bad image
   tarball had sha256 `a5889cb07ca73da27db730b4754de08094e604161fb63af464a70b148765bab7`
   and was 2.71 GB uncompressed. Loading it on a Lunar Lake laptop reproduces a
   clean run — proving the bytes are not the bug, the CPU is.

6. **Reproduce locally.** Use the recipe in `Quick Reference` step 5. If you do
   NOT have an Azure-class Skylake/Cascade-Lake runner handy, file the issue
   upstream with the GHA run logs + cores — Modular has the matching hardware.

7. **Hand off.** Comment on modular/modular#6413 with disassembly snippets and
   point to this skill. The fix belongs in Mojo's runtime CPUID detection
   routine. Do not attempt to work around it in the user codebase.

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
| --- | --- | --- | --- |
| File-content bisect via single-commit reverts | Reverted #5381 (workflow fan-out), #5385 (`\|\| true` removal), #5387 (`::warning::` removal), #5388 (test alias), #5389 (justfile rewrite); ran CI 8× each | All 32 negative-control outcomes were green; main stayed red. P(by chance @ 87% historical crash rate) ≈ 2e-29 | When the bisect anomaly is a GHA cache-key flip rather than a source change, file-content reverts can't reproduce. Switch to a runtime-CPU / codegen hypothesis. |
| Manual cache eviction expecting deterministic rebuild | `gh actions-cache delete <bad-key> -R …` then re-ran the workflow expecting the new image to be bug-free | New image rebuilt with same hash family and same crash signature — the rebuild is just sometimes lucky (~13% pass rate). The "bug" is not stored in cache bytes. | Cache eviction is not a fix. The image tarball loaded on a Lunar Lake laptop runs cleanly with the same bytes — confirming the trigger is the CPU, not the image. |
| "Build host had AVX-512, runtime didn't" hypothesis | Assumed CI image was built on a newer CPU and pinned codegen to AVX-512, then deployed to an older runner | Both build host and test host are GHA `ubuntu-latest` Azure VMs without AVX-512. The Lunar Lake laptop also lacks AVX-512 but does NOT reproduce. | Not a simple build-vs-runtime CPU mismatch. The discriminator is likely AVX-VNNI / SHA-NI / VAES presence (Lunar Lake has them; older Azure VMs don't), or a CPUID misread that triggers an AVX-512 default. |
| Treat a "rebased and now it works" report as a real fix | Read another Mojo project's commit log claiming a JIT crash was fixed by rebasing on main | The "fix" was almost certainly GHA cache eviction at the org/repo cache boundary — same pattern we observed here. Subsequent runs on the same code re-flake. | Treat "rebased and fixed" Mojo JIT stories as cache-eviction luck until proven otherwise via cache-key diff + disassembly. |
| Single-iteration CI confirmation | Ran the suspect PR once green, declared "fixed" | At 13% historical pass rate on a buggy main, single-shot green is meaningless. Need ≥8 iterations to get P(false-positive) below 0.0000005. | Always use the 8-run protocol for Mojo JIT crash verification. One green run on a flaky-by-CPU bug means nothing. |

## Results & Parameters

### Pinned versions

| Artifact | Identifier |
| --- | --- |
| Mojo conda artifact | `mojo-1.0.0b2.dev2026050805-release.conda` |
| Mojo binary sha256 | `8b6f080d54b7c53185786a9a928afbfcf2fbb539d89c9d44da3b5b6700a8b6dc` |
| Bad container image sha256 | `a5889cb07ca73da27db730b4754de08094e604161fb63af464a70b148765bab7` |
| Bad image GHA cache key | `container-image-uid1001-ab0290811d2e7f7979c17d7c115fa41c6cce25bed01fcf8e329ed32a7f9a9ed8` |
| Good image GHA cache key | `container-image-uid1001-8f28e14581a46d4510c3beb68e9df14a277b4656024648…` |
| Reference Azure runner kernel | `6.17.0-1010-azure` (hostname `runnervmeorf1`) |

### Faulting instructions captured (4 distinct backtraces, 6 instruction families)

| Backtrace | Frame | Instruction | AVX-512 feature |
| --- | --- | --- | --- |
| A (`test_tensor_dataset_negative_indexing`) | `abs() math.mojo:3746` → `assert_almost_equal+48` | `vandps (%r15,%rax,1){1to4},%xmm3,%xmm3` | AVX-512F `{1to4}` embedded broadcast |
| B (`test_substitute_simple_env_var`) | `_strip() string_slice.mojo:1035` (`_strip+68`) | `vmovdqa64 (%rcx,%rax,1),%zmm0` | 512-bit register, AVX-512F only |
| B' (`_is_valid_utf8_runtime() _utf8.mojo:173`) | `load_config+2857` | `vmovdqu64 (%r12,%rax,1),%zmm0` ; `vmovdqu64 %zmm0,0x1e0(%rsp)` | Unaligned 512-bit load/store |
| C1 (`test_dropout_forward_*`, `test_linear_struct_initialization`) | `philox._single_round philox.mojo:162` → `next_uint32+178` | `vpternlogd $0x96,%xmm3,%xmm4,%xmm7` | AVX-512F ternary logic |
| C2 (`test_relu_backward_basic`) | `_relu_backward_op activation.mojo:475` → `dispatch_binary+3024` | `vcmpltss (%r10,%rdi,4),%xmm0,%k1` ; `vmovss (%rsi,%rdi,4),%xmm1{%k1}{z}` | AVX-512F opmask `%k1` + masked move with zeroing |
| D (`match_h2` in swisstable) | `_swisstable.mojo:114` → `_insert+4476` | `vpbroadcastb %eax,%xmm0` | AVX-512BW reg-source byte broadcast |

### Crash rate measurements

| Host | Crash rate | Sample size |
| --- | --- | --- |
| Azure GHA Skylake-class runner (kernel `6.17.0-1010-azure`) | ~80% per CI dispatch (per-job basis) | 14 dispatches |
| Lunar Lake laptop (no AVX-512, has AVX-VNNI/SHA-NI/VAES) | 0% | 50 iterations |

### Negative-control bisect outcomes

| Reverted PR | Hypothesis | CI runs | Outcome |
| --- | --- | --- | --- |
| #5381 | Workflow fan-out matrix triggers crash | 8 | 8/8 green |
| #5385 | `\|\| true` workaround removal triggers crash | 8 | 8/8 green |
| #5387 | `::warning::` removal triggers crash | 8 | 8/8 green |
| #5388 | Test alias triggers crash | 8 | 8/8 green |
| #5389 | Justfile rewrite + workflow timeout triggers crash | 8 | 8/8 green |

P(all 32 green by chance at historical 87% crash rate) ≈ 2.3e-29 — file contents
are decisively NOT the cause.

### Surviving hypothesis (handed off to Modular)

Mojo's runtime CPU detection emits AVX-512 codegen on Azure runners with older
Skylake/Cascade Lake-class CPUs that lack AVX-512. Three sub-hypotheses, any of
which would explain the data:

1. Detection consults CPUID directly and misreads a feature bit
2. Mojo defaults to a generic AVX-512-capable target when it can't confidently
   classify the host
3. The detection routine writes to `$HOME/.modular` on first install and the
   value gets cached incorrectly (would explain CPU-dependent reproducibility:
   the cache was populated on a different-class CPU than where it's read)

### Upstream references

- Issue: [modular/modular#6413](https://github.com/modular/modular/issues/6413)
- Initial findings comment: [#6413 c-4435784092](https://github.com/modular/modular/issues/6413#issuecomment-4435784092)
- Cache content drift hypothesis: [#6413 c-4435794613](https://github.com/modular/modular/issues/6413#issuecomment-4435794613)
- Local reproducer recipe: [#6413 c-4436157861](https://github.com/modular/modular/issues/6413#issuecomment-4436157861)

## Verified On

| Project | Context | Details |
| --- | --- | --- |
| ProjectOdyssey | PR #5399 (bisect/6413-positive-control) | 12+ symbolicated ELF cores, 4 distinct backtraces all firing AVX-512 instructions |
| ProjectOdyssey | PRs #5395, #5396, #5397, #5398 (negative-control reverts) | 32 green job outcomes; file-content variables ruled out |
| Local | Lunar Lake laptop loading bad cached image (`a5889cb…`) | 0/50 crash; same binary as CI, different CPU — confirms CPU-gated bug |
| Upstream | modular/modular#6413 (HomericIntelligence comments 4435784092 / 4435794613 / 4436157861) | Disassembly evidence, cache-content-drift analysis, podman-based local reproducer recipe |
