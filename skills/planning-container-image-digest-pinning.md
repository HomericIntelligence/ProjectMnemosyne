---
name: planning-container-image-digest-pinning
description: "Planning-discipline for pinning floating container image tags (:latest, :alpine) in a Compose/e2e stack to immutable name:vX.Y.Z@sha256:<digest> references for reproducibility — WHAT a planner can and cannot verify offline. Use when: (1) planning a fix for an issue like ':latest image tags break reproducibility' in a docker-compose/e2e file, (2) you are about to write specific upstream version tags and sha256 digests into a plan without registry access, (3) you need to choose between pinning a multi-arch manifest-list digest vs a single-arch image digest, (4) you are tempted to cite an existing Actions SHA-pin convention as proof that container images should be digest-pinned, or to rely on `compose config` as the acceptance check."
category: ci-cd
date: 2026-06-20
version: "1.1.0"
user-invocable: false
verification: unverified
history: planning-container-image-digest-pinning.history
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
  - ci-wiring
  - plan-review
---

# Planning a Container-Image Digest-Pinning Fix: What a Planner Can (and Cannot) Verify Offline

## Overview

| Field | Value |
|-------|-------|
| **Date** | 2026-06-20 |
| **Objective** | Produce a PLAN (not an implementation) for Odysseus issue #188 "[MAJOR] E2E compose stack uses :latest image tags": pin `prom/prometheus:latest`, `grafana/loki:latest`, `grafana/grafana:latest` in `docker-compose.e2e.yml` to immutable `name:vX.Y.Z@sha256:<digest>` references and add a guard script. |
| **Outcome** | PLAN ONLY — never executed. The durable learning is planning discipline: a planner with no registry access must defer every digest/version choice to implementation time with explicit resolution commands, and must distinguish what was verified from what was extrapolated. |
| **Verification** | unverified (plan only — no registry was queried, no `compose up`/CI ran; the local `grep`/file inspections of the repo WERE run and are real) |
| **History** | [changelog](./planning-container-image-digest-pinning.history) |

> **Warning:** This workflow has not been validated end-to-end. Treat as a hypothesis until CI confirms.

**History:** [changelog](./planning-container-image-digest-pinning.history)

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
# PRIMARY (CORRECT): resolve the REGISTRY-CANONICAL multi-arch manifest-LIST digest:
skopeo inspect --format '{{.Digest}}' docker://docker.io/prom/prometheus:v2.55.1
# FALLBACK (also correct — returns the manifest-list digest):
docker buildx imagetools inspect --format '{{.Manifest.Digest}}' prom/prometheus:v2.55.1
# WRONG — do NOT use: `podman manifest inspect ... | sha256sum` hashes the JSON TEXT,
# not the registry digest, and silently yields a @sha256: that pulls nothing.

# --- AUTHORITATIVE, tooling/env-INDEPENDENT acceptance check: every image digest-pinned ---
grep -nE 'image:\s*\S+@sha256:[0-9a-f]{64}' docker-compose.e2e.yml   # must match each pinned line
# Guard-script regex to reject any remaining floating tag (WHOLE-FILE):
grep -nE 'image:\s*\S+:(latest|alpine)\b|image:\s*[^@[:space:]]+:[^@[:space:]]+$' docker-compose.e2e.yml

# --- Wire the guard into CI in the SAME change, then PROVE the wiring exists: ---
# add `bash scripts/check_e2e_image_pins.sh` as a step in the `validate` job of ci.yml,
# right after the YAML-lint step, then verify:
grep -n 'check_e2e_image_pins.sh' .github/workflows/ci.yml   # MUST return a hit

# --- Confirm the chosen tag actually EXISTS / is not yanked before pinning ---
skopeo inspect docker://docker.io/grafana/grafana:11.4.0 >/dev/null && echo "tag exists"
```

### Detailed Steps

1. **Mark every version + digest as "verify against registry at implementation time."** With no registry access, the planner cannot know the real digest. Write the version tag as a candidate and use a literal `<RESOLVED_DIGEST>` placeholder; provide the exact `skopeo inspect --format '{{.Digest}}'` command that the implementer must run. NEVER paste a plausible-looking 64-hex string — a guessed digest will pin a wrong/nonexistent image.
2. **Treat the chosen version tag as unconfirmed too.** A tag may be EOL/yanked or simply not exist. The implementer must `skopeo inspect docker://.../<repo>:<tag>` to confirm existence, and should prefer a maintained LTS line over the newest tag.
3. **Pin the multi-arch manifest-LIST digest, not a single-arch image digest.** `name@sha256:<digest>` can pin either. A single-platform digest breaks contributors on a different CPU arch (arm64 vs amd64). `skopeo inspect --format '{{.Digest}}' docker://<repo>:<tag>` and `docker buildx imagetools inspect --format '{{.Manifest.Digest}}'` return the manifest-list digest — use those. Call this out explicitly in the plan.
4. **State verified-vs-extrapolated precisely when citing precedent.** Verified: the repo SHA-pins GitHub **Actions** (commit `2c8039c`, `ci.yml:16`). Extrapolation: "therefore container images should be digest-pinned." Actions are pinned by **git commit SHA**, images by **registry content digest** — related convention, not the same one. Do not present the extrapolation as a verified fact.
5. **Wire the guard into CI in the SAME change, or drop it — a guard nothing runs is decorative (P3/TDD gap).** A guard a contributor must remember to run gives ZERO regression protection: the exact `:latest` regression it is meant to stop sails through CI. Verified here: CI's `yamllint` only covers `configs/` (`ci.yml:24`), so a `docker-compose.e2e.yml` regression is NOT caught. The plan MUST add the guard as a step in an existing CI job (here: the `validate` job of `.github/workflows/ci.yml`, right after the YAML-lint step, running `bash scripts/check_e2e_image_pins.sh`) and include a VERIFICATION step that greps the CI file to prove it (`grep -n 'check_e2e_image_pins.sh' .github/workflows/ci.yml`) — not merely that the script file exists. A reviewer treats a centerpiece guard that does not run in CI as a MAJOR finding (forces NOGO).
6. **Lead with the CORRECT digest command; mark the broken one as wrong, not as an alternative (P7/POLA).** An implementer follows steps top-to-bottom and hits the first-listed command. The PRIMARY/first command must be the correct one: `skopeo inspect --format '{{.Digest}}' docker://docker.io/<ref>` (fallback `docker buildx imagetools inspect --format '{{.Manifest.Digest}}'`). `podman manifest inspect ... | sha256sum` is factually broken — it hashes the manifest JSON TEXT, not the registry-canonical digest, silently yielding a `@sha256:` that pulls nothing. Never present a known-broken command as the default path even when a correct alternative is mentioned nearby; explicitly label the wrong approach as wrong. A wrong-as-written command is a MAJOR finding.
7. **Resolve the whole-file-guard vs scoped-issue tension explicitly.** A digest-presence guard scoped to ALL `image:` lines will also flag images outside the issue evidence (here `nats:alpine` at `docker-compose.e2e.yml:14`). Two coherent choices: (a) scope the guard to only the issue's services, or (b) make the guard whole-file AND pin the extra in-file image too. A half-guarded file invites the very regression you are preventing — prefer the whole-file guard + pin the extra in-file image, and RECORD the scope decision. Cross-file out-of-scope items (e.g. `nats:latest` in `e2e/docker-compose.cluster.yml:12,25`) stay out of scope; the guard's blast radius may legitimately expand scope WITHIN the same file but not across files.
8. **Name the `@sha256:[0-9a-f]{64}` grep as the authoritative gate; label `compose config` "best-effort, NOT a gate."** `podman compose -f ... config` resolves env-var interpolation (`${PROJECT_ROOT}`, `${ARGUS_DIR}`, `${HERMES_DIR}`, `${MYRMIDONS_DIR}`, ...) and can fail offline on unset vars for reasons unrelated to the pin; `podman compose` also delegates to the docker-compose plugin and may not pin-validate. The tooling/env-independent `grep` for `@sha256:[0-9a-f]{64}` is the AUTHORITATIVE acceptance check; if you keep `compose config`, supply the required env vars and mark it best-effort.
9. **Self-audit for the two cheapest MAJORs before submitting (verdict-floor mechanics).** A single MAJOR forces NOGO regardless of otherwise A-grade requirements-alignment/concreteness/scope; two majors here (decorative guard + broken primary command) dropped an otherwise strong plan to grade C. Before submitting, audit for (1) a centerpiece deliverable that does not actually run, and (2) a command/step that is wrong as written — these are the two cheapest majors to self-catch.

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
| Guard script added but not wired into CI (R1 plan-review) | Ran `scripts/check_e2e_image_pins.sh` only locally / deferred CI wiring as out-of-scope | A guard a contributor must remember to run gives zero regression protection; the exact `:latest` regression sails through CI — reviewer flagged MAJOR (forces NOGO) | Wire any new guard into an existing CI job in the SAME change (here: a step in the `validate` job of `.github/workflows/ci.yml` after the YAML-lint step), and `grep -n 'check_e2e_image_pins.sh' .github/workflows/ci.yml` in verification to PROVE the wiring — not just that the script exists. |
| Listed `podman manifest inspect \| sha256sum` as the PRIMARY digest command (R1 plan-review) | Presented it first, with skopeo as a parenthetical "prefer if available" | It hashes the manifest JSON TEXT, not the registry digest → a garbage `@sha256:` that pulls nothing; an implementer following steps top-to-bottom hits the wrong command first — reviewer flagged MAJOR | Make the CORRECT command (`skopeo inspect --format '{{.Digest}}'`, fallback `docker buildx imagetools inspect --format '{{.Manifest.Digest}}'`) the PRIMARY/first one; mark the broken approach as wrong, never as an alternative. |
| Whole-file guard flags an out-of-scope in-file image (R1 plan-review) | Guard regex matched `nats:alpine` (`docker-compose.e2e.yml:14`) outside the issue evidence | Either the guard or the scope is inconsistent — a half-guarded file invites the very regression you are preventing | Prefer the whole-file guard + pin the extra in-file image, and RECORD the scope decision explicitly; cross-file items (`e2e/docker-compose.cluster.yml`) stay out of scope. The guard's blast radius may expand scope within the same file only. |
| Relied on `podman compose config` as the acceptance gate (R1 plan-review) | Used `podman compose -f docker-compose.e2e.yml config` to prove the pin is valid | Fails offline on unset `${PROJECT_ROOT}`/`${ARGUS_DIR}`/`${HERMES_DIR}`/`${MYRMIDONS_DIR}` for reasons unrelated to the pin | The `@sha256:[0-9a-f]{64}` grep is the AUTHORITATIVE, env-independent gate; label `compose config` "best-effort, NOT a gate" (supply the env vars if you keep it). |
| Submitted a plan with a centerpiece that does not run + a wrong command (R1 plan-review) | Trusted otherwise A-grade alignment/concreteness/scope to carry the plan | A single MAJOR forces NOGO regardless; two majors (decorative guard + broken primary command) dropped an A-strong plan to grade C | Before submitting, self-audit for the two cheapest majors: (1) a centerpiece deliverable that does not actually run, (2) a command/step that is wrong as written. |

## Results & Parameters

**Issue:** Odysseus #188 "[MAJOR] E2E compose stack uses :latest image tags" — PLAN ONLY, not implemented.

**Target file & images in scope** (`docker-compose.e2e.yml`):

```text
prom/prometheus:latest   -> prom/prometheus:vX.Y.Z@sha256:<RESOLVED_DIGEST>
grafana/loki:latest      -> grafana/loki:X.Y.Z@sha256:<RESOLVED_DIGEST>
grafana/grafana:latest   -> grafana/grafana:X.Y.Z@sha256:<RESOLVED_DIGEST>
```

Candidate versions (UNVERIFIED — confirm at implementation time): Prometheus v2.55.1, Loki 3.3.2, Grafana 11.4.0. Prefer a maintained LTS line; do not paste these into the manifest without `skopeo inspect`-confirming both the tag and the manifest-list digest.

**Scope decision (R1 refinement):** prefer a WHOLE-FILE guard, so also pin the extra in-file image `nats:alpine` (`docker-compose.e2e.yml:14`) in the same change and record the decision. **Out of scope (cross-file, documented, not changed):** `nats:latest` (`e2e/docker-compose.cluster.yml:12,25`).

**Resolution commands (implementation time) — PRIMARY first, broken one marked:**

```bash
# CORRECT (primary):
skopeo inspect --format '{{.Digest}}' docker://docker.io/<repo>:<tag>
# CORRECT (fallback):
docker buildx imagetools inspect --format '{{.Manifest.Digest}}' <repo>:<tag>
# WRONG — never use: `podman manifest inspect <repo>:<tag> | sha256sum` (hashes JSON text, not the registry digest).
```

**Acceptance check (authoritative, tooling/env-independent):**

```bash
# Every image line must carry a 64-hex content digest (THE gate):
grep -nE 'image:\s*\S+@sha256:[0-9a-f]{64}' docker-compose.e2e.yml
# Guard: fail if any floating tag remains (whole-file):
! grep -nE 'image:\s*\S+:(latest|alpine)\b' docker-compose.e2e.yml
# `podman compose -f docker-compose.e2e.yml config` is best-effort only, NOT a gate
# (fails offline on unset ${PROJECT_ROOT}/${ARGUS_DIR}/${HERMES_DIR}/${MYRMIDONS_DIR}).
```

**CI wiring (REQUIRED in the same change — a guard nothing runs is decorative):**

```bash
# Add to the `validate` job of .github/workflows/ci.yml, after the YAML-lint step:
#   - run: bash scripts/check_e2e_image_pins.sh
# Then PROVE the wiring exists (must return a hit):
grep -n 'check_e2e_image_pins.sh' .github/workflows/ci.yml
```

**Verified-vs-extrapolated ledger for this plan:**

| Claim | Status |
|-------|--------|
| Repo SHA-pins GitHub Actions (`ci.yml:16`, commit `2c8039c`) | Verified (read locally) |
| "Therefore images should be digest-pinned" | Extrapolation (not the same convention) |
| CI `yamllint` covers only `configs/` (`ci.yml:24`) | Verified (read locally) |
| Chosen version tags exist / are not yanked | Unverified (no registry access) |
| `sha256` digests for the chosen tags | Unverified — `<RESOLVED_DIGEST>` placeholders only |
