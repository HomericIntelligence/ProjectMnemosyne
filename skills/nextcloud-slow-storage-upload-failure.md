---
name: nextcloud-slow-storage-upload-failure
description: "Diagnose Nextcloud 'I can't upload' reports by proving whether the cause is SLOW BACKING STORAGE (NFS / remote data dir) rather than Nextcloud itself, using a WebDAV chunked-vs-direct-PUT signature. Use when: (1) users report uploads that hang, time out, or take seconds for tiny files, (2) the Nextcloud data dir lives on NFS / a NAS / other remote storage, (3) you need to distinguish a storage I/O bottleneck from a Nextcloud config or brute-force-throttle problem before touching either."
category: debugging
date: 2026-06-25
version: "1.0.0"
user-invocable: false
verification: verified-local
tags: []
---

# Nextcloud Slow Storage Upload Failure

## Overview

| Field | Value |
|-------|-------|
| Objective | Users reported "I can't upload" to Nextcloud. Determine whether the root cause is the Nextcloud application or the SLOW BACKING STORAGE (an NFS-mounted / remote data directory) before changing anything. |
| Central lesson | Reproduce uploads over WebDAV with a throwaway user and compare CHUNKED upload vs a DIRECT PUT. If chunked succeeds (all `201`) but a direct PUT of a TINY file hangs / times out / takes seconds, the bottleneck is storage metadata + write speed (`.part` → fsync → RENAME → stat → DB-update), NOT Nextcloud. No Nextcloud config fixes a slow disk. |
| Worked example | Dockerized Nextcloud with its data dir on an NFS share exported by a NAS. Direct PUT of a tiny file ~5s; a BRAND-NEW user's first PUT timed out at ~30s (first write also creates the home dir + copies the skeleton). Chunked uploads all returned `201`. |
| Outcome | Root-caused to server-side storage I/O: NFS write ~2-6 MB/s and rename ~1.7s on a healthy sub-ms LAN. Fix belongs on the storage server (`sync`→`async`+`no_wdelay`, SMART/disk health, more nfsd threads, or faster data dir) — not in Nextcloud. |
| Verification | verified-local — all signatures reproduced live this session via `curl` WebDAV, `docker exec ... occ`, `dd conv=fsync`, and `mv` timing on the actual hosts, NOT via CI. |

## When to Use

Use this methodology when:

- Nextcloud users report uploads that hang, time out, or take many seconds for even a tiny file, while the rest of the web UI feels responsive.
- The Nextcloud data directory lives on NFS, a NAS, or any remote / networked storage rather than a local SSD.
- A brand-new user cannot upload at all (times out) while existing users are merely slow — a strong tell for storage that is slow enough that the extra first-write work (home dir + skeleton copy) crosses the timeout.
- You are tempted to "fix" it with a Nextcloud config knob (`part_file_in_storage`, `tempdirectory`) before proving WHERE the time goes.

Do NOT assume the app is at fault, and do NOT hammer WebDAV with repeated auth while testing — that trips brute-force protection and its throttle delay MASQUERADES as an upload hang.

## Verified Workflow

The core value of this skill is the CHUNKED-vs-DIRECT-PUT signature plus raw host benchmarks. Run in order.

### 0. Run occ as the container's web PUID (not www-data)

On installs that set a custom `PUID`, `php occ` must run as that uid, not `www-data`.

```bash
docker exec -u 1002 nextcloud_nextcloud_1 php occ status
docker exec -u 1002 nextcloud_nextcloud_1 php occ config:list system | grep -iE 'datadirectory|tempdirectory'
```

### 1. Create a throwaway test user (avoids polluting real accounts)

```bash
# OC_PASS avoids putting the password on the command line / in history:
docker exec -e OC_PASS='TestPass123!' -u 1002 nextcloud_nextcloud_1 \
  php occ user:add --password-from-env testuploader
```

### 2. Reproduce the two upload paths over WebDAV and COMPARE

CHUNKED upload — what the web UI and modern desktop/mobile clients actually use:

```bash
BASE=https://nextcloud.example.com
U=testuploader; P='TestPass123!'; ID=$(date +%s)
# 1. MKCOL the upload session:
curl -s -o /dev/null -w '%{http_code}\n' -u "$U:$P" -X MKCOL \
  "$BASE/remote.php/dav/uploads/$U/$ID"
# 2. PUT a chunk:
curl -s -o /dev/null -w '%{http_code}\n' -u "$U:$P" -T ./tinyfile \
  "$BASE/remote.php/dav/uploads/$U/$ID/00001"
# 3. MOVE (assemble) to the target file, declaring total length:
curl -s -o /dev/null -w '%{http_code}\n' -u "$U:$P" -X MOVE \
  -H "Destination: $BASE/remote.php/dav/files/$U/tiny-chunked.bin" \
  -H "OC-Total-Length: $(stat -c%s ./tinyfile)" \
  "$BASE/remote.php/dav/uploads/$U/$ID/.file"
```

DIRECT PUT — single request straight to the file endpoint:

```bash
curl -s -o /dev/null -w 'code=%{http_code} time=%{time_total}s\n' -u "$U:$P" \
  -T ./tinyfile "$BASE/remote.php/dav/files/$U/tiny-direct.bin"
```

Interpretation:

| Observation | Conclusion |
|-------------|------------|
| Chunked all `201` but DIRECT PUT hangs / times out / takes SECONDS for a tiny file | Storage metadata + write speed is the bottleneck (direct PUT does `.part` → fsync → RENAME → stat → DB-update on the slow disk) |
| Brand-new user's FIRST PUT times out (~30s) but an existing user's PUT merely takes ~5s | Confirms slow storage — the first write ALSO creates the home dir and copies the skeleton, pushing it past the timeout |
| Both paths fast | Storage is NOT the bottleneck; look elsewhere (network, PHP, DB) |

### 3. Confirm with raw host benchmarks against the DATA DIR

Bypass Nextcloud entirely and measure the share directly:

```bash
DATADIR=/mnt/nas/nextcloud-data          # the actual data dir from occ config:list
# Write throughput (single final fsync):
dd if=/dev/zero of="$DATADIR/.bench" bs=1M count=20 conv=fsync   # report MB/s
# Rename cost (this is what a direct PUT does at the end):
time mv "$DATADIR/.bench" "$DATADIR/.bench2"
rm -f "$DATADIR/.bench2"
# Compare against LOCAL disk to prove it is the share, not the box:
dd if=/dev/zero of=/tmp/.bench bs=1M count=20 conv=fsync; rm -f /tmp/.bench
```

Verdict: single-digit MB/s write + a rename >1s on a LAN with healthy sub-ms ping = SERVER-SIDE storage I/O bottleneck (slow / failing disk, `sync` NFS export, or an underpowered NAS). Also run `df -h "$DATADIR"` — ZFS/btrfs slow badly when near-full.

### Quick Reference

| Step | Command | What it proves |
|------|---------|----------------|
| occ as web PUID | `docker exec -u 1002 <ctr> php occ status` | occ runs at all (custom PUID, not www-data) |
| Throwaway user | `occ user:add --password-from-env` with `OC_PASS` | Test without touching real accounts |
| Chunked upload | `MKCOL` → `PUT .../00001` → `MOVE .../.file` + `OC-Total-Length` | The path the UI uses; expect all `201` |
| Direct PUT | `curl -T file .../dav/files/<u>/<name>` with `-w %{time_total}` | Isolates storage rename/metadata cost |
| Host write | `dd if=/dev/zero of=<datadir>/.b bs=1M count=20 conv=fsync` | Raw write MB/s of the share |
| Host rename | `time mv` on the share vs local | Metadata/rename latency (the real killer) |
| Fullness | `df -h <datadir>` | Near-full ZFS/btrfs = slow |
| NFS version | `rpcinfo -p <nas> \| grep nfs` | Which NFS versions the NAS actually exports |
| Un-throttle | `occ security:bruteforce:reset <ip>` | Clears a throttle that masquerades as a hang |

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
|---------|----------------|---------------|----------------|
| Ran `occ` as `www-data` | `docker exec -u www-data <ctr> php occ ...` | This install sets a custom `PUID`; occ must run as that uid (e.g. `1002`) | On custom-PUID installs run `occ` as the web PUID, not `www-data` |
| Repeatedly re-authed WebDAV while testing | Hammered auth with many `curl` attempts (some with wrong creds) | Tripped Nextcloud brute-force protection — later requests got `401` or a THROTTLE DELAY that looked like an upload "hang" | A "hang" can be a throttle delay. Use unique/successful creds, don't hammer; reset via `occ security:bruteforce:reset <ip>` and inspect `oc_bruteforce_attempts` |
| Nextcloud-side config mitigations | Set `part_file_in_storage=false` and `tempdirectory=/tmp` | Barely helped — the FINAL file must still land on the slow storage; `tempdirectory` already defaults to a local path | No Nextcloud config fixes a slow-disk problem; the fix is on the storage server |
| Panicked that `/mnt/nas` "is NOT a mountpoint" | Ran `mountpoint /mnt/nas` and saw it fail | The NFS shares mount as SUBDIRECTORIES (e.g. `/mnt/nas/Documents`); `/mnt/nas` itself is a plain local dir | Check the SPECIFIC subdir: `mountpoint /mnt/nas/<share>`, not the parent |
| Remount client as NFSv4 to speed it up | `mount -t nfs -o vers=4 <nas>:/... /mnt/...` | Failed `mount.nfs: Protocol not supported` — the NAS only exports NFSv2/3 | Verify exported versions first: `rpcinfo -p <nas> \| grep nfs`; do not assume v4 is available |

## Results & Parameters

### occ helpers (run as the web PUID)

```bash
CTR=nextcloud_nextcloud_1; PUID=1002
docker exec -u $PUID $CTR php occ config:list system | grep -iE 'datadirectory|tempdirectory'
# Throwaway test user (password via env, not argv):
docker exec -e OC_PASS='TestPass123!' -u $PUID $CTR php occ user:add --password-from-env testuploader
# Clear a brute-force throttle that masquerades as a hang:
docker exec -u $PUID $CTR php occ security:bruteforce:reset 203.0.113.7
```

### WebDAV reproduction (chunked vs direct)

```bash
BASE=https://nextcloud.example.com; U=testuploader; P='TestPass123!'; ID=$(date +%s)
# CHUNKED (what UI/clients use) — expect 201 on each:
curl -s -o /dev/null -w '%{http_code}\n' -u "$U:$P" -X MKCOL "$BASE/remote.php/dav/uploads/$U/$ID"
curl -s -o /dev/null -w '%{http_code}\n' -u "$U:$P" -T ./tinyfile "$BASE/remote.php/dav/uploads/$U/$ID/00001"
curl -s -o /dev/null -w '%{http_code}\n' -u "$U:$P" -X MOVE \
  -H "Destination: $BASE/remote.php/dav/files/$U/tiny-chunked.bin" \
  -H "OC-Total-Length: $(stat -c%s ./tinyfile)" \
  "$BASE/remote.php/dav/uploads/$U/$ID/.file"
# DIRECT PUT — time it:
curl -s -o /dev/null -w 'code=%{http_code} time=%{time_total}s\n' -u "$U:$P" \
  -T ./tinyfile "$BASE/remote.php/dav/files/$U/tiny-direct.bin"
```

### Host benchmarks against the data dir

```bash
DATADIR=/mnt/nas/nextcloud-data
dd if=/dev/zero of="$DATADIR/.bench" bs=1M count=20 conv=fsync      # write MB/s
time mv "$DATADIR/.bench" "$DATADIR/.bench2"; rm -f "$DATADIR/.bench2"   # rename latency
dd if=/dev/zero of=/tmp/.bench bs=1M count=20 conv=fsync; rm -f /tmp/.bench   # local baseline
df -h "$DATADIR"                                                     # near-full check
mountpoint /mnt/nas/<share>                                         # check the SUBDIR, not the parent
rpcinfo -p <nas-ip> | grep nfs                                      # which NFS versions are exported
```

### Numbers observed this session

| Metric | Slow NFS share | Local disk |
|--------|----------------|-----------|
| Sequential write (`dd conv=fsync`) | ~2-6 MB/s | ~877 MB/s |
| Rename (`mv`) | ~1.7s | instant |
| Read | ~20 MB/s | (fast) |
| Direct PUT, tiny file | ~5s (existing user) | — |
| Direct PUT, brand-new user's FIRST write | ~30s TIMEOUT | — |
| Chunked upload (MKCOL/PUT/MOVE) | all `201` | — |
| LAN ping | healthy sub-ms | — |

### The fix (storage server, NOT Nextcloud)

- Switch the NFS export from `sync` to `async` + `no_wdelay` on the storage server.
- Check SMART / disk health for a slow or failing drive.
- Raise the nfsd thread count on the NAS.
- Or move the Nextcloud data dir to faster (local/SSD) storage.
- If storage is near-full (ZFS/btrfs), free space — allocation slows dramatically when full.

Ruled OUT as fixes: `part_file_in_storage=false`, `tempdirectory=/tmp` (final file still lands on slow storage); NFSv4 remount (NAS only exports v2/3). Watch for brute-force throttle delays masquerading as upload hangs during testing.
