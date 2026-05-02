---
name: homeric-intelligence-ecosystem-installer
description: "Add a portable ecosystem installer script (scripts/shell/install.sh) to ProjectHephaestus that installs all HomericIntelligence dependencies on any Tailnet host; deploy it remotely via parallel SSH fan-out. Use when: (1) onboarding a new host to the HomericIntelligence mesh, (2) diagnosing missing dependencies (Go, nats-py, cmake, templ) on worker/control/apollo hosts, (3) extending the shared installer with new dependency sections, (4) troubleshooting nats-server install, Go version, or pip system-packages restrictions on Debian 12, (5) running a parallel SSH fan-out across all Tailnet hosts to install the ecosystem."
category: tooling
date: 2026-04-28
version: "1.1.0"
user-invocable: false
verification: verified-local
history: homeric-intelligence-ecosystem-installer.history
tags:
  - ecosystem
  - installer
  - homeric-intelligence
  - nats-server
  - go
  - python
  - cmake
  - tailscale
  - podman
  - hephaestus
  - debian
  - mesh-bringup
  - dependencies
  - ssh-fanout
  - parallel-deploy
  - tailnet
---

# HomericIntelligence Ecosystem Installer

## Overview

| Field | Value |
| ------- | ------- |
| **Date** | 2026-04-28 |
| **Objective** | Create a portable ecosystem installer (`scripts/shell/install.sh`) in ProjectHephaestus that installs all HomericIntelligence dependencies on any Tailnet host — and deploy it across all reachable Tailnet hosts via parallel SSH fan-out |
| **Outcome** | Installer runs on 5 of 7 hosts; 2 hosts (aeolus, hephaestus) fully complete; 3 partial (artemis, hermes, apollo); 2 failed (athena, titan) due to missing git + sudo password requirement |
| **Verification** | verified-local — executed on 5 of 7 Tailnet hosts; athena/titan blocked by missing git + sudo password |
| **History** | [changelog](./homeric-intelligence-ecosystem-installer.history) |

## When to Use

- Bringing up a new host (epimetheus, apollo, hephaestus, aeolus, or any Tailnet node) for the HomericIntelligence mesh
- Diagnosing which dependencies are missing on a host before mesh bringup
- Installing Go 1.23+, templ, nats-py, nats-server, cmake 3.20+, pixi, or gh CLI on Debian stable
- Adding new dependency sections to the shared installer in ProjectHephaestus
- Running a parallel SSH fan-out to install the ecosystem across all reachable Tailnet hosts simultaneously
- Explaining why `pip3 install nats-py` fails on Debian 12 without `--break-system-packages`
- Explaining why apt cmake on Debian stable is too old (3.18.x) and how to get 3.20+
- Explaining why NATS server must be installed as a native binary (not podman) for cross-host connectivity

## Verified Workflow

### Quick Reference

```bash
# Check only — see what's missing
just install-check

# Install all dependencies (default: all roles)
just install

# Install only worker-role dependencies (Python, nats-py, Go, podman)
just install ROLE=worker

# Install only control-role dependencies (C++ build chain, cmake, conan)
just install ROLE=control

# Direct script usage
bash scripts/shell/install.sh --role worker --install
bash scripts/shell/install.sh --role control --install
bash scripts/shell/install.sh --role all     # check-only by default
bash scripts/shell/install.sh --install      # install all deps
```

### Remote SSH Fan-Out Deployment (Parallel)

Deploy the installer to all Tailnet hosts simultaneously:

```bash
# Step 1: Add host keys for all targets (do this FIRST — prevents host key verification failure)
ssh-keyscan -H aeolus apollo artemis athena hephaestus hermes titan >> ~/.ssh/known_hosts

# Step 2: Probe all hosts in parallel — check reachability, arch, Python, git presence
for host in aeolus apollo artemis athena hephaestus hermes titan; do
  echo -n "$host: "
  ssh -o ConnectTimeout=6 -o BatchMode=yes "$host" \
    'echo OK && uname -m && python3 --version 2>/dev/null && which git 2>/dev/null || echo no-git' \
    2>&1 | tr '\n' ' '
  echo
done

# Step 3: Check sudo passwordless status per host
for host in aeolus apollo artemis athena hephaestus hermes titan; do
  echo -n "$host sudo: "
  ssh -o BatchMode=yes "$host" 'sudo -n true 2>&1 && echo NOPASSWD-OK || echo NEEDS-PASSWORD'
done

# Step 4: For hosts with git + NOPASSWD sudo — dispatch parallel installer agents
# (Fan out 7 Haiku sub-agents simultaneously, one per host)
# Each agent runs:
ssh -o BatchMode=yes <host> '
  mkdir -p ~/Projects
  git clone https://github.com/HomericIntelligence/ProjectHephaestus.git ~/Projects/ProjectHephaestus || \
    git -C ~/Projects/ProjectHephaestus pull
  bash ~/Projects/ProjectHephaestus/scripts/shell/install.sh --install
'

# Step 5: For hosts with sudo password required — provide interactive command to user
# Use ! prefix convention so user runs it with password prompt:
ssh <host> 'sudo apt-get install -y git && mkdir -p ~/Projects && \
  git clone https://github.com/HomericIntelligence/ProjectHephaestus.git ~/Projects/ProjectHephaestus && \
  bash ~/Projects/ProjectHephaestus/scripts/shell/install.sh --install'
```

### Detailed Steps

1. **Add installer to ProjectHephaestus** at `scripts/shell/install.sh`
   - Pattern based on `e2e/doctor.sh` in Odysseus: colored output helpers, `version_gte`, `has_cmd`, `get_version`, counters
   - NOT a copy of `doctor.sh` — the new script is host-agnostic (no submodule checks, no Myrmidons, no crosshost topology)

2. **Script structure** — sections in order:

   | Section | Role Gate | Notes |
   | --------- | ----------- | ------- |
   | Core tooling: git, curl, jq, unzip, just, gh CLI | all | gh installed via official apt source |
   | Tailscale | all | install script + tailscaled status check |
   | Python 3.10+, pip3, nats-py, pixi | all | nats-py: `--break-system-packages` fallback to `--user` |
   | Go 1.23+ | worker | Official tarball to `/usr/local/go`; apt version too old on Debian stable |
   | templ | worker | `GOBIN=~/.local/bin go install github.com/a-h/templ/cmd/templ@latest` |
   | nats-server 2.10+ | all | Native binary to `~/.local/bin`; NOT podman |
   | nats CLI | all | zip from GitHub releases; not in apt |
   | Container: podman, podman-compose, podman socket | worker | slirp4netns issues preclude podman for NATS |
   | C++ build chain | control | cmake 3.20+ from kitware repo or pip; ninja, gcc, g++, libssl-dev, conan |
   | PATH sanity | all | Check `~/.local/bin` and `/usr/local/go/bin` in PATH |

3. **Justfile recipes** — add to ProjectHephaestus `justfile`:
   ```makefile
   # Verify all HomericIntelligence host dependencies (no install)
   install-check:
       bash scripts/shell/install.sh

   # Install missing dependencies for a given role (default: all)
   install ROLE="all":
       bash scripts/shell/install.sh --role {{ROLE}} --install
   ```

4. **Key implementation details**:

   ```bash
   # nats-py on Debian 12 — system pip restricts installs
   if pip3 install nats-py --break-system-packages 2>/dev/null; then
     check_pass "nats-py"
   elif pip3 install nats-py --user 2>/dev/null; then
     check_warn "nats-py (user install)"
   else
     check_fail "nats-py"
   fi

   # Go — apt version is 1.19 on Debian 12; must use official tarball
   GO_VERSION="1.23.4"
   curl -fsSL "https://go.dev/dl/go${GO_VERSION}.linux-amd64.tar.gz" | \
     sudo tar -C /usr/local -xz
   # Adds /usr/local/go/bin to PATH

   # templ — requires Go 1.23+
   GOBIN="$HOME/.local/bin" go install github.com/a-h/templ/cmd/templ@latest

   # nats-server — native binary, not podman
   NATS_VERSION="2.10.21"
   curl -fsSL "https://github.com/nats-io/nats-server/releases/download/v${NATS_VERSION}/nats-server-v${NATS_VERSION}-linux-amd64.zip" \
     -o /tmp/nats-server.zip
   unzip -o /tmp/nats-server.zip -d /tmp/nats-server-extract
   mv /tmp/nats-server-extract/nats-server-*/nats-server "$HOME/.local/bin/"
   chmod +x "$HOME/.local/bin/nats-server"

   # nats CLI — zip from GitHub
   NATS_CLI_VERSION="0.1.5"
   curl -fsSL "https://github.com/nats-io/natscli/releases/download/v${NATS_CLI_VERSION}/nats-${NATS_CLI_VERSION}-linux-amd64.zip" \
     -o /tmp/nats-cli.zip
   unzip -o /tmp/nats-cli.zip -d /tmp/nats-cli-extract
   mv /tmp/nats-cli-extract/nats-*/nats "$HOME/.local/bin/"

   # cmake 3.20+ — apt gives 3.18.x on Debian stable; use pip or kitware
   pip3 install cmake --break-system-packages  # gets 3.28+
   # OR: add kitware apt repo for cmake 3.25+
   ```

### Why NATS Must Be Native Binary (Not Podman)

Slirp4netns (rootless podman networking) creates a user-space NAT that breaks cross-host NATS
connections: other Tailnet hosts see the podman NAT address, not the real Tailscale IP. Native
binary on `~/.local/bin` binds directly to the Tailscale interface and is reachable from any
Tailnet host.

### Difference from e2e/doctor.sh (Odysseus)

| Feature | `e2e/doctor.sh` | `scripts/shell/install.sh` |
| --------- | ----------------- | ---------------------------- |
| Location | Odysseus repo | ProjectHephaestus (shared) |
| Go check | None | Yes (1.23+) |
| templ check | None | Yes |
| gh CLI install | None | Yes |
| nats-server install | None | Yes (native binary) |
| Submodule checks | Yes | No |
| Myrmidons/crosshost | Yes | No |
| Host-agnostic | No | Yes |

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
| --------- | ---------------- | --------------- | ---------------- |
| pip3 install nats-py (plain) | `pip3 install nats-py` on Debian 12 | Debian 12 enforces PEP 668 — system pip refuses installs without `--break-system-packages` | Always use `--break-system-packages` first, fall back to `--user` |
| podman for NATS server | Run `nats-server` inside rootless podman container | Slirp4netns NAT hides real Tailscale IP; cross-host NATS connections fail | NATS server must be a native binary bound to the Tailscale interface |
| apt cmake on Debian stable | `sudo apt install cmake` | Debian stable ships cmake 3.18.x; Agamemnon requires cmake 3.20+ | Use `pip3 install cmake --break-system-packages` or add kitware apt repo |
| apt go on Debian stable | `sudo apt install golang` | Debian stable ships Go 1.19; templ and Agamemnon require 1.23+ | Download official Go tarball from https://go.dev/dl/ |
| pkill -f nats-server | `pkill -f "nats-server"` to stop stale server | Returns exit code 144 on some hosts (pkill receives SIGTERM itself) | Use `kill $(ps aux \| grep nats-server \| grep -v grep \| awk '{print $2}')` |
| hermes.main:app entrypoint | `uvicorn hermes.main:app` | Module `hermes.main` does not exist; correct module is `hermes.server` | Always use `uvicorn hermes.server:app` for ProjectHermes |
| Agamemnon/Nestor auto-reconnect | Restarted NATS server, expected binaries to reconnect automatically | C++ NATS clients do not auto-reconnect after server restart | After any NATS restart, kill and restart Agamemnon and Nestor too |
| NATS monitoring on :4222 | `curl http://localhost:4222/varz` | Port 4222 is the NATS protocol port; monitoring HTTP is on :8222 | NATS monitoring endpoint: `http://localhost:8222/varz` |
| C++ binaries in build/ root | `./control/ProjectAgamemnon/build/agamemnon` | Binaries are in `build/debug/`, not `build/` root | Correct path: `./control/ProjectAgamemnon/build/debug/agamemnon` |
| SSH without ssh-keyscan first | Probed new host `aeolus` over SSH without adding host key | Host key verification failed — SSH refused connection | Run `ssh-keyscan -H <host> >> ~/.ssh/known_hosts` before any batch SSH operation to new hosts |
| sudo apt-get in BatchMode SSH | `ssh -o BatchMode=yes host 'sudo apt-get install -y git'` | `sudo` requires a terminal for password prompt; silently fails with "a terminal is required" | Check `sudo -n true` first; if NEEDS-PASSWORD, escalate to user with an interactive command |
| Cloning main before PR merged | Dispatched agents to `git clone` main branch of ProjectHephaestus before install.sh PR merged | install.sh missing from main; agents found no script to run | Either merge the PR first, or clone the feature branch: `git clone -b feat/... <url>` |
| Python 3.7 on apollo | Dispatched installer agent to apollo (Python 3.7.3) | Python 3.10+ required; 3.7 is EOL and below minimum | Check `python3 --version` before dispatching; apollo needs `sudo apt-get install -y python3.10` first |
| git not pre-installed on athena/titan | Tried to clone ProjectHephaestus on athena and titan | Neither host had git installed; clone fails silently in BatchMode | Always check `which git` during probe step; if missing + sudo needs password, give user a manual command |

## Results & Parameters

### Tailnet Host Inventory (2026-04-28)

| Host | IP | Python | git | sudo | Result |
| ------ | ---- | -------- | ----- | ------ | -------- |
| aeolus | 100.65.107.65 | 3.12.3 | yes | NOPASSWD | DONE |
| apollo | 100.68.51.128 | 3.7.3 | yes | NOPASSWD | PARTIAL — Python 3.7 too old |
| artemis | 100.74.100.3 | 3.12.3 | yes | NEEDS-PASSWORD | PARTIAL — 16/30 ✓, Go/podman/cmake need sudo |
| athena | 100.124.17.101 | 3.12.3 | no | NEEDS-PASSWORD | FAIL — no git, sudo needs password |
| hephaestus | 100.122.194.113 | 3.12.3 | yes | NOPASSWD | DONE |
| hermes | 100.73.61.56 | 3.12.3 | yes | NOPASSWD | PARTIAL — 24/28 ✓, Go/templ need sudo |
| titan | 100.115.74.124 | 3.12.3 | no | NEEDS-PASSWORD | FAIL — no git, sudo needs password |

### Dependency Version Matrix

| Dependency | Minimum | Recommended | Install Method |
| ------------ | --------- | ------------- | ---------------- |
| Go | 1.23.0 | 1.23.4 | Official tarball → `/usr/local/go` |
| cmake | 3.20.0 | 3.28+ | `pip3 install cmake --break-system-packages` |
| nats-server | 2.10.0 | 2.10.21 | Native binary → `~/.local/bin` |
| nats CLI | 0.1.0 | 0.1.5 | zip from GitHub → `~/.local/bin` |
| Python | 3.10.0 | 3.11+ | System apt |
| pixi | any | latest | `curl -fsSL https://pixi.sh/install.sh \| bash` |
| templ | any | latest | `GOBIN=~/.local/bin go install github.com/a-h/templ/cmd/templ@latest` |
| gh CLI | any | latest | Official GitHub apt repo |

### Expected Output (all-pass scenario)

```
[PASS] git 2.39.5
[PASS] curl 7.88.1
[PASS] jq 1.6
[PASS] just 1.13.0
[PASS] gh 2.47.0
[PASS] tailscaled running
[PASS] python3 3.11.2
[PASS] pip3 24.0
[PASS] nats-py (installed)
[PASS] pixi 0.25.0
[PASS] go 1.23.4 (>= 1.23.0)
[PASS] templ (installed)
[PASS] nats-server 2.10.21 (>= 2.10.0)
[PASS] nats CLI 0.1.5
[PASS] podman 4.3.1
[PASS] podman socket running
[PASS] cmake 3.28.1 (>= 3.20.0)
[PASS] ninja 1.11.1
[PASS] conan 2.3.0
[PASS] ~/.local/bin in PATH
[PASS] /usr/local/go/bin in PATH

Summary: 21 passed, 0 failed, 0 warnings
```

### PATH additions required (add to ~/.bashrc or ~/.zshrc)

```bash
export PATH="$HOME/.local/bin:$PATH"
export PATH="/usr/local/go/bin:$PATH"
```

### Pre-Flight Checklist for SSH Fan-Out

Before dispatching installer agents to all Tailnet hosts:

```bash
# 1. Add host keys (prevents host key verification failures)
ssh-keyscan -H aeolus apollo artemis athena hephaestus hermes titan >> ~/.ssh/known_hosts

# 2. Probe reachability + Python version + git presence
for host in aeolus apollo artemis athena hephaestus hermes titan; do
  echo -n "$host: "
  ssh -o ConnectTimeout=6 -o BatchMode=yes "$host" \
    'echo OK && uname -m && python3 --version 2>/dev/null && which git 2>/dev/null || echo no-git' \
    2>&1 | tr '\n' ' '
  echo
done

# 3. Check sudo passwordless
for host in aeolus apollo artemis athena hephaestus hermes titan; do
  echo -n "$host sudo: "
  ssh -o ConnectTimeout=6 -o BatchMode=yes "$host" \
    'sudo -n true 2>&1 && echo NOPASSWD-OK || echo NEEDS-PASSWORD' 2>&1
done
```

Only dispatch agents to hosts where: Python >= 3.10, git is installed, and sudo is NOPASSWD-OK (or no sudo required). For the rest, provide interactive commands to the user.

## Verified On

| Project | Context | Details |
| --------- | --------- | --------- |
| ProjectHephaestus | PR #309 (2026-04-28) | install.sh bash -n syntax check passed; script ran clean on epimetheus; CI pending |
| Tailnet fan-out (2026-04-28) | 7-host parallel SSH deployment | 2 fully done (aeolus, hephaestus); 3 partial (artemis, hermes, apollo); 2 failed (athena, titan) |
