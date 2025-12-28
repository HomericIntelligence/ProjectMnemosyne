# Plugin Standards

Standards for creating and validating skills in the ProjectMnemosyne marketplace.

## Required Structure

```text
plugins/<category>/<name>/
├── .claude-plugin/
│   └── plugin.json           # Metadata (REQUIRED)
├── skills/<name>/
│   └── SKILL.md              # Main knowledge (REQUIRED)
└── references/
    └── notes.md              # Additional context (optional)
```

## plugin.json Requirements

| Field | Required | Description |
|-------|----------|-------------|
| `name` | Yes | Lowercase kebab-case identifier |
| `version` | Yes | Semantic version (e.g., "1.0.0") |
| `description` | Yes | Trigger conditions (20+ chars) |
| `author.name` | Yes | Author name |
| `date` | Yes | Creation date (YYYY-MM-DD) |
| `category` | Yes | One of 8 approved categories |
| `tags` | Yes | Array of searchable keywords |
| `skills` | Yes | Path to skills directory |
| `source_project` | No | Source project name |

## SKILL.md Requirements

### YAML Frontmatter (Required)

```yaml
---
name: skill-name
description: "Trigger conditions"
category: category-name
source: source-project
date: YYYY-MM-DD
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
|----------|-------------|
| `training` | ML training experiments |
| `evaluation` | Model evaluation |
| `optimization` | Performance tuning |
| `debugging` | Bug investigation |
| `architecture` | Design decisions |
| `tooling` | Automation tools |
| `ci-cd` | Pipeline configs |
| `testing` | Test strategies |

## Validation Rules

1. **plugin.json must exist** in `.claude-plugin/` directory
2. **SKILL.md must exist** in `skills/<name>/` directory
3. **Failed Attempts section required** - validation fails without it
4. **Description must be specific** - 20+ characters with trigger conditions
5. **Category must be valid** - one of 8 approved categories
6. **Date format** - YYYY-MM-DD

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
|---------|-----------|--------|
| Used inline vLLM | OOM on single GPU | Use external server |
| batch_size=16 | Gradient overflow | Use batch_size=4 |

### Bad Failed Attempts

| Attempt | Why Failed | Lesson |
|---------|-----------|--------|
| It didn't work | Unknown | Try again |
