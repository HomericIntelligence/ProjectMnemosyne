---
name: add-ci-badge-to-readme
description: "Add a GitHub Actions CI status badge to a README. Use when: a README is missing a CI badge, a new workflow should be surfaced via a badge, or a reviewer requests build status visibility."
category: documentation
date: 2026-03-07
user-invocable: false
---

## Overview

| Field | Value |
|-------|-------|
| **Skill** | add-ci-badge-to-readme |
| **Category** | documentation |
| **Complexity** | Low |
| **Time** | < 5 minutes |
| **Risk** | Minimal — single line README edit |

## When to Use

- A README has Mojo/License/Tests badges but no CI build status badge
- A new GitHub Actions workflow was added and should be visible on the project home page
- A GitHub issue or reviewer requests a CI badge
- Follow-up to adding a new workflow file

## Verified Workflow

1. **Find the workflow file** — confirm the target `.github/workflows/<name>.yml` exists:

   ```bash
   ls .github/workflows/
   ```

2. **Read the README badge block** — identify the line after which to insert the new badge:

   ```bash
   # Read lines 1-15 of README.md
   ```

3. **Insert the badge** using the Edit tool — append after the last existing badge:

   ```markdown
   [![CI](https://github.com/<org>/<repo>/actions/workflows/<workflow>.yml/badge.svg?branch=main)](https://github.com/<org>/<repo>/actions/workflows/<workflow>.yml)
   ```

   Badge URL pattern:
   - **Image**: `https://github.com/<org>/<repo>/actions/workflows/<file>.yml/badge.svg?branch=main`
   - **Link**: `https://github.com/<org>/<repo>/actions/workflows/<file>.yml`

4. **Validate with pre-commit** — run markdownlint to confirm no linting issues:

   ```bash
   pixi run pre-commit run --files README.md
   ```

5. **Commit, push, and create PR**:

   ```bash
   git add README.md
   git commit -m "docs(readme): add CI badge for <workflow> workflow"
   git push -u origin <branch>
   gh pr create --title "docs(readme): add CI badge for <workflow> workflow" \
     --body "Closes #<issue>"
   gh pr merge --auto --rebase
   ```

## Results & Parameters

| Parameter | Value Used | Notes |
|-----------|-----------|-------|
| Workflow file | `comprehensive-tests.yml` | Confirmed present before editing |
| Badge branch | `?branch=main` | Always pin to main for stability |
| Badge placement | After last existing badge | Keeps badge block together |
| Pre-commit hooks | All passed | markdownlint, trailing-whitespace, end-of-file |

### Badge Template (copy-paste)

```markdown
[![CI](https://github.com/<ORG>/<REPO>/actions/workflows/<WORKFLOW>.yml/badge.svg?branch=main)](https://github.com/<ORG>/<REPO>/actions/workflows/<WORKFLOW>.yml)
```

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
|---------|----------------|---------------|----------------|
| Writing tests | Issue template requested pytest tests for "new functionality" | There is no Python code — the change is a one-line README edit with no testable logic | Skip test writing for pure documentation changes; do not follow issue template boilerplate blindly |
| Running `just pre-commit-all` | Tried the justfile shortcut | `just` not on PATH in this environment | Fall back to `pixi run pre-commit run --files README.md` directly |
