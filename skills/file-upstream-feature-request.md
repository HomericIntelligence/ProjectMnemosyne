---
name: file-upstream-feature-request
description: "Use when filing a feature request or bug against a third-party OSS repo. Covers: duplicate check, label discovery, local patch proposal via secret gist, smoke testing, and clean cross-repo issue creation with gh CLI. Use when: (1) proposing a new flag/behavior to an upstream tool you don't maintain, (2) attaching a proposed patch as a gist to an external issue, (3) needing to verify no duplicate exists before filing."
category: tooling
date: 2026-04-25
version: "1.0.0"
user-invocable: false
verification: verified-local
tags: [gh, github, upstream, feature-request, gist, patch, oss, third-party, issue-filing, gh-extension]
---

# File Upstream Feature Request Against Third-Party OSS Repo

## Overview

| Field | Value |
|-------|-------|
| **Date** | 2026-04-25 |
| **Objective** | File a well-formed feature request against an upstream OSS repo (`HaywardMorihara/gh-tidy`) with a proposed patch, secret gist link, local env metadata, and a smoke-tested change — without modifying any real repo state |
| **Outcome** | Issue #62 filed successfully at https://github.com/HaywardMorihara/gh-tidy/issues/62; gist at https://gist.github.com/mvillmow/4b8eedf4e9cdf74760d78ada68fa1ed7 |
| **Verification** | verified-local — patch syntax-checked with `bash -n`, smoke-tested with `GH_TIDY_DEV_MODE=1` in a `mktemp -d` throwaway repo |
| **Source** | ProjectScylla session: filing `--auto-delete` feature request against gh-tidy |

## When to Use

- About to file a feature request or bug against an upstream OSS tool you don't maintain
- Want to include a proposed patch as supporting evidence (not a PR — just a reference)
- Need to verify no duplicate issue exists before filing
- Need to discover what labels exist on an external repo before assigning any
- Proposing a new CLI flag that follows the existing pattern in a bash extension/script
- Smoke testing a bash script change safely (without touching real git state)

## Verified Workflow

### Quick Reference

```bash
# 1. Clone upstream to a throwaway dir
git clone https://github.com/<owner>/<repo> /tmp/<repo>-investigate-$$

# 2. Check for duplicate issues
gh issue list --repo <owner>/<repo> --state all --search "<keywords>" --limit 20

# 3. Discover available labels
gh label list --repo <owner>/<repo>

# 4. Collect local version metadata
gh extension list                          # shows installed SHA
git -C /tmp/<repo>-investigate-$$ log --oneline -1   # upstream HEAD
gh --version
git --version
bash --version

# 5. Create proposal branch + edit
git -C /tmp/<repo>-investigate-$$ checkout -b proposal-branch
# ... edit the file following existing patterns exactly ...

# 6. Syntax check + smoke test
bash -n /tmp/<repo>-investigate-$$/<file>
NEW_FLAG=1 bash /tmp/<repo>-investigate-$$/<file>  # repo-specific dev-mode if available

# 7. Generate patch
git -C /tmp/<repo>-investigate-$$ diff main..proposal-branch > /tmp/proposed-patch.diff

# 8. Create secret gist
gh gist create /tmp/proposed-patch.diff --desc "Proposed patch: <feature>" # no --public = secret

# 9. Write issue body to file, then file cross-repo
gh issue create --repo <owner>/<repo> \
  --title "<feature request title>" \
  --label enhancement \
  --body-file /tmp/issue-body.md

# 10. Cleanup
rm -rf /tmp/<repo>-investigate-$$
```

### Detailed Steps

**Step 1: Clone to a throwaway directory**

Always use a process-isolated temp path to avoid polluting any real working directory:

```bash
TMPCLONE="/tmp/<repo>-investigate-$$"
git clone https://github.com/<owner>/<repo> "$TMPCLONE"
```

**Step 2: Duplicate check before anything else**

Never file without verifying no open or closed duplicate exists:

```bash
gh issue list --repo <owner>/<repo> --state all --search "<keyword1> <keyword2>" --limit 20
```

Use multiple search terms (flag name, behavior description, related terms). A clean result (0 issues) is the gate to proceed.

**Step 3: Label discovery**

Labels differ across repos. Never assume `enhancement`, `bug`, `feature` exist:

```bash
gh label list --repo <owner>/<repo>
```

Only assign labels that appear in the output.

**Step 4: Collect local version metadata for the issue body**

Include this table in the issue body so maintainers can reproduce:

```bash
# Installed extension version (from gh extension list output — shows SHA)
gh extension list | grep <ext-name>

# Latest upstream HEAD
git -C "$TMPCLONE" log --oneline -1

# Drift (commits behind/ahead)
git -C "$TMPCLONE" rev-list --count HEAD

# Tool versions
gh --version
git --version
bash --version
uname -a  # OS
```

**Step 5: Read and understand the existing pattern**

Before proposing any change, read the full source to understand the existing idiom. For bash extensions, look for:

- How existing flags are defined (help text, env-var docs, defaults table)
- How env vars are named and initialized (e.g., `GH_TIDY_*` prefix pattern)
- How arg-parse `case` statements handle the flag
- Where in the main logic the flag value is consumed

Follow the existing pattern exactly — this makes the patch minimally invasive and easy for maintainers to review.

**Step 6: Create a proposal branch and edit**

```bash
git -C "$TMPCLONE" checkout -b proposal-<feature>
# Edit the file following the existing pattern
```

**Step 7: Syntax check and smoke test**

Always do both:

```bash
# Syntax check — instant, no execution
bash -n "$TMPCLONE/<script>"

# Smoke test — if the repo has a dev mode env var, use it
# Use mktemp -d to create a throwaway git repo for isolation
SMOKE_DIR=$(mktemp -d)
git -C "$SMOKE_DIR" init
git -C "$SMOKE_DIR" commit --allow-empty -m "init"
DEV_MODE_VAR=1 NEW_FLAG=true bash "$TMPCLONE/<script>"
rm -rf "$SMOKE_DIR"
```

The smoke test confirms the new code path fires and the existing protection logic (e.g., protecting trunk) still works.

**Step 8: Generate the patch**

```bash
git -C "$TMPCLONE" diff main..proposal-<feature> > /tmp/proposed-patch.diff
```

**Step 9: Create a secret (unlisted) gist**

A secret gist is URL-accessible but does not appear on your public profile:

```bash
# No --public flag = secret/unlisted
gh gist create /tmp/proposed-patch.diff --desc "Proposed patch: <feature description>"
# Captures: gist URL (https://gist.github.com/<user>/<id>)
# Raw URL: https://gist.github.com/<user>/<id>/raw/<filename>
```

**Step 10: Write issue body to a file**

Avoid shell quoting issues by writing to a file:

```bash
cat > /tmp/issue-body.md << 'ISSUEBODY'
## Summary
<1-2 sentence description of the feature being requested>

## Proposed Behavior

| Invocation | `--new-flag` present | Env Var set | Result |
|------------|----------------------|-------------|--------|
| ... | ... | ... | ... |

## Motivation
<Why this is useful — what problem it solves>

## Proposed Implementation

I've written a proposed patch following the existing `--flag` / `GH_<TOOL>_<FLAG>` pattern in the codebase.

**Patch (secret gist):** <gist URL>

To apply and test locally:
```bash
gh extension install <owner>/<repo>
# locate install path
ls "$(gh extension list | awk '/<repo>/{print $3}')"
# apply patch
curl -sL <raw gist URL> | git apply --directory="..."
```

## Environment

| Component | Value |
|-----------|-------|
| `gh-tidy` installed version | `<SHA from gh extension list>` |
| Latest upstream HEAD | `<SHA> <message>` |
| `gh` version | `<version>` |
| `git` version | `<version>` |
| `bash` version | `<version>` |
| OS | `<uname -a output>` |

## Verification

Patch syntax-checked with `bash -n` and smoke-tested with `<DEV_MODE_VAR>=1` in a
`mktemp -d` throwaway git repository — confirmed the new code path fires and trunk
branch is still protected without touching any real repository state.
ISSUEBODY
```

**Step 11: File the issue**

```bash
gh issue create \
  --repo <owner>/<repo> \
  --title "<Feature: descriptive title>" \
  --label enhancement \
  --body-file /tmp/issue-body.md
# Returns the issue URL — capture it
```

**Step 12: Cleanup**

```bash
# cd away first to avoid getcwd errors
cd /tmp
rm -rf "$TMPCLONE"
rm -f /tmp/proposed-patch.diff /tmp/issue-body.md
```

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
|---------|----------------|---------------|----------------|
| `yes \| gh tidy` for smoke test | Piped `yes` to bypass interactive prompts in `gh tidy` | Fragile for non-interactive automation — output order is unpredictable, prompts may not align with `yes` responses | Use dev-mode env vars (e.g., `GH_TIDY_DEV_MODE=1`) instead of piping `yes` for smoke testing |
| `cd "$TMPCLONE" && rm -rf "$TMPCLONE"` | Changed into tmp dir, then removed it in the same shell session | Shell issues `getcwd` error after CWD is deleted — benign but alarming and confusing | Always `cd /tmp` (or any persistent dir) before `rm -rf`-ing the directory you were in |
| Assigning labels without checking | Assumed common labels like `feature` or `good-first-issue` existed | Labels vary per repo; assigning a non-existent label causes `gh issue create` to fail | Always run `gh label list --repo <owner>/<repo>` before any `--label` argument |
| Filing from memory / stale context | Began drafting issue without re-reading current source | Existing pattern may differ from memory; patch becomes inconsistent with the codebase | Always read the full source file before proposing a change, even for a small addition |
| Skipping duplicate check | Jumped straight to implementation | Risk of filing a duplicate issue, wasting maintainer time | Always run `gh issue list --state all --search "<keywords>"` first — check both open and closed |

## Results & Parameters

### Issue Body Template (Copy-Paste Ready)

```markdown
## Summary
<1-2 sentences>

## Proposed Behavior

| Invocation | Flag present | Env Var set | Result |
|------------|--------------|-------------|--------|
| Default    | No           | Not set     | Interactive prompts |
| With flag  | Yes          | —           | <new behavior> |
| Via env    | —            | Yes         | <new behavior> |

## Motivation
<Why needed>

## Proposed Implementation
Proposed patch following existing flag/env-var pattern: <gist URL>

Apply instructions:
```bash
curl -sL <raw gist URL> | git apply
```

## Environment
| Component | Value |
|-----------|-------|
| Installed version | `<SHA>` |
| Upstream HEAD | `<SHA>` |
| gh version | `<version>` |

## Verification
Syntax-checked with `bash -n`; smoke-tested with `<DEV_MODE>=1` in throwaway repo.
```

### Key gh CLI Commands

```bash
# Duplicate check (always --state all to catch closed issues too)
gh issue list --repo <owner>/<repo> --state all --search "<terms>" --limit 20

# Label discovery
gh label list --repo <owner>/<repo>

# Installed extension SHA
gh extension list | grep <ext-name>

# Secret gist (no --public = unlisted)
gh gist create <file> --desc "<description>"

# Cross-repo issue creation from any directory
gh issue create --repo <owner>/<repo> --title "..." --label <label> --body-file <path>
```

### Gist Visibility Reference

| Flag | Visibility |
|------|-----------|
| `gh gist create` (no flag) | Secret — URL-accessible, not listed on profile |
| `gh gist create --public` | Public — appears on profile, indexed by search |

Use secret gists for proposed patches on third-party repos to keep your profile clean while still providing a shareable URL.

## Verified On

| Project | Context | Outcome |
|---------|---------|---------|
| ProjectScylla | Filed `--auto-delete` feature request against `HaywardMorihara/gh-tidy` | Issue #62 filed successfully; gist created; /tmp clone cleaned up |
