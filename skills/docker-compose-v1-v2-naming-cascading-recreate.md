---
name: docker-compose-v1-v2-naming-cascading-recreate
description: "Diagnose unexpected container recreates when switching from docker-compose v1 (Python binary) to docker compose v2 (Go CLI plugin) on a project with existing containers. Use when: (1) running `docker compose up -d <single-service>` unexpectedly reports Recreate for OTHER services you did not target, (2) container names change from underscore (`project_service_1`) to hyphen (`project-service-1`) after an update, (3) a service without an explicit `container_name:` gets swept into a naming migration triggered by a sibling service's update, (4) you see a transient `No such container: <hex-id>` error mid-operation on a project with mixed v1/v2 history."
category: debugging
date: 2026-07-06
version: "1.0.0"
user-invocable: false
verification: verified-local
tags: [docker, docker-compose, container-naming, recreate, cascading-recreate]
---

# Docker Compose v1 to v2 Naming Cascading Recreate

## Overview

| Field | Value |
|-------|-------|
| **Date** | 2026-07-06 |
| **Objective** | Understand why bumping a single service's image with `docker compose` (v2) unexpectedly recreated sibling services on a project whose containers were originally created with `docker-compose` (v1) |
| **Outcome** | Root cause identified (v1 to v2 container naming convention change) and confirmed safe in all three observed cases — no data loss, since affected services used bind-mounted host paths |
| **Verification** | verified-local |

## When to Use

- You need to bump an image tag or otherwise update ONE service in an existing Docker
  Compose project using the modern `docker compose` (v2, no hyphen, Go plugin) CLI, but
  the project's containers currently exist under the legacy `docker-compose` (v1, Python
  binary) naming scheme.
- Running `docker compose up -d <service>` reports `Recreate` for services you did NOT
  target on the command line.
- Container names change from `<project>_<service>_<n>` (underscores) to
  `<project>-<service>-<n>` (hyphens) after an otherwise routine update.
- You see a transient `Error response from daemon: No such container: <hex-id>` during
  the operation, and are unsure whether something broke.
- You want to confirm whether an unplanned recreate lost data before investigating further.

## Verified Workflow

### Quick Reference

```bash
# 1. Before being alarmed by an unplanned Recreate, check whether the container's data
#    lives on a bind mount (safe) or an anonymous/named volume (verify separately):
docker inspect <service> --format '{{json .Mounts}}' | python3 -m json.tool
# Look for "Type": "bind" (host path preserved across recreate) vs "Type": "volume".

# 2. After the operation completes, confirm the end state rather than trusting
#    transitional log noise (Recreate messages, transient "No such container" errors):
docker ps -a --filter "name=<project>" --format '{{.Names}}\t{{.Image}}\t{{.Status}}'
# Confirm: (a) no duplicate/orphaned OLD-named containers left alongside new ones,
# (b) all expected services are Up, (c) image tags on services you did NOT intend to
# touch are unchanged (only the container NAME changed, not the image).

# 3. Permanent fix to prevent future cascades: pin container_name explicitly for every
# service in the compose file so neither v1 nor v2 naming conventions matter:
#   services:
#     db:
#       container_name: myproject_db
```

### Detailed Steps

1. **Recognize the trigger condition.** A Compose project was originally deployed years
   ago with the legacy `docker-compose` v1 binary, which names containers
   `<project>_<service>_<n>` (underscore-delimited). The v1 binary is broken/unavailable,
   so the modern `docker compose` v2 plugin (no hyphen, bundled with modern Docker) is
   used instead to bump an image tag on one service.

2. **Understand the naming mismatch.** v2's default container naming convention is
   `<project>-<service>-<n>` (hyphen-delimited) for any service that does NOT have an
   explicit `container_name:` set in the compose file. When v2 evaluates a project whose
   containers currently exist under the v1 underscore scheme, it does not recognize the
   existing container as a match for that service (different name/label expectations) —
   so it silently plans a **recreate** under the new dash-named convention, even though
   nothing about that service's actual configuration changed.

3. **Understand the cascade.** This recreate is not limited to the service you targeted.
   Because `docker compose up -d <service>` still evaluates the full dependency graph,
   ANY service reachable via `depends_on` that also lacks an explicit `container_name:`
   can get swept into the same v1-to-v2 naming migration and get recreated too — even
   though you only intended to update one service's image tag.

4. **This was observed three times in one session** on a homelab host bumping image
   versions across independent projects:
   - Bumping Gitea's image and running `docker compose up -d gitea` ALSO recreated the
     `db` (MariaDB) service, purely because `db` had no `container_name:` set and got
     swept into the v1 to v2 naming migration alongside `gitea`.
   - Bumping coturn's image similarly renamed `talk_hpb_coturn_1` to
     `talk_hpb-coturn-1`.
   - Running `docker compose pull nextcloud-redis && docker compose up -d
     nextcloud-redis` also recreated the Traefik container's network attachment
     reference — a separate incident with a different root cause (see the
     `docker-traefik-network-loss-on-recreation` skill), noted here only as context for
     how often unexpected recreates surfaced in the same session.

5. **Verify data safety before treating the recreate as alarming.** As long as the
   affected service's data lives on a bind-mounted host path (not an anonymous/named
   Docker volume), a container recreate does NOT lose data — a new container instance
   is simply created against the same host directory:

   ```bash
   docker inspect <service> --format '{{json .Mounts}}' | python3 -m json.tool
   # "Type": "bind"   -> host path preserved, safe
   # "Type": "volume" -> probably fine if it is the SAME named volume, but double-check
   #                     the volume itself was not also renamed/orphaned.
   ```

6. **Check the actual end state, not the transitional log noise.** An unexpected
   `Recreate` line for a sibling service, or a transient
   `Error response from daemon: No such container: <hex-id>` mid-operation (a race
   during the mixed-convention transition), does not by itself mean something broke:

   ```bash
   docker ps -a --filter "name=<project>" --format '{{.Names}}\t{{.Image}}\t{{.Status}}'
   ```

   Confirm: (a) no duplicate/orphaned OLD-named containers remain alongside the new
   ones, (b) all expected services show `Up`, (c) image tags on services you did NOT
   intend to touch are unchanged — only the container NAME changed, not the image.

7. **For the Gitea/db case specifically**, data integrity was additionally confirmed
   with an application-level health check after the unplanned DB recreate:

   ```bash
   docker exec <gitea-container> gitea doctor check --all
   # 28/28 checks OK -> no corruption from the unplanned DB container recreate
   ```

8. **Prevent future cascades** by setting an explicit `container_name:` on every service
   in a compose file that mixes v1 history with v2 tooling — this removes v2's
   auto-naming from the equation entirely, so future updates to one service can never
   trigger a naming-driven recreate of another.

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
|---------|----------------|---------------|-----------------|
| Assuming an unexpected `Recreate` line meant something was broken | Treated any sibling-service `Recreate` output as evidence of misconfiguration and started investigating compose file diffs for unrelated services | The recreate was actually caused by v1 to v2 naming migration, not by an actual config drift; there was no misconfiguration to find | Check the final `docker ps -a` state and mount types FIRST, before assuming a config bug — the transitional log noise (Recreate, transient "No such container") is a known side effect of the naming migration, not necessarily a real problem |
| Assuming a transient `No such container: <hex-id>` error meant the operation failed | Treated the mid-operation error as a hard failure requiring rollback | The error was a transient race during the mixed v1/v2 naming transition; the operation completed successfully and the final state was clean | Verify the end state with `docker ps -a` rather than reacting to a single transitional error line during a recreate |
| Assuming data loss because "the database container got recreated" | Was ready to restore from backup after `db` was unexpectedly recreated by a Gitea image bump | `db` used a bind-mounted host path, so the recreate did not touch the underlying data directory at all | Always check `docker inspect <service> --format '{{json .Mounts}}'` for `"Type": "bind"` vs `"volume"` before assuming a recreate caused data loss |

## Results & Parameters

**Naming convention comparison:**

| CLI generation | Container name pattern | Example |
|-----------------|------------------------|---------|
| `docker-compose` (v1, Python binary) | `<project>_<service>_<n>` (underscores) | `talk_hpb_coturn_1` |
| `docker compose` (v2, Go plugin) | `<project>-<service>-<n>` (hyphens) | `talk_hpb-coturn-1` |

**Mount-type verification (run before reacting to any unexpected recreate):**

```bash
docker inspect <service> --format '{{json .Mounts}}' | python3 -m json.tool
```

**End-state verification (run after any `docker compose up -d <service>` that reports
extra recreates or a transient error):**

```bash
docker ps -a --filter "name=<project>" --format '{{.Names}}\t{{.Image}}\t{{.Status}}'
```

**Application-level integrity check used for the Gitea/db case:**

```bash
docker exec <gitea-container> gitea doctor check --all
# Result observed: 28/28 checks OK
```

**Permanent mitigation** — pin `container_name:` on every service that lacks one, in any
compose project with v1-era history:

```yaml
services:
  db:
    container_name: myproject_db
  redis:
    container_name: myproject_redis
```

**Three real recreates observed in one session, all confirmed clean:**

| Service updated | Sibling(s) unexpectedly recreated | Root cause | Data at risk? |
|-----------------|-------------------------------------|------------|----------------|
| Gitea (image bump) | `db` (MariaDB) | `db` had no `container_name:`; swept into v1 to v2 naming migration | No — bind-mounted host path |
| coturn (image bump) | (self) `talk_hpb_coturn_1` -> `talk_hpb-coturn-1` | Same service renamed under v2 convention | No — bind-mounted host path |
| nextcloud-redis (image bump) | Traefik network attachment | Separate root cause (external network not declared in Traefik's own compose file); not the v1/v2 naming issue, noted for context only | See `docker-traefik-network-loss-on-recreation` skill |

## Verified On

| Project | Context | Details |
|---------|---------|---------|
| HomeLab (apollo) | Gitea + MariaDB, Nextcloud Talk HPB coturn, Nextcloud redis — image version bumps in one session using `docker compose` v2 on projects with v1-era container names | Confirmed via `docker ps -a` clean end states on all three services; `gitea doctor check --all` (28/28 OK) additionally confirmed no DB corruption |
