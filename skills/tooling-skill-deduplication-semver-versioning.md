---
name: tooling-skill-deduplication-semver-versioning
description: "Deduplicate overlapping skills by merging clusters into consolidated skills, and implement semantic versioning for skill amendments. Use when: (1) multiple skills cover the same topic with redundant content, (2) skill registry has 1000+ entries with obvious duplicates, (3) version bump rules need to distinguish major/minor/patch changes."
category: tooling
date: 2026-03-28
version: "1.3.0"
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
| **Outcome** | Four rounds: 16 adr009-* merged to 3 (net -13); 10 mojo-test-* merged to 1 (net -9); 6 deprecated-file-cleanup-* merged to 1 (net -5); 18 CI-failure-triage-* merged to 3 (net -15). Semver rules added. |
| **Verification** | verified-ci |
| **History** | [changelog](./tooling-skill-deduplication-semver-versioning.history) |

## When to Use

- Multiple skills share a common prefix (e.g., `adr009-*`, `pr-review-*`, `mojo-test-*`)
- `/advise` returns redundant or contradictory advice for the same topic
- Need to identify duplicate clusters in a large skills registry (1000+ skills)
- Updating `/learn` versioning rules to use semantic versioning

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

**Round 4: CI failure triage cluster (2026-03-28)**

```yaml
skills_before: 18
skills_after: 3
net_reduction: 15 skills (-83%)
files_deleted: 35 (18 .md + 17 .notes.md)
lines_deleted: 4303
lines_added: 1034
unique_lessons_preserved: 25+ Failed Attempts rows across 3 skills
consolidated_into:
  - ci-cd-failure-diagnosis-log-analysis (7 sources)
  - ci-cd-failure-fix-patterns (6 sources)
  - ci-cd-preexisting-failure-triage (5 sources)
split_strategy: by_topic_not_prefix (3 distinct topics within ci-* prefix)
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

Note: `mojo-test-*` cluster (was 8) resolved in PR #1075 (10->1). `deprecated-file-*` cluster (was 6) resolved in PR #1077 (6->1). CI failure triage cluster (was 18+) resolved in PR #1085 (18->3).

## Verified On

| Project | Context | Details |
|---------|---------|---------|
| ProjectMnemosyne | PR #1040, merged 16 adr009 skills + added semver | 2026-03-25 session |
| ProjectMnemosyne | PR #1075, merged 10 mojo-test-* skills into 1 | 2026-03-27 session |
| ProjectMnemosyne | PR #1077, merged 6 deprecated-file-cleanup-* skills into 1 | 2026-03-28 session |
| ProjectMnemosyne | PR #1085, merged 18 CI-failure-triage-* skills into 3 | 2026-03-28 session |
