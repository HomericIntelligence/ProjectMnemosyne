---
name: generator-template-placeholder-cleanup
description: "Review TODO comments in code generator scripts and reclassify as TEMPLATE: markers or actual work items. Use when: cleaning up generator scripts, distinguishing template scaffolding from implementation gaps, or working on TODO-review issues."
category: documentation
date: 2026-03-04
user-invocable: false
---

## Overview

| Field | Value |
|-------|-------|
| **Category** | documentation |
| **Effort** | Low (mechanical substitution) |
| **Languages** | Python (generator scripts), any generated language |
| **Project Type** | Projects with code generation scripts that output scaffolded files |

## When to Use

- A GitHub cleanup issue asks to "review TODOs" in generator scripts
- Generator scripts contain `# TODO:` comments inside template string literals
- You need to distinguish intentional scaffolding (template placeholders) from actual implementation gaps
- Pre-commit hooks or linters flag TODO comments in code

## Key Insight: Two Kinds of TODOs in Generator Scripts

Generator scripts contain TODOs in two distinct locations:

1. **In Python logic** (the generator itself) — may be actual implementation gaps
2. **In Mojo/target-language template strings** — always intentional placeholders for generated output

The classification step is critical: read each TODO in context to determine which category it falls into.

## Verified Workflow

1. **Read all affected generator scripts** in parallel using the Read tool
2. **Classify each TODO** — check if it is inside a template string literal vs. Python code
3. **For template placeholders**: replace `# TODO:` with `# TEMPLATE:` in-place
4. **For actual work items**: create separate GitHub issues and link them
5. **For outdated items**: remove them
6. **Update script docstrings**: add a `Template Placeholders:` section to each script's module docstring explaining the `TEMPLATE:` convention
7. **Verify** with `grep "# TODO:" scripts/generators/` — should return no matches
8. **Run pre-commit** to confirm formatting/linting passes
9. **Commit, push, create PR** with `Closes #<issue>`

## Classification Decision Tree

```
Is the TODO inside a Python string literal (template body)?
├─ YES → TEMPLATE: placeholder — replace with # TEMPLATE:
└─ NO (bare Python code) → Is it needed for the script to work?
    ├─ YES, missing implementation → Create separate issue
    └─ NO, outdated → Remove it
```

## Results & Parameters

**Session results** (issue #3080, ProjectOdyssey):

- 4 generator scripts reviewed: `generate_tests.py`, `generate_model.py`, `generate_layer.py`, `generate_dataset.py`
- 31 TODOs found across all scripts
- 31/31 classified as template placeholders (0 actual work items, 0 outdated)
- All `# TODO:` → `# TEMPLATE:` substitutions made
- All 4 script docstrings updated with `Template Placeholders:` section
- Pre-commit hooks passed: ruff format, ruff check, markdownlint, trailing-whitespace, yaml

**Commit message format used**:
```
cleanup(generators): mark template placeholders with TEMPLATE: prefix

Review all TODO comments in generator scripts and classify each as an
intentional template placeholder. Replace all # TODO: markers with
# TEMPLATE: markers in generated Mojo output, and add Template Placeholders
documentation sections to each script's module docstring.

Closes #<issue>
```

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
|---------|----------------|---------------|----------------|
| Batch-replace all TODOs at once | Considered using `replace_all=True` on a single Edit call per file | TODOs had slightly different surrounding context, making single-pattern replacement fragile | Use individual targeted Edit calls per TODO for precision |
| Running full test suite | Ran `pixi run python -m pytest tests/ -v` expecting generator tests | No `tests/scripts/generators/` directory exists; generator scripts have no pytest tests | Check for test coverage before assuming tests exist; pre-commit is sufficient validation here |

## Notes

- The `# TEMPLATE:` convention is already established in this project (prior commit `e21e00b9` introduced it)
- When no `# TODO:` remain in generator scripts, grep confirms completeness: `grep -r "# TODO:" scripts/generators/` returns empty
- GLIBC errors from `mojo format` in pre-commit are a pre-existing environment issue (not caused by these changes) — all Python-targeted hooks still pass
