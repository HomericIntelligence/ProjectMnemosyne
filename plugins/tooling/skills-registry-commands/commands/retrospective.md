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
   - Category (training, evaluation, optimization, debugging, architecture, tooling, ci-cd, testing)
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

4. **Generate plugin files** in `plugins/<category>/<name>/`:

   **CRITICAL**: SKILL.md MUST meet CI validation requirements or PR will fail:

   - `.claude-plugin/plugin.json` with metadata
   - `skills/<name>/SKILL.md` with **required format**:
     - ✅ **YAML frontmatter** (starts with `---`)
       ```yaml
       ---
       name: skill-name
       description: "Use when: specific triggers"
       category: architecture
       tier: 2
       date: YYYY-MM-DD
       ---
       ```
     - ✅ **Overview section** with `## Overview` header and table
     - ✅ **Failed Attempts table** (MUST be table format, not prose):
       ```markdown
       ## Failed Attempts

       | Attempt | What Was Tried | Why It Failed | Lesson Learned |
       |---------|----------------|---------------|----------------|
       | ... | ... | ... | ... |
       ```
     - ✅ All other sections (When to Use, Verified Workflow, Results & Parameters)
   - `references/notes.md` with raw details

5. **Commit and push**:
   ```bash
   git add plugins/<category>/<name>/
   git commit -m "feat: add <name> skill

Documents <brief description>.

Key learnings:
- <bullet 1>
- <bullet 2>
- <bullet 3>

🤖 Generated with [Claude Code](https://claude.com/claude-code)

Co-Authored-By: Claude Sonnet 4.5 <noreply@anthropic.com>"

   git push -u origin skill/<category>/<name>
   ```

6. **Create PR** (only if push succeeded):
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

   - [ ] Validate plugin with `python scripts/validate_plugins.py plugins/`
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

**All sections are CI-validated. Missing or incorrectly formatted sections will fail the build.**

| Section | Format | CI-Required |
|---------|--------|-------------|
| **YAML frontmatter** | Starts with `---`, includes name/description/category/date | ✅ YES |
| **Overview section** | `## Overview` header with table | ✅ YES |
| When to Use | Specific trigger conditions | ⚠️ Recommended |
| Verified Workflow | Steps that worked | ⚠️ Recommended |
| **Failed Attempts** | **TABLE format** (not prose) | ✅ YES |
| Results & Parameters | Copy-paste configs | ⚠️ Recommended |

**Common CI failures**:
- Missing YAML frontmatter entirely
- Failed Attempts as prose paragraphs instead of table
- Overview table without "## Overview" header

## Example

```
/skills-registry-commands:retrospective
```

Claude will analyze the session and guide you through creating a new skill.
