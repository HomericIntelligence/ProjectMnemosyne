---
name: ci-cd-achaean-fleet-ci-cascade-patterns
description: "AchaeanFleet Docker infrastructure CI cascade failure sequence and fixes. Use when: (1) running a myrmidon swarm on HomericIntelligence/AchaeanFleet, (2) diagnosing cascading CI failures in a Docker image build pipeline, (3) fixing base-image ENTRYPOINT, OCI multi-arch build, or vendor download URL issues in AchaeanFleet vessels."
category: ci-cd
date: 2026-04-24
version: "1.0.0"
user-invocable: false
verification: verified-ci
tags: [achaeanfleet, docker, ci-cascade, multi-arch, oci, opencode, goose, entrypoint, qemu]
---

# CI/CD: AchaeanFleet CI Cascade Patterns

## Overview

| Field | Value |
|-------|-------|
| **Date** | 2026-04-24 |
| **Objective** | Document the ordered cascade of CI failures encountered in AchaeanFleet myrmidon swarm sessions so future sessions can fix them in sequence without wasted iteration |
| **Outcome** | Successful — 13 open PRs → 0 open PRs; ~10 issues implemented; cascade sequence fully mapped |
| **Verification** | verified-ci |

AchaeanFleet (`HomericIntelligence/AchaeanFleet`) is an infrastructure-only Docker image repo
for the HomericIntelligence agent mesh. It builds 3 base images and 9+ vessel images. When
CI is broken, failures are cascading — fixing one reveals the next. This skill documents the
observed order and exact fix for each layer.

## When to Use

- Starting a myrmidon swarm or implementation sprint on AchaeanFleet
- CI is red and the error message points to Docker build, ENTRYPOINT check, version pin test, or multi-arch build
- A vessel Dockerfile's tool download URL returns 404
- Multi-arch build fails with `oci-layout://` reference errors
- `goose --version || true` is hiding a real build failure

## Verified Workflow

### Quick Reference

```bash
# 1. Check YAML syntax first (prevents all subsequent failures)
python3 -c "import yaml; yaml.safe_load(open('.github/workflows/ci.yml')); print('OK')"

# 2. Check base image references in vessel Dockerfiles
grep "FROM\|ARG BASE_IMAGE" vessels/*/Dockerfile

# 3. Verify all three bases have ENTRYPOINT
grep "ENTRYPOINT" bases/Dockerfile.node bases/Dockerfile.python bases/Dockerfile.minimal

# 4. Check OCI output path (must be directory, not .tar)
grep "type=oci,dest=" dagger/pipeline.ts .github/workflows/ci.yml

# 5. Verify opencode download URL
grep -r "opencode" vessels/opencode/Dockerfile

# 6. Check for || true masking real failures
grep "|| true" vessels/*/Dockerfile
```

### Detailed Steps

**The cascade failure order** (fix each in sequence — each fix reveals the next):

#### Level 1: YAML Syntax Errors

Immediate failure before any job runs.

```bash
# Fix: validate YAML before pushing
python3 -c "import yaml; yaml.safe_load(open('.github/workflows/ci.yml')); print('OK')"
# Also check compose files
python3 -c "import yaml; yaml.safe_load(open('compose/docker-compose.mesh.yml')); print('OK')"
```

#### Level 2: Docker Build Failures — Wrong Base Image References

Vessel Dockerfiles may reference a base that was renamed or doesn't match the matrix.

```dockerfile
# Pattern: vessel must declare ARG BASE_IMAGE and use it
ARG BASE_IMAGE
FROM ${BASE_IMAGE}
```

#### Level 3: Version Pin Test Failures

`test_dockerfile_pins.py` and `test_dockerfile_version_pins.py` enforce that every
`apt-get install` line uses `package=version` pins, not bare package names.

```bash
# Find unpinned installs
grep -n "apt-get install" bases/Dockerfile.* vessels/*/Dockerfile | grep -v "=[0-9]"
# Fix: pin every package with =version suffix
```

#### Level 4: Compose Validation Failures

Missing `depends_on`, bad volume mount paths, or unlisted services.

```bash
# Validate compose files
docker compose -f compose/docker-compose.mesh.yml config --quiet
```

#### Level 5: "Verify ENTRYPOINT is set" Failures

**Critical**: All three base images MUST have `ENTRYPOINT`. The CI check runs on ALL bases.

```dockerfile
# All three of these files need this line:
# bases/Dockerfile.node
# bases/Dockerfile.python    ← commonly missing
# bases/Dockerfile.minimal   ← commonly missing
ENTRYPOINT ["/entrypoint.sh"]
```

```bash
# Verify
grep "ENTRYPOINT" bases/Dockerfile.node bases/Dockerfile.python bases/Dockerfile.minimal
# Expected: all three should show: ENTRYPOINT ["/entrypoint.sh"]
```

#### Level 6: Multi-Arch Build Failures — OCI Layout Directory vs Tarball

The `oci-layout://` protocol requires a **directory**, not a `.tar` file.

```bash
# WRONG — creates tarball, oci-layout:// cannot read it:
--output type=oci,dest=/tmp/foo.tar

# CORRECT — creates OCI directory layout:
--output type=oci,dest=/tmp/foo
```

In `dagger/pipeline.ts` or CI workflow:

```typescript
// Wrong:
const outputPath = `/tmp/${imageName}.tar`;
// Right:
const outputPath = `/tmp/${imageName}`;  // no extension = directory
```

QEMU must also be registered before buildx for multi-arch builds:

```yaml
- name: Set up QEMU
  uses: docker/setup-qemu-action@v3   # MUST come before setup-buildx
- name: Set up Docker Buildx
  uses: docker/setup-buildx-action@v3
```

#### Level 7: opencode Download URL Wrong

The opencode vessel downloads a binary release. The asset name changed between versions.

```dockerfile
# WRONG (asset does not exist):
ARG OPENCODE_VERSION=0.1.x
RUN curl -fsSL "https://github.com/sst/opencode/releases/download/v${OPENCODE_VERSION}/opencode_linux_amd64.tar.gz"

# CORRECT (actual asset name as of 2026-04):
RUN curl -fsSL "https://github.com/sst/opencode/releases/download/v${OPENCODE_VERSION}/opencode-linux-x64.tar.gz"
```

Always verify release asset names:

```bash
gh release view v<VERSION> --repo sst/opencode --json assets --jq '.[].name'
```

#### Level 8: `|| true` Masking Real Failures

`goose --version || true` (and similar patterns) hides build errors on non-amd64 architectures.
Once QEMU is correctly set up, these suppressions must be removed.

```dockerfile
# Before (masks failures):
RUN goose --version || true

# After (correct — binary must work):
RUN goose --version
```

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
|---------|----------------|---------------|----------------|
| Fix ENTRYPOINT in only Dockerfile.node | Assumed only node base needed ENTRYPOINT since most vessels use it | CI "Verify ENTRYPOINT" check runs on all 3 base images independently | All three bases (node, python, minimal) MUST have ENTRYPOINT |
| `--output type=oci,dest=/tmp/foo.tar` | Assumed .tar suffix creates valid OCI tarball for oci-layout:// | `oci-layout://` protocol reads directory layout, not tarballs | Drop the .tar extension — an extensionless path creates an OCI directory |
| `opencode_linux_amd64.tar.gz` download URL | Followed naming convention from other tools (amd64) | The opencode release asset is named `opencode-linux-x64.tar.gz` (x64 not amd64) | Always verify release asset names with `gh release view` before hardcoding URLs |
| Keep `goose --version \|\| true` after QEMU fix | Left the suppression in place after adding QEMU setup | Non-amd64 build failures were silently swallowed, masking broken arm64 vessel builds | Remove `\|\| true` once QEMU is available — binary version checks must be hard failures |
| Fixing ci.yml rebase conflicts by keeping PR's version | Multiple swarm branches both modify the validate job's step block | Conflict at lines 260-430; PR's version may duplicate steps already in HEAD | Keep HEAD's version of shared steps; add only genuinely new steps from the PR |

## Results & Parameters

### Session Outcome

- **Repo**: `HomericIntelligence/AchaeanFleet`
- **Session type**: Multi-session myrmidon swarm
- **Starting state**: 13 open PRs, ~235 issues (prior session had classified 235 → 10 remaining)
- **Ending state**: 0 open PRs, ~10 issues implemented, 3 new PRs created (#547, #548, #549)
- **Issues remaining after session**: ~6 labeled "research" (#421, #353, #325, #305, #302, #277) + #184 (Nomad TLS, requires infrastructure)

### Issues to Leave for Research Sessions

These issues are genuinely hard and should NOT be attempted in a swarm implementation session:

- `#421, #353, #325, #305, #302, #277` — labeled "research", require design/investigation
- `#184` — Phase 6 Nomad TLS cert distribution, requires infrastructure provisioning

### CI Rebase Conflict Resolution for ci.yml

When multiple swarm branches both modify `ci.yml` (adding different validate steps), the
conflict always appears in the validate job's step block (lines 260-430 in AchaeanFleet).

**Resolution strategy**:
1. Keep HEAD's version of all shared/duplicate steps
2. Identify the PR's genuinely new steps (not duplicates of HEAD)
3. Add only those new steps at the appropriate position
4. Validate YAML after resolution: `python3 -c "import yaml; yaml.safe_load(open('.github/workflows/ci.yml'))"`

### Classification Accuracy

The prior session's classification of 235 → 10 remaining issues was accurate.
All "easy" issues were successfully implemented. This validates the classification methodology
documented in `batch-low-difficulty-issue-impl`.

## Verified On

| Project | Context | Details |
|---------|---------|---------|
| HomericIntelligence/AchaeanFleet | Multi-session myrmidon swarm 2026-04 | 13 PRs → 0, cascade sequence fully mapped |
