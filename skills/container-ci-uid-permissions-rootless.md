---
name: container-ci-uid-permissions-rootless
description: "Use when: (1) a justfile recipe fails writing to build/ or dist/ because rootless Podman left those directories owned by a subuid-mapped UID the host user cannot write, (2) fixing rootless Podman CI failures involving Dockerfile ARG scoping across FROM boundaries, workspace UID mapping, or compose provider compatibility, (3) implementing multi-stage Docker builds, multi-arch OCI images, or integrating pixi-volume isolation and GHA cache extraction into container workflows, (4) cleaning up CI workflows referencing non-existent test directories with dead Docker steps."
category: ci-cd
date: 2026-07-18
version: "1.1.0"
user-invocable: false
history: container-ci-uid-permissions-rootless.history
tags: [podman, rootless, subuid, uid-mapping, justfile, permissions, build-dir, dist, docker, multistage, oci, multi-arch, pixi, gha-cache, dockerfile-arg, compose, dead-step-cleanup, container-ci, uv, uv-sync, uv-venv, bind-mount, UV_PYTHON_INSTALL_DIR, UV_PROJECT_ENVIRONMENT, astral-uv-image]
---

# Container CI UID Permissions and Rootless Podman Patterns

## Overview

| Field | Value |
|-------|-------|
| **Date** | 2026-07-18 |
| **Objective** | One canonical reference for container-level CI failures involving rootless Podman UID/GID mapping, subuid namespacing, host/container `build/`-`dist/` write boundaries, multi-stage Dockerfile patterns, multi-arch OCI builds, pixi-volume isolation, GHA cache extraction, dead Docker CI step cleanup, and uv-in-container gotchas (uv-managed CPython UID traversal, compose bind-mount masking the venv, podman `COPY --from` of the astral uv image) surfaced migrating C++ repos pixi -> uv |
| **Outcome** | Successful — consolidates 5 verified skills; each specific case (rootless build-dir permissions, ARG scoping, multistage size reduction, dead-step cleanup) retained as a concrete example. v1.1.0 adds three uv-in-container gotchas reproduced via real `podman build` across Charybdis/Keystone/Scylla pixi -> uv migrations |
| **Verification** | verified-ci — all absorbed fixes merged with green CI across ProjectOdyssey, ProjectScylla, and AchaeanFleet; the uv-container gotchas were reproduced via real `podman build` across the Charybdis/Keystone/Scylla pixi -> uv migrations |

## When to Use

- A `just` recipe fails with `mkdir: Permission denied` or `PermissionError: [Errno 13]`
  when writing into `build/` or `dist/` after another recipe ran in a rootless Podman container
- `ls -ln build/` shows files owned by a very high UID (e.g. `524288`, `100000+`) — a subuid
  mapping, not your host UID — and the host user cannot write or `chmod` them
- A CI runner fails with `pixi: not found` because a recipe that needs the pixi environment ran
  host-side instead of through the container `_run` wrapper
- Container builds fail with `can't find uid for user :` or empty `${VAR}` in `COPY --chown`
  (Dockerfile `ARG` not re-declared across `FROM` boundaries)
- `Permission denied` creating files inside a bind-mounted workspace in CI containers
- `podman compose` delegates to the docker-compose CLI plugin and Podman-specific compose
  options (`userns_mode`, etc.) are silently ignored
- You are writing or refactoring a multi-stage Dockerfile, or want to shrink a production image
  by separating build-time from runtime dependencies
- You are chaining multi-arch OCI builds in GitHub Actions, extracting a GHA-cached image tar for
  local repro, or integrating pixi-volume isolation into a container workflow
- A CI workflow references a non-existent test directory (dead Docker step) and you need to
  decide whether to implement the tests or remove the step
- A Dockerfile removes system `python3` and runs `uv sync` (so uv downloads its OWN CPython), then
  switches to a non-root `USER` in the same stage, and the next `conan`/`cmake` call dies with
  `crun: executable file 'conan' not found` / `Permission denied` (exit 126/127) — the uv-managed
  interpreter landed in root's private `/root/.local/share/uv` (mode 0700) the non-root user cannot
  traverse
- A compose `dev` service bind-mounts the host repo over the same path where `uv sync` created the
  venv (default `/workspace/.venv`), and tools installed into that venv vanish at runtime —
  `compose exec dev conan …` / `cmake` fail `not found in $PATH` (exit 127) because the bind-mount
  MASKS the image-baked venv
- A `COPY --from=ghcr.io/astral-sh/uv:<tag>@<digest>` (tag AND digest together) is REJECTED by
  podman/buildah with `no stage or image found with that name`, or a wrong uv-image digest gives
  `reading manifest … manifest unknown`

## Why Rootless Podman UID Mismatches Happen

Rootless Podman maps UIDs through `/etc/subuid`:

- Container UID 0 (root) → the host user (e.g. UID 1001)
- Container UID 1001 → a host subuid far outside the normal range (e.g. 101001, 524288)

So a bind-mounted host file (owned by host UID 1001) appears as **root-owned** inside the
container, and a file written from inside the container as the app user lands on the host owned by
a **subuid the host user cannot write or even `chmod`** (`chmod` on a file you do not own is
`EPERM`, full stop). Any host-side recipe that writes into a directory a prior in-container recipe
populated will hit `Permission denied`. This bug class recurred four times in one packaging
session alone.

## Verified Workflow

### Quick Reference

| Issue | Root Cause | Fix |
| ----- | ---------- | --- |
| `mkdir`/`PermissionError` writing `build/`-`dist/` host-side | Prior in-container recipe owns the tree (subuid) | Wrap the recipe in the `_run` container wrapper |
| `pixi: not found` on CI runner | Recipe ran host-side; runner has no pixi | Wrap in `_run` so it runs in-container where pixi exists |
| Host creates `dist/`, in-container recipe can't write | Host-owned dir, container is subuid-mapped | `chmod 777 dist` on the owning side BEFORE the other side writes |
| `chmod -R o+rX dist` → `EPERM` | `-R` walks foreign-owned sibling files | Narrow to a glob of only this recipe's own artifacts |
| Stale `build/` from a prior UID mapping | Host can't write the dir's contents | `mv build build.stale.$(date +%s)` then recreate (mv needs write on PARENT only) |
| `can't find uid for user :` | Docker `ARG` doesn't persist across `FROM` | Re-declare `ARG` in every stage that uses it |
| `Permission denied` on workspace files in CI | Rootless Podman UID namespace mapping | `chmod -R a+rwX .` on host before container use (CI runners are ephemeral) |
| `docker-compose` ignores `userns_mode` | docker-compose CLI plugin, not Podman compose | Don't use Podman-specific compose extensions |
| Host-created build dirs non-writable in container | mkdir ran on host, not in container | Remove host-side mkdir; inner recipe `mkdir -p` inside the container |
| Justfile build mode always "debug" | `${1:-debug}` is empty in justfile bash | Use `{{mode}}` template substitution |
| SBOM scan auth failure to GHCR | Syft can't inherit Podman login | Export image to tarball (`podman save`), scan locally |
| Production image bloated with build tools | gcc/g++/make in runtime image | Multi-stage build: copy artifacts from builder, drop build tools |
| `type=docker` for multi-arch build | docker output is single-platform | Use `type=oci,dest=<dir>` (no `.tar`) for multi-arch OCI layout |
| CI step references non-existent `tests/docker/` | Dead step never ran meaningful tests | Remove the dead step, document the decision in an ADR |
| `conan`/`cmake` `not found` / `Permission denied` (126/127) after non-root `USER` switch | uv-managed CPython landed in root's `/root/.local/share/uv` (0700); non-root user can't traverse `/root` | `ENV UV_PYTHON_INSTALL_DIR=/opt/uv-python` (outside `/root`) + `chmod -R a+rX /opt/uv-python /opt/venv`; or use a proper multi-stage build |
| `conan`/`cmake` `not found in $PATH` (127) via `compose exec dev` | compose bind-mount `.:/workspace:Z` MASKS the venv baked at `/workspace/.venv` | `ENV UV_PROJECT_ENVIRONMENT=/opt/venv` (venv outside the mount) + `ENV PATH="/opt/venv/bin:$PATH"` |
| `COPY --from=ghcr.io/astral-sh/uv:<tag>@<digest>` → `no stage or image found with that name` | podman/buildah rejects tag-AND-digest as a `COPY --from` reference | Alias it as a named stage: `FROM ghcr.io/astral-sh/uv:<tag>@<digest> AS uv` then `COPY --from=uv /uv /uvx /usr/local/bin/` |

```bash
# FIX A — recipe must run in the container: wrap it in the _run wrapper
# Before (runs host-side, hits Permission denied + 'pixi: not found' on CI):
build-recipe:
    pixi exec --spec rattler-build -- rattler-build build --recipe conda.recipe/recipe.yaml
# After (runs inside the container where pixi exists and UIDs are consistent):
build-recipe:
    @just _run "pixi exec --spec rattler-build -- rattler-build build --recipe conda.recipe/recipe.yaml"

# FIX B — host creates a dir an in-container recipe will write into: chmod 777 it first
mkdir -p dist
chmod 777 dist          # on the side that OWNS the dir, BEFORE the other side writes
just wheel              # in-container recipe can now write into dist/

# FIX C — an in-container recipe must chmod only the files IT created (never -R over the tree)
# Before (fails — recurses over host-owned siblings the recipe does not own):
chmod -R o+rX dist
# After (narrow to exactly the artifacts this recipe produced):
chmod o+rX dist/projectodyssey-*.whl

# FIX D — reclaim a stale build dir from a prior run with a different UID mapping
mv build build.stale.$(date +%s)   # mv needs write on the PARENT only, not the contents
mkdir build                         # recreate fresh, host-owned
```

### Detailed Steps

#### 1. Rootless Podman host/container `build/`-`dist/` permission mismatches

Diagnose ownership first: `ls -ln build/`. A UID like `524288` or `100000+` is a Podman subuid
mapping the host user cannot write.

- **Decide where the recipe belongs.** Needs pixi / the toolchain, or writes into a tree the
  container also writes → wrap in `_run` (in-container). This also fixes `pixi: not found` because
  the CI runner host has no pixi but the container does. Genuinely host-only recipes must never
  write into a container-shared directory.
- **Fix A — wrap host-only recipes in `_run`.** A `build-recipe` (rattler-build) or `wheel` that
  needs pixi and writes artifacts must run in-container.
- **Fix B — `chmod 777` a shared dir on the owning side, before the other side writes.** When a
  host step creates `dist/` then hands off to an in-container `just wheel`, the host must
  `chmod 777 dist` immediately after `mkdir dist`.
- **Fix C — narrow `chmod` to only the files the recipe created.** `chmod -R o+rX dist` fails with
  `EPERM` because the recursion walks foreign-owned sibling files. Replace the `-R` walk with an
  explicit glob (`chmod o+rX dist/projectodyssey-*.whl`).
- **Fix D — reclaim a stale build dir via `mv`, not `chmod`.** A leftover `build/` from a prior run
  with a different UID mapping cannot be written or `chmod`'d, but the host **can `mv` the whole
  directory aside** because moving a directory needs write on the *parent* only.

#### 2. Dockerfile ARG scoping across FROM boundaries

`ARG` declarations are scoped to a single build stage and do NOT persist across `FROM`. Symptom:
`COPY --chown=${USER_NAME}:${USER_NAME}` fails with `can't find uid for user :` (empty ARG).

```dockerfile
FROM ubuntu:24.04 AS base
ARG USER_NAME=dev

FROM base AS development
ARG USER_NAME=dev          # MUST re-declare — without this, USER_NAME is empty
USER ${USER_NAME}
COPY --chown=${USER_NAME}:${USER_NAME} . .

FROM development AS ci      # inherits USER_NAME from development

FROM base AS production
ARG USER_NAME=dev          # from base again → MUST re-declare
COPY --from=development /home/${USER_NAME}/.pixi /home/${USER_NAME}/.pixi
```

Empty ARGs cause **silent** failures, not build errors — always audit `ARG` across ALL stages.
Also: `ARG` must appear BEFORE the `RUN` that consumes it, or it is empty in that layer.

#### 3. Rootless Podman workspace permissions and container UID crash fixes

Bind-mounted host files (owned by host UID 1001) appear as container-root, so the container app
user (UID 1001) cannot write them. Make the workspace world-writable on the host before the
container uses it (safe — CI runners are ephemeral single-use VMs):

```yaml
- name: Fix workspace permissions
  shell: bash
  run: chmod -R a+rwX . || true
```

For containers that crash because a user's home dir or pixi dirs are over-restricted, do NOT
over-restrict them in the Dockerfile, and redirect `HOME` at startup when the mounted home is not
writable:

```dockerfile
# Make home dir traversable by other UIDs; do NOT chmod -R 700 the pixi dirs
RUN chmod 755 /home/${USER_NAME}
# REMOVE: RUN chmod -R 700 $PIXI_HOME $PIXI_CACHE_DIR   # breaks under UID remapping
```

```bash
# entrypoint.sh — fall back to a writable HOME if the mounted one isn't writable
if ! mkdir -p "${HOME}/.cache" 2>/dev/null; then
    export HOME="/tmp/home-$(id -u)"
    mkdir -p "${HOME}"
    export PIXI_HOME="${HOME}/.pixi"
fi
exec "$@"
```

Do NOT try `userns_mode: keep-id` in `docker-compose.yml`, `PODMAN_USERNS=keep-id`, or `chown`
inside the container — the docker-compose CLI plugin ignores Podman extensions, the env var is
unreliable through the Docker API, and in-container `chown` to non-root involves subuid mapping
complexity. Prefer the simple host-side `chmod`.

#### 4. Justfile parameters, host-vs-container dirs, Podman socket, SBOM

```just
# WRONG — $1 is empty in justfile bash blocks → MODE always "debug"
_build-inner mode="debug":
    #!/usr/bin/env bash
    MODE="${1:-debug}"
# CORRECT — just template substitution
_build-inner mode="debug":
    #!/usr/bin/env bash
    MODE="{{mode}}"
```

- Don't create build output dirs on the host before `podman compose exec`; let the inner build
  script `mkdir -p` inside the container where the user has correct permissions.
- Start the Podman socket on GH Actions (`systemctl --user start podman.socket`; export
  `DOCKER_HOST=unix:///run/user/$(id -u)/podman/podman.sock`); `podman compose` delegates to the
  docker-compose plugin which needs the socket.
- SBOM: export the image to a tarball and scan it locally instead of pulling from GHCR:

```yaml
- run: podman save -o /tmp/image.tar "$REGISTRY/$IMAGE:$TAG"
- uses: anchore/sbom-action@v0
  with: { image: /tmp/image.tar }
```

#### 5. Multi-stage Docker build (image size reduction)

Separate build-time from runtime dependencies to drop build tools from production (verified
246MB / 30% reduction on ProjectScylla: 818MB → 572MB):

```dockerfile
FROM python:3.12-slim AS builder
ENV PIP_NO_CACHE_DIR=1 PIP_DISABLE_PIP_VERSION_CHECK=1
RUN apt-get update && apt-get install -y --no-install-recommends gcc g++ build-essential \
    && rm -rf /var/lib/apt/lists/*
COPY pyproject.toml README.md /opt/app/
COPY src/ /opt/app/src/
RUN pip install --no-cache-dir /opt/app/

FROM python:3.12-slim
# Copy BOTH site-packages AND bin/ — forgetting bin/ breaks CLI entry points
COPY --from=builder /usr/local/lib/python3.12/site-packages /usr/local/lib/python3.12/site-packages
COPY --from=builder /usr/local/bin /usr/local/bin
RUN apt-get update && apt-get install -y --no-install-recommends git ca-certificates \
    && rm -rf /var/lib/apt/lists/*     # runtime deps only, NO build tools
WORKDIR /workspace
CMD ["python", "-m", "app"]
```

Build context in `docker-compose.yml` must include every `COPY` source (use `context: ..` if the
Dockerfile copies from the repo root). Verify build tools are gone:
`docker run --rm app:multi-stage gcc --version  # gcc: not found`.

#### 6. Multi-arch OCI, pixi isolation, GHA cache extraction

```yaml
# Multi-arch: QEMU MUST come before buildx; use type=oci dir (no .tar) for OCI layout
- uses: docker/setup-qemu-action@v3
- uses: docker/setup-buildx-action@v3
- uses: docker/build-push-action@v6
  with:
    platforms: linux/amd64,linux/arm64
    outputs: type=oci,dest=/tmp/base-minimal      # directory, NOT a .tar
- uses: docker/build-push-action@v6
  with:
    build-contexts: base:latest=oci-layout:///tmp/base-minimal
```

```toml
# pixi volume isolation — .pixi/config.toml (commit to repo)
[detached-environments]
detached-environments = true
# Mount only the cache (pixi-cache:/home/dev/.cache/pixi), NOT ~/.pixi (shadows the binary)
```

```bash
# GHA cache extraction for local forensic repro
gh workflow run extract-cached-image.yml --ref <branch>
RUN_ID=$(gh run list --workflow=extract-cached-image.yml --limit=1 --json databaseId --jq '.[0].databaseId')
gh run download "$RUN_ID"
podman load -i container-image-*/dev.tar
podman run --rm -it <loaded-image-tag> bash
```

#### 7. Dead Docker CI step cleanup

When a CI workflow references a non-existent test directory (e.g. `tests/docker/`), decide:
implement the tests (feasible in CI, no secrets, quick) vs. remove the dead step (requires
secrets, heavyweight integration, tracked elsewhere). To remove: read the workflow, confirm the
dir is missing (`ls tests/docker/`), delete only the dead steps, rename the workflow if its name
overpromises, document the decision in an ADR (`docs/dev/adr/<name>.md`), and check README CI
badges that would break.

```yaml
# After: dead pytest step replaced with a tracking comment
# Docker integration tests are deferred — see docs/dev/adr/docker-testing-deferred.md
# Entrypoint script testing is tracked in GitHub issue #1113
```

#### 8. uv-in-container gotchas (pixi -> uv migration)

Migrating C++ repos off pixi onto uv introduces three container-specific traps, all reproduced with
a real `podman build`. The unifying theme: uv's DEFAULT locations (root's private home for the
managed CPython, `/workspace/.venv` for the project venv) collide with rootless-container UID
traversal rules and compose bind-mounts. Redirect both out of those defaults into shared `/opt`
paths.

**Gotcha A — uv-managed CPython in root's home breaks non-root container users.**
When a Dockerfile removes system `python3` and runs `uv sync`, uv downloads its OWN CPython and, by
default, installs it under ROOT's private home `/root/.local/share/uv/…` (dir mode `0700`). If the
stage later switches to a non-root `USER` (single-stage, or a same-stage switch), that user CANNOT
traverse `/root` to reach the interpreter, so the next `conan`/`cmake` call dies with
`crun: executable file 'conan' not found` / `Permission denied` (exit 126/127). Move the managed
interpreter to a shared `/opt` path OUTSIDE `/root` and make it traversable:

```dockerfile
# Put uv's managed CPython outside /root and make it non-root-readable
ENV UV_PYTHON_INSTALL_DIR=/opt/uv-python
RUN uv sync --frozen \
    && chmod -R a+rX /opt/uv-python /opt/venv    # traversable by the non-root USER
USER app     # single-stage / same-stage switch is exactly the case that breaks by default
```

NOTE: a proper MULTI-STAGE Dockerfile is IMMUNE — run the uv build as root in a `builder` stage, and
in the final stage only `COPY --from=builder` the built artifact plus switch `USER` for runtime; the
non-root user never touches uv. The bug is specific to the single-stage-with-early-USER-switch shape.
(Repro: Charybdis pixi -> uv migration.)

**Gotcha B — a compose bind-mount MASKS the uv venv.**
If `uv sync` creates the venv at the default `/workspace/.venv` and a docker/podman-compose `dev`
service bind-mounts the host repo over the same path (`.:/workspace:Z`), the image-baked venv is
HIDDEN by the mount at runtime, so tools installed into it vanish and `conan`/`cmake` (invoked by
bare name inside the container via `compose exec`) fail `not found in $PATH` (exit 127). Put the
venv OUTSIDE the bind-mounted path so the mount cannot shadow it, and add its `bin/` to `PATH` for
bare-name resolution:

```dockerfile
# venv lives outside /workspace so the compose bind-mount can't mask it
ENV UV_PROJECT_ENVIRONMENT=/opt/venv
ENV PATH="/opt/venv/bin:$PATH"
RUN uv sync --frozen
```

```yaml
# compose dev service: the mount over /workspace no longer hides the venv at /opt/venv
services:
  dev:
    volumes:
      - .:/workspace:Z
# make deps -> `podman-compose exec dev conan …` now resolves conan from /opt/venv/bin
```

(Repro: Keystone pixi -> uv migration — `make deps` execs `podman-compose exec dev conan …`;
validated by reproducing the bind-mount-over-`/workspace` scenario, after which `make deps`
succeeds.)

**Gotcha C — podman `COPY --from` of the astral uv image rejects tag-AND-digest.**
`COPY --from=ghcr.io/astral-sh/uv:<tag>@<digest>` (tag AND digest together) is REJECTED by
podman/buildah with `no stage or image found with that name`. Alias the image as a named build
stage first, then `COPY --from` the stage name. Also VERIFY the digest resolves via the ghcr
manifest API BEFORE using it — a wrong digest gives `reading manifest … manifest unknown`:

```dockerfile
# WRONG — podman/buildah: "no stage or image found with that name"
COPY --from=ghcr.io/astral-sh/uv:0.11.21@sha256:ff07b86af50d4d9391d9daf4ff89ce427bc544f9aae87057e69a1cc0aa369946 /uv /uvx /usr/local/bin/

# CORRECT — alias as a named stage, then COPY --from the stage
FROM ghcr.io/astral-sh/uv:0.11.21@sha256:ff07b86af50d4d9391d9daf4ff89ce427bc544f9aae87057e69a1cc0aa369946 AS uv
# … your build stages …
COPY --from=uv /uv /uvx /usr/local/bin/
```

```bash
# Verify the digest resolves BEFORE using it (a wrong digest → "manifest unknown")
# ff07b86… is the real 0.11.21 digest; Scylla first hit sha256:0b6dc79… which did NOT exist.
curl -sSL -H "Authorization: Bearer $(curl -sSL \
  'https://ghcr.io/token?scope=repository:astral-sh/uv:pull' | jq -r .token)" \
  -H 'Accept: application/vnd.oci.image.index.v1+json' \
  https://ghcr.io/v2/astral-sh/uv/manifests/sha256:ff07b86af50d4d9391d9daf4ff89ce427bc544f9aae87057e69a1cc0aa369946
```

(Repro: Scylla pixi -> uv migration.)

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
|---------|----------------|---------------|----------------|
| `just build-recipe` / `just wheel` run host-side | Ran pixi/rattler-build recipes directly on the host | Host user cannot write `build/` once an in-container recipe owns it (subuid); also `pixi: not found` on CI runners with no host pixi | Wrap recipes that need pixi or write build artifacts in the `_run` container wrapper |
| Host creates `dist/`, in-container `just wheel` writes into it | `mkdir dist` host-side, then invoked in-container recipe | Host-created `dist/` is host-owned; the subuid-mapped container user cannot write into it | After `mkdir dist`, `chmod 777 dist` on the host side BEFORE the in-container recipe writes |
| `chmod -R o+rX dist` inside the in-container recipe | Recursive chmod to make output world-readable | `-R` recursed onto host-owned siblings the recipe did not own → `chmod` on a non-owned file is `EPERM` | Never `chmod -R` over a tree with foreign-owned siblings; narrow to the specific files the recipe created |
| `chmod`/`chown` a foreign-owned stale `build/` | Tried to fix permissions on a dir from a prior UID mapping | `chmod` on a file you do not own is always `EPERM` | `mv` the directory aside from a writable parent (mv needs write on the PARENT only), then recreate |
| `userns_mode: keep-id` in docker-compose.yml | Added Podman user-namespace mapping to the compose file | `podman compose` on GH Actions delegates to the docker-compose CLI plugin, which ignores Podman extensions | Check the actual compose provider before using Podman-specific features |
| `PODMAN_USERNS=keep-id` env var | Set env var to apply keep-id to all containers | Unreliable when containers are created through the Docker API by docker-compose, not the Podman CLI | Podman CLI env vars may not be honored when docker-compose creates containers via the API |
| `chown` inside container as root | `podman compose exec -u 0` to chown workspace | Overcomplicated; chown to a non-root UID involves subuid mapping complexities | Prefer simple host-side `chmod` over in-container ownership changes |
| Missing Dockerfile `ARG` re-declaration | `USER_NAME` declared only in the `base` stage | development/production stages silently used an empty string → `can't find uid for user :` | Re-declare `ARG` in every stage; empty ARGs are silent failures, not errors |
| `mkdir -p <out>` on host before `podman compose exec` | Created the output dir on the host runner | Container process (different UID, rootless remapping) cannot write a host-created dir | Create output dirs inside the container exec command, not on the host |
| `MODE="${1:-debug}"` in a justfile recipe | Read the mode arg as a bash positional | justfile passes args via `{{param}}` template substitution, not `$1` | Use `{{mode}}` — `$1` is always empty in justfile bash blocks |
| `chmod -R 700 $PIXI_HOME $PIXI_CACHE_DIR` in Dockerfile | Restricted pixi dirs for "security" | Breaks pixi when the container runs as a different UID under rootless remapping | Do not over-restrict pixi/home dirs; `chmod 755` the home dir and leave pixi dirs accessible |
| `workspace-pixi` named volume at `.pixi/` | Shadowed host `.pixi/` with a Docker volume | Shadows the pixi binary itself when `~/.pixi/bin` is inside the mount | Use `detached-environments = true` and mount only the cache, not the whole `.pixi/` |
| `type=docker` / `type=oci,dest=foo.tar` for multi-arch OCI | Single-platform output / `.tar` extension on OCI dest | `type=docker` is single-platform; `oci-layout://` requires a directory, not a tarball | Use `type=oci,dest=<dir>` (no `.tar`) and run `setup-qemu-action` before buildx |
| `RUN pre-commit install` in the Dockerfile | Installed hooks at image build time | The workspace bind-mount is not active at build time; hooks get shadowed at runtime | Install pre-commit hooks in `entrypoint.sh` at container startup, not in the Dockerfile |
| Assuming new test failures were regressions | 4 test groups failed after the container fixes | Those tests were previously skipped because the container build failed; fixing infra exposed pre-existing bugs | When fixing infrastructure, expect to uncover pre-existing failures hidden by earlier-stage breaks |
| Implementing heavyweight Docker integration tests in PR CI | Considered Option A (write the missing tests) for a dead `tests/docker/` step | The tests needed API keys not available in CI and were heavyweight for PR CI | Remove the dead step + document in an ADR (Option B) when tests require secrets or are heavyweight |
| Left uv-managed CPython in root's default home, then switched to non-root `USER` | `uv sync` with no `UV_PYTHON_INSTALL_DIR`, then `USER app` in the same stage | uv put its CPython in `/root/.local/share/uv` (mode 0700); the non-root user can't traverse `/root`, so `conan`/`cmake` die 126/127 (`not found` / `Permission denied`) | Set `UV_PYTHON_INSTALL_DIR=/opt/uv-python` (outside `/root`) + `chmod -R a+rX` it; or use a proper multi-stage build where the non-root user never touches uv (Charybdis) |
| Left the uv venv at default `/workspace/.venv` under a compose bind-mount | `uv sync` created `/workspace/.venv`; compose `dev` bind-mounts `.:/workspace:Z` over it | The bind-mount MASKS the image-baked venv at runtime; `compose exec dev conan …` fails `not found in $PATH` (127) | Set `UV_PROJECT_ENVIRONMENT=/opt/venv` so the venv lives outside the mount + `ENV PATH="/opt/venv/bin:$PATH"` for bare-name resolution (Keystone) |
| `COPY --from=ghcr.io/astral-sh/uv:<tag>@<digest>` directly | Referenced the astral uv image by tag AND digest in a single `COPY --from` | podman/buildah rejects it: `no stage or image found with that name`; a wrong digest also gives `manifest unknown` | Alias as a named stage `FROM …@<digest> AS uv` then `COPY --from=uv /uv /uvx /usr/local/bin/`, and verify the digest via the ghcr manifest API first (Scylla hit a nonexistent `sha256:0b6dc79…`; `ff07b86…` is the real 0.11.21 digest) |

## Results & Parameters

### Decision rule: host-side vs `_run`

```text
Needs pixi / the toolchain?                       → _run (in-container)
Writes into build/ or dist/?                      → _run, OR chmod 777 the dir first
Pure host shell (git, gh, moves outside build/)?  → host-side is fine
```

### chmod / mv ownership rule

```text
chmod on a file you OWN          → OK
chmod on a file you do NOT own   → EPERM (always — even +r, even same group)
mv a directory                   → needs write on the PARENT only, not the dir's contents
```

To make foreign-owned artifacts readable, run `chmod` on the side that **created** them; to get
rid of a foreign-owned directory, `mv` it aside from a writable parent.

### Rootless Podman CI configuration (verified)

```yaml
runner: ubuntu-latest (Ubuntu 24.04, GLIBC 2.39)
podman: rootless (default on ubuntu-latest)
compose_provider: /usr/libexec/docker/cli-plugins/docker-compose
container_user: dev (UID 1001)
runner_user: runner (UID 1001)
# Podman build for GHCR push:
#   podman build --format docker -f Containerfile --target <target> -t <tag> .
# GHA cache (NOT Docker buildx GHA cache):
#   actions/cache on ~/.local/share/containers keyed by hashFiles('Dockerfile','pixi.toml','pixi.lock')
```

### Verification commands

```bash
podman info --format '{{.Host.Security.Rootless}}'   # confirm rootless
ls -ln build/                                         # spot subuid-mapped owners (524288, 100000+)
podman compose version                                # see the actual compose provider
docker run --rm app:multi-stage gcc --version         # expect: gcc: not found (build tools dropped)
```

### Multi-stage image size reduction (ProjectScylla #601/#649)

| Version | Size | Reduction |
|---------|------|-----------|
| Original (single-stage) | 818MB | --- |
| Multi-stage | 572MB | **-246MB (-30%)** |

### OCI layout: directory vs tarball

| `dest=` value | Result on disk | `oci-layout://` compatible? |
|---------------|----------------|------------------------------|
| `/tmp/foo.tar` | Single `.tar` archive | No — fails with "not a directory" |
| `/tmp/foo` | OCI layout dir (`index.json`, `blobs/`, `oci-layout`) | Yes |

## Verified On

| Project | Context | Details |
|---------|---------|---------|
| ProjectOdyssey | Issue #5413 packaging verification — rootless Podman host/container `build/`-`dist/` boundary | PRs #5422, #5424, #5425, #5426 — all merged green |
| ProjectOdyssey | Rootless Podman CI: Dockerfile ARG scoping, workspace chmod, justfile `{{mode}}`, SBOM tarball | Fixed all 3 failing CI workflows on main |
| ProjectScylla | Multi-stage Docker build (Issue #601, PR #649); dead Docker CI step cleanup (Issue #1114, PR #1157) | 246MB/30% image reduction; 3185 tests passing |
| AchaeanFleet | Multi-arch OCI, pixi isolation, GHA cache extraction patterns | container build/runtime consolidation |
| ProjectCharybdis | pixi -> uv migration — Gotcha A: uv-managed CPython in root's home breaks non-root container users | Reproduced via `podman build`; fixed with `UV_PYTHON_INSTALL_DIR=/opt/uv-python` + `chmod -R a+rX` |
| ProjectKeystone | pixi -> uv migration — Gotcha B: compose bind-mount over `/workspace` masks the uv venv | Reproduced the bind-mount-over-`/workspace` scenario; `UV_PROJECT_ENVIRONMENT=/opt/venv` + `PATH` fix makes `make deps` (`podman-compose exec dev conan …`) succeed |
| ProjectScylla | pixi -> uv migration — Gotcha C: podman `COPY --from` of the astral uv image (tag+digest) rejected | Alias as a named stage; verify digest via ghcr manifest API (nonexistent `sha256:0b6dc79…` → `manifest unknown`; `ff07b86…` is the real 0.11.21 digest) |
