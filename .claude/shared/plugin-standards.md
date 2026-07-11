# Plugin Standards

Standards for creating and validating skills in the Mnemosyne marketplace.

> **Format:** Mnemosyne uses the **flat-file skill format** introduced in v2.0.0.
> Each skill is a single markdown file at `skills/<name>.md`. There is no
> nested `<name>/SKILL.md`, no per-skill `plugin.json`, and no `.claude-plugin/`
> directory inside each skill. The only documented exception is
> `plugins/tooling/mnemosyne/` (command infrastructure), which is *not* a skill.
> See `CLAUDE.md` for repo structure and `templates/skill-template.md` for a
> ready-to-copy template.

## Required Structure

```text
skills/
└── <name>.md                  # Single flat skill file (REQUIRED)
```

Optional sibling files alongside `<name>.md`:

- `<name>.notes.md` / `<name>.notes-<topic>.md` — session notes (excluded from marketplace)
- `<name>.history*` — historical revisions (excluded from marketplace)

## SKILL Metadata (YAML Frontmatter in `<name>.md`)

| Field | Required | Description |
| ------- | ---------- | ------------- |
| `name` | Yes | Lowercase kebab-case identifier (matches the filename stem) |
| `description` | Yes | Trigger conditions (20+ chars) |
| `version` | Yes | Semantic version (e.g., "1.0.0") |
| `date` | Yes | Last-updated date (YYYY-MM-DD) |
| `category` | Yes | One of the approved categories below |
| `tags` | Yes | YAML list of searchable keywords |
| `verification` | Yes | One of `verified-ci`, `verified-local`, `verified-precommit`, `unverified` |
| `source` | No | Originating project (e.g., `ProjectOdyssey`) |

## SKILL.md Requirements

### YAML Frontmatter (Required)

```yaml
---
name: skill-name
description: "Trigger conditions (≥20 chars)"
category: category-name
version: "1.0.0"
date: YYYY-MM-DD
verification: verified-local
tags:
  - keyword-1
  - keyword-2
---
```

### Required Sections

1. **Title** (H1): Skill name
2. **Overview table**: Date, objective, outcome
3. **When to Use**: Bullet list of trigger conditions
4. **Verified Workflow**: Numbered steps that worked
5. **Failed Attempts** (REQUIRED): Table of failures
6. **Results & Parameters**: Copy-paste ready configs
7. **References**: Links to issues, docs

## Approved Categories

| Category | Description |
| ---------- | ------------- |
| `training` | ML training experiments |
| `evaluation` | Model evaluation |
| `optimization` | Performance tuning |
| `debugging` | Bug investigation |
| `architecture` | Design decisions |
| `tooling` | Automation tools |
| `ci-cd` | Pipeline configs |
| `testing` | Test strategies |

## Validation Rules

1. **`skills/<name>.md` must exist** — the flat file *is* the skill
2. **Frontmatter must be valid YAML** delimited by `---` lines
3. **Failed Attempts section required** — validation fails without it
4. **Description must be specific** — 20+ characters with trigger conditions
5. **Category must be valid** — one of the approved categories above
6. **Date format** — YYYY-MM-DD
7. **`verification` must be one of** `verified-ci` / `verified-local` / `verified-precommit` / `unverified`

## Quality Guidelines

### Good Description

```text
"GRPO training with external vLLM server. Use when: (1) Running vLLM on
separate GPUs, (2) vllm_skip_weight_sync errors, (3) OpenAI API parsing
issues. Verified on gemma-3-12b-it."
```

### Bad Description

```text
"Training experiments"  # Too vague, no trigger conditions
```

### Good Failed Attempts

| Attempt | Why Failed | Lesson |
| --------- | ----------- | -------- |
| Used inline vLLM | OOM on single GPU | Use external server |
| batch_size=16 | Gradient overflow | Use batch_size=4 |

### Bad Failed Attempts

| Attempt | Why Failed | Lesson |
| --------- | ----------- | -------- |
| It didn't work | Unknown | Try again |

## Search Command Standards

All grep/find commands in skills **MUST exclude hidden directories** to avoid searching `.pixi/`, `.git/`, `.cache/`, etc.

### Required Pattern

```bash
# Correct - excludes all directories starting with .
grep -rn "pattern" --include="*.ext" --exclude-dir='.*' .

# Multiple file types
grep -rn "FIXME" --include="*.mojo" --include="*.py" --exclude-dir='.*' .

# With Perl regex
grep -oP "FIXME\(#\K\d+" --include="*.mojo" --exclude-dir='.*' -r . | sort -u
```

### Common Mistake

```bash
# WRONG - searches .pixi/, .git/, .cache/, etc.
grep -rn "FIXME" --include="*.mojo" .

# CORRECT - excludes hidden directories
grep -rn "FIXME" --include="*.mojo" --exclude-dir='.*' .
```

### Why This Matters

- `.pixi/` contains thousands of dependency files with their own TODOs/FIXMEs
- `.git/` contains repository metadata
- Hidden directories pollute search results with false positives
- Slows down searches significantly
