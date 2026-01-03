# Batch PR Creation and CI Fixer

| Field | Value |
|-------|-------|
| Date | 2025-12-31 |
| Objective | Create PRs for orphaned branches and fix CI failures across multiple PRs |
| Outcome | Successfully created 8 PRs and fixed CI failures in 4 of them |
| Repository | mvillmow/ProjectOdyssey |

## When to Use

- Multiple branches exist without corresponding PRs
- Several PRs are failing CI with similar issues
- Need to batch process branches after a development sprint
- Orphaned feature branches need cleanup

## Verified Workflow

### Phase 1: Identify Orphaned Branches

```bash
# List all remote branches
git fetch --all
git branch -r --format='%(refname:short)' | grep -v 'origin/HEAD'

# Check existing PRs to avoid duplicates
gh pr list --state all --json number,title,headRefName,state

# Compare commits between branch and main
git log origin/main..origin/<branch> --oneline
```

### Phase 2: Batch Create PRs

```bash
# For each branch with completed work:
gh pr create --head "<branch-name>" \
  --title "<type>(scope): description" \
  --body "$(cat <<'EOF'
## Summary
- Key change 1
- Key change 2

## Test Plan
- [x] Tests pass
- [x] Pre-commit passes

Closes #<issue-number>

Generated with [Claude Code](https://claude.com/claude-code)
EOF
)"

# Enable auto-merge immediately
gh pr merge <pr-number> --auto --rebase
```

### Phase 3: Diagnose CI Failures

```bash
# Check CI status
gh pr checks <pr-number>

# Get failed run logs
gh run view <run-id> --log-failed | head -100

# Common failure patterns to look for:
# - "mojo-format" → needs `pixi run mojo format`
# - "List[Type](args)" → deprecated syntax
# - "validate-test-coverage" → new test not in CI workflow
# - "ruff-check-python" → unused imports/variables
```

### Phase 4: Fix Each PR

```bash
# Checkout the branch
git checkout <branch-name>
git pull origin <branch-name>

# Fix mojo formatting
pixi run mojo format <file1.mojo> <file2.mojo>

# Fix Python linting
pixi run ruff check --fix <file.py>

# Commit and push
git add <files>
git commit -m "fix: resolve pre-commit issues"
git push
```

## Failed Attempts

### 1. Pushing Without Running Pre-commit Locally
**What happened**: All 8 PRs were created but 4 failed CI due to formatting issues.
**Why it failed**: `mojo format` wasn't run on new/modified files before pushing.
**Lesson**: Always run `just pre-commit-all` before pushing.

### 2. Missing Test Coverage Validation
**What happened**: PR #3027 failed because `test_composed_op.mojo` wasn't in CI workflow.
**Why it failed**: New test files must be explicitly added to `.github/workflows/comprehensive-tests.yml`.
**Fix**: Add new test files to the appropriate test group pattern.

### 3. Deprecated List Syntax in Docstrings
**What happened**: `List[Int](3, 3)` in docstring examples triggered CI failure.
**Why it failed**: Pre-commit hook checks all `.mojo` files including code in docstrings.
**Fix**: Use list literals `[3, 3]` even in documentation examples.

## Results & Parameters

### PRs Created

| PR | Branch | Issue | Status |
|----|--------|-------|--------|
| #3021 | 3008--testing--fp4-mxfp4-test-cover | #3008 | Passed |
| #3022 | 3009--testing--float16-precision-is | #3009 | Fixed |
| #3023 | 3010--testing--placeholder-test-fix | #3010 | Fixed |
| #3024 | 3011--cleanup--unused-variable-decl | #3011 | Passed |
| #3026 | 3013--feature--extensor-operations- | #3013 | Fixed |
| #3027 | 3014--feature--autograd-enhancement | #3014 | Fixed |
| #3028 | 3015--feature--simd-mixed-precision | #3015 | Passed |

### Common CI Fixes Applied

| Issue | Files Affected | Fix |
|-------|----------------|-----|
| Mojo format | conv.mojo, matrix.mojo, shape.mojo, traits.mojo | `pixi run mojo format <file>` |
| Deprecated List syntax | conftest.mojo | `List[Int](3, 3)` → `[3, 3]` |
| Unused Python imports | test_dependency_resolver.py | `pixi run ruff check --fix` |
| Missing test coverage | comprehensive-tests.yml | Add test file to pattern |

### Key Commands Reference

```bash
# Batch check all PR statuses
for pr in 3021 3022 3023 3024 3026 3027 3028; do
  echo "PR #$pr:"
  gh pr checks $pr 2>&1 | grep -E "fail|pass" | head -5
done

# Get failed logs for a specific PR
gh pr checks <pr> | grep fail | awk '{print $4}' | xargs -I{} gh run view {} --log-failed

# Fix and push in one command
git checkout <branch> && \
  pixi run mojo format $(git diff --name-only HEAD~1 | grep '\.mojo$') && \
  git add -A && \
  git commit -m "style: apply mojo format" && \
  git push
```

## Checklist for Future Use

- [ ] Run `just pre-commit-all` before creating PRs
- [ ] Check if new test files need CI workflow updates
- [ ] Use list literals `[1, 2, 3]` not `List[Int](1, 2, 3)`
- [ ] Enable auto-merge immediately after PR creation
- [ ] Close duplicate PRs with proper comments
