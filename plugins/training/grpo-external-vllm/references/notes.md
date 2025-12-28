# Notes

Raw findings from GRPO external vLLM experiments.

## Key Insight

The main breakthrough was realizing that `vllm_skip_weight_sync` errors weren't
a configuration issue but a fundamental limitation of inline vLLM with GRPO.
Using an external server completely sidesteps the weight synchronization problem.

## Error Messages Encountered

```text
RuntimeError: vllm_skip_weight_sync is True but model weights have diverged
```

```text
torch.cuda.OutOfMemoryError: CUDA out of memory. Tried to allocate 2.00 GiB
```

## Timeline

- Day 1: Tried inline vLLM, hit OOM
- Day 2: Added vllm_skip_weight_sync, worked initially then diverged
- Day 3: Set up external server, everything worked
