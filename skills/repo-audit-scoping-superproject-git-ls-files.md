---
name: repo-audit-scoping-superproject-git-ls-files
description: "Scope a full-coverage repo audit correctly when the target is a git SUPERPROJECT (contains submodules). Use when: (1) running /repo-analyze-strict-full or any full-coverage audit on a meta-repo/superproject like Odysseus, (2) a naive `find . -type f` inventory returns tens of thousands of files (it descended into submodule working trees), (3) you must bucket the repo's OWN tracked files by section and swarm them without overflowing context, (4) the working tree is on a feature branch behind origin/main and you need to grade against the shipped state, (5) grading a coordination/meta-repo fairly (no product source, but configs/schema/e2e are still gradeable)."
category: testing
date: 2026-07-02
version: "1.0.0"
user-invocable: false
verification: verified-local
tags:
  - repo-audit
  - superproject
  - submodule
  - git-ls-files
  - gitlink
  - file-inventory
  - scoping
  - swarm
  - meta-repo
  - origin-main-crosscheck
---

# Repo Audit Scoping on a Git Superproject (git ls-files, not find)

## Overview

| Field | Value |
|-------|-------|
| **Date** | 2026-07-02 |
| **Objective** | Scope a full-coverage repo audit on a git SUPERPROJECT so only the repo's OWN files are audited — not the working trees of its submodules |
| **Outcome** | Success — `git ls-files` gave 246 real tracked files (a `find` inventory reported 31,006); 15-section read-only swarm dispatched in waves of ≤3; origin/main cross-check on a 7-behind branch caught 2 false findings |
| **Verification** | verified-local — the audit ran end-to-end this session and the file-count/methodology was confirmed live, but there is no CI gate on an audit report, so verified-local (NOT verified-ci) |
| **Category** | testing |

---

## When to Use

Apply this when you are about to run a full-coverage audit (e.g. `/repo-analyze-strict-full`) and the target repo is a **git superproject** — it references other repos as submodules (a `.gitmodules` file, or `git ls-files --stage` entries with mode `160000`). Odysseus is the canonical example: a coordination hub referencing 14 HomericIntelligence submodules, with no product source of its own.

Reach for it specifically when:

- A naive `find . -type f` file inventory returns tens of thousands of files and you suspect it walked into submodule working trees.
- You need to bucket the repo's own files by top-level section and fan them out to read-only swarm agents without blowing up scope or context.
- The working tree is on a feature branch that is behind `origin/main`, so files may look stale or missing versus what actually shipped.
- You are grading a meta-repo and want to avoid both grade-inflation and unfair F's on criteria (like "package publishing") that are legitimately N/A for a coordination hub.

This is the **scoping** trap. For the dispatch mechanics of the swarm see [[parallel-agent-swarm-dispatch-patterns]]; for the grading rubric see [[code-quality-audit-principles]].

**Don't use when**: the repo is an ordinary single-repo project with no submodules — there `git ls-files` and a pruned `find` agree, and there is no gitlink trap to avoid.

---

## Verified Workflow

### Quick Reference

```bash
# On a git SUPERPROJECT, inventory the repo's OWN files.
# Submodules appear as single gitlink entries (mode 160000), NOT their expanded contents.
git ls-files > /tmp/audit-files.txt; wc -l /tmp/audit-files.txt          # 246, not 31k
git ls-files --stage | awk '$1=="160000"{print $4}'                      # the submodule gitlink paths
git ls-files | awk -F/ '{print $1}' | sort | uniq -c | sort -rn          # bucket by top-level dir

# Stale-branch guard when auditing a feature branch behind main:
git fetch origin main -q
git show origin/main:path/to/file                                        # grade against shipped state
```

### Detailed steps

1. **Confirm it is a superproject.** Check for `.gitmodules`, or list gitlink entries:
   `git ls-files --stage | awk '$1=="160000"{print $4}'`. If this prints paths, each is a submodule that appears in the index as ONE entry, not as its contents.
2. **Inventory the repo's OWN files with `git ls-files`**, never `find`. In a superproject `git ls-files` lists only the superproject's tracked files (246 for Odysseus) and leaves each submodule as a single gitlink; `find . -type f` descends into all 14 submodule working trees and returns ~31,000 files (14 unrelated repos).
3. **Bucket by top-level section**: `git ls-files | awk -F/ '{print $1}' | sort | uniq -c | sort -rn`. Save the full file list to the scratchpad dir and pass its path to every agent so all agents share ONE inventory.
4. **Dispatch one read-only general-purpose sub-agent per audit section, in WAVES of ≤3 concurrent.** Even though audit agents are read-only and light, honor the hermes WSL ceiling (16 GB / 8 core) — see [[reference_wsl_overload_multiagent]] and [[debugging-wsl-host-hang-oom-forensic-diagnosis]]. Wait for each wave's task-notifications before launching the next wave.
5. **Each agent reads EVERY file in its bucket** (no sampling cap) and, if the branch is stale, cross-checks `git show origin/main:<path>` before recording a file as "missing" or "stale". Grade against origin/main (the shipped state), not the local branch.
6. **Grade meta-repo-fair.** Tell each agent the repo is a coordination hub with NO product source, so criteria like "package registry publishing" are justified N/A — but the NATS subject schema IS a gradeable contract, and `configs/`, install scripts, and `e2e/` ARE gradeable. Then synthesize a weighted overall grade from the section grades.

*Verified locally — no CI gate on audit output.*

---

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
|---------|----------------|---------------|----------------|
| Use `find` for the file inventory | `find . -type f -not -path '*/.git/*' ...` to enumerate files to audit | Descended into all 14 submodule working trees → 31,006 files (should be 246); would audit 14 other repos and overflow context | On a superproject use `git ls-files` (gitlinks stay single entries), never `find` |
| Hand-prune submodule paths from `find` | Added `-path ./sub -prune` for each submodule directory | Still returned ~24k files (missed nested `.git/modules` plus build/tests dirs); brittle and easy to get wrong | Don't hand-prune; `git ls-files` already excludes submodule contents and build artifacts correctly |
| Flag a file as "missing" from the local branch | An agent flagged `scripts/gen-ecosystem-table.sh` as "does not exist on disk" and recorded it as a gap | File was merged to `origin/main` but the audited branch was ~7 behind → false-negative | On a stale branch, cross-check `git show origin/main:<path>` before recording "missing"; grade against the shipped state |

---

## Results & Parameters

- **Odysseus**: 246 tracked files via `git ls-files` (a `find` inventory reported 31,006). Buckets: `e2e` 107, `docs` 33, `scripts` 23, `.github` 19, `configs` 11, `tests` 8, `tools` 7, root-meta 38. 14 submodule gitlinks (mode 160000).
- **Dispatch**: 15 audit sections, 5 waves of ≤3 concurrent read-only general-purpose agents, shared file list saved to a scratchpad path and passed to each agent.
- **Stale-branch guard**: working tree was on `fix/hermes-overload-throttle` (~7–9 commits behind `origin/main`); cross-checking `origin/main` caught 2 false findings (a generator present on main but not the branch, and per-PR CI jobs stripped locally but present on main).
- **Grading fairness**: meta-repo with no product source → "package registry publishing" scored N/A; NATS subject schema, `configs/`, install scripts, and `e2e/` treated as gradeable contracts.

---

## Verified On

| Repo / Context | Task | Result |
|----------------|------|--------|
| Odysseus (HI meta-repo) | `/repo-analyze-strict-full` full-coverage audit, 2026-07 | `git ls-files` → 246 files (find said 31,006); 15-section swarm in waves of 3; origin/main cross-check on a 7-behind branch caught 2 false findings |
