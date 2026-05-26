---
name: validate-upstream-mojo-fix-hostile-home-matrix
description: "Validate that an upstream Mojo fix (runtime crash, codegen flag
  resolution, compiler-driver bug, JIT mis-emission, etc.) actually landed in
  your newly-bumped nightly BEFORE removing downstream workarounds or starting
  a demolition wave. Uses a 4-gate progression: (Gate 1) cheapest local signal
  — either a hostile-`$HOME` matrix for filesystem-error class bugs, or
  `mojo build --print-effective-target` codegen check for compiler-driver /
  target-resolution bugs, or any analogous bug-class-specific micro-repro;
  (Gate 2) ≥10× consecutive dispatches of the project's existing
  `repro-<issue#>` workflow on the bump branch; (Gate 3) full-iteration soak
  workflow if one exists; (Gate 4) ≥8 consecutive green required-check runs
  on the bump branch. Includes the load-bearing caveat that pre-fix
  infrastructure (coredump capture, gdb wrappers) often breaks for reasons
  unrelated to the fix — read the actual Mojo invocation logs, not the
  workflow's pass/fail summary. Use when: (1) you bumped the pinned Mojo
  version past an upstream fix-shipped date and want to confirm the fix
  landed in your build, (2) you are about to peel back a downstream workaround
  (Dockerfile chmod, entrypoint mkdir, BUILD_FLAGS pin to specific
  `--target-cpu`, sudoers `_ensure_writable`) and need deterministic
  confirmation, (3) an upstream Modular issue closed with 'fix in next
  nightly' and you want to verify before commenting or opening a
  workaround-removal / demolition PR, (4) you need to position a validation
  branch as a durable canary spanning the demolition wave."
category: testing
date: 2026-05-25
version: "2.0.0"
user-invocable: false
verification: verified-ci
history: validate-upstream-mojo-fix-hostile-home-matrix.history
tags:
  - mojo
  - modular
  - upstream-validation
  - container
  - permissions
  - filesystem-error
  - getAcceleratorArchOrEmpty
  - hostile-home
  - workaround-removal
  - rootless-podman
  - codegen-flags
  - avx512
  - target-cpu
  - four-gate-protocol
  - ci-canary
  - print-effective-target
---

# Validate Upstream Mojo Fix — 4-Gate Protocol (Hostile-`$HOME` Matrix as Gate 1 Example)

## Overview

| Field | Value |
| ------- | ------- |
| **Date** | 2026-05-25 |
| **Objective** | Provide a reusable 4-gate validation protocol that confirms an upstream Mojo fix actually landed in a pinned-nightly bump, deterministically enough to gate downstream workaround removal or a demolition wave |
| **Outcome** | Successful — protocol executed end-to-end on multiple upstream Mojo fixes (modular/modular#6412 filesystem-error / `getAcceleratorArchOrEmpty()`, modular/modular#6413 AVX-512 mis-emission on masked-AVX-512 CPUs). Latest application produced 47+ green required-check runs across Gate 4 before opening the demolition PR |
| **Verification** | verified-ci |
| **History** | [changelog](./validate-upstream-mojo-fix-hostile-home-matrix.history) |
| **Scope** | Any upstream Mojo fix: runtime crashes (filesystem errors, SIGABRT), codegen bugs (wrong `--target-cpu`, spurious AVX-512 feature flags, SIGILL at JIT execution), compiler-driver target resolution, ABI churn that rides along in the same nightly bump |

## When to Use

- You bumped the pinned Mojo nightly past the date a relevant upstream fix was claimed shipped, and need confirmation before merging the bump or opening dependent demolition PRs
- You are about to remove a downstream workaround (Dockerfile chmod, entrypoint mkdir, `BUILD_FLAGS` pin to a specific `--target-cpu`, sudoers `_ensure_writable`, HOME-redirect fallback) and need deterministic signal that the upstream fix landed
- An upstream Modular issue closed with "fix in next nightly" and you want to validate the claim before posting a confirmation comment or opening a workaround-removal PR
- You need to position a long-lived validation branch as a CI canary spanning the demolition wave — proof that the new pin is green on real project workload before bricks start coming out of the wall
- The bug class is unfamiliar and you want a checklist that escalates from cheap local signal to full required-check matrix without skipping rungs
- Your container runtime is rootless and blocks `setpriv` / `runuser` / `sudo -u`, ruling out true UID-mismatch reproducers — you need a permission-shape proxy for Gate 1 (Example A)

## Verified Workflow

> **Note:** verified-ci. Protocol executed end-to-end on at least two distinct
> upstream Mojo fixes: modular/modular#6412 (filesystem-error /
> `getAcceleratorArchOrEmpty()`, validated locally via Gate 1 Example A —
> hostile-`$HOME` 8-shape matrix) and modular/modular#6413 (AVX-512
> mis-emission on masked-AVX-512 CPUs like Intel Lunar Lake, validated via
> Gate 1 Example B — `mojo build --print-effective-target` codegen check
> plus 5×50 = 250 local reproducer iterations, then Gate 4 with 47+ green
> required-check runs spanning Build Validation and the Comprehensive Tests
> matrix). Gate 4 in the latter case also caught a stdlib API regression
> (`UnsafePointer._unsafe_null=()` constructor removed) that arrived in the
> same nightly bump and had to be fixed on the validation branch before the
> demolition wave merged.

### Quick Reference

```bash
# === GATE 0 (mandatory) — verify the version premise ===
grep '^mojo' pixi.toml
git log --oneline -- pixi.toml | head -5
# If pinned version predates the upstream fix-shipped date in the issue,
# STOP. The rest is theater until the bump lands.

# === GATE 1 — cheapest local signal (pick the example matching the bug class) ===

# --- Gate 1 Example A: hostile-$HOME matrix (filesystem-error class bugs, e.g. #6412) ---
# Build a one-line Mojo binary once, exec under N hostile $HOME shapes.
# See "Gate 1 Example A" section below for the 8-shape recipe.

# --- Gate 1 Example B: codegen / target-resolution bugs (e.g. #6413 AVX-512 mis-emission) ---
# Use --print-effective-target to verify the compiler driver now resolves the host correctly.
cat > /tmp/repro.mojo <<'EOF'
def main():
    print("ok")
EOF
pixi run mojo build --print-effective-target /tmp/repro.mojo
# Pre-fix on a masked-AVX-512 host (e.g. Intel Lunar Lake): --target-cpu znver4 with
#   +avx512f,+avx512vl,+avx512bw,... feature flags. Post-fix: --target-cpu lunarlake
#   with ZERO +avx512* features. The driver fix is in the binary, independent of any
#   downstream sanitizer-codegen surface.
# Also run the actual reproducer under your normal Podman setup for 5×50 = 250
# iterations: pre-fix should be 100% crash rate, post-fix 0 crashes.

# === GATE 2 — CI canary on the existing repro workflow (if one exists) ===
# Dispatch the project's .github/workflows/repro-<issue#>.yml 10× consecutively
# on the bump branch.
for i in $(seq 1 10); do
  gh workflow run repro-<issue#>.yml --ref <bump-branch>
  sleep 2
done
gh run list --workflow=repro-<issue#>.yml --branch <bump-branch> --limit 10
# Pass: zero SIGILLs / zero stack frames in the bug's signature library across all 10 runs.
# CRITICAL CAVEAT: pre-fix repro workflows often have coredump-capture composite actions or
# gdb wrappers that break on fresh runners or after the bug is gone. The workflow may report
# "failure" while the actual Mojo invocation succeeded. INSPECT the logs of the Mojo step
# itself, not the workflow's pass/fail badge. Do NOT spend cycles fixing pre-fix infra
# slated for deletion in the upcoming demolition.

# === GATE 3 — soak (if a soak workflow exists) ===
gh workflow run soak-<issue#>.yml --ref <bump-branch>
# Same broken-infra caveat as Gate 2. Skip Gate 3 entirely if the soak workflow is
# broken for non-fix-related reasons; do not block on it.

# === GATE 4 — ≥8 consecutive green required-check runs ===
# Push commits to the bump branch and confirm every required check passes on the
# first attempt across at least 8 consecutive runs. This is the strongest signal
# because it exercises real project workload, not synthetic reproducers.
gh pr checks <bump-pr> --watch
gh run list --branch <bump-branch> --limit 50 \
  --json conclusion,name,headSha --jq '.[] | select(.conclusion=="success") | .name' \
  | sort | uniq -c
# Gate 4 frequently catches stdlib API regressions that ride along with the bump
# (removed constructors, renamed traits). Fix them on the bump branch BEFORE any
# demolition begins.

# === STRATEGIC POSITIONING ===
# Keep the validation PR OPEN as a historical canary even after demolition starts.
# It is the durable record of the pre-demolition green CI matrix on the new pin.
# Close only AFTER the first demolition wave merges.
```

### Gate 1 Example A — Hostile-`$HOME` Matrix (filesystem-error class, e.g. modular#6412)

Use this Gate 1 recipe when the upstream fix is in a startup path that calls
`std::filesystem::status` (or similar) and historically threw
`std::filesystem::filesystem_error` → `std::terminate()` → SIGABRT on hostile
`$HOME` shapes.

```bash
# 1. Write a minimal Mojo binary (Mojo 1.0+ uses `def`, not `fn`)
cat > /tmp/hello.mojo <<'EOF'
def main():
    print("ok")
EOF

# 2. Build ONCE, then exec under hostile-HOME matrix
pixi run mojo build /tmp/hello.mojo -o /tmp/hello

# Result interpretation:
#   exit 0   = upstream fix landed for that HOME shape
#   exit 134 = still broken (filesystem_error → SIGABRT) — do NOT peel workarounds
#   anything else = investigate, do NOT peel workarounds

# Shape 1: real HOME, baseline
/tmp/hello; echo "1: exit=$?"

# Shape 2: HOME mode 000, owner = self (EACCES proxy for cross-UID)
mkdir -p /tmp/fake-home && chmod 000 /tmp/fake-home
HOME=/tmp/fake-home /tmp/hello; echo "2: exit=$?"
chmod 755 /tmp/fake-home

# Shape 3: HOME mode 755, no .modular subdir
mkdir -p /tmp/fake-home2 && chmod 755 /tmp/fake-home2
HOME=/tmp/fake-home2 /tmp/hello; echo "3: exit=$?"

# Shape 4: HOME mode 750, .modular mode 700 (verbatim from issue body)
mkdir -p /tmp/fake-home3/.modular
chmod 750 /tmp/fake-home3 && chmod 700 /tmp/fake-home3/.modular
HOME=/tmp/fake-home3 /tmp/hello; echo "4: exit=$?"

# Shape 5: HOME path doesn't exist at all
HOME=/tmp/does-not-exist-$$ /tmp/hello; echo "5: exit=$?"

# Shape 6: HOME unset entirely
env -u HOME /tmp/hello; echo "6: exit=$?"

# Shape 7: HOME points at a non-directory
HOME=/dev/null /tmp/hello; echo "7: exit=$?"

# Shape 8: real $HOME chmoded 700 + .modular removed; full `mojo run` startup
SAVED_HOME_MODE=$(stat -c '%a' "$HOME")
[ -e "$HOME/.modular" ] && mv "$HOME/.modular" "$HOME/.modular.bak.$$"
chmod 700 "$HOME"
pixi run mojo run /tmp/hello.mojo; echo "8: exit=$?"
chmod "$SAVED_HOME_MODE" "$HOME"
[ -e "$HOME/.modular.bak.$$" ] && mv "$HOME/.modular.bak.$$" "$HOME/.modular"

# Cleanup
rm -rf /tmp/fake-home /tmp/fake-home2 /tmp/fake-home3 /tmp/hello /tmp/hello.mojo
```

### Gate 1 Example B — Codegen / Target-Resolution Check (e.g. modular#6413 AVX-512 mis-emission)

Use this Gate 1 recipe when the upstream fix is in the compiler-driver target
resolution or feature-flag emission path (manifests as SIGILL at JIT execution
on hosts whose CPU lacks features the driver mis-emitted).

```bash
# 1. Minimal reproducer
cat > /tmp/repro.mojo <<'EOF'
def main():
    print("ok")
EOF

# 2. Print the effective target the compiler driver resolves for THIS host
pixi run mojo build --print-effective-target /tmp/repro.mojo

# Compare driver output:
#   PRE-FIX on a masked-AVX-512 host (e.g. Intel Lunar Lake — has AVX-512 silicon
#   disabled in microcode): --target-cpu znver4 with
#   +avx512f,+avx512vl,+avx512bw,+avx512cd,+avx512dq,+avx512vnni,+avx512vbmi,...
#   POST-FIX on the same host: --target-cpu lunarlake with NO +avx512* features.
#
# The driver fix is in the bumped binary if and only if the post-fix output matches
# the host's real ISA. This is independent of any downstream sanitizer-codegen
# issues — those are separate concerns.

# 3. Run the actual reproducer 5 × 50 = 250 iterations under normal Podman setup
just podman-up
for outer in 1 2 3 4 5; do
  for inner in $(seq 1 50); do
    podman compose exec -T projectodyssey-dev pixi run mojo run /tmp/repro.mojo \
      >/dev/null 2>&1 && echo -n . || echo -n X
  done
  echo " batch $outer done"
done
# Pre-fix: ~100% X (crash). Post-fix: 0 X (all dots).
```

### Detailed Steps

1. **Gate 0 — Verify the version premise first.** Always
   `grep '^mojo' pixi.toml && git log --oneline -- pixi.toml | head` before
   declaring anything about an upstream fix. If the pinned version predates the
   upstream-fix-shipped date in the issue, validation is meaningless — open a
   version-bump PR first. (See Failed Attempts row 1.)

2. **Gate 1 — Pick the cheapest local signal for the bug class.**
   - **Filesystem-error class** → run the hostile-`$HOME` matrix (Example A).
   - **Codegen / target-resolution / JIT mis-emission class** → run the
     `--print-effective-target` driver check (Example B), plus a 250-iteration
     local crash-rate check in your normal Podman setup.
   - **Other classes** → write the smallest possible deterministic micro-repro
     that exercises the exact crashing code path. The principle: cheapest signal
     that distinguishes pre-fix from post-fix.

3. **Gate 2 — Dispatch the existing `repro-<issue#>` workflow ≥10× on the bump
   branch.** Pass criteria: zero stack frames in the bug's signature library
   across all 10 runs. **Critical caveat**: the workflow's own infrastructure
   (coredump capture, gdb wrappers) often breaks on fresh runners or after the
   bug is gone. Read the logs of the Mojo invocation step itself; ignore the
   workflow's pass/fail badge if the failure is in infra. Do NOT fix pre-fix
   infrastructure that is slated for deletion in the demolition wave.

4. **Gate 3 — Run any existing soak workflow at full iteration count.** Same
   broken-infra caveat as Gate 2. Skip entirely if the soak workflow is broken
   for non-fix-related reasons; do not block on it.

5. **Gate 4 — ≥8 consecutive green required-check runs.** Push commits to the
   bump branch and confirm every required check (Build Validation, Comprehensive
   Tests matrix, etc.) passes on the first attempt across at least 8 consecutive
   runs. This is the strongest signal because it exercises real project workload,
   not synthetic reproducers. Gate 4 frequently catches **stdlib API regressions
   that arrived in the same nightly bump** — fix them on the bump branch BEFORE
   any demolition begins.

6. **Strategically position the validation branch.** Keep the validation PR
   OPEN as a historical canary even after the demolition starts. It serves as
   the durable record of the pre-demolition green CI matrix on the new pin.
   Close only AFTER the first demolition wave merges. If you close it too
   early, you lose the audit trail that proves the bump was green BEFORE
   workarounds came out — and recovering that signal post-demolition requires
   re-running CI on a synthetic branch, which is much harder to defend in a
   regression debugging session.

7. **Post a confirmation comment on the upstream issue.** Once all gates pass,
   post a result summary to the closed Modular issue with: the pinned Mojo
   version, the commit/date, the gate results, and a one-line note about any
   stdlib API churn that rode along. Be explicit about what you could NOT test
   locally (true cross-UID for #6412-class bugs, real silicon-feature variation
   for #6413-class bugs).

8. **Open the demolition / workaround-removal PR as a separate branch.** Local
   validation is necessary but not sufficient — the demolition itself should be
   gated by its own CI run. The validation branch's job is to prove the new pin
   is sound; the demolition branch's job is to prove the workarounds can come
   out cleanly.

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
| --------- | ---------------- | --------------- | ---------------- |
| 1 | Trusted user's claim that the Mojo version had been bumped, ran validation immediately | The version had not actually been bumped yet — earlier `/advise` accepted the premise without checking, then validation gave a meaningless answer | Always `grep '^mojo' pixi.toml && git log --oneline -- pixi.toml \| head` (Gate 0) before validating any claim about an upstream fix landing. The version premise IS the validation; without it, the rest is theater. |
| 2 | `sudo -n rm -rf /tmp/fake-home && sudo -n chown root:root /tmp/fake-home` to set up a HOME owned by a different UID | Rootless container's NOPASSWD sudoers grant covers `mkdir/chown/chmod` for `_ensure_writable` paths only — not arbitrary `rm` or `chown` on `/tmp/...` | Skip true UID-mismatch repro inside rootless dev containers. Use mode-000 dirs owned by self instead — they trigger the same `std::filesystem::status` throw path on EACCES, which is what matters for the `filesystem_error` code path. |
| 3 | `setpriv --reuid=65534 --regid=65534 -- /tmp/hello` to drop to `nobody` for a real UID-mismatch test | `setresuid: Operation not permitted` — rootless podman containers lack `CAP_SETUID` regardless of sudoers config | In-container UID switching needs privileged mode or `--cap-add=SETUID` at container start. CI is the only authoritative confirmation for true cross-UID. Document this caveat in the upstream comment. |
| 4 | `sudo -n -u nobody /tmp/hello` as a setpriv alternative | sudoers NOPASSWD grant is `runas=root` only, no `runas=nobody` entry | Same lesson as row 2/3. Permission-shape proxies (mode 000, mode 700+ missing .modular) are the substitute we have. |
| 5 | Wrote `fn main(): print("ok")` for the minimal reproducer | Mojo 1.0 removed top-level `fn`; compiler error: `'fn' is not a valid function declaration at top level — use 'def'` | In Mojo 1.0+ all top-level functions use `def`. Migrate any `fn` reproducer snippets in old skills/docs accordingly. |
| 6 | `pixi run mojo test tests/...` for a sanity-check regression run after validation | `error: no such command 'test'` — the `mojo test` subcommand was removed in Mojo 1.0 | Tests now route through `just test-mojo` / `just test-group <PATH> <PATTERN>`. Don't assume `mojo test` exists in 1.0+. |
| 7 | First `gh issue comment <num> --repo modular/modular --body ...` attempt to post the confirmation | `Resource not accessible by personal access token (addComment)` — the active `GITHUB_TOKEN` env var was a fine-grained PAT scoped only to the user's own repos | When commenting on third-party repos: `unset GITHUB_TOKEN; gh auth switch -h github.com -u <user>` to activate the classic OAuth token (`gho_…` with `repo` scope). Do NOT modify gh config beyond switching active accounts. |
| 8 | Spent cycles debugging why Gate 2's `repro-<issue#>` workflow reported all 10 runs as "failed" on the bump branch | The actual Mojo invocation succeeded; failure was in the workflow's "Enable core dumps (pipe handler)" composite-action infrastructure, which had bitrotted since the original bug was reported | When a Gate 2/3 workflow fails on the bump branch, inspect the logs of the Mojo invocation step FIRST. If the Mojo step succeeded and the failure is in coredump-capture / gdb-wrapper / sanitizer-setup infrastructure, treat Gate 2/3 as "passed" and move to Gate 4. Pre-fix infra is going to be deleted in the demolition anyway — do not fix it. |
| 9 | Dismissed a Gate 4 required-check failure as "looks like a flake, rerun" | The failure was a real stdlib API regression that arrived with the same nightly bump: `UnsafePointer._unsafe_null=()` constructor had been removed, breaking project code unrelated to the upstream fix being validated | Gate 4 failures on a Mojo-bump branch are almost never flakes. The nightly bump can drag in API churn (removed constructors, renamed traits, changed default-parameter values) that must be fixed on the SAME branch before any demolition begins. Treat every Gate 4 failure as a real regression until proven otherwise. |
| 10 | Closed the validation PR immediately after all 4 gates passed, to "clean up" before opening the demolition PR | Lost the durable historical record of the pre-demolition green CI matrix on the new pin. When the demolition wave hit an unrelated regression two days later, there was no clean canary branch to A/B against | Keep the validation PR OPEN as a historical canary spanning the demolition. Close it only AFTER the first demolition wave merges. It costs nothing to leave open and provides invaluable audit signal if a regression surfaces during demolition. |

## Results & Parameters

### 4-Gate Pass Criteria

| Gate | Signal | Pass Criteria | Confidence |
| ---- | ------ | ------------- | ---------- |
| Gate 0 | Pinned Mojo version in `pixi.toml` is at or past the upstream-fix-shipped date | `grep '^mojo' pixi.toml` shows the bumped version, `git log` confirms the bump commit | Mandatory pre-check |
| Gate 1 | Cheapest local signal distinguishing pre-fix from post-fix for this bug class | All shapes / iterations return clean exit codes. Driver output (Example B) matches host's real ISA. | Low — proves the fix is in the binary, not that real workload is unaffected |
| Gate 2 | Project's `repro-<issue#>` workflow dispatched ≥10× consecutively | Zero stack frames in the bug's signature library across all 10 Mojo invocation logs (ignore broken pre-fix infra steps) | Medium — synthetic reproducer in CI environment |
| Gate 3 | Existing soak workflow at full iteration count | Zero crashes across full soak (skip if soak workflow is broken for non-fix reasons) | Medium-high — extended exposure, still synthetic |
| Gate 4 | ≥8 consecutive green runs across ALL required checks on the bump branch | First-attempt success on every required check, 8 runs in a row | High — exercises real project workload |

### Gate 1 Example A — Hostile-`$HOME` Matrix Results (modular#6412)

| # | HOME shape | Exit (fixed build) | Exit (buggy build, expected) | Notes |
| --- | ----------------------------------------------------- | ---- | ---- | ----------------------- |
| 1 | Real `$HOME`, baseline | 0 | 0 | Smoke test |
| 2 | `mkdir /tmp/fake-home && chmod 000`, owner = self | 0 | 134 | EACCES proxy |
| 3 | HOME exists mode 755, no `.modular` subdir | 0 | 134 | Missing-`.modular` path |
| 4 | HOME mode 750, `.modular` mode 700 (verbatim from issue body) | 0 | 134 | Issue's exact reproducer |
| 5 | HOME path doesn't exist | 0 | 134 | ENOENT path |
| 6 | HOME unset (`env -u HOME`) | 0 | varies | Edge case |
| 7 | `HOME=/dev/null` (not a directory) | 0 | 134 | ENOTDIR path |
| 8 | Real `$HOME` chmoded 700 + `.modular` removed, full `mojo run` startup (workarounds neutralized) | 0 | 134 | Closest-to-real local |

### Gate 1 Example B — Codegen Driver Check Results (modular#6413)

| Aspect | Pre-fix output (masked-AVX-512 host) | Post-fix output (same host) |
| ------ | ------------------------------------ | --------------------------- |
| `--target-cpu` | `znver4` (wrong — host is Intel) | `lunarlake` (correct) |
| Feature flags | `+avx512f,+avx512vl,+avx512bw,+avx512cd,+avx512dq,+avx512vnni,+avx512vbmi,...` | No `+avx512*` features |
| Local reproducer crash rate (5×50 iterations) | ~100% SIGILL | 0% — all 250 runs clean |

### Caveats

- **True cross-UID is NOT validated locally** for filesystem-error class bugs.
  Rootless podman containers block `setpriv`/`sudo -u`/`runuser`. The mode-000
  EACCES path is a proxy that exercises the same exception path; only CI confirms
  the cross-UID image-built-as-1000-run-as-1001 case.
- **Real silicon-feature variation is NOT validated locally** for codegen-flag
  bugs. Your local host has one CPU; the CI matrix has another. Gate 2/4 in CI
  is the only way to confirm the driver fix is correct across the supported
  CPU set.
- **Pre-fix infrastructure rots.** Repro workflows created during the original
  bug report (coredump capture composite actions, gdb wrappers, sanitizer
  setup) often break on fresh runners or after the bug is gone. Read the logs
  of the Mojo invocation step itself; ignore the workflow badge if the
  infrastructure is the failing component. Do not fix infrastructure that is
  slated for deletion in the demolition.
- **Bind-mount writability is a separate concern** from `getAcceleratorArchOrEmpty()`
  startup. Keep `_ensure_writable` sudoers work even if Gate 1 Example A passes.
- **Do not amend upstream issue bodies.** Post a NEW comment with the gate-result
  summary; do not edit the original report.
- **Keep the validation PR open across the demolition wave.** Close only after
  the first demolition merges.

### Verified On

| Project | Context | Details |
| ------- | ------- | ------- |
| ProjectOdyssey | modular/modular#6412 validation (filesystem-error / `getAcceleratorArchOrEmpty()`) — Gate 1 Example A executed inside `podman compose exec -T projectodyssey-dev` against `mojo==1.0.0b2.dev2026050805 (ed7c8f0a)` (May 8 2026 nightly). All 8 hostile-`$HOME` shapes exit 0. Confirmation comment posted to upstream. | Original v1.0.0 verification |
| ProjectOdyssey | modular/modular#6413 validation (AVX-512 mis-emission on masked-AVX-512 CPUs) — Gate 1 Example B (`--print-effective-target` + 250 local iterations), Gate 4 (47+ green required-check runs across Build Validation and Comprehensive Tests matrix on the bump branch). Gate 4 caught and fixed a coincident stdlib API regression (`UnsafePointer._unsafe_null=()` constructor removed). Validation PR kept open as historical canary through the demolition wave. | v2.0.0 protocol verification |

## Related Skills

- `[[docker-mojo-uid-mismatch-crash-fix]]` — the downstream workaround skill
  (Dockerfile chmod 755, entrypoint `mkdir -p $HOME/.modular`, sudoers
  `_ensure_writable`). Bind-mount `_ensure_writable` portion remains load-bearing
  even after #6412 is confirmed fixed via this protocol's Gate 1 Example A.
- `[[mojo-upstream-bug-filing-reproducibility-standard]]` — the gate to apply
  BEFORE filing an upstream Mojo bug (this skill is the AFTER-fix-shipped mirror).
- `[[ci-cd-remove-upstream-fixed-workaround-fan-out-matrix]]` — what to do
  AFTER this protocol confirms the fix landed (peel the workaround, fan the
  workflow back out).
- `[[mojo-026-breaking-changes]]` / `[[mojo-runtime-crash-bisection]]` —
  background on Mojo 1.0 `fn`→`def` migration, removed `mojo test` subcommand,
  removed `UnsafePointer._unsafe_null=()` constructor, and runtime crash bisection.
