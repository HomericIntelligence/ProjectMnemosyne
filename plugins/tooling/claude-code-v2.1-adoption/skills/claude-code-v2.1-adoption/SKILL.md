---
name: claude-code-v2.1-adoption
description: "Systematic approach to adopting Claude Code v2.1.0 features. Use when upgrading to new Claude Code version or analyzing CHANGELOG for feature adoption."
user-invocable: false
---

# Claude Code v2.1.0 Feature Adoption

Systematic workflow for analyzing Claude Code CHANGELOG and adopting new features in a skills marketplace.

## Overview

| Item | Details |
|------|---------|
| Date | 2026-01-08 |
| Objective | Adopt 5 new features from Claude Code v2.1.0 in ProjectMnemosyne |
| Outcome | Successfully created 5 PRs with comprehensive documentation |
| Source | Claude Code v2.1.0 CHANGELOG |

## When to Use

- Upgrading skills marketplace to new Claude Code version
- Analyzing CHANGELOG to identify applicable features
- Creating documentation skills for new platform capabilities
- Updating plugin schemas and templates for new fields
- Systematically implementing multiple related features

## Verified Workflow

### 1. Research Phase: Use /advise

Start with `/advise` to search existing skills about Claude Code features:

```text
/advise Analyze the release notes https://github.com/anthropics/claude-code/blob/main/CHANGELOG.md
```

This provides:
- Related skills (claude-plugin-format, claude-plugin-marketplace, retrospective-hook-integration)
- What worked vs failed in previous integrations
- Known schema constraints and validation requirements

### 2. Feature Analysis

Analyze CHANGELOG for new features:

```bash
# Fetch CHANGELOG
curl -L https://raw.githubusercontent.com/anthropics/claude-code/main/CHANGELOG.md

# Identify v2.1.0 features
# - user-invocable field for skills
# - agent hooks field (PreToolUse/PostToolUse/Stop)
# - disallowedTools (CLI only, NOT frontmatter)
# - agent field for skills
# - once field for hooks
```

**Key distinction**: Separate CLI/settings features from frontmatter features.

### 3. Create Implementation Plan

Break down into separate PRs:

1. **PR1: user-invocable field**
   - Add to internal sub-skills
   - Update template
   - Document usage

2. **PR2+3: Agent hooks + tool blocking**
   - Create documentation skill
   - Combine related features in single PR
   - Provide templates for common patterns

3. **PR4: agent field**
   - Create documentation skill
   - Update template
   - Document routing patterns

4. **PR5: once field**
   - Update existing hook documentation
   - Add to template examples

### 4. Implementation Pattern

For each feature:

```bash
# Create feature branch
git checkout main
git checkout -b feature/<feature-name>

# For new documentation skills
mkdir -p plugins/tooling/<skill-name>/{.claude-plugin,skills/<skill-name>,references}

# Create plugin.json
cat > .claude-plugin/plugin.json <<'EOF'
{
  "name": "skill-name",
  "version": "1.0.0",
  "description": "Trigger conditions...",
  "author": {"name": "HomericIntelligence"},
  "skills": "./skills"
}
EOF

# Create SKILL.md with:
# - When to Use (trigger conditions)
# - Verified Workflow (step-by-step)
# - Failed Attempts (what didn't work)
# - Results & Parameters (copy-paste templates)

# Update template if needed
# Regenerate marketplace.json
python3 scripts/generate_marketplace.py

# Commit and push
git add -A
git commit -m "feat(...): ..."
git push -u origin feature/<feature-name>

# Create PR with auto-merge
gh pr create --title "..." --body "..." --label "enhancement"
gh pr merge --auto --rebase
```

### 5. Use Scripts for Bulk Updates

For bulk frontmatter updates:

```python
#!/usr/bin/env python3
"""Add field to skill frontmatter."""
import re
from pathlib import Path

def add_field(file_path: Path, field_name: str, field_value: str) -> bool:
    content = file_path.read_text()

    if f"{field_name}:" in content:
        return False  # Already has field

    pattern = r'^(---\n)(.*?)(---\n)'
    match = re.match(pattern, content, re.DOTALL)

    if not match:
        return False

    frontmatter = match.group(2)
    new_frontmatter = frontmatter.rstrip() + f"\n{field_name}: {field_value}\n"
    new_content = f"---\n{new_frontmatter}---\n" + content[match.end():]

    file_path.write_text(new_content)
    return True
```

### 6. Document in Central Files

Update `CLAUDE.md` with new field usage:

```markdown
**SKILL.md**:

- YAML frontmatter (name, description)
  - `user-invocable`: Set to `false` for internal/sub-skills
  - `agent`: Optional agent type (e.g., mojo-specialist)
```

### 7. Create Retrospective

After completing all PRs:

```text
/retrospective
```

Capture the workflow for future version upgrades.

## Failed Attempts

| Attempt | Why Failed | Lesson Learned |
|---------|-----------|----------------|
| Adding `disallowedTools` array to agent frontmatter | Field not supported in v2.1.0 - only CLI `--disallowedTools` works | Always verify CHANGELOG mentions frontmatter support, not just CLI flags |
| Using single PR for all 5 features | Too much scope, harder to review | Separate PRs for independent features, combine only closely related ones |
| Implementing features before researching with /advise | Missed existing skills about claude-plugin-format and schema constraints | Always start with `/advise` to leverage prior team knowledge |
| Assuming all CHANGELOG features apply to frontmatter | Some features (disallowedTools) are CLI-only | Distinguish CLI/settings features from frontmatter features |

## Results & Parameters

### Feature Adoption Checklist

- [ ] Start with `/advise <changelog-url>` to research existing knowledge
- [ ] Fetch and analyze CHANGELOG for target version
- [ ] Identify frontmatter vs CLI/settings features
- [ ] Create separate PRs for independent features
- [ ] Combine closely related features (agent hooks + tool blocking)
- [ ] Update templates with new fields
- [ ] Document in CLAUDE.md
- [ ] Create documentation skills for complex patterns
- [ ] Run `/retrospective` after completion

### PR Template

```markdown
## Summary

[Feature description from CHANGELOG]

## Changes

**New/Updated**: [files changed]
- ✅ [specific change]
- ✅ [specific change]

## Test Plan

- [ ] Verify [expected behavior]
- [ ] CI validation passes

## References

- Claude Code v[X.Y.Z] CHANGELOG: [feature name]

🤖 Generated with [Claude Code](https://claude.com/claude-code)
```

### Python Script Pattern

```python
# scripts/add_frontmatter_field.py
SUB_SKILLS = [
    "plugins/category/plugin/skills/sub-skill/SKILL.md",
]

def add_field(file_path: Path) -> bool:
    # Check if field exists
    # Parse YAML frontmatter
    # Add field
    # Write back
    return True
```

### Documentation Skill Structure

```text
plugins/tooling/<feature-name>/
├── .claude-plugin/
│   └── plugin.json
├── skills/<feature-name>/
│   └── SKILL.md           # Main documentation
└── references/
    └── notes.md           # Implementation details
```

## Verified On

| Project | Context | Details |
|---------|---------|---------|
| ProjectMnemosyne | v2.1.0 upgrade | [notes.md](../references/notes.md) |

## Key Insights

1. **Start with /advise**: Leverage existing team knowledge about Claude Code integration before implementing

2. **CHANGELOG analysis critical**: WebFetch the CHANGELOG to extract features with examples and version info

3. **Frontmatter vs CLI distinction**: Not all CHANGELOG features apply to plugin frontmatter (e.g., disallowedTools)

4. **Combine related PRs**: Agent hooks + tool blocking belong together (same implementation mechanism)

5. **Script bulk updates**: Use Python scripts for frontmatter updates across multiple skills

6. **Documentation skills pattern**: Create skills for complex features (agent-hooks-pattern, skills-agent-field)

7. **Template updates essential**: New fields must appear in templates with inline documentation

8. **Incremental adoption**: 5 separate PRs easier to review than monolithic change

## References

- [Claude Code CHANGELOG](https://github.com/anthropics/claude-code/blob/main/CHANGELOG.md)
- Related skill: claude-plugin-format (schema requirements)
- Related skill: claude-plugin-marketplace (marketplace setup)
- Related skill: retrospective-hook-integration (SessionEnd hooks)
- PRs: #70 (user-invocable), #71 (agent hooks), #72 (agent field), #73 (once field)
