---
name: git-dco-signoff-distinct-from-gpg-sign
description: "The DCO Signed-off-by trailer (git commit -s) is a SEPARATE requirement from GPG/SSH cryptographic signing (git commit -S); a commit can be -S signed yet still fail the pr-policy DCO check because it lacks the trailer. Use when: (1) a PR is BLOCKED and the pr-policy / required-checks-gate CI gate fails with 'missing Signed-off-by: Name <email> trailer' even though git log --show-signature shows a valid GPG signature, (2) automation/agent-generated commits (auto-impl branches) lack the DCO trailer because the generator ran `git commit -S` without `-s`, (3) you need to retroactively add Signed-off-by to every commit on a branch WITHOUT losing GPG signatures, (4) lint passes but required-checks-gate still fails — check pr-policy sub-checks (Check 4 is DCO), (5) you fixed only one blocker (mypy/lint) but the gate is still red on a second independent DCO failure, (6) `git log` shows TWO (or more) `Signed-off-by` trailers on the same commit after the retroactive fix-all recipe was run more than once — this is a DUPLICATE trailer, not a missing one, caused by `--exec ... -s -S` being run twice with different `user.name` config values, since `-s` dedups by literal string match on the whole trailer line, not by email, (7) you are about to run `git rebase --exec \"git commit --amend --no-edit -s -S\" origin/main` on a branch that may ALREADY carry a Signed-off-by trailer (e.g. a resumed/interrupted rebase session) — reconcile `git config user.name` first to avoid producing a duplicate trailer."
category: ci-cd
date: 2026-07-12
version: "1.1.0"
user-invocable: false
verification: verified-ci
history: git-dco-signoff-distinct-from-gpg-sign.history
tags: []
---

# Git DCO Signed-off-by Is Distinct from GPG Signing

## Overview

| Field | Value |
|-------|-------|
| **Date** | 2026-06-26 |
| **Objective** | Land 5 stranded auto-impl refactor PRs whose `required-checks-gate` was red because `pr-policy` Check 4 (DCO Signed-off-by trailer) failed independently of GPG signing |
| **Outcome** | Successful — added the `Signed-off-by` trailer to every commit (including bot-authored ones) while preserving GPG signatures; pr-policy and required-checks-gate went green |
| **Verification** | verified-ci — these commits actually merged in ProjectHephaestus on 2026-06-26 via this fix |

## When to Use

- A PR is BLOCKED and the `pr-policy` / `required-checks-gate` CI gate fails with `missing Signed-off-by: Name <email> trailer` even though `git log --show-signature` shows a valid GPG signature.
- Automation/agent-generated commits (auto-impl branches like #1385, #1392) lack the DCO trailer because the generator ran `git commit -S` without `-s`.
- You need to retroactively add `Signed-off-by` to every commit on a branch WITHOUT losing GPG signatures.
- Lint passes but `required-checks-gate` still fails — inspect the `pr-policy` sub-checks (Check 4 is DCO).
- You fixed only one blocker (mypy/lint) but the gate is still red on a second, independent DCO failure.
- `git log` shows TWO (or more) `Signed-off-by` trailers on the same commit after running the retroactive fix-all recipe more than once — a DUPLICATE trailer, not a missing one, caused by different `user.name` config between passes.
- You are about to run the retroactive fix-all recipe on a branch from an interrupted/resumed session and are unsure whether a trailer is already present — reconcile `git config user.name` first to avoid producing a duplicate.

## Verified Workflow

The key fact: `git commit -S` (GPG/SSH cryptographic signature, satisfies
`required_signatures` / `verified=true`) is ORTHOGONAL to `git commit -s`
(appends a `Signed-off-by: Name <email>` text trailer, the Developer Certificate
of Origin). `pr-policy` Check 4 requires the TRAILER on every commit; it does
not inspect the GPG signature. A commit can be `%G?`=`G`/`U` (cryptographically
signed) and still fail Check 4 for lack of the trailer.

### Quick Reference

```bash
# 1. ALWAYS commit with BOTH the DCO trailer (-s) and the GPG signature (-S):
git commit -s -S -m "feat(scope): message"

# 2. Retroactively add the DCO trailer to EVERY commit on a branch while
#    PRESERVING GPG signing (works because commit.gpgsign=true):
git rebase --exec "git commit --amend --no-edit -s -S" origin/main
git push --force-with-lease

# 3. Verify per-commit — every commit MUST show a non-empty signoff:
git log origin/main..HEAD \
  --format="%h %s | signoff:[%(trailers:key=Signed-off-by,valueonly)] gpg:%G?"

# 4. Find WHICH pr-policy sub-check failed (the gate aggregates):
gh run view --job <id> --log   # grep for "Check 4: DCO Signed-off-by"
```

### Detailed Steps

1. **Diagnose the real blocker.** `required-checks-gate` aggregates several
   checks; a red gate is often a downstream consequence of `pr-policy`. Open the
   gate's job log with `gh run view --job <id> --log` and find the named
   sub-checks ("Check 3: Conventional Commits", "Check 4: DCO Signed-off-by").
   Enumerate ALL failing sub-checks before re-pushing — do not assume a single
   cause.
2. **Confirm it is DCO, not GPG.** Run `git log --show-signature -1` — if it
   shows a valid signature but the gate still fails on `missing Signed-off-by`,
   the problem is the missing text trailer, a separate requirement.
3. **Add the trailer to every commit.** Run
   `git rebase --exec "git commit --amend --no-edit -s -S" origin/main`. The
   `-s` appends the trailer; `-S` re-applies the GPG signature so the rebase
   does not strip it. This covers EVERY commit on the branch, including
   bot/automation-authored ones — Check 4 validates all of them, not just HEAD.
4. **Verify.** Run the per-commit verify command above; every line must show a
   non-empty `signoff:[...]`. A `gpg:U` (signed but locally-untrusted key) is
   FINE — GitHub verifies server-side, and both `U` and `G` satisfy
   crypto-signing.
5. **Push.** `git push --force-with-lease` (safer than `--force`).

### Duplicate trailers from re-signing with different user.name

Running the exact recipe from step 3 (`git rebase --exec "git commit --amend
--no-edit -s -S" origin/main`) a SECOND time — e.g. because a rebase session
was interrupted and resumed, or a mass-rebase was re-run defensively — does
NOT deduplicate an existing `Signed-off-by` trailer if `git config user.name`
differs between the two passes. Instead of one trailer, the commit ends up
with two:

```text
Signed-off-by: Micah Villmow <noreply@users.noreply.github.com>
Signed-off-by: mvillmow <noreply@users.noreply.github.com>
```

**Root cause.** `-s`/`--signoff` dedups by a LITERAL STRING match on the whole
trailer line (`Signed-off-by: <exact name> <exact email>`), not by email
alone. If pass 1 ran under `user.name=mvillmow` and pass 2 ran under
`user.name="Micah Villmow"` (same email, different display name), git does not
recognize the second as "the same person already signed off" — it appends a
new line instead of skipping.

**Functionally harmless for this repo's CI.** `scripts/check_dco_signoff.py`
in ProjectHephaestus only requires ONE well-formed line matching
`^Signed-off-by: .+ <[^<>@\s]+@[^<>@\s]+>$` anywhere in the commit body, so a
duplicate does not fail `pr-policy` Check 4. It is untidy and reads as a
confusing diff to a human reviewer, but it is not a merge blocker on its own.

**Prevention.** Reconcile `git config user.name` and `git config --global
user.name` to ONE canonical value BEFORE the first `--exec ... -s -S` pass,
especially across an interrupted/resumed session:

```bash
git config user.name            # local override, if any
git config --global user.name   # global default
# pick one canonical value and set it before rebasing
git config user.name "Micah Villmow"
```

**Recovery if trailers are already duplicated.** Do NOT run `git commit -s`
again — that risks adding a THIRD variant if `user.name` still isn't
reconciled. Instead run a second `--exec` pass with a message-rewrite script
that keeps only the first trailer:

```bash
git rebase --exec '
  python3 - <<PYEOF
import re, subprocess
msg = subprocess.run(["git", "log", "-1", "--format=%B"], capture_output=True, text=True, check=True).stdout
lines = msg.splitlines()
seen_signoff = False
kept = []
for line in lines:
    if line.startswith("Signed-off-by:"):
        if seen_signoff:
            continue  # drop every trailer after the first
        seen_signoff = True
    kept.append(line)
new_msg = "\n".join(kept)
subprocess.run(["git", "commit", "--amend", "-S", "-m", new_msg], check=True)
PYEOF
' origin/main
```

Note the recovery pass's `git commit --amend` uses `-S` only, NOT `-s` — the
script itself already writes the canonical trailer into the rewritten
message, so re-adding `-s` would risk re-triggering the same
literal-string-mismatch dedup failure if `user.name` still isn't reconciled.
This recovery is a pure commit-MESSAGE rewrite (no file content changes), so
it runs with zero working-tree conflicts. Verify with:

```bash
git log origin/main..HEAD --format='%h %(trailers:key=Signed-off-by)'
# every commit must show exactly ONE Signed-off-by line
```

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
|---------|----------------|---------------|----------------|
| Committed with `git commit -S` only (no -s) | Assumed GPG signing satisfied the policy | pr-policy Check 4 failed: missing Signed-off-by trailer; required-checks-gate then failed downstream | DCO trailer is a separate text requirement from crypto signing — always pass both -s and -S |
| Fixed the mypy/lint error and assumed the gate would pass | Treated required-checks-gate as a single-cause failure | Gate still red — a second independent DCO failure remained | A required-checks-gate failure can aggregate multiple independent causes; enumerate ALL failing pr-policy sub-checks before re-pushing |
| Re-signed only the new commit, left the original auto-impl commit untouched | Thought only my own commit needed the trailer | Check 4 validates EVERY commit on the PR, including bot/automation-authored ones | Use `git rebase --exec ... -s -S origin/main` to cover every commit, not just HEAD |
| Ran `--exec "git commit --amend --no-edit -s -S" origin/main` twice with different `user.name` between passes | Expected `-s` to dedupe an already-present trailer on the second pass | Produced duplicate `Signed-off-by` trailers instead of deduping — `-s` matches the whole trailer line literally, not just the email | Reconcile `user.name` (local + global) to one canonical value before the first pass; recover via a message-rewrite `--exec` pass keeping only the first trailer |

## Results & Parameters

- **Repo**: `HomericIntelligence/ProjectHephaestus`
- **Gate**: `pr-policy` (required), with sub-check script `check_dco_signoff.py`
  (Check 4). `required-checks-gate` aggregates it and shows red downstream.
- **Context**: Landing 5 stranded auto-impl refactor PRs; PR #1615's
  required-checks-gate failed on both lint(mypy) AND DCO. Multiple auto-impl
  branches (#1385, #1392) had the same DCO gap.
- **Always-commit recipe** (copy-paste):

  ```bash
  git commit -s -S -m "feat(scope): message"
  ```

- **Retroactive fix-all recipe** (copy-paste):

  ```bash
  git rebase --exec "git commit --amend --no-edit -s -S" origin/main
  git push --force-with-lease
  ```

- **Verify recipe** (copy-paste):

  ```bash
  git log origin/main..HEAD \
    --format="%h %s | signoff:[%(trailers:key=Signed-off-by,valueonly)] gpg:%G?"
  ```

- **Interpreting `%G?`**: `G` = good signature, `U` = signed but
  locally-untrusted key (FINE — GitHub verifies server-side). Both satisfy
  crypto-signing; neither implies the DCO trailer is present.
- **Duplicate-trailer dedup mechanism**: `-s`/`--signoff` dedups by a LITERAL
  STRING match on the whole `Signed-off-by: Name <email>` line, not by email
  alone. Running the retroactive fix-all recipe twice with different
  `user.name` config values (e.g. `mvillmow` vs `Micah Villmow`, same email)
  produces two trailers instead of one deduplicated trailer.
- **Duplicate-trailer recovery recipe** (copy-paste; keeps only the first
  trailer, re-signs with `-S` only — no `-s` — to avoid re-triggering the same
  mismatch):

  ```bash
  git rebase --exec '
    python3 - <<PYEOF
  import re, subprocess
  msg = subprocess.run(["git", "log", "-1", "--format=%B"], capture_output=True, text=True, check=True).stdout
  lines = msg.splitlines()
  seen_signoff = False
  kept = []
  for line in lines:
      if line.startswith("Signed-off-by:"):
          if seen_signoff:
              continue
          seen_signoff = True
      kept.append(line)
  subprocess.run(["git", "commit", "--amend", "-S", "-m", "\n".join(kept)], check=True)
  PYEOF
  ' origin/main
  ```

- **Verified On**:

  | PR | Repo | Context |
  |----|------|---------|
  | [#2056](https://github.com/HomericIntelligence/ProjectHephaestus/pull/2056) | `HomericIntelligence/ProjectHephaestus` | `[Critical] Fail closed autonomous auto-merge paths`, branch `2054-auto-impl`, 17 commits; encountered during a large rebase (~38 commits forward onto `origin/main`) that required two separate `--exec ... -s -S` re-signing passes because of an interrupted/resumed session with different `user.name` config between passes. Verified LOCALLY — the recovery script was run and observed (via `git log --format='%(trailers:key=Signed-off-by)'`) to produce exactly one clean trailer per commit. Not yet verified against this Mnemosyne skill PR's own CI at authoring time. |
