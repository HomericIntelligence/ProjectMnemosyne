---
name: pre-commit-pass-filenames-evaluation
description: 'Evaluate whether a pre-commit hook should use pass_filenames: true or
  false, then document the decision. Use when: (1) a hook has pass_filenames: false
  and intent is unclear, (2) asked to review a hook''s filename-passing behavior,
  (3) adding an explanatory comment to .pre-commit-config.yaml.'
category: documentation
date: 2026-03-07
version: 1.0.0
user-invocable: false
---
## Overview

| Field | Value |
|-------|-------|
| **Category** | documentation |
| **Complexity** | XS |
| **Typical runtime** | < 10 minutes |
| **Key tools** | Read, Grep, Edit, Bash (pre-commit), git, gh |

## When to Use

- Issue asks to evaluate if a pre-commit hook should use `pass_filenames: true` instead of `false`
- A hook has `pass_filenames: false` and the rationale is undocumented
- Follow-up from a PR that changed a sibling hook's `pass_filenames` setting
- The hook's script needs to be inspected to determine whether it uses file arguments

## Verified Workflow

1. **Read `.pre-commit-config.yaml`** — locate the hook and note `entry:`, `files:`, and `pass_filenames:` values
2. **Read the script referenced in `entry:`** — check how it handles arguments:
   - Does it use `sys.argv` for positional args? → could support `pass_filenames: true`
   - Does it do whole-repo scanning (e.g. `find_files(repo_root)`)? → `pass_filenames: false` is correct
   - Does it ignore positional args entirely? → `pass_filenames: false` is correct
3. **Grep for `sys.argv` and `argparse`** in the script to confirm argument handling
4. **Decide**: if the script ignores file args or does a global scan, `pass_filenames: false` is intentional
5. **Add a 3-line inline comment** directly above the `pass_filenames: false` line explaining the design
6. **Run the hook** to verify no regression: `pixi run pre-commit run <hook-id> --all-files`
7. **Commit, push, and create PR** linking to the issue

### Key Decision Criteria

| Script behavior | Correct setting |
|----------------|-----------------|
| Iterates over `sys.argv[1:]` as file paths | `pass_filenames: true` |
| Uses `argparse` with positional `files` argument | `pass_filenames: true` |
| Scans repo root with `Path.glob` / `os.walk` | `pass_filenames: false` |
| Only checks `"--flag" in sys.argv` (no positional args) | `pass_filenames: false` |
| Reads a fixed config/workflow file at a hardcoded path | `pass_filenames: false` |

### Comment Template

```yaml
        # pass_filenames: false is intentional — this script performs a whole-repo
        # <operation> against <target>, not per-file validation.
        # The files: pattern handles efficient triggering; the script ignores file args.
        pass_filenames: false
```

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
|---------|----------------|---------------|----------------|
| Switching to `pass_filenames: true` without reading the script | Assumed symmetry with a sibling hook | Script does not process positional file args; passing them would be silently ignored | Always read the script before deciding |
| Checking only the hook config | Looked at `files:` pattern and `entry:` only | Did not reveal whether the script actually processes `sys.argv[1:]` | Must grep the script for argument handling code |

## Results & Parameters

### Commit message format

```text
docs(pre-commit): document intentional pass_filenames: false for <hook-id> hook

<Script> performs a whole-repo <operation>, not per-file validation.
It ignores positional file arguments — pass_filenames: false is the correct setting.

Added inline comment to clarify this design decision.

Closes #<issue-number>

Co-Authored-By: Claude Sonnet 4.6 <noreply@anthropic.com>
```

### Verification command

```bash
pixi run pre-commit run <hook-id> --all-files
# Expected: "<Hook Name>...Passed"
```

## Verified On

| Project | Context | Details |
|---------|---------|---------|
| ProjectOdyssey | Issue #3352, PR #3992 | validate-test-coverage hook; script uses `find_test_files(repo_root)` whole-repo scan |
