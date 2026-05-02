# Docker to Podman Migration - Session Notes

## Context

ProjectOdyssey had `NATIVE=1` added to CI workflows as a workaround to bypass Docker container
execution. The user wanted this removed entirely — ALL Mojo commands must run inside Podman
containers in CI.

## Migration Scope

### Phase 1: Core infrastructure (14 files)

- justfile: Full rewrite from Docker to Podman
  - `docker_service` → `podman_service`
  - `_run` helper: Docker detection → Podman detection
  - All `docker-*` recipes → `podman-*`
  - Removed old standalone Podman section (was separate from Docker section)
  - GHCR recipes: `docker build` → `podman build --format docker`
  - CI recipes: removed `docker buildx`, simplified

- docker-compose.yml:
  - `:delegated` → `:Z` (SELinux label for rootless Podman)
  - `${HOME}/.gitconfig` → `${HOME:-.}/.gitconfig` (CI safety)

- New setup-container composite action:
  - `touch "$HOME/.gitconfig"` (prevents bind-mount failure)
  - Export `USER_ID`/`GROUP_ID` to `GITHUB_ENV`
  - `actions/cache` on `~/.local/share/containers`
  - `podman compose build` + `up -d`
  - 30-second retry loop for container readiness

- 3 main test workflows:
  - comprehensive-tests.yml (8 jobs)
  - build-validation.yml
  - training-tests-weekly.yml

- GHCR publish: docker.yml → container-publish.yml
  - Removed: docker/setup-qemu-action, docker/setup-buildx-action, docker/login-action,
    docker/metadata-action, docker/build-push-action
  - Added: shell-based tag generation, `podman build/push`, `actions/cache`

- release.yml: `publish-docker` → `publish-container`

### Phase 2: Remaining workflows (7 files)

Discovered during audit that 9 additional jobs ran Mojo commands:
- release.yml: `build` + `test` jobs
- benchmark.yml: `benchmark-execution` + `simd-benchmarks`
- model-e2e-tests-weekly.yml
- paper-validation.yml: `validate-implementation` + `validate-reproducibility`
- simd-benchmarks-weekly.yml
- validate-configs.yml: `validate-paper-reproducibility`
- mojo-version-check.yml

Pattern: `pixi run mojo ...` → `podman compose exec -T <service> bash -c 'pixi run mojo ...'`

### Mojo compilation fixes (on main)

- test_shape_part3.mojo: Duplicate 5-arg `assert_value_at` calls (signature is 4-arg: tensor, flat_index, expected, message)
- SimpleMLP2 in models.mojo: Missing `train()`, `set_inference_mode()`, `parameters()` returned empty list instead of 4 tensors

## Key Reference URLs

- https://oneuptime.com/blog/post/2026-03-18-use-github-container-registry-podman/view
- https://oneuptime.com/blog/post/2026-01-27-podman-cicd/view
- https://github.com/ibm-cloud-architecture/refarch-cloudnative-devops-kubernetes/blob/master/docs/podman.md

## Critical Learnings

1. **`--format docker` is mandatory** for GHCR pushes. Without it, Podman uses OCI format
   which some tools don't handle correctly.

2. **`actions/cache` on `~/.local/share/containers`** replaces Docker's `type=gha` cache.
   Key by Dockerfile hash + dependency lockfiles.

3. **Host file operations stay on host** — the workspace bind mount means `mkdir -p` on host
   creates dirs visible in container and vice versa.

4. **Always audit ALL workflows** — `grep -r 'pixi run mojo' .github/workflows/` before
   declaring migration complete. Easy to miss infrequently-run workflows (weekly, manual-only).

5. **Non-Mojo jobs can keep setup-pixi** — pre-commit, docs, security scanning, smoke tests
   that only use Python/shell don't need the container overhead.

6. **`podman compose` reads `docker-compose.yml` natively** — no need to rename the file.

7. **`:Z` volume label** — required for rootless Podman SELinux relabeling, harmless no-op
   on systems without SELinux.
