---
name: bulk-fix-orphan-quick-reference
description: "Bulk-fix SKILL.md files with orphaned top-level ## Quick Reference sections alongside ## Verified Workflow. Use when: validate_plugins.py reports Quick Reference warnings across many files."
category: tooling
date: 2026-03-15
user-invocable: false
---

# Bulk-Fix Orphaned Quick Reference Sections

Demote top-level `## Quick Reference` headings to `### Quick Reference` subsections
inside `## Verified Workflow` across an entire skills directory in one pass.

## Overview

| Item | Details |
|------|---------|
| Name | bulk-fix-orphan-quick-reference |
| Category | tooling |
| Trigger | validate_plugins.py warns about orphaned Quick Reference sections |
| Script | `scripts/fix_quick_reference_batch.py` |
| Scope | Any directory containing SKILL.md files (recursive) |

## When to Use

- `validate_plugins.py skills/ plugins/` emits warnings about `## Quick Reference` being a top-level section
- A batch migration (e.g., `migrate_odyssey_skills.py`) produced files that kept `## Quick Reference` at h2 level
- Post-migration cleanup pass needed before merging a skill import PR
- `fix_remaining_warnings.py` `main()` hardcoded list does not cover all affected files

## Verified Workflow

### Quick Reference

```bash
# Dry-run to preview which files would be changed
python3 scripts/fix_quick_reference_batch.py skills/ --dry-run

# Apply fixes
python3 scripts/fix_quick_reference_batch.py skills/

# Verify no warnings remain
python3 scripts/validate_plugins.py skills/ plugins/
```

### 1. Identify affected files

```bash
# First-pass validation — collect files emitting the warning
python3 scripts/validate_plugins.py skills/ plugins/ 2>&1 | grep "Quick Reference"
```

The warning fires when a SKILL.md contains **both**:
- A top-level `## Quick Reference` heading, AND
- A `## Verified Workflow` heading

Skills that only have `## Quick Reference` alongside `## Workflow` (Odyssey format)
are **not** affected — the warning only applies to Mnemosyne format.

### 2. Run the batch fix script

```bash
# Preview (safe — no writes)
python3 scripts/fix_quick_reference_batch.py skills/ --dry-run

# Apply
python3 scripts/fix_quick_reference_batch.py skills/
```

The script:

1. Recursively finds all `SKILL.md` files in the target directory
2. Filters to those with both `## Quick Reference` and `## Verified Workflow`
3. Extracts the full `## Quick Reference` block (up to the next `##` or EOF)
4. Demotes the heading: `## Quick Reference` → `### Quick Reference`
5. Removes the block from its original position
6. Inserts the demoted block immediately after the `## Verified Workflow` heading line
7. Writes the result back (in-place)
8. Runs a second pass to confirm zero files still trigger the warning

### 3. Verify zero warnings remain

```bash
python3 scripts/validate_plugins.py skills/ plugins/
# Should show no "Quick Reference" warnings
```

### 4. Commit and push

```bash
git add skills/
git commit -m "fix(skills): merge orphaned Quick Reference sections into Verified Workflow"
git push
```

## Implementation Details

The core transformation in `merge_quick_reference_into_verified_workflow()`:

```python
import re

def merge_quick_reference_into_verified_workflow(content: str) -> str:
    # Extract ## Quick Reference block (up to next ## or EOF)
    qr_match = re.search(
        r"^(## Quick Reference\s*\n.*?)(?=^##|\Z)",
        content,
        re.MULTILINE | re.DOTALL,
    )
    qr_block = qr_match.group(1)

    # Demote heading
    qr_as_subsection = re.sub(
        r"^## Quick Reference", "### Quick Reference", qr_block, count=1
    )

    # Remove from original position, insert after ## Verified Workflow
    content_without_qr = content[:qr_match.start()] + content[qr_match.end():]
    vw_match = re.search(r"^## Verified Workflow[^\n]*\n", content_without_qr, re.MULTILINE)
    insert_pos = vw_match.end()
    subsection_text = "\n" + qr_as_subsection.lstrip("\n")
    return content_without_qr[:insert_pos] + subsection_text + content_without_qr[insert_pos:]
```

Key properties:
- **Idempotent**: applying twice produces the same result as applying once
- **No-op guards**: returns unchanged if either section is absent
- **Preserves body content**: only the heading level changes, content is moved intact

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
|---------|----------------|---------------|----------------|
| Simple string replace `## Quick Reference` → `### Quick Reference` | Used `str.replace()` without extracting and relocating the block | Demoted the heading in place without moving it under Verified Workflow — structural position unchanged | Must extract + remove + reinsert, not just replace heading in place |
| Assert `"## Quick Reference" not in result` | Used plain substring check to verify heading was gone | `### Quick Reference` contains `## Quick Reference` as a substring, so the assertion always failed | Use `re.search(r"^## Quick Reference", result, re.MULTILINE)` to check for top-level heading only |
| Running fix against `.claude/skills/` expecting 54+ hits | Assumed Odyssey `.claude/skills/` format would trigger the warning | Odyssey files have `## Workflow` (not `## Verified Workflow`), so 0 files matched the condition | The warning only fires in Mnemosyne format; the 54 affected files live in the migrated `skills/` directory |

## Results & Parameters

| Metric | Value |
|--------|-------|
| Script | `scripts/fix_quick_reference_batch.py` |
| Tests | `tests/scripts/test_fix_quick_reference_batch.py` (33 tests) |
| Target directory | Any `skills/` directory (pass as argument) |
| Default directory | `.claude/skills/` |
| Dry-run flag | `--dry-run` |
| Second-pass validation | Built-in (`verify_no_warnings()`) |
| Files affected in issue #3777 | 54+ in ProjectMnemosyne `skills/` |
| Test pass rate | 33/33 (100%) |
