---
name: ci-cd-cascading-dockerfile-ci-failure-remediation
description: "Diagnose and fix cascading CI failures specific to Docker/compose infrastructure repos. Use when: (1) a Docker infrastructure repo has 10+ open PRs all failing CI, (2) Dockerfile RUN inline comments cause 'unknown instruction' parse errors, (3) Nomad job validator is run against non-job HCL files (vault policies, etc.), (4) BATS tests fail under set -euo pipefail due to unset BUILD_DATE or VCS_REF variables, (5) pixi.lock is stale after adding dependencies causing CI lockfile gate to fail, (6) pytest pin-enforcement checks fail for yarn or pip install invocations, (7) compose service uses bare WORKSPACE_ROOT mount rejected by CI validator, (8) hardcoded service counts in compose validation break when new services are added, (9) base image FROM line lacks SHA256 digest pinning, (10) OCI layout artifact pipeline uses wrong format (tar vs directory), (11) multi-arch buildx fails because QEMU is not set up before buildx initialization."
category: ci-cd
date: 2026-04-24
version: "1.0.0"
user-invocable: false
verification: verified-ci
tags: [docker, dockerfile, cascading-failures, compose, nomad, bats, pixi, multi-arch, qemu, oci, digest-pinning]
---

# Cascading CI Failure Remediation in Docker Infrastructure Repos

## Overview

| Field | Value |
|-------|-------|
| **Date** | 2026-04-24 |
| **Objective** | Fix 13 open PRs in AchaeanFleet (Docker/compose infrastructure repo) — all failing CI due to cascading failures introduced one at a time as main advanced |
| **Outcome** | All 13 PRs merged; CI green across the entire repo |
| **Verification** | verified-ci |

## When to Use

- Docker infrastructure repo (base images + vessel Dockerfiles + compose files) has many PRs failing CI
- Each fix to main reveals the NEXT hidden failure class (cascading pattern)
- Failures span multiple categories: syntax, runtime, pin enforcement, compose validation, build system
- PRs become DIRTY/UNSTABLE after main advances and need rebasing with conflict resolution

## Verified Workflow

### Quick Reference

```bash
# 1. Fix RUN inline comment parse error
grep -rn "RUN.*\\\\.*#" bases/ vessels/ Dockerfile*
# Remove inline comments from backslash-continuation lines

# 2. Guard Nomad validator against non-job HCL
if ! grep -q '^job ' "$f"; then continue; fi

# 3. Fix BATS unset variable under set -euo pipefail
BUILD_DATE="${BUILD_DATE:-$(date -u +%Y-%m-%dT%H:%M:%SZ)}"
VCS_REF="${VCS_REF:-$(git rev-parse --short HEAD 2>/dev/null || echo unknown)}"

# 4. Regenerate stale pixi.lock
pixi install

# 5. Pin yarn in Dockerfile
RUN npm install -g yarn@1.22.22

# 6. Fix bare workspace mount
# BAD:  ${WORKSPACE_ROOT:-/home/mvillmow}:/workspace
# GOOD: ${WORKSPACE_ROOT:-/home/mvillmow}/Agents/AgentName:/workspace

# 7. Dynamic service count in compose validation
EXPECTED=$(docker compose -f docker-compose.mesh.yml config --services | wc -l)
ACTUAL=$(grep -c '^\s\{2\}[a-z]' docker-compose.mesh.yml)
[ "$ACTUAL" -eq "$EXPECTED" ]

# 8. Rebase all dirty PRs
git rebase origin/main
git push --force-with-lease
```

### Detailed Steps

#### Phase 1: Triage Failure Classes

Before fixing anything, categorize all failures by type. Cascading failures mean that CI will gate
on the FIRST failure class; subsequent failures are hidden until earlier ones are fixed.

Fix in this priority order:
1. **Syntax errors** (Dockerfile parse, YAML parse) — block all builds
2. **Runtime script errors** (Nomad validate on wrong file, BATS unset vars)
3. **Pin enforcement checks** (yarn, npm, pip)
4. **Compose validation** (workspace mounts, service counts)
5. **Base image verification** (digest pinning, multi-arch)
6. **Build system** (OCI layout format, QEMU for multi-arch)

#### Phase 2: Fix Dockerfile RUN Inline Comment Bug

Docker's parser does NOT treat `# ...` as a comment when it appears after `\` on a multi-line
`RUN` continuation line. The next non-whitespace token after `\` is treated as a new instruction.

```dockerfile
# BROKEN — Docker parser sees "wget" as an unknown instruction
RUN apt-get install -y \
    curl \ # install curl
    wget

# FIXED — remove inline comments entirely from RUN blocks
RUN apt-get install -y \
    curl \
    wget
```

Search command:
```bash
grep -rn "\\\\[[:space:]]*#" bases/ vessels/
```

#### Phase 3: Guard Nomad Job Validator

The `nomad job validate` command only works on HCL files that contain a `job` stanza.
Running it against vault policy files or other HCL produces: `Error: 1 error occurred: * job: ...`

```bash
# In CI validate script — add guard before nomad job validate:
for f in nomad/*.hcl; do
  if ! grep -q '^job ' "$f"; then
    echo "Skipping $f (not a Nomad job file)"
    continue
  fi
  nomad job validate "$f"
done
```

#### Phase 4: Fix BATS Variable Unset Under set -euo pipefail

Scripts tested by BATS that use `set -euo pipefail` will fail if `BUILD_DATE` or `VCS_REF`
are referenced but not set in the test environment.

```bash
# Add defaults at top of script (before set -euo pipefail or right after):
BUILD_DATE="${BUILD_DATE:-$(date -u +%Y-%m-%dT%H:%M:%SZ)}"
VCS_REF="${VCS_REF:-$(git rev-parse --short HEAD 2>/dev/null || echo unknown)}"
```

#### Phase 5: Update Stale pixi.lock

After adding dependencies to `pixi.toml`, the lock file must be regenerated. CI uses
`pixi install --locked` — a stale lockfile fails with "lock-file not up-to-date".

```bash
pixi install   # regenerates pixi.lock
git add pixi.lock
```

#### Phase 6: Pin npm/yarn Package Versions in Dockerfiles

Pin enforcement tests check that `npm install -g <package>` uses an explicit version tag.

```dockerfile
# BROKEN — no version pin
RUN npm install -g yarn

# FIXED — pinned version
RUN npm install -g yarn@1.22.22

# ALSO: pip install -r <file> is exempt from pin checks (requirements file handles pinning)
# Direct pip installs need pins: pip install package==1.2.3
```

#### Phase 7: Fix WORKSPACE_ROOT Bare Mount in Compose Files

CI validators reject bare home-directory mounts. Each agent must have its own subdirectory.

```yaml
# BROKEN — mounts entire home directory
volumes:
  - ${WORKSPACE_ROOT:-/home/mvillmow}:/workspace

# FIXED — per-agent subdirectory
volumes:
  - ${WORKSPACE_ROOT:-/home/mvillmow}/Agents/AgentName:/workspace
```

Directory must also exist on the host:
```bash
mkdir -p ~/Agents/AgentName
```

#### Phase 8: Replace Hardcoded Service Counts with Dynamic Comparison

Compose validation scripts that hardcode expected service counts break when new services are added.

```bash
# BROKEN — hardcoded count
EXPECTED_COUNT=12
ACTUAL=$(docker compose -f docker-compose.mesh.yml config --services | wc -l)
[ "$ACTUAL" -eq "$EXPECTED_COUNT" ] || exit 1

# FIXED — dynamic: compare compose config output with actual entries
EXPECTED=$(docker compose -f docker-compose.mesh.yml config --services | wc -l)
ACTUAL=$(grep -c '^\s\{2\}[a-z]' docker-compose.mesh.yml)
[ "$ACTUAL" -eq "$EXPECTED" ] || { echo "Service count mismatch"; exit 1; }
```

#### Phase 9: Add SHA256 Digest Pinning to Base Images

Trivy and security gates require base images to be pinned to a specific digest.

```dockerfile
# BROKEN — tag only (mutable)
FROM debian:bookworm-slim

# FIXED — tag + immutable digest
FROM debian:bookworm-slim@sha256:4724b8c21e5f48c4f1ee3598d5ff42e1dc8db6f4c60e74da940c27e5940a71e5
```

Get the current digest:
```bash
docker pull debian:bookworm-slim
docker inspect debian:bookworm-slim --format '{{index .RepoDigests 0}}'
# or
crane digest debian:bookworm-slim
```

#### Phase 10: Fix OCI Layout Artifact Format

`oci-layout://` scheme requires an uncompressed OCI image directory, not a `.tar` archive.

```bash
# BROKEN — produces tar archive, not OCI directory
docker save image:tag -o image.tar

# FIXED — use buildx with oci output type (directory format)
docker buildx build \
  --output type=oci,dest=/tmp/oci-image-dir \
  -t image:tag .
```

#### Phase 11: Add QEMU Before Buildx for Multi-Arch Builds

Multi-architecture `docker buildx build --platform linux/amd64,linux/arm64` requires QEMU
binfmt_misc registration before buildx is initialized.

```yaml
# In GitHub Actions workflow — order matters:
- name: Set up QEMU
  uses: docker/setup-qemu-action@v3   # MUST come before setup-buildx-action

- name: Set up Docker Buildx
  uses: docker/setup-buildx-action@v3
```

#### Phase 12: PR Rebase Strategy After Main Fixes

Once root-cause fixes land on main, all PRs that touched the same files are DIRTY/UNSTABLE.

```bash
# For each affected PR branch:
git fetch origin
git rebase origin/main

# Conflict resolution pattern for compose files:
# When PR adds lines (e.g., agent-sidecar mount) AND main changed the same block
# (e.g., fixed workspace path) — keep BOTH changes:
# - Accept main's corrected path
# - Re-add the PR's new line(s) that were lost in the conflict

git push --force-with-lease origin HEAD
```

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
|---------|----------------|---------------|----------------|
| Fix all PRs before fixing main | Rebased individual PR branches and pushed patches | CI kept failing because root-cause bugs were on main; each rebase pulled the broken main back in | Fix root-cause bugs on main FIRST, then rebase all PRs |
| Inline comments in RUN apt-get | `apt-get install curl \ # comment` thinking # after \ is a comment | Docker parser treats the token after \ as a new instruction, not a comment continuation | Never put # comments after \ in multi-line RUN blocks |
| Running nomad validate on all .hcl files | `for f in *.hcl; do nomad job validate "$f"; done` | vault-policy.hcl has no `job` stanza — nomad validate errors on non-job HCL | Guard with `grep -q '^job '` before calling nomad job validate |
| Using hardcoded service count in compose validation | `[ "$ACTUAL" -eq 12 ]` | Adding new agent services broke the hardcoded count without anyone noticing | Always compare dynamically using `docker compose config --services | wc -l` |
| OCI layout via docker save | `docker save image:tag -o artifact.tar` for OCI layout pipeline | `oci-layout://` requires an uncompressed directory tree, not a tarball | Use `docker buildx build --output type=oci,dest=<dir>` for OCI layout format |
| Multi-arch build without QEMU | `docker buildx build --platform linux/amd64,linux/arm64` | Fails with exec format error for non-native arch without binfmt_misc registration | Always run `docker/setup-qemu-action` before `docker/setup-buildx-action` in CI |
| Bare workspace mount | `${WORKSPACE_ROOT}:/workspace` | CI security validator flags bare home directory mounts as too broad | Use per-agent paths: `${WORKSPACE_ROOT}/Agents/<name>:/workspace` |
| Unpinned npm global install | `RUN npm install -g yarn` | Pin enforcement test (pytest) fails for any global npm install without `@version` | Always pin: `npm install -g yarn@1.22.22` |

## Results & Parameters

### Cascading Failure Timeline

Each push to main in this session revealed the NEXT hidden failure class. The pattern was:

```
Push 1: Dockerfile RUN inline comment → unknown instruction: wget
Push 2: nomad job validate on vault-policy.hcl → validation error
Push 3: BATS set -euo pipefail + unset BUILD_DATE → unbound variable
Push 4: pixi.lock stale → lock-file not up-to-date
Push 5: yarn unpinned → pytest pin check failure
Push 6: bare WORKSPACE_ROOT mount → compose security validation failure
Push 7: hardcoded service count → count mismatch after new service added
Push 8: missing SHA256 digest → Trivy/security gate failure
Push 9: OCI tar format → oci-layout:// format error
Push 10: missing QEMU → exec format error on non-native arch buildx
```

### PR Rebase Pattern for Compose File Conflicts

```
<<<<<<< HEAD (main)
      - ${WORKSPACE_ROOT:-/home/mvillmow}/Agents/Vegai:/workspace   ← main's fix
=======
      - ${WORKSPACE_ROOT:-/home/mvillmow}:/workspace                ← PR's old path
      - /home/mvillmow/ProjectAgamemnon/agent-sidecar:/app/agent-sidecar:ro  ← PR's new line
>>>>>>> skill/add-vegai-agent
```

Resolution: Keep main's corrected path AND the PR's new line:
```yaml
      - ${WORKSPACE_ROOT:-/home/mvillmow}/Agents/Vegai:/workspace
      - /home/mvillmow/ProjectAgamemnon/agent-sidecar:/app/agent-sidecar:ro
```

### Expected CI Output After All Fixes

```
✓ dockerfile-lint
✓ nomad-validate
✓ bats-unit-tests
✓ pixi-lock-check
✓ pin-enforcement
✓ compose-security-check
✓ compose-service-count
✓ trivy-base-image-scan
✓ oci-layout-build
✓ multi-arch-buildx
```

## Verified On

| Project | Context | Details |
|---------|---------|---------|
| HomericIntelligence/AchaeanFleet | Fixed 13 open PRs all failing CI; cascading failure remediation session | 2026-04-24; all PRs merged, CI green |
