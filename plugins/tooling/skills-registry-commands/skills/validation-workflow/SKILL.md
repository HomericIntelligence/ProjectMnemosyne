---
name: validation-workflow
description: GitHub Actions CI for validating skill plugins. Use when setting up CI/CD for a skills marketplace or enforcing plugin quality.
user-invocable: false
---

# Plugin Validation Workflow

CI/CD pipeline for validating skills and auto-generating marketplace.

## Overview

| Item | Details |
|------|---------|
| Date | 2025-12-29 |
| Objective | Automate skill validation and marketplace generation |
| Outcome | Consistent quality, auto-updated discoverability |
| Source | Sionic AI HuggingFace blog |

## When to Use

- Setting up CI/CD for a skills marketplace
- Validating plugin.json structure on PRs
- Enforcing required sections in SKILL.md
- Auto-generating marketplace.json on merge
- Preventing low-quality skills from entering registry

## Verified Workflow

### 1. PR Validation Workflow

Copy `.github/workflows/validate-plugins.yml`:

```yaml
name: Validate Plugins

on:
  pull_request:
    paths:
      - 'plugins/**'

jobs:
  validate:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - name: Set up Python
        uses: actions/setup-python@v5
        with:
          python-version: '3.11'

      - name: Validate plugin.json files
        run: python scripts/validate_plugins.py

      - name: Check SKILL.md exists
        run: |
          for plugin_json in $(find plugins -name "plugin.json"); do
            plugin_dir=$(dirname $(dirname "$plugin_json"))
            skill_md=$(find "$plugin_dir/skills" -name "SKILL.md" 2>/dev/null)
            if [ -z "$skill_md" ]; then
              echo "ERROR: Missing SKILL.md for $plugin_json"
              exit 1
            fi
          done

      - name: Validate SKILL.md sections
        run: |
          for skill_md in $(find plugins -name "SKILL.md"); do
            if ! grep -q "## Failed Attempts" "$skill_md"; then
              echo "ERROR: Missing 'Failed Attempts' section in $skill_md"
              exit 1
            fi
          done
```

### 2. Auto-Generate Marketplace on Merge

Copy `.github/workflows/update-marketplace.yml`:

```yaml
name: Update Marketplace

on:
  push:
    branches: [main]
    paths:
      - 'plugins/**'

jobs:
  update:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - name: Set up Python
        uses: actions/setup-python@v5
        with:
          python-version: '3.11'

      - name: Generate marketplace.json
        run: python scripts/generate_marketplace.py

      - name: Commit and push
        run: |
          git config user.name "github-actions[bot]"
          git config user.email "github-actions[bot]@users.noreply.github.com"
          git add marketplace.json
          git diff --staged --quiet || git commit -m "chore: update marketplace.json [skip ci]"
          git push
```

### 3. Install Scripts

Copy from this plugin's `scripts/` directory:
- `validate_plugins.py` - PR validation
- `generate_marketplace.py` - Marketplace generation

## Failed Attempts

| Attempt | Why Failed | Lesson |
|---------|-----------|--------|
| No validation on PRs | Bad plugins entered registry | Validate before merge |
| Manual marketplace.json edits | Out of sync with actual plugins | Auto-generate on merge |
| Optional failures section | Most valuable info missing | Make it required in validation |
| Validate only plugin.json | SKILL.md quality ignored | Check both files |
| Single validation script | Hard to debug which check failed | Separate steps in workflow |

## Results & Parameters

```yaml
# Validation rules
validation:
  required_plugin_fields:
    - name
    - version
    - description
  min_description_length: 20
  description_must_contain: "Use when:"
  required_skill_sections:
    - "## Failed Attempts"
    - "## When to Use"

# Workflow triggers
triggers:
  validate_on: pull_request (paths: plugins/**)
  generate_on: push to main (paths: plugins/**)

# Commit message patterns
commits:
  marketplace_update: "chore: update marketplace.json [skip ci]"
  skip_ci_pattern: "[skip ci]"  # Prevent infinite loops

# Best practices
recommendations:
  - Separate validation and generation workflows
  - Use [skip ci] for auto-commits
  - Validate both plugin.json AND SKILL.md
  - Show specific error messages
  - Fail fast on first error per file
```

## References

- Source blog: https://huggingface.co/blog/sionic-ai/claude-code-skills-training
- GitHub Actions: https://docs.github.com/en/actions
- Key insight: "Auto-update marketplace makes skills discoverable to /plugin system"
