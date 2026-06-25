---
name: unison-systemd-home-env-required
description: "Fixes unison crashing with 'Environment variable HOME not found' when run from systemd. Use when: (1) unison fails immediately in a systemd service, (2) journalctl shows Fatal error about HOME, (3) all datasets fail before any files sync."
category: debugging
date: 2026-06-23
version: "1.0.0"
user-invocable: false
verification: verified-local
tags: []
---

# unison: systemd HOME Environment Variable Required

## Overview

| Field | Value |
|-------|-------|
| **Date** | 2026-06-23 |
| **Objective** | Fix unison crashing immediately when run from a systemd service |
| **Outcome** | Successful — two fixes identified; Option B (User= directive) preferred |
| **Verification** | verified-local |

## When to Use

- unison service fails immediately with `Fatal error: exception Util.Fatal("Environment variable HOME not found")`
- All sync datasets fail instantly before any files are read or written
- unison runs from a systemd service unit (not interactively from a shell)
- journalctl shows the HOME error repeated for every dataset attempted

## Verified Workflow

Verified locally only — CI validation pending.

### Quick Reference

```bash
# Option A: Quick fix when running as root — add to sync script
export HOME=/root

# Option B (preferred): Add User= to systemd service unit
# Edit /etc/systemd/system/your-sync.service
# [Service]
# User=mvillmow

# After either fix:
systemctl daemon-reload && systemctl restart your-sync.service
```

### Detailed Steps

1. Confirm the error by checking journalctl for the service:
   `journalctl -u your-sync.service --no-pager | grep "HOME\|Fatal"`

2. Choose a fix:

   **Option A** (quick fix, running as root):
   Add `export HOME=/root` to the top of your sync script, before calling unison.

   **Option B** (preferred — run as a specific user):
   Add `User=mvillmow` (or the appropriate user) to the `[Service]` section of the systemd unit file.
   When `User=` is set, systemd automatically sets `HOME` to that user's home directory.
   This also fixes NFS root_squash write failures simultaneously.

3. Reload and restart the service:

   ```bash
   systemctl daemon-reload && systemctl restart your-sync.service
   ```

4. Verify the fix — unison should now proceed past the archive lookup:

   ```bash
   journalctl -u your-sync.service -f
   ```

   You should see unison reading its archive files from `$HOME/.unison/` instead of crashing.

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
|---------|----------------|---------------|----------------|
| Run unison from systemd without HOME set | Launched unison service unit with no User= or Environment= directive | systemd does not set HOME by default; unison cannot find its archive directory | Always set HOME explicitly via User= or Environment= when running unison from systemd |
| Assuming the error is a permissions problem | Investigated file permissions on source and destination paths | unison crashes before opening any paths — the HOME check happens at startup | The fatal crash precedes any file I/O; it is purely an environment variable issue |

## Results & Parameters

- **unison archive location**: `$HOME/.unison/` (created automatically by unison on first run)
- **systemd default**: Does NOT set `HOME` unless `User=` is specified or `Environment=HOME=...` is added
- **Option A config** — add to script: `export HOME=/root` (only when running as root)
- **Option B config** — add to `[Service]` section:

  ```ini
  [Service]
  User=mvillmow
  ```

- **Reload command**: `systemctl daemon-reload && systemctl restart <service>`
- **Data safety**: No data loss from this error — unison exits before modifying any files
- **Bonus fix**: `User=` also resolves NFS `root_squash` write permission denials in the same service

## Verified On

| Project | Context | Details |
|---------|---------|---------|
| apollo-homelab | NAS-USB nightly sync via systemd | unison two-way sync across multiple datasets |
