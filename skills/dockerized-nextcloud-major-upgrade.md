---
name: dockerized-nextcloud-major-upgrade
description: "Upgrade a Dockerized Nextcloud across consecutive major versions (e.g. 25 to 34) using official nextcloud:<NN>-apache images with zero data loss, one major at a time. Use when: (1) running Nextcloud in Docker and need to climb several majors, (2) the entrypoint occ upgrade never completes and occ status keeps needsDbUpgrade=true, (3) occ refuses commands with 'Nextcloud is in maintenance mode', (4) you want a gated upgrade script that backs up, recreates, and validates each major."
category: tooling
date: 2026-06-25
version: "1.0.0"
user-invocable: false
verification: verified-local
tags: []
---

# Dockerized Nextcloud Major-Version Upgrade

## Overview

| Field | Value |
| ------- | ------- |
| **Date** | 2026-06-25 |
| **Objective** | Upgrade a Dockerized Nextcloud across many consecutive majors (25 to 34) using official `nextcloud:<NN>-apache` images, with zero data loss |
| **Outcome** | Successful — NC 25.0.13 to 34.0.0 across 7 majors, 8 users preserved throughout, 0 container restarts, ~5 min per major |
| **Verification** | verified-local (executed end-to-end on a live production homelab; not a CI-gated test) |

## When to Use

- Running Nextcloud in Docker via the official `nextcloud:<NN>-apache` images and you need to climb one or more major versions.
- The container is on new code but `occ status` shows `needsDbUpgrade: true` and the DB migration never runs.
- `occ` refuses every command with `Nextcloud is in maintenance mode, hence the database isn't accessible. Cannot perform any command except 'maintenance:mode --off'`.
- You want a repeatable, gated upgrade script that pre-flights health, backs up, recreates the container, polls until settled, and validates before committing — climbing many majors safely.

## The #1 Gotcha (read this first)

**Do NOT enable Nextcloud maintenance mode BEFORE recreating the container on the new image.** Maintenance mode blocks BOTH:

1. the official image entrypoint's automatic `occ upgrade`, AND
2. `occ` itself (it prints the "maintenance mode ... can't perform any command" error above).

The result: the container runs the new code but `needsDbUpgrade` stays `true` forever and the DB migration never runs.

**Fix:** ensure maintenance is OFF at container start. When OFF, the entrypoint auto-completes the upgrade cleanly. Observed directly this session: with maintenance OFF, NC went 26 to 27 fully automatically; with maintenance pre-enabled, NC 25 to 26 got stuck at `needsDbUpgrade=true` and required a manual `occ upgrade`. If you are ever stuck: `occ maintenance:mode --off` then `occ upgrade`.

Note: this is the opposite of the data-dir relocation workflow, where you DO want maintenance ON to freeze writes. For version upgrades, keep it OFF.

## Verified Workflow

> Verified locally only on a live production homelab — CI validation pending.

Nextcloud **cannot skip majors** and **cannot downgrade**: do exactly one major per cycle (25 to 26 to 27 ... to 34). `occ` must run as the container's actual web/PUID user — find it from the owner of `/var/www/html/config/config.php` (a custom PUID install rejects `-u www-data` with `unable to find user www-data`). All examples below use `-u 1002`; substitute your install's uid.

### Quick Reference

```bash
CT=nextcloud_nextcloud_1          # container name
U=1002                            # web/PUID uid (owner of config/config.php)
occ() { docker exec -u "$U" "$CT" php occ "$@"; }

# --- per-major cycle: repeat once per major (NN -> NN+1) ---

# 1. Pre-flight health (must be clean BEFORE upgrading)
occ check                         # clean
occ integrity:check-core          # empty / OK
occ status                        # needsDbUpgrade: false

# 2. Backup (consistent InnoDB dump; does NOT need maintenance mode)
docker exec "$CT" mariadb-dump --single-transaction --routines --triggers \
  --databases nextcloud > /backups/nextcloud-$(date +%F-%H%M).sql

# 3. Pre-pull the next image (~1.2GB)
docker pull nextcloud:27-apache  # = nextcloud:<NN+1>-apache

# 4. Bump the image tag via your orchestrator and recreate the container.
#    Data volumes persist: webroot, config, custom_apps, themes, and the data dir.
#    Ensure maintenance mode is OFF before/at recreation (see "#1 Gotcha").

# 5. With maintenance OFF, the entrypoint runs occ upgrade on start.
#    Poll until settled (~60-120s for ~60 apps):
until occ status 2>/dev/null \| grep -q '"needsDbUpgrade": false'; do sleep 5; done
occ status                        # versionstring shows NN+1, needsDbUpgrade: false
# If it never settles, run it explicitly:
occ upgrade

# 6. Add new OPTIONAL performance indices each major adds
occ db:add-missing-indices --dry-run   # shows what it will add
occ db:add-missing-indices             # adds them online

# 7. Update apps to NN+1-compatible versions, re-enable any disabled by the upgrade
occ app:update --all
occ app:enable <app>              # for each app the upgrade disabled

# 8. Validate the cycle
occ status                        # version=NN+1, maintenance=false, needsDbUpgrade=false
occ check                         # clean
occ integrity:check-core          # OK
occ user:list \| wc -l            # user count UNCHANGED
curl -s -o /dev/null -w '%{http_code}' https://<your-ingress>/   # 200
```

### Detailed Steps

1. **Pre-flight health gate.** Do not upgrade an unhealthy instance. `occ check` must be clean, `occ integrity:check-core` empty/OK, and `occ status` must show `needsDbUpgrade: false`. If a previous upgrade left it dirty, finish that first.
2. **Backup.** `mariadb-dump --single-transaction --routines --triggers --databases nextcloud`. The `--single-transaction` flag gives a consistent InnoDB snapshot with NO downtime and NO maintenance mode. Gate the script: abort if the dump is smaller than ~1MB (a near-empty dump means the backup failed).
3. **Pre-pull** `nextcloud:<NN+1>-apache` so recreation is fast (the image is ~1.2GB).
4. **Bump the tag and recreate** the container through your orchestrator's config. The data volumes (webroot, config, custom_apps, themes, and the data dir, e.g. on NFS) persist across recreation. Critically: keep maintenance mode OFF (see "#1 Gotcha").
5. **Let the entrypoint upgrade, then poll.** With maintenance OFF, the entrypoint runs `occ upgrade` on start. Poll `occ status` until `versionstring` shows NN+1 and `needsDbUpgrade: false`. If it doesn't settle, run `occ upgrade` explicitly.
6. **Add missing indices.** Each major adds new OPTIONAL performance indices. Run `occ db:add-missing-indices --dry-run` to preview, then run it without the flag to add them online. (Observed additions this session: `schedulingobjects`, `oc_mail_*`, `oc_text_steps`.)
7. **Update and re-enable apps.** `occ app:update --all` fetches NN+1-compatible app versions. The upgrade disables some apps; re-enable each with `occ app:enable <app>`. Community/3rd-party apps with no NN+1 release stay disabled — that's expected (see Failed Attempts).
8. **Validate gate.** Confirm `occ status` (version=NN+1, maintenance=false, needsDbUpgrade=false), `occ check` clean, `occ integrity:check-core` OK, user count UNCHANGED, and ingress returns HTTP 200. Only then proceed to the next major.

### Gated Upgrade Script Pattern

A gated script climbs many majors safely. Each iteration: pre-flight health gate to backup (abort if dump < ~1MB) to pull to bump to deploy/recreate to poll-until-settled (fallback to `occ upgrade`) to indices to `app:update` + re-enable to validate gate, and **only commits/advances on PASS**. This session climbed 25 to 34 (7 majors) this way: 8 users intact throughout, 0 container restarts.

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
| --------- | ---------------- | --------------- | ---------------- |
| Enable maintenance mode before recreating (25 to 26) | Ran `occ maintenance:mode --on` then bumped the image and recreated | Maintenance mode blocked BOTH the entrypoint's auto `occ upgrade` AND `occ` itself; `needsDbUpgrade` stayed `true` forever and occ printed "Nextcloud is in maintenance mode ... Cannot perform any command except 'maintenance:mode --off'" | Keep maintenance OFF for version upgrades. Recovery: `occ maintenance:mode --off` then `occ upgrade`. With maintenance OFF at start, 26 to 27 completed fully automatically |
| `docker exec -u www-data` to run occ | Assumed the standard `www-data` user on a custom PUID install | Failed with `unable to find user www-data` — the install uses PUID 1002, not www-data | Run occ as the container's actual web/PUID uid. Find it from the owner of `/var/www/html/config/config.php`, e.g. `-u 1002` |
| `occ app:enable files_rightclick` (and duplicatefinder, files_mindmap) | Tried to re-enable community apps after the major bump | `App ... cannot be installed because it is not compatible with this version of the server.` — `files_rightclick` was dropped @28 (deprecated; right-click is native now), `duplicatefinder` and `files_mindmap` dropped @32 | Some 3rd-party apps have no release for the new major and stay disabled. This is expected and non-fatal — just record which apps are lost |
| Treating Apache/Fontconfig log lines as upgrade failures | Saw `AH01797 ... client denied by server configuration: /var/www/html/data/.ncdata` and `Fontconfig error: No writable cache directories` and suspected a broken upgrade | The AH01797 line is Apache CORRECTLY blocking web access to the data dir (a security check, often the setupcheck probing `.ncdata`); the Fontconfig line is cosmetic | These are benign log noise, not errors. Validate via `occ status` / `occ check`, not raw log greps |
| Skipping a major (jump 25 to 27) | Considered bumping straight to a far image to save time | Nextcloud cannot skip majors and cannot downgrade; the upgrade refuses | Always go one major at a time, never skip, never downgrade |

## Results & Parameters

### Configuration

```bash
# Per-major variables
CT=nextcloud_nextcloud_1          # container name
U=1002                            # web/PUID uid = owner of /var/www/html/config/config.php
IMAGE=nextcloud:<NN+1>-apache     # official image, one major above current

# Backup gate threshold
MIN_DUMP_BYTES=1000000            # abort upgrade if mariadb-dump < ~1MB

# Set a low-usage maintenance window (NC28+ setupcheck recommendation).
# maintenance_window_start is an hour 0-23 in UTC; 1 = 01:00 UTC.
docker exec -u "$U" "$CT" php occ config:system:set \
  maintenance_window_start --value=1 --type=integer

# Surface other admin recommendations (NC28+): X-Frame-Options header, etc.
docker exec -u "$U" "$CT" php occ setupchecks
```

### Expected Output

- `occ status` after each cycle: `version: NN+1.0.0`, `maintenance: false`, `needsDbUpgrade: false`.
- `occ check`: no output (clean); `occ integrity:check-core`: empty / `No errors found`.
- `occ db:add-missing-indices --dry-run`: lists optional indices (e.g. on `schedulingobjects`, `oc_mail_*`, `oc_text_steps`); the real run adds them online with no downtime.
- `occ user:list \| wc -l`: identical count before and after every major (8 users held across all 7 upgrades).
- Ingress: HTTP `200`.
- Full climb: NC `25.0.13` to `34.0.0`, 7 majors, ~5 min each, 8 users preserved, 0 container restarts.
- Benign (ignore): `AH01797 ... client denied by server configuration: /var/www/html/data/.ncdata`; `Fontconfig error: No writable cache directories`.
- Expected app losses (no new-major release): `files_rightclick` (@28), `duplicatefinder` and `files_mindmap` (@32).

## Verified On

| Project | Context | Details |
| --------- | --------- | --------- |
| Homelab | Live production Dockerized Nextcloud, 25.0.13 to 34.0.0, 8 users | Executed end-to-end this session; verified-local |

## References

- [Nextcloud official Docker image (Docker Hub)](https://hub.docker.com/_/nextcloud)
- [Nextcloud upgrade docs](https://docs.nextcloud.com/server/latest/admin_manual/maintenance/upgrade.html)
- [occ command reference](https://docs.nextcloud.com/server/latest/admin_manual/occ_command.html)
- [homelab-nextcloud-data-dir-nfs-migration.md](homelab-nextcloud-data-dir-nfs-migration.md)
