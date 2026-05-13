---
name: cross-doc-citation-drift-defenses
description: "Procedural and audit defenses against two failure modes when authoring inter-citing markdown corpora: (A) section-numbering drift when one document is reorganized but its citers are not updated in the same commit, and (B) arXiv ID-to-title swaps within a single author's multi-paper corpus during initial drafting. Use when: (1) authoring a corpus of inter-citing markdown documents (research scoping docs, design specs, paper drafts) with §-references between files, (2) citations involve external sources (arXiv IDs, DOIs, model cards, API URLs), (3) multiple documents share section-numbering schemes that may be reorganized during review loops, (4) multi-author corpora where one author has 3+ papers (Millidge, Bengio, Hinton, etc.) — high ID/title swap risk, (5) you need authoring-time defenses, not just post-hoc verification."
category: documentation
date: 2026-05-12
version: "1.0.0"
user-invocable: false
verification: verified-local
tags: [citation, cross-reference, section-numbering, stale-reference, arxiv, primary-source, authoring-discipline, multi-document-corpus, citation-drift, reorganization-discipline]
---

# Cross-Doc Citation Drift Defenses

## Overview

| Field | Value |
| ------- | ------- |
| **Date** | 2026-05-12 |
| **Objective** | Prevent two related failure modes when authoring a corpus of inter-citing markdown documents: (A) silent dangling §-references when one document is reorganized but its citers are not updated in the same commit, and (B) arXiv ID-to-title swaps within a single author's multi-paper corpus during initial drafting that survive multiple review cycles because each citation looks plausible in isolation. |
| **Outcome** | Successful on Predictive-Coding-in-Mojo Phase 0 corpus: caught 8 stale §-references (LITERATURE/DEPENDENCY citing ALGORITHM §6.x.x after ALGORITHM was reorganized to flat §1-§7) via Myrmidon swarm complexity-auditor role; caught 2 arXiv-ID-to-title swaps in the Millidge PC paper corpus that survived two prior `feature-dev:code-reviewer` cycles before a third merged project-specialized reviewer caught them via cross-paper consistency check. |
| **Verification** | verified-local — caught real instances in one session (8+ stale §-references, 2 fabricated arXiv-ID-to-title swaps); not yet validated across multiple projects. |
| **Complements** | `citation-verification-arxiv-abstract-fetch` — that skill is the post-hoc audit verifier for numeric-claim defects in already-cited papers; this skill is the authoring-time procedural discipline that prevents drift in the first place and the structural-defense pattern for ID-to-title swaps during initial corpus drafting. |

## When to Use

- Authoring a corpus of inter-citing markdown documents (research scoping docs, design specs, paper drafts) where one file's §4.2.3 is referenced from a sibling file's prose.
- Citations involve external sources (arXiv IDs, DOIs, model cards, API URLs) where ID-to-title mismatch is undetectable without primary-source lookup.
- Multiple documents share section-numbering schemes that may be reorganized during review loops (initial draft uses one outline; review reorganizes it; citers are forgotten).
- Multi-author corpora where one author has 3+ papers (Millidge has 5 PC papers; Bengio, Hinton, LeCun have many) — high ID/title swap risk because a swap within an author's own corpus is locally plausible (right author, right year, right topic) and only visible via cross-paper consistency check.
- You need authoring-time defenses (procedural) AND verification-time defenses (audit), not either alone — both failure modes survive multiple reviewer cycles.

## When NOT to Use

- Single-document deliverables with no internal cross-references.
- Citation-free technical writing (pure how-to docs).
- Live code where typechecking and CI handle reference validity (this skill is for prose corpora that lack a compile/CI cross-ref check).

## Verified Workflow

### Quick Reference

```bash
# 1. § GREP-AUDIT — list every §-reference across the corpus and verify against actual §-headings.
#    Use `§` glyph as the prefix so cross-references can be distinguished from non-cite digit-dot-digit patterns.
grep -rEn "[A-Z_]+\.md *§[0-9]+(\.[0-9]+)*" <docs-dir>/ \
  | awk -F'§' '{print $1, "§"$2}' | sort -u

# 2. EXTRACT every §-heading in the cited documents:
grep -rEn "^#{2,4} §[0-9]+(\.[0-9]+)*" <docs-dir>/ | sort -u

# 3. DIFF the two — every reference §-number in (1) must resolve to a heading §-number in (2).
#    Citations whose §-number is NOT in the heading list are stale and must be remapped.

# 4. ARXIV-ID round-trip — for every primary-source citation, WebFetch the arXiv abstract page
#    and verify the returned title matches the citation entry's claim. ID-to-title swaps within
#    a single author's corpus are otherwise invisible.
```

### Citation entry template (use verbatim for every primary-source citation)

```text
**Citation:** <Author1>, <Author2>, <AuthorN> et al. "Full Paper Title." *Venue*, vol/issue/pages, year. DOI/URL.
**arXiv ID** (if applicable): <NNNN.NNNNN>
**Status:** [verified-via-WebFetch on YYYY-MM-DD] | [ASSUMPTION — to validate]
```

The `Status:` line is the auditable provenance — every entry should explicitly say whether it was WebFetched or is provisional. Absent `Status:` markers signal the entry has been verified end-to-end.

### Detailed Steps

#### Failure mode A — Section-numbering drift across documents

When document X is drafted citing document Y's `§4.2.3` based on Y's draft outline, then Y is later reorganized to a flat `§4` structure (no §4.2.3), X's citation silently becomes a dangling reference. `grep §4.2.3 Y.md` returns nothing. The reader following the link gets "section not found." The drift compounds: every downstream artifact citing Y inherits stale references.

**Defense A.1 — Global mapping table during reorganization.** When restructuring document Y's section numbering, immediately produce a mapping table and apply it via global find-replace across all citing documents in one commit:

```text
| Old §-number | New §-number | Notes                              |
| ------------ | ------------ | ---------------------------------- |
| §6.2.2       | §2.2         | Layer-type rule for Linear         |
| §6.2.3       | §2.3         | Layer-type rule for Conv2D         |
| §6.3.1       | §4.1         | Energy update equation             |
| §6.4         | §7           | Promoted to top-level pseudocode   |
```

Apply via global find-replace across all citing files in one commit. **Do not** rename sections in Y first, then "remember to update citations later" — the citing documents will diverge before you remember, and downstream artifacts (PR descriptions, issue bodies, follow-on docs) will inherit the stale numbering.

**Defense A.2 — Greppable §-prefix.** Use the `§` glyph prefix in headings (`### §4.2.3 Title`) so cross-references can be grep-audited. Plain `4.2.3` digit-dot-digit patterns can't be distinguished from non-cite occurrences (version numbers, dates, decimal values). The `§` glyph provides the disambiguating signal that makes a corpus-wide audit possible.

**Defense A.3 — Reviewer subagent for cross-doc consistency.** A "complexity-auditor" or "cross-reference-checker" role takes the corpus as input and verifies every cited §-number resolves to an actual §-heading in the target document. This was the role that caught the §6.x-to-§2.x/§4.x/§7.x drift in the Predictive-Coding session — neither the per-file `feature-dev:code-reviewer` nor the markdown linter can see cross-document drift.

#### Failure mode B — arXiv ID-to-title swap during multi-paper summarization

When an exploration agent summarizes a research corpus where one author has multiple papers (Millidge has 5 PC papers), the agent reliably swaps arXiv IDs and titles between papers. The swap survives multiple review cycles because each individual citation looks plausible — the right author, right year, right topic — but the ID points to a different paper in the same author's corpus.

**Defense B.1 — WebFetch every arXiv ID against its abs page during initial drafting.** Don't trust the exploration agent's summary. For each citation entry, fetch `https://arxiv.org/abs/<id>` and verify the returned title and first author match the citation entry's claim. This is the citation-verifier role; do it during initial drafting, not as a final pass — by the final pass, the swap has propagated to derived artifacts.

**Defense B.2 — Full titles in every citation entry, not genre tags.** A citation entry that says "Millidge 2022 energy-based" is harder to audit than one that says "Millidge 2022 — 'Backpropagation at the Infinitesimal Inference Limit of Energy-Based Models'". The full title makes ID-to-title mismatches visible to a reader without WebFetch. When summarizing handoff notes that will become citations, demand full titles. Reserve genre tags for prose; never use them as the citation locator.

**Defense B.3 — `[ASSUMPTION — to validate]` marker for borderline citations.** When a citation entry is partially derived (year confirmed but venue unclear, ID confirmed but full title not yet fetched), mark it explicitly with the `[ASSUMPTION — to validate]` token. The marker is auditable; absent markers signal the entry has been verified end-to-end. A reviewer can then `grep -n 'ASSUMPTION' <docs-dir>/` to find unfinished work.

**Defense B.4 — Procedural AND verification-based defenses.** Both failure modes survive multiple reviews. In the Predictive-Coding session, two prior `feature-dev:code-reviewer` cycles passed the LITERATURE.md citation entries before the merged project-specialized reviewer caught the swaps. The defenses must be procedural (during authoring) AND verification-based (during review), not either alone. Pattern-matching scrubs cannot catch ID-to-title swaps, and per-file reviewers cannot catch cross-document §-drift.

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
| --------- | ---------------- | --------------- | ---------------- |
| Drafted LITERATURE.md / DEPENDENCY.md citing ALGORITHM §6.2.2 based on ALGORITHM's draft outline | Initial ALGORITHM draft used nested §6.x.x for layer-type rules; LITERATURE/DEPENDENCY were drafted referencing that scheme | ALGORITHM was reorganized to flat §1-§7 structure during its own review loop; the §6.x.x scheme was abandoned. 8 stale references propagated across 3 files. `grep §6.2.2 ALGORITHM.md` returned nothing — the references were dangling but markdownlint saw no problem | Reorganize once; produce a global mapping table at the moment of reorganization; global-replace across all citing documents BEFORE any other commit lands. Do not "remember to update citations later" — the citing documents will diverge before you remember |
| Two prior review cycles via `feature-dev:code-reviewer` on LITERATURE.md | First reviewer caught wrong arXiv ID for the 26.21% SOTA paper; second reviewer caught residuals; we thought citations were clean after two passes | Third reviewer (merged project-specialized role) caught additional ID swaps in the Millidge corpus that the prior reviewers had verified individually but didn't cross-check against each other. Each Millidge entry looked plausible in isolation (right author, right year, right PC topic) but two IDs pointed to swapped titles within his own corpus | Multi-author-corpus citations need WebFetch verification of EVERY arXiv ID + full-title shorthand in entries, not just spot-checks. Per-file reviewers cannot detect intra-author swaps; only a verifier that fetches every ID's abs page and cross-checks against the entry's claimed title can |
| Genre-tag shorthand for Millidge papers ("energy-based", "computation-graph", "survey") | Used 1-2 word descriptors instead of full titles in summary handoffs from exploration agents to drafting agents | The descriptors made ID-to-title swaps invisible to downstream readers — both "energy-based" and "computation-graph" are plausible labels for either paper in Millidge's corpus, so neither the human reviewer nor the next agent in the chain could spot a wrong assignment without WebFetching | Always include full titles in citation entries; reserve genre tags for prose, never for the citation locator. Demand full titles in any handoff note that will become a citation |
| Trusting "looks-plausible" individual citations during the second review cycle | Each citation entry passed individual review (right author, right year, right topic, plausible title) — assumed the corpus was clean | Plausibility is local; correctness is global. An ID-to-title swap within a single author's own corpus is locally plausible by construction (the swap target is by definition the same author, similar topic, often the same year). The swap is only visible against the primary source | Never let "looks plausible" substitute for "verified against primary source" for any citation that is load-bearing. The cost of a WebFetch is small; the cost of a fabricated citation in a published artifact is large |
| Pattern-based scrubs for citation residue (literal-phrase, frontmatter, semantic-judgment) | Ran multiple text-pattern scrubs across the corpus before declaring citations clean | Pattern scrubs cannot detect §-number drift (the new §-number is a real heading somewhere, just not in the cited document) and cannot detect ID-to-title swaps (both the ID and the title are well-formed and from the right author). Both failure modes are STRUCTURAL, not textual | Cross-doc citation drift is a structurally different hazard class from text residue. It cannot be caught by regex — only by (a) global mapping tables enforced at reorganization time and (b) primary-source verification of every external ID. Add this as a separate gate from text scrubs |

## Results & Parameters

### Defense matrix

| Failure mode | Authoring-time defense | Audit-time defense | Detector role |
| -------------- | ----------------------- | -------------------- | --------------- |
| §-numbering drift | Global mapping table at moment of reorganization; `§` glyph prefix in headings | grep-audit script (Quick Reference §1-§3); reviewer subagent that diffs reference §-numbers vs heading §-numbers | complexity-auditor / cross-reference-checker subagent |
| arXiv ID-to-title swap | Full titles in every citation entry (no genre tags as locator); `[ASSUMPTION — to validate]` marker for partial entries | WebFetch every ID's abs page; cross-check returned title vs entry's claim | citation-verifier subagent (also see `citation-verification-arxiv-abstract-fetch`) |

### Recommended grep-audit commands

```bash
# § GREP-AUDIT — list every §-reference across the corpus
grep -rEn "[A-Z_]+\.md *§[0-9]+(\.[0-9]+)*" <docs-dir>/ \
  | awk -F'§' '{print $1, "§"$2}' | sort -u

# Extract every §-heading in target documents
grep -rEn "^#{2,4} §[0-9]+(\.[0-9]+)*" <docs-dir>/ | sort -u

# Find unverified citation entries (those lacking a Status: marker)
grep -L 'Status:' <docs-dir>/*-citations.md

# Find still-pending assumptions
grep -rn 'ASSUMPTION — to validate' <docs-dir>/
```

### Citation entry template (verbatim)

```text
**Citation:** <Author1>, <Author2>, <AuthorN> et al. "Full Paper Title." *Venue*, vol/issue/pages, year. DOI/URL.
**arXiv ID** (if applicable): <NNNN.NNNNN>
**Status:** [verified-via-WebFetch on YYYY-MM-DD] | [ASSUMPTION — to validate]
```

### Reorganization mapping table template

When reorganizing a document's §-numbering, produce this table BEFORE renaming any sections:

```text
| Old §-number | New §-number | Notes                              |
| ------------ | ------------ | ---------------------------------- |
| §6.2.2       | §2.2         | Layer-type rule for Linear         |
| §6.2.3       | §2.3         | Layer-type rule for Conv2D         |
| §6.3.1       | §4.1         | Energy update equation             |
| §6.4         | §7           | Promoted to top-level pseudocode   |
```

Apply via global find-replace across all citing files in one commit. The mapping table itself should be archived (e.g., in the reorganization PR description) so reviewers can audit the migration.

### Key insight: both modes survive multi-reviewer rotation

In the verified Predictive-Coding session, the §-drift survived two prior reviewer rotations because each reviewer was scoped to a single file and could not see cross-document references. The arXiv ID swap survived two prior reviewer rotations because each reviewer verified entries individually (right author, right year, right topic) and could not see intra-author swaps. The defenses must be:

1. **Procedural** — produce mapping tables and full-title entries during authoring, not after.
2. **Cross-document** — audit roles that take the whole corpus as input, not just one file.
3. **Primary-source-bound** — WebFetch every ID against its abs page; trust no exploration-agent summary for citation entries.

## Verified On

| Project | Context | Details |
| --------- | --------- | --------- |
| mvillmow/Random — Predictive-Coding-in-Mojo Phase 0 | Caught 8 stale §-references via Myrmidon swarm complexity-auditor role (§6.x.x dangling references after ALGORITHM was flattened to §1-§7); caught 2 arXiv-ID-to-title swaps in the Millidge PC paper corpus via 3 successive citation-verifier rounds | Commits `ad52b73` (cross-ref sweep), `693277c` and `011f985` (citation fixes) document the fixes. Both failure modes survived two prior `feature-dev:code-reviewer` cycles before being caught |
