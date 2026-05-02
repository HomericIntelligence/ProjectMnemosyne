---
name: podman-rootless-dns-container-resolution
description: "Fix podman rootless DNS resolution failures between containers in compose networks. Use when: (1) containers cannot resolve each other by service name, (2) NATS/HTTP connections fail with 'Temporary failure in name resolution', (3) aardvark-dns is running but resolution still fails."
category: debugging
date: 2026-03-30
version: "1.1.0"
user-invocable: false
verification: verified-local
history: podman-rootless-dns-container-resolution.history
tags:
  - podman
  - rootless
  - dns
  - aardvark-dns
  - compose
  - networking
---

# Podman Rootless DNS Container Name Resolution Failure

## Overview

| Field | Value |
| ------- | ------- |
| **Date** | 2026-03-30 |
| **Objective** | Fix container-to-container DNS resolution in podman rootless compose networks |
| **Outcome** | Automated workaround via start-stack.sh launcher script |
| **History** | [changelog](./podman-rootless-dns-container-resolution.history) |
| **Verification** | verified-local |

## When to Use

- `podman compose up` starts services but they can't connect to each other by name
- Container logs show: `socket.gaierror: [Errno -3] Temporary failure in name resolution`
- `aardvark-dns` process is running, network has `dns_enabled: true`, but resolution still fails
- NATS clients (nats.c or nats-py) fail to connect when using `nats://nats:4222`
- Python containers (python:3.12-slim) are most affected; C++ containers may also fail

## Verified Workflow

### Quick Reference

```bash
# Diagnosis: verify DNS is running but not resolving
podman exec <container> python3 -c "import socket; socket.gethostbyname('nats')"
# → socket.gaierror: [Errno -3] Temporary failure in name resolution

# Verify network connectivity works by IP
NATS_IP=$(podman inspect odysseus-nats-1 | python3 -c "
import sys,json; d=json.load(sys.stdin)
nets=d[0]['NetworkSettings']['Networks']
print(list(nets.values())[0]['IPAddress'])")

podman exec <container> python3 -c "
import socket; s=socket.socket(); s.connect(('${NATS_IP}', 4222)); print('OK')"
# → OK (connectivity works, only DNS is broken)

# Workaround: restart containers with direct IPs
podman rm -f <container>
podman run -d --name <container> --network <network> \
  -e "NATS_URL=nats://${NATS_IP}:4222" <image>
```

### Automated Launcher Script (Recommended)

Create a `start-stack.sh` that automates the workaround:

```bash
#!/usr/bin/env bash
set -euo pipefail

get_ip() {
  podman inspect "$1" 2>/dev/null | python3 -c "
import sys,json; d=json.load(sys.stdin)
nets=d[0]['NetworkSettings']['Networks']
print(list(nets.values())[0]['IPAddress'])"
}

# Step 1: Start everything via compose
podman compose -f docker-compose.e2e.yml up -d
sleep 10

# Step 2: Discover IPs (stable — containers are running)
NATS_IP=$(get_ip odysseus-nats-1)

# Step 3: Restart NATS-dependent services with direct IPs
podman run -d --replace --name odysseus-agamemnon-1 \
  --network odysseus_homeric-mesh \
  -p 8080:8080 -e "NATS_URL=nats://${NATS_IP}:4222" \
  odysseus-agamemnon:latest
# ... repeat for hermes, myrmidon, exporter
```

### Detailed Steps

1. Check if `aardvark-dns` is running: `ps aux | grep aardvark`
2. Check network has DNS: `podman network inspect <net> | grep dns_enabled`
3. Check aardvark-dns config: `cat /run/user/1000/containers/networks/aardvark-dns/<network>` — first line is DNS IP
4. Check container `/etc/resolv.conf` — if nameserver doesn't match aardvark-dns IP, that's the bug
5. Use the launcher script (above) or manually restart with direct IPs
6. Use `--replace` flag on `podman run` to avoid "name already in use" errors

### Root Cause Analysis

The failure occurs because:
- `aardvark-dns` binds to a gateway IP on a specific bridge subnet (e.g., `10.89.2.1`)
- After `podman compose down` + `up` cycles, the network gets recreated on a different subnet
- Container `/etc/resolv.conf` gets `nameserver 10.89.0.1` (from the new bridge gateway)
- But aardvark-dns is still listening on `10.89.2.1` (from a previous incarnation)
- The mismatch means DNS queries go to a non-existent resolver
- Additionally, glibc caches NXDOMAIN responses — even patching `/etc/resolv.conf` inside a running container doesn't help (the cache persists)
- Only destroying and recreating the container clears the glibc DNS cache

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
| --------- | ---------------- | --------------- | ---------------- |
| `depends_on: condition: service_healthy` | Wait for NATS healthy before starting dependent containers | NATS scratch image has no shell — `CMD-SHELL` healthchecks fail. Also, even with delay, DNS can still fail. | Healthcheck-based ordering doesn't fix DNS race |
| `healthcheck: test: ["CMD-SHELL", "true"]` | Trivial healthcheck that always passes | NATS image has no `/bin/sh` at all — scratch/distroless image | Cannot use CMD-SHELL with scratch images |
| `healthcheck: test: ["CMD-SHELL", "wget ..."]` | Wget-based health check | NATS image has no wget, no curl, no shell | NATS official image is a minimal scratch image |
| `healthcheck: test: ["CMD", "nats-server", "--help"]` | Use existing binary for health | `nats-server --help` returns exit code 1 (not 0) when server is already running | Even binary-based checks can have unexpected exit codes |
| Removing all healthchecks | Simple `depends_on` without conditions | Services start but DNS still fails on first boot — race condition | Ordering alone doesn't solve DNS registration race |
| Patching `/etc/resolv.conf` live | `podman exec <c> sh -c "echo nameserver 10.89.2.1 > /etc/resolv.conf"` | glibc caches NXDOMAIN — even with correct resolv.conf, cached failures persist | Must destroy+recreate container to clear glibc DNS cache |
| `dns_enabled: true` in network config | Added `driver_opts: dns_enabled: "true"` to compose network | DNS was already enabled; this option is the default and has no effect | The issue is gateway mismatch, not DNS being disabled |
| Explicit network aliases | Added `aliases: [nats]` under each service's network config | Aliases registered correctly in aardvark-dns config file but containers still can't resolve | Aliases don't help when the resolver IP itself is wrong |

## Results & Parameters

```yaml
# Environment where this was observed
podman_version: 4.9.3
os: Ubuntu 24.04 (WSL2)
kernel: 6.6.87.2-microsoft-standard-WSL2
dns_server: aardvark-dns
network_driver: bridge
rootless: true

# Working configuration
workaround: start-stack.sh launcher script (compose up → discover IPs → restart with direct IPs)
workaround_alt: direct_container_ip via manual podman run --replace
nats_image: nats:latest  # scratch image, no shell
affected_images:
  - python:3.12-slim (Hermes, argus-exporter)
  - custom C++20 ubuntu:24.04 (Agamemnon, Nestor, hello-myrmidon)

# Ports that can become zombies after compose down
zombie_port_issue: true
fix: pkill -f rootlessport  # or remap to non-conflicting ports
```

## Verified On

| Project | Context | Details |
| --------- | --------- | --------- |
| Odysseus | E2E pipeline with 9 containers | NATS, Agamemnon, Nestor, Hermes, Myrmidon all affected by DNS race |
