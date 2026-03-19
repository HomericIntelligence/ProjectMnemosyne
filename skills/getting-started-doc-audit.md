---
name: getting-started-doc-audit
description: 'Audit and rewrite getting-started documentation stubs by sourcing real
  commands from justfile and versions from pixi.toml, removing fabricated APIs. Use
  when: stub files contain placeholder text, follow-up audit after installation.md
  is written, or markdown linting fails on broken fenced code blocks.'
category: documentation
date: 2026-03-15
version: 1.0.0
user-invocable: false
---
## Overview

| Field | Value |
|-------|-------|
| **Skill** | getting-started-doc-audit |
| **Category** | documentation |
| **Trigger** | Follow-up audit of `docs/getting-started/` after one doc is written |
| **Output** | Rewritten stubs with accurate commands, no fabricated APIs, clean markdown |

## When to Use

- A follow-up issue requests auditing remaining stubs in `docs/getting-started/` after
  `installation.md` was written
- Any file in `docs/getting-started/` contains fabricated function calls or API names that
  don't exist in the codebase (e.g., `TensorDataset`, `Trainer`, `EarlyStopping`)
- Fenced code blocks are malformed (duplicate delimiters, missing language tags, unclosed blocks)
- Commands in docs reference scripts or tools that don't exist (e.g., non-existent Python scripts,
  benchmark tools not yet implemented)

## Verified Workflow

### Quick Reference

```bash
# 1. List files to audit
ls docs/getting-started/

# 2. Read each file to identify placeholder content
# 3. Check real commands
grep -E "^(train|build|test|infer)" justfile
grep -E "mojo|version" pixi.toml

# 4. Check what actually exists in the codebase
ls shared/ papers/ scripts/

# 5. Rewrite placeholder files, then lint
pixi run npx markdownlint-cli2 docs/getting-started/*.md
```

### Step 1: Audit all files in the directory

Read every file in `docs/getting-started/` and classify each as:

- **Accurate** — commands and APIs are real; no rewrite needed
- **Placeholder text** — contains fabricated API calls or stub prose
- **Broken markdown** — malformed fenced code blocks (common: duplicate delimiters like
  ` ```bash\n```bash ` or unclosed blocks ending in ` ```text `)

The most reliable signal for fabricated APIs: check whether the imported modules or function
calls actually exist by grepping the codebase.

```bash
# Verify API exists before keeping it in docs
grep -r "TensorDataset" shared/ papers/
grep -r "class Trainer" shared/
```

### Step 2: Establish ground truth from build system files

**Never invent commands.** Source everything from:

```bash
# Real justfile recipes
cat justfile | grep -E "^[a-z]"

# Pinned dependency versions
grep -E "mojo|version" pixi.toml

# What directories actually exist
ls papers/ shared/ scripts/ tools/ 2>&1
```

### Step 3: Rewrite placeholder files

For each file with placeholder content:

1. Keep the document's purpose and headings
2. Replace all fabricated API calls with real ones (or remove the section entirely if
   the feature doesn't exist yet)
3. Replace all non-existent commands with confirmed `just` or `pixi run` commands
4. Fix malformed fenced code blocks (one opening delimiter, one language tag, one closing delimiter)

**Pattern for conceptual content over fabricated API docs**:

When the APIs shown don't exist yet, rewrite the doc as a conceptual orientation:
- What exists today (real shared library, real recipes)
- What is still planned (clearly labeled)
- How to use what currently exists

### Step 4: Lint and fix

```bash
pixi run npx markdownlint-cli2 docs/getting-started/*.md
```

Common lint errors and fixes:

| Error | Cause | Fix |
|-------|-------|-----|
| MD001 heading-increment | h5 after h3 (h3 inside h5 block resets level) | Change inner `#####` to `####` |
| MD040 fenced-code-language | Code block missing language tag | Add language after opening ` ``` ` |
| MD031 blanks-around-fences | No blank line before/after code block | Add blank lines |

### Step 5: Commit and PR

```bash
git add docs/getting-started/<file1>.md docs/getting-started/<file2>.md
git commit -m "docs(getting-started): rewrite <files> with accurate commands"
git push -u origin <branch>
gh pr create --title "..." --body "Closes #<issue>"
```

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
|---------|----------------|---------------|----------------|
| Keeping fabricated APIs | Preserved `TensorDataset`, `Trainer`, `EarlyStopping` imports in first_model.md | These types don't exist in `shared/`; docs would mislead users and fail when tried | Always grep the codebase to verify APIs before keeping them in docs |
| Using `#####` subsections inside `####` blocks that also contain `###` headings | Kept original heading structure with h3 inner sections | Markdownlint MD001: after a `###` resets the "current level", a subsequent `#####` is seen as jumping 2 levels | Flatten inner subsections to bold text, or demote the `#####` items to `####` |
| Referencing non-existent scripts | Kept `python scripts/validate_links.py`, `python tools/paper-scaffold/scaffold.py` in repository-structure.md | Scripts don't exist in the repo; running them fails | Check `ls scripts/` and `ls tools/` before including any script path in docs |
| Using `mojo test tests/` command | Showed `mojo test tests/` as the test command | Project uses `just test-mojo` and `just test-group`; bare `mojo test` not configured | Always check justfile for the project's actual test recipes |

## Results & Parameters

**Session outcome**: 2 files rewritten, 0 markdownlint errors, PR #4828 created.

**Files changed**:

- `docs/getting-started/first_model.md` — full rewrite (760→252 lines net after removing
  fabricated content)
- `docs/getting-started/repository-structure.md` — fixed all malformed fenced code blocks,
  replaced non-existent scripts with real `just` commands

**Files with no changes needed**:

- `docs/getting-started/quickstart.md` — already accurate with real commands and verified output
- `docs/getting-started/installation.md` — written in the previous issue (#3304), already accurate

**Lint validation**:

```bash
pixi run npx markdownlint-cli2 docs/getting-started/first_model.md docs/getting-started/repository-structure.md
# Summary: 0 error(s)
```

**Mojo version in pixi.toml**: `0.26.1`

**Justfile recipes used in docs** (confirmed real):

```text
train, infer, build, build-release, test-mojo, test-group, pre-commit, pre-commit-all
```
