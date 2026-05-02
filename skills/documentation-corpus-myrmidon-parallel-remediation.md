---
name: documentation-corpus-myrmidon-parallel-remediation
description: "Myrmidon swarm pattern for remediating a large document corpus in parallel using isolated git worktree agents. Use when: (1) an unpublished research corpus contains change-note prose, correction-history blocks, or backward-compatibility text that must be deleted (not annotated), (2) defects span many files and must be fixed in parallel without file ownership collisions, (3) you need wave-based execution: parallel fixers → read-only verifier → merge. Includes citation-verification pass that web-fetches arXiv abstracts to catch fabricated numeric ranges, reversed-polarity claims, and paper-body figures misattributed as abstract-level."
category: documentation
date: 2026-04-20
version: "1.6.0"
user-invocable: false
verification: verified-local
history: documentation-corpus-myrmidon-parallel-remediation.history
tags: [myrmidon, swarm, parallel, corpus, remediation, worktree, wave-based, change-notes, unpublished, conflict-partitioning, citation-verification, arxiv-abstract-check]
---

# Documentation Corpus: Myrmidon Parallel Remediation

## Overview

| Field | Value |
| ------- | ------- |
| **Date** | 2026-04-18 |
| **Objective** | Remediate a large unpublished research corpus by running parallel worktree fixer agents that delete change-note prose, correct arithmetic errors, and normalize terminology — without file ownership collisions |
| **Outcome** | Successful — pre-flight conflict partitioning eliminated all merge conflicts; "no change-logging" constraint in fixer prompts prevented meta-commentary residue; Wave B verifier confirmed zero residual matches |
| **Verification** | verified-local (workflow executed end-to-end; agents ran, committed successfully; no external CI) |

## When to Use

- Research corpus is **unpublished** and contains change-note / correction-history / backward-compatibility prose that must be deleted (not annotated or moved to changelogs)
- Defects span 20+ files and multiple repair classes (arithmetic, terminology, structure, citations)
- File-level collision risk is high because some files appear in multiple repair classes (WATCH files)
- You want parallel execution (Wave A) followed by a read-only audit (Wave B) before merging
- Prior session used `[corrected: ...]` inline markers and those markers now need stripping

## Verified Workflow

### Quick Reference

```bash
# Step 1: Pre-flight — enumerate all defects
grep -rn "Critical correction|corrected from|previously stated|earlier draft|updated after review|flagged in review|per audit|Changelog|Revision history|Change notes|was missing|now reflects|this replaces|originally claimed|In the original version|for backward compat|legacy (docs|behavior|wording)|Critical corrections applied|CERTAIN \(in legacy|CERTAIN \(in original|CERTAIN \(if uncorrected|CORRECTED:|corrected\)|Year corrected|previously missing.*added|not.*as previously stated" research/*.md

# Step 2: Identify WATCH files (appear in 2+ repair classes)
# Step 3: Assign WATCH files to their primary repair-class agents
#          Assign GO files (appear in only 1 class) to that class or a scrub agent
# Step 4: Launch Wave A — 6 parallel fixer agents (worktree, general-purpose)
# Step 5: Wave B — 1 verifier (Explore, read-only, re-runs audit rubric + residual grep)
# Step 6: Wave C — merge confirmed worktree diffs to main checkout
```

### Detailed Steps

#### Phase 0: Pre-Flight Audit-Grep (main context, read-only)

Run the full defect-enumeration grep across the corpus before launching any fixer. Record:
- Which files matched
- Which repair class owns each match (see Repair Class taxonomy below)
- Which files matched in 2+ classes (**WATCH files**)

Do **not** start editing until the full match set is known.

#### Phase 1: Conflict Partitioning

Classify every file as WATCH or GO:

- **WATCH file**: appears in 2+ repair class match sets. Assign to exactly one agent — the agent whose repair class has the most matches in that file (or the most critical match). That agent also folds corpus-wide scrub patterns into its pass.
- **GO file**: appears in exactly 1 repair class match set. Assign to that class's agent.

**Result**: every file is owned by exactly one agent. Zero collision risk regardless of parallel execution order.

#### Phase 2: Wave A — Parallel Fixer Agents

Launch 6 fixer agents simultaneously in a single message (one `Agent` tool call each):

| Agent | Repair Class | Files |
| ------- | ------------- | ------- |
| R1 | Arithmetic / numeric corrections | GO arithmetic files + WATCH files assigned here |
| R2 | Terminology normalization | GO terminology files + WATCH files assigned here |
| R3 | Structural insertions (missing sections) | GO structure files |
| R4 | Citation format / locator additions | GO citation files |
| R5 | Inline correction-marker stripping | GO marker files |
| R6 | Corpus-wide scrub (change-note prose) | All remaining GO files not assigned above |

**Agent configuration**: `isolation: "worktree"`, `subagent_type: general-purpose`

**Required constraints in every fixer agent prompt**:

1. "Read-before-edit discipline: Read each target region before editing. Preserve exact existing arithmetic — do NOT recompute numbers."
2. "No change-logging of the fix itself. Do NOT add 'updated per remediation', 'fixed in this revision', or any meta-commentary. The repaired file must read as if it was always in its repaired state."
3. "Do NOT reorder sections. Do NOT add new sections beyond the specific insertions specified. Do NOT touch files outside your assigned list."
4. "Return format: for each file — (path, lines_deleted, lines_added, hunks_modified) + diff summary ≤ 20 lines + list any change-note left in place with reason."

**Folding R6 into WATCH-file agents**: Since WATCH-file agents already have the file open, include the R6 (corpus-wide scrub) patterns in their prompts. This reduces total agent count and avoids a second pass over those files.

#### Phase 3: Wave B — Verifier

Launch a single verifier agent after all Wave A agents complete:

- `subagent_type: Explore` (read-only by default)
- Reads each fixed file in the Wave A worktrees
- Re-runs the audit rubric (every dimension must score ≥ B)
- Re-runs the residual-pattern grep (must return zero matches)
- **Note**: Bash may not be available for shell grep in Explore agents. Structure checks as file-read patterns instead of shell commands.
- Pass criteria: every dimension ≥ B AND zero residual matches

#### Phase 4: Wave C — Merge

After Wave B confirms pass:

```bash
# Review diffs from each worktree
git diff --stat  # per worktree

# Apply to main checkout — most critical repair class first (R1 arithmetic, then R2, etc.)
git add <specific files>
git commit -m "fix: <description>"
```

Merge order: R1 (arithmetic) → R2 (terminology) → R3 (structure) → R4 (citations) → R5 (markers) → R6 (scrub).

## Unpublished Corpus Change-Note Deletion Philosophy

When a research corpus is **unpublished**, all change-note / correction-history / backward-compatibility prose must be **DELETED** — not annotated, not moved to changelogs, not summarized. The document must read as if it was always correct.

### Patterns to grep and delete

```bash
# All patterns that indicate change-history prose in an unpublished doc:
grep -n "Critical corrections applied:" file.md           # delete entire block
grep -n "(corrected from " file.md                        # delete parenthetical, keep final value only
grep -n "previously stated\|not.*as previously stated" file.md  # delete qualifier phrase
grep -n "CERTAIN (in legacy docs)\|CERTAIN (in original doc)" file.md  # delete row or rewrite cell
grep -n "\*\*Weight memory (corrected):\*\*" file.md      # rewrite as "**Weight memory:**"
grep -n "Previously missing citations now added:" file.md # delete sentence
grep -n "^## Corrections Applied" file.md                 # delete entire section
grep -n "\[corrected:" file.md                            # delete inline marker, keep corrected value
grep -n "earlier draft\|updated after review\|flagged in review" file.md
```

### Post-deletion check

After each deletion, re-read ±5 lines for dangling forward/backward references:
- "as noted above"
- "per the correction"
- "see the correction to"
- "as corrected in"

These become orphaned and must also be deleted or rewritten.

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
| --------- | ---------------- | --------------- | ---------------- |
| Background agents for long corpus passes | Launched fixer agents with `run_in_background=true` across 39 files | Stream idle timeout after ~28 minutes; agent connection dropped with "API Error: ConnectionRefused" at ~2M tokens / 77 tool uses | Use foreground agents (default) for long-running tasks. Split large batches into smaller foreground agents rather than one large background agent. |
| Wave B verifier with general-purpose subagent | Used `subagent_type: general-purpose` for verifier without specifying Bash access | Explore agents have Bash tool, but general-purpose agents without explicit shell prompts may not run grep commands reliably | Use `subagent_type: Explore` for verifiers. Note explicitly in the prompt that Bash may not be available — structure verification as file-read pattern checks instead of shell greps. |
| Skipping pre-flight grep | Launched fixer agents without first enumerating all defects | Two agents were assigned overlapping files; merge produced conflicts on 3 files | Always run pre-flight grep first. Never launch fixers until the full match set and WATCH/GO partitioning is complete. |
| Assigning same file to two parallel agents | Trusted agents to "avoid" touching the same file organically | Both agents edited the file; merge conflict | Explicit file lists per agent, no overlaps. The partition must be stated in the prompt: "Your file list is exhaustive — do not touch any file not on this list." |
| R6 scrub as separate agent from WATCH-file agents | Ran corpus-wide scrub as a standalone 7th agent after WATCH-file agents | WATCH-file agents had already opened files that R6 also needed; R6 re-opened and re-read them unnecessarily | Fold R6 patterns into WATCH-file agent prompts. Since those agents have the file open anyway, they perform the scrub in the same pass. Reduces agent count and total tool calls. |
| Annotating change-notes instead of deleting | Added `<!-- removed per audit -->` comments instead of deleting the change-note blocks | Annotation preserves the change-history narrative in a different form — still visible in rendered Markdown as whitespace or broken prose | Unpublished corpora require hard deletion. No annotation, no changelog, no comment. The file must read as if it was always in its final state. |
| Full cherry-pick when worktrees diverged from main | Ran `git cherry-pick <worktree-HEAD>` after main advanced past worktree base commit | Cherry-pick replayed the full commit including file regions where the worktree lacked main's subsequent improvements; conflicted on ancestor-state drift that had nothing to do with the intended fix | Use narrow diff `git diff HEAD~1 HEAD -- <owned files>` piped to `git apply --3way`; on remaining conflicts prefer `--theirs` (the Wave A fixer output). |
| Wave B verifier confirmed "verdict present" without checking uniqueness | Asked verifier to confirm the canonical novelty verdict appears; it did — but an older verdict line from a prior cleanup also remained | Presence check passes with duplicates; verifier missed 2 files with two `**Novelty verdict:**` lines each | Wave B rubric must include a uniqueness check: at most one verdict line per `## <section>` block. Grep pattern: `grep -c '^\*\*Novelty verdict:' <file>`. |
| Attempted `git checkout -- <path>` to reset wholesale copy | Safety Net blocked the command | Safety Net refuses `git checkout --` (discards data) and `git worktree remove --force` (can delete uncommitted changes) and `git stash drop` (permanent deletion) | Use `git stash push -m` to park unwanted changes; use `git worktree remove` without `--force` (accept that locked worktrees stay until parent process ends). |
| Worktree commits land on main unexpectedly for some agent variants | Launched 5 Wave 2 fixer agents with `isolation: "worktree"` and `subagent_type: general-purpose` | 2 of the 5 agents (Agents B and C) committed directly to main rather than their worktree branch; `git worktree list` showed no worktree for them. Partition assumed every agent would land on its own branch; merge order discipline broke (R3b content hit main before R3a structural inserts could be verified independently). Latent risk if partition had been imperfect — one main-landing agent could silently overwrite another | Verify after each Wave 2 agent completes: `git -C "$WORKTREE_PATH" log --oneline -1` AND `git log main..HEAD --oneline` on the main checkout. If the agent's commit already appears on main (use `git merge-base --is-ancestor`), skip its narrow-patch step; otherwise apply the patch normally. Do NOT assume worktree isolation is respected by all agent returns. |
| Phase 2a pre-flight greps used corpus-wide glob for §8 check | Initial pre-flight grep for "missing §8" used `research_*.md` glob including 7 Thematic-template files that legitimately use `## Accuracy / Quality Tradeoff` (non-numbered) instead of `## 8.` | False-positive detection flagged Thematic files (5.9, 5.10, 6.1–6.5) as "missing §8" when they weren't. Agent assignment nearly sent Thematic files to the R3 §8-insertion class, which would have introduced an extraneous numbered §8 to files that should only have the unnumbered thematic section | For dual-template corpora, run SEPARATE greps per template. For §8 check: `grep -L "^## 8\." $(ls STANDARD_files_only)` — explicitly enumerate the Standard-template glob. Verification scripts at the end must conditionally check `^## 8\.` for Standard and `^## Accuracy / Quality Tradeoff` for Thematic. |
| WebFetch sub-agents populating §X/Table-N locators from arXiv abstracts | User-requested per-file Citation Verifier sub-agents with WebFetch to populate missing §8 fields (arch-research-myrmidon-swarm-review v1.4.0 Phase 1 sub-agent role) | WebFetch on arXiv abstract pages returns abstract-only data — no paper-internal section numbers (§4.2, Table 3) and no figure/table captions. The "quality_delta with §X.Y locator" field could not be populated from arXiv metadata alone. Sub-agents returned `NO_PUBLIC_ABLATION` or fell back to in-file citation manifests | Before launching Citation Verifier sub-agents, know whether paper-internal locators are required. If yes and you only have arXiv abstracts, either (a) switch source to HuggingFace Papers, OpenReview, or ACL Anthology (which expose full paper structure), (b) fall back to extracting locators from the file's OWN citation manifest (where Wave 1 already resolved them), or (c) write "no public ablation" and accept the D2 downgrade. Do NOT let sub-agents invent or approximate locators. |
| `git apply --3way` leaves conflict markers in files but exits 0 | Wave 3 narrow-patch merge ran `git apply --3way /tmp/wave2-agent-X.patch` followed immediately by `git add <file>` and `git commit` | `git apply --3way` writes conflict markers to the file when it can't auto-merge, BUT it exits 0 (success) as long as at least one file applied. The subsequent `git add` staged the file with unresolved `<<<<<<<` / `=======` / `>>>>>>>` markers baked in; the commit landed with broken markdown | After EVERY `git apply --3way`, run `grep -rnE "^<<<<<<<" <files>` as a gate before `git add`. If any markers exist, resolve them MANUALLY (using `git diff --check` or the file list from the apply output) BEFORE staging. The v1.1.0 `--theirs` advice applies AFTER marker resolution, not instead of it. |
| `git commit --amend` without HEAD verification amends the wrong commit | After resolving a conflict in a file from a previously-committed patch, ran `git commit --amend --no-edit` to fold the conflict resolution into the just-created commit | HEAD had already advanced past the target commit (a subsequent `git apply` + `git commit` had landed). `--amend` modified the WRONG commit (the later one), bundling the fix-up into an unrelated change's diff; attribution got muddled | Before `--amend`, ALWAYS verify HEAD: `git log -1 --pretty=%s` to confirm the commit message matches the commit you intend to amend. Better still, avoid `--amend` in narrow-patch sequences entirely — create a follow-up `fix: resolve <file> conflict from <original-commit>` commit instead. `--amend` assumes HEAD stability; wave-based merges do not provide that stability. |
| Agent scope-boundary misreads left pre-existing scrub residues outside assigned files | R4 and R5 fixer agents correctly detected pre-existing `**CORRECTED:**` and `Critical corrections applied:` blocks in files they were editing but did NOT scrub them because those patterns weren't in their per-file scope instructions | Scrub residue leaked into merged output even when gates claimed clean; coordinator had to discover them only in corpus-wide post-merge grep | Every fixer agent prompt — even non-WATCH agents — should include a "if you see any change-note pattern anywhere in your assigned files, delete it (R6 scrub fold is always in scope)" clause. Trust-but-verify: always run a corpus-wide scrub grep post-merge, not just per-worktree grep |
| Wave-B verifier flagged false-positive "missing Executive Summary" because some standard files use numbered §2 Executive Summary | Verifier prompt said "verify `^## Executive Summary` heading exists" and the awk grep treated `^## 2. Executive Summary` as a miss | 5 files (3.1–3.5) were wrongly flagged as structural failures when they were legitimately numbered Exec Summary variants | Verifier structural checks for Exec Summary must accept both `^## Executive Summary` (unnumbered) AND `^## N. Executive Summary` (numbered) template variants. Write the check as `grep -E "^## ([0-9]+\. )?Executive Summary"` not a strict unnumbered match |
| Post-Wave-B discovery: several files had `## 8. Risk Assessment` + separate unnumbered `## Accuracy / Quality Tradeoff` instead of `## 8. Accuracy / Quality Tradeoff` | Original corpus template had both sections present but numbered Risk as §8; the rubric requires §8 = Accuracy/Quality | Standard §8 check failed on 3.1–3.5 and 4.4 even though the Accuracy content was fully present under a different heading | When Standard template requires §8 = a specific title, enforce that BOTH (a) the numbered §8 heading exists AND (b) its title matches the canonical name. Don't conflate presence of an Accuracy section anywhere with the §8 numbered slot. Fix pattern: renumber the "wrong" §8 to unnumbered `## Risk Assessment` and promote the unnumbered Accuracy section to `## 8. Accuracy / Quality Tradeoff` |
| Thematic template required `## Citations` heading but 6.x corpus used bare `<!-- CITATION MANIFEST -->` HTML comment | All 5 Thematic files in group 6 had a fully-populated citation manifest as an HTML comment block with no Markdown heading, so the Thematic `^## Citations` presence check failed | Verifier missed this on first pass (comment presence looked close enough); only caught by strict post-merge awk scan | Thematic template verification must enforce literal Markdown headings (`^## Citations`), not look for HTML comments or other soft equivalents. If corpus conventions use HTML comment manifests, add a Markdown `## Citations` heading immediately above the `<!-- CITATION MANIFEST -->` marker so both conventions are satisfied |
| Bibliography-entry change-note stubs survive corpus-wide scrub grep | Ran corpus-wide scrub grep for patterns like `Critical corrections applied`, `corrected from`, `previously stated`, `[corrected:`, `CORRECTED:`, `Weight memory (corrected)`, `not.*as previously stated`. Gate returned zero matches. Committed. | Bibliography entries carried a separate sub-class of residue the gate did not cover: trailing tokens like `ADDED — missing from original 5.10 research document`, `Second missing citation from original 5.9 summary`, `Not cited in original 5.9 summary`, `Critical addition.` appended to a citation line, `Added during merge.` appended as a sentence, and inline bibliographic meta-notes like `Note: citation key collision — use [X-Y] to disambiguate`. Because the fixer agents' scrub prompt was built from the R6 pattern list and none of those patterns were in the list, the fixer passes and the Wave B verifier both reported clean. | The R6 pattern list must include bibliography-entry suffixes and disambiguation-note patterns. Append these to every fixer prompt and Wave B verifier: `\bADDED\b` (word-boundary), `ADDED —`, `\. ADDED`, `missing from original`, `second missing citation`, `not cited in original`, `critical addition\.`, `added during merge\.`, `citation key collision`, `\. Note: citation key`, `— use \[.*\] to disambiguate`. Run the scrub pass TWICE after the first clean gate: residue often hides in structured content (tables, bibliography lists) where parser heuristics make it look like data rather than prose. |
| "Understated in the original" / "material gap in the original doc" / "[Original doc: X — WRONG]" pattern class | Initial R6 pattern list covered "critical correction", "corrected from", "previously stated". Wave A fixer agents scrubbed all matches and committed. | A parallel class of prose exists that marks the current text as having *superseded* a prior claim — phrased as editorial judgment rather than direct correction. Examples found after commit: `This risk is UNDERSTATED in the original doc`, `A material gap in the original doc`, `Absence from original doc was a gap`, `Missing from original doc's training stability discussion`, `[Original doc: ~2% — WRONG; error from using V=151,936 for A1]`. These read as authorial commentary to the scrub regex but are semantically change-notes. | Extend the R6 pattern list with semantic-judgment phrases: `understated in the original`, `material gap in the original`, `absence from original`, `missing from original doc`, `— WRONG;`, `[Original doc:`. Run these as a separate second pass focused on semantic scrub, distinct from the first pass's literal-phrase scrub. |
| Fixer agents land on main instead of their worktree (recovery protocol) | Launched three parallel Wave A fixer agents (R3, R4, R2) all with `isolation: "worktree"` and `subagent_type: "general-purpose"`. Each agent's prompt included explicit instructions to commit on its worktree branch. After completion, 2 of 3 agents (R4 and R2) reported worktree paths but their commits had landed on `main` in the shared repo directly — `git worktree list` showed no worktree branch for them. Only R3 correctly landed on its worktree branch (`worktree-agent-a1babe44`). | The `isolation: "worktree"` parameter is advisory to the agent runtime — some agent variants or runtime versions interpret it as "operate on an isolated copy" but still write commits to the parent repo's `main` when the agent path-resolves to the canonical directory. The prompt cannot force worktree discipline unilaterally. | ALWAYS verify after every Wave A agent completes, before proceeding to Wave C: `AGENT_COMMIT=$(git -C "$WORKTREE" rev-parse HEAD); if git merge-base --is-ancestor "$AGENT_COMMIT" main; then echo "Agent already landed on main → skip narrow patch for this agent"; else echo "Agent on worktree → proceed with narrow patch"; fi`. When some agents land on main and others land on worktrees, the Wave C merge order must interleave: on-main agents need nothing (they're already merged); worktree agents need narrow-patch. The `git diff HEAD~N HEAD -- <files>` depth N must reach the correct pre-agent base commit — use `HEAD~2` if the agent's worktree has two follow-up commits on top of the shared base (e.g., an initial fix commit plus a second-batch commit), not `HEAD~1`. Verify with `git -C "$WORKTREE" log --oneline -5` before extracting the patch. The mandatory conflict-marker gate `grep -rnE '^<<<<<<<' <files>` is still required after `git apply --3way` even when the worktree and main touch disjoint files — `--3way` can emit markers when line endings, whitespace, or nearby context differ even if the patch hunks don't literally overlap. |
| Three-commit progression: scrub-clean gate passes do NOT mean corpus-clean | After committing Wave A fixer output and a first R6 scrub follow-up, the gate `grep -rnEi "<R6 pattern union>" research_*.md` returned zero matches. Declared corpus clean. User requested another pass anyway. | Second pass surfaced 8+ more residue patterns: trailing `Critical addition.` / `Added during merge.` in bibliographies, `ADDED — missing from original` stubs in 6 bibliography entries, `UNDERSTATED in the original doc` in a §5 implementation bullet, `[Original doc: ~2% — WRONG]` labels under TPOT arithmetic breakdowns. Third pass (the one after that) surfaced zero additional patterns. The first-pass grep was clean ONLY because the pattern list didn't cover the new sub-classes. | "Clean under current gate" ≠ "clean under all gates the next reader will apply." After Wave C merge, schedule at least TWO post-merge audit passes with intentionally-expanded pattern lists — the first pass catches the patterns the scrub agent knew about; the second pass uses looser/semantic patterns (e.g., `original doc`, `pre-merge`, `during merge`, `missing from`, `added in this revision`, `WRONG`, `— corrected`, `\bADDED\b`). Treat Wave B clean as a local optimum, not a global one. |
| Authorial-review parentheticals survive v1.4.0 three-pass scrub | After releasing v1.4.0 with literal-phrase, bibliography-suffix, and semantic-judgment grep passes, re-audited the corpus and found four residual tokens: `(revised per review)`, `(qualified per review)`, `**Critical blockers (per review):**`, `**Status**: PARTIAL (~70% coverage after additions)` | None of these match the three v1.4.0 pattern classes: no literal "correction" phrase, no bibliography `[ADDED]` marker, no semantic-judgment "understated"/"material gap"/"[Original doc:" token. The parentheticals read as neutral parenthetical qualifiers to a regex but are semantically change-notes ("revised per review" = "this was revised during review") | Extend the R6 pattern list with a FOURTH pass for authorial-review parentheticals: `per review`, `after additions`, `after review`, `during review`, `post-review`, `(qualified per`, `(revised per`, `(qualified\)`, `(revised\)`. Run as a fourth pass in the scrub protocol. Lesson: review-process vocabulary leaks into edited text as parentheticals; scrub must catch the process metadata (`per review`, `after review`) not just direct correction words (`corrected`, `revised from`). |
| Frontmatter process-metadata (`## Status: MERGED`, `## Merged: DATE`, `## Sources:`, `## Date: ... (merged)`) survives all four v1.5.0 passes | v1.5.0 declared clean; hunt-the-next-class audit found 9 frontmatter lines across 5 files (1_5, 1_6, 1_7, 5_9, 5_10) that weren't scrubbed — 34 of 39 files followed the clean `## ID: X.Y` convention; 5 files leaked merge-process headers at the top of the file between `## ID` and `## Executive Summary` | The v1.3.0–v1.5.0 passes all match patterns in body prose. Frontmatter-style `## Status: MERGED` lines don't contain any of the literal/suffix/semantic/review tokens — they are pure process metadata in YAML-like heading form that evaded all four prior patterns. | Add Pass 5 — anchored-at-line-start grep for process-metadata headings: `^## (Status\|Merged\|Sources):`, `^## Date:.*\(merged\)`. Run as a fifth pass in the scrub protocol. Also audit all files for the *absence* of uniform frontmatter conventions: if 34/39 files use `## ID:` only, the 5 outliers are residue. Lesson: the document's frontmatter is as scrubbable as the body prose; unpublished docs must "read as if always in final state" applies to metadata, not just content. |
| Support-doc changelog section survives all passes because scrubs were scoped to `research_*.md` | v1.3.0–v1.5.0 passes ran on `research_*.md` only. `SHARED_PRELUDE.md:131–144` carried a `## Changelog: Corrections Applied to Prior Prelude` section — a 7-row correction-history table referencing a phantom `SHARED_PRELUDE.md.bak` file that no longer existed on disk. This is the single most egregious change-log-in-an-unpublished-doc violation the corpus contained, and no prior pass flagged it. | Grep scope must include ALL files that ship with the corpus — the shared prelude, architecture synthesis, cross-reference matrix, implementation spec, and priority ranking are part of the corpus even if they aren't named `research_*.md`. Prior passes' narrow scoping was a false economy. | Add Pass 6 — anchored-at-line-start grep for top-level changelog sections across the FULL corpus scope: `^## (Changelog\|Corrections Applied\|Revision history\|Change notes\|Prior Prelude)`. Glob must include all support docs, not only `research_*.md`. Verify that any `.bak` file referenced in a changelog either still exists (in which case the changelog is documenting real rollback state) or is absent (in which case the changelog is a phantom and must be deleted). |
| Cross-file numeric drift — arithmetic in prelude disagrees with arithmetic in research docs | Prelude line 58 and line 125 said "A2 @ 40,960 tokens ≈ 10.49 GB" in the KV-cache table. Two research files (3_4 and 1_2) independently re-derived the same number as 10.74 GB via the formula `64×2×8×128×40960×2 = 10,737,418,240 bytes`. Prelude was arithmetically wrong; two downstream files had corrected it silently; two other downstream files (6_2, 3_3) had inherited the prelude's wrong number. No text pattern catches this. | A "canonical source" with arithmetic errors is worse than no canonical source — it propagates the error to every doc that inherits it, while the docs that re-derived from scratch silently disagree. The v1.3.0–v1.5.0 pattern-based scrubs have no mechanism for arithmetic cross-check. | Add Pass 8 — arithmetic cross-check. For every canonical baseline × context-length combination in the prelude, re-compute the bytes value from scratch using the prelude's own formula. Grep the rendered value (both GB decimal and GiB binary) across the corpus and flag any that disagree with the re-derivation. The prelude itself is a potential source of error; don't trust it until you've verified its arithmetic against its own stated formulas. |
| Unit-label drift (GB vs GiB for the same byte count) within a single file | Prelude §Baseline-C-complexity (lines 87, 227) used "GiB" consistently; prelude §KV-cache-table (line 127) used "GB" for the same `10,737,418,240`-byte value. Research file 5_1 (line 234) also used "GB" for this value. Exec-summary tables in 6_3, 6_2, 6_4, 6_5 all used "GiB" correctly. A reader taking numbers at face value across conventions gets arithmetically inconsistent ratios. | Binary (GiB) vs decimal (GB) for the same bytes diverges by 7.4%. The prelude's own two sections contradict each other (both cite the same byte count but render it as "10.0 GiB" vs "~10.0 GB"). Prior scrubs never checked unit labels. | Add Pass 8b — unit-label grep for round-GiB values that are labeled GB: `\b10\.0 GB\b`, `\b20\.0 GB\b`, `\b80\.0 GB\b`, `\b160\.0 GB\b` for Baseline C (K2 family, 80 layers, GQA 8:1, head_dim=128). For each hit, inspect surrounding table header: if the whole table uses "GB" consistently, convert to the decimal rendering (`10.0 GB` → `10.74 GB`); if the table uses "GiB", retain binary rendering. Do not mix conventions within one table or prelude section. |
| Citations to real papers, but misquoting the paper's numeric claims — fabricated ranges, reversed polarity, paper-body figures presented as abstract quotes | Corpus cited `arXiv:2604.11035` (I-DLM) as "2.9–4.1× throughput at high concurrency" in research_6_3 and research_6_4. WebFetch of the arXiv abstract revealed the paper says "about 3× higher throughput than prior state-of-the-art DLMs" — the specific "2.9–4.1×" range is nowhere in the abstract; it was fabricated precision. Similar issues across the corpus: `arXiv:2406.10774` (Quest) — corpus had 7.03× self-attention / 2.23× end-to-end, abstract has them swapped; `arXiv:2511.18890` (Nemotron-Flash) — corpus headlined "over 45× higher throughput than comparable Transformer baselines", abstract specifies 18.7×/45.6× vs Qwen3-1.7B/0.6B (the 45× applies only to the smaller comparison); `arXiv:2510.13876` (GateSkip) — corpus said "25% compute savings on Llama-3.1-8B with >90% baseline accuracy", abstract says "up to 15% compute on long-form reasoning / 50% on instruction-tuned"; `arXiv:2208.14111` (RAFT) — corpus quoted "+5.31/+5.71 GLUE 100-shot, +0.7 GLUE full data", abstract reports "+5.71 GLUE 100-shot, +2.05 SQuAD full-data"; `arXiv:2007.11824` (FReLU) — corpus listed 4 authors including "Zheng", abstract lists 3 authors Ma/Zhang/Sun; `arXiv:2405.14852` (PV-Tuning) — corpus listed 6 authors with "Frantar, Panda, Hoefler", abstract lists 8 authors with none of those three. | The v1.3.0–v1.5.0 scrubs all match patterns inside the corpus. None of them can verify that a specific numeric claim matches the cited source's actual statement. Fabricated precision ("2.9–4.1×" derived from an abstract's "~3×") looks like legitimate content to any pattern-based checker; it only surfaces when you fetch the primary source and compare. Reversed-polarity claims ("+17% degradation" vs the paper's "our method reduces PPL") survive pattern scrubs unchanged. Wrong author lists and truncated titles in bibliographies also survive pattern scrubs. | Add Pass 7 — citation verification via arXiv abstract fetch. Dispatch parallel verification agents (one per file-group, ~6 files each) with up to 30 WebFetch calls each. For every body numeric claim attributed to a paper with an arXiv ID: (a) WebFetch `https://arxiv.org/abs/<ID>`; (b) verify paper exists, title/authors match, numeric claim is supported, direction/polarity is correct, ranges are not fabricated; (c) flag discrepancies with recommended fixes. Skip pre-2024 well-known foundational papers unless the claim is surprising. Prioritize exec summary, §4 Technical Analysis, §8 Accuracy / Quality Tradeoff, and derivation-tag-adjacent citations. Remedy pattern: where a body-level number is correct but not in the abstract, annotate `[per Table X, §Y of paper body]` rather than implying abstract support; where a number is fabricated or polarity-reversed, replace with the abstract's actual claim. Lesson: citation existence is necessary but not sufficient — the corpus must also say what the cited paper actually says. Pattern-based scrubs cannot catch this class; only direct primary-source verification can. |

## Results & Parameters

### Pre-flight grep union pattern

```bash
# Full union — run this exactly before partitioning
grep -rn \
  "Critical correction\|corrected from\|previously stated\|earlier draft\|\
updated after review\|flagged in review\|per audit\|Changelog\|\
Revision history\|Change notes\|was missing\|now reflects\|\
this replaces\|originally claimed\|In the original version\|\
for backward compat\|legacy (docs\|behavior\|wording)\|\
Critical corrections applied\|CERTAIN \\(in legacy\|\
CERTAIN \\(in original\|CERTAIN \\(if uncorrected\|\
CORRECTED:\|corrected)\|Year corrected\|\
previously missing.*added\|not.*as previously stated" \
  research/*.md
```

### Repair class taxonomy

| Class | Description | Typical patterns |
| ------- | ------------- | ----------------- |
| R1 | Arithmetic / numeric corrections | Wrong constants, recomputed formulas, mislabeled context lengths |
| R2 | Terminology normalization | Model name used as architectural label, TPOT direction symbols |
| R3 | Structural insertions | Missing `## Benefits vs Baseline X` sections, missing TTFT/TPOT rows |
| R4 | Citation format | Missing `§X.Y` locators, wrong citation style |
| R5 | Inline marker stripping | `[corrected: ...]` markers, `(corrected from X)` parentheticals |
| R6 | Corpus-wide scrub | "Critical corrections applied" blocks, "previously stated" qualifiers, risk-table rows with legacy labels, `**Weight memory (corrected):**` headers |

### Expanded R6 pattern list (bibliography + semantic + authorial-review + frontmatter + support-doc + cross-file + citation-verification)

The v1.3.0 scrub grep covered literal-phrase change-note patterns. The 2026-04-20 evening session surfaced two additional sub-classes that a single-pass literal grep misses: bibliography-entry suffixes (trailing tokens appended to citation lines) and semantic-judgment prose (editorial commentary about a prior claim being superseded). The 2026-04-20 late-evening post-v1.4.0 re-audit surfaced a third sub-class: authorial-review parentheticals (`(per review)`, `(revised per review)`, `(qualified per review)`, `after additions`) — review-process vocabulary that leaks into edited text as parenthetical qualifiers. The 2026-04-20 v1.6.0 hunt-the-next-class audit surfaced four more sub-classes: (a) frontmatter process-metadata (`## Status: MERGED`, `## Merged: DATE`, `## Sources: ...`, `## Date: ... (merged)` — editorial pass was scoped to body prose, so YAML-like frontmatter lines went undetected in 5 of 39 files); (b) support-doc changelogs (prior scrubs only ran on `research_*.md` — `SHARED_PRELUDE.md` carried a full 7-row `## Changelog: Corrections Applied to Prior Prelude` section that referenced a phantom `.bak` file); (c) cross-file numeric drift (prelude said A2 @ 40K KV = 10.49 GB but the arithmetic produces 10.74 GB; two downstream files had the correct 10.74 while prelude + two others had the wrong 10.49 — no text pattern catches this, only re-derivation + cross-file cross-check does); (d) unit-label drift (`10.0 GB` vs `10.0 GiB` for the same byte count in different parts of the same prelude). Additionally, the v1.6.0 session added a **citation-verification pass** that web-fetches every cited arXiv abstract and compares the corpus's numeric claims against the abstract text — this is the only way to catch fabricated numeric ranges (e.g. "2.9–4.1×" when abstract says "~3×"), reversed polarity ("+17% degradation" when paper's own method is the improvement direction), paper-body figures misattributed as abstract quotes, wrong author lists, and truncated paper titles. Run EIGHT passes — all must return zero matches before declaring the corpus clean.

```bash
# Pass 1: literal-phrase scrub (original v1.3.0 pattern list)
grep -rnE \
  "Critical correction|corrected from|previously stated|\[corrected:|\
CORRECTED:\*\*|\*\*CORRECTED|Weight memory \(corrected\)|Year corrected|\
In the original version|not as previously stated|Key corrections|\
originally claimed|this replaces|previously missing|\
Changelog|Revision history|Change notes" \
  research_*.md

# Pass 2: bibliography-suffix scrub (NEW in v1.4.0)
grep -rnE \
  "\bADDED\b|ADDED —|\. ADDED[^:]|missing from original|\
second missing citation|not cited in original|\
critical addition\.|added during merge\.|\
citation key collision|— use \[.*\] to disambiguate" \
  research_*.md

# Pass 3: semantic-judgment scrub (NEW in v1.4.0)
grep -rnEi \
  "understated in the original|material gap in the original|\
absence from original|missing from original doc|\
— WRONG;|\[Original doc:|original document('s)? (error|claim|figure|stated)|\
original research doc|pre-merge doc" \
  research_*.md

# Pass 4: authorial-review parenthetical scrub (NEW in v1.5.0)
grep -rnEi \
  "per review|after additions|after review|during review|post-review|\
\(qualified per |\(revised per |\(qualified\)|\(revised\)" \
  research_*.md

# Pass 5: frontmatter process-metadata (NEW in v1.6.0)
# Catches `## Status: MERGED`, `## Merged: DATE`, `## Sources: ...`, `## Date: ... (merged)`
# These are YAML-like frontmatter lines that body-prose scrubs miss entirely.
grep -rnE "^## (Status|Merged|Sources):|^## Date:.*\(merged\)" \
  research/*.md SHARED_PRELUDE.md

# Pass 6: support-doc changelog sections (NEW in v1.6.0)
# Scope must include all support docs (prelude, synthesis, matrix), not just research_*.md.
# Catches `## Changelog:`, `## Corrections Applied`, `## Revision history`, `## Prior Prelude`.
grep -rnE "^## (Changelog|Corrections Applied|Revision history|Change notes|Prior Prelude)" \
  research/*.md SHARED_PRELUDE.md architecture_synthesis.md cross_reference_matrix.md \
  priority_ranking.md implementation_spec_phase1.md 2>/dev/null

# Pass 7: citation verification via arXiv abstract fetch (NEW in v1.6.0)
# Step A: enumerate every citation that makes a specific numeric claim
#         (percentages, ratios, bytes, tokens, PPL, seconds, accuracy points)
#         attributed to a named paper with an arXiv ID.
# Step B: for each, WebFetch https://arxiv.org/abs/<ID> and verify:
#         (1) paper exists at that ID,
#         (2) title/authors match corpus,
#         (3) the specific numeric claim is supported by the abstract,
#         (4) direction/polarity is not reversed (improvement vs degradation),
#         (5) ranges are not fabricated (e.g., "2.9-4.1×" when abstract says "~3×").
# Failure mode if skipped: no text pattern catches these hazards. The I-DLM
# "2.9-4.1×" range was fabricated precision from an abstract that only said "~3×";
# the Ma et al. PPL framing was directionally defensible but polarity-ambiguous;
# SwitchHead's "2× / 0.3-0.8 PPL degradation" was paper-body but abstract reported
# "up to 8× fewer attention matrices" and baseline match (no degradation).
# Dispatch: 6 parallel verification agents (one per file-group) each with up to
# 30 WebFetch calls; focus on body numeric claims in Exec Summary, §4 Technical,
# §8 Accuracy, and derivation-tag-adjacent citations. Skip pre-2024 well-known
# foundational papers (Transformer, Mamba, LoRA, RoPE) unless the claim is surprising.

# Pass 8: cross-file numeric drift + unit-label drift (NEW in v1.6.0)
# Step A: re-derive canonical numbers from SHARED_PRELUDE.md formulas from scratch.
#         For each baseline × context-length combination, compute bytes with the
#         prelude's formula and check both decimal (GB) and binary (GiB) renderings.
# Step B: grep the rendered values across the corpus and flag any that disagree
#         with the canonical re-derivation. Example: A2 @ 40K =
#         64×2×8×128×40960×2 = 10,737,418,240 bytes = 10.74 GB decimal = 10.00 GiB.
#         "10.49 GB" is arithmetically wrong and must be corrected.
# Step C: grep `\b<number> GB\b` for each bytes-count that equals a round GiB
#         value (10.0, 20.0, 80.0, 160.0) and check whether the surrounding
#         context uses GiB or GB consistently; `10.0 GB` is really 10.74 GB
#         decimal or 10.0 GiB binary and must not be labeled the other way.
grep -rnE "\b10\.0 GB\b" research/*.md SHARED_PRELUDE.md
# Inspect each hit: if context references Baseline C / K2 / 72B dense, the
# value `10,737,418,240` bytes must be labeled consistently — either GiB (binary)
# throughout the surrounding table or converted to the decimal 10.74 GB.

# Gate: ALL EIGHT passes must return zero matches.
# If pass 1 is clean but pass 2, 3, 4, 5, 6, 7, or 8 surfaces hits, that is the
# expected first-iteration result — fix and re-run all eight until all return zero.
```

**Why eight passes, not one giant union**: pass 1 and pass 2 are literal text scrubs; pass 3 and pass 4 are case-insensitive because editorial and review-process phrases vary in capitalization; pass 5 and pass 6 are anchored at line start to catch frontmatter and support-doc headings that body scrubs miss; pass 7 requires web access to verify claims against primary sources (no regex can catch fabricated numeric ranges); pass 8 requires arithmetic re-derivation and unit-label cross-checks (no regex can catch a number that's right in the body but wrong in the prelude). Folding them into a single grep loses the case distinction or explodes the alternation list, and web-verification and arithmetic passes are structurally separate from text scrubs. Keeping them as eight separate invocations also makes the failure mode legible — a fail on pass 5 tells you the frontmatter class is the problem, not body prose; a fail on pass 7 tells you citation content is fabricated, not that scrubbable vocabulary leaked; a fail on pass 8 tells you the prelude's own math is inconsistent with downstream derivations.

### Agent count by corpus size

| Files | Recommended Wave A agents |
| ------- | -------------------------- |
| 10–20 | 3–4 (combine low-density repair classes) |
| 20–40 | 5–6 (one per primary repair class) |
| 40–80 | 6–8 (split high-density classes by file range) |

### Wave C merge: narrow-patch cherry-pick (when worktree base diverged from main)

When `main` has advanced past the commit each worktree was created from, a full `git cherry-pick <worktree-HEAD>` replays the entire commit and conflicts on ancestor-state drift unrelated to the Wave A fix. Extract a narrow diff restricted to each agent's owned files and apply with 3-way merge:

```bash
# For each worktree, produce a narrow patch limited to assigned files:
git -C "$WORKTREE_DIR" diff HEAD~1 HEAD -- ArchIdeas/research/<file1> ArchIdeas/research/<file2> > /tmp/rX.patch

# Apply with 3-way merge (falls back to conflict markers only where genuinely needed):
cd $MAIN_REPO
git apply --3way /tmp/rX.patch

# Resolve remaining conflicts — prefer the Wave A fixer's version (it was purpose-designed
# and Wave B already verified it end-to-end):
git checkout --theirs <conflicted-file>
git add <file>
git commit
```

**Why 3-way apply beats cherry-pick**: cherry-pick replays the full commit (all file hunks) and must reconcile everything including unintended ancestor-state drift. A 3-way diff limited to the agent's owned files only reconciles the intentional edits.

**Why `--theirs` for conflict resolution**: "Theirs" is the Wave A fixer agent's output — designed with the full canonical rubric in mind and already validated by Wave B. "Ours" is typically incidental prior-draft phrasing from an earlier cleanup pass.

#### MANDATORY Wave-A post-completion verification

Run this for EVERY Wave A agent before touching Wave B or C. Two classes of agent-runtime (described in the v1.4.0 "Fixer agents land on main" Failed Attempt row) respect `isolation: "worktree"` differently; without this check some agents silently land on main while others land on worktrees, and the narrow-patch step replays already-merged work or — worse — overwrites a main-landing agent's commit with stale content.

```bash
# MANDATORY Wave-A post-completion verification (NEW in v1.4.0)
# Run this for EVERY Wave A agent before touching Wave B or C.

for WT in "$WT_R1" "$WT_R2" "$WT_R3" "$WT_R4" "$WT_R5"; do
  [ -d "$WT" ] || continue
  AGENT_COMMIT=$(git -C "$WT" rev-parse HEAD)
  WT_BRANCH=$(git -C "$WT" branch --show-current)

  if git -C "$MAIN_REPO" merge-base --is-ancestor "$AGENT_COMMIT" main; then
    echo "[$WT_BRANCH → $AGENT_COMMIT] already on main — skip Wave C patch"
  else
    echo "[$WT_BRANCH → $AGENT_COMMIT] on worktree — Wave C narrow-patch required"
    # Verify patch depth before extraction:
    git -C "$WT" log --oneline -5   # count commits since shared base
  fi
done
```

**Patch-depth caveat**: when an agent commits twice on its worktree (e.g., initial fix + a follow-up second-batch commit), `HEAD~1` extracts only the second commit. Use `git log --oneline -5` to count commits since the shared base and use the correct `HEAD~N` depth. The mandatory conflict-marker gate (`grep -rnE '^<<<<<<<|^>>>>>>>|^======='`) still applies after `git apply --3way` even when the worktree and main touch disjoint files — `--3way` can emit markers when line endings, whitespace, or nearby context differ even if the patch hunks don't literally overlap.

### Wave B rubric addition: verdict uniqueness check

Presence checks pass duplicates. After Wave B's rubric and residual-pattern greps, run a per-section uniqueness check:

```bash
# After Wave B rubric, run a uniqueness check:
for f in <fixed files>; do
  count=$(grep -c "^\*\*Novelty verdict:" "$f")
  if [ "$count" -gt 1 ]; then
    echo "FAIL: $f has $count novelty verdicts (expected 1)"
  fi
done
```

**Exception — per-section, not per-file**: Some templates legitimately place the verdict in BOTH the Executive Summary and the Prior Art Classification section. Treat that as two distinct *contexts*. The real invariant is: **at most one `**Novelty verdict:**` line per `## <section>` block**, not per file. If your verdict-in-both-sections template is in use, refine the check to count per-section (scan `##` boundaries, count verdict lines within each).

### Wave 2 agent landing verification

Some Wave 2 agents commit directly to `main` rather than to their worktree branch. Before each Wave 3 narrow-patch step, verify where the agent's commit actually landed:

```bash
# After EACH Wave 2 agent returns (before Wave 3), verify where its commit landed:
AGENT_COMMIT=$(git -C "$WORKTREE_PATH" rev-parse HEAD)
ALREADY_ON_MAIN=$(git -C "$MAIN_REPO" merge-base --is-ancestor "$AGENT_COMMIT" main && echo yes || echo no)

if [ "$ALREADY_ON_MAIN" = "yes" ]; then
  echo "Agent $X commit $AGENT_COMMIT already on main — skip narrow-patch step"
else
  # Standard Wave 3 flow: extract narrow diff + git apply --3way
  git -C "$WORKTREE_PATH" diff HEAD~1 HEAD -- <owned files> > /tmp/rX.patch
  git -C "$MAIN_REPO" apply --3way /tmp/rX.patch
  # MANDATORY: check for conflict markers before staging
  grep -rnE "^<<<<<<<|^>>>>>>>|^=======" <owned files> && echo "RESOLVE FIRST" && exit 1
  git add <owned files>
  git commit -m "fix: ..."
fi
```

**Why**: `isolation: "worktree"` is not uniformly respected by every agent variant. Without this check the same intentional edit can land twice (once from the agent directly on main, once from the narrow-patch replay), or — in the worst case — a main-landing agent can silently overwrite another's work if the partition is imperfect.

### Dual-template corpus verification gates

For corpora with two templates (Standard `## 1.`–`## 8.` vs Thematic unnumbered `## Accuracy / Quality Tradeoff`), each template's required structure must be verified separately. A corpus-wide `research_*.md` wildcard will false-positive on the template it doesn't apply to.

```bash
# Standard files (require ## 8.)
STANDARD_FILES=$(ls research/research_{1_*,2_*,3_*,4_*,5_{1,2,3,4,5,6,7,8}}*.md 2>/dev/null)
for f in $STANDARD_FILES; do
  grep -q "^## 8\." "$f" || echo "MISSING §8 (Standard): $f"
done

# Thematic files (require ## Accuracy / Quality Tradeoff as unnumbered)
THEMATIC_FILES=$(ls research/research_{5_9,5_10,6_*}*.md 2>/dev/null)
for f in $THEMATIC_FILES; do
  grep -q "^## Accuracy / Quality Tradeoff" "$f" || echo "MISSING Accuracy section (Thematic): $f"
done

# Novelty verdict per-section uniqueness (v1.1.0 rule, extended)
for f in research/research_*.md; do
  awk '/^## /{sec=$0} /^\*\*Novelty verdict:/{count[sec]++} END{
    for(s in count) if(count[s]>1) print FILENAME ":" s ":" count[s]
  }' "$f"
done
```

### Worktree cleanup after merge

```bash
MNEMOSYNE_DIR="$HOME/.agent-brain/ProjectMnemosyne"
# After all merges confirmed:
git -C "$MNEMOSYNE_DIR" worktree remove /tmp/mnemosyne-skill-doc-corpus-remediation 2>/dev/null || true
git -C "$MNEMOSYNE_DIR" worktree prune
```

## Verified On

| Project | Context | Details |
| --------- | --------- | --------- |
| ArchIdeas corpus | 39-file research corpus, 6 repair classes | Apr 2026 — Wave A: 6 parallel worktree agents. Wave B: Explore verifier. All change-note prose deleted. Zero residual matches confirmed. |
| ArchIdeas corpus | 39-file audit + remediation rerun | Apr 2026-04-19 — Wave A: 5 parallel worktree agents (R1/R2/R3/R5/R6 across 13 files). Narrow-patch cherry-pick handled 3 of 5 conflicts via --theirs resolution. Post-merge grep caught 2 duplicate-verdict files missed by Wave B presence check. |
| ArchIdeas corpus | 39-file fresh audit + full remediation run | Apr 2026-04-19 (evening) — Wave 1: 6 parallel Explore audit agents (39 files graded on 6 dimensions). Wave 2: 5 parallel worktree fixer agents (§8 insert + canonical verdict markers + 3_8/5_3/5_10 scrub + 6_3 D6 retighten). Wave 3: narrow-patch merge with 2 conflicts resolved. Two unexpected behaviors: (1) some agents committed directly to main bypassing worktree, (2) `git apply --3way` left conflict markers that required manual resolution gates. |
| ArchIdeas corpus | 39-file fresh audit + remediation + follow-up structural-fix pass | 2026-04-20 — Wave 1: 6 parallel Explore audit agents (graded 39 files on 6 dimensions). All files scored ≥B+; 21 files had one or more sub-B dimensions. Wave A: 4 parallel worktree fixer agents (R1 arith ×2, R3 struct ×13, R4 cite ×3/4 — agent skipped 6.4 legitimately, R5 marker ×2). Wave C: narrow-patch merges with 7 conflicts resolved via --theirs. Wave B verifier caught 4 unresolved issues: 3.1–3.5 had §8=Risk with separate unnumbered Accuracy; 6.1–6.5 had bare `<!-- CITATION MANIFEST -->` without `## Citations` heading; 4.2/4.6/5.4 needed §8 renumbering; 1.7 had a pre-existing `CORRECTED from original` residue. All fixed in two follow-up commits. Final state: zero residual scrub patterns, zero duplicate per-section verdicts, all Standard §8 = Accuracy/Quality, all Thematic have ## Citations + ## Accuracy + 4× Benefits. |
| ArchIdeas | 2026-04-20 evening session — full re-audit + 3-wave fixer + 3-pass scrub | Surfaced bibliography-suffix and semantic-judgment scrub classes; 2 of 3 Wave A agents landed on main (not worktree); 6 commits total on main |
| ArchIdeas | 2026-04-20 late-evening post-v1.4.0 re-audit | Found `(per review)` / `(revised per review)` / `(qualified per review)` / `after additions` residue in 2 files that evaded the v1.4.0 three-pass scrub; v1.5.0 adds a fourth pass |
