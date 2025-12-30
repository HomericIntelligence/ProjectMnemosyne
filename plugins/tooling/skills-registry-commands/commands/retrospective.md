---
description: Save session learnings as a new skill plugin
---

# /retrospective

Capture session learnings and create a new skill plugin in the ProjectMnemosyne marketplace.

## Target Repository

**Repository**: `HomericIntelligence/ProjectMnemosyne`
**Base branch**: `main`

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

3. **Clone/checkout the marketplace repository**:
   ```bash
   gh repo clone HomericIntelligence/ProjectMnemosyne /tmp/ProjectMnemosyne
   cd /tmp/ProjectMnemosyne
   git checkout -b skill/<category>/<name>
   ```

4. **Generate plugin files** in `plugins/<category>/<name>/`:
   - `.claude-plugin/plugin.json` with metadata
   - `skills/<name>/SKILL.md` with findings
   - `references/notes.md` with raw details

5. **Create PR**:
   ```bash
   git add plugins/<category>/<name>/
   git commit -m "feat: add <name> skill"
   git push -u origin skill/<category>/<name>

   # Write PR body to a temp file
   cat > /tmp/pr-body.md << 'EOF'
   ## Summary
   - <1-3 bullet points about what was learned>

   ## Key Findings
   - What worked
   - What failed (most valuable)

   🤖 Generated with [Claude Code](https://claude.com/claude-code)
   EOF

   gh pr create --repo HomericIntelligence/ProjectMnemosyne --base main \
     --title "feat: add <name> skill" \
     --body-file /tmp/pr-body.md
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
