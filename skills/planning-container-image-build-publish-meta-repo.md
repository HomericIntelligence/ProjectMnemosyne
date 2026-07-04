---
name: planning-container-image-build-publish-meta-repo
description: "Planning-phase risk checklist for designing a container-image BUILD + PUBLISH workflow (ghcr.io, docker/build-push-action, multi-arch) in a git-SUBMODULE META-REPO that owns only a handful of Dockerfiles while delegating app images to submodule repos. This is the DIFFERENT search surface a plan REVIEWER reaches for — 'are this image-publish plan's assumptions verified?' — distinct from the release-workflow planning skill (tags/CHANGELOG/semver) and from the image-DIGEST-PINNING skill (consuming :latest in compose). Core thesis: an image-publish plan is full of assertions that look like decisions but are unverified guesses — the docker/* action SHAs, the ghcr.io namespace casing, multi-arch buildability of every Dockerfile, and whether a new required-check job is ACTUALLY enforced. Use when: (1) reviewing or writing a plan that adds a `.github/workflows/image-publish.yml` building owned Dockerfiles and pushing to ghcr.io, (2) a plan hard-codes docker/setup-qemu-action / setup-buildx-action / login-action / metadata-action / build-push-action SHAs with version comments WITHOUT a fresh `gh api` lookup, (3) a plan writes `ghcr.io/<org>` namespace casing without confirming GHCR's lowercase requirement against a real published package, (4) a plan promises `platforms: linux/amd64,linux/arm64` but a target Dockerfile hard-codes an amd64-only vendor download URL (e.g. `*-linux-amd64.tar.gz`), (5) a plan adds a job to a canonical `_required.yml` but does NOT also update the branch-protection ruleset JSON, (6) a plan sets a new ADR Status to 'Accepted' when the repo's CLAUDE.md says new ADRs start 'Proposed', (7) a plan decides to build ONLY meta-repo-owned images vs ALL fleet/submodule images and that altitude call is asserted, not justified."
category: ci-cd
date: 2026-06-20
version: "1.1.0"
user-invocable: false
verification: unverified
history: planning-container-image-build-publish-meta-repo.history
tags:
  - planning
  - planning-methodology
  - container-images
  - image-publish
  - ghcr
  - docker-build-push
  - build-push-action
  - multi-arch
  - linux-arm64
  - qemu
  - buildx
  - meta-repo
  - git-submodules
  - third-party-action-sha
  - required-checks
  - branch-protection
  - canonical-checks
  - adr-status
  - proposed-vs-accepted
  - meta-repo-owned-vs-submodule-owned
  - dry-source-of-truth
  - verify-dont-assert
  - unverified-assumptions
  - ghcr-lowercase-namespace
  - dockerfile-arch-audit
  - re-planning
  - nogo-finding-resolution
  - attach-to-existing-mechanism
  - fixed-required-check-set
  - per-image-platforms-matrix
  - policy-test-assertions
  - open-decision-not-silent-narrowing
  - repo-verified-findings
---

# Container Image Build/Publish Planning: Assumptions & Risks (Submodule Meta-Repo)

## Overview

| Field | Value |
| ------- | ------- |
| **Date** | 2026-06-20 |
| **Objective** | Capture the durable PLANNING-PHASE risks surfaced while writing an implementation plan for Odysseus issue #201 ("No container image build or publish workflow") — a MINOR/DRY finding in a git-submodule meta-repo. The plan proposed an ADR (ghcr.io registry + tag scheme + promotion policy), a `.github/workflows/image-publish.yml` that builds ONLY the 3 e2e/test Dockerfiles Odysseus physically owns (delegating submodule app images to their own repos), a bash policy regression test, a `just` recipe, and per-PR enforcement. **R0** of the plan made several assertions that LOOKED like decisions but were unverified guesses. **R1** (this version) investigated each against the live Odysseus repo and RESOLVED them. |
| **R0 → R1** | R0 got a NOGO (Grade C; 3 Major + 2 minor). R1 closed every finding, each now backed by DIRECT repo inspection: (1) the central NOGO — "a new `_required.yml` job is not actually enforced" — was closed by folding the new validation as a STEP into the already-required `schema-validation` job (8 fixed fleet-wide contexts pinned with `integration_id: 15368`; ZERO ruleset-JSON edits); (2) multi-arch promised but `e2e/single-container/Dockerfile:43` hardcodes `nats-server-...-linux-amd64.tar.gz` → per-image `platforms` matrix; (3) action SHAs resolved in-session via `gh api`; (4) ADR ships `Status: Proposed` per `docs/adr/template.md:3`; (5) scope ambiguity surfaced as an explicit OPEN DECISION (Proposed ADR), not silently narrowed; (6) GHCR lowercase asserted via policy test. |
| **Outcome** | Findings are now REPO-VERIFIED by direct inspection — but the overall plan was STILL never executed end-to-end (no image built or pushed, no CI run). Be precise about the distinction: each *finding* is verified; the *plan outcome* is not. Verification therefore stays `unverified`. This skill is a reviewer/author checklist plus a plan-time verification cheat-sheet, not a verified procedure. |
| **Verification** | unverified |

> **Warning:** This workflow has not been validated end-to-end. Treat as a hypothesis until CI confirms.

## When to Use

Reach for this when REVIEWING or WRITING an image-build/publish plan for a submodule meta-repo and you need to separate *verified decisions* from *unverified guesses*. Specifically:

- The plan adds a **`.github/workflows/image-publish.yml`** that builds owned Dockerfiles and pushes to **ghcr.io**, and you need to know which of its choices are facts vs guesses.
- The plan **hard-codes docker/* action SHAs** — `docker/setup-qemu-action`, `docker/setup-buildx-action`, `docker/login-action`, `docker/metadata-action`, `docker/build-push-action` — with `# vX.Y.Z` version comments, but the SHAs were NOT confirmed with a fresh `gh api` lookup. Deferring verification "to implementation time" is NOT verification: a plan that presents an unverified SHA as if pinned is asserting a guess.
- The plan writes **`ghcr.io/<org>` namespace casing** (e.g. `ghcr.io/homericintelligence`) without confirming against a real published package. GHCR DOES lowercase org names, so lowercasing is correct — but "correct because I asserted it" is not the same as "confirmed against an existing `ghcr.io/<org>/<pkg>` package or the documented lowercasing rule". The actual org slug (`HomericIntelligence`) is mixed-case; the plan must SAY why lowercasing is safe.
- The plan promises **`platforms: linux/amd64,linux/arm64`** (multi-arch) but a target Dockerfile **hard-codes an amd64-only vendor download** (e.g. `nats-server-*-linux-amd64.tar.gz`). The build context + `submodules: recursive` may be correct, yet the arm64 leg will FAIL because the binary it downloads does not exist for arm64. Reading the Dockerfile is necessary but NOT sufficient — every `ADD`/`RUN curl|wget` of an arch-specific asset is a multi-arch landmine. (Cross-ref `[[ci-cd-achaean-fleet-ci-cascade-patterns]]` Level 6/8 — vendor download URL + OCI multi-arch — and `[[ci-cd-opencode-asset-arch-naming]]` for the `TARGETARCH`→asset-name mapping fix.)
- The plan adds a **new job to a canonical `_required.yml`** but only *flags* (does not perform) the branch-protection ruleset JSON + `canonical-checks.md` updates. A job named in `_required.yml` whose `name:` is NOT in the ruleset's pinned status-check contexts is SILENTLY non-blocking — the gate exists but never blocks a merge. (Same wiring trap as `[[release-workflow-planning-assumptions-and-risks]]` step 6 / `[[planning-verify-issue-premise-before-implementing]]`.)
- The plan sets a **new ADR Status to "Accepted"** when the repo's `CLAUDE.md` says new ADRs are "Proposed" until merged. A status-convention conflict is a reviewer nit that blocks merge; read the repo's ADR convention before stamping a status.
- The plan rests on a **meta-repo-altitude scoping judgment** — "fix #201 by building only the 3 images Odysseus owns, delegate submodule app images to their own repos" — that a reviewer may read differently (the issue's "submodule components" phrasing could be read as wanting submodule app images built here too). The altitude call must be JUSTIFIED (DRY: avoid dual sources of truth), not asserted.

## Proposed Workflow

> **Warning:** This workflow has not been validated end-to-end. Treat as a hypothesis until CI confirms.
>
> **Heading note:** The repository validator (`scripts/validate_plugins.py`) hard-requires the literal section string `## Verified Workflow`, so the canonical steps are emitted under that heading to keep validation green. This skill is a PLANNING methodology captured at `unverified` level. Read every step below as **proposed**, per the warning.

## Verified Workflow

> **Warning:** This workflow has not been validated end-to-end. Treat as a hypothesis until CI confirms.

### Quick Reference

Run these checks at PLAN time (or demand them as implementation acceptance criteria) before treating any of these assertions as a decision:

| # | Risky assertion in the plan | Verify-instead command / action | Fail signal | R1 RESOLUTION (repo-verified) |
| - | --------------------------- | -------------------------------- | ----------- | ----------------------------- |
| 1 | Hard-coded docker/* action SHAs with `# vX.Y.Z` comments | `gh api repos/docker/build-push-action/git/ref/tags/v6 --jq '.object.sha'` (and setup-qemu / setup-buildx / login / metadata) — resolve the tag to its current commit SHA AT PLAN TIME | The pinned SHA does not match the live tag's commit, or the tag does not exist → stale/yanked pin | Resolve each in-session (deref annotated tags via `.object.type==tag` → `git/tags/<sha>`); add a policy test that every `uses:` is a 40-hex SHA (reject `@vX` and short SHAs) |
| 2 | `ghcr.io/<org>` lowercase namespace | `git remote get-url origin` (real org casing) + confirm GHCR lowercases (docs) OR `gh api /orgs/<org>/packages?package_type=container` to see an existing published package's path | Plan asserts casing without any source; or an existing package uses a different path form | Assert `ghcr.io/homericintelligence` (lowercase) and reject the mixed-case org name in a policy test |
| 3 | `platforms: linux/amd64,linux/arm64` for every owned Dockerfile | `grep -nE 'amd64|x86_64|aarch64|arm64|TARGETARCH|uname -m' <Dockerfile>` for EACH built Dockerfile | Any hard-coded `*-linux-amd64.*` download with no `TARGETARCH` mapping → arm64 build fails | VERIFIED: `e2e/single-container/Dockerfile:43` hardcodes `nats-server-v2.10.24-linux-amd64.tar.gz`. Set `platforms` PER-IMAGE in the matrix (the two `python:3.11-slim` images → multi-arch; the amd64-binary image → `linux/amd64` only) + a policy test that the amd64-only image is never advertised arm64 |
| 4 | New required-check job added to `_required.yml` | `grep -n '<new-job-name>' configs/github/*ruleset*.json configs/github/canonical-checks.md` | Job `name:` absent from the ruleset JSON → check is silently non-blocking | VERIFIED: `canonical-checks.md` defines a FIXED fleet-wide set of EXACTLY 8 contexts; `repo-ruleset.json` pins those bare contexts with `integration_id: 15368`. Do NOT add a new "required" job — fold the validation as a STEP into the already-required `schema-validation` job (already validates `.github/workflows/*.yml` + ruleset JSON). ZERO ruleset edits; fleet uniformity preserved |
| 5 | New ADR Status = "Accepted" | `grep -niE 'Status.*Proposed|until merged|new ADR' CLAUDE.md docs/adr/template.md` | CLAUDE.md/template says "Proposed until merged" → "Accepted" violates convention | VERIFIED: `docs/adr/template.md:3` and `008-nats-tls-encryption.md:3` both use `**Status:** Proposed`. Ship new ADRs `Status: Proposed`; add a policy test asserting it |
| 6 | "Build only meta-repo-owned images" altitude call | `git submodule status` + read each owned Dockerfile's `COPY`/context; confirm submodule repos already build their own images | Submodule images already published elsewhere → building them here = dual source of truth (DRY) | Surface the altitude as an explicit OPEN DECISION (options A/B) recorded as a *Proposed* ADR for the issue author to ratify at merge — do NOT silently narrow scope |
| 7 | `context: .` + `submodules: recursive` for a Dockerfile that COPYs submodule paths | Read the Dockerfile's `COPY`/`ADD` sources; confirm checkout step uses `submodules: recursive` | Dockerfile COPYs a submodule path but checkout omits `submodules: recursive` → build can't find the path | Confirm `context: .` + `submodules: recursive` for the COPY-from-submodule Dockerfile; pair with the per-image multi-arch audit (row 3) |

**Plan-time verification command sequence** — run this exact block (or demand it as acceptance criteria) BEFORE pinning any SHA, promising multi-arch, or wiring a required check:

```bash
# (A) Re-resolve EVERY docker/* action tag to its current commit SHA at PLAN time.
# Do NOT carry a SHA from a skill/template/memory — re-look it up.
for ref in \
  "docker/setup-qemu-action:v3" \
  "docker/setup-buildx-action:v3" \
  "docker/login-action:v3" \
  "docker/metadata-action:v5" \
  "docker/build-push-action:v6"; do
  repo="${ref%%:*}"; tag="${ref##*:}"
  sha=$(gh api "repos/$repo/git/ref/tags/$tag" --jq '.object.sha' 2>/dev/null)
  # tag may be a lightweight tag (commit) or annotated (tag object) -> deref if needed:
  type=$(gh api "repos/$repo/git/ref/tags/$tag" --jq '.object.type' 2>/dev/null)
  if [ "$type" = "tag" ]; then sha=$(gh api "repos/$repo/git/tags/$sha" --jq '.object.sha'); fi
  echo "$repo@$sha   # $tag (resolved at plan time)"
done

# (B) GHCR namespace casing: confirm the real org slug + the lowercasing rule.
git remote get-url origin                 # real org casing (e.g. HomericIntelligence)
# GHCR lowercases owner+image: ghcr.io/<lowercased-org>/<image>. Confirm against a real package:
gh api "/orgs/<org>/packages?package_type=container" --jq '.[].name' 2>/dev/null || \
  echo "no container packages yet -> cite GHCR lowercasing docs explicitly, do not just assert"

# (C) Multi-arch audit: grep EVERY owned Dockerfile for arch-specific downloads.
for df in e2e/**/Dockerfile* testing/**/Dockerfile* ; do
  echo "== $df =="
  grep -nE 'amd64|x86_64|aarch64|arm64|TARGETARCH|TARGETPLATFORM|uname -m' "$df" || echo "  (no arch tokens)"
done
# A line like `nats-server-*-linux-amd64.tar.gz` with NO TARGETARCH mapping => arm64 build WILL FAIL.

# (D) Required-check wiring: a new _required.yml job is enforced ONLY if the ruleset pins its name.
NEWJOB="image-publish"   # whatever the plan names the job
grep -n "$NEWJOB" .github/workflows/_required.yml
grep -n "$NEWJOB" configs/github/*ruleset*.json configs/github/canonical-checks.md \
  || echo "ABSENT from rulesets -> SILENTLY non-blocking; plan MUST include the ruleset edit"

# (E) ADR status convention: read it; don't guess.
grep -niE 'Status|Proposed|Accepted|until merged' CLAUDE.md docs/adr/template.md

# (F) Altitude/scoping: confirm submodule repos own their own images (avoid DRY violation).
git submodule status
```

Two cross-cutting source-trust rules:

- **Re-verify third-party action SHAs at plan time, do not defer.** A plan that writes `docker/build-push-action@<sha> # v6` without having run `gh api repos/docker/build-push-action/git/ref/tags/v6` is presenting a guess as a pin. "Verify at implementation time" is a deferral, not a verification — the reviewer cannot tell a fresh SHA from a stale one, so the burden is on the plan to show the lookup.
- **Distinguish meta-repo-OWNED images from submodule-OWNED images.** Building a submodule's app image in the meta-repo creates a second source of truth for that image (the submodule's own CI builds it too) — a DRY violation. The meta-repo should build ONLY the Dockerfiles it physically owns (e2e/test harnesses) and delegate app images to the submodule repos that own them. State this altitude decision and its DRY justification explicitly; do not let it be an unspoken assumption.

### META-lesson: how a re-plan correctly closes a NOGO finding

A NOGO finding of the form **"the artifact you added doesn't actually achieve the stated effect"** (e.g. you added a job and called it "required", but it does not actually block merges) is best closed by **ATTACHING the new behavior to an EXISTING mechanism already known to have that effect** — NOT by building a parallel mechanism and asserting it works.

In Odysseus #201 the central R0 NOGO was exactly this: a new `image-validate` job in `_required.yml` is NOT actually required, because the branch-protection ruleset pins a FIXED fleet-wide set of EXACTLY 8 contexts (`configs/github/canonical-checks.md`) and `configs/github/repo-ruleset.json` pins precisely those 8 bare contexts with `"integration_id": 15368`. The required-set is a cross-repo CONTRACT, not a per-repo knob — every one of the 15 repos must emit the same 8. So the R1 resolution does NOT add a 9th "required" job; it folds the new validation as a STEP inside the already-required `schema-validation` job (which already runs `check-jsonschema` over `.github/workflows/*.yml` and `jq`-validates the ruleset JSON). This buys genuine per-PR enforcement with ZERO ruleset-JSON edits and preserves fleet uniformity.

The general rule has two halves:

1. **Before adding a "required" check, read the ruleset JSON + the canonical-checks doc** to learn whether the required-set is a fixed cross-repo contract. If it is, you cannot make something "required" by naming a new job — you must attach to a context that is already pinned.
2. **Add a verification command that PROVES the attachment.** It is not enough to claim the step is enforced; assert (a) the step lives INSIDE the already-required job, and (b) `configs/github/` is unchanged:

   ```bash
   # (a) the new validation runs inside the already-required `schema-validation` job:
   awk '/name: schema-validation/,/^  [a-z]/' .github/workflows/_required.yml | grep -n '<new-step-name>'
   # (b) prove no ruleset edits were needed (fleet contract untouched):
   git diff --quiet -- configs/github/ && echo "configs/github unchanged -> fleet contract preserved" \
     || echo "ERROR: ruleset/canonical-checks touched -> you broke fleet uniformity"
   ```

### Detailed Steps

**1. Re-resolve every docker/* action SHA at plan time — never defer, never copy from memory.**
The five canonical docker actions for a build/publish workflow are `docker/setup-qemu-action` (multi-arch emulation), `docker/setup-buildx-action` (the buildx builder), `docker/login-action` (GHCR auth), `docker/metadata-action` (tag/label generation), and `docker/build-push-action` (the build). Each must be pinned to a commit SHA, and that SHA must be resolved FROM the published tag at plan time:

```bash
gh api repos/docker/build-push-action/git/ref/tags/v6 --jq '.object.sha'
```

Annotated tags require a second deref (`git/tags/<sha>` → `.object.sha`). A `# v6` comment next to an un-looked-up SHA is theater; the reviewer cannot distinguish it from a yanked SHA.

**2. Treat GHCR namespace casing as a verification task.**
GHCR requires lowercase owner+image segments: `ghcr.io/<lowercased-org>/<image>`. The org `HomericIntelligence` lowercases to `homericintelligence`. Lowercasing IS correct — but cite the rule (GHCR docs) or an existing `ghcr.io/<org>/<pkg>` package, rather than asserting it. The trap is a plan that silently lowercases and a reviewer who cannot tell whether the author knew GHCR lowercases or just got lucky.

**3. Audit EVERY owned Dockerfile for arch-specific downloads, then set `platforms` PER-IMAGE.**
`platforms: linux/amd64,linux/arm64` only works if every layer is arch-portable. A Dockerfile that does `wget ... nats-server-vX-linux-amd64.tar.gz` downloads an amd64 binary unconditionally; under QEMU on the arm64 leg the resulting image contains an amd64 binary that won't execute (or the download 404s for a non-existent arm64 asset). Grep each built Dockerfile for `amd64|x86_64|aarch64|arm64|TARGETARCH|uname -m`. **VERIFIED in Odysseus:** of the three owned Dockerfiles, `e2e/nats-loki-bridge/Dockerfile` and `e2e/Dockerfile.argus-exporter` are pure-Python (`FROM python:3.11-slim`, multi-arch-capable), while `e2e/single-container/Dockerfile:43` hardcodes `nats-server-v2.10.24-linux-amd64.tar.gz` with no `TARGETARCH` mapping → its arm64 leg PROVABLY fails. RESOLUTION: do NOT promise one blanket `platforms` for all images — set `platforms` PER-IMAGE in the build matrix (pure-Python images → `linux/amd64,linux/arm64`; the amd64-binary image → `linux/amd64` only) and add a policy-test assertion that the amd64-only image is never advertised arm64. (Alternative for a portable image: a `TARGETARCH`→asset-name mapping — see `[[ci-cd-opencode-asset-arch-naming]]` and `[[ci-cd-achaean-fleet-ci-cascade-patterns]]` Levels 7/8 — but only if the upstream actually publishes a linux-arm64 asset.)

**4. Attach the new validation to an ALREADY-required job; do not add a new "required" job.**
**VERIFIED in Odysseus:** `configs/github/canonical-checks.md` defines a FIXED fleet-wide set of EXACTLY 8 required check contexts (`lint`, `unit-tests`, `integration-tests`, `security/dependency-scan`, `security/secrets-scan`, `build`, `schema-validation`, `deps/version-sync`) that all 15 fleet repos must emit, and `configs/github/repo-ruleset.json` pins exactly those 8 BARE contexts with `"integration_id": 15368` (the `org-ruleset*.json` variants pin `"Required Checks / <name>"`). The required-set is a cross-repo CONTRACT, so a new `_required.yml` job whose `name:` is not in that fixed set runs but NEVER blocks a merge — and editing the ruleset to add a 9th context would break fleet uniformity. RESOLUTION: do NOT add a new "required" job for a repo-local policy check — fold the new image-publish validation as a STEP into the already-required `schema-validation` job (it already runs `check-jsonschema` over `.github/workflows/*.yml` and `jq`-validates the ruleset JSON, so an image-publish policy test is a natural fit). This gives genuine per-PR enforcement with ZERO ruleset-JSON edits. Prove it with `awk '/name: schema-validation/,/^  [a-z]/' .github/workflows/_required.yml | grep '<new-step>'` AND `git diff --quiet -- configs/github/`.

**5. Respect the ADR status convention from the repo's CLAUDE.md.**
Odysseus `CLAUDE.md` says new ADRs use Status "Proposed" until merged (superseding decisions get a new ADR; ADRs are append-only). **VERIFIED:** `docs/adr/template.md:3` and the latest real ADR `docs/adr/008-nats-tls-encryption.md:3` both literally read `**Status:** Proposed`. A plan that stamps a new ADR "Accepted" before merge violates the convention — a merge-blocking nit. RESOLUTION: ship the new ADR with `Status: Proposed`, and add a policy test asserting any ADR added by this change carries `**Status:** Proposed`.

**6. Resolve scope ambiguity as an explicit OPEN DECISION, not by silently narrowing.**
Issue #201's "build images for submodule components" phrasing is ambiguous: build only the 3 meta-repo-owned Dockerfiles, or build all fleet/submodule app images here too? Meta-repo altitude (build only owned images, DRY-delegate the rest) is defensible — building a submodule's image here duplicates the submodule's own CI build = a second source of truth — but it is a JUDGMENT call the issue author may read differently. RESOLUTION: do NOT present a unilateral reinterpretation as settled. Lay out options A (owned only) / B (all fleet images) in the plan and record the chosen option as a *Proposed* ADR decision for the issue author to ratify at merge. Surfacing the ambiguity beats silently narrowing scope.

**7. Confirm build context + `submodules: recursive` for any Dockerfile that COPYs submodule paths.**
The single-container e2e Dockerfile COPYs from submodule paths, so its build context must be the repo root and the checkout step must use `submodules: recursive` (and `build-push-action` `context: .`). This was VERIFIED by reading the Dockerfile — but reading proves the COPY paths, not that the build succeeds. Pair the context check with the per-image multi-arch audit (step 3): a correct context does not save the amd64-only NATS download on the arm64 leg.

**8. Encode every finding as a fast, deterministic policy test wired into `schema-validation`.**
Because the enforcement mechanism is the already-required `schema-validation` job (step 4), each repo-verified finding should become an assertion the policy test runs on every PR — no network, no actual build needed:
- every `uses:` in `image-publish.yml` is a 40-hex commit SHA (reject `@vX` and short SHAs);
- the registry namespace is the lowercase `ghcr.io/homericintelligence` (reject the mixed-case org slug);
- the amd64-only image (`single-container`) is never listed with `linux/arm64` in the `platforms` matrix;
- any newly added ADR carries `**Status:** Proposed`.
These assertions are what convert the R1 *findings* into *enforced invariants* — but note this is still plan-stage: the workflow has not been run, so verification stays `unverified`.

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
| --------- | ---------------- | --------------- | ---------------- |
| Pin docker/* action SHAs and defer verification | The plan wrote `docker/setup-qemu-action@<sha> # v3`, `docker/setup-buildx-action@<sha> # v3`, `docker/login-action@<sha> # v3`, `docker/metadata-action@<sha> # v5`, `docker/build-push-action@<sha> # v6` and DEFERRED confirming the SHAs to implementation time | A deferred verification is not a verification — the reviewer cannot distinguish a fresh pin from a stale/yanked one; the plan presents guesses as decisions | RESOLUTION: re-resolve EVERY action tag at plan time with `gh api repos/<owner>/<repo>/git/ref/tags/<tag> --jq '.object.sha'` (deref annotated tags via `git/tags/<sha>`). Never present a `# vX` comment next to an un-looked-up SHA; never carry a SHA from a skill/template/memory |
| Assert `ghcr.io/homericintelligence` lowercase casing | The plan lowercased the org slug (`HomericIntelligence` → `homericintelligence`) and used `ghcr.io/homericintelligence/<image>` as fact | GHCR DOES lowercase, so the result is correct — but it was ASSERTED, not confirmed against the GHCR lowercasing rule or an existing published package; "right by luck" is indistinguishable from "right by verification" to a reviewer | RESOLUTION: confirm the real org slug with `git remote get-url origin`, then cite GHCR's documented lowercasing OR an existing `ghcr.io/<org>/<pkg>` package (`gh api /orgs/<org>/packages?package_type=container`). State WHY lowercasing is safe |
| Promise linux/arm64 for a Dockerfile that hard-codes an amd64 tarball | The plan set `platforms: linux/amd64,linux/arm64` for all 3 owned images, including the single-container e2e Dockerfile, having only READ the Dockerfile (confirming its COPY paths) — the build was never run | The single-container Dockerfile hard-codes `nats-server-*-linux-amd64.tar.gz` with no `TARGETARCH` mapping; the arm64 leg downloads a non-portable/absent binary and the build BREAKS. Reading proves COPY paths, not arm64 buildability | RESOLUTION: grep EVERY built Dockerfile for `amd64\|x86_64\|aarch64\|arm64\|TARGETARCH\|uname -m`. Any unconditional `*-linux-amd64.*` download is a multi-arch landmine — fix with a `TARGETARCH`→asset mapping (`[[ci-cd-opencode-asset-arch-naming]]`) or drop arm64 for that image and document the single-arch exception. Cross-ref `[[ci-cd-achaean-fleet-ci-cascade-patterns]]` Level 6/8 |
| Add an `image-publish` job to `_required.yml` and only FLAG the ruleset edit | The plan added a new required-checks job to the canonical `_required.yml` and noted that the branch-protection ruleset JSON + `canonical-checks.md` "must be updated" — but did NOT include those edits | A job in `_required.yml` whose `name:` is absent from the rulesets' pinned status-check contexts runs but never blocks a merge — the gate is SILENTLY non-blocking. Flagging an edit is not making it | RESOLUTION: the plan must EITHER include the `configs/github/*ruleset*.json` + `canonical-checks.md` edits OR attach the new step to an already-pinned job. Verify with `grep -n '<job-name>' configs/github/*ruleset*.json`. Required-check status is conferred by the ruleset pin, not by the job existing in `_required.yml` |
| Set ADR-009 Status to "Accepted" pre-merge | The plan stamped the new ADR Status as "Accepted" immediately | The repo's `CLAUDE.md` says new ADRs are "Proposed" until merged (ADRs are append-only; superseding decisions get a new ADR). "Accepted" pre-merge violates the documented convention — a merge-blocking nit | RESOLUTION: read `CLAUDE.md` + `docs/adr/template.md` and set Status to "Proposed" until the ADR is merged. Respect the repo's ADR-status convention |
| Assume meta-repo-altitude scoping (3 owned images only) without justification | The whole plan rested on "fix #201 at the meta-repo altitude — build only the 3 owned Dockerfiles, delegate submodule app images" without making the DRY reasoning explicit | The issue's "submodule components" phrasing is ambiguous; a reviewer could read it as wanting submodule app images built in the meta-repo too. An unjustified altitude call is a judgment a reviewer may simply reject | RESOLUTION (R1): do NOT silently narrow scope. Surface the ambiguity as an explicit OPEN DECISION (options A: owned-only / B: all fleet images) and record the chosen option as a *Proposed* ADR for the issue author to ratify at merge. State the DRY justification (building a submodule's image here = a second source of truth) so the reviewer can agree or dispute it on the merits |
| R1: close the "not actually required" NOGO by adding a 2nd "required" job | In R0 the plan added a NEW `image-validate` job to `_required.yml` and called the gate "required"; the obvious R1 reflex is to also pin a 9th context in the ruleset JSON | VERIFIED: `configs/github/canonical-checks.md` defines a FIXED fleet-wide set of EXACTLY 8 required contexts and `repo-ruleset.json` pins exactly those 8 bare contexts with `integration_id: 15368`. The required-set is a cross-repo CONTRACT — adding a 9th context breaks fleet uniformity across all 15 repos, and a job not in the set never blocks merges | RESOLUTION (R1 + META-lesson): when a NOGO says "the artifact you added doesn't achieve the stated effect (enforced)", ATTACH the new behavior to an EXISTING mechanism already known to have that effect rather than building a parallel one. Fold the image-publish validation as a STEP into the already-required `schema-validation` job (it already validates workflow YAML + ruleset JSON). Genuine per-PR enforcement, ZERO ruleset edits, fleet contract preserved |
| R1: claim "multi-arch works now" with one blanket `platforms` for all images | R1 reflex after the R0 arm64 break: set `platforms: linux/amd64,linux/arm64` once for the whole build | Two of the three owned images (`python:3.11-slim`) ARE multi-arch-capable, but `e2e/single-container/Dockerfile:43` hardcodes `nats-server-...-linux-amd64.tar.gz` (no `TARGETARCH`) and still breaks on arm64. A single blanket `platforms` re-introduces the same break for one image | RESOLUTION (R1): set `platforms` PER-IMAGE in the build matrix (pure-Python → multi-arch; the amd64-binary image → `linux/amd64` only) and add a policy test asserting the amd64-only image is never advertised arm64. Audit EVERY Dockerfile's download URLs, not just the base image |
| R1: treat the now-verified findings as if the PLAN is verified | After resolving all 6 findings by direct repo inspection, the temptation is to upgrade `verification` to verified-local/verified-ci | The findings are repo-verified by inspection, but the PLAN was still never executed end-to-end — no image was built or pushed and no CI run exercised the workflow. Verified findings ≠ verified plan | RESOLUTION (honesty gate): keep `verification: unverified`. Be precise in the Overview/notes: each FINDING is repo-verified; the plan OUTCOME is not. Only a green CI run that builds+pushes the images would justify upgrading the level |

## Results & Parameters

This skill produced no execution results (it is `unverified` — no image was built or pushed). What it produces is a plan-time verification cheat-sheet for an image-build/publish workflow in a submodule meta-repo, plus the reusable snippets that resolve each risk. In R1 each finding was VERIFIED by direct Odysseus inspection (the PLAN remains unverified — never run end-to-end).

**R1 repo-verified evidence (Odysseus @ main):**

| Finding | Evidence (file:line / command output) |
| ------- | ------------------------------------- |
| Fixed 8-context required-set is a fleet contract | `configs/github/canonical-checks.md` "Required checks" table lists exactly 8: `lint`, `unit-tests`, `integration-tests`, `security/dependency-scan`, `security/secrets-scan`, `build`, `schema-validation`, `deps/version-sync` |
| Ruleset pins exactly those 8 bare contexts | `configs/github/repo-ruleset.json` lines 29–36: each is `{ "context": "<name>", "integration_id": 15368 }`; `org-ruleset*.json` use `"Required Checks / <name>"` |
| `schema-validation` is the natural attach point | `.github/workflows/_required.yml` job `name: schema-validation` already runs `check-jsonschema` over `find .github/workflows -name "*.yml"` AND `jq`-validates the four `configs/github/*ruleset*.json` files |
| amd64-only image break | `e2e/single-container/Dockerfile:43` → `nats-server-v2.10.24-linux-amd64.tar.gz` (no `TARGETARCH`); base `FROM ubuntu:24.04` |
| Multi-arch-capable images | `e2e/nats-loki-bridge/Dockerfile:1` and `e2e/Dockerfile.argus-exporter:1` both `FROM python:3.11-slim` |
| ADR status convention | `docs/adr/template.md:3` and `docs/adr/008-nats-tls-encryption.md:3` both `**Status:** Proposed`; `CLAUDE.md` mandates Proposed-until-merged |

**Per-image `platforms` matrix (do NOT use one blanket `platforms`):**

```yaml
strategy:
  matrix:
    include:
      - image: nats-loki-bridge
        dockerfile: e2e/nats-loki-bridge/Dockerfile      # FROM python:3.11-slim -> portable
        platforms: linux/amd64,linux/arm64
      - image: argus-exporter
        dockerfile: e2e/Dockerfile.argus-exporter        # FROM python:3.11-slim -> portable
        platforms: linux/amd64,linux/arm64
      - image: single-container
        dockerfile: e2e/single-container/Dockerfile       # hardcodes linux-amd64 NATS tarball
        platforms: linux/amd64                            # amd64 ONLY — never advertise arm64
```

**Proof-of-attachment commands (the META-lesson verification — run at plan/PR time):**

```bash
# The new validation MUST live inside the already-required schema-validation job:
awk '/name: schema-validation/,/^  [a-z]/' .github/workflows/_required.yml | grep -n 'image-publish'
# And NO ruleset/canonical-checks edits were needed (fleet contract preserved):
git diff --quiet -- configs/github/ \
  && echo "configs/github unchanged -> fleet contract preserved" \
  || echo "ERROR: ruleset touched -> fleet uniformity broken"
```

**Plan-time action-SHA resolution (run for ALL five docker actions; never defer):**

```bash
resolve_action_sha() {  # usage: resolve_action_sha docker/build-push-action v6
  local repo="$1" tag="$2"
  local obj; obj=$(gh api "repos/$repo/git/ref/tags/$tag" --jq '{type:.object.type,sha:.object.sha}')
  local type sha
  type=$(echo "$obj" | gh api --jq '.type' 2>/dev/null || python3 -c "import sys,json;print(json.load(sys.stdin)['type'])" <<<"$obj")
  sha=$(python3 -c "import sys,json;print(json.load(sys.stdin)['sha'])" <<<"$obj")
  if [ "$type" = "tag" ]; then sha=$(gh api "repos/$repo/git/tags/$sha" --jq '.object.sha'); fi
  echo "uses: $repo@$sha   # $tag"
}
resolve_action_sha docker/setup-qemu-action  v3
resolve_action_sha docker/setup-buildx-action v3
resolve_action_sha docker/login-action       v3
resolve_action_sha docker/metadata-action    v5
resolve_action_sha docker/build-push-action  v6
```

**Multi-arch Dockerfile audit (any hit on an unconditional amd64 download is a NOGO for arm64):**

```bash
# Run for every Dockerfile the workflow will build.
for df in e2e/single-container/Dockerfile e2e/*/Dockerfile testing/**/Dockerfile; do
  [ -f "$df" ] || continue
  echo "== $df =="
  grep -nE 'amd64|x86_64|aarch64|arm64|TARGETARCH|TARGETPLATFORM|uname -m' "$df" \
    || echo "  (no arch tokens — likely portable, but confirm base image is multi-arch)"
done
# Example landmine line: ADD https://.../nats-server-v2.10.0-linux-amd64.tar.gz /tmp/
#   -> no TARGETARCH mapping -> arm64 leg gets an amd64 binary / 404 -> build FAILS.
```

**`TARGETARCH`→asset mapping fix (the portable form; see `[[ci-cd-opencode-asset-arch-naming]]`):**

```dockerfile
ARG TARGETARCH
RUN case "$TARGETARCH" in \
      amd64) NATS_ARCH=amd64 ;; \
      arm64) NATS_ARCH=arm64 ;; \
      *) echo "unsupported arch: $TARGETARCH" >&2; exit 1 ;; \
    esac; \
    curl -fsSL "https://github.com/nats-io/nats-server/releases/download/v2.10.0/nats-server-v2.10.0-linux-${NATS_ARCH}.tar.gz" \
      -o /tmp/nats.tar.gz
# NOTE: confirm the upstream actually publishes a linux-arm64 asset for this version
# before mapping it — some vendors ship amd64 only (then drop arm64 + document it).
```

**Required-check wiring proof (a `_required.yml` job is enforced ONLY if a ruleset pins its name):**

```bash
NEWJOB="image-publish"
grep -n "$NEWJOB" .github/workflows/_required.yml            # job exists in the workflow
grep -n "$NEWJOB" configs/github/*ruleset*.json              # job NAME pinned as a status context?
grep -n "$NEWJOB" configs/github/canonical-checks.md         # documented?
# If the last two are empty: the check runs but DOES NOT BLOCK merges.
# The plan must include the ruleset + canonical-checks edits, or attach the step to a pinned job.
```

**GHCR namespace + login skeleton (lowercase owner; cite the rule, don't assert):**

```yaml
# org HomericIntelligence -> ghcr.io/homericintelligence/<image>  (GHCR lowercases owner+image)
env:
  REGISTRY: ghcr.io
  # Use ${{ github.repository_owner }} lowercased so casing is derived, not hand-typed:
permissions:
  contents: read
  packages: write          # required to push to GHCR
steps:
  - uses: docker/login-action@<resolved-sha>   # see resolve_action_sha
    with:
      registry: ghcr.io
      username: ${{ github.actor }}
      password: ${{ secrets.GITHUB_TOKEN }}
  - name: lowercase owner
    run: echo "OWNER_LC=${GITHUB_REPOSITORY_OWNER,,}" >> "$GITHUB_ENV"   # derive casing
```

**Reviewer focus list (the risks, condensed):** (1) every docker/* action SHA re-resolved at plan time via `gh api`, never deferred; (2) ghcr.io namespace lowercasing cited (docs or existing package), not asserted; (3) every owned Dockerfile audited for arch-specific downloads before promising linux/arm64 — the single-container NATS amd64 tarball BREAKS arm64; (4) any new `_required.yml` job ALSO pinned in `configs/github/*ruleset*.json` (else silently non-blocking) — the ruleset edit must be IN the plan, not just flagged; (5) ADR Status = "Proposed" per CLAUDE.md, not "Accepted" pre-merge; (6) build only meta-repo-OWNED Dockerfiles, delegate submodule app images to their own repos (DRY), and JUSTIFY the altitude; (7) `context: .` + `submodules: recursive` confirmed for Dockerfiles that COPY submodule paths.

## Related Skills

- `[[release-workflow-planning-assumptions-and-risks]]` — the planning-risk counterpart for tag-triggered RELEASE workflows (versions/CHANGELOG/semver/signing). Shares the third-party-action-SHA and required-check-wiring traps; this skill is the IMAGE-build/publish counterpart.
- `[[ci-cd-achaean-fleet-ci-cascade-patterns]]` — the verified-ci IMPLEMENTATION cascade for Docker image builds (Level 6/8 = vendor download URL + OCI multi-arch). This skill is the plan-stage counterpart for those same failure classes.
- `[[gha-release-package-workflow-patterns]]` — implementation mechanics of release.yml / package publication.
- `[[ci-cd-opencode-asset-arch-naming]]` — the `TARGETARCH`→asset-name mapping fix for arch-specific vendor downloads.
- `[[planning-container-image-digest-pinning]]` — the CONSUMING side: pinning floating image tags in compose/e2e to immutable digests (distinct from building/publishing images).
- `[[planning-verify-issue-premise-before-implementing]]` — adjacent planning skill on required-check gating and verifying issue claims.
