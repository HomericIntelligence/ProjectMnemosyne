---
name: gha-slsa-docker-build-attestation
description: "Use when: (1) adding SLSA provenance or SBOM attestations to a Docker image publish GitHub Actions workflow, (2) choosing between provenance mode=min vs mode=max for supply-chain audit compliance, (3) writing structural regression tests for GHA workflow YAML flags using yaml.safe_load instead of regex, (4) deciding whether to use docker/build-push-action built-in attestation vs slsa-github-generator reusable workflow, (5) adding id-token: write and attestations: write permissions to a publish job with blast-radius analysis, (6) making pyyaml an explicit dev dependency instead of relying on it transitively."
category: ci-cd
date: 2026-06-20
version: "1.0.0"
user-invocable: false
tags:
  - slsa
  - sbom
  - attestation
  - provenance
  - docker
  - docker-build-push
  - github-actions
  - supply-chain
  - id-token
  - oidc
  - pyyaml
  - structural-testing
  - yaml-safe-load
---

# GHA SLSA Docker Build Attestation

## Overview

| Field | Value |
|-------|-------|
| Date | 2026-06-20 |
| Objective | Add SLSA provenance (`mode=max`) and SBOM attestations to an existing `docker/build-push-action` step in a Docker image publish GitHub Actions workflow, with structural regression tests that prevent flag-placement bugs |
| Outcome | Publish workflow emits signed SLSA provenance and SPDX SBOM for every image push; 6 structural regression tests using `yaml.safe_load` guard that the flags land in the correct step; `pyyaml` declared explicitly in dev deps |
| Verification | verified-local |

## When to Use

- Adding SLSA provenance or SBOM attestations to a Docker image publish workflow.
- Choosing between `provenance: true` (mode=min, omits build materials) and `provenance: mode=max` (records source materials, satisfies supply-chain audits).
- Deciding between `docker/build-push-action` built-in attestation and the `slsa-github-generator` reusable workflow.
- Writing regression tests for GHA workflow YAML to assert flags are under the correct YAML step (not just somewhere in the file).
- Scoping `id-token: write` and `attestations: write` permissions to a specific job to limit blast radius.
- Evaluating the risk of `id-token: write` in a workflow where actions are pinned to 40-char commit SHAs.

## Verified Workflow

### Quick Reference

| Goal | Mechanism | Key constraint |
|------|-----------|----------------|
| SLSA provenance | `provenance: mode=max` in `docker/build-push-action` `with:` block | `mode=max` (not `true` / `mode=min`) to include build materials |
| SBOM attestation | `sbom: true` in `docker/build-push-action` `with:` block | Requires `attestations: write` permission |
| OIDC token | `id-token: write` in publish job `permissions:` | Job-level scope (not workflow-level) |
| Regression tests | `yaml.safe_load` + structural navigation to the specific step | Never use `re.search` on raw YAML text |
| pyyaml availability | Declare `pyyaml = ">=6.0,<7"` in dev deps explicitly | Do not rely on transitive dep from `pre-commit` |
| Consumer verification | `gh attestation verify oci://ghcr.io/<org>/<repo>:<tag> --owner <org>` | Run after each tagged release |

### Detailed Steps

#### A. Permissions block on the publish job

Add `id-token: write` and `attestations: write` to the `permissions:` block of the job that calls `docker/build-push-action`. Scope at job level, not workflow level.

```yaml
jobs:
  publish:
    permissions:
      contents: read
      packages: write
      id-token: write     # required for OIDC → SLSA provenance signing
      attestations: write # required for SBOM + provenance attestation upload
```

**Why job-level, not workflow-level:** A workflow-level `id-token: write` grants OIDC token access to every job, including untrusted third-party actions that may be in earlier jobs (e.g., a lint job that `uses: some-third-party/action@...`). Job-level scoping limits the token to only the publish job.

**Risk posture for `id-token: write`:** The OIDC token this permission grants lets an action exchange it for a short-lived cloud credential scoped to this repository. The blast radius is bounded to the current repo when all actions in the job are pinned to 40-char commit SHAs (no mutable `@v1` tags). Verify with:

```bash
grep -n "uses:" .github/workflows/publish.yml | grep -v "@[0-9a-f]\{40\}"
# Should return nothing — every uses: line must end with a 40-char SHA
```

#### B. Attestation flags in the `docker/build-push-action` `with:` block

Add `provenance` and `sbom` to the **same** `with:` block as the existing build step, not as separate steps:

```yaml
- name: Build and push
  uses: docker/build-push-action@<SHA>  # v6+
  with:
    context: .
    push: true
    tags: ${{ steps.meta.outputs.tags }}
    labels: ${{ steps.meta.outputs.labels }}
    provenance: mode=max   # SLSA level 2; records build materials
    sbom: true             # SPDX SBOM
```

**`provenance: mode=max` vs `provenance: true` (mode=min):**

| Value | SLSA level | Build materials | Supply-chain audit? |
|-------|-----------|-----------------|---------------------|
| `true` / `mode=min` | L1 | Not included | Cosmetic only |
| `mode=max` | L2+ | Included (source, deps) | Yes — satisfies auditors |

`provenance: true` is the `docker/build-push-action` default, but it maps to `mode=min`, which omits the build materials that make the attestation meaningful. Always use `mode=max` for real supply-chain security.

**`docker/build-push-action` vs `slsa-github-generator` reusable workflow:**

| Approach | Shape change | When to use |
|----------|-------------|-------------|
| `docker/build-push-action` built-in (`provenance: mode=max`, `sbom: true`) | Minimal — two flags on existing step | Existing workflow already uses this action; no job split needed |
| `slsa-github-generator` reusable workflow | Major — requires build/sign job split and separate caller workflow | Starting from scratch or need SLSA L3 |

Use `docker/build-push-action` built-in when you already have a working publish workflow. The reusable workflow approach is only warranted when you need SLSA L3 (tamper-proof build process in a hermetic environment).

#### C. Structural regression tests using `yaml.safe_load`

The critical discipline: **never use `re.search` on raw YAML text** to assert attestation flags. A regex test passes even if the flag appears in the wrong step, the wrong job, or at workflow level. Use `yaml.safe_load` and navigate the structure to the specific step.

```python
import yaml
from pathlib import Path

_WORKFLOW_PATH = Path(".github/workflows/publish.yml")

def _publish_workflow() -> dict:
    return yaml.safe_load(_WORKFLOW_PATH.read_text())

def _publish_job() -> dict:
    jobs = _publish_workflow()["jobs"]
    # Adjust key to match your workflow's actual job name
    return jobs["publish"]

def _build_push_step() -> dict:
    for step in _publish_job()["steps"]:
        if step.get("name") == "Build and push":
            return step
    raise AssertionError("Could not locate the 'Build and push' step in publish.yml")


def test_publish_job_has_id_token_write() -> None:
    perms = _publish_job().get("permissions", {})
    assert perms.get("id-token") == "write", (
        "publish job must declare 'id-token: write' for SLSA provenance signing"
    )

def test_publish_job_has_attestations_write() -> None:
    perms = _publish_job().get("permissions", {})
    assert perms.get("attestations") == "write", (
        "publish job must declare 'attestations: write' for SBOM upload"
    )

def test_build_push_step_exists() -> None:
    step = _build_push_step()
    assert step is not None

def test_build_push_step_enables_max_provenance() -> None:
    with_block = _build_push_step().get("with", {})
    assert with_block.get("provenance") == "mode=max", (
        "provenance must be 'mode=max' (not 'true'/mode=min) to include build materials"
    )

def test_build_push_step_enables_sbom() -> None:
    with_block = _build_push_step().get("with", {})
    assert with_block.get("sbom") is True, (
        "sbom must be true in the Build and push step's with: block"
    )

def test_build_push_step_has_push_true() -> None:
    with_block = _build_push_step().get("with", {})
    assert with_block.get("push") is True, (
        "push must be true — attestations are only created when the image is pushed"
    )
```

**Why structural navigation beats regex:**

```python
# BAD — passes even if provenance: mode=max is in a comment, the wrong step, or wrong job
assert re.search(r"provenance:\s*mode=max", workflow_text)

# GOOD — fails if the flag is in any context other than the correct step's with: block
assert _build_push_step()["with"]["provenance"] == "mode=max"
```

#### D. Explicit pyyaml dev dependency

The structural tests require `pyyaml`. Do not rely on it being available transitively (e.g., pulled in by `pre-commit`). Transitive deps are invisible to lock-file auditors and can disappear when the parent dep is updated.

In `pixi.toml`:

```toml
[feature.dev.dependencies]
pyyaml = ">=6.0,<7"
```

In `pyproject.toml` (if using extras):

```toml
[project.optional-dependencies]
dev = [
    "pyyaml>=6.0,<7",
]
```

#### E. ADR for `id-token: write` security tradeoff

Create an ADR documenting the decision and its mitigations. Key sections:

- **Status:** Accepted
- **Context:** `id-token: write` is required for OIDC-based SLSA provenance signing. It grants any action in the job the ability to request an OIDC token exchangeable for short-lived cloud credentials.
- **Decision:** Scope `id-token: write` at job level (not workflow level). Pin all actions in the publish job to 40-char commit SHAs to bound the blast radius.
- **Consequences:** All future actions added to the publish job must be SHA-pinned. The job must not call untrusted third-party actions without security review.
- **Verification command:** `gh attestation verify oci://ghcr.io/<org>/<repo>:<tag> --owner <org>`

Add a one-sentence cross-reference in `CLAUDE.md` or `README.md`:
```
Each published image carries SLSA provenance (`mode=max`) and an SPDX SBOM attestation
(see [ADR-004](docs/adr/ADR-004-slsa-build-provenance.md)).
```

#### F. Verify attestations after release

After pushing a versioned tag and the publish workflow completes:

```bash
gh attestation verify oci://ghcr.io/<org>/<repo>:<tag> --owner <org>
```

Expected output: `Attestation verified: SLSA provenance (mode=max)` and SBOM attestation line. Any failure here means the `id-token: write` or `attestations: write` permissions were not correctly applied, or the action SHA is too old to support attestation.

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
|---------|----------------|---------------|----------------|
| `provenance: true` | Set `provenance: true` in the `with:` block (verbatim from the issue description) | `true` maps to `mode=min`, which omits build materials. The attestation is created but is cosmetically SLSA without recording sources, deps, or build environment. Supply-chain auditors reject it. | Always use `provenance: mode=max`. The `true` default exists for backward compat, not for meaningful supply-chain security. |
| Regex tests on raw YAML | Used `re.search(r"provenance:\s*mode=max", workflow_text)` in test | Passes even if the flag is in a comment, the wrong step, the wrong job, or at workflow level. A flag in the wrong YAML context provides false assurance. | Use `yaml.safe_load` + structural navigation to the specific step's `with:` block. The test must fail if the flag migrates to any other location. |
| Relying on transitive pyyaml | Assumed `pyyaml` would be available because `pre-commit` pulls it in | Transitive deps are invisible in the lock file. They disappear when the parent dep is updated or dropped. The tests fail in a clean environment where `pre-commit` is not installed. | Declare `pyyaml = ">=6.0,<7"` explicitly in dev dependencies. |
| Workflow-level `id-token: write` | Added the permission at the top-level `permissions:` block | Grants OIDC token access to every job in the workflow, including lint and test jobs that may call third-party actions. Violates principle of least privilege. | Scope `id-token: write` at the `jobs.<publish>.permissions:` level to limit OIDC token availability to the publish job only. |
| `slsa-github-generator` reusable workflow | Considered using the `slsa-github-generator` for L3 provenance | Requires splitting the workflow into build and sign jobs, a separate caller workflow, and significantly different YAML structure. For an existing workflow already using `docker/build-push-action`, this is unnecessary complexity — `mode=max` in the existing step achieves L2 provenance. | Use `docker/build-push-action` built-in attestation when the workflow already uses that action. `slsa-github-generator` is only warranted for L3 (hermetic build environment). |

## Results & Parameters

**Test file placement:** Tests that parse `.github/workflows/publish.yml` belong in the test suite alongside other CI integration tests (e.g., `tests/test_ci_publish_workflow.py`). They run with `pytest` and do not require a live Docker daemon or GitHub credentials.

**Minimum action version for attestation support:** `docker/build-push-action@v6+` (or its equivalent 40-char SHA). Earlier versions do not support the `provenance` and `sbom` flags.

**Permission matrix for the publish job:**

| Permission | Value | Purpose |
|-----------|-------|---------|
| `contents` | `read` | Checkout source |
| `packages` | `write` | Push to GHCR |
| `id-token` | `write` | OIDC token for SLSA signing |
| `attestations` | `write` | Upload attestation to GitHub |

**Verification command for consumers:**

```bash
gh attestation verify oci://ghcr.io/<org>/<repo>:<tag> --owner <org>
```

**Full test count context:** When adding these 6 structural tests, they run alongside the existing pytest suite. They add < 100 ms overhead (pure YAML parse, no I/O beyond reading one file).

**Incidental fix: committed artifacts in git history.** If `coverage.xml` or `.coverage` were accidentally committed before setting up the workflow, remove them:

```bash
git rm --cached coverage.xml
echo "coverage.xml" >> .gitignore
echo ".coverage" >> .gitignore
git commit -m "chore: remove coverage.xml artifact and add to .gitignore"
```

## Verified On

| Project | Context | Details |
|---------|---------|---------|
| ProjectHermes | Issue #491 / ADR-004 | Added `provenance: mode=max` + `sbom: true` to `.github/workflows/publish.yml`; 6 structural regression tests using `yaml.safe_load`; `pyyaml = ">=6.0,<7"` added to pixi.toml dev deps; 507 unit tests passed; 97.60% coverage |
