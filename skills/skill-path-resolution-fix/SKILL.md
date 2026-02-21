# Skill: Skill Path Resolution Fix

## Overview

| Field | Value |
|-------|-------|
| Date | 2026-02-21 |
| Issue | #801 |
| PR | #906 |
| Category | tooling |
| Objective | Fix skill documentation that used relative `bash scripts/...` invocations that only work when the caller's CWD is the skill directory |
| Outcome | Success — path-independent invocations in SKILL.md, self-location idiom in shell script, synced to ProjectMnemosyne |

## When to Use

Trigger this skill when:

- A SKILL.md Quick Reference uses `bash scripts/<name>.sh` (relative path)
- A shell script inside a skill's `scripts/` subdirectory uses relative paths internally
- A skill was added to `tests/claude-code/shared/skills/` but the docs only work from inside that directory
- You get errors like `bash: scripts/preflight_check.sh: No such file or directory` when running from a different CWD
- Syncing a skill between ProjectScylla and ProjectMnemosyne where invocation patterns differ

## Verified Workflow

### 1. Identify the anti-pattern

```bash
# Find all relative script invocations in SKILL.md files
grep -rn "bash scripts/" tests/claude-code/shared/skills/
grep -rn "bash scripts/" build/ProjectMnemosyne/plugins/
```

Look for:
- `bash scripts/<name>.sh` — relative path, CWD-dependent
- `./scripts/<name>.sh` — same problem
- Any invocation without an absolute or `<skill-dir>`-relative path

### 2. Fix the shell script (add self-location idiom)

Add at the top of the script (after shebang and comments, before `set -`):

```bash
# Self-locating: works regardless of caller's CWD
# shellcheck disable=SC2034
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
```

**Why `# shellcheck disable=SC2034`**: ShellCheck flags `SCRIPT_DIR` as unused if the
script doesn't reference it internally (e.g., when it only calls `gh`/`git`). The variable
is intentionally kept as a documented idiom and for future-proofing. The disable comment
suppresses the false positive without skipping all ShellCheck checks.

**Why after shebang/comments, before `set -`**: Placing `SCRIPT_DIR` before `set -uo pipefail`
ensures the location is captured before strict mode; the subshell `cd` doesn't trigger `pipefail`.

Also update the Usage comment in the script header:

```bash
# Usage:
#   bash /path/to/scripts/<name>.sh <args>
#   bash "$(dirname "${BASH_SOURCE[0]}")/<name>.sh" <args>
```

### 3. Fix SKILL.md Quick Reference

Replace the relative invocation with a `<skill-dir>` placeholder pattern:

**Before:**
```bash
bash scripts/preflight_check.sh <issue>
```

**After:**
```bash
# Replace <skill-dir> with the absolute path to this skill directory
bash <skill-dir>/scripts/preflight_check.sh <issue>
```

Add a Note callout immediately before the code block:

```markdown
> **Note:** `<skill-dir>` is the absolute path to this skill's directory.
> Resolve it with: `SKILL_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"`
> or use the skill's installed path directly, e.g.:
> `tests/claude-code/shared/skills/github/gh-implement-issue` (ProjectScylla)
```

Apply the same fix to every occurrence in the file (Quick Reference AND Workflow section).

### 4. Verify the fix

```bash
# Run from a DIFFERENT directory than the skill dir
bash tests/claude-code/shared/skills/github/gh-implement-issue/scripts/preflight_check.sh <issue>

# Run with absolute path
bash /absolute/path/to/scripts/preflight_check.sh <issue>

# Confirm anti-pattern is gone
grep -n "bash scripts/" tests/claude-code/shared/skills/github/gh-implement-issue/SKILL.md
# Should return nothing
```

### 5. Sync to ProjectMnemosyne

Apply the same Quick Reference fix to the Mnemosyne SKILL.md:

```bash
# Check what's in Mnemosyne
cat build/ProjectMnemosyne/plugins/tooling/gh-implement-issue/skills/gh-implement-issue/SKILL.md

# Apply the same Note callout and <skill-dir> pattern
# Add Pre-Flight Check Results table, updated Error Handling rows, references
```

Update `references/notes.md` with:
- Canonical source location of the script in ProjectScylla
- How to resolve `<skill-dir>` at runtime
- Sync history entry with date, changes, and issue number

Commit Mnemosyne on its own branch:

```bash
git -C build/ProjectMnemosyne checkout -b skill/tooling/gh-implement-issue-preflight-sync
git -C build/ProjectMnemosyne add plugins/tooling/gh-implement-issue/
git -C build/ProjectMnemosyne commit -m "fix(skills): Sync preflight_check.sh sections into gh-implement-issue skill"
git -C build/ProjectMnemosyne push -u origin skill/tooling/gh-implement-issue-preflight-sync
cd build/ProjectMnemosyne && gh pr create --title "..." --body "..."
```

### 6. Commit and PR (ProjectScylla)

```bash
git add tests/claude-code/shared/skills/github/gh-implement-issue/SKILL.md \
        tests/claude-code/shared/skills/github/gh-implement-issue/scripts/preflight_check.sh
git commit -m "fix(skills): Fix preflight_check.sh path resolution in gh-implement-issue skill"
git push -u origin <branch>
gh pr create --title "..." --body "Closes #<issue>"
gh pr merge --auto --rebase <pr-number>
```

## Failed Attempts

| Attempt | Why Failed | Lesson |
|---------|------------|--------|
| Add `SCRIPT_DIR` without `# shellcheck disable=SC2034` | ShellCheck hook failed with `SC2034: SCRIPT_DIR appears unused` | Always add the disable comment when `SCRIPT_DIR` is documenting the idiom but not used internally — it's a false positive that will block commits |
| Reading Mnemosyne files via worktree `Read` tool | Worktree (`/home/mvillmow/ProjectScylla/.worktrees/issue-801/`) doesn't include `build/` directory — `File does not exist` | Use absolute paths pointing to the main repo's `build/ProjectMnemosyne/`, not the worktree path |
| Looking for `build/` inside the worktree | Worktrees only contain the checked-out branch files; `build/` is gitignored/excluded | Always check `ls /home/mvillmow/ProjectScylla/build/` directly, not the worktree path |

## Results & Parameters

### Shell Script Self-Location Template

```bash
#!/usr/bin/env bash
# Usage:
#   bash /path/to/scripts/<name>.sh <args>
#   bash "$(dirname "${BASH_SOURCE[0]}")/<name>.sh" <args>

# Self-locating: works regardless of caller's CWD
# shellcheck disable=SC2034
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

set -uo pipefail
```

### SKILL.md Quick Reference Template

```markdown
> **Note:** `<skill-dir>` is the absolute path to this skill's directory.
> Resolve it with: `SKILL_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"`
> or use the skill's installed path directly.

```bash
# Replace <skill-dir> with the absolute path to this skill directory
bash <skill-dir>/scripts/<name>.sh <args>
```
```

### Mnemosyne references/notes.md Template

```markdown
## Canonical Source

`<script>.sh` lives in the canonical ProjectScylla location:

```
tests/claude-code/shared/skills/<category>/<skill-name>/scripts/<script>.sh
```

## Skill Directory Resolution

The `<skill-dir>` placeholder resolves to the absolute path of the skill directory.
Resolve it at runtime with:

```bash
SKILL_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
bash "${SKILL_DIR}/scripts/<script>.sh" <args>
```

## Sync History

- <date>: <changes summary> (issue #<number>)
```

## References

- Issue #801 — original path resolution fix for `preflight_check.sh`
- ShellCheck SC2034: https://www.shellcheck.net/wiki/SC2034
- `BASH_SOURCE[0]` pattern: standard bash self-location idiom
