---
name: inference360-ifm-k2v3-logical-rename
description: "Rename Inference360 logical K2V3 surfaces to IFM without breaking physical checkpoint or benchmark storage paths. Use when: (1) replacing k2v3/K2V3 names in manifests, docs, tests, scripts, and routes, (2) preserving real external paths that still contain k2v3, (3) adding a guard that blocks old logical names while allowing storage references."
category: tooling
date: 2026-06-18
version: "1.0.0"
user-invocable: false
verification: verified-ci
tags: [inference360, k2v3, ifm, rename, manifests, h200-slurm]
---

# Inference360 IFM K2V3 Logical Rename

## Overview

| Field | Value |
|-------|-------|
| **Date** | 2026-06-18 |
| **Objective** | Rename Inference360 logical surfaces from K2V3/k2v3/k2_v3 to IFM/ifm while preserving real physical storage paths that still contain k2v3. |
| **Outcome** | Successful. Tracked filenames and logical identifiers moved to IFM, old logical names were guarded by tests, physical checkpoint and PerfHC storage paths were intentionally preserved, and Inference360 PR #161 passed CI. |
| **Verification** | verified-ci |

## When to Use

- A user asks to rename all Inference360 K2V3 naming to IFM.
- The change spans H200 Slurm service manifests, docs/runbooks, docs/evaluations, generation scripts, launch scripts, default model registries, benchmark examples, and tests.
- Old logical names must disappear, but real external storage still uses k2v3 path segments.
- A bulk rename has started to mutate protected paths or generated placeholder tokens.
- Ruff reformats a stale-token guard in a way that defeats the guard.

## Verified Workflow

### Quick Reference

```bash
# Work in an isolated Inference360 branch/worktree, then inventory old names.
git ls-files | rg 'k2v3|K2V3|K2v3|k2_v3'
rg -n 'k2v3|K2V3|K2v3|k2_v3' .

# Rename tracked files with git mv so history follows the IFM names.
git mv scripts/generate_k2v3_m1_manifests.py scripts/generate_ifm_m1_manifests.py
git mv scripts/multi_model_k2v3_launch.sh scripts/multi_model_ifm_launch.sh

# Update logical surfaces to IFM, but do not rewrite physical storage paths.
rg -n 'k2v3|K2V3|K2v3|k2_v3' docs manifests scripts tests README.md

# Required post-change checks.
git diff --check
git ls-files | rg 'k2v3|K2V3|K2v3|k2_v3' || true
rg -n 'k2v3|K2V3|K2v3|k2_v3' .
just validate
```

### Detailed Steps

1. **Rename tracked files first with `git mv`.** Do not rely only on content replacement. Move old K2V3-named files across docs/runbooks, docs/evaluations, manifests, and scripts to IFM filenames so `git log --follow` remains useful. Verified examples included `generate_k2v3_m1_manifests.py` -> `generate_ifm_m1_manifests.py` and `multi_model_k2v3_launch.sh` -> `multi_model_ifm_launch.sh`.

2. **Separate logical identifiers from physical storage.** Logical repo surfaces should become IFM: `model_id`, `display_name`, `host`, `slurm_job_name`, route endpoints such as `/ifm/...`, `manifest_version`, profile names, `default-models.yaml`, tool README text, and benchmark report examples. Real storage paths should remain unchanged when that is where the data actually lives.

3. **Protect known physical storage references.** Preserve paths like `/workspace/checkpoints/huggingface/k2v3-...` and `/lustrefs/users/micah.villmow/modular/LLM360/PerfHC/k2v3_single_node_perfhc/...`. Rewriting those paths makes Slurm jobs point at nonexistent checkpoint or PerfHC artifacts.

4. **Add or keep a logical-name guard test.** The guard should scan repo surfaces that should be logically renamed and fail on old K2V3 names while allowlisting only physical storage references. The guard is the durable protection against future examples, docs, or manifests reintroducing old logical names.

5. **Write stale-token constants so Ruff cannot fold them back.** Avoid adjacent string literal tricks in tests because Ruff can collapse them into the old token. Use explicit concatenation:

   ```python
   LEGACY_COMPACT_MODEL_PREFIX = "k2" + "v3"
   LEGACY_UNDERSCORE_PARSER = "k2" + "_v3"
   ```

6. **Avoid self-matching placeholder tokens during bulk replacement.** If temporarily protecting text before a bulk rewrite, do not use placeholders containing the replacement target, such as `@@K2V3_PROTECTED_...@@`. The replacement pass can mutate the placeholder itself and prevent restoration. Use neutral placeholders, or restore the affected files from `HEAD` and redo the replacement more narrowly.

7. **Verify filenames, content, and CI.** Require `git diff --check` to be clean, `git ls-files | rg 'k2v3|K2V3|K2v3|k2_v3'` to show no old tracked filenames, repo-wide `rg` to show only physical storage exceptions, full local validation to pass, and PR CI to pass before calling the rename done.

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
|---------|----------------|---------------|----------------|
| Rename every old token everywhere | Bulk replacement included checkpoint and PerfHC storage strings | External storage paths still physically contained k2v3, so rewritten jobs would point at paths that did not exist | Treat logical identifiers and physical storage locations as different classes of data. Preserve real paths unless storage has actually moved. |
| Placeholder tokens containing K2V3 | Protected strings used placeholders like `@@K2V3_PROTECTED_...@@` before a bulk rewrite | The placeholder itself contained the target token and was transformed, making restoration fail | Use neutral placeholder tokens with no old or new name in them, or restore from `HEAD` before continuing. |
| Adjacent string literal stale-token guard | A test tried to avoid embedding the stale token by writing adjacent string literals | Ruff can collapse adjacent string literals back into the exact old token, defeating the guard's intent | Use explicit concatenation, for example `"k2" + "v3"` and `"k2" + "_v3"`. |
| Filename audit skipped | Content was updated but old filenames were not checked separately | A repo-wide content grep does not prove tracked filenames were renamed | Run `git ls-files | rg 'k2v3|K2V3|K2v3|k2_v3'` and require no matches. |

## Results & Parameters

### Logical Surfaces That Should Become IFM

```yaml
logical_identifiers:
  - model_id
  - display_name
  - host
  - slurm_job_name
  - manifest_version
  - profile names
  - route endpoints such as /ifm/...
repo_surfaces:
  - docs/runbooks
  - docs/evaluations
  - manifests
  - scripts
  - default-models.yaml
  - tool README
  - benchmark report examples
```

### Physical References That Should Stay K2V3

```text
/workspace/checkpoints/huggingface/k2v3-...
/lustrefs/users/micah.villmow/modular/LLM360/PerfHC/k2v3_single_node_perfhc/...
```

These are storage facts, not logical product names. Change them only after storage is moved or a new verified path exists.

### Guard Test Pattern

```python
LEGACY_COMPACT_MODEL_PREFIX = "k2" + "v3"
LEGACY_UNDERSCORE_PARSER = "k2" + "_v3"

ALLOWED_PHYSICAL_PATH_FRAGMENTS = (
    "/workspace/checkpoints/huggingface/k2v3-",
    "/lustrefs/users/micah.villmow/modular/LLM360/PerfHC/k2v3_single_node_perfhc/",
)
```

The test should scan logical repo surfaces and fail on stale K2V3 tokens unless the match is inside a known physical storage fragment.

### Verification Evidence

```text
git diff --check: clean
git ls-files | rg 'k2v3|K2V3|K2v3|k2_v3': no old filenames
repo-wide rg of old tokens: only physical storage paths remained
local validation: passed
Inference360 PR #161 CI: passed
verification: verified-ci
```

## Verified On

| Project | Context | Details |
|---------|---------|---------|
| LLM360/Inference360 | PR #161, K2V3-to-IFM logical rename across H200 Slurm manifests, docs, scripts, examples, and tests | Verified with clean diff whitespace check, no stale tracked filenames, stale logical-name grep guard, full local validation, and passing CI. |
