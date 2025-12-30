---
description: Save session learnings as a new skill plugin
---

# /retrospective

Capture session learnings and create a new skill plugin in the ProjectMnemosyne marketplace.

## Target Repository

**Repository**: `HomericIntelligence/ProjectMnemosyne`
**Base branch**: `main`
**Clone location**: `<ProjectRoot>/build/ProjectMnemosyne/`

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

3. **Setup repository** (IMPORTANT: Don't remove/reclone if exists):
   ```bash
   # Create build directory if it doesn't exist
   mkdir -p build

   # Clone only if directory doesn't exist
   if [ ! -d "build/ProjectMnemosyne" ]; then
     gh repo clone HomericIntelligence/ProjectMnemosyne build/ProjectMnemosyne
   fi

   cd build/ProjectMnemosyne

   # Fetch latest changes and create branch from origin/main
   git fetch origin
   git checkout -b skill/<category>/<name> origin/main
   ```

4. **Generate plugin files** in `plugins/<category>/<name>/`:
   - `.claude-plugin/plugin.json` with metadata
   - `skills/<name>/SKILL.md` with findings
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
   # Write PR body to build directory (not /tmp)
   cat > ../pr-body-<name>.md << 'EOF'
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
     --body-file ../pr-body-<name>.md
   ```

## Common Issues & Solutions

### Issue: "No commits between main and skill/..."

**Cause**: The branch was already merged or rebased incorrectly.

**Solution**: Don't rebase. Create branch directly from `origin/main`:
```bash
git checkout -b skill/<category>/<name> origin/main
```

### Issue: Repository already exists

**Cause**: Tried to remove and reclone unnecessarily.

**Solution**: Never `rm -rf` the build directory. Just fetch and create new branch:
```bash
cd build/ProjectMnemosyne
git fetch origin
git checkout -b skill/<category>/<name> origin/main
```

### Issue: Uncommitted changes warning

**Cause**: Previous retrospective left uncommitted files.

**Solution**: Clean or stash before creating new branch:
```bash
git stash
git checkout -b skill/<category>/<name> origin/main
```

## Required SKILL.md Sections

| Section | Purpose |
|---------|---------|
| Overview table | Date, objective, outcome |
| When to Use | Trigger conditions |
| Verified Workflow | Steps that worked |
| **Failed Attempts** | What didn't work (REQUIRED) |
| Results & Parameters | Copy-paste configs |

## Example

```
/skills-registry-commands:retrospective
```

Claude will analyze the session and guide you through creating a new skill.
