---
name: bulk-issue-dedup
description: "Bulk deduplicate GitHub issues by clustering similar titles, identifying canonical issues, and closing duplicates with explanatory comments. Use when: issue tracker has grown noisy with repeated variants of the same request, or before sprint planning to reduce open issue count."
category: tooling
date: 2026-03-13
user-invocable: false
---

## Overview

| Field | Value |
|-------|-------|
| **Category** | tooling |
| **Complexity** | Low-Medium |
| **Time** | 30–90 min depending on issue count |
| **Prerequisites** | `gh` CLI authenticated, read/write access to repo |

Systematically reduces GitHub issue noise by identifying duplicate clusters, finding the canonical
(oldest) issue per cluster, and bulk-closing all variants with a comment linking to the canonical.
Also identifies "subset" issues (narrower scope of a broader parent) and closes those separately.

## When to Use

- Issue count has grown 3x+ from organic development (agents repeatedly creating similar issues)
- Sprint planning is blocked by noisy issue list
- ADR or standard has generated 10+ near-identical follow-up issues
- Before classifying issues by complexity, want to remove obvious duplicates first

## Verified Workflow

### Quick Reference

```bash
# List all open issues
gh issue list --state open --limit 500 --json number,title \
  --jq '.[] | "\(.number)\t\(.title)"'

# Bulk close a cluster (canonical = lowest number, keep open)
CANONICAL=4101
for issue in 4450 4446 4441 4436 4429; do
  gh issue close "$issue" \
    --comment "Duplicate of #$CANONICAL — closing as part of bulk dedup"
done

# Close subset issues (narrower scope)
gh issue close 3867 \
  --comment "Subset of #3774 — scope is covered by the broader parent issue"
```

### Step 1: Retrieve all open issues

```bash
gh issue list --state open --limit 500 --json number,title \
  --jq '.[] | "\(.number)\t\(.title)"' > /tmp/issues.txt
wc -l /tmp/issues.txt
```

Use `--limit 500` (or higher) to get all issues in one call.

### Step 2: Identify duplicate clusters

Look for title patterns like:

- `"Audit all X for Y compliance"` repeated 20+ times
- `"Add Y pre-commit hook"` repeated 15+ times
- `"Document X in Y"` repeated 10+ times
- `"Fix X in Y.mojo"` with same underlying issue

Use an agent with the full issue list to reason about clusters:

```
Analyze these N open GitHub issues and identify ALL duplicate clusters.
For each cluster, identify:
1. The canonical (lowest number) issue
2. All duplicates to close
3. Any subset issues (narrower scope than a broader parent)

Output bash commands to close them all with appropriate comments.
```

### Step 3: Close duplicates in batches

For exact duplicates:

```bash
for issue in LIST_OF_DUPLICATES; do
  gh issue close "$issue" \
    --comment "Duplicate of #CANONICAL — closing as part of bulk dedup"
done
```

For subset issues:

```bash
gh issue close SUBSET_NUMBER \
  --comment "Subset of #PARENT — this specific case is covered by the broader parent issue"
```

### Step 4: Verify already-resolved issues

For "stale reference" or "verify X exists" issues, check the actual file state before closing:

```bash
# Example: verify stale count claim
grep "12 func" docs/dev/phases.md

# If not found → issue is already resolved
gh issue close 4435 --comment "Already resolved — file now shows correct count after prior refactor"
```

**Key rule**: Always read the file/config BEFORE assuming an issue is stale. Prior refactoring
may have already fixed it.

### Step 5: Track totals

```bash
# Count remaining open issues
gh issue list --state open --limit 500 --json number --jq 'length'
```

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
|---------|----------------|---------------|----------------|
| Close all in one loop | Used single bash loop for all 95 issues | `gh` rate limiting hit on large batches | Break into smaller batches of 10-20 |
| Auto-detect duplicates via title similarity | Tried fuzzy string matching in Python | Too many false positives (e.g., "audit X" ≠ "add X audit") | Use agent reasoning for cluster detection instead |
| Fix pre-existing lint in same PR | Attempted to fix unrelated markdown violations | Scope creep, complex diff | Keep fix PR focused on intended changes only |
| Close "stale reference" without reading file | Assumed issue was stale based on title alone | Issue #4435 title said "stale" but phases.md was already correct | Always read the actual file first |

## Results & Parameters

### Session Results (2026-03-13, ProjectOdyssey)

| Metric | Value |
|--------|-------|
| Starting issue count | 363 |
| Round 1 closed (ADR-009 clusters) | 84 |
| Round 2 closed (other clusters) | 11 |
| Round 3 closed (subsets) | 28 |
| Round 4 closed (already-resolved) | 12 |
| Code fix PR (#4509) | 7 files, 5 issues |
| **Total closed** | **112** |
| Final count | ~250 |

### Canonical identification rule

```
canonical = min(issue_number for issue in cluster)
```

Oldest issue (lowest number) = canonical. This preserves original context/discussion.

### Comment templates

```
# Exact duplicate
"Duplicate of #CANONICAL — closing as part of bulk dedup"

# Subset issue
"Subset of #PARENT — this specific case is covered by the broader parent issue"

# Already resolved
"Already resolved — verified [what was checked]: [what was found]"
```

### Cluster detection prompt (for agent delegation)

```
Analyze these N open GitHub issues and identify ALL duplicate clusters
and subset relationships. For each cluster:
- Canonical: lowest issue number (keep open)
- Duplicates: list of issue numbers to close
- Subsets: issues that are narrower scope of a broader canonical

Output as bash script with gh issue close commands and appropriate comments.
Total count of issues to close: X
```
