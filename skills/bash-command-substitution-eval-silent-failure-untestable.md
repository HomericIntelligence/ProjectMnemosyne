---
name: bash-command-substitution-eval-silent-failure-untestable
description: "The inner command of `eval \"$(/cmd ...)\"` runs in a command-substitution subshell whose non-zero exit is swallowed, so the eval-failure rc-capture path is unreachable and untestable via the public function. Use when: (1) writing or reviewing a bats/unit test that claims to assert `eval` returns non-zero by pointing it at a nonexistent or exit-N command, (2) a test named 'eval failure surfaces rc' is functionally identical to the happy-path test and can never catch a regression, (3) hardening an `eval`-bound function with a whitelist regex and then trying to test the real-eval-failure branch, (4) deciding whether a `local _rc=0; eval \"$line\" || _rc=$?` capture is verifiable by runtime test or only by code inspection, (5) reconciling a `|| true` call-site (POLA-visible failure tolerance) against a repo `forbid-or-true` pre-commit hook, (6) removing redundant line-level `# shellcheck disable=SC2015` under a file-wide disable."
category: testing
date: 2026-06-11
version: "1.0.0"
verification: verified-local
user-invocable: false
tags:
  - bash
  - eval
  - command-substitution
  - subshell
  - silent-failure
  - exit-code
  - rc-capture
  - whitelist
  - bats
  - shell-testing
  - untestable
  - false-test
  - shellcheck
  - forbid-or-true
  - pre-commit
  - pola
  - security
---

# Bash Command-Substitution `eval` Silent Failure Is Untestable

## Overview

| Field | Value |
|-------|-------|
| **Date** | 2026-06-11 |
| **Objective** | Explain why `eval "$(/cmd ...)"` cannot surface the inner command's non-zero exit, and how that makes the eval-failure rc-capture path a false-test trap |
| **Outcome** | Success (verified-local) — all 9 bats tests + full pre-commit passed locally on ProjectHephaestus PR #1036, issue #743; CI merge not yet confirmed at capture time |
| **Category** | testing |
| **Theme** | A subshell's exit code is discarded by command substitution; only its stdout becomes `eval`'s input, so a failing inner command yields `eval ""` → rc=0 |

## When to Use

Trigger this skill when:

- You are writing or reviewing a bats/unit test that asserts `eval "$(/path/to/cmd)"` returns non-zero by pointing at a **nonexistent path** or a command that `exit N`s — this assertion can never hold.
- A test named something like "eval failure surfaces non-zero return code" is **functionally identical** to the happy-path test (same observable behavior, rc=0) and therefore can never catch a regression.
- You hardened an `eval`-bound function with an input **whitelist regex** (a security fix) and now want a public-API test that exercises real `eval` failure — it is unreachable.
- You must decide whether a `local _rc=0; eval "$line" || _rc=$?; return "$_rc"` capture is verifiable by a runtime test or **only by code inspection**.
- A legitimate `... || true` call-site (failure tolerance made visible per POLA) collides with a repo `forbid-or-true` pre-commit pygrep hook.
- You see line-level `# shellcheck disable=SC2015` in a file that already has a file-wide `# shellcheck disable=SC2015` at the top.

Do NOT use when:

- The failure you care about is `eval` of a **literal string** you control directly (e.g. `eval "exit 1"` with no command substitution) — that DOES return non-zero and is testable.
- The subshell exit code matters in a non-`eval` context (use process-substitution / capture-then-check patterns instead).

## Verified Workflow

### The core mechanism

When you write:

```bash
eval "$(/nonexistent/bin/brew shellenv)"
```

and `/nonexistent/bin/brew` does not exist (or exits non-zero):

1. The command substitution `$(...)` runs in a **subshell**.
2. The subshell fails (e.g. exit 127 "command not found"), but that exit code does **not** propagate to the parent.
3. The substitution evaluates to an **empty string**.
4. The parent runs `eval ""`, which **succeeds with rc=0**.

So the `warn: failed to apply` branch and the `|| _rc=$?` capture **never fire**. The exit code of the substituted command is discarded; only its **stdout** becomes `eval`'s input.

### Why you cannot have both a strict whitelist and a real-eval-failure test

To make `eval` itself return non-zero you need the substitution (or the input line) to **emit valid output that then fails as a shell command** — e.g. a line that runs `exit 1`, or syntactically invalid shell that `eval` rejects. But if the function gates its input through a whitelist regex (the security hardening), any such contrived string is **rejected upstream by the whitelist**. The failing-`eval` path is therefore genuinely **unreachable through the public function**. You cannot have both "strict whitelist" and "a public-API test that exercises real `eval` failure."

### Honest resolution

1. Gate `eval`-bound input through a **single-source-of-truth whitelist regex** at function entry; return a distinct code (e.g. `2`) on refusal.
2. Capture eval's own rc explicitly:
   ```bash
   add_to_bashrc() {
     local line="$1"
     [[ "$line" =~ $ADD_TO_BASHRC_ALLOWED_RE ]] || return 2   # refuse non-whitelisted input
     # ... idempotent append ...
     local _rc=0
     eval "$line" || _rc=$?
     return "$_rc"
   }
   ```
3. At call-sites that tolerate runtime failure, write `add_to_bashrc "..." || true` so the suppression is **visible** (POLA). If a `forbid-or-true` pre-commit hook objects, add a narrow `exclude:` for that file in `.pre-commit-config.yaml` rather than hiding the tolerance.
4. In tests:
   - Assert the whitelist **accepts** valid shapes and **rejects** invalid ones (refusal returns non-zero + prints the refusal message).
   - Assert **idempotent** append (running twice does not duplicate the line).
   - For the eval-failure-rc path: **document in the test that it is unreachable via the public whitelisted API** and verified by inspection of the `local _rc=0; eval || _rc=$?` structure. Do NOT keep a test that asserts `[ "$status" -eq 0 ]` under a name claiming it tests *failure* — **rename it** to reflect what it actually verifies, e.g. "whitelisted eval form is accepted even if the command is not found."

### Secondary lessons (same PR, worth knowing)

- **Redundant line-level `# shellcheck disable=SC2015`**: if a file-wide disable already exists at the top, remove the per-line ones — they falsely imply a local-only suppression.
- **PR scope discipline**: an unrelated `env.pop(...)` edit to `loop_runner.py` with no linkage to the issue drew a YAGNI review thread and had to be removed. Keep one-issue PRs free of incidental edits.
- **`forbid-or-true` tradeoff**: the security fix legitimately needs `|| true` at call-sites to make eval-failure tolerance visible; reconcile with the repo's `forbid-or-true` pygrep hook via a narrow `exclude:` on that file, not by deleting the visible tolerance.

### Quick Reference

| Symptom | Reality | Action |
|---------|---------|--------|
| Test asserts `eval "$(/nonexistent ...)"` returns non-zero | Subshell fails → empty stdout → `eval ""` → rc=0; assertion never holds | Rename test to "whitelisted form accepted even if command not found"; do not assert failure |
| Want to test real `eval`-failure branch behind a whitelist | Whitelist rejects any failing-shell payload upstream → path unreachable | Verify by code inspection of `local _rc=0; eval \|\| _rc=$?`; document untestability in the test |
| `\|\| true` at call-site blocked by `forbid-or-true` hook | Tolerance is intentional + POLA-visible | Add narrow `exclude:` for the file in `.pre-commit-config.yaml` |
| Line-level `# shellcheck disable=SC2015` under a file-wide disable | Redundant; misleads readers | Remove the per-line disable |
| Inner command's exit code seems "lost" in `eval "$(...)"` | Command substitution discards the subshell rc; only stdout flows to `eval` | If you need the inner rc, capture output and command separately, then check rc before `eval` |

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
|---------|----------------|---------------|----------------|
| 1 | Test `eval "$(/nonexistent/.../brew shellenv)"` and assert `[ "$status" -ne 0 ]` | Command substitution failed in the subshell → empty output → `eval ""` → rc=0; the assertion never holds | A nonexistent-path substitution cannot make `eval` fail; the test is a false test identical to the happy path |
| 2 | Inject a fake `brew` that `exit 42`s, expecting `eval` to return 42 | The subshell exits 42 but still emits no stdout → parent runs `eval ""` → rc=0 | The exit code of the substituted command is discarded; only its stdout becomes `eval`'s input |
| 3 | Craft a whitelisted-looking string whose expansion produces failing shell | The whitelist regex (`ADD_TO_BASHRC_ALLOWED_RE`) rejects any such contrived form before `eval` runs | A strict input whitelist makes the real-eval-failure path unreachable via the public function — verify it by inspection, not a runtime test |

## Results & Parameters

| Parameter | Value |
|-----------|-------|
| **Where verified** | ProjectHephaestus PR #1036, issue #743 ("[MINOR] scripts/shell/install.sh:35-36 uses eval over user-controlled $line") |
| **Fix shape** | Hardened `add_to_bashrc` with a single-source whitelist regex + rc-capture (`local _rc=0; eval "$line" \|\| _rc=$?; return "$_rc"`) |
| **Verification** | verified-local — all 9 bats tests + full pre-commit passed locally; CI merge not yet confirmed at capture time |
| **Review evidence** | 3 review threads on the false eval-failure test (PRRT_kwDOQww0as6Hk2__, PRRT_kwDOQww0as6Hk59w, PRRT_kwDOQww0as6HqXcM); redundant shellcheck disables (PRRT_kwDOQww0as6HqXcK / ...XcL); YAGNI scope thread on `loop_runner.py` env.pop (PRRT_kwDOQww0as6HqXcI) |
| **Refusal code** | `2` (distinct from generic failure) when input fails the whitelist |
| **Key tradeoff** | Strict whitelist vs. testable eval-failure path — mutually exclusive; chose the whitelist and documented the untestability |
