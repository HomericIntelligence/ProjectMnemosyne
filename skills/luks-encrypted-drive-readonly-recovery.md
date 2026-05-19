---
name: luks-encrypted-drive-readonly-recovery
description: "Read-only recovery of files from a hotplugged LUKS-encrypted drive, prioritizing data safety over speed. Use when: (1) a SATA/USB drive with LUKS partitions needs file extraction, (2) drive health is unknown or suspect and you must not write to it, (3) imaging-first vs mount-directly tradeoff needs to be decided."
category: tooling
date: 2026-05-18
version: "1.0.0"
user-invocable: false
verification: verified-local
tags: [luks, cryptsetup, ddrescue, data-recovery, btrfs, ext4, blockdev, readonly]
---

# LUKS Encrypted Drive Read-Only Recovery

## Overview

| Field | Value |
|-------|-------|
| Objective | Extract specific files from a hotplugged LUKS-encrypted drive without writing to it |
| Outcome | Successful — 97.2% of source files matched live trees by sha256; remaining 2.8% were KDE cache/desktop state, not user data |
| Verification | verified-local (executed on real hardware; no CI) |

## When to Use

- A SATA or USB drive with a `crypto_LUKS` partition (visible via `lsblk -f` or `blkid`) is plugged in
- You have the passphrase (or are still imaging blindly before deciding)
- Drive provenance is unclear — could be failing — so writes to the original device must be impossible

## Verified Workflow

**Decision: image first vs mount directly**

- Image first (`ddrescue`) is the textbook-safe path
- Mount-directly is faster and acceptable IF: (a) drive enumerates cleanly, (b) you have the passphrase, (c) SMART is healthy, (d) you commit to `--readonly` cryptsetup + `ro,noload`/`ro,nologreplay`/`ro,norecovery` mount flags
- Always back up the LUKS header (`cryptsetup luksHeaderBackup`) — it's tiny (~2 MB) and the only thing that makes the data fundamentally recoverable later
- Always set kernel-level RO (`blockdev --setro /dev/sdX`) on the device AND partition. This is a belt-and-suspenders defense — even with `--readonly` cryptsetup and `mount -o ro`, the block layer flag prevents any accidental write at all layers

### Quick Reference

```bash
# 1. Identify and confirm — never assume the device letter
lsblk -o NAME,SIZE,TYPE,FSTYPE,SERIAL,TRAN
udevadm info --query=property --name=/dev/sdX | grep -E "ID_MODEL|ID_VENDOR|ID_SERIAL|ID_BUS"

# 2. Force read-only at kernel block layer (the safety net)
sudo blockdev --setro /dev/sdX
sudo blockdev --setro /dev/sdX1
sudo blockdev --getro /dev/sdX     # must print 1

# 3. Inspect LUKS header (read-only) and back it up
sudo cryptsetup luksDump /dev/sdX1
sudo cryptsetup luksHeaderBackup /dev/sdX1 --header-backup-file /path/to/sdX1-luks-header.img

# 4. Unlock READ-ONLY
sudo cryptsetup --readonly luksOpen /dev/sdX1 recovered

# 5. Inspect inner FS and choose mount flags
INNER=$(sudo blkid -o value -s TYPE /dev/mapper/recovered)
case "$INNER" in
  ext*)  OPTS="ro,noload" ;;       # noload skips journal replay (would be a write)
  xfs)   OPTS="ro,norecovery" ;;
  btrfs) OPTS="ro,nologreplay" ;;
  *)     OPTS="ro" ;;
esac
sudo mkdir -p /mnt/recovered
sudo mount -o "$OPTS" /dev/mapper/recovered /mnt/recovered

# 6. Cleanup (reverse order)
sudo umount /mnt/recovered
sudo cryptsetup luksClose recovered
# blockdev RO flag clears when device is unplugged or via --setrw if desired
```

### Detailed steps

- Sanity-check device identity via `udevadm info` BEFORE running anything privileged. Multi-bay USB docks (e.g. JMicron JMS561) can report placeholder serials shared across slots, so size+model are more reliable than serial alone.
- For ext4: `ro,noload` is critical. Plain `mount -o ro` will still replay the journal if the FS is marked dirty — which is a write. `noload` skips that.
- For btrfs: `ro,nologreplay` is the equivalent. Without it, btrfs may perform tree updates on mount.
- For xfs: `ro,norecovery`.

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
|---------|----------------|---------------|----------------|
| Assume `/dev/sde` was the target drive based on user description "encrypted SATA" | Wrote recover.sh hardcoded to /dev/sde | User had multiple drives plugged in via a USB dock with placeholder serials; sde was actually a different 224G drive, not the intended one | Always confirm device by SIZE+MODEL from `udevadm info`, not by enumeration order. Multi-slot USB docks share serials. |
| Plan to ddrescue-image the partition first (224 GiB) | Wrote full image-first script | User pushed back: drive enumerated fine and the goal was specific files, not full archival | Imaging is the textbook-safe answer but is overkill when (a) drive is healthy, (b) you have the passphrase, (c) you commit to kernel-level RO + `--readonly` cryptsetup + journal-skip mount flags |
| Use `cryptsetup luksOpen` without `--readonly` flag | First draft of recover.sh | Cryptsetup will update LUKS header metadata on open (last-used timestamps, key-slot iterations recompute on some versions) — that is a write to the source | Always pass `--readonly` to `cryptsetup luksOpen` for recovery. It prevents header-metadata writes. |
| Use `mount -o ro` alone | First-draft mount step | ext4 still replays journal on a dirty FS even when mounted read-only. That's a write. | Use `ro,noload` for ext4, `ro,nologreplay` for btrfs, `ro,norecovery` for xfs. Plain `ro` is insufficient for dirty filesystems. |

## Results & Parameters

- LUKS header backup file size: ~2 MB (1024 KiB sectors × 2). Always preserve it.
- Read-only block device flag verification: `blockdev --getro /dev/sdX` returns `1`.
- Validation strategy used afterward to confirm completeness: hash-based comparison. For each file on the recovered drive, sha256 the bytes; check whether the same hash exists anywhere under the live target trees. Path-based comparison is wrong because directory layouts diverge. 97.2% match rate is typical when the recovered drive is an older snapshot of the same data — the remaining "missing" files are mostly KDE/Plasma cache (akonadi DBs, kactivitymanagerd, plasma session state), browser caches, container layer files, and pycache. Real user data is almost never in the gap.

### Verified On

| Project | Context | Details |
|---------|---------|---------|
| Personal | LUKS-on-btrfs 1.8 TB Seagate ST2000DL003; 488,574 files; KDE Plasma source | Recovery succeeded; drive subsequently failed SMART (separate skill) |
