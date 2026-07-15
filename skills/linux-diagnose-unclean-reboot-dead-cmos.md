---
name: linux-diagnose-unclean-reboot-dead-cmos
description: "Diagnose why a Linux server rebooted unexpectedly and came back up degraded, working backward from limited log evidence to distinguish a genuine power-loss/dead-CMOS-battery event from a software crash. Use when: (1) a server rebooted unexpectedly overnight and came back up degraded, (2) journalctl -b -1 fails with insufficient permissions or only one boot is listed, (3) diagnosing an unclean shutdown with no persistent journal available."
category: debugging
date: 2026-07-13
version: "1.0.0"
user-invocable: false
verification: verified-local
tags: []
---
# Linux Diagnose Unclean Reboot Dead CMOS

## Overview

| Attribute | Value |
| ----------- | ------- |
| **Date** | 2026-07-13 |
| **Objective** | Diagnose why a Debian Linux server rebooted unexpectedly overnight and came back up `degraded`, with only limited log evidence (journald not configured for persistent storage) |
| **Outcome** | Identified a stale-RTC-date signature at the start of the crash boot's kernel log, corroborated by a recurrence of the same stale date in an unrelated systemd unit's failure record, pointing to a genuine power-loss event (most likely a dying/dead CMOS coin-cell battery) rather than a software crash |
| **Scope** | Debian/systemd servers with rsyslog present; applies generally to any Linux host where journald is volatile (non-persistent) and evidence must be reconstructed from `last`, rotated rsyslog files, and RTC timestamp artifacts |

## When to Use

Use this skill when:

1. A server rebooted unexpectedly (no scheduled maintenance) and came back up in a `degraded` systemd state
2. `journalctl -b -1` fails with "No journal files were opened due to insufficient permissions" or `journalctl --list-boots` shows only the current boot
3. You need to distinguish "the OS crashed" from "the machine actually lost power" with little or no panic/OOM/hardware-error evidence in the logs
4. You suspect a dying CMOS/RTC battery but need a repeatable, evidence-based way to confirm it rather than guessing
5. You want to harden a host so a future incident doesn't require this rsyslog-archaeology process

**Do NOT use for:**
- Diagnosing a reboot where persistent journald (`/var/log/journal` present) already contains the previous boot's logs and `journalctl -b -1` works cleanly — just read that boot's logs directly
- Confirming the CMOS battery is physically dead — this skill produces a well-evidenced inference, not physical confirmation; the coin cell still needs to be tested/replaced to fully confirm

## Verified Workflow

### Step 1: Establish the reboot/crash history

Start with `last -x`, which shows reboot, shutdown, and runlevel-change entries in order. A prior
session ending in the literal word `crash` with **no** corresponding `shutdown system down` entry
immediately before the next `reboot system boot` line is the first signal of an unclean/unexpected
restart — a clean reboot or shutdown always logs a `shutdown` entry first.

### Step 2: Check whether journald has the previous boot at all

Before doing anything else, confirm whether journald actually retained the crash boot's logs:

```bash
journalctl --list-boots
journalctl -b -1
```

If this errors with "No journal files were opened due to insufficient permissions" (even when run
as a user in the `systemd-journal` group), or only one boot is listed, check whether journald is
running in volatile mode:

```bash
ls -ld /var/log/journal
```

If `/var/log/journal` does not exist, journald has never persisted logs across boots and the
previous boot's journal is simply gone — full stop, there is no way to recover it after the fact.
Fall back to rsyslog's rotated flat files instead.

### Step 3: Fall back to rsyslog's rotated files — but verify which file actually has the crash boot

```bash
sudo ls -la /var/log/syslog* /var/log/kern.log*
```

These files are root:adm — you need `sudo` or `adm` group membership to read them.

**Gotcha:** do not assume the CURRENT (unrotated) `/var/log/syslog` / `/var/log/kern.log` contains
the crash boot's kernel messages just because it is "today's" file. logrotate typically runs once
daily (sometimes triggered as part of very early boot-time cron/systemd-timer activity), so
depending on exactly when in the boot sequence rotation fires relative to when the crash boot's log
lines were written, the crash boot's messages can end up in the `.1` rotated file instead of (or
split across) the current file. Always check the actual timestamp range in **both** `kern.log` /
`kern.log.1` and `syslog` / `syslog.1` around the boot time in question before treating either
file's contents as authoritative:

```bash
sudo head -5 /var/log/kern.log.1
sudo tail -5 /var/log/kern.log.1
sudo head -5 /var/log/kern.log
sudo tail -5 /var/log/kern.log
```

### Step 4: Look for the stale-RTC-date signature at the very start of the crash boot

Once you've located the correct file/section, look at the earliest kernel lines of the crash boot
(`kernel: [    0.xxxxxx]` lines near the beginning of that boot's log block). The key diagnostic
signature for a genuine power-loss / dead-CMOS-battery event is: the wall-clock timestamps on those
earliest lines show an obviously wrong/stale date (e.g., epoch-adjacent like "Dec 31 1969", or a
fixed old date like "Feb 14 2019") that then gets corrected mid-boot — visible as `ntpd` /
`systemd-timesyncd` messages like "Unexpected origin timestamp ... does not match" right around the
correction point, or a sudden jump in subsequent log timestamps to the true current date.

That signature is strong, specific evidence that the hardware real-time clock (RTC) lost its
battery-backed date. The RTC only resets like this on a **genuine loss of standby power** — the
machine was physically unplugged, a breaker tripped, a PSU hiccupped, or (most commonly on an
always-on machine that's otherwise never fully powered off) the CMOS coin-cell battery that keeps
the RTC alive during any brief power loss is dead or dying.

Critically: a software crash or kernel panic does **not** reset the RTC — the RTC is independent
hardware that only loses state when it loses all power, including its battery backup. This
signature is what lets you distinguish "the OS crashed" from "the machine actually lost power" even
with zero panic/OOM/hardware-error evidence in the logs.

### Step 5: Corroborate a chronic (not one-off) dead battery

Check whether the exact same stale date/time recurs across multiple, otherwise-unrelated incidents
— for example a leftover stale `Active: failed ... since <that exact stale date>` timestamp on some
systemd unit's last-failure record from a completely separate, much older incident:

```bash
systemctl list-units --state=failed
systemctl status <unit> --no-pager | grep -i "since"
```

A recurrence of the identical stale date across unrelated incidents is evidence the RTC has been
intermittently losing power for a long time — consistent with a battery that has been dying/dead for
a while, causing this on every sufficiently long power interruption — not a one-off fluke.

### Step 6: Systematically rule out other causes before concluding it's power/RTC

A wrong diagnosis here is costly (the fix is a physical part replacement), so rule out alternatives
first:

```bash
# Would a real kernel panic have hung the machine instead of rebooting it?
sysctl kernel.panic kernel.panic_on_oops

# If both are 0, a real panic hangs rather than reboots — UNLESS a hardware
# watchdog forced the reboot. Check for a watchdog device and whether it fired:
ls /dev/watchdog*

# Grep available logs for kernel/hardware-level failure signatures:
sudo grep -aEi 'mce|hardware error|thermal|watchdog|panic|oops|BUG|segfault|oom-killer|oom_kill|ACPI Error' /var/log/kern.log /var/log/kern.log.1 /var/log/syslog /var/log/syslog.1

# Drive health
sudo smartctl -H -A /dev/sda

# Thermal readings
cat /sys/class/thermal/thermal_zone*/temp

# ECC memory errors (if the system has ECC RAM)
cat /sys/devices/system/edac/mc/mc*/ce_count /sys/devices/system/edac/mc/mc*/ue_count 2>/dev/null
```

A clean bill of health across all of these, combined with the stale-RTC signature from Step 4-5, is
what makes "power loss / dead CMOS battery" the best-supported conclusion. This is an inference from
strong circumstantial/absence-of-alternative evidence, not a certainty — say so plainly in any
write-up, and note that the physical battery still needs to be tested/replaced to fully confirm.

### Step 7: Harden the host so this isn't necessary next time

```bash
# Enable persistent journald storage BEFORE the next incident
sudo mkdir -p /var/log/journal
# (or set Storage=persistent in /etc/systemd/journald.conf)
sudo systemctl restart systemd-journald

# After the next reboot, journalctl -b -1 will actually work.

# Let the investigating user read rsyslog's flat files without sudo:
sudo usermod -aG adm <user>
```

### Quick Reference

```bash
# 1. Reboot/crash history
last -x

# 2. Does journald have the previous boot?
journalctl --list-boots
journalctl -b -1
ls -ld /var/log/journal

# 3. Fall back to rsyslog rotated files (check BOTH current and .1, compare timestamp ranges)
sudo ls -la /var/log/syslog* /var/log/kern.log*
sudo head -5 /var/log/kern.log.1; sudo tail -5 /var/log/kern.log.1
sudo head -5 /var/log/kern.log; sudo tail -5 /var/log/kern.log

# 4. Look for stale-RTC-date signature at start of crash boot's kernel log
sudo grep -a 'kernel: \[    0\.' /var/log/kern.log.1

# 5. Corroborate chronic recurrence via stale failed-unit timestamps
systemctl list-units --state=failed
systemctl status <unit> --no-pager | grep -i "since"

# 6. Rule out alternative causes
sysctl kernel.panic kernel.panic_on_oops
ls /dev/watchdog*
sudo grep -aEi 'mce|hardware error|thermal|watchdog|panic|oops|BUG|segfault|oom-killer|oom_kill|ACPI Error' /var/log/kern.log* /var/log/syslog*
sudo smartctl -H -A /dev/sda
cat /sys/class/thermal/thermal_zone*/temp
cat /sys/devices/system/edac/mc/mc*/ce_count /sys/devices/system/edac/mc/mc*/ue_count 2>/dev/null

# 7. Harden for next time
sudo mkdir -p /var/log/journal && sudo systemctl restart systemd-journald
sudo usermod -aG adm <user>
```

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
| --------- | ---------------- | --------------- | ---------------- |
| Ruling out kernel panic from sysctl alone | Saw `kernel.panic=0` and `kernel.panic_on_oops=0` and concluded "definitely not a panic" without checking further | A hardware watchdog can force a reboot even when panic-on-oops is disabled and no hang would otherwise occur; that alternative explanation was not yet ruled out | Explicitly check `/dev/watchdog*` for a watchdog device and whether it fired before ruling out panic-driven reboot; do not assume, verify |
| Reading the wrong rotated log file first | Grabbed `kern.log.1` and treated it as "the crash boot's log" before checking its timestamp range | The file's timestamp range didn't actually cover the crash boot; wasted a step chasing the wrong data | Always check the timestamp range (`head`/`tail`) of a rotated log file against the actual crash boot time before treating its contents as authoritative |

## Results & Parameters

### Diagnostic signature reference

```text
Genuine power loss / dead CMOS battery signature:
  - Crash boot's earliest kernel.log lines show a stale/wrong date
    (e.g. "Dec 31 1969" or a fixed old date like "Feb 14 2019")
  - ntpd / systemd-timesyncd logs "Unexpected origin timestamp ... does
    not match" right around the correction point, OR timestamps jump
    abruptly to the true current date mid-boot
  - RTC is independent battery-backed hardware; it only resets on TOTAL
    loss of power (unplug, breaker trip, PSU hiccup, or dead CMOS cell)
  - A software crash/panic does NOT reset the RTC -> this signature is
    diagnostic for power loss specifically, not just "something crashed"

Corroboration of CHRONIC (not one-off) dead battery:
  - Same exact stale date recurs in an unrelated systemd unit's
    "Active: failed ... since <date>" record from a much older incident
```

### Rule-out checklist (all must be clean to support the power-loss conclusion)

```markdown
- [ ] kernel.panic / kernel.panic_on_oops reviewed, watchdog device checked
- [ ] No mce/hardware error/thermal/watchdog/panic/oops/BUG/segfault/
      oom-killer/ACPI Error hits in available logs
- [ ] smartctl -H -A shows healthy drive
- [ ] Thermal zone readings normal
- [ ] EDAC ce_count/ue_count normal (if ECC RAM present)
```

### Verification level note

This conclusion (chronic RTC/CMOS battery issue) is an inference from strong circumstantial
evidence — corroborated by a second independent occurrence of the same stale date — but the
physical CMOS battery had not yet been replaced/tested at time of writing. Treat the root cause as
highly likely but not 100% physically confirmed until the battery is tested or swapped.

## Verified On

| Project | Context | Details |
| --------- | --------- | --------- |
| apollo homelab | 2026-07-13 crash recovery investigation — unexpected overnight reboot, journald non-persistent, resolved via rsyslog archaeology and RTC stale-date signature | verified-local |
