---
description: Save session learnings as a new skill plugin
---

# /retrospective

Capture session learnings and create a new skill plugin in the ProjectMnemosyne marketplace.

## Target Repository

**Repository**: `HomericIntelligence/ProjectMnemosyne`
**Base branch**: `main`
**Clone location**: `<ProjectRoot>/build/<PID>/ProjectMnemosyne/`

Each Claude Code session gets its own isolated clone (via process ID) to avoid interference.
Automatically skipped if already running in the ProjectMnemosyne repository.

## Instructions

When the user invokes this command:

1. **Analyze the conversation** to extract:
   - Objective: What was the user trying to accomplish?
   - Steps taken: What approaches were tried?
   - Successes: What worked?
   - Failures: What didn't work and why?
   - Parameters: What configs/settings were used?

2. **Prompt for metadata**:
   - Category (training, evaluation, optimization, debugging, architecture, tooling, ci-cd, testing, documentation)
   - Skill name (kebab-case)

3. **Setup repository**:
   ```bash
   # Detect if already in ProjectMnemosyne
   CURRENT_REMOTE=$(git remote get-url origin 2>/dev/null || echo "")
   if [[ "$CURRENT_REMOTE" == *"ProjectMnemosyne"* ]] && [[ "$CURRENT_REMOTE" != *"ProjectMnemosyne-"* ]]; then
     # Already in ProjectMnemosyne - work in current directory
     MNEMOSYNE_DIR="."
   else
     # Use PID-scoped build directory - NEVER modify local repo
     MNEMOSYNE_DIR="build/$$/ProjectMnemosyne"

     if [ ! -d "$MNEMOSYNE_DIR" ]; then
       # Clone fresh
       mkdir -p "build/$$"
       gh repo clone HomericIntelligence/ProjectMnemosyne "$MNEMOSYNE_DIR"
     else
       # Update existing clone
       # Ensure we're on main branch
       if ! git -C "$MNEMOSYNE_DIR" symbolic-ref HEAD | grep -q "refs/heads/main"; then
         echo "Error: $MNEMOSYNE_DIR is not on main branch."
         echo "Fix: rm -rf build/$$"
         exit 1
       fi

       # Ensure no local commits or conflicts
       if ! git -C "$MNEMOSYNE_DIR" pull --ff-only origin main; then
         echo "Error: Cannot fast-forward $MNEMOSYNE_DIR/main. May have local commits or conflicts."
         echo "Fix: rm -rf build/$$"
         exit 1
       fi
     fi

     cd "$MNEMOSYNE_DIR"
   fi

   # Create branch from origin/main (clean state)
   git checkout -b skill/<category>/<name> origin/main
   ```

4. **Generate plugin files** in `skills/<category>/<name>/`:

   **File 1: `.claude-plugin/plugin.json`**
   ```json
   {
     "name": "<skill-name>",
     "version": "1.0.0",
     "description": "<description>. Use when: (1) trigger1, (2) trigger2.",
     "category": "<category>",
     "date": "YYYY-MM-DD",
     "tags": ["tag1", "tag2", "tag3"]
   }
   ```
   Rules:
   - `name`: Must match directory name, lowercase kebab-case (`^[a-z0-9-]+$`)
   - `description`: 20+ characters, include "Use when:" trigger conditions
   - No extra fields — only name, version, description, category, date, tags
   - ⚠️ The `version` field is REQUIRED — omitting it will fail CI.

   **File 2: `skills/<name>/SKILL.md`** with **required format**:
   > ⚠️ SKILL.md must be at `skills/<name>/SKILL.md` (nested directory), NOT at the plugin root.

   ```yaml
   ---
   name: skill-name
   description: "Brief description. Use when: specific triggers."
   category: <category>
   date: YYYY-MM-DD
   user-invocable: false
   ---
   ```

   Required sections:
   - ✅ **YAML frontmatter** (starts with `---`)
   - ✅ **Overview section** with `## Overview` header and table
   - ✅ **When to Use** with specific trigger conditions
   - ✅ **Verified Workflow** (exact header — NOT "## Workflow")
   - ✅ **Failed Attempts table** (MUST be table format, not prose):
     ```markdown
     ## Failed Attempts

     | Attempt | What Was Tried | Why It Failed | Lesson Learned |
     |---------|----------------|---------------|----------------|
     | ... | ... | ... | ... |
     ```
   - ✅ **Results & Parameters** with copy-paste configs

   **File 3: `references/notes.md`** with raw session details

5. **Validate plugin** (MUST pass before committing):

   ### Pre-Commit Validation Checklist

   Before running `validate_plugins.py`, verify these common failure points:

   | # | Check | Common Error |
   |---|-------|-------------|
   | 1 | `.claude-plugin/plugin.json` exists | "Missing .claude-plugin/plugin.json" |
   | 2 | `plugin.json` has `name`, `version`, `description` fields | "Missing required fields: version" |
   | 3 | `skills/<name>/SKILL.md` exists (nested under `skills/`) | "Missing skills/ directory" |
   | 4 | SKILL.md starts with `---` YAML frontmatter | "missing YAML frontmatter" |
   | 5 | `## Failed Attempts` section exists with pipe-delimited table | "Missing Failed Attempts section" |
   | 6 | `category` is one of: training, evaluation, optimization, debugging, architecture, tooling, ci-cd, testing, documentation | "Invalid category" |

   ```bash
   python3 scripts/validate_plugins.py skills/
   ```
   If validation fails, fix errors and re-run. Do NOT commit until it passes.

6. **Commit and push**:
   ```bash
   git add skills/<category>/<name>/
   git commit -m "feat: add <name> skill

Documents <brief description>.

Key learnings:
- <bullet 1>
- <bullet 2>
- <bullet 3>

🤖 Generated with [Claude Code](https://claude.com/claude-code)

Co-Authored-By: Claude <noreply@anthropic.com>"

   git push -u origin skill/<category>/<name>
   ```

7. **Create PR** (only if push succeeded):
   ```bash
   # Write PR body to build directory (use $MNEMOSYNE_DIR from step 3)
   cat > "$MNEMOSYNE_DIR/pr-body-<name>.md" << 'EOF'
   ## Summary

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
   - <Failed attempt 2> → <Why it failed>

   ## Test Plan

   - [ ] Validate plugin with `python3 scripts/validate_plugins.py skills/`
   - [ ] Install plugin and verify skill appears
   - [ ] Check skill activation with relevant triggers

   🤖 Generated with [Claude Code](https://claude.com/claude-code)
   EOF

   gh pr create --repo HomericIntelligence/ProjectMnemosyne --base main \
     --title "feat: add <name> skill" \
     --body-file "$MNEMOSYNE_DIR/pr-body-<name>.md"

   # After successful PR creation, clean up the feature branch
   BRANCH_NAME="skill/<category>/<name>"
   git checkout main
   git branch -D "$BRANCH_NAME"
   ```

## Common Issues & Solutions

### Top CI Failures (Most Common)

| Error | Cause | Fix |
|-------|-------|-----|
| "Missing .claude-plugin/plugin.json" | Forgot to create plugin.json | Create `.claude-plugin/plugin.json` from SKILL.md frontmatter |
| "Missing required fields: version" | plugin.json missing `version` | Add `"version": "1.0.0"` to plugin.json |
| "Missing skills/ directory" | SKILL.md at wrong path | Move SKILL.md to `skills/<name>/SKILL.md` (nested) |
| "missing YAML frontmatter" | SKILL.md doesn't start with `---` | Add `---` YAML block at top of SKILL.md |
| "Missing Failed Attempts section" | Section absent or wrong format | Add `## Failed Attempts` with pipe-delimited table |

### Issue: "No commits between main and skill/..."

**Cause**: The branch was already merged or rebased incorrectly.

**Solution**: Don't rebase. Create branch directly from `origin/main`:
```bash
git checkout -b skill/<category>/<name> origin/main
```

### Issue: Build directory cleanup

**Cause**: Multiple Claude Code sessions accumulate build directories.

**Solution**: Periodically clean old build directories:
```bash
# Remove all PID-scoped build directories
rm -rf build/*/ProjectMnemosyne

# Or remove the entire build directory
rm -rf build/
```
The next `/advise` or `/retrospective` will re-clone automatically.

## Required SKILL.md Sections

| Section | Format |
|---------|--------|
| **YAML frontmatter** | Starts with `---`, includes name/description/category/date/user-invocable |
| **Overview section** | `## Overview` header with table |
| When to Use | Specific trigger conditions |
| Verified Workflow | Steps that worked (exact header) |
| **Failed Attempts** | **TABLE format** (not prose) |
| Results & Parameters | Copy-paste configs |

## Example

```
/skills-registry-commands:retrospective
```

Claude will analyze the session and guide you through creating a new skill.
