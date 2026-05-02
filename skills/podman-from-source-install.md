---
name: podman-from-source-install
description: 'Build and install full Podman 4.0+ from source on Debian/PureOS. Use
  when: apt repos only ship 3.x, GitHub static binary is podman-remote not full podman,
  or host GLIBC < 2.32 requires a container engine.'
category: tooling
date: 2026-03-19
version: 1.0.0
user-invocable: false
---
## Overview

| Property | Value |
| ---------- | ------- |
| **Goal** | Install working full Podman 4.0+ on Debian 11 / PureOS 10 |
| **Host** | PureOS 10 (Byzantium), Debian 11 base, GLIBC 2.31 |
| **Problem** | Kubic apt repos max at 3.4.2; GitHub releases ship podman-remote only |
| **Solution** | Build full podman from source using Go 1.24+ |
| **Install target (root)** | `/usr/local/bin/podman` |
| **Install target (user)** | `~/.local/bin/podman` |
| **Time** | ~10-15 minutes total (Go download + podman build) |

## When to Use

- Host has GLIBC 2.31 and needs Podman 4.0+ to run Mojo containers
- `apt-get install podman` gives version 3.x (Kubic Debian_11 repo caps at 3.4.2)
- GitHub static binary (`podman-remote-static-linux_amd64.tar.gz`) was installed but
  fails with "cannot connect to Podman socket" — it is `podman-remote`, not full podman
- `podman info` fails with socket error despite `podman --version` showing 4.0+

## Verified Workflow

### Quick Reference

```bash
# One-shot install (run as root for global install)
sudo bash scripts/install-podman.sh

# Then build the dev image
pixi run just podman-build

# Then run tests
pixi run just test-mojo
```

### Step 1 — Detect install context

```bash
if [ "$(id -u)" -eq 0 ]; then
    INSTALL_DIR="/usr/local/bin"
    BUILD_DIR="/usr/local/src"
else
    INSTALL_DIR="${HOME}/.local/bin"
    BUILD_DIR="${HOME}/.local/src"
fi
```

**Critical**: check `$INSTALL_DIR/podman` directly, not `which podman`. The `which` result
may point to a stale `podman-remote` binary from a previous failed attempt.

### Step 2 — Early exit check (full podman only)

Version number alone is insufficient — `podman-remote` also reports 5.x. The only
reliable test is `podman info` succeeding without a socket:

```bash
if [ -x "$INSTALL_DIR/podman" ]; then
    major=$("$INSTALL_DIR/podman" --version | grep -oP '\d+' | head -1)
    if [ "$major" -ge 4 ] && "$INSTALL_DIR/podman" info &>/dev/null; then
        echo "Already installed — nothing to do"
        exit 0
    elif [ "$major" -ge 4 ]; then
        echo "podman-remote found — removing and rebuilding"
        rm -f "$INSTALL_DIR/podman"
    fi
fi
```

### Step 3 — Resolve versions

```bash
PODMAN_VERSION=$(curl -fsSL "https://api.github.com/repos/containers/podman/releases/latest" \
    | grep '"tag_name"' | grep -oP '\d+\.\d+\.\d+')

GO_VERSION=$(curl -fsSL "https://raw.githubusercontent.com/containers/podman/v${PODMAN_VERSION}/go.mod" \
    | grep "^go " | grep -oP '\d+\.\d+(\.\d+)?')
```

As of 2026-03-19: Podman 5.8.1 requires Go 1.24.2.

### Step 4 — Install Go (no apt needed)

```bash
GO_INSTALL_DIR="${BUILD_DIR}/go-${GO_VERSION}"
GO_URL="https://go.dev/dl/go${GO_VERSION}.linux-amd64.tar.gz"
curl -fsSL "$GO_URL" -o /tmp/go.tar.gz
mkdir -p "$GO_INSTALL_DIR"
tar -xz -C "$GO_INSTALL_DIR" -f /tmp/go.tar.gz --strip-components=1
export PATH="${GO_INSTALL_DIR}/bin:${PATH}"
```

Idempotent: skip download if `$GO_INSTALL_DIR/bin/go` already exists at correct version.

### Step 5 — Install build dependencies

```bash
sudo apt-get install -y \
    libgpgme-dev \
    libassuan-dev \
    libbtrfs-dev \
    libdevmapper-dev \
    libseccomp-dev \
    pkg-config \
    iptables \
    slirp4netns \
    fuse-overlayfs \
    containernetworking-plugins
```

**Critical**: `libseccomp-dev` is required for the `seccomp` build tag. Missing it produces:
`Package libseccomp was not found in the pkg-config search path`.

### Step 6 — Clone and build

```bash
git clone --depth=1 --branch "v${PODMAN_VERSION}" \
    https://github.com/containers/podman.git "$BUILD_DIR/podman-${PODMAN_VERSION}"

cd "$BUILD_DIR/podman-${PODMAN_VERSION}"
make GOFLAGS="-trimpath" \
    CGO_ENABLED=1 \
    BUILDTAGS="exclude_graphdriver_devicemapper selinux seccomp" \
    binaries
```

Idempotent: skip clone if source directory already exists.

### Step 7 — Install and verify

```bash
cp bin/podman "$INSTALL_DIR/podman"
chmod 755 "$INSTALL_DIR/podman"

# Verify it's full podman (not remote)
"$INSTALL_DIR/podman" info
```

### Justfile `_run` helper — detect working podman

Version check alone is insufficient. Add `podman info` to the condition:

```just
elif command -v podman &>/dev/null && \
    [ "$(podman --version | grep -oP '\d+' | head -1)" -ge 4 ] 2>/dev/null && \
    podman info &>/dev/null; then
    podman run --rm --userns=keep-id ...
```

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
| --------- | ---------------- | --------------- | ---------------- |
| GitHub static binary | Downloaded `podman-remote-static-linux_amd64.tar.gz` from GitHub releases | It is `podman-remote`, not full podman — requires a running podman socket | GitHub releases only ship `podman-remote`; full podman must be built from source |
| Kubic apt repo (unstable, Debian_11) | Added `devel:/kubic:/libcontainers:/unstable/Debian_11` repo | Repo returns 404 for Debian 11 | Only `stable` Kubic repo exists for Debian 11 |
| Kubic apt repo (stable, Debian_11) | Added `devel:/kubic:/libcontainers:/stable/Debian_11` repo | Only ships 3.4.2 — too old | Kubic repos cap at 3.4.2 for Debian 11; no 4.x available |
| `podman machine init` | Ran after installing podman-remote 5.8.1 | Requires `qemu-img` not present; also wrong approach for rootless containers | `podman machine` is for macOS/Windows VM wrapping; Linux uses rootless natively |
| `which podman` for early-exit check | Checked `podman --version` via PATH | PATH contained stale `podman-remote` binary that reported 5.8.1 but failed `podman info` | Check the specific install path, not whatever PATH resolves to |
| Early-exit via `--help` subcommand grep | Grep for `run\|build\|pull` in `podman --help` to detect full vs remote | `podman-remote --help` also lists these subcommands | `podman info` without a socket is the only reliable full-vs-remote test |
| `sudo install-podman.sh` (old version) | Ran script as root without root-aware path logic | Script used `$HOME` which resolved to `/root`, installing to `/root/.local/bin` instead of `/usr/local/bin` | Scripts run as root must detect `id -u` and install to `/usr/local/bin` globally |
| Missing `libseccomp-dev` in build deps | Built without libseccomp-dev | `pkg-config` couldn't find `libseccomp` — build failed | Always include `libseccomp-dev` in podman build dependencies |

## Results & Parameters

```bash
# Versions confirmed working (2026-03-19)
Podman:  5.8.1
Go:      1.24.2
OS:      PureOS 10 (Byzantium) / Debian 11 base
GLIBC:   2.31 (host — Mojo still needs container)

# Build time: ~10 minutes on first run
# Idempotent: safe to re-run, skips completed steps

# Key build flags
BUILDTAGS="exclude_graphdriver_devicemapper selinux seccomp"
CGO_ENABLED=1
GOFLAGS="-trimpath"
```
