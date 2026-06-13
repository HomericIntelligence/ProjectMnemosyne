---
name: argparse-version-action-crash-scope
description: "Identify the true crash scope when an issue blames --version for a script crash. Use when: (1) an issue claims --version flag causes a crash, (2) a script uses argparse action='version' and also accesses os.environ, (3) debugging KeyError or missing env var crashes in CLI scripts."
category: debugging
date: 2026-06-13
version: "1.0.0"
user-invocable: false
verification: unverified
tags: []
---

# Argparse Version Action Crash Scope

## Overview

| Field | Value |
|-------|-------|
| **Date** | 2026-06-13 |
| **Objective** | Correctly identify which invocations trigger a crash when a script uses argparse action="version" and accesses os.environ |
| **Outcome** | Approach documented; not yet validated end-to-end |
| **Verification** | unverified |

## When to Use

- An issue reports that running `script --version` causes a crash
- A script uses `parser.add_argument("--version", action="version", version=...)` AND accesses `os.environ["SOME_VAR"]` at module or script level
- Debugging `KeyError` or `SystemExit` in a CLI script's entry point
- Verifying the actual crash scope before planning a fix

## Verified Workflow

> **Warning:** This workflow has not been validated end-to-end. Treat as a hypothesis until CI confirms.

### Quick Reference

```python
# argparse action="version" behavior:
# parser.parse_args(["--version"]) → prints version → sys.exit(0)
# This exits BEFORE any code after parse_args() runs.

# Crash scope for os.environ access AFTER parse_args():
# - `script --version`  → NO crash (sys.exit(0) before env access)
# - `script --help`     → NO crash (sys.exit(0) before env access)
# - `script` (no args)  → CRASH if SOME_VAR not in os.environ
# - `script --flag val` → CRASH if SOME_VAR not in os.environ
```

```bash
# Quickly verify argparse version behavior in Python:
python3 -c "
import argparse, sys
p = argparse.ArgumentParser()
p.add_argument('--version', action='version', version='1.0')
print('Calling parse_args with --version...')
p.parse_args(['--version'])
print('This line never runs')
"
# Output: 1.0  (then exits with code 0, never reaches print)
```

### Detailed Steps

1. **Read the issue framing carefully**: If an issue says "`--version` causes a crash", question the framing before accepting it as fact.

2. **Locate the argparse setup in the script**: Find `add_argument("--version", action="version", ...)`. This is the critical pattern — `action="version"` makes `parse_args()` call `sys.exit(0)` immediately when `--version` is passed.

3. **Locate the env var access**: Find `os.environ["VAR"]` or `os.environ.get("VAR")` calls. Note whether they are:
   - **Before** `parse_args()` → can crash on ANY invocation including `--version`
   - **After** `parse_args()` → `--version` safely exits before reaching them

4. **Determine true crash scope**:
   - If env access is AFTER `parse_args()`: `--version` and `--help` are SAFE; crash happens on normal invocations without the env var
   - If env access is BEFORE `parse_args()`: ALL invocations crash if env var missing

5. **Verify independently**: Run the argparse version behavior check (Quick Reference above) to confirm understanding before writing the fix.

6. **Fix accordingly**: The fix is to guard the env var access, NOT to change the `--version` handling:
   ```python
   # Instead of:
   REPO = os.environ["GITHUB_REPOSITORY"]  # KeyError if not set

   # Use:
   REPO = os.environ.get("GITHUB_REPOSITORY")
   if REPO is None:
       print("Error: GITHUB_REPOSITORY environment variable not set", file=sys.stderr)
       sys.exit(1)
   ```

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
|---------|----------------|---------------|----------------|
| Accept issue framing at face value | Assumed `--version` invocation was the crash trigger | argparse `action="version"` exits before any env var access — `--version` is actually safe | Always verify argparse action="version" behavior independently; `sys.exit(0)` in parse_args means post-parse code never runs |
| Fix `--version` handling | Considered modifying version display to guard against crash | `--version` was never the problem; it safely exits before the crash site | The real fix is guarding the env var access that runs on normal (non-version, non-help) invocations |

## Results & Parameters

**Key argparse facts**:
- `action="version"`: calls `sys.exit(0)` inside `parse_args()`, before returning
- `action="help"` (default `-h`/`--help`): same — `sys.exit(0)` inside `parse_args()`
- Any code after `args = parser.parse_args()` is unreachable when `--version` or `--help` is passed

**Crash trigger pattern**:
```python
# This script crashes ONLY on normal invocations (not --version or --help)
def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--version", action="version", version="1.0")
    args = parser.parse_args()          # sys.exit(0) here if --version/--help
    repo = os.environ["GITHUB_REPOSITORY"]  # KeyError here on normal invocation
```

**Correct fix location**: Guard `os.environ` access, not the `--version` argument.

## Verified On

| Project | Context | Details |
|---------|---------|---------|
| ProjectHephaestus | Issue #1300 (severity_label.py GITHUB_REPOSITORY KeyError) | Issue blamed --version; actual crash was on normal invocations without env var |
