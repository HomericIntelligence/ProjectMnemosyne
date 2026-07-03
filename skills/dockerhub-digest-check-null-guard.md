---
name: dockerhub-digest-check-null-guard
description: "Correctly fetch and compare Docker Hub tag digests in CI digest-pin checkers. CRITICAL: jq -r on an error JSON prints the STRING 'null', which passes [ -z ] emptiness checks and poisons downstream compares (auto-filed 'Latest: null' issues); Docker Hub returns 401 JSON without an anonymous bearer token even for public images; the value comparable to a FROM image@sha256 pin is the docker-content-digest RESPONSE HEADER fetched with manifest-list/OCI-index Accept types — NEVER .config.digest. Use when: (1) a digest-pin check workflow reports null/always-stale, (2) writing any CI job that queries registry-1.docker.io, (3) updating base-image digest pins and needing to verify the new digest before committing."
category: ci-cd
date: 2026-07-03
version: "1.0.0"
user-invocable: false
verification: verified-local
tags: [docker-hub, registry-v2, digest-pin, docker-content-digest, jq-null, github-actions, oci-image-index, supply-chain, base-image]
---

# Docker Hub Digest-Check Workflows: Bearer Token, docker-content-digest Header, and the jq-null Guard

## Overview

| Field | Value |
|-------|-------|
| **Date** | 2026-07-03 |
| **Objective** | Root-cause and fix a scheduled GitHub Actions digest-check workflow (`.github/workflows/digest-check.yml`) that compares a Dockerfile `FROM python:3.12-slim@sha256:<pin>` against Docker Hub and auto-filed an issue with body "Latest: null" (ProjectScylla issue #2025). |
| **Outcome** | Identified three stacked bugs: no anonymous bearer token (401 JSON), `jq -r` printing the literal string "null" past a `[ -z ]` guard, and comparing the wrong digest field. Produced a working token + `docker-content-digest`-header fetch pattern, verified live against Docker Hub. |
| **Verification** | verified-local (all registry commands executed live against Docker Hub on 2026-07-03; the fixed workflow has NOT yet run in CI) |

## When to Use

- A scheduled digest-pin check workflow reports `null` or is permanently "stale" (re-files the same issue every run even after pins were updated).
- You are writing any CI job that queries `registry-1.docker.io` (Docker Hub Registry v2 API) — even for public images.
- You are updating base-image digest pins (`FROM image@sha256:<pin>`) and need to verify the new digest end-to-end before committing.
- A workflow auto-files issues whose body embeds obviously-broken data (e.g. "Latest: null") — the filer itself is the bug.
- You are about to bulk-replace an old digest across a repo and need to classify which occurrences are real pins vs test fixtures vs doc examples.

## Verified Workflow

### Quick Reference

```bash
# 1. Anonymous bearer token FIRST (Docker Hub 401s without it, even for public images)
TOKEN=$(curl -fsSL "https://auth.docker.io/token?service=registry.docker.io&scope=repository:library/python:pull" | jq -r '.token')

# 2. The digest comparable to a FROM image@sha256 pin = docker-content-digest RESPONSE HEADER
#    with manifest-list/OCI-index Accept types (NEVER .config.digest from the body)
LATEST=$(curl -fsSL -o /dev/null -w '%header{docker-content-digest}' \
  -H "Authorization: Bearer $TOKEN" \
  -H "Accept: application/vnd.docker.distribution.manifest.list.v2+json,application/vnd.oci.image.index.v1+json" \
  "https://registry-1.docker.io/v2/library/python/manifests/3.12-slim" | sed 's/^sha256://')

# 3. Guard the jq-null trap: "null" is a NON-EMPTY string and passes [ -z ]
if [ -z "$LATEST" ] || [ "$LATEST" = "null" ]; then echo "ERROR: could not fetch digest"; exit 1; fi
```

### Detailed Steps

1. **Get an anonymous bearer token first.** Unauthenticated GETs to `registry-1.docker.io/v2/...` return a **401 JSON error body, even for public images**. Fetch a token from `auth.docker.io` scoped to the repository:

   ```bash
   TOKEN=$(curl -fsSL "https://auth.docker.io/token?service=registry.docker.io&scope=repository:library/python:pull" | jq -r '.token')
   ```

2. **Fetch the manifest-list/index digest from the `docker-content-digest` RESPONSE HEADER.** The digest comparable to a Dockerfile `FROM image@sha256:<pin>` is the manifest-list/OCI-index digest, and it lives in the response header — request it with the right Accept types:

   ```bash
   LATEST=$(curl -fsSL -o /dev/null -w '%header{docker-content-digest}' \
     -H "Authorization: Bearer $TOKEN" \
     -H "Accept: application/vnd.docker.distribution.manifest.list.v2+json,application/vnd.oci.image.index.v1+json" \
     "https://registry-1.docker.io/v2/library/python/manifests/3.12-slim" | sed 's/^sha256://')
   ```

   Note: the `%header{name}` write-out variable requires curl >= 7.83 (ubuntu-latest runners ship curl 8.x). NEVER compare `.config.digest` from the manifest body — that is the image-config blob digest and can never match a FROM pin.

3. **Guard against the jq-null trap explicitly.** `jq -r '.field'` on an error/mismatched JSON prints the literal STRING `null`, which is non-empty and passes `[ -z "$X" ]` — then poisons every downstream compare into permanent "stale":

   ```bash
   if [ -z "$LATEST" ] || [ "$LATEST" = "null" ]; then echo "ERROR: could not fetch digest"; exit 1; fi
   ```

4. **Verify a new pin end-to-end before committing it.** HEAD `manifests/sha256:<digest>` with the token and the same index Accept types — expect HTTP 200 and content-type `application/vnd.oci.image.index.v1+json` (the same media type as the old pins). Then walk index -> amd64 manifest -> config blob and check the embedded version env (observed `PYTHON_VERSION=3.12.13` for python:3.12-slim digest `423ed6ab25b1921a477529254bfeeabf5855151dc2c3141699a1bfc852199fbf`).

5. **Fix the broken auto-filer in the SAME PR as the pin update.** When an auto-filer workflow embeds its own bug in the issue it files ("Latest: null"), updating only the pins does not stop the noise — the broken compare (`"null" != <pin>` → always stale) re-files the issue on every scheduled run even after the pins are current.

6. **Classify digest occurrences before bulk-replacing.** Grep the old digests across the repo and classify each hit as real pin vs synthetic test fixture (arbitrary constants written to tmp files to test digest FORMAT) vs doc example. Only real pins and docs quoting the current pin need updates; fixtures must be left alone.

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
|---------|----------------|---------------|----------------|
| Unauthenticated registry GET | `curl -s https://registry-1.docker.io/v2/library/python/manifests/3.12-slim` piped to jq | Docker Hub returns 401 JSON error body without a bearer token, even for public images | Always fetch an anonymous token from auth.docker.io first |
| Relying on `[ -z "$VAR" ]` after `jq -r` | Workflow checked emptiness only | `jq -r` prints the literal string "null" on missing fields/error JSON — non-empty, passes the check, then poisons the digest compare into permanent "stale" | Add an explicit `[ "$VAR" = "null" ]` guard |
| Comparing `.config.digest` to a FROM pin | Workflow parsed `.config.digest` from the manifest JSON | `.config.digest` is the image-CONFIG blob digest; a `FROM image@sha256:` pin is the manifest-list/index digest — they can never match | Use the `docker-content-digest` response header with manifest-list/OCI-index Accept types |
| Trusting the auto-filed issue body for the target digest | Issue said "Latest: null" | The filer itself was broken; its output was the bug artifact | Independently resolve the digest from the registry before planning a pin update |

## Results & Parameters

**Verification level:** verified-local — all commands below were executed live against Docker Hub on 2026-07-03; the fixed workflow has NOT yet been exercised in CI.

**Exact working token + header command pair:**

```bash
TOKEN=$(curl -fsSL "https://auth.docker.io/token?service=registry.docker.io&scope=repository:library/python:pull" | jq -r '.token')
LATEST=$(curl -fsSL -o /dev/null -w '%header{docker-content-digest}' \
  -H "Authorization: Bearer $TOKEN" \
  -H "Accept: application/vnd.docker.distribution.manifest.list.v2+json,application/vnd.oci.image.index.v1+json" \
  "https://registry-1.docker.io/v2/library/python/manifests/3.12-slim" | sed 's/^sha256://')
```

**Null-guard snippet (required after every `jq -r` / header extraction):**

```bash
if [ -z "$LATEST" ] || [ "$LATEST" = "null" ]; then echo "ERROR: could not fetch digest"; exit 1; fi
```

**Key parameters:**

- Token endpoint: `https://auth.docker.io/token?service=registry.docker.io&scope=repository:<namespace>/<repo>:pull` (use `library/<repo>` for official images)
- Accept types for the pin-comparable digest: `application/vnd.docker.distribution.manifest.list.v2+json,application/vnd.oci.image.index.v1+json`
- `%header{docker-content-digest}` write-out requires curl >= 7.83 (ubuntu-latest ships curl 8.x)
- Observed for `python:3.12-slim` on 2026-07-03: index digest `423ed6ab25b1921a477529254bfeeabf5855151dc2c3141699a1bfc852199fbf`, content-type `application/vnd.oci.image.index.v1+json`, embedded `PYTHON_VERSION=3.12.13`

## Verified On

- 2026-07-03 — ProjectScylla issue #2025 planning session: `.github/workflows/digest-check.yml` auto-filed "Latest: null"; all registry commands run live against Docker Hub from the dev machine. CI run of the fixed workflow still pending.
