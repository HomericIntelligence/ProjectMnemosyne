---
name: deduplicate-test-fixtures
description: "Eliminate duplicated test fixture files using runtime block-based composition. Use when: test fixtures have duplicate YAML blocks, find | md5sum shows duplication, want single source of truth for shared configs."
category: testing
date: 2026-01-02
---

# Deduplicate Test Fixtures

Eliminate duplicated test fixture files by using runtime block-based composition.

## Overview

| Field | Value |
|-------|-------|
| **Date** | 2026-01-02 |
| **Category** | testing |
| **Objective** | Eliminate duplicated test fixture files by using runtime block-based composition |
| **Outcome** | SUCCESS - Removed 1034 files (239,888 lines), reduced fixture size by 16% |

## When to Use

Use this skill when:

- Test fixtures contain many copies of the same file across different test directories
- You notice the same markdown/config content duplicated in 10+ locations
- Repository size is growing due to test fixture duplication
- `find | md5sum | sort | uniq -c` shows high duplication counts

Trigger conditions:

- Running `find tests -name "*.md" | xargs md5sum | sort | uniq -c | sort -rn | head -5` shows counts > 10
- Test fixture directories follow a pattern like `test-XXX/tierY/subtestZ/`
- A shared resources directory exists or can be created

## Verified Workflow

### Step 1: Identify Duplication Pattern

```bash
# Find most duplicated files by content hash
find tests -type f -name "*.md" | xargs md5sum | awk '{print $1}' | sort | uniq -c | sort -rn | head -20

# See which files share the same hash
find tests -type f -name "*.md" | xargs md5sum | grep "<hash-from-above>"
```

### Step 2: Check for Existing Infrastructure

Look for existing composition or symlink mechanisms:

```bash
# Search for compose/symlink functions
grep -r "_compose\|_symlink\|resources" src/ --include="*.py"

# Check for shared resources directory
ls -la tests/*/shared/ 2>/dev/null
```

### Step 3: Create Shared Blocks Directory

If not exists, decompose the duplicated content into reusable blocks:

```text
tests/shared/blocks/
├── B01-section-name.md
├── B02-another-section.md
└── ...
```

### Step 4: Create Migration Script

Create a script that:

1. Maps directory names to block compositions
2. Updates config.yaml with `resources` specification
3. Deletes duplicated files after config update

```python
# Key mapping structure
DIRECTORY_TO_BLOCKS = {
    "00-empty": [],
    "01-vanilla": [],
    "02-specific": ["B02"],
    "03-full": ["B01", "B02", "B03", ...],
}
```

### Step 5: Run with Dry-Run First

```bash
python scripts/migrate_to_blocks.py tests/fixtures/tests/ --dry-run
```

Verify output shows expected updates before running for real.

### Step 6: Execute Migration

```bash
python scripts/migrate_to_blocks.py tests/fixtures/tests/
```

### Step 7: Verify

```bash
# Check no duplicates remain
find tests -type f -name "CLAUDE.md" -path "*/t0/*" | wc -l  # Should be 0

# Check size reduction
du -sh tests/fixtures/
```

## Failed Attempts


| Attempt | Why Failed | Lesson |
|---------|-----------|--------|
| Initial approach | See details below | Refer to notes in this section |

### 1. Misidentified Source of Duplication

**What happened**: Initial assumption was that agent markdown files (e.g., `implementation-review-specialist.md`) were duplicated 66 times.

**Actual situation**: The duplication was CLAUDE.md files in T0 tier directories (1034 copies), not agent files.

**Lesson**: Always run the hash analysis first to identify the actual source of duplication before planning a solution.

### 2. Incomplete Previous Migration

**What happened**: A prior commit (d7dfeb9) claimed to "remove 197MB duplication" but the duplicated files still existed.

**Actual situation**: The commit added infrastructure (`_compose_claude_md()` method) but never ran the actual migration to delete files.

**Lesson**: After adding migration infrastructure, always verify the migration actually ran by checking file counts and sizes.

### 3. Scope Creep Risk

**What happened**: T5 tier had some duplicated files but was deferred.

**Decision**: Focus on the largest source of duplication (T0 with 1034 files) and defer smaller sources to follow-up work.

**Lesson**: Set clear scope boundaries. It's better to complete a focused migration than to expand scope and risk incomplete work.

## Results & Parameters

### Config Format

```yaml
# config.yaml format for block-based composition
name: "Full CLAUDE.md"
description: "All 18 blocks"
extends_previous: false
resources:
  claude_md:
    blocks: [B01, B02, B03, B04, B05, B06, B07, B08, B09, B10, B11, B12, B13, B14, B15, B16, B17, B18]
```

### Directory to Block Mapping

```yaml
directory_patterns:
  00-empty: []           # No blocks, no CLAUDE.md generated
  01-vanilla: []         # Tool defaults, no CLAUDE.md
  02-critical-only: [B02]
  03-full: [B01-B18]     # All blocks
  04-minimal: [B01, B02]
  05-core-seven: [B01-B07]
  NN-BXX: [BXX]          # Single block pattern (e.g., 06-B01 → [B01])
```

### Metrics

| Metric | Before | After |
|--------|--------|-------|
| CLAUDE.md files in T0 | 1034 | 0 |
| Fixture size | 56MB | 47MB |
| Lines removed | 0 | 239,888 |
| Config files updated | 0 | 1128 |

## Related Files

- `scripts/migrate_t0_to_blocks.py` - Migration script
- `src/scylla/e2e/tier_manager.py` - Runtime composition (`_compose_claude_md()`)
- `tests/claude-code/shared/blocks/` - Shared block files (B01-B18)
