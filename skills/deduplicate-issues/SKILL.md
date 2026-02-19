# Skill: Deduplicate GitHub Issues

## Overview

| Field | Value |
|-------|-------|
| **Date** | 2026-02-15 |
| **Objective** | Systematically identify and close duplicate or resolved GitHub issues |
| **Outcome** | ✅ Successfully closed 5 issues (4 duplicates, 1 already resolved) |
| **Impact** | Reduced open issue count from 23 to 18 |
| **Category** | ci-cd |

## When to Use This Skill

Use this skill when:

1. **Repository has accumulated duplicate issues** from:
   - Automated issue creation workflows that create duplicates
   - Parent issues spawning multiple identical child issues
   - Similar issues created at different times

2. **Issues are already resolved but not closed**:
   - Code changes completed but issue wasn't updated
   - Work done as part of another issue/PR
   - Feature implemented in a different way

3. **Issue backlog needs cleanup** to:
   - Improve issue tracker signal-to-noise ratio
   - Make priority planning more effective
   - Reduce cognitive load for developers

## Verified Workflow

### Phase 1: Discovery and Analysis

1. **List all open issues**:

   ```bash
   gh issue list --state open --limit 50
   ```

2. **Identify duplicate patterns**:
   - **Exact duplicates**: Same title, same description, same parent
   - **Near-duplicates**: Similar scope, overlapping objectives
   - **Already resolved**: Code exists, feature implemented, work completed

3. **For each duplicate pair, determine which to keep**:
   - **Prefer older issues** (created first) - maintains issue number continuity
   - **Keep the more detailed issue** if creation times are close
   - **Keep the issue with more activity** (comments, references)

4. **Verify resolution claims**:

   ```bash
   # Search codebase for mentioned classes/functions
   grep -r "ClassName" scylla/

   # Check git history for related changes
   git log --all --grep="keyword"
   ```

### Phase 2: Systematic Closure

For each issue to close:

1. **Add explanatory comment** before closing:

   ```bash
   gh issue comment <number> --body "Closing as duplicate of #<kept-issue>. [Explanation]"
   ```

2. **Close with appropriate reason**:
   - `--reason "not planned"` - For duplicates
   - `--reason "completed"` - For already resolved

   ```bash
   gh issue close <number> --reason "not planned"
   ```

3. **Document the closure decision** in the comment:
   - What makes it a duplicate
   - Which issue supersedes it
   - Why one was chosen over the other

### Phase 3: Verification

1. **List open issues again** to confirm closure:

   ```bash
   gh issue list --state open --limit 50
   ```

2. **Verify expected count**:
   - Calculate: `previous_count - closed_count = expected_count`
   - Confirm closed issues no longer appear

## Session Example

### Context

- Repository had 23 open issues
- Multiple duplicate pairs created from automated workflows
- One issue already resolved but not closed

### Duplicates Identified

| Keep (older) | Close (newer) | Reason |
|--------------|---------------|--------|
| #652 | #661 | Both request HEALTHCHECK in Dockerfile |
| #651 | #662 | Both request pinning base image to SHA256 |
| #650 | #660 | Both request pinning npm package version |
| #664 | #659 | Same long lines in same YAML files (#664 broader scope) |
| N/A | #657 | BaseRunResult already removed from codebase |

### Execution Commands

```bash
# Pair 1: HEALTHCHECK - close #661, keep #652
gh issue comment 661 --body "Closing as duplicate of #652. Both issues request adding HEALTHCHECK instruction to Dockerfile, created as follow-ups from #601."
gh issue close 661 --reason "not planned"

# Pair 2: Pin base image - close #662, keep #651
gh issue comment 662 --body "Closing as duplicate of #651. Both issues request pinning the Docker base image to SHA256 digest, created as follow-ups from #601."
gh issue close 662 --reason "not planned"

# Pair 3: Pin claude-code npm - close #660, keep #650
gh issue comment 660 --body "Closing as duplicate of #650. Both issues request pinning @anthropic-ai/claude-code npm package to a specific version, created as follow-ups from #601."
gh issue close 660 --reason "not planned"

# Near-duplicate: Long lines in YAML - close #659, keep #664
gh issue comment 659 --body "Closing as duplicate of #664. Both issues address the same long lines (228 chars) in the same rubric YAML files. #664 covers the broader scope."
gh issue close 659 --reason "not planned"

# Already resolved: BaseRunResult removal
gh issue comment 657 --body "Closing as already resolved. BaseRunResult has been removed from the source code (no longer exists in scylla/). The removal was completed as part of the type-alias-consolidation work."
gh issue close 657 --reason "completed"
```

### Results

- **Issues closed**: 5 (4 duplicates, 1 resolved)
- **Final count**: 18 open issues
- **All closures documented** with explanatory comments

## Failed Attempts

**None in this session.** The workflow executed cleanly because:

1. **Pre-planning phase** identified all duplicates before execution
2. **Clear duplicate criteria** (same title, same parent, same content)
3. **Verification step built in** (source code search for "already resolved" claims)
4. **Systematic approach** prevented errors

### Potential Pitfalls (Not Encountered)

- **Closing wrong issue in a pair**: Always close the newer issue, keep the older
- **Missing context**: Some "duplicates" may have subtle differences requiring separate issues
- **Over-aggressive cleanup**: Issues that seem similar but address different aspects
- **Not verifying "already resolved"**: Always check source code, not just assumptions

## Parameters & Configuration

### GitHub CLI Settings

```bash
# Ensure proper authentication
gh auth status

# Required scopes: repo (full), read:org
```

### Issue Closure Reasons

| Reason | Use Case |
|--------|----------|
| `not planned` | Duplicates, out of scope, decided against |
| `completed` | Already resolved, work finished |

### Comment Template

```markdown
Closing as duplicate of #<kept-issue>. [Brief explanation of why they're duplicates and which parent/workflow created them.]
```

## Best Practices

1. **Always comment before closing** - Explain the decision for future reference
2. **Link to the kept issue** - Make it easy to find the canonical issue
3. **Keep older issues** - Maintains issue number continuity and references
4. **Verify resolution claims** - Search codebase before closing as "completed"
5. **Document patterns** - If duplicates came from a workflow, note it for fixing
6. **Be conservative** - When unsure if it's truly a duplicate, leave open or ask

## Integration with Other Skills

- **Complements**: `github-issue-workflow` skill for general issue management
- **Precedes**: Issue prioritization and sprint planning
- **Follows**: Automated issue creation workflows that may create duplicates

## References

- [GitHub CLI issue commands](https://cli.github.com/manual/gh_issue)
- [ProjectScylla GitHub Issue Workflow](/.claude/shared/github-issue-workflow.md)
