---
name: ci-cd-triage-pr-vs-systemic-failures
description: "Distinguish PR-introduced CI regressions from systemic main-branch failures and infrastructure flakes BEFORE bisecting, reverting, or rerunning. Use when: (1) a PR has unexplained CI failures and you're tempted to blame the PR, (2) before invoking `gh run rerun` on any job, (3) before proposing to revert a dependency/toolchain bump, (4) distinguishing GitHub infrastructure flakes (HTTP 500 on git fetch) from real failures, (5) classifying `mojo: error: execution crashed` as libKGEN JIT (modular#6413) vs. an actual PR bug, (6) deciding whether to leave a failure as-is on the surface PR while addressing it in a separate workaround PR. ProjectOdyssey-specific policy: NEVER `gh run rerun` to dismiss as flake, NEVER revert/pin-back a Mojo version bump, ALWAYS file or reference an upstream Modular issue for runtime crashes."
category: ci-cd
date: 2026-05-11
version: 1.0.0
user-invocable: false
verification: verified-ci
tags:
  - ci-failure
  - triage
  - mojo-jit
  - modular-6413
  - github-infra-flake
  - main-branch-history
  - projectodyssey-policy
---
# CI/CD Triage: PR-Introduced vs. Systemic Failures

Decide whether a red CI on a pull request is the PR's fault, a systemic failure already present on `main`, or a transient GitHub infrastructure flake — BEFORE wasting effort on bisection, revert, or policy-violating reruns.

## Overview

| Attribute | Value |
| ----------- | ------- |
| **Date** | 2026-05-11 |
| **Objective** | Avoid misattributing systemic CI failures (libKGEN JIT crash, GitHub infra flakes) to a PR's diff |
| **Outcome** | On PR #5381, identified `mojo: error: execution crashed` failures as already-failing on `main` (7+ consecutive failure conclusions), referenced modular#6413, addressed via separate workaround PR #5382 instead of churning the surface PR |
| **Verification** | verified-ci (the triage approach was applied successfully in this session) |
| **Repo** | HomericIntelligence/ProjectOdyssey |

## When to Use

Use this skill when any of these triggers fire:

- A PR's CI is red and you're about to assume the PR caused it
- You're tempted to type `gh run rerun --failed` to "see if it was a flake"
- A toolchain bump (Mojo, Python, container base image) just landed and CI got worse — and someone suggests reverting it
- Failure messages look like infrastructure noise: HTTP 500 on `git fetch`, podman socket not ready, network reset during checkout
- Failure messages look like Mojo runtime crashes: `mojo: error: execution crashed`, `libKGENCompilerRTShared.so` in backtrace, crash with no Mojo-source stack frame
- A reviewer asks "is this CI failure from your PR or pre-existing?" and you don't yet know

**Trigger phrases**: "is this my fault", "should I rerun this", "should we revert the bump", "CI is red but I didn't touch that file", "JIT crash again".

## Verified Workflow Quick Reference

### Step 1 — Check `main` branch history FIRST (before doing anything else)

For each failing workflow, pull the recent main runs:

```bash
gh run list --branch main --limit 10 \
  --workflow="Comprehensive Tests" \
  --json conclusion,createdAt,headSha \
  --jq '.[] | "\(.createdAt)\t\(.conclusion)\t\(.headSha[0:8])"'
```

Read the conclusion column:

- **3+ consecutive `failure` on main → SYSTEMIC.** Not the PR's fault. Stop bisecting.
- **Mixed success/failure → flaky pre-existing.** Still not the PR's fault if the failing test files are unrelated to the diff.
- **All `success` on main → potentially PR-introduced.** Now it's worth investigating the PR diff.

Do this for every distinct workflow that's red on the PR. Different workflows can have different states.

### Step 2 — Classify failure signatures from job logs

Pull logs (`gh run view <id> --log-failed` or open the failed job) and grep for these signatures:

| Signature in log | Classification | Action |
| ------------------ | ---------------- | -------- |
| `HTTP 500` / `HTTP 502` / `HTTP 503` from `git fetch`, `actions/checkout`, or `actions/upload-artifact` | GitHub infrastructure flake | Leave as-is. Next push will naturally re-run; do NOT `gh run rerun`. |
| `mojo: error: execution crashed` with `libKGENCompilerRTShared.so` and no Mojo source frame | libKGEN JIT runtime crash, modular#6413 | Reference upstream issue. Do NOT revert Mojo bump. Workaround in a separate PR (e.g. `gdb -batch` wrap to capture cores). |
| `Cannot connect to podman socket` / `dial unix /run/podman.sock: connect: no such file` | Container setup race | Leave as-is or file a CI infra issue. Not PR's fault. |
| `fortify_fail_abort` appearing only in a code comment / docstring | Text-match noise from grep on commit body / file content | Ignore. Not a real abort. |
| Test in a file the PR did not touch failing only on this run | Likely pre-existing or flake — confirm via Step 1 main history | Do NOT rerun; document and proceed. |
| Test the PR DID touch failing reproducibly | PR-introduced regression | Fix the PR. |

### Step 3 — Apply policy (ProjectOdyssey)

Three hard rules from user memory:

- **`feedback_no_ci_retries.md`** — **NEVER** run `gh run rerun` (or `--failed`) to dismiss a failure as a flake. Root-cause it, file an upstream issue if it's a Modular bug, and implement a workaround.
- **`feedback_no_revert_bumps.md`** — **NEVER** propose reverting or pinning back a Mojo version bump because CI broke. Fix forward.
- **`feedback_jit_crashes_fixable.md`** — Investigate execution crashes as real bugs. Don't close them as "unfixable JIT issues."

If your instinct on a red PR is "just rerun" or "revert the bump," stop and re-read this section.

### Step 4 — Resolve

- **Systemic main failure**: leave the surface PR's failure as-is, link the existing tracking PR/issue (e.g. PR #5382 for the gdb-capture workaround, modular#6413 for the upstream). Mention in PR comment: "This failure also occurs on `main` — see `<link>`; addressed separately."
- **Infrastructure flake**: do nothing. The next push for any reason will trigger a fresh run; the flake will not persist.
- **PR-introduced**: fix the PR.

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
| --------- | ---------------- | --------------- | ---------------- |
| 1 | Assumed the new red CI was my fix's regression and started bisecting the PR diff | Did not check `main` history first; wasted ~30 min before realizing 7+ consecutive main runs had the same failure | Always run the Step 1 `gh run list --branch main` query FIRST before touching the PR |
| 2 | Considered `gh run rerun --failed` to retry the crashed Mojo jobs "just to see if it was a one-off" | Violates `feedback_no_ci_retries.md`; reruns mask systemic upstream bugs and produce no diagnostic value | Root-cause the signature (libKGEN -> modular#6413), reference the upstream issue, implement a documented workaround in a separate PR |
| 3 | Considered proposing to revert the Mojo version bump because the JIT crash appeared after it | Violates `feedback_no_revert_bumps.md`; reverting hides the bug from upstream and traps the repo on an old toolchain | Fix forward: file/reference the Modular issue, add a CI-side workaround (e.g. `gdb -batch` core capture), keep the bump |
| 4 | Treated a `fortify_fail_abort` substring in a commit body / docstring as a real abort signature | The string only appeared in narrative text inside a log dump, not in an actual abort frame | Grep for the full structural pattern (e.g. `received signal SIGABRT` + frame address) before tagging as a real crash |
| 5 | Treated GitHub `HTTP 500` on `git fetch` during checkout as PR-introduced | It's a GitHub-side service-availability issue affecting all checkouts in that window | Tag as infra flake; leave alone; will clear naturally on next push |

## Results & Parameters

### The one command to memorize

```bash
gh run list --branch main --limit 10 \
  --workflow="<workflow name>" \
  --json conclusion,createdAt,headSha \
  --jq '.[] | "\(.createdAt)\t\(.conclusion)\t\(.headSha[0:8])"'
```

Run it for every workflow that is red on the PR. Repeat for each distinct workflow name (e.g. `Comprehensive Tests`, `Build Validation`, `Pre-commit`).

### Signature → classification map

| Log signature | Tag | Upstream / tracking |
| ----------------- | ----- | --------------------- |
| `HTTP 5xx` on `git fetch` / `actions/checkout` | infra-flake | GitHub status page |
| `mojo: error: execution crashed` + `libKGENCompilerRTShared.so` | mojo-jit | modular/modular#6413 |
| Podman socket connect refused | container-setup | repo infra |
| `fortify_fail_abort` substring in narrative text | noise | n/a — ignore |
| Test file outside PR diff, reproducible on main | systemic | check Step 1, link main run |
| Test file inside PR diff, reproducible locally | pr-regression | fix the PR |

### Decision rule (one-liner)

> If `gh run list --branch main` shows 3+ consecutive `failure` for the same workflow, the failure is systemic — do not blame the PR, do not rerun, do not revert, do not bisect.

## Related Skills

- `mojo-jit-crash-retry` — deep dive on libKGEN crash forensics (coredumps, symbolication, hypothesis-disproof). Use AFTER this skill classifies a failure as `mojo-jit`.
- `pr-review-no-action-ci-diagnosis` — handles the no-action verdict path once triage decides the PR is clean.
- `ci-cd-failure-diagnosis-log-analysis` — broader log-analysis patterns for non-Mojo CI signatures.
- `preexisting-flaky-crash-rerun` / `mojo-transient-crash-rerun` — **superseded for ProjectOdyssey** by the no-rerun policy; do not use their `gh run rerun` recommendation in this repo.
