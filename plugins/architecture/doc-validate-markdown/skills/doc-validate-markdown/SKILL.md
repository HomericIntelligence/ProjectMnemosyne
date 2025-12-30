---
name: doc-validate-markdown
description: "Validate markdown files for formatting, links, and style compliance using markdownlint"
category: architecture
source: ProjectOdyssey
date: 2025-12-30
---

# Validate Markdown Files

Validate markdown formatting and style compliance.

## Overview

| Date | Objective | Outcome |
|------|-----------|---------|
| 2025-12-30 | Consistent markdown formatting | Clean documentation passing CI |

## When to Use

- (1) Before committing documentation
- (2) Markdown linting errors in CI
- (3) Creating new documentation
- (4) Updating existing docs

## Verified Workflow

1. **Run validation** - Check all markdown files
2. **Review errors** - Identify issues by rule ID
3. **Auto-fix** - Fix auto-fixable issues
4. **Manual fix** - Address remaining issues
5. **Verify** - Re-run validation
6. **Commit** - Stage and commit changes

## Results

Copy-paste ready commands:

```bash
# Check all markdown
npx markdownlint-cli2 "**/*.md"

# Check specific file
npx markdownlint-cli2 README.md

# Fix auto-fixable issues
npx markdownlint-cli2 --fix "**/*.md"

# Check with config
npx markdownlint-cli2 --config .markdownlint.yaml "**/*.md"
```

### Common Issues & Fixes

**MD040: Code blocks need language**

```text
Wrong: code block without language tag
Correct: Add language like ```python or ```bash
```

**MD031: Blank lines around blocks**

Add one blank line before and after code blocks.

**MD013: Line too long**

Keep lines under 120 characters. Break at natural boundaries.

**MD022: Heading spacing**

Add blank line before and after headings.

### Configuration File

`.markdownlint.yaml`:

```yaml
line-length:
  line_length: 120
  code_blocks: false
  tables: false
```

### Validation Checklist

- [ ] All code blocks have language specified
- [ ] All code blocks have blank lines before and after
- [ ] All lists have blank lines before and after
- [ ] All headings have blank lines before and after
- [ ] No lines exceed 120 characters
- [ ] File ends with newline
- [ ] No trailing whitespace

## Failed Attempts

| Attempt | Why Failed | Lesson |
|---------|------------|--------|
| Ran `--fix` without reviewing changes | Auto-fix broke code examples | Always review auto-fix changes before committing |
| Fixed only reported line | Same error on adjacent lines | Fix all instances of same issue, not just reported ones |
| Ignored MD013 line length | CI still failed | Configure exceptions in `.markdownlint.yaml` instead of ignoring |
| Used different config locally vs CI | Inconsistent results | Use same config file in both environments |

## Error Handling

| Problem | Solution |
|---------|----------|
| MD040: Missing language tag | Add language: ` ```mojo ` |
| MD031: Missing blank lines | Add blank line before/after block |
| MD013: Line too long | Break line at 120 characters |
| MD022: Heading spacing | Add blank line before/after heading |

## References

- Related skill: quality-run-linters for complete linting
- Configuration: `.markdownlint.yaml`
