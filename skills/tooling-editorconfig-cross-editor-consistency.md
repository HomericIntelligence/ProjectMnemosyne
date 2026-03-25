---
name: tooling-editorconfig-cross-editor-consistency
description: "Add .editorconfig for cross-editor formatting consistency. Use when: (1) repository
  lacks .editorconfig, (2) contributors use different editors with inconsistent indentation/whitespace,
  (3) non-Python files (YAML, JSON, Markdown, shell) need formatting standards beyond what ruff covers."
category: tooling
date: 2026-03-25
version: "1.0.0"
user-invocable: false
verification: verified-precommit
tags:
  - editorconfig
  - developer-experience
  - formatting
  - cross-editor
---

# Skill: EditorConfig Cross-Editor Consistency

## Overview

| Field | Value |
|-------|-------|
| **Date** | 2026-03-25 |
| **Objective** | Add `.editorconfig` to ensure consistent editor settings across all file types and IDEs |
| **Outcome** | Success — PR created, pre-commit passes |
| **Verification** | verified-precommit |

## When to Use

- Repository has no `.editorconfig` at the root
- Multiple file types (Python, YAML, JSON, TOML, Markdown, shell) need consistent formatting
- Python formatting is handled by ruff/black but non-Python files have no formatting enforcement
- Audit finding flags missing cross-editor consistency configuration
- Companion to `.gitattributes` (git-level line endings) — `.editorconfig` handles editor-level settings

## Verified Workflow

> **Note:** Verification level is `verified-precommit` — pre-commit hooks pass but CI validation pending.

### Quick Reference

```bash
# 1. Check if .editorconfig exists
ls .editorconfig 2>&1 || echo "does not exist"

# 2. Inventory file types to determine indent settings
find . -name "*.py" -o -name "*.yml" -o -name "*.yaml" -o -name "*.json" \
       -o -name "*.toml" -o -name "*.sh" -o -name "*.md" \
       -o -name "Dockerfile*" -o -name "Makefile" | head -20

# 3. Create .editorconfig (see template below)

# 4. Validate
pre-commit run --files .editorconfig
```

### Detailed Steps

1. **Check for existing `.editorconfig`** — if one exists, amend it rather than replacing.

2. **Inventory file types in the repo** to determine which sections are needed:
   - Python (`.py`) — always 4-space indent per PEP 8
   - YAML (`.yml`, `.yaml`) — always 2-space indent
   - JSON/TOML — typically 2-space indent
   - Markdown (`.md`) — trailing whitespace must be preserved (significant for line breaks)
   - Shell scripts (`.sh`) — typically 2-space indent
   - Dockerfiles — typically 4-space indent
   - Makefiles — **must use tabs** (Make syntax requires it)

3. **Create `.editorconfig`** using this template:

```ini
root = true

[*]
end_of_line = lf
insert_final_newline = true
charset = utf-8
trim_trailing_whitespace = true

[*.py]
indent_style = space
indent_size = 4

[*.{yml,yaml}]
indent_style = space
indent_size = 2

[*.md]
trim_trailing_whitespace = false

[*.{json,toml}]
indent_style = space
indent_size = 2

[*.sh]
indent_style = space
indent_size = 2

[Dockerfile*]
indent_style = space
indent_size = 4
```

**Important**: If the repo has a `Makefile`, add:
```ini
[Makefile]
indent_style = tab
```

4. **Key setting: `root = true`** — prevents EditorConfig from searching parent directories. Always include this.

5. **Key setting: `trim_trailing_whitespace = false` for Markdown** — two trailing spaces in Markdown create a `<br>` line break. Trimming them would break formatting.

6. **Run pre-commit** to validate:
```bash
pre-commit run --files .editorconfig
```

7. **Commit and PR** following conventional commit format:
```
feat(dx): add .editorconfig for cross-editor consistency
```

### Alignment with Existing Tools

| Concern | `.editorconfig` | `.gitattributes` | ruff/black |
|---------|-----------------|-------------------|------------|
| Line endings | `end_of_line = lf` | `* text=auto eol=lf` | N/A |
| Python indent | `indent_size = 4` | N/A | Enforced |
| YAML indent | `indent_size = 2` | N/A | N/A |
| Trailing whitespace | `trim_trailing_whitespace` | N/A | Python only |
| Final newline | `insert_final_newline` | N/A | Python only |

`.editorconfig` is complementary — it configures the editor *before* you type, while linters/formatters fix *after* you save. `.gitattributes` normalizes at the git layer.

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
|---------|----------------|---------------|----------------|
| N/A | Direct approach worked | N/A | Adding .editorconfig is straightforward — no gotchas encountered |

## Results & Parameters

**Session outcome**: PR #1556 created in ProjectScylla

**Template covers**: Python (4-space), YAML (2-space), JSON/TOML (2-space), shell (2-space), Dockerfile (4-space), Markdown (preserve trailing whitespace)

**Pre-commit result**: All hooks passed (most skipped as not applicable to `.editorconfig` file type)

**Relationship to other skills**:
- Pair with `gitattributes-setup` for complete cross-platform + cross-editor consistency
- Pair with `repo-hygiene-audit-implementation` when implementing audit findings

## Verified On

| Project | Context | Details |
|---------|---------|---------|
| ProjectScylla | Issue #1526, PR #1556 | Audit finding S13 — DX section |
