---
name: delete-deprecated-skills
description: "Delete deprecated skill directories and update all cross-references. Use when: skills reference removed systems, cleanup issues list DEPRECATED-marked skills, or planning-system migration leaves orphaned skill files."
category: tooling
date: 2026-03-05
user-invocable: false
---

# Delete Deprecated Skills

## Overview

| Item | Details |
|------|---------|
| Name | delete-deprecated-skills |
| Category | tooling |
| Description | Delete deprecated skill directories and scrub all references from documentation, agent configs, and scripts. |
| Trigger | Cleanup issues listing DEPRECATED-marked skill directories |

## When to Use

- A GitHub issue requests deleting skill directories marked `DEPRECATED`
- Skills reference a removed system (e.g. `notes/plan/` directory no longer exists)
- Planning-system migration leaves orphaned `.claude/skills/` directories
- `CLAUDE.md` Available Skills list contains skills that no longer exist

## Verified Workflow

### Step 1: Confirm directories exist

```bash
ls -la .claude/skills/ | grep <pattern>
```

### Step 2: Find ALL references before deleting

```bash
# Grep across entire repo - captures docs, agents, scripts, CLAUDE.md
grep -r "skill-name-1\|skill-name-2\|skill-name-3" . --include="*.md" --include="*.py" \
  --include="*.yaml" --include="*.yml" -l
```

Key files to check:

- `CLAUDE.md` - Available Skills list section
- `.claude/agents/*.md` - Skills tables and Delegation Patterns sections
- `.claude/skills/*/SKILL.md` - Cross-skill references
- `docs/dev/skills-architecture.md` - Architecture documentation
- `scripts/*.py` - Code generators that emit skill references

### Step 3: Delete the directories

```bash
rm -rf .claude/skills/<name-1>/ .claude/skills/<name-2>/ .claude/skills/<name-3>/
```

### Step 4: Update each reference file

For `CLAUDE.md` - remove from the `**Available Skills**` bullet list:

```markdown
# Remove entire category line if all skills in it are deprecated
- **Plan**: plan-regenerate-issues, plan-validate-structure, plan-create-component
```

For agent `.md` files - remove rows from Skills tables and Delegation Patterns lists:

```markdown
# Remove table row
| `plan-regenerate-issues` | Syncing modified plans with GitHub |

# Remove list item
- `plan-validate-structure` - Validating section structure
```

For `docs/dev/skills-architecture.md` - remove entire subsections for each skill:

```markdown
### 8. Plan Management Skills

#### plan-regenerate-issues
...entire subsection...

#### plan-validate-structure
...entire subsection...
```

For Python scripts - remove lines that emit deprecated skill references:

```python
# Remove lines like:
section.append("- `plan-validate-structure` - Validating section structure")
```

### Step 5: Verify no remaining references

```bash
grep -r "skill-name-1\|skill-name-2\|skill-name-3" . --include="*.md" --include="*.py" -l
# Should return only the task/prompt file, not real project files
```

### Step 6: Run pre-commit hooks

```bash
pixi run pre-commit run --all-files
# Mojo format hook may fail due to GLIBC version in local env - this is pre-existing
# All markdown, Python, YAML hooks should pass
```

### Step 7: Commit, push, and create PR

```bash
git add <specific files only - not task prompt files>
git commit -m "chore(skills): delete deprecated <pattern> skill directories and update references"
git push -u origin <branch>
gh pr create --title "..." --body "Closes #<issue>"
gh pr merge --auto --rebase
```

## Results & Parameters

### Session Results (Issue #3063)

Deleted 3 skill directories:

- `.claude/skills/plan-validate-structure/`
- `.claude/skills/plan-create-component/`
- `.claude/skills/plan-regenerate-issues/`

Updated 8 files:

| File | Change |
|------|--------|
| `CLAUDE.md` | Removed `**Plan**` category bullet (3 skills) |
| `.claude/agents/foundation-orchestrator.md` | Removed 2 references (Skills table + Delegation Patterns) |
| `.claude/agents/papers-orchestrator.md` | Removed 1 reference (Skills table) |
| `.claude/agents/shared-library-orchestrator.md` | Removed 1 reference (Skills table) |
| `.claude/agents/tooling-orchestrator.md` | Removed 1 reference (Skills table) |
| `.claude/skills/track-implementation-progress/SKILL.md` | Removed 1 cross-skill reference |
| `docs/dev/skills-architecture.md` | Removed entire `### 8. Plan Management Skills` subsection + implementation roadmap entries |
| `scripts/update_agents_claude4.py` | Removed 2 lines that emit deprecated skill references |

### Key Grep Pattern Used

```bash
grep -r "plan-validate-structure|plan-create-component|plan-regenerate-issues" \
  . --include="*.md" --include="*.py" -l
```

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
|---------|----------------|---------------|----------------|
| Glob to find skill dirs | `Glob("**/.claude/skills/plan-*")` | Returned no results despite dirs existing | Glob has path restrictions; use `ls` via Bash to confirm directory existence |
| Assuming only CLAUDE.md needed updates | Checked only CLAUDE.md initially | Missed 7 other files with references | Always grep the entire repo before and after deleting to find all references |
| Forgetting Python scripts | Ran grep on `.md` files only | Missed `scripts/update_agents_claude4.py` which generates agent configs | Include `--include="*.py"` in grep sweep |
