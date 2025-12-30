---
name: shell-recovery-patterns
description: "TRIGGER: Shell commands returning exit code 1 with no output, bash unresponsive after git worktree removal"
category: tooling
source: ProjectOdyssey
date: 2025-12-29
---

# Shell Recovery Patterns

Patterns for recovering from corrupted shell sessions, especially after git worktree operations that delete the shell's current working directory.

## Overview

| Item | Details |
|------|---------|
| Date | 2025-12-29 |
| Objective | Recover from shell corruption after worktree removal |
| Outcome | Partial - identified root cause and workarounds |

## When to Use

- All bash commands return exit code 1 with empty output
- Shell becomes unresponsive after git worktree remove
- Even simple commands like `echo "test"` or `/bin/true` fail
- Background shells and subagents also fail with same symptoms
- Glob/Read/Write tools still work but Bash doesn't

## Verified Workflow

### Detection Pattern

1. **Symptom recognition**: Every bash command returns exit code 1 with no output
2. **Verification test**: Even `/bin/true` fails
3. **Root cause**: Shell's current working directory was deleted

### Safe Worktree Removal

**Before removing a worktree:**

```bash
# 1. Ensure you're NOT in the worktree directory
cd /path/to/main/repo  # Explicit cd to main repo first

# 2. Verify current directory is NOT inside worktrees/
pwd
# Should show: /path/to/main/repo (not /path/to/main/repo/worktrees/*)

# 3. Then remove worktree
git worktree remove path/to/worktree
git worktree prune
```

### Recovery Options

1. **Wait for session reset**: Starting a new conversation resets the shell
2. **Use file operations**: Glob, Read, Write tools still work
3. **Document for manual execution**: Write out bash commands for user to run

### Workaround When Shell is Broken

```python
# These tools still work when shell is broken:
Glob("**/target_file")           # Find files
Read("/absolute/path/to/file")   # Read files
Write("/path/to/file", content)  # Write files

# Document commands for user to execute manually
```

## Failed Attempts

| Attempt | Why Failed | Lesson |
|---------|-----------|--------|
| `cd /valid/path && command` | Shell can't execute when cwd invalid | cd doesn't help |
| Subshell `(cd /path && cmd)` | Parent shell corruption affects subshells | Isolation doesn't work |
| Background shell | Background shells inherit broken environment | Same session problem |
| Subagent with Bash | All agents share same shell session | No agent isolation |
| `/bin/bash -c 'command'` | New bash inherits invalid cwd | Explicit bash doesn't help |
| `exec bash` | Can't exec when shell is broken | exec fails too |
| Setting OLDPWD | Env vars don't fix getcwd failure | Not a path issue |

## Results & Parameters

### Root Cause Analysis

When a git worktree is removed while the shell's current working directory is inside that worktree (or the worktrees/ directory):

1. The shell can't execute `getcwd()` - directory no longer exists
2. Every command implicitly tries to resolve paths relative to cwd
3. Even absolute path commands fail because shell initialization fails

### Prevention Checklist

```yaml
before_worktree_removal:
  - verify_cwd_is_main_repo: true
  - run_pwd_check: true
  - list_worktrees_first: true

if_working_in_worktree:
  - exit_worktree_first: true
  - cd_to_main_repo: true
```

### Recovery Checklist

```yaml
when_shell_broken:
  - verify_glob_works: true      # Glob doesn't depend on shell cwd
  - document_pending_commands: true
  - start_new_session: true      # Only reliable fix
  - verify_with_pwd_and_echo: true
```

## References

- Source: ProjectOdyssey issue #2784 analysis session
- Related: Git worktree management, shell environment recovery
- Context: Occurred during cleanup of stale worktrees after PR merge
