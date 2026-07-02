---
name: inference360-staging-fresh-allocation-control
description: "Validate and debug Inference360 staging/control API launches and issue 257 reproducers. Use when: (1) proving IFM or multi-model vLLM endpoints through the Inference360 control API, (2) reproducing Inference360 issue 257 / IFM corruption with vLLM, SGLang, HF, XLLM, or public NanoGPT cache-logits comparison paths, (3) capturing logprobs, token IDs, launch commands, logits tensors, and cleanup evidence for H200 repro workflows."
category: debugging
date: 2026-07-02
version: "1.2.0"
user-invocable: false
verification: verified-ci
history: inference360-staging-fresh-allocation-control.history
tags: [inference360, slurm, h200, control, staging, vllm, sglang, xllm, ifm, corruption, nodepool, nanogpt, cache-logits]
---

# Inference360 Fresh-Allocation Staging Control Validation

## Overview

| Field | Value |
| ------- | ------- |
| **Date** | 2026-07-02 |
| **Objective** | Run Inference360 staging/control tests and deterministic issue 257 repros, including a public open-source SGLang/NanoGPT cache-logits reproducer that avoids IFM models and private paths. |
| **Outcome** | Successful local end-to-end cluster/control validation, issue 257 vLLM IFM evidence, and a CI-verified public reproducer for SGLang radix-prefix-cache / chunked-prefill tail-logit instability. |
| **Verification** | verified-ci for the public SGLang/NanoGPT reproducer in Inference360 PR #326. Prior H200 Slurm fresh-allocation workflow remains verified-local. |
| **History** | [changelog](./inference360-staging-fresh-allocation-control.history) |

## When to Use

- The user asks to validate Inference360 staging, control API, or lifecycle behavior for IFM, multi-model vLLM, or similar H200 Slurm services.
- Existing endpoints or jobs are already running, but the user has not explicitly said allocation reuse is acceptable.
- You need evidence that a staging/control run allocated a fresh Slurm nodepool job and released it afterward.
- A manifest-driven launch fails and you need to separate control-plane, artifact, and probe-token-budget failures.
- You are investigating Inference360 issue 257, IFM corruption, converted checkpoint behavior, or parser-product versus true corruption classifications.
- You need a reproducible engine/checkpoint comparison across vLLM, SGLang, optional HF checkpoint, and optional native XLLM while preserving raw request/response JSONL, logprobs, token IDs, launch commands, and Slurm cleanup snapshots.
- You need a public, open-source-only SGLang reproducer for cache/prefix-cache numerical instability that uses `woywan/nanogpt` instead of IFM checkpoints or private artifact paths.
- You need to compare cached tail logits against cold-prefill logits across radix prefix cache and chunked prefill variants, including block-aligned and non-block-aligned prompt lengths.

## Verified Workflow

> Verification note: This is verified locally only. It was executed live on the
> H200 Slurm cluster and Inference360 control path on 2026-06-23, but not in CI.

### Quick Reference

```text
Rule: do not reuse existing model allocations for staging/control validation
unless the user explicitly asks for reuse.

1. Read the relevant Inference360 docs for the surface under test.
2. Identify occupied H200 nodes and exclude them from the temporary NodePool.
3. Start a temporary exclusive H200 8-GPU NodePool labeled for the staging test.
4. If Slurm control-plane startup fails, confirm it did not create a model
   allocation before switching to local foreground control.
5. Validate manifest artifact paths before relaunching a failed service.
6. Probe health, models, metrics, and chat completions with enough max_tokens
   for reasoning-heavy models.
7. For issue-257 style corruption repros, run the runbook-local
   engine/checkpoint comparison runner against each fresh endpoint variant.
8. For public SGLang cache-logits repros, use NanoGPT prepare-only first,
   then run the generated SGLang variants and compare cached tail logits
   against cold-prefill logits.
9. Stop the service, release the nodepool allocation, stop control, and verify
   the Slurm job leaves the queue.
```

Detailed workflow from the verified session:

1. Work from `/mnt/weka/home/micah.villmow/Inference360` on the H200 Slurm m2/mbzuai environment. The session date was 2026-06-23.
2. Read the relevant repo contract before acting: `README.md`, `AGENTS.md`, `docs/product-contracts.md`, `docs/runbooks/control-node-container.md`, and `docs/runbooks/ifm-cli.md`.
3. Do not probe an existing model endpoint as the validation path unless the user explicitly approves reuse. In the observed session, job `1764925` on `fs-mbz-gpu-824` for `inference-ifm-multi-model-vllm` was rejected as a reused allocation.
4. Exclude occupied H200 nodes from the temporary nodepool. The verified run excluded `fs-mbz-gpu-351`, `fs-mbz-gpu-718`, `fs-mbz-gpu-809`, `fs-mbz-gpu-824`, and `fs-mbz-gpu-862`.
5. Use a temporary exclusive H200 8-GPU NodePool labeled `purpose=staging-fresh-control-test`.
6. Try real Slurm control first when that is the requested path. In this session, control job `1782899` allocated `fs-mbz-cpu-007`, failed immediately with `sacct` state `FAILED 0:53`, and had no `slurm-1782899.out`. It did not create an H200 model allocation.
7. If the Slurm control job fails before model allocation, start local foreground control for the lifecycle run. The first local-control attempt at `127.0.0.1:28643` allocated fresh H200 nodepool job `1782954` on `fs-mbz-gpu-319`, but model start failed with HTTP 400 because the checked-in manifest pointed both `model.path` and `tokenizer_path` at missing artifact `/mnt/weka/shrd/k2m/suqi.sun/bbq_image/bbq-32b-mid3_v3/checkpoint_0005500`. Release that allocation before retrying.
8. Verify artifact facts before retrying:
   - Missing: `/mnt/weka/shrd/k2m/suqi.sun/bbq_image/bbq-32b-mid3_v3/checkpoint_0005500`
   - Exists: `/mnt/weka/shrd/k2m/suqi.sun/bbq_image/bbq-32b-mid3_v3/checkpoint_0002500`
   - Exists: `/mnt/weka/shrd/k2m/suqi.sun/bbq_image/bbq-4b-mid1_v3-final`
   - Exists: `/mnt/weka/shrd/k2m/suqi.sun/bbq_image/vllm-bbq-0518.sqsh`
   - 32B mid1 final existed, but the successful rerun used the current mid3 `checkpoint_0002500`.
9. Create a temporary manifest from `manifests/ifm-multi-model-experimental-m2.yaml` by replacing `checkpoint_0005500` with `checkpoint_0002500`. In the verified run this was `/tmp/ifm-multi-model-experimental-m2-checkpoint-0002500.yaml`.
10. Validate the temporary manifest through the Inference360 Python APIs: `load_manifest`, `resolve_manifest_for_cluster(..., "m2")`, and `validate_manifest`.
11. Start clean local control at `127.0.0.1:28644` with token `fresh-local-control-4b-32b-2` and registry `/tmp/inference360-fresh-4b-32b-localcontrol2/control-registry.json`.
12. Run the lifecycle launch through the control API. The successful run allocated fresh exclusive H200 nodepool job `1782986` on `fs-mbz-gpu-555`, with job name `i360-1b1fb993-fresh-h200-8gpu-node-1`.
13. Launch multi-model vLLM using `/mnt/weka/shrd/k2m/suqi.sun/bbq_image/vllm-bbq-0518.sqsh` and mount 32B `checkpoint_0002500` to `/models/32b`, 8B final to `/models/8b`, and 4B final to `/models/4b`.
14. Use this port and GPU layout: `IFM_32B` on port `18410`, GPUs `0,1,2,3`, tensor parallelism `4`; `IFM_8B` on port `18411`, GPUs `4,5`, tensor parallelism `2`; `IFM_4B` on port `18412`, GPU `6`, tensor parallelism `1`.
15. Include serving arguments `--gpu-memory-utilization 0.82`, `--reasoning-parser k2_v3`, `--tool-call-parser k2_v3`, and `--enable-auto-tool-choice`.
16. Probe with `/tmp/inference360_fresh_multimodel_probe.py`, checking `/health`, `/v1/models`, `/metrics`, and `/v1/chat/completions`. Use `max_tokens=128`; the status helper's `max_tokens=5` can yield blank content for reasoning-heavy models.
17. Cleanup is part of the validation, not an optional follow-up. Run `inference360 stop`, `inference360 release`, stop local control, then verify `squeue -j <nodepool-job-id>` becomes empty after `CG` teardown.

Issue 257 engine/checkpoint comparison extension from the verified 2026-06-25 session:

1. Keep one-off repro and debug scripts under `docs/runbooks/issue-257/`, not normal `scripts/` or test-package locations. This keeps issue-specific cluster probes near the runbook and out of reusable product surfaces.
2. Use the checked-in runner `docs/runbooks/issue-257/engine_checkpoint_compare_seed42.py` and smoke tests in `docs/runbooks/issue-257/engine_checkpoint_compare_seed42_smoke.py`.
3. Launch a fresh Inference360-managed H200 Slurm allocation through the control server for each endpoint variant. Do not reuse stale long-lived endpoints for corruption classification.
4. Use explicit request `seed=42`, `max_tokens=256`, and a sentinel `seed=0`.
5. For each endpoint variant, run these phases:
   - `seed42-standard`: three standard repeats.
   - `seed42-logprobs`: `logprobs=true`, `top_logprobs=5`.
   - `seed42-logprobs-token-ids`: `logprobs=true`, `top_logprobs=5`, `return_token_ids=true`.
   - `sentinel-seed0-standard`: standard request with `seed=0`.
6. Preserve full request and response JSONL, request/response SHA256s, prompt SHA, endpoint launch command in every trial row, `server.log`, Slurm job and node IDs, and `squeue`/`sacct` cleanup snapshots in the private artifact root.
7. Use `scripts/ifm_corruption_trials.py` to summarize logprob and token-ID presence/count fields while preserving the full raw response body.
8. For HF/native XLLM comparison on a cluster with those artifacts, run the same runner with `HF_MODEL_PATH`, `XLLM_MODEL_PATH`, `XLLM_TOKENIZER_PATH`, `XLLM_REPO`, and `XLLM_CONTAINER_IMAGE` set explicitly. If those paths are absent, record the path as skipped rather than pretending the comparison ran.
9. For handoff to another cluster, append a sanitized GitHub issue comment with checkout, env vars, live command, interpretation matrix, and artifact reporting expectations. Keep raw internal paths and Slurm metadata in private runbooks or artifact logs unless explicit approval is given.

Issue 257 public SGLang/NanoGPT cache-logits reproducer from the CI-verified PR #326 session:

1. Keep the public reproducer under `docs/runbooks/issue-257/`, next to the issue-specific runbook material, not under generic product scripts.
2. Use `docs/runbooks/issue-257/reproduce_sglang_nanogpt_cache_logits.py` and smoke tests in `docs/runbooks/issue-257/reproduce_sglang_nanogpt_cache_logits_smoke.py`.
3. Use public model `woywan/nanogpt`; do not require IFM checkpoints, internal endpoint names, private checkpoint paths, or private prompts.
4. Launch SGLang variants with radix prefix cache enabled/disabled and chunked prefill enabled/disabled. Compare cached tail logits against cold-prefill logits, not only cache-on variants against each other.
5. Cover both block-aligned and non-block-aligned prompt lengths. Keep prefix length fixed when changing aligned versus unaligned cases so the comparison isolates tail length.
6. Install a runtime `sitecustomize` patch that hooks `SGLang` `LogitsProcessor._get_logits` and dumps tensors per request. Do not modify the installed SGLang package in place.
7. Dump raw logits and normalized tail tensors to output files, then emit a markdown pass/fail table for the variant/case matrix.
8. Use `--prepare-only` when the agent only needs command plans and runtime patch artifacts, or when the active environment should not launch SGLang. Put generated artifacts in a private output directory.
9. Treat raw prompt, output, and logits artifacts as potentially sensitive. Do not commit generated artifacts if they include private prompts, endpoints, absolute infrastructure paths, or private model outputs.

Copy-paste issue-257 local validation commands:

```bash
cd /mnt/weka/home/micah.villmow/Inference360

.venv/bin/ruff check \
  scripts/ifm_corruption_trials.py \
  docs/runbooks/issue-257/engine_checkpoint_compare_seed42.py \
  docs/runbooks/issue-257/engine_checkpoint_compare_seed42_smoke.py

.venv/bin/ruff format --check \
  scripts/ifm_corruption_trials.py \
  docs/runbooks/issue-257/engine_checkpoint_compare_seed42.py \
  docs/runbooks/issue-257/engine_checkpoint_compare_seed42_smoke.py

.venv/bin/python -m pytest \
  docs/runbooks/issue-257/engine_checkpoint_compare_seed42_smoke.py

PYTHON=.venv/bin/python \
INFERENCE360=.venv/bin/inference360 \
scripts/validate.sh
```

Copy-paste public SGLang/NanoGPT reproducer validation commands:

```bash
cd /mnt/weka/home/micah.villmow/Projects/Inference360

.venv/bin/python -m py_compile \
  docs/runbooks/issue-257/reproduce_sglang_nanogpt_cache_logits.py

.venv/bin/python -m pytest \
  docs/runbooks/issue-257/reproduce_sglang_nanogpt_cache_logits_smoke.py

.venv/bin/python -m pytest \
  docs/runbooks/issue-257/reproduce_sglang_nanogpt_cache_logits_smoke.py \
  docs/runbooks/issue-257/reproduce_sglang_nanogpt_rmsnorm_smoke.py

.venv/bin/python docs/runbooks/issue-257/reproduce_sglang_nanogpt_cache_logits.py \
  --model woywan/nanogpt \
  --output-dir <private-output-dir> \
  --prepare-only
```

Copy-paste issue-257 comparison environment shape:

```bash
cd /mnt/weka/home/micah.villmow/Inference360
export LOG_ROOT=/mnt/weka/shrd/k2m/micah.villmow/debuglogs/inference360/257/runs

# Optional comparison paths only when visible on the current cluster.
export HF_MODEL_PATH=<hf-checkpoint-path>
export XLLM_MODEL_PATH=<xllm-model-path>
export XLLM_TOKENIZER_PATH=<xllm-tokenizer-path>
export XLLM_REPO=<xllm-repo-path>
export XLLM_CONTAINER_IMAGE=<xllm-container-image>

.venv/bin/python docs/runbooks/issue-257/engine_checkpoint_compare_seed42.py \
  --log-root "$LOG_ROOT" \
  --endpoint-name <endpoint-variant> \
  --base-url <fresh-endpoint-base-url> \
  --model IFM_4B \
  --launch-command '<exact fresh endpoint launch command>'
```

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
| ------- | -------------- | ------------- | -------------- |
| Reused existing allocation | Probed existing job `1764925` on `fs-mbz-gpu-824` for `inference-ifm-multi-model-vllm` | The user explicitly did not want allocation reuse for staging/control validation | Treat fresh allocation as the default unless reuse is explicitly requested |
| Slurm control job first | Started real Slurm control job `1782899` on `fs-mbz-cpu-007` | It failed immediately with `sacct` state `FAILED 0:53` and no `slurm-1782899.out`; it did not create an H200 model allocation | Confirm control-plane failure did not leak a model allocation before switching to local foreground control |
| Missing 32B checkpoint | Local control at `127.0.0.1:28643` allocated job `1782954` on `fs-mbz-gpu-319`, then launched the checked-in manifest | Model start returned HTTP 400 because `checkpoint_0005500` was missing for both model and tokenizer paths | Validate artifact paths and use a temporary manifest pointing at the existing `checkpoint_0002500` before retrying |
| Too-small chat probe token budget | Used the status helper behavior with `max_tokens=5` as the chat-completion readiness probe | Reasoning-heavy models can return blank content with such a small budget even when the endpoint is healthy | Probe with `max_tokens=128` and require nonempty content plus `finish_reason` of `stop` |
| Raw artifact issue comment | Tried to post a detailed GitHub issue comment with raw internal artifact paths and Slurm metadata | The platform blocked the disclosure; a sanitized comment succeeded | Keep exact private paths in private artifacts/runbooks and use sanitized issue comments unless explicit approval is given |
| Assumed SGLang existed in multi-model image | Tried to use the vLLM/XLLM image with `/opt/venv/bin/python` for SGLang | The image failed with `No module named sglang` | Verify the runtime image and Python path before treating an engine variant as tested |
| SGLang parser flags on incompatible build | Started the dedicated SGLang image with IFM parser flags | That SGLang build rejected `--reasoning-parser ifm` | Parser flag compatibility is engine-build-specific; separate parser flag incompatibility from model generation behavior |
| SGLang without parser flags on converted checkpoint | Started the dedicated SGLang image without parser flags | Startup reached checkpoint loading but failed importing converted checkpoint remote code with `TypeError: check_model_inputs() missing 1 required positional argument: 'func'` | Do not classify startup/import failures as clean SGLang model behavior; record them as runtime compatibility blockers |
| Raw legacy model naming in tracked logical surfaces | Used raw legacy naming directly where repository guard tests inspect logical surfaces | Naming guard tests rejected the tracked surface | Construct legacy path stems in code when needed or keep raw details in external artifact logs |
| IFM/private-path public repro | Tried to frame the public issue 257 reproducer around IFM models, internal endpoints, or absolute checkpoint paths | That would make the reproducer unusable publicly and risk leaking operational details | Use `woywan/nanogpt`, public SGLang, sanitized command plans, and private output directories |
| Cache-on-only comparison | Compared SGLang cache-enabled variants against each other | Two cache-enabled paths can share the same numerical defect and mask the instability | Compare cached tail logits against a cold-prefill baseline |
| Moving prefix length between cases | Changed both prefix length and tail shape while testing aligned versus unaligned prompts | The result no longer isolated the tail-length/block-boundary effect | Keep prefix length fixed and vary the tail case deliberately |
| Committing raw generated artifacts | Considered checking in prompt/output/logit dumps for convenience | Raw outputs can contain private prompts, endpoints, paths, or model artifacts | Commit the reproducer and smoke tests only; keep generated outputs in private artifact roots |

## Results & Parameters

Successful probe results came from
`/tmp/inference360-fresh-4b-32b-localcontrol2/06-fresh-api-probe.json`:

```text
status: ok

IFM_32B
base_url: http://fs-mbz-gpu-555:18410
health: HTTP 200
models: HTTP 200, [IFM_32B]
metrics: HTTP 200
chat: HTTP 200
chat_content: "4"
finish_reason: stop
latency_ms: 2038.5
usage.total_tokens: 93

IFM_4B
base_url: http://fs-mbz-gpu-555:18412
health: HTTP 200
models: HTTP 200, [IFM_4B]
metrics: HTTP 200
chat: HTTP 200
chat_content: "4"
finish_reason: stop
latency_ms: 1758.4
usage.total_tokens: 103
```

Cleanup evidence:

```text
inference360 stop stopped server ifm-multi-model-bbq-vllm:fs-mbz-gpu-555
inference360 release released fs-mbz-gpu-555
local control exited
squeue -j 1782986 became empty after CG teardown
```

Important operational parameters:

- Temporary NodePool label: `purpose=staging-fresh-control-test`
- Successful fresh nodepool job: `1782986`
- Successful H200 node: `fs-mbz-gpu-555`
- Successful local control endpoint: `127.0.0.1:28644`
- Successful local control token: `fresh-local-control-4b-32b-2`
- Successful control registry: `/tmp/inference360-fresh-4b-32b-localcontrol2/control-registry.json`
- Temporary manifest: `/tmp/ifm-multi-model-experimental-m2-checkpoint-0002500.yaml`
- Verification level: `verified-local`, not `verified-ci`

Issue 257 observed results from branch `investigate/257-engine-checkpoint-compare`, commit `f155b1f`, PR <https://github.com/LLM360/Inference360/pull/279>:

```text
Issue: https://github.com/LLM360/Inference360/issues/257
Runbook runner: docs/runbooks/issue-257/engine_checkpoint_compare_seed42.py
Runbook smoke: docs/runbooks/issue-257/engine_checkpoint_compare_seed42_smoke.py
Trial logger: scripts/ifm_corruption_trials.py
Detailed runbook: docs/runbooks/ifm-issue-257-corruption-investigation.md

vLLM converted checkpoint:
  seed42-standard: corruption reproduced in 3/3 repeats
  seed42-logprobs: corruption reproduced; 256 completion logprob entries and 1280 top-logprob entries
  seed42-logprobs-token-ids: corruption reproduced; 108 prompt token IDs and 256 completion token IDs
  sentinel-seed0-standard: did not classify as corruption; classified as parser_product

HF/native XLLM:
  exact 4B mid1 paths were not visible on the M2 host
  runner records skipped unless explicit env vars are provided

SGLang:
  vLLM/XLLM image lacked the sglang module
  dedicated SGLang image rejected IFM parser flags
  dedicated SGLang image without parser flags failed importing converted checkpoint remote code

Interpretation:
  current evidence gives concrete token IDs/logprobs for the corrupt vLLM path
  SGLang/HF/native XLLM comparison needs a compatible original checkpoint/runtime on another cluster
```

Issue 257 validation evidence:

```text
.venv/bin/ruff check ... passed
.venv/bin/ruff format --check ... passed
.venv/bin/python -m pytest docs/runbooks/issue-257/engine_checkpoint_compare_seed42_smoke.py passed, 4 tests
PYTHON=.venv/bin/python INFERENCE360=.venv/bin/inference360 scripts/validate.sh passed, 819 passed, 8 skipped
just validate was not usable because just resolved to a broken Python shim
PR CI at last poll: CodeQL/secrets/SAST/SCA green; validate still in progress
```

Issue 257 public SGLang/NanoGPT cache-logits reproducer from Inference360 PR #326:

```text
Issue: https://github.com/LLM360/Inference360/issues/257
PR: https://github.com/LLM360/Inference360/pull/326
Runner: docs/runbooks/issue-257/reproduce_sglang_nanogpt_cache_logits.py
Smoke tests: docs/runbooks/issue-257/reproduce_sglang_nanogpt_cache_logits_smoke.py
Model: woywan/nanogpt

Behavior covered:
  radix prefix cache enabled and disabled
  chunked prefill enabled and disabled
  block-aligned and non-block-aligned prompt lengths
  cached tail logits versus cold-prefill logits
  raw logits and normalized tail tensor dumps
  markdown pass/fail summary table
  --prepare-only command-plan/runtime-patch generation

Implementation detail:
  runtime sitecustomize patch hooks SGLang LogitsProcessor._get_logits
  and dumps per-request tensors without editing the installed SGLang package

Verification:
  py_compile on reproducer passed
  pytest docs/runbooks/issue-257/reproduce_sglang_nanogpt_cache_logits_smoke.py passed
  combined smoke suite with RMSNorm tests passed 11 tests
  GitHub PR #326 checks passed after integration
```

## Verified On

| Project | Context | Details |
| ------- | ------- | ------- |
| LLM360/Inference360 | H200 Slurm m2/mbzuai fresh-allocation staging/control validation for IFM 4B and 32B on 2026-06-23 | Live control/API probes passed for fresh job `1782986` on `fs-mbz-gpu-555`, and the allocation was released afterward. |
| LLM360/Inference360 | Issue 257 IFM 4B converted-checkpoint corruption comparison on 2026-06-25 | Fresh-control H200 repro workflow produced vLLM seed-42 corruption evidence with logprobs/token IDs; HF/native XLLM and compatible SGLang comparison remained blocked on missing/compatible runtime paths. |
| LLM360/Inference360 | Issue 257 public SGLang/NanoGPT cache-logits reproducer in PR #326 on 2026-07-02 | Public open-source-only reproducer and smoke tests passed CI after integration, including cache-logits smoke and combined RMSNorm smoke coverage. |
