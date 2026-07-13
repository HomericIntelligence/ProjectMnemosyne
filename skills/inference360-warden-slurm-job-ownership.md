---
name: inference360-warden-slurm-job-ownership
description: "Track Warden-launched user-owned Slurm jobs without classifying arbitrary user jobs as Inference360-owned. Use when: (1) implementing Inference360 Warden orphan or tracking-mismatch detection, (2) comparing Slurm queue state against Warden Registry state, (3) configuring periodic Warden Slurm scans from the runtime manifest."
category: architecture
date: 2026-07-07
version: "1.0.0"
user-invocable: false
verification: verified-local
tags:
  - inference360
  - warden
  - slurm
  - h200
  - orphan-detection
  - tracking-mismatch
  - registry
  - manifest-driven
---

# Inference360 Warden Slurm Job Ownership

## Overview

| Field | Value |
|-------|-------|
| **Date** | 2026-07-07 |
| **Objective** | Implement Inference360 Warden tracking-mismatch detection for active H200 Slurm jobs that Warden launched for the user but that are missing from Warden runtime/Registry state. |
| **Outcome** | Local implementation pattern and focused tests passed. The key contract is that a Slurm job owned by the Unix user is not automatically Inference360-owned; it must carry Warden/Inference360 scheduler evidence. |
| **Verification** | verified-local - focused Inference360 tests passed locally; CI validation pending for the uncommitted #343 implementation. |

## When to Use

- Inference360 needs to scan the Slurm queue for orphaned, leaked, or untracked Warden jobs.
- A user clarifies that "Inference360-owned" means GPU Slurm jobs owned by the user and launched by Warden, not every user-launched Slurm job.
- You are adding or reviewing Warden `tracking_mismatches`, orphan reports, or Registry reconciliation.
- You need a repeatable background Warden scan interval controlled by `manifests/services/warden-runtime.yaml`.
- Tests need to prove manual user jobs are ignored while Warden-launched H200 jobs are reported.

## Verified Workflow

Verified locally only - CI validation pending.

### Quick Reference

```bash
# Focused local verification used for the captured implementation.
UV_CACHE_DIR=/tmp/i360-uv-cache uv run pytest tests/test_warden_lifecycle.py \
  -k 'tracking_mismatch or orphan_detection or warden_serve_runtime_uses_runtime_manifest_server_defaults or warden_server_defaults_are_loaded_from_runtime_manifest' \
  -q
```

```yaml
# Runtime manifest contract.
server_defaults:
  orphan_detection:
    scan_interval_seconds: 60.0
```

```text
# Queue scan shape.
squeue -u <operator-user> --noheader -o '%i|%T|%u|%j|%R'
scontrol show job <job-id>
```

### Detailed Steps

1. Treat Slurm as scheduler of record and Warden as lifecycle owner. The reconciliation loop observes Slurm, but it must not cancel or mutate jobs simply because they are untracked.

2. Define ownership from scheduler evidence, not from Unix ownership alone. A job is a Warden/Inference360 job only when its fresh `scontrol show job` record carries an Inference360 scheduler comment such as `inference360:nodepool`, `inference360:warden`, or a model-scoped `inference360:*:*` comment. A manual user job with another comment is ignored.

3. Scan the active user queue first:

   ```text
   squeue -u <operator-user> --noheader -o '%i|%T|%u|%j|%R'
   ```

   Only active Slurm states continue to fresh job inspection. Parse failures should fail closed with a manifest/runtime error instead of silently misclassifying jobs.

4. Refresh each candidate with `scontrol show job <job-id>`. Use the fresh `JobState`, `JobName`, `Comment`, `NodeList`, and `BatchHost` instead of trusting stale `squeue` columns.

5. Build the tracked job-id set from Warden runtime state:

   | State source | Include when |
   |--------------|--------------|
   | `state["warden"]["slurm_job_id"]` | Warden control job id is present |
   | `state["nodes"][*]["slurm_job_id"]` | Node is not terminal |
   | `state["servers"][*]["slurm_job_id"]` | Server is in a current lifecycle state |
   | `_autoscaling_releases[*]["slurm_job_id"]` | Delayed release intent still owns the allocation |

6. Report only active Inference360-owned Slurm jobs whose ids are absent from the tracked set. Persist them under `tracking_mismatches` with `classification: tracking_mismatch`, `routeable: false`, and `action: inspect_and_reconcile_warden_registry`.

7. Run the scan periodically inside Warden. Source the interval from `server_defaults.orphan_detection.scan_interval_seconds`; the captured default was `60.0` seconds and schema validation rejects non-positive values.

8. On scan failure, redact operational details before storing or logging the error. Endpoint addresses and tokens from scheduler failures should become placeholders such as `<REDACTED_ENDPOINT>` and `<REDACTED_TOKEN>`.

9. Test with fake Slurm runners rather than live Slurm. At minimum cover:

   - Warden-launched active job missing from state is reported as a tracking mismatch.
   - User-launched or non-Inference360-commented active job is ignored.
   - Already tracked allocation is ignored.
   - Scheduler failure increments tracking-mismatch reconcile failures and stores redacted error text.
   - Manifest validation rejects invalid scan intervals.

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
|---------|----------------|---------------|----------------|
| Classify by Unix user only | Treated every active Slurm job owned by the operator user as an Inference360 orphan candidate | Users can launch their own Slurm jobs outside Warden; those must not be tracked or flagged by Warden | Require Warden/Inference360 scheduler evidence such as the Slurm `Comment` field before classifying ownership |
| Trust `squeue` alone | Used queue rows as the full source of ownership truth | `squeue` gives useful ids and state, but not enough ownership evidence to distinguish Warden jobs from manual jobs | Use `squeue` only for enumeration, then refresh each candidate with `scontrol show job` |
| Cancel or repair automatically | Considered treating untracked Warden jobs as immediately reclaimable or routeable failures | Missing Registry state is an incident that may need operator investigation; automatic cancellation can destroy useful evidence or a live serving allocation | Persist a non-routeable `tracking_mismatch` incident with an inspect/reconcile action |
| Hard-code scan cadence | Made the repeat interval a code constant or environment variable | Inference360 lifecycle behavior must be manifest-driven and reviewable | Configure `server_defaults.orphan_detection.scan_interval_seconds` in the Warden runtime manifest and schema |

## Results & Parameters

### Observed Local Verification

```text
Command:
UV_CACHE_DIR=/tmp/i360-uv-cache uv run pytest tests/test_warden_lifecycle.py -k 'tracking_mismatch or orphan_detection or warden_serve_runtime_uses_runtime_manifest_server_defaults or warden_server_defaults_are_loaded_from_runtime_manifest' -q

Result:
8 passed, 190 deselected in 0.10s
```

### Ownership Rules

| Input evidence | Classification |
|----------------|----------------|
| Active user job with `Comment=inference360:nodepool` and no tracked Warden state | `tracking_mismatch` |
| Active user job with model-scoped Inference360 comment and no tracked Warden state | `tracking_mismatch` |
| Active user job with non-Inference360 comment | Ignored |
| Active Inference360 job whose id is present in active Warden node/server/control/release state | Ignored as tracked |
| Inactive Slurm job | Ignored by active-state filter |

### Registry Incident Shape

```json
{
  "classification": "tracking_mismatch",
  "routeable": false,
  "action": "inspect_and_reconcile_warden_registry",
  "reason": "Inference360-owned Slurm job is active but missing from Warden runtime state",
  "slurm_job_id": "101",
  "slurm_state": "RUNNING",
  "slurm_user": "operator",
  "slurm_job_name": "warden-free-h200-a-abc12345",
  "scheduler_comment": "inference360:nodepool",
  "ownership_kind": "nodepool"
}
```

## Verified On

| Project | Context | Details |
|---------|---------|---------|
| LLM360/Inference360 | Issue #343 implementation session on 2026-07-07 | Focused local tests passed for tracking mismatch detection and manifest-driven orphan scan interval. Local branch had not yet been committed or CI-validated when this skill was captured. |
