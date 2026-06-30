---
name: nfs-server-oom-recursive-metadata-ops
description: "A RAM-starved NFS server (low-power appliance NAS) OOM-crashes and silently wedges under recursive metadata operations; reads are safe but metadata writes are deadly. Use when: (1) a Linux NFS client logs multi-hour 'nfs: server <ip> not responding, still trying' windows that end in 'OK', (2) an appliance NAS with little RAM 'keeps hanging' or crash-loops while a chown -R / chmod -R or rsync runs, (3) you must decide whether it is a failing disk or an out-of-memory crash before acting."
category: debugging
date: 2026-06-28
version: "1.0.0"
user-invocable: false
verification: verified-local
tags: []
---

# RAM-Starved NFS Server OOM-Crashes Under Recursive Metadata Ops

## Overview

| Field | Value |
|-------|-------|
| **Date** | 2026-06-28 |
| **Objective** | Diagnose why an appliance NAS used as an NFS server "keeps hanging" for multi-hour stretches, and safely get 3 TB of data off it. |
| **Central lesson** | The multi-hour `nfs: server not responding` windows were OOM **crashes, not slowness**. A tiny-RAM NAS exhausts memory under recursive metadata writes (`chown -R` / `chmod -R` over millions of inodes); btrfs metadata + inode/dentry slab is **unswappable**, so swap never helps and the OOM-killer fires — killing critical procs **including `mdadm`**. **Reads are safe; metadata writes are deadly.** |
| **Worked example** | NETGEAR ReadyNAS 104 — 1 ARMv7 core (~34 BogoMIPS), **496 MB RAM**, 4x3TB RAID5 btrfs — exporting NFS to a Linux client. A 265-day uptime ended the moment heavy ops began; one post-crash boot lasted only 7 minutes before OOMing again (crash loop). |
| **Outcome** | Confirmed OOM (not disk failure) via SMART/btrfs/mdstat + dmesg `oom-kill`. Extracted 3 TB overnight with **0 hangs** using a throttled, one-share-at-a-time read-only rsync. |
| **Verification** | verified-local — executed end-to-end and confirmed on a live homelab NAS migration (2026-06), NOT via this repo's CI. |

## When to Use

- A Linux NFS **client**'s kernel log shows `nfs: server <ip> not responding, still trying` for **multi-hour** stretches followed by `nfs: server <ip> OK` — and the NAS is a low-power appliance (ARM, few cores, little RAM).
- An appliance NAS "keeps hanging", wedges, or crash-loops (short boots) while a recursive `chown -R` / `chmod -R a+rX` or a concurrent rsync is running over many inodes.
- A long stable uptime ends abruptly the moment heavy metadata operations start.
- You need to decide whether the cause is a **failing disk** (which looks similar) or an **out-of-memory crash** before recommending any fix.
- You must copy a large dataset OFF a fragile, RAM-starved NAS without crashing it.

## Verified Workflow

The core insight: prove the "not responding" windows are **crashes** (each ends in a reboot), rule out the disk, confirm OOM in the NAS logs, then extract data with READS only — never recursive metadata writes.

### Quick Reference

```bash
# --- On the CLIENT: find the "not responding" windows ---
journalctl -k | grep "not responding"        # multi-hour gaps ending in "OK"

# --- On the NAS: prove each "recovery" was actually a REBOOT ---
last -x reboot                                # reboot times match the client's "OK" times
journalctl --list-boots                       # short boots == crash loop
journalctl -k -b -1 | grep -iE "oom|out of memory|killed process"  # PREVIOUS boot's OOM
free -m                                        # ~25-45 MB free of 496 == zero headroom

# --- Rule OUT a failing disk (looks similar) ---
for d in /dev/sda /dev/sdb /dev/sdc /dev/sdd; do smartctl -H -A "$d"; done
#   look for Current_Pending_Sector / Offline_Uncorrectable / Command_Timeout (all 0 == healthy)
btrfs device stats /<mountpoint>              # corruption_errs/read_io_errs etc. all 0 == healthy
cat /proc/mdstat                              # [UUUU] == array NOT degraded

# --- Extract data GENTLY: READS only, one share at a time, throttled ---
nice -n19 ionice -c3 rsync -rlptD --bwlimit=25m --timeout=120 \
  nas:/export/share1/ /dest/share1/
#   then watch the client log BETWEEN shares; back off if "not responding" appears:
journalctl -k -f | grep --line-buffered "not responding"
```

### Detailed Steps

1. **Reframe the symptom.** The user reports "the NAS keeps hanging." On the **client**, run
   `journalctl -k | grep "not responding"`. You will see long windows (e.g. 07:41→10:13,
   12:00→16:36) of `nfs: server <ip> not responding, still trying` ending in `nfs: server <ip> OK`.
   Do **not** assume this is slowness — slowness recovers, a crash reboots.

2. **Prove the windows are crashes, not slowness.** On the NAS, run `last -x reboot` and correlate
   the reboot timestamps with the client's `nfs: server OK` timestamps. If they **match exactly**,
   each "recovery" is the NAS finishing a reboot. `journalctl --list-boots` confirms a crash loop
   (one boot here lasted only ~7 minutes before OOMing again).

3. **Rule out a failing disk** (a dying drive produces similar transient I/O errors and timeouts):
   - `smartctl -H -A /dev/sdX` for every disk — a failing drive shows climbing **Command_Timeout**
     and nonzero **Current_Pending_Sector** / **Offline_Uncorrectable**. Here all were 0 and all PASSED.
   - `btrfs device stats <mount>` — `corruption_errs` / `read_io_errs` / `write_io_errs` were all ZERO.
   - `cat /proc/mdstat` — showed `[UUUU]`, i.e. the array is **not** degraded.
   - Earlier transient `Input/output error`s were the box dying mid-operation, NOT bad data.

4. **Confirm OOM in the NAS logs.** Because uptime is short after a crash, check the **previous**
   boot's persistent journal: `journalctl --list-boots` then `journalctl -k -b -1`. Look for
   `oom-kill`, `Out of memory: Kill process N (chown)`, `Kill process N (mdadm)`,
   `upsd invoked oom-killer`. Confirm headroom with `free -m`: ~25-45 MB free of 496 MB is
   essentially zero, which is why even small ops tip it over.

5. **Understand WHY swap does not help.** btrfs metadata and the inode/dentry **slab cache** are
   **unswappable kernel memory**. The 1 GB swap stays at 0 used during the crash — it cannot rescue
   slab pressure. Dirty metadata can't be dropped until written, so the slab grows until OOM.

6. **Extract data with READS only.** Reading reclaims clean inode cache under pressure, so a
   read-only copy is safe. Copy GENTLY, **one share at a time**, throttled:
   `nice -n19 ionice -c3 rsync -rlptD --bwlimit=25m --timeout=120`. Monitor the client's
   `nfs: not responding` log between shares and back off if it reappears. This moved 3 TB overnight
   with **0 hangs**. (To avoid touching ownership on a root_squash export, prefer exporting
   `no_root_squash` + a read-only copy over any chmod — see the related `nfs-root-squash`
   and `homelab-nextcloud-data-dir-nfs-migration` skills.)

7. **Never run mass recursive metadata writes on this class of box.** A `chown -R` / `chmod -R a+rX`
   across all shares (millions of inodes) WILL OOM and can OOM-kill `mdadm` (array risk). Even a
   "targeted" chmod is risky at ~25 MB free — test on a small folder and watch.

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
|---------|----------------|---------------|----------------|
| Mass recursive metadata write | `chown -R mvillmow:GRP; chmod -R a+rX` across all 8 shares (millions of inodes) | Inode/dentry + btrfs metadata slab (unswappable) exhausted 496 MB RAM; OOM-killer killed `mdadm` AND `chown`; multi-hour wedge + crash-loop (7-min boots) | NEVER mass recursive `chown -R`/`chmod -R` a RAM-starved NFS box — it can OOM-kill the RAID manager and risk the array |
| "Targeted" chmod | `chmod -R a+rX` on ~41k inodes across 5 folders, assuming small == safe | STILL OOM'd around a ~2,365-inode folder because idle free RAM was only ~25 MB | Zero headroom means even "small" metadata writes are risky; prefer `no_root_squash` + read-only copy over chmod |
| Blamed the disk | Assumed a failing drive from earlier `Input/output error`s | SMART (`-H -A`) all PASSED w/ 0 Command_Timeout; `btrfs device stats` all 0; `/proc/mdstat` `[UUUU]` — it was OOM, the errors were the box dying mid-op | Rule out disk with SMART + btrfs counters + mdstat BEFORE blaming hardware; transient I/O errors during a crash are not bad data |
| Expected swap to absorb it | Relied on the NAS's 1 GB swap to handle memory pressure | btrfs metadata + slab cache is unswappable kernel memory; swap stayed at 0 used while RAM hit OOM | On a slab-bound workload, swap is useless; the binding constraint is unswappable kernel memory, not anon pages |

## Results & Parameters

**Hardware (the constraint):** NETGEAR ReadyNAS 104 — 1 ARMv7 core (~34 BogoMIPS), **496 MB RAM**,
4x3TB RAID5 btrfs. Idle free RAM ~25-45 MB. 1 GB swap, useless for slab pressure.

**The crucial distinction:**

- **READS are safe** — the kernel reclaims clean inode/dentry cache under read pressure. Reading
  3 TB via rsync ran clean with 0 hangs.
- **Metadata WRITES are deadly** — dirty btrfs metadata can't be dropped until written, so the
  unswappable slab grows until OOM. A single ~2,365-inode `chmod` crashed the box.

**Gentle extraction command (3 TB overnight, 0 hangs), one share at a time:**

```bash
nice -n19 ionice -c3 rsync -rlptD --bwlimit=25m --timeout=120 \
  nas:/export/<share>/ /dest/<share>/
```

**Diagnostic one-liners:**

```bash
journalctl -k | grep "not responding"   # CLIENT: multi-hour crash windows ending in "OK"
last -x reboot                            # NAS: reboot times == client "OK" times (proof of crash)
journalctl --list-boots                   # NAS: short boots == crash loop
journalctl -k -b -1 | grep -iE "oom|out of memory|killed process"  # OOM in PREVIOUS boot
smartctl -H -A /dev/sdX                   # disk health: Command_Timeout / Pending_Sector == 0 == OK
btrfs device stats /<mount>               # corruption/read/write_io_errs all 0 == healthy
cat /proc/mdstat                          # [UUUU] == array not degraded
free -m                                    # ~25-45 MB free of 496 == zero headroom
```

**Expected healthy outputs (confirming OOM, not disk):** SMART `PASSED`, all `Command_Timeout` /
`Current_Pending_Sector` / `Offline_Uncorrectable` = 0; `btrfs device stats` all counters 0;
`/proc/mdstat` shows `[UUUU]`; NAS dmesg/journal shows `oom-kill` / `Out of memory: Kill process
N (chown)` / `Kill process N (mdadm)`.

## Verified On

| Project | Context | Details |
|---------|---------|---------|
| Homelab NAS migration | Live ReadyNAS 104 NFS server (496 MB RAM) crash-looping under `chown -R`/`chmod -R`; 3 TB extracted via throttled read-only rsync, 2026-06 | verified-local (live hosts via ssh/journalctl/smartctl; not this repo's CI) |
