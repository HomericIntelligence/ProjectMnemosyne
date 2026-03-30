---
name: podman-rootless-dns-container-resolution
description: "Fix podman rootless DNS resolution failures between containers in compose networks. Use when: (1) containers cannot resolve each other by service name, (2) NATS/HTTP connections fail with 'Temporary failure in name resolution', (3) aardvark-dns is running but resolution still fails."
category: debugging
date: 2026-03-30
version: "1.0.0"
user-invocable: false
verification: verified-local
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
|-------|-------|
| **Date** | 2026-03-30 |
| **Objective** | Fix container-to-container DNS resolution in podman rootless compose networks |
| **Outcome** | Workaround found — use container IPs directly via NATS_URL env var override |
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

### Detailed Steps

1. Check if `aardvark-dns` is running: `ps aux | grep aardvark`
2. Check network has DNS: `podman network inspect <net> | grep dns_enabled`
3. Check container `/etc/resolv.conf` points to `10.89.0.1` (podman DNS)
4. If resolution still fails, get target container IP: `podman inspect <target> | jq '.[0].NetworkSettings.Networks'`
5. Restart failing containers with `NATS_URL=nats://<IP>:4222` (or equivalent env var)
6. For production: file podman bug report; for E2E testing: IP workaround is acceptable

### Root Cause Analysis

The failure occurs when:
- Multiple containers start simultaneously via `podman compose up -d`
- Some containers attempt DNS resolution before `aardvark-dns` has fully registered all container names
- The DNS resolution failure is cached by glibc, and even after `aardvark-dns` has the record, the container's resolver returns stale NXDOMAIN
- Restarting the container (not just the process) clears the DNS cache

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
|---------|----------------|---------------|----------------|
| `depends_on: condition: service_healthy` | Wait for NATS healthy before starting dependent containers | NATS scratch image has no shell — `CMD-SHELL` healthchecks fail. Also, even with delay, DNS can still fail. | Healthcheck-based ordering doesn't fix DNS race |
| `healthcheck: test: ["CMD-SHELL", "true"]` | Trivial healthcheck that always passes | NATS image has no `/bin/sh` at all — scratch/distroless image | Cannot use CMD-SHELL with scratch images |
| `healthcheck: test: ["CMD-SHELL", "wget ..."]` | Wget-based health check | NATS image has no wget, no curl, no shell | NATS official image is a minimal scratch image |
| `healthcheck: test: ["CMD", "nats-server", "--help"]` | Use existing binary for health | `nats-server --help` returns exit code 1 (not 0) when server is already running | Even binary-based checks can have unexpected exit codes |
| Removing all healthchecks | Simple `depends_on` without conditions | Services start but DNS still fails on first boot — race condition | Ordering alone doesn't solve DNS registration race |

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
workaround: direct_container_ip
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
|---------|---------|---------|
| Odysseus | E2E pipeline with 9 containers | NATS, Agamemnon, Nestor, Hermes, Myrmidon all affected by DNS race |
