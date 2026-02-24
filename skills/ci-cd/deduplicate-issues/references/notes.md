# Session Notes: Deduplicate GitHub Issues

## Session Context

**Date**: 2026-02-15
**Branch**: `skill/ci-cd/deduplicate-issues`
**Objective**: Close duplicate and resolved GitHub issues to clean up the issue backlog

## Initial State

```bash
gh issue list --state open --limit 50
# Result: 23 open issues, 1 open PR (#706)
```

## Analysis Process

### Step 1: Identify Duplicate Patterns

**Pattern 1: Exact Duplicates from Parent Issue #601**

Three pairs of issues were created as follow-ups from the same parent issue, resulting in identical duplicates:

| Older (Keep) | Newer (Close) | Title | Created From |
|--------------|---------------|-------|--------------|
| #652 | #661 | Add HEALTHCHECK instruction to Dockerfile | #601 |
| #651 | #662 | Pin base image to SHA256 digest for reproducibility | #601 |
| #650 | #660 | Pin @anthropic-ai/claude-code npm package to specific version | #601 |

**Pattern 2: Near-Duplicates (Scope Overlap)**

| Keep | Close | Reasoning |
|------|-------|-----------|
| #664 (Refactor long lines in rubric YAML files) | #659 (Address long lines in test fixture rubric YAML files) | Both reference the same 2 files with the same 228-char lines. #664 has broader scope covering both files. |

### Step 2: Verify "Already Resolved" Claims

**Issue #657: Remove deprecated BaseRunResult dataclass**

Verification steps:

```bash
# Search for BaseRunResult in source code
grep -r "BaseRunResult" scylla/
# Result: No matches in source code

# Check if it exists only in documentation
grep -r "BaseRunResult" .claude-plugin/
# Result: Found in .claude-plugin/skills/type-alias-consolidation/SKILL.md
# Documentation confirms it was removed
```

**Conclusion**: #657 is already resolved - BaseRunResult no longer exists in source code.

### Step 3: Validate Non-Duplicates

**Issue #658: Standardize ExecutionInfo types**

Verification:

```bash
grep -rn "class ExecutionInfo" scylla/
# Found 3 separate ExecutionInfo classes:
# - scylla/reporting/result.py:12
# - scylla/core/results.py:62
# - scylla/executor/runner.py:60
```

**Conclusion**: Still valid - 3 separate classes exist that need standardization.

**Issue #692: ConfigLoader validation**

Compared to closed #673:

- #673: Fixed a specific config file
- #692: Add validation to prevent future issues

**Conclusion**: Different scope - #692 is about adding validation, not fixing a config.

**Issue #682: CI check for model config naming**

Compared to closed #637:

- #637: Fixed one config file
- #682: Add CI enforcement to prevent future issues

**Conclusion**: Different scope - #682 is about CI automation, not fixing a config.

## Execution Log

### Duplicate Closures (4 issues)

```bash
# Issue #661 (duplicate of #652)
gh issue comment 661 --body "Closing as duplicate of #652. Both issues request adding HEALTHCHECK instruction to Dockerfile, created as follow-ups from #601."
gh issue close 661 --reason "not planned"
# Output: ✓ Closed issue HomericIntelligence/ProjectScylla#661

# Issue #662 (duplicate of #651)
gh issue comment 662 --body "Closing as duplicate of #651. Both issues request pinning the Docker base image to SHA256 digest, created as follow-ups from #601."
gh issue close 662 --reason "not planned"
# Output: ✓ Closed issue HomericIntelligence/ProjectScylla#662

# Issue #660 (duplicate of #650)
gh issue comment 660 --body "Closing as duplicate of #650. Both issues request pinning @anthropic-ai/claude-code npm package to a specific version, created as follow-ups from #601."
gh issue close 660 --reason "not planned"
# Output: ✓ Closed issue HomericIntelligence/ProjectScylla#660

# Issue #659 (near-duplicate of #664)
gh issue comment 659 --body "Closing as duplicate of #664. Both issues address the same long lines (228 chars) in the same rubric YAML files. #664 covers the broader scope."
gh issue close 659 --reason "not planned"
# Output: ✓ Closed issue HomericIntelligence/ProjectScylla#659
```

### Already Resolved Closure (1 issue)

```bash
# Issue #657 (BaseRunResult already removed)
gh issue comment 657 --body "Closing as already resolved. BaseRunResult has been removed from the source code (no longer exists in scylla/). The removal was completed as part of the type-alias-consolidation work."
gh issue close 657 --reason "completed"
# Output: ✓ Closed issue HomericIntelligence/ProjectScylla#657
```

## Verification

```bash
gh issue list --state open --limit 50
# Result: 18 open issues (down from 23)
```

**Issues Closed**: 5
**Issues Remaining**: 18
**PR Status**: #706 still open (not a duplicate)

## Key Learnings

### What Worked Well

1. **Systematic approach**: Pre-planning phase identified all duplicates before making changes
2. **Clear criteria**: Kept older issues, closed newer ones consistently
3. **Documentation**: Every closure included an explanatory comment
4. **Verification**: Checked source code before closing "already resolved" issues
5. **Conservative approach**: When uncertain, left issues open (#658, #692, #682)

### Decision Framework

**For Exact Duplicates**:

- Same title + same description + same parent → Duplicate
- Close newer, keep older

**For Near-Duplicates**:

- Check if both address identical files/code
- Keep broader scope version
- Close narrower scope version

**For "Already Resolved"**:

- Search source code: `grep -r "ClassName" scylla/`
- Check git history: `git log --all --grep="keyword"`
- Only close if concrete evidence of resolution exists

### Automation Opportunities

**Future Enhancement**: Create a script to:

1. Fetch all open issues via GitHub API
2. Group by title similarity (fuzzy matching)
3. Flag potential duplicates for review
4. Generate closure commands with comments

## Related Issues

- **Parent Issue**: #601 (created many of the duplicates through automated workflow)
- **Kept Issues**: #652, #651, #650, #664 (remain open and valid)
- **Closed Issues**: #661, #662, #660, #659 (duplicates), #657 (resolved)
- **Validated Issues**: #658, #692, #682 (not duplicates, remain open)

## Command Reference

```bash
# List all open issues
gh issue list --state open --limit 50

# Search for code/classes in source
grep -rn "ClassName" scylla/

# Comment on issue
gh issue comment <number> --body "Message"

# Close issue with reason
gh issue close <number> --reason "not planned"  # For duplicates
gh issue close <number> --reason "completed"    # For already resolved

# View issue details
gh issue view <number> --comments
```

## Metadata

- **Session Duration**: ~10 minutes
- **Tools Used**: `gh` CLI, `grep`
- **Issues Analyzed**: 23
- **Issues Closed**: 5
- **Success Rate**: 100% (no errors, all closures executed correctly)
