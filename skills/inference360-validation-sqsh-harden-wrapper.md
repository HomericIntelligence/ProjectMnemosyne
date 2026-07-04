---
name: inference360-validation-sqsh-harden-wrapper
description: "Harden Inference360 local validation around digest-verified Enroot/SquashFS wrappers. Use when: (1) replacing a removed Podman dev-container validation path, (2) resolving validation images from WardenRuntime manifests, (3) strict review requires fail-closed shell wrapper and CI/local validation separation."
category: ci-cd
date: 2026-07-04
version: "1.0.0"
user-invocable: false
verification: verified-ci
tags: [inference360, validation, enroot, squashfs, wardenruntime, ci, shell, strict-review]
---

# Inference360 Validation SquashFS Wrapper Hardening

## Overview

| Field | Value |
|-------|-------|
| **Date** | 2026-07-04 |
| **Objective** | Fix strict PR review findings for an Inference360 validation change that moved public local `just validate` from a removed Podman dev-container path to a digest-verified local Enroot/SquashFS wrapper. |
| **Outcome** | Successful: unrelated scope was removed, the wrapper resolved image provenance from reviewed WardenRuntime manifests, stale Enroot rootfs reuse was eliminated, and local plus GitHub PR checks passed. |
| **Verification** | verified-ci |

## When to Use

- Inference360 `just validate` needs to stay local and containerized while hosted GitHub runners use host validation because they do not have local Enroot/SquashFS.
- A shell wrapper must bootstrap validation before the normal Python/private helpers can be trusted or installed.
- Strict review flags stale container rootfs reuse, regex interpolation in shell parsers, missing cluster fail-closed behavior, or digest checks that only validate manifest text.
- A PR bundles unrelated Warden lifecycle, progress logging, or issue-range evidence changes with validation wrapper work and needs scope reduction before merge.

## Verified Workflow

### Quick Reference

```bash
# Start by minimizing drift from the target branch.
git fetch origin
git rebase origin/master
git rev-list --left-right --count origin/master...HEAD

# Keep local validation containerized.
just validate              # calls scripts/run_validation_container.sh locally
just _validate-host        # used by GitHub Actions hosted runners

# Wrapper preflight contract.
bash -n scripts/run_validation_container.sh
scripts/run_validation_container.sh --help
just --dry-run validate
just --dry-run _validate-host
```

### Detailed Steps

1. Rebase the PR branch on `origin/master` before fixing review issues. If the rebase skips a patch-equivalent commit that is already on master, treat that as scope reduction, then prove the branch is not behind with:

   ```bash
   git rev-list --left-right --count origin/master...HEAD
   ```

2. Remove unrelated PR scope before merge. For the verified PR, Warden lifecycle progress logging docs/tests/code and issue-range evidence docs were unrelated to the validation wrapper issue, so restoring those files to `origin/master` removed strict review blockers.

3. Preserve the CI/local split:
   - `just validate` remains public local validation and calls `scripts/run_validation_container.sh`.
   - GitHub Actions calls `just _validate-host` because hosted runners do not provide the local Enroot/SquashFS runtime.

4. Resolve validation image defaults from the reviewed `WardenRuntime` manifest in `manifests/services/warden-runtime.yaml`. Do not resolve the wrapper defaults from `ModelService`, default model manifests, or hardcoded private paths.

5. Keep the host bootstrap parser deliberately narrow. Because the wrapper runs before validation, parse only:
   - `kind: WardenRuntime`
   - the selected `clusters.<name>` profile
   - `runtime.container_squashfs`
   - `runtime.container_digest`

   Document this exception in the design and operator docs so future maintainers do not replace it with broader host Python/private helper calls before validation.

6. Make the wrapper fail closed and avoid shell parser footguns:
   - fail when `--cluster` is missing from `clusters`, with an error like `missing required cluster profile: clusters.<name>`;
   - avoid regex interpolation when matching cluster names in awk/shell;
   - require a `.sqsh` image path;
   - require `runtime.container_digest` to match `sha256:<64 hex>`;
   - compute the actual `.sqsh` digest and exit on mismatch before any Enroot call.

7. Bind the verified SquashFS bytes to the rootfs that is actually started. If a same-named Enroot rootfs already exists:

   ```bash
   enroot remove -f <name>
   enroot create --name <name> <container.sqsh>
   enroot start <name>
   ```

   Handle `enroot list` failure directly instead of treating it as an absent rootfs.

8. Restage host `uv` every run. Copy it to a temp file, `chmod 0555`, then atomically move it into `/i360-tmp/host-bin/uv` so stale or corrupted staged binaries cannot persist across validation runs.

9. Strengthen tests around real risk, not only happy paths:
   - default checked-in WardenRuntime manifest resolution with `$CONTAINERDIR` expansion;
   - unknown cluster profile fails closed and does not leak private paths;
   - digest mismatch on the non-`--print` path produces no Enroot logs or calls;
   - existing rootfs is removed before create/start;
   - repeated `uv` staging overwrites stale staged files and restores `0555` mode;
   - `--print` shows the remove/create/start sequence;
   - docs tests assert the fresh-rootfs and WardenRuntime contracts.

10. Verify locally and in CI before enabling merge.

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
|---------|----------------|---------------|----------------|
| Digest mismatch tested only under `--print` | Asserted digest validation while printing the command plan | `--print` did not prove the real execution path avoided Enroot calls | Add a non-`--print` digest-mismatch test that proves no Enroot log/call appears |
| Checked only that staged `uv` existed | Reused a previously staged host `uv` binary | Existence alone does not prove stale or corrupted binaries are replaced | Corrupt the staged file and permissions before rerun, then assert replacement and `0555` mode |
| Custom AWK parser silently fell back | Unknown cluster names used top-level defaults | This diverged from the Python resolver and could launch with the wrong runtime path | Missing `clusters.<name>` must fail closed with a narrow, non-leaking error |
| Reused existing Enroot rootfs | Started a same-named rootfs after verifying only current `.sqsh` bytes | The verified bytes were not necessarily the bytes used to create the stale rootfs | Remove any same-named rootfs, recreate it from the verified `.sqsh`, then start |
| Bundled unrelated lifecycle work | Mixed Warden progress logging and issue-range evidence changes into the validation wrapper PR | Strict review flagged major scope blockers unrelated to the target issue | Restore unrelated hunks to `origin/master` or split them into separate PRs |

## Results & Parameters

### Verified Commands

```bash
env UV_CACHE_DIR=.tmp/uv-cache just pre-commit
env UV_CACHE_DIR=.tmp/uv-cache just _validate-host
env UV_CACHE_DIR=.tmp/uv-cache uv run pytest \
  tests/test_setup_workflow.py \
  tests/test_cli.py \
  tests/test_ci_workflow.py \
  tests/test_local_container_docs.py \
  tests/test_quality_gate_scripts.py \
  tests/test_inference360_utils.py \
  tests/test_cleanup_contracts.py \
  tests/test_onboarding_docs.py -q
env UV_CACHE_DIR=.tmp/uv-cache uv run pytest tests/test_setup_workflow.py -q -k "validation_container_wrapper"
env UV_CACHE_DIR=.tmp/uv-cache uv run ruff check inference360 tests
env UV_CACHE_DIR=.tmp/uv-cache uv run ruff format --check inference360 tests
bash -n scripts/run_validation_container.sh
git diff --check origin/master
just --dry-run validate
just --dry-run _validate-host
scripts/run_validation_container.sh --help
```

### Observed Results

| Check | Result |
|-------|--------|
| `just pre-commit` | passed |
| `just _validate-host` | passed with `1151 passed, 1 skipped`, coverage `81.99%` |
| Focused host suite | passed with `495 passed` |
| `validation_container_wrapper` focused tests | passed with `11 passed, 21 deselected` |
| Ruff check and format check | passed |
| Shell syntax, dry-run, help, and diff checks | passed |
| GitHub PR checks | all passed |

### PR Evidence

| Project | Context | Details |
|---------|---------|---------|
| LLM360/Inference360 | PR #339 strict review fixes for issue #340 | Final head `ccc9dd108e1ca821814c4cbf2d8d4b8749e83b8f`; mergeable; all PR checks passed after force-with-lease push. |

### Redaction Contract

Do not include private endpoint addresses, absolute infrastructure paths, checkpoint paths, prompts, tokens, cookies, or user-specific paths in docs, tests, PR text, or skill content. Use placeholders such as `<REPO>`, `<REDACTED_ENDPOINT>`, `<REDACTED_CHECKPOINT_PATH>`, and `<REDACTED_INFRA_PATH>` when shape matters.

## Verified On

| Project | Context | Details |
|---------|---------|---------|
| LLM360/Inference360 | PR #339, verified-ci | Local host/container wrapper checks and GitHub PR checks passed for digest-verified Enroot/SquashFS validation wrapper hardening. |
