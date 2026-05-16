---
name: git-cherry-pick-dependent-commit-becomes-noop-when-prerequisite-dropped
description: "When salvaging commits from a rejected PR via cherry-pick, a commit's subject line can disguise the fact that it only operates on a separate commit you're dropping. The cherry-pick either conflicts or applies cleanly but introduces dead code (e.g. an EXTRA_ENV array with no env vars). Decision procedure: inspect the commit's actual diff (`git show <commit> -- <file>`); if every added line references the dropped feature, the commit is feature-scoped and should also be dropped — even if its subject describes a 'general' or 'compat' fix. Use when: (1) cherry-pick conflicts on a commit whose subject suggests general value, (2) the chain of commits has internal dependencies you're trying to break apart, (3) considering keeping a 'compat fix' or 'refactor' that operates only on lines you're dropping."
category: tooling
date: 2026-05-15
version: "1.0.0"
user-invocable: false
verification: verified-local
tags:
  - git
  - cherry-pick
  - rejected-pr
  - salvage
  - dependent-commits
  - dead-code
  - yagni
  - conflict-resolution
---

## Overview

| Field | Value |
| ------- | ------- |
| **Date** | 2026-05-15 |
| **Objective** | Salvage portable commits from a rejected PR without carrying forward dead-code scaffolding that only made sense in the presence of dropped commits |
| **Outcome** | Decision procedure: inspect the actual diff of any "general-sounding" commit; if every added line references the dropped feature, drop the commit too. Avoided committing an empty EXTRA_ENV array in ProjectOdyssey PR #5407. |
| **Verification** | verified-local (procedure-level learning; the resulting PR #5407 merged cleanly, supporting evidence) |

## When to Use

- A cherry-pick conflicts on a commit whose subject line suggests general/refactor/compat value
- You are breaking apart a chain of commits with internal dependencies (later commits modify lines earlier commits added)
- You are considering keeping a "compat fix" or "refactor" that — on inspection — operates only on lines tied to the feature you're dropping
- A cherry-pick applies cleanly but you suspect the result may be a no-op or dead code

## Verified Workflow

### Quick Reference: 4-step decision procedure

```bash
# 1. Inspect the conflicting commit's ORIGINAL diff (not the conflict markers)
git show <commit> -- <file>

# 2. Classify every ADDED line:
#    a) About the dropped feature?                          → feature-scoped → DROP
#    b) General mechanism operating on dropped feature data? → feature-scoped → DROP
#    c) General mechanism applied to UNRELATED lines?        → general      → KEEP (resolve conflict)

# 3. Re-read commit message body and original PR description.
#    If rationale explicitly cites the dropped feature, lean toward DROP.

# 4. Sanity check: cherry-pick --no-commit, manually strip dropped-feature lines,
#    then `git diff --cached`. Empty/trivial diff confirms no-op → DROP.
```

### Step 1: Identify the cherry-pick conflict

```bash
git cherry-pick <commit-sha>
# Conflict in <file>
```

### Step 2: Inspect the commit's ACTUAL diff (not the conflict markers)

```bash
git show <commit-sha> -- <conflicting-file>
```

Read every `+` line. The subject line is a hypothesis; the diff is the evidence.

### Step 3: Classify added lines (a/b/c above)

If **all** added lines fall under (a) or (b), the commit is feature-scoped, not general. Abort and drop.

### Step 4: Verify by no-op test if uncertain

```bash
git cherry-pick --abort
git cherry-pick --no-commit <commit-sha>   # if it applied cleanly originally
# Manually edit out the dropped-feature lines
git diff --cached
# If the remaining diff is empty or trivial, the commit is dead code → drop it
git reset --hard HEAD
```

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
| --- | --- | --- | --- |
| Judged commit by its subject line | "use explicit -e KEY=VAL (docker-compose compat)" sounded like a generic compat fix worth keeping | The compat fix only operated on the three gdb-specific env vars; without those, the new EXTRA_ENV machinery had nothing to do | Always inspect the *actual diff* (`git show <commit> -- <file>`), not the subject line, when deciding to cherry-pick |
| Resolved the conflict by keeping the new EXTRA_ENV array and removing gdb refs | First instinct: edit the merge conflict manually to drop just the gdb lines | Would have committed an EXTRA_ENV array with no env vars ever added to it — dead code that confuses future readers | If the post-strip diff is empty or near-empty, the commit is feature-scoped — abort and drop it |
| Cherry-picked both commits then planned to "fix later" | Argued for keeping the compat fix as future-proofing for adding more env vars | YAGNI violation: now there's a placeholder EXTRA_ENV array that pretends to be general but isn't tied to any real consumer; future PRs adding env vars don't know whether to use it or replicate it | Don't carry forward speculative scaffolding from a rejected PR — re-introduce the mechanism when a real consumer needs it |
| Assumed `git cherry-pick A B` would either both apply or both not | First commit `9d452948` applied clean; second `133e6b56` conflicted. Wondered if rebase order or git was confused | Cherry-pick conflicts are per-commit and per-hunk; one applying clean tells you nothing about the next. Each cherry-pick is independent | When cherry-picking multiple commits, prepare to abort and reassess after each — they're not a transaction |

## Results & Parameters

### Worked example: ProjectOdyssey PR #5382 → PR #5407 (2026-05-15)

PR #5382 was rejected but contained portable improvements. Two `justfile` commits were related:

**Commit `95891f90` "fix(ci): forward MOJO_TEST_UNDER_GDB into the container"** — added bare `-e VARNAME` passthroughs:

```diff
--- a/justfile
+++ b/justfile
@@ -76,7 +76,16 @@ _run cmd:
-            podman compose exec -e USER_ID={{USER_ID}} -e GROUP_ID={{GROUP_ID}} -T {{podman_service}} bash -c "$HOME_FIXUP {{cmd}}"
+            # Forward CI/coredump env vars into the container. Without these
+            # -e passthroughs, MOJO_TEST_UNDER_GDB / CRASH_BUNDLE_DIR set on
+            # the GHA runner are NOT visible to the bash recipe inside the
+            # container, so the gdb wrapper would be silently skipped.
+            podman compose exec \
+                -e USER_ID={{USER_ID}} -e GROUP_ID={{GROUP_ID}} \
+                -e MOJO_TEST_UNDER_GDB \
+                -e MOJO_UNDER_GDB \
+                -e CRASH_BUNDLE_DIR \
+                -T {{podman_service}} bash -c "$HOME_FIXUP {{cmd}}"
```

**Commit `133e6b56` "fix(ci): use explicit -e KEY=VAL for env passthrough (docker-compose compat)"** — converted the bare passthroughs to an EXTRA_ENV array:

```diff
--- a/justfile
+++ b/justfile
@@ -80,11 +80,17 @@ _run cmd:
+            #
+            # NOTE: docker-compose (cli-plugin) rejects bare `-e VARNAME`
+            # (without `=value`) with "badly formed, must be key=value" — we
+            # must build the args conditionally with explicit values.
+            EXTRA_ENV=()
+            if [ -n "${MOJO_TEST_UNDER_GDB-}" ]; then EXTRA_ENV+=(-e "MOJO_TEST_UNDER_GDB=${MOJO_TEST_UNDER_GDB}"); fi
+            if [ -n "${MOJO_UNDER_GDB-}" ];      then EXTRA_ENV+=(-e "MOJO_UNDER_GDB=${MOJO_UNDER_GDB}"); fi
+            if [ -n "${CRASH_BUNDLE_DIR-}" ];    then EXTRA_ENV+=(-e "CRASH_BUNDLE_DIR=${CRASH_BUNDLE_DIR}"); fi
             podman compose exec \
                 -e USER_ID={{USER_ID}} -e GROUP_ID={{GROUP_ID}} \
-                -e MOJO_TEST_UNDER_GDB \
-                -e MOJO_UNDER_GDB \
-                -e CRASH_BUNDLE_DIR \
+                "${EXTRA_ENV[@]}" \
                 -T {{podman_service}} bash -c "$HOME_FIXUP {{cmd}}"
```

### Analysis

The user wanted to drop everything gdb-related — including `95891f90` and the gdb scaffolding.

**Naive read of `133e6b56`'s subject**: "docker-compose compat fix" — sounds general, worth keeping.

**Naive cherry-pick**: conflict. Without `95891f90`, the bare `-e VARNAME` lines `133e6b56` expected to replace don't exist.

**Closer read of `133e6b56`'s actual diff**: the EXTRA_ENV array it builds contains **only** the three gdb env vars (`MOJO_TEST_UNDER_GDB`, `MOJO_UNDER_GDB`, `CRASH_BUNDLE_DIR`). Every added line falls under classification (b) — a general mechanism operating exclusively on the dropped feature's data. Without gdb, the array would be empty. The "compat fix" is purely scoped to those gdb passthroughs.

**Decision**: `133e6b56` is a no-op without `95891f90`. Drop it.

Net: of the two related commits, only the unrelated `9d452948` (USER_ID/GROUP_ID export) was meaningfully portable; PR #5407 cherry-picked that one commit alone.

## Verified On

- **Repo**: HomericIntelligence/ProjectOdyssey
- **Source PR (rejected)**: #5382
- **Salvage PR (merged)**: #5407
- **Merge commit**: `e79165e2`
- **Date**: 2026-05-15
- **Verification**: verified-local — the *learning* is a git/cherry-pick decision procedure, not code that ran in CI. The downstream PR #5407 (which executed the decision) merged successfully, which is supporting evidence but not direct CI validation of the *procedure*.
