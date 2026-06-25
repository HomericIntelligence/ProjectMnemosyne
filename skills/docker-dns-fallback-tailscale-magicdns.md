---
name: docker-dns-fallback-tailscale-magicdns
description: "Make Docker container DNS resilient when the host resolver is Tailscale MagicDNS (a single point of failure for every container). Use when: (1) bursts of 'Could not resolve host' / 'Connection could not be established' errors hit MULTIPLE containers at once, (2) the host /etc/resolv.conf has only 'nameserver 100.100.100.100' with systemd-resolved inactive and no fallback, (3) DNS works now but app logs show a historical concentrated outage window that self-recovered."
category: debugging
date: 2026-06-25
version: "1.0.0"
user-invocable: false
verification: verified-local
tags: []
---

# Docker DNS Fallback for Tailscale MagicDNS Single Point of Failure

## Overview

| Field | Value |
|-------|-------|
| **Date** | 2026-06-25 |
| **Objective** | Make Docker container DNS resilient when the host resolver is solely Tailscale MagicDNS (100.100.100.100), so a tailscaled blip no longer takes out DNS for every container at once |
| **Outcome** | Successful — diagnosed a self-recovered ~8h MagicDNS outage and added a Tailscale-independent public DNS fallback at the Docker daemon level |
| **Verification** | verified-local |

## When to Use

- Bursts of DNS failures across MULTIPLE containerized services simultaneously (e.g. Nextcloud logging 600+ `Could not resolve host`, `Connection could not be established with host <smtp>`, `dns_get_record(): A temporary server error occurred`)
- The errors are BURSTY and HISTORICAL — concentrated in a short window on one day, then ZERO for days afterward (a transient outage that self-recovered, not an ongoing misconfiguration)
- The host `/etc/resolv.conf` contains ONLY `nameserver 100.100.100.100` (Tailscale MagicDNS) plus a `ts.net` search domain, with `systemd-resolved` inactive and no second nameserver
- `/etc/docker/daemon.json` has no `dns` key, so containers inherit the host's single resolver via Docker's embedded resolver (127.0.0.11)
- You want DNS resilience for ALL containers in one place rather than per-service compose edits

## Verified Workflow

### Quick Reference

```bash
# 1. Confirm container resolver chain
docker exec <c> cat /etc/resolv.conf        # expect: nameserver 127.0.0.11 (Docker embedded)
docker exec <c> getent hosts example.com    # test resolution from inside the container

# 2. Confirm the host has a SINGLE Tailscale-owned resolver, no fallback
cat /etc/resolv.conf                         # only: nameserver 100.100.100.100 + ts.net search
ls -l /etc/resolv.conf                       # regular file Tailscale rewrites
systemctl is-active systemd-resolved         # inactive
cat /etc/docker/daemon.json                  # no "dns" key
tailscale status                             # Running

# 3. CHECK restart policies BEFORE restarting docker (containers with restart=no stay stopped!)
for c in $(docker ps --format '{{.Names}}'); do \
  echo "$c $(docker inspect -f '{{.HostConfig.RestartPolicy.Name}}' $c)"; done

# 4. Add the daemon DNS fallback (Tailscale FIRST, then public), validate JSON, restart docker
sudo systemctl restart docker

# 5. Manually start any container whose RestartPolicy is "no"
docker start <name>
```

The `dns` value for `/etc/docker/daemon.json` (merge with any existing keys):

```json
{ "dns": ["100.100.100.100", "1.1.1.1", "8.8.8.8"] }
```

### Detailed Steps

1. **Reproduce / scope the symptom.** Identify that the DNS errors hit several containers at once, not just one service. This points at a SHARED resolver, not a per-app bug.
2. **Confirm the failures are historical, not live.** Read the app log TIMESTAMPS and group by hour. If they cluster in a single ~8h window and then drop to ZERO for 2+ days, the resolver had a transient outage that self-recovered. Do not "fix" something that is not currently broken — fix the FRAGILITY instead.
3. **Inspect the container resolver.** `docker exec <c> cat /etc/resolv.conf` shows `nameserver 127.0.0.11` (Docker's embedded resolver on user-defined networks), which forwards to the host's nameservers. `docker exec <c> getent hosts <host>` confirms resolution works now.
4. **Inspect the host resolver.** `cat /etc/resolv.conf` shows ONLY `nameserver 100.100.100.100` (MagicDNS) plus a `ts.net` search domain. `systemctl is-active systemd-resolved` is `inactive`. `cat /etc/docker/daemon.json` has no `dns` key. `tailscale status` is Running. There is NO second resolver to fall through to — Tailscale is a single point of failure for all container DNS.
5. **Confirm it works right now.** Run `getent hosts <host>` ~10 times; 10/10 success proves the failures were transient, not a standing misconfiguration.
6. **Check restart policies FIRST** (see the critical caveat below): list every running container's `RestartPolicy.Name` so you know which ones will NOT auto-restart when docker restarts.
7. **Edit `/etc/docker/daemon.json`** to add the `dns` array with Tailscale's resolver FIRST (so `*.ts.net` still resolves) then public fallbacks. Validate the JSON before saving (e.g. `python3 -m json.tool /etc/docker/daemon.json`).
8. **Restart docker:** `sudo systemctl restart docker`.
9. **Manually start `restart=no` containers** that did not auto-restart: `docker start <name>`.
10. **Verify the fix.** A default-bridge container's `/etc/resolv.conf` now lists all three nameservers, and the public fallbacks are reachable (e.g. PHP `stream_socket_client('udp://1.1.1.1:53', ...)`). A Tailscale DNS blip can no longer take out container DNS.

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
|---------|----------------|---------------|----------------|
| Edit host resolv.conf | Add a fallback `nameserver` line directly to the host `/etc/resolv.conf` | Tailscale OWNS and rewrites `/etc/resolv.conf`, so manual fallback entries get clobbered on the next tailscaled write | Do not hand-edit a Tailscale-managed resolv.conf; put the fallback where Tailscale will not overwrite it |
| Per-container compose `dns:` | Add a `dns:` list to one service's compose file | Works, but only covers that single service; every other container is still exposed to the single-resolver SPOF | Use the Docker daemon level (`daemon.json`) so ALL containers get the fallback in one place, persisting across reboots |
| Tailscale admin-console nameservers | Set global fallback nameservers in the Tailscale admin console | Does NOT help if `tailscaled` / MagicDNS itself is DOWN — then `100.100.100.100` does not answer at all, so admin-console config is moot | True resilience requires a resolver INDEPENDENT of Tailscale (a public IP), not more config behind the same failing daemon |
| Restart docker, walk away | `sudo systemctl restart docker` and assume all containers come back | `restart docker` stops ALL containers and only auto-restarts those whose RestartPolicy is NOT `no` (4 agent containers with `--restart no` stayed STOPPED) | Audit RestartPolicy BEFORE restarting docker; manually `docker start` every `restart=no` container afterward |

## Results & Parameters

**Root cause:** The host `/etc/resolv.conf` is managed solely by Tailscale (`nameserver 100.100.100.100` = MagicDNS), `systemd-resolved` is inactive, and there is NO fallback nameserver. Docker's embedded resolver (127.0.0.11, used on user-defined networks) forwards to the host's nameservers, so when tailscaled / MagicDNS blips (daemon restart, upstream hiccup) EVERY container's DNS fails simultaneously in bursts. There is no second resolver to fall through to.

**The fix** — `/etc/docker/daemon.json` (merge with existing keys; Tailscale FIRST so `*.ts.net` keeps resolving, then public fallbacks):

```json
{ "dns": ["100.100.100.100", "1.1.1.1", "8.8.8.8"] }
```

Then:

```bash
sudo systemctl restart docker
```

**CRITICAL CAVEAT:** `systemctl restart docker` STOPS ALL CONTAINERS and only auto-restarts those whose RestartPolicy is NOT `no` (i.e. `always` / `unless-stopped` / `on-failure`). Containers started with `--restart no` (or no policy) stay STOPPED and must be started manually:

```bash
# Audit BEFORE restarting:
for c in $(docker ps --format '{{.Names}}'); do \
  echo "$c $(docker inspect -f '{{.HostConfig.RestartPolicy.Name}}' $c)"; done
# After restart, start the restart=no ones:
docker start <name>
```

**Verification (verified-local on a live PureOS host):**

- Diagnosed 600+ Nextcloud warnings as a self-recovered ~8h Tailscale MagicDNS outage (errors clustered in one ~8h window, then ZERO for 2+ days).
- At diagnosis time everything resolved and connected fine (10/10 `getent hosts` succeeded) — proving the failures were transient.
- Applied the `daemon.json` fallback; a default-bridge container's `/etc/resolv.conf` then listed all three nameservers and the public fallbacks were reachable (`udp://1.1.1.1:53`).
- 4 agent containers were `restart=no` and required a manual `docker start` after the docker restart.
- Net effect: container DNS now has a Tailscale-independent fallback, so a MagicDNS blip can no longer take out DNS for every container at once.
