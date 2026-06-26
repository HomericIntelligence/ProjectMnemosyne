---
name: inference360-diffusion-sglang-dllm-manifests
description: "Bring up diffusion checkpoints in Inference360 with manifest-driven SGLang DLLM launch fields. Use when: (1) adding SGLang-only DLLM serving options, (2) rendering diffusion model launch flags into Slurm templates, (3) keeping experimental diffusion manifests gated off from production."
category: tooling
date: 2026-06-26
version: "1.0.0"
user-invocable: false
verification: verified-ci
tags: [inference360, diffusion, sglang, dllm, manifest, h200, slurm]
---

# Inference360 Diffusion SGLang DLLM Manifests

## Overview

| Field | Value |
|-------|-------|
| **Date** | 2026-06-26 |
| **Objective** | Enable bringup of diffusion checkpoints in LLM360/Inference360 through SGLang DLLM manifests instead of ad hoc launch string edits. |
| **Outcome** | PR #286 for issue #285 merged with schema, template, manifest, and validation coverage for two experimental SGLang diffusion services. |
| **Verification** | verified-ci. CI passed validate, secrets, sast, python-sca, and CodeQL before auto-merge. Local host fallback validation passed with 852 passed and 8 skipped; plain `just validate` was blocked locally only because rootless Podman was unavailable. |

## When to Use

- You need to bring up a diffusion checkpoint on the Inference360 H200 Slurm platform using SGLang.
- A SGLang launch needs DLLM-specific flags such as `--dllm-algorithm`, `--dllm-algorithm-config`, `--json-model-override-args`, `--sampling-backend`, or `--cuda-graph-bs`.
- A proposed serving field is valid only for `runtime.default_engine: sglang` and must fail closed for vLLM or TensorRT-LLM manifests.
- An experimental manifest needs to stay gated with `experimental.enabled: true` and `production.enabled: false`.
- A manifest uses a placeholder container digest and should be rejected before review or CI.

## Verified Workflow

### Quick Reference

```bash
cd <Inference360 checkout>

python -m pytest tests/test_manifest_validation.py -k \
  "nld_diffusion or diffusiongemma or sglang_dllm or non_sglang or placeholder_container_digest"

PYTHON=.venv/bin/python \
INFERENCE360=.venv/bin/inference360 \
scripts/validate.sh

# Run only when rootless Podman is available on the host.
just validate
```

### Detailed Steps

1. Add SGLang-only DLLM serving fields to the service manifest schema:
   `sglang_dllm_algorithm`, `sglang_dllm_algorithm_config`,
   `sglang_json_model_override_args`, `sglang_sampling_backend`, and
   `sglang_cuda_graph_bs`.
2. Register a Jinja `shell_quote` filter through `shlex.quote` so JSON model
   override arguments render as one safe shell argument.
3. Render the DLLM fields in `slurm/sglang.sbatch.j2` as `engine_command` array
   arguments, not as string-concatenated shell fragments. Preserve the existing
   SGLang launcher shape and only add the flags when the manifest sets them.
4. Add manifest validation that rejects any SGLang-only serving field unless
   `runtime.default_engine` is `sglang`.
5. Reject the all-zero placeholder container digest
   `sha256:0000000000000000000000000000000000000000000000000000000000000000`
   for experimental and production manifests.
6. Add experimental SGLang manifests for the diffusion checkpoints. Keep them
   experimental-only: `experimental.enabled: true`, `production.enabled: false`,
   and production promotion gates closed.
7. Test both manifest validation and generated Slurm rendering. The useful
   regression tests covered the two concrete diffusion manifests, synthetic
   DLLM flag rendering, non-SGLang rejection, and placeholder digest rejection.
8. Run the full host fallback validation and CI. Treat plain `just validate` as
   a stronger gate when rootless Podman is available, but do not treat a local
   Podman-unavailable host as a product failure if host validation and CI pass.

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
|---------|----------------|---------------|----------------|
| Ad hoc launch string edits | Tried to encode diffusion SGLang flags directly in launch command text | The behavior was not schema-covered, hard to review, and easy to drift from generated artifacts | Make SGLang DLLM launch behavior manifest-driven, schema-validated, template-rendered, and test-covered |
| Placeholder container digest | Allowed experimental manifests to carry `sha256:000...` while wiring up launch fields | The manifest looked reviewable but could not represent a reproducible runtime image | Reject placeholder digests in validation before manifests reach CI or cluster bringup |
| Cross-engine DLLM fields | Considered putting SGLang-only fields on vLLM or TensorRT-LLM manifests | Other engines do not own those launch flags, so accepting the fields would create misleading configuration | Fail closed unless `runtime.default_engine` is `sglang` |
| Unquoted JSON override args | Rendered JSON model overrides like ordinary text | Shell parsing can split or reinterpret JSON instead of passing it as one argument | Add a Jinja `shell_quote` filter and assert the rendered Slurm contains the quoted JSON argument |

## Results & Parameters

### Schema Fields

```yaml
serving:
  sglang_dllm_algorithm: <algorithm-name>
  sglang_dllm_algorithm_config: <container-config-path>
  sglang_json_model_override_args: '{"ar_mode": true}'
  sglang_sampling_backend: pytorch
  sglang_cuda_graph_bs: [1, 2, 4, 8]
```

### Template Rendering Contract

`slurm/sglang.sbatch.j2` should render these fields as array arguments:

```bash
engine_command+=(--dllm-algorithm FastDiffuser)
engine_command+=(--dllm-algorithm-config /opt/sglang_fork/test/registered/dllm/configs/nemotron_labs_fastdiffuser.yaml)
engine_command+=(--json-model-override-args '{"ar_mode": true}')
engine_command+=(--sampling-backend pytorch)
engine_command+=(--cuda-graph-bs 1 2 4 8)
```

### Diffusion Manifest Parameters

| Manifest | Algorithm | Extra DLLM Parameters | Gating |
|----------|-----------|-----------------------|--------|
| `manifests/experimental/nemotron-labs-diffusion-8b-sglang-experimental-m2.yaml` | `FastDiffuser` | Config file name `nemotron_labs_fastdiffuser.yaml`; JSON model override args `{"ar_mode": true}` | Experimental enabled, production disabled |
| `manifests/experimental/diffusiongemma-26b-a4b-sglang-experimental-m2.yaml` | `Gemma4Renoise` | Sampling backend `pytorch`; `sglang_cuda_graph_bs: [1]` | Experimental enabled, production disabled |

### Tests That Mattered

- `test_nld_diffusion_manifest_renders_fastdiffuser_sglang_launch`
- `test_diffusiongemma_manifest_renders_pr28054_gemma4renoise_launch`
- `test_sglang_dllm_launch_fields_render_as_array_arguments`
- `test_non_sglang_engines_reject_sglang_dllm_launch_fields`
- `test_manifest_validation_rejects_placeholder_container_digest`

### Verified On

| Project | Context | Details |
|---------|---------|---------|
| LLM360/Inference360 | PR #286 for issue #285, merged 2026-06-26 | CI passed validate, secrets, sast, python-sca, and CodeQL before auto-merge; local host fallback validation passed with 852 passed and 8 skipped |

