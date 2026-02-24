---
name: extract-dependencies
description: "Analyze imports and identify all module dependencies. Use when mapping project structure."
mcp_fallback: none
category: analysis
tier: 2
---

# Extract Dependencies

## Overview

| Item | Details |
|------|---------|
| Date | N/A |
| Objective | Analyze import statements and identify all external and internal module dependencies in codebase. - Understanding module coupling |
| Outcome | Operational |


Analyze import statements and identify all external and internal module dependencies in codebase.

## When to Use

- Understanding module coupling
- Planning dependency updates
- Identifying circular dependencies
- Generating dependency graphs

## Quick Reference

```bash
# Python dependency extraction
grep -r "^import\|^from" --include="*.py" . | sort | uniq

# Generate dependency graph
pipdeptree

# Check for circular dependencies
python3 -c "import ast; [print(f.name) for f in ast.walk(ast.parse(open('file.py').read())) if isinstance(f, ast.Import)]"
```

## Verified Workflow

1. **Scan imports**: Extract all import statements from codebase
2. **Categorize dependencies**: Separate external, internal, standard library
3. **Map relationships**: Create graph of which modules import which
4. **Identify chains**: Trace dependency chains (A→B→C)
5. **Report analysis**: Document dependency structure and issues

## Output Format

Dependency analysis:

- External dependencies (with versions)
- Internal module dependencies
- Dependency graph (text or ASCII art)
- Circular dependencies (if found)
- Recommended import order
- Unnecessary or redundant dependencies

## Failed Attempts

| Attempt | Why Failed | Lesson |
|---------|------------|--------|
| N/A | This skill was migrated from uncategorized | Document failures as they occur |


## Results & Parameters

N/A — this skill describes a workflow pattern.

## References

- See `check-dependencies` skill for validation
- See `analyze-code-structure` skill for module organization
- See pixi.toml for declared project dependencies
