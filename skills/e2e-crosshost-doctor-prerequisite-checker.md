---
name: e2e-crosshost-doctor-prerequisite-checker
description: "Build a `just doctor` prerequisite checker for the HomericIntelligence cross-host E2E pipeline. Use when: (1) creating or extending the doctor diagnostic tool, (2) adding new check categories or dependency verifications, (3) debugging missing prerequisites on worker/control hosts, (4) implementing auto-install modes for CI or fresh host setup."
category: tooling
date: 2026-04-06
version: "1.3.0"
user-invocable: false
verification: verified-local
tags:
  - e2e
  - doctor
  - prerequisite
  - cross-host
  - deployment
  - verification
  - podman
  - tailscale
  - cpp20
  - homeric-intelligence
  - wsl2
  - ssh
  - systemd
  - dbus
  - linger
  - source-build
  - unit-files
  - service-in-template
  - firewalld
  - firewall
  - worker-provisioning
---

# E2E Cross-Host Doctor Prerequisite Checker

## Overview

| Field | Value |
| ------- | ------- |
| **Date** | 2026-04-06 |
| **Objective** | Create a `just doctor` prerequisite checker/installer for the HomericIntelligence cross-host E2E evaluation pipeline, organized by component categories from docs/architecture.md |
| **Outcome** | ~530-line bash script (`e2e/doctor.sh`) with 7 check categories, role filtering (`--role worker\|control`), auto-install mode (`--install`), and post-deployment service health verification (`--check-services`). All 3 role modes verified on control host. |
| **Verification** | verified-local |

## When to Use

- Creating a new doctor/prerequisite checker for a distributed deployment pipeline
- Adding new check categories to an existing doctor script (follow the architecture.md-driven pattern)
- Debugging why a fresh host fails to build or run HomericIntelligence services
- Setting up CI gates that verify prerequisites before E2E pipeline execution
- Extending the `--install` auto-fix mode with new dependency installers
- Verifying cross-host service health after deployment (`--check-services`)
- Diagnosing `systemctl --user` failures over SSH (missing `$DBUS_SESSION_BUS_ADDRESS` / `$XDG_RUNTIME_DIR`)
- Diagnosing podman socket enable failures when podman was installed from source and `systemctl --user` reports "Unit podman.socket could not be found"
- Diagnosing why cross-host service ports are blocked despite Tailscale connectivity working (SSH works but `curl` to service ports returns "No route to host")
- Setting up a new worker host that participates in the HomericIntelligence Tailscale mesh for cross-host E2E validation

## Verified Workflow

### Quick Reference

```bash
# Check-only mode (all hosts)
just doctor

# Check + auto-install missing dependencies
just doctor --install

# Check only worker-host dependencies (skips C++ build chain)
just doctor --role worker

# Check only control-host dependencies (skips container runtime)
just doctor --role control

# Post-deployment service health verification
just doctor --check-services --worker-ip 100.92.173.32 --control-ip 100.73.61.56

# Combined: worker role + install
just doctor --role worker --install
```

### Design Principles

1. **Architecture-driven organization**: Check categories map 1:1 to the component inventory in `docs/architecture.md`. This ensures the doctor stays in sync with the system and makes it obvious where to add new checks.

2. **Role filtering**: The `--role worker|control` flag scopes checks per host type. Worker hosts skip C++ build chain checks (they run containers only). Control hosts skip container runtime checks (they build and run native binaries).

3. **Composable exit codes**: Exit 0 on all pass, exit 1 on any failure. This makes the doctor composable with CI pipelines (`just doctor && just e2e-test`).

4. **Install mode as opt-in**: The `--install` flag enables auto-fix for missing dependencies. Without it, the doctor is read-only and safe for diagnostics.

### The 7 Check Categories

| # | Category | Scope | Key Checks |
| --- | ---------- | ------- | ------------ |
| 1 | Core Tooling | all hosts | git, just, python3, pip3, curl, jq |
| 2 | Tailscale (Network Topology) | all hosts | tailscale binary, tailscaled running, peer reachability (if IPs provided) |
| 3 | Container Runtime (AchaeanFleet) | worker only | podman, podman compose, podman socket, aardvark-dns PID staleness |
| 4 | C++ Build Chain | control only | cmake >= 3.20, ninja, g++ >= 11, libssl-dev, make, conan >= 2.0, Conan default profile, pixi |
| 5 | Python Dependencies | all hosts | nats-py (required by odysseus-console.py) |
| 6 | Submodule Health | all hosts | submodules initialized, Myrmidons ai-maestro references, symlink resolution |
| 7 | Service Health (Cross-Host) | --check-services | NATS, Agamemnon, Hermes, Grafana, Prometheus, argus-exporter (worker); Nestor (control) |

### Detailed Steps

1. **Output helpers**: Define `check_pass()`, `check_fail()`, `check_warn()`, `check_skip()` with color codes and counters. Reuse the color palette from `e2e/lib/common.sh` for consistency.

2. **Argument parsing**: Use a `while [[ $# -gt 0 ]]` loop with `case` for `--install`, `--role`, `--check-services`, `--worker-ip`, `--control-ip`.

3. **Version comparison helper**: The `version_gte()` function uses `sort -V` for semantic version comparison:
   ```bash
   version_gte() {
       printf '%s\n%s\n' "$2" "$1" | sort -V | head -1 | grep -qF "$2"
   }
   ```
   This returns 0 (true) if `$1 >= $2`. Used for cmake >= 3.20, g++ >= 11, conan >= 2.0.

4. **Role gating**: Define `should_check_worker()` and `should_check_control()` helpers that check the `$ROLE` variable. Entire category sections are wrapped in `if should_check_*; then ... else check_skip ...; fi`.

5. **Aardvark-dns staleness check** (WSL2-specific): Read PID from `${XDG_RUNTIME_DIR}/containers/networks/aardvark-dns/aardvark.pid`, test with `kill -0`, warn if stale. With `--install`, remove the stale PID file.

6. **Myrmidons ai-maestro detection**: `grep -r "aim_" "$MYRMIDONS_DIR/scripts/"` catches stale function references. This is critical because the Myrmidons submodule pin can lag behind migrations.

7. **Symlink resolution**: Iterate `git submodule status` output, run `readlink -f` on each path, warn on broken symlinks.

8. **SSH/systemd user session handling** (for `systemctl --user` commands): Before calling `systemctl --user`, export fallback env vars:
   ```bash
   export XDG_RUNTIME_DIR="${XDG_RUNTIME_DIR:-/run/user/$(id -u)}"
   export DBUS_SESSION_BUS_ADDRESS="${DBUS_SESSION_BUS_ADDRESS:-unix:path=${XDG_RUNTIME_DIR}/bus}"
   ```
   If `systemctl --user` still fails (systemd user instance not running), print actionable diagnostics suggesting `sudo loginctl enable-linger $USER` then reconnect. Never swallow `systemctl --user` errors with `2>/dev/null` -- capture stderr and surface it on failure.

9. **Source-built podman unit file detection and install** (for `--install` path, podman socket check): Before calling `systemctl --user enable --now podman.socket`, verify the unit exists:
   ```bash
   if ! systemctl --user cat podman.socket &>/dev/null; then
       # Unit not found — podman likely installed from source without unit files
       # Search known source tree locations
       for src_dir in ~/.local/src/podman-*/contrib/systemd/user \
                      /usr/local/src/podman-*/contrib/systemd/user; do
           if [[ -d "$src_dir" ]]; then
               mkdir -p ~/.config/systemd/user
               cp "$src_dir/podman.socket" ~/.config/systemd/user/podman.socket
               # Process .service.in template: substitute @@PODMAN@@ with actual binary path
               sed "s|@@PODMAN@@|$(command -v podman)|g" \
                   "$src_dir/podman.service.in" \
                   > ~/.config/systemd/user/podman.service
               systemctl --user daemon-reload
               break
           fi
       done
   fi
   systemctl --user enable --now podman.socket
   ```
   Verify success with `systemctl --user is-active podman.socket` and check the socket file exists at `/run/user/$(id -u)/podman/podman.sock`. Fix: PR Odysseus#86, issue #85.

10. **Firewalld / Tailscale zone check** (for new worker hosts): On hosts using firewalld (default on Debian 11+ and many systemd distros), the `tailscale0` interface is not automatically placed in the `trusted` zone. This causes all non-SSH service ports to return "No route to host" (ICMP reject) even though Tailscale connectivity itself is working. Add a check that probes whether `tailscale0` is in the trusted zone (or equivalent iptables ACCEPT rule exists) and warn loudly if not:
    ```bash
    # Check if firewalld is active and tailscale0 is in trusted zone
    if systemctl is-active --quiet firewalld 2>/dev/null; then
        if firewall-cmd --get-active-zones 2>/dev/null | grep -A1 "trusted" | grep -q "tailscale0"; then
            check_pass "firewalld: tailscale0 in trusted zone"
        else
            check_fail "firewalld: tailscale0 NOT in trusted zone (cross-host service ports will be blocked)"
            if [[ "$INSTALL" == "true" ]]; then
                sudo firewall-cmd --permanent --zone=trusted --add-interface=tailscale0
                sudo firewall-cmd --reload
                check_pass "firewalld: tailscale0 added to trusted zone (reload applied)"
            else
                echo "  Fix: sudo firewall-cmd --permanent --zone=trusted --add-interface=tailscale0 && sudo firewall-cmd --reload"
            fi
        fi
    fi
    ```
    With `--install`, auto-apply the fix. Key diagnostic: "No route to host" (ICMP reject = firewall block) vs. connection timeout (silent drop = Tailscale ACL block). If `ping <worker-ip>` succeeds but `nc -zv <worker-ip> 4222` returns "No route to host", the worker's firewall is the culprit — not Tailscale ACL. See Failed Attempts for full diagnosis.

    **Worker provisioning checklist addition** — run these on every new worker host before E2E validation:
    ```bash
    # On new worker host: add tailscale0 to firewalld trusted zone
    # (firewalld is default on Debian 11+ and many systemd distros)
    sudo firewall-cmd --permanent --zone=trusted --add-interface=tailscale0
    sudo firewall-cmd --reload

    # Verify zone assignment
    firewall-cmd --get-active-zones
    # Should show: tailscale0 in trusted zone

    # Verify from control host (should be "Connection refused", not "No route to host")
    nc -zv <worker-ip> 4222
    # "Connection refused" = firewall open, NATS not running yet (correct)
    # "No route to host"   = firewall still blocking (fix not applied)
    ```

11. **Summary**: Print pass/fail/warn counts. If any failures and `--install` was not used, print a hint to run `just doctor --install`.

### File Layout

```
e2e/doctor.sh           # The doctor script (~530 lines)
justfile                 # Integration: doctor *ARGS: bash e2e/doctor.sh {{ ARGS }}
```

### Install Commands by Dependency

| Dependency | Install Method |
| ------------ | --------------- |
| git, python3, pip3, curl, jq, podman, cmake, ninja-build, g++, libssl-dev, make | `apt-get install -y <pkg>` |
| just | `cargo install just` or prebuilt binary via `just.systems/install.sh` |
| tailscale | `curl -fsSL https://tailscale.com/install.sh \| sh` |
| conan | `pip3 install --break-system-packages conan` |
| pixi | `curl -fsSL https://pixi.sh/install.sh \| bash` |
| nats-py | `pip3 install --break-system-packages nats-py` |
| podman socket | `systemctl --user enable --now podman.socket` -- **SSH caveat**: requires `XDG_RUNTIME_DIR` and `DBUS_SESSION_BUS_ADDRESS` env vars; if systemd user instance is not running, must first run `sudo loginctl enable-linger $USER` and reconnect. **Source-build caveat**: if podman was built from source, the systemd unit files may not be installed. Check with `systemctl --user cat podman.socket`; if missing, copy `podman.socket` and process `podman.service.in` from `~/.local/src/podman-*/contrib/systemd/user/` into `~/.config/systemd/user/` then `daemon-reload` before enabling (see Detailed Step 9 and Failed Attempts) |
| Conan profile | `conan profile detect --force` |
| submodules | `git submodule update --init --recursive` |

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
| --------- | ---------------- | --------------- | ---------------- |
| Conan via pixi | Assumed conan would be available through pixi environment since the justfile uses `pixi run conan install` | Conan is expected to be system-installed. Agamemnon's pixi.toml does not declare conan as a dependency. The `pixi run` invocation works because pixi falls through to system PATH. | The doctor check correctly expects system-installed conan. Do not add conan to pixi.toml; it is a system prerequisite. |
| Single flat check list | Initially wrote all checks in a flat sequence without category sections | Hard to map failures back to the architecture component that needs attention, and no way to skip irrelevant checks per host role | Organize checks by architecture.md component hierarchy (7 categories) and gate by role |
| Reusing common.sh directly | Tried `source e2e/lib/common.sh` for color and output helpers | common.sh defines functions for E2E test phases (PHASE_START, PHASE_END) that conflict with the doctor's simpler pass/fail/skip model | Define doctor-specific helpers (check_pass, check_fail, check_warn, check_skip) that match common.sh's color palette but have different semantics |
| Podman socket enable over SSH (silent failure) | `just doctor --role worker --install` ran `systemctl --user enable --now podman.socket` in the install path (`e2e/doctor.sh:233`), with stderr redirected to `/dev/null` | SSH sessions lack `$DBUS_SESSION_BUS_ADDRESS` and `$XDG_RUNTIME_DIR` env vars. Without these, `systemctl --user` cannot connect to the user's D-Bus session bus. The error was silently swallowed by `2>/dev/null`, and the fallback `check_warn` message told the user to run the same failing command manually. Confirmed with `loginctl show-user $USER --property=Linger` showing `Linger=no`. | (1) Always export `XDG_RUNTIME_DIR="${XDG_RUNTIME_DIR:-/run/user/$(id -u)}"` and `DBUS_SESSION_BUS_ADDRESS="${DBUS_SESSION_BUS_ADDRESS:-unix:path=${XDG_RUNTIME_DIR}/bus}"` before calling `systemctl --user`. (2) Setting env vars alone is NOT sufficient if the systemd user instance is not running at all (SSH without linger). Must detect this case and print actionable diagnostics: suggest `sudo loginctl enable-linger $USER`, then reconnect, or run from a desktop session. (3) Never swallow `systemctl --user` errors with `2>/dev/null` -- capture and surface them. Fix: PR Odysseus#82, issue #81. |
| `systemctl --user` when unit files missing (source-built podman) | After PR #82 fixed env vars and linger, `systemctl --user enable --now podman.socket` still failed with "Unit podman.socket could not be found" on a host with podman 5.8.1 built from source to `~/.local/bin/podman` | Podman installed from source does not automatically install systemd user unit files. The `podman.socket` and `podman.service` units were absent from `~/.config/systemd/user/` and all systemd search paths. PR #82's env var fix was necessary but not sufficient — once the D-Bus session was reachable, the unit itself was simply missing. The error message "Unit podman.socket could not be found" is the key diagnostic signal. Source trees (e.g. `~/.local/src/podman-5.8.1/contrib/systemd/user/`) contain `podman.socket` and `podman.service.in` (a template requiring `@@PODMAN@@` substitution with the actual binary path). | Before calling `systemctl --user enable`, probe with `systemctl --user cat podman.socket`. If it fails, search `~/.local/src/podman-*/contrib/systemd/user/` and `/usr/local/src/podman-*/contrib/systemd/user/` for the unit templates. Copy `podman.socket` directly; process `podman.service.in` through `sed "s\|@@PODMAN@@\|$(command -v podman)\|g"` to produce `podman.service`. Install both to`~/.config/systemd/user/`, run`systemctl --user daemon-reload`, then proceed with`enable --now`. Fix: PR Odysseus#86, issue #85. |
| Misdiagnosed as Tailscale ACL | `curl http://<worker-ip>:4222/varz` from the control host returned "No route to host" and only port 22 (SSH) was reachable. Initial assumption: Tailscale ACL policy was blocking specific ports. Checked Tailscale admin console — default ACL was "allow all". Attempted to add explicit ACL rules for ports 4222, 8080, 8085, 3001, 9090, 9100 — no effect. | Tailscale's default ACL is "allow all" between devices on the same tailnet. A "No route to host" response is an ICMP reject from the kernel firewall (`firewalld`/`iptables`/`nftables`), not a Tailscale drop. If it were a Tailscale ACL block, the connection would timeout silently (no ICMP reject). The worker host (epimetheus, Debian 11+) had `firewalld` active with `tailscale0` in the `public` zone (default), which blocks inbound connections to most ports. Only SSH (port 22) was permitted through the public zone's default rules. Key diagnostic: `ping <worker-ip>` succeeds (Tailscale up) + `nc -zv <worker-ip> 4222` returns "No route to host" (ICMP reject = firewall block). If Tailscale ACL were blocking, `nc` would hang silently. | (1) Distinguish "No route to host" (ICMP reject = local firewall) from connection timeout (silent drop = network/ACL/Tailscale policy). (2) Tailscale default ACL is "allow all" — do not blame Tailscale ACL without first verifying the worker's kernel firewall. (3) Fix: `sudo firewall-cmd --permanent --zone=trusted --add-interface=tailscale0 && sudo firewall-cmd --reload` on the worker host. After this fix, all 6 cross-host E2E test phases unblocked on epimetheus (2026-04-06). (4) Add this as a `just doctor` check: warn if `tailscale0` is not in the firewalld `trusted` zone. |

## Results & Parameters

### Configuration

```yaml
# File location
file: e2e/doctor.sh
lines: ~530
language: bash

# Justfile integration
justfile_recipe: |
  doctor *ARGS:
      bash e2e/doctor.sh {{ ARGS }}

# CLI flags
flags:
  --install: "Auto-install missing dependencies"
  --role: "worker | control | all (default: all)"
  --check-services: "Enable post-deployment service health checks"
  --worker-ip: "Tailscale IP of worker host (used with --check-services)"
  --control-ip: "Tailscale IP of control host (used with --check-services)"

# Version requirements
versions:
  cmake: ">= 3.20"
  g++: ">= 11"
  conan: ">= 2.0"

# Key paths
paths:
  podman_socket: "${XDG_RUNTIME_DIR:-/run/user/$(id -u)}/podman/podman.sock"
  aardvark_pid: "${XDG_RUNTIME_DIR:-/run/user/$(id -u)}/containers/networks/aardvark-dns/aardvark.pid"
  myrmidons_scripts: "provisioning/Myrmidons/scripts/"

# Service health endpoints (Section 7)
service_endpoints:
  nats: "http://<worker_ip>:8222/healthz"
  agamemnon: "http://<worker_ip>:8080/v1/health"
  hermes: "http://<worker_ip>:8085/health"
  grafana: "http://<worker_ip>:3001/api/health"
  prometheus: "http://<worker_ip>:9090/-/healthy"
  argus_exporter: "http://<worker_ip>:9100/metrics"
  nestor: "http://<control_ip>:8081/v1/health"

# Exit codes
exit_codes:
  0: "All checks passed"
  1: "One or more checks failed"
```

### Expected Output

Successful run on a fully-configured control host:

```
HomericIntelligence Doctor - E2E Pipeline Prerequisites
===============================================
  Role: all    Install: false

Core Tooling
  [pass] git 2.43.0
  [pass] just 1.25.2
  [pass] python3 3.12.3
  [pass] pip3 24.0
  [pass] curl 8.5.0
  [pass] jq 1.7.1

Tailscale (Network Topology)
  [pass] tailscale 1.62.0
  [pass] tailscaled running

Container Runtime (AchaeanFleet)
  [pass] podman 4.9.3
  [pass] podman compose 1.0.6
  [pass] podman socket active
  [pass] aardvark-dns OK

C++ Build Chain
  [pass] cmake 3.28.3 (>= 3.20)
  [pass] ninja 1.11.1
  [pass] g++ 13.2.0 (>= 11)
  [pass] libssl-dev 3.0.13
  [pass] make 4.3
  [pass] conan 2.3.0 (>= 2.0)
  [pass] Conan default profile exists
  [pass] pixi 0.18.0

Python Dependencies
  [pass] nats-py 2.7.2

Submodule Health
  [pass] All 15 submodules initialized
  [pass] Myrmidons targets Agamemnon (not ai-maestro)
  [pass] All submodule paths resolve

===============================================
All 22 checks passed.
```

## Related Skills

| Skill | Relationship |
| ------- | ------------- |
| `e2e-homeric-compose-cpp-pipeline` | The E2E pipeline that this doctor validates prerequisites for |
| `architecture-crosshost-nats-compose-deployment` | The cross-host deployment topology whose services the doctor verifies |

## Verified On

| Project | Context | Details |
| --------- | --------- | --------- |
| Odysseus | feat/crosshost-e2e-pipeline branch | Ran `just doctor`, `just doctor --role worker`, `just doctor --role control` on control host. All 3 modes passed. |
| Odysseus | main branch, PR #82 (issue #81) | Fixed `just doctor --role worker --install` failing to enable podman socket over SSH due to missing `$DBUS_SESSION_BUS_ADDRESS` and `$XDG_RUNTIME_DIR`. Verified locally on worker host via SSH. |
| Odysseus | main branch, PR #86 (issue #85) | Fixed `just doctor --role worker --install` failing to enable podman socket when podman 5.8.1 was built from source (`~/.local/bin/podman`) and systemd unit files were not installed. Implemented unit file detection and install from source tree `contrib/systemd/user/`. Verified: `systemctl --user is-active podman.socket` → `active`, socket at `/run/user/1000/podman/podman.sock`. |
| Odysseus (epimetheus worker) | main branch, 2026-04-06 | Diagnosed and fixed firewalld blocking all cross-host service ports on epimetheus despite Tailscale connectivity being up. Running `sudo firewall-cmd --permanent --zone=trusted --add-interface=tailscale0 && sudo firewall-cmd --reload` unblocked all 6 cross-host E2E test phases. Confirmed: `nc -zv <worker-ip> 4222` changed from "No route to host" to "Connection refused" (NATS not yet running, firewall open). |
