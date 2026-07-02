---
name: inference360-ifm-warden-inferencex-matrix-results
description: "Run IFM benchmarks through Inference360 Warden and PerfHC without masking serving gaps. Use when: (1) benchmarking routed Warden OpenAI-compatible endpoints, (2) requiring route-aware server-side /tokenize for exact counts, (3) publishing sanitized InferenceX or PerfHC artifacts."
category: evaluation
date: 2026-07-02
version: "1.1.0"
user-invocable: false
verification: verified-local
history: inference360-ifm-warden-inferencex-matrix-results.history
tags:
  - inference360
  - ifm
  - warden
  - inferencex
  - perfhc
  - benchmark
  - tokenize
  - openai-compatible
  - h200
  - slurm
  - haproxy
---

# Inference360 IFM Warden InferenceX Matrix Results

## Overview

| Field | Value |
|-------|-------|
| **Date** | 2026-07-02 |
| **Objective** | Build and run IFM benchmark workflows where Warden owns lifecycle, PerfHC/InferenceX exercise the routed OpenAI-compatible service path, exact token counts come from a local tokenizer or route-aware `/tokenize`, and sanitized artifacts land in PerfHC. |
| **Outcome** | Operational. The original IFM Warden matrix and sanitized artifacts merged after CI passed; the routed endpoint and fail-closed `/tokenize` requirement was implemented in PerfHC PR #42 with local verification and PR checks pending at capture time. |
| **Verification** | verified-local. PerfHC PR #42 passed local pytest, Ruff, compileall, and staged whitespace checks; GitHub checks were pending at capture time. Earlier Inference360 PR #328 and PerfHC PR #41 evidence remains verified-ci. |
| **History** | [changelog](./inference360-ifm-warden-inferencex-matrix-results.history) |

## When to Use

- You need to benchmark IFM checkpoints through the real Inference360 Warden lifecycle rather than direct ad hoc server launches.
- A run must isolate checkpoints by registering, starting, benchmarking, stopping, and then moving to the next checkpoint.
- InferenceX should exercise the OpenAI-compatible HAProxy route, not a private backend port.
- PerfHC needs to benchmark routed Warden endpoint URLs shaped like `<origin>/<route>/v1` or `<origin>/<route>/v1/models`.
- Endpoint-only raw runs need exact token counts and must fail when neither local `transformers` tokenizers nor route-aware server-side `/tokenize` works.
- A public GitHub issue or PR needs to discuss the serving contract without exposing private host, port, route, checkpoint, or model details.
- Benchmark result JSON is going to PerfHC or another durable repository and must be sanitized before commit.
- You need to prove both execution completeness and published artifact safety for a large benchmark matrix.

## Verified Workflow

### Quick Reference

```text
Inputs:
- private model facts: <REDACTED_CHECKPOINT_ROOT>/models.yaml
- checked-in runner: manifest-driven Inference360 workflow
- lengths: 1024, 10000, 100000
- num_prompts: 1
- max_concurrency: 1
- request_rate: inf
- ignore_eos: true

Loop:
1. Read checkpoint config.json for max context length.
2. Generate framework-neutral model id, route, and manifest filename.
3. warden status
4. allocate only if no suitable node is available.
5. registry register the generated manifest.
6. start the model on the selected node and require state=running and ready=true.
7. run InferenceX against the HAProxy route for all 9 length pairs.
8. redact saved JSON fields and scan artifacts.
9. stop the model in finally before the next checkpoint.

Endpoint-only PerfHC contract:
- Accept bare hosts, `/v1`, routed `/v1`, and routed `/v1/models` endpoint inputs.
- Normalize benchmark requests from `<route>/v1/models` to `<route>/v1`.
- Include the route slug in endpoint-derived output paths to avoid host/port collisions.
- Tokenize at the route root: `<origin>/<route>/tokenize`.
- If local tokenizer loading is unavailable and `/tokenize` fails, raise and fix the inference service.
```

### Detailed Steps

1. Keep private checkpoint roots, tokenizer paths, container paths, and container digests in an external private models YAML. The checked-in runner may accept an explicit file path, but it must not hardcode values such as `<REDACTED_CHECKPOINT_ROOT>`, `<REDACTED_CONTAINER_SQSH>`, or `<REDACTED_CONTAINER_DIGEST>`.

2. Generate logical model IDs, routes, and manifest filenames from lower-case model names. Do not encode serving framework names such as vLLM or SGLang into those logical surfaces. Put the engine only in runtime metadata, benchmark metadata, or report fields.

3. Before launching a checkpoint, read its `config.json` and derive the maximum supported context from known keys such as:

   ```text
   max_position_embeddings
   max_sequence_length
   seq_length
   model_max_length
   n_positions
   ```

   Do not hardcode maximum context limits in the runner.

4. Use Warden as the lifecycle authority:

   ```text
   status
   allocate if no suitable node is already available
   registry register <generated-manifest>
   start <model> on <chosen-node> with a launch timeout
   require returned state=running and ready=true
   run benchmarks
   stop <model> in finally
   ```

   A remaining registration is not the same thing as a loaded endpoint. At completion, confirm no active routes and no running servers.

5. Run InferenceX and PerfHC only through the OpenAI-compatible HAProxy or Warden route, represented in shared artifacts as `<REDACTED_ENDPOINT>`. Do not benchmark private backend ports when the intended product path is the routed API.

6. Normalize routed endpoint URLs before sending benchmark traffic. Accept operator input as a bare origin, `/v1`, `<route>/v1`, or `<route>/v1/models`; use `<route>/v1` for OpenAI-compatible benchmark requests; keep health/status checks able to probe the host root and route-local `/v1/models`.

7. Include the route in endpoint-derived output paths. When multiple models share one host and port through different routes, host/port-only slugs collide and can overwrite or intermix results.

8. Treat `/tokenize` as part of the benchmark-serving contract for endpoint-only raw runs. If PerfHC cannot load a local `transformers` tokenizer, post tokenization to the route root, for example `<origin>/<route>/tokenize`, not necessarily the host root. Missing or failing `/tokenize` should raise and fail the benchmark; approximate token counts hide an inference-service defect.

9. When filing public issues for missing serving surfaces, use the repository issue template and placeholders such as `<warden-origin>`, `<route>`, and `<model-id>`. Do not paste private hostnames, IPs, ports, checkpoint paths, or route names when sanitized placeholders are enough to reproduce the contract.

10. Use the verified matrix parameters:

   ```text
   input lengths: 1024, 10000, 100000
   output lengths: 1024, 10000, 100000
   num_prompts: 1
   max_concurrency: 1
   request_rate: inf
   ignore_eos: true
   trust_remote_code: true only when the manifest or tokenizer requires it
   ```

11. Save one InferenceX JSON artifact per model and length pair. Redact before publishing because the raw JSON can include endpoint URL, tokenizer/checkpoint paths, tokenizer IDs, and the full command line.

12. Redact at least these fields recursively before commit:

   ```text
   base_url
   endpoint_discovery_url
   command
   tokenizer
   tokenizer_id
   ```

   Use placeholders such as `<REDACTED_ENDPOINT>`, `<REDACTED_CHECKPOINT_PATH>`, `<REDACTED_CONTAINER_SQSH>`, and `<REDACTED_CONTAINER_DIGEST>` where shape matters.

13. Audit the local run log and the published PerfHC tree separately. The run log proves execution count and missing cells. The PerfHC git tree proves durable published artifacts and must be the target of the leak scan. Generated smoke benchmark output with timestamps and metrics should stay uncommitted unless the PR intentionally publishes benchmark results.

14. Treat CI failures as workflow feedback:
    - Bandit B104 can flag intentional `0.0.0.0` bind or comparison in generated launch logic. Add a scoped `# nosec B104` and explain the intentional bind with a preceding comment.
    - Existing IFM naming guards may reject new legacy `k2v3` logical surfaces. Use an IFM-neutral prompt mix default such as `ifm_single_node`.
    - If local `just validate` cannot run because rootless Podman is unavailable, say that directly and rely on the GitHub validate job only after it passes.

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
|---------|----------------|---------------|----------------|
| Framework names in routes | Encoded the serving framework into model IDs and routes | The logical product surface should not change when the runtime engine changes | Keep model IDs, routes, and manifest filenames framework-neutral; store engine in metadata only |
| Raw PerfHC JSON artifacts | Published saved InferenceX JSON before sanitizing all embedded fields | `tokenizer_id` and related fields can contain checkpoint or tokenizer paths | Post-process JSON artifacts recursively and leak scan the committed tree |
| Unannotated wildcard bind logic | Left intentional `0.0.0.0` bind/comparison without a scoped suppression | SAST failed on Bandit B104 | Add a narrow `# nosec B104` with a preceding comment explaining the generated launch bind |
| Legacy prompt mix naming | Used a `k2v3_single_node` prompt mix default in the checked-in runner | Existing IFM naming guard rejects new legacy `k2v3` surfaces | Use an IFM-neutral prompt mix directory name such as `ifm_single_node` |
| Local-only validation assumption | Tried to use local `just validate` on the cluster host as the final validation | Rootless Podman was unavailable on that host | Document the local blocker and require GitHub validate CI to pass before claiming verified-ci |
| Scratch-only leak scan | Scanned local scratch output but not the published PerfHC tree | Published artifacts can differ after copy, redaction, or commit selection | Run leak scans against the exact PerfHC git tree that will be pushed |
| Approximate tokenizer fallback | Allowed PerfHC to estimate token counts when local tokenizer loading was unavailable and endpoint `/tokenize` returned 404 | Tests could pass while masking a missing inference-service capability | Endpoint-only raw benchmarks require exact token counts; fail closed and fix the serving surface |
| Host-root tokenization only | Posted server-side tokenization to `<origin>/tokenize` for a warden-routed endpoint | Routed Warden services may need tokenization at `<origin>/<route>/tokenize` to select the right model surface | Preserve the route root when constructing `/tokenize` URLs |
| Public issue with concrete internal endpoint | Prepared repro details using real host, port, model route, or checkpoint names | Public repositories and issue templates require placeholders for sensitive endpoint data | Use sanitized placeholders while preserving request shape and expected response contract |
| Commit generated smoke JSON by default | Considered adding endpoint-only smoke output such as `openai-compatible-in16-out8-c1.json` with timestamps and metrics | Generated smoke files are run artifacts, not implementation changes, and can add noisy or stale results to a code PR | Leave generated benchmark output uncommitted unless the PR is explicitly a benchmark-results publication |

## Results & Parameters

### Merged Evidence

| Repository | PR | Merge Date | Merge Commit | CI Evidence |
|------------|----|------------|--------------|-------------|
| LLM360/Inference360 | #328 | 2026-07-02 | `c32c2b956e2895118869d6ca9b460db22e3337c3` | `pre-commit`, `validate`, `secrets`, `sast`, `python-sca`, CodeQL passed |
| LLM360/PerfHC | #41 | 2026-07-02 | `aa9feb21878a332e2986a0ae218c8c1d5dd7a9b8` | `tests-and-static-checks` passed |

### Routed Endpoint Contract

| Input Shape | Benchmark Base | Models Probe | Tokenize URL |
|-------------|----------------|--------------|--------------|
| `<origin>` | `<origin>/v1` | `<origin>/v1/models` | `<origin>/tokenize` |
| `<origin>/v1` | `<origin>/v1` | `<origin>/v1/models` | `<origin>/tokenize` |
| `<origin>/<route>/v1` | `<origin>/<route>/v1` | `<origin>/<route>/v1/models` | `<origin>/<route>/tokenize` |
| `<origin>/<route>/v1/models` | `<origin>/<route>/v1` | `<origin>/<route>/v1/models` | `<origin>/<route>/tokenize` |

Endpoint-derived output paths should include a route slug as well as host and port because Warden can serve multiple model routes behind one origin.

### Tokenization Service Contract

```text
Required for endpoint-only raw runs when no local transformers tokenizer is available:
POST <route-root>/tokenize

Prompt request shape:
{"model": "<model-id>", "prompt": "<text>", "add_special_tokens": false}

Chat request shape:
{"model": "<model-id>", "messages": [...], "add_generation_prompt": true}

Acceptable response shape:
{"tokens": [...]} or {"count": <integer>}
```

The endpoint is a common serving-engine extension rather than a core OpenAI API route. GitHub code search found vLLM routing `/tokenize` and `/detokenize`, vLLM's tokenize API router, and SGLang exposing `@app.post("/tokenize")`. Use that evidence to justify an inference-service issue, but keep public repros sanitized.

### PerfHC PR #42 Local Verification

```bash
cd <PerfHC checkout>

PYTHONPATH=<PerfHC checkout> \
XDG_CACHE_HOME=/tmp/uv-cache \
UV_TOOL_DIR=/tmp/uv-tools \
uvx --with httpx pytest tests -q
# 34 passed

ruff check \
  perfhc_bench/endpoints.py \
  perfhc_bench/suite.py \
  perfhc_bench/runtime/common.py \
  tests/test_perfhc_bench.py
# All checks passed

python3 -m compileall perfhc_bench scripts tests
# succeeded

git diff --staged --check
# no output
```

### Public Tracking Issue

LLM360/Inference360 issue #331 requested `POST /tokenize` on Warden OpenAI-compatible routes. The issue used placeholders instead of real endpoint details and framed missing `/tokenize` as an inference-service gap, not a PerfHC workaround.

### Published Artifact Contract

```text
PerfHC origin/master contains:
- 45 matrix JSON files
- 5 models x 9 length pairs
- length pairs from {1024, 10000, 100000} input x {1024, 10000, 100000} output
- sanitized benchmark metadata
- no private checkpoint paths, endpoint hosts/IPs, tokenizer command paths, or container launch paths
```

### Runtime Completion Contract

```text
At completion:
- no active Warden routes
- no running Warden servers
- model registrations may remain

Interpretation:
- registrations are durable registry metadata
- active routes and running servers are loaded endpoint state
- do not treat remaining registrations as leaked running endpoints
```

### Leak Scan Shape

Run the leak scan against the published repository tree, not only temporary output:

```bash
cd <PerfHC checkout>

rg -n \
  '<REDACTED_CHECKPOINT_ROOT>|<REDACTED_ENDPOINT>|<REDACTED_CONTAINER_SQSH>|<REDACTED_CONTAINER_DIGEST>|tokenizer_id|base_url|endpoint_discovery_url|command' \
  <published-artifact-root>
```

Replace the placeholder patterns with the private path, endpoint, and container substrings that must never be published. The expected result is no private-path or private-endpoint hits. Generic JSON keys may still appear if their values are redacted placeholders.

## Verified On

| Project | Context | Details |
|---------|---------|---------|
| LLM360/Inference360 | PR #328, merged 2026-07-02 | Runner merged at `c32c2b956e2895118869d6ca9b460db22e3337c3`; CI passed `pre-commit`, `validate`, `secrets`, `sast`, `python-sca`, and CodeQL. |
| LLM360/PerfHC | PR #41, merged 2026-07-02 | Result artifacts merged at `aa9feb21878a332e2986a0ae218c8c1d5dd7a9b8`; CI passed `tests-and-static-checks`; published tree contained 45 sanitized matrix JSON files. |
| LLM360/PerfHC | PR #42, branch `codex/warden-tokenize-required`, commit `80f1b5ba3` | Local verification passed with 34 pytest tests, Ruff on changed Python files, compileall, and staged whitespace checks; GitHub PR check was pending at learning capture. |
| LLM360/Inference360 | Issue #331, filed 2026-07-02 | Public bug report requested route-aware `POST /tokenize` for Warden OpenAI-compatible routes using placeholders instead of private endpoint details. |
