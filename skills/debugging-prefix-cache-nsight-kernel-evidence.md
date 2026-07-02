---
name: debugging-prefix-cache-nsight-kernel-evidence
description: "Capture and interpret Nsight kernel-name evidence for vLLM or SGLang prefix-cache nondeterminism. Use when: (1) cache hits change output despite temperature=0, (2) warm prefix-cache paths may select different GEMM tiling, (3) you need actual GPU kernel names rather than profiler-free hypotheses, (4) batch-invariant or deterministic kernels are being considered as a replay control instead of a production fix."
category: debugging
date: 2026-07-02
version: "1.0.0"
user-invocable: false
verification: verified-ci
tags:
  - inference
  - vllm
  - sglang
  - prefix-cache
  - nsight
  - nsys
  - ncu
  - h200
  - slurm
  - determinism
---

# Prefix-Cache Nsight Kernel Evidence

## Overview

| Field | Value |
|-------|-------|
| **Date** | 2026-07-02 |
| **Objective** | Prove whether a warm prefix-cache path changes the executed GPU kernel regime by collecting actual Nsight kernel names from matched good and bad H200 Slurm cases. |
| **Outcome** | Successful. The good/no-prefix case and warm prefix-cache case produced endpoint-level Nsight Systems traces; the warm prefix-cache case showed additional smaller-tile `nvjet_tst_*` GEMM symbols. |
| **Verification** | verified-ci for helper/extractor/tests and verified H200 Slurm execution for the profiler run. |

## When to Use

- A vLLM or SGLang endpoint returns different text for a matched request only when prefix caching is enabled.
- A temperature-0 or otherwise deterministic request appears nondeterministic and the suspected difference is cache hit shape, active prefill rows, block/page alignment, or GEMM tiling.
- A reviewer asks for actual GPU kernel names instead of a prose hypothesis about prefix-cache behavior.
- You need to distinguish production fixes from replay controls such as slower batch-invariant or deterministic kernels.
- You need a redacted, durable runbook/blog section that names kernel families without publishing private prompts, checkpoint paths, endpoints, or artifact roots.

## Verified Workflow

### Quick Reference

```bash
# Preview both Slurm profiler cases without allocating GPUs.
docs/runbooks/<incident>/profile_prefix_cache_kernels.sh \
  --print \
  --model-path <REDACTED_CHECKPOINT_PATH>/<model> \
  --container-image <REDACTED_INFRA_PATH>/<image>.sqsh \
  --output-dir <REDACTED_INFRA_PATH>/<incident>-kernels \
  --profiler nsys

# Run the same helper on the H200 Slurm cluster when ready.
docs/runbooks/<incident>/profile_prefix_cache_kernels.sh \
  --model-path <REDACTED_CHECKPOINT_PATH>/<model> \
  --container-image <REDACTED_INFRA_PATH>/<image>.sqsh \
  --output-dir <REDACTED_INFRA_PATH>/<incident>-kernels \
  --profiler nsys

# Extract kernel names from the exported Nsight SQLite database.
python docs/runbooks/<incident>/extract_nsys_kernel_names.py \
  <artifact-root>/<case>/server.sqlite \
  --contains cublas,gemm,cutlass,xmma,wgmma,mma \
  --output-json <artifact-root>/<case>/kernel_names.filtered.json \
  --output-md <artifact-root>/<case>/kernel_names.filtered.md \
  --limit 120
```

### Detailed Steps

1. **Build matched endpoint cases.** Use one good/no-prefix case and one bad/warm-prefix-cache case with the same model, prompt shape, max tokens, seed, tensor parallelism, and endpoint flags except the cache control. For warm cache, send one warmup request to populate the shared prefix before measuring the matched request.
2. **Capture kernel names under the profiler, not by inference.** Use Nsight Systems for endpoint-level kernel-name evidence. Add an Nsight Compute mode only when you need launch counts, sections, or per-kernel metrics and can tolerate the higher overhead.
3. **Keep command construction reviewable.** The profiler helper should support `--print`, CLI flags with env fallbacks, enum validation for `nsys`/`ncu`, integer validation for ports and counts, and shell-safe quoting for any nested `bash -lc` script.
4. **Preserve the raw evidence privately.** Keep `.nsys-rep`, SQLite exports, filtered/all JSON summaries, filtered/all Markdown summaries, launch commands, client JSON, and the commit SHA under a private artifact root. Redact checkpoint paths, endpoints, prompts, tokens, and user-specific infrastructure paths before writing docs or PR bodies.
5. **Compare kernel families by case.** Start with the filtered GEMM-like set, then inspect the all-kernel summary for supporting kernels such as FlashAttention and KV-cache write kernels.
6. **Decode names conservatively.** Treat `nvjet_tst_<M>x<N>_<K>x<...>_...` names as evidence of tile-shape families, not as a complete cuBLASLt algorithm contract. `splitK`, `coopA`, and `coopB` suffixes are useful clues, but a per-layer claim still needs launch correlation or NVTX ranges.
7. **Separate active compute rows from logical context length.** A cache hit can keep the same logical context length while reducing the number of newly computed prefill rows. Kernel selection usually responds to the active compute shape, not just the total prompt length.
8. **Avoid over-broad deterministic-kernel fixes.** Batch-invariant or deterministic kernels are good replay controls, but they may be slower and broader than the cache-shape bug. Prefer an engine-owned, shape-stable fast path when the evidence points to a local cache-hit tiling transition.
9. **Document limitations.** Endpoint traces can show that the warm path entered a smaller-tile regime. They do not automatically prove which layer produced a bad token, which cuBLASLt algorithm ID was selected, or that a named kernel caused corruption. State those limits explicitly.
10. **Verify helper code and docs through CI.** Add tests for profiler print mode, invalid profiler rejection, nonnumeric controls, markdown escaping in extractors, and shell syntax/operator contract coverage. Run focused tests, full validation, pre-push hooks, and GitHub checks.

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
|---------|----------------|---------------|----------------|
| Reason from text outputs only | Compared good/bad generations and latency without profiler evidence | It showed the symptom but not the GPU execution path | Capture kernel names before making a root-cause claim about tiling or GEMM mode |
| Treat cache hit as only a performance event | Assumed identical tokens plus same logical context length meant the numerical path was equivalent | Warm cache can change active prefill rows and therefore kernel selection | Track token identity, logical context length, and active compute shape separately |
| Use global deterministic kernels as the fix | Proposed slower batch-invariant or deterministic kernels for all requests | They are useful controls but can mask a local scheduler/cache contract bug and may regress performance | Use deterministic modes for replay; target production fixes at shape-stable cache-hit scheduling |
| Publish profiler evidence with local paths | Wanted to cite local notes, artifact roots, or infrastructure paths directly | Durable docs and skills must not leak private endpoint, checkpoint, prompt, or path data | Redact all operational evidence and cite checked-in runbooks/helpers instead |
| Assert layer-level causality from endpoint names | Interpreted endpoint-level kernel symbols as proof of a specific layer failure | Kernel names alone lack per-layer launch correlation | Phrase the result as endpoint-level evidence unless NVTX/per-layer hashes bind launches to layers |
| Markdown table emitted raw kernel names | Wrote kernel names with `|`, backticks, or newlines directly into Markdown | Special characters can corrupt tables or render misleading rows | Escape `\`, `|`, backticks, carriage returns, and newlines before writing Markdown summaries |

## Results & Parameters

### Evidence Pattern

The verified H200 Slurm run compared:

| Case | Cache State | Request Shape | Expected Evidence |
|------|-------------|---------------|-------------------|
| `good-no-prefix` | Prefix caching disabled | One measured prompt and one generated token | Baseline larger-prefill GEMM kernel families |
| `bad-prefix-cache-warm-hit` | Prefix caching enabled and warmed | One warmup to fill the shared prefix, then the same measured prompt and one generated token | Baseline kernels plus smaller-tile warm-cache GEMM families |

The observed endpoint-level warm-cache trace added smaller-tile `nvjet_tst_*` symbols such as:

```text
nvjet_tst_192x16_64x8_4x1_v_bz_TNT
nvjet_tst_128x16_64x11_4x1_v_bz_splitK_TNT
nvjet_tst_64x16_64x16_4x1_v_bz_TNT
nvjet_tst_64x16_64x16_4x1_v_bz_splitK_TNT
```

Both traces also included larger-prefill-style symbols such as:

```text
nvjet_tst_256x128_64x4_1x2_h_bz_coopA_TNT
nvjet_tst_320x128_64x3_1x2_h_bz_coopB_TNT
nvjet_tst_192x8_64x8_4x1_v_bz_TNT
```

Supporting kernels in the same evidence set included `cublasLt::splitKreduce_kernel<...>`, FlashAttention SM90 forward kernels, and a vLLM KV-cache reshape/cache write kernel.

### Interpretation Rules

| Signal | Interpretation | Do Not Claim Without More Evidence |
|--------|----------------|------------------------------------|
| `MxN` tile changes in `nvjet_tst_*` | Different GEMM tile family was executed | Exact layer, exact cuBLASLt algorithm ID, or causal corruption |
| `splitK` suffix | Split-K reduction path was present | That split-K alone caused nondeterminism |
| `coopA` / `coopB` suffix | Cooperative operand-loading variant changed | That the operand variant is wrong |
| FlashAttention kernels present | Attention backend participated in the request | That attention caused the bad token |
| KV-cache write kernel present | Cache write/reshape path ran | That cache storage is corrupt |

### Verification Commands

The Inference360 PR that captured this learning used:

```bash
uv run pytest tests/test_issue257_profile_prefix_cache_kernels.py \
  tests/test_issue257_nsys_kernel_extractor.py \
  tests/test_quality_gate_scripts.py -q

uv run pre-commit run --all-files
just validate
gh pr checks <pr-number>
```

Observed sanitized results:

- Focused tests: 75 passed.
- Local full validation: 1051 passed, 9 skipped.
- Pre-push hook: 1059 passed, 1 skipped.
- GitHub checks: `validate`, `pre-commit`, `sast`, `secrets`, `python-sca`, CodeQL, and action/python analysis passed.

## Verified On

| Project | Context | Details |
|---------|---------|---------|
| LLM360/Inference360 | PR #327, issue #257 prefix-cache nondeterminism blog/runbook/profiler work, 2026-07-02 | H200 Slurm Nsight Systems run completed for good/no-prefix and bad/warm-prefix-cache cases. Helper/extractor/docs changes passed local full validation, pre-push pytest, and GitHub checks. |
