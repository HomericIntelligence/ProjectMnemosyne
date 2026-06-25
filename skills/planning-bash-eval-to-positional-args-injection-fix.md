---
name: planning-bash-eval-to-positional-args-injection-fix
description: >-
  Methodology for planning a bash shell-injection remediation that replaces
  `eval "$cmd"` with positional-parameter expansion `"$@"` in a retry/wrapper
  helper. Use when: (1) planning a fix that swaps `eval "$cmd"` for `"$@"` in a
  retry, with-timeout, or generic command-wrapper helper; (2) the plan reorders
  a helper signature so the command becomes a trailing varargs slot
  (`func MAX SLEEP COMMAND...`); (3) the plan claims a helper has "zero call
  sites" so the signature reorder is "free" — the single highest-risk assumption;
  (4) deciding whether to add a new CI lint guard or lean on an existing
  shellcheck gate; (5) proving injection-safety of a bash command wrapper before
  writing implementation code; (6) reviewing such a plan that was authored but
  NOT executed against the working tree.
category: architecture
date: 2026-06-20
version: "1.0.0"
user-invocable: false
verification: unverified
tags:
  - bash
  - eval
  - shell-injection
  - positional-parameters
  - varargs
  - retry-helper
  - signature-reorder
  - call-site-audit
  - submodules
  - grep-fragile
  - shellcheck
  - lint-gate
  - canary-test
  - command-substitution
  - planning-risks
  - security
  - dry
  - mktemp
---

# Planning a Bash `eval "$cmd"` → `"$@"` Injection Fix

## Overview

| Field | Value |
| ------- | ------- |
| **Date** | 2026-06-20 |
| **Source issue** | Odysseus (meta-repo) #190 — `retry()` in `e2e/lib/common.sh` executes its command string via `eval`, a shell-injection vector |
| **Verification** | unverified (planning-phase methodology; NO commands ran against the working tree, the canary test was authored but never executed, and `pixi run just lint` / shellcheck were never run) |
| **Objective** | Capture the durable planning methodology and the specific assumptions/risks that an `eval "$cmd"` → `"$@"` bash-injection remediation plan MUST verify before it is trusted |
| **Category** | architecture (planning/design methodology — there is no dedicated security category) |
| **Theme** | The fix itself is small; the *risk* lives in the plan's unverified assumptions (zero call sites, lint-gate coverage, proof of safety) |

> [!WARNING]
> **PROPOSED WORKFLOW — UNVERIFIED.** This skill documents a planning methodology
> that was authored but never executed. No commands were run against the working
> tree, the canary test below was written but never run, and `pixi run just lint`
> / shellcheck were never invoked. Treat every step as a *proposal to verify*,
> not a confirmed result. The "Verified Workflow" heading below is retained only
> because the repository's skill validator requires that literal section name.

The core fix is trivial: stop running an attacker-influenceable command string
through `eval` and instead pass the command as separate positional arguments,
invoking it with `"$@"`. The danger is not the diff — it is the chain of
unverified assumptions a plan leans on to claim the diff is "free" and "safe."

---

## When to Use

Use this skill when:

1. Planning a remediation that replaces `eval "$cmd"` (or `eval "$@"`, `eval $cmd`) with positional-parameter expansion `"$@"` inside a retry, with-timeout, backoff, or generic command-wrapper helper.
2. The plan must **reorder a helper's signature** so the command-to-run becomes a trailing varargs slot — e.g. `retry MAX_ATTEMPTS SLEEP_BETWEEN COMMAND [ARGS...]`.
3. The plan claims the helper has **zero call sites**, so the signature reorder needs no caller migration. This is the highest-risk claim in the whole plan.
4. Deciding whether to add a brand-new CI lint step or to **lean on an existing shellcheck/lint gate** as the regression guard (a DRY decision that must still be verified to cover the changed path).
5. You need to **prove** the injection is closed, not merely assert that `eval` was deleted.
6. You are *reviewing* such a plan (especially one authored but not executed) and need the checklist of things to independently re-verify.

Do NOT use this skill when:

- The `eval` runs a literal string you fully control with no external input (no injection surface) and there is no security driver — that is a style change, not a remediation.
- The wrapper genuinely needs to evaluate shell *syntax* (pipes, redirections, globbing supplied as one string). `"$@"` runs a single command with literal args; if callers legitimately pass `"foo | bar"` as one string, a naive `"$@"` swap will break them. Re-scope first.

---

## Verified Workflow

### Quick Reference

| Step | Action | Why |
| ------ | ------- | ----- |
| 1 | Reorder signature so command is the trailing varargs (`func MAX SLEEP CMD...`) | `"$@"` cannot capture an arbitrary-length command if leading positional args follow it |
| 2 | Mirror an existing in-repo safe-retry idiom that already uses `"$@"` | Consistency + a vetted reference (here `_agamemnon_curl_retry`) |
| 3 | Verify "zero call sites" with a DEF-vs-INVOCATION grep, widened across submodules | The "reorder is free" claim is grep-fragile and highest-risk |
| 4 | Confirm the existing lint gate actually covers the changed file's path | DRY reuse only works if the awk/path filter includes `e2e/` and the new test |
| 5 | Prove safety with a positive canary test (`mktemp -u` sentinel inside `$(touch ...)`) | Stronger than grepping that `eval` was removed |
| 6 | Mark the plan `unverified`; recommend the reviewer re-run the call-site grep | Honesty: nothing here was executed |

### Step 1 — The signature MUST reorder so the command is trailing varargs

`"$@"` expands to *all* remaining positional parameters. It can only capture an
arbitrary-length command if no fixed positional args come **after** it. So the
helper signature must put its own knobs first and the command last:

```bash
# BEFORE (injection-prone): command arrives as one string, run via eval
retry() {
  local cmd="$1" max="${2:-3}" sleep_between="${3:-2}"
  local attempt=1
  until eval "$cmd"; do            # <-- shell-injection vector
    (( attempt >= max )) && return 1
    attempt=$(( attempt + 1 ))
    sleep "$sleep_between"
  done
}

# AFTER: knobs first, command + args as trailing "$@"; never eval
retry() {
  local max="$1" sleep_between="$2"
  shift 2
  local attempt=1
  until "$@"; do                   # literal exec of the command + args
    (( attempt >= max )) && return 1
    attempt=$(( attempt + 1 ))
    sleep "$sleep_between"
  done
}
# call: retry 3 2 curl -fsS "$url"
```

The reorder is not cosmetic — it is *required* by how `"$@"` works. A plan that
keeps the command in `$1` and tries `"$@"` is internally inconsistent.

### Step 2 — Mirror an existing in-repo safe-retry idiom

If the repo already hardened a similar wrapper, copy its shape instead of
inventing one. In this case the reference was
`provisioning/Myrmidons/scripts/lib/api.sh:233` (`_agamemnon_curl_retry`), which
already runs its target via `"$@"`. Citing and mirroring a vetted in-repo idiom
reduces review surface and keeps the two helpers consistent.

### Step 3 — Verify "zero call sites" (the highest-risk claim)

The "no callers → reorder is free" assumption is the single most fragile part of
the plan, because a plain `grep -rn 'retry'` is wrong in several ways:

- It does not distinguish the **definition** (`retry()` / `function retry`) from **invocations** (`retry ...`).
- A superproject grep may **not descend into git submodule working trees** the way you expect, so callers living in submodules are missed.
- It misses **dynamic/indirect** invocation (`"$fn" ...`, `eval`, `command retry`, aliases).
- It misses callers that **source the lib from outside the repo**.

Recommended grep that separates definition from invocation:

```bash
# Definitions (expect exactly the one you are changing):
grep -rnE '^\s*(function\s+)?retry\s*\(\)|^\s*function\s+retry\b' .

# Invocations (callers): word-boundary, not followed by '(' :
grep -rnE '\bretry[[:space:]]+[^([:space:]]' . \
  | grep -vE '\bretry\s*\(\)'

# Widen across submodules explicitly — do NOT trust the superproject sweep:
git submodule foreach --recursive \
  'grep -rnE "\bretry[[:space:]]" . || true'
```

Then explicitly recommend in the plan that **the reviewer re-run the call-site
grep independently and widen it across submodules** before trusting "no
migration needed." Treat "zero call sites" as a claim to be falsified, not a fact.

### Step 4 — Confirm the existing lint gate covers the changed path (DRY, but verify)

Leaning on an existing shellcheck/lint gate instead of adding a new CI step is a
sound DRY decision — but only if that gate actually lints the file you changed
and the new test file. Here the gate was `justfile:198-211` (a shellcheck step
added for issue #195) that **filters submodule paths via `awk`**. Before relying
on it:

- Confirm `e2e/` (the changed file's directory) is **in scope** of the awk path
  filter and not excluded as a submodule path.
- Confirm the **new test file** will be picked up — it must be **tracked** by git
  (the gate typically iterates tracked shell files).

```bash
# Reproduce what the gate selects, then check your paths appear:
git ls-files '*.sh' | awk '<the same filter the justfile uses>' \
  | grep -E 'e2e/lib/common\.sh|e2e/.*test'
```

If `e2e/` is filtered out, the DRY reuse is an illusion — add a guard or fix the
filter.

### Step 5 — Prove injection-safety with a positive canary test

Do not "prove" the fix by grepping that `eval` is gone. Removing `eval` does not
prove that args aren't expanded somewhere else (a stray `eval`, an unquoted
expansion, `bash -c "$*"`). Use a **positive canary**: pass, as an argument, a
string containing a command-substitution that *would* create a sentinel file if
the arg were ever evaluated; then assert the sentinel never comes to exist.

```bash
# Canary: a path that must NEVER be created.
sentinel="$(mktemp -u)"            # reserved name, file does NOT exist yet
# Pass an arg whose literal text contains a command substitution:
retry 1 0 printf '%s\n' "$(touch "$sentinel"; echo pwned)"
# If the arg were eval'd, $sentinel would now exist. It must not:
[[ -e "$sentinel" ]] && { echo "INJECTION: sentinel created"; exit 1; }
echo "safe: argument passed literally, never evaluated"
```

This is strictly stronger than `grep -n eval` because it tests the *behavior*
(args are passed literally) rather than the *absence of one keyword*.

### Step 6 — Mark the plan unverified and hand the reviewer the re-checks

Because nothing was executed, set verification to `unverified`, label the section
"Proposed Workflow," and explicitly enumerate what the reviewer must run:
the call-site grep (widened across submodules), the lint-gate path check, and the
canary test. Honesty about verification level is part of the deliverable.

---

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
| --------- | ---------------- | --------------- | ---------------- |
| 1 | Trusted a single `grep -rn 'retry'` over the superproject to claim the helper has zero callers, so the signature reorder is "free" | A plain superproject grep conflates the DEFINITION with INVOCATIONS, does not reliably descend into git submodule working trees, and misses dynamic/indirect callers and out-of-repo sourcers | The "zero call sites" claim is the highest-risk assumption: separate def-vs-invocation patterns, widen the grep across submodules (`git submodule foreach --recursive`), and recommend the reviewer re-run it independently before trusting "no migration needed" |
| 2 | Proved injection-safety only by grepping that `eval` was removed from the helper | Absence of the `eval` keyword does not prove arguments aren't expanded elsewhere (a stray `eval`, an unquoted expansion, or `bash -c "$*"` could still evaluate them) | Prove safety with a positive canary test: pass a `$(touch <mktemp -u sentinel>)` argument and assert the sentinel file never exists — this tests behavior, not the absence of a keyword |
| 3 | Kept the command in `$1` and switched the invocation to `"$@"` without reordering the signature | `"$@"` expands ALL positional parameters; with `max`/`sleep` still after the command it cannot capture an arbitrary-length command and would re-include the knobs | The fix REQUIRES a signature reorder so the command becomes the trailing varargs slot (`func MAX SLEEP CMD...`), then `shift`; mirror an existing in-repo `"$@"` idiom (`_agamemnon_curl_retry`) |
| 4 | Assumed the existing `justfile` shellcheck gate would catch any regression in the changed file, with no path check | The gate filters submodule paths via `awk`; if `e2e/` is excluded or the new test file is untracked, the changed file is never linted and the "regression guard" does nothing | DRY reuse of a lint gate is sound only after verifying the gate's path filter includes the changed file's directory AND the new (tracked) test file |

## Results & Parameters

| Parameter | Value |
| ----------- | ------- |
| **Where planned** | Odysseus meta-repo, GitHub issue #190 (`retry()` in `e2e/lib/common.sh` runs its command via `eval`) |
| **Fix shape** | Reorder to `retry MAX_ATTEMPTS SLEEP_BETWEEN COMMAND [ARGS...]`, drop `eval "$cmd"`, run the command via `"$@"` (never `eval`) |
| **Reference idiom** | `provisioning/Myrmidons/scripts/lib/api.sh:233` — `_agamemnon_curl_retry`, an in-repo hardened retry already using `"$@"` |
| **Regression guard** | Existing shellcheck gate at `justfile:198-211` (added for issue #195) — reused per DRY, but its awk path filter must be verified to include `e2e/` and the new tracked test |
| **Proof of safety** | Positive canary: `mktemp -u` sentinel embedded in a `$(touch ...)` command-substitution argument; assert the sentinel file never exists |
| **Highest risk** | The "zero call sites → reorder is free" assumption — grep-fragile; must distinguish def vs invocation and widen across submodules |
| **Verification level** | unverified — no commands run, canary authored but never executed, `pixi run just lint` / shellcheck never invoked |
| **Reviewer must re-run** | (a) call-site grep widened across submodules, (b) lint-gate path/coverage check, (c) the canary test |
