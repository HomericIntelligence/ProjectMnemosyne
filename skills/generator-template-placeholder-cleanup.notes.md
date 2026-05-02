# Session Notes: generator-template-placeholder-cleanup

## Session Context

- **Date**: 2026-03-04
- **Project**: ProjectOdyssey
- **Issue**: #3080 — [Cleanup] Review generator script TODOs
- **Branch**: `3080-auto-impl`
- **PR**: #3176

## Objective

Review 31 TODO comments across 4 generator Python scripts and determine whether each is:
1. An intentional template placeholder (keep, mark with TEMPLATE:)
2. An actual implementation gap (create separate issue)
3. Outdated (remove)

## Files Affected

| File | TODOs | Classification |
| ------ | ------- | ---------------- |
| `scripts/generators/generate_tests.py` | 14 | All template placeholders |
| `scripts/generators/generate_model.py` | 5 | All template placeholders (3 in Mojo template strings, 2 in Python fallback strings) |
| `scripts/generators/generate_layer.py` | 4 | All template placeholders |
| `scripts/generators/generate_dataset.py` | 8 | All template placeholders |

## Key Discovery

The generator scripts produce Mojo source code by interpolating Python template strings.
TODOs inside those template strings are intentional scaffolding in the *output* — they
signal to the developer that after running the generator, they must fill in module-specific
logic. They are not gaps in the generator Python code itself.

Two TODOs in `generate_model.py` appear in Python code (lines 266, 293) but are inside
string return values that get embedded in generated output — also template placeholders.

## Steps Taken

1. Read all 4 scripts in parallel
2. Classified all 31 TODOs as template placeholders
3. Made individual Edit calls to replace each `# TODO:` with `# TEMPLATE:`
4. Added `Template Placeholders:` docstring section to all 4 script module docstrings
5. Verified with grep: no remaining `# TODO:` in scripts/generators/
6. Ran pre-commit: all Python hooks passed (mojo format skipped due to GLIBC environment issue)
7. Committed: `cleanup(generators): mark template placeholders with TEMPLATE: prefix`
8. Pushed branch, created PR #3176, enabled auto-merge

## Validation

```bash
# Confirm no TODOs remain
grep -r "# TODO:" scripts/generators/  # returns empty

# Pre-commit result
Ruff Format Python.......Passed
Ruff Check Python........Passed
Validate Test Coverage...Passed
Markdown Lint............Passed
Trim Trailing Whitespace.Passed
Fix End of Files.........Passed
Check YAML...............Passed
```
