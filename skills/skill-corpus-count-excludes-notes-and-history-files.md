---
name: skill-corpus-count-excludes-notes-and-history-files
description: "Use when: (1) counting the number of skills in the marketplace corpus, (2) auditing per-category skill counts, (3) any script or agent step that measures corpus size with ls/find/git ls-tree on the skills/ directory. Naive *.md globs silently include .notes.md companion files and inflate counts by ~57%."
category: tooling
date: 2026-05-19
version: "1.0.0"
user-invocable: false
verification: verified-local
tags: ["skill-corpus", "marketplace", "counting"]
---

# Skill Corpus Count Excludes Notes and History Files

## Overview

| Field | Value |
| ------- | ------- |
| **Date** | 2026-05-19 |
| **Objective** | Count the real number of skills in `skills/` without inflating by `.notes.md` or `.history` companion files |
| **Outcome** | Successful — canonical one-liner identified and verified against ground-truth corpus of 693 skills |

## When to Use

Apply this skill whenever you need an accurate count of skills in the marketplace:

- Before and after consolidation sessions to verify corpus size changed as expected
- In orchestrator scripts that compute per-category breakdowns
- In CI validation steps that check corpus size thresholds
- When an agent reports a suspiciously large corpus count (naive glob inflates by ~57%)
- When writing or reviewing any script that enumerates `skills/*.md`

## Verified Workflow

### Quick Reference

```bash
# Canonical: count only real skill files, not companion files
ls skills/*.md | grep -v "\.notes\.md$" | wc -l

# Alternative using find (safer with spaces in filenames)
find skills/ -maxdepth 1 -name "*.md" ! -name "*.notes.md" | wc -l

# Alternative using git (counts only committed files)
git ls-tree -r HEAD -- skills/ | awk '{print $NF}' | grep "\.md$" | grep -v "\.notes\.md$" | wc -l

# Per-category count (must also exclude .notes.md)
grep -h "^category:" skills/*.md | grep -v "\.notes\.md" | sort | uniq -c | sort -rn
# Correct form — exclude .notes.md files before grepping:
for f in skills/*.md; do [[ "$f" == *.notes.md ]] && continue; grep "^category:" "$f"; done | sort | uniq -c | sort -rn
```

### Detailed Steps

1. Understand the three file types that coexist in `skills/`:
   - `<name>.md` — the actual skill document (counts toward corpus size)
   - `<name>.notes.md` — raw session notes companion file (does NOT count)
   - `<name>.history` — changelog snapshot (does NOT count)

2. Always add `grep -v "\.notes\.md$"` (or `! -name "*.notes.md"` with `find`) to any enumeration of `skills/*.md`.

3. When doing per-category audits, filter out `.notes.md` files before piping to `grep "^category:"` — `.notes.md` files inherit a `category:` frontmatter line from their sibling and will double-count every skill.

4. If using `git ls-tree`, apply the same `grep -v "\.notes\.md$"` filter after selecting `.md` files.

5. Cross-check: `ls skills/*.notes.md | wc -l` should equal roughly half of `ls skills/*.md | wc -l` (every skill may have a companion); `ls skills/*.history | wc -l` is typically smaller.

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
| --------- | ---------------- | --------------- | ---------------- |
| 1 | `ls skills/*.md \| wc -l` | Returned 1,089 — silently included all `.notes.md` companion files; inflated by ~57% | Always exclude `.notes.md` (and `.history`) with `grep -v "\.notes\.md$"` |
| 2 | `find skills/ -name "*.md" \| wc -l` | Same problem — `*.md` glob matches `.notes.md` too | The `.notes.md` extension is a double-extension; standard `*.md` globs catch it |
| 3 | `git ls-tree -r HEAD -- skills/ \| grep "\.md$"` | Still includes `.notes.md` because they end in `.md` | Tree-level enumeration has the same trap |
| 4 | Per-category audit via `grep -h "^category:" skills/*.md` | Inflated category counts by ~57% — every `.notes.md` inherits its sibling's frontmatter category | Per-category counts must also exclude `.notes.md` |

## Results & Parameters

### Configuration

No configuration required — this is a one-liner shell pattern.

```bash
# Correct corpus count
CORPUS_SIZE=$(ls skills/*.md | grep -v "\.notes\.md$" | wc -l)
echo "Real skill count: $CORPUS_SIZE"

# Breakdown by category (correct)
for f in skills/*.md; do
  [[ "$f" == *.notes.md ]] && continue
  grep "^category:" "$f"
done | sort | uniq -c | sort -rn
```

### Expected Output

- `CORPUS_SIZE` reflects only actual skill files
- The `grep -v "\.notes\.md$"` filter removes approximately one companion file per skill
- Naive `ls skills/*.md | wc -l` will be approximately 1.57x the real count when every skill has a `.notes.md` companion
- A mismatch between naive count and filtered count is a reliable signal that `.notes.md` files are present

## Verified On

| Project | Context | Details |
| --------- | --------- | --------- |
| Mnemosyne | 2026-05-19 second-pass consolidation session (epic #1823) | Real corpus = 693 skills vs naive count of 1,089; .notes.md = 396, .history = 96 |

## References

- [Epic #1823 — second-pass consolidation](https://github.com/HomericIntelligence/Mnemosyne/issues/1823)
- [CLAUDE.md — Plugin Standards](../CLAUDE.md)
