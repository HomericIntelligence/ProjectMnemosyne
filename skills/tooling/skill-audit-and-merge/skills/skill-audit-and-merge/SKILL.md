---
name: skill-audit-and-merge
description: "Systematic audit and consolidation of skills marketplace plugins"
---

# Skill Audit and Merge

Analyze a skills marketplace to identify merge candidates, improve metadata, and reorganize for better discoverability.

## Overview

| Field | Value |
|-------|-------|
| **Date** | 2026-01-01 |
| **Objective** | Consolidate 43 plugins into coherent workflows, add missing metadata |
| **Outcome** | Reduced to 37 plugins, 100% tag coverage, 3 new workflow plugins |
| **Duration** | ~1 hour |

## When to Use

- Marketplace has grown organically with overlapping plugins
- Multiple plugins form a sequential workflow (e.g., create → switch → sync → cleanup)
- Plugins are missing tags, hurting `/advise` discoverability
- Plugins are in wrong categories (e.g., workflow tools in debugging/)
- Need to identify gaps in coverage (empty categories)

## Verified Workflow

### Phase 1: Comprehensive Audit

1. **Launch parallel Explore agents** for thorough analysis:
   ```
   Agent 1: Inventory all plugins by category
   Agent 2: Assess content quality of each SKILL.md
   Agent 3: Identify overlaps and merge candidates
   ```

2. **Identify merge candidates** - look for:
   - Plugins with cross-references to each other
   - Sequential workflow steps (create/switch/sync/cleanup)
   - Plugins where one orchestrates the others

3. **Identify improvement needs**:
   - Missing tags (check plugin.json)
   - Missing Failed Attempts tables (required per CLAUDE.md)
   - Wrong category placement

### Phase 2: Get User Decisions

Ask about:
- **Merge style**: Separate sub-skills vs single consolidated SKILL.md
- **Category changes**: e.g., worktree tools → tooling/ vs debugging/
- **Scope**: Metadata only vs full consolidation

### Phase 3: Execute Changes

For each merge:
1. Create new directory: `plugins/<category>/<workflow-name>/`
2. Create plugin.json with comprehensive description
3. Create skills/ subdirectories for each sub-skill
4. Copy/adapt SKILL.md files with updated cross-references
5. Create references/notes.md explaining the merge
6. Delete old plugin directories

### Phase 4: Finalize

1. Regenerate marketplace.json: `python scripts/generate_marketplace.py`
2. Verify plugin count matches expectations
3. Commit all changes

## Failed Attempts

| Attempt | What Went Wrong | Lesson Learned |
|---------|-----------------|----------------|
| Assumed SKILL.md files were missing | Exploration agent reported sparse content, but files existed and were complete | Always verify with direct file reads before planning fixes |
| Ran generate_marketplace.py with wrong repo name | Got "repository not found" error on PR creation | Check `git remote -v` to confirm actual repo name |
| Initially listed wrong plugin count in plan | Said 35 but got 37 after merge | Double-check arithmetic: 43 - 4 + 1 - 3 + 1 - 2 + 1 = 37 |
| Tried to create PR to non-existent repo | PR creation failed with GraphQL error | Verify repo exists before gh pr create |

## Results & Parameters

### Merge Patterns

| Pattern | Example | Structure |
|---------|---------|-----------|
| Sequential workflow | worktree-{create,switch,sync,cleanup} | 4 sub-skills in skills/ |
| Orchestrator + primitives | gh-fix-pr-feedback + get/reply | 3 sub-skills, orchestrator is primary |
| Analysis + Action | analyze-ci-failure-logs + fix-ci-failures | 2 sub-skills: analyze/ and fix/ |

### Directory Structure for Merged Plugin

```
plugins/<category>/<workflow-name>/
├── .claude-plugin/
│   └── plugin.json          # Description explains N-in-1 structure
├── skills/
│   ├── <sub-skill-1>/
│   │   └── SKILL.md
│   ├── <sub-skill-2>/
│   │   └── SKILL.md
│   └── ...
└── references/
    └── notes.md              # Explains merge, lists original plugins
```

### plugin.json Template for Merged Plugin

```json
{
  "name": "<workflow-name>",
  "version": "1.0.0",
  "description": "Complete <workflow> workflow. Contains N sub-skills: (1) <skill-1> - <purpose>, (2) <skill-2> - <purpose>...",
  "tags": ["<domain>", "<sub-skill-1>", "<sub-skill-2>", "workflow"]
}
```

### Commands Used

```bash
# Create merged plugin structure
mkdir -p plugins/<category>/<name>/{.claude-plugin,skills/<sub1>,skills/<sub2>,references}

# Move content (git tracks as rename)
git mv plugins/old/skills/old/SKILL.md plugins/new/skills/new/SKILL.md

# Delete old plugins
rm -rf plugins/<category>/<old-plugin-1> plugins/<category>/<old-plugin-2>

# Regenerate marketplace
python scripts/generate_marketplace.py

# Verify count
grep -c '"name":' .claude-plugin/marketplace.json
```

## Key Insights

1. **Parallel exploration is faster**: Launch 3 agents to analyze inventory, content quality, and overlaps simultaneously

2. **User decisions matter for scope**: Always ask about merge style, category changes, and scope before starting

3. **Cross-references reveal clusters**: If plugins reference each other in "See also" sections, they're merge candidates

4. **Merged plugins need clear descriptions**: Explain N-in-1 structure in plugin.json description

5. **Test plugin count after merge**: `43 - (4-1) - (3-1) - (2-1) = 37`

## Prevention Checklist

Before creating new plugins:
- [ ] Check if related plugins exist that could be extended
- [ ] Ensure plugin has tags (for /advise discoverability)
- [ ] Place in correct category (tooling for workflows, ci-cd for Docker fixes, etc.)
- [ ] Include Failed Attempts table (required)

## References

- PR #22: https://github.com/HomericIntelligence/ProjectMnemosyne/pull/22
- CLAUDE.md plugin standards
- git-worktree-workflow, gh-pr-review-workflow, ci-failure-workflow (examples of merged plugins)
