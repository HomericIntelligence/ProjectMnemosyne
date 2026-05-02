---
name: pypi-trusted-publishing-setup
description: "Configure PyPI trusted publishing (OIDC) with GitHub Actions for namespace packages. Use when: (1) setting up OIDC trusted publishing for a new PyPI project, (2) debugging 403/400 errors during PyPI upload, (3) publishing namespace packages like Org-Project to PyPI."
category: ci-cd
date: 2026-03-22
version: "1.0.0"
user-invocable: false
---

# PyPI Trusted Publishing Setup

## Overview

| Date | Objective | Outcome |
| ------ | ----------- | --------- |
| 2026-03-22 | Configure OIDC trusted publishing for HomericIntelligence-Hephaestus | Successfully published v0.4.0 after fixing distribution name, environment, and pending publisher |

## When to Use

- Setting up OIDC trusted publishing for a **new** PyPI project
- Debugging `403 Forbidden` or `400 Non-user identities cannot create new projects` during PyPI upload
- Migrating from `secrets.PYPI_API_TOKEN` to trusted publishing
- Publishing namespace packages (e.g., `OrgName-ProjectName`) to PyPI
- Changing a PyPI distribution name while keeping the Python import name unchanged

## Verified Workflow

### Quick Reference

```yaml
# .github/workflows/release.yml
permissions:
  contents: write
  id-token: write  # REQUIRED for OIDC

jobs:
  build-and-publish:
    environment: pypi  # Must match PyPI trusted publisher config
    steps:
      - uses: pypa/gh-action-pypi-publish@release/v1
        with:
          verbose: true  # Enable during setup, disable after confirmed working
```

### Step 1: Configure pyproject.toml

The `name` field MUST exactly match the PyPI project name:

```toml
[project]
name = "OrgName-ProjectName"  # Distribution name on PyPI

[tool.hatch.build.targets.wheel]
packages = ["projectname"]  # Python import name (can differ)
```

Wheel filenames are normalized to lowercase: `orgname_projectname-*.whl` (PEP 625).

### Step 2: Configure GitHub Environment

Repository Settings → Environments → create `pypi`:
- Deployment branches and tags: "Selected branches and tags", add `v*` tag pattern
- Required reviewers (optional): Add reviewer for manual approval gate

### Step 3: Workflow permissions

Must have `id-token: write` at top level of workflow.

### Step 4: Register on PyPI

**For NEW projects** (doesn't exist on PyPI yet): Add a **pending publisher** at https://pypi.org/manage/account/publishing/ — OIDC cannot create new projects.

**For EXISTING projects**: Add trusted publisher at project settings → Publishing.

### Step 5: Update dependent files

When changing distribution name, also update:
- `pixi.toml` pypi-dependencies key (lowercase)
- Regenerate `pixi.lock`
- Integration test wheel globs (must be lowercase)

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
| --------- | ---------------- | --------------- | ---------------- |
| Hardcoded SHA for pypi-publish | `pypa/gh-action-pypi-publish@76f52bc...` | SHA was invalid/not found | Use `@release/v1` branch ref |
| Protected branches only on env | GitHub env `protected_branches: true` | Tags are not protected branches | Use "Selected branches and tags" with `v*` pattern |
| Distribution name mismatch | `pyproject.toml` name `hephaestus`, PyPI project `HomericIntelligence` | `403 OIDC scoped token not valid for project` | Distribution name must EXACTLY match PyPI project |
| Trusted publisher for new project | Added trusted publisher, not pending publisher | `400 Non-user identities cannot create new projects` | New projects need **pending publisher** first |
| Uppercase wheel glob | `HomericIntelligence_Hephaestus-*.whl` | File not found | PEP 625: wheels are always lowercase |
| Changed pyproject.toml only | Forgot pixi.toml/pixi.lock | `lock-file not up-to-date` | Must update pixi.toml dep name and regen lock |
| Non-verbose publish action | Default `verbose: false` | Only got `403 Forbidden` with no detail | Always enable `verbose: true` when debugging |

## Results & Parameters

### Working release workflow

```yaml
name: Release
on:
  push:
    tags: ["v*"]
permissions:
  contents: write
  id-token: write
jobs:
  build-and-publish:
    environment: pypi
    steps:
      - uses: pypa/gh-action-pypi-publish@release/v1
        with:
          verbose: true
```

### Namespace package pattern

| Repo | PyPI Name | Import | Wheel |
| ------ | ----------- | -------- | ------- |
| ProjectHephaestus | `HomericIntelligence-Hephaestus` | `import hephaestus` | `homericintelligence_hephaestus-*.whl` |
| ProjectKeystone | `HomericIntelligence-Keystone` | `import keystone` | `homericintelligence_keystone-*.whl` |

### Debugging checklist

1. Enable `verbose: true` on publish action
2. Check HTML error body in logs
3. Verify `id-token: write` permission
4. Verify environment name matches (case-sensitive)
5. Verify distribution name matches PyPI project
6. New projects: use pending publisher
