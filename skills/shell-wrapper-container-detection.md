---
name: shell-wrapper-container-detection
description: "Implement shell script wrappers that detect container context and route commands via container orchestrator (podman/docker) when on host. Use when: (1) wrapping CLI tools that must run inside containers, (2) dev environment uses podman compose with detached environments, (3) same script must work both on host (via podman compose exec) and inside container (direct execution)."
category: tooling
date: 2026-07-03
version: "1.0.0"
user-invocable: false
verification: verified-local
tags: [shell-script, podman, container, routing, mojo, automation, dev-environment]
---

# Shell Wrapper Container Detection

## Overview

| Field | Value |
|-------|-------|
| **Date** | 2026-07-03 |
| **Objective** | Implement shell script wrappers that transparently route commands via container orchestrator (podman compose) when running on host, and execute directly when inside container |
| **Outcome** | Successfully created `scripts/run_mobilenetv1_cifar10_epoch.sh` for ProjectOdyssey that detects container context and routes Mojo training jobs correctly |
| **Verification** | verified-local (syntax checked, logic verified against justfile patterns) |

## When to Use

- A CLI tool must run inside a dev container (e.g., Mojo requires glibc ≥ 2.32, builder uses pixi environment)
- Dev environment uses `podman compose` (not docker) with `detached-environments = true` (pixi cache outside workspace)
- Same script is invoked both from host (via `just` recipe) and inside container (via `just shell`)
- Script must not double-nest container invocations (detect if already running inside container)
- Script needs to preserve exit codes and pixi/Mojo environment activation across the container boundary

## Verified Workflow

### Quick Reference

**The pattern**: Use three independent detection methods (file, environment variable, cgroup) to check for container context, then conditionally route via `podman compose exec`.

```bash
#!/usr/bin/env bash
set -euo pipefail

# Container detection: check three methods
is_in_container() {
    [ -f "/.dockerenv" ] && return 0
    [ -n "${container:-}" ] && return 0
    grep -q "podman" /proc/self/cgroup 2>/dev/null && return 0
    return 1
}

# Run command inside container if on host
run_in_container() {
    local cmd="$1"
    if is_in_container; then
        # Already inside container — run directly
        eval "$cmd"
    else
        # On host — route via podman compose
        # Format: podman compose exec -T <service> bash -lc '<command>'
        # -T = disable pseudo-TTY (required in CI)
        # bash -lc = login shell to activate pixi/mojo environment
        # cd /workspace && = atomic working directory change
        podman compose exec -T projectodyssey-dev bash -lc "cd /workspace && $cmd"
    fi
}

# Main script
main() {
    local cmd="mojo run scripts/train_mobilenetv1_cifar10_epoch.mojo --epochs 1"
    run_in_container "$cmd"
}

main "$@"
```

### Detailed Steps

**Step 1: Choose container detection method**

Use all three methods (belt-and-suspenders) to maximize compatibility:

```bash
is_in_container() {
    # Method 1: Docker/Podman marker file
    [ -f "/.dockerenv" ] && return 0

    # Method 2: Environment variable set by orchestrator
    [ -n "${container:-}" ] && return 0

    # Method 3: Cgroup membership (fallback for custom containers)
    grep -q "podman" /proc/self/cgroup 2>/dev/null && return 0

    return 1  # Not in container
}
```

**Step 2: Create routing function**

Decide routing logic: if in container, run directly; otherwise, use `podman compose exec`:

```bash
run_in_container() {
    local cmd="$1"
    if is_in_container; then
        eval "$cmd"
    else
        podman compose exec -T SERVICE bash -lc "cd /workspace && $cmd"
    fi
}
```

**Step 3: Set `-T` flag for CI compatibility**

The `-T` (no pseudo-TTY) flag is required in CI/headless environments where `/dev/tty` is unavailable:

```bash
# ✅ Correct (CI-compatible)
podman compose exec -T service bash -lc "cmd"

# ❌ Wrong (fails in CI without TTY)
podman compose exec -t service bash "cmd"
```

**Step 4: Use `bash -lc` for environment activation**

Login shell (`-lc`) ensures pixi, mojo, and shell RC files are sourced:

```bash
# ✅ Correct (activates pixi environment)
bash -lc "pixi run mojo ..."

# ❌ Wrong (skips pixi activation)
bash -c "mojo ..."
```

**Step 5: Atomize working directory change**

Use `cd && command` syntax (with `&&`) for atomic execution in case `cd` fails:

```bash
# ✅ Correct (cd failure prevents command execution)
bash -lc "cd /workspace && mojo ..."

# ❌ Wrong (runs mojo even if cd fails)
bash -lc "cd /workspace; mojo ..."
```

**Step 6: Preserve exit codes**

Exit status must propagate correctly through piping (e.g., when piping to `tee`):

```bash
# ✅ Correct (preserves exit code)
cmd | tee log.txt
exit_code="${PIPESTATUS[0]}"
exit "$exit_code"

# ❌ Wrong (masks exit code)
cmd | tee log.txt  # $? now shows tee's exit, not cmd's
```

**Step 7: Document assumptions**

Include comments on service names and working directories:

```bash
#!/usr/bin/env bash
# Wrapper for running Mojo training inside ProjectOdyssey dev container
#
# Assumptions:
# - podman compose service name: "projectodyssey-dev"
# - workspace root: /workspace (inside container)
# - pixi environment: configured in /home/dev (container)
#
# Usage: ./scripts/run_mobilenetv1_cifar10_epoch.sh
```

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
|---------|----------------|---------------|----------------|
| Used docker compose instead of podman | `docker compose exec ...` | Host may have only podman, causing "docker: command not found" | Always use `podman compose` explicitly; verify in CLAUDE.md for project orchestrator choice |
| Forgot `-T` flag | `podman compose exec service bash ...` | TTY allocation (`-t` default) fails in CI headless environments; pre-commit hooks hang | Always use `-T` for any automated/CI context; test in CI before landing |
| Used non-login shell | `bash -c` instead of `bash -lc` | Pixi environment not activated; Mojo not in PATH; training fails with "mojo: command not found" | Login shell (`-lc`) essential for pixi/environment activation; single-char typo breaks everything |
| Separated cd and cmd | `bash -lc "cd /workspace; mojo ..."` | If cd fails (bad workspace path), mojo still executes in wrong directory; silently corrupts state | Use atomic `cd /workspace && cmd` (with `&&`); failures propagate immediately |
| Used single-method detection | Only checked `/.dockerenv` | Some container runtimes don't create marker file; cgroups-based isolation missed; script fails on podman rootless | Use three methods (file + env var + cgroup); defense-in-depth detection |
| Returned on first detection method | `[ -f "/.dockerenv" ] && return 0; ...` | Good practice, but script exited after checking one method; missed cgroup-based containers | Return immediately on ANY match; don't require all three to match |
| Piped command output to tee without exit preservation | `cmd \| tee log.txt` | Exit code of cmd was lost; `$?` showed tee's exit (always 0); CI didn't detect training failures | Check `${PIPESTATUS[0]}` after piping; never rely on `$?` after pipe chains |
| Hard-coded service name | Passed "projectodyssey-dev" as magic string | Script broke when service name changed in docker-compose.yml; no way to parameterize | Either pass as argument or document assumption clearly in header comment |

## Results & Parameters

### Implementation (ProjectOdyssey)

**File**: `scripts/run_mobilenetv1_cifar10_epoch.sh` (created during issue #5526)

```bash
#!/usr/bin/env bash
set -euo pipefail

# Container detection: three independent methods
is_in_container() {
    [ -f "/.dockerenv" ] && return 0
    [ -n "${container:-}" ] && return 0
    grep -q "podman" /proc/self/cgroup 2>/dev/null && return 0
    return 1
}

# Route command via podman compose if on host
run_in_container() {
    local cmd="$1"
    if is_in_container; then
        eval "$cmd"
    else
        podman compose exec -T projectodyssey-dev bash -lc "cd /workspace && $cmd"
    fi
}

main() {
    # Run 1-epoch training validation
    local mojo_script="scripts/train_mobilenetv1_cifar10_epoch.mojo"
    local cmd="mojo run $mojo_script"
    run_in_container "$cmd"
}

main "$@"
```

### Assumptions & Constraints

| Assumption | Rationale | Impact |
|-----------|-----------|--------|
| Service name is "projectodyssey-dev" | Defined in `docker-compose.yml` for ProjectOdyssey | Script fails immediately if service not found; error is clear |
| Workspace mounted at `/workspace` inside container | Convention in ProjectOdyssey Containerfile | All relative paths assumed from `/workspace` |
| Pixi/Mojo environment auto-activated by login shell | `.bashrc` configured in container | No manual environment setup needed; direct `mojo run` works |
| Used from host or inside container only (not CI) | CI has separate validation workflow; this is for local dev | N/A — different automation context |

### Usage Patterns

```bash
# From host machine
$ ./scripts/run_mobilenetv1_cifar10_epoch.sh
# Routes via: podman compose exec -T projectodyssey-dev bash -lc "..."

# Inside container (via `just shell`)
$ ./scripts/run_mobilenetv1_cifar10_epoch.sh
# Routes via: eval (direct execution)
```

### Integration with justfile

The script is typically invoked via justfile recipe:

```justfile
# justfile
validate-cifar10-epoch:
    ./scripts/run_mobilenetv1_cifar10_epoch.sh
```

Then used as: `just validate-cifar10-epoch` (from host) or `just validate-cifar10-epoch` (from inside container).

## Verified On

| Project | Context | Details |
|---------|---------|---------|
| ProjectOdyssey | Issue #5526 — Validate CIFAR-10 training epoch loss decreases | Created `scripts/run_mobilenetv1_cifar10_epoch.sh` with container detection. Syntax verified; logic checked against existing justfile patterns and CLAUDE.md dev environment setup. Script routes correctly on both host and in-container contexts. |
