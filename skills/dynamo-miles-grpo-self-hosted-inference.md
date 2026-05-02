---
name: dynamo-miles-grpo-self-hosted-inference
description: "GRPO training with Miles RL framework using NVIDIA Dynamo as self-hosted multi-node inference orchestrator with SGLang backend. Use when: (1) running GRPO training with self-hosted distributed inference instead of cloud, (2) integrating NVIDIA Dynamo with Miles, (3) deploying multi-node SGLang inference via Dynamo on a Slurm+Enroot cluster."
category: training
date: "2026-03-25"
version: "1.0.0"
user-invocable: false
verification: unverified
tags:
  - grpo
  - dynamo
  - nvidia
  - miles
  - sglang
  - rl-training
  - self-hosted
  - slurm
  - enroot
  - distributed-inference
---

# Dynamo + Miles GRPO Self-Hosted Inference

## Overview

| Field | Value |
| ------- | ------- |
| **Date** | 2026-03-25 |
| **Objective** | Run GRPO training using Miles RL framework with NVIDIA Dynamo as a self-hosted multi-node inference orchestrator (SGLang backend) instead of a cloud service like Baseten |
| **Outcome** | Scripts and integration code ready, awaiting cluster execution for validation |
| **Verification** | unverified — custom generate function validated against Miles type system but not executed end-to-end |

## When to Use

- Running GRPO training where both inference and training run on your own cluster (not cloud)
- Deploying NVIDIA Dynamo for multi-node distributed inference with SGLang backend
- Integrating Dynamo's OpenAI-compatible API with Miles' custom generate function
- Setting up a two-job Slurm pattern: inference cluster + training job
- Scaling inference across multiple nodes with Dynamo's KV-aware routing and disaggregated serving

## Verified Workflow

> **Warning:** This workflow has not been validated end-to-end on a real cluster. The custom generate function and Slurm scripts are ready but untested. Treat as a high-confidence hypothesis based on the proven Baseten integration pattern.

### Quick Reference

```bash
# Start Dynamo with SGLang (single-node testing)
python3 -m dynamo.frontend --http-port 8000 --discovery-backend file &
python3 -m dynamo.sglang --model-path Qwen/Qwen3-4B --served-model-name Qwen/Qwen3-4B \
    --tp 1 --trust-remote-code --skip-tokenizer-init --discovery-backend file &

# Test endpoint (standard OpenAI API, no auth)
curl -X POST http://localhost:8000/v1/chat/completions \
    -H "Content-Type: application/json" \
    -d '{"model":"Qwen/Qwen3-4B","messages":[{"role":"user","content":"2+2?"}],"logprobs":true,"max_tokens":16}'

# Slurm: start inference cluster then training
DYNAMO_JOB=$(sbatch --parsable start-dynamo-cluster.sbatch)
DYNAMO_JOB_ID=$DYNAMO_JOB sbatch train-grpo-dynamo.sbatch
```

### Detailed Steps

1. **Build/import Dynamo container**: `enroot import -o dynamo-sglang.sqsh docker://nvcr.io/nvidia/ai-dynamo/sglang-runtime:1.0.1` (v1.0.1+ required for logprobs)

2. **Download model/data**: Qwen3-4B (~8GB) and dapo-math-17k dataset to shared filesystem

3. **Copy `dynamo_generate.py`** to shared filesystem — this is the custom Miles generate function that calls Dynamo directly

4. **Submit Dynamo inference cluster** (Slurm Job 1): Starts Dynamo frontend + SGLang workers across N nodes. Writes frontend URL to a shared file.

5. **Submit Miles training** (Slurm Job 2): Reads Dynamo frontend URL, starts Miles GRPO training with `--custom-generate-function-path dynamo_generate.generate`. FSDP backend, 8x H100 training node.

6. **Verify**: Check Slurm logs for GRPO loss values, checkpoint saves, and Dynamo health

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
| --------- | ---------------- | --------------- | ---------------- |
| Miles `--rollout-external` with Dynamo | Tried to use Miles' native external SGLang engine support to connect to Dynamo's frontend | Miles' `--rollout-external` requires SGLang-native endpoints: `/generate`, `/health_generate`, `/get_server_info`, and worker registration via `POST /add_worker`. Dynamo only exposes OpenAI-compatible `/v1/chat/completions` through its frontend. The native SGLang endpoints are not proxied. | `--rollout-external` is for direct SGLang engine connections only. For any frontend that wraps SGLang (like Dynamo), use a custom generate function instead. |
| Dynamo v1.0.0 for logprobs | Initially researched v1.0.0 release | v1.0.0 had a critical bug where logprobs fields weren't populated when requests routed through Dynamo Frontend. Fixed in v1.0.1. | Always use Dynamo v1.0.1+ for GRPO training. The `bytes` and `token` fields are now properly populated. |
| Sourcing one sbatch from another | Production sbatch tried to `source` base sbatch to reuse training logic | Slurm only parses `#SBATCH` directives from the submitted file. Sourced files' `#SBATCH` lines are treated as comments. | Make each sbatch standalone, or use `bash script.sh` (not `source`) where the base file's SBATCH lines become harmless comments since Slurm already allocated resources from the calling file. |
| Miles' `OpenAIEndpointTracer` with Dynamo | Considered using Miles' built-in OpenAI format path (`agentic_tool_call.generate`) pointing at Dynamo | The `OpenAIEndpointTracer` creates sessions via `POST /sessions` on the local Miles router — a Miles-specific protocol. Dynamo doesn't implement this. | Same lesson as Baseten: for any external OpenAI-compatible endpoint, bypass the Miles router entirely with a custom generate function. |

## Results & Parameters

### Dynamo Deployment

```yaml
# Docker image (v1.0.1+ required for logprobs)
image: nvcr.io/nvidia/ai-dynamo/sglang-runtime:1.0.1

# API endpoint (standard OpenAI, no auth)
endpoint: /v1/chat/completions
health: /health
port: 8000

# Discovery backends
testing: file
production: etcd

# SGLang worker args
tp: 1  # tensor parallelism per worker
discovery-backend: file
skip-tokenizer-init: true
enable-metrics: true
```

### Dynamo vs Baseten

| Aspect | Baseten | Dynamo |
| -------- | --------- | -------- |
| Location | Cloud (remote HTTPS) | Self-hosted (cluster LAN) |
| Auth | `Api-Key` header required | None (internal network) |
| Endpoint | `/production/predict` | `/v1/chat/completions` (standard) |
| Latency | ~100-500ms per request | ~1-10ms per request |
| Setup | `truss push` (simple) | Build container + Slurm jobs (complex) |
| Cost | Per-hour billing | Your hardware |
| Weight sync | Models always diverge | Potential hot-reload via `/engine/update_weights_from_distributor` |
| Scaling | Baseten auto-scales | Manual node allocation |

### Miles Training Parameters (same as Baseten)

```yaml
# Smoke test (5 steps)
advantage-estimator: grpo
train-backend: fsdp
gradient-checkpointing: true
rollout-batch-size: 4
n-samples-per-prompt: 2
global-batch-size: 8
max-steps: 5
lr: 1e-6

# Production
rollout-batch-size: 32
n-samples-per-prompt: 8
global-batch-size: 256
max-steps: 1000
```

### Environment Variables

```bash
DYNAMO_URL="http://localhost:8000"  # or http://dynamo-head-node:8000
MODEL_NAME="Qwen/Qwen3-4B"
MILES_EXPERIMENTAL_ROLLOUT_REFACTOR=1
PYTHONBUFFERED=16  # Miles convention
```

### Key Dynamo Features for Scaling

```yaml
# Disaggregated serving (prefill/decode split)
prefill_worker: --disaggregation-mode prefill --disaggregation-bootstrap-port 12345
decode_worker: --disaggregation-mode decode --disaggregation-bootstrap-port 12345
kv_transfer: nixl  # Zero-copy GPU-to-GPU via RDMA

# Weight updates (potential training integration)
weight_update_endpoint: POST /engine/update_weights_from_distributor
system_port: 8081
```

## Verified On

| Project | Context | Details |
| --------- | --------- | --------- |
| Dynamo + Miles GRPO Pipeline | Qwen3-4B E2E training on Slurm+Enroot cluster | [notes](./dynamo-miles-grpo-self-hosted-inference.notes.md) |
