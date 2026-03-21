---
name: github-actions-security-patterns
description: Secure GitHub Actions workflows against command injection via user-controlled inputs. Use when creating or reviewing workflow files.
category: ci-cd
date: 2026-03-20
version: 1.0.0
---

# GitHub Actions Security Patterns

| Field | Value |
|-------|-------|
| Date | 2026-03-10 |
| Objective | Create secure CI/CD workflows for TitanSchedule |
| Outcome | Success — caught injection risk via pre-commit hook |

## When to Use

- Creating GitHub Actions workflows with `workflow_dispatch` inputs
- Reviewing workflows that use any `github.event.*` context in `run:` commands
- Any workflow that accepts external/user-controlled data

## Verified Workflow

1. Use `env:` block to pass user-controlled inputs to `run:` commands
2. Reference via `$ENV_VAR` (shell variable) instead of `${{ }}` (template interpolation)

### Safe Pattern

```yaml
- name: Run scraper
  env:
    SCRAPE_URL: ${{ github.event.inputs.url || vars.DEFAULT_URL }}
  run: pixi run scrape "$SCRAPE_URL"
```

### Unsafe Pattern (AVOID)

```yaml
- run: pixi run scrape ${{ github.event.inputs.url }}
```

## Overview

| Field | Value |
|-------|-------|
| **Date** | YYYY-MM-DD |
| **Objective** | Skill objective |
| **Outcome** | Success/Operational |

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
|---------|----------------|---------------|----------------|
| N/A | Direct approach worked | N/A | Solution was straightforward |
## Risky Inputs Reference

All of these should use the `env:` pattern, never direct interpolation in `run:`:
- `github.event.inputs.*` (workflow_dispatch)
- `github.event.issue.title` / `.body`
- `github.event.pull_request.title` / `.body` / `.head.ref`
- `github.event.comment.body`
- `github.event.commits.*.message`
- `github.head_ref`

## Results & Parameters

- Tool: Pre-commit security hook caught the vulnerability automatically
- Fix: One-line change — wrap in `env:` block, quote the shell variable
