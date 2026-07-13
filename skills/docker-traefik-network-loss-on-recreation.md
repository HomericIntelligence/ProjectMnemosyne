---
name: docker-traefik-network-loss-on-recreation
description: "Diagnose and fix Traefik 504 Gateway Timeout after container recreation caused by Docker network isolation. Use when: (1) Traefik returns 504 for all backends after being recreated, (2) backends show UP in Traefik dashboard but are unreachable, (3) direct curl to container works but Traefik cannot reach it, (4) planning ANY Traefik container recreate (image bump, major upgrade) and want to check proactively whether it's at risk before touching anything."
category: debugging
date: 2026-07-06
version: "1.1.0"
user-invocable: false
verification: verified-local
history: docker-traefik-network-loss-on-recreation.history
tags: [traefik, docker, networking, "504", gateway-timeout, network-isolation]
---

# Docker Traefik Network Loss on Recreation

## Overview

| Field | Value |
|-------|-------|
| **Date** | 2026-07-06 |
| **Objective** | Diagnose and fix Traefik 504 Gateway Timeout for all backends after Traefik container recreation; catch the risk proactively before recreating |
| **Outcome** | Successful — immediate hotfix and permanent compose fix identified (v1.0.0); reconfirmed working through a real Traefik v2->v3 major upgrade, plus a proactive pre-recreate detection method added (v1.1.0) |
| **Verification** | verified-local |
| **History** | [changelog](./docker-traefik-network-loss-on-recreation.history) |

## When to Use

- Traefik returns 504 Gateway Timeout for ALL backends simultaneously after container recreation
- Traefik dashboard shows services as "UP" with correct IPs, but requests still fail
- Direct HTTP to a backend container IP works from host but Traefik cannot reach it
- Timeout is exactly 30 seconds (matching Traefik's default DialTimeout)
- Traefik was recently stopped + removed + recreated via `docker compose up -d`
- Backends live on an external Docker network not declared in Traefik's own compose file
- **Planning ANY Traefik container recreate** (a routine image bump, or a major-version
  upgrade like v2->v3) and want to check proactively whether this failure mode will hit,
  rather than discovering it reactively via a 504 outage after the fact

## Verified Workflow

### Quick Reference

```bash
# PROACTIVE: run this BEFORE any planned recreate to know if you're at risk
docker inspect <traefik-container> --format '{{json .NetworkSettings.Networks}}' | python3 -m json.tool
grep -A5 "^networks:" /path/to/traefik/docker-compose.yml
# If a network name appears in the inspect output but NOT in the compose file's
# networks: block, that attachment is out-of-band and WILL be dropped on recreate.

# REACTIVE: instant fix if you're already seeing 504s (no restart needed):
docker network connect <external-network> <traefik-container>
# Example:
docker network connect homelabos_traefik homelabos

# Verify fix:
docker inspect <traefik-container> --format '{{json .NetworkSettings.Networks}}'
# Should now show BOTH networks
```

### Detailed Steps

0. **Proactive detection, before touching anything.** Before recreating Traefik for
   ANY reason (routine image bump, major-version upgrade), compare its ACTUAL live
   network attachments against what the compose file declares:
   ```bash
   docker inspect <traefik-container> --format '{{json .NetworkSettings.Networks}}' | python3 -m json.tool
   grep -A5 "^networks:" /path/to/docker-compose.yml
   ```
   If the live inspect output shows a network that does not appear in the compose
   file's own `networks:` block at all, that attachment came from an out-of-band
   `docker network connect` (run once, manually, possibly years ago by a setup script)
   and is invisible to compose — it WILL be silently dropped on the next recreate.
   Apply the permanent fix (step 7 below) BEFORE recreating, not after backends go dark.

1. **Confirm dial timeout signature** (if you're already reacting to an outage): 504s
   that take exactly 30 seconds to return = Traefik DialTimeout, NOT a backend issue.

2. **Check backend health independently**:
   ```bash
   # From host — if this works, backend is healthy
   curl -v http://<container-ip>:<port>/
   # From within same network — if this works, network isolation is confirmed
   docker exec <peer-container> wget -qO- http://<backend-ip>:<port>/
   ```

3. **Inspect Traefik's network membership**:
   ```bash
   docker inspect <traefik-container> --format '{{json .NetworkSettings.Networks}}'
   # Should list BOTH traefik's own network AND backend's network
   ```

4. **Inspect backend network membership**:
   ```bash
   docker network inspect <backend-network>
   # Traefik container should appear in the Containers list — if absent, this is the bug
   ```

5. **Confirm cross-network unreachability** (optional, definitive):
   ```bash
   docker run --rm --network <traefik-network> alpine nc -zv <backend-ip> <port>
   # FAIL = confirmed: traefik network cannot reach backend network
   ```

6. **Apply instant fix** (no restart, takes effect immediately):
   ```bash
   docker network connect <backend-external-network> <traefik-container>
   ```

7. **Apply permanent fix** — add to Traefik's `docker-compose.yml`:
   ```yaml
   networks:
     traefik:
       driver: bridge
     homelabos_traefik:    # <-- the backend external network
       external: true

   services:
     traefik:
       networks:
         - traefik
         - homelabos_traefik    # <-- must be listed here too
   ```
   After recreating, re-run the proactive check from step 0 to confirm the same
   networks with the same IP addresses are still attached post-recreate.

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
|---------|----------------|---------------|----------------|
| Checking SSL certs | Verified SSL certificate validity when 504s appeared | SSL was valid; 504 is a backend connectivity error, not TLS | SSL errors and 504s are unrelated; check network before certs |
| Checking `docker ps` | Verified all containers showed as running | All containers were indeed running; the problem was network connectivity | Container status = running does NOT mean Traefik can reach the container |
| Trusting Traefik dashboard | Dashboard showed backend service as "UP" with correct IP | Traefik discovers backends via Docker socket (labels), not via network reachability | Dashboard "UP" = label-discovered; it does NOT verify network connectivity |
| curl from host | Confirmed backend was reachable from host machine | Host has routing to both Docker networks; Traefik container does not | Host network access is NOT the same as Traefik container network access |

## Results & Parameters

**Traefik v2.2 defaults:**

- `DialTimeout`: 30 seconds (the exact 504 latency is the diagnostic fingerprint)

**Network verification commands:**

```bash
# Check which networks Traefik is joined to:
docker inspect <traefik-container> --format '{{json .NetworkSettings.Networks}}'

# Check which containers are on the backend network:
docker network inspect <backend-network>

# Probe cross-network reachability from Traefik's network:
docker run --rm --network <traefik-network> alpine nc -zv <backend-ip> <port>
```

**Permanent docker-compose.yml fix (minimal diff):**

```yaml
networks:
  traefik:
    driver: bridge
  homelabos_traefik:
    external: true      # declares the pre-existing backend network

services:
  traefik:
    networks:
      - traefik
      - homelabos_traefik   # joins Traefik to the backend network on every recreation
```

**Root cause summary:** `docker compose up -d` only connects a container to networks
declared in its own compose file. If backends joined an external network that is NOT
declared in Traefik's compose, Traefik loses connectivity on every recreation even
though it can still discover backends via the Docker socket.

**Post-fix verification (v1.1.0, Traefik v2.2 -> v3.7.6 upgrade):** after applying the
permanent fix and recreating Traefik on a real major-version bump (not just a patch),
`docker inspect <traefik-container> --format '{{json .NetworkSettings.Networks}}'`
showed the identical two networks with the identical IP addresses as before the
recreate — confirming the fix is recreate-safe across a major-version upgrade, not just
a same-version restart. All dependent backends (a web app, a git server, a
push-notification sidecar) stayed reachable through the recreate with zero downtime
attributable to this failure mode.

## Verified On

| Project | Context | Details |
|---------|---------|---------|
| HomeLab (apollo) | Traefik v2.2 with Nextcloud and Gitea backends on separate Docker network | Immediate fix + permanent compose fix both verified locally |
| HomeLab (apollo) | Traefik v2.2 -> v3.7.6 major upgrade; same external-network attachment | Proactive detection (step 0) run before recreating; permanent fix confirmed to survive a major-version recreate, not just a same-version restart |
