---
name: merge-duplicate-docs
description: "Merge two overlapping markdown docs into one canonical source, preserving unique content and fixing all cross-references. Use when: two files cover the same topic (DRY violation), one has visual/summary content and the other has detailed specs, or you need a single authoritative reference."
category: documentation
date: 2026-03-05
user-invocable: false
---

## Overview

| Attribute | Value |
|-----------|-------|
| **Goal** | Eliminate duplicate documentation by merging into one canonical file |
| **Inputs** | Two overlapping markdown files, grep search for cross-references |
| **Outputs** | Updated canonical file, deleted duplicate, updated references |
| **Trigger** | DRY violation: two files document the same topic |
| **Time** | ~15 minutes for typical doc merge |

## When to Use

- Two markdown files both document the same concept (e.g., an agent hierarchy)
- One file is a visual/diagram/quick-reference and the other has detailed specs
- A GitHub issue requests merging/consolidating overlapping docs
- Cross-references between files create circular dependencies

## Verified Workflow

### Step 1: Read Both Files

Read both files in parallel to understand their content and overlap:

```
Read file-A.md  # e.g., hierarchy.md (visual diagrams, quick reference)
Read file-B.md  # e.g., agent-hierarchy.md (detailed per-agent specs)
```

Identify:
- Shared content (same in both)
- Unique content in file-A (keep in place)
- Unique content in file-B (must be merged into file-A)

### Step 2: Find All Cross-References

Search the entire repo for references to the file being deleted:

```bash
grep -r "agent-hierarchy\.md" --include="*.md" -l
```

Or use the Grep tool with `output_mode: "content"` to see exact lines.

### Step 3: Fix Broken Syntax in the Canonical File

Before merging, fix any existing issues in the canonical file:

- Fenced code blocks ending with ` ```text ` instead of ` ``` `
- Overly long lines (>120 chars for markdownlint MD013)
- Missing blank lines around lists (MD032)
- Self-referential links in "See Also" sections pointing to the file being deleted

### Step 4: Append Unique Content

Add unique sections from file-B to file-A in a logical structure. For a hierarchy doc, the typical order is:

1. Visual diagram (already in canonical)
2. Level summaries (already in canonical)
3. Quick reference (already in canonical)
4. **Detailed per-agent specs** (unique to detailed file — append as new section)
5. **Delegation rules** (unique to detailed file — append)
6. **Config template** (unique to detailed file — append)
7. **Org model mappings** (unique to detailed file — append)
8. **Phase workflow table** (unique to detailed file — append)
9. See Also (update to remove reference to deleted file)

### Step 5: Delete the Duplicate File

```bash
rm agents/agent-hierarchy.md
```

### Step 6: Update All Cross-References

For each file found in Step 2, update the link:

```
old: [Agent Hierarchy](../agent-hierarchy.md)
new: [Agent Hierarchy](../hierarchy.md)
```

Also update any prose descriptions:
- `**agent-hierarchy.md** - Complete detailed hierarchy specification`
- → `**hierarchy.md** - Visual hierarchy diagram and complete agent specifications`

### Step 7: Run Linting

```bash
SKIP=mojo-format pixi run pre-commit run markdownlint-cli2 --all-files
```

Fix any line-length (MD013) or list-spacing (MD032) errors from the merged content.
Long lines from the detailed file often need wrapping at natural phrase boundaries.

### Step 8: Commit and PR

Stage all modified files explicitly (not `git add -A`):

```bash
git add canonical-file.md deleted-file.md file1.md file2.md ...
git commit -m "docs(scope): merge duplicate-file.md into canonical-file.md

Eliminates DRY violation. Closes #ISSUE"
```

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
|---------|----------------|---------------|----------------|
| Closing code blocks with ` ```text ` | Original file used ` ```text ` to close fenced blocks (not just open them) | markdownlint treats ` ```text ` as an opening of a new block, not a closing | Always close fenced code blocks with plain ` ``` ` — only opening tags get a language specifier |
| Adding merged content without checking line lengths | Pasted detailed spec content directly | Lines from the detailed file were 150-241 chars, failing MD013 (120 char limit) | After merging content, always run markdownlint to catch line-length violations from the source file |
| Keeping self-referential "See Also" link | `hierarchy.md` had a link to `agent-hierarchy.md` in its See Also section | Creates a broken link after deletion | When merging, remove all references to the deleted file from the canonical file itself |

## Results & Parameters

### Reference Update Pattern

Files that commonly reference documentation files and need updating:

- `CLAUDE.md` — project structure tree diagram
- `agents/README.md` — documentation index and references section
- `agents/docs/*.md` — cross-links in related docs
- `scripts/agents/README.md` — see also sections
- `tests/agents/mock_agents/README.md` — test documentation links

### Markdownlint Common Fixes After Merge

```markdown
# Long line fix — wrap at natural phrase boundary
- **Language Context**: Designs Mojo module structures, leverages Mojo features (SIMD, traits, structs);
  coordinates review across all code dimensions

# List spacing fix — add blank line before list
**Level 3 Breakdown:**

- Implementation/Execution Specialists: 11 (...)
- Code Review Specialists: 13 (...)
```

### Grep Command for Finding References

```bash
# Find all markdown files referencing the file to be deleted
grep -rn "old-filename\.md" --include="*.md" .

# Or use ripgrep
rg "old-filename\.md" --type md -l
```
