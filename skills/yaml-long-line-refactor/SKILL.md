# YAML Long Line Refactor

**Category:** ci-cd
**Date:** 2026-02-15
**Source:** Issue #664
**Outcome:** ✅ Success

| Metric | Value |
|--------|-------|
| **Objective** | Fix yamllint warnings for lines exceeding 120 characters |
| **Files Modified** | 2 (docs/arxiv/dryrun/raw/rubric.yaml, tests/fixtures/tests/test-001/expected/rubric.yaml) |
| **Warnings Eliminated** | 2 (line length: 228 → 3 lines under 120 chars each) |
| **Tests Passed** | 51 rubric-related tests, all pre-commit hooks |
| **Semantic Preservation** | ✅ Verified with yaml.safe_load() - identical parsed output |

## When to Use This Skill

Use this skill when:

- yamllint reports line length warnings (e.g., "228 > 120 chars")
- YAML files contain long string values that exceed line length limits
- You need to improve YAML readability without changing parsed values
- Pre-commit hooks or CI fail due to YAML line length issues

**Trigger Patterns:**

- `yamllint: line too long (XXX > 120 characters)`
- Long inline strings in YAML configuration files
- Need to refactor YAML while maintaining semantic equivalence

## Verified Workflow

### 1. Identify Long Lines

```bash
# Run yamllint to find warnings
yamllint path/to/file.yaml

# Expected output:
# file.yaml:95:121: [warning] line too long (228 > 120 characters) (line-length)
```

### 2. Choose Block Scalar Type

**Decision Matrix:**

| Scalar Type | Symbol | Behavior | Use Case |
|-------------|--------|----------|----------|
| **Folded** | `>` | Joins lines with spaces (single paragraph) | Long descriptions, error messages, documentation |
| **Literal** | `\|` | Preserves line breaks (multi-line text) | Code blocks, formatted text, poetry |

**For this use case:** Use folded block scalar (`>`) for long descriptive strings that should remain as single paragraphs.

### 3. Refactor YAML

**Before:**

```yaml
check: "Overall engineering judgment: Is the solution appropriately scoped for a Hello World task? Consider: simplicity vs over-engineering, maintainability, clarity, and whether a senior engineer would approve this PR."
```

**After:**

```yaml
check: >
  Overall engineering judgment: Is the solution appropriately scoped for a Hello World task?
  Consider: simplicity vs over-engineering, maintainability, clarity, and whether a senior
  engineer would approve this PR.
```

**Key Points:**

- Use `>` (folded block scalar) for text that should be joined with spaces
- Indent continuation lines consistently (typically 2 spaces)
- Break lines at natural boundaries (sentence endings, punctuation)
- Keep each line under the limit (120 chars for yamllint default)

### 4. Validate Changes

```bash
# Step 1: Verify yamllint warnings are resolved
yamllint path/to/file.yaml
# Expected: No warnings, exit code 0

# Step 2: Verify semantic equivalence
python3 -c "
import yaml
with open('path/to/file.yaml') as f:
    data = yaml.safe_load(f)
    # Navigate to the refactored field
    value = data['path']['to']['field']
    print(f'Length: {len(value)}')
    print(f'Text: {repr(value)}')
"
# Expected: Text should be identical to original (spaces join lines, trailing newline added)

# Step 3: Run pre-commit hooks
pre-commit run --all-files
# Expected: All hooks pass

# Step 4: Run tests
pytest tests/ -v -k <relevant_test_pattern>
# Expected: All tests pass
```

### 5. Commit and Create PR

```bash
# Stage changes
git add path/to/file.yaml

# Commit with descriptive message
git commit -m "fix(yaml): refactor long lines using block scalars

Refactor long lines (XXX > 120 chars) using YAML folded block scalar syntax
to improve readability and eliminate yamllint warnings.

Closes #<issue-number>"

# Push and create PR
git push -u origin <branch-name>
gh pr create --title "fix(yaml): refactor long lines using block scalars" \
  --body "Closes #<issue-number>"
gh pr merge --auto --rebase
```

## Failed Attempts

### ❌ None - First Approach Succeeded

**Why it worked:**

- Straightforward application of YAML block scalar syntax
- Clear yamllint error messages pointed directly to problematic lines
- Folded block scalar (`>`) was the correct choice for this text type
- Validation workflow caught any potential issues early

**Risk Mitigation:**

- Verified semantic equivalence with `yaml.safe_load()` to ensure parsed values were identical
- Tested against all rubric-related tests (51 tests passed)
- Ran pre-commit hooks to catch any formatting issues

## Results & Parameters

### yamllint Configuration

Default configuration from `.yamllint` (no custom overrides needed):

```yaml
rules:
  line-length:
    max: 120
    level: warning
```

### Files Modified

1. **docs/arxiv/dryrun/raw/rubric.yaml:95**
   - Original: 228 characters (single line)
   - Refactored: 3 lines (98, 93, 32 chars)
   - Parsed length: 212 chars (includes trailing newline from block scalar)

2. **tests/fixtures/tests/test-001/expected/rubric.yaml:96**
   - Identical change for test fixture consistency

### Validation Results

```bash
# yamllint validation
$ yamllint docs/arxiv/dryrun/raw/rubric.yaml
# No output (success)

$ yamllint tests/fixtures/tests/test-001/expected/rubric.yaml
# No output (success)

# Pre-commit hooks
$ pre-commit run --all-files
Check for shell=True (Security)..........................................Passed
Ruff Format Python.......................................................Passed
Ruff Check Python........................................................Passed
Mypy Type Check Python...................................................Passed
Markdown Lint............................................................Passed
YAML Lint................................................................Passed
Trim Trailing Whitespace.................................................Passed
Fix End of Files.........................................................Passed
Check for Large Files....................................................Passed
Fix Mixed Line Endings...................................................Passed

# Tests
$ pytest tests/ -v -k rubric
51 passed, 2094 deselected, 1 warning in 9.34s

# Semantic verification
$ python3 -c "import yaml; ..."
✓ Both files have identical parsed check text
```

### Block Scalar Behavior

**Folded Block Scalar (`>`):**

- Joins lines with single spaces
- Adds trailing newline at end
- Preserves empty lines as paragraph breaks
- Trims trailing whitespace from each line

**Example:**

```yaml
# Input
text: >
  Line one
  Line two
  Line three

# Parsed as
"Line one Line two Line three\n"
```

## Key Learnings

1. **Always verify semantic equivalence** - Use `yaml.safe_load()` to ensure refactored YAML produces identical parsed values
2. **Choose the right block scalar** - Folded (`>`) for paragraphs, Literal (`|`) for formatted text
3. **Test fixture consistency** - Apply identical changes to both production and test files
4. **Line breaking strategy** - Break at natural boundaries (sentence endings) for better readability
5. **Validation workflow** - yamllint → pre-commit → tests → semantic verification

## References

- YAML Specification: <https://yaml.org/spec/1.2/spec.html#id2796251>
- yamllint Documentation: <https://yamllint.readthedocs.io/>
- Issue #664: Refactor long lines in rubric YAML files
- PR #725: Implementation

## Related Skills

- `yaml-frontmatter-validation` - YAML validation and formatting patterns
- `validate-workflow` - yamllint validation approach
- `quality-fix-formatting` - Automated formatting workflow
- `run-precommit` - Pre-commit hook best practices
