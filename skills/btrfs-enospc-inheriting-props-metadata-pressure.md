---
name: btrfs-enospc-inheriting-props-metadata-pressure
description: "btrfs `error inheriting props ... -28` during file creation is a transient METADATA-reservation shortfall on old kernels, NOT a full disk or a failing drive — and `btrfs balance` usually cannot fix it. Use when: (1) rsync to a btrfs volume fails on a handful of files with `close failed ... Input/output error (5)` and exits rc=11, hitting different files each run, (2) the btrfs host's dmesg shows `BTRFS error (device mdX): error inheriting props for ino N (root R): -28` while `df` shows the volume far from full, (3) you are tempted to run `btrfs balance` to fix an ENOSPC that df says is not real, (4) you must decide between disk-full, disk-failure, and metadata-pressure before acting."
category: debugging
date: 2026-07-04
version: "1.0.0"
user-invocable: false
verification: verified-local
tags: [btrfs, enospc, rsync, metadata, balance, homelab, nas, raid5]
---

# btrfs `-28` "error inheriting props" Is Metadata Pressure, Not a Full Disk

## Overview

| Field | Value |
|-------|-------|
| **Date** | 2026-07-04 |
| **Objective** | Diagnose why an rsync backup to a btrfs volume intermittently fails a handful of files with `Input/output error (5)` / rc=11, and fix it without corrupting data or running a risky balance. |
| **Central lesson** | The kernel's `error inheriting props for ino N (root R): -28` is `-ENOSPC`, but `-28` here is a **transient metadata-reservation shortfall** when creating a new inode (which inherits the parent subvol's compression property), NOT a full disk and NOT disk failure. On old kernels (4.4/4.19) this reservation can momentarily fail under metadata pressure. `df` shows TBs free; `btrfs fi usage` shows TBs **unallocated** — so there is nothing under-full for a `balance` to reclaim. The real fix is to reduce write **churn** (fewer new inodes per run), not to grow or rebalance space. |
| **Worked example** | Live homelab NAS: btrfs on an md **RAID5** device, kernel **4.19**, backing up NextCloud via rsync. ~2 `-28` failures/run on different files each time; `df` ~40% used (5 TB free); `btrfs fi usage` = data chunks 100% packed, metadata ~87%, **4.96 TiB unallocated**. Excluding NextCloud `appdata_*/preview/` (185,856 entries) cut the transfer 242k→56k entries and drove `-28` toward 0. |
| **Outcome** | Root-caused as metadata pressure (not disk-full / not failure); `balance` correctly identified as a no-op (nothing to reclaim) and a risk on a RAM-starved box; fixed by excluding regenerable high-churn trees from the backup and retrying stubborn files while idle. |
| **Verification** | verified-local — executed end-to-end on a live homelab NAS (2026-07), NOT via this repo's CI. |

## When to Use

- An rsync backup to a **btrfs** volume fails on a small, **changing** set of files with
  `rsync: close failed on "…": Input/output error (5)` and exits **rc=11** — some files that
  fail one run succeed the next.
- The btrfs host's `dmesg` / kernel log shows
  `BTRFS error (device mdX): error inheriting props for ino N (root R): -28` (often on an old
  4.4/4.19 kernel), while `df` says the volume is nowhere near full.
- You are about to run `btrfs balance` to "free space" for an ENOSPC that `df` insists is not real
  — **check `btrfs fi usage` first** (see below); a balance is almost certainly a no-op here.
- You must distinguish **disk-full** vs **disk/RAID failure** vs **metadata-reservation pressure**
  before acting, and want the exact commands to rule each in or out.

## Verified Workflow

The core insight: `-28` is `-ENOSPC`, but the binding constraint is a **transient metadata
reservation** during new-inode creation, not free space. Rule out disk-full and disk-failure,
then confirm via `btrfs fi usage` that there is nothing to balance, and fix by cutting write churn.

### Quick Reference

```bash
# --- 1. See the real error on the btrfs HOST (not just rsync's rc=11 on the client) ---
dmesg | grep -i btrfs        # look for: error inheriting props for ino N (root R): -28

# --- 2. Rule OUT disk-full ---
df -h /<mnt>                  # here ~40% used, ~5 TB free  => NOT full

# --- 3. Rule OUT disk / RAID failure ---
smartctl -H -A /dev/sdX      # PASSED, 0 Pending/Uncorrectable/Command_Timeout
btrfs device stats /<mnt>    # all counters 0 == healthy
cat /proc/mdstat             # [UUUU] == array NOT degraded

# --- 4. The DECIDING check before ever running balance: is anything under-full? ---
btrfs filesystem df /<mnt>       # Data,single total ~= used  => data chunks are packed
btrfs filesystem usage /<mnt>    # read "Device unallocated" — here 4.96 TiB unallocated
#   Unallocated is LARGE  => btrfs can freely allocate new data AND metadata chunks;
#   there is NOTHING under-full to reclaim  => balance is a no-op (and risky on low RAM).

# --- 5. The FIX: reduce inode churn so fewer new files are created per run ---
rsync -a --exclude-from=/path/backup-excludes.txt  src/  dest/
#   For a couple of stubborn large files, retry them individually while the box is IDLE.
```

### Detailed Steps

1. **Read the HOST's error, not just rsync's.** rsync only reports `Input/output error (5)` and
   `rc=11` on the client. SSH to the btrfs host and run `dmesg | grep -i btrfs`; the real message is
   `BTRFS error (device mdX): error inheriting props for ino N (root R): -28`. `-28` is `-ENOSPC`.
   "inheriting props" means: creating a new inode inherits the parent subvolume's properties
   (notably the `compression` prop), and reserving metadata for that inherit step is what failed.

2. **Rule out disk-full immediately.** `df -h /<mnt>`. Here it was ~40% used with ~5 TB free.
   A `-28` with a mostly-empty `df` is the signature of **metadata pressure**, not a full volume.

3. **Rule out disk / RAID failure** (a dying drive throws similar transient I/O errors):
   - `smartctl -H -A /dev/sdX` for each member — clean (`PASSED`, 0 Pending/Uncorrectable).
   - `btrfs device stats /<mnt>` — all counters 0.
   - `cat /proc/mdstat` — `[UUUU]`, array not degraded.
   If all three are clean, this is not hardware.

4. **Run `btrfs fi usage` BEFORE even thinking about balance.** The deciding number is
   **Device unallocated**. Here: `Data,single total=used` (data chunks 100% packed), metadata ~87%,
   but **4.96 TiB unallocated**. Large unallocated space means btrfs can allocate brand-new data
   **and** metadata chunks on demand — so there is nothing under-full for a balance to reclaim.
   `btrfs balance -dusage=N` would find no under-full data chunks and no-op. A balance only helps
   when the device is **fully allocated** (`unallocated ≈ 0`) with under-full chunks to compact.

5. **Do NOT run balance here.** Besides being a no-op, `balance` is a heavy metadata operation; on a
   RAM-starved box it risks OOM for zero benefit. Checking `Device unallocated` first is the whole
   guardrail.

6. **Fix the real problem: reduce write churn.** `-28` scales with how many **new inodes** you create
   per run (each new file does the props-inherit reservation). Exclude regenerable / high-churn trees
   from the backup with `--exclude-from`:
   - NextCloud `appdata_*/preview/` — here **185,856 entries** (~43% of all files, a deep nested tree);
     excluding it cut the per-run transfer **242k → 56k entries (77%)** and dropped `-28` from ~2/run
     toward 0.
   - Per-user `cache/` and `uploads/`, `.thumbnails/`, OS cruft (`.DS_Store`, `Thumbs.db`).
   - **Keep real user data** — only exclude regenerable/ephemeral content.

7. **Retry stubborn large files while idle.** For the last one or two files that still `-28`
   mid-backup, rsync them individually when the box is otherwise idle — a single-file write under low
   metadata contention usually succeeds where the mid-backup attempt failed.

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
|---------|----------------|---------------|----------------|
| Assumed the disk was full | Read `-28` as ENOSPC and expected `df` to show a full volume | `df -h` showed ~40% used, ~5 TB free — the volume was nowhere near full | A btrfs `-28` with a mostly-empty `df` is metadata-reservation pressure, not free-space exhaustion; check `df` before assuming full |
| Assumed disk / RAID failure | Suspected a dying drive from the `Input/output error (5)` on the client | `smartctl -H -A` clean (0 Pending/Uncorrectable), `btrfs device stats` all 0, `/proc/mdstat` `[UUUU]` | Rule out hardware with SMART + `btrfs device stats` + mdstat first; a transient btrfs metadata `-28` mimics a failing disk on the client |
| Proposed `btrfs balance` to free space | About to run `btrfs balance -dusage=N` to fix the ENOSPC | `btrfs fi usage` showed **4.96 TiB unallocated** and data chunks 100% packed — nothing under-full to reclaim, so balance is a no-op; on a RAM-starved box it is a risky heavy metadata op (OOM risk) for zero benefit | ALWAYS check `btrfs fi usage` "Device unallocated" before running balance — balance only helps when unallocated ≈ 0 with under-full chunks; never balance to "fix" a metadata-pressure `-28` |

## Results & Parameters

**Environment (the constraint):** btrfs on md **RAID5**, kernel **4.19** (old-kernel props-inherit
reservation is the trigger), live homelab NAS backing up NextCloud via rsync. ~2 `-28` failures/run,
different files each run.

**Diagnostic one-liners:**

```bash
dmesg | grep -i btrfs          # HOST: error inheriting props for ino N (root R): -28  (= -ENOSPC)
df -h /<mnt>                    # ~40% used, ~5 TB free  => NOT disk-full
smartctl -H -A /dev/sdX        # PASSED, 0 Pending/Uncorrectable/Command_Timeout  => disk healthy
btrfs device stats /<mnt>      # all counters 0  => no btrfs-level corruption/errors
cat /proc/mdstat               # [UUUU]  => RAID array not degraded
btrfs filesystem df /<mnt>     # Data,single total ~= used  => data chunks 100% packed
btrfs filesystem usage /<mnt>  # "Device unallocated": 4.96 TiB  => nothing for balance to reclaim
```

**Deciding numbers (this case):** Data chunks 100% packed, Metadata ~87% used, **4.96 TiB
unallocated**. Large unallocated => btrfs allocates new data+metadata chunks freely => balance no-op.

**The fix — an rsync `--exclude-from` file for a NextCloud backup:**

```text
# backup-excludes.txt  (rsync --exclude-from) — exclude regenerable / high-churn trees only.
# NextCloud preview cache: here 185,856 entries (~43% of files, deep nested tree)
appdata_*/preview/
# Per-user transient dirs
*/cache/
*/uploads/
# Thumbnails and OS cruft
.thumbnails/
.DS_Store
Thumbs.db
```

```bash
rsync -a --exclude-from=backup-excludes.txt  src/  dest/
# Result: per-run transfer 242k -> 56k entries (77% fewer new inodes); -28 dropped ~2/run -> ~0.
# Stubborn large files: rsync each one individually while the box is idle (low metadata contention).
```

**Expected healthy outputs (confirming metadata pressure, not disk-full/failure):** `df` far from
full; `smartctl` `PASSED` with 0 error counters; `btrfs device stats` all 0; `/proc/mdstat`
`[UUUU]`; `btrfs fi usage` shows large **Device unallocated** with packed data chunks.

## Verified On

| Project | Context | Details |
|---------|---------|---------|
| Homelab NAS backup | Live btrfs-on-md-RAID5 volume (kernel 4.19) throwing `error inheriting props ... -28` during rsync of NextCloud; fixed by excluding `appdata_*/preview/` (185,856 entries) + cache/thumbnails, 2026-07 | verified-local (live host via ssh/dmesg/smartctl/btrfs; not this repo's CI) |
