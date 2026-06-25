---
name: verify-audit-issue-reproduces-before-fixing
description: "When an audit issue's cited content is ABSENT from the current file, do NOT conclude 'never existed / non-reproducible' until you have searched the CORRECT refs (live origin/main, not a stale pin) with the EXACT audited strings across `git log --all`. Content may have existed and been REMOVED — and the disposition 'already-resolved, provenance commit X' is materially different and better than 'phantom finding.' Use `git merge-base --is-ancestor` to distinguish removal-by-a-main-lineage-commit from an orphaned/abandoned lineage. Use when: (1) an audit/auto-generated issue cites file:line + quoted offending strings that are not in the file now, (2) you inspected a submodule pin / detached HEAD instead of origin/main, (3) your `git log -S` came back empty and you are tempted to call the finding phantom, (4) deciding how to close an audit issue."
category: documentation
date: 2026-06-19
version: "2.0.0"
user-invocable: false
verification: verified-local
history: verify-audit-issue-reproduces-before-fixing.history
tags:
  - audit-finding
  - already-resolved
  - provenance-commit
  - premise-verification
  - git-log-pickaxe-all
  - git-merge-base-ancestry
  - stale-submodule-pin
  - live-tip-inspection
  - orphaned-lineage
  - history-replacement
  - planning-methodology
---

# Verify an Audit Issue Reproduces Before Fixing

## Overview

| Field | Value |
|-------|-------|
| **Date** | 2026-06-19 |
| **Objective** | Before planning a fix for (or closing) an audit-filed issue, determine whether the cited content is genuinely a phantom or whether it EXISTED and was removed — by searching the correct refs (`origin/main`, full `--all` history) with the exact audited strings, and classifying the removal mechanism |
| **Outcome** | A repeatable planning discipline. For issue #26 the corrected outcome was **already-resolved, citing provenance commit `a3878c3`** — the audit was ACCURATE at filing; the terminology existed and was removed by history replacement. This OVERTURNS the v1.0.0 conclusion of "non-reproducible / never existed" |
| **Verification** | verified-local |
| **History** | [changelog](./verify-audit-issue-reproduces-before-fixing.history) |

**Verified locally only — CI validation pending.** Every git command in the Verified Workflow
(`git fetch`, `git show origin/main:README.md`, `git rev-list --count <pin>..origin/main`,
`git log --all -S`, `git show <sha>:README.md`, `git merge-base --is-ancestor`) was actually executed
against the live working tree + freshly fetched origin this session and the outputs confirmed the
corrected disposition. No CI ran. Two assumptions remain unverified (see Risks): the canonical status
set was taken from the issue body (not the live Agamemnon API contract), and the "removed per ADR-006
re-scope" causal story is INFERRED from lineage + content, not from a single attributable diff
(because the lineages are disjoint).

## When to Use

- An audit or auto-generated issue cites `file:line` coordinates **and** quotes specific offending
  strings, but those strings are **not present in the file you are looking at now**.
- You inspected a **submodule pin / detached HEAD** (or any non-`origin/main` ref) and are about to
  conclude the finding is phantom — you have not yet checked the LIVE tip.
- Your first `git log -S'...'` came back **empty** and you are tempted to write "never existed /
  non-reproducible." (This is exactly how v1.0.0 of this skill got it WRONG.)
- The offending token is a common English word (`done`, `todo`, `fix`, `wip`) that can appear in
  prose, so you must search the EXACT audited substring (including backticks), not a loose word.
- You need to decide between "phantom finding," "already-resolved (existed, then removed)," and
  "finding genuinely holds — needs a fix."

## Verified Workflow

**Headline: when audited content is absent, search the CORRECT refs (`origin/main`, `--all`) with the
EXACT audited strings BEFORE concluding "never existed." Content that existed-then-was-removed closes
as "already-resolved, provenance commit X" — a materially different and better disposition than
"phantom finding." Use `git merge-base --is-ancestor` to tell removal-on-the-main-lineage apart from
an orphaned/abandoned lineage.**

### Quick Reference

```bash
# 0. Fetch and inspect the LIVE tip, not the pinned/detached SHA you happen to be on.
git fetch origin
git show origin/main:README.md | grep -niE '\b(done|todo)\b'   # what is canonical NOW

# 1. Quantify how stale the pin you first inspected is (don't trust a detached HEAD).
git rev-list --count <pin-sha>..origin/main                    # e.g. 37 commits behind

# 2. Pickaxe the FULL history with the EXACT audited substring (note --all, not just HEAD).
#    Use the real backtick-wrapped strings, not loose words.
git log --all --oneline -S'is `done`'   -- README.md           # finds where it EXISTED
git log --all --oneline -S'still `todo`' -- README.md
git log --all --oneline -S'marked done' -- README.md

# 3. Confirm the EXACT cited lines in the commit that contained them.
git show <found-sha>:README.md | awk 'NR==7||NR==14||NR==16{printf "%d: %s\n",NR,$0}'

# 4. Classify the removal mechanism: linear edit on main vs orphaned/abandoned lineage.
git merge-base --is-ancestor <found-sha> origin/main \
  && echo "ancestor → removed by a commit ON the main lineage" \
  || echo "NOT ancestor → orphaned/abandoned lineage (history replacement)"

# 5. (only if classifying as still-broken) confirm the real canonical values in source of truth.
grep -niE 'completed|pending|in_progress|backlog|review' src/keystone/models.py
```

### Detailed Steps

1. **Fetch and inspect the LIVE tip — never just the pin you landed on.** A submodule pin or detached
   HEAD can be many commits behind. In issue #26 the pin first inspected (`3185bc9`) was **37 commits
   behind** `origin/main` (`git rev-list --count 3185bc9..origin/main` → 37). Always
   `git fetch origin` and inspect `git show origin/main:README.md` before judging "what the file
   says now."

2. **Quantify pin staleness explicitly.** `git rev-list --count <pin>..origin/main` turns "I think
   the pin is old" into a number. A non-trivial count means the file you inspected is NOT the live
   file, and any "non-reproducible" claim built on it is unsafe.

3. **Pickaxe the FULL history with the EXACT audited substring.** This is the step v1.0.0 botched.
   Two failure modes to avoid:
   - **Wrong refs:** a plain `git log -S` only searches the history reachable from your current
     (possibly stale, detached) HEAD. Use `git log --all -S'...'` so abandoned/orphaned lineages are
     searched too.
   - **Wrong string:** the audit quoted backtick-wrapped status values (``is `done` ``,
     ``still `todo` ``). Loose searches like `-S'marked done'` / `-S'todo'` UNDER-matched. Search the
     exact audited substring.

     For issue #26, searching the exact strings across `--all` FOUND commit `a3878c3`, which
     `git show a3878c3:README.md` proves contained the audit's exact strings at the exact cited lines:
     - L7: "When a task is marked done, Keystone traverses the DAG…"
     - L14: "When a task's status transitions to `done`, Keystone identifies the affected team."
     - L16: "Identifies tasks where every dependency is `done` and the task itself is still `todo`."

     So the audit was **ACCURATE at filing** — the content existed. Empty was a search artifact, not
     proof of absence.

4. **Confirm the exact cited lines in the commit that contained them.**
   `git show <found-sha>:README.md | awk 'NR==7||NR==14||NR==16'` converts "it existed somewhere" into
   "it existed at exactly the audited coordinates," which is what makes the provenance citation solid.

5. **Classify the removal mechanism with `git merge-base --is-ancestor`.** This distinguishes two very
   different removal stories:
   - `git merge-base --is-ancestor <found-sha> origin/main` → **true** → the content was removed by a
     commit ON the main lineage (a normal linear edit). The diff is attributable.
   - → **false** → the found commit is **NOT** on the main lineage; the terminology was removed by
     **history replacement** — the old lineage was abandoned and `origin/main` descends from a
     different root.

     For issue #26 it returned **false**: `a3878c3` is not an ancestor of `origin/main`, which
     descends from a different root `2e9f216` ("Initial commit"). The ai-maestro scaffold lineage was
     abandoned when ProjectKeystone was re-scoped to a C++ transport library (per ADR-006). There is
     therefore NO single attributable diff that removed the terminology — the lineages are disjoint.

6. **Write the disposition the evidence supports — prefer provenance over phantom.** When content
   existed and was removed, close as **already-resolved, citing the provenance commit** (here
   `a3878c3`). This CONFIRMS the audit tooling was correct, rather than wrongly signaling a phantom
   finding and eroding trust in the audit. Cite the exact commands and SHAs so a reviewer can re-run
   them. Only if the live `origin/main` STILL contains the offending strings do you proceed to plan an
   actual edit (step 5 of Quick Reference confirms the canonical values).

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
|---------|----------------|---------------|----------------|
| Misread an empty `git log -S` as "content never existed" | Ran `git log -S'marked done'` / `-S'todo'` and got no results, then concluded the finding was phantom / non-reproducible (this was v1.0.0's core, later-overturned claim) | The searches (a) ran only on a stale detached-pin's reachable history — not `--all`, not `origin/main` — and (b) used loose phrasings, not the actual backtick-wrapped strings (``is `done` ``, ``still `todo` ``). The exact strings DID exist, in commit `a3878c3` | Empty `-S` output is NOT proof of absence. Search `git log --all -S'<exact substring>'`, inspect candidates with `git show <sha>:README.md`, and check ancestry with `git merge-base --is-ancestor` before ever saying "never existed" |
| Inspected the stale submodule pin instead of the live tip | Judged "what the file says now" from the detached pin `3185bc9` | `3185bc9` was **37 commits behind** `origin/main` (`git rev-list --count 3185bc9..origin/main` → 37); the pinned file was not the live file | Always `git fetch origin` and inspect `git show origin/main:README.md`; quantify pin staleness with `git rev-list --count <pin>..origin/main` |
| Assumed "absent now" implies "phantom / never existed" | Jumped to a non-reproducible close once the strings were not in the current file | The strings existed historically (`a3878c3`); absent-now means removed, not phantom. "Already-resolved, provenance commit X" is the correct and better disposition | Distinguish existed-then-removed from never-existed; the former closes with provenance, confirming the audit was right |
| Trusted a plain `git log -S` to cover all history | Searched only HEAD-reachable history | A detached/stale HEAD does not reach abandoned/orphaned lineages where the content may live | Use `git log --all -S` so orphaned lineages (history replacement) are searched |
| Assumed any removal is a linear edit on main | Looked for "the commit that removed it" expecting an attributable diff | `a3878c3` is NOT an ancestor of `origin/main` (different root `2e9f216`); removal was by history replacement (re-scope per ADR-006), so no single diff removed it | Use `git merge-base --is-ancestor <sha> origin/main` to tell removal-on-main from orphaned/abandoned lineage |

## Results & Parameters

Corrected facts from the issue #26 planning session (ProjectKeystone `README.md`,
`done`/`todo` vs canonical `completed`/`pending`):

| Parameter | Value |
|-----------|-------|
| Live-tip inspection | `git fetch origin` then `git show origin/main:README.md \| grep -niE '\b(done\|todo)\b'` → canonical terminology now (no audited strings) |
| Pin staleness | `git rev-list --count 3185bc9..origin/main` → **37** (pin first inspected was 37 commits behind) |
| History pickaxe (decisive) | `git log --all --oneline -S'is \`done\`' -- README.md` and `-S'still \`todo\`'` → **FOUND commit `a3878c3`** (exact audited strings existed) |
| Provenance commit | `git show a3878c3:README.md` → L7 "marked done … traverses the DAG", L14 "transitions to `done`", L16 "every dependency is `done` … still `todo`" — exact cited lines 7/14/16 |
| Removal mechanism | `git merge-base --is-ancestor a3878c3 origin/main` → **false (NOT ancestor)**; `origin/main` descends from different root `2e9f216` ("Initial commit") → history replacement, not linear edit |
| Causal story (inferred) | ai-maestro scaffold lineage abandoned when ProjectKeystone re-scoped to a C++ transport library (per ADR-006); no single attributable diff (disjoint lineages) |
| Canonical statuses | `backlog/pending/in_progress/review/completed` — from issue body, NOT verified against live Agamemnon API contract |
| Audit accuracy | **ACCURATE at filing** — content existed at the cited coordinates in `a3878c3` |
| Conclusion | **Already-resolved** — close issue #26 citing provenance commit `a3878c3`; no file edit (live tip already canonical) |
| Verification level | verified-local (all git commands above executed against live tree + fetched origin this session; no CI) |

### Decision tree

```
Audit issue cites file:line + quoted offending string, but string is ABSENT from the file now
│
├─ 0. git fetch origin; inspect git show origin/main:README.md (the LIVE tip)
│   ├─ string STILL present on origin/main → finding HOLDS → plan a real fix
│   └─ string absent on origin/main → go to 1
│
├─ 1. Was the ref you first inspected a stale pin?
│      git rev-list --count <pin>..origin/main  (non-zero ⇒ inspected the wrong file)
│
├─ 2. git log --all -S'<EXACT audited substring incl. backticks>' -- <file>
│   ├─ EMPTY (and you used --all + exact string) → genuinely never existed → phantom
│   └─ commit <sha> found → content EXISTED → confirm with git show <sha>:file → go to 3
│
├─ 3. git merge-base --is-ancestor <sha> origin/main
│   ├─ ancestor → removed by a commit ON main (attributable linear edit)
│   └─ NOT ancestor → orphaned/abandoned lineage (history replacement); no single diff
│
└─ 4. Disposition: CLOSE as already-resolved, citing provenance commit <sha>.
       (Confirms the audit was correct — better than signalling a phantom finding.)
```

### Risks for the plan reviewer (most uncertain assumptions)

- **Canonical status set not verified against the live API.** The set
  (`backlog/pending/in_progress/review/completed`) was taken from the issue body, NOT checked against
  the live ProjectAgamemnon API contract/source. This has **zero impact** when the disposition is a
  no-op already-resolved close, but flag it — if a future close hinges on the canonical set, verify it.
- **Causal "removed per ADR-006 re-scope" story is inferred, not attributed.** Because the
  ai-maestro-scaffold lineage and `origin/main` are **disjoint** (different roots), there is no single
  diff that removed the terminology. The re-scope explanation is inferred from the lineage split plus
  the README content change, not read from one attributable commit. Present it as inference, not fact.
