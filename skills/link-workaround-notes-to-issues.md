---
name: link-workaround-notes-to-issues
description: 'Link temporary workaround NOTE comments in source code to tracking GitHub
  issues. Use when: performing NOTE/TODO cleanup sprints, auditing untracked workarounds,
  or ensuring every temporary hack has a tracking issue.'
category: documentation
date: 2026-03-05
version: 1.0.0
user-invocable: false
---
## Overview

| Field | Value |
|-------|-------|
| **Objective** | Update bare `# NOTE:` comments to `# NOTE(#NNNN):` format linking to GitHub tracking issues |
| **Trigger** | Cleanup issues requiring all workaround NOTEs to be traceable |
| **Output** | Modified source files with issue references; no logic changes |
| **Scope** | Source files only — comment text changes, no functional code edits |

## When to Use

- A cleanup issue asks to "link workaround NOTEs to tracking issues"
- Running a NOTE/TODO/FIXME audit sprint (e.g. part of a master cleanup epic)
- CI or code review flags untracked temporary workarounds
- You need to ensure every `# NOTE:` that describes a limitation has a traceable issue number

## Verified Workflow

### Step 1: Discovery

Grep all `# NOTE:` markers (uppercase only to focus on structured markers):

```bash
grep -rn "# NOTE:" --include="*.mojo" .
```

Filter out already-linked NOTEs:

```bash
grep -rn "# NOTE:" --include="*.mojo" . | grep -v "tracked in #\|#[0-9]\{4,\}"
```

### Step 2: Categorize by Root Cause

Group NOTEs into clusters with a shared root cause before creating issues — avoids creating duplicate or overlapping tracking issues:

| Group | Root Cause | Files |
|-------|-----------|-------|
| A | Python interop blocked | trainer_interface.mojo, __init__.mojo |
| B | FP16 SIMD compiler limitation | mixed_precision.mojo (x2) |
| C | Image loading external deps | run_infer.mojo |
| D | Mojo stdlib missing os.remove() | file_io.mojo |
| E | BF16 aliased to FP16 | precision_config.mojo |
| F | Conv backward disabled (ownership) | test_conv.mojo |
| G | Model backward not implemented | googlenet-cifar10/train.mojo |

### Step 3: Find or Create Tracking Issues

For each group, search before creating:

```bash
gh issue list --label "cleanup" --state open --search "Python Mojo interop"
gh issue list --state open --search "FP16 SIMD"
```

If no existing issue covers it, create one:

```bash
gh issue create \
  --title "[Workaround] <short description>" \
  --body "## Objective
Track temporary workaround.

## Affected Files
- \`path/to/file.mojo:LINE\`

## Resolution
Implement when <blocker> is resolved.

Part of #<parent-issue>" \
  --label "cleanup,technical-debt"
```

Record the issue number for each group.

### Step 4: Update NOTE Comments

Change `# NOTE:` to `# NOTE(#NNNN):` — no other text changes:

```
Before:
    # NOTE: Python data loader integration blocked by Track 4 (Python↔Mojo interop).

After:
    # NOTE(#3076): Python data loader integration blocked by Track 4 (Python↔Mojo interop).
```

For multi-line NOTEs where the issue is referenced in the body (not the opening line), the NOTE is already linked — skip it.

For NOTEs that already follow the `# NOTE(#NNNN):` pattern or have `(tracked in #NNNN)` — skip them.

### Step 5: Verify Coverage

```bash
# Should return empty output if all NOTEs are linked
grep -rn "# NOTE:" --include="*.mojo" . | grep -v "#[0-9]\{4,\}"
```

### Step 6: Pre-commit and PR

```bash
pixi run pre-commit run --all-files
git add <changed files>
git commit -m "chore(cleanup): link workaround NOTEs to tracking issues (#NNNN)"
gh pr create --title "chore(cleanup): link workaround NOTEs to tracking issues" \
  --body "Closes #NNNN" --label "cleanup"
gh pr merge --auto --rebase
```

## Key Patterns Learned

### What Already Has Tracking (Skip These)

- `# NOTE(#NNNN):` — already linked (opening line)
- Multi-line NOTE where `#NNNN` appears in body text (e.g. "Tracked in project issue #3015") — already linked
- NOTEs that are purely informational (not workarounds) — skip

### What Needs Linking (Update These)

- `# NOTE: <limitation description>` with no issue reference anywhere in the NOTE block
- The fix is minimal: change `# NOTE:` to `# NOTE(#NNNN):` only

### Issue Search Before Creating

Always search `gh issue list` before creating — many cleanup issues already exist for common root causes (FP16 SIMD, Python interop, BF16, missing stdlib functions). Creating duplicates wastes tracking capacity.

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
|---------|----------------|---------------|----------------|
| Linking all NOTEs | Tried to add issue refs to all `# NOTE:` lines including informational ones | Created unnecessary issue noise | Only link NOTEs that describe temporary workarounds or blocked features |
| Creating new issues for all groups | Started creating new tracking issues for each group without searching first | Would have created duplicates of existing cleanup issues (#3076, #3087, etc.) | Always `gh issue list --search` before creating |
| Modifying multi-line NOTE body | Considered adding `(tracked in #NNNN)` to body lines that already had `#NNNN` in them | No change needed — body reference is sufficient | If `#NNNN` appears anywhere in the NOTE block, it's already linked |

## Results & Parameters

### Session Stats

- 6 files updated (comment text only)
- 3 NOTEs already had issue references (skipped)
- 0 new tracking issues created (all mapped to existing issues)
- Pre-commit: all hooks passed

### Issue Mapping Reference

| Pattern | Typical Tracking Issue Category |
|---------|--------------------------------|
| Python↔Mojo interop blocked | Python interop / Track 4 |
| FP16/BF16 compiler limitation | Mojo compiler limitation |
| Missing stdlib function | Mojo stdlib gap |
| External library required | External dependency |
| Struct ownership issue prevents tests | Type system / ownership |
| Model backward pass not implemented | Implementation debt |
