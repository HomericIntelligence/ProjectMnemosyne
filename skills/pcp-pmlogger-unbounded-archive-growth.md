---
name: pcp-pmlogger-unbounded-archive-growth
description: "Documents how PCP (Performance Co-Pilot) pmlogger silently accumulates unbounded archives on Debian/PureOS systems, consuming gigabytes of root disk with no warnings. Use when: (1) root disk is unexpectedly full on a Debian/PureOS/HomelabOS server, (2) /var/log/pcp is large and growing, (3) pmlogger or pmcd are running and you don't use PCP dashboards."
category: tooling
date: 2026-06-20
version: "1.0.0"
user-invocable: false
verification: verified-local
tags:
  - pcp
  - pmlogger
  - pmcd
  - performance-co-pilot
  - disk-bloat
  - log-rotation
  - debian
  - pureos
  - systemd
  - homelab
---

# PCP pmlogger Unbounded Archive Growth

## Overview

| Field | Value |
|-------|-------|
| **Date** | 2026-06-20 |
| **Objective** | Recover root disk space consumed by PCP pmlogger archives on apollo (PureOS/Debian HomelabOS server) |
| **Outcome** | Successful — 36 GB freed; pmlogger and pmcd disabled at boot |
| **Verification** | verified-local — executed on apollo, confirmed via `du -sh /var/log/pcp` |

## When to Use

- Root disk on a Debian, PureOS, or HomelabOS server is unexpectedly full
- `du -sh /var/log/pcp` shows multiple gigabytes
- `/var/log/pcp/pmlogger/<hostname>/` contains many daily `.0` archive files
- `pmlogger` and/or `pmcd` are running (`ps aux | grep pmlogger`) but PCP dashboards are not in use
- Server has been running for months/years without explicit PCP configuration

## Verified Workflow

Verified locally on apollo (PureOS/Debian). CI validation pending.

### Quick Reference

```bash
# Diagnose
du -sh /var/log/pcp
du -xhd1 /var/log/pcp
ls -lh /var/log/pcp/pmlogger/"$(hostname)"/

# Fix: disable services (not using PCP dashboards)
sudo systemctl disable --now pmlogger pmcd
sudo rm -rf /var/log/pcp/pmlogger/"$(hostname)"/*

# Fix: cap retention (want to keep PCP)
sudo pmlogger_daily -k 3 -x 3
```

### Detailed Steps

1. **Diagnose the problem** — confirm PCP is the culprit:

   ```bash
   du -sh /var/log/pcp          # total size
   du -xhd1 /var/log/pcp        # breakdown by subdir
   ls -lh /var/log/pcp/pmlogger/"$(hostname)"/   # daily archive files
   ps aux | grep -E 'pmlogger|pmcd'              # confirm services running
   systemctl status pmlogger pmcd                # confirm enabled at boot
   ```

   Expected output: daily archive files named `YYYYMMDD.0`, each ~1.9 GB.

2. **Choose a remediation path:**

   **Path A — Not using PCP dashboards (recommended for most homelab servers):**

   ```bash
   # Stop and disable both services immediately
   sudo systemctl disable --now pmlogger pmcd

   # Verify disabled (is-enabled is the correct check; is-active may still show active briefly)
   systemctl is-enabled pmlogger pmcd   # should show: disabled / disabled

   # Delete accumulated archives
   sudo rm -rf /var/log/pcp/pmlogger/"$(hostname)"/*

   # Verify space recovered
   du -sh /var/log/pcp   # should show ~4 KB to ~27 MB (empty dirs + config)
   ```

   Note: `systemctl disable --now` stops the service immediately AND prevents restart at boot.
   The process may briefly appear as "active" in `systemctl is-active` right after; use
   `systemctl is-enabled` to confirm it won't restart. The services are harmless for the
   current session — they just cannot refill once archives are deleted and they won't start on
   next boot.

   **Path B — Keep PCP but cap retention:**

   ```bash
   # Run pmlogger_daily with retention caps
   # -k 3: keep last 3 days; -x 3: compress archives older than 3 days
   sudo pmlogger_daily -k 3 -x 3

   # For permanent configuration, edit the control file:
   # $PCP_SYSCONF_DIR/pmlogger/control  (typically /etc/pcp/pmlogger/control)
   # or add to /etc/cron.daily/pcp
   ```

3. **Verify recovery:**

   ```bash
   du -sh /var/log/pcp
   # Expected after Path A: ~4 KB to ~27 MB
   # Expected after Path B: size of 3 days of archives (~6 GB)
   ```

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
|---------|----------------|---------------|----------------|
| Ignoring /var/log growth | /var/log/pcp was never audited during routine maintenance | PCP produces no warnings, alerts, or log rotation by default | Always audit large directories under /var/log on Debian/PureOS servers |
| Using `systemctl is-active` to confirm disable | Checked `is-active` immediately after `disable --now` | Service may still show "active" briefly after `disable --now` | Use `systemctl is-enabled` instead — it immediately reflects the boot state |

## Results & Parameters

**Environment:** apollo, PureOS/Debian, HomelabOS, busy server (containers, many processes, network traffic)

**Growth rate observed:** ~1.9 GB/day per archive file

**Total accumulated:** 36 GB over multiple years

**After remediation (Path A):**

```
$ du -sh /var/log/pcp
27M     /var/log/pcp
```

**Key configuration files (if keeping PCP):**

- `/etc/pcp/pmlogger/control` — controls what is logged and retention
- `/etc/cron.daily/pcp` — daily maintenance cron (calls `pmlogger_daily`)
- `$PCP_SYSCONF_DIR/pmlogger/control` — same as above via PCP env var

**Archive naming convention:**

```
/var/log/pcp/pmlogger/<hostname>/YYYYMMDD.0   # daily archive, ~1.9 GB each
```

**Root cause:** PCP is included in the default package set for some Debian/PureOS installations.
Both `pmcd` (collector daemon) and `pmlogger` (archive writer) start at boot and run indefinitely.
No retention policy is configured by default. The only symptom is disk exhaustion at 90%+.

## Verified On

| Project | Context | Details |
|---------|---------|---------|
| HomelabOS/apollo | PureOS/Debian server, 2026-06-20 | 36 GB freed; both services disabled |
