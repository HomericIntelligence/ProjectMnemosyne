---
name: tailscale-split-dns-dnsmasq-restricted-nameserver
description: "Give tailnet devices LAN-speed access to a self-hosted service by killing the WAN hairpin — a tiny dnsmasq container bound to the host's tailnet IP plus a Tailscale 'restricted nameserver' overrides the public hostname to the tailnet IP (no Tailscale 'Custom DNS records' UI needed). Use when: (1) a self-hosted service (NextCloud, etc.) is slow from LAN/tailnet because its public hostname resolves to the WAN IP and traffic hairpins out and back through the router capped at upstream bandwidth, (2) you want `svc.example.com` to resolve to the host's tailnet IP for tailnet devices while all other `*.example.com` names still resolve to their real public records, (3) the Tailscale admin 'Custom DNS records' section is missing/unfindable and you need the always-available split-DNS model instead."
category: tooling
date: 2026-07-04
version: "1.0.0"
user-invocable: false
verification: verified-local
tags: []
---

# Tailscale Split-DNS via dnsmasq Container + Restricted Nameserver (Kill the WAN Hairpin)

## Overview

| Field | Value |
|-------|-------|
| **Date** | 2026-07-04 |
| **Objective** | Make a self-hosted service's public hostname resolve to the host's TAILNET IP for tailnet devices, so uploads/downloads go over Tailscale (direct on LAN, WireGuard remote) at LAN speed instead of hairpinning out through the router's upstream link |
| **Outcome** | Successful — verified ~30 MB/s LAN DAV upload over the tailnet path vs ~5.7 MB/s via the public WAN hairpin (~5.3x faster) on a live homelab; all other `*.example.com` names still forward to their real public records |
| **Verification** | verified-local |

## When to Use

- A self-hosted service (e.g. NextCloud) is slow from LAN/tailnet because `svc.example.com` resolves to the public **WAN IP**, so LAN/tailnet devices hairpin out to the router and back — capped by upstream/upload bandwidth (~5 MB/s here) instead of LAN speed.
- You want ONE hostname (or a few) to resolve to the host's **tailnet IP** for tailnet devices, while every OTHER `*.example.com` name keeps resolving to its real public record.
- The Tailscale admin console **"Custom DNS records"** section is missing or unfindable — the **"restricted nameserver"** split-DNS model is always available and works tailnet-wide.
- Devices use MagicDNS (query `100.100.100.100`), so a router-level DNS override cannot help them — you need a tailnet-scoped nameserver.

## Verified Workflow

### Quick Reference

```bash
# 0. FIRST confirm the service actually answers on the tailnet IP (traefik binds 0.0.0.0;
#    the cert stays valid for the public hostname, so use --resolve to test that specific IP):
curl -k --resolve svc.example.com:443:100.68.51.128 https://svc.example.com/status.php

# 1. dnsmasq config bound to override just the one hostname, forward everything else.
#    /etc/tailscale-dns/dnsmasq.conf :
#      address=/svc.example.com/100.68.51.128
#      no-resolv
#      server=1.1.1.1
#      server=8.8.8.8

# 2. Run dnsmasq in Docker bound ONLY to the host's tailnet IP:53 (NOT an open resolver):
docker run -d --name tailscale-dns --restart unless-stopped \
  -p 100.68.51.128:53:53/udp -p 100.68.51.128:53:53/tcp \
  -v /etc/tailscale-dns/dnsmasq.conf:/etc/dnsmasq.conf:ro \
  4km3/dnsmasq
# (image ENTRYPOINT is `/usr/sbin/dnsmasq --keep-in-foreground`, reads /etc/dnsmasq.conf)

# 3. Tailscale admin -> DNS -> Nameservers -> Add nameserver 100.68.51.128
#    -> toggle "Restrict to domain" -> example.com

# 4. Verify (see Detailed Steps below):
dig @100.68.51.128 svc.example.com +short          # -> 100.68.51.128 (override)
dig @100.68.51.128 other.example.com +short        # -> real public IP (forwarded)
dig svc.example.com +short                          # via MagicDNS -> 100.68.51.128
```

### Detailed Steps

1. **Confirm the service answers on the tailnet IP first.** Before touching DNS, prove the
   reverse proxy is reachable on the tailnet IP and that TLS still works for the public
   hostname: `curl -k --resolve svc.example.com:443:100.68.51.128 https://svc.example.com/status.php`.
   Traefik (and most proxies) bind `0.0.0.0`, so they already listen on `tailscale0`; the
   certificate is issued for the public hostname and remains valid regardless of which IP you
   connect to. If this fails, fix reachability before changing DNS.
2. **Write the dnsmasq config** at `/etc/tailscale-dns/dnsmasq.conf`:
   - `address=/svc.example.com/100.68.51.128` — the override (add one `address=` line per
     host-served service).
   - `no-resolv` — do NOT read the host's `/etc/resolv.conf` (which is MagicDNS and would loop).
   - `server=1.1.1.1` and `server=8.8.8.8` — upstreams so any OTHER `*.example.com` name (and
     everything else) still forwards to its real public record.
3. **Run dnsmasq in Docker bound ONLY to the host's tailnet IP on port 53** (UDP + TCP). Binding
   to `100.68.51.128:53` rather than `0.0.0.0:53` keeps it off the LAN/WAN interfaces so it is
   **not an open resolver**. The `4km3/dnsmasq` image's ENTRYPOINT is
   `/usr/sbin/dnsmasq --keep-in-foreground` and it reads `/etc/dnsmasq.conf`, so mounting the
   config there is all that is required.
4. **Add the restricted nameserver in the Tailscale admin console**: DNS -> Nameservers ->
   Add nameserver `100.68.51.128` -> toggle **Restrict to domain** -> `example.com`. Now tailnet
   devices send only `*.example.com` lookups to the host's dnsmasq; all other domains keep using
   their normal resolvers.
5. **Verify** (all four should hold):
   - `dig @100.68.51.128 svc.example.com +short` -> `100.68.51.128` (override served locally).
   - `dig @100.68.51.128 other.example.com +short` -> that name's real public IP (forwarded upstream).
   - After the restricted nameserver is live, the host's own default resolver
     (MagicDNS `100.100.100.100`) returns the tailnet IP for the overridden name:
     `dig svc.example.com +short` -> `100.68.51.128`.
   - A real upload via the resolved name is LAN-fast. Isolate the two paths with `curl --resolve`
     to compare: `--resolve svc.example.com:443:100.68.51.128` (tailnet) vs
     `--resolve svc.example.com:443:<public-wan-ip>` (hairpin).
6. **To add more services**, append another `address=/svc2.example.com/100.68.51.128` line and
   `docker restart tailscale-dns`.

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
|---------|----------------|---------------|----------------|
| 1 | Looked for the Tailscale admin **"Custom DNS records"** section to point `svc.example.com` at the tailnet IP | The section was not present/findable in the admin UI for this account | Do not depend on "Custom DNS records"; the **restricted nameserver** split-DNS model is always available and achieves the same override tailnet-wide |
| 2 | Considered a router (ASUS RT-AC66U) local-DNS override via its **"Dynamic DNS"** feature | DDNS only *tracks/publishes* the public IP — it cannot serve a local override; and devices running MagicDNS query `100.100.100.100` directly, bypassing the router entirely | A router override cannot reach MagicDNS devices; the override must live on a nameserver Tailscale itself routes queries to |
| 3 | (Design consideration) binding dnsmasq to `0.0.0.0:53` | Would expose an open resolver on LAN/WAN and could collide with other port-53 listeners | Bind ONLY to the tailnet IP (`100.68.51.128:53`) so it is reachable solely over Tailscale and is not an open resolver |

## Results & Parameters

**Before/after (live homelab, apollo, tailnet IP 100.68.51.128, 2026-07):**

| Path | How isolated | DAV upload throughput |
|------|--------------|-----------------------|
| Public WAN hairpin | `curl --resolve svc.example.com:443:<public-wan-ip>` | ~5.7 MB/s (upstream-capped) |
| Tailnet (this fix) | `curl --resolve svc.example.com:443:100.68.51.128` | ~30 MB/s (LAN speed) |

**`/etc/tailscale-dns/dnsmasq.conf`:**

```conf
# Override the self-hosted service's public hostname to the host's tailnet IP.
address=/svc.example.com/100.68.51.128
# Add one address= line per host-served service, then: docker restart tailscale-dns
# Do NOT read the host resolv.conf (it is MagicDNS -> would loop).
no-resolv
# Upstreams so every OTHER *.example.com name still forwards to its real public record.
server=1.1.1.1
server=8.8.8.8
```

**docker run:**

```bash
docker run -d --name tailscale-dns --restart unless-stopped \
  -p 100.68.51.128:53:53/udp -p 100.68.51.128:53:53/tcp \
  -v /etc/tailscale-dns/dnsmasq.conf:/etc/dnsmasq.conf:ro \
  4km3/dnsmasq
```

**Tailscale admin steps:** DNS -> Nameservers -> Add nameserver `100.68.51.128` -> toggle
**Restrict to domain** -> enter `example.com` -> Save.

**Gotchas / operational notes:**

- The `-p 100.68.51.128:53` bind is on the `tailscale0` interface, so on reboot the container
  can race `tailscaled` coming up. The `--restart unless-stopped` policy retries; in practice it
  came back with **0 restarts** and re-bound cleanly.
- A `tailscale` package upgrade restarts `tailscaled`. Verify the container and its tailnet-IP
  binding survive the restart (they did here — split-DNS kept resolving).
- Port 53 must be free on that IP. `systemd-resolved`'s `127.0.0.53` stub listens on loopback,
  not on the tailnet IP, so it does **not** conflict.
- The TLS cert is issued for the public hostname and stays valid over the tailnet path; test with
  `curl -k --resolve` only to isolate the IP, not because the cert is wrong.

## Verified On

| Project | Context | Details |
|---------|---------|---------|
| homelab (apollo) | Live homelab NextCloud, tailnet IP 100.68.51.128, 2026-07 — verified ~30 MB/s tailnet vs ~5.7 MB/s public hairpin | verified-local |
