---
name: sata-drive-bus-disconnect-diagnosis
description: "Diagnose and triage a SATA drive that has dropped off the bus (capacity=0, DID_BAD_TARGET on every command). Use when: (1) dmesg shows 'detected capacity change from N to 0' on a drive that was previously working, (2) smartctl returns 'A mandatory SMART command failed', (3) wipefs/sgdisk hit 'Read error 5/22' on raw device access."
category: debugging
date: 2026-05-18
version: "1.0.0"
user-invocable: false
verification: verified-local
tags: [sata, scsi, smartctl, drive-failure, did-bad-target, dmesg, reallocated-sectors, ahci]
---

## Overview

| Field | Value |
|-------|-------|
| Objective | Determine whether a drive that's gone offline (capacity=0, all SCSI cmds fail) is recoverable, transiently failing, or end-of-life |
| Outcome | Successful triage. The drive was brought back online via SCSI delete+rescan, but SMART then revealed 64,216 reallocated sectors and "Drive failure expected in less than 24 hours" — drive retired |
| Verification | verified-local |

## When to Use

- `dmesg` shows `sd X:Y:Z:W: [sdN] detected capacity change from <size> to 0`
- Every SCSI command on the drive returns `hostbyte=DID_BAD_TARGET`
- `blockdev --getsize64 /dev/sdN` returns `0` for a drive that should be present
- `smartctl -H /dev/sdN` returns `A mandatory SMART command failed: exiting`
- Partition-table tools (`sgdisk`, `wipefs`) fail with `Read error 5` or `Read error 22` on raw device access
- btrfs or ext4 has auto-remounted read-only after persistent I/O errors

## Verified Workflow

**The pattern to recognize:** `DID_BAD_TARGET` is NOT a media error. It means the SATA controller could not reach the target at all. This usually clears with a SCSI re-enumeration without needing a reboot. After the drive comes back, *then* run SMART to determine if it should be trusted.

### Quick Reference

```bash
# 1. Confirm the symptom
sudo dmesg | grep -iE "sdX|ata[0-9]|DID_BAD_TARGET|capacity change" | tail -40
sudo blockdev --getsize64 /dev/sdX     # 0 confirms drive is offline
sudo smartctl -H /dev/sdX              # "mandatory SMART command failed" confirms ATA is dead

# 2. Tell the kernel to forget the device
DEV_SCSI=$(readlink -f /sys/block/sdX/device)
echo 1 | sudo tee "$DEV_SCSI/delete"

# 3. Rescan every AHCI host (don't try to identify which one — just rescan all)
for h in $(ls /sys/class/scsi_host/); do
  proc=$(cat /sys/class/scsi_host/$h/proc_name 2>/dev/null)
  [ "$proc" = "ahci" ] && echo "- - -" | sudo tee /sys/class/scsi_host/$h/scan
done

# 4. If still offline, escalate to host_reset
for h in $(ls /sys/class/scsi_host/); do
  proc=$(cat /sys/class/scsi_host/$h/proc_name 2>/dev/null)
  if [ "$proc" = "ahci" ] && [ -e /sys/class/scsi_host/$h/host_reset ]; then
    echo 1 | sudo tee /sys/class/scsi_host/$h/host_reset
  fi
done

# 5. Once back, the REAL question: is it safe to use?
sudo smartctl -H /dev/sdX
sudo smartctl -A /dev/sdX     # check Reallocated_Sector_Ct (ID 5)
```

### Detailed Steps

- SCSI delete+rescan succeeds where reboots sometimes don't, because it forces the kernel to re-run probe without touching the drive's power state. The drive's own controller may have just timed out on a command and gone unresponsive but is still physically alive on the SATA link.
- If delete+rescan doesn't work, `host_reset` on the AHCI host is the next escalation. Beyond that, only a full power cycle (shutdown, not reboot — the drive PCB must lose power) will recover it.
- **Interpreting SMART after recovery:**
  - `Reallocated_Sector_Ct` (ID 5) RAW_VALUE = number of sectors permanently remapped to spare area
  - Healthy drive: 0
  - Concerning: >100
  - Failing now: thousands
  - End-of-life: >10,000 — spare pool likely exhausted
  - In this session: 64,216 — drive was definitively dying, SMART overall status returned FAILED with "Drive failure expected in less than 24 hours"
- **Crucial nuance:** A drive that drops off the bus then comes back is NOT necessarily safe to use even if it currently reads fine. The drop is the symptom of bad sectors causing command timeouts that the controller can't handle. Each subsequent drop has a chance of being permanent.

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
|---------|----------------|---------------|----------------|
| Assume the I/O errors were filesystem-level (btrfs csum failures) | Initially planned `btrfs scrub` as the diagnostic | dmesg showed `DID_BAD_TARGET` on every command including `Read Capacity(16)` — the failure was below the filesystem at the SCSI host level | When errors are `DID_BAD_TARGET` and `capacity change to 0`, the problem is the SATA link/drive electronics, not the filesystem. Read dmesg before reaching for FS tools. |
| `wipefs -a` + `sgdisk --zap-all` on an offline drive | Wrote a wipe script and ran it | `sgdisk` reported `Warning! Read error 5; strange behavior now likely!` then `Warning! GPT main header not overwritten! Error is 5` — drive was already offline | Always check `blockdev --getsize64` returns non-zero before any partition operation. A drive showing size 0 in `lsblk` means it's not actually there from the kernel's perspective. |
| Reboot to recover the drive | Considered as first step | Reboots don't power-cycle SATA drives — the drive PCB stays powered through warm reboot, so a controller that's in a wedged state stays wedged | For wedged drives, either: (a) SCSI delete+rescan from userspace (no reboot needed), or (b) full power-down (not warm reboot). `shutdown -h` then power-on works; `reboot` often doesn't. |
| Trust that "drive came back online" meant it was usable | After SCSI delete+rescan brought it back at full capacity | SMART immediately reported FAILED status with 64,216 reallocated sectors and explicit "<24h failure" prediction. The drive could read sector 0 but was minutes from total death | A drive returning to the bus is necessary but not sufficient. Always run `smartctl -H` and check Reallocated_Sector_Ct before deciding to keep using it. |

## Results & Parameters

**dmesg signatures that indicate this failure mode (not media error):**
- `hostbyte=DID_BAD_TARGET driverbyte=DRIVER_OK` on every command
- `Read Capacity(16) failed`
- `detected capacity change from <N> to 0`
- `Sense not available`

**Compare against actual media errors (different problem):**
- `Sense Key: Medium Error`
- `Add. Sense: Unrecovered read error`
- Capacity stays at correct size

**Recovery success rate observed:** SCSI delete+rescan brought a `DID_BAD_TARGET` drive back online in one attempt. The SATA link came up at full 6.0 Gbps. The drive then operated normally for the duration of the diagnostic session (~30 minutes) before being retired.

**SMART thresholds (Seagate-class drives):**
- ID 5 Reallocated_Sector_Ct: vendor-normalized VALUE drops as RAW_VALUE grows. THRESH typically 36. When VALUE ≤ THRESH, drive is officially failing.
- Observed values on the dead drive: VALUE=003, WORST=003, THRESH=036, RAW=64216 — VALUE far below THRESH, status FAILED.

## Verified On

| Project | Context | Details |
|---------|---------|---------|
| Personal | Seagate ST2000DL003-9VT166 (2TB, 2011-era 5400 RPM) on SATA port ata3 / host2 | Drive came back via SCSI delete+rescan; SMART then confirmed end-of-life with 64,216 reallocated sectors |
