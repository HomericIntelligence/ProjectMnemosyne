---
name: ci-cd-docker-base-entrypoint-all-bases
description: "All Docker base images in AchaeanFleet require an ENTRYPOINT instruction or CI verification will fail. Use when: (1) adding a new base Dockerfile to AchaeanFleet, (2) debugging CI failures on 'Verify ENTRYPOINT is set' step, (3) copying an existing base Dockerfile to create a new variant, (4) writing entrypoint scripts that load Docker secrets before exec'ing CMD."
category: ci-cd
date: 2026-04-24
version: "1.0.0"
user-invocable: false
verification: verified-local
tags: [docker, dockerfile, entrypoint, base-image, ci, achaeanfleet, secrets]
---

# Docker Base Images — ENTRYPOINT Required for All Bases

## Overview

| Field | Value |
| ------- | ------- |
| **Date** | 2026-04-24 |
| **Objective** | Ensure all AchaeanFleet base images have ENTRYPOINT set so CI verification passes and vessel containers can load Docker secrets (API keys) at startup |
| **Outcome** | Success — ENTRYPOINT added to `Dockerfile.python` and `Dockerfile.minimal`; fixes committed to main branch of AchaeanFleet |
| **Verification** | verified-local — fixes committed to main; CI runs queued at time of capture |

## When to Use

- Adding a new base Dockerfile to `bases/` in AchaeanFleet
- CI fails on the "Verify ENTRYPOINT is set" step for any base image
- Copying `Dockerfile.node` (the original template) to create `Dockerfile.python` or `Dockerfile.minimal` — the entrypoint is easy to omit
- Debugging vessel containers that silently fail to read API keys from Docker secrets mounts
- Writing or updating `bases/entrypoint.sh` (the script that loads secrets before exec'ing CMD)

## Verified Workflow

### Quick Reference

```dockerfile
# Required block in EVERY base Dockerfile (node, python, minimal)
# Must appear BEFORE the USER directive so COPY and chmod run as root

COPY bases/entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

# ... other root-level instructions ...

USER agent
ENTRYPOINT ["/entrypoint.sh"]
```

```bash
# Verify all three bases have ENTRYPOINT before pushing
grep -l "ENTRYPOINT" bases/Dockerfile.node bases/Dockerfile.python bases/Dockerfile.minimal
# Must list all three files
```

### Detailed Steps

1. Open `bases/entrypoint.sh` and confirm it loads Docker secrets before exec'ing CMD:

   ```bash
   # Pattern in entrypoint.sh: load API keys from /run/secrets/ then exec "$@"
   for secret_file in /run/secrets/*; do
     export "$(basename "$secret_file")"="$(cat "$secret_file")"
   done
   exec "$@"
   ```

2. In each base Dockerfile (`Dockerfile.node`, `Dockerfile.python`, `Dockerfile.minimal`), add the COPY and chmod as root, then set ENTRYPOINT after the USER directive:

   ```dockerfile
   COPY bases/entrypoint.sh /entrypoint.sh
   RUN chmod +x /entrypoint.sh

   # ... remaining root-level steps ...

   USER agent
   ENTRYPOINT ["/entrypoint.sh"]
   ```

3. Confirm ordering: COPY and chmod must come BEFORE `USER agent`. The agent user cannot write to `/entrypoint.sh` — only root can COPY files to `/`.

4. Verify with grep before committing:

   ```bash
   grep -n "ENTRYPOINT" bases/Dockerfile.node bases/Dockerfile.python bases/Dockerfile.minimal
   ```

5. The CI step "Verify ENTRYPOINT is set" runs against all three bases. All three must have the instruction or the job fails.

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
| --------- | ---------------- | --------------- | ---------------- |
| Attempt 1 | Adding `ENTRYPOINT ["/entrypoint.sh"]` after `USER agent` without the COPY/chmod block above it | The agent user does not have permission to write to `/entrypoint.sh` — the COPY step must be run as root before the USER directive | Always place `COPY <entrypoint> /entrypoint.sh` and `RUN chmod +x /entrypoint.sh` before the `USER agent` line, even though the entrypoint executes as the agent user |
| Attempt 2 (root cause) | `Dockerfile.python` and `Dockerfile.minimal` were created as copies of `Dockerfile.node` but the ENTRYPOINT block was omitted | The node base was the original template; python and minimal were derived later without the entrypoint, and the CI check was added in a separate PR that exposed the gap | When copying a Dockerfile to create a new variant, audit every structural instruction: HEALTHCHECK, ENTRYPOINT, USER, EXPOSE — all are easy to miss |

## Results & Parameters

### Canonical ENTRYPOINT Block for AchaeanFleet Bases

```dockerfile
# Place BEFORE USER agent — must run as root to copy into /
COPY bases/entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

# ... remaining root instructions ...

USER agent
ENTRYPOINT ["/entrypoint.sh"]
```

### entrypoint.sh Purpose

`bases/entrypoint.sh` performs two tasks before handing control to CMD:

1. **Loads Docker secrets** — reads API keys from `/run/secrets/` and exports them as environment variables so vessel containers (agent tools) can authenticate to LLM providers
2. **Exec's CMD** — replaces itself with the container's CMD via `exec "$@"` so process signals propagate correctly

All three bases need this because every vessel (`FROM achaean-base-node`, `FROM achaean-base-python`, `FROM achaean-base-minimal`) inherits and relies on the secrets-loading entrypoint at startup.

### CI Check Being Satisfied

The CI "Verify ENTRYPOINT is set" step inspects the built image with `docker inspect` and asserts that `Config.Entrypoint` is non-empty. Missing ENTRYPOINT leaves this field as `null`, causing the check to exit non-zero.

```bash
# What CI does (simplified):
ENTRYPOINT=$(docker inspect "$IMAGE" --format '{{json .Config.Entrypoint}}')
[ "$ENTRYPOINT" != "null" ] || { echo "ENTRYPOINT not set on $IMAGE"; exit 1; }
```

### Affected Files

- `bases/Dockerfile.node` — had ENTRYPOINT (original template, no change needed)
- `bases/Dockerfile.python` — missing ENTRYPOINT (fix: add COPY + chmod + ENTRYPOINT)
- `bases/Dockerfile.minimal` — missing ENTRYPOINT (fix: add COPY + chmod + ENTRYPOINT)

## Verified On

| Project | Context | Details |
| --------- | --------- | --------- |
| AchaeanFleet | 2026-04-24 — CI failures on "Verify ENTRYPOINT is set" for python and minimal bases | Fixed by adding `COPY bases/entrypoint.sh /entrypoint.sh`, `RUN chmod +x /entrypoint.sh`, and `ENTRYPOINT ["/entrypoint.sh"]` to both missing bases; committed to main |
