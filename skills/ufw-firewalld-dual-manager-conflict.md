---
name: ufw-firewalld-dual-manager-conflict
description: "Diagnose and fix a Linux host running TWO firewall managers at once (ufw AND firewalld both active), which produces nondeterministic netfilter rule ordering and can silently break DNS/outbound connectivity. Also covers why firewalld is present on Debian/PureOS (pulled by the pureos-standard metapackage, so it cannot be apt-removed cleanly) and the correct disable-not-uninstall fix. Use when: (1) outbound/DNS breaks after adding ufw, (2) `systemctl is-active ufw firewalld` shows both active, (3) deciding ufw vs firewalld on a Debian-family host, (4) a firewall package can't be removed because a distro metapackage depends on it."
category: debugging
date: 2026-07-04
version: "1.0.0"
verification: verified-local
user-invocable: false
tags: [ufw, firewalld, firewall, netfilter, dns, connectivity, debian, pureos, nftables, iptables]
---

# UFW / Firewalld Dual-Manager Conflict

## Overview

| Field | Value |
| ------- | ------- |
| **Date** | 2026-07-04 |
| **Objective** | Diagnose and fix a Linux host running both `ufw` and `firewalld` simultaneously, which yields nondeterministic netfilter rule ordering and can silently break DNS/outbound connectivity |
| **Outcome** | Detected the dual-manager conflict on host `epimetheus` (PureOS 10 Byzantium, kernel 5.10), disabled `firewalld` without uninstalling it (metapackage dependency), and standardized on `ufw` alone — connectivity restored |
| **Verification** | verified-local |

An AI agent (Claude) lost outbound connectivity shortly after `ufw` was configured on the host. The instinct was to blame the newly added `ufw` inbound rules, but the `ufw` default policy was `allow outgoing` — which permits all outbound traffic, and stateful conntrack automatically allows replies to those connections. The `ufw` rules were never the problem.

The real root cause: **both `ufw` and `firewalld` were active at the same time.** Two firewall managers both writing into netfilter produce undefined rule ordering, and `firewalld`'s default-zone behavior can reject or mangle traffic, which broke DNS and outbound. The user had effectively *switched* firewalls (firewalld → ufw) without realizing firewalld was already running since first boot — they did not add a firewall to a host that had none.

## When to Use

- Outbound connectivity or DNS resolution breaks shortly after configuring or enabling `ufw`.
- `systemctl is-active ufw firewalld` reports `active` for **both** managers.
- You are deciding whether to standardize on `ufw` or `firewalld` on a Debian-family host (Debian, Ubuntu, PureOS).
- A firewall package (or any distro-default package) cannot be cleanly `apt remove`d because a distribution metapackage depends on it.
- An AI agent or automated tool loses network access after a firewall change and you need to distinguish "rules blocked it" from "two firewalls are fighting."

## Verified Workflow

### 1. Detect the dual-manager conflict FIRST (before touching any rules)

```bash
systemctl is-active ufw firewalld
```

If this prints `active` twice, you have two firewall managers running concurrently. Stop here — do not start editing `ufw` rules. The conflict, not the rules, is almost certainly the cause of nondeterministic breakage.

### 2. Understand why firewalld is even installed (Debian/PureOS)

On PureOS/Debian, `firewalld` is typically **not** user-installed. Verify:

```bash
apt-mark showmanual | grep -x firewalld            # absent => it came in as a dependency
apt-cache rdepends --installed firewalld           # shows pureos-standard depends on it
```

`pureos-standard` is the base-install metapackage. Because it depends on `firewalld`, running `apt remove firewalld` would try to remove `pureos-standard` too — which is undesirable and can cause upgrade problems later. This is why you must **disable, not uninstall.**

### 3. Apply the fix: disable (do not uninstall) the redundant firewall

```bash
sudo systemctl disable --now firewalld     # stop it now AND prevent it starting at boot
```

This stops `firewalld` immediately and disables it at boot, so it never touches netfilter again — while leaving the package installed to satisfy the `pureos-standard` metapackage dependency. It is fully reversible (`systemctl enable --now firewalld`).

Run exactly ONE firewall manager. Here that is `ufw`.

### 4. Verify the clean end-state

```bash
systemctl is-active firewalld      # expect: inactive
systemctl is-enabled firewalld     # expect: disabled
systemctl is-active ufw            # expect: active
systemctl is-enabled ufw           # expect: enabled
# Confirm connectivity is restored:
getent hosts api.anthropic.com     # DNS resolves
curl -sS -o /dev/null -w '%{http_code}\n' https://api.anthropic.com   # outbound TCP 443 succeeds
curl -sS -o /dev/null -w '%{http_code}\n' https://github.com          # outbound TCP 443 succeeds
```

### 5. Inspect actual rules with the right backend tool

If `ufw` uses the legacy **iptables** backend, `nft list ruleset` may fail with "command not found" because the nftables CLI is not installed. Use iptables instead:

```bash
sudo iptables -S            # dump rules in a re-applyable form
sudo iptables -L -n -v      # verbose numeric listing with counters
```

### ufw vs firewalld guidance

- `ufw` is the native/expected front-end on Debian/Ubuntu/PureOS. `firewalld` is the RHEL/Fedora default.
- For a fixed-location workstation or server with static interfaces (e.g. LAN + Tailscale) and simple rules, `ufw`'s linear allow/deny model is simpler and less surprising.
- `firewalld`'s zone model earns its complexity on laptops that roam between trusted/untrusted networks, or on complex multi-homed routers.
- Recommendation for this environment: **standardize on `ufw`, keep `firewalld` disabled, and NEVER run both.**

### Key insight about `default allow outgoing`

A `ufw` `default allow outgoing` policy does **not** block browsing, DNS, or AI-agent outbound traffic. Stateful conntrack automatically allows replies to your outbound connections. If outbound breaks under a ufw-only host, suspect the DNS resolver / Tailscale MagicDNS or a leftover second firewall — not the outgoing policy.

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
| ------- | ------- | ------- | ------- |
| Blame the ufw inbound rules for Claude losing connectivity | Reviewing and loosening the `ufw` rules | `ufw` default was `allow outgoing`, so outbound was never blocked; the real cause was `firewalld` running concurrently | Check `systemctl is-active ufw firewalld` for a dual-manager conflict before touching rules; suspect DNS / a second firewall for outbound breakage |
| `apt remove firewalld` to eliminate the conflict | Uninstalling the `firewalld` package | The `pureos-standard` metapackage depends on `firewalld`, so removal drags the metapackage out with it | Use `systemctl disable --now firewalld` (disable, don't uninstall) for distro-default packages a metapackage requires |
| `nft list ruleset` to inspect the effective firewall | The `nft` CLI | The nftables CLI was not installed; `ufw` used the iptables backend | Use `iptables -S` / `iptables -L -n -v` when `nft` is absent |

## Results & Parameters

Verified-local on host `epimetheus` (PureOS 10 Byzantium, kernel 5.10).

**Detection (run first):**
```bash
systemctl is-active ufw firewalld          # both "active" => dual-manager conflict
```

**Fix:**
```bash
sudo systemctl disable --now firewalld     # disable + stop; do NOT uninstall
```

**Why firewalld is installed (investigation):**
```bash
apt-mark showmanual | grep -x firewalld    # absent => came as a dependency, not user-installed
apt-cache rdepends --installed firewalld   # pureos-standard metapackage depends on it
```

**Verification:**
```bash
systemctl is-active firewalld              # inactive
systemctl is-enabled firewalld             # disabled
systemctl is-active ufw                    # active
systemctl is-enabled ufw                   # enabled
getent hosts api.anthropic.com             # DNS resolves
curl -sS -o /dev/null -w '%{http_code}\n' https://api.anthropic.com   # 200/4xx (TCP 443 reachable)
curl -sS -o /dev/null -w '%{http_code}\n' https://github.com          # 200/4xx (TCP 443 reachable)
```

**Rule inspection when nft is absent:**
```bash
sudo iptables -S
sudo iptables -L -n -v
```

**Expected clean end-state:** `ufw` active + enabled; `firewalld` inactive + disabled; DNS resolves; outbound TCP 443 to `api.anthropic.com` and `github.com` succeeds; exactly one firewall manager touching netfilter.
