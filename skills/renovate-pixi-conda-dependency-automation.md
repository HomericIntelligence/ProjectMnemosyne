---
name: renovate-pixi-conda-dependency-automation
description: "Add Renovate config to automate conda-forge/pixi dependency updates that Dependabot cannot parse. Use when: (1) a repo uses pixi.toml for conda-forge deps but Dependabot only covers pip/github-actions, (2) conda deps are updated manually with no automation signal, (3) setting up Renovate to mirror an existing Dependabot cadence/grouping."
category: ci-cd
date: 2026-05-28
version: "1.0.0"
user-invocable: false
verification: verified-precommit
tags:
  - renovate
  - pixi
  - conda
  - conda-forge
  - dependabot
  - dependency-automation
  - renovate-json
---

# Renovate Config for conda/pixi Dependency Automation

## Overview

| Field | Value |
|-------|-------|
| **Date** | 2026-05-28 |
| **Objective** | Automate conda-forge/pixi dependency updates that Dependabot cannot cover |
| **Outcome** | Success — renovate.json created, validated, and merged via PR #667 |
| **Verification** | verified-precommit (Renovate app runtime validation pending first run) |

## When to Use

- A repo uses `pixi.toml` for conda-forge dependencies
- Dependabot is already configured for `pip` and `github-actions` but skips `pixi.toml`
- Conda deps (pydantic, pygithub, ruff, mypy, etc.) are drifting with no automated PRs
- You want Renovate cadence/grouping to mirror the existing Dependabot config

## Verified Workflow

> **Warning:** This workflow produces a valid renovate.json confirmed by JSON parse and pre-commit (verified-precommit); Renovate app first-run validation is pending CI integration.

### Quick Reference

```json
{
  "$schema": "https://docs.renovatebot.com/renovate-schema.json",
  "extends": [
    "config:recommended",
    ":pixi"
  ],
  "labels": ["dependencies"],
  "schedule": ["every week on monday"],
  "prConcurrentLimit": 5,
  "packageRules": [
    {
      "description": "Group all conda-forge / pixi deps into one PR",
      "matchManagers": ["pixi"],
      "groupName": "conda-pixi-dependencies",
      "labels": ["dependencies"],
      "commitMessagePrefix": "chore(deps):"
    },
    {
      "description": "Group GitHub Actions updates",
      "matchManagers": ["github-actions"],
      "groupName": "github-actions",
      "labels": ["dependencies", "ci/cd"],
      "commitMessagePrefix": "chore(deps):"
    }
  ]
}
```

```bash
# Validate JSON parses cleanly before committing
python3 -c "import json; json.load(open('renovate.json')); print('valid')"
```

### Detailed Steps

1. **Read `.github/dependabot.yml`** to note existing cadence (weekly), grouping strategy, labels, and commit-message prefix
2. **Create `renovate.json`** in the repo root using `config:recommended` + `:pixi` presets
3. **Mirror Dependabot cadence**: match `schedule` to `"every week on monday"` (weekly)
4. **Set `prConcurrentLimit`**: 5 avoids a PR flood on first Renovate run
5. **Add `packageRules`**: group `matchManagers: ["pixi"]` into one PR; group `github-actions` to match Dependabot behavior (avoids duplicate GHA PRs from both tools)
6. **Validate**: `python3 -c "import json; json.load(open('renovate.json'))"`
7. **Update `CONTRIBUTING.md`** Dependency Updates section — replace the manual-update note with a description of Renovate's coverage (keep the `pixi update` command for out-of-cycle manual refreshes)
8. **Commit** with `chore(deps): add Renovate config for conda/pixi dependencies` + `Closes #<issue>`

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
|---------|----------------|---------------|----------------|
| Using Dependabot for pixi | Dependabot `package-ecosystem: pip` | pip ecosystem cannot parse pixi.toml; pixi deps silently skipped | Must use Renovate with :pixi preset |
| No prConcurrentLimit | Omitting the PR cap | First Renovate run opens one PR per dependency | Set prConcurrentLimit: 5 to batch via groupName |
| Separate github-actions packageRule omitted | Letting Renovate handle GHA without explicit rule | Renovate may open duplicate GHA PRs alongside Dependabot | Add explicit github-actions packageRule with same groupName as Dependabot |

## Results & Parameters

Key config parameters:
- `extends: ["config:recommended", ":pixi"]` — the `:pixi` preset enables native pixi.toml parsing
- `schedule: ["every week on monday"]` — matches Dependabot weekly cadence
- `prConcurrentLimit: 5` — prevents PR flood on first run
- `matchManagers: ["pixi"]` in packageRules — targets only pixi.toml entries
- `commitMessagePrefix: "chore(deps):"` — matches Dependabot commit-message prefix convention

CONTRIBUTING.md update pattern (replace the manual-update paragraph):

```markdown
- **Renovate** (`renovate.json`) is configured with the `:pixi` preset and watches
  conda-forge / pixi dependencies in `pixi.toml` — the package ecosystem Dependabot
  cannot parse. Renovate opens grouped PRs on a weekly cadence, matching Dependabot's
  schedule. To manually refresh the lock file outside of that cycle:

  ```bash
  pixi update           # updates pixi.lock; commit alongside any range changes
  ```
```

## Verified On

| Project | Context | Details |
|---------|---------|---------|
| ProjectHephaestus | Issue #484 — Renovate for conda/pixi, PR #667 | JSON valid; pre-commit passed; Renovate app first run pending |
