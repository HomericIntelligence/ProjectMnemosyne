---
name: sionic-blog-conversion
description: Convert knowledge sources like blog posts into Claude Code plugins. Use when extracting skills from documentation, creating importable plugins from external knowledge, or building a skills marketplace.
---

# Converting Knowledge Sources to Claude Code Plugins

How to extract learnings from blog posts, documentation, and external resources into importable Claude Code plugins.

## Overview

| Item | Details |
|------|---------|
| Date | 2025-12-29 |
| Objective | Convert Sionic AI blog post into importable plugins for other Claude agents |
| Outcome | Created skills-registry-commands plugin with 4 sub-skills + spec-driven-experimentation |
| Source | https://huggingface.co/blog/sionic-ai/claude-code-skills-training |

## When to Use

- Extracting valuable patterns from blog posts or articles
- Converting documentation into reusable plugins
- Building a skills marketplace from scattered knowledge
- Making external learnings importable by other Claude agents
- Packaging best practices as distributable plugins

## Verified Workflow

### 1. Fetch and Analyze the Source

Use WebFetch to get the content:

```
WebFetch(url, prompt="Extract all key learnings, techniques, workflows, and recommendations...")
```

Key things to extract:
- Core concepts and patterns
- Verified workflows
- Failed attempts (most valuable!)
- Concrete parameters and configs
- Tool/script examples

### 2. Identify Distinct Skills vs Infrastructure

Separate **domain knowledge** from **infrastructure**:

**Infrastructure** (should be merged into one plugin):
- Commands that enable the system (/advise, /retrospective)
- Supporting scripts (validation, marketplace generation)
- Documentation patterns
- CI/CD workflows
- Hooks and automation

**Domain knowledge** (separate plugins):
- ML experiment patterns (TECHSPEC.md)
- Domain-specific techniques
- Training recipes
- Debugging patterns

### 3. Create Plugin Structure

For infrastructure plugin (all-in-one):
```
skills-registry-commands/
├── .claude-plugin/plugin.json
├── skills/
│   ├── advise/SKILL.md              # Command spec
│   ├── retrospective/SKILL.md       # Command spec
│   ├── documentation-patterns/SKILL.md  # Best practices
│   └── validation-workflow/SKILL.md     # CI/CD
├── hooks/
│   └── retrospective-trigger.py     # Auto-prompt on session end
├── scripts/
│   ├── validate_plugins.py          # PR validation
│   └── generate_marketplace.py      # Index generation
└── references/
    └── notes.md                     # Setup instructions
```

For domain knowledge plugins (focused):
```
spec-driven-experimentation/
├── .claude-plugin/plugin.json
├── skills/spec-driven-experimentation/
│   └── SKILL.md                     # TECHSPEC.md pattern
└── references/
    └── examples.md
```

### 4. Write Effective Descriptions

Use the blog's pattern:
```
"{what} + Use when: {numbered triggers} + Verified on/Source: {context}"
```

Examples:
- "Complete skills registry system: /advise, /retrospective, documentation patterns, and CI validation. Use when: (1) Setting up team knowledge capture, (2) Adding skill search/creation to any project, (3) Implementing the Sionic AI skills pattern."
- "TECHSPEC.md pattern for structured ML experiments. Use when: (1) Planning parameter sweeps, (2) Defining success criteria before training, (3) Budget-constrained experiment design."

### 5. Populate SKILL.md with Blog Content

Required sections from blog insights:
- **When to Use**: Specific trigger conditions
- **Verified Workflow**: Step-by-step what worked
- **Failed Attempts**: What didn't work (REQUIRED!)
- **Results & Parameters**: Copy-paste ready configs
- **References**: Link back to source

### 6. Test Plugin Merging Logic

When deciding to merge vs separate:
- Same **purpose**? Merge (e.g., all registry infrastructure together)
- Different **domain**? Separate (e.g., ML patterns vs registry system)
- Ask: "Would someone want just part of this?" If yes, consider splitting

### 7. Clean Up Redundant Plugins

After creating comprehensive plugins:
- Delete meta-plugins (e.g., skill-marketplace-design now redundant)
- Remove domain-specific examples if not relevant
- Keep only universally useful patterns

## Failed Attempts

| Attempt | Why it Failed | Lesson Learned |
|---------|---------------|----------------|
| Creating 3 separate plugins initially | Fragmented infrastructure (docs, validation, commands) | Merge related infrastructure into one complete package |
| Keeping skill-marketplace-design | Redundant with skills-registry-commands | Delete meta-skills once comprehensive version exists |
| Including Mojo-specific skills | Not relevant to general marketplace | Only keep universally applicable patterns |
| Vague plugin descriptions | Users don't know when to use it | Use "{what} + Use when: {triggers}" pattern |
| Missing Failed Attempts section | Lost most valuable learnings | Always extract what didn't work from source |

## Results & Parameters

```yaml
# Conversion checklist
source_analysis:
  - Extract core concepts
  - Identify infrastructure vs domain knowledge
  - Note failed attempts (critical!)
  - Capture copy-paste configs

plugin_structure:
  infrastructure: "Merge into single comprehensive plugin"
  domain_knowledge: "Separate focused plugins"

description_pattern: "{what} + Use when: {numbered triggers} + Source: {context}"

skill_md_sections:
  - Overview (table format)
  - When to Use (specific triggers)
  - Verified Workflow (numbered steps)
  - Failed Attempts (table - REQUIRED)
  - Results & Parameters (copy-paste configs)
  - References (link to source)

cleanup_criteria:
  - Remove meta-plugins after creating comprehensive versions
  - Delete domain-specific examples if not universally relevant
  - Keep only patterns that other teams would reuse
```

## Example: Sionic AI Blog Conversion

**Source**: https://huggingface.co/blog/sionic-ai/claude-code-skills-training

**Created**:
1. `skills-registry-commands` (tooling) - Complete system
   - `/advise` command
   - `/retrospective` command
   - Documentation patterns
   - Validation workflow
   - SessionEnd hook
   - Scripts (validate, generate)

2. `spec-driven-experimentation` (training) - Domain knowledge
   - TECHSPEC.md pattern
   - Hypothesis-driven design
   - Success criteria framework

**Deleted** (after analysis):
- `skill-marketplace-design` - Redundant meta-skill
- `mojo-simd-errors` - Domain-specific, not universal
- `layerwise-gradient-check` - Domain-specific, not universal

**Result**: 2 focused plugins instead of 5 fragmented ones

## Key Insights

1. **Infrastructure belongs together**: Commands, hooks, scripts, and docs should be one complete package
2. **Domain knowledge stays separate**: ML patterns, language-specific techniques should be focused plugins
3. **Failed attempts are gold**: Always extract what didn't work - it saves weeks of trial-and-error
4. **Descriptions need triggers**: Generic descriptions don't help `/advise` matching
5. **Merge after creating**: It's easier to create separately then merge than to design merged from start
6. **Delete redundant meta-skills**: Once you have comprehensive version, remove the prototype

## References

- Source blog: https://huggingface.co/blog/sionic-ai/claude-code-skills-training
- Created plugin: skills-registry-commands
- Created plugin: spec-driven-experimentation
- Session: Converting external knowledge to importable plugins
