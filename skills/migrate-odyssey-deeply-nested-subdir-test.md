---
name: migrate-odyssey-deeply-nested-subdir-test
description: 'Pattern for testing multi-level directory nesting in shutil.copytree
  migrations. Use when: adding coverage for recursive copy of auxiliary subdirectories,
  verifying deep paths survive migration.'
category: testing
date: 2026-03-15
version: 1.0.0
user-invocable: false
---
## Overview

| Field | Value |
| ------- | ------- |
| **Skill** | migrate-odyssey-deeply-nested-subdir-test |
| **Category** | testing |
| **Task** | Add pytest test verifying deeply nested subdirs (e.g. `scripts/utils/helper.sh`) survive a `shutil.copytree`-based migration |
| **Language** | Python / pytest |
| **Trigger** | Issue requests test coverage for multi-level nesting inside auxiliary subdirs of a migration script |

## When to Use

- An issue mentions "no tests verifying multi-level nesting" for a copytree-based migration.
- Existing tests only cover flat files within a subdirectory (e.g. `scripts/run.sh`) but not nested paths (`scripts/utils/helper.sh`).
- The migration uses `shutil.copytree`, which is recursive by default, but coverage is missing.
- A follow-up issue from a parent migration issue requests nesting tests.

## Verified Workflow

### Quick Reference

```python
# Pattern: create a nested dir inside an existing auxiliary subdir, assert it arrives at dest
nested_dir = skill_dir / "scripts" / "utils"
nested_dir.mkdir(parents=True)
(nested_dir / "helper.sh").write_text("#!/bin/bash\necho helper")

# ... call migrate_skill(...)

nested_helper = (
    mnemosyne_skills
    / "tooling" / "agent-run-orchestrator"
    / "skills" / "agent-run-orchestrator"
    / "scripts" / "utils" / "helper.sh"
)
assert nested_helper.exists(), f"Expected deeply nested helper at {nested_helper}"
```

### Step 1 — Read the existing test file

Find which test class covers auxiliary subdirectory copying (e.g. `TestMigrateSkillAuxiliaryDirs`).
Identify the nearest similar test (`test_skill_with_nested_scripts_content`) to use as a template.

### Step 2 — Identify the insertion point

The new test should be added directly after the flat-nesting test and before unrelated tests
(e.g. `test_dry_run_does_not_copy_files`). This keeps related tests grouped.

### Step 3 — Use the existing `make_skill_dir` helper

The test helper already creates the base skill directory structure. Call it first, then
**manually create** the nested subdirectory within `scripts/`:

```python
skill_dir = make_skill_dir(odyssey_skills, "agent-run-orchestrator")
nested_dir = skill_dir / "scripts" / "utils"
nested_dir.mkdir(parents=True)
(nested_dir / "helper.sh").write_text("#!/bin/bash\necho helper")
```

Note: `make_skill_dir` returns the skill root directory — capture the return value.

### Step 4 — Assert the full path at the destination

Build the expected destination path component by component. The migration places content at:

```
mnemosyne_skills / <category> / <skill-name> / "skills" / <skill-name> / <subdir> / ...
```

So for `scripts/utils/helper.sh`:

```python
nested_helper = (
    mnemosyne_skills
    / "tooling"
    / "agent-run-orchestrator"
    / "skills"
    / "agent-run-orchestrator"
    / "scripts"
    / "utils"
    / "helper.sh"
)
assert nested_helper.exists(), f"Expected deeply nested helper at {nested_helper}"
```

### Step 5 — Run only the affected test class to confirm

```bash
pixi run python -m pytest tests/scripts/test_migrate_odyssey_skills.py::TestMigrateSkillAuxiliaryDirs -v
```

All tests in the class (not just the new one) must pass before committing.

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
| --------- | ---------------- | --------------- | ---------------- |
| N/A — direct approach worked | Read existing test class, identified pattern, inserted test immediately | — | The flat-nesting test (`test_skill_with_nested_scripts_content`) was a perfect template; no iteration needed |

## Results & Parameters

**Test added**: `test_skill_with_deeply_nested_scripts_subdir`

**Class**: `TestMigrateSkillAuxiliaryDirs`

**File**: `tests/scripts/test_migrate_odyssey_skills.py`

**Run command**:

```bash
pixi run python -m pytest tests/scripts/test_migrate_odyssey_skills.py::TestMigrateSkillAuxiliaryDirs -v
```

**Result**: 12/12 passed (11 pre-existing + 1 new)

**Key insight**: `shutil.copytree` is recursive by default, so no code change was needed — only
a test to verify the behavior is exercised and protected against future regressions.
