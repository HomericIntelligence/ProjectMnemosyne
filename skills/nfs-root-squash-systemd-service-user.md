---
name: nfs-root-squash-systemd-service-user
description: "Fix systemd services that silently fail to write to NFS shares due to root_squash. Use when: (1) a systemd service running as root fails to write to NFS mounts, (2) per-file sync failures appear despite rw mount, (3) touch/write as root returns 'Read-only file system' on an NFS share."
category: debugging
date: 2026-06-23
version: "1.0.0"
user-invocable: false
verification: verified-local
tags: []
---

# NFS Root-Squash Blocks Systemd Service Writes

## Overview

| Field | Value |
|-------|-------|
| **Date** | 2026-06-23 |
| **Objective** | Fix systemd service (running as root) that silently fails to write to NFS shares with root_squash |
| **Outcome** | Successful — adding `User=<username>` to the service unit resolves the issue |
| **Verification** | verified-local |

## When to Use

- A systemd service running as root silently fails to write to an NFS share
- Sync tool (unison, rsync) reports per-file "failed:" for every file being copied to an NFS mount
- `touch /mnt/nas/somefile` as root returns "Read-only file system" or "Permission denied" even though the mount is `rw`
- NFS share has `root_squash` enabled (default on most NFS servers) and the service runs as uid 0
- Other users (non-root) can write to the same NFS path fine

## Verified Workflow

> Verified locally on Debian. CI validation pending.

### Quick Reference

```bash
# 1. Edit the service unit
systemctl edit --full <service-name>

# Add to [Service] section:
# User=<username-who-owns-nfs-files>
# Environment=HOME=/home/<username>

# 2. Fix log file ownership
chown <username> /var/log/<service>.log

# 3. Reload and restart
systemctl daemon-reload
systemctl restart <service-name>

# 4. Verify writes work
sudo -u <username> touch /mnt/nas/test-write && echo "OK" && sudo -u <username> rm /mnt/nas/test-write
```

### Detailed Steps

1. **Identify the NFS root_squash problem**: Run `touch /mnt/nas/somedir/test` as root. If it returns "Read-only file system" or "Permission denied" while the mount shows `rw`, root_squash is active. Confirm with `cat /proc/mounts | grep nfs` or `showmount -e <server>`.

2. **Edit the systemd service unit** to run as the NFS share owner instead of root:

   ```ini
   [Service]
   Type=oneshot
   User=mvillmow
   Environment=HOME=/home/mvillmow
   ExecStart=/usr/local/bin/nas-usb-sync.sh
   ```

   Use `systemctl edit --full <service>` or directly edit the unit file in `/etc/systemd/system/`.

3. **Fix log file ownership**: If the service writes to a log file created as root, transfer ownership:

   ```bash
   chown <username> /var/log/<service>.log
   ```

4. **Reload systemd and restart the service**:

   ```bash
   systemctl daemon-reload
   systemctl restart <service-name>
   ```

5. **Verify**: Check `journalctl -u <service-name> -n 50` for errors. Confirm writes now succeed.

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
|---------|----------------|---------------|----------------|
| Root service default | Run systemd service as root (default, no User= set) | NFS root_squash maps uid 0 to nobody (uid 99\|65534), blocking all writes | Never run services that write to NFS shares as root when root_squash is enabled |
| sudo in bash (no TTY) | `sudo -u '#1002' -g '#1002' rsync ...` from within a non-interactive bash context | "sudo: no tty present and no askpass program specified" — sudo requires a TTY unless NOPASSWD is set | Use `User=` in the systemd unit instead of sudo inside the script; avoids TTY requirement entirely |

## Results & Parameters

**NFS root_squash behavior:**

| uid | Mapped to | Can write to NFS? |
|-----|-----------|-------------------|
| 0 (root) | nobody (uid 99 or 65534) | No (blocked by root_squash) |
| 1000 (mvillmow) | mvillmow (uid 1000) | Yes (if file permissions allow) |
| Any non-root uid | Same uid | Yes (if file permissions allow) |

**Minimal working service unit:**

```ini
[Unit]
Description=NAS USB Sync

[Service]
Type=oneshot
User=mvillmow
Environment=HOME=/home/mvillmow
ExecStart=/usr/local/bin/nas-usb-sync.sh

[Install]
WantedBy=multi-user.target
```

**Checklist after applying fix:**

- `User=<username>` set in `[Service]` section
- `Environment=HOME=/home/<username>` set if service uses tools that need HOME (unison, rsync with SSH, etc.)
- Log file owned by service user: `chown <username> /var/log/<service>.log`
- `systemctl daemon-reload` run after editing the unit
- Service user has read access to source paths and write access to destination NFS paths

## Verified On

| Project | Context | Details |
|---------|---------|---------|
| apollo homelab | unison two-way NAS\|USB sync via systemd oneshot timer | Service user changed from root to mvillmow (uid 1000); all NFS writes succeeded |
