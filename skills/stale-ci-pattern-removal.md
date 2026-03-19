---
name: stale-ci-pattern-removal
description: 'Remove stale file references from CI workflow test pattern strings after
  test files are deleted. Use when: (1) a test file was deleted but still appears
  in a GitHub Actions workflow pattern string, (2) closing a cleanup issue where the
  only remaining work is a dangling workflow reference.'
category: ci-cd
date: 2026-03-07
version: 1.0.0
user-invocable: false
---
## Overview

| Field | Value |
|-------|-------|
| **Skill** | stale-ci-pattern-removal |
| **Category** | ci-cd |
| **Complexity** | Low |
| **Risk** | Low |
| **Time** | < 5 minutes |

When a test file is deleted from the codebase, its filename often lingers in CI workflow
pattern strings (e.g. `just test-group` invocations in GitHub Actions). This causes no
immediate CI failure (since the test runner simply skips missing files), but leaves misleading
dead references. This skill documents the minimal workflow to identify and remove them.

## When to Use

- A GitHub issue asks to "remove a test file entirely" and the file no longer exists on disk
- CI workflow contains a space-separated pattern string that lists individual test filenames
- The only remaining work to close an issue is removing a stale filename from a YAML workflow
- A cleanup/deprecation issue where the test file itself is already gone

## Verified Workflow

1. **Confirm the file is gone**: Check the filesystem — do not assume the issue description
   is current. The file may already have been deleted in a prior commit.

   ```bash
   ls tests/shared/core/test_<name>.mojo 2>/dev/null || echo "File does not exist"
   ```

2. **Grep for all references** to find every place the filename appears:

   ```bash
   grep -r "test_<name>" . --include="*.yml" --include="*.yaml" --include="*.toml" --include="*.mojo"
   ```

3. **Edit the workflow file**: Remove only the stale filename token from the pattern string.
   The pattern strings are space-separated, so remove the token and its surrounding space.

   Use the `Edit` tool (not `sed`) to make a precise, reviewable change.

4. **Verify no remaining references** (excluding prompt/issue files):

   ```bash
   grep -r "test_<name>" . --include="*.yml" --include="*.toml" --include="*.mojo"
   ```

5. **Commit, push, create PR** following the standard branch workflow:
   - Branch: `<issue-number>-auto-impl`
   - Commit message: `refactor(tests): remove <name> from CI`
   - PR body: `Closes #<issue>`
   - Enable auto-merge: `gh pr merge <pr> --auto --rebase`

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
|---------|----------------|---------------|----------------|
| Glob for the file in worktree | `Glob tests/shared/core/test_backward_compat_aliases.mojo` | File did not exist — already deleted in a prior commit | Always verify file existence first; issue descriptions may lag behind actual state |
| Background `find` command | Used `find /home/mvillmow/Odyssey2 -name "test_backward_compat_aliases.mojo"` | Ran as background task, output wasn't available when needed | For quick existence checks, use `ls` or `Glob` synchronously instead of background `find` |

## Results & Parameters

### Pattern string location (example)

```yaml
# .github/workflows/comprehensive-tests.yml
pattern: "test_backward_linear.mojo test_backward_conv_pool.mojo test_backward_losses.mojo test_backward_compat_aliases.mojo ..."
```

After removal:

```yaml
pattern: "test_backward_linear.mojo test_backward_conv_pool.mojo test_backward_losses.mojo ..."
```

### Grep command to find all references

```bash
grep -r "<test_filename>" . \
  --include="*.yml" --include="*.yaml" \
  --include="*.toml" --include="*.mojo" \
  -l
```

### Minimal commit message template

```
refactor(tests): remove <test_filename> from CI

The test file <path> has been deleted; this removes the dangling
reference from the CI workflow pattern string.

Closes #<issue>
```
