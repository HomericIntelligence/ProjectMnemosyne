# Session Notes: Dynamo + Miles GRPO Self-Hosted Inference

## Session Context

Date: 2026-03-25
User: Setting up RL training with self-hosted NVIDIA Dynamo (SGLang) + Miles on Slurm+Enroot cluster
Cluster: Dozens of 8x H100 80GB nodes
Prior work: Baseten + Miles integration completed in same session (see baseten-miles-grpo-external-inference skill)

## Key Technical Discoveries

### 1. Dynamo Does NOT Expose SGLang Native Endpoints

Dynamo's frontend only proxies these endpoints:
- `/v1/chat/completions` (POST)
- `/v1/completions` (POST)
- `/v1/embeddings` (POST)
- `/health` (GET)

**NOT exposed**: SGLang's `/generate`, `/health_generate`, `/get_server_info`, `/flush_cache`

This means Miles' `--rollout-external` (which requires SGLang-native endpoints) cannot connect to Dynamo. Must use custom generate function.

### 2. Dynamo v1.0.1 Logprobs Fix

v1.0.0 had a critical bug: logprobs fields weren't populated when requests routed through Dynamo Frontend. Fixed in v1.0.1. The `bytes` and `token` fields are now properly populated.

Always use: `nvcr.io/nvidia/ai-dynamo/sglang-runtime:1.0.1`

### 3. Two-Job Slurm Pattern

Unlike Baseten (external cloud service), Dynamo runs on the same cluster. This requires:
- **Job 1**: Long-running inference cluster (Dynamo frontend + SGLang workers)
- **Job 2**: Training job (Miles GRPO) that depends on Job 1

Job 1 writes its frontend URL to a shared file:
```bash
echo "http://${HEAD_NODE}:${FRONTEND_PORT}" > "${SHARED_DIR}/dynamo-frontend-url-${SLURM_JOB_ID}.txt"
```

Job 2 auto-detects it:
```bash
DYNAMO_JOB_ID=12345 sbatch train-grpo-dynamo.sbatch
# Inside script: DYNAMO_URL=$(cat /shared/dynamo-frontend-url-${DYNAMO_JOB_ID}.txt)
```

### 4. Discovery Backends

- `file`: Testing, single-node. Workers write to shared file. No external dependencies.
- `etcd`: Production, multi-node. Distributed configuration store. Required for dozens of nodes.
- `kubernetes`: Native K8s service discovery.
- `mem`: In-memory, development only.

### 5. Disaggregated Serving

Dynamo supports prefill/decode split with NIXL zero-copy GPU-to-GPU KV transfer:
```bash
# Prefill worker
python3 -m dynamo.sglang --disaggregation-mode prefill --disaggregation-bootstrap-port 12345 --disaggregation-transfer-backend nixl

# Decode worker
python3 -m dynamo.sglang --disaggregation-mode decode --disaggregation-bootstrap-port 12345 --disaggregation-transfer-backend nixl
```

Performance: 2-7x improvement by separating compute-bound prefill from memory-bound decode.

### 6. Weight Update API

Dynamo exposes `POST /engine/update_weights_from_distributor` on the system port (8081). This could enable hot-reloading training checkpoints into the inference server — eliminating the weight sync gap. Not yet tested.

## Files Created

- `~/work/REPORT-dynamo-miles-grpo-training.md` (1420 lines)
- `~/work/dynamo-training/dynamo_generate.py`
- `~/work/scripts/dynamo/{env,start-dynamo-sglang,test-dynamo,stop-dynamo}.sh`
- `~/work/scripts/slurm/dynamo/{setup-dynamo,start-dynamo-cluster,train-grpo-dynamo,train-grpo-dynamo-production}.sbatch`

## References

- NVIDIA Dynamo: https://github.com/ai-dynamo/dynamo
- Dynamo SGLang examples: `dynamo/examples/backends/sglang/`
- Dynamo SGLang docs: `dynamo/docs/backends/sglang/`
- Docker image: `nvcr.io/nvidia/ai-dynamo/sglang-runtime:1.0.1`
- Miles repo: https://github.com/radixark/miles
- Related skill: baseten-miles-grpo-external-inference
