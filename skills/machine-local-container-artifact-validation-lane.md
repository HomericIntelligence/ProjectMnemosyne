---
name: machine-local-container-artifact-validation-lane
description: "Keep a local validation lane containerized against a machine-local, digest-verified image artifact while hosted CI uses a host lane, and fail closed when the artifact is missing. Use when: (1) `just validate` (or equivalent) must run in a reviewed container locally but hosted runners lack that container runtime, (2) a validation wrapper must bootstrap before the normal language/private helpers can be trusted, (3) a build/run tool does NOT fetch or build the runtime image so it must be materialized per machine, (4) a digest check only validates manifest text rather than the actual image bytes, (5) strict review flags stale rootfs reuse, unsafe shell interpolation, or a PR bundling unrelated scope."
category: ci-cd
date: 2026-07-18
version: "1.0.0"
tags: [ci-cd, validation, container, image-artifact, digest, fail-closed, host-vs-local-lane, materialization, shell-wrapper, strict-review, scope-reduction]
user-invocable: false
---

# Machine-Local Container-Artifact Validation Lane

## Overview

| Field | Value |
| ------- | ------- |
| **Date** | 2026-07-18 |
| **Objective** | Preserve a containerized local validation lane backed by a machine-local, digest-verified image artifact, split from a host lane for hosted CI, without stale-rootfs reuse or unsafe shell parsing. |
| **Outcome** | Reusable pattern: dual local/host lanes, verify-image-bytes-by-digest, fail-closed on a missing artifact, treat the image as separately materialized per machine, and reduce unrelated PR scope under strict review. |
| **Verification** | verified-ci (generalized from a container-validation wrapper hardening whose local + hosted PR checks passed; the concrete container runtime and product names are intentionally omitted). |

## When to Use

- Local `just validate` (or an equivalent gate) must run inside a reviewed container, but hosted CI runners do not have that container runtime and must run a host lane instead.
- A shell wrapper must bootstrap validation before the normal language/private helpers can be trusted or installed.
- The build/run tool (e.g. `uv run`, `npm`, a task runner) does NOT build or download the runtime image, so the image is a machine-local reviewed artifact that must be materialized on each target environment.
- A digest check currently only validates manifest text rather than the actual image bytes.
- Strict review flags stale container rootfs reuse, regex/interpolation injection in a shell parser, missing fail-closed behavior, or a PR that bundles unrelated lifecycle/logging/evidence changes with the wrapper work.
- The build/run tool reports the runtime image missing on one machine but succeeds on another, and you must tell a missing reviewed artifact apart from a language/runtime/lifecycle failure.

## Verified Workflow

### Quick Reference

```bash
# 1. Keep two lanes explicit: containerized local vs host CI.
just validate         # local: runs the reviewed container wrapper
just _validate-host   # hosted CI: runs validation directly on the host

# 2. Wrapper preflight contract — prove it before trusting it.
bash -n scripts/run_validation_container.sh      # syntax
scripts/run_validation_container.sh --help       # documented interface
just --dry-run validate                          # command it will run
just --dry-run _validate-host

# 3. Verify the IMAGE BYTES, not just the manifest text.
#    require the configured digest to match sha256:<64 hex>,
#    compute the real image digest, and exit BEFORE any container call on mismatch.
```

### Detailed Steps

1. **Minimize drift first.** Rebase the branch on the target base before fixing review findings. If a rebase drops a patch-equivalent commit already on base, that is legitimate scope reduction — then prove the branch is not behind (`git rev-list --left-right --count base...HEAD`).
2. **Reduce unrelated scope.** If the PR bundles changes unrelated to the validation wrapper (lifecycle logging, progress docs, unrelated evidence), restore those files to base. Strict reviewers block on bundled scope; a focused diff merges.
3. **Preserve the CI/local split.** Keep a containerized local lane and a separate host lane for hosted runners that lack the container runtime. Do not "simplify" by collapsing the local lane into the host lane — that silently drops the reviewed-container guarantee. Document why the wrapper bootstraps before the normal language/private helpers, so a future maintainer does not replace it with broader host calls that run before validation.
4. **Verify image bytes by digest, fail closed.** Require the configured image digest to match `sha256:<64 hex>`; compute the actual image artifact's digest and exit on mismatch **before** any container create/start. A digest check that only validates manifest text is false assurance — validate the bytes that will actually run.
5. **Bind the verified bytes to the started rootfs.** If a same-named container rootfs already exists, remove it before create/start so a stale rootfs is never silently reused. Repeated staging must overwrite stale staged files and restore the expected permission mode.
6. **Avoid unsafe shell parsing.** Do not interpolate untrusted manifest fields into regexes or command strings in the wrapper; parse defensively so a crafted manifest value cannot inject behavior.
7. **Treat the image as per-machine materialized.** The runtime image is a machine-local reviewed artifact — it is not built or downloaded by the build/run tool. When it is missing on one machine but present on another, the fix is to materialize it on that machine, not to debug the language runtime. Document this so a "missing runtime artifact" is diagnosed as materialization, distinct from a language/scheduler/lifecycle failure.

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
|---------|----------------|---------------|----------------|
| Collapse the containerized local lane into the host lane | "Simplified" validation to one path | Silently dropped the reviewed-container guarantee locally | Keep local-container and host lanes separate; hosted CI uses the host lane because it lacks the runtime |
| Digest check that validates only the manifest text | Compared the digest string in the manifest | The actual image bytes could differ from the manifest claim | Compute the real artifact digest and exit on mismatch before any container call |
| Reuse an existing same-named container rootfs | Started validation against whatever rootfs was present | Stale rootfs contents contaminated the run | Remove the same-named rootfs before create/start; bind the freshly verified bytes |
| Interpolate manifest fields into a shell regex/parser | Built the wrapper's parsing with raw interpolation | Injection risk / brittle parsing flagged by strict review | Parse defensively; never interpolate untrusted manifest values into regex or command strings |
| Debug the language runtime when the image was "missing" | Chased a Python/runtime error on one machine | The image is a machine-local artifact not fetched by the build tool | Materialize the reviewed image per machine; diagnose a missing artifact as materialization, not a runtime bug |
| Ship the wrapper fix bundled with unrelated changes | Left lifecycle/logging/evidence edits in the PR | Strict review blocked on bundled scope | Restore unrelated files to base; keep the PR focused on the wrapper |

## Results & Parameters

- **Two lanes**: `validate` (containerized local) and `_validate-host` (host CI); never collapse them.
- **Digest contract**: `sha256:<64 hex>`, verified against the real image bytes, fail-closed before any container call.
- **Rootfs**: remove same-named rootfs before start; overwrite stale staged files; restore expected mode.
- **Materialization**: image is per-machine reviewed artifact, not fetched by the build/run tool.
- **Review discipline**: rebase to minimize drift, restore unrelated files to base, keep the diff focused.

## Attribution

Generalized from a project-specific container-validation wrapper hardening (a SquashFS/Enroot-backed `just validate` lane), with the concrete container runtime, product, and cluster names removed. The transferable core — dual local/host lanes, digest-verified image bytes, fail-closed on missing artifacts, per-machine materialization, and strict-review scope discipline — is host- and project-neutral.
