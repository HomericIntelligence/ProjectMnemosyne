---
name: bulk-skill-migration-script
description: Write an idempotent Python script to bulk-migrate skills from a source
  Claude project to a ProjectMnemosyne marketplace. Handles discovery, SKILL.md transformation,
  category mapping, and skips already-migrated skills.
category: tooling
date: 2026-03-04
version: 1.0.0
user-invocable: false
---
# Bulk Skill Migration Script

Automate bulk migration of skills from a source repo (e.g. ProjectOdyssey2 `.claude/skills/`)
to ProjectMnemosyne's `skills/<category>/<name>/` plugin structure.

## Overview

| Item | Details |
|------|---------|
| Date | 2026-03-04 |
| Objective | Migrate all source skills to Mnemosyne plugin format idempotently |
| Outcome | 4 missing skills ported; 81 already-present skills correctly skipped |

## When to Use

- Porting skills from a source project to ProjectMnemosyne for the first time
- Running incremental migrations when new skills are added to a source project
- Auditing which source skills are missing from Mnemosyne
- Automating the repetitive SKILL.md transformation (frontmatter cleanup, section renames, path generalization)

## Verified Workflow

1. **Audit first** — list source skills vs. Mnemosyne skills to know scope:

   ```bash
   ls /path/to/source/.claude/skills/ | sort > /tmp/source_skills.txt
   ls /path/to/ProjectMnemosyne/skills/ | sort > /tmp/mnemosyne_skills.txt
   comm -23 /tmp/source_skills.txt /tmp/mnemosyne_skills.txt
   ```

2. **Write the migration script** in the source repo's `scripts/` directory with these functions:

   ```python
   def parse_frontmatter(content: str) -> tuple[dict, str]:
       """Parse YAML frontmatter, return (dict, remaining body)."""

   def determine_category(skill_name: str, frontmatter: dict, tier: str | None) -> str:
       """Map source categories to valid Mnemosyne categories."""

   def generalize_content(content: str) -> str:
       """Replace hardcoded paths with <project-root>, <package-manager>, etc."""

   def transform_skill_md(content: str, skill_name: str, category: str) -> str:
       """Full SKILL.md transformation pipeline."""

   def skill_already_exists(skill_name: str) -> bool:
       """Check across all category dirs — idempotency guard."""

   def migrate_skill(...) -> bool:
       """Create .claude-plugin/plugin.json + skills/<name>/SKILL.md."""
   ```

3. **Run dry-run first**:

   ```bash
   python3 scripts/migrate_odyssey_skills.py --dry-run
   ```

4. **Run for real** (skip-existing is default):

   ```bash
   python3 scripts/migrate_odyssey_skills.py
   ```

5. **Validate all plugins** in Mnemosyne:

   ```bash
   cd /path/to/ProjectMnemosyne
   python3 scripts/validate_plugins.py skills/
   ```

6. **Regenerate marketplace index**:

   ```bash
   python3 scripts/generate_marketplace.py
   ```

7. **Commit and PR** in ProjectMnemosyne, then commit the script in source repo.

## Category Mapping Table

| Source Category | Mnemosyne Category |
|---|---|
| `github`, `worktree`, `agent`, `plan`, `generation` | `tooling` |
| `ci`, `phase` | `ci-cd` |
| `mojo` | `architecture` |
| `doc` | `documentation` |
| `quality`, `review` | `evaluation` |
| `testing` | `testing` |
| `analysis`, `ml` | `optimization` |
| `training` | `training` |

## Key Transformations

```python
# Required SKILL.md transformations
body = re.sub(r"^## Workflow\b", "## Verified Workflow", body, flags=re.MULTILINE)

# Path generalization replacements
PATH_REPLACEMENTS = [
    (r"/home/username/ProjectName/", "<project-root>/"),
    (r"\bProjectName\b", "<project-name>"),
    (r"\bpixi run mojo\b", "<package-manager> run mojo"),
    (r"\bpixi run\b", "<package-manager> run"),
]

# Remove Odyssey-specific frontmatter fields
# Keep only: name, description, category, date, user-invocable
FIELDS_TO_REMOVE = {"mcp_fallback", "agent", "tier", "source"}
```

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
|---------|----------------|---------------|----------------|
| Using `comm` with inline `ls` substitution | `ls dir/ \| sort > /tmp/file.txt` in one command | Sort error: "cannot read: ls" — shell quoting issue | Pipe `ls` output separately before passing to sort |
| Checking existence only by top-level dir name | `if (mnemosyne_dir / skill_name).exists()` | Skills may be under category subdirs; flat check misses them | Iterate all category subdirs: `for cat in mnemosyne_skills_dir.iterdir(): if (cat / skill_name).exists()` |
| Regex substitution order matters | Replacing `pixi run mojo` after `pixi run` | `pixi run` replacement fires first, leaving `mojo` dangling | Put more specific patterns (longer strings) before general ones |
| Assuming all tier-2 skills need same category | Mapping all tier-2 to `optimization` | `generate-api-docs` belongs to `documentation`, not `optimization` | Build per-skill override map for tier-2 categories |
| Writing PR body inline with `--body "..."` | Used `"$(cat <<'EOF'...)"` with nested quotes | Special chars broke heredoc quoting in some shells | Write body to a temp file, use `--body-file` flag |

## Results & Parameters

### Script Parameters

| Parameter | Default | Description |
|-----------|---------|-------------|
| `--dry-run` | false | Show planned actions without creating files |
| `--skill NAME` | all | Migrate only a specific skill by name |
| `--force` | false | Overwrite skills that already exist in Mnemosyne |
| `--skip-existing` | true | Skip skills already present (idempotency) |

### Example Output

```
Found 85 skills in Odyssey2
SKIP: gh-create-pr-linked (already exists in Mnemosyne)
...
Processing: worktree-cleanup (category=tooling, tier=None)
  Migrating worktree-cleanup -> skills/tooling/worktree-cleanup/
  OK: skills/tooling/worktree-cleanup/.claude-plugin/plugin.json
  OK: skills/tooling/worktree-cleanup/skills/worktree-cleanup/SKILL.md

Migration Summary:
  Succeeded: 4
  Skipped:   81
  Failed:    0
```

### Validation Pass

```
python3 scripts/validate_plugins.py skills/
-> ALL VALIDATIONS PASSED (377 plugins, 0 errors)
```

## References

- Source script: `scripts/migrate_odyssey_skills.py` in ProjectOdyssey2
- ProjectMnemosyne validator: `scripts/validate_plugins.py`
- Marketplace generator: `scripts/generate_marketplace.py`
- Related skills: `port-reusable-scripts`, `plugin-generalization`, `fix-skill-validation-warnings`
