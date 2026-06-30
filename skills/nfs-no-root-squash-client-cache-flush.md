---
name: nfs-no-root-squash-client-cache-flush
description: "Read/write owner-restricted files over NFS by granting the client no_root_squash, then flushing the client's NFS access cache (drop_caches) so it stops serving stale 'Permission denied'. Use when: (1) rsync/backup as root fails with thousands of 'Permission denied (13)' on owner-only (700/750/770/755) files on an NFS export, (2) you changed an export server-side but the client keeps returning the OLD denial, (3) a freshly-named file reads fine while the exact files denied before keep failing (stale client access cache)."
category: tooling
date: 2026-06-28
version: "1.0.0"
user-invocable: false
verification: verified-local
tags: []
---

# NFS no_root_squash + Client Access-Cache Flush

## Overview

| Field | Value |
|-------|-------|
| **Date** | 2026-06-28 |
| **Objective** | Read/back up owner-restricted files on a `root_squash` NFS export whose owner uids don't map to the client |
| **Outcome** | Successful — grant `no_root_squash`, then flush the client NFS access cache; rsync drops from ~3,064 denials to 0 |
| **Verification** | verified-local |

## When to Use

- `rsync`/backup as **root** over NFSv3 fails with thousands of `send_files failed to open ...: Permission denied (13)` and `opendir ...: Permission denied` on files/dirs owned by uids that don't map to the client.
- The export uses `root_squash` (the default), so the client's root is mapped to `anon` (uid 99) and cannot read owner-only (700/750/770/755) files it doesn't own.
- You changed the export **server-side** (added `no_root_squash`, ran `exportfs -ra`) but the client **keeps** returning the previously-cached `Permission denied` and never re-asks the server.
- Tell-tale asymmetry: a **freshly-named** file (never accessed, so never cached) reads fine immediately, while the **exact** files denied before keep failing — that is a stale client cache, not a server problem.
- Companion to `nfs-root-squash-systemd-service-user`: use **that** skill when the file owner maps to a client user (just run as that user); use **this** skill when the owner does **not** map and you genuinely need `no_root_squash`.

## Verified Workflow

> Verified locally on a live homelab NFS migration (2026-06). CI validation pending.

### Quick Reference

```bash
# --- ON THE NFS SERVER ---
# 1. Grant THIS client no_root_squash (match the exact client IP; don't touch others)
sed -i 's/192.168.2.20(\(.*\)root_squash/192.168.2.20(\1no_root_squash/' /etc/exports
exportfs -ra
exportfs -v | grep 192.168.2.20        # confirm LIVE state shows no_root_squash

# --- ON THE NFS CLIENT (the critical, oft-missed step) ---
# 2. Flush the per-inode ACCESS-check cache so the client re-asks the server
sync; echo 3 > /proc/sys/vm/drop_caches   # or remount the share, or wait out actimeo (~30 min)

# 3. Probe a RESTRICTIVE subdir (NOT the 777 share root) to confirm the real state
touch /mnt/nas/Pictures/Pic3/.x && rm -f /mnt/nas/Pictures/Pic3/.x && echo WRITABLE

# 4. Re-run the gentle root rsync — now 0 denials
nice -n19 ionice -c3 rsync -rlptD --chown=owner /mnt/nas/ /backup/dest/

# --- ON THE NFS SERVER, AFTER you're done (security tightening) ---
# 5. Revert to root_squash
sed -i 's/192.168.2.20(\(.*\)no_root_squash/192.168.2.20(\1root_squash/' /etc/exports
exportfs -ra
```

### Detailed Steps

1. **Confirm it's an ownership/squash problem, not a mount problem.** The mount is `rw`, yet root gets `Permission denied (13)` on owner-only files. Under `root_squash` the client's root maps to `anon` (uid 99); it is neither the owner nor granted world access, so it cannot read 700/750/770/755 files. Only the owning uid (if it maps to a client user) or `no_root_squash` grants access.

2. **Grant `no_root_squash` to this client on the server.** Edit `/etc/exports` so the client spec reads `192.168.2.20(...,rw,no_root_squash,...)` — match the exact client IP so you don't loosen other clients — then `exportfs -ra`. Now the client's root is the server's root over NFS and can read/write anything.

3. **CRITICAL — flush the client's NFS access cache.** The Linux NFS client caches per-inode ACCESS-check results (governed by `actimeo`, default ~30 min via `acregmax`/`acdirmax` attribute caching). After a server-side export change, the client keeps serving the previously-cached `Permission denied` and never re-asks the server. Flush it **on the client**: `sync; echo 3 > /proc/sys/vm/drop_caches` (or remount, or wait out `actimeo`). Diagnostic confirmation: a freshly-named file reads fine while previously-denied files keep failing = stale client cache.

4. **Test writability on a RESTRICTIVE subdir, not the share root.** Share roots are frequently `777` (writable even under `root_squash` via `anon`), which masks the real state. Probe a child dir whose perms/owner are restrictive (e.g. a `775 mvillmow` subdir), not `/mnt/nas/<share>/.x`.

5. **Re-run the read/rsync.** It now succeeds with 0 denials. Use a gentle, low-priority copy on RAM-starved NAS appliances: `nice -n19 ionice -c3 rsync -rlptD --chown=owner ...`.

6. **Revert to `root_squash` when done** if you only needed it temporarily. Reverting is a security *tightening* and low-friction (`sed` back, `exportfs -ra`).

#### Appliance NAS caveat (NETGEAR ReadyNAS and similar)

`readynasd` regenerates `/etc/exports` from its own config DB on reboot / any config change, **wiping a manual `sed` edit**. For persistence either (a) set "no root squash / allow root access" per-share in the admin UI, **or** (b) have the consuming script re-apply the LIVE export table at the start of each run (no `/etc/exports` dependence):

```bash
exportfs -o rw,no_root_squash 192.168.2.20:/path     # mutates the live table directly
exportfs -v | grep 192.168.2.20                       # verify it actually took
```

Always verify the LIVE state with `exportfs -v | grep <client>` (look for `no_root_squash` vs `root_squash`) and confirm empirically with a restrictive-subdir write test — don't trust that the setting "took".

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
|---------|----------------|---------------|----------------|
| Set `no_root_squash`, rsync immediately | Added `no_root_squash` + `exportfs -ra`, re-ran rsync at once | Client served ~3,064 STALE cached denials; it never re-asked the server (per-inode ACCESS cache, `actimeo` ~30 min) | After any server-side export change you MUST flush the client cache: `sync; echo 3 > /proc/sys/vm/drop_caches`, then re-run (0 denials) |
| Recursively `chmod` the files on the NAS | Tried to make files readable by mass `chmod -R` on the server instead of using `no_root_squash` | OOM-crashed the RAM-starved NAS (see the related NFS-OOM skill) | `no_root_squash` + `drop_caches` is the gentle, correct path; mass chmod on the server is dangerous |
| Probe writability on the share root | `touch /mnt/nas/Pictures/.x` reported "WRITABLE" | Share root is `777` — always writable even under `root_squash` via `anon`; it masks the real constraint | Probe a RESTRICTIVE child (`/mnt/nas/Pictures/Pic3/.x`, 775 mvillmow) → DENIED reveals the truth |
| Manual `/etc/exports` edit on appliance NAS | `sed`-edited `/etc/exports` on a NETGEAR ReadyNAS | `readynasd` regenerates `/etc/exports` from its config DB on reboot/any change, wiping the edit | Set it in the admin UI, or re-apply the LIVE table with `exportfs -o rw,no_root_squash <client>:/path` each run |

## Results & Parameters

**Exact commands (copy-paste):**

```bash
# Grant + apply (server)
sed -i 's/...root_squash.../...no_root_squash.../' /etc/exports
exportfs -ra
exportfs -v | grep 192.168.2.20            # expect: ...,no_root_squash,...

# Flush stale client access cache (client) — THE key gotcha
sync; echo 3 > /proc/sys/vm/drop_caches

# Empirical probe on a RESTRICTIVE subdir (client)
touch /mnt/nas/Pictures/Pic3/.x && rm -f /mnt/nas/Pictures/Pic3/.x && echo WRITABLE

# Gentle root rsync (client)
nice -n19 ionice -c3 rsync -rlptD --chown=owner /mnt/nas/ /backup/dest/

# Live-table re-apply for appliance NAS that reverts /etc/exports
exportfs -o rw,no_root_squash 192.168.2.20:/path
```

**Squash semantics:**

| Export setting | Client root maps to | Can read owner-only (700/750) files? |
|----------------|---------------------|--------------------------------------|
| `root_squash` (default) | `anon` (uid 99) | No — not the owner, no world access |
| `no_root_squash` | server root (uid 0) | Yes — root bypasses the permission check |

**Key numbers / notes:**

- Before flush: ~3,064 `Permission denied (13)`; after `drop_caches`: 0 denials.
- `actimeo` default ~30 min (`acregmax`/`acdirmax`) — the cache lifetime you'd otherwise wait out.
- Security framing: `no_root_squash` = client root is server root over NFS. Negligible risk for a trusted single-admin host that already has full `rw` to the shares; that's why it's the right tool here. Revert to `root_squash` afterward as a tightening.

## Verified On

| Project | Context | Details |
|---------|---------|---------|
| apollo homelab | Live NFS data migration (2026-06); backing up owner-restricted files from a ReadyNAS export over NFSv3 | `no_root_squash` + `sync; echo 3 > /proc/sys/vm/drop_caches` took rsync from ~3,064 denials to 0 |
