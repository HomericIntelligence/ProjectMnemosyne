---
name: nextcloud-talk-hpb-standalone-deploy
description: "Deploy the Nextcloud Talk High-Performance Backend (standalone spreed-signaling server + Janus SFU + coturn) as Docker containers behind a reverse proxy and wire it into Nextcloud via occ to clear the admin 'High-performance backend' warning. Use when: (1) Talk calls break down beyond 2-3 participants, (2) the Nextcloud admin 'High-performance backend' row is red/missing, (3) you need a single-instance HPB without a separate NATS/Redis cluster."
category: tooling
date: 2026-06-25
version: "1.0.0"
user-invocable: false
verification: verified-local
tags: []
---

# Nextcloud Talk HPB Standalone Deploy

## Overview

| Field | Value |
|-------|-------|
| **Date** | 2026-06-25 |
| **Objective** | Deploy the Nextcloud Talk High-Performance Backend (standalone signaling server + Janus SFU + coturn) as Docker containers behind a reverse proxy, wire it to Nextcloud via `occ`, and clear the "High-performance backend" admin warning so Talk calls scale beyond 2-3 participants. |
| **Outcome** | Signaling server reaches Janus and coturn; `/api/v1/welcome` responds; the Nextcloud admin "High-performance backend" row turns green and its "Test this server" passes. TURN relay across NATs additionally requires router port-forwarding. |

The stock Nextcloud Talk internal signaling is peer-to-peer and only works reliably for
2-3 participants. Larger calls need the High-Performance Backend (HPB): a standalone
`spreed-signaling` server that offloads media routing to a Janus SFU (Selective Forwarding
Unit) and uses coturn for TURN/STUN relay. This skill deploys all three as Docker
containers for a single instance (internal NATS, no external NATS/Redis cluster) and wires
them into Nextcloud.

## When to Use

- Talk video calls degrade or fail once more than 2-3 participants join.
- The Nextcloud admin settings → Talk page shows the "High-performance backend" row red,
  empty, or with a "Test this server" failure.
- You want a minimal single-instance HPB and do not want to run a separate NATS or Redis
  container.
- You are deploying HPB components behind an existing reverse proxy (traefik or similar)
  with wildcard DNS and TLS already in place.

## Verified Workflow

### Quick Reference

| Component | Image | Key gotcha |
|-----------|-------|------------|
| Signaling | `strukturag/nextcloud-spreed-signaling:latest` | NO semver Docker tags; `:v2.1.1` does not exist on Docker Hub |
| Janus SFU | `mwalbeck/janus-gateway` | Has its own entrypoint; do NOT override `command:`; internal-only |
| coturn | `coturn/coturn:4.6.2` | `network_mode: host`; needs router port-forwarding for real relay |

**1. Pin images correctly.** The signaling image `strukturag/nextcloud-spreed-signaling`
publishes only git-commit-hash tags (each with a `-proxy` variant) plus `latest` — it has
NO semver tags. The GitHub RELEASE tag `:v2.1.1` does NOT exist on Docker Hub and
`docker pull` fails with `manifest unknown: manifest unknown`. Use `:latest` (currently
resolves to 2.1.1) or pin by a commit-hash tag / digest.

**2. Janus uses its own entrypoint.** The `mwalbeck/janus-gateway` image ships its own
entrypoint. Adding `command: ["janus", ...]` fails with
`exec: "janus": executable file not found in $PATH`. Use the image default. Janus is
internal-only on the private compose network — the signaling server reaches it at
`ws://janus:8188`; publish NO ports for it.

**3. Render `server.conf` on disk BEFORE `docker-compose up`.** A bind-mount whose source
file is missing gets created by Docker as a DIRECTORY, silently breaking the mount. Create
the file first. The v2 format (verified against the real `server.conf.in`):

```ini
[http]
listen = 0.0.0.0:8080
[sessions]
hashkey = <64-char random>
blockkey = <32-char random>
[backend]
backends = nextcloud
[nextcloud]
urls = https://<nextcloud-domain>
secret = <signaling_shared_secret>
[nats]
url = nats://loopback
[mcu]
type = janus
url = ws://janus:8188
[turn]
apikey = <turn_secret>
secret = <turn_secret>
servers = turn:<signaling-domain>:3478?transport=udp,turn:<signaling-domain>:3478?transport=tcp
```

Key structural point: `[backend]` uses `backends = <id>` PLUS a SEPARATE `[<id>]` section
whose URL key is `urls` (PLURAL, not `url`) and `secret`. `[nats] url = nats://loopback`
selects the internal NATS, so NO separate NATS or Redis container is needed for a single
instance.

**4. coturn.** Run `coturn/coturn:4.6.2` with `network_mode: host` and CLI flags:

```text
-n --no-cli --no-tls --no-dtls --listening-port=3478 --fingerprint \
  --use-auth-secret --static-auth-secret=<turn_secret> --realm=<domain> \
  --min-port=<lo> --max-port=<hi> --external-ip=<public_ip>/<lan_ip>
```

Real cross-NAT relay REQUIRES the user to port-forward on their ROUTER: `3478/udp`,
`3478/tcp`, and the relay range (e.g. `49160-49200/udp`). The admin warning still clears
from the signaling server alone even without the router ports.

**5. Wire Nextcloud via `occ`** (run as the web PUID, e.g.
`docker exec -u 1002 nextcloud_nextcloud_1 php occ`):

```bash
occ talk:signaling:add "https://<signaling-domain>" "<signaling_secret>" --verify
occ talk:stun:add "<signaling-domain>:3478"
occ talk:turn:add turn "<signaling-domain>:3478" "udp,tcp" --secret "<turn_secret>"
```

**6. Reverse proxy.** Route the signaling subdomain → the signaling container's `:8080`
(it serves the WebSocket; traefik and most proxies proxy WS natively). Put NO auth
(basic / forward-auth) middleware in front of the signaling route — it breaks the Talk
WebSocket handshake. A wildcard `*.domain` DNS record plus wildcard TLS cert already cover
a fresh `signaling.` subdomain, so no new DNS record or certificate is required.

**7. Validate.** Signaling container logs should show `Found JANUS VideoRoom plugin`,
`Using janus MCU`, `Adding "turn:...:3478..." as TURN server`, and
`Listening on 0.0.0.0:8080`. Then:

```bash
curl https://<signaling-domain>/api/v1/welcome
# -> {"nextcloud-spreed-signaling":"Welcome","version":"..."}
```

Finally, in Nextcloud admin settings the "High-performance backend" row turns green and its
"Test this server" passes.

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
|---------|----------------|---------------|----------------|
| Pin signaling by release tag | Set image to `strukturag/nextcloud-spreed-signaling:v2.1.1` (the GitHub release tag) | `docker pull` failed `manifest unknown: manifest unknown` — Docker Hub has only git-commit-hash tags and `latest`, no semver tags | Use `:latest` or pin by commit-hash tag / digest; the GitHub release tag is not a Docker tag |
| Override Janus command | Added `command: ["janus", ...]` to the Janus service | Container crashed with `exec: "janus": executable file not found in $PATH` | The `mwalbeck/janus-gateway` image has its own entrypoint; do NOT set `command:` |
| Bind-mount missing conf | Started `docker-compose up` before creating `server.conf` on disk | Docker created the missing bind source as a DIRECTORY, so the signaling server got a directory where a config file was expected | Render/create `server.conf` on disk BEFORE `docker-compose up` |
| Wrong backend URL key | Wrote `url = https://...` inside the `[nextcloud]` backend section | Backend registration silently failed; the key must be `urls` (plural) | The `[<backend-id>]` section uses `urls` (PLURAL) + `secret`, not `url` |
| Auth middleware on signaling route | Left basic/forward-auth middleware in front of the `signaling.` reverse-proxy route | The Talk WebSocket handshake was blocked and the HPB test failed | Put NO auth middleware in front of the signaling WebSocket route |

## Results & Parameters

| Parameter | Value / Setting |
|-----------|-----------------|
| Signaling image | `strukturag/nextcloud-spreed-signaling:latest` (resolves to 2.1.1; no semver tags exist) |
| Janus image | `mwalbeck/janus-gateway` (default entrypoint; internal-only at `ws://janus:8188`) |
| coturn image | `coturn/coturn:4.6.2`, `network_mode: host` |
| coturn listening port | `3478` (udp + tcp) |
| coturn relay range | e.g. `49160-49200/udp` (router-forwarded) |
| Signaling HTTP listen | `0.0.0.0:8080` (reverse-proxied as the `signaling.` subdomain) |
| NATS | internal (`nats://loopback`) — no separate NATS/Redis container |
| MCU type | `janus` |
| Router port-forwards (for real TURN relay) | `3478/udp`, `3478/tcp`, relay range `/udp` |
| occ user | web PUID (e.g. `-u 1002`) |
| Admin outcome | "High-performance backend" row green; "Test this server" passes |
| `/api/v1/welcome` | `{"nextcloud-spreed-signaling":"Welcome","version":"..."}` |

**Secrets to generate**: `hashkey` (64-char random), `blockkey` (32-char random),
`signaling_shared_secret` (shared with Nextcloud via `talk:signaling:add`), and
`turn_secret` (shared between coturn `--static-auth-secret`, the `[turn]` section, and
`talk:turn:add --secret`).

**Scope note**: The signaling server alone clears the admin warning and enables SFU-routed
calls. Cross-NAT TURN relay additionally depends on the router port-forwarding above.
