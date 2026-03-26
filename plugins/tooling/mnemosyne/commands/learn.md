---
description: Save session learnings as a new skill plugin. Use after experiments, debugging sessions, or when you want to preserve team knowledge.
---

# /learn

Capture session learnings and create or amend a skill file in the ProjectMnemosyne marketplace.

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

3. **CRITICAL — Search for existing skills to amend**:

   Before creating a new file, search the registry for skills covering the same topic:

   ```bash
   MNEMOSYNE_DIR="$HOME/.agent-brain/ProjectMnemosyne"
   # Search by keywords from the skill name
   ls "$MNEMOSYNE_DIR/skills/" | grep -i "<keyword1>\|<keyword2>\|<keyword3>" | grep -v ".notes.md" | grep -v ".history"
   # Also search descriptions in frontmatter
   grep -l "<keyword>" "$MNEMOSYNE_DIR/skills/"*.md 2>/dev/null | head -20
   ```

   **If an existing skill covers the same topic → AMEND it** (don't create a new file):

   a. Read the existing skill to understand its current state
   b. Archive the current version to the history log (see Step 4)
   c. Update the skill `.md` in-place with new learnings:
      - Add new Failed Attempts rows to the table
      - Update the Verified Workflow if the approach changed
      - Update Results & Parameters with new data
      - Bump the `version` using **semantic versioning** (see table below)
      - Update the `date` to today

   **Semantic versioning rules for skill amendments:**

   | Change Type | Bump | When to Use | Examples |
   |-------------|------|-------------|----------|
   | **Major** (X.0.0) | `1.0.0` → `2.0.0` | Merge multiple skills, rewrite verified workflow, change core recommendation | Consolidating 5 duplicate skills; replacing recommended API |
   | **Minor** (0.X.0) | `1.0.0` → `1.1.0` | Add new findings, new failed attempts, extend workflow with new steps | Adding 2 Failed Attempts rows; new "When to Use" trigger |
   | **Patch** (0.0.X) | `1.0.0` → `1.0.1` | Fix typos, formatting, metadata corrections, clarify existing text | Fix category typo; fix broken markdown table |
   d. Update the changelog in the history file

   **If no existing skill matches → Create a new skill** (proceed to Step 5)

4. **History log management** (for amendments):

   When amending an existing skill, preserve the previous version in `skills/<name>.history`:

   **File: `skills/<name>.history`**

   This is an append-only log. Each entry records what changed and why. Format:

   ```markdown
   # <skill-name> — History

   ## v2.0.0 (YYYY-MM-DD)

   **Changed by:** Session context (e.g., "PR #5107 gradient checking fixes")
   **Verification:** verified-ci | verified-local | verified-precommit | unverified

   ### What changed
   - Updated tolerance from 1e-2 absolute to rtol=1e-2 + atol=1e-2 combined
   - Added check_gradient() as preferred API over check_gradients()
   - Added 2 new Failed Attempts entries

   ### Why
   Previous approach (v1.0.0) used check_gradients() with absolute tolerance.
   CI showed this fails for multi-channel conv2d where gradient magnitudes reach ~32-126.
   Relative tolerance via check_gradient() handles large magnitudes correctly.

   ### Previous version (v1.0.0) snapshot
   <paste the full previous skill content here as a reference>

   ---

   ## v1.0.0 (YYYY-MM-DD)

   **Initial version.**
   ```

   **Rules for history files:**
   - Append new entries at the TOP (newest first)
   - Always include: version, date, what changed, why, previous snapshot
   - The snapshot preserves the exact previous content for auditability
   - Add a reference from the main skill file: `**History:** [changelog](./skills/<name>.history)`

5. **CRITICAL — Honesty gate for "Verified Workflow"**:

   Before writing the "Verified Workflow" section, answer these questions honestly:
   - Was the workflow actually executed end-to-end? (Not just pre-commit hooks — the actual tests/code)
   - Did CI pass with these changes? If not, the section MUST be titled "Proposed Workflow" not "Verified Workflow"
   - Were the results observed in CI, or only locally? If only locally, state: "Verified locally only — CI validation pending"

   **Verification levels** (must be stated in the skill):
   - `verified-ci`: Tests pass in CI (highest confidence)
   - `verified-local`: Tests pass locally but not confirmed in CI
   - `verified-precommit`: Only pre-commit hooks pass (formatting, linting)
   - `unverified`: Approach is theoretically sound but never executed

   Add this as a frontmatter field:
   ```yaml
   verification: verified-ci | verified-local | verified-precommit | unverified
   ```

6. **Setup repository**:
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

7. **Generate or amend skill file** as flat `skills/<name>.md`:

   > New flat format: Single `.md` file in `skills/` root (not nested directories or plugin.json)

   **File 1: `skills/<name>.md`** with **YAML frontmatter + markdown body**:

   ```yaml
   ---
   name: <skill-name>
   description: "Brief description of what this skill teaches. Use when: (1) trigger1, (2) trigger2."
   category: <category>
   date: YYYY-MM-DD
   version: "1.0.0"
   user-invocable: false
   verification: <verified-ci|verified-local|verified-precommit|unverified>
   history: <name>.history  # Only present if skill has been amended
   tags: []
   ---

   # Skill Title

   ## Overview

   | Field | Value |
   |-------|-------|
   | **Date** | YYYY-MM-DD |
   | **Objective** | What was this skill developed to accomplish? |
   | **Outcome** | Was it successful? Operational? |
   | **Verification** | verified-ci / verified-local / verified-precommit / unverified |
   | **History** | [changelog](./<name>.history) |

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
   | ProjectName | Session context | [notes.md](./skills/<name>.notes.md) |
   ```

   Rules:
   - Filename: lowercase kebab-case (`^[a-z0-9-]+$`) — e.g., `training-grpo-external-vllm-setup.md`
   - `category`: one of 9 valid categories (no "refactoring" — use "architecture")
   - All required fields in frontmatter: name, description, category, date, version, verification
   - All required markdown sections: Overview, When to Use, Verified Workflow, Failed Attempts, Results & Parameters
   - **If verification is `unverified` or `verified-precommit`**: rename the section to "Proposed Workflow" instead of "Verified Workflow" and add a warning: "> **Warning:** This workflow has not been validated end-to-end. Treat as a hypothesis until CI confirms."

   **File 2: `skills/<name>.notes.md`** (optional):
   - Raw session details, code snippets, debugging logs
   - Human-readable reference material
   - Only create if additional context needed beyond main skill file

   **File 3: `skills/<name>.history`** (created on first amendment):
   - Append-only changelog with version snapshots
   - Referenced from main skill file via `history` frontmatter field
   - See Step 4 for format

8. **Validate skill** (MUST pass before committing):

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

9. **Commit and push**:
   ```bash
   # For new skills:
   git add skills/<name>.md skills/<name>.notes.md 2>/dev/null || true
   git commit -m "feat: add <name> skill

Documents <brief description of what was learned>.

Verification: <verified-ci|verified-local|verified-precommit|unverified>

Key learnings:
- <bullet 1>
- <bullet 2>
- <bullet 3>

Co-Authored-By: Claude Sonnet 4.6 <noreply@anthropic.com>"

   # For amendments:
   git add skills/<name>.md skills/<name>.history skills/<name>.notes.md 2>/dev/null || true
   git commit -m "feat: amend <name> skill (v<X.0.0>)

<Brief description of what changed and why>.

Verification: <level>
Previous version archived in <name>.history

Key changes:
- <change 1>
- <change 2>

Co-Authored-By: Claude Sonnet 4.6 <noreply@anthropic.com>"

   git push -u origin skill/<name>
   ```

10. **Create PR** (only if push succeeded):
    ```bash
    gh pr create --repo HomericIntelligence/ProjectMnemosyne --base main \
      --title "feat: <add|amend> <name> skill" \
      --body "## Summary

<New skill | Amends existing skill from v<old> to v<new>>.

Documents <brief description of what was learned>.

- <Key point 1>
- <Key point 2>
- <Key point 3>

## Verification Level

**<verified-ci|verified-local|verified-precommit|unverified>**

<If not verified-ci, explain what is pending>

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

    # Enable auto-merge so the PR merges automatically once CI passes
    gh pr merge --auto --rebase --repo HomericIntelligence/ProjectMnemosyne
    ```

11. **Cleanup** (if cloned to $HOME/.agent-brain):
    ```bash
    if [ "$NEED_CLEANUP" = true ]; then
      # After PR created, remove the worktree clone
      rm -rf "$HOME/.agent-brain/ProjectMnemosyne"
    fi
    ```

## Amendment Workflow Summary

```text
Existing skill found?
├─ YES → Amend workflow:
│   1. Read existing skill
│   2. Create/append to <name>.history with previous version snapshot
│   3. Update <name>.md in-place (new data, bump version, update date)
│   4. Add history frontmatter field if first amendment
│   5. Commit both files
│
└─ NO → New skill workflow:
    1. Create <name>.md with full template
    2. Optionally create <name>.notes.md
    3. No history file needed yet
    4. Commit
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

**Solution**: Safe to delete anytime — re-clones automatically on next `/advise` or `/learn`:
```bash
rm -rf $HOME/.agent-brain/ProjectMnemosyne
```

## Required Sections

| Section | Format | Purpose |
|---------|--------|---------|
| **YAML frontmatter** | Starts with `---`, includes name/description/category/date/version/verification | Metadata for marketplace |
| **Overview** | `## Overview` with table (date, objective, outcome, verification) | Quick context |
| **When to Use** | Bullet points with trigger conditions | Discoverability |
| **Verified Workflow** | Steps that worked + `### Quick Reference` subsection | The actual solution |
| **Failed Attempts** | Table: Attempt, What Was Tried, Why Failed, Lesson | Prevent wasted effort |
| **Results & Parameters** | Copy-paste configs, expected outputs | Actionable reference |

## Example

```
/mnemosyne:learn
```

Claude will analyze the session, check for existing skills to amend, and either update an existing skill (with history) or create a new one.
