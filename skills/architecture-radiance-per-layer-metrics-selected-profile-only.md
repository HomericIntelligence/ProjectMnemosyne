---
name: architecture-radiance-per-layer-metrics-selected-profile-only
description: "Use when adding analytical model metrics to Radiance: (1) every operator/graph node needs explicit SoL coverage, (2) dtype-aware hardware projection and serving estimates must recompute from user-provided inference inputs."
category: architecture
date: 2026-04-27
version: "1.1.0"
user-invocable: false
verification: verified-local
history: architecture-radiance-per-layer-metrics-selected-profile-only.history
tags: [radiance, metrics, hardware-profile, operator-kernels, layer-aggregation, sol, roofline, dtype, serving-estimates]
---

# Radiance Dtype-Aware SoL Coverage And Serving Estimates

## Overview

| Field | Value |
| ------- | ------- |
| **Date** | 2026-04-27 |
| **Objective** | Extend Radiance's analytical metrics so every graph/operator node receives an explicit Speed-of-Light (SoL) row, unsupported coverage is visible, hardware projection is dtype-aware, and serving estimates are recomputed from user-provided inference inputs. |
| **Outcome** | Successful local implementation: complete modeled/unmodeled SoL coverage, dtype-dependent peak compute and storage bytes, nullable SoL rows with diagnostics, backend TTFT/TPOT/ITL estimates, frontend Radiance Perf recompute panel, and unit scale helpers. |
| **Verification** | verified-local - backend tests, targeted frontend tests, frontend build, diff check, and targeted Ruff passed locally; CI validation pending. |
| **History** | [changelog](./architecture-radiance-per-layer-metrics-selected-profile-only.history) |

## When to Use

- You need Radiance graph/operator nodes to have complete SoL coverage instead of silently omitting unsupported or unmodeled nodes.
- Hardware projection must account for dtype support, dtype-specific peak TFLOPs, and dtype-dependent memory/storage bytes.
- Serving performance estimates such as TTFT, TPOT, ITL, output tokens/sec, and KV cache footprint need to be derived from inference scenario inputs.
- The Model Explorer viewer needs a left-side performance panel that can start a recomputation run with updated `performanceInputs`.
- You are touching Radiance metric formulas and need to avoid repeated magic constants such as `1_000_000_000_000`.

## Verified Workflow

Verified locally only - CI validation pending.

### Quick Reference

```bash
# Backend contract, SoL coverage, serving estimate, and fixture checks
python -m pytest tests/backend -q

# Frontend build and targeted Radiance UI/service tests
cd vendor/model_explorer/src/ui
npm run build
npm test -- --watch=false --browsers=ChromeHeadless \
  --include=src/services/radiance_run_service.spec.ts \
  --include=src/components/radiance_source_input/radiance_source_input.spec.ts

# Mechanical checks used for this change
git diff --check
python -m ruff check \
  radiance/units.py \
  radiance/metrics/hardware.py \
  radiance/metrics/models.py \
  radiance/metrics/engine.py \
  radiance/metrics/ops/addmm.py \
  radiance/metrics/ops/matmul.py \
  radiance/metrics/ops/embedding.py \
  radiance/server/routes.py \
  radiance/server/runs.py \
  tests/backend/test_units.py \
  tests/backend/test_metrics_engine.py \
  tests/backend/test_run_routes.py \
  tests/backend/test_theoretical_runs.py \
  tests/backend/test_release_fixture_suite.py \
  --select E,F,B,I --ignore E402
```

### Detailed Steps

1. Preserve the operator graph as the metric source of truth and the layer graph as the user-facing aggregation target. Do not try to infer exact FLOPs or memory traffic from layer type alone.
2. Require complete SoL artifact coverage. For every operator/graph node, write either a modeled SoL row or an explicit unmodeled row. Unmodeled rows should use nullable `theoretical_latency_ms` and `speed_of_light_pct`, set `coverage_kind`, and include a diagnostic.
3. Add dtype fields at each metric boundary. `OpEstimate` and `LayerEstimate` should carry compute, activation, weight, and memory dtype information so formulas and projections do not collapse everything into fp16.
4. Make hardware profiles dtype-aware. Keep `supported_dtypes` and `peak_tflops_by_dtype` on `HardwareProfile`, and have projection choose the effective compute dtype peak rather than a single fixed `peak_fp16_tflops` value.
5. Treat unsupported dtype/operator combinations as uncovered diagnostics, not estimates. If the hardware or kernel cannot support the requested dtype, produce an explicit unmodeled reason and avoid guessed latency.
6. Use dtype-dependent byte accounting. Normalize dtype aliases and compute storage bytes from dtype for weights, activations, KV cache, and operator memory traffic.
7. Fix shape-sensitive kernels while adding coverage. In this session `addmm` needed robust operand inference for both PyTorch argument order and the local trace order, `matmul` needed broadcasted output batch handling, and `embedding` needed zero FLOPs plus traffic based on accessed rows/output/index rather than full table reads.
8. Add serving estimates to the run pipeline. Persist `performance/serving_estimates.json` and include TTFT, TPOT/ITL, end-to-end latency, output tokens/sec, decode roofline, KV bytes per token, and KV cache footprint.
9. Accept `performanceInputs` on run creation and map them into an inference scenario. Include batch size, context/sequence length, max output tokens, max sequence length, max num sequences, max batched tokens, KV cache budget GiB, compute/activation/weight/KV dtypes, tensor parallel size, and pipeline parallel size.
10. Add a viewer-side Radiance Perf panel on the left side, opposite graph/node details. Show roofline and serving metrics, expose the inference inputs, and wire the Update button to start a new backend run with `performanceInputs` and navigate to the recomputed run.
11. Replace repeated scale constants with helpers. Add `radiance/units.py` with decimal helpers (`hundred`, `thousand`, `million`, `billion`, `trillion`) and binary helpers (`kilo`, `mega`, `giga`, `tera`, `peta`) so formulas express units directly.
12. Update fixtures and release tests so missing SoL rows fail. A release fixture check should assert that operator SoL coverage includes all graph node IDs, including unmodeled nodes.

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
| --------- | ---------------- | --------------- | ---------------- |
| Start from layer-only graph extraction | Reuse the existing layer graph as the sole source of analytical truth | Layer nodes are the right user-facing scope, but they do not preserve the exact operator semantics needed for FLOPs and memory formulas | Keep operator truth internally and aggregate onto layers afterward |
| Treat hardware as a fixed built-in catalog | Initial plan referenced preselected accelerator profiles for every run | Product direction changed: hardware must be configurable per request, and computing all profiles adds noise and cost | Make `hardwareProfile` required on run start and project only the selected profile |
| Hide unsupported operations behind heuristic fallbacks | Could have estimated unknown ops from adjacent layer shape or layer type | That would silently inflate modeled coverage and weaken trust in analytical output | Unsupported ops must stay explicit in coverage and produce no fabricated metric values |
| Omit unmodeled nodes from SoL artifacts | Only write SoL rows when a kernel produced a theoretical latency | Many graph nodes appeared to have no calculation at all, making coverage impossible to audit | Write explicit unmodeled SoL rows with `coverage_kind`, null latency/SoL percent, and diagnostics |
| Use one fp16 peak for all projections | Project all modeled ops through `peak_fp16_tflops` | bf16/fp8/int8/fp32 support and throughput differ by hardware, so a single peak makes roofline output misleading | Store `peak_tflops_by_dtype` and select projection peak from the effective compute dtype |
| Count embedding as full table traffic | Treat embedding memory as if the entire table were read and assign compute work | Inference only accesses indexed rows; full table size is capacity, not per-request traffic | Use accessed row/output/index bytes for traffic and zero compute FLOPs |
| Keep repeated numeric scale literals | Inline constants such as `1_000_000_000_000` in projection formulas | Repetition made units harder to audit and encouraged inconsistent decimal/binary scaling | Centralize decimal and binary scale helpers in `radiance/units.py` |

## Results & Parameters

### Core Contract Changes

```text
radiance/contracts/models.py
  InferenceScenario:
    batch_size
    context_length
    sequence_length
    max_output_tokens
    max_sequence_length
    max_num_sequences
    max_num_batched_tokens
    kv_cache_budget_gib
    compute_dtype
    activation_dtype
    weight_dtype
    kv_cache_dtype
    tensor_parallel_size
    pipeline_parallel_size

  HardwareProfile:
    supported_dtypes
    peak_tflops_by_dtype
    peak_tflops_for_dtype(dtype)
    supports_dtype(dtype)

  SolRecord:
    theoretical_latency_ms: nullable
    speed_of_light_pct: nullable
    coverage_kind
    diagnostic
    compute_dtype
    memory_dtype
```

### Metric Model Changes

```text
radiance/metrics/models.py
  dtype_storage_nbytes(dtype)
  normalize_dtype_name(dtype)
  promoted_compute_dtype(...)
  OpEstimate dtype fields
  LayerEstimate dtype fields

radiance/metrics/engine.py
  MetricsAnalysisResult.unmodeled_operator_reasons
  explicit uncovered diagnostics for unknown ops and unsupported dtype/operator cases
```

### Serving Estimate Inputs

```json
{
  "performanceInputs": {
    "batchSize": 1,
    "contextLength": 2048,
    "sequenceLength": 2048,
    "maxOutputTokens": 128,
    "maxSequenceLength": 4096,
    "maxNumSequences": 1,
    "maxNumBatchedTokens": 2048,
    "kvCacheBudgetGib": 16,
    "computeDtype": "float16",
    "activationDtype": "float16",
    "weightDtype": "float16",
    "kvCacheDtype": "float16",
    "tensorParallelSize": 1,
    "pipelineParallelSize": 1
  }
}
```

### Serving Estimate Artifact

```text
performance/serving_estimates.json
  formula_version: serving-roofline-v1
  ttft_ms
  tpot_ms
  inter_token_latency_ms
  end_to_end_latency_ms
  output_tokens_per_second
  kv_cache_bytes_per_token
  kv_cache_footprint_bytes
  decode_roofline
```

### Unit Helpers

```python
from radiance.units import billion, giga, trillion

compute_latency_ms = (flops / trillion(peak_tflops)) * thousand(1)
memory_latency_ms = (bytes_moved / billion(peak_hbm_gbps)) * thousand(1)
memory_capacity_bytes = giga(memory_gib)
```

### Verification Commands And Results

```text
python -m pytest tests/backend -q
202 passed, 2 skipped

npm run build
passed

npm test -- --watch=false --browsers=ChromeHeadless --include=src/services/radiance_run_service.spec.ts --include=src/components/radiance_source_input/radiance_source_input.spec.ts
14 SUCCESS

git diff --check
passed

targeted python -m ruff check on touched backend core files
passed
```

Full Ruff was not used as a gate for this session because the repository had many pre-existing unrelated Ruff findings outside the touched scope.

## Verified On

| Project | Context | Details |
| --------- | --------- | --------- |
| Radiance | Dtype-aware complete SoL coverage, serving performance estimates, and Model Explorer recompute panel | Verified locally with backend suite, targeted frontend tests, frontend build, diff check, and targeted Ruff on touched backend files |
