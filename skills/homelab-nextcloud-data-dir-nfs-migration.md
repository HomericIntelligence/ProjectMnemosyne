---
name: homelab-nextcloud-data-dir-nfs-migration
description: "Migrate Nextcloud data directory from local NVMe to NFS-mounted NAS while keeping core (webroot, config, DB) on fast local storage. Use when: (1) Nextcloud data dir lives on local disk and you want to move it to NAS, (2) HomelabOS Nextcloud compose has NFS bind mounts but NFS was mounted after container start, (3) need to rsync to NFS share that uses root_squash."
category: architecture
date: 2026-06-23
version: "1.0.0"
user-invocable: false
verification: verified-local
tags: []
---

# Homelab Nextcloud Data Directory NFS Migration

## Overview

| Field | Value |
|-------|-------|
| **Date** | 2026-06-23 |
| **Objective** | Migrate Nextcloud's data directory (271 GB) from local NVMe to NFS-mounted NAS, keeping Nextcloud core on fast local NVMe |
| **Outcome** | Successful — Nextcloud confirmed reading from NAS via `df -h /data` showing NFS server IP |
| **Verification** | verified-local (executed end-to-end; CI validation pending) |

## When to Use

- Moving Nextcloud data directory from local disk to a NAS NFS share
- HomelabOS Nextcloud compose already has the NFS path in the bind mount but NFS was mounted after container start (data silently stayed on local disk)
- Rsyncing large data sets to an NFS share that has root_squash enabled (files must be owned by the Nextcloud uid, not root)
- Hardening Docker service startup order so containers wait for NFS mounts

## Verified Workflow

> Verified locally only — CI validation pending.

### Quick Reference

```bash
# 1. Expose hidden local data beneath NFS mount
sudo mount --bind / /mnt/root-view

# 2. Pass 1 rsync (online, no downtime) — run as Nextcloud uid 1002
sudo -u '#1002' -g '#1002' rsync -rltD --partial --info=progress2 \
  /mnt/root-view/mnt/nas/Documents/NextCloud/ \
  /mnt/nas/Documents/NextCloud/

# 3. Enable maintenance mode + stop container
docker exec nextcloud_nextcloud_1 php occ maintenance:mode --on
docker compose -f /var/homelabos/nextcloud/docker-compose.yml stop nextcloud

# 4. Pass 2 rsync (delta, while offline)
sudo -u '#1002' -g '#1002' rsync -rltD --partial --info=progress2 \
  /mnt/root-view/mnt/nas/Documents/NextCloud/ \
  /mnt/nas/Documents/NextCloud/

# 5. Verify before cutover
diff <(cd /mnt/root-view/mnt/nas/Documents/NextCloud && find . | sort) \
     <(cd /mnt/nas/Documents/NextCloud && find . | sort)
# Must produce no output

# 6. Start container (NFS already mounted, bind resolves to NFS)
docker compose -f /var/homelabos/nextcloud/docker-compose.yml up -d nextcloud

# 7. Confirm data is on NAS
docker exec nextcloud_nextcloud_1 df -h /data
# Must show NFS server IP (e.g., 192.168.2.11:/data/Documents/NextCloud)

# 8. Disable maintenance mode, then scan files
docker exec nextcloud_nextcloud_1 php occ maintenance:mode --off
docker exec nextcloud_nextcloud_1 php occ files:scan --all
```

### Detailed Steps

1. **Understand the root cause (if data is on local disk despite NFS bind in compose)**

   HomelabOS Nextcloud compose may already have the correct NFS path as the bind source
   (e.g., `/mnt/nas/Documents/NextCloud:/data`). If NFS was not mounted when Docker started
   the container, Docker resolved the bind to the bare local directory at that path — silently
   writing 271 GB locally. The compose is correct; only the startup order needs fixing.

2. **Expose the hidden local data**

   The live NFS mount sits on top of the local directory, hiding it. Use a bind view of the
   root filesystem to access it:

   ```bash
   sudo mkdir -p /mnt/root-view
   sudo mount --bind / /mnt/root-view
   # Local data is now visible at:
   # /mnt/root-view/mnt/nas/Documents/NextCloud/
   ```

3. **Identify Nextcloud's container uid**

   ```bash
   docker exec nextcloud_nextcloud_1 id www-data
   # uid=1002(www-data) gid=1002(www-data)
   ```

   All rsync runs must use this uid because the NFS export has `root_squash` — root writes
   land as `nobody` (99:99).

4. **Pass 1 rsync — online, no downtime**

   ```bash
   sudo -u '#1002' -g '#1002' rsync -rltD --partial --info=progress2 \
     /mnt/root-view/mnt/nas/Documents/NextCloud/ \
     /mnt/nas/Documents/NextCloud/
   ```

   This catches the bulk of the data while Nextcloud is still serving users.

5. **Take Nextcloud offline for the delta pass**

   ```bash
   docker exec nextcloud_nextcloud_1 php occ maintenance:mode --on
   docker compose -f /var/homelabos/nextcloud/docker-compose.yml stop nextcloud
   ```

6. **Pass 2 rsync — delta only**

   Same command as Pass 1. Catches files changed during Pass 1.

7. **Verify file tree is identical**

   ```bash
   diff <(cd /mnt/root-view/mnt/nas/Documents/NextCloud && find . | sort) \
        <(cd /mnt/nas/Documents/NextCloud && find . | sort)
   ```

   Output must be empty. Also confirm `.ocdata` is owned by uid 1002:

   ```bash
   ls -la /mnt/nas/Documents/NextCloud/.ocdata
   ```

8. **Restart container**

   With NFS already mounted, Docker resolves the bind to the NFS share:

   ```bash
   docker compose -f /var/homelabos/nextcloud/docker-compose.yml up -d nextcloud
   docker exec nextcloud_nextcloud_1 df -h /data
   # 192.168.2.11:/data/Documents/NextCloud  ...
   ```

9. **Reclaim local disk space (fail-safe first)**

   Move local data to `.OLD` rather than deleting immediately. An empty local mountpoint
   acts as a fail-safe: if NFS fails at boot, Nextcloud sees no `.ocdata` and halts instead
   of silently re-forking 271 GB locally.

   ```bash
   sudo mv /mnt/root-view/mnt/nas/Documents/NextCloud \
           /mnt/root-view/mnt/nas/Documents/NextCloud.OLD
   sudo mkdir -p /mnt/root-view/mnt/nas/Documents/NextCloud
   # After verification period, delete OLD:
   sudo rm -rf /mnt/root-view/mnt/nas/Documents/NextCloud.OLD
   ```

10. **Harden boot startup order**

    Create a systemd drop-in so Docker waits for NFS before starting containers:

    ```bash
    sudo mkdir -p /etc/systemd/system/docker.service.d/
    sudo tee /etc/systemd/system/docker.service.d/wait-nas.conf <<'EOF'
    [Unit]
    RequiresMountsFor=/mnt/nas/Documents
    EOF
    sudo systemctl daemon-reload
    ```

11. **Disable maintenance mode and reconcile DB**

    ```bash
    docker exec nextcloud_nextcloud_1 php occ maintenance:mode --off
    docker exec nextcloud_nextcloud_1 php occ files:scan --all
    # Scan completes in ~33 seconds for 271 GB / 48,346 files
    ```

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
|---------|----------------|---------------|----------------|
| rsync as root to NFS | `sudo rsync ... /mnt/nas/Documents/NextCloud/` | NFS export has root_squash; all files landed owned nobody (99:99); Nextcloud cannot read them | Always rsync to NFS as the Nextcloud uid (`sudo -u '#1002' -g '#1002'`), never as root |
| rsync without bind view | `sudo -u '#1002' rsync /mnt/nas/Documents/NextCloud/ ...` | Source path is the live NFS mount itself, not the local data hidden beneath it — copies NFS back to NFS | Mount a bind view of `/` first to expose the hidden local directory |
| occ files:scan in maintenance mode | `docker exec ... php occ files:scan --all` while `maintenance:mode --on` | Returns "database isn't accessible" | Disable maintenance mode before running `occ files:scan`; maintenance mode blocks DB access |

## Results & Parameters

```
Nextcloud container user:  uid=1002 gid=1002
Total data:                271 GB, 610 folders, 48,346 files
files:scan duration:       ~33 seconds

NFS fstab entry:
  192.168.2.11:/data/Documents  /mnt/nas/Documents  nfs  defaults,_netdev,soft,timeo=30,retrans=3  0  0

Systemd drop-in (/etc/systemd/system/docker.service.d/wait-nas.conf):
  [Unit]
  RequiresMountsFor=/mnt/nas/Documents

MariaDB dump (container renamed mysqldump to mariadb-dump):
  docker exec nextcloud_mariadb mariadb-dump --single-transaction \
    -u<user> -p"<pass>" nextcloud > backup.sql

Confirmation command:
  docker exec nextcloud_nextcloud_1 df -h /data
  # 192.168.2.11:/data/Documents/NextCloud  ...
```

## Verified On

| Project | Context | Details |
|---------|---------|---------|
| HomelabOS Nextcloud | apollo homelab server, NVMe to TrueNAS NFS | End-to-end migration; Nextcloud serving from NAS confirmed |
