---
name: dockerized-mariadb-version-upgrade
description: "Safely upgrade a Dockerized MariaDB across a major version and finalize on-disk system tables with zero data loss, while stopping silent version drift. Use when: (1) a Docker Compose MariaDB uses an unpinned `image: mariadb` (resolves to `:latest`) and may have silently drifted to a newer major, (2) you need to run `mariadb-upgrade` to finalize system tables after a version jump, (3) the on-disk upgrade marker looks stale because you checked the legacy `mysql_upgrade_info` instead of `mariadb_upgrade_info`, (4) recreated container has an empty MYSQL_ROOT_PASSWORD env but the stored root password persists on an existing data volume."
category: tooling
date: 2026-06-25
version: "1.0.0"
user-invocable: false
verification: verified-local
tags: []
---

# Dockerized MariaDB Version Upgrade

## Overview

| Field | Value |
|-------|-------|
| **Date** | 2026-06-25 |
| **Objective** | Safely upgrade two live Dockerized MariaDB instances 11.7.2 to 11.8.8 LTS and finalize on-disk system tables with zero data loss, and stop silent version drift |
| **Outcome** | Successful — upgraded a gitea DB (~235MB) and a nextcloud DB (~430MB), all tables OK, both apps healthy, 0 data loss |
| **Verification** | verified-local (executed end-to-end on a live homelab; CI validation pending) |

## When to Use

- A Docker Compose service uses an unpinned `image: mariadb` (which resolves to `mariadb:latest`) and a redeploy may have silently pulled a newer major and triggered an on-disk upgrade of a live database.
- You need to recreate a MariaDB container on a newer pinned tag and finalize the system tables with `mariadb-upgrade`.
- The last-upgraded version marker looks stale because you checked the legacy `mysql_upgrade_info` file instead of the newer `mariadb_upgrade_info`.
- A recreated container shows an empty `MYSQL_ROOT_PASSWORD` env while the real stored root password (from first init) still persists on an existing data volume, breaking root admin ops.
- You want to move off a short-term MariaDB release (e.g. 11.7, near EOL) onto an LTS tag (e.g. 11.8) for set-and-forget stability.

## Verified Workflow

> Verified locally only on a live homelab — CI validation pending.

Pin the image, recreate the container on the new pinned tag (the data volume persists and MariaDB starts on the existing data dir), THEN run `mariadb-upgrade` to finalize the system tables. Upgrade ONE consecutive major at a time (11.7 to 11.8 is fine). To make a redeploy reuse the byte-identical image already running with no network pull, locally `docker tag <running-image-id> mariadb:<version>` first.

### Quick Reference

```bash
# 0. Backup first (note: newer images renamed mysqldump -> mariadb-dump)
docker exec <db> sh -c 'mariadb-dump -uroot -p"$MYSQL_ROOT_PASSWORD" --single-transaction --routines --triggers --databases <db_name>' > backup.sql

# 1. (Optional) Reuse the exact running image as a pinned local tag (no network pull)
docker tag <running-image-id> mariadb:11.8.8

# 2. Pin the tag in compose (image: mariadb:11.8.8) and recreate the container.
#    The data volume is unchanged; MariaDB starts on the existing data dir.

# 3. Confirm the running server version (use the mariadb client, NOT mysql)
docker exec <db> sh -c 'mariadb -uroot -p"$MYSQL_ROOT_PASSWORD" -N -e "SELECT VERSION();"'

# 4. Finalize system tables (runs the 8 phases; all tables -> OK)
docker exec <db> sh -c 'mariadb-upgrade -uroot -p"$MYSQL_ROOT_PASSWORD"'

# 5. Verify the NEW marker file equals the new version; the stale legacy file should be gone
docker exec <db> sh -c 'cat /var/lib/mysql/mariadb_upgrade_info'   # -> 11.8.8-MariaDB
docker exec <db> sh -c 'ls /var/lib/mysql/mysql_upgrade_info'      # -> No such file (removed)

# 6. Verify binary names on the new image (old names are deprecated/removed)
docker exec <db> mariadbd --version                               # works
# docker exec <db> mysqld --version  -> "executable file not found"

# 7. Verify the app(s) using the DB still connect and data is intact.
```

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
|---------|----------------|---------------|----------------|
| 1 | Left `image: mariadb` unpinned in compose | Resolves to `mariadb:latest`; an earlier redeploy silently pulled a newer MAJOR and triggered an on-disk upgrade of the LIVE DB. We found DBs had drifted 10.9.3 to 11.7.2 via a `:latest` pull. | Always pin an explicit tag (e.g. `mariadb:11.8.8`). To reuse the byte-identical running image with no pull, `docker tag <running-image-id> mariadb:<version>` locally first. |
| 2 | Checked `/var/lib/mysql/mysql_upgrade_info` to read the last-upgraded version | Newer MariaDB 11.x records the version in `mariadb_upgrade_info`, NOT the legacy `mysql_upgrade_info`. The old file read `10.9.3-MariaDB` while the server was already 11.7.2 — i.e. `mariadb-upgrade` had never run after the `:latest` jump. | Check `mariadb_upgrade_info`. Running `mariadb-upgrade` removes the stale `mysql_upgrade_info` and writes the new `mariadb_upgrade_info`. |
| 3 | Ran `docker exec <c> mysqld --version` and used the `mysql` / `mysqldump` clients | Newer images dropped the legacy binaries; `mysqld --version` fails with "executable file not found". | Use the new names: `mariadbd`, `mariadb`, `mariadb-dump`, `mariadb-upgrade`. |
| 4 | Ran `mariadb-upgrade -uroot -p"$MYSQL_ROOT_PASSWORD"` after recreate, relying on the compose env | Compose's root-password source had changed to an unset variable, so the recreated container had an EMPTY `MYSQL_ROOT_PASSWORD` env. MariaDB only applies `MYSQL_ROOT_PASSWORD` on FIRST init (empty data dir); on an existing volume it is IGNORED and the original stored password persists. Admin ops failed with the empty env. | Point the compose root-password env at a value/file equal to the already-stored password. Setting the env to the correct value is harmless on an existing volume — it just makes the env match reality; it does NOT change the stored password. |

## Results & Parameters

Upgraded two live Dockerized MariaDB instances 11.7.2 to 11.8.8 LTS with zero data loss:

| Database | Data Dir Size | Result | App Health After |
|----------|---------------|--------|------------------|
| gitea DB | ~235 MB | All tables OK | Healthy, data intact |
| nextcloud DB | ~430 MB | All tables OK | Healthy, data intact |

Key parameters and facts:

- **Pin tag**: `image: mariadb:11.8.8` (never leave `image: mariadb`, which is `:latest`).
- **Release choice**: 11.7 is a short-term release (near EOL); 11.8 is LTS. Prefer LTS tags for set-and-forget.
- **Upgrade granularity**: one consecutive major at a time (11.7 to 11.8 is fine).
- **Marker file**: `/var/lib/mysql/mariadb_upgrade_info` (NOT the legacy `mysql_upgrade_info`). After `mariadb-upgrade`, it equals the new version (e.g. `11.8.8-MariaDB`) and the legacy file is gone.
- **Binary names**: `mariadbd`, `mariadb`, `mariadb-dump`, `mariadb-upgrade`. The `mysqld` / `mysql` / `mysqldump` names are deprecated/removed.
- **Root password caveat**: `MYSQL_ROOT_PASSWORD` is applied only on first init (empty data dir); on an existing volume it is ignored and the stored password persists. Make the compose env equal the stored password so admin ops work.

Copy-paste-ready verified procedure:

```bash
# Backup
docker exec <db> sh -c 'mariadb-dump -uroot -p"$MYSQL_ROOT_PASSWORD" --single-transaction --routines --triggers --databases <db_name>' > backup.sql

# Pin + recreate the container on mariadb:<new> (via your orchestrator); data volume unchanged.

# Confirm version
docker exec <db> sh -c 'mariadb -uroot -p"$MYSQL_ROOT_PASSWORD" -N -e "SELECT VERSION();"'

# Finalize system tables (8 phases; all tables -> OK)
docker exec <db> sh -c 'mariadb-upgrade -uroot -p"$MYSQL_ROOT_PASSWORD"'

# Verify marker (== new version); stale mysql_upgrade_info should be gone
docker exec <db> sh -c 'cat /var/lib/mysql/mariadb_upgrade_info'

# Verify each app that uses the DB still connects and data is intact.
```
