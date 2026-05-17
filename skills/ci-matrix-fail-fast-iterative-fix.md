---
name: ci-matrix-fail-fast-iterative-fix
description: "In a GitHub Actions matrix with default fail-fast: true, when one entry FAILS the siblings get CANCELLED before their own steps run — hiding their latent failures. Fix the failing entry first, push, and let CI surface what the siblings actually do. Use when: (1) a PR shows 1 FAILURE and N CANCELLED siblings in the same matrix job (e.g. Build Vessel Images), (2) tempted to speculatively pre-fix all matrix entries with the same patch, (3) matrix entries have different ecosystems (Node vs Python vs system) so CVE/test surfaces differ, (4) deciding whether to disable fail-fast vs iterate."
category: ci-cd
date: 2026-05-16
version: "1.0.0"
user-invocable: false
verification: verified-local
tags:
  - github-actions
  - matrix
  - fail-fast
  - cancelled-jobs
  - iterative-debugging
  - cve
  - trivy
  - vessel-images
  - achaean-fleet
---

# CI Matrix fail-fast Hides Cancelled Failures — Fix One, Re-run, Discover Rest

## Overview

| Field | Value |
|-------|-------|
| **Date** | 2026-05-16 |
| **Objective** | Decide how to debug a matrix CI job where one entry FAILS and the rest are CANCELLED — speculate-fix-all vs iterate one-at-a-time. |
| **Outcome** | Iterative discovery wins when matrix entries have differing ecosystems. Speculative wave-fixes risk adding untested no-op changes to siblings with different CVE/test surfaces. |
| **Verification** | verified-local — pattern is a CI-architecture observation confirmed on AchaeanFleet PR #662 (6-vessel `Build Vessel Images` matrix, 1 FAILURE + 5 CANCELLED). |

## When to Use

- A GitHub Actions matrix shows `1 FAILURE` and `N CANCELLED` for sibling entries, and you are tempted to broadcast a fix across all entries.
- Matrix entries use **different base images** or different language ecosystems (e.g. `achaean-base-node` vs `achaean-base-minimal`, Node vs Python vs system-only) so a single fix is unlikely to apply uniformly.
- You are debugging Trivy / pip-audit / dependency-scan failures where the CVE surface is per-entry.
- You are evaluating whether to flip `fail-fast: false` to surface all failures at once.

## Verified Workflow

### Quick Reference

```bash
# 1. Identify the failing matrix entry
gh pr view <num> --json statusCheckRollup \
  --jq '.statusCheckRollup[] | select(.conclusion=="FAILURE") | .name'

# 2. Identify the cancelled siblings (these were ABORTED, not actually failing yet)
gh pr view <num> --json statusCheckRollup \
  --jq '.statusCheckRollup[] | select(.conclusion=="CANCELLED") | .name'

# 3. Read ONLY the failing entry's log — siblings have no useful log
gh run view <run-id> --log-failed
# or
gh run view <run-id> --json jobs \
  --jq '.jobs[] | select(.conclusion=="failure") | {name, steps}'

# 4. Fix the failing entry's specific issue, push, wait for CI.
#    Previously-CANCELLED siblings now run to completion and surface
#    their own real conclusions (success | failure with distinct cause).
```

### Detailed Steps

1. **Stop and resist the urge to broadcast.** Before editing files in every matrix entry, confirm whether the entries share the same ecosystem. If `Dockerfile.aider` uses `FROM achaean-base-node` but `Dockerfile.opencode` uses `FROM achaean-base-minimal`, the CVE/dependency surfaces are not the same.
2. **List matrix entries and their conclusions** with `gh pr view --json statusCheckRollup`. Group by conclusion: FAILURE vs CANCELLED vs SUCCESS.
3. **Read only the FAILURE entry's log.** CANCELLED jobs have no diagnostic value yet — they were terminated mid-stream by the runner.
4. **Apply the minimal fix to that single entry.** For example, pin only the pip deps that Trivy flagged in `aider`'s Dockerfile; do not touch the Node-based siblings.
5. **Push and wait for CI.** The previously-CANCELLED entries now execute end-to-end. Each will resolve to SUCCESS (latent-clean) or FAILURE (now actionable with its own log).
6. **Iterate per entry.** Each new FAILURE may have a different root cause (different base image, different scanner output).
7. **Only consider `fail-fast: false` as a global change** when matrix entries are roughly homogeneous AND a single push-cycle per failure is too expensive. Costs: longer CI on truly-bad PRs and higher status-check noise.

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
|---------|----------------|---------------|----------------|
| Speculatively pre-fix all 6 vessels with `aider`'s pip pins | Considered applying GitPython/Pillow/urllib3 version bumps to `claude`, `codex`, `codebuff`, `opencode`, `worker` Dockerfiles in the same commit | `claude`/`codex`/`codebuff` are Node-based (no Python deps to pin); `opencode`/`worker` use `achaean-base-minimal` (no Python interpreter). The pip-pin change would be a no-op or worse, an unintended addition with no signal that it helped. | When matrix entries diverge in ecosystem, each has its own CVE surface. Fix the entry whose failure you can read, observe the rest. |
| Treating CANCELLED siblings as "also broken" in the status rollup | Reading the PR check rollup and assuming 6 failures need 6 fixes | CANCELLED ≠ FAILED. The CANCELLED entries were aborted by the fail-fast scheduler before their Trivy/build steps ran. Their actual outcomes are unknown until the matrix re-runs without the upstream sibling tripping fail-fast. | A CANCELLED conclusion carries **no information** about whether that entry would have passed. Do not count it as a failure. |
| Flipping `fail-fast: false` as the first response | Disabling fail-fast on the whole matrix to "see everything at once" | Doubles or N-tuples CI minutes on truly bad PRs; adds noise to the rollup so the human eye loses the actual offender. Useful for a final audit pass, not for the first iteration. | Use `fail-fast: false` strategically (e.g. once near merge), not as a default debugging crutch. |

## Results & Parameters

**Concrete session evidence — AchaeanFleet PR #662, `Build Vessel Images` matrix:**

```text
matrix.vessel  | base image              | conclusion
---------------|-------------------------|-----------
aider          | achaean-base-minimal    | FAILURE   (Trivy flagged GitPython/Pillow/urllib3)
claude         | achaean-base-node       | CANCELLED (Node-based; no Python deps)
codex          | achaean-base-node       | CANCELLED (Node-based; no Python deps)
codebuff       | achaean-base-node       | CANCELLED (Node-based; no Python deps)
opencode       | achaean-base-minimal    | CANCELLED (no Python interpreter)
worker         | achaean-base-minimal    | CANCELLED (no Python interpreter)
```

**The wrong fix that was rejected:**

```dockerfile
# Adding identical pip pins to all 6 vessels — 5 of them have no pip!
RUN pip install --no-cache-dir \
    "GitPython>=3.1.41" \
    "Pillow>=10.3.0" \
    "urllib3>=2.2.2"
```

**The right fix (applied to `Dockerfile.aider` only):**

```dockerfile
# Only the aider vessel actually installs aider via pip → only it needs the pin
RUN pip install --no-cache-dir \
    aider-chat \
    "GitPython>=3.1.41" \
    "Pillow>=10.3.0" \
    "urllib3>=2.2.2"
```

**Expected CI signal after pushing the targeted fix:**

- `aider`: re-runs; either SUCCESS (fix worked) or FAILURE with a different log (next layer of issue).
- The 5 previously-CANCELLED vessels: now run to completion and report their **own** conclusions independently. Each may surface a distinct issue (Node base CVEs, system-package vulnerabilities) that was never visible while fail-fast was masking them.

## Verified On

| Project | Context | Details |
|---------|---------|---------|
| HomericIntelligence/AchaeanFleet | PR #662 `Build Vessel Images` matrix (6 vessels: aider, claude, codex, codebuff, opencode, worker) | 1 FAILURE + 5 CANCELLED → iterative fix path chosen over wave-fix |
