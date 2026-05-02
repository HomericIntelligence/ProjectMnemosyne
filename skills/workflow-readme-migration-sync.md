---
name: workflow-readme-migration-sync
description: 'Update workflow README documentation to reflect completed CI/CD migrations.
  Use when: a README still describes inline steps replaced by composite actions, deferred
  documentation work is being closed out, or cross-references in a workflow README
  are stale after consolidation.'
category: documentation
date: 2026-03-15
version: 1.0.0
user-invocable: false
---
## Overview

| Field | Value |
| ------- | ------- |
| **Skill** | workflow-readme-migration-sync |
| **Category** | documentation |
| **Trigger** | Issue closing deferred README documentation after workflows are already migrated |
| **Effort** | ~15 min |
| **Risk** | Low — documentation only, no code changes |

## When to Use

- A GitHub issue references "deferred documentation" from a prior consolidation pass
- Workflow files already use the new pattern (e.g. composite action) but README still shows the old inline pattern
- "Remaining Duplication" or similar stale sections exist in a workflow README
- "Adding New Workflows" guidance still directs contributors to the old approach

## Verified Workflow

### Quick Reference

```bash
# 1. Grep workflows to confirm migration is complete
grep -rn "prefix-dev/setup-pixi" .github/workflows/*.yml | grep -v README

# 2. Grep README to find stale prose
grep -n "inline\|Not Yet Migrated\|Remaining Duplication\|no composite action" .github/workflows/README.md

# 3. Run markdownlint after edits
pixi run pre-commit run markdownlint-cli2 --files .github/workflows/README.md
```

### Step 1 — Verify the migration is actually done

Before touching the README, confirm the workflows already use the new pattern:

```bash
# Should return 0 results if migration is complete
grep -rn "prefix-dev/setup-pixi" .github/workflows/*.yml | grep -v README | wc -l

# Should return results for each migrated workflow
grep -rn "uses: ./.github/actions/setup-pixi" .github/workflows/*.yml | wc -l
```

If the inline pattern is still present in `.yml` files, the README update is premature — do
the workflow migration first.

### Step 2 — Identify all stale README locations

```bash
grep -n "inline\|Not Yet Migrated\|no composite action\|prefix-dev/setup-pixi\|Remaining Duplication" \
  .github/workflows/README.md
```

Typical stale locations in a post-migration README:

1. **Individual workflow description bullets** — e.g. "Uses inline `prefix-dev/setup-pixi`"
2. **"Remaining Duplication" section** — lists workflows as not-yet-migrated
3. **"Common Patterns > Composite Actions"** — says no composite actions exist
4. **"Pixi-Based Environment Setup"** — shows old inline YAML snippet
5. **"Adding New Workflows"** checklist — tells contributors to add to duplication table
6. **Audit quick-reference commands** — grep command checks for inline usage count

### Step 3 — Apply targeted edits

**Workflow description bullets** (use `replace_all: true` when the same phrase appears multiple times):

```
Before: - Uses inline `prefix-dev/setup-pixi` for Mojo environment
After:  - Uses `.github/actions/setup-pixi` composite action for Mojo environment
```

**"Remaining Duplication" section** — replace with a "Composite Actions" section that:
- Names the composite action file
- Lists migrated workflows in a table
- Includes a verification command showing expected count = 0

**"Pixi-Based Environment Setup"** — replace old YAML example with the composite action `uses:` line and note why the explicit cache step is preferred over `cache: true`.

**"Adding New Workflows"** — replace "add to Remaining Duplication table" with "use the composite action".

**Audit commands** — update to verify zero inline usage remains.

### Step 4 — Validate markdown

```bash
SKIP=mojo-format pixi run pre-commit run markdownlint-cli2 --files .github/workflows/README.md
```

Fix any lint errors before committing.

### Step 5 — Commit and PR

```bash
git add .github/workflows/README.md
git commit -m "docs(workflows): update README to reflect completed <migration-name>

<Brief description of what changed and why the old README was stale.>

Closes #<issue-number>"

git push -u origin <branch>
gh pr create --title "docs(workflows): ..." --body "Closes #<issue>"
gh pr merge --auto --rebase
```

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
| --------- | ---------------- | --------------- | ---------------- |
| Editing "Uses inline" bullets one at a time | Used `replace_all: false` for the first bullet, then tried to match the second with trailing context | Context string wasn't unique — edit tool reported string not found | When the same phrase appears multiple times, use `replace_all: true` on the first pass; only use contextual matching when the surrounding text differs |
| Updating SHA-pinning documentation examples | Considered replacing `prefix-dev/setup-pixi@v0.9.3` in the SHA-pinning examples section | Those lines are intentional documentation of the pinning pattern, not actual workflow steps | Always check whether a `prefix-dev/setup-pixi` reference is in a code example block explaining a concept vs. a step to be migrated |

## Results & Parameters

**PR created**: https://github.com/HomericIntelligence/ProjectOdyssey/pull/4847

**Files changed**: `.github/workflows/README.md` only (26 insertions, 45 deletions)

**Validation command**:

```bash
# After migration, inline count should be 0
grep -rl "prefix-dev/setup-pixi" .github/workflows/*.yml | wc -l
```

**Key replacement patterns** (copy-paste):

```bash
# Count remaining inline uses
grep -rn "prefix-dev/setup-pixi" .github/workflows/*.yml | grep -v README | wc -l

# Confirm composite action is in use
grep -rn "uses: ./.github/actions/setup-pixi" .github/workflows/*.yml | wc -l
```
