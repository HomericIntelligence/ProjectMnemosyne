---
name: traefik-middleware-cross-provider-reference-suffix
description: "Diagnose and fix a Traefik router that fails to load with `middleware \"X@<provider>\" does not exist` because a middleware reference omitted its provider suffix and Traefik silently assumed it lived in the referencing router's own provider. Use when: (1) a Docker-labeled router references a middleware defined in the file provider (or vice versa) without an explicit `@file`/`@docker` suffix, (2) one router 404s or fails to route while a sibling router on the same host/different entrypoint works fine, (3) `docker logs` shows nothing useful for a Traefik routing failure."
category: debugging
date: 2026-07-06
version: "1.0.0"
user-invocable: false
verification: verified-local
tags: [traefik, middleware, docker-provider, file-provider, reverse-proxy, dynamic-configuration, cross-provider-reference]
---

# Traefik Middleware Cross-Provider Reference Suffix

## Overview

| Field | Value |
|-------|-------|
| **Date** | 2026-07-06 |
| **Objective** | Diagnose and fix a Traefik v3 router failing to load because a middleware reference (added to fix a v2→v3 breaking change) implicitly resolved to the wrong provider |
| **Outcome** | Successful — root cause identified and fixed on a live homelab Traefik v3.7.6 instance |
| **Verification** | verified-local |
| **History** | none — initial version |

## When to Use

- A Traefik router defined via Docker labels references a middleware that is actually defined in the file provider (or vice versa), and the reference has NO explicit `@file`/`@docker` provider suffix.
- Traefik's internal log shows `middleware "X@docker" does not exist` (or `X@file`, `X@<any-provider>`) for a specific `routerName`, but the instance otherwise appears to be running fine.
- One router 404s (or otherwise fails to route) while a sibling router for the same host on a **different entrypoint** works perfectly — a strong signal of a per-router config-load failure rather than a DNS/network/TLS problem.
- `docker logs <traefik-container>` shows nothing relevant — check whether static config sets `log.filePath`, which redirects Traefik's real runtime logging into a file inside the container instead of stdout.
- You are migrating middleware chains during a Traefik v2→v3 upgrade (e.g. replacing the removed `headers.sslRedirect` option with a `redirectScheme` middleware) and are adding a NEW middleware reference to an existing router's chain.

## Verified Workflow

### Quick Reference

```bash
# 1. Check whether Traefik logs are redirected away from stdout
docker exec <traefik-container> cat /etc/traefik/traefik.yml | grep -A2 '^log:'
#   If log.filePath is set, docker logs will NOT show runtime errors.

# 2. Read the real runtime log (and access log) inside the container
docker exec <traefik-container> cat /var/log/traefik/traefik.log | grep -i error
docker exec <traefik-container> cat /var/log/traefik/access.log | tail

# 3. Look for the exact signature of this bug
#    {"level":"error","entryPointName":"http","routerName":"nextcloud-http@docker",
#     "error":"middleware \"redirect@docker\" does not exist", ...}

# 4. Fix: qualify the cross-provider middleware reference with its real provider
#    BROKEN  (bare name -> Traefik assumes same provider as the router, i.e. @docker):
#      traefik.http.routers.nextcloud-http.middlewares=customFrameHomelab@file,redirect,nextcloud-headers,nextcloud-dav
#    FIXED   (explicit @file suffix matches where `redirect` is actually defined):
#      traefik.http.routers.nextcloud-http.middlewares=customFrameHomelab@file,redirect@file,nextcloud-headers,nextcloud-dav

# 5. Recreate the affected container and confirm
docker compose up -d <service>
curl -I http://<host>/   # expect 307/308 redirect instead of 404
```

### Detailed Steps

1. **Recognize the trigger scenario**: you added or edited a middleware reference in a router's chain, where the router and the middleware are defined via DIFFERENT Traefik providers (e.g. router via Docker labels, middleware via the static file provider's YAML). This commonly happens mid-upgrade when a removed option (like v3 dropping `headers.sslRedirect`) forces you to point an existing router at a shared middleware defined elsewhere.

2. **Do not trust `docker logs` alone.** Check the static configuration for `log.filePath` (or `--log.filepath` CLI flag / `TRAEFIK_LOG_FILEPATH` env var). If set, `docker logs` only ever shows Traefik's startup banner — all runtime routing errors go to that file instead of stdout.
   ```bash
   docker exec <traefik-container> cat /var/log/traefik/traefik.log | grep -i error
   docker exec <traefik-container> cat /var/log/traefik/access.log | tail
   ```

3. **Identify the exact error signature**: `middleware "X@<provider>" does not exist`, tagged with a specific `routerName`. Note which provider suffix Traefik appended to the bare middleware name — it will always be the SAME provider as the router that referenced it, not the provider where the middleware is actually defined.

4. **Use the sibling-router clue to rule out broader causes.** If a router for the same hostname on a different entrypoint (e.g. the HTTPS router) works perfectly while only one specific router (e.g. the plain-HTTP redirect router) fails, that is strong evidence of a per-router config-LOAD failure — not DNS, not TLS/certificates, not a bad `Host()` rule. A router that fails to load simply stops existing; a plain `404` on that hostname/entrypoint combination is the visible symptom, and it looks deceptively like a routing-rule or DNS problem.

5. **Apply the fix**: add the explicit `@<provider>` suffix matching where the middleware is ACTUALLY defined. In the reproduction case, the correct fix was `redirect@file` (matching the pattern of the other, correctly-working reference in the same middleware list, `customFrameHomelab@file`).

6. **General rule**: cross-provider middleware references in Traefik ALWAYS need an explicit `@<provider>` suffix. Same-provider references can omit it — and if you DO omit it, Traefik assumes same-provider-as-referencer, silently, with no warning at config-parse time. The error only surfaces at runtime, per-router, on the first request that exercises that router.

7. **Recreate the container and verify** the previously-404ing router now returns the expected redirect status code (e.g. `307`) instead of `404`.

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
|---------|----------------|---------------|-----------------|
| Chasing TLS/certificate issues | Checked certificate validity and TLS handshake for the failing host | Certs were valid; the failure was a router that never loaded at all, not a TLS negotiation problem | A bare `404` (not a TLS error) means the request reached Traefik but found no matching, loaded router — check router load state before certs |
| Chasing DNS issues | Considered whether the hostname resolved incorrectly for the plain-HTTP entrypoint | DNS was identical for both the working HTTPS router and the failing HTTP router on the same hostname | If a sibling router on the same host/different entrypoint works, DNS is already ruled out |
| Assuming a bad `Host()` rule | Suspected the router's `Host()` matcher was misconfigured, causing a routing miss | The rule was correct and unchanged from before the upgrade; the router simply failed to LOAD due to the middleware reference error, so no rule was ever evaluated | A `404` from Traefik can mean "no router loaded for this rule" as easily as "rule didn't match" — check the internal error log before re-auditing matcher syntax |
| Relying on `docker logs` to confirm "no errors" | Ran `docker logs <traefik-container>` and saw no errors, concluded Traefik config was clean | `log.filePath` was set in static config, redirecting all runtime logs to a file inside the container; `docker logs` only shows the startup banner | Always check for a configured `log.filePath` before trusting `docker logs` as the complete picture |

## Results & Parameters

**Error signature to grep for:**

```text
{"level":"error","entryPointName":"http","routerName":"nextcloud-http@docker","error":"middleware \"redirect@docker\" does not exist","time":"..."}
```

**Broken Docker label (bare cross-provider reference):**

```text
traefik.http.routers.nextcloud-http.middlewares=customFrameHomelab@file,redirect,nextcloud-headers,nextcloud-dav
```

**Fixed Docker label (explicit `@file` suffix):**

```text
traefik.http.routers.nextcloud-http.middlewares=customFrameHomelab@file,redirect@file,nextcloud-headers,nextcloud-dav
```

**Log inspection commands (when `log.filePath` is set):**

```bash
docker exec <traefik-container> cat /var/log/traefik/traefik.log | grep -i error
docker exec <traefik-container> cat /var/log/traefik/access.log | tail
```

**Root cause summary:** Traefik resolves a middleware (or any cross-referenced dynamic-config object) reference that omits an explicit `@<provider>` suffix by assuming it lives in the SAME provider as the object doing the referencing — never by searching across all configured providers. A router defined via the Docker provider that references a bare-named middleware which only exists in the file provider will fail to load with `middleware "X@docker" does not exist`, even though a middleware with that exact name genuinely exists elsewhere. The fix is always to add the correct explicit provider suffix on any cross-provider reference.

**Traefik version:** v3.7.6 (upgraded from v2.2). Confirmed the same provider-suffix-inference behavior existed in v2.2 as well — this is not new to v3, but a v3 breaking change (removal of `headers.sslRedirect`) is what prompted adding the new cross-provider reference that exposed it.

## Verified On

| Project | Context | Details |
|---------|---------|---------|
| HomeLab (apollo) | Traefik v3.7.6 upgrade, Docker provider + file provider, Nextcloud HTTP→HTTPS redirect router | Reproduced live; confirmed via internal log file; fix verified by observing `404` → `307` after adding `@file` suffix and recreating the container |
