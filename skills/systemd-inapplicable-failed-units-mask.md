---
name: systemd-inapplicable-failed-units-mask
description: "Triage systemd units stuck in \"failed\" state that are actually INAPPLICABLE to the hardware/filesystem rather than genuinely broken — the fix is to mask + reset-failed, not repair. Covers the two canonical cases (fwupd-refresh failing on legacy-BIOS machines with \"0 local devices supported\", snapper-boot failing because root is ext4 not btrfs / no 'root' snapper config) and why masking alone leaves a stale failed flag that reset-failed must clear. Use when: (1) systemctl --failed lists units that can never succeed on this hardware, (2) fwupd-refresh fails on a legacy-BIOS host, (3) snapper-boot fails with \"config 'root' does not exist\", (4) a unit still shows failed after being masked."
category: debugging
date: 2026-07-04
version: "1.0.0"
user-invocable: false
verification: verified-local
tags: [systemd, systemctl, failed-units, mask, reset-failed, fwupd, snapper, legacy-bios, btrfs, ext4]
---

# Triage Inapplicable systemd Failed Units: Mask + reset-failed, Don't Repair

## Overview

| Field | Value |
|-------|-------|
| **Date** | 2026-07-04 |
| **Objective** | Clear systemd units stuck in "failed" state that can NEVER succeed on this hardware/filesystem, without wasting time trying to "repair" them |
| **Outcome** | Success — `systemctl --failed` reduced from 2 failing units to `0 loaded units listed` via mask + reset-failed |
| **Verification** | verified-local (host "epimetheus", PureOS 10, kernel 5.10, legacy BIOS, ext4 root) |

## When to Use

- `systemctl --failed` lists units that are **structurally impossible** on this machine (not fixable misconfigs).
- `fwupd-refresh.service` fails on a **legacy-BIOS** host (`WARNING: Firmware can not be updated in legacy BIOS mode`, `0 local devices supported`).
- `snapper-boot.service` fails with `The config 'root' does not exist. Likely snapper is not configured.` on a machine whose **root filesystem is not btrfs**.
- A unit **still shows failed after you masked it** — masking prevents future runs but does not clear the latched failed flag.

## Verified Workflow

The core insight: some "failed" units are not broken — they are attempting work that is
**structurally impossible** on this hardware/filesystem. The correct action is to **mask + reset-failed**
(stop them running and clear the flag), NOT to repair them.

### Quick Reference

```bash
# 1. Diagnose — confirm the unit is truly inapplicable (not a fixable failure).
#    Read the real ExecStart and run it manually; journalctl often shows "No entries".
systemctl cat fwupd-refresh.service     # see the actual ExecStart
fwupdmgr refresh --force                # manual run → "0 local devices supported" on legacy BIOS
systemctl cat snapper-boot.service
snapper list-configs                    # EMPTY → no configs
findmnt -no FSTYPE /                    # ext4 → snapper needs btrfs, so 'root' config can't exist

# 2. Mask (stronger than disable — blocks any dependency/timer from re-triggering).
sudo systemctl disable --now fwupd-refresh.timer 2>/dev/null   # stop the timer if present
sudo systemctl mask fwupd-refresh.service
sudo systemctl disable --now snapper-boot.service
sudo systemctl mask snapper-boot.service

# 3. CRITICAL: masking does NOT clear the latched failed state — clear it explicitly.
sudo systemctl reset-failed fwupd-refresh.service snapper-boot.service

# 4. Verify.
systemctl --failed                      # → "0 loaded units listed"

# Reversible at any time:
# sudo systemctl unmask fwupd-refresh.service snapper-boot.service
```

### Detailed Steps

1. **Confirm inapplicability before masking.** Do not mask a unit until you have proven it can
   never work on this host. Run the unit's actual `ExecStart` command manually (`systemctl cat <unit>`
   to see it) and read the real error. `journalctl -u <unit>` sometimes reports "No entries" for these
   failures, so the manual run is more reliable than the journal.

2. **Case 1 — fwupd-refresh on legacy BIOS.** Running `fwupdmgr refresh --force` manually shows the
   metadata refresh itself **succeeds** (`Successfully downloaded new metadata`) but emits
   `WARNING: Firmware can not be updated in legacy BIOS mode` and `0 local devices supported`.
   fwupd delivers firmware via UEFI capsules; a legacy-BIOS boot has no updatable devices, so the unit
   exits non-zero with no job to do. Not repairable — inapplicable to the hardware. (Reversible if the
   machine later switches to UEFI.)

3. **Case 2 — snapper-boot on ext4 root.** The unit runs
   `snapper --config root create --cleanup-algorithm number --description "boot"`. It fails with
   `The config 'root' does not exist. Likely snapper is not configured.` Diagnosis: `snapper list-configs`
   is **empty** (no configs) and `findmnt -no FSTYPE /` returns `ext4`. Snapper snapshots require btrfs;
   the root filesystem is ext4, so a 'root' config cannot meaningfully exist and snapshots were never
   possible. Not a broken safety net — snapshotting was never available on this fs. (This host's btrfs
   volumes were `/home` and `/opt`, but this unit targets `root`.)

4. **Mask, not just disable.** `mask` symlinks the unit to `/dev/null` so no dependency or timer can
   re-trigger it, which is stronger than `disable`. Stop any associated timer first
   (`systemctl disable --now fwupd-refresh.timer`).

5. **Clear the latched failed flag.** After masking, `systemctl --failed` **still** listed both units as
   `masked failed failed` — masking prevents future runs but does NOT clear the failed state latched from
   the last run. Run `systemctl reset-failed <units>` to clear it immediately. (A reboot would also clear
   it, but `reset-failed` is immediate.)

6. **Verify** `systemctl --failed` reports `0 loaded units listed`.

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
|---------|----------------|---------------|----------------|
| Try to repair fwupd-refresh so it stops failing | Rerunning / reconfiguring fwupd | Legacy-BIOS host has "0 local devices supported" — fwupd (UEFI capsule) has nothing to update; the refresh already succeeds, the unit just exits non-zero | Mask inapplicable units instead of repairing; confirm inapplicability by running the command manually |
| Repair snapper-boot / create a 'root' config | Expecting snapper to snapshot / configuring it | Root filesystem is ext4; snapper needs btrfs, so a 'root' config can't meaningfully exist | Check `findmnt -no FSTYPE /` — snapper is inapplicable on non-btrfs roots; mask the unit |
| Assume masking clears the failed state | `systemctl mask` then `systemctl --failed` | Masked units still showed "masked failed failed" — the failed flag from the last run persists | Run `systemctl reset-failed <units>` after masking to clear the latched state |

## Results & Parameters

**Diagnosis commands (confirm inapplicability first):**

```bash
systemctl cat fwupd-refresh.service      # inspect actual ExecStart
fwupdmgr refresh --force                 # → "0 local devices supported" (legacy BIOS)
systemctl cat snapper-boot.service
snapper list-configs                     # → empty (no configs)
findmnt -no FSTYPE /                     # → ext4 (snapper needs btrfs)
```

**Fix commands:**

```bash
sudo systemctl disable --now fwupd-refresh.timer 2>/dev/null
sudo systemctl mask fwupd-refresh.service
sudo systemctl disable --now snapper-boot.service
sudo systemctl mask snapper-boot.service
sudo systemctl reset-failed fwupd-refresh.service snapper-boot.service
```

**Expected end state:**

```text
$ systemctl --failed
0 loaded units listed.
```

**Reverse (if hardware/fs changes later):**

```bash
sudo systemctl unmask fwupd-refresh.service snapper-boot.service
```

## Verified On

| Project | Context | Details |
|---------|---------|---------|
| epimetheus (PureOS 10, kernel 5.10, legacy BIOS, ext4 root) | Boot-time `systemctl --failed` triage | fwupd-refresh (UEFI-only firmware) and snapper-boot (btrfs-only snapshots) masked + reset-failed → 0 failed units |
