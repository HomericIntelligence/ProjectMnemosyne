# Code Quality Audit Implementation Workflow

| Attribute | Value |
|-----------|-------|
| **Date** | 2026-02-14 |
| **Category** | workflow |
| **Objective** | Implement findings from a comprehensive code quality audit by creating tracking issues and fixing HIGH priority items |
| **Outcome** | ✅ Successfully created 10 tracking issues (#670-679) and implemented all mechanical HIGH priority fixes |
| **Impact** | Coverage threshold increased to 80%, model configs fixed, backup files prevented, audit findings systematically tracked |

## Overview

This skill captures the complete workflow for implementing code quality audit findings, including:

1. Creating GitHub tracking issues for all audit findings
2. Implementing HIGH priority mechanical fixes
3. Verifying existing infrastructure
4. Creating a comprehensive PR with all changes

## When to Use This Skill

Use this workflow when:

- You have a completed code quality audit with actionable findings
- The audit has categorized findings by priority (HIGH/MEDIUM/LOW)
- You need to create tracking issues for systematic implementation
- You want to implement mechanical fixes while deferring complex refactoring

**Trigger phrases:**

- "Implement the quality audit findings"
- "Create tracking issues for code quality improvements"
- "Fix HIGH priority code quality issues"

## Verified Workflow

### Phase 1: Create Tracking Issues

1. **Create batch issue creation script**

   ```bash
   # Create script at scripts/quality_audit_<date>_issues.sh
   #!/usr/bin/env bash
   set -euo pipefail

   # Validate required labels first
   required_labels=("testing" "documentation" "refactor")
   for label in "${required_labels[@]}"; do
       if ! gh label list --limit 100 | grep -q "^${label}[[:space:]]"; then
           echo "ERROR: Required label '${label}' not found"
           exit 1
       fi
   done

   # Create issues sequentially (not parallel)
   issue_url=$(gh issue create --title "..." --label "..." --body "...")
   issue_num=$(echo "$issue_url" | grep -oP '\d+$')
   issue_numbers+=("$issue_num")
   ```

2. **Issue template structure**

   ```markdown
   ## Objective
   Brief description (2-3 sentences)

   ## Deliverables
   - [ ] Deliverable 1
   - [ ] Deliverable 2

   ## Success Criteria
   - Criterion 1
   - Criterion 2

   ## Priority
   HIGH/MEDIUM/LOW - Impact description

   ## Estimated Effort
   X hours

   ## Verification
   ```bash
   # Commands to verify fix
   ```

   ## Context

   From [Audit Name] (#ISSUE-NUMBER)

   ```

3. **Post summary to tracking issue**

   ```bash
   gh issue comment <tracking-number> --body "$(cat <<EOF
   ## GitHub Issues Created

   ### HIGH Priority
   - #<num> - Description

   ### MEDIUM Priority
   - #<num> - Description

   ### LOW Priority
   - #<num> - Description
   EOF
   )"
   ```

### Phase 2: Implement HIGH Priority Fixes

**Only implement mechanical/automated fixes:**

1. **Configuration changes** (coverage thresholds, .gitignore patterns)

   ```bash
   # Example: Update coverage threshold
   sed -i 's/fail_under = 70/fail_under = 80/' pyproject.toml
   ```

2. **Fix naming inconsistencies** (file renames, config corrections)

   ```bash
   # Example: Fix model config
   # Edit config/models/<file>.yaml to align name with file name
   ```

3. **Clean up artifacts**

   ```bash
   # Example: Remove backup files
   find . -name "*.orig" -type f -delete
   # Add pattern to .gitignore
   echo "*.orig" >> .gitignore
   echo "*.bak" >> .gitignore
   ```

**DO NOT implement:**

- Complex refactoring (function decomposition)
- Architectural changes (multi-stage Docker builds)
- Changes requiring design decisions

### Phase 3: Verification

1. **Verify pre-commit hooks pass**

   ```bash
   pre-commit run --all-files
   ```

2. **Check specific changes**

   ```bash
   # Coverage threshold
   grep "fail_under" pyproject.toml

   # Model configs
   for file in config/models/*.yaml; do
     grep -E "^(model_id|name):" "$file" | head -2
   done

   # .gitignore patterns
   grep -E "\.orig|\.bak" .gitignore
   ```

3. **Review git diff**

   ```bash
   git diff
   ```

### Phase 4: Create PR

1. **Stage and commit**

   ```bash
   git add <changed-files>
   git commit -m "feat(quality): Implement code quality audit findings from #<issue>

   Implements HIGH priority fixes from [Audit Name]:

   1. Created <N> GitHub tracking issues (#X-Y) for audit findings
   2. [List each HIGH priority fix with one-line description]
   3. Verified [existing infrastructure that didn't need changes]

   Created Issues:
   - HIGH: #X Description
   - MEDIUM: #Y Description
   - LOW: #Z Description

   Closes #<tracking-issue>

   Co-Authored-By: Claude Sonnet 4.5 <noreply@anthropic.com>"
   ```

2. **Push and create PR**

   ```bash
   git push -u origin <branch-name>

   gh pr create \
     --title "Implement Code Quality Audit Findings ([Date/Name])" \
     --body "..." \
     --label "refactor" --label "testing" --label "documentation"

   gh pr merge --auto --rebase
   ```

## Failed Attempts & Lessons Learned

### ❌ Failed: Using `--json` flag with `gh issue create`

**What was tried:**

```bash
issue_num=$(gh issue create ... --json number --jq .number)
```

**Why it failed:**

- The `--json` flag is not available in all versions of gh CLI
- Error: "unknown flag: --json"

**Solution:**
Extract issue number from URL returned by gh:

```bash
issue_url=$(gh issue create ...)
issue_num=$(echo "$issue_url" | grep -oP '\d+$')
```

### ❌ Failed: Assuming all fixes need implementation

**What was tried:**
Created tasks for mypy, YAML linting, .env.example, CONTRIBUTING.md

**Why it failed:**

- Many infrastructure items were already implemented
- Wasted time planning work that was already done

**Solution:**

1. Check existing infrastructure FIRST:

   ```bash
   # Check pre-commit hooks
   grep -A 5 "mypy" .pre-commit-config.yaml

   # Check for existing files
   ls -la .env.example CONTRIBUTING.md

   # Check pyproject.toml for existing configs
   grep -A 10 "\[tool.pytest" pyproject.toml
   grep -A 10 "\[tool.coverage" pyproject.toml
   ```

2. Only implement what's actually missing or needs fixing

### ⚠️ Important: Sequential vs Parallel Issue Creation

**Best practice:** Create issues **sequentially**, not in parallel

**Reason:**

- Easier to track which issues were created
- Prevents race conditions or API rate limiting
- Allows for better error handling per issue

## Results & Parameters

### Audit Metrics Implemented

| Metric | Before | After | Improvement |
|--------|--------|-------|-------------|
| Coverage Threshold | 70% | 80% | +10% |
| Backup Files | Not prevented | .gitignore | Protected |
| Model Config Issues | 2 inconsistencies | 0 | Fixed |
| Tracking Issues | 0 | 10 | Created |

### Configuration Changes

**pyproject.toml:**

```toml
[tool.coverage.report]
fail_under = 80  # Changed from 70
```

**.gitignore additions:**

```
*.orig
*.bak
```

**Model config fixes:**

- `claude-opus-4-1.yaml`: Corrected model_id and name to "4.1"
- `claude-sonnet-4-5.yaml`: Corrected name to "4.5"

### Script Template

The issue creation script pattern:

```bash
#!/usr/bin/env bash
set -euo pipefail

# 1. Validate labels
# 2. Create issues sequentially
# 3. Extract issue numbers from URLs
# 4. Post summary to tracking issue
```

## References

- Original tracking issue: #594
- Created issues: #670-679
- Pull request: #680
- Audit date: February 2026
- Overall audit grade: 78/100 (B)

## Team Knowledge Integration

This skill builds on:

- **code-quality-audit-principles** - How to conduct objective audits
- **quality-audit-tracking** - Issue creation patterns
- **quality-coverage-report** - Coverage threshold configuration
- **run-precommit** - Pre-commit hook verification

## Success Indicators

✅ **Complete** when:

- All audit findings have tracking issues
- HIGH priority mechanical fixes are implemented
- Pre-commit hooks pass
- PR created with auto-merge enabled
- Tracking issue updated with summary

❌ **Incomplete** if:

- Complex refactoring attempted (should be deferred to issues)
- Pre-commit hooks fail
- Verification commands don't pass
- Missing tracking issues for any findings
