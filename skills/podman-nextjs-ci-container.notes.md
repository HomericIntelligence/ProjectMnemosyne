# Session Notes: Podman Dev Container for AI Maestro

## Date: 2026-03-19

## Context

User wanted to: (1) run all testing, linting, build, and typecheck for AI Maestro and fix any issues found, then (2) create a Podman dev container so the entire repo can be built and tested inside a container.

## Phase 1: Host CI Simulation

All 4 checks passed on host without code fixes needed:
- `yarn test` — 486 tests pass
- `yarn lint` — warnings only (no errors)
- `npx tsc --noEmit` — clean
- `yarn build` — passes (stale `.next` cache was only issue, fixed by `rm -rf .next`)

## Phase 2: Container Creation

### Iteration 1: node:20.18.3
- Failed: vite 7.3.1 requires >=20.19.0
- Error: engine incompatibility during build

### Iteration 2: node:20.19.2 + npm install -g yarn
- Failed: yarn already installed in node:20 image
- Fix: removed the yarn install step

### Iteration 3: groupadd -g 1000 for node user
- Failed: GID 1000 already taken by existing `node` user
- Fix: use existing `node` user directly

### Iteration 4: Short image name `node:20.19.2-bookworm-slim`
- Failed: Podman can't resolve short names
- Fix: use `docker.io/library/node:20.19.2-bookworm-slim`

### Iteration 5: Sequential CI without .next cleanup
- Failed: build step hangs due to stale .next cache
- Fix: `(rm -rf .next || true)` before build

### Iteration 6: Default heap size
- Failed: OOM during Next.js production build
- Fix: `NODE_OPTIONS="--max-old-space-size=4096"`

### Final: Working Containerfile
- All tests pass (486)
- Lint clean (warnings only)
- tsc clean
- Build succeeds (53 pages)

## Phase 3: GitHub Issue + Patch

- Created issue #296 on 23blocks-OS/ai-maestro
- Could not push (no write access to upstream)
- Created gist with `git format-patch` and attached to issue via comment
- Updated gist after yarn.lock fix

## Files Created/Modified

| File | Action |
| ------ | -------- |
| `Containerfile` | Created |
| `.containerignore` | Created |
| `package.json` | Modified (6 container:* scripts) |
| `yarn.lock` | Updated (lockfile sync after version bump) |

## Skills Registry Patterns Applied

- dockerfile-layer-caching: COPY package.json+yarn.lock before source
- dockerfile-dep-pin: pinned node:20.19.2-bookworm-slim
- fix-docker-platform: --platform linux/amd64
- fix-docker-shell-tty: -it flags on container:shell
- build-run-local: matches container:ci approach