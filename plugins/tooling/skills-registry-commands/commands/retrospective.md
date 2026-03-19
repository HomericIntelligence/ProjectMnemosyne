---
description: Save session learnings as a new skill plugin
---

# /retrospective

Capture session learnings and create a new flat-format skill file in the ProjectMnemosyne marketplace.

## Target Repository

**Repository**: `HomericIntelligence/ProjectMnemosyne`
**Base branch**: `main`
**Clone location**: `$HOME/.agent-brain/ProjectMnemosyne/`

Single shared clone in user's home directory. Automatically cleaned after PR creation.
Automatically skipped if already running in the ProjectMnemosyne repository.

## Instructions

When the user invokes this command:

1. **Analyze the conversation** to extract:
   - Objective: What was the user trying to accomplish?
   - Steps taken: What approaches were tried?
   - Successes: What worked?
   - Failures: What didn't work and why?
   - Parameters: What configs/settings were used?

2. **Auto-generate skill metadata** (NO user prompting):
   - Analyze conversation topic to extract: `<topic>-<subtopic>`
   - Generate short 4-word summary from key learning
   - Filename: `<topic>-<subtopic>-<short-4-word-summary>` (kebab-case)
   - Auto-detect category from conversation context (training, evaluation, optimization, debugging, architecture, tooling, ci-cd, testing, documentation)

3. **Setup repository**:
   ```bash
   # Detect if already in ProjectMnemosyne
   CURRENT_REMOTE=$(git remote get-url origin 2>/dev/null || echo "")
   if [[ "$CURRENT_REMOTE" == *"ProjectMnemosyne"* ]] && [[ "$CURRENT_REMOTE" != *"ProjectMnemosyne-"* ]]; then
     # Already in ProjectMnemosyne - work in current directory
     MNEMOSYNE_DIR="."
     NEED_CLEANUP=false
   else
     # Use shared home directory location
     MNEMOSYNE_DIR="$HOME/.agent-brain/ProjectMnemosyne"
     NEED_CLEANUP=true

     if [ ! -d "$MNEMOSYNE_DIR" ]; then
       # Clone fresh
       mkdir -p "$HOME/.agent-brain"
       gh repo clone HomericIntelligence/ProjectMnemosyne "$MNEMOSYNE_DIR"
     fi

     # Always update to latest main before starting
     git -C "$MNEMOSYNE_DIR" fetch origin
     git -C "$MNEMOSYNE_DIR" checkout main
     git -C "$MNEMOSYNE_DIR" pull --ff-only origin main

     cd "$MNEMOSYNE_DIR"
   fi

   # Create branch from origin/main (clean state)
   git checkout -b skill/<name> origin/main
   ```

4. **Generate skill file** as flat `skills/<name>.md`:

   > ✅ New flat format: Single `.md` file in `skills/` root (not nested directories or plugin.json)

   **File 1: `skills/<name>.md`** with **YAML frontmatter + markdown body**:

   ```yaml
   ---
   name: <skill-name>
   description: "Brief description of what this skill teaches. Use when: (1) trigger1, (2) trigger2."
   category: <category>
   date: YYYY-MM-DD
   version: "1.0.0"
   user-invocable: false
   tags: []
   ---

   # Skill Title

   ## Overview

   | Field | Value |
   |-------|-------|
   | **Date** | YYYY-MM-DD |
   | **Objective** | What was this skill developed to accomplish? |
   | **Outcome** | Was it successful? Operational? |

   ## When to Use

   - Trigger condition 1
   - Trigger condition 2

   ## Verified Workflow

   ### Quick Reference

   ```bash
   # Copy-paste ready commands
   command --flag value
   ```

   ### Detailed Steps

   1. Step 1 description
   2. Step 2 description

   ## Failed Attempts

   | Attempt | What Was Tried | Why It Failed | Lesson Learned |
   |---------|----------------|---------------|----------------|
   | Attempt 1 | Description | Why failed | Lesson |

   ## Results & Parameters

   [Copy-paste ready configs and expected outputs]

   ## Verified On

   | Project | Context | Details |
   |---------|---------|---------|
   | ProjectMnemosyne | Session context | [notes.md](./skills/<name>.notes.md) |
   ```

   Rules:
   - Filename: lowercase kebab-case (`^[a-z0-9-]+$`) — e.g., `training-grpo-external-vllm-setup.md`
   - `category`: one of 9 valid categories (no "refactoring" — use "architecture")
   - All required fields in frontmatter: name, description, category, date, version
   - All required markdown sections: Overview, When to Use, Verified Workflow, Failed Attempts, Results & Parameters

   **File 2: `skills/<name>.notes.md`** (optional):
   - Raw session details, code snippets, debugging logs
   - Human-readable reference material
   - Only create if additional context needed beyond main skill file

5. **Validate skill** (MUST pass before committing):

   ### Pre-Commit Validation Checklist

   Before running `validate_plugins.py`, verify:

   | # | Check | Error If Missing |
   |---|-------|------------------|
   | 1 | Skill is in `skills/<name>.md` (flat, NOT nested) | File in wrong location |
   | 2 | YAML frontmatter starts with `---` | "missing YAML frontmatter" |
   | 3 | Frontmatter has: name, description, category, date, version | "Missing required field: X" |
   | 4 | `category` is one of: training, evaluation, optimization, debugging, architecture, tooling, ci-cd, testing, documentation | "Invalid category" |
   | 5 | Markdown has all 5 sections: Overview, When to Use, Verified Workflow, Failed Attempts, Results & Parameters | "Missing required section" |
   | 6 | `## Failed Attempts` has pipe-delimited table | "Failed Attempts table missing required columns" |
   | 7 | `## Quick Reference` is subsection `### Quick Reference` (under Verified Workflow) | "Quick Reference should use ###" |

   ```bash
   python3 scripts/validate_plugins.py
   ```
   If validation fails, fix errors and re-run. Do NOT commit until it passes.

6. **Commit and push**:
   ```bash
   git add skills/<name>.md skills/<name>.notes.md 2>/dev/null || true
   git commit -m "feat: add <name> skill

Documents <brief description of what was learned>.

Key learnings:
- <bullet 1>
- <bullet 2>
- <bullet 3>

Co-Authored-By: Claude Sonnet 4.6 <noreply@anthropic.com>"

   git push -u origin skill/<name>
   ```

7. **Create PR** (only if push succeeded):
   ```bash
   gh pr create --repo HomericIntelligence/ProjectMnemosyne --base main \
     --title "feat: add <name> skill" \
     --body "## Summary

Documents <brief description of what was learned>.

- <Key point 1>
- <Key point 2>
- <Key point 3>

## Key Findings

**What Worked**:
- <Successful approach 1>
- <Successful approach 2>

**What Failed**:
- <Failed attempt 1> → <Why it failed>

## Test Plan

- [ ] Validate with \`python3 scripts/validate_plugins.py\`
- [ ] Verify skill appears in marketplace
- [ ] Test skill discovery with relevant keywords

Co-Authored-By: Claude Sonnet 4.6 <noreply@anthropic.com>"
   ```

8. **Cleanup** (if cloned to $HOME/.agent-brain):
   ```bash
   if [ "$NEED_CLEANUP" = true ]; then
     # After PR created, remove the worktree clone
     rm -rf "$HOME/.agent-brain/ProjectMnemosyne"
   fi
   ```

## Common Issues & Solutions

### Top Validation Failures

| Error | Cause | Fix |
|-------|-------|-----|
| "Missing required field: X" | Frontmatter missing a field | Add field to YAML: name, description, category, date, version |
| "Invalid category" | Category not in approved list | Use one of: training, evaluation, optimization, debugging, architecture, tooling, ci-cd, testing, documentation |
| "missing YAML frontmatter" | Doesn't start with `---` | Add `---` at very top of file before metadata |
| "Missing required section: X" | Missing Overview/When/Workflow/Failed/Results | Add all 5 sections with `##` headers |
| "Failed Attempts table missing required columns" | Table format incorrect | Use: \| Attempt \| What Was Tried \| Why It Failed \| Lesson Learned \| |
| "Quick Reference should use ###" | Using `## Quick Reference` instead of `###` | Demote to `### Quick Reference` (subsection of Verified Workflow) |
| Skill not in marketplace | File not committed or in wrong location | Verify in `skills/<name>.md` (root of skills dir, not nested) |

### Issue: PR already exists

**Cause**: Branch was already pushed in previous attempt.

**Solution**: Either delete the branch and re-push, or update the existing PR:
```bash
# Delete old branch and try again
git push origin :skill/<name>
git push -u origin skill/<name>

# OR update existing PR
git push origin skill/<name>
```

### Issue: Cleanup directory

**Cause**: Shared clone at `$HOME/.agent-brain/ProjectMnemosyne` takes up disk space.

**Solution**: Safe to delete anytime — re-clones automatically on next `/advise` or `/retrospective`:
```bash
rm -rf $HOME/.agent-brain/ProjectMnemosyne
```

## Required Sections

| Section | Format | Purpose |
|---------|--------|---------|
| **YAML frontmatter** | Starts with `---`, includes name/description/category/date/version | Metadata for marketplace |
| **Overview** | `## Overview` with table (date, objective, outcome) | Quick context |
| **When to Use** | Bullet points with trigger conditions | Discoverability |
| **Verified Workflow** | Steps that worked + `### Quick Reference` subsection | The actual solution |
| **Failed Attempts** | Table: Attempt, What Was Tried, Why Failed, Lesson | Prevent wasted effort |
| **Results & Parameters** | Copy-paste configs, expected outputs | Actionable reference |

## Example

```
/skills-registry-commands:retrospective
```

Claude will analyze the session, auto-generate the skill filename, and guide you through creating a new flat-format skill file.
