---
name: corpus-surgical-correction-batch
description: "Surgical batch correction of a large research document corpus (50+ files) after a review pass. Use when: (1) a review process has identified specific errors across many documents that share a common root cause, (2) you need corrections to be traceable (auditable inline markers), (3) you want to preserve all surrounding text and structure, (4) corrections span multiple independent document groups that can be parallelized."
category: architecture
date: 2026-04-13
version: "1.0.0"
user-invocable: false
verification: verified-local
tags: []
---

# Corpus Surgical Correction: Batch Parallel Pattern

## Overview

| Field | Value |
|-------|-------|
| **Date** | 2026-04-13 |
| **Objective** | Apply corrections identified by a review pass to 62 research/summary documents and 4 synthesis documents — without rewriting sections or losing provenance |
| **Outcome** | All 66 files corrected across 8 parallel batches; every change marked with `[corrected: ...]` inline notes |
| **Verification** | verified-local |

## When to Use

- Post-review correction pass on 20+ documents
- Multiple documents share the same root-cause error (e.g., wrong constant propagated from a shared context)
- You need corrections to be auditable (reviewable by humans without re-reading the full doc)
- Document groups are independent and can be processed in parallel
- You want to preserve original structure, prior art classifications, and verdict text

## Verified Workflow

### Quick Reference

```
1. Categorize errors:
   a. Systemic (same correction in every file)  → inject into every agent prompt
   b. File-specific (unique corrections)        → route to the appropriate batch agent

2. Partition documents into groups of 5–8 files each

3. Launch all batch agents in parallel (one Agent tool call per group)

4. Each agent:
   a. Reads the review file(s) for its assigned ideas
   b. Makes in-place edits (Edit tool, precise old_string→new_string)
   c. Adds [corrected: ...] notes inline — never silent edits
   d. Verifies it did not touch review_*.md or verification_*.md

5. Wait for all batch completion notifications
```

### Detailed Steps

1. **Classify errors by scope** before writing any agent prompt:
   - **Universal systemic errors**: same wrong value appears in every file (e.g., KV cache formula error, wrong vocab size). List these explicitly in every batch agent prompt.
   - **Idea-specific errors**: found only in a specific file (e.g., arithmetic error in a specific worked example). Route to the batch that owns that file.
   - **Synthesis doc errors**: errors in the summary/priority/spec documents that need separate treatment (don't mix with research/summary corrections).

2. **Write batch agent prompts** with:
   - Canonical correct values for all systemic errors at the top (so agent doesn't need to look them up)
   - For each file: the specific errors to fix, with the wrong value and correct value stated explicitly
   - Clear rule: only modify `research_*.md` and `summary_*.md`, never `review_*.md` or `verification_*.md`
   - Instruction to add `[corrected: ...]` notes inline for every change

3. **Inline correction marker format**:
   ```
   ~8.59 GB [corrected from ~68 GB: used KV head count=8, not query head count=64; formula: 64L × 2 × 8KV × 128hd × 32768tok × 2B = 8.59 GB]
   ```
   This preserves: original value, corrected value, derivation, reason.

4. **Read-only files**: Always tell agents which files are ground truth and must not be modified:
   - `review_*.md` — the review documents are the source of truth for corrections
   - `verification_*.md` — the sub-agent verification reports
   - Never modify these even if they contain errors; they are the audit trail

5. **Synthesis docs are a separate batch**: Create one dedicated agent for the synthesis documents. It reads the synthesis validation report first, then applies corrections. Never mix with research/summary corrections.

6. **Verify completion**: After all batches complete, spot-check 2–3 corrections per batch by reading the affected file sections.

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
|---------|----------------|---------------|----------------|
| Single agent for all 62 files | Tried one agent to fix everything | Context exhaustion; agent loses track of which corrections it has applied | Partition into groups of 5–8 files per agent |
| Silent corrections without markers | Applied corrections without `[corrected: ...]` notes | Changes become invisible in the document; humans can't audit what changed without diffing | Always add inline `[corrected: ...]` markers — even for "obvious" fixes |
| Rewriting whole sections | Replaced entire paragraphs to fix one number | Lost surrounding context and nuance; introduced new errors | Surgical edits only: change the minimum needed, preserve everything else |
| Mixing research and synthesis doc corrections | One agent correcting both research docs and synthesis docs | Agent tried to apply research-file corrections to synthesis docs and vice versa; file naming conventions differ | Dedicated separate agent for synthesis docs; they have different structure and different error sets |
| Agent correcting review files | Agent "fixed" errors it found in review_*.md | Destroyed the audit trail (review files are ground truth) | Explicitly state in every prompt which files are read-only |

## Results & Parameters

### Agent Prompt Template for a Correction Batch

```markdown
You are correcting errors in AI architecture research documents at [DIR].
You will fix ONLY the specific errors identified by the review process.
Do NOT rewrite sections wholesale — make surgical corrections.

## Canonical Correct Values (use these everywhere)
[List all systemic correct values with formulas]

## Files to Fix

### [IDEA_ID] — [file1].md + [file2].md
Per review_[id].md:
- Error 1: "[old value]" → "[correct value]" with "[explanation]"
- Error 2: ...

## Rules
- Edit files in-place using precise string replacements
- Preserve all surrounding text, formatting, and structure
- Add "[corrected: ...]" notes inline so changes are traceable
- Do NOT change prior art classifications, verdict text, or section structure
- Only modify [research|summary]_*.md files
- Do not touch review_*.md or verification_*.md
```

### Correction Rate Statistics (31 research docs + 31 summary docs + 4 synthesis docs)

| Error Type | Files Affected | Batches Required |
|------------|----------------|-----------------|
| KV cache ~68 GB → ~8.59 GB for A2 at 32K | 23/62 research+summary | All 7 research batches |
| Vocab 151,936 → 248,320 for A1/B | 12/62 | Most batches |
| Context 32,768 → 262,144 for A1/B | 15/62 | Most batches |
| Idea-specific arithmetic errors | 8/62 | Targeted |
| Synthesis doc corrections | 4/4 synthesis | 1 dedicated batch |

## Verified On

| Project | Context | Details |
|---------|---------|---------|
| ArchIdeas | 31 AI architecture ideas post-review correction | 62 research/summary docs + 4 synthesis docs; 8 parallel correction batches |
