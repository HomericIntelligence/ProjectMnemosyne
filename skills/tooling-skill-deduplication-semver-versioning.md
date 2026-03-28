---
name: tooling-skill-deduplication-semver-versioning
description: "Deduplicate overlapping skills by merging clusters into consolidated skills, and implement semantic versioning for skill amendments. Use when: (1) multiple skills cover the same topic with redundant content, (2) skill registry has 1000+ entries with obvious duplicates, (3) version bump rules need to distinguish major/minor/patch changes."
category: tooling
date: 2026-03-28
version: "1.5.0"
user-invocable: false
verification: verified-ci
history: tooling-skill-deduplication-semver-versioning.history
tags: [deduplication, merge, semver, versioning, skills-registry, consolidation]
---

# Skill Deduplication and Semantic Versioning

## Overview

| Field | Value |
|-------|-------|
| **Date** | 2026-03-28 |
| **Objective** | Merge duplicate skill clusters into consolidated skills, with semantic versioning for amendments |
| **Outcome** | Six rounds: 16 adr009-* merged to 3 (net -13); 10 mojo-test-* merged to 1 (net -9); 6 deprecated-file-cleanup-* merged to 1 (net -5); 9 conv2d-gradient-* merged to 3 (net -6); 12 adr009-test-splitting-* merged to 3 (net -9); 4 adr009-* merged to 1 with OBSOLETE notice (net -3). |
| **Verification** | verified-ci |
| **History** | [changelog](./tooling-skill-deduplication-semver-versioning.history) |

## When to Use

- Multiple skills share a common prefix (e.g., `adr009-*`, `pr-review-*`, `mojo-test-*`)
- `/advise` returns redundant or contradictory advice for the same topic
- Need to identify duplicate clusters in a large skills registry (1000+ skills)
- Updating `/learn` versioning rules to use semantic versioning
- A skill covers a topic that is now OBSOLETE and needs a prominent deprecation notice before all other content

## Verified Workflow

### Quick Reference

```bash
# Find duplicate clusters by 2-part prefix
ls skills/*.md | grep -v notes.md | grep -v history | sed 's|skills/||;s|\.md$||' | \
  awk -F'-' '{print $1"-"$2}' | sort | uniq -c | sort -rn | head -20

# List all skills in a cluster
ls skills/<prefix>*.md | grep -v notes.md | grep -v history

# Read descriptions to group by subtopic
for f in skills/<prefix>*.md; do
  echo "=== $(basename $f .md) ==="; head -5 "$f" | grep "^description:"; echo
done
```

### Detailed Steps

**Phase 1: Identify duplicate clusters**

1. List all skill names, extract 2-part prefixes, count occurrences
2. Focus on clusters with 3+ skills sharing a prefix
3. Read descriptions to sub-group within each cluster (e.g., adr009-* split into: test-splitting, CI-patterns, audit)

**Phase 2: Merge each sub-group**

For each sub-group of duplicates:

1. Read ALL source skills — extract unique content from each:
   - Failed Attempts rows (deduplicate by lesson, not exact text)
   - Verified Workflow steps (combine into comprehensive workflow)
   - When to Use triggers (union of all triggers)
   - Results & Parameters (merge all configs)
2. Write a single consolidated skill at `skills/<merged-name>.md`:
   - Use `version: "1.0.0"` (new consolidated skill, not an amendment)
   - Description covers ALL trigger conditions from all sources
   - All unique learnings preserved
3. Delete all superseded source `.md` and `.notes.md` files (remember to delete both)
4. No `.history` file needed — this is a new v1.0.0 skill, not an amendment
5. If another agent may have already deleted some files, skip them silently (`git rm` will error on missing files)

**Special case: OBSOLETE topics**

When the underlying topic is no longer applicable (e.g., a bug was fixed at the compiler level),
consolidate ALL related skills into a single historical reference with a prominent obsolescence
notice immediately after the Overview table:

```markdown
## <Topic> Status: OBSOLETE

> **<Topic> has been fixed.** <Brief explanation of why the workaround is no longer needed.>
>
> **Do NOT use this skill to implement <workaround> on new code.**
>
> For <the actual problem>, use **<preferred solution>** instead:
> - <Preferred solution detail 1>
> - <Preferred solution detail 2>
>
> This skill is preserved for historical reference and for understanding existing code
> that has not yet been updated.
```

Key difference from regular consolidation: even well-organized 3-file clusters warrant
further consolidation to 1 when a prominent OBSOLETE notice is the primary requirement,
because splitting the obsolescence notice across 3 files fragments the message.

**Phase 3: Validate**

```bash
python3 scripts/validate_plugins.py
```

**Phase 4: Use parallel agents for large merges**

For multiple clusters, launch parallel agents (one per group) in the same worktree. Each agent reads its group's skills and writes the merged output.

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
|---------|----------------|---------------|----------------|
| Parallel agents in same worktree | Launched 3 agents to merge 3 groups simultaneously in one worktree | Worked fine — no conflicts since each agent writes different files | Parallel agents in a shared worktree work when they touch non-overlapping files |
| Major-only version bumps | Always bump X.0.0 for any amendment | Loses information about change scale — a typo fix looks the same as a full rewrite | Use semver: Major for rewrites/merges, Minor for new findings, Patch for typos |
| Merging by exact text dedup | Tried deduplicating Failed Attempts by exact row match | Different skills describe the same lesson with different wording | Deduplicate by lesson/concept, not by exact text match |
| Splitting into multiple consolidated files | Planned 10 mojo-test-* files into 2-3 sub-groups | All 10 files covered the same core workflow with minor variations | When content is truly redundant, even large clusters (10 files) can consolidate to 1 |
| Forgetting .notes.md files | Deleted .md files but forgot accompanying .notes.md | Orphaned .notes.md files clutter the skills directory | Always delete both .md and .notes.md when removing source skills |
| Cross-category consolidation | Source skills had mismatched categories (e.g., one marked `documentation`, rest `tooling`) | Category was set per-skill rather than reflecting the actual content topic | When consolidating, pick the most accurate category for the merged skill's actual function, not just the majority |
| Over-splitting subtopics | Planned 9 conv2d skills into more than 3 groups | Content analysis showed clear 3-way split: finite-difference checks, depthwise-specific quirks, analytical-value tests | Group by actual usage scenario (how the tests are written), not by file naming pattern |
| Depthwise mixed with standard conv2d | Considered merging depthwise into the standard conv2d finite-differences skill | Depthwise has critical API differences (kernel shape, field names, tolerance API) that warrant a dedicated skill | Even when topics are adjacent, separate skills when the API contract differs significantly |
| Assuming one-time merges are durable | Merged adr009-* cluster in Round 1 (16->3), assumed stable | /learn calls after the merge created 9 new duplicate skills covering the same adr009 split topic | Deduplication is not permanent; re-duplication occurs organically — schedule periodic re-consolidation passes |
| Stopping at 3 when topic is OBSOLETE | Round 5 consolidated 12 adr009 skills to 3 sub-skills | When the underlying topic (ADR-009 workaround) was declared OBSOLETE, the 3-file structure fragmented the OBSOLETE notice | When a topic is OBSOLETE, consolidate further to 1 file — the obsolescence notice is the dominant content |

## Results & Parameters

### Deduplication Results

**Round 1: ADR-009 cluster (2026-03-25)**

```yaml
skills_before: 16
skills_after: 3
net_reduction: 13 skills (-81%)
lines_before: 3279
lines_after: 864
unique_lessons_preserved: 35 Failed Attempts rows
```

**Round 2: Mojo test splitting cluster (2026-03-27)**

```yaml
skills_before: 10
skills_after: 1
net_reduction: 9 skills (-90%)
lines_deleted: 2499
lines_added: 250
unique_lessons_preserved: 12 Failed Attempts rows, 17 Verified On entries
files_deleted: 20 (10 .md + 10 .notes.md)
```

**Round 3: Deprecated file cleanup cluster (2026-03-28)**

```yaml
skills_before: 6
skills_after: 1
net_reduction: 5 skills (-83%)
files_deleted: 12 (6 .md + 6 .notes.md)
unique_lessons_preserved: 8 Failed Attempts rows
consolidated_into: deprecated-file-stub-cleanup
```

**Round 5: ADR-009 test splitting second pass (2026-03-28)**

```yaml
skills_before: 12
skills_after: 3
net_reduction: 9 skills (-75%)
files_deleted: 19 (12 .md + 5 .notes.md + 1 .history + 1 extra notes)
lines_deleted: 2745
lines_added: 553
split_into:
  - adr009-test-file-split-workflow (ci-cd): how to split — full CI pattern fork, import audit, compile hang variant
  - adr009-split-audit-recovery (testing): codebase audit, batch issue creation, dropped-test recovery
  - adr009-desplit-merge-workflow (testing): reversing splits; CRITICAL dedup bug where struct defs get "<top-level>" name
key_insight: prior round merged these to 3, but subsequent /learn calls recreated 9 more duplicates — re-consolidation needed
```

**Round 6: ADR-009 OBSOLETE consolidation (2026-03-28)**

```yaml
skills_before: 4
skills_after: 1
net_reduction: 3 skills (-75%)
files_deleted: 3 (adr009-split-audit-recovery.md, adr009-desplit-merge-workflow.md, adr009-ci-pattern-updates.md)
motivation: ADR-009 was fixed at compiler level; needed single skill with prominent OBSOLETE notice
key_insight: when a topic is OBSOLETE, consolidate to 1 even if subtopics were well-organized into 3
obsolete_notice_position: immediately after Overview table (before "When to Use")
```

**Round 4: Conv2D gradient testing cluster (2026-03-28)**

```yaml
skills_before: 9
skills_after: 3
net_reduction: 6 skills (-67%)
files_deleted: 18 (9 .md + 9 .notes.md)
lines_deleted: 2136
lines_added: 712
split_into:
  - conv2d-gradient-checking-finite-differences (standard conv2d: padding, stride, multi-channel)
  - depthwise-conv2d-gradient-checking-tests (depthwise-specific API quirks)
  - conv2d-backward-analytical-value-tests (exact expected values, batch accumulation, border pixel formula)
key_insight: topic-adjacent skills with different APIs warrant separate skills even in same domain
```

### Semver Rules for /learn

| Change Type | Bump | When |
|-------------|------|------|
| Major (X.0.0) | `1.0.0` → `2.0.0` | Merge skills, rewrite workflow, change core recommendation |
| Minor (0.X.0) | `1.0.0` → `1.1.0` | Add findings, failed attempts, extend workflow |
| Patch (0.0.X) | `1.0.0` → `1.0.1` | Fix typos, formatting, metadata |

### Top Duplicate Clusters Remaining (for future merges)

```
9  pr-review-*
7  skill-fix-*
7  pre-commit-*
7  mojo-hash-*
7  mojo-extensor-*
7  github-actions-*
7  git-worktree-*
5  mojo-jit-*
5  mass-pr-*
5  batch-pr-*
```

Note: `mojo-test-*` cluster (was 8) resolved in PR #1075 (10->1). `deprecated-file-*` cluster (was 6) resolved in PR #1077 (6->1). `conv2d-gradient-*` cluster (was 9) resolved in PR #1080 (9->3). ADR-009 second pass (12 re-duplicated) resolved in PR #1086 (12->3). ADR-009 OBSOLETE pass resolved in PR #1097 (4->1).

## Verified On

| Project | Context | Details |
|---------|---------|---------|
| ProjectMnemosyne | PR #1040, merged 16 adr009 skills + added semver | 2026-03-25 session |
| ProjectMnemosyne | PR #1075, merged 10 mojo-test-* skills into 1 | 2026-03-27 session |
| ProjectMnemosyne | PR #1077, merged 6 deprecated-file-cleanup-* skills into 1 | 2026-03-28 session |
| ProjectMnemosyne | PR #1080, merged 9 conv2d-gradient-* skills into 3 | 2026-03-28 session |
| ProjectMnemosyne | PR #1086, re-consolidated 12 adr009-test-splitting-* skills into 3 (cluster re-duplicated after prior merge) | 2026-03-28 session |
| ProjectMnemosyne | PR #1097, consolidated 4 adr009-* skills to 1 with prominent OBSOLETE notice (ADR-009 fixed at compiler level) | 2026-03-28 session |
