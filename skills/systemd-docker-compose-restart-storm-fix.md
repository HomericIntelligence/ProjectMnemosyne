---
name: systemd-docker-compose-restart-storm-fix
description: "Fix systemd units supervising docker-compose-managed stacks that get stuck in activating (auto-restart) restart-storm loops, caused by combining systemd Restart=always with an attached (foreground) `docker compose up` on services that already carry their own container-level restart: policy. Use when: (1) `systemctl status` shows `Active: activating (auto-restart)` indefinitely for a docker compose unit even though `docker ps` shows the container running fine, (2) unit logs show `Error response from daemon: Conflict. The container name ... is already in use by container ...`, (3) after switching a unit to detached `docker compose up -d` you instead see `Error response from daemon: endpoint with name ... already exists in network ...` with zero matching containers in `docker ps -a`, (4) designing a systemd unit to supervise a docker-compose project and deciding who should own restart responsibility."
category: tooling
date: 2026-07-13
version: "1.0.0"
user-invocable: false
verification: verified-local
tags: [systemd, docker-compose, docker, restart-storm, RemainAfterExit, libnetwork]
---

# systemd + docker compose Restart-Storm Fix

## Overview

| Field | Value |
|-------|-------|
| **Date** | 2026-07-13 |
| **Objective** | Fix systemd units supervising docker-compose-managed stacks (Traefik reverse proxy + 3 app stacks on a Debian homelab host) found stuck in `activating (auto-restart)` restart-storm loops |
| **Outcome** | Root cause identified (double supervision: systemd `Restart=always` racing container-level `restart:` policy over an attached `docker compose up`) and fixed on 4 real production units; a distinct stuck-libnetwork-endpoint gotcha was also hit and cleared while applying the fix |
| **Verification** | verified-local |

## When to Use

- `systemctl status <unit>` shows `Active: activating (auto-restart)` indefinitely for a
  unit that wraps `docker compose up`, even though `docker ps` shows the actual
  application container up and serving traffic the whole time.
- Unit logs (`journalctl -u <unit>`) show repeated
  `Error response from daemon: Conflict. The container name "/X" is already in use by
  container "<id>". You have to remove (or rename) that container to be able to reuse
  that name.`
- You are designing or reviewing a systemd unit that supervises a `docker compose`
  project and need to decide whether systemd or Docker should own restart
  responsibility for the containers.
- After applying the `Type=oneshot` + `up -d` fix below, a restart instead fails with
  `Error response from daemon: endpoint with name <container-name> already exists in
  network <project>_<network>`, even though `docker ps -a --filter name=<container-name>`
  shows zero matching containers — this is a distinct, separate gotcha covered below,
  not the original restart-storm.

## Verified Workflow

### Quick Reference

**Before (restart-storm anti-pattern) — do not use this shape when containers already
have their own `restart:` policy:**

```ini
[Service]
Restart=always
RestartSec=3
ExecStart=/usr/bin/docker compose -p <name> up
ExecStop=/usr/bin/docker compose -p <name> down
```

**After (fixed) — systemd owns boot/shutdown lifecycle only, Docker owns crash
recovery:**

```ini
[Service]
Type=oneshot
RemainAfterExit=yes
WorkingDirectory=<path>
ExecStart=/usr/bin/docker compose -p <name> up -d
ExecStop=/usr/bin/docker compose -p <name> down
```

**Post-fix verification:**

```bash
systemctl daemon-reload
systemctl restart <unit>.service
systemctl --failed
# Expect: empty (no failed units)
systemctl status <unit>.service
# Expect: Active: active (exited)  <- correct steady state for oneshot + RemainAfterExit=yes
docker ps --filter "name=<project>"
# Expect: all expected containers Up
```

**If a restart instead hits the libnetwork endpoint gotcha (zero matching containers in
`docker ps -a`, but `endpoint with name ... already exists in network ...`):**

```bash
# Check Live Restore BEFORE restarting the daemon — see Failed Attempts / caveat below.
docker info | grep -i 'Live Restore'

# Full daemon restart is what actually clears the stale libnetwork endpoint reservation:
systemctl restart docker.service

# Confirm the stale endpoint is gone, then retry:
docker network inspect <network> --format '{{json .Containers}}'
docker compose -p <name> up -d
```

### Detailed Steps

1. **Recognize the trigger condition.** A systemd unit wraps `docker compose up`
   (no `-d`, i.e. attached/foreground) with `Restart=always` / `RestartSec=3`, and
   `systemctl status` shows `Active: activating (auto-restart)` persisting indefinitely,
   even though the application is reachable and `docker ps` shows its container running.

2. **Confirm the double-supervision root cause.** Check whether the same containers
   also carry their own restart policy in the compose file:

   ```bash
   grep -B3 'restart:' docker-compose.yml
   ```

   If every container has `restart: always` or `restart: unless-stopped` set AND the
   systemd unit also has `Restart=always` around an attached `docker compose up`, both
   Docker and systemd believe they own restart responsibility for the same container —
   this is the anti-pattern.

3. **Understand the failure sequence.** Attached (foreground) `docker compose up` exits
   with the exit code of whatever container stopped, the instant ANY service container
   in the project stops — even momentarily. A container-level `restart:` policy event
   causes Docker to internally cycle a container -> the attached `docker compose up`
   process observes that exit and terminates -> systemd's `Restart=always` reruns
   `ExecStart` -> the new `docker compose up` invocation tries to (re)create a container
   Docker's OWN restart policy has already spun back up under the same name ->
   `Error response from daemon: Conflict. The container name "/X" is already in use by
   container "<id>". You have to remove (or rename) that container to be able to reuse
   that name.` -> `ExecStart` fails -> `Restart=always` reruns it again -> infinite loop.
   This is the `activating (auto-restart)` state seen in step 1, and it persists even
   though the actual application container is up and serving traffic the whole time.

4. **Apply the fix per unit**: remove `Restart=`/`RestartSec=` entirely, switch
   `ExecStart` to run compose detached (`docker compose up -d`), and set
   `Type=oneshot` + `RemainAfterExit=yes` so systemd treats "the containers were
   successfully brought up" as the unit's completed, steady-state success condition
   instead of expecting a long-running foreground process. systemd's role becomes
   purely "bring the stack up at boot, tear it down at shutdown/stop"; Docker's own
   per-container `restart:` policies remain the sole owner of runtime crash recovery.
   See the Quick Reference before/after snippets above.

5. **Reload and restart each fixed unit**, then verify:

   ```bash
   systemctl daemon-reload
   systemctl restart <unit>.service
   systemctl --failed
   systemctl status <unit>.service
   docker ps --filter "name=<project>"
   ```

   Expect `systemctl --failed` empty and `Active: active (exited)` per unit (the
   correct state for a successfully-completed oneshot with `RemainAfterExit=yes`), with
   containers confirmed running via `docker ps` and, where applicable, a functional
   HTTP check through the reverse proxy.

6. **If a restart after the fix instead fails with a DIFFERENT error** —
   `Error response from daemon: endpoint with name <container-name> already exists in
   network <project>_<network>` — this is not the same "name already in use" conflict
   from step 3. Confirm `docker ps -a --filter name=<container-name>` shows ZERO
   containers by that name; if so, this is a stuck Docker libnetwork endpoint
   reservation (a known class of Docker/libnetwork bug where an endpoint's name
   registration in the network driver's internal state outlives the container that held
   it, especially after a container creation attempt was interrupted partway through).
   See Failed Attempts below for what does and does not clear it, and the Live Restore
   caveat before restarting `docker.service` on a host with other live containers.

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
|---------|----------------|---------------|-----------------|
| Leaving `Restart=always` on the systemd unit while containers already had their own `restart:` policy | Assumed systemd-level restart supervision was harmless extra insurance on top of Docker's own `restart:` policy | Attached `docker compose up` exits whenever ANY container in the project stops, even momentarily due to its OWN restart policy cycling; systemd then reruns `ExecStart`, which collides with the container Docker already restarted under the same name (`Conflict. The container name ... is already in use`), producing an infinite `activating (auto-restart)` loop | Two independent supervisors must not both own restart responsibility for the same container; pick one (Docker's `restart:` policy for crash recovery, systemd for boot/shutdown lifecycle only via `Type=oneshot` + `RemainAfterExit=yes`) |
| `docker compose -p <name> down --remove-orphans` to clear the stuck libnetwork endpoint | Removed a stray container, hoping it would also free the network endpoint reservation | A stray container was removed but the `endpoint with name ... already exists` conflict recurred on the very next `up -d` attempt | `down --remove-orphans` does not reliably release a stale libnetwork endpoint reservation; it only removes containers it can see |
| Manually finding and force-removing a specific container stuck in Docker's `Created` (never-fully-started) state via `docker ps -a` + `docker rm -f <id>` | Targeted the specific container ID holding the endpoint name, on the theory that removing it directly would free the reservation | Helped once, but a fresh stuck `Created`-state container reappeared after the next failed `up -d` attempt, still holding the same endpoint | Removing the visible container is not sufficient when the endpoint registration lives in libnetwork's internal driver state, independent of the container object itself |
| `systemctl restart docker.service` (full Docker daemon restart) | Restarted the entire Docker daemon to force it to rebuild its internal network state | This worked — `docker network inspect <network> --format '{{json .Containers}}'` showed the stale endpoint gone (empty) afterward, and the next `docker compose up -d` succeeded cleanly | A full daemon restart is what actually clears a stuck libnetwork endpoint reservation; but CHECK `docker info \| grep -i 'Live Restore'` first — if `Live Restore Enabled: false` (a common default), restarting `docker.service` briefly stops EVERY container on the host, not just the one with the stuck endpoint, because containers are not decoupled from the dockerd process lifecycle without Live Restore. Treat it as a real, if brief (~1-2 min), full-host outage of all containerized services on a host running other independent live stacks, and get confirmation before doing it if other services rely on uptime. |

## Results & Parameters

**Anti-pattern identified (do not combine):**

| Layer | Setting | Problem when combined with the other layer |
|-------|---------|----------------------------------------------|
| systemd unit | `Restart=always` / `RestartSec=3` wrapping an ATTACHED `docker compose up` (no `-d`) | Reruns `ExecStart` every time any container in the project exits, even momentarily |
| docker-compose.yml | `restart: always` / `restart: unless-stopped` on every service container | Docker independently restarts the same container that just triggered systemd's rerun, causing a container-name conflict |

**Fix applied to 4 real production systemd units** (Traefik reverse proxy + 3 app
stacks on a Debian host): removed `Restart=`/`RestartSec=`, changed `ExecStart` to
`docker compose -p <name> up -d`, set `Type=oneshot` + `RemainAfterExit=yes`. Kept
`ExecStop=docker compose -p <name> down` unchanged.

**Verification performed after the fix:**

- `systemctl --failed` — empty across all 4 units.
- `systemctl status <unit>` — `Active: active (exited)` on all 4 (expected steady state
  for `Type=oneshot` + `RemainAfterExit=yes`).
- `docker ps` — all containers in all 4 projects confirmed running.
- Functional HTTP checks through the reverse proxy confirmed applications reachable.

**Separate gotcha encountered while applying the fix to one unit:**

- Error: `Error response from daemon: endpoint with name <container-name> already
  exists in network <project>_<network>`, with `docker ps -a --filter
  name=<container-name>` showing zero matching containers — a stuck libnetwork
  endpoint reservation outliving its container.
- Resolution: `systemctl restart docker.service`, confirmed via
  `docker network inspect <network> --format '{{json .Containers}}'` returning empty
  for the stale endpoint before the next `up -d` succeeded.
- Caveat: check `docker info | grep -i 'Live Restore'` before restarting `docker.service`
  on a host with other unrelated live containers — `Live Restore Enabled: false` means
  the daemon restart briefly stops every container on the host.

## Verified On

| Project | Context | Details |
|---------|---------|---------|
| HomeLab (Debian host) | Traefik reverse proxy + 3 independent HomelabOS docker-compose app stacks, each supervised by its own systemd unit | Confirmed via `systemctl --failed` (empty), `systemctl status` (`active (exited)` on all 4 units), `docker ps` (containers running), and functional HTTP checks through the reverse proxy after applying the `Type=oneshot` + `RemainAfterExit=yes` + `up -d`/`down` fix to all 4 units |
