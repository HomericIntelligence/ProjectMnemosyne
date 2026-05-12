---
name: modular-6433-vs-6413-failure-triage
description: "Distinguish modular#6433 (OOM, fixed) from modular#6413 (libKGEN JIT crash, open) when verifying upstream fixes. Use when: (1) removing a #6433 workaround, (2) CI fails after upgrading Mojo nightly, (3) deciding whether to revert a fix-verification PR."
category: ci-cd
date: 2026-05-11
version: "1.0.0"
verification: verified-ci
user-invocable: false
tags: []
---

# Triage: modular#6433 (OOM, Fixed) vs modular#6413 (libKGEN JIT, Open)

## Overview

| Field | Value |
| ------- | ------- |
| **Date** | 2026-05-11 |
| **Objective** | When CI fails after removing a `modular#6433` workaround (or after a Mojo nightly bump), classify each failed job as #6433 (OOM, fixed upstream) or #6413 (libKGEN JIT crash, still open) before deciding whether to revert. |
| **Outcome** | Bash triage script + decision matrix that maps log signature → action. Correctly classified all 7 failed jobs on HomericIntelligence/ProjectOdyssey PR #5381 as #6413 (no revert needed). |
| **Verification** | verified-ci (used to verify PR #5381; classification matched the eventual upstream-triage outcome) |

## When to Use

- You are removing a `modular#6433` workaround and want to verify the upstream fix actually holds in CI.
- CI fails after upgrading the pinned Mojo nightly version and you need to know whether the regression is #6433 or a different bug.
- You are deciding whether to revert a fix-verification PR based on red CI.

## The Two Failure Signatures

| Aspect | modular#6433 (OOM) | modular#6413 (libKGEN JIT) |
| --- | --- | --- |
| **Status** | FIXED in `1.0.0b2.dev2026050805` ([modular@99c4bfc9d6](https://github.com/modular/modular/commit/99c4bfc9d6b6fbe0c793cea766c7da504a6609a0)) | OPEN as of 2026-05-11 |
| **Root cause** | Mojo compiler reserved ~3.6 GB virtual address space per invocation; parallel jobs blew the 7 GB GHA runner | JIT code-generator crash inside `libKGENCompilerRTShared.so` |
| **Exit code** | 137 (SIGKILL/OOM-killer) or 124 (timeout) | Often 137 too (in-process signal handler) — exit code is **not** a discriminator |
| **Log signature** | `Killed`, `out of memory`, `cannot allocate`, `virtual address`, `mmap.*failed`, `MAP_PRIVATE.*fail` | Stack frame `libKGENCompilerRTShared.so+0x6ef7b` / `+0x6c156` / `+0x6fc27` (offsets are for `1.0.0b2.dev2026050805`); `mojo: error: execution crashed` |
| **Behavior** | Whole job dies mid-compilation; not test-specific; reproducible | Hits specific tests that compile fine but crash during JIT execution; non-deterministic; partial test output before crash |
| **Captured by** | Standard CI logs | `coredump-capture` GHA artifact in addition to logs |

## Verified Workflow

### Quick Reference

```bash
# After CI fails on a fix-verification PR, classify each failed job.
JOB_IDS=$(gh pr view <PR> --json statusCheckRollup | python3 -c "
import sys, json
for c in (json.load(sys.stdin).get('statusCheckRollup') or []):
    if c.get('conclusion') == 'FAILURE':
        print(c.get('detailsUrl','?').rsplit('/job/',1)[-1])")

for id in $JOB_IDS; do
  echo "=== job $id ==="
  HITS=$(gh run view --job=$id --log 2>&1 \
    | grep -iE "Killed|OOM-killer|out of memory|virtual address|mmap.*failed|cannot allocate" \
    | grep -vE "TCMalloc|echo|# " | head -3)
  if [ -n "$HITS" ]; then
    echo "OOM EVIDENCE — modular#6433 fix may NOT be working — investigate"
    echo "$HITS"
  else
    LIBKGEN=$(gh run view --job=$id --log 2>&1 \
      | grep -E "libKGENCompilerRTShared.so\+0x[0-9a-f]+" | head -1)
    if [ -n "$LIBKGEN" ]; then
      echo "libKGEN trace — modular#6413 (separate bug) — no revert needed"
      echo "$LIBKGEN"
    else
      echo "Unknown signature — needs manual inspection"
    fi
  fi
done
```

### Detailed Steps

1. **Rebase the verification PR onto current `origin/main`** so you are testing the latest pinned Mojo version, not a stale snapshot.
2. **Push and wait for CI.** If everything is green, the upstream fix is confirmed — ship it.
3. **For each failed job, run the triage script above.** Pipe `gh run view --job=$id --log` through OOM-keyword grep first, then through the `libKGENCompilerRTShared.so+0x` regex.
4. **Read the upstream commit message literally.** Confirm it describes the exact symptom you observed (OOM mid-compilation), not just adjacent symptoms (general memory pressure, generic compiler crash).
5. **Cross-reference with `coredump-capture` artifacts.** A captured coredump strongly suggests #6413, since #6433 produces a clean SIGKILL with no usable core.
6. **Consult the decision matrix below** before taking any action (revert, ship, escalate).

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
| --- | --- | --- | --- |
| Treat all failures as fix-not-working | Assumed all 7 red jobs on PR #5381 meant `modular#6433` was unfixed; was about to recommend reverting the workaround removal | Failures were actually `modular#6413` — a separate, pre-existing bug; reverting would have lost a valid cleanup | Read the PR's "What to watch for" table literally; failures can be a separate bug, not the one you were testing |
| Use `grep -i "fail"` to classify | Counted "fail"-keyword matches in each job log to bucket failures | Too broad — matched both signatures and most ordinary CI lines (e.g., `fail-fast: false`) | Use signature-specific keywords (`Killed`, `out of memory`, `virtual address`) for OOM, and address-specific patterns (`libKGENCompilerRTShared.so+0x`) for libKGEN |
| Classify by exit code alone | Assumed `137` == SIGKILL == OOM-killer, therefore #6433 | Many libKGEN crashes also exit 137 because the in-process signal handler kills the process | Combine exit code with log signature; the log signature beats the exit code |
| Mix up `modular#6187` with `modular#6413` | Cross-references between #6187 and #6413 were inconsistent in older ADRs; treated them as the same issue | Wasted time chasing the wrong upstream issue; status, fix commit, and offset list differed | Verify the upstream commit message and issue title match the symptom you actually observed, not just an adjacent symptom |

## Results & Parameters

| Signal | Means | Action |
| --- | --- | --- |
| OOM kill, no libKGEN trace | `modular#6433` is NOT actually fixed in the pinned nightly | Revert the workaround removal; file follow-up on upstream issue |
| libKGEN signal trace, no OOM | `modular#6413` (separate bug, still open) | Keep the change; file a separate `mojo-jit-crash-retry`-style bug if needed |
| All jobs green | Both workarounds truly unnecessary | Ship it |
| Mixed (some OOM, some libKGEN) | `modular#6433` only partially fixed | Investigate before reverting; may need to keep workaround for a subset of jobs |
| Unknown signature | Neither pattern matches | Escalate; do not auto-revert and do not auto-ship |

## Verified On

Used to verify `HomericIntelligence/ProjectOdyssey` PR #5381 (commit `9c13d83812`). Result:
7 failed jobs, zero OOM signatures, all libKGEN traces at consistent offsets
`+0x6ef7b` / `+0x6c156` / `+0x6fc27`. Conclusion: `modular#6433` fix confirmed
working; failures attributable to `modular#6413` (separate, pre-existing bug);
no revert needed.
