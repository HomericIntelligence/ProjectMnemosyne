---
name: readme-from-codebase-exploration
description: "Replace placeholder README.md with accurate project description by exploring the live codebase. Use when: README has placeholder text, project has outgrown its docs, or a new contributor needs to understand quickly."
category: documentation
date: 2026-03-05
user-invocable: false
---

## Overview

| Attribute | Value |
|---|---|
| **Category** | documentation |
| **Trigger** | README contains placeholder text or is significantly out of date |
| **Output** | Accurate, structured README.md with verified links and real content |
| **Pre-commit** | `pixi run pre-commit run --files README.md` must pass |

## When to Use

- README.md contains placeholder lines like "Description here.", "Features list.", "Installation steps."
- The codebase has grown (new modules, architectures, test counts) but docs haven't kept up
- A P0 issue flags the README as misleading to new contributors
- Badge counts (tests, coverage) are stale

## Verified Workflow

### 1. Read the current README

Read the existing README first to understand what placeholders exist and what structure to keep.

### 2. Explore the live codebase in parallel

Run parallel queries to gather accurate content:

```bash
# Count actual test files
find . -name "test_*.mojo" | wc -l

# Count total source files
find . -name "*.mojo" | wc -l

# List model test files to enumerate architectures
ls tests/models/

# List shared library structure
ls shared/
```

### 3. Read supporting documentation

Read `shared/README.md`, `CONTRIBUTING.md`, `docs/getting-started/installation.md`,
and `pixi.toml` to gather real installation instructions and library descriptions.

### 4. Write the new README

Key sections to include:

- **What This Is** — 2-sentence project purpose + scale (lines of code, # architectures, # tests)
- **Implemented Architectures** — table with architecture, paper citation, status
- **Shared Library** — subsections per major module (core, autograd, training) with component lists
- **Getting Started** — real `pixi install`, real `just test-mojo` commands
- **Documentation** — links to actual files (verify they exist before linking)
- **Project Structure** — text tree of actual directories
- **Testing Strategy** — describe the real strategy (e.g. two-tier layerwise + e2e)
- **Coverage Status** — honest note if coverage tooling is blocked

### 5. Validate with pre-commit

```bash
pixi run pre-commit run --files README.md
```

All checks must pass: markdownlint, trailing whitespace, end-of-file fixer.

### 6. Commit and PR

```bash
git add README.md
git commit -m "docs(readme): replace placeholder text with accurate project description"
gh pr create --title "..." --body "Closes #<issue>"
gh pr merge --auto --rebase
```

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
|---------|----------------|---------------|----------------|
| Linking to `docs/getting-started/installation.md` content | Copying raw text from the file | The installation.md itself had placeholder content | Read the file before referencing it — don't assume docs are real |
| Using `npx markdownlint-cli2` for linting | Ran directly via pixi | `npx` not found in pixi environment | Use `pixi run pre-commit run --files README.md` instead |
| Running `just pre-commit-all` | Used `pixi run just` | `just` not found as a pixi command | Use `pixi run pre-commit run --files <file>` for single-file validation |

## Results & Parameters

### Badge Update Pattern

```markdown
[![Tests](https://img.shields.io/badge/tests-247%2B-brightgreen.svg)](tests/)
```

Count test files before writing: `find . -name "test_*.mojo" | wc -l`

### Architecture Table Pattern

```markdown
| Architecture | Paper | Status |
|---|---|---|
| LeNet-5 | LeCun et al., 1998 | Implemented |
| AlexNet | Krizhevsky et al., 2012 | Implemented |
```

### Shared Library Description Pattern

Group by subdirectory, not by individual file. Each subsection gets:
- A bold heading matching the directory name
- A bullet list of high-level capabilities (not filenames)

### Pre-commit Validation (Working Command)

```bash
pixi run pre-commit run --files README.md
```

Expected passing output:
```text
Markdown Lint............................................................Passed
Trim Trailing Whitespace.................................................Passed
Fix End of Files.........................................................Passed
Check for Large Files....................................................Passed
Fix Mixed Line Endings...................................................Passed
```
