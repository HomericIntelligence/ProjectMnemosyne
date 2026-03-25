# Session Notes: Baseten + Miles GRPO External Inference

## Session Context

Date: 2026-03-25
User: Setting up RL training pipeline with Baseten (inference) + Miles (training)
Target: Qwen3-4B for E2E testing, scaling to Qwen3.5-397B MoE later

## Key Technical Discoveries

### 1. Baseten URL Pattern

Baseten wraps vLLM behind its API gateway. Tried multiple URL patterns:

| URL Tried | Result |
|-----------|--------|
| `https://model-{ID}.api.baseten.co/v1/chat/completions` | 404 |
| `https://model-{ID}.api.baseten.co/production/v1/chat/completions` | 404 |
| `https://model-{ID}.api.baseten.co/production/v1` | 404 |
| `https://model-{ID}.api.baseten.co/production` | 404 |
| **`https://model-{ID}.api.baseten.co/production/predict`** | **200** |

The `/predict` endpoint accepts standard OpenAI chat completion payloads and returns standard OpenAI responses.

### 2. Miles Architecture Deep Dive

Miles has two rollout paths:

**Path A (default)**: SGLang-based
- `OpenAIEndpointTracer` creates sessions via `POST /sessions` on Miles router
- Agent function sends to `router_url/sessions/{id}/v1/chat/completions`
- Router proxies to SGLang and records request/response
- `collect_records()` gets data via `GET /sessions/{id}`
- Requires local Miles router + SGLang server

**Path B (custom)**: Direct endpoint
- Set `MILES_EXPERIMENTAL_ROLLOUT_REFACTOR=1`
- `--custom-generate-function-path` points to your async generate function
- Function receives `GenerateFnInput` (sample, state.tokenizer, sampling_params)
- Function returns `GenerateFnOutput` (constructed Sample objects)
- No router needed

### 3. Miles Sample Construction

Critical fields for GRPO training:
```python
sample.tokens = prompt_token_ids + output_token_ids  # from tokenizer + logprobs.token_id
sample.rollout_log_probs = [item["logprob"] for item in logprobs.content]
sample.loss_mask = [1] * len(output_token_ids)  # train on all output tokens
sample.response = message_content
sample.response_length = len(output_token_ids)
sample.status = Sample.Status.COMPLETED  # or TRUNCATED/ABORTED
```

### 4. Baseten vLLM Logprobs Format

```json
{
  "choices": [{
    "logprobs": {
      "content": [
        {"token": "<think>", "token_id": 151667, "logprob": -0.0000, "top_logprobs": [...]},
        {"token": "\n", "token_id": 198, "logprob": -0.0234, "top_logprobs": [...]}
      ]
    }
  }]
}
```

`token_id` field is present in Baseten's vLLM responses (vllm/vllm-openai:latest).

### 5. Slurm + Enroot Notes

- Use `srun --container-image=path.sqsh --container-mounts=src:dst` for Enroot
- `enroot import -o /path/output.sqsh docker://image:tag` to import
- Don't `source` one sbatch from another — Slurm only parses SBATCH directives from the submitted file
- `PYTHONBUFFERED=16` is a Miles convention (from their example scripts), not standard Python

## Files Created

- `~/work/qwen3-4b-baseten/config.yaml` — Truss config
- `~/work/miles-training/baseten_generate.py` — Custom generate function
- `~/work/scripts/slurm/train-grpo.sbatch` — Slurm smoke test
- `~/work/scripts/slurm/train-grpo-production.sbatch` — Production run
- `~/work/scripts/{env,test-baseten,check-status}.sh` — Helper scripts
- `~/work/REPORT-baseten-miles-grpo-training.md` — Full report (979 lines)

## References

- Miles repo: https://github.com/radixark/miles
- Baseten docs: https://docs.baseten.co/development/model/build-your-first-model
- Truss examples: https://github.com/basetenlabs/truss-examples
- Miles OpenAI format example: `miles/examples/openai_format/run-qwen3-4B.sh`
- Miles custom generate: `miles/miles/rollout/generate_hub/agentic_tool_call.py`
- Miles FSDP MoE support: `miles/miles/backends/fsdp_utils/models/qwen3_moe.py`
