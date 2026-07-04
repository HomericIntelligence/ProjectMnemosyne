---
name: ci-gitleaks-pixi-managed-secrets-scan-planning
description: "Plan a safe replacement of ad hoc Gitleaks release-tarball downloads in required GitHub Actions workflows with pixi-managed lint-environment tooling. Use when: (1) a required secrets-scan job downloads gitleaks directly from GitHub Releases, (2) moving scanner trust to pixi.lock / conda-forge, (3) reviewing whether pixi setup changes preserve gitleaks detect behavior."
category: ci-cd
date: 2026-07-04
version: "1.0.0"
user-invocable: false
verification: unverified
tags: [github-actions, gitleaks, secrets-scan, pixi, pixi-lock, conda-forge, required-workflow, supply-chain, planning, projecthephaestus]
---

# Gitleaks Pixi-Managed Secrets Scan Planning

## Overview

| Field | Value |
|-------|-------|
| **Date** | 2026-07-04 |
| **Objective** | Replace an ad hoc Gitleaks release-tarball download in a required workflow with pixi-managed lint-environment tooling while preserving `gitleaks detect` behavior. |
| **Outcome** | Planning guidance only. The plan identifies the right reviewer risks and verification gates, but it has not confirmed conda-forge availability, lock resolution, GitHub Actions runtime behavior, or exact scanner exit semantics in CI. |
| **Verification** | unverified |

> **Warning:** This workflow has not been validated end-to-end. Treat as a hypothesis until CI confirms.

## When to Use

- A required GitHub Actions job such as `security/secrets-scan` or `security-secrets-scan` downloads `gitleaks_<version>_linux_x64.tar.gz` directly from GitHub Releases.
- You want to move scanner installation into `pixi.toml` / `pixi.lock` so CI uses a locked lint environment instead of an inline download and SHA check.
- A plan proposes `pixi run --environment lint gitleaks detect` and needs reviewer-facing uncertainty called out before implementation.
- You are changing a required workflow such as `.github/workflows/_required.yml` and must avoid job-name, cache, path, or setup side effects that could block all PRs.
- You need to compare the trust model shift: explicit release-tarball SHA verification versus conda-forge package artifacts pinned by the lockfile.

## Proposed Workflow

> **Warning:** This workflow has not been validated end-to-end. Treat as a hypothesis until CI confirms.

### Quick Reference

```bash
# Locate the current secrets-scan implementation and keep the .gitleaks.toml policy unchanged.
grep -nE "security.*secrets|gitleaks|GITLEAKS|setup-pixi-env" .github/workflows/_required.yml
git diff -- .gitleaks.toml

# Confirm the exact package/version exists before editing pixi.toml.
pixi search gitleaks

# Add Gitleaks to the lint feature, then regenerate the lock without installing.
pixi add --feature lint "gitleaks>=8.30.0,<9" --no-install
pixi install --locked

# Reproduce the CI command locally through pixi, not through a downloaded binary.
pixi run --environment lint gitleaks detect --source=. --verbose

# Review only the intended dependency/workflow changes.
git diff -- pixi.toml pixi.lock .github/workflows/_required.yml tests/unit/ci
```

### Detailed Steps

1. **Read the live workflow before planning edits.** Confirm the current `security-secrets-scan` job location, existing checkout depth, any explicit `GITLEAKS_VERSION` / tarball / SHA variables, and the exact `gitleaks detect` flags. Do not infer behavior from a stale plan or from another repository.

2. **Keep scanner policy out of scope unless the issue asks for it.** `.gitleaks.toml` conditionals and allowlists are scanner behavior, not installation mechanics. A tarball-to-pixi change should leave that file unchanged unless a runtime test proves the package changes config interpretation.

3. **Verify conda package availability before committing to the design.** The critical assumption is that the configured pixi channels can solve `gitleaks>=8.30.0,<9` for every platform already present in the repository lockfile. If they cannot, either pick a verified available version with reviewer approval or keep the release-download path.

4. **Regenerate and inspect `pixi.lock` deliberately.** The lockfile should gain the supported platform artifacts and hashes for Gitleaks without broad unrelated resolver churn. Review `git diff -- pixi.lock` for unexpected platform removals, lock-format changes, or dependency movement unrelated to the scanner.

5. **Wire workflow setup in the existing required job.** Prefer the repo's existing `.github/actions/setup-pixi-env` action if other `_required.yml` jobs use it successfully. Insert it in `security-secrets-scan` only where it is needed, and verify the action does not alter paths, caches, or environment variables used by neighboring security jobs.

6. **Preserve the `gitleaks detect` contract.** Replace the downloaded binary invocation with the pixi command while keeping the same source, verbosity, exit-code behavior, and any PR/main conditional semantics. Avoid switching to `gitleaks protect`, `--no-git`, or a reduced diff-only scan unless that is the explicit requirement.

7. **Update tests for behavior-relevant workflow strings, but do not overtrust them.** Unit tests can assert that the workflow calls `setup-pixi-env`, uses the lint environment, removes tarball download variables, and keeps the scan command. They do not prove the GitHub Actions runner can resolve the environment or that the conda-forge binary behaves identically.

8. **Make CI/runtime verification an acceptance criterion.** The minimum implementation proof is local `pixi run --environment lint gitleaks detect` plus the repo's workflow/unit tests. The real confidence gate is the required GitHub Actions job passing after the PR runs.

## Verified Workflow

No verified workflow exists for this learning yet. Use the `## Proposed Workflow` section above; this heading is present only because the ProjectMnemosyne validator currently requires the literal `## Verified Workflow` section name.

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
|---------|----------------|---------------|----------------|
| Release tarball in required workflow | Downloaded a pinned Gitleaks release tarball inside `_required.yml`, checked an explicit SHA-256, extracted the binary, and ran `gitleaks detect` | The scanner install path is ad hoc workflow logic that must be maintained separately from the repo's pixi-managed lint toolchain; upgrades require editing version, URL, tarball name, SHA, and tests together | Prefer a locked pixi lint environment when the exact scanner package is available across lockfile platforms, but review the trust-model shift from explicit release SHA to lockfile-controlled conda artifacts. |
| String-only workflow regression tests | Asserted that `_required.yml` contains or omits expected strings | String tests can catch accidental reintroduction of tarball downloads, but they do not execute GitHub Actions setup or prove the scanner binary behaves the same as the release artifact | Treat tests as structural guards; require local pixi execution and CI job results before calling the migration verified. |

## Results & Parameters

**Captured from:** ProjectHephaestus issue #1483 implementation-plan review context.

**Target objective:** Replace the ad hoc Gitleaks release-tarball download in `.github/workflows/_required.yml` with pixi-managed lint-environment tooling, preserving `gitleaks detect` behavior.

**Plan-cited current state, not independently verified here:** `_required.yml:720-731` was said to download `gitleaks_8.30.0_linux_x64.tar.gz`, verify a hard-coded SHA, extract it, and run `./gitleaks detect`. `_required.yml:683-691` and `_required.yml:743-751` were said to show existing `setup-pixi-env` usage in dependency-scan and SAST jobs.

**Most uncertain assumptions to verify during implementation:**

- The configured pixi channels provide a compatible `gitleaks>=8.30.0,<9` build across every platform represented in the repository lockfile.
- Regenerating `pixi.lock` includes the expected artifacts and hashes without widening scanner-version behavior or creating unrelated resolver drift.
- `.github/actions/setup-pixi-env` can be used safely inside `security-secrets-scan` without cache, PATH, or environment side effects.
- Local `pixi run --environment lint gitleaks detect` faithfully matches the previous downloaded upstream binary behavior.

**Plan evidence not independently checked in this capture:** the cited live target `.github/workflows/_required.yml:720-731`, the claimed setup-pixi-env examples at `_required.yml:683-691` and `_required.yml:743-751`, the `pixi.toml` lint-feature shape, and the proposed `tests/unit/ci/test_gitleaks_config.py` placement came from the implementation plan, not from this `/learn` run.

**Not yet verified:** package availability on the configured pixi channels, lockfile resolution, GitHub Actions runner behavior, and current `gitleaks detect` exit semantics in CI.

**Reviewer checklist:**

- Confirm `.gitleaks.toml` remains unchanged unless scanner behavior testing requires a targeted config edit.
- Confirm the workflow no longer carries duplicated `GITLEAKS_VERSION`, tarball URL/name, or inline SHA variables after the pixi migration.
- Confirm removing the explicit SHA check is accepted as a trust-model move to `pixi.lock` and conda-forge artifacts, not an accidental weakening.
- Confirm the required job name/check context remains stable.
- Confirm tests cover the workflow shape, and CI proves the runtime behavior.

## Verified On

| Project | Context | Details |
|---------|---------|---------|
| ProjectHephaestus | Issue #1483 planning capture | Unverified planning learning from an implementation-plan review; no implementation, lock solve, or CI run had been executed at capture time. |
