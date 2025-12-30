# Claude Plugin Marketplace - Raw Session Notes

## Session Context

- **Date**: 2025-12-30
- **Duration**: ~2 hours
- **Goal**: Set up ProjectMnemosyne as a Claude Code skills marketplace
- **Source**: HuggingFace blog on Claude Code skills training

## Error Messages Encountered

### marketplace.json owner validation error

```text
Error validating marketplace JSON from file:///path/to/marketplace.json
owner: Expected object, received string
```

**Resolution**: Changed `"owner": "HomericIntelligence"` to:

```json
"owner": {
  "name": "HomericIntelligence",
  "url": "https://github.com/HomericIntelligence"
}
```

### plugin.json unrecognized keys error

```text
Error reading plugin JSON from file:///path/to/plugin.json
Unrecognized key(s) in object: 'date', 'category', 'tags', 'source_project'
```

**Resolution**: Removed all unsupported fields, kept only:

- name
- version
- description
- author
- skills

### GitHub authentication error

```text
Error adding marketplace: Failed to clone repository
```

**Resolution**: Used local path instead of GitHub URL:

```bash
claude plugin marketplace add /home/mvillmow/ProjectMnemosyne-marketplace
```

## Working Commands

```bash
# Registration
claude plugin marketplace add /absolute/path/to/repo

# Installation
claude plugin install grpo-external-vllm@ProjectMnemosyne
claude plugin install mojo-simd-errors@ProjectMnemosyne
claude plugin install github-actions-mojo@ProjectMnemosyne
claude plugin install layerwise-gradient-check@ProjectMnemosyne
claude plugin install skill-marketplace-design@ProjectMnemosyne

# Verification
claude plugin marketplace list
```

## Files Modified

1. `.claude-plugin/marketplace.json` - Fixed owner schema
2. `plugins/*/plugin.json` - Removed unsupported fields from all 5 plugins
3. `scripts/generate_marketplace.py` - Updated to generate correct schema

## PRs Created

1. **PR #1**: Initial marketplace implementation (merged)
2. **PR #2**: Schema fixes for Claude Code compatibility (merged)

## Blog Source

[Claude Code Skills Training - Sionic AI](https://huggingface.co/blog/sionic-ai/claude-code-skills-training)

Key points from blog:

- `/advise` command searches marketplace before work
- `/retrospective` captures learnings and creates PR
- Failed Attempts section is required in SKILL.md
- Plugin structure: `.claude-plugin/plugin.json` + `skills/*/SKILL.md`
