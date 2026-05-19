---
name: container-build-and-runtime-patterns
description: "Canonical guide to container build and runtime patterns spanning Docker, Podman, and rootless: multi-stage builds, multi-arch OCI, UID/GID mismatch fixes, layer caching strategies, entrypoint patterns, healthchecks, pixi-volume isolation, GHA cache extraction, Conan-in-Docker chains, dockerfile extras validation. Use when: (1) writing or refactoring a Dockerfile, (2) diagnosing a rootless Podman or UID mismatch crash, (3) extracting / sharing image cache between local and GHA, (4) integrating Conan profiles with a multistage build, (5) container-based E2E test infra."
category: ci-cd
date: 2026-05-18
version: "1.0.0"
user-invocable: false
verification: verified-local
history: container-build-and-runtime-patterns.history
tags: [merged, docker, podman, container, dockerfile, multistage, rootless]
---

# Container Build and Runtime Patterns

## Overview

| Field | Value |
| ------- | ------- |
| **Date** | 2026-05-18 |
| **Objective** | Canonical guide consolidating 41 container/Docker/Podman skills into one reference |
| **Outcome** | Successful — covers multi-stage builds, rootless Podman, layer caching, healthchecks, pixi isolation, GHA cache, Conan chains |

## When to Use

- Writing or refactoring a Dockerfile or Containerfile
- Diagnosing rootless Podman UID/GID permission crashes inside containers
- Chaining multi-arch OCI builds in GitHub Actions
- Extracting a GHA-cached image tar for local forensic reproduction
- Integrating Conan 2 profiles with a Docker multistage C++ build
- Adding healthchecks to distroless or scratch-based images
- Containerizing E2E tests or pixi-based CI pipelines
- Migrating from Docker to Podman (removing `NATIVE=1` escape hatches)
- Debugging Docker Hub rate limit failures in CI
- Setting up pre-commit hooks inside bind-mounted dev containers

## Verified Workflow

### Quick Reference

**Multi-stage build skeleton:**

```dockerfile
FROM python:3.12-slim@sha256:<DIGEST> AS builder
RUN apt-get update && apt-get install -y --no-install-recommends build-essential \
    && rm -rf /var/lib/apt/lists/*
COPY pyproject.toml /app/
RUN pip install --user --no-cache-dir -e /app
COPY . /app

FROM python:3.12-slim@sha256:<DIGEST> AS runtime
COPY --from=builder /root/.local /root/.local
ENV PATH=/root/.local/bin:$PATH
ENTRYPOINT ["python", "-m", "myapp"]
```

**Rootless Podman — UID mismatch fixes:**

```dockerfile
# Make home dir traversable by other UIDs
RUN chmod 755 /home/${USER_NAME}
# Do NOT over-restrict pixi dirs:
# REMOVE: RUN chmod -R 700 $PIXI_HOME $PIXI_CACHE_DIR
```

**entrypoint.sh — redirect HOME if needed:**

```bash
if [ ! -d "${HOME}/.modular" ]; then
    mkdir -p "${HOME}/.modular" 2>/dev/null || {
        export HOME="/tmp/mojo-home-$(id -u)"
        mkdir -p "${HOME}/.modular"
        export PIXI_HOME="${HOME}/.pixi"
    }
fi
exec "$@"
```

**Pre-commit in bind-mounted container — install at startup, not image build:**

```bash
# entrypoint.sh
if [ -d ".git" ] && [ ! -f ".git/hooks/pre-commit" ]; then
    pixi run pre-commit install
fi
```

**Multi-arch OCI layout (QEMU must come first):**

```yaml
- uses: docker/setup-qemu-action@v3
- uses: docker/setup-buildx-action@v3
- name: Build base
  uses: docker/build-push-action@v6
  with:
    platforms: linux/amd64,linux/arm64
    outputs: type=oci,dest=/tmp/base-minimal   # NO .tar — saves as directory
- name: Build downstream
  uses: docker/build-push-action@v6
  with:
    build-contexts: base:latest=oci-layout:///tmp/base-minimal
```

**pixi volume isolation (detached-environments):**

```toml
# .pixi/config.toml — commit to repo
[detached-environments]
detached-environments = true
```

```yaml
# docker-compose.yml — remove workspace-pixi named volume
services:
  dev:
    volumes:
      - .:/workspace:Z
      - pixi-cache:/home/dev/.cache/pixi   # cache only, NOT shadow the binary
volumes:
  pixi-cache:
```

**GHA cache extraction (local forensic repro):**

```bash
gh workflow run extract-cached-image.yml --ref <branch>
RUN_ID=$(gh run list --workflow=extract-cached-image.yml --limit=1 --json databaseId --jq '.[0].databaseId')
gh run download "$RUN_ID"
podman load -i container-image-*/dev.tar
podman run --rm -it <loaded-image-tag> bash
```

**Distroless / scratch healthcheck workaround:**

```yaml
# docker-compose / podman-compose — use string form, NOT array form
healthcheck:
  test: "wget -qO- http://localhost:8080/health 2>/dev/null || exit 1"
  interval: 10s
  timeout: 5s
  retries: 5
  start_period: 30s
```

**ENTRYPOINT block for multi-base images (run as root, switch to user):**

```dockerfile
COPY bases/entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh
# ... remaining root instructions ...
USER agent
ENTRYPOINT ["/entrypoint.sh"]
```

**Dockerfile ARG scoping across multi-stage:**

```dockerfile
FROM ubuntu:24.04 AS base
ARG USER_NAME=dev

FROM base AS development
ARG USER_NAME=dev   # MUST re-declare — ARG does not cross FROM boundaries
USER ${USER_NAME}
```

**Conan 2 profile fix:**

```bash
# Stage 1: use --profile:all= (sets host AND build profile)
conan install . --profile:all=conan/profiles/default --build=missing
# Stage 2: if GCC version mismatch, downgrade compiler.version in profile to match distro default
```

**Docker Hub rate limit — switch to MCR mirror:**

```dockerfile
FROM mcr.microsoft.com/mirror/docker/library/ubuntu:24.04
```

**Container image security patching:**

```dockerfile
FROM python:3.12-slim@sha256:<DIGEST>
RUN apt-get update && apt-get upgrade -y && apt-get install -y --no-install-recommends \
    git ca-certificates \
    && rm -rf /var/lib/apt/lists/*
```

**Podman to Docker migration key differences:**

```bash
# Podman build (must use --format docker for GHCR push)
podman build --format docker -f Containerfile --target <target> -t <tag> .
# Cache: use actions/cache on ~/.local/share/containers, NOT type=gha
# Volume mount: use :Z instead of :delegated
```

**Throttle container-publish with paths-filter:**

```yaml
on:
  schedule:
    - cron: '0 6 * * *'   # 06:00 UTC — off-peak
  workflow_dispatch:
  push:
    paths:
      - 'Dockerfile*'
      - 'docker-compose.yml'
      - '<dep-manifest>'
      - '.github/workflows/container-publish.yml'
    tags:
      - 'v*'
```

**Podman compose clone-aware restart:**

```bash
podman compose down && podman compose up -d
```

**Podman rootless DNS fix:**

```bash
# Ensure aardvark-dns is installed and containers share the same compose network
podman network ls   # verify network exists
podman inspect <container> | jq '.[0].NetworkSettings.Networks'
```

**SBOM image-not-known fix — broaden event guard:**

```yaml
# Emit branch tag on push, schedule, AND workflow_dispatch
if: >-
  (github.event_name == 'push' ||
   github.event_name == 'schedule' ||
   github.event_name == 'workflow_dispatch') &&
  startsWith(github.ref, 'refs/heads/')
```

**Dockerfile layer cache ordering (ARG before RUN):**

```dockerfile
# ARG declarations must appear BEFORE RUN commands that consume them
ARG EXTRAS=""
ARG BUILD_TYPE=release
RUN echo "Building $BUILD_TYPE with extras: $EXTRAS"
```

**Optional-dep layer caching with tomllib:**

```dockerfile
ARG EXTRAS=""
COPY pyproject.toml /opt/app/
RUN pip install --user --no-cache-dir \
    $(python3 -c "
import tomllib, os
data = tomllib.load(open('/opt/app/pyproject.toml', 'rb'))
deps = list(data['project']['dependencies'])
opt = data['project'].get('optional-dependencies', {})
for group in [g.strip() for g in os.environ.get('EXTRAS', '').split(',') if g.strip()]:
    deps.extend(opt.get(group, []))
print(' '.join(deps))
" EXTRAS="$EXTRAS")
```

**Dockerfile version guard patterns:**

```dockerfile
# Pin installer versions via ENV for reproducibility
ENV PIXI_VERSION=0.63.2
RUN curl -fsSL https://pixi.sh/install.sh | bash -s -- --version $PIXI_VERSION
```

**Forbid remote ops in E2E containers:**

```python
# pytest conftest.py — block git fetch/clone inside container tests
import subprocess
original_run = subprocess.run
def guarded_run(args, **kwargs):
    if isinstance(args, list) and args[0] == 'git' and args[1] in ('fetch', 'clone'):
        raise RuntimeError("Remote git ops forbidden in E2E container tests")
    return original_run(args, **kwargs)
subprocess.run = guarded_run
```

**Docker Compose v5 healthcheck (string form, not array):**

```yaml
# Docker Compose v5 (v2.39+) splits array healthchecks on spaces
# WRONG (array — gets split): test: ["CMD-SHELL", "wget -qO- http://..."]
# CORRECT (string form):
healthcheck:
  test: "wget -q -O /dev/stdout http://localhost:8080/health | grep -q ok || exit 1"
```

### Detailed Steps

1. **Dockerfile authoring**: pin all base images with SHA256 digests; add `apt-get upgrade -y` for CVE defense; never put `#` comments after `\` in multi-line RUN blocks (Docker parses the token after `\` as a new instruction).
2. **Layer caching**: copy dependency manifests (`pyproject.toml`, `pixi.toml`) before source; declare `ARG` before the `RUN` that consumes it.
3. **Rootless Podman**: re-declare `ARG` in every `FROM` stage; `chmod 755` home dir; use `:Z` not `:delegated`; create output dirs inside the container exec, not on the host.
4. **Multi-arch**: always run `docker/setup-qemu-action` BEFORE `docker/setup-buildx-action`; use `type=oci,dest=/tmp/foo` (no `.tar`) for OCI layout directories; `type=docker` does not support multi-platform.
5. **pixi isolation**: set `detached-environments = true` in `.pixi/config.toml`; mount `pixi-cache` to `~/.cache/pixi`, NOT `~/.pixi` (which shadows the binary).
6. **Healthchecks on distroless/scratch**: use string form in docker-compose; use a Go/Rust compiled binary or TCP check via `nc` if no shell available.
7. **Conan 2 + Docker**: use `--profile:all=` (not `--profile=`); match `compiler.version` to distro GCC (Ubuntu 24.04 ships gcc-13, not gcc-14).
8. **GHA image cache extraction**: reconstruct the exact cache key string; export via `podman save`; download artifact with `gh run download`.

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
| --------- | ---------------- | --------------- | ---------------- |
| Fix all PRs before fixing root cause on main | Rebased individual PR branches | CI kept failing because root bugs were on main; each rebase pulled broken main back | Fix root-cause bugs on main FIRST, then rebase PRs |
| Inline `#` comment after `\` in Dockerfile RUN | `apt-get install curl \ # comment` | Docker parser treats the token after `\` as a new instruction, not a comment | Never put `#` comments after `\` in multi-line RUN blocks |
| `RUN pre-commit install` in Dockerfile | Install at image build time | Workspace bind-mount not active at build time; installed hooks get shadowed at runtime | Install pre-commit hooks in `entrypoint.sh` (container startup), not Dockerfile |
| `type=oci,dest=/tmp/foo.tar` for OCI layout | Added `.tar` extension to OCI dest path | `oci-layout://` requires a directory; `.tar` creates a single archive — fails with "not a directory" | Omit `.tar` extension; buildx saves an OCI layout directory |
| Multi-arch build without QEMU | `docker buildx build --platform linux/amd64,linux/arm64` without QEMU setup | Fails with exec format error for non-native arch | Always run `docker/setup-qemu-action` before `docker/setup-buildx-action` |
| `load: true` for multi-arch base image | Push base into Docker daemon, reference by name in downstream | `docker-container` driver builds in an isolated container that does NOT share host daemon image store | Use OCI layout directory via `/tmp` for same-job chaining |
| `type=docker` output for multi-platform build | Set output type to docker for multi-arch | `type=docker` does not support multiple platforms | Use `type=oci` for multi-arch; `type=docker` is single-platform only |
| `docker/login-action` with Podman | Used Docker-specific GHA actions with Podman | These actions assume Docker daemon is running | Use raw `podman login` via `run:` steps instead |
| `type=gha` Docker buildx cache with Podman | Docker GHA cache strategy | Podman does not support buildx or GHA cache type | Use `actions/cache` on `~/.local/share/containers` keyed by Dockerfile hash |
| Keeping `:delegated` volume mount with Podman | Docker-only volume consistency option | Podman ignores `:delegated` and may warn | Use `:Z` for SELinux label compatibility |
| `chmod -R 700 $PIXI_HOME $PIXI_CACHE_DIR` in Dockerfile | Restrict pixi dirs for security | Breaks pixi when container runs as different UID (rootless remapping) | Remove overly-restrictive chmod on pixi dirs |
| `workspace-pixi` named volume at `.pixi/` | Shadow host `.pixi/` with Docker volume | Shadows pixi binary itself when `~/.pixi/bin` is inside the mount path | Use `detached-environments = true` and mount only cache, not the entire `.pixi/` |
| `["CMD-SHELL", "wget -qO- ..."]` healthcheck array | Docker Compose v5 healthcheck array | Compose v5 (v2.39+) splits healthcheck arrays on spaces — each flag becomes a separate arg | Use string form: `test: "wget -qO- http://... \|\| exit 1"` |
| `apt-get install gcc-14 && update-alternatives` for Conan GCC | Set gcc-14 via alternatives for Conan 2 sub-shell | Conan 2 sub-shells don't inherit alternatives; `CMAKE_C_COMPILER` stays empty | Downgrade `compiler.version` in Conan profile to match distro default, or pass `tools.build:compiler_executables` explicitly |
| Bare `--profile=conan/profiles/default` in Conan 2 | Conan 1 invocation style | Conan 2 requires BOTH host and build profiles; bare `--profile=` only sets host profile | Use `--profile:all=` for in-repo profile files |
| Authenticating to Docker Hub for rate limits | Added Docker Hub credentials | Adds secret management overhead; MCR mirror is simpler and free | Use `mcr.microsoft.com/mirror/docker/library/` — no auth, no rate limits |
| `mkdir -p benchmark-results` on host before `podman compose exec` | Create output dir on host runner | Container process (different UID, rootless remapping) cannot write host-created dirs | Create output dirs inside the container exec command, not on the host |
| `RUN nomad job validate` on all `.hcl` files | `for f in *.hcl; do nomad job validate "$f"; done` | vault-policy.hcl has no `job` stanza; nomad errors on non-job HCL | Guard with `grep -q '^job '` before calling nomad job validate |
| Hardcoded service count in compose validation | `[ "$ACTUAL" -eq 12 ]` | Adding new services breaks the hardcoded count silently | Use `docker compose config --services \| wc -l` dynamically |
| `type=docker` for OCI layout artifact pipeline | `docker save` for OCI layout pipeline | `oci-layout://` requires uncompressed directory tree, not a tarball | Use `docker buildx build --output type=oci,dest=<dir>` for OCI layout |
| Broad paths filter (`**/*.toml`) for throttle | Used glob to catch all TOML files | Unrelated `.toml` files (Rust crates, tooling configs) triggered rebuilds | Be specific: use literal filenames, not broad globs |
| Cron at `'0 0 * * *'` (UTC midnight) | Scheduled container builds at midnight UTC | Coincides with GHA queue surge; builds queued 30+ min | Pick off-peak: `0 6 * * *` was empirically uncontended |
| Forgot `tags: ['v*']` in push trigger when adding paths | Release tag pushes after adding `paths:` filter | Tags don't modify filtered paths, so tag pushes no longer triggered builds | Keep tags as a separate trigger entry without `paths:` |
| Only bumping primary base image digest for CVEs | Updated Python base image SHA only | npm CVEs from `node:20-slim` remained | Bump ALL pinned image digests, not just the primary base |
| `\|\| true` on binary version check in multi-arch | `RUN goose --version \|\| true` without QEMU | Without QEMU, arm64 invocations fail silently when guarded by `\|\| true` | Remove `\|\| true` from sanity checks after confirming QEMU is set up |
| `git config core.hooksPath .git/hooks` before pre-commit install | Set hooks path explicitly | If `core.hooksPath` is set, pre-commit refuses to install | Do not set `core.hooksPath` unless intentional; unset before `pre-commit install` |
| Separate `helpers.py` for test utilities | Created `tests/foundation/helpers.py` | `conftest.py` is already the shared utilities file; extra file adds indirection | Put plain helper functions directly in `conftest.py` |
| Using symlink `Dockerfile` → `Containerfile` during Docker-to-Podman migration | Kept `Dockerfile` symlink for compatibility | Unnecessary complexity | Rename directly to `Containerfile`; Podman finds it first |

## Results & Parameters

### Security Patching Cadence

| Step | Command |
| ------ | ------- |
| Bump pinned digest | Update all `FROM image@sha256:...` lines |
| OS CVE patches | `apt-get update && apt-get upgrade -y` in first RUN |
| npm audit | `npm audit fix` in Node stages |
| Trivy scan | Add `aquasecurity/trivy-action` to CI workflow |

### Podman CI Key Parameters

```yaml
# Build for GHCR
podman build --format docker -f Containerfile --target <target> -t <tag> .

# GHA cache (not Docker buildx GHA cache)
- uses: actions/cache@v4
  with:
    path: ~/.local/share/containers
    key: container-image-uid${{ steps.uid.outputs.user_id }}-${{ hashFiles('Dockerfile', 'pixi.toml', 'pixi.lock') }}
```

### OCI Layout: Directory vs Tarball

| `dest=` value | Result on disk | `oci-layout://` compatible? |
| --------------- | ---------------- | ------------------------------ |
| `/tmp/foo.tar` | Single `.tar` archive file | No — fails with "not a directory" |
| `/tmp/foo` | OCI layout directory (`index.json`, `blobs/`, `oci-layout`) | Yes |

### Rootless Podman UID Quick-Fix Table

| Issue | Root Cause | Fix |
| ------- | ----------- | ----- |
| `can't find uid for user :` | Docker ARGs don't persist across `FROM` | Re-declare `ARG` in each stage |
| `Permission denied` on workspace files | Rootless Podman UID namespace mapping | `chmod -R a+rwX .` on host before container use |
| `docker-compose` ignores `userns_mode` | docker-compose CLI plugin, not Podman compose | Don't use Podman-specific compose extensions in docker-compose |
| SBOM scan auth failure | Syft can't authenticate to GHCR | Export image to tarball, scan locally |

### Healthcheck: Distroless / Scratch

```dockerfile
# Option A: compiled binary probe (copy nc or a Go binary into the image)
HEALTHCHECK --interval=10s --timeout=5s CMD ["/usr/bin/nc", "-z", "localhost", "8080"]

# Option B: TCP check via shell (only if shell is available)
HEALTHCHECK CMD sh -c "wget -qO- http://localhost:8080/health | grep -q ok || exit 1"
```

### Dockerfile Version Pin Pattern

```dockerfile
ENV PIXI_VERSION=0.63.2
RUN curl -fsSL https://pixi.sh/install.sh | bash -s -- --version $PIXI_VERSION
```

### Container-Throttle Schedule (Empirically Good)

```yaml
schedule_cron: '0 6 * * *'   # 06:00 UTC — off-peak
```

## Verified On

| Project | Context | Details |
| --------- | --------- | --------- |
| ProjectOdyssey | Multiple PRs — Docker-to-Podman migration, pixi isolation, UID mismatch | skills/docker-to-podman-migration.history |
| AchaeanFleet | PR #219 — multi-arch OCI, Conan 2 profile chain, ENTRYPOINT enforcement | skills/container-build-and-runtime-patterns.history |
| ProjectKeystone | PR — rootless Podman DNS, compose mount clone-aware | skills/container-build-and-runtime-patterns.history |
| ProjectNestor | PR — C++ coverage container, clang-format pinning, Podman CI containerization | skills/container-build-and-runtime-patterns.history |
| ProjectScylla | PR — E2E container testing, pixi container env isolation | skills/container-build-and-runtime-patterns.history |

## References

- [docker-mojo-uid-mismatch-crash-fix.md](docker-mojo-uid-mismatch-crash-fix.md) — detailed Mojo UID mismatch fixes (keep-as-example)
- [docker-multistage-build.md](docker-multistage-build.md) — full multistage build walkthrough (keep-as-example)
- [fix-podman-rootless-ci.md](fix-podman-rootless-ci.md) — rootless Podman CI setup (keep-as-example)
- [podman-from-source-install.md](podman-from-source-install.md) — install Podman from source (keep-as-example)
- [docker-entrypoint-bats.md](docker-entrypoint-bats.md) — BATS testing for entrypoints (keep-as-example)
- [Podman rootless documentation](https://github.com/containers/podman/blob/main/docs/tutorials/rootless_tutorial.md)
- [Docker multi-stage builds](https://docs.docker.com/build/building/multi-stage/)
- [OCI image spec](https://github.com/opencontainers/image-spec)
