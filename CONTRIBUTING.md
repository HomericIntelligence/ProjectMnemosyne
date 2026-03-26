# Contributing to ProjectMnemosyne

Thank you for your interest in contributing to ProjectMnemosyne! This guide covers everything
you need to know about contributing skills, maintaining quality standards, and navigating the
PR process.

## Table of Contents

- [How to Contribute a Skill](#how-to-contribute-a-skill)
- [Skill Structure](#skill-structure)
- [Quality Standards](#quality-standards)
- [Categories](#categories)
- [Branch and Commit Conventions](#branch-and-commit-conventions)
- [Pull Request Process](#pull-request-process)
- [Validation](#validation)
- [Code Style](#code-style)
- [Cross-Repository Compatibility](#cross-repository-compatibility)

## How to Contribute a Skill

### Option 1: Automatic via `/learn` (Recommended)

The easiest way to contribute is using the `/learn` command after a valuable session:

1. Complete an experiment, debugging session, or development task.
2. Run `/learn` in your Claude Code session.
3. Claude automatically:
   - Reads your entire conversation history.
   - Extracts successes, failures, and parameters.
   - Auto-generates a skill filename: `<topic>-<subtopic>-<short-4-word-summary>`.
   - Creates a branch (`skill/<name>`), commits, pushes, and opens a PR.
4. Review and merge the PR.

### Option 2: Manual Creation

1. Copy the template: `templates/skill-template.md`
2. Save as `skills/<name>.md` (lowercase, kebab-case).
3. Fill in the YAML frontmatter (see [Skill Structure](#skill-structure) below).
4. Fill in all required markdown sections.
5. Optionally create `skills/<name>.notes.md` for raw session details.
6. Create a PR following the [branch conventions](#branch-and-commit-conventions).

## Skill Structure

All skills are flat markdown files in the `skills/` directory with YAML frontmatter.

```text
skills/<name>.md             # Main skill file with YAML frontmatter + markdown content
skills/<name>.notes.md       # (Optional) Additional context from development session
```

### Required YAML Frontmatter

```yaml
---
name: skill-name-here
description: "Use when: (1) specific condition, (2) another condition"
category: training
date: 2026-03-24
version: "1.0.0"
user-invocable: false
tags: [optional, searchable, keywords]
---
```

| Field | Description |
|-------|-------------|
| `name` | Lowercase, kebab-case identifier |
| `description` | Trigger conditions with specific use cases |
| `category` | One of the 9 approved categories (see below) |
| `date` | Creation date (YYYY-MM-DD) |
| `version` | Semantic version (e.g., "1.0.0") |
| `user-invocable` | Set to `false` for internal/sub-skills |
| `tags` | (Optional) Searchable keywords array |

### Required Markdown Sections

Every skill must include:

1. **Overview table** -- Date, objective, outcome.
2. **When to Use** -- Specific trigger conditions.
3. **Verified Workflow** -- Step-by-step instructions that worked, including a Quick Reference subsection.
4. **Failed Attempts table (REQUIRED)** -- Must include columns: Attempt, What Was Tried, Why It Failed, Lesson Learned.
5. **Results & Parameters** -- Copy-paste ready configs and expected outputs.

### Filename Convention

```
<topic>-<subtopic>-<short-4-word-summary>.md
```

All lowercase, kebab-case. Examples:
- `mojo-parametric-dtype-migration.md`
- `docker-pixi-isolation.md`
- `batch-subprocess-signal-hang.md`

## Quality Standards

1. **Specific descriptions**: Include trigger conditions, not vague summaries. Descriptions should specify *when* to use the skill (e.g., "Use when: (1) encountering vLLM weight sync errors, (2) setting up multi-GPU GRPO training").
2. **Failures required**: Every skill must document what did not work and why. The Failed Attempts table is mandatory.
3. **Copy-paste ready**: Parameters, configurations, and commands should work immediately when copied.
4. **No duplication**: Link to external docs instead of copying content. If a skill overlaps with an existing one, extend rather than duplicate.

## Categories

| Category | Description |
|----------|-------------|
| `training` | ML training experiments and hyperparameters |
| `evaluation` | Model evaluation and metrics |
| `optimization` | Performance tuning and speedups |
| `debugging` | Bug investigation and fixes |
| `architecture` | Design decisions and patterns |
| `tooling` | Automation and developer tools |
| `ci-cd` | Pipeline configurations and CI fixes |
| `testing` | Test strategies and patterns |
| `documentation` | Paper writing, academic reviews, knowledge docs |

## Branch and Commit Conventions

### Branch Naming

- **Skills (automatic)**: `skill/<name>` (e.g., `skill/mojo-parametric-dtype-migration`)
- **Fixes**: `fix/<issue-number>-<short-description>` (e.g., `fix/913-contributing-changelog`)
- **Features**: `feat/<short-description>`

### Commit Messages

Follow the [Conventional Commits](https://www.conventionalcommits.org/) format:

```
<type>: <short description>

[optional body]

[optional footer]
```

Common types:
- `feat:` -- New skill or feature
- `fix:` -- Bug fix or correction
- `docs:` -- Documentation changes
- `chore:` -- Maintenance tasks (e.g., marketplace.json updates)

Examples:
```
feat: add mojo-parametric-dtype-migration skill
fix: resolve marketplace validation issues and missing frontmatter fields
docs: update migration status - 100% complete
```

## Pull Request Process

1. Create a branch following the naming conventions above.
2. Make your changes (add skill files, fix issues, etc.).
3. Run validation locally before pushing (see [Validation](#validation)).
4. Push your branch and create a PR.
5. CI will automatically validate:
   - YAML frontmatter has required fields.
   - All required markdown sections are present.
   - Failed Attempts section exists.
   - Description is specific (20+ characters).
   - Category is valid.
6. Once CI passes and the PR is approved, it will be merged.
7. `marketplace.json` auto-updates on merge.

## Validation

All PRs are validated by CI. Run validation locally before submitting:

```bash
python3 scripts/validate_plugins.py skills/
```

The validator checks:
- Required frontmatter fields are present and valid.
- All required markdown sections exist.
- Failed Attempts table is included.
- Description meets minimum length (20+ characters).
- Category is one of the 9 approved values.

## Code Style

### Markdown

- Use ATX-style headers (`#`, `##`, `###`).
- Use fenced code blocks with language identifiers (e.g., ` ```bash`, ` ```yaml`).
- Use tables for structured data (overview, failed attempts, verified-on).
- Keep lines readable; no strict line length limit, but aim for clarity.

### YAML Frontmatter

- Use lowercase kebab-case for the `name` field.
- Quote string values that contain special characters.
- Use arrays for `tags`.

### General Principles

This project follows these development principles:

- **KISS**: Keep it simple. Do not add complexity when a simpler solution works.
- **YAGNI**: Do not add features until they are required.
- **DRY**: Do not duplicate functionality, data structures, or algorithms.
- **POLA**: Create intuitive and predictable interfaces.

## Cross-Repository Compatibility

Skills should be generic enough to work across multiple repositories:

1. **No `source:` in frontmatter** -- Do not include repository-specific source fields.
2. **Use placeholders** -- Replace hardcoded paths with `<project-root>`, `<test-path>`, `<package-manager>`.
3. **Add a "Verified On" section** -- Document where the skill was validated:
   ```markdown
   ## Verified On

   | Project | Context | Details |
   |---------|---------|---------|
   | ProjectName | PR #XXX context | [notes.md](../skills/skill-name.notes.md) |
   ```
4. **Move specifics to references** -- Put project-specific commands, paths, and code in a `.notes.md` file.
5. **Generic workflows** -- Write workflows that can be adapted to any repository structure.
