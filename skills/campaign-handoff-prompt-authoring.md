---
name: campaign-handoff-prompt-authoring
description: "Teaches the required anatomy of a single self-contained cross-machine resume prompt that hands a strictly-serial multi-PR epic campaign to a fresh session with no access to the prior transcript. Use when: (1) a long-running serial epic driven one PR at a time must move to another machine or operator, (2) context compaction is about to destroy the working memory that keeps a serial campaign safe and you need a compaction-survival brief, (3) you must restate a session Stop-hook completion condition, the in-flight PR's per-thread REAL/FALSE-POSITIVE classification, and the serial issue ordering so the receiving session neither redoes finished work nor picks up two dependent issues at once."
category: tooling
date: 2026-07-05
version: "1.0.0"
user-invocable: false
verification: verified-local
tags:
  - handoff
  - resume-prompt
  - cross-machine
  - serial-campaign
  - epic
  - context-compaction
  - operator-continuity
---

# Campaign Handoff Prompt Authoring

## Overview

| Field | Value |
|-------|-------|
| **Date** | 2026-07-05 |
| **Objective** | Write a single self-contained resume prompt that lets a fresh session (no prior transcript) pick up a strictly-serial multi-PR epic campaign mid-flight without re-deriving anything. |
| **Outcome** | Prompt authored and delivered this session (epic #1809 got a status comment; the handoff prompt was handed to the operator). Not yet executed end-to-end on the second machine. |
| **Verification** | verified-local |

## When to Use

- A long-running serial epic (e.g. ProjectHephaestus epic #1809 — a queue-based automation-pipeline rewrite delivered as ~14 strictly-serialized sub-issues #1810→#1823, each `Depends on #prev`) is being driven one PR at a time on one machine and the operator asks to move the work to another machine.
- Context compaction is about to wipe the working memory that makes a serial campaign safe — the same prompt shape doubles as a compaction-survival brief.
- You need the receiving session to continue without: (a) re-reading and re-classifying the in-flight PR's review threads, (b) losing the completion condition that a session-scoped Stop hook was enforcing, or (c) picking up two dependent issues at once (mutual-conflict strand).

## Verified Workflow

A good cross-machine handoff prompt for a serial multi-PR campaign MUST contain, **in order**, the seven parts below. The prompt is the ONLY channel — the transcript, the Stop hook, and any local plan files do NOT travel to the other machine.

### Quick Reference

```text
1. GOAL (verbatim) + explicit completion condition
   e.g. "each sub-issue passes /review-pr-strict AND the whole repo
   passes /repo-analyze-strict-full" — the receiving session's Stop
   hook won't exist unless re-established, so STATE it.

2. BINDING SPEC pointers (durable in-repo artifacts, never the transcript)
   e.g. epic body + docs/AUTOMATION_LOOP_ARCHITECTURE.md + the ADR.

3. STATE snapshot
   - which issues are MERGED vs OPEN
   - for the single in-flight PR: branch name, commit count, CI status,
     mergeStateStatus, and EACH unresolved review thread individually
     classified REAL (with the fix) or FALSE-POSITIVE (with the refutation)
   e.g. "PR #1851: 5 unresolved bot threads: 2 real (__all__ export not
   defined → add names), 1 real (dup assignment → dedupe), 2 false-positive
   (Protocol `...` → refute)"

4. NEXT STEPS strictly serialized + per-issue gate sequence + special
   evidence requirements
   e.g. cutover issue #1818 merges ONLY with live-drive evidence: dry-run
   classification, shadow diff, scoped live drive through merge, Ctrl-C
   interrupt/resume drill.

5. STANDING CONSTRAINTS that must survive the machine switch
   signed -S + DCO -s commits; squash-only; literal `Closes #N`;
   never --no-verify; auto-merge only after state:implementation-go;
   temp files in build/; never delete Mnemosyne; run /learn after work.

6. POINTER to the execution-playbook memory (do NOT inline every recovery
   pattern) — the memory travels with the account; name it + summarize
   the failure modes it covers.
   e.g. project_epic1809_execution_playbook.md covers: loop-commit-fails
   recovery, DCO commit-tree v2 branch-swap, dependency-parser false-positive
   rewording, big-PR delta verification, required-checks-gate
   rerun-the-failed-run, operator-GO churn path.

7. FIRST-ACTION reminder: `pgrep -af hephaestus.automation` to catch
   orphan processes before starting.
```

### Detailed Steps

1. **Restate the GOAL verbatim, including the Stop-hook passing criteria.** A fresh session on another machine has no session-scoped Stop hook, so it will stop early unless the completion condition is written into the prompt body. For epic #1809 the condition was: each sub-issue passes `/review-pr-strict` AND the whole repo passes `/repo-analyze-strict-full`.
2. **Point at the BINDING SPEC as durable artifacts.** Name the exact files/issue bodies that are the contract — here the epic body + `docs/AUTOMATION_LOOP_ARCHITECTURE.md` + the ADR. Never say "see the plan" or "as discussed"; the transcript and local `~/.claude/plans` files do not exist on the other machine.
3. **Give a STATE snapshot.** List which issues are MERGED vs OPEN. For the single in-flight PR, give branch name, commit count, CI status, `mergeStateStatus`, and — critically — classify EACH unresolved review thread individually as REAL (with the fix) or FALSE-POSITIVE (with the refutation). "PR #1851 needs review" is useless; the itemized classification is what saves the receiving session a full context window.
4. **Write NEXT STEPS strictly serialized** with the per-issue gate sequence and any special evidence requirements (e.g. the cutover issue merges only with live-drive evidence: dry-run classification, shadow diff, scoped live drive through merge, Ctrl-C interrupt/resume drill). Serial ordering in the prompt is what prevents the receiving session from opening two dependent issues at once and stranding them on mutual conflict.
5. **Enumerate STANDING CONSTRAINTS** that must survive the switch (see Quick Reference item 5).
6. **Point at the execution-playbook memory** rather than inlining every recovery pattern. Account-level memory travels with the account; the prompt only needs to name the file and summarize the failure modes it covers.
7. **End with the first-action reminder** `pgrep -af hephaestus.automation` to catch orphan automation processes before starting.

**Why it matters:** context compaction and machine switches both destroy the working memory that makes a serial campaign safe. The handoff prompt is the ONLY channel. If it omits the in-flight per-thread classification or the serial ordering, the receiving session either redoes finished work or picks up two dependent issues simultaneously and strands them.

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
|---------|----------------|---------------|----------------|
| Terse handoff | Wrote `continue epic #1809 from PR #1851` | Receiving session had to re-read the whole PR and re-classify every unresolved thread from scratch — wasted a full context window | Inline the per-thread REAL/FALSE-POSITIVE classification (with fix / refutation) directly in the prompt |
| Relied on the Stop hook | Assumed the "each issue passes /review-pr-strict AND repo passes /repo-analyze-strict-full" goal would carry over | A fresh session on another machine has no session-scoped Stop hook, so it would stop early after one PR | Restate the completion condition explicitly in the prompt body |
| Pointed at "the plan" | Referenced "the plan" without a path | The plan lived in a local `~/.claude/plans` file that does not exist on the other machine — dangling reference | Point only at durable in-repo artifacts (issue bodies, committed docs, the ADR) plus account-level memory files |

## Results & Parameters

Concrete instantiation for epic #1809 (copy-paste skeleton — replace the bracketed parts):

```text
GOAL: <verbatim epic goal>. Completion condition (Stop-hook equivalent):
every sub-issue passes /review-pr-strict AND the whole repo passes
/repo-analyze-strict-full. Do not stop until both hold for the last issue.

BINDING SPEC: the epic #1809 body, docs/AUTOMATION_LOOP_ARCHITECTURE.md,
and docs/adr/<n>-*.md. These are the contract — do not rely on any transcript.

STATE:
- MERGED: #1810..#<k> (verify on origin/main before trusting).
- OPEN in-flight: PR #1851 on branch <branch>, <n> commits, CI <status>,
  mergeStateStatus <status>. Unresolved threads:
    * <thread> — REAL — fix: <fix>
    * <thread> — REAL — fix: <fix>
    * <thread> — FALSE-POSITIVE — refute: <refutation>
- NOT STARTED: #<k+1>..#1823 (each Depends on #prev; do ONE at a time).

NEXT STEPS (strictly serial):
  1. Finish PR #1851: apply the 2 REAL fixes, refute the FALSE-POSITIVEs,
     get GO, arm auto-merge only after state:implementation-go, merge.
  2. Then #<k+1>: <gate sequence>.
  ...
  Special: cutover #1818 merges ONLY with live-drive evidence (dry-run
  classification, shadow diff, scoped live drive through merge, Ctrl-C
  interrupt/resume drill).

STANDING CONSTRAINTS: git commit -S -s (signed + DCO); squash-only;
literal `Closes #N`; never --no-verify; auto-merge only after
state:implementation-go; temp files in build/; never delete
Mnemosyne; run /learn after work.

PLAYBOOK: see memory project_epic1809_execution_playbook.md — covers
loop-commit-fails recovery, DCO commit-tree v2 branch-swap,
dependency-parser false-positive rewording, big-PR delta verification,
required-checks-gate rerun-the-failed-run, operator-GO churn path.

FIRST ACTION: run `pgrep -af hephaestus.automation` to catch orphan
processes before starting.
```

## Verified On

| Project | Context | Details |
|---------|---------|---------|
| ProjectHephaestus | Epic #1809 cross-machine handoff, 2026-07-05 session — prompt authored and delivered to operator; NOT yet executed end-to-end on the second machine (hence verified-local, not verified-ci) | epic #1809 body + project_epic1809_execution_playbook.md |
