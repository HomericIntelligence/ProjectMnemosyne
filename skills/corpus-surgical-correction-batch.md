---
name: corpus-surgical-correction-batch
description: "Surgical batch correction of a large research document corpus (50+ files) after a review pass. Use when: (1) a review process has identified specific errors across many documents that share a common root cause, (2) you need corrections to be traceable (auditable inline markers), (3) stripping correction-narrative text from a document corpus after corrections have been accepted and made permanent, (4) you want to preserve all surrounding text and structure, (5) corrections span multiple independent document groups that can be parallelized."
category: architecture
date: 2026-04-14
version: "1.1.0"
user-invocable: false
verification: verified-local
history: corpus-surgical-correction-batch.history
tags: [latex, narrative-removal, corpus-edit]
---

# Corpus Surgical Correction: Batch Parallel Pattern

## Overview

| Field | Value |
| ------- | ------- |
| **Date** | 2026-04-13 |
| **Objective** | Apply corrections identified by a review pass to 62 research/summary documents and 4 synthesis documents — without rewriting sections or losing provenance |
| **Outcome** | All 66 files corrected across 8 parallel batches; every change marked with `[corrected: ...]` inline notes |
| **Verification** | verified-local |
| **History** | [changelog](./corpus-surgical-correction-batch.history) |

## When to Use

- Post-review correction pass on 20+ documents
- Multiple documents share the same root-cause error (e.g., wrong constant propagated from a shared context)
- You need corrections to be auditable (reviewable by humans without re-reading the full doc)
- Document groups are independent and can be processed in parallel
- You want to preserve original structure, prior art classifications, and verdict text
- Stripping correction-narrative text (e.g., `[corrected: ...]` markers, 'Threats to Validity' sections, 'not X as stated' inline fragments, `.bak` references) from a corpus AFTER corrections have been permanently accepted — the narrative is a legacy artifact, not a live threat

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

### Optional Phase: Post-Correction Narrative Removal

Use this phase when correction markers and error-narrative text has been permanently accepted and should be stripped from the final output (e.g., before publishing a paper or freezing a corpus).

#### Quick Reference

```python
import re, pathlib

# Pass 1: Remove [corrected: ...] markers (possibly multiline)
corrected_marker_re = re.compile(r'\[corrected[^\]]*\]', re.IGNORECASE | re.DOTALL)

# Pass 2: Remove inline error-reference fragments
inline_fragments = [
    r'\(not ~?\d+\s*GB as stated[^)]*\)',
    r'\(prior prelude[^)]*\)',
    r'as stated in the prior prelude[^.]*\.',
    r'The prelude erroneously[^.]*\.',
    r'\(erroneously[^)]*\)',
]

# Pass 3: Remove whole sections/paragraphs
section_patterns = [
    r'\\section\{Threats to Validity\}.*?(?=\\section|\Z)',
    r'\\subsection\{Known Prelude Errors\}.*?(?=\\subsection|\\section|\Z)',
]
```

#### Detailed Steps

1. **Classify narrative text** before writing any regex:
   - Inline markers: `[corrected: ...]`, `(not X as stated)`, `(prior prelude had X)`
   - Section-level narrative: `\section{Threats to Validity}`, `\subsection{Known Prelude Errors}`
   - Reference fragments: `.bak` file paths, "six factual errors" counts

2. **Apply passes sequentially** — broadest (section removal) last:
   a. Pass 1: Remove inline `[corrected: ...]` markers with DOTALL regex (they can span lines)
   b. Pass 2: Remove specific inline fragment patterns (each pattern must be verified to be unique enough not to match live content)
   c. Pass 3: Remove whole section blocks (regex must anchor to the next `\section` or end-of-file)

3. **After each pass, rebuild LaTeX** (`pdflatex + bibtex + pdflatex×2`) and inspect the log:
   - `grep "^!" paper.log` → must be 0 errors
   - `grep "Undefined control sequence" paper.log` — regex may have left orphan LaTeX fragments (e.g., `\5`, `\59`) from mid-sentence removal

4. **Diagnose orphan fragments** by grepping the `.tex` for the literal text around the error line number:
   - Common cause: regex deleted text that was *inside* an `\href{}{}` argument, leaving a syntactically broken sequence
   - Fix: rewrite the surrounding sentence completely rather than just removing the fragment

5. **Diagnose table column count drift**: if narrative was in a `tabular` cell and was removed entirely, the table may now have fewer cells than its column spec. Fix by rewriting the full table row.

6. **Verify clean**: `grep -rn "\[corrected" .` and `grep -rn "Threats to Validity" .` → both return empty after all passes complete.

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
| --------- | ---------------- | --------------- | ---------------- |
| Single agent for all 62 files | Tried one agent to fix everything | Context exhaustion; agent loses track of which corrections it has applied | Partition into groups of 5–8 files per agent |
| Silent corrections without markers | Applied corrections without `[corrected: ...]` notes | Changes become invisible in the document; humans can't audit what changed without diffing | Always add inline `[corrected: ...]` markers — even for "obvious" fixes |
| Rewriting whole sections | Replaced entire paragraphs to fix one number | Lost surrounding context and nuance; introduced new errors | Surgical edits only: change the minimum needed, preserve everything else |
| Mixing research and synthesis doc corrections | One agent correcting both research docs and synthesis docs | Agent tried to apply research-file corrections to synthesis docs and vice versa; file naming conventions differ | Dedicated separate agent for synthesis docs; they have different structure and different error sets |
| Agent correcting review files | Agent "fixed" errors it found in review_*.md | Destroyed the audit trail (review files are ground truth) | Explicitly state in every prompt which files are read-only |
| Single regex pass for all inline fragments | One big alternation `(pattern_A\|pattern_B\|...)` applied once | Different phrasing of the same error narrative required different patterns; a single pass missed variants that used different sentence structure | Run separate targeted passes per phrasing variant; verify with `grep` after each pass |
| Removing mid-sentence fragment without checking context | Stripped `(not ~68 GB as stated)` from inside a sentence | Left orphan `\5` (LaTeX undefined control sequence) because the fragment was mid-sentence inside an `\href{}` arg | After each regex removal, rebuild LaTeX immediately and inspect log before proceeding |
| Regex removal inside tabular cell | Removed entire cell content that contained correction narrative | Left row with fewer cells than column spec; caused "Missing \item" or tabular alignment error | After removing content from table cells, count columns against the `{ll...}` spec and add empty cells if needed |
| Grepping for exact phrase | Used `grep "not ~68 GB as stated"` to verify removal | Phrase had slight variants in different sections (e.g., "not 68 GB" vs "not ~68 GB") | Always use flexible patterns with `grep -E` and check the count drops to 0 for all variants |

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
| ------------ | ---------------- | ----------------- |
| KV cache ~68 GB → ~8.59 GB for A2 at 32K | 23/62 research+summary | All 7 research batches |
| Vocab 151,936 → 248,320 for A1/B | 12/62 | Most batches |
| Context 32,768 → 262,144 for A1/B | 15/62 | Most batches |
| Idea-specific arithmetic errors | 8/62 | Targeted |
| Synthesis doc corrections | 4/4 synthesis | 1 dedicated batch |

### Post-Correction Narrative Removal Notes (2026-04-14)

Applied to: `/home/mvillmow/Random/ArchIdeas/research/report/paper.tex` (3,320 lines, 102 pages)

Passes required: 3 (inline markers → inline fragments → section block)
LaTeX rebuilds required: 3 (one after each pass, plus 1 extra to fix orphan `\5` sequence)
Final state: 0 errors, 0 unresolved references, 102 pages

Patterns that required special care:
- `[corrected: ...]` markers: used `re.DOTALL` because some spanned 3+ lines
- `\section{Threats to Validity}` block: must use `re.DOTALL` + lookahead for next `\section`
- Inline `\href` argument removal: verify the enclosing sentence remains syntactically valid after removal

## Verified On

| Project | Context | Details |
| --------- | --------- | --------- |
| ArchIdeas | 31 AI architecture ideas post-review correction | 62 research/summary docs + 4 synthesis docs; 8 parallel correction batches |
