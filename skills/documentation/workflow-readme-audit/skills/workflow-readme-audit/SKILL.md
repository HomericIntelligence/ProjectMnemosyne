---
name: workflow-readme-audit
description: "Audit .github/workflows/README.md against actual files on disk, update inventory to match reality, and document remaining duplication. Use when: workflows were added/deleted but README was not updated, a consolidation pass removed workflows still listed, or inline setup steps exist across many workflows needing inventory before extraction."
category: documentation
date: 2026-03-07
user-invocable: true
---

# Workflow README Audit

## Overview

| Attribute | Value |
|-----------|-------|
| **Date** | 2026-03-07 |
| **Objective** | Audit `.github/workflows/README.md` against actual on-disk files after a consolidation pass removed/added workflows |
| **Outcome** | README updated: removed 2 stale entries, added 13 undocumented workflows, corrected filename, documented 13 inline `setup-pixi` duplications; pre-commit passed; PR created |
| **Related Issues** | ProjectOdyssey #3344, follow-up from #3149 |

## When to Use This Skill

Use this skill when:

- A GitHub issue asks to update `workflows/README.md` to "reflect the current state" after a consolidation pass
- Workflows were deleted (e.g., `unit-tests.yml`, `integration-tests.yml`) but the README still lists them
- New workflows were added (e.g., `claude.yml`, `docker.yml`) that have no documentation entry
- The README references a filename that does not match what exists on disk (e.g., `security-scan.yml` vs `security.yml`)
- You need to inventory inline setup patterns (e.g., `prefix-dev/setup-pixi`) to plan composite action extraction

**Triggers:**

- Issue title contains "workflow README", "workflow inventory", "workflow count", "reflect current state"
- `workflows/README.md` table references files that don't exist on disk
- A consolidation PR merged but no follow-up README update happened
- Issue mentions "remaining duplication" or "not yet migrated" workflows

## Verified Workflow

### Phase 1: Establish Ground Truth

```bash
# Get the definitive list of actual workflow files
ls .github/workflows/*.yml

# Get exact count
ls .github/workflows/*.yml | wc -l
```

Cross-reference with the current README table. Identify:

| Finding | Action |
|---------|--------|
| File in README but not on disk | Remove from README |
| File on disk but not in README | Add to README |
| Filename mismatch (e.g., `security-scan.yml` vs `security.yml`) | Correct the filename |

### Phase 2: Read Each Undocumented Workflow

For each workflow missing from the README, read the first 20 lines to extract:

- `name:` field (display name)
- `on:` triggers (PR, push, schedule, workflow_dispatch)
- `paths:` filters if any

```bash
# Quick metadata extraction for multiple files
for f in workflow1.yml workflow2.yml; do
  echo "=== $f ==="
  head -20 .github/workflows/$f
done
```

### Phase 3: Audit Inline Duplication

```bash
# Find all workflows with inline setup step (e.g., setup-pixi)
grep -rl "prefix-dev/setup-pixi" .github/workflows/*.yml

# Count them
grep -rl "prefix-dev/setup-pixi" .github/workflows/*.yml | wc -l
```

Create a table in the README listing each duplicated workflow, its category, and a note
that this is intentional deferred work (not an oversight).

### Phase 4: Rewrite the README Summary Table

The table must reflect **only files that actually exist**. Add a shell command so future
readers can verify without trusting a hardcoded number:

```markdown
To get the current workflow count:

```bash
ls .github/workflows/*.yml | wc -l
```
```

### Phase 5: Fix Common markdownlint Failures

The original README had closing ` ``` ` fences with `text` on the same line (e.g., ` ```text `).
markdownlint-cli2 treats this as MD031/MD040 violations. Replace with bare ` ``` `.

Also watch for:

| Error | Fix |
|-------|-----|
| `MD013/line-length` (>120 chars) | Wrap blockquote or table cell content |
| `MD029/ol-prefix` (out-of-sequence numbered list) | Reset list numbering to 1/2/3 when starting a new logical group |

### Phase 6: Commit and PR

```bash
git add .github/workflows/README.md
git commit -m "docs(ci): update workflow README to reflect post-consolidation inventory

- Remove stale entries: <list deleted workflows>
- Add documentation for: <list new workflows>
- Correct filename: <old> -> <new>
- Fix broken fenced code blocks (closing backticks had 'text' on same line)
- Add Remaining Duplication section: N workflows with inline <step>
- Add audit commands so inventory stays verifiable without hardcoded counts

Closes #<issue>

Co-Authored-By: Claude <noreply@anthropic.com>"

git push -u origin <branch>
gh pr create \
  --title "docs(ci): update workflow README to reflect post-consolidation inventory" \
  --body "Closes #<issue>" \
  --label "documentation"
gh pr merge --auto --rebase
```

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
|---------|----------------|---------------|----------------|
| `pixi run npx markdownlint-cli2` for pre-validation | Run markdownlint before committing | `npx` not in PATH in this shell context; pixi environment setup takes >2 min | Just commit — pre-commit hook runs markdownlint automatically and gives precise line numbers |
| `find ~/.pixi -name "markdownlint*"` for binary | Locate markdownlint outside of pixi run | `find` on home dir ran for >3 min without completing | Use `git commit` directly; the pre-commit hook finds markdownlint via its own env |
| Closing fences with `text` on same line (from original README) | Kept existing style of ` ```text ` | MD031/MD040 lint failures at commit time | Always use bare ` ``` ` for closing fences; only opening fences take a language tag |

## Results & Parameters

**Summary table structure** (copy-paste template for new projects):

```markdown
| Workflow | Trigger | Purpose | Duration |
|----------|---------|---------|----------|
| **Category** | | | |
| [name.yml](#anchor) | PR, push main | Short description | < N min |
```

**Remaining Duplication section template:**

```markdown
## Remaining Duplication

### <Step Name> Inline Usage (Not Yet Migrated to Composite Action)

| Workflow | Category | Notes |
|----------|----------|-------|
| `workflow.yml` | Testing | Path-triggered |

**Why not migrated**: <reason — scope of previous consolidation pass>
**Follow-up work**: Create `.github/actions/<name>/action.yml` as composite action.
```

**Audit commands to include in README** (so counts stay verifiable):

```bash
# Count workflows using a specific inline step
grep -rl "prefix-dev/setup-pixi" .github/workflows/*.yml | wc -l

# List them
grep -rl "prefix-dev/setup-pixi" .github/workflows/*.yml

# Count total workflows
ls .github/workflows/*.yml | wc -l
```

## Key Observations

1. **README filenames drift from reality** — when workflows are renamed or deleted, the README
   is rarely updated. Always cross-reference with `ls .github/workflows/*.yml`.

2. **Read the first 20 lines of each file** — `name:`, `on:`, and `paths:` are always in the
   first 20 lines of a GitHub Actions workflow. No need to read the full file for inventory purposes.

3. **Ordered list numbering resets across logical groups** — markdownlint MD029 requires lists
   to start at 1. If you have two separate numbered lists (e.g., "PR/push jobs" and "weekly jobs"),
   each must start at 1 independently.

4. **Document intentional deferred work explicitly** — a "Remaining Duplication" section is more
   useful than silence. Readers need to know that 13 workflows sharing inline setup is a known
   state, not an oversight, and what the migration path is.

5. **Pre-commit hook is the authoritative linter** — use `git commit` to trigger it rather than
   trying to run `npx markdownlint-cli2` directly. The hook provides line numbers and exact error text.

6. **The note about non-existent files belongs in the table** — when a file mentioned in planning
   doesn't exist on disk (e.g., `build-validation.yml`), add a blockquote note directly below the
   table explaining its absence rather than either omitting it or listing it as if it exists.

## Verified On

| Project | Context | Details |
|---------|---------|---------|
| ProjectOdyssey | Issue #3344, PR #3978 | 22 workflows; pre-commit passed (markdownlint, trailing-whitespace, end-of-file-fixer) |
