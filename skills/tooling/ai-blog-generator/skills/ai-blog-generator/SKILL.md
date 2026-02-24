---
name: ai-blog-generator
description: "Generate AI-authored blog posts from git commit history to fill documentation gaps"
category: tooling
date: 2025-12-30
---

# AI Blog Generator

Generate blog posts retroactively based on git commit history, with proper AI-generation attribution.

## Overview

| Date | Objective | Outcome |
|------|-----------|---------|
| 2025-12-30 | Fill 29 missing blog posts from git history | 50 sequential posts (Day One - Day Fifty) |

## When to Use

- Filling gaps in project blog/changelog history
- Documenting past work retroactively from git commits
- Creating development blogs for dates without posts
- Generating consistent, templated posts from commit data
- Backfilling documentation after a period of undocumented work

## Verified Workflow

### Phase 1: Analysis

1. **List existing blog posts**: `ls notes/blog/*.md`
2. **Get git history for date range**:

   ```bash
   git log --oneline --since="2025-11-01" --until="2025-12-31" --format="%ad %s" --date=short
   ```

3. **Identify gaps**: Cross-reference dates with commits vs dates with posts
4. **Create mapping**: `[date] -> [commits] -> [blog title]`

### Phase 2: Template

Use this exact template for AI-generated posts:

```markdown
# Day [Number]: [Title]

**Project:** [Project Name]
**Date:** [Full Date]
**Branch:** `main`
**Tags:** #tag1 #tag2 #tag3

---

> **Note:** This blog post was AI-generated based on git commit history.
> Content reflects actual work done but was not written in real-time.

---

## TL;DR

[2-3 sentence summary of the day's work]

**Key insight:** [One-liner takeaway]

---

## [Main Content Sections]

[Content based on commits]

---

## What's Next

### Immediate Priorities

1. [Next task]
2. [Following task]

---

## Reflections

1. [Learning or insight]
2. [Challenge faced]

---

**Status:** [Summary]
**Next:** [Next steps]

### Stats

- **Commits:** [N]
- **Key changes:** [List]

---

*This post was reconstructed from git history by AI on [Current Date].*
```

### Phase 3: Commit with Backdated Timestamps

Use both `GIT_AUTHOR_DATE` and `GIT_COMMITTER_DATE` to preserve authentic timeline:

```bash
git add notes/blog/MM-DD-YYYY.md && \
GIT_AUTHOR_DATE="YYYY-MM-DDT23:00:00" \
GIT_COMMITTER_DATE="YYYY-MM-DDT23:00:00" \
git commit -m "docs(blog): add Day N - Title (AI-generated)

AI-generated blog post based on git commit history for YYYY-MM-DD.
Covers: [brief themes]

Co-Authored-By: Claude <noreply@anthropic.com>"
```

### Phase 4: Sequential Numbering

After generating all posts, verify sequential day numbering:

```python
# Sort all posts chronologically and renumber
files_sorted = sorted(files, key=parse_date)
for i, f in enumerate(files_sorted, 1):
    # Update "# Day X:" to "# Day {num_words[i]}:"
```

### Phase 5: PR Creation

1. Run pre-commit: `just pre-commit-all`
2. Push branch: `git push -u origin blog/fill-missing-posts`
3. Create PR: `gh pr create --title "docs(blog): Add N missing posts"`
4. Enable auto-merge: `gh pr merge --auto --rebase`

## Results

### Parameters Used

| Parameter | Value |
|-----------|-------|
| Date range | Nov 7 - Dec 29, 2025 |
| Posts generated | 29 |
| Total posts | 50 |
| Commit time | 23:00:00 (end of day) |
| AI notices | Top AND bottom |

### Output

- 29 blog posts created
- All posts pass markdown linting
- Sequential numbering: Day One through Day Fifty
- Authentic git timeline preserved via backdated commits

## Failed Attempts

| Attempt | Why Failed | Lesson |
|---------|------------|--------|
| Assigned day numbers without checking existing posts | Created 9+ duplicate day numbers (Day Twelve appeared twice, etc.) | Always analyze ALL existing posts before assigning numbers |
| Used bash for-loop with complex variable substitution | Syntax errors with subshells and pipes | Use Python scripts for complex date/file manipulation |
| Original PR merged before fixing numbering | Auto-merge completed during fix | Review PR thoroughly before enabling auto-merge |
| Git log date filtering with `--since="DATE 00:00"` | Returned inconsistent results | Use `--since="YYYY-MM-DD" --until="YYYY-MM-DD"` format |

## Error Handling

| Problem | Solution |
|---------|----------|
| Duplicate day numbers | Renumber ALL posts chronologically after generation |
| Markdown lint failures | Run `just pre-commit-all` before committing |
| Missing AI attribution | Include notice at BOTH top and bottom of posts |
| Non-chronological order | Sort by parsed date (year, month, day) not filename |

## Key Learnings

1. **Always analyze first**: Check all existing posts before generating new ones
2. **Sequential numbering is global**: Day numbers must be unique across ALL posts
3. **Backdating requires both dates**: Set both `GIT_AUTHOR_DATE` and `GIT_COMMITTER_DATE`
4. **AI attribution twice**: Put notice at top (visible immediately) AND bottom (footer)
5. **Use Python for complexity**: Bash subshells are error-prone for date manipulation

## References

- Source PR: [PR #3003](https://github.com/mvillmow/ProjectOdyssey/pull/3003)
- Fix PR: [PR #3004](https://github.com/mvillmow/ProjectOdyssey/pull/3004)
- Blog location: `notes/blog/MM-DD-YYYY.md`
- Related skill: `doc-update-blog` for manual blog updates
