---
name: ci-shell-grep-case-mismatch
description: 'Skill: ci-shell-grep-case-mismatch. Use when a shell-tests or smoke-check
  CI workflow fails because a grep -q assertion checks the wrong casing of a string
  vs the actual content in a source file — especially with org names or proper nouns.'
category: ci-cd
date: 2026-04-23
version: 1.0.0
user-invocable: false
---
# Skill: ci-shell-grep-case-mismatch

## Overview

| Field | Value |
|-------|-------|
| Date | 2026-04-23 |
| Objective | Fix CI failure caused by `grep -q` assertion checking case-incorrect string against source file content |
| Outcome | Success — workflow unblocked after changing grep string to match exact casing in source file |
| Verification | verified-ci — fix pushed to main, workflow immediately unblocked further PRs |
| Category | ci-cd |

### What Happened

`shell-tests.yml` contained `grep -q 'homeric-intelligence' scripts/notify-proteus.sh`. But `notify-proteus.sh` uses `HomericIntelligence` (CapitalCase — the canonical GitHub org name). Every push to main since that workflow was added failed "Shell Script Tests". The fix was to change the grep to match the actual string in the file.

## When to Use

Trigger this skill when:

- A shell-tests or smoke-check workflow fails with exit code 1 on a `grep -q` step
- A CI workflow asserts an org name, project name, or any proper noun string in a shell script
- Debugging "grep command failed" in a GitHub Actions workflow step
- You suspect a case mismatch between a CI assertion and the actual source file content

## Verified Workflow

### Quick Reference

```bash
# Before writing or debugging a grep assertion in CI, verify the exact form:
grep 'HomericIntelligence' scripts/notify-proteus.sh   # exact match
grep -i 'homericintelligence' scripts/notify-proteus.sh  # case-insensitive sanity check

# Safe defensive pattern — use -i when the assertion intent is "this org appears somewhere":
grep -qi 'homericintelligence' scripts/notify-proteus.sh

# Exact-match pattern when the assertion intent requires a specific form:
grep -q 'HomericIntelligence' scripts/notify-proteus.sh
```

### Diagnostic Steps

1. Run the failing workflow step locally:
   ```bash
   grep -q 'homeric-intelligence' scripts/notify-proteus.sh; echo $?
   # If exit code is 1, the string is not in the file
   ```
2. Find what form is actually used in the file:
   ```bash
   grep -i 'homeric' scripts/notify-proteus.sh
   # Reveals: HomericIntelligence (CapitalCase), not homeric-intelligence (kebab-case)
   ```
3. Update the CI assertion to match the exact form from step 2, or switch to `grep -qi` if case-insensitivity is acceptable.

### Key Rules

- GitHub org names are CapitalCase (`HomericIntelligence`); kebab-case is for package names, URLs, and slugs — not necessarily the org display name
- Always run `grep <string> <file>` locally before writing a CI assertion to verify the match
- The "fast smoke test" pattern for shell scripts (grep for a magic string) is fragile if the string form does not match the actual content
- Use `grep -qi` (case-insensitive) as a safer fallback when the assertion intent is just "this org name appears somewhere"
- Use exact `grep -q` when the assertion must verify a specific canonical form

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
|---------|---------------|---------------|----------------|
| 1 | `grep -q 'homeric-intelligence' scripts/notify-proteus.sh` in `shell-tests.yml` | File uses `HomericIntelligence` (CapitalCase), not kebab-case; grep returned exit 1 | Never assume kebab-case for a proper noun — check the source file first |
| 2 | Assuming the workflow would pass because "the org name is there" | The string form in the file did not match the grep pattern; CI is case-sensitive by default | Case sensitivity is the default; always verify with a local grep run |

## Results & Parameters

| Parameter | Value |
|-----------|-------|
| Shell script path | `scripts/notify-proteus.sh` |
| Incorrect assertion | `grep -q 'homeric-intelligence'` |
| Correct assertion | `grep -q 'HomericIntelligence'` |
| Case-insensitive fallback | `grep -qi 'homericintelligence'` |
| CI workflow file | `.github/workflows/shell-tests.yml` |
| Failure mode | `grep` exits 1 → workflow step fails → "Shell Script Tests" job fails |
| Canonical org name | `HomericIntelligence` (CapitalCase, not kebab-case) |
