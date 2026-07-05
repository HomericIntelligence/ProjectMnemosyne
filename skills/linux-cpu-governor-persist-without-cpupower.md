---
name: linux-cpu-governor-persist-without-cpupower
description: "Set and persist the Linux CPU frequency scaling governor (e.g. performance) across reboots on a system with NO cpufrequtils/linux-cpupower package installed, using direct sysfs writes plus a minimal systemd oneshot unit — works under the intel_pstate driver without needing any governor-management package. Use when: (1) a host is sitting on the wrong scaling_governor (e.g. powersave when it should be performance) and `dpkg -l | grep -iE 'cpufrequtils|cpupower'` returns empty, (2) you want two servers to have matching CPU throughput behavior, (3) you need the setting to survive a reboot without adding new package surface."
category: tooling
date: 2026-07-04
version: "1.0.0"
user-invocable: false
verification: verified-local
tags: []
---

# Linux CPU Governor: Persist Without cpupower/cpufrequtils

## Overview

| Field | Value |
|-------|-------|
| **Date** | 2026-07-04 |
| **Objective** | Match an always-on homelab server's CPU governor (`powersave`) to a sibling server's (`performance`) for consistent throughput, and make the change survive reboots, on a host with no `cpufrequtils`/`linux-cpupower` package installed |
| **Outcome** | Successful — direct sysfs writes applied `performance` immediately on all cores; a minimal systemd oneshot unit reapplies it at every boot with zero new package surface |
| **Verification** | verified-local |

## When to Use

- `cat /sys/devices/system/cpu/cpu0/cpufreq/scaling_governor` shows an unwanted governor (e.g. `powersave`) and you want `performance` (or vice versa).
- `dpkg -l | grep -iE 'cpufrequtils|cpupower'` returns nothing — no governor-management tooling is installed, which is why nothing has ever pinned a governor at boot.
- The driver is `intel_pstate` (`cat /sys/devices/system/cpu/cpu0/cpufreq/scaling_driver`) and you've heard (incorrectly) that you need `cpupower`/`cpufrequtils` installed before you can even change the governor.
- You want the setting to survive a reboot without adding a new package whose driver-model assumptions (`cpufrequtils` historically assumes `acpi-cpufreq`) may not match `intel_pstate` cleanly.
- You're aligning CPU behavior across two or more homelab/fleet servers and want a portable, driver-agnostic mechanism (plain systemd unit + sysfs) rather than a distro-specific package.

## Verified Workflow

> **Caveat:** This workflow was verified locally — the governor change and the systemd unit's
> active/enabled state were confirmed immediately after applying them. It was **not** verified
> across an actual physical reboot: this host has LUKS-encrypted boot requiring physical presence
> to unlock, and no reboot was performed this session. The reboot-survival claim rests on
> standard, well-understood systemd semantics (`RemainAfterExit=yes` + `WantedBy=multi-user.target`
> guarantee the `ExecStart` command runs once at every boot and the unit is reported active
> afterward), not on an observed reboot. Treat the "survives reboot" claim as high-confidence but
> not empirically confirmed end-to-end.

### Quick Reference

```bash
# 1) Apply immediately — no package needed
for f in /sys/devices/system/cpu/cpu*/cpufreq/scaling_governor; do
  echo performance | sudo tee "$f" > /dev/null
done
cat /sys/devices/system/cpu/cpu*/cpufreq/scaling_governor   # confirm all cores show "performance"

# 2) Persist across reboots WITHOUT installing cpufrequtils/cpupower
sudo tee /etc/systemd/system/cpu-performance-governor.service > /dev/null <<'EOF'
[Unit]
Description=Set CPU scaling governor to performance
After=multi-user.target

[Service]
Type=oneshot
ExecStart=/bin/sh -c 'for f in /sys/devices/system/cpu/cpu*/cpufreq/scaling_governor; do echo performance > "$f"; done'
RemainAfterExit=yes

[Install]
WantedBy=multi-user.target
EOF

sudo systemctl daemon-reload
sudo systemctl enable --now cpu-performance-governor.service
systemctl status cpu-performance-governor.service --no-pager   # confirm active (exited)
systemctl is-enabled cpu-performance-governor.service           # confirm "enabled"
```

### Detailed Steps

1. **Verify what's available and what's driving frequency scaling before acting.**
   - `cat /sys/devices/system/cpu/cpu0/cpufreq/scaling_available_governors` — confirms which
     governors this hardware supports (e.g. `performance powersave`).
   - `cat /sys/devices/system/cpu/cpu0/cpufreq/scaling_driver` — confirms the active driver
     (e.g. `intel_pstate`).
   - `dpkg -l | grep -iE 'cpufrequtils|cpupower'` — if this is empty, no governor-management
     package is installed, which explains why the governor was never pinned at boot.

2. **Apply the governor directly via sysfs — no package required.** Writing to
   `/sys/devices/system/cpu/cpu*/cpufreq/scaling_governor` works fine under `intel_pstate`
   without the driver needing to be in a special "passive" mode. The common misconception is
   that `cpupower`/`cpufrequtils` are required to change the governor at all; they are not —
   they're only one of several ways to make the change *persist*.

3. **Persist without installing `cpufrequtils`/`cpupower`.** Write a minimal systemd oneshot
   unit (see Quick Reference) that reapplies the same sysfs writes at every boot. `Type=oneshot`
   plus `RemainAfterExit=yes` means the unit runs the `ExecStart` command once and then reports
   `active (exited)` rather than failing/restarting; `WantedBy=multi-user.target` plus
   `systemctl enable` wires it into the normal boot target.

4. **Confirm both the immediate effect and the persistence mechanism.**
   - `cat /sys/devices/system/cpu/cpu*/cpufreq/scaling_governor` → `performance` on every core.
   - `systemctl status cpu-performance-governor.service --no-pager` → `active (exited)`.
   - `systemctl is-enabled cpu-performance-governor.service` → `enabled`.
   - A genuine reboot test was not performed this session (LUKS-encrypted boot requires
     physical presence) — see the caveat above.

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
|---------|----------------|---------------|-----------------|
| Install `cpufrequtils` to manage the governor | Considered installing the `cpufrequtils` package to set/persist the governor | Not chosen: adds a package with a driver-model mismatch history vs `intel_pstate` (`cpufrequtils` historically assumes `acpi-cpufreq`), and is unnecessary | You don't need `cpufrequtils`\/`cpupower` at all to change OR persist the governor under `intel_pstate`; direct sysfs writes plus a oneshot systemd unit suffice, with zero new package surface |

## Results & Parameters

**Exact commands (copy-paste):**

```bash
# Apply now (all cores)
for f in /sys/devices/system/cpu/cpu*/cpufreq/scaling_governor; do
  echo performance | sudo tee "$f" > /dev/null
done

# Persist via systemd oneshot (no cpufrequtils/cpupower package)
sudo systemctl daemon-reload
sudo systemctl enable --now cpu-performance-governor.service
```

**Environment observed:**

| Item | Value |
|------|-------|
| Kernel | 4.19 |
| CPU | Intel i7-8565U |
| Scaling driver | `intel_pstate` |
| Available governors | `performance powersave` |
| Governor-management package installed | None (`cpufrequtils`\/`cpupower` both absent) |
| Confirmed result | All 8 cores report `performance`; `cpu-performance-governor.service` is `active (exited)` and `enabled` |

**Why this approach over installing a package:** avoids adding `cpufrequtils` (which on some
distro/kernel combos fights with `intel_pstate`'s own internal governor management —
`cpufrequtils` historically assumes the `acpi-cpufreq` driver's model). A plain systemd unit
writing directly to sysfs is driver-agnostic and has zero new package surface.

## Verified On

| Project | Context | Details |
|---------|---------|---------|
| apollo homelab | Aligning CPU governor between two always-on homelab servers (2026-07) | `performance` applied immediately on all 8 cores; `cpu-performance-governor.service` confirmed `active (exited)` + `enabled` via systemd, without installing `cpufrequtils`\/`cpupower`; reboot-survival not empirically observed this session (LUKS boot requires physical presence) |
