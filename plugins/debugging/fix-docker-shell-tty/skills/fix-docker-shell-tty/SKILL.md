---
name: fix-docker-shell-tty
description: "Fix Docker interactive shell failures caused by missing or incorrect TTY flags"
category: debugging
source: ProjectOdyssey
date: 2025-12-30
---

# Fix Docker Shell TTY

Fix interactive Docker shell commands that fail due to missing or incorrect TTY allocation flags.

## Overview

| Item | Details |
|------|---------|
| Date | 2025-12-30 |
| Objective | Fix `just shell` command failing to start interactive Docker shell |
| Outcome | Success - Added `-it` flags to enable proper TTY allocation |
| Duration | ~5 minutes |

## When to Use

- `docker compose exec` or `docker exec` fails for interactive shells
- Shell starts but input/output doesn't work
- justfile `shell` recipe produces errors or hangs
- Container shell exits immediately
- Error messages about TTY or terminal allocation

## Verified Workflow

### 1. Identify the Problem

Check for TTY-related flags in Docker commands:

```bash
# Look for -T flag (disables TTY - WRONG for interactive)
grep -n "\-T" justfile

# Look for missing -it flags
grep -n "docker.*exec" justfile
```

### 2. Understand TTY Flags

| Flag | Purpose | Use Case |
|------|---------|----------|
| `-T` | **Disable** pseudo-TTY | Non-interactive scripts, CI pipelines |
| `-t` | Allocate pseudo-TTY | Interactive terminal sessions |
| `-i` | Keep STDIN open | Interactive input |
| `-it` | Combined interactive TTY | Interactive shell sessions |

### 3. Apply the Fix

**Before (broken):**

```just
shell:
    @docker compose exec -T {{docker_service}} bash
```

**After (fixed):**

```just
shell:
    @docker compose exec -it {{docker_service}} bash
```

### 4. Verify the Fix

```bash
# Test interactive shell
just shell

# Should get interactive prompt, be able to type commands
# Ctrl+D or exit to leave
```

## Failed Attempts

| Attempt | Why Failed | Lesson |
|---------|-----------|--------|
| Using `-T` flag for shell | `-T` explicitly disables TTY allocation | `-T` is for non-interactive commands only |
| No flags at all | Works sometimes but unreliable | Always use `-it` for interactive shells |

## Results & Parameters

### The Fix

Changed justfile `shell` recipe from:

```just
shell:
    @docker compose exec -e USER_ID={{USER_ID}} -e GROUP_ID={{GROUP_ID}} -T {{docker_service}} bash
```

To:

```just
shell:
    @docker compose exec -it -e USER_ID={{USER_ID}} -e GROUP_ID={{GROUP_ID}} {{docker_service}} bash
```

### Key Insight

The `-T` flag was present because it's appropriate for **non-interactive** commands (like in the `_run` helper). But for the `shell` recipe specifically, interactive TTY is required.

**Rule of thumb:**

- **Interactive commands** (shell, debugging): Use `-it`
- **Non-interactive commands** (running scripts, CI): Use `-T` or no flags

## Docker Exec Flag Reference

```bash
# Interactive shell (what you usually want)
docker compose exec -it <service> bash

# Non-interactive script execution
docker compose exec -T <service> ./script.sh

# Non-interactive with environment variables
docker compose exec -T -e VAR=value <service> command

# Interactive with environment variables
docker compose exec -it -e VAR=value <service> bash
```

## Related Patterns

### Justfile Non-Interactive Helper

For non-interactive commands, `-T` is correct:

```just
[private]
_run cmd:
    @docker compose exec -T {{docker_service}} bash -c "{{cmd}}"
```

### Docker Run vs Exec

Same principle applies to `docker run`:

```bash
# Interactive
docker run -it --rm image bash

# Non-interactive
docker run --rm image ./script.sh
```

## Verification Checklist

- [ ] Identified `-T` flag in interactive shell command
- [ ] Changed to `-it` flags
- [ ] Tested `just shell` works interactively
- [ ] Verified other Docker commands still work

## References

- Docker exec reference: <https://docs.docker.com/engine/reference/commandline/exec/>
- Docker compose exec: <https://docs.docker.com/compose/reference/exec/>
- PR #2961: <https://github.com/mvillmow/ProjectOdyssey/pull/2961>
