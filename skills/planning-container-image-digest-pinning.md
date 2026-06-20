---
name: planning-container-image-digest-pinning
description: "Planning-discipline for pinning floating container image tags (:latest, :alpine) in a Compose/e2e stack to immutable name:vX.Y.Z@sha256:<digest> references for reproducibility — WHAT a planner can and cannot verify offline. Use when: (1) planning a fix for an issue like ':latest image tags break reproducibility' in a docker-compose/e2e file, (2) you are about to write specific upstream version tags and sha256 digests into a plan without registry access, (3) you need to choose between pinning a multi-arch manifest-list digest vs a single-arch image digest, (4) you are tempted to cite an existing Actions SHA-pin convention as proof that container images should be digest-pinned, or to rely on `compose config` as the acceptance check."
category: ci-cd
date: 2026-06-20
version: "1.0.0"
user-invocable: false
verification: unverified
tags:
  - planning
  - container-images
  - digest-pinning
  - reproducibility
  - docker-compose
  - skopeo
  - multi-arch-manifest
  - offline-verification
  - latest-tag
  - guard-script
---

# Planning a Container-Image Digest-Pinning Fix: What a Planner Can (and Cannot) Verify Offline

## Overview

| Field | Value |
|-------|-------|
| **Date** | 2026-06-20 |
| **Objective** | Produce a PLAN (not an implementation) for Odysseus issue #188 "[MAJOR] E2E compose stack uses :latest image tags": pin `prom/prometheus:latest`, `grafana/loki:latest`, `grafana/grafana:latest` in `docker-compose.e2e.yml` to immutable `name:vX.Y.Z@sha256:<digest>` references and add a guard script. |
| **Outcome** | PLAN ONLY — never executed. The durable learning is planning discipline: a planner with no registry access must defer every digest/version choice to implementation time with explicit resolution commands, and must distinguish what was verified from what was extrapolated. |
| **Verification** | unverified (plan only — no registry was queried, no `compose up`/CI ran; the local `grep`/file inspections of the repo WERE run and are real) |

> **Warning:** This workflow has not been validated end-to-end. Treat as a hypothesis until CI confirms.

## When to Use

- You are planning a fix for an issue whose evidence is floating image tags (`:latest`, `:alpine`, bare `:tag`) in a `docker-compose*.yml` / e2e stack, and the ask is to pin them to immutable `name:vX.Y.Z@sha256:<digest>` references.
- You are about to type specific upstream version numbers (e.g. Prometheus v2.55.1, Loki 3.3.2, Grafana 11.4.0) and their `sha256` digests into the plan — but you have NO registry access to confirm them.
- You must decide whether to pin the multi-arch **manifest-list** digest or a single-platform image digest, and contributors may run arm64 vs amd64.
- You are tempted to justify image digest-pinning by citing the repo's existing GitHub **Actions** SHA-pin convention (e.g. commit `2c8039c`, `ci.yml:16`) — a related but NOT identical convention.
- You plan to add a guard script and/or use `compose config` as the acceptance check, and need to know whether either actually protects against regressions offline.

## Verified Workflow

> **Warning:** This workflow has not been validated end-to-end. Treat as a hypothesis until CI confirms. It is a planning-discipline workflow derived from a plan that was not executed end-to-end — the repo `grep`/file inspections below WERE run and are real, but no registry query or `compose up` was performed.

### Quick Reference

```bash
# --- DEFER digest resolution to implementation time. NEVER invent a digest. ---
# Resolve the REGISTRY-CANONICAL multi-arch manifest-LIST digest (preferred):
skopeo inspect --format '{{.Digest}}' docker://docker.io/prom/prometheus:v2.55.1
# Equivalent with buildx (also returns the manifest-list digest):
docker buildx imagetools inspect --format '{{.Manifest.Digest}}' prom/prometheus:v2.55.1
# podman manifest inspect prints JSON; do NOT pipe it through sha256sum (see Failed Attempts).

# --- Robust, tooling-INDEPENDENT acceptance check: every image is digest-pinned ---
grep -nE 'image:\s*\S+@sha256:[0-9a-f]{64}' docker-compose.e2e.yml   # must match each pinned line
# Guard-script regex to reject any remaining floating tag:
grep -nE 'image:\s*\S+:(latest|alpine)\b|image:\s*[^@[:space:]]+:[^@[:space:]]+$' docker-compose.e2e.yml

# --- Confirm the chosen tag actually EXISTS / is not yanked before pinning ---
skopeo inspect docker://docker.io/grafana/grafana:11.4.0 >/dev/null && echo "tag exists"
```

### Detailed Steps

1. **Mark every version + digest as "verify against registry at implementation time."** With no registry access, the planner cannot know the real digest. Write the version tag as a candidate and use a literal `<RESOLVED_DIGEST>` placeholder; provide the exact `skopeo inspect --format '{{.Digest}}'` command that the implementer must run. NEVER paste a plausible-looking 64-hex string — a guessed digest will pin a wrong/nonexistent image.
2. **Treat the chosen version tag as unconfirmed too.** A tag may be EOL/yanked or simply not exist. The implementer must `skopeo inspect docker://.../<repo>:<tag>` to confirm existence, and should prefer a maintained LTS line over the newest tag.
3. **Pin the multi-arch manifest-LIST digest, not a single-arch image digest.** `name@sha256:<digest>` can pin either. A single-platform digest breaks contributors on a different CPU arch (arm64 vs amd64). `skopeo inspect --format '{{.Digest}}' docker://<repo>:<tag>` and `docker buildx imagetools inspect --format '{{.Manifest.Digest}}'` return the manifest-list digest — use those. Call this out explicitly in the plan.
4. **State verified-vs-extrapolated precisely when citing precedent.** Verified: the repo SHA-pins GitHub **Actions** (commit `2c8039c`, `ci.yml:16`). Extrapolation: "therefore container images should be digest-pinned." Actions are pinned by **git commit SHA**, images by **registry content digest** — related convention, not the same one. Do not present the extrapolation as a verified fact.
5. **Check whether the guard is actually wired into CI — a guard that nothing runs is decorative.** Verified here: CI's `yamllint` only covers `configs/` (`ci.yml:24`), so a regression to `:latest` in `docker-compose.e2e.yml` would NOT be caught. Flag explicitly whether the new guard script should be added to a CI job (real regression protection) or is being left out-of-scope (no protection).
6. **Enumerate adjacent unpinned images and mark them in/out of scope.** Found but outside the issue evidence: `nats:alpine` (`docker-compose.e2e.yml:14`) and `nats:latest` (`e2e/docker-compose.cluster.yml:12,25`). Document them as out-of-scope rather than silently expanding — let the reviewer decide.
7. **Make a digest-presence `grep` the acceptance check; treat `compose config` as nice-to-have.** `podman compose -f ... config` resolves env-var interpolation (`${HERMES_DIR}`, `${PROJECT_ROOT}`, ...) which may be unset offline, so `config` can warn/fail for reasons unrelated to the pin; `podman compose` also delegates to the docker-compose plugin and may not pin-validate. A `grep` for `@sha256:[0-9a-f]{64}` is tooling-independent and robust.

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
|---------|----------------|---------------|----------------|
| Invent the digest in the plan | Write a concrete `@sha256:<64-hex>` for each image directly in the plan | No registry access during planning — any digest typed is a guess that pins a wrong or nonexistent image | A planner must NEVER invent a digest. Use a `<RESOLVED_DIGEST>` placeholder and supply the exact `skopeo inspect --format '{{.Digest}}'` resolution command; defer resolution to implementation time. |
| Trust the chosen version tag exists | Pick Prometheus v2.55.1 / Loki 3.3.2 / Grafana 11.4.0 and assume they are valid published tags | Tags can be EOL, yanked, or simply nonexistent; none were confirmed against the registry | Implementer must `skopeo inspect docker://.../<repo>:<tag>` to confirm the tag exists; prefer a maintained LTS line over the newest tag. |
| `podman manifest inspect ... \| sha256sum` to get the digest | Hash the JSON output of `podman manifest inspect` to obtain the pin digest | This hashes the JSON TEXT, not the registry-canonical manifest digest — produces a value that does not match any real `@sha256:` the registry serves | Use `skopeo inspect --format '{{.Digest}}'` or `docker buildx imagetools inspect --format '{{.Manifest.Digest}}'`; do not derive a digest by hashing inspect output. |
| Pin a single-arch image digest | Resolve and pin the platform-specific (e.g. amd64) image digest | `name@sha256:<single-arch>` breaks contributors on a different CPU arch (arm64) — the image won't pull on their platform | Pin the multi-arch **manifest-list** digest (what `skopeo inspect --format '{{.Digest}}'` returns for a multi-arch repo); call this out in the plan. |
| Cite the Actions SHA-pin convention as proof | Justify image digest-pinning by pointing at the repo's `ci.yml:16` Actions-pinned-by-SHA precedent (commit `2c8039c`) | Actions are pinned by **git commit SHA**; container images by **registry content digest** — related but not the same convention; presenting it as verified overstates the evidence | When citing a convention, state exactly what was verified (Actions are SHA-pinned) vs. what is an extrapolation (therefore images should be digest-pinned). |
| Rely on `compose config` as the acceptance check | Use `podman compose -f docker-compose.e2e.yml config` to validate the pinned stack | `config` interpolates `${HERMES_DIR}`/`${PROJECT_ROOT}`/etc. which are unset offline, so it warns/fails for reasons unrelated to the pin; `podman compose` delegates to the docker-compose plugin and may not pin-validate at all | Use a tooling-independent `grep -E 'image:\s*\S+@sha256:[0-9a-f]{64}'` as the robust acceptance check; treat `compose config` as a nice-to-have that can fail on unset env vars. |
| Add a guard script and assume it protects regressions | Add a script that rejects floating tags, but only "note" CI wiring as out-of-scope | CI `yamllint` covers only `configs/` (`ci.yml:24`); nothing runs the guard on `docker-compose.e2e.yml`, so a regression to `:latest` is not caught | A guard that isn't wired into a CI job is decorative — explicitly flag whether it should be added to CI, or that the file currently has no regression protection. |

## Results & Parameters

**Issue:** Odysseus #188 "[MAJOR] E2E compose stack uses :latest image tags" — PLAN ONLY, not implemented.

**Target file & images in scope** (`docker-compose.e2e.yml`):

```text
prom/prometheus:latest   -> prom/prometheus:vX.Y.Z@sha256:<RESOLVED_DIGEST>
grafana/loki:latest      -> grafana/loki:X.Y.Z@sha256:<RESOLVED_DIGEST>
grafana/grafana:latest   -> grafana/grafana:X.Y.Z@sha256:<RESOLVED_DIGEST>
```

Candidate versions (UNVERIFIED — confirm at implementation time): Prometheus v2.55.1, Loki 3.3.2, Grafana 11.4.0. Prefer a maintained LTS line; do not paste these into the manifest without `skopeo inspect`-confirming both the tag and the manifest-list digest.

**Out of scope (documented, not changed):** `nats:alpine` (`docker-compose.e2e.yml:14`); `nats:latest` (`e2e/docker-compose.cluster.yml:12,25`).

**Resolution commands (implementation time):**

```bash
skopeo inspect --format '{{.Digest}}' docker://docker.io/<repo>:<tag>
docker buildx imagetools inspect --format '{{.Manifest.Digest}}' <repo>:<tag>
```

**Acceptance check (tooling-independent):**

```bash
# Every image line must carry a 64-hex content digest:
grep -nE 'image:\s*\S+@sha256:[0-9a-f]{64}' docker-compose.e2e.yml
# Guard: fail if any floating tag remains:
! grep -nE 'image:\s*\S+:(latest|alpine)\b' docker-compose.e2e.yml
```

**Verified-vs-extrapolated ledger for this plan:**

| Claim | Status |
|-------|--------|
| Repo SHA-pins GitHub Actions (`ci.yml:16`, commit `2c8039c`) | Verified (read locally) |
| "Therefore images should be digest-pinned" | Extrapolation (not the same convention) |
| CI `yamllint` covers only `configs/` (`ci.yml:24`) | Verified (read locally) |
| Chosen version tags exist / are not yanked | Unverified (no registry access) |
| `sha256` digests for the chosen tags | Unverified — `<RESOLVED_DIGEST>` placeholders only |
