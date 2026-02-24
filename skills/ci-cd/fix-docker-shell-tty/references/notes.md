# Fix Docker Shell TTY - Session Notes

## Raw Session Details

**Date**: 2025-12-30
**Source**: ProjectOdyssey justfile debugging session

## Problem Statement

User reported `just shell` command was creating an error and not running correctly.

## Investigation

1. Read `/home/mvillmow/ProjectOdyssey/justfile`
2. Found `shell` recipe at line 280-281:
   ```just
   shell:
       @docker compose exec -e USER_ID={{USER_ID}} -e GROUP_ID={{GROUP_ID}} -T {{docker_service}} bash
   ```
3. Identified `-T` flag as the culprit

## Root Cause Analysis

The `-T` flag in `docker compose exec` **disables pseudo-TTY allocation**. This is the opposite of what's needed for an interactive shell session.

For interactive shells, you need:
- `-i`: Keep STDIN open even if not attached
- `-t`: Allocate a pseudo-TTY

Combined as `-it` for interactive terminal sessions.

## The Fix

Changed from:
```
-T {{docker_service}}
```

To:
```
-it {{docker_service}}
```

## Context: Why -T Existed

The justfile has a `_run` helper function that uses `-T`:

```just
[private]
_run cmd:
    @docker compose exec -T {{docker_service}} bash -c "{{cmd}}"
```

This is **correct** for `_run` because it executes non-interactive commands. The `-T` prevents issues with automated/scripted command execution.

However, the `shell` recipe was likely copy-pasted from `_run` without adjusting the flags for interactive use.

## PR Details

- Branch: `fix-docker-shell-tty`
- PR: https://github.com/mvillmow/ProjectOdyssey/pull/2961
- Single file change: `justfile`

## Commit Message

```
fix(justfile): add -it flags to shell recipe for interactive TTY

The shell recipe was missing TTY allocation flags, causing interactive
shell sessions to fail. Added -it flags to enable proper interactive
terminal support.
```
