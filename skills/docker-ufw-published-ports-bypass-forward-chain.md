---
name: docker-ufw-published-ports-bypass-forward-chain
description: "Docker published ports (docker run -p / compose ports:) bypass ufw's normal INPUT-chain allow/deny rules entirely, via the DOCKER-USER/FORWARD chain. Use when: (1) a ufw deny/allow rule doesn't seem to affect a containerized service, (2) auditing firewall coverage for a Docker host, (3) trying to restrict a docker-published port to a trusted interface/VPN mesh."
category: debugging
date: 2026-07-04
version: "1.0.0"
user-invocable: false
verification: verified-local
tags: [docker, ufw, iptables, firewall, networking]
---

# Docker Published Ports Bypass ufw's INPUT Chain

## Overview

| Field | Value |
|-------|-------|
| **Date** | 2026-07-04 |
| **Objective** | Determine why a homelab server's ufw firewall rules had no effect on Docker-published container ports, and find the correct way to restrict them. |
| **Outcome** | Root cause confirmed live via iptables inspection; a working DOCKER-USER-chain restriction pattern was designed and reviewed (not applied in this instance since the ports were intentionally kept public). |
| **Verification** | verified-local |
| **History** | none yet |

## When to Use

- A `ufw allow`/`ufw deny` rule for a port doesn't seem to have any effect, and that port is published by a Docker container (`docker run -p` or compose `ports:`).
- Auditing a Docker host's firewall coverage — need to know which ports are actually filtered by ufw vs. which are exposed regardless of ufw's rules.
- Restricting a docker-published port (e.g. an admin dashboard, an SSH-over-git port) to a trusted interface (a VPN mesh, or a LAN subnet) without touching the container's own publish config.

## Verified Workflow

### Quick Reference

```bash
# 1. Confirm the bypass -- is DOCKER-USER just a no-op RETURN?
sudo iptables -L DOCKER-USER -n --line-numbers
sudo iptables -L FORWARD -n --line-numbers | head -20

# 2. Restrict a published port to one trusted interface (order matters: DROP first, then ACCEPT)
sudo iptables -I DOCKER-USER 1 -p tcp --dport <PORT> -j DROP
sudo iptables -I DOCKER-USER 1 -i <trusted-iface> -p tcp --dport <PORT> -j ACCEPT

# 3. Verify
sudo iptables -L DOCKER-USER -n --line-numbers
```

### Detailed Steps

1. **Understand the architecture.** Docker manages its own iptables rules independent of ufw. Publishing a container port inserts a DNAT rule in the `nat` table's `PREROUTING` chain, and traffic destined for that port is *forwarded* into the container's network namespace via the `filter` table's `FORWARD` chain -- specifically through `DOCKER-USER` -> `DOCKER-ISOLATION-STAGE-1` -> a per-Docker-network `DOCKER` chain that unconditionally `ACCEPT`s the mapped port. None of this touches the `INPUT` chain, which is the only chain `ufw allow`/`ufw deny` commands modify. So a docker-published port is reachable regardless of any ufw rule, even under ufw's default-deny-incoming policy.

2. **Confirm the bypass empirically before assuming it applies.** Run:

   ```bash
   sudo iptables -L DOCKER-USER -n --line-numbers
   sudo iptables -L FORWARD -n --line-numbers | head -20
   ```

   If `DOCKER-USER` contains only a single `RETURN` rule (Docker's unconfigured default) and `FORWARD`'s first jump target is `DOCKER-USER`, nothing is filtering docker-published ports before they reach Docker's own `ACCEPT` rules.

3. **Distinguish host-bound services from docker-published ones.** A process binding directly to a host socket (sshd, Samba, a bare-metal NFS server, Cockpit, etc. -- anything NOT started via `docker run -p`) genuinely IS governed by ufw's `INPUT` chain as expected. The bypass is specific to Docker's forwarded/published ports; don't over-generalize the finding to "ufw doesn't work on this host."

4. **If restriction is actually wanted, add rules directly to `DOCKER-USER`** -- never a plain `ufw allow/deny`, since that only ever touches `INPUT`:

   ```bash
   sudo iptables -I DOCKER-USER 1 -p tcp --dport <PORT> -j DROP
   sudo iptables -I DOCKER-USER 1 -i <trusted-iface> -p tcp --dport <PORT> -j ACCEPT
   ```

   Order matters: insert the `DROP` rule first, then the `ACCEPT` rule (also at position 1). Each `-I chain 1` push shifts existing rules down, so doing DROP-then-ACCEPT results in a final chain order of ACCEPT (evaluated first, matches the trusted interface) -> DROP (catches everyone else) -> the original `RETURN` (unaffected, so other ports meant to stay public still fall through to Docker's own ACCEPT).

5. **Persist across reboots via ufw's own lifecycle, not a separate mechanism.** Raw `iptables -I` rules vanish on reboot. Rather than adding a dependency on `iptables-persistent`, append an `iptables-restore`-format block to `/etc/ufw/after.rules` (which ufw reapplies on every boot/reload):

   ```text
   *filter
   :DOCKER-USER - [0:0]
   -A DOCKER-USER -i <trusted-iface> -p tcp --dport <PORT> -j ACCEPT
   -A DOCKER-USER -p tcp --dport <PORT> -j DROP
   -A DOCKER-USER -j RETURN
   COMMIT
   ```

   Read the existing `after.rules` file first (needs root to read) to see where other tables/chains are already declared, so you don't create a duplicate `*filter`/`COMMIT` block.

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
|---------|-----------------|----------------|-------------------|
| Assumed plain ufw rules would govern docker-published ports | Planned to restrict Traefik/Gitea's docker-published ports the same way as host-bound services, via `ufw allow`/`ufw deny` | ufw rules only modify the `INPUT` chain; docker-published ports are matched in `FORWARD` via `DOCKER-USER`, never reaching `INPUT` | Always check `iptables -L DOCKER-USER -n` before assuming a ufw rule will affect a containerized service |
| Considered a third-party `ufw-docker` helper script | Community tooling exists to automate this fix | Adds an extra trust surface/dependency for a homelab; the manual `DOCKER-USER` + `after.rules` pattern is a handful of lines and easier to audit | For a small number of ports, hand-writing the `DOCKER-USER` rules is safer and more transparent than installing a third-party script |

## Results & Parameters

Diagnostic output confirming the bypass (before any fix):

```text
$ sudo iptables -L DOCKER-USER -n --line-numbers
Chain DOCKER-USER (1 references)
num  target     prot opt source               destination
1    RETURN     all  --  0.0.0.0/0            0.0.0.0/0

$ sudo iptables -L FORWARD -n --line-numbers | head -5
Chain FORWARD (policy DROP)
num  target     prot opt source               destination
1    DOCKER-USER  all  --  0.0.0.0/0            0.0.0.0/0
2    DOCKER-ISOLATION-STAGE-1  all  --  0.0.0.0/0            0.0.0.0/0
3    ACCEPT     all  --  0.0.0.0/0            0.0.0.0/0            ctstate RELATED,ESTABLISHED
```

Restriction commands to trust one interface (e.g. a VPN mesh) and drop everyone else on a given port:

```bash
sudo iptables -I DOCKER-USER 1 -p tcp --dport 8181 -j DROP
sudo iptables -I DOCKER-USER 1 -i tailscale0 -p tcp --dport 8181 -j ACCEPT
```

## Verified On

| Project | Context | Details |
|---------|---------|---------|
| Homelab server audit | Auditing a Docker host (Traefik, Gitea, Nextcloud stacks) running ufw, comparing firewall coverage against a sibling server | Confirmed via live `iptables -L DOCKER-USER`/`FORWARD` inspection; restriction commands drafted and reviewed but not applied since the ports were intentionally kept public in this case |
