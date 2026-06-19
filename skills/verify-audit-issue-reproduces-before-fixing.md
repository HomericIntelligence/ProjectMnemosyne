---
name: verify-audit-issue-reproduces-before-fixing
description: "Verify an audit issue actually reproduces against the live file BEFORE planning a fix — treat audit line numbers and quoted strings as claims, not facts. Run the repro greps DURING planning; the legitimate outcome may be 'no edit, recommend closing as non-reproducible.' Use git log -S to distinguish a stale finding (content NEVER existed) from an already-fixed one (content existed, removed in a later commit). Use when: (1) an audit/auto-generated issue cites file:line coordinates and quoted offending strings, (2) the offending token is a common English word (done/todo/fix) that could be benign prose, (3) you are tempted to write a 'Files to Modify' section before grepping, (4) deciding whether to close an issue as non-reproducible."
category: documentation
date: 2026-06-19
version: "1.0.0"
user-invocable: false
verification: verified-local
tags:
  - audit-finding
  - non-reproducible
  - premise-verification
  - line-number-drift
  - git-log-pickaxe
  - planning-methodology
  - close-as-cannot-reproduce
  - token-vs-status-value
  - stale-finding
---

# Verify an Audit Issue Reproduces Before Fixing

## Overview

| Field | Value |
|-------|-------|
| **Date** | 2026-06-19 |
| **Objective** | Before planning a fix for an audit-filed issue, prove the finding actually reproduces against the live working tree — rather than trusting the issue's cited line numbers and quoted strings as facts |
| **Outcome** | A repeatable planning discipline: run repro greps + `git log -S` during planning; for issue #26 the outcome was correctly "non-reproducible, recommend closing — no edit" because the cited content never existed in the file or its history |
| **Verification** | verified-local |

Verified locally only — CI validation pending. The greps, `awk` line dumps, and `git log -S`
pickaxe searches documented below were actually executed against the live working tree this
session and their outputs confirmed the finding did not reproduce. No CI ran, and the cross-repo
assumptions in Results & Parameters (submodule pin freshness, the Agamemnon canonical status set,
and whether the audit targeted a different/old path) remain unverified.

## When to Use

- An audit or auto-generated issue cites `file:line` coordinates **and** quotes specific offending
  strings (e.g. "lines 7/14/16 use `done`/`todo` instead of `completed`/`pending`").
- You are about to write a "Files to Modify" section based on the issue body without having opened
  the file yet.
- The offending token is a common English word (`done`, `todo`, `fix`, `wip`) that can legitimately
  appear in prose/comments, so a raw grep hit is not proof of a real defect.
- You need to decide between "this is a stale finding that never existed" vs "this was already fixed
  in a later commit" vs "the finding genuinely holds."
- The issue may have targeted a **different file**, an old fork/path, or a stale submodule pin that
  no longer maps to the current file.

## Verified Workflow

### Quick Reference

```bash
# 1. Whole-file scan for the offending tokens (NOT just the cited lines).
#    Audit line numbers drift or are entirely wrong — scan the whole file.
grep -niE '\b(done|todo)\b' README.md            # expect: NO MATCHES if non-reproducible

# 2. Dump the ACTUAL content of the cited lines to see what is really there.
awk 'NR>=1&&NR<=20{printf "%d: %s\n",NR,$0}' README.md

# 3. Pickaxe the file HISTORY — did the cited content EVER exist?
#    Empty in BOTH directions => never existed (stale finding), not "fixed later".
git log --oneline -S'marked done' -- README.md   # expect: EMPTY
git log -S'todo' -- README.md                     # expect: EMPTY

# 4. Confirm what the REAL canonical values are in the actual source of truth.
grep -niE 'completed|pending|in_progress|backlog|review' src/keystone/models.py
#   e.g. TERMINAL_STATUSES = frozenset({"completed","failed","error","cancelled"})  (models.py:9)

# 5. Disambiguate common-English-word hits from real status-value misuse.
#    "all neighbors done" / "removed when done" are PROSE, not a status value.
grep -niE '\b(done|todo)\b' src/keystone/*.py    # then read each hit IN CONTEXT
```

### Detailed Steps

1. **Scan the whole file, never only the cited lines.** Audit line numbers drift or are simply
   wrong. Run `grep -niE '\b(token)\b' <file>` over the entire file. In issue #26 the audit claimed
   `ProjectKeystone/README.md` lines 7/14/16 used `done`/`todo`; the whole-file grep returned
   **zero matches**. Lines 7/14/16 were actually a blank line, a `## Overview` heading, and a
   project-description sentence in a 435-line C++20 HMAS document — none mentioning task status.

2. **Dump the actual cited-line content.** Use `awk 'NR>=A&&NR<=B{printf "%d: %s\n",NR,$0}' <file>`
   (or `sed -n 'A,Bp'`) to print exactly what lives at the cited coordinates. This converts the
   audit's claim into an observation. If the lines contain nothing resembling the quoted strings,
   the finding does not reproduce.

3. **Pickaxe the history with `git log -S` — in BOTH directions of interpretation.** This is the
   decisive diagnostic that distinguishes two very different situations:
   - `git log -S'<quoted string>' -- <file>` returns **empty** → the content NEVER existed in this
     file's history → the finding is **stale/fabricated**, recommend closing as non-reproducible.
   - `git log -S'<quoted string>' -- <file>` returns a **commit** → the content existed and was
     removed/changed in a later commit → the finding was **already fixed** (different skill:
     `stale-plan-already-resolved`).

     For issue #26 BOTH `git log --oneline -S'marked done' -- README.md` and
     `git log -S'todo' -- README.md` were empty — ruling out "already fixed in a later commit" too.

4. **Confirm the real canonical values from the actual source of truth.** Do not assume the audit's
   "should be X" is correct either. Grep the real model/source:
   `grep -niE 'completed|pending|in_progress|backlog|review' src/keystone/models.py` confirmed the
   canonical statuses (`TERMINAL_STATUSES = frozenset({"completed","failed","error","cancelled"})`
   at `models.py:9`) — i.e. the real source already uses canonical values.

5. **Disambiguate token-as-English-word from token-as-status-value.** When the offending token is a
   common word, a raw grep hit is not proof. For issue #26 the only `done` hits in
   `src/keystone/*.py` were ordinary English in comments ("all neighbors done", "removed when done")
   — NOT status-value misuse. Read each hit in context before concluding.

6. **Write the conclusion the evidence supports — including "no edit."** A legitimate planning
   outcome is "non-reproducible; recommend closing." Do not author a "Files to Modify" section to
   satisfy a template when the finding does not reproduce. Cite the exact commands and their empty
   outputs so a reviewer can re-run them.

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
|---------|----------------|---------------|----------------|
| Trust the audit's cited lines 7/14/16 as fact | Was about to plan edits at the quoted coordinates | Those lines were a blank line, a `## Overview` heading, and a description sentence — none mentioned task status | Treat audit line numbers and quoted strings as claims; open and grep the live file first |
| Grep only the cited lines | Would have checked just lines 7/14/16 for `done`/`todo` | Audit line numbers drift or are wrong; a narrow check can miss real hits OR confirm a phantom | Scan the WHOLE file (and history), never only the cited line numbers |
| Assume "not present now" means "already fixed in a later commit" | Considered closing as already-resolved | `git log -S'marked done'` and `git log -S'todo'` were BOTH empty — the content never existed; "already fixed" was the wrong conclusion | Use `git log -S` to check whether cited content EVER existed; empty = stale finding, not already-fixed |
| Treat every `done`/`todo` grep hit as a status-value defect | Grepped `src/keystone/*.py` for `done`/`todo` and saw hits | The hits were ordinary English in comments ("all neighbors done", "removed when done"), not status values | When the token is a common English word, filter benign prose/comment hits from real status-value misuse before concluding |
| Author a "Files to Modify" section to fit the plan template | Felt obligated to produce edits for the issue | The finding did not reproduce; any edit would be fabricated | A legitimate planning outcome is "no edit; recommend closing as non-reproducible" — run the repro greps BEFORE writing any fix section |

## Results & Parameters

Concrete facts from the issue #26 planning session (ProjectKeystone `README.md`):

| Parameter | Value |
|-----------|-------|
| Whole-file token scan | `grep -niE '\b(done\|todo)\b' README.md` → **NO MATCHES** |
| Cited-line dump | `awk 'NR>=1&&NR<=20{printf "%d: %s\n",NR,$0}' README.md` → line 7 blank, line 14 `## Overview`, line 16 a description sentence |
| History pickaxe (decisive) | `git log --oneline -S'marked done' -- README.md` → **EMPTY**; `git log -S'todo' -- README.md` → **EMPTY** (content never existed) |
| Canonical statuses (real source) | `grep -niE 'completed\|pending\|in_progress\|backlog\|review' src/keystone/models.py` → `TERMINAL_STATUSES = frozenset({"completed","failed","error","cancelled"})` at `models.py:9` |
| Benign token hits | only `done` in `src/keystone/*.py` comments: "all neighbors done", "removed when done" — prose, not status values |
| README reality | 435-line C++20 HMAS document; cited lines 7/14/16 unrelated to task status |
| Conclusion | **Non-reproducible** — recommend closing issue #26; no file edit |
| Verification level | verified-local (greps + git-log executed and confirmed this session; no CI) |

### Decision tree

```
Audit issue cites file:line + quoted offending string
│
├─ 1. grep -niE '\b(token)\b' <whole file>
│   ├─ NO matches → likely non-reproducible → go to 2
│   └─ matches → read in context (token = status value, or just English?) → go to 4
│
├─ 2. git log -S'<quoted string>' -- <file>
│   ├─ EMPTY → content NEVER existed → STALE finding → close as non-reproducible
│   └─ commit found → content existed, removed later → ALREADY FIXED
│       └─ (use skill: stale-plan-already-resolved)
│
├─ 3. Confirm real canonical values in the actual source of truth (don't trust the
│      audit's "should be X" either): grep the model/source file.
│
└─ 4. Token = common English word?
    ├─ yes → filter benign prose/comment hits from real status-value misuse
    └─ no  → a hit is strong evidence the finding reproduces
```

### Risks for the plan reviewer (most uncertain assumptions)

- **Audit may have targeted a DIFFERENT file/path.** The plan assumed the audit's premise was simply
  wrong. Not fully excluded: the audit may have targeted an OLD fork/path (e.g. an ai-maestro-era
  README) that no longer maps to this submodule's current README. The plan relied on the issue's own
  file path (`README.md`) being the intended target.
- **Submodule pin may be stale.** Inspection relied on the submodule being pinned at the correct
  integration SHA (detached HEAD `3185bc9`). If Odysseus's pin is stale, the "live file" inspected
  may differ from a fresh clone of ProjectKeystone `main`. The plan did NOT independently fetch and
  compare ProjectKeystone's `main` tip — do that before final close.
- **Canonical status set was taken as given.** The ProjectAgamemnon REST API canonical set
  (`backlog, pending, in_progress, review, completed`) came from the issue body + Prior Learnings,
  NOT verified against the actual Agamemnon API contract/source. Re-verify against source if the
  close decision hinges on it.
