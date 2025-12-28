---
name: grpo-external-vllm
description: "GRPO training with external vLLM server for distributed GPU setups"
category: training
source: ProjectOdyssey
date: 2025-12-28
---

# GRPO External vLLM Server

Configure GRPO (Group Relative Policy Optimization) training with an external vLLM inference server.

## Overview

| Item | Details |
|------|---------|
| Date | 2025-12-28 |
| Objective | Train LLM with GRPO using separate inference server |
| Outcome | Success |

## When to Use

- Running vLLM inference on separate GPUs from training
- Encountering `vllm_skip_weight_sync` errors with inline vLLM
- OpenAI API response parsing issues with TRL
- Memory-constrained environments needing GPU separation

## Verified Workflow

1. **Start external vLLM server** on dedicated GPU(s):

   ```bash
   CUDA_VISIBLE_DEVICES=4,5,6,7 python -m vllm.entrypoints.openai.api_server \
     --model google/gemma-3-12b-it \
     --port 8000 \
     --tensor-parallel-size 4
   ```

2. **Configure TRL trainer** to use external server:

   ```python
   from trl import GRPOConfig, GRPOTrainer

   config = GRPOConfig(
       use_vllm=True,
       vllm_server_host="localhost",
       vllm_server_port=8000,
       # Disable inline vLLM
       vllm_gpu_memory_utilization=0.0,
   )
   ```

3. **Run training** on remaining GPUs:

   ```bash
   CUDA_VISIBLE_DEVICES=0,1,2,3 python train_grpo.py
   ```

## Failed Attempts

| Attempt | Why Failed | Lesson |
|---------|-----------|--------|
| Inline vLLM on same GPUs | OOM - training + inference compete for memory | Separate inference to dedicated GPUs |
| `vllm_skip_weight_sync=True` | Weights diverge after few steps | External server avoids sync issues |
| batch_size=16 | Gradient overflow with large batches | Use batch_size=4, increase gradient_accumulation |
| Default OpenAI parsing | TRL expected different response format | Use `--chat-template` flag on server |

## Results & Parameters

```yaml
# Training config
model: google/gemma-3-12b-it
batch_size: 4
gradient_accumulation_steps: 4
learning_rate: 1e-5
max_steps: 1000
warmup_steps: 100

# vLLM server config
tensor_parallel_size: 4
max_model_len: 4096
gpu_memory_utilization: 0.9

# Hardware
training_gpus: 4x A100 80GB
inference_gpus: 4x A100 80GB
```

## References

- TRL GRPO documentation: https://huggingface.co/docs/trl/grpo_trainer
- vLLM OpenAI server: https://docs.vllm.ai/en/latest/serving/openai_compatible_server.html
- Related: debugging/vllm-weight-sync
