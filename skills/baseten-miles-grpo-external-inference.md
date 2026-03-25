---
name: baseten-miles-grpo-external-inference
description: "GRPO training with Miles RL framework using Baseten-hosted vLLM as external inference endpoint. Use when: (1) running GRPO training with a remote OpenAI-compatible inference server, (2) integrating Baseten with Miles bypassing the SGLang router, (3) deploying a model on Baseten for RL training rollouts."
category: training
date: "2026-03-25"
version: "1.0.0"
user-invocable: false
tags:
  - grpo
  - baseten
  - miles
  - vllm
  - rl-training
  - external-inference
  - slurm
  - enroot
---

# Baseten + Miles GRPO External Inference

## Overview

| Field | Value |
|-------|-------|
| **Date** | 2026-03-25 |
| **Objective** | Run GRPO training using Miles RL framework with a Baseten-hosted Qwen3-4B (vLLM) as the external inference endpoint for rollout generation |
| **Outcome** | Operational — Baseten endpoint deployed and verified, custom generate function written and validated against Miles type system, Slurm+Enroot training scripts ready |

## When to Use

- Running GRPO (or other RL) training where inference and training are on separate infrastructure
- Integrating Baseten's hosted vLLM with Miles RL framework
- Bypassing Miles' built-in SGLang router/session mechanism for external API-based inference
- Deploying models on Baseten via Truss CLI for RL training rollouts
- Setting up Slurm+Enroot jobs for Miles training on HPC clusters

## Verified Workflow

### Quick Reference

```bash
# Deploy model to Baseten
pip install truss && truss login
cd /path/to/truss-config/ && truss push

# Baseten API call (correct URL pattern)
curl -X POST "https://model-{MODEL_ID}.api.baseten.co/production/predict" \
    -H "Authorization: Api-Key {KEY}" \
    -H "Content-Type: application/json" \
    -d '{"messages":[{"role":"user","content":"hi"}],"model":"Qwen/Qwen3-4B","max_tokens":4,"logprobs":true}'

# Check deployment status
curl -s "https://api.baseten.co/v1/models/{MODEL_ID}/deployments/{DEPLOY_ID}" \
    -H "Authorization: Api-Key {KEY}"

# Submit Miles training via Slurm+Enroot
export BASETEN_API_KEY="your-key"
sbatch train-grpo.sbatch
```

### Detailed Steps

1. **Deploy inference model on Baseten**: Create a `config.yaml` with vLLM docker_server config, `truss push` to deploy. Baseten wraps vLLM behind `/production/predict` endpoint.

2. **Verify logprobs**: GRPO requires `logprobs=true` in requests. Baseten's vLLM returns `token_id` and `logprob` in `choices[0].logprobs.content[]` items.

3. **Write custom generate function**: Miles normally uses a local SGLang router with session tracking (`OpenAIEndpointTracer`). For external endpoints like Baseten, write a custom `baseten_generate.py` that:
   - Implements `async def generate(input: GenerateFnInput) -> GenerateFnOutput`
   - Calls Baseten directly via httpx with `Api-Key` auth header
   - Constructs Miles `Sample` objects from the OpenAI response (tokens, rollout_log_probs, loss_mask, status)
   - Attaches `generate.add_arguments = _add_arguments` for Miles CLI integration

4. **Enable experimental rollout**: Set `MILES_EXPERIMENTAL_ROLLOUT_REFACTOR=1` env var and use `--custom-generate-function-path baseten_generate.generate`

5. **Run training**: Use FSDP backend (`--train-backend fsdp`) which loads HF checkpoints directly (no Megatron conversion needed). Use `--gradient-checkpointing` for memory efficiency.

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
|---------|----------------|---------------|----------------|
| Using Miles' built-in OpenAI format path (`agentic_tool_call.generate` + `dapo_math.run_agent`) | Tried to swap the base_url to point at Baseten instead of local SGLang | The `OpenAIEndpointTracer` creates sessions via `POST /sessions` on the local Miles router, which doesn't exist on Baseten. The agent function sends requests through `router_url/sessions/{id}/v1/chat/completions` — a Miles-specific protocol, not standard OpenAI. | Must write a custom generate function that bypasses the router entirely when using external inference. |
| Using `--rollout-external` with `--rollout-external-engine-addrs` | Tried Miles' native external engine support to point at Baseten | `--rollout-external` expects SGLang-native endpoints (with `/generate` and router worker registration via `POST /add_worker`), not OpenAI-compatible endpoints. Baseten serves `/v1/chat/completions` via vLLM. | `--rollout-external` is for external SGLang instances only, not arbitrary OpenAI endpoints. |
| Using `miles.utils.http_utils.post` in agent function for Baseten | Tried using Miles' built-in async HTTP client to call Baseten | Miles' `_http_client` is a plain `httpx.AsyncClient` with no auth headers. Baseten requires `Api-Key` authentication in the `Authorization` header. | Use your own httpx client with custom headers for authenticated endpoints. |
| URL pattern `/production/v1/chat/completions` | Assumed Baseten exposes vLLM's endpoint path directly | Returns 404. Baseten wraps vLLM behind `/production/predict` — a Baseten-specific gateway pattern. Also tried `/v1/chat/completions` (404) and `/production` (404). | The correct Baseten URL is `https://model-{ID}.api.baseten.co/production/predict`. |
| `train-grpo-production.sbatch` sourcing base sbatch | Production sbatch used `source train-grpo.sbatch` to reuse the srun command | Slurm only parses `#SBATCH` directives from the submitted file, not sourced files. The production SBATCH directives (24hr time) were used but the base file's directives were silently ignored. Confusing and fragile. | Make each sbatch file standalone. Don't source one sbatch from another. |
| CPU-only training on 16GB RAM machine | Tried to run FSDP with `--fsdp-cpu-offload` and `--actor-num-gpus-per-node 0` | Qwen3-4B needs ~16GB for weights alone (fp32), plus ~32GB for Adam optimizer states. FSDP CPU offload still requires at least 1 GPU for forward/backward passes. | FSDP CPU offload reduces GPU memory but doesn't eliminate GPU requirement. Need at least 1 GPU with 24GB+ VRAM. |

## Results & Parameters

### Baseten Deployment Config (Qwen3-4B)

```yaml
# config.yaml for truss push
model_name: Qwen3-4B
base_image:
  image: vllm/vllm-openai:latest
docker_server:
  start_command: >
    sh -c "python3 -m vllm.entrypoints.openai.api_server
    --model Qwen/Qwen3-4B --host 0.0.0.0 --port 8000
    --served-model-name Qwen/Qwen3-4B --tensor-parallel-size 1
    --trust-remote-code --max-num-seqs 32 --max-num-batched-tokens 4096
    --enable-prefix-caching"
  predict_endpoint: /v1/chat/completions
  server_port: 8000
resources:
  accelerator: L4
  use_gpu: true
```

### Miles GRPO Training Parameters

```yaml
# Smoke test (5 steps)
advantage-estimator: grpo
train-backend: fsdp
gradient-checkpointing: true
rollout-batch-size: 4
n-samples-per-prompt: 2
rollout-max-response-len: 1024
global-batch-size: 8
max-steps: 5
lr: 1e-6

# Production
rollout-batch-size: 32
n-samples-per-prompt: 8
rollout-max-response-len: 8192
global-batch-size: 256
max-steps: 1000
```

### Key Environment Variables

```bash
BASETEN_API_KEY="your-key"
BASETEN_MODEL_URL="https://model-{ID}.api.baseten.co/production"
MODEL_NAME="Qwen/Qwen3-4B"
MILES_EXPERIMENTAL_ROLLOUT_REFACTOR=1
PYTHONBUFFERED=16  # Miles convention, not standard Python PYTHONUNBUFFERED
```

### Baseten API Pattern

```
Auth header:   Authorization: Api-Key {key}
Endpoint:      POST https://model-{ID}.api.baseten.co/production/predict
Status API:    GET  https://api.baseten.co/v1/models/{ID}/deployments/{DEPLOY_ID}
Cost:          L4 ~$0.85/hr, B200 ~$9.98/hr (auto-scales to 0)
```

## Verified On

| Project | Context | Details |
|---------|---------|---------|
| Baseten + Miles GRPO Pipeline | Qwen3-4B E2E training setup | [notes](./baseten-miles-grpo-external-inference.notes.md) |
