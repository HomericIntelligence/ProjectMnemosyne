---
name: write-installation-docs
description: 'Replace placeholder installation documentation with complete, accurate
  content. Use when: installation.md contains placeholder text, a README links to
  an installation guide that needs real content, or a follow-up issue requests writing
  real installation steps.'
category: documentation
date: 2026-03-07
version: 1.0.0
user-invocable: false
---
## Overview

| Field | Value |
|-------|-------|
| **Skill** | write-installation-docs |
| **Category** | documentation |
| **Trigger** | Placeholder installation docs, README linking to stub guide |
| **Output** | Complete installation.md with prereqs, install steps, verification, Docker alt, troubleshooting |
| **Validation** | markdownlint-cli2 via pre-commit hook |

## When to Use

- `docs/getting-started/installation.md` contains placeholder text ("Step 1", "Requirements.", etc.)
- A README or other doc links to an installation guide that has no real content
- A follow-up issue requests writing real installation steps after initial scaffolding
- Pixi-based Mojo project needs onboarding documentation

## Verified Workflow

1. **Read current file** to confirm placeholder state
2. **Read issue comments** for implementation plan: `gh issue view <N> --comments`
3. **Source version data** from `pixi.toml` — do NOT guess versions
4. **Source commands** from `justfile` — use exact recipe names
5. **Write complete content** covering:
   - Prerequisites (platform, Git, Pixi, optional Docker)
   - Pixi installation via curl
   - Repository cloning
   - `pixi install` with channel info
   - Mojo version requirement from `pixi.toml`
   - Verification with `just build` and `just test-mojo`
   - Docker alternative using GHCR image
   - Troubleshooting (channel errors, version mismatch, `just` not found, container not running)
6. **Validate markdown** — run pre-commit markdownlint hook:
   ```bash
   pixi run pre-commit run --all-files markdownlint-cli2
   ```
7. **Commit and push** — stage only the doc file, not the prompt file
8. **Create PR** linked to issue with `Closes #<N>` in body

## Key Decisions

### Source Versions from pixi.toml — Not From Memory

Always read `pixi.toml` for the exact Mojo version constraint before writing docs.
Do not use approximate version strings from memory.

```toml
# Example from pixi.toml
[dependencies]
mojo = ">=0.26.1.0.dev2025122805,<0.27"
```

Document the constraint range (`>=0.26.1,<0.27`) not the full nightly build string.

### Source Commands from justfile — Not From README

Read the `justfile` directly to confirm recipe names. The README may be stale.
Key recipes: `just build`, `just test-mojo`, `just docker-up`, `just shell`.

### Use `pixi run pre-commit run` for Markdownlint Validation

`npx` may not be available in the pixi environment. Use the pre-commit hook instead:

```bash
# WORKS
pixi run pre-commit run --all-files markdownlint-cli2

# FAILS - npx not found in pixi env
pixi run npx markdownlint-cli2 path/to/file.md
```

### Troubleshooting Section Is Required

Installation docs that lack troubleshooting cause repeated support requests.
Always include sections for: channel errors, version mismatches, missing tools, container not running.

## Results & Parameters

### Markdownlint Rules to Follow

- Language tags on all fenced code blocks (` ```bash `, ` ```toml `, ` ```text `)
- Blank line before and after every code block
- Blank line before and after every list
- Blank line before and after every heading
- Lines <= 120 characters

### Recommended Section Structure

```text
# Installation
## Prerequisites
## Installing Pixi
## Cloning the Repository
## Installing Dependencies
## Mojo Version Requirements
## Verifying the Installation
## Docker Alternative
### Pull the Development Image
### Start the Development Environment
### Open a Shell in the Container
### Run Tests Directly
## Troubleshooting
### <pixi install> fails with channel errors
### Mojo version mismatch
### <just> command not found
### Docker container not running
```

### Git: Stage Only the Doc File

The worktree may contain a `.claude-prompt-<N>.md` file — do NOT stage it:

```bash
git add docs/getting-started/installation.md
# Do NOT: git add .
```

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
|---------|----------------|---------------|----------------|
| `pixi run npx markdownlint-cli2 path/to/file.md` | Used npx to run markdownlint directly | `npx: command not found` in the pixi env | Use `pixi run pre-commit run --all-files markdownlint-cli2` instead |
| Hardcoding Mojo version string | Writing `0.26.1.0.dev2025122805` directly | Full nightly build strings go stale immediately | Use version range (`>=0.26.1,<0.27`) from pixi.toml constraint |
