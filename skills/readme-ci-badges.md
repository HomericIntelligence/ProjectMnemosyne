---
name: readme-ci-badges
description: 'Add GitHub Actions status badges for key CI workflows to a README badge
  block. Use when: adding missing PR-critical workflow badges, improving CI health
  visibility at a glance, or following up on a badge audit issue.'
category: documentation
date: 2026-03-15
version: 1.0.0
user-invocable: false
---
## Overview

| Field | Value |
|-------|-------|
| **Skill** | readme-ci-badges |
| **Category** | documentation |
| **Effort** | Very Low (single-line edit) |
| **Risk** | None — purely additive README change |
| **Pre-commit safe** | Yes — markdownlint, trailing-whitespace, end-of-file-fixer all pass |

## When to Use

- A follow-up issue asks to add CI badges for workflows that run on every PR
- README badge row is missing a workflow that represents a critical quality gate
- New workflow was added to `.github/workflows/` and the README was not updated
- Performing a CI health audit and want visitors to see full build status at a glance

## Verified Workflow

### Quick Reference

Badge URL pattern:
```text
[![<Label>](https://github.com/<org>/<repo>/actions/workflows/<file>.yml/badge.svg?branch=main)](https://github.com/<org>/<repo>/actions/workflows/<file>.yml)
```

### Step 1 — Identify missing badges

```bash
ls .github/workflows/
```

Compare the listed `.yml` files against the badge block at the top of `README.md`.
Prioritize workflows that trigger on every PR (e.g., `build-validation.yml`,
`pre-commit.yml`, `security.yml`, `comprehensive-tests.yml`).

### Step 2 — Locate the existing badge block

```bash
head -20 README.md
```

Find the last badge line in the existing block to know where to insert.

### Step 3 — Add the badge

Use the Edit tool to insert the new badge **after** the last existing CI badge:

```markdown
[![Build](https://github.com/HomericIntelligence/ProjectOdyssey/actions/workflows/build-validation.yml/badge.svg?branch=main)](https://github.com/HomericIntelligence/ProjectOdyssey/actions/workflows/build-validation.yml)
```

### Step 4 — Validate

```bash
pixi run pre-commit run --files README.md
```

All hooks must pass (markdownlint, trailing-whitespace, end-of-file-fixer).

### Step 5 — Commit and PR

```bash
git add README.md
git commit -m "docs(readme): add <Label> badge for <file>.yml workflow

Closes #<issue-number>"

git push -u origin <branch>
gh pr create --title "docs(readme): add <Label> badge for <file>.yml" \
  --body "Closes #<issue-number>" --label "documentation"
gh pr merge --auto --rebase
```

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
|---------|----------------|---------------|----------------|
| Adding badge before the CI badge | Inserted new badge before `[![CI](…)]` | Broke visual grouping — CI should anchor the block | Always append after the last existing CI badge, not before |
| Comma-separating `Closes` lines | `Closes #3922, #3306` in PR body | Project convention requires one `Closes #N` per line | Use separate lines for each issue reference |

## Results & Parameters

### Session: issue-3922 (2026-03-15)

**Issue**: "Add badges for other key GitHub Actions workflows" (follow-up from #3306)

**Workflows already badged**: `comprehensive-tests.yml` (CI), `pre-commit.yml`, `security.yml`

**Workflow added**: `build-validation.yml` → `[![Build](…)](…)`

**Pre-commit result**: All hooks passed with zero changes needed

**PR**: https://github.com/HomericIntelligence/ProjectOdyssey/pull/4831

### Copy-paste badge template

```markdown
[![Build](https://github.com/HomericIntelligence/ProjectOdyssey/actions/workflows/build-validation.yml/badge.svg?branch=main)](https://github.com/HomericIntelligence/ProjectOdyssey/actions/workflows/build-validation.yml)
```

### Criteria for "badge-worthy" workflows

A workflow deserves a README badge if it:

1. Runs on every PR (`on: pull_request`)
2. Represents a critical quality gate (build, test, lint, security)
3. Is not a niche/supplemental workflow (benchmarks, weekly scans, etc.)
