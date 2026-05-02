---
name: batch-fix-implementation
description: Implement coordinated batch fixes across multiple files using minimal
  edits. Use when fixing multiple low-complexity issues in a single PR.
category: ci-cd
date: 2026-03-14
version: 1.0.0
user-invocable: false
---
## Overview

| Aspect | Details |
|--------|---------|
| **Purpose** | Coordinate batch fixes across 5+ files using minimal, focused edits |
| **When to Use** | Multiple low-complexity issues (text, comments, docstrings, trivial one-liners) that benefit from a single PR |
| **Complexity** | Simple edits per file, complex coordination across files |
| **Typical Duration** | 30-60 minutes for 8-10 fixes |
| **Files Modified** | 8-12 files per batch |
| **Key Skill** | Planning & parallel edits using Read/Edit tools effectively |

## When to Use

This skill applies when:

1. **Multiple isolated issues** (5+) can be fixed independently without blocking each other
2. **Issue scope is low-complexity**: Pure text changes, comment updates, docstring fixes, or trivial one-line code changes
3. **Changes are verifiable** without extensive testing (pre-commit hooks catch formatting issues)
4. **All fixes fit in one PR** without exceeding reasonable review scope (typically 10-12 issues per batch)
5. **No architectural changes** are needed (avoid mixing batch fixes with refactoring)

## Verified Workflow

### Step 1: Plan & Read All Files First

**Why**: Reading all files before editing prevents conflicts and ensures you understand the context.

1. Create a detailed plan listing all issues and exactly which files need changes
2. Read the current state of ALL files that will be modified
3. Note any import requirements or dependencies (e.g., `dtype_to_string()` must be imported)
4. Identify pre-existing lint/format issues that are OUT OF SCOPE

**Success Indicator**: You have complete knowledge of what will change before making edits

### Step 2: Apply Edits Sequentially by File

**Why**: Processing one file at a time prevents context switching errors.

1. Use Edit tool for each change (NOT Bash sed/awk)
2. Include sufficient context in old_string to ensure unique matches
3. For multiple occurrences in same file, either:
   - Use `replace_all: true` with careful context
   - Use `replace_all: false` and provide more context for each
4. Verify edit succeeded before moving to next file

**Example**: Fix `String(dtype)` → `dtype_to_string(dtype)` in 3 files

```
File 1: shared/utils/file_io.mojo
  Old: var dtype_str = String(dtype)
  New: var dtype_str = dtype_to_string(dtype)

File 2: shared/core/extensor.mojo
  Old: "Warning: randn() is designed for floating-point types, got", String(dtype),
  New: "Warning: randn() is designed for floating-point types, got", dtype_to_string(dtype),

File 3: shared/testing/fuzz_core.mojo
  Old: + String(dtype) + ", Error: "
  New: + dtype_to_string(dtype) + ", Error: "
```

### Step 3: Use Python Scripts for Bulk Text Replacements

**When**: 10+ identical replacements needed in same file (not suited for Edit tool)

**Example** - Replace 17 closing fence tags in scripts/README.md:

```python
import re

with open('scripts/README.md', 'r') as f:
    content = f.read()

# Replace only closing fences (lines with ```text on their own)
content = re.sub(r'^```text\s*$', '```', content, flags=re.MULTILINE)

with open('scripts/README.md', 'w') as f:
    f.write(content)
```

**Key**: Use regex with MULTILINE flag to match full-line patterns only

### Step 4: Handle Directory Restructuring Carefully

**For removals**: Use Edit tool with full context to remove subtrees

```
Old: (include entire block from first item to last item)
     ├── tests/                          # Agent test suite
     └── playground/                     # Deprecated/experimental scripts
         ├── README.md                   # Playground documentation
         ├── create_single_component_issues.py  # ...
         ...
         └── condense_mojo_guidelines.py

New: └── tests/                          # Agent test suite
```

**Key**: Include enough lines above/below to create a unique match

### Step 5: Validate with Pre-Commit Before Committing

```bash
# Check specific files that changed
pixi run npx markdownlint-cli2 docs/file1.md docs/file2.md
pixi run mojo format shared/file.mojo shared/other.mojo

# Run full pre-commit suite (optional, but recommended)
just pre-commit-all
```

**Know pre-existing issues**: If linter reports errors, check if they existed before your changes:

```bash
git diff <file> | grep -E "^[+-]" | head -20
```

### Step 6: Group Issues by PR Theme

Create branch with descriptive name:
```bash
git checkout -b batch/low-complexity-fixes-round2
```

Commit with all 8 issues in description:
```bash
git commit -m "fix: batch low-complexity fixes (Round 2)

- #3830: Replace String(dtype) with dtype_to_string() in 3 files
- #3919: Fix malformed code blocks in first_model.md
- #4465: Fix \`\`\`text closing fences in scripts/README.md (17 instances)
... (all 8 issues listed)

Co-Authored-By: Claude <noreply@anthropic.com>"
```

### Step 7: Create PR with Issue References

Use `Closes #<number>` in PR body for all issues:

```markdown
Closes #3830 #3919 #4465 #3988 #3822 #3823 #3968 #4097
```

Enable auto-merge:
```bash
gh pr merge --auto --rebase
```

### Quick Reference

| Task | Command |
|------|---------|
| Read file to verify state | `Read` tool with offset/limit |
| Make single edit | `Edit` with enough context for uniqueness |
| Make bulk replacements | Python script with `re.sub()` and MULTILINE flag |
| Check pre-existing issues | `git diff <file>` |
| Validate formatting | `pixi run npx markdownlint-cli2` or `pixi run mojo format` |
| Create batch branch | `git checkout -b batch/<theme>-<round>` |
| Link to issues | "Closes #X #Y #Z" in PR body |

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
|---------|----------------|---------------|----------------|
| Using Bash sed/awk for multiple edits | `sed -i 's/String(dtype)/dtype_to_string(dtype)/g'` | Pattern matching too broad, missed context-specific nuances | Always use Edit tool for code changes to preserve context |
| Replacing all ```text at once without checking context | Single regex replace for all 17 instances | Some were opening fences (need language tag), some closing (need bare ```) | Use `read()` to understand pattern first, then apply targeted fix |
| Making edits without reading file state first | Started editing based on plan assumptions | Didn't verify imports existed or understand exact line numbers | Always read files first, especially when dependencies may exist |
| Adding blank lines manually instead of via Python script | Tried to Edit add blank lines after every ``` fence | Created many duplicate/overlapping edit attempts | Use Python script for structural changes (blank lines, bulk replacements) |
| Not checking for pre-existing linter errors | Assumed all lint failures were from my changes | Wasted time trying to fix errors that existed before changes | Run `git diff` to see only changed lines, ignore pre-existing lint issues |
| Creating PR on existing batch branch | Tried to add round 2 fixes to existing `batch/low-complexity-fixes` branch | Branch already had PR #4509 from round 1 | Create new branch `batch/low-complexity-fixes-round2` for continuation |
| Trying to format Mojo files with mojo format command | `pixi run mojo format shared/file.mojo` | Got compiler error about missing `comptime_assert_stmt` (pre-existing Mojo bug) | Skip mojo format when compiler fails; verify changes manually via Read |
| Not grouping issues by common pattern | Processed issues one at a time | Lost sight of batch coordination benefits | Plan all issues up front, group by file/type before executing |

## Results & Parameters

### Successful Execution Parameters

```yaml
# Planning
issues_per_batch: 8
files_affected: 9
complexity_level: low  # Text/comment/docstring only, no refactoring

# Execution
read_before_edit: true  # Always read files first
use_edit_tool: true  # For code changes
use_python_script: true  # For 10+ bulk replacements
validate_with_git_diff: true  # Check only changed lines

# Validation
skip_precommit_on_compiler_error: true  # Mojo format has known bugs
check_pre_existing_lint: true  # Ignore errors from before changes
validate_imports: true  # Verify dtype_to_string() exists before replacing

# PR Creation
auto_merge_enabled: true  # Set for smooth merging
branch_naming: "batch/<theme>-<round>"  # Descriptive, round-specific
issue_closures: "Closes #X #Y #Z ..." # All issues in description
```

### Files Modified in Working Example

```
shared/utils/file_io.mojo          # String(dtype) → dtype_to_string()
shared/core/extensor.mojo          # String(dtype) → dtype_to_string()
shared/testing/fuzz_core.mojo      # String(dtype) → dtype_to_string()
docs/getting-started/first_model.md  # Fix doubled opening fences, closing tags
scripts/README.md                  # Replace 17 ```text closing tags, remove stale trees
.github/workflows/README.md        # Add 3 missing workflows to table
CLAUDE.md                          # Add mojo-format compat note
docs/dev/mojo-glibc-compatibility.md  # Fix Debian 10/11 reference
tests/shared/test_imports_part1.mojo  # Part 1 of split
```

### Key Learnings

1. **Planning is critical**: Spend 10 minutes planning before first edit saves 30 minutes of back-and-forth
2. **Read files first**: Understanding current state prevents edit conflicts and missed context
3. **Python scripts shine for bulk replacements**: For 10+ identical changes, regex is faster and safer than Edit tool
4. **Batch by theme**: Group related issues (e.g., all markdown fence fixes) in description for clarity
5. **Pre-existing lint issues exist**: Always check `git diff` to verify your changes didn't introduce errors
6. **Branch naming matters**: Use round-specific names to avoid PR conflicts on batch work
7. **Auto-merge on day one**: Set auto-merge immediately after PR creation for smooth CI integration
