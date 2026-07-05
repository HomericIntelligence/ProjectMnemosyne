---
name: debugging-ufw-systemd-active-status-misleading
description: "systemctl is-active ufw can report active (exited) for weeks while the firewall enforces zero rules, because ufw.service's ExecStart always exits 0. Use when: (1) auditing a host's firewall/security posture and systemctl reports ufw as active, (2) ports that should be blocked are reachable despite ufw appearing enabled, (3) verifying whether a systemd oneshot/exited unit's active status actually reflects the application-level state it manages."
category: debugging
date: 2026-07-04
version: "1.0.0"
user-invocable: false
verification: verified-local
tags: []
---

# ufw systemd "active" Status Is Misleading — Check ENABLED, Not systemctl

## Overview

| Field | Value |
|-------|-------|
| **Date** | 2026-07-04 |
| **Objective** | Determine whether a homelab host's firewall (ufw) was actually enforcing rules during a security audit |
| **Outcome** | Successful — found `systemctl is-active ufw` reported "active" for weeks while `ENABLED=no` in `/etc/ufw/ufw.conf` meant zero enforcement; fixed with `sudo ufw enable` |
| **Verification** | verified-local |

## When to Use

- Auditing a Debian/Ubuntu-family host's firewall as part of a security checklist and `systemctl is-active ufw` (or `systemctl status ufw`) reports "active" or "active (exited)"
- Ports that should be firewalled (e.g. Samba 445/139, NFS 2049/111, admin consoles like Cockpit on 9090) are reachable from the network despite ufw appearing enabled
- More generally: verifying whether a systemd unit's "active" status actually reflects the real, application-level enabled/disabled state of the tool it wraps, versus just meaning "the last ExecStart process exited 0"
- Before writing new firewall rules from scratch — check whether rules were already staged in a prior, unfinished setup attempt

## Verified Workflow

### Quick Reference

```bash
# Do NOT trust this alone — it can lie for oneshot/exited units:
systemctl is-active ufw            # -> "active" even when ufw enforces nothing

# Authoritative checks instead:
sudo ufw status verbose            # prints "Status: inactive" if truly disabled
grep ENABLED /etc/ufw/ufw.conf     # ENABLED=no means no enforcement, regardless of systemd

# Before writing new rules, check what's already staged:
grep -v '^#\|^\*\|^COMMIT\|^:' /etc/ufw/user.rules

# Fix:
sudo ufw enable
sudo ufw status verbose            # re-verify "Status: active" with expected rules/policies
```

### Detailed Steps

1. **Don't stop at `systemctl is-active ufw`.** It reports "active (exited)" because `ufw.service`'s `ExecStart` runs `/lib/ufw/ufw-init start quiet`, which exits 0 regardless of whether ufw is actually enabled. systemd only records that the ExecStart process exited successfully — it has no idea whether ufw's own enable/disable flag is set.

2. **Run the tool's own status command**: `sudo ufw status verbose`. If ufw is truly disabled, this prints literally `Status: inactive`, contradicting what `systemctl is-active` showed.

3. **Confirm directly in the config file**: `cat /etc/ufw/ufw.conf` and check the `ENABLED=` field. `ENABLED=no` means the firewall enforces nothing at the packet-filter level, no matter what systemd reports.

4. **Before writing any new rules, check for pre-staged ones**: `grep -v '^#\|^\*\|^COMMIT\|^:' /etc/ufw/user.rules`. A "disabled" firewall does not imply an empty rule set — an earlier, unfinished setup attempt may have already staged rules (e.g. an SSH allow rule, a full-trust rule for a VPN mesh interface) that just need to be activated.

5. **Enable the firewall**: `sudo ufw enable`. This flips `ENABLED=yes` in `ufw.conf` and actually loads the rules into the packet filter.

6. **Re-verify**: `sudo ufw status verbose` should now show `Status: active` along with the expected rules and default policies (e.g. deny incoming, allow outgoing, deny routed).

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
|---------|----------------|---------------|----------------|
| Trusting `systemctl is-active ufw` | Used `systemctl is-active ufw` as sufficient proof the firewall was enforcing rules during a security audit | It reported "active (exited)" for weeks while `ENABLED=no` in `ufw.conf` meant zero enforcement — all ports (Samba 445/139, NFS 2049/111, Cockpit 9090) were fully open to the internet. `ufw.service`'s `ExecStart` (`/lib/ufw/ufw-init start quiet`) exits 0 regardless of the `ENABLED` flag | systemd "active" for a oneshot/exited unit only means the ExecStart process exited 0 — it says nothing about the application-level state the unit nominally manages. Always use the tool's own status command (`ufw status verbose`) or check its config file directly |

## Results & Parameters

**Where the real state lives:**

| Signal | Command | Reliability |
|--------|---------|-------------|
| systemd unit state | `systemctl is-active ufw` | Unreliable — always "active (exited)" once started once, regardless of enable/disable |
| ufw's own status | `sudo ufw status verbose` | Authoritative — prints `Status: active` or `Status: inactive` |
| ufw config file | `grep ENABLED /etc/ufw/ufw.conf` | Authoritative — `ENABLED=yes` or `ENABLED=no` |

**Why systemd is fooled — `ufw.service` ExecStart:**

```ini
[Service]
Type=oneshot
ExecStart=/lib/ufw/ufw-init start quiet
ExecStop=/lib/ufw/ufw-init stop
RemainAfterExit=yes
```

`/lib/ufw/ufw-init start quiet` exits 0 whether or not `ENABLED=yes` is set in `/etc/ufw/ufw.conf`. Combined with `RemainAfterExit=yes`, this is why `systemctl is-active` permanently shows "active (exited)" after the first boot, independent of the actual firewall state.

**Pre-staged rules check (before assuming you need to write rules from scratch):**

```bash
grep -v '^#\|^\*\|^COMMIT\|^:' /etc/ufw/user.rules
```

In this case this turned up an already-present SSH allow rule and a full-trust rule for a VPN mesh interface from an earlier, unfinished setup attempt — no new rules needed to be written before enabling.

**Before/after `ufw status verbose` shape:**

```text
# Before (despite systemctl is-active ufw == "active"):
Status: inactive

# After `sudo ufw enable`:
Status: active
Logging: on (low)
Default: deny (incoming), allow (outgoing), deny (routed)
...rules listed here (e.g. SSH allow, trusted-interface allow)...
```

## Verified On

| Project | Context | Details |
|---------|---------|---------|
| apollo homelab | Firewall/security checklist audit | `systemctl is-active ufw` reported active for weeks with `ENABLED=no`; all ports (Samba, NFS, Cockpit 9090) exposed. Fixed via `sudo ufw enable`, re-verified with `sudo ufw status verbose` |
