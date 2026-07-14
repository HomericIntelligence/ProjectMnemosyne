---
name: docker-apt-runc-conflict-removes-docker-ce
description: "Diagnose and fix a Docker Engine that has vanished (docker.service/docker.socket unit files missing, dpkg shows docker-ce/docker.io in state rc) because installing the standalone Debian runc package forced apt to remove containerd.io/docker-ce via a Conflicts/Replaces relationship. Use when: (1) docker.socket not found after unmask, (2) docker-ce shows rc in dpkg -l, (3) Docker disappeared after installing build tools (e.g. a from-source Docker/Moby/containerd build-dependency list that includes runc)."
category: debugging
date: 2026-07-13
version: "1.0.0"
user-invocable: false
verification: verified-local
tags:
  - docker
  - docker-ce
  - containerd
  - runc
  - apt
  - dpkg
  - systemd
  - systemctl
  - homelab
  - debian
---

# Docker apt runc Conflict Removes docker-ce

## Overview

| Field | Value |
|-------|-------|
| **Date** | 2026-07-13 |
| **Objective** | Restore a fully-working Docker Engine on a Debian "buster"-based host (self-hosted HomelabOS stack: Traefik + several docker-compose-managed services) after `docker.service`/`docker.socket` were found masked and every dependent systemd unit was failing |
| **Outcome** | Successful fix — root cause was that installing the standalone Debian `runc` package had caused apt to remove `containerd.io` and (transitively) `docker-ce`; reinstalling `docker-ce docker-ce-cli containerd.io` restored a healthy daemon |
| **Verification** | verified-local — executed live on a real host, confirmed `docker info` healthy afterward. Not verified-ci since this isn't a CI-testable scenario |

## When to Use

- `systemctl start docker.socket` fails with `Failed to start docker.socket: Unit docker.socket not found.` even AFTER `systemctl unmask docker.service docker.socket` and `systemctl daemon-reload` succeeded
- `find /lib/systemd/system /usr/lib/systemd/system -iname 'docker.service'` returns nothing — the unit file genuinely does not exist on disk, not just masked
- `dpkg -l | grep -i docker` shows `docker-ce` and/or `docker.io` in state `rc` (removed, config remains) while `docker-ce-cli`, `docker-ce-rootless-extras`, `docker-buildx-plugin`, `docker-compose-plugin` are still `ii` (installed) — i.e. only the engine/daemon packages vanished, not the CLI/plugins
- Docker was working, you (or a script) then ran `apt-get install` with a from-source Docker/Moby/containerd/runc build-dependency list (commonly includes `btrfs-progs gcc git golang-go go-md2man iptables libbtrfs-dev libseccomp-dev libselinux1-dev make pkg-config runc uidmap`), and Docker broke immediately after
- You want to know, before it bites you, whether installing the standalone `runc` package on a host that also has packaged `docker-ce`/`containerd.io` is safe (it is not)

## Verified Workflow

### Quick Reference

```bash
# 1. Confirm the unit files are actually missing, not just masked
systemctl unmask docker.service docker.socket
systemctl daemon-reload
systemctl start docker.socket   # if this still says "Unit docker.socket not found", the package is gone
find /lib/systemd/system /usr/lib/systemd/system -iname 'docker.service'   # empty output confirms it

# 2. Check which docker packages are actually installed vs removed
dpkg -l | grep -i docker
# look for docker-ce / docker.io in state "rc" (removed) vs docker-ce-cli / plugins still "ii"

# 3. Find the apt transaction that removed them
grep -i -E 'runc|containerd.io|docker-ce' /var/log/apt/history.log

# 4. Confirm the mechanism: containerd.io's package metadata conflicts with standalone runc
apt-cache show containerd.io | grep -E 'Provides|Conflicts|Replaces'
# Provides: containerd, runc
# Conflicts: containerd, runc
# Replaces: containerd, runc

# 5. Fix: reinstall the Docker-repo packages; let apt remove the standalone runc automatically
apt-get install docker-ce docker-ce-cli containerd.io
# apt will list "runc" under "The following packages will be REMOVED" -- this is expected, let it proceed

# 6. Verify
systemctl start docker.socket
systemctl start docker.service
docker info
```

### Detailed Steps

1. **Don't stop at `systemctl unmask`.** If Docker was previously masked (e.g. by an earlier
   troubleshooting step, or a HomelabOS provisioning script), `systemctl unmask docker.service
   docker.socket` followed by `systemctl daemon-reload` will succeed and remove the
   admin-created `/dev/null` mask symlinks — but this does **nothing** if the underlying vendor
   unit file is simply absent. The tell is that `systemctl start docker.socket` still fails with
   `Failed to start docker.socket: Unit docker.socket not found.` *after* a clean unmask +
   reload. Confirm the unit file is truly gone (not just masked) with:

   ```bash
   find /lib/systemd/system /usr/lib/systemd/system -iname 'docker.service'
   ```

   Empty output means the package that ships this unit file was removed from the system —
   this is a package problem, not a systemd-state problem.

2. **Check installed vs removed package state with `dpkg -l`:**

   ```bash
   dpkg -l | grep -i docker
   ```

   `rc` means removed with config retained (not installed); `ii` means fully installed. In this
   incident, `docker-ce` and `docker.io` were both `rc` while `docker-ce-cli`,
   `docker-ce-rootless-extras`, `docker-buildx-plugin`, and `docker-compose-plugin` were all
   still `ii`. Only the actual engine/daemon packages were gone — the CLI and plugins survived,
   which is why `docker` commands still resolved but immediately failed to reach a daemon.

3. **Find the root cause in apt's history log:**

   ```bash
   grep -i -E 'runc|containerd.io|docker-ce' /var/log/apt/history.log
   ```

   In this incident, an earlier `apt-get install btrfs-progs gcc git golang-go go-md2man
   iptables libbtrfs-dev libseccomp-dev libselinux1-dev make pkg-config runc uidmap ...` (the
   classic dependency list for building Docker/Moby/containerd/runc from source) had, as a side
   effect, done `Remove: containerd.io, docker-ce`. Installing the standalone Debian `runc`
   package had forced apt's dependency resolver to remove the Docker-repo `containerd.io` and
   (transitively) `docker-ce` packages.

4. **Confirm the exact mechanism** with `apt-cache show`:

   ```bash
   apt-cache show containerd.io | grep -E 'Provides|Conflicts|Replaces'
   ```

   Docker's own `containerd.io` `.deb` package ships its own bundled `/usr/bin/runc` and
   explicitly declares `Provides:`/`Conflicts:`/`Replaces:` against the standalone Debian
   `runc` package to avoid a file-ownership clash over `/usr/bin/runc`. This means: installing
   the standalone `runc` package will force-remove `containerd.io` (and anything depending on
   it, like `docker-ce`) — and the reverse is equally true: reinstalling `containerd.io` will
   automatically remove the standalone `runc` package again, cleanly reclaiming
   `/usr/bin/runc` without any manual `dpkg -r` needed.

5. **Fix by reinstalling the Docker-repo packages:**

   ```bash
   apt-get install docker-ce docker-ce-cli containerd.io
   ```

   `docker-ce-cli` was already present in this incident so it was a no-op; the important part
   is `docker-ce` and `containerd.io`. apt will automatically list `runc` under "The following
   packages will be REMOVED" and proceed — this is expected/correct behavior, not an error to
   fight or work around.

6. **Verify the daemon is healthy:**

   ```bash
   systemctl start docker.socket
   systemctl start docker.service
   docker info
   ```

   After the reinstall, `docker.service`/`docker.socket` unit files existed again, both units
   started cleanly, and `docker info` reported a healthy daemon.

7. **Practical implication going forward:** if you are ever doing a from-source build of
   Docker/containerd/runc on a host that also has the packaged `docker-ce`/`containerd.io`
   installed, expect installing a standalone `runc` package (or any build-dependency list that
   includes it) to silently remove your working Docker installation as an apt side effect —
   budget for reinstalling `docker-ce` afterward, or avoid installing the standalone `runc`
   package if you don't strictly need it.

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
|---------|----------------|---------------|-----------------|
| `systemctl unmask` + `daemon-reload` alone | Ran `systemctl unmask docker.service docker.socket` and `systemctl daemon-reload`, expecting this to fully resolve the failing units since they appeared masked | Unmasking only removes an admin-created `/dev/null` mask symlink; `systemctl start docker.socket` still failed with `Unit docker.socket not found.` because the underlying vendor unit file didn't exist on disk at all — the package shipping it had been removed | A successful unmask that still can't find the unit afterward means the problem is a missing package, not (only) a mask; verify with `find /lib/systemd/system /usr/lib/systemd/system -iname 'docker.service'` before assuming the mask was the whole story |

## Results & Parameters

**Environment:** Debian "buster"-based homelab host running HomelabOS (Traefik + several
docker-compose-managed services)

**Failing command (after unmask):**

```bash
systemctl start docker.socket
```

**Observed error:**

```text
Failed to start docker.socket: Unit docker.socket not found.
```

**Decisive diagnostic output:**

```text
$ dpkg -l | grep -i docker
rc  docker-ce                     ...
rc  docker.io                     ...
ii  docker-ce-cli                 ...
ii  docker-ce-rootless-extras     ...
ii  docker-buildx-plugin          ...
ii  docker-compose-plugin         ...
```

```text
$ apt-cache show containerd.io | grep -E 'Provides|Conflicts|Replaces'
Provides: containerd, runc
Conflicts: containerd, runc
Replaces: containerd, runc
```

**Root cause:** an earlier `apt-get install` of a from-source Docker/Moby/containerd build
dependency list (including the standalone Debian `runc` package) triggered apt to remove
`containerd.io` and, transitively, `docker-ce`, because `containerd.io` declares
`Conflicts:`/`Replaces:` against the standalone `runc` package (both ship `/usr/bin/runc`).

**Fix applied:**

```bash
apt-get install docker-ce docker-ce-cli containerd.io
# apt lists "runc" under "The following packages will be REMOVED" -- expected, let it proceed
systemctl start docker.socket
systemctl start docker.service
docker info   # confirmed healthy
```

## Verified On

| Project | Context | Details |
|---------|---------|---------|
| homelab | Debian "buster"-based host, HomelabOS stack (Traefik + docker-compose services), 2026-07-13 | Confirmed via live `dpkg -l`/`apt-cache show`/`/var/log/apt/history.log` output; fix verified with `docker info` reporting a healthy daemon afterward |
