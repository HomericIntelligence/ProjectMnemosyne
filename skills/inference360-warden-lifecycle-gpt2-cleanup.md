---
name: inference360-warden-lifecycle-gpt2-cleanup
description: "Align and debug Inference360 Warden lifecycle smoke workflows. Use when: (1) Warden docs, CLI, tests, or API paths drift around allocate/register/start/stop/deregister/deallocate, (2) a lightweight H200 Slurm lifecycle smoke needs a checked-in gpt2-mini manifest, (3) Warden Slurm startup times out and must prove cleanup instead of leaking jobs."
category: debugging
date: 2026-06-29
version: "1.0.0"
user-invocable: false
verification: verified-ci
tags:
  - inference360
  - warden
  - lifecycle
  - slurm
  - h200
  - gpt2-mini
  - deallocate
  - cleanup
---

# Inference360 Warden Lifecycle GPT2 Cleanup

## Overview

| Field | Value |
|-------|-------|
| **Date** | 2026-06-29 |
| **Objective** | Bring an Inference360 Warden lifecycle PR back into alignment after strict review by removing README/runbook/design-doc drift, completing the control-to-Warden rename, making cluster selection auto-detect on-cluster, adding a lightweight gpt2-mini smoke manifest, closing lifecycle behavior issues, and making timeout cleanup fail closed. |
| **Outcome** | The PR fix path was verified by local validation and GitHub CI before merge. The full live Warden model lifecycle did not complete because the CPU Warden allocation remained pending for Slurm `Priority`, but timeout cleanup behavior was verified locally and with live short retries. |
| **Verification** | verified-ci for the PR workflow. Live full lifecycle remained scheduler-blocked; cleanup behavior was verified locally and live with no leaked Slurm jobs after short-timeout retries. |

## When to Use

- Inference360 Warden docs, tests, or runbooks disagree on the lifecycle command sequence.
- A smoke-test manifest needs to validate infrastructure behavior without requiring a large private model.
- `control` naming is still present in Warden lifecycle docs, tests, routes, or logs after a rename.
- `release` aliases or `/warden/release` artifacts appear after the canonical command has become `deallocate`.
- `warden up` submits a Slurm job, then times out during node discovery or liveness checks.
- Warden token handling, request size bounds, or Slurm `--wrap` command construction is under review.

## Verified Workflow

### Quick Reference

```text
Canonical Warden lifecycle:
warden up
allocate
register
start --job-class default
stop --job-class default
deregister
deallocate
warden down

Use --cluster only for off-cluster or non-autodetected contexts.
Use erwanf/gpt2-mini for checked-in lightweight infrastructure smoke tests.
On Warden startup timeout after sbatch returns a job id, best-effort scancel
the job before re-raising the timeout error.
```

### Detailed Steps

1. Re-read the repository contract before changing lifecycle behavior: `README.md`, `AGENTS.md`, and `docs/inference360-design.md`; include release, governance, security, or nodepool runbooks only when those surfaces are touched.

2. Normalize the lifecycle sequence everywhere to:

   ```text
   warden up -> allocate -> register -> start --job-class default -> stop --job-class default -> deregister -> deallocate -> warden down
   ```

   Tests, scripts, and runbooks should assert `--job-class default` on both `start` and `stop`.

3. Make `--cluster` optional for `warden up` and `register` when the command runs on-cluster and cluster autodetection can resolve the target. Keep `--cluster` in examples only when documenting off-cluster or non-autodetected contexts.

4. Remove the legacy `release` alias cleanly. The canonical surfaces are:

   ```text
   CLI command: deallocate
   HTTP endpoint: /warden/deallocate
   response key: deallocated_node_ids
   log stage: stage=deallocate
   ```

5. Use exact stale lifecycle scans instead of broad `rg release`, which matches unrelated release-process text:

   ```bash
   rg -n 'warden_release_nodes|/warden/release|released_node_ids|stage=release|alias for release|release allocated|release even|release the node|controlled release|allocation and release|releasing -->'
   ```

6. Use `erwanf/gpt2-mini` as the checked-in lightweight default model manifest for infrastructure smoke tests. Keep large private model paths out of the default validation path.

7. Harden Warden token and request handling:
   - token-bearing config files should be mode `0600`;
   - Warden Slurm `--wrap` should not include `--token`;
   - `warden up --check` should print a redacted token;
   - handler construction should fail closed when no token is configured;
   - request body size should be bounded.

8. Ensure `/warden/deallocate` passes the injected Slurm runner into `warden_deallocate_nodes`. A focused regression test should fail when expected `scancel` calls are absent.

9. Treat cluster facts as dated evidence. In the verified session, live Slurm validation on 2026-06-29 found the M2 `cpuonly` Warden allocation used `QOS=k2m` and `Account=k2m`, not `main/main`. Update `manifests/clusters/m2.yaml` and document that evidence in `docs/runbooks/nodepool-cluster-defaults.md`, with an explicit note to revalidate before production rollout.

10. If `warden up` receives a Slurm job id from `sbatch` but later fails node discovery or liveness before the Warden server is usable, best-effort cleanup must run before the exception escapes. Regression-test the pending case with a fake `scontrol show job` response containing `JobState=PENDING`; `launch_warden_server_job(... wait_timeout_seconds=-1 ...)` should raise a node-discovery error and the runner should observe:

    ```python
    ["scancel", "201"]
    ```

11. Do not keep resubmitting long live lifecycle attempts when Warden CPU jobs remain pending for Slurm `Priority`. Use a short timeout to verify cleanup, then inspect the queue for the specific job id.

12. When rootless Podman is unavailable, do not claim `just validate` passed. Use host validation plus GitHub CI:

    ```bash
    python -m pytest
    ruff check .
    python -m compileall inference360 tests
    inference360 check all --cluster m1
    inference360 check all --cluster m2
    ```

    Then verify the PR's current head is mergeable and all required GitHub checks pass.

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
|---------|----------------|---------------|----------------|
| Broad `rg release` cleanup | Searched for `release` everywhere while removing the alias | Matched unrelated release-process documentation and created noise | Use exact stale lifecycle scans for `/warden/release`, `released_node_ids`, `stage=release`, and old prose patterns |
| Required `--cluster m2` on-cluster | Kept examples and tests requiring `--cluster` for Warden commands | On-cluster Warden flows should autodetect cluster unless the context is off-cluster or ambiguous | Make `--cluster` optional for `warden up` and `register`; keep it only where autodetection is unavailable |
| Large private smoke model as default | Used large internal model manifests for infrastructure smoke validation | Heavy/private defaults slow validation and couple smoke tests to unavailable artifacts | Use checked-in `erwanf/gpt2-mini` for lightweight lifecycle smoke tests |
| Partial release-to-deallocate rename | Changed some CLI/docs surfaces but left `/warden/release`, `released_node_ids`, or `stage=release` artifacts | Mixed names make reviews and operators unsure which lifecycle command is canonical | Rename CLI, HTTP, response keys, tests, logs, and docs together |
| Missing runner injection in deallocate handler | The `/warden/deallocate` handler called deallocation without the injected Slurm runner | Focused tests saw no `scancel` command, so the handler could pass without actually using the test runner | Assert Slurm runner interactions at the handler boundary |
| Token in Slurm wrap or printed config | Let token material appear in generated command/config output | Token-bearing process args and readable config files are avoidable exposure | Keep config `0600`, redact checks, avoid `--token` in `--wrap`, and fail closed without a token |
| Waiting on live Warden CPU allocation | Retried full lifecycle attempts while Warden CPU jobs stayed pending with `Reason=Priority` | Scheduler priority blocked the lifecycle before model start, so repeated long attempts did not add evidence | Use short timeout retries to verify cleanup and inspect `squeue -j <job>` |

## Results & Parameters

### Verification Evidence

```text
PR workflow verification:
- full local pytest: 799 passed, 1 skipped
- ruff: pass
- compileall: pass
- inference360 check all --cluster m1: status ok with promotion/pre-health readiness failing closed
- inference360 check all --cluster m2: status ok with promotion/pre-health readiness failing closed
- GitHub PR checks: all passing and mergeable before merge

Live lifecycle verification:
- full model lifecycle did not complete because Warden CPU allocation stayed pending for Slurm Priority
- short-timeout retries verified cleanup behavior
- follow-up queue inspection showed no leaked Slurm jobs for the retried Warden startup attempts

Unavailable validation:
- just validate could not run on the host because rootless Podman was unavailable
```

### Contracts to Preserve

| Surface | Expected Contract |
|---------|-------------------|
| Lightweight smoke model | `erwanf/gpt2-mini` |
| Start command | `start --job-class default` |
| Stop command | `stop --job-class default` |
| Deallocation CLI | `deallocate` |
| Deallocation endpoint | `/warden/deallocate` |
| Deallocation response key | `deallocated_node_ids` |
| Deallocation log stage | `stage=deallocate` |
| On-cluster `--cluster` | Optional when autodetection works |
| Warden timeout cleanup | `scancel <job_id>` after `sbatch` succeeds but node discovery or liveness times out |
| M2 Warden CPU allocation evidence | On 2026-06-29, `cpuonly` used `QOS=k2m` and `Account=k2m`; revalidate before production rollout |

### Related Issues

The captured PR aligned the Warden lifecycle behavior tracked by Inference360 GitHub issues #190 through #196. Keep future issue comments and runbooks sanitized: redact endpoint addresses, absolute infrastructure paths, checkpoint paths, prompts, tokens, cookies, and user-specific locations.
