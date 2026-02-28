---
name: docker-optional-dep-layer-caching
description: "TRIGGER CONDITIONS: When a Dockerfile uses tomllib to extract pyproject.toml runtime deps for layer caching but omits optional-dependency groups, causing them to be reinstalled on every source change when installed as extras"
user-invocable: false
category: tooling
date: 2026-02-27
---

# docker-optional-dep-layer-caching

Extend Docker Layer 2 `tomllib` extraction to include `[project.optional-dependencies]` groups via an `ARG EXTRAS=""` build argument so they land in the cached pip layer.

## Overview

| Item | Details |
|------|---------|
| Date | 2026-02-27 |
| Objective | Cache optional-dependency groups in Docker Layer 2 alongside runtime deps |
| Outcome | Success |

## When to Use

- A Dockerfile uses a `python3 -c "import tomllib..."` snippet in Layer 2 to cache `[project].dependencies`
- The project has `[project.optional-dependencies]` groups (e.g. `analysis`, `dev`) in `pyproject.toml`
- Anyone might build the image with `pip install /opt/scylla/[analysis]` — if `analysis` extras aren't in Layer 2, they bypass the cache and reinstall on every source rebuild
- You want `EXTRAS=analysis docker-compose build` or `--build-arg EXTRAS=analysis` to be sufficient to cache extras without touching source layers

## Verified Workflow

1. **Add `ARG EXTRAS=""`** before the Layer 2 `COPY pyproject.toml` line in the Dockerfile (not after — ARG must be in scope for the RUN command)

2. **Extend the `tomllib` Python snippet** to read `EXTRAS` from the environment and pull the named groups from `[project.optional-dependencies]`:

   ```dockerfile
   ARG EXTRAS=""
   COPY pyproject.toml /opt/scylla/
   RUN pip install --user --no-cache-dir \
       $(python3 -c "
   import tomllib, os
   data = tomllib.load(open('/opt/scylla/pyproject.toml', 'rb'))
   deps = list(data['project']['dependencies'])
   opt = data['project'].get('optional-dependencies', {})
   for group in [g.strip() for g in os.environ.get('EXTRAS', '').split(',') if g.strip()]:
       deps.extend(opt.get(group, []))
   print(' '.join(deps))
   " EXTRAS="$EXTRAS")
   ```

   Key points:
   - Pass `EXTRAS="$EXTRAS"` as an env var to the shell `$(...)` subshell — ARG values are available as shell variables in `RUN` but must be forwarded explicitly to Python via `os.environ`
   - Split on `,` so `EXTRAS=analysis,dev` installs both groups
   - `data['project'].get('optional-dependencies', {})` is safe when no optional groups exist
   - Empty/blank EXTRAS produces the original runtime-only dep list (no regression)

3. **Update docker-compose.yml** to wire `EXTRAS` through from the host environment:

   ```yaml
   build:
     context: ..
     dockerfile: docker/Dockerfile
     args:
       EXTRAS: ${EXTRAS:-}
   ```

4. **Write static-analysis tests** (no Docker daemon required) that assert:
   - `ARG EXTRAS` is declared
   - `ARG EXTRAS` appears before Layer 3 (before `--no-deps` install)
   - `optional-dependencies` is referenced in the Layer 2 RUN command
   - `EXTRAS=$EXTRAS` is passed into the python snippet
   - `os.environ` or `os.getenv` is used to read `EXTRAS`
   - Default is `ARG EXTRAS=""` (empty → no regression)
   - `docker-compose.yml` references `EXTRAS` in build args

5. **Run tests** — all 7 static-analysis assertions pass in < 0.1 s with no Docker daemon

## Failed Attempts

| Attempt | Why Failed | Lesson |
|---------|-----------|--------|
| Using `ENV EXTRAS` instead of `ARG EXTRAS` | ENV persists into the final image and leaks build config into runtime containers | Always use `ARG` for build-time-only values |
| Passing `EXTRAS` directly in the python snippet without `EXTRAS="$EXTRAS"` | Shell subshell `$(...)` inherits the builder's ARG as a shell variable but Python's `os.environ` only sees variables passed explicitly | Pass ARG values via `KEY=value python3 -c ...` prefix |
| Placing `ARG EXTRAS=""` after `COPY pyproject.toml` | ARG is in scope for the subsequent RUN, but moving it before COPY makes the Dockerfile self-documenting and keeps the caching contract explicit | Declare ARG before the COPY it gate-keeps |

## Results & Parameters

```yaml
# Dockerfile Layer 2 — copy-paste ready
ARG EXTRAS=""
COPY pyproject.toml /opt/scylla/
RUN pip install --user --no-cache-dir \
    $(python3 -c "
import tomllib, os
data = tomllib.load(open('/opt/scylla/pyproject.toml', 'rb'))
deps = list(data['project']['dependencies'])
opt = data['project'].get('optional-dependencies', {})
for group in [g.strip() for g in os.environ.get('EXTRAS', '').split(',') if g.strip()]:
    deps.extend(opt.get(group, []))
print(' '.join(deps))
" EXTRAS="$EXTRAS")

# docker-compose.yml build args
build:
  args:
    EXTRAS: ${EXTRAS:-}

# Build invocations
docker build .                                      # runtime only (default)
docker build --build-arg EXTRAS=analysis .          # + analysis group
docker build --build-arg EXTRAS=analysis,dev .      # + both groups
EXTRAS=analysis docker-compose build                # via compose
```

## Verified On

| Project | Context | Details |
|---------|---------|---------|
| ProjectScylla | Issue #1139, PR #1202 | [notes.md](../../references/notes.md) |

## References

- Related skills: `python-version-alignment` (Dockerfile + pyproject.toml alignment)
- External docs: [Docker ARG reference](https://docs.docker.com/reference/dockerfile/#arg)
