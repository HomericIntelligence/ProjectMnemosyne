---
name: docker-container-writable-layer-log-bloat
description: "Diagnose and fix Docker containers accumulating gigabytes of log data in their overlay2 writable layer due to log files written to internal paths not bind-mounted to the host. Use when: (1) docker system df shows unexpectedly large container sizes, (2) a long-running container's writable layer has grown to GBs, (3) host disk usage is unexplained and containers are suspects."
category: tooling
date: 2026-06-20
version: "1.0.0"
user-invocable: false
verification: verified-local
tags:
  - docker
  - compose
  - writable-layer
  - overlay2
  - log-bloat
  - disk
  - traefik
  - bind-mount
  - docker-diff
  - logrotate
---

# Docker Container Writable-Layer Log Bloat

## Overview

| Field | Value |
|-------|-------|
| **Date** | 2026-06-20 |
| **Objective** | Identify and recover disk space consumed by log files accumulating inside Docker container writable layers |
| **Outcome** | Successful — freed 72 GB on apollo by bind-mounting Traefik log dir and recreating container |
| **Verification** | verified-local |

## When to Use

- `docker system df` shows containers consuming unexpectedly large disk (GBs or tens of GBs)
- A long-running container has a writable layer far larger than the image itself
- Host disk is filling up but no large files appear under `/var`, `/home`, or application directories
- A stateless service (reverse proxy, load balancer, gateway) has been running for months or years without restarts
- You suspect a container writes logs internally but you cannot find those logs on the host

## Verified Workflow

### Quick Reference

```bash
# 1. Survey — which containers are large?
docker system df -v | grep -v "^REPOSITORY\|^IMAGE\|^VOLUME\|^Build" | sort -k4 -rh | head -20

# 2. Find what changed inside the container
docker diff <container_name>

# 3. Confirm the file contents
docker exec <container_name> tail -20 /var/log/traefik/access.log

# 4. Fix: add bind-mount, recreate (drops the writable layer)
mkdir -p /var/homelabos/traefik/logs
# Add to docker-compose.yml volumes:
#   - "/var/homelabos/traefik/logs:/var/log/traefik"
docker stop <container_name> && docker rm <container_name>
docker compose up -d

# 5. Verify logs now appear on the host
ls -lh /var/homelabos/traefik/logs/
```

### Detailed Steps

1. **Survey container disk usage.** Run `docker system df` for a summary. If containers show large SIZE, run `docker system df -v` which lists every container with its writable-layer size. Sort by size descending to find the culprit.

2. **Identify internal file accumulation with `docker diff`.** Run `docker diff <container>` — this compares the container's current filesystem against its image. Lines starting with `A` are files added by the running container (not in the image). Log files accumulating over months appear here (e.g., `A /var/log/traefik/access.log`).

3. **Confirm the file type.** Run `docker exec <container> tail -20 <path>` to verify the content. Plain HTTP access logs, application logs, or audit logs are the typical culprits.

4. **Root-cause the configuration.** Inspect the application config for log `filePath` settings that point to internal container paths rather than stdout/stderr or bind-mounted host paths.
   - For Traefik: check `traefik.yaml` for `log.filePath` and `accessLog.filePath`
   - For other apps: check for any log output path that is NOT a Docker volume or bind-mount

5. **Fix: bind-mount the log directory to the host.**
   - Add a bind-mount in `docker-compose.yml`:
     ```yaml
     volumes:
       - "/var/homelabos/traefik/logs:/var/log/traefik"
     ```
   - Create the host directory: `mkdir -p /var/homelabos/traefik/logs`

6. **Recreate the container** (this is what reclaims the disk — `docker restart` does NOT drop the writable layer):
   ```bash
   docker stop <container_name>
   docker rm <container_name>
   docker compose up -d
   ```

7. **Verify.** Check that logs appear on the host: `ls -lh /var/homelabos/traefik/logs/`. Run `docker system df` again to confirm the writable-layer size is now small (KB, not GB).

8. **Set up logrotate for the host-side log files** to prevent future unbounded growth:
   ```
   /var/homelabos/traefik/logs/*.log {
       daily
       rotate 14
       compress
       missingok
       notifempty
       sharedscripts
   }
   ```

### Prevention: Docker Global Log Options

Set global log rotation for all containers' stdout/stderr in `/etc/docker/daemon.json`:

```json
{
  "log-driver": "json-file",
  "log-opts": {
    "max-size": "50m",
    "max-file": "3"
  }
}
```

Restart Docker after: `systemctl restart docker`. This caps stdout/stderr logs but does NOT affect files written directly to the container filesystem — those require bind-mounts.

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
|---------|----------------|---------------|----------------|
| `docker restart` to reclaim space | Restarted the container hoping it would free the writable layer | `docker restart` keeps the container and its writable layer intact — only `docker rm` drops it | Must stop AND remove the container to reclaim writable-layer disk |
| Looking for large files on the host | Searched host filesystem under `/var`, `/home`, app dirs | Files inside a container writable layer do not appear on the host filesystem at predictable paths | Use `docker diff` to find files added inside the container, not host `find` |
| `docker system prune` | Ran prune hoping it would clean up the container | `docker system prune` removes only stopped containers, dangling images, and unused networks — it does not touch running containers | Must explicitly `docker stop && docker rm` the container first |
| Relying on container log driver for file logs | Assumed the json-file log driver would cap the log growth | The json-file log driver only captures stdout/stderr; files written directly to the container filesystem bypass it entirely | Log rotation via daemon.json only covers stdout/stderr, not internal file writes |

## Results & Parameters

### Environment

| Parameter | Value |
|-----------|-------|
| Host | apollo (HomelabOS server) |
| Container | homelabos (Traefik v2.2 reverse proxy) |
| Runtime duration | ~5 years without recreation |
| Writable layer size before fix | 76.3 GB |
| Disk freed after fix | ~72 GB |
| Container status after fix | Healthy, logs writing to host path |

### Traefik Config That Caused the Problem

```yaml
# traefik.yaml — paths not bind-mounted = writable-layer accumulation
log:
  filePath: /var/log/traefik/traefik.log
accessLog:
  filePath: /var/log/traefik/access.log
```

### docker-compose.yml Fix

```yaml
services:
  traefik:
    image: traefik:v2.2
    volumes:
      # Fix: bind-mount log dir so logs land on host, not writable layer
      - "/var/homelabos/traefik/logs:/var/log/traefik"
```

### Key Commands

```bash
# Find large containers
docker system df -v

# Find what a container wrote internally (vs its image)
docker diff <container_name>

# Check content of a suspected log file
docker exec <container_name> tail -20 /path/to/log

# Recreate to drop writable layer (the actual disk reclaim step)
docker stop <name> && docker rm <name> && docker compose up -d

# Audit ALL running containers for internal file writes
for c in $(docker ps -q); do
  name=$(docker inspect --format '{{.Name}}' "$c")
  count=$(docker diff "$c" | wc -l)
  echo "$count changes: $name"
done | sort -rn | head -20
```

## Verified On

| Project | Context | Details |
|---------|---------|---------|
| HomelabOS (apollo) | Traefik v2.2 running 5 years, 76.3 GB writable layer | Freed 72 GB by bind-mounting log dir and recreating container |
