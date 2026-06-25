---
name: inference360-staging-fresh-allocation-control
description: "Validate Inference360 staging/control API launches on fresh H200 Slurm allocations. Use when: (1) proving IFM or multi-model vLLM endpoints through the Inference360 control API, (2) the user asks for staging/control validation and has not explicitly approved reusing an existing allocation, (3) checking that Slurm nodepool allocations are released after live probes."
category: testing
date: 2026-06-23
version: "1.0.0"
user-invocable: false
verification: verified-local
tags: [inference360, slurm, h200, control, staging, vllm, nodepool]
---

# Inference360 Fresh-Allocation Staging Control Validation

## Overview

| Field | Value |
| ------- | ------- |
| **Date** | 2026-06-23 |
| **Objective** | Run Inference360 staging/control tests for IFM 4B and 32B through the Inference360 API without reusing existing model allocations. |
| **Outcome** | Successful local end-to-end cluster/control validation on m2/mbzuai using a fresh exclusive H200 8-GPU NodePool allocation, followed by release verification. |
| **Verification** | verified-local. The workflow ran live on the H200 Slurm cluster and control path, but was not verified in CI. |

## When to Use

- The user asks to validate Inference360 staging, control API, or lifecycle behavior for IFM, multi-model vLLM, or similar H200 Slurm services.
- Existing endpoints or jobs are already running, but the user has not explicitly said allocation reuse is acceptable.
- You need evidence that a staging/control run allocated a fresh Slurm nodepool job and released it afterward.
- A manifest-driven launch fails and you need to separate control-plane, artifact, and probe-token-budget failures.

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
7. Stop the service, release the nodepool allocation, stop control, and verify
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

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
| ------- | -------------- | ------------- | -------------- |
| Reused existing allocation | Probed existing job `1764925` on `fs-mbz-gpu-824` for `inference-ifm-multi-model-vllm` | The user explicitly did not want allocation reuse for staging/control validation | Treat fresh allocation as the default unless reuse is explicitly requested |
| Slurm control job first | Started real Slurm control job `1782899` on `fs-mbz-cpu-007` | It failed immediately with `sacct` state `FAILED 0:53` and no `slurm-1782899.out`; it did not create an H200 model allocation | Confirm control-plane failure did not leak a model allocation before switching to local foreground control |
| Missing 32B checkpoint | Local control at `127.0.0.1:28643` allocated job `1782954` on `fs-mbz-gpu-319`, then launched the checked-in manifest | Model start returned HTTP 400 because `checkpoint_0005500` was missing for both model and tokenizer paths | Validate artifact paths and use a temporary manifest pointing at the existing `checkpoint_0002500` before retrying |
| Too-small chat probe token budget | Used the status helper behavior with `max_tokens=5` as the chat-completion readiness probe | Reasoning-heavy models can return blank content with such a small budget even when the endpoint is healthy | Probe with `max_tokens=128` and require nonempty content plus `finish_reason` of `stop` |

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

## Verified On

| Project | Context | Details |
| ------- | ------- | ------- |
| LLM360/Inference360 | H200 Slurm m2/mbzuai fresh-allocation staging/control validation for IFM 4B and 32B on 2026-06-23 | Live control/API probes passed for fresh job `1782986` on `fs-mbz-gpu-555`, and the allocation was released afterward. |
