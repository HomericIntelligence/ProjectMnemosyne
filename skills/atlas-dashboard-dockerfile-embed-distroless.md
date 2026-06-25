---
name: atlas-dashboard-dockerfile-embed-distroless
description: "Package a Go HTTP service into a tiny distroless image with assets baked in via //go:embed. Use when: (1) writing a Dockerfile/.dockerignore/Makefile for a Go service that must ship static web assets inside the binary, (2) targeting gcr.io/distroless/static:nonroot (no shell, nonroot UID, non-privileged port) with a ≤30MB image budget, (3) injecting a build-time version string when .dockerignore excludes .git so `git describe` cannot run inside the build."
category: ci-cd
date: 2026-06-20
version: "1.0.0"
user-invocable: false
verification: unverified
tags:
  - atlas
  - dashboard
  - go
  - docker
  - dockerfile
  - go-embed
  - embed-fs
  - distroless
  - dockerignore
  - ldflags
  - git-describe
  - build-arg
  - multi-stage
  - nonroot
---

# Atlas Dashboard: Dockerfile + embed.FS + distroless Packaging (M1)

## Overview

| Field | Value |
|-------|-------|
| **Date** | 2026-06-20 |
| **Objective** | Plan ProjectArgus issue #153 "[atlas][M1] Dockerfile + embed.FS + distroless runtime" — add Dockerfile/.dockerignore/Makefile and `//go:embed` wiring on top of the #152 chi-server skeleton |
| **Outcome** | PLAN ONLY — never executed; no `docker build` run, no CI green. Captured for the next implementer. |
| **Verification** | unverified (plan only — never built or run in CI) |

## When to Use

- Writing a `Dockerfile` for a Go HTTP service whose static web assets must live **inside** the binary (no `COPY web/` at runtime).
- Targeting `gcr.io/distroless/static:nonroot` and you need to satisfy: no shell, nonroot UID, non-privileged port, static-binary-only copy.
- The issue spec asks for a `git describe`-derived version but a correct `.dockerignore` excludes `.git`.
- You hit a build where a `Dockerfile` `ARG` is unexpectedly empty in a later `FROM` stage.
- You need to keep a Go container image small (≤30MB) and are deciding between `embed.FS` vs. copying an assets directory.

## Proposed Workflow

> **Warning:** This workflow has not been validated end-to-end. Treat as a hypothesis until CI confirms.

### Quick Reference

```bash
# 1. embed: web/ MUST be a sibling of the .go file holding the directive
#    cmd/argus-dashboard/main.go  +  cmd/argus-dashboard/web/...
#    //go:embed web         <- legal
#    //go:embed ../web      <- ILLEGAL (no parent refs)
fs.Sub(assets, "web/static")   # serve /static/ from embedded web/static/

# 2. Compute version on the HOST (Makefile), NOT inside the Dockerfile,
#    because .dockerignore excludes .git -> `git describe` cannot run in-build.
VERSION := $(shell git describe --tags --always 2>/dev/null || echo dev)
docker build --build-arg VERSION=$(VERSION) -t argus-dashboard .

# 3. Re-declare ARG in EVERY stage that consumes it (ARG does not cross FROM).
# 4. distroless:nonroot -> bind a non-privileged port (3002 OK), no shell-form healthcheck.
```

### Detailed Steps

1. **Embed lives next to the directive file; no parent references.** `//go:embed web` only works when `web/` is a sibling of the `.go` file that contains the directive. Place embedded assets at `cmd/argus-dashboard/web/...` next to `main.go`. `//go:embed ../web` is a compile error — embed patterns cannot escape the directive file's directory. Serve the static route by sub-rooting the FS: `sub, _ := fs.Sub(assets, "web/static"); mux.Handle("/static/", http.StripPrefix("/static/", http.FileServer(http.FS(sub))))`.
2. **Multi-stage Dockerfile, version via `--build-arg`, `git describe` on the host.** A correct `.dockerignore` excludes `.git`, so any `RUN git describe` inside the build context fails (no `.git`). Resolve the issue spec's `-X version.Version=$(git describe ...)` contradiction by: (a) computing `git describe --tags --always` in the **Makefile** on the host, (b) passing it as `ARG VERSION` (default `dev`), (c) consuming it in `-ldflags "-X .../version.Version=$VERSION"`.
3. **Re-declare `ARG VERSION` in each `FROM` stage that uses it.** A `Dockerfile` `ARG` declared before the first `FROM` (or in the builder stage) is **not** visible in a later stage; an undeclared `ARG` expands to empty silently — the version becomes blank with no error. Add `ARG VERSION` immediately after each `FROM ... AS <stage>` that references `$VERSION`.
4. **Respect the distroless:nonroot runtime constraints.** `gcr.io/distroless/static:nonroot` has no shell (no shell-form `HEALTHCHECK`, no entrypoint scripts — use exec-form or an in-binary `/healthz` handler), runs as a nonroot UID (bind a non-privileged port like 3002, never <1024), and contains only what you `COPY` — so you copy a single static binary. This is exactly **why** `embed.FS` is required: there is no place to `COPY web/` and have it served, and the embedded assets are what keep the image ≤30MB.
5. **Drop `-ldflags -X` if no version package exists in the upstream skeleton.** If #152 did not create a `version` package, `-X version.Version=...` references a non-existent symbol. Fall back to building without the `-X` flag (or add a minimal `internal/version` package) rather than failing the build.

## Verified Workflow

_Not applicable._ This skill was captured from a planning session and is `unverified`: the Dockerfile/embed plan was never built and no CI ran, so there is no verified workflow. The actionable, hypothesis-level mechanics live under **Proposed Workflow** above and must be treated as unvalidated until CI confirms them. (This placeholder section exists only because `scripts/validate_plugins.py` requires the literal `## Verified Workflow` heading; it intentionally makes no verification claim.)

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
|---------|----------------|---------------|----------------|
| 1 | Followed the issue spec literally: `RUN ... -X version.Version=$(git describe --tags --always)` inside the Dockerfile build. | A correct `.dockerignore` excludes `.git`, so `git describe` has no repo to read inside the build context — the spec is self-contradictory. | Compute `git describe` on the HOST in the Makefile and pass it via `--build-arg VERSION=` (default `dev`); never run `git describe` inside the build. |
| 2 | Placed embedded assets at repo-root `web/` and wrote `//go:embed ../web` in `cmd/argus-dashboard/main.go`. | `//go:embed` patterns are relative to the directive file's directory and cannot reference parent directories — compile error. | Put `web/` as a sibling of the `.go` file holding the directive (`cmd/argus-dashboard/web/`); serve via `fs.Sub(assets, "web/static")`. |
| 3 | Declared `ARG VERSION` once before the first `FROM` and used `$VERSION` in the final runtime stage. | `ARG` does not cross `FROM` boundaries; an undeclared `ARG` in a later stage expands to empty with no error — version silently blank. | Re-declare `ARG VERSION` immediately after each `FROM ... AS <stage>` that consumes it. |
| 4 | Planned a shell-form `HEALTHCHECK CMD curl ...` and copied `web/` into the final image. | `distroless:nonroot` has no shell and copies only the static binary — shell healthcheck cannot run and `COPY web/` assets would not be served from the binary. | Use an in-binary `/healthz` handler (exec-form check), bind a non-privileged port (3002), and rely on `embed.FS` instead of `COPY web/` to stay ≤30MB. |

## Results & Parameters

- **Status:** Implementation plan for ProjectArgus issue #153; not executed. No image was built, no size measured, no CI confirmed.
- **Target image:** `gcr.io/distroless/static:nonroot`, size budget ≤30MB, runtime port 3002 (non-privileged).
- **Key paths (hypothesis, pending #152 verification):** `cmd/argus-dashboard/main.go`, `cmd/argus-dashboard/web/static/...`, `Dockerfile`, `.dockerignore`, `Makefile`.
- **Build invocation:** `docker build --build-arg VERSION=$(git describe --tags --always 2>/dev/null || echo dev) -t argus-dashboard .`
- **Unverified assumptions (must check before building):** module path in `go.mod`, existence of a `version` package, location of the `web/` directory, whether `atlas.css`/`/healthz` already exist from #152. See the companion skill `planning-dependent-issue-unverified-upstream` for the verification methodology.
