---
name: planning-unmerged-parent-contract-compile-smoke-gate
description: "Plan an issue whose dependency parent issue is NOT yet merged (verified via `gh pr list --search '<N>' --state all` returning `[]`) but has an APPROVED plan on file. Consume the parent's approved-plan contract (function signatures, struct field names, return types) instead of re-implementing or hedging — but mandate a compile-smoke-test (`pixi run mojo build --Werror`) as the FIRST verification step immediately after the parent PR merges to catch contract drift. When a reviewer NOGOs the plan for unverified APIs, Read each flagged API's on-disk source line NOW and revise every assumption that was wrong — empirically 4-of-4 flagged assumptions were wrong (2 would not have compiled, 1 would silently have produced wrong loss). Assume a 100% wrong-rate on any cited-but-unread API. Grep-verify every numeric count claim (parameter counts, field counts) against the current tree AND flag same-line coordination hazards when multiple planned PRs touch identical stale comments. List every external API you cite but did NOT `Read` in a dedicated 'Unverified API Assumptions' section so reviewers can target verification. For random-init deep-network convergence thresholds, use a two-tier assertion (hard floor `loss[final] < loss[0]` + issue-prescribed `loss[final] < 0.95 * loss[0]`) — never weaken the issue's threshold; mitigate on data/hyperparams (more samples, larger bias amplitude, warm-up epoch). Grep for cross-file callers (`grep -rn 'fname(' --include='*.mojo'`) before changing a per-example function's signature. Smoke-run the example's `main()` itself, not just an importing test file. **Validation-only sub-case (v1.2.0):** when the child issue is validation-only (run a script, capture a log, assert a criterion — no code corrections in this task), the SAME plan-authoring discipline applies to the entrypoint path, CLI flag names, batch log format, data-loader defaults, container invocation form (`just shell -c '<cmd>'`), and wall-clock budget — every one is a cited-but-unread assumption unless the parent PR has merged. For log-parsers, mandate a `parsed N > 0` sanity check so a format mismatch fails LOUDLY instead of producing a garbage summary next to an exit-0 wrapper. For loss-decrease criteria on short/noisy runs, prefer a smoothed trend (linear fit slope) over first-decile-vs-last-decile means; a monotonically-decreasing epoch can still fail a decile comparison if the last decile plateaus above the first decile due to noise. Include an 'Assumption Mapping for Mechanical Re-Plan' table (Assumption → File/line to fix once parent merges) so re-planning after dep merge is line-anchored and mechanical. Flag container-network assumptions (dataset auto-download inside the podman network namespace) and gitignored-artifact-attachment (attach via `gh pr comment --body-file` when `logs/` is gitignored). **Prerequisite-gate + dispatch-table sub-case (v1.3.0):** when the child plan IMPORTS symbols the unmerged sibling introduces (e.g. `CompletionQueue`, `StageName` from a package that does NOT yet exist on `origin/main`), the plan's FIRST implementation step must be a concrete PREREQUISITE GATE that STOPS if the package directory is absent — not a prose 'Depends on #NNNN' note. Verify empirically before planning: `git fetch origin && git log --oneline origin/main | grep '(#<dep>)'` and `test -d <path/the/dep/creates>`. Any op/route/dispatch table in a plan must resolve EVERY enumerated case to a concrete named callable with a re-grepped `file:line` — never 'dispatch job.op to module X'; when NO clean public seam exists for a case, say so explicitly and pick the minimal one rather than silently leaving the gap. Re-grep every cited `file:line` right before emitting the plan; a `~` or an un-verified line number is a reviewer ding (and a signal you never opened the file there). When a test double stands in for a real interface used by all later tests, enumerate its FULL mutator surface — never 'etc.'. Anticipate the MINOR-tightening cluster a reviewer demands even on a sound design: catch `BaseException` (not `Exception`) in a worker whose result is read via `future.result()` in a callback thread; specify unspecified helper paths (lock-file path); derive an invariant's target set from `__all__` rather than hardcoding private names AND add a non-empty guard so the invariant cannot pass vacuously. Use when: (1) planning issue B where B depends on unmerged issue A but A has an approved plan comment, (2) a reviewer NOGOed a plan for cited-but-unread APIs and you're revising, (3) about to cite an API signature (`randn`, `AnyTensor.store`, `cross_entropy`) you have not `Read`, (4) writing a numeric count into a plan that another planned PR also touches, (5) asserting a loss-decrease threshold on random-init deep networks, (6) changing a per-example function's signature and unsure whether other files call it, (7) authoring a validation-only issue that runs a script produced by an unmerged parent, (8) writing a bash wrapper + Python log-parser pair without a `parsed N > 0` sanity check, (9) picking a wall-clock budget or fallback batch count by heuristic with no benchmark data, (10) planning any issue in a stacked/serialized epic where the issue 'Depends on #NNNN', (11) writing a plan that imports symbols a sibling PR introduces, (12) any plan containing an op/route/dispatch table, (13) re-planning after a plan-review NOGO whose findings are 'hand-waved dispatch' or 'unverified prerequisite'."
category: architecture
date: 2026-07-04
version: "1.3.0"
user-invocable: false
verification: unverified
history: planning-unmerged-parent-contract-compile-smoke-gate.history
tags:
  - planning
  - nogo-revision
  - unmerged-parent
  - approved-plan-contract
  - compile-smoke-test
  - contract-drift
  - verify-each-flagged-api-on-disk
  - grep-verify-counts
  - same-line-coordination-hazard
  - unverified-api-assumptions
  - two-tier-loss-threshold
  - random-init-convergence-hypothesis
  - cross-file-caller-grep
  - smoke-run-example-main
  - validation-only-task
  - log-parser-sanity-check
  - smoothed-trend-vs-decile-means
  - container-network-assumption
  - gitignored-artifact-attachment
  - wall-clock-heuristic-without-benchmark
  - assumption-mapping-for-mechanical-replan
  - prerequisite-gate-step-zero
  - imports-from-unmerged-sibling
  - dispatch-table-named-callable
  - resolve-every-op-to-file-line
  - document-missing-public-seam
  - reverify-line-numbers-before-emit
  - test-double-full-surface
  - stacked-serialized-epic
  - baseexception-in-worker-future
  - invariant-from-dunder-all-nonempty-guard
---

# Planning against an Unmerged Parent — Contract + Compile-Smoke Gate

## Overview

| Field | Value |
|-------|-------|
| **Date** | 2026-07-04 |
| **Objective** | Capture the planning meta-discipline for authoring issue B whose dependency parent issue A is NOT yet merged (`gh pr list --search "<A>" --state all` returns `[]`) but has an APPROVED plan comment on file. Consume the parent's approved-plan contract instead of re-implementing or hedging, and gate the whole downstream plan on a compile-smoke-test the moment A's PR merges. When a reviewer NOGOs the plan for unverified APIs, treat that as a 100%-wrong-rate signal on every cited-but-unread symbol: Read each flagged API's on-disk source NOW and revise every assumption. Add same-line coordination-hazard scans, an Unverified-API-Assumptions section for every cited-but-unread symbol, a two-tier loss threshold that preserves the issue-prescribed target, a cross-file-caller grep before changing a per-example function signature, and a smoke-run of the example's `main()` in addition to any test-file compile. |
| **Outcome** | Planning artifact produced; the training epoch this plan targets has NOT been executed. Learnings are from an adversarial plan review + a NOGO'd R0 → verified R1 revision, not from a green CI run. |
| **Verification** | unverified — planning meta-skill; the ProjectOdyssey plan itself was reviewed but the resulting training epoch has not been executed. |
| **History** | v1.0.0 (2026-07-02): initial capture from ProjectOdyssey issue #5516 plan review (parent issue #5515 unmerged; only an approved-plan comment existed). Seven learnings distilled from six unverified-API assumptions plus a same-line-coordination hazard. v1.1.0 (2026-07-02): amended after a NOGO→R1 revision on the same #5516 plan revealed that 4-of-4 reviewer-flagged unverified APIs were WRONG (2 would not compile, 1 would silently produce wrong loss). Added the NOGO-verify-each-flagged-API-on-disk pattern as the primary revision anchor, plus four sub-patterns: hard-floor-before-percent-threshold, cross-file-caller-grep, smoke-run-example-main, and the "name-collision with overload family" trap (`.set` has 12 dtype overloads and would confuse search — `.store[dtype]` was correct but was a coin flip in R0). v1.2.0 (2026-07-02): amended after authoring the plan for ProjectOdyssey #5526 (CIFAR-10 one-epoch loss-decrease validation, depends on unmerged #5525). Extended the meta-discipline to the **validation-only** sub-case where the child issue does not modify code but runs a script produced by the parent and asserts a criterion. Added six sub-patterns: (a) log-parser sanity check (`parsed N > 0`) so a batch-log format mismatch fails loudly instead of a wrapper-exits-0-with-garbage-summary false-negative; (b) smoothed-trend loss-decrease criterion (linear fit slope) over first-decile-vs-last-decile means for short/noisy runs; (c) an explicit "Assumption Mapping for Mechanical Re-Plan" table (Assumption → File/line to fix once parent merges); (d) container-network assumption flag (CIFAR-10 auto-download inside podman namespace may be restricted); (e) gitignored-artifact attachment via `gh pr comment --body-file` when `logs/` is `.gitignore`d and cannot be committed; (f) wall-clock budget/fallback heuristics (60-min threshold, `MAX_BATCHES=200` fallback) must either cite benchmark evidence or be flagged as heuristic-without-data. v1.3.0 (2026-07-04): amended from ProjectHephaestus issue #1812 (a worker-pool module that imports symbols from unmerged sibling #1811; epic #1809). R0 plan got a B / NOGO; R1 addressed every finding. Extends the discipline from the DEPENDENCY-IMPORT and DISPATCH-TABLE angle: (a) a plan importing symbols an unmerged sibling introduces (`CompletionQueue`, `StageName`) must make its FIRST implementation step a concrete PREREQUISITE GATE that STOPS if the package dir is absent — verified via `git log --oneline origin/main \| grep '(#<dep>)'` + `test -d <path>` — not a prose "Depends on #NNNN" note (R0's "Confirmed via gh issue view" was a MAJOR finding); (b) every op/route/dispatch-table case must resolve to a concrete named callable with a re-grepped `file:line`, never "dispatch job.op to module X" (R0's six-op `_run_git` hand-wave was NOGO'd), and when no clean public seam exists for a case, document that and pick the minimal one rather than leave the gap (the `clone` op had only a private `_ensure_clone` in a coverage-omitted module → direct `git_utils.run(["gh","repo","clone",...])`); (c) re-grep every cited `file:line` right before emitting — R0's `~500` (actual 864), `204` (actual 104), and a wrong test path (`tests/unit/automation/` vs `tests/unit/validation/`) were each a ding; (d) a test double standing in for "the interface used by all later tests" must enumerate its FULL mutator surface, never "etc."; (e) the MINOR-tightening cluster a reviewer demands even on a sound design (catch `BaseException` in a `future.result()`-read worker; specify the lock-file path; derive an invariant's target set from `__all__` + a non-empty guard). |

> This skill is about the **PLAN-AUTHORING** angle when the dependency parent is still just a plan on paper.
> For the case where the parent is ALREADY MERGED and just needs to be read from `main`, see
> `planning-dependent-issue-unverified-upstream`. For the general "did this issue's premise even
> survive the last refactor?" audit, see `planning-verify-issue-premise-before-implementing`.
> This skill covers the specific gap those two leave: parent-plan exists, parent-code does NOT, and you
> are about to transcribe signatures from the plan comment into your own plan as if they were merged code —
> AND the NOGO-revision loop when a reviewer catches you doing exactly that.

## When to Use

- Planning issue B when B depends on unmerged issue A but A has an approved plan comment (verified: `gh pr list --repo <org>/<repo> --search "<A>" --state all --json number,state` returns `[]` and the plan comment is grade-B / GO).
- **A reviewer NOGOed your plan citing "unverified API assumptions" and you are writing R1.** Before revising a single line, `Read` each flagged API's source. Assume 100% wrong-rate on cited-but-unread symbols until proven otherwise on disk.
- About to cite an API signature (`randn`, `AnyTensor.store`, `cross_entropy`, layer constructor kwargs) you have NOT `Read` in the source of truth.
- Writing a numeric count into a plan (e.g. `"total trainable parameters: 81"`, `"6 conv layers"`, `"20 BN gammas"`) that another planned PR also touches on the same line.
- Asserting a loss-decrease threshold (e.g. `"loss drops 5% in 10 batches"`) on a random-init deep network after only a handful of batches — especially when the issue prescribes the threshold and you cannot weaken it.
- Changing a per-example function's signature (`train_epoch`, `evaluate`, `build_batch`) and unsure whether other files call it — the search for callers must run before the plan lands.
- **(v1.2.0)** Authoring a **validation-only** child issue whose entire job is to run a script the parent PR will produce, capture a log, and assert a criterion (loss decrease, accuracy floor, runtime under budget). Every path/flag/log-format/data-loader-default/container-invocation is a cited-but-unread assumption unless the parent has merged.
- **(v1.2.0)** Writing a bash wrapper + Python (or Mojo) log parser pair that gates PR readiness on a scalar criterion (loss decreased, accuracy above threshold). Missing a `parsed N > 0` sanity check means a format mismatch makes the wrapper exit 0 (script ran) while the summarizer produces garbage — a false-negative NOGO or, worse, a false-positive GO.
- **(v1.2.0)** Picking a wall-clock budget (e.g. "60 minutes"), a fallback batch count (e.g. `MAX_BATCHES=200`), or any convergence-window heuristic by intuition with no benchmark data cited.
- **(v1.2.0)** Asserting a loss-decrease criterion on a SHORT (< 100 batch) or noisy run using first-decile-vs-last-decile means; a legitimately monotonically-decreasing run can still fail this if the last decile plateaus above the first decile due to noise on a small subset.
- **(v1.2.0)** Planning to attach a run artifact (log, CSV, image) to a PR when the output directory (e.g. `logs/`) is gitignored — `git add` will silently fail, so the plan must either whitelist the exact file (`git add -f`) or attach via `gh pr comment --body-file` instead.
- **(v1.2.0)** Planning any command that runs inside a container (`podman`, `docker`, `just shell -c '<cmd>'`) where dataset auto-download depends on egress out of the container's network namespace.
- **(v1.3.0)** Planning any issue in a **stacked / serialized epic** where the issue body says "Depends on #NNNN" and that dependency is not yet merged (epic like ProjectHephaestus #1809 with 14 serialized children #1810–#1823). The "Depends on" line is a HAZARD marker, not a plan step — the plan must convert it into a concrete prerequisite gate.
- **(v1.3.0)** Writing a plan whose test/impl code **imports a symbol a sibling PR introduces** (a class, enum, or function that does NOT exist on `origin/main` yet — e.g. `CompletionQueue`, `StageName` from a package the sibling creates). The plan must not let the implementer write tests against nonexistent symbols.
- **(v1.3.0)** Any plan containing an **op / route / dispatch table** (a `job.op → handler`, a command router, a stage dispatcher). Every enumerated case must resolve to a concrete named callable at a verified `file:line`.
- **(v1.3.0)** **Re-planning after a plan-review NOGO** whose findings are "hand-waved dispatch" (a table that says "dispatch to module X" without naming the function per case) or "unverified prerequisite" (a prose "Depends on #NNNN" with no verification step and no gate).

## Verified Workflow

<!-- The literal token "## Verified Workflow" is required by scripts/validate_plugins.py.
This skill's verification level is "unverified" — the PROPOSED WORKFLOW subsection below
carries the real semantics. Do not read this heading as an implicit warranty. -->

### Proposed Workflow (UNVERIFIED — planning artifact only)

> **Warning:** This workflow was distilled from an adversarial review of an unexecuted plan
> (ProjectOdyssey #5516) plus a NOGO→R1 revision on the same plan. No downstream training run
> has produced green CI against it. Treat every checklist item as a hypothesis; the compile-smoke-test
> and the smoke-run-example-main step are the only gates that empirically discharge the
> "parent plan == parent code" and "test-file compile == example runs" assumptions.

### Quick Reference

```bash
# 0. NOGO REVISION LOOP — if a reviewer flagged N unverified APIs, `Read` each of the
#    N source lines BEFORE revising. Do not attempt to skip this by adding a "verify later"
#    step to the plan. Empirically observed: 4-of-4 flagged APIs were wrong on first read.
Read src/.../tensor_creation.mojo   # for each flagged symbol
Read src/.../loss.mojo
Read src/.../any_tensor.mojo

# 1. Confirm the parent dependency is NOT yet merged (returning [] means the plan
#    is a contract, not a fact):
gh pr list --repo <org>/<repo> --search "<PARENT_ISSUE_N>" --state all --json number,state

# 2. Grep-verify every numeric count claim BEFORE writing it into the plan:
grep -cE '<pattern>' <path>

# 3. Detect same-line coordination hazards (other planned PRs touching the same file):
gh pr list --repo <org>/<repo> --state open --search "<filename>" --json number,title,headRefName

# 4. Immediately after parent PR merges, run compile-smoke-test as verification step 1:
pixi run mojo build --Werror path/to/entrypoint.mojo

# 5. Cross-file-caller grep before changing a per-example function signature:
grep -rn 'train_epoch(' --include='*.mojo'   # substitute your function name

# 6. Smoke-run the EXAMPLE's own main(), not just a test file that imports from it:
pixi run mojo run examples/<arch>/train.mojo --epochs 1 --batch-size <small>

# 7. For any random-init deep-network convergence claim, encode a two-tier assertion.
#    NEVER weaken the issue-prescribed threshold; mitigate on data/hyperparams side.
#    hard floor: loss[final] < loss[0]         (must hold, else training regressed)
#    issue-prescribed: loss[final] < 0.95 * loss[0]   (target from issue; do not soften)

# 8. (v1.3.0) PREREQUISITE-GATE verification when the plan imports symbols an unmerged
#    sibling introduces. Run these BEFORE writing the plan and make step 0 a hard gate:
git fetch origin
git log --oneline origin/main | grep -E '\(#1811\)'   # dep PR merged? (empty => NOT merged)
test -d hephaestus/automation/pipeline/ && echo "pkg present" || echo "PKG ABSENT — gate must STOP"
#    Plan step 0 (literal): "STOP if `hephaestus/automation/pipeline/` is absent — do not
#    write tests against CompletionQueue/StageName until #1811 has merged and this dir exists."

# 9. (v1.3.0) Re-grep EVERY cited file:line right before emitting the plan. A `~` or a
#    guessed number is a reviewer ding and a signal you never opened the file there.
grep -n 'def run_agent_session' hephaestus/automation/session_runner.py   # confirm 864, not ~500
grep -n 'self\.lock' hephaestus/automation/worktree_manager.py            # confirm 104, not 204
```

### Detailed Steps

1. **If revising a NOGOed plan: `Read` every flagged API's source line NOW.**
   The reviewer's NOGO on "unverified API assumptions" is a 100%-wrong-rate signal until
   disproven per-symbol on disk. Do not respond by adding a "verify later" step to the plan —
   that is what got you here. For each flagged symbol, open the source file, find the exact
   `fn`/`def`/parametric-signature line, and either (a) confirm your R0 signature matches
   and note the line-anchored citation, or (b) revise every downstream call site that used
   the wrong signature. Empirically observed on ProjectOdyssey #5516: 4 flagged, 4 wrong —
   2 would not have compiled, 1 would silently have produced wrong loss, 1 was correct-by-coin-flip.

2. **Confirm the parent is unmerged and its plan is approved.**
   Run `gh pr list --repo <org>/<repo> --search "<PARENT_ISSUE_N>" --state all --json number,state`.
   An empty list (`[]`) means no PR exists yet — the parent is only a plan. Then read the parent
   issue's most recent plan comment and confirm it carries an explicit approval grade (grade-B / GO
   is the minimum in this codebase). If the plan is not yet approved, STOP: you cannot consume a
   contract that hasn't been ratified.

3. **Consume the contract, do not hedge or re-implement.**
   Once the parent plan is approved, transcribe function signatures, struct field names, and return
   types verbatim from the plan comment into your child plan. Do NOT invent "just-in-case" fallback
   code paths for the case where the parent plan doesn't ship — that hedging noise buries the real
   contract and doubles review surface. If the parent plan lands with drift, the compile-smoke-test
   in step 6 catches it; don't pre-hedge.

4. **List every cited-but-unread API in an `## Unverified API Assumptions` section.**
   For every symbol you referenced without `Read`-ing its source (`randn`, `AnyTensor.store`,
   `cross_entropy` label dtype, layer constructor kwargs), add a row to a dedicated section with
   columns: Symbol | Assumed Signature | Where Cited | Verify With. This gives the reviewer a
   targeted attack surface and gives the implementer an explicit pre-flight list. See the
   template in Results & Parameters. If a reviewer NOGOs on this section, jump to step 1.

5. **Grep-verify every numeric count claim AND scan for same-line coordination hazards.**
   For each count assertion (e.g. `"total trainable parameters: 81"`, `"6 conv layers"`), run a
   `grep -cE` against the current tree to derive the number from source. Then run
   `gh pr list --repo <org>/<repo> --state open --search "<filename>" --json number,title,headRefName`
   to see whether any OTHER open PR is planned to touch the same file. If two PRs both plan to edit
   the same stale comment line (e.g. `train.mojo:311 "Total trainable parameters: 84"`), coordinate:
   either sequence the merges with an explicit note, or reduce one PR's scope so it doesn't touch
   the shared line. On rebase, the pre-fixed line appears as an empty hunk — drop it with
   `git commit --amend --no-edit`; no merge conflict is expected.

6. **Gate everything downstream on a compile-smoke-test the moment the parent PR merges.**
   Verification step 1 of the child implementation is `pixi run mojo build --Werror
   path/to/entrypoint.mojo`. If that fails, the parent implementer drifted from the approved plan
   (renamed `ResNet18Velocities` to `Velocities`, changed return tuple order, dropped a kwarg) and
   the child plan's transcribed signatures are stale. Fix the child plan against actual merged code
   BEFORE writing any tests. Do NOT skip this step in favor of "just start writing tests and see
   what fails" — that pushes contract-drift discovery to the slowest feedback loop.

7. **Before changing a per-example function's signature, grep for cross-file callers.**
   Per-example functions like `train_epoch`, `evaluate`, `build_batch` are conventionally
   redefined locally in each example. But that convention is not enforced — some helper may be
   shared. Run `grep -rn 'train_epoch(' --include='*.mojo'` and inspect each hit. If every hit is
   inside `examples/<own_arch>/…` files with their own local definitions, the signature change is
   safe. If any hit is in a shared module or a sibling example's importer, either narrow the
   change or plan a coordinated multi-file edit.

8. **Smoke-run the example's own `main()`, not just a test file that imports from it.**
   A test that imports `train_epoch` proves it compiles but does NOT prove the example's `main()`
   still runs end-to-end (argument parsing, dataset loading, checkpoint save-path resolution can
   all break independently of the function under test). Add `pixi run mojo run
   examples/<arch>/train.mojo --epochs 1 --batch-size <small>` as its own verification step. This
   is cheap for small architectures and is the only step that catches wiring bugs at the top
   level.

9. **Two-tier loss assertion — hard floor BEFORE the issue-prescribed percent threshold.**
   A "loss drops 5% in 10 batches" claim on a randomly-initialized ResNet with untuned SGD is a
   HYPOTHESIS, not a guarantee. Encode a hard floor (`loss_final < loss_initial`, must hold or
   training regressed) BEFORE the issue-prescribed `loss_final < 0.95 * loss_initial` check, so
   failure logs distinguish "no decrease" from "insufficient decrease." **Never weaken the
   issue-prescribed threshold** — the issue is the contract. If the target flakes, mitigate on
   the DATA/hyperparams side: more samples (`3.2×`), larger class-mean bias amplitude (`2×`),
   optional warm-up epoch. Both tiers are asserted; the hard floor gives a cleaner failure
   signal, the issue threshold is what the DoD asks for.

10. **Read any file cited as prior-art precedent.**
    If your plan says "analogous to `examples/lenet_emnist/train.mojo`", you must have opened that
    file and quoted a line-anchored range. A filename in a plan without a line-anchored quote is an
    unverified claim; either read it and cite the actual pattern, or drop the reference.

11. **(v1.2.0) For validation-only child issues: build an "Assumption Mapping for Mechanical Re-Plan" table.**
    When the child issue does not modify code but runs a script produced by an unmerged parent, every
    cited path (`examples/<arch>/train_<data>.mojo`), CLI flag (`--epochs`, `--max-batches`,
    `--data-dir`), batch log format (`step=<i> loss=<f> lr=<f>`), data-loader default (auto-download
    location, cache directory), container invocation form (`just shell -c '<cmd>'` vs
    `podman exec dev bash -c '<cmd>'`), and companion path (e.g. smoke test from the parent) is
    an assumption. List them in a dedicated table with columns:
    `Assumption | Cited As | File/line to fix once parent merges | Verify with`.
    This makes re-planning after the parent PR merges a **mechanical** find-and-replace instead of
    a re-read of the whole plan. Example rows: `entrypoint path | examples/mobilenetv1/train_cifar10.mojo |
    scripts/run_mobilenetv1_cifar10_epoch.sh L12 | grep -l 'train_cifar10' examples/`; `CLI flag names
    | --epochs / --max-batches / --data-dir | scripts/run_*.sh L24-30 | mojo run <entrypoint> --help`.

12. **(v1.2.0) Design log parsers with a `parsed N > 0` sanity check that fails LOUDLY on format mismatch.**
    A bash wrapper that runs `mojo run <script>` and pipes into a Python summarizer can exit 0 (the
    Mojo run succeeded) while the summarizer emits garbage (regex matched nothing). The wrapper's
    exit code is a lie about criterion satisfaction. Mandate that the summarizer:
    (a) `raise SystemExit(1)` if fewer than K loss values are parsed (K = 20 or 10% of expected batches,
    whichever is smaller); (b) print `PARSED n=<N> expected=<E> format=<pattern>` on both success and
    failure; (c) the wrapper propagates the summarizer's exit code. Without this, a batch-log format
    change in the parent script (e.g. `loss=` becomes `train_loss=`) silently produces a false-negative
    NOGO (or worse, a false-positive GO if the empty-list mean is masked by a default).

13. **(v1.2.0) Prefer a smoothed trend (linear fit slope) over first-decile-vs-last-decile means for
    short/noisy runs.** A "mean of first 10% of batches vs mean of last 10% of batches" comparison is
    intuitive but pathological: a legitimately monotonically-decreasing epoch can still fail if the
    last decile plateaus above the first decile due to noise on a small subset. For short (< 200 batch)
    runs, fit a linear regression `loss[i] = a + b * i`, assert `b < 0` (slope negative) alongside
    the issue-prescribed absolute-decrease criterion. Combine with the two-tier hard-floor pattern from
    step 9. Cite the actual number of samples the criterion is asserted on so a reviewer can sanity-check
    the statistical power.

14. **(v1.2.0) Flag container-network assumptions explicitly.**
    A validation script that runs inside a container (`just shell`, `podman exec`) inherits the
    container's network namespace, which may block egress to arbitrary hosts (dataset mirrors,
    package registries). If the plan assumes a first-run auto-download (CIFAR-10, EMNIST, ImageNet
    subset), either (a) verify the container's egress policy against the mirror host, or (b) pre-stage
    the data on the host and bind-mount it into the container. Never plan "the script will download
    on first run" without one of those two, and add a fallback: `if [ ! -d "$DATA_DIR" ]; then echo
    "PLAN.md L<N>: data not present and container egress unverified" >&2; exit 2; fi`.

15. **(v1.2.0) Plan artifact attachment against `.gitignore` up front.**
    If the artifact directory is gitignored (very common for `logs/`, `runs/`, `checkpoints/`),
    `git add` silently no-ops on it and the PR ships without the evidence. Either (a) whitelist the
    specific artifact with `git add -f logs/<specific-file>.log`, (b) copy the artifact into a
    non-gitignored location (`docs/evidence/`) before staging, or (c) attach it via
    `gh pr comment --body-file` after opening the PR. The plan must specify which of the three, and
    include the exact command. A generic "attach the log to the PR" instruction leaves the implementer
    to discover the gitignore silently.

16. **(v1.2.0) Never pick a wall-clock budget or fallback batch count without benchmark evidence — or flag it.**
    A "60-minute wall-clock threshold, fallback to `MAX_BATCHES=200`" pair is not a fact — it is a
    guess. Either cite a benchmark (`prior epoch on <hardware> ran in X minutes for N batches`,
    `parent PR's smoke test on same runner takes Y seconds/batch`) or explicitly label the numbers as
    "heuristic, no benchmark data — reviewer should override if their hardware differs." The
    heuristic path is fine when speed matters more than precision, but the label matters because a
    reviewer cannot distinguish "cited number" from "guessed number" from the plan text.

17. **(v1.3.0) A plan that imports symbols from an unmerged sibling must make its FIRST step a
    concrete PREREQUISITE GATE — not a prose "Depends on #NNNN".**
    When the child plan's test/impl code imports a class or enum the sibling introduces
    (`CompletionQueue`, `StageName`), verify EMPIRICALLY before writing the plan:
    `git fetch origin && git log --oneline origin/main | grep -E '\(#<dep>\)'` (empty output =
    the dep PR has not merged) and `test -d <path/the/dep/creates>`. If the package directory
    (e.g. `hephaestus/automation/pipeline/`) does not exist on `origin/main` and the dependency
    is unmerged, the plan must SAY SO explicitly and make implementation step 0 a gate that
    STOPS if the package is absent — so the implementer never writes tests against nonexistent
    symbols. A prose "Depends on #1811" note plus "Confirmed via `gh issue view 1811`" is NOT a
    gate; the plan reviewer flags it as a MAJOR finding because there is no verification step and
    the imports are against symbols not on `main`. This is the PRE-implementation analogue of the
    post-merge compile-smoke gate (step 6): the compile-smoke gate catches drift after the sibling
    merges; the prerequisite gate stops work before it merges.

18. **(v1.3.0) Every op / route / dispatch-table case must resolve to a concrete named callable
    at a verified `file:line` — never "dispatch to module X".**
    A plan that says a router "dispatches `job.op` to `worktree_manager` / `git_utils` calls" for
    six ops without naming which function handles each op is hand-waving and gets NOGO'd. Write a
    full table: each op → exact function + re-grepped line. **Corollary — when NO clean public seam
    exists for a case, say so explicitly and pick the minimal one.** If the only handler for an op
    is a private `_ensure_clone` in a coverage-omitted module, do not silently leave the gap for the
    implementer: document the absence and choose a direct minimal call
    (`git_utils.run(["gh", "repo", "clone", ...])`). The dispatch table is where a reviewer probes
    for "which real function runs here?" — answer it for every enumerated case.

19. **(v1.3.0) Re-grep every cited `file:line` right before emitting the plan.**
    Plan reviewers verify cited line numbers. A `~500` or a guessed `204` is a reviewer ding — and
    a signal that you never actually opened the file at that spot. Right before emitting, re-grep
    each citation: `grep -n 'def run_agent_session' <file>` (confirmed 864, not the R0 `~500`),
    `grep -n 'self.lock' <file>` (confirmed 104, not the R0 `204`), and re-derive any cited test
    path from `ls` (`tests/unit/validation/`, not the R0-guessed `tests/unit/automation/`). Cheap
    to fix, but each stale ref costs a review round.

20. **(v1.3.0) When a test double stands in for a real interface "used by all later tests",
    enumerate its FULL surface — never "etc.".**
    A `FakeGitHub` (or any fake that downstream stage/coordinator tests depend on) must list its
    COMPLETE mutator method set, not "a few mutators + etc.". Downstream tests build on the fake's
    contract; deferring "etc." leaves a consumer contract unspecified and the reviewer will demand
    the full list. Defer nothing that a consumer contract needs.

21. **(v1.3.0) Anticipate the MINOR-tightening cluster a reviewer demands even on a sound design.**
    Even a well-architected plan draws a small predictable set of MINOR findings; pre-empt them:
    (a) catch `BaseException` (not `Exception`) in a worker whose result is read via
    `future.result()` in a callback thread — a bare `Exception` lets `KeyboardInterrupt`/`SystemExit`
    escape the worker and never reach the future's caller; (b) specify every unspecified helper path
    (a lock-file path, a state-dir path) rather than leaving it "TBD"; (c) derive an invariant's
    target set from `__all__` rather than hardcoding private names, AND add a "set is non-empty"
    guard so the invariant cannot pass VACUOUSLY (an empty target set makes "for each X assert P(X)"
    trivially true). This is the same NOGO→GO convention-guard sub-pattern captured in
    `architecture-executable-convention-guard-pattern`, seen here from the dependency/dispatch angle.

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
|---------|----------------|---------------|----------------|
| 1 | Assumed `randn(shape, dtype, seed=..., mean=..., std=...)` signature without reading `projectodyssey.tensor.tensor_creation`. Transcribed the signature from analogy to numpy / PyTorch. | On-disk (`src/projectodyssey/tensor/tensor_creation.mojo:531`) the signature is `def randn(shape: List[Int], dtype: DType, seed: Int = 0) raises -> AnyTensor` — N(0,1) only, NO `mean`/`std` kwargs. R0 test would not compile. | Any API cited in a plan MUST have been `Read` from source OR flagged in an `## Unverified API Assumptions` section. Analogy to numpy/PyTorch is not a signature source of truth. |
| 2 | Used `AnyTensor.store[DType.float32](idx, val)` without verifying method existence. Skill confirmed `.load[dtype]` exists at `any_tensor.mojo:1479` but `.store` was NOT verified — assumed by read/write symmetry. | On R1 verification `.store[dtype: DType]` DOES exist at `any_tensor.mojo:1499` — but so does `.set()` at line 860 with dozens of dtype overloads. R0 was a coin-flip that landed correct; the search could just as easily have found only `.set` first and been misled. | Grep for the setter form explicitly (`grep -nE 'fn (store\|set\|update)\b' any_tensor.mojo`) before citing. Read/write API symmetry is a heuristic; verify it. "Correct by coin-flip" still counts as an unverified assumption. |
| 3 | Assigned `cross_entropy` labels as `float32` via `AnyTensor.set(idx, Float32(c))`. Mojo-tensor-design skill explicitly warns "update() requires int32 or int64 labels, got float32", but the plan authored float32 labels anyway. | On R1 verification (`src/projectodyssey/core/loss.mojo:260-292`) `cross_entropy` targets MUST be one-hot — SAME SHAPE as logits, not integer class indices at all. R0's integer-label assumption would silently produce wrong loss (not even a dtype-guard raise). Fix: build integer labels, then `one_hot_encode(labels_int, num_classes)` from `src/projectodyssey/data/formats/idx_loader.mojo:246`. | Read the callee's label-shape AND dtype contract in the source BEFORE constructing test tensors. "Integer class indices" is a strong prior from PyTorch/TF, but Mojo `cross_entropy` here uses one-hot. Priors from other frameworks are NOT evidence. |
| 4 | Cited `examples/lenet_emnist/train.mojo` and `examples/alexnet_cifar10/run_train.mojo` as "analogous class-mean-signal convergence tests" but never opened them. Referenced as precedent for the 5% loss-decrease threshold. | If those tests use a different threshold, different data shapes, or different assertion styles, the analogy fails silently and the reviewer has no way to check. A filename without a quote is not evidence. | Any file cited as prior-art precedent MUST be `Read` and quoted with a line-anchored range. A filename in a plan without a line-anchored quote is an unverified claim; drop it or verify it. |
| 5 | Asserted `loss[final] < 0.95 * loss[0]` on 10 batches of random-init ResNet-18 with untuned SGD-momentum (lr=0.01) as a hard CI gate. | 5% decrease over 10 batches from random init on separable-but-noisy synthetic data is plausible-but-not-guaranteed. Random-init deep nets can spend the first several batches on BN adjustment before loss trends down. A "monotone-ish" run gets flagged as regression when it isn't. | Convergence thresholds on random-init deep nets are HYPOTHESES. Use a two-tier assertion: hard floor `loss[final] < loss[0]` (real regression) plus the issue-prescribed `< 0.95 * loss[0]` (target). Never weaken the issue-prescribed threshold; mitigate on data/hyperparams side (more samples, larger bias amplitude, warm-up epoch). |
| 6 | Trusted #5515's approved-plan text as if it were merged code. Read the plan comment, transcribed signatures verbatim, but the implementer may rename `ResNet18Velocities` to `Velocities`, or return `Tuple` instead of a struct, or reorder returns. | Silent drift compiles into the child plan as false facts. The child plan reads consistent but references symbols that don't exist post-merge. Discovery is pushed to the slowest feedback loop (test failures). | Consume the parent contract as a HYPOTHESIS with a mandatory `pixi run mojo build --Werror` compile-smoke-test as verification step 1 immediately after the parent PR merges. That is the ONLY step that empirically discharges the "plan == code" assumption. |
| 7 | Same-line coordination hazard on `train.mojo:311` "Total trainable parameters: 84". Both #5515's plan and this plan touch the identical stale comment line. | Whichever PR merges second gets an empty hunk on rebase (or a merge conflict if lines diverged further). Neither plan flagged the collision in R0. | When grep-verifying a count claim, ALSO grep for other planned PRs touching the same line: `gh pr list --repo <org>/<repo> --state open --search "<filename>" --json number,title,headRefName`. Either coordinate merge order explicitly or narrow one PR's scope so it doesn't touch the shared line. On rebase, drop the empty hunk with `git commit --amend --no-edit`. |
| 8 | Responded to a NOGO-for-unverified-APIs by adding a "verify these APIs before implementation" step to the plan and re-submitting, rather than reading each source line NOW and revising the plan. | Reviewer NOGOs on unverified APIs because the concrete signatures they encode drive downstream test code, tensor-construction code, and assertions. A "verify later" step does not change any of those downstream lines — it just delays discovery of the same bugs. R1 review will re-NOGO on the same grounds. | When a reviewer NOGOs a plan for unverified APIs, Read each flagged API's source line NOW and revise every downstream assumption before re-submitting. Empirical rate on ProjectOdyssey #5516: 4-of-4 flagged assumptions wrong. Assume 100% wrong-rate on cited-but-unread APIs until proven otherwise on disk. |
| 9 | Left the 5%-loss-decrease threshold unqualified when the issue prescribed it, then quietly weakened it to `< loss[0]` after a flaky first test run. | The issue is the contract. Silently weakening the threshold hides the fact that the data / hyperparams don't drive the prescribed convergence. Review will catch it on the diff; if it doesn't, the DoD is violated. | Never weaken an issue-prescribed threshold. Add a hard floor BEFORE the issue-prescribed percent check so failure logs distinguish "no decrease" from "insufficient decrease" — but keep the issue's threshold. Mitigate on the data/hyperparams side (samples×3.2, class-mean bias×2, warm-up epoch). |
| 10 | Assumed `.set` and `.store[dtype]` on `AnyTensor` were interchangeable and picked whichever the plan text made grammatically nicer, without a `grep -nE 'fn (set\|store)\b' any_tensor.mojo`. | Both exist. `.set` has ~12 dtype overloads (`any_tensor.mojo:860`), `.store[dtype]` is parametric (`any_tensor.mojo:1499`). Picking one by aesthetic rather than by verification is a coin flip; it landed correct in R0 but there was no evidence at plan-time distinguishing the two. | Two-of-a-kind API names on the same type require an explicit grep of BOTH forms before citation. "The one I picked exists" ≠ "the one I picked was the right one to pick." Cite the line-anchored source for whichever you choose. |
| 11 | Cited `extract_batch_pair` in the plan as returning "a batch pair" without checking the return type. | On-disk (`src/projectodyssey/data/batch_utils.mojo:76-78`) it returns `Tuple[AnyTensor, AnyTensor]`, which is compatible with the plan's tuple-unpack usage. But at plan-time this was a lucky guess — the same signature space includes `Tuple[AnyTensor, AnyTensor, Int]` or a named struct. | Return-type of every function whose result you tuple-unpack MUST be `Read`. "It returns a pair" is not a signature. `Tuple[T, U]` vs `struct BatchPair { data: T; labels: U }` unpack differently. |
| 12 | Planned to change `train_epoch`'s signature in a per-example file without a `grep -rn 'train_epoch(' --include='*.mojo'` for cross-file callers. Assumed it was local because "every example has its own `train_epoch`". | The convention held here (every hit was inside another example's own `train_epoch` local definition), so the signature change was safe. But the plan authored the change without evidence. If a sibling example or shared helper HAD called it, the change would have broken unrelated examples silently. | Before changing a per-example function's signature, `grep -rn 'fname(' --include='*.mojo'` and inspect each hit. If every hit is inside its own example's local definition, the change is safe. If any hit crosses example boundaries, plan a coordinated multi-file edit. |
| 13 | Ran a Mojo compile of a test file that imports `train_epoch` from the example, treated the successful compile as proof that "the example still runs." | Test-file compile only proves `train_epoch` itself compiles. It does NOT prove the example's `main()` still runs — argument parsing, dataset loading, checkpoint save-path resolution can all break independently of the function under test. | Smoke-run the example's own `main()` end-to-end: `pixi run mojo run examples/<arch>/train.mojo --epochs 1 --batch-size <small>`. This is cheap for small architectures and is the only step that catches wiring bugs at the top level (arg parser, dataset loader, checkpoint path). |
| 14 | **(v1.2.0)** Wrote paths `examples/mobilenetv1/train_cifar10.mojo`, `examples/mobilenetv1/smoke_overfit_one_batch.mojo` into the ProjectOdyssey #5526 plan by inferring from the issue-title pattern, without `grep -r 'MobileNetV1' examples/` or a `gh issue view 5525 --comments` fetch of the parent's approved deliverables. | The parent PR #5525 has not merged, so no file exists to read. The inference from issue-title pattern is a guess — the real path could be under `src/projectodyssey/models/mobilenetv1/`, or be a `pixi run train` recipe, or use `train_cifar.mojo` (no `10`). Reviewer must flag every path in the plan as unverified. | For validation-only issues whose parent is unmerged, every path/flag/entrypoint MUST be either (a) sourced from the parent's approved-plan comment quoted line-anchored, or (b) placed in an "Assumption Mapping for Mechanical Re-Plan" table so the implementer knows exactly what to sweep after the parent PR merges. Inference from title patterns is NOT evidence. |
| 15 | **(v1.2.0)** Designed a bash wrapper (`scripts/run_mobilenetv1_cifar10_epoch.sh`) + Python parser (`scripts/summarize_epoch_log.py`) pair without a `parsed N > 0` sanity check in the Python side. The wrapper propagates `mojo run`'s exit code and pipes into the summarizer for the loss-decrease criterion. | If the parent's actual batch log format is `train_loss=<f>` instead of `loss=<f>`, the regex `loss=([\d.]+)` matches zero lines. The Python parser's `mean(first_10pct) < mean(last_10pct)` comparison on two empty lists produces `nan < nan == False` (or a ZeroDivisionError silently caught elsewhere), so the wrapper exits 0 (Mojo run succeeded) with a garbage summary. A reviewer looking at the log artifact would see a decreasing loss trend and the criterion NOGO'd — false-negative NOGO. Or worse, a default `float('inf')` fallback makes `inf < inf` false but exits 0 masked — false-positive GO. | Every log parser MUST emit `PARSED n=<N> expected=<E> format=<pattern>` and `raise SystemExit(1)` if `N < K` where K is a sanity floor (e.g. 20 loss values or 10% of expected). The wrapper must propagate the summarizer's exit code, not just the Mojo run's. |
| 16 | **(v1.2.0)** Chose "mean of first 10% of batches vs mean of last 10% of batches" as the loss-decrease criterion for a one-epoch CIFAR-10 run with `MAX_BATCHES=200` fallback. | On 200 batches, the first decile is 20 samples and the last decile is 20 samples. A legitimately monotonically-decreasing loss trace can still fail this criterion if the last decile plateaus above the first decile due to noise on the tail (learning rate not yet decayed, batch-norm still adjusting). A reviewer would see a clearly-decreasing loss and the criterion NOGO'd. | For short/noisy runs, use a smoothed trend (linear fit slope `b < 0`) as the primary criterion, or widen the comparison window (first third vs last third; or first quintile vs last quintile). Cite the sample count the criterion is asserted on so a reviewer can sanity-check the statistical power. Combine with the two-tier hard-floor pattern from Attempt 5's lesson. |
| 17 | **(v1.2.0)** Planned to `git add logs/mobilenetv1-cifar10-epoch-<date>.log` and commit the artifact to the PR without checking whether `logs/` is in `.gitignore`. | The ProjectOdyssey repo has `logs/` gitignored (matches the `Logs` note in CLAUDE.md). `git add logs/<file>.log` silently no-ops (or requires `-f`), and the PR ships without the evidence artifact. The reviewer cannot verify the criterion. | Plan artifact attachment against `.gitignore` up front: either (a) `git add -f logs/<specific-file>.log` with a note in the plan, (b) copy the artifact to a non-gitignored location (`docs/evidence/`) before staging, or (c) attach via `gh pr comment --body-file logs/<file>.log` after opening the PR. Specify which of the three, with the exact command, in the plan. |
| 18 | **(v1.2.0)** Planned to run `pixi run mojo run examples/mobilenetv1/train_cifar10.mojo --data-dir /tmp/cifar10` inside `just shell -c '<cmd>'` and rely on the trainer's first-run auto-download of CIFAR-10. | The container's network namespace may block egress to arbitrary mirror hosts. Also, `just shell -c '<cmd>'` is itself an unverified invocation form — the justfile recipe may not accept `-c` and instead requires an interactive shell followed by a manual command. Both assumptions could break the plan on first execution. | For container-run steps: verify the justfile recipe's invocation form (`grep -A5 '^shell:' justfile`) and verify container egress to the dataset mirror, OR pre-stage data on the host and bind-mount it in. Add a fallback preflight: `if [ ! -d "$DATA_DIR" ]; then echo "PLAN: data not present and container egress unverified" >&2; exit 2; fi`. Never plan "the script will download on first run" without confirming the network policy. |
| 19 | **(v1.2.0)** Picked "60-minute wall-clock threshold" and "`MAX_BATCHES=200` fallback if projected epoch > 60 min" by intuition, with no benchmark citation for MobileNetV1-on-CIFAR-10 throughput on the target hardware. | The threshold is neither too aggressive nor too lax by any measured standard — it's a guess. A slower runner blows the budget and the plan looks broken; a faster runner completes so fast the fallback never triggers and the threshold is inert. Reviewer cannot tell "guessed" from "cited" from the plan text. | Either cite a benchmark (`prior epoch on <hardware> ran in X minutes for N batches`, `parent PR's smoke test on same runner takes Y seconds/batch`) or explicitly label the numbers as "heuristic, no benchmark data — reviewer should override if their hardware differs." Both paths are valid; hiding the guess is not. |
| 20 | **(v1.2.0)** Referenced CLAUDE.md sections ("Troubleshooting: Mojo Test Execution and GLIBC Compatibility", "Common Commands", "Language Preference") from the in-context project instructions without re-reading CLAUDE.md from disk in the current turn to confirm the section headings and content still match. | CLAUDE.md may have changed since it was loaded into context (another agent's commit, a PR merged mid-session). The in-context copy is a snapshot, not the current file. Citing a section by name from the snapshot can be stale by seconds. | For plan text that cites configuration/documentation sections, either re-`Read` the file in the current turn or explicitly flag the citation as "from in-context copy, current file may differ." The distinction matters when the plan is reviewed hours later against `main`. |
| 21 | **(v1.2.0)** Wrote the ProjectOdyssey #5526 plan without running `gh issue view 5525 --comments` first, then transcribed inferred deliverables of #5525 (the entrypoint script + smoke test) into the plan as if they were known contract elements. | The dependent-issue premise ("run the script #5525 produces") is the whole plan. If #5525's approved plan (or the merged code, if any) uses different filenames, flags, or a different smoke-test path, every command in the #5526 plan needs revision. Not fetching #5525's plan comment is the exact trap `planning-dependent-issue-unverified-upstream` warns against — but for the plan-only, parent-still-unmerged case. | Before authoring ANY validation-only plan against an unmerged parent, run `gh issue view <parent#> --comments` and `gh pr list --search "<parent#>" --state all --json number,state,headRefName`. If the parent has a merged PR, read the merged tree (see companion skill). If not, quote the approved-plan comment verbatim and mark every transcribed element as "parent-plan contract, verify via compile-smoke-test post-merge." |
| 22 | **(v1.3.0, Hephaestus #1812 R0)** Documented the dependency on unmerged sibling #1811 as a prose "Depends on #1811" note plus "Confirmed via `gh issue view 1811`", then wrote tests importing `CompletionQueue` and `StageName` from `hephaestus.automation.pipeline` — a package that does NOT exist on `origin/main`. | The plan reviewer flagged this as a MAJOR finding: there was no verification step, and the imports were against symbols not on `main`. `git log --oneline origin/main \| grep '(#1811)'` was empty and `test -d hephaestus/automation/pipeline/` failed — the package was absent. An implementer following R0 would write tests against nonexistent symbols. | A plan importing symbols from an unmerged sibling must make implementation step 0 a concrete PREREQUISITE GATE that STOPS if the package dir is absent. Verify EMPIRICALLY at plan-time: `git fetch origin && git log --oneline origin/main \| grep -E '\(#<dep>\)'` + `test -d <path>`. A prose "Depends on #NNNN" is not a gate. (R1 fix: step 0 explicitly stops if `hephaestus/automation/pipeline/` is absent.) |
| 23 | **(v1.3.0, Hephaestus #1812 R0)** Wrote that `_run_git` would "dispatch `job.op` to `worktree_manager` / `git_utils` calls" for six ops, without naming which function handles each op. | The reviewer NOGO'd this as hand-waving: a dispatch table that names a MODULE but not the per-case callable leaves the implementer to guess the seam. One op (`clone`) had NO clean public seam at all — only a private `_ensure_clone` in a coverage-omitted module — and R0 silently left that gap. | Every op/route/dispatch-table case must resolve to a concrete named callable + a re-grepped `file:line`. When no clean public seam exists, say so explicitly and pick the minimal one (R1 fix: full op→function table; `clone` → direct `git_utils.run(["gh","repo","clone",...])` with the missing-seam noted). Do not leave the gap for the implementer. |
| 24 | **(v1.3.0, Hephaestus #1812 R0)** Cited `run_agent_session` at "~500", `self.lock` at "204", and a test path `tests/unit/automation/` — none re-verified before emitting the plan. | The reviewer verifies cited line numbers. Actual lines were 864 and 104; the actual test path was `tests/unit/validation/`. Each stale/approximate ref was a separate ding. A `~` or a guessed number is a signal the file was never opened at that spot. | Re-grep EVERY cited `file:line` right before emitting the plan (`grep -n 'def run_agent_session' <file>` → 864, `grep -n 'self.lock' <file>` → 104) and re-derive test paths from `ls`. Cheap to fix; each stale ref costs a review round. |
| 25 | **(v1.3.0, Hephaestus #1812 R0)** Listed a few mutator methods on the `FakeGitHub` test double followed by "etc.", even though the fake is "used by all later tests" (downstream stage/coordinator tests depend on its contract). | The reviewer demanded the COMPLETE mutator list: downstream tests build on the fake's contract, and "etc." leaves a consumer contract unspecified. Deferring surface a consumer needs is a review round wasted. | When a test double stands in for a real interface used by all later tests, enumerate its FULL mutator surface — never "etc.". Defer nothing that a consumer contract needs. |
| 26 | **(v1.3.0, Hephaestus #1812 R0)** Sound worker-pool design still drew a cluster of MINOR findings: caught bare `Exception` in the worker (result read via `future.result()` in a callback thread), left a lock-file path unspecified, and hardcoded private symbol names in an invariant with no non-empty guard. | Even a well-architected plan draws a predictable MINOR set. Bare `Exception` lets `KeyboardInterrupt`/`SystemExit` escape the worker and never surface at the future's caller; an unspecified helper path is a TBD the implementer must invent; an invariant over hardcoded private names can pass VACUOUSLY (and drifts when `__all__` changes). | Pre-empt the cluster: catch `BaseException` (not `Exception`) in a worker whose result is read via `future.result()`; specify every helper path (lock-file, state-dir); derive an invariant's target set from `__all__` AND add a "set is non-empty" guard so it can't pass vacuously. Reinforces `architecture-executable-convention-guard-pattern` from the dependency/dispatch angle. |

## Results & Parameters

### Verified On

| Repository | Session | Notes |
|------------|---------|-------|
| ProjectOdyssey | GitHub issue #5516 plan (dependency #5515 unmerged) | Session 2026-07-02 — R0 plan reviewed adversarially and NOGO'd (Grade C) for 4 unverified APIs; R1 revision verified each flagged API on disk and found 4-of-4 R0 assumptions wrong. Neither R0 nor R1 has been executed. |
| ProjectOdyssey | GitHub issue #5526 plan (dependency #5525 unmerged) | Session 2026-07-02 — validation-only child issue (run one CIFAR-10 epoch, assert loss decreases). Plan authored without `gh issue view 5525 --comments` and without grep-verifying paths in the current tree, then flagged as v1.2.0 evidence for the validation-only-child-issue sub-case. Plan never executed. |
| ProjectHephaestus | GitHub issue #1812 plan (worker-pool module; depends on unmerged sibling #1811; epic #1809) | Session 2026-07-04 — R0 plan got a **B / NOGO** from the plan reviewer for (a) a prose-only "Depends on #1811" with no prerequisite gate while importing `CompletionQueue`/`StageName` from the not-yet-existing `hephaestus.automation.pipeline`, (b) a hand-waved six-op `_run_git` dispatch table, (c) stale/approximate cited line numbers (`~500` vs 864, `204` vs 104) and a wrong test path, (d) a `FakeGitHub` mutator surface listed with "etc.". R1 re-plan addressed every finding (step-0 prerequisite gate, full op→function table, re-grepped line refs, complete fake surface, MINOR-tightening cluster). **Neither R0 nor R1 was executed / CI-validated — plan only.** |

### Copy-Paste (v1.3.0): Prerequisite gate + dispatch table for an unmerged-sibling import

```bash
# BEFORE writing the plan: prove the sibling has NOT merged and its package is absent.
git fetch origin
git log --oneline origin/main | grep -E '\(#1811\)' || echo "DEP #1811 NOT MERGED"
test -d hephaestus/automation/pipeline/ && echo "pkg present" || echo "PKG ABSENT"

# Plan implementation STEP 0 (make it a hard gate, verbatim in the plan):
#   "STOP if `hephaestus/automation/pipeline/` is absent on the working tree.
#    Do NOT write tests importing CompletionQueue / StageName until #1811 has merged
#    and this package exists. This gate replaces a prose 'Depends on #1811' note."
```

```markdown
## Op Dispatch Table (every case → a concrete named callable at a verified file:line)

| job.op   | Handler (function)                        | Source (re-grepped)                          |
|----------|-------------------------------------------|----------------------------------------------|
| worktree | `worktree_manager.add_worktree`           | hephaestus/automation/worktree_manager.py:NN |
| rebase   | `git_utils.rebase`                        | hephaestus/automation/git_utils.py:NN        |
| clone    | `git_utils.run(["gh","repo","clone",...])`| NO public seam — only private `_ensure_clone` in a coverage-omitted module; minimal direct call chosen and documented |
| ...      | ... (resolve EVERY enumerated op — no "dispatch to module X") | ...                          |
```

### Copy-Paste: NOGO revision loop — Read each flagged API on disk

```bash
# When a reviewer NOGOs on unverified APIs, DO NOT respond by adding a "verify later"
# step to the plan. Read each flagged API's source line NOW.
# Example (from ProjectOdyssey #5516 R1):

# Flagged API 1: randn
Read src/projectodyssey/tensor/tensor_creation.mojo   # line 531
# On-disk: def randn(shape: List[Int], dtype: DType, seed: Int = 0) raises -> AnyTensor
# R0 assumed mean=/std= kwargs — WRONG. Revise the synthetic-data builder.

# Flagged API 2: cross_entropy
Read src/projectodyssey/core/loss.mojo   # lines 260-292
# On-disk: targets MUST be one-hot, same shape as logits.
# R0 assumed integer class indices — WRONG. Add one_hot_encode step.

# Flagged API 3: AnyTensor.store[dtype]
Read src/projectodyssey/core/any_tensor.mojo   # line 1499
# On-disk: store[dtype: DType](self, index, value: Scalar[dtype]) — exists.
# R0 correct-by-coin-flip; document the line-anchored citation now.

# Flagged API 4: extract_batch_pair
Read src/projectodyssey/data/batch_utils.mojo   # lines 76-78
# On-disk: returns Tuple[AnyTensor, AnyTensor] — matches R0's tuple-unpack.
# R0 correct-by-coin-flip; document.
```

### Copy-Paste: Grep for parameter count

```bash
# Count parameter fields declared in a model file. Adjust the pattern for the
# tensor-container convention used in your codebase.
grep -cE '^    var .+_(kernel|bias|gamma|beta): AnyTensor' examples/resnet18_cifar10/model.mojo
```

### Copy-Paste: Compile-smoke-test after parent merges

```bash
# Verification step 1 immediately after the parent PR merges. If this fails, the
# parent implementer drifted from the approved plan — fix the child plan's
# transcribed signatures against actual merged code before writing tests.
pixi run mojo build --Werror path/to/entrypoint.mojo
```

### Copy-Paste: Cross-file caller grep before signature change

```bash
# Before changing a per-example function's signature, prove no other file calls it.
# Every hit should be inside its own example's local definition of the same name.
# If any hit crosses example boundaries, plan a coordinated multi-file edit.
grep -rn 'train_epoch(' --include='*.mojo'
```

### Copy-Paste: Smoke-run the example's own main()

```bash
# A test-file compile does NOT prove the example's main() still runs end-to-end.
# Run the example itself with 1 epoch and a tiny batch to catch arg-parser,
# dataset-loader, and checkpoint-path wiring bugs at the top level.
pixi run mojo run examples/<arch>/train.mojo --epochs 1 --batch-size 8
```

### Copy-Paste: Detect same-line coordination hazards

```bash
# Find every open PR that plans to touch the same file. Read each hit's diff
# region: if two PRs both plan to edit the same stale comment or numeric literal,
# coordinate merge order or reduce scope. On rebase, the pre-fixed line appears
# as an empty hunk — drop with `git commit --amend --no-edit`.
gh pr list --repo <org>/<repo> --state open --search "<filename>" --json number,title,headRefName
```

### Copy-Paste: Two-tier loss-threshold assertion (Mojo pseudo-code)

```mojo
# Hard floor — must hold for training to be considered functional. Asserted FIRST
# so failure logs distinguish "no decrease" from "insufficient decrease."
# If loss regressed from initial, training is broken (bad gradient sign, bad LR,
# broken forward pass) — this is a real signal.
assert_true(loss_final < loss_initial, "training regressed loss")

# Issue-prescribed threshold — DO NOT weaken this. The issue is the contract.
# If it flakes, mitigate on the data/hyperparams side (more samples, larger
# class-mean bias, warm-up epoch), not by lowering the bar.
assert_true(loss_final < 0.95 * loss_initial, "loss did not decrease 5% per issue DoD")
```

### Copy-Paste: Unverified API Assumptions section template

```markdown
## Unverified API Assumptions

Every symbol below was CITED in this plan but NOT `Read` from source. Reviewer must
verify each before approving; implementer must smoke-test each before writing tests.
If the reviewer NOGOs on this section, jump to the "NOGO revision loop" copy-paste
above and `Read` each row's source line NOW — do not respond by adding a "verify later"
step. Empirical rate: 4-of-4 flagged rows on ProjectOdyssey #5516 R0 were wrong.

| Symbol | Assumed Signature | Where Cited | Verify With |
|--------|-------------------|-------------|-------------|
| `randn` | `randn(shape, dtype, seed=..., mean=..., std=...)` | synthetic-data builder | Read `projectodyssey/tensor/tensor_creation.mojo` |
| `AnyTensor.store[dtype]` | `store[DType.float32](idx, val)` | label tensor construction | `grep -nE 'fn (store\|set)\b' any_tensor.mojo` |
| `cross_entropy` label shape | tolerates integer class indices | loss computation | Read the loss source; check for one-hot requirement |
| `extract_batch_pair` return | `Tuple[AnyTensor, AnyTensor]` | batch loop | Read `data/batch_utils.mojo` return signature |
```

### Confirm parent is unmerged

```bash
# Empty list ([]) means the parent is only a plan, not merged code. That's the
# trigger to consume the parent's plan as a CONTRACT and gate downstream work
# on a compile-smoke-test after the parent PR merges.
gh pr list --repo <org>/<repo> --search "<PARENT_ISSUE_N>" --state all --json number,state
```

### Copy-Paste (v1.2.0): Assumption Mapping for Mechanical Re-Plan

For **validation-only** child issues whose parent is unmerged, include this table in the plan so
re-planning after the parent PR merges is a mechanical find-and-replace, not a re-read of the
whole plan. Every row is either sourced from the parent's approved-plan comment (quote it
line-anchored) OR flagged as unverified.

```markdown
## Assumption Mapping for Mechanical Re-Plan

Once the parent PR merges, sweep every row: `Read` the merged file, confirm or correct the
assumption, and update the "File/line to fix" cell's target line.

| Assumption | Cited As (in this plan) | File/line to fix once parent merges | Verify With |
|------------|-------------------------|-------------------------------------|-------------|
| Entrypoint path | `examples/mobilenetv1/train_cifar10.mojo` | `scripts/run_mobilenetv1_cifar10_epoch.sh` L12 | `grep -l 'MobileNetV1' examples/` after parent merges |
| CLI flag names | `--epochs`, `--max-batches`, `--data-dir` | `scripts/run_*.sh` L24-30 | `pixi run mojo run <entrypoint> --help` |
| Batch log format | `step=<i> loss=<f> lr=<f>` | `scripts/summarize_epoch_log.py` regex L18 | run entrypoint once, `head -50 logs/<file>.log` |
| Smoke test path | `examples/mobilenetv1/smoke_overfit_one_batch.mojo` | plan step "on failure" section | `ls examples/mobilenetv1/*smoke*.mojo` |
| Data loader default | CIFAR-10 auto-download to `~/.cache/cifar10/` | bash wrapper `DATA_DIR` default | Read the loader source for cache-dir literal |
| Container invocation | `just shell -c '<cmd>'` | bash wrapper invocation form | `grep -A5 '^shell:' justfile` |
| Wall-clock budget | 60 min threshold, `MAX_BATCHES=200` fallback | bash wrapper env-var defaults | benchmark actual epoch on target hardware |
```

### Copy-Paste (v1.2.0): Log parser sanity check (Python)

```python
# Every log parser MUST refuse to summarize on a format mismatch. A wrapper that
# propagates `mojo run`'s exit code but pipes into a summarizer that silently
# produces a garbage result is a false-negative NOGO waiting to happen.
import re
import sys

PATTERN = re.compile(r"step=(\d+) loss=([\d.eE+-]+) lr=([\d.eE+-]+)")
SANITY_MIN = 20  # or 10% of expected batches, whichever is smaller

losses = []
with open(sys.argv[1]) as f:
    for line in f:
        m = PATTERN.search(line)
        if m:
            losses.append(float(m.group(2)))

# LOUD failure on format mismatch. Emit N even on success so the reviewer can
# see how many samples the criterion is asserted on.
expected = int(sys.argv[2]) if len(sys.argv) > 2 else -1
print(f"PARSED n={len(losses)} expected={expected} pattern={PATTERN.pattern!r}", file=sys.stderr)
if len(losses) < SANITY_MIN:
    print(f"ERROR: parser matched {len(losses)} < {SANITY_MIN} loss values — "
          f"log format may have changed. Refusing to summarize.", file=sys.stderr)
    sys.exit(1)
```

### Copy-Paste (v1.2.0): Smoothed-trend loss-decrease criterion (Python)

Prefer this over "mean of first 10% vs mean of last 10%" for short/noisy runs.

```python
# Linear fit slope as the primary decrease criterion. A monotonically-decreasing
# loss with a noisy tail passes this even when first-decile vs last-decile fails.
import numpy as np

def loss_decreasing(losses: list[float], min_slope_magnitude: float = 1e-4) -> tuple[bool, float]:
    """Return (decreased, slope). Slope < -min_slope_magnitude passes."""
    if len(losses) < 20:
        raise ValueError(f"need >= 20 samples for slope fit, got {len(losses)}")
    xs = np.arange(len(losses))
    ys = np.asarray(losses)
    # Guard against NaN/inf that would corrupt the fit
    if not np.isfinite(ys).all():
        return (False, float("nan"))
    slope, _intercept = np.polyfit(xs, ys, 1)
    return (bool(slope < -min_slope_magnitude), float(slope))

# Combine with the two-tier hard-floor pattern (Attempt 5's lesson):
# hard floor: losses[-1] < losses[0]   (must hold, else training regressed)
# issue DoD:  losses[-1] < 0.95 * losses[0]   (issue-prescribed target)
# trend:      slope < 0                (robust to tail noise on short runs)
```

### Copy-Paste (v1.2.0): Container preflight and gitignored-artifact attachment

```bash
# 1. Verify the `just shell -c` invocation form actually works before planning
#    on it. Some justfile shell recipes require an interactive shell.
grep -A5 '^shell:' justfile
just shell -c 'echo ok'   # if this errors, use `podman exec dev bash -c` instead

# 2. Container-network preflight for dataset auto-download. If the container's
#    network namespace blocks egress, the trainer's "auto-download on first run"
#    fails deep inside the loader with a stack trace, wasting a full launch.
if [ ! -d "$DATA_DIR" ]; then
  echo "PLAN.md L<N>: data not present and container egress unverified" >&2
  echo "Either bind-mount host-side data or verify egress to the mirror host" >&2
  exit 2
fi

# 3. Attach an artifact whose directory is gitignored. `git add` silently
#    no-ops on gitignored paths. Pick ONE of the three options and document it.

# Option (a): force-add the specific artifact
git add -f logs/mobilenetv1-cifar10-epoch-2026-07-02.log

# Option (b): copy to a non-gitignored evidence directory
mkdir -p docs/evidence
cp logs/mobilenetv1-cifar10-epoch-2026-07-02.log docs/evidence/
git add docs/evidence/mobilenetv1-cifar10-epoch-2026-07-02.log

# Option (c): attach via PR comment after opening
gh pr comment <PR_NUM> --body-file logs/mobilenetv1-cifar10-epoch-2026-07-02.log
```
