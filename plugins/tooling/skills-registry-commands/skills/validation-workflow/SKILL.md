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

## When to Use

- Setting up CI/CD for a skills marketplace
- Enforcing required sections in SKILL.md
- Auto-generating marketplace.json on merge
- Preventing low-quality skills from entering registry

## Verified Workflow

### 1. PR Validation

CI runs `python3 scripts/validate_plugins.py plugins/` on every PR touching `plugins/**`, `templates/**`, or `scripts/validate_plugins.py`.

**What it checks** (`scripts/validate_plugins.py`):
- `.claude-plugin/plugin.json` exists with name, version, description
- Name matches `^[a-z0-9-]+$`
- Description ≥ 20 chars
- Category valid if present (9 approved values)
- SKILL.md has YAML frontmatter (`---`)
- Required sections: Overview, When to Use, Verified Workflow, Failed Attempts, Results
- Failed Attempts has table format (pipe characters)

Run locally before committing:
```bash
python3 scripts/validate_plugins.py plugins/
```

### 2. Auto-Generate Marketplace on Merge

On push to `main` (paths: `plugins/**`), CI runs:
```bash
python3 scripts/generate_marketplace.py plugins/ .claude-plugin/marketplace.json
```

Result is committed with `[skip ci]` to prevent infinite loops.

### 3. Install Scripts

Copy from this plugin's `scripts/` directory:
- `validate_plugins.py` — PR validation
- `generate_marketplace.py` — Marketplace generation

## Failed Attempts

| Attempt | Why Failed | Lesson |
|---------|-----------|--------|
| No validation on PRs | Bad plugins entered registry | Validate before merge |
| Manual marketplace.json edits | Out of sync with actual plugins | Auto-generate on merge |
| Optional failures section | Most valuable info missing | Make it required in validation |
| Single validation script | Hard to debug which check failed | Separate steps in workflow |
| Inline grep validation | Missed edge cases, hard to maintain | Use dedicated validate_plugins.py |

## Results & Parameters

```yaml
# Validation rules (from validate_plugins.py)
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
  validate_on: pull_request (paths: plugins/**, templates/**, scripts/validate_plugins.py)
  generate_on: push to main (paths: plugins/**)

# Commit message patterns
commits:
  marketplace_update: "chore: update marketplace.json [skip ci]"
  skip_ci_pattern: "[skip ci]"  # Prevent infinite loops
```

## References

- GitHub Actions: https://docs.github.com/en/actions
- Key insight: "Auto-update marketplace makes skills discoverable to /plugin system"
