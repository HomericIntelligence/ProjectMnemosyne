---
name: debugging-prefix-cache-nsight-kernel-evidence
description: "Capture and interpret Nsight and active-row evidence for vLLM, XLLM, or SGLang prefix-cache nondeterminism. Use when: (1) cache hits change output despite deterministic settings, (2) warm prefix-cache paths may select different GEMM tiling, (3) bit-exact cache replay still leaves garbled text, (4) sampling or token selection may be the real corruption source."
category: debugging
date: 2026-07-09
version: "1.1.0"
user-invocable: false
verification: verified-local
history: debugging-prefix-cache-nsight-kernel-evidence.history
tags:
  - inference
  - vllm
  - xllm
  - sglang
  - prefix-cache
  - nsight
  - nsys
  - ncu
  - h200
  - slurm
  - determinism
  - sampling
---

# Prefix-Cache Shape and Kernel Evidence

## Overview

| Field | Value |
|-------|-------|
| **Date** | 2026-07-09 |
| **Objective** | Prove whether a warm prefix-cache path changes the executed GPU kernel regime, then separate real cache-shape numerical drift from downstream sampling or token-selection corruption. |
| **Outcome** | Successful as a diagnostic. Nsight evidence showed different GEMM families on warm cache paths, and local cache-shape replay made the tested cold and cache-hit computation bit-exact. The same output class still appeared under direct XLLM/HF sampling, so the garbled-text investigation pivoted to sampling/token selection. |
| **Verification** | verified-local for the 2026-07-09 cache-shape replay and sampling pivot; earlier helper/extractor work was verified-ci. |
| **History** | [changelog](./debugging-prefix-cache-nsight-kernel-evidence.history) |

## When to Use

- A vLLM or SGLang endpoint returns different text for a matched request only when prefix caching is enabled.
- A temperature-0 or otherwise deterministic request appears nondeterministic and the suspected difference is cache hit shape, active prefill rows, block/page alignment, or GEMM tiling.
- A vLLM or XLLM prefix-cache hit changes the active row dimension seen by non-attention linear layers while attention still sees the full logical context through KV cache.
- You made a cache-hit replay path bit-exact and need to decide whether the remaining corruption belongs to sampling, token selection, or model code instead of prefix-cache numerics.
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
8. **Map cache reuse to non-attention row shapes.** In vLLM/XLLM-style prefix-cache reuse, attention can still attend to the full logical context through cached KV, while qkv, o_proj, and MLP linear layers only process newly active tail rows. For a logical prompt length of 108 and block size 16, a warm hit can reuse 96 rows and compute a 12-row tail.
9. **Replay cache-hit shapes inside cold prefill.** To test whether the shape transition itself explains numerical drift, split cold prefill dynamically into block-aligned and tail segments:

   ```python
   aligned_m = (m // block_size) * block_size
   tail_m = m % block_size
   segments = [aligned_m, tail_m] if aligned_m and tail_m else [m]
   ```

   Compare cold replay against the warm cache-hit path. If the split replay is bit-exact for the tested path, the cache-shape drift is real and isolated.
10. **Treat bit-exact cache replay as a narrowing result, not a fix.** If the same garbled output class survives after cache-shape replay is bit-exact, run direct engine/HF sampling comparisons and pivot toward sampling or token selection. Do not keep forcing the prefix-cache hypothesis after the evidence moves.
11. **Avoid over-broad deterministic-kernel fixes.** Batch-invariant or deterministic kernels are good replay controls, but they may be slower and broader than the cache-shape bug. Prefer an engine-owned, shape-stable fast path when the evidence points to a local cache-hit tiling transition.
12. **Document limitations.** Endpoint traces can show that the warm path entered a smaller-tile regime. They do not automatically prove which layer produced a bad token, which cuBLASLt algorithm ID was selected, or that a named kernel caused corruption. A bit-exact cache replay also does not prove sampling is correct. State those limits explicitly.
13. **Verify helper code and docs through CI.** Add tests for profiler print mode, invalid profiler rejection, nonnumeric controls, markdown escaping in extractors, shell syntax/operator contract coverage, cache-shape segmentation, and sampling/token-selection pivots. Run focused tests, full validation, pre-push hooks, and GitHub checks.

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
|---------|----------------|---------------|----------------|
| Reason from text outputs only | Compared good/bad generations and latency without profiler evidence | It showed the symptom but not the GPU execution path | Capture kernel names before making a root-cause claim about tiling or GEMM mode |
| Treat cache hit as only a performance event | Assumed identical tokens plus same logical context length meant the numerical path was equivalent | Warm cache can change active prefill rows and therefore kernel selection | Track token identity, logical context length, and active compute shape separately |
| Use global deterministic kernels as the fix | Proposed slower batch-invariant or deterministic kernels for all requests | They are useful controls but can mask a local scheduler/cache contract bug and may regress performance | Use deterministic modes for replay; target production fixes at shape-stable cache-hit scheduling |
| Publish profiler evidence with local paths | Wanted to cite local notes, artifact roots, or infrastructure paths directly | Durable docs and skills must not leak private endpoint, checkpoint, prompt, or path data | Redact all operational evidence and cite checked-in runbooks/helpers instead |
| Assert layer-level causality from endpoint names | Interpreted endpoint-level kernel symbols as proof of a specific layer failure | Kernel names alone lack per-layer launch correlation | Phrase the result as endpoint-level evidence unless NVTX/per-layer hashes bind launches to layers |
| Markdown table emitted raw kernel names | Wrote kernel names with `|`, backticks, or newlines directly into Markdown | Special characters can corrupt tables or render misleading rows | Escape `\`, `|`, backticks, carriage returns, and newlines before writing Markdown summaries |
| Assume `--no-enable-prefix-caching` guarantees correctness | Disabled prefix caching and treated the cold path as a correctness oracle | The cache path can be a real numerical difference but not the only corruption source | Use no-cache runs as one control, then verify model and sampling paths independently |
| Treat bit-exact cache replay as the final fix | Split cold prefill into block-aligned and tail rows until it matched the warm cache-hit path bit-exactly | The same garbled output class still appeared under direct XLLM/HF sampling | Bit-exact cache replay proves the cache-shape drift is real, not that output corruption is solved |
| Generalize from a low-hit-rate model | Used a model that did not reproduce failures to argue the serving bug was absent | Its prefix-cache hit rate and active-row shape exposure were not comparable to the failing case | Compare cache hit rate, block alignment, active tail rows, and sampling path before clearing a serving bug |

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

### Cache-Shape Replay Pattern

For prefix-cache investigations, track these dimensions separately:

| Dimension | Cold Prefill | Warm Prefix-Cache Hit |
|-----------|--------------|-----------------------|
| Logical context length | Full prompt length | Full prompt length through cached KV plus tail |
| Attention context | Full prompt rows | Cached prefix rows plus newly computed tail rows |
| Non-attention linear active rows | All prompt rows | Newly computed tail rows only |
| GEMM shape exposure | One larger active `M` unless replay-split | Smaller tail `M` after block-aligned reuse |

Concrete local case:

```text
logical prompt length: 108
block size: 16
reused prefix rows: 96
active tail rows: 12
```

Cold replay segmentation used this rule:

```python
aligned_m = (m // block_size) * block_size
tail_m = m % block_size
segments = [aligned_m, tail_m] if aligned_m and tail_m else [m]
```

Use `[m]` when `tail_m == 0` or `aligned_m == 0`, because there is no meaningful two-segment cold replay. In the issue #257 local investigation, this split made the tested cold and cache-hit computation bit-exact, proving cache-shape drift was real for that path.

### Red-Herring Decision Rule

Bit-exact cache-shape replay is a diagnostic milestone, not a root-cause verdict. After the cache path matched bit-exactly, the same output class still appeared under direct XLLM/HF sampling in the local investigation. That changed the next question from "is the prefix cache corrupting math?" to "which sampling or token-selection path is choosing the bad token?"

### Interpretation Rules

| Signal | Interpretation | Do Not Claim Without More Evidence |
|--------|----------------|------------------------------------|
| `MxN` tile changes in `nvjet_tst_*` | Different GEMM tile family was executed | Exact layer, exact cuBLASLt algorithm ID, or causal corruption |
| `splitK` suffix | Split-K reduction path was present | That split-K alone caused nondeterminism |
| `coopA` / `coopB` suffix | Cooperative operand-loading variant changed | That the operand variant is wrong |
| FlashAttention kernels present | Attention backend participated in the request | That attention caused the bad token |
| KV-cache write kernel present | Cache write/reshape path ran | That cache storage is corrupt |
| Bit-exact split cold replay | Cache-hit active-row drift was reproduced and isolated for the tested path | That garbled text is fixed, or that sampling/token selection is correct |
| Direct XLLM/HF sampling reproduces the same output class | The investigation should pivot downstream of prefix-cache math | That every serving path is innocent without comparable sampling controls |

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
- 2026-07-09 local issue #257 follow-up: cache-shape replay made the tested cold/cache-hit path bit-exact; direct XLLM/HF sampling still showed the same output class, so the current amendment is verified-local pending this Mnemosyne PR's checks.

## Verified On

| Project | Context | Details |
|---------|---------|---------|
| LLM360/Inference360 | PR #327, issue #257 prefix-cache nondeterminism blog/runbook/profiler work, 2026-07-02 | H200 Slurm Nsight Systems run completed for good/no-prefix and bad/warm-prefix-cache cases. Helper/extractor/docs changes passed local full validation, pre-push pytest, and GitHub checks. |
| LLM360/Inference360 | Issue #257 local cache-shape replay and sampling pivot, 2026-07-09 | Local H200 Slurm/XLLM investigation verified that splitting cold prefill into block-aligned and tail rows made the tested cache-hit path bit-exact. Comparable garbled outputs still appeared under direct XLLM/HF sampling, so root-cause work pivoted to sampling/token selection. |
