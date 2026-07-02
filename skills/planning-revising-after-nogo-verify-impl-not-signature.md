---
name: planning-revising-after-nogo-verify-impl-not-signature
description: "When a plan reviewer NOGOs your plan for unverified assumptions — parameter-name semantics, backward-op behavior, param counts, scalar-read APIs, kwargs support — the fix is NOT to hand-wave more justification. The fix is to READ THE ACTUAL IMPLEMENTATION BODY of every flagged claim (not just the signature) and cite `file:line` inline in the revised plan. Signature-level trust is the recurring failure mode across all six patterns in this skill. Use when: (1) revising a plan after a NOGO on unverified claims, (2) a backward-op has a `training: Bool` parameter and you need to know which inputs the training branch actually consumes vs ignores (parameter names lie — the training branch of BN backward re-derives from `x` and never touches `running_mean`/`running_var` despite them being in the signature), (3) counting trainable params (grep the source; don't trust arithmetic OR stale docstring comments — both fail differently), (4) planning `add_backward` for residual sums where downstream reviewers may misread `(dY, dY)` return as a double-count bug (it's the correct path-gradient split; the reconvergence sum happens at the shared upstream input), (5) planning scalar-read assertions in tests (use `AnyTensor.load[dtype](i)` — sanctioned in `any_tensor.mojo:1479` — not `._data.bitcast[T]()[i]` UAF hazard), (6) checking whether a stdlib function accepts `seed` as a keyword arg (grep the signature — don't guess), (7) `@fieldwise_init` factory ergonomics with 80+ fields (kwargs are legal and readable; positional is error-prone at that scale), (8) scaffold-first when a `Depends on #N` target is unmerged (define the contract locally IN THIS PR with a rename-pass plan for the merge case, rather than blocking on the dep). This skill is the POSITIVE PATTERN for recovering from the failure mode captured in `planning-follower-issue-unmerged-dependency-assumptions` (unmerged-dep case) and `mojo-planning-verify-type-semantics-and-source-counts` (probe-before-planning case): after the NOGO, verify by reading impl BODIES, not just signatures or docstrings."
category: architecture
date: 2026-07-02
version: "1.0.0"
user-invocable: false
verification: verified-local
tags:
  - planning
  - plan-revision
  - nogo-recovery
  - verify-impl-not-signature
  - mojo
  - resnet
  - backward-pass
  - batch-norm
  - add-backward
  - residual-network
  - fieldwise-init
  - anytensor
  - load-dtype
  - grep-authoritative
  - scaffold-first
  - unmerged-dependency
  - path-gradient-vs-double-count
---

# Planning: Revising After a NOGO — Verify Implementation Bodies, Not Signatures

## Overview

| Field | Value |
| ------- | ------- |
| **Date** | 2026-07-02 |
| **Objective** | Capture the *positive* recovery pattern when a plan reviewer NOGOs unverified claims: read the actual implementation body (not just the signature or docstring) of every flagged claim and cite `file:line` inline in the revised plan. Complements the "verify BEFORE planning" discipline of `mojo-planning-verify-type-semantics-and-source-counts` and the "scaffold-first for unmerged deps" discipline of `planning-follower-issue-unmerged-dependency-assumptions` — this skill is what to do when those disciplines were skipped the first time and the reviewer caught it. |
| **Outcome** | R1 revision of ProjectOdyssey issue #5515 plan (ResNet-18 backward pass + SGD-momentum training loop) resolved all six NOGO categories from R0 by direct source-code reads: `_batch_norm2d_backward_training` at `normalization.mojo:371-455` (training branch IGNORES `running_mean`/`running_var` and re-derives from `x`), grep-count 81 trainable params (comment said 84, R0 arithmetic said 82 — grep authoritative), `add_backward` shape-match branch returns `(grad, grad)` as CORRECT path-gradient split (residual sum happens at reconvergence), `AnyTensor.load[DType.float32](0)` at `any_tensor.mojo:1479` as sanctioned scalar read, `randn(shape, dtype, seed=0)` at `tensor_creation.mojo:531` accepts seed kwarg, `@fieldwise_init` accepts kwargs → factory can use `ResNet18Velocities(conv1_kernel=..., ...)` for readability, scaffold-first plan for still-open dep #5514. Plan itself not yet implemented (verified-local, not verified-ci). |
| **Verification** | verified-local — every load-bearing R1 claim was verified by direct grep + Read of the pinned ProjectOdyssey `main` source (impl bodies, not signatures). Cited file:line: `normalization.mojo:371-455`, `any_tensor.mojo:1479`, `arithmetic.mojo:354` (`_reduce_broadcast_dims`), `tensor_creation.mojo:531`. The plan itself has not yet run through `pixi run mojo build` or CI, so behavior at merge time is `verified-local`, not `verified-ci`. |
| **Category** | architecture / planning |
| **Related Issues** | ProjectOdyssey #5515 R1 revision |
| **Related Skills** | `mojo-planning-verify-type-semantics-and-source-counts` (pre-planning probe discipline), `planning-follower-issue-unmerged-dependency-assumptions` (unmerged-dep failure catalog — this skill's Pattern 6 is the positive counterpart) |

## When to Use

Use this skill when:

1. **A reviewer NOGOs your plan for unverified claims.** The temptation is to write more prose justifying the claim. The correct action is to open the file the claim references and paste the impl body's `file:line` back into the revised plan. Signature-level trust is the recurring failure mode.
2. **A backward-op has a `training: Bool` parameter.** Parameter names in the signature are not a contract on which inputs the training branch actually reads. See Pattern 1.
3. **You need to know how many trainable params a model has.** See Pattern 2. The grep is authoritative. Neither the docstring comment nor hand-arithmetic is.
4. **A downstream reviewer might misread `add_backward` for shape-matching inputs.** See Pattern 3. `(dY, dY)` is correct, not a bug.
5. **A test asserts a tensor value at a specific index.** See Pattern 4. Use the sanctioned `.load[dtype](i)` API, not `._data.bitcast[T]()[i]`.
6. **You are about to write `f(..., seed=42)` for a stdlib function whose signature you have not read.** See Pattern 5.
7. **A `@fieldwise_init` struct has 20+ fields and you are writing a factory.** See Pattern 5 in the sibling skill and Pattern 6 here (kwargs are legal and much more reviewable at that scale).
8. **A `Depends on #<N>` target is still open and no PR references it.** See Pattern 6. Scaffold the contract locally in this PR rather than blocking.

**Trigger keywords in a review comment:** "verify", "cite line", "signature vs semantics", "which stats does it actually use", "trust the docstring", "prove this by reading source", "unverified", "hand-wave", "count doesn't match".

## Verified Workflow

> **Verified-local:** Every claim below was verified by direct grep + Read of the pinned ProjectOdyssey `main` source at R1 revision time. File:line evidence is inline. The plan itself has not yet been executed under `pixi run mojo build` or CI — behavior at merge time is not `verified-ci`.

### Pattern 1 — "Signature ≠ semantics" for backward ops with a training-mode branch

**Recurring failure mode:** you read a backward-op signature like:

```mojo
fn batch_norm2d_backward(
    grad_output: AnyTensor,
    x: AnyTensor,
    gamma: AnyTensor,
    running_mean: AnyTensor,
    running_var: AnyTensor,
    training: Bool,
    epsilon: Float64,
) raises -> Tuple[AnyTensor, AnyTensor, AnyTensor]:
```

and write plan text saying "we pass the saved batch stats as `running_mean`/`running_var`". Then you generate code that assumes those inputs are load-bearing.

**Reality at `src/projectodyssey/core/normalization.mojo:371-455`:** `_batch_norm2d_backward_training` re-derives batch mean and variance from `x` inside the function and **never touches** `running_mean`/`running_var`. Passing meaningless snapshots in those slots produces correct-looking gradients silently — the reviewer's NOGO on "which stats does the training branch actually consume" catches this.

**Rule:** whenever a backward op has a `training: Bool` parameter, ALWAYS read the training branch impl (not just the signature) before claiming which inputs are load-bearing. Cite the impl range `file:start-end` in the plan.

**Grep to run at plan-review time:**

```bash
# Locate the training branch of any *_backward function with a training flag
grep -nE '_backward_training|if training' src/projectodyssey/core/normalization.mojo | head
# Then Read lines around the hit to see which inputs are actually consumed
```

### Pattern 2 — Grep-count trainable params; ignore docstring comments and hand-arithmetic

**Recurring failure mode:** the plan sweeps SGD updates over per-field parameters (`conv1_kernel`, `bn1_gamma`, ..., `s4b2_bn2_beta`, `fc_weights`, `fc_bias`) and needs to know how many. Three numbers are available and they disagree:

- Docstring comment at `examples/resnet18_cifar10/model.mojo:105` (or similar): "84 trainable parameters" — WRONG, folds in BN running stats which are non-trainable.
- Hand-arithmetic in the plan: "4 (conv1 + bn1) + 5×8 (8 blocks × 5 tensors each average) + 3×12 (3 projections × 12) + 2 (fc) = 82" — off-by-one, hand-arithmetic is unreliable for variable-shaped block layouts.
- Grep count from HEAD: 81 (authoritative).

**Rule:** the grep is the source of truth. Paste the exact command AND the numeric output into the plan.

**Grep to run at plan-review time:**

```bash
# Trainable-only field declarations. Exclude running_mean/running_var (BN EMA state, non-trainable)
grep -cE '^    var .+_(kernel|bias|gamma|beta): AnyTensor' \
  examples/resnet18_cifar10/model.mojo
# → 81 (for ResNet-18 at HEAD as of 2026-07-02)

# Sanity: separately confirm fc_weights and fc_bias are counted
grep -nE '^    var fc_(weights|bias):' examples/resnet18_cifar10/model.mojo
```

The compile-time error on a missing struct field is a safety net, but the reviewer needs the number in the plan too — otherwise the SGD sweep loop can be silently incomplete or over-count.

### Pattern 3 — `add_backward` returning `(dY, dY)` for shape-matching inputs is correct, not a bug

**Recurring failure mode:** at the residual reconvergence in a ResNet block, the forward is `out = add(F(x), x)`. The backward for `add(a, b)` with shape-matching `a, b` returns `(grad_output, grad_output)` — literally the same upstream gradient handed to both branches. A reviewer who thinks in terms of "the two gradients should sum to grad_output, not each equal it" will flag this as a double-count.

**Reality:** the two returned tensors are two *path-gradients* that terminate at different upstream tensors and are then summed at the reconvergence point where those tensors originate from a shared source. The chain rule for `y = a + b` is `dy/da = 1, dy/db = 1`, so `grad_a = grad_output * 1 = grad_output` and same for `b`. When `a` and `b` share ancestry, the sum happens at that shared ancestor — NOT inside `add_backward` itself. `_reduce_broadcast_dims` at `src/projectodyssey/core/arithmetic.mojo:354` handles the broadcast-dim reduction path for shape-mismatch cases; for shape-match, no reduction happens and the pass-through is exact.

**Rule:** when a reviewer flags `(dY, dY)` as a suspected double-count, cite `arithmetic.mojo:354` in the plan and explicitly note that the residual sum is at the reconvergence point in the caller, not inside `add_backward`. This prevents the same reviewer from re-raising the concern on R2/R3.

**Wording to include verbatim in the revised plan:**

> For shape-matching `add(a, b)`, `add_backward` correctly returns `(grad_out, grad_out)`. These are two separate path-gradients; they are NOT double-counted. The residual sum happens where the two path-gradients reconverge on the shared upstream input in the caller. See `src/projectodyssey/core/arithmetic.mojo:354` for the broadcast-dim reduction path (unused when shapes match).

### Pattern 4 — Test scalar reads via `AnyTensor.load[dtype](i)`, not `._data.bitcast[T]()[i]`

**Recurring failure mode:** in a test file that asserts "did this tensor's element at index 0 change", it is tempting to write:

```mojo
var val = tensor._data.bitcast[Float32]()[0]  # BAD — UAF hazard, ignores view semantics
```

`_data` is a private field, `bitcast` bypasses ownership, and indexing into a raw pointer ignores stride / view offset. This is the exact pattern the sibling skill `mojo-tensor-design-view-semantics-numeric-correctness` warns against.

**Reality at `src/projectodyssey/tensor/any_tensor.mojo:1479`:** `AnyTensor` provides a sanctioned `load[dtype: DType](index: Int) -> Scalar[dtype]` method that respects view semantics and ownership. That is the API to use.

**Rule:** anywhere a plan needs to compare "did tensor value at index 0 change" in a test assertion, use:

```mojo
var val = tensor.load[DType.float32](0)  # GOOD — sanctioned, safe, view-aware
```

Cite `any_tensor.mojo:1479` in the plan so the reviewer does not need to re-verify.

### Pattern 5 — `randn(shape, dtype, seed=0)` — grep the signature, don't guess

**Recurring failure mode:** the plan writes `randn(shape, DType.float32, seed=42)` on faith that the function accepts `seed` as a keyword arg. If it doesn't, the test file fails to compile at the reproducibility fixture — a discovery at implementation time, not planning time.

**Reality at `src/projectodyssey/tensor/tensor_creation.mojo:531`:** the signature is `randn(shape, dtype, seed=0)` — seed IS a keyword-defaulted parameter. Verified.

**Rule:** for every stdlib call in the plan that uses a non-obvious keyword arg, grep the signature and cite `file:line`.

**Grep to run at plan-review time:**

```bash
grep -nE '^fn randn' src/projectodyssey/tensor/tensor_creation.mojo
# tensor_creation.mojo:531:fn randn(shape: ..., dtype: DType, seed: UInt64 = 0) raises -> AnyTensor
```

### Pattern 6 — `@fieldwise_init` accepts kwargs; use them for 20+ field factories

**Recurring failure mode:** the R0 plan wrote `initialize_velocities(model) → ResNet18Velocities(model)` — a single-arg factory. That is wrong because `@fieldwise_init` generates a per-field constructor. But the naive fix "OK, so 81 positional args" is also wrong for reviewability: silently misordered kwargs are a bug, silently misordered 81-tuple positional args are a nightmare to review.

**Reality:** `@fieldwise_init` accepts BOTH positional AND keyword constructors (see the sibling skill `mojo-planning-verify-type-semantics-and-source-counts` §3, verified at `src/projectodyssey/training/precision_config.mojo:68`). Prefer kwargs at 20+ fields:

```mojo
var vel = ResNet18Velocities(
    conv1_kernel = zeros_like(model.conv1_kernel),
    conv1_bias   = zeros_like(model.conv1_bias),
    bn1_gamma    = zeros_like(model.bn1_gamma),
    bn1_beta     = zeros_like(model.bn1_beta),
    # ... 77 more, each on its own line, each with the field name for reviewability ...
    fc_weights   = zeros_like(model.fc_weights),
    fc_bias      = zeros_like(model.fc_bias),
)
```

**Rule:** the factory in the revised plan uses kwargs (one per line) explicitly. Positional at 81 args is a POLA violation — the field name is the review anchor.

### Pattern 7 — Scaffold-first when the dependency is unmerged; rename-pass is the merge plan

**Recurring failure mode:** the plan blocks on `Depends on #5514` (still-open, no PRs). R0's mitigation was to invent 11 cache field names and hope they match the dep on merge.

**Reality:** `gh issue view 5514 --json state` → OPEN, zero PRs. The correct plan structure:

1. Define the CACHE contract locally IN THIS PR (`ResNet18ForwardCache`, `IdentityCache`, `ProjectionCache` as `@fieldwise_init(Movable)` structs with the fields the backward pass consumes).
2. Define the VELOCITY contract locally (`ResNet18Velocities`, matching the trainable-param grep at 81 fields — Pattern 2).
3. Define the FORWARD_CACHE contract locally (which activations `forward_with_cache` returns).
4. Ship the backward pass + SGD loop against the LOCAL definitions. Compile-checked from the moment the PR opens.
5. If #5514 merges FIRST with different names, do a rename pass on the ~5–10 struct field references. The load-bearing 200 lines of backward-pass block-helper bodies are naming-insensitive.

This turns "waiting on unmerged dep" into "unblocked with a compile-checked local shim". The rename pass is a mechanical diff, not a re-design.

**Grep to run at plan-review time:**

```bash
gh issue view 5514 --json state,title -q '{state, title}'
gh pr list --search 'in:body #5514' --state open  # confirms no PR references the dep
```

**Cross-reference:** the *failure catalog* for this pattern lives in `planning-follower-issue-unmerged-dependency-assumptions.md` (PR #2933 at time of writing). This skill's Pattern 7 is the *positive workflow*.

### Quick Reference

```text
1. Reviewer NOGO on unverified claim  → open the file, read the impl body, cite file:line.
2. Backward-op with training: Bool     → read the training branch; parameter names in the
                                          signature lie about which inputs are consumed.
3. Trainable-param count               → grep -cE '^    var .+_(kernel|bias|gamma|beta):
                                          AnyTensor' <model>.mojo — authoritative over
                                          docstring comments and hand-arithmetic.
4. add_backward for shape-match inputs → returns (dY, dY); this is correct path-gradient
                                          split. Sum happens at reconvergence in caller.
5. Test scalar reads                   → t.load[DType.float32](i), NOT
                                          t._data.bitcast[Float32]()[i]. Sanctioned at
                                          any_tensor.mojo:1479.
6. Stdlib kwarg support (e.g., seed)   → grep the signature and cite file:line before
                                          typing f(..., seed=42).
7. @fieldwise_init with 20+ fields     → factory uses kwargs (one per line); positional at
                                          81 args is unreviewable.
8. Unmerged dependency                 → scaffold the contract locally IN THIS PR;
                                          rename-pass if dep merges first with different
                                          names. Do not block.
```

**Verified probe commands (ProjectOdyssey main, 2026-07-02):**

```bash
# Pattern 1 — training branch of BN backward
grep -nE '_batch_norm2d_backward_training' src/projectodyssey/core/normalization.mojo
# → :371 (impl body ignores running_mean/running_var; re-derives from x)

# Pattern 2 — trainable-param count
grep -cE '^    var .+_(kernel|bias|gamma|beta): AnyTensor' \
  examples/resnet18_cifar10/model.mojo
# → 81

# Pattern 3 — add_backward broadcast-dim reduction
grep -nE '_reduce_broadcast_dims|fn add_backward' src/projectodyssey/core/arithmetic.mojo
# → :354 (broadcast path); shape-match branch is pass-through

# Pattern 4 — sanctioned scalar read
grep -nE '^\s*fn load\[' src/projectodyssey/tensor/any_tensor.mojo
# → :1479

# Pattern 5 — randn seed kwarg
grep -nE '^fn randn' src/projectodyssey/tensor/tensor_creation.mojo
# → :531 (seed: UInt64 = 0)

# Pattern 7 — dep status
gh issue view 5514 --json state -q .state       # → OPEN
gh pr list --search 'in:body #5514' --state open # → (empty)
```

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
| --------- | ---------------- | --------------- | ---------------- |
| Trust the signature `batch_norm2d_backward(grad_output, x, gamma, running_mean, running_var, training, epsilon)` at face value | R0 plan claimed "we pass the saved batch stats as `running_mean`/`running_var` for training mode" — assumed both inputs are load-bearing because they are in the parameter list | The training branch `_batch_norm2d_backward_training` at `normalization.mojo:371-455` re-derives batch mean and variance from `x` internally and never touches `running_mean`/`running_var`. Signature parameter names describe API shape, not which branches consume which inputs. Silently produces correct-looking gradients from meaningless snapshots. | Whenever a backward op has a `training: Bool` parameter, ALWAYS read the training branch impl body (not just the signature) before claiming which inputs are load-bearing. Cite the impl range `file:start-end` in the plan |
| Trust the docstring comment "Total trainable parameters: 84" in the model file | R0 plan cited 84 from the docstring | The docstring folded in `bn1_running_mean` / `bn1_running_var` — BN EMA state that is not trainable. Off by 2+ from reality. | Never trust an inline count comment when it disagrees with an authoritative grep. Write out the trainable-field regex explicitly, exclude `running_*`, and cite the command + output |
| Fall back to hand-arithmetic when the docstring is wrong: "4 + 5×8 + 3×12 + 2 = 82" | After the reviewer NOGO'd on 84, R0.5 tried to compute the count from block topology | Hand-arithmetic on a variable-shaped block layout is unreliable — the "5 tensors per block" average is wrong for projection blocks (12 params) vs identity blocks (8 params), and the "3 projections" tally missed one edge case. Gave 82, grep gave 81. | The grep is authoritative. `grep -cE '^    var .+_(kernel|bias|gamma|beta): AnyTensor' <file>` is a one-liner. Use it; paste the output; move on |
| Describe `add_backward` returning `(dY, dY)` as "distributing the gradient into two streams" without citing why the sum is not doubled | R0 plan wrote weakly-worded justification | The reviewer read `(dY, dY)` as a suspected double-count and NOGO'd. Reasonable — the terminology "distributing" is ambiguous | Write the *chain-rule reason* in the plan explicitly: `dy/da = 1, dy/db = 1` for `y = a + b`, so both path-gradients equal `grad_output`. The residual sum happens at the shared upstream input's reconvergence, NOT inside `add_backward`. Cite `arithmetic.mojo:354` explicitly |
| Write `tensor._data.bitcast[Float32]()[0]` for a scalar assertion in the test file | R0 plan test wrote raw pointer arithmetic | `_data` is private, `bitcast` bypasses ownership, and indexing ignores view offset / stride. UAF hazard, and violates view-semantics discipline captured in the sibling skill `mojo-tensor-design-view-semantics-numeric-correctness` | Use the sanctioned `t.load[DType.float32](i)` — verified at `any_tensor.mojo:1479`. This applies not just to production code but to test-file assertion helpers too |
| Write `randn(shape, DType.float32, seed=42)` on the assumption `seed` is a kwarg | R0 plan reproducibility fixture | The kwarg name was correct, but the R0 author never verified — pure luck it was right. Reviewer flagged it as unverified. | Grep the signature. `grep -nE '^fn randn' src/projectodyssey/tensor/tensor_creation.mojo` → `:531`. Cite `file:line` in the plan |
| Write `initialize_velocities(model) → ResNet18Velocities(model)` — a single-arg factory | R0 assumed velocities could be built from the model in one call | `@fieldwise_init` generates a per-field constructor. A single-arg call is illegal. The naive "fix" — 81 positional args — is unreviewable | Use kwargs, one per line. `@fieldwise_init` accepts them (sibling skill verified at `precision_config.mojo:68`). Positional at 81 args is a POLA violation; the field name is the review anchor |
| Invent cache field names against `Depends on #5514` prose alone and hope they match on merge | R0 named 11 fields "conv pre-BN, BN pre-ReLU, ..." based on the dep issue body | The dep is still open, no PRs. Field-name drift on merge is guaranteed. R0 also blocked on the dep rather than shipping. | Scaffold the contract locally IN THIS PR: `@fieldwise_init(Movable)` structs defined in the same file as the code that consumes them. Compile-checked from PR-open. Rename pass if the dep merges first with different names — the 200 lines of block-helper bodies are naming-insensitive |
| React to the NOGO by writing more prose justifying the R0 claims | R0.5 draft answered each reviewer point with additional argument | Prose does not verify. The reviewer's whole point was "your claims are not grounded in source". Answering with more claims fails identically | The fix for a NOGO on unverified claims is to OPEN THE FILE, read the impl body (not just the signature or docstring), and paste `file:line` back into the plan. Verification means reading impl bodies; hand-waving means arguing about signatures |

## Results & Parameters

### R1 revision produced

- `_batch_norm2d_backward_training` at `normalization.mojo:371-455` cited explicitly; plan states which inputs are load-bearing (`grad_output`, `x`, `gamma`) and which are IGNORED in the training branch (`running_mean`, `running_var`).
- Trainable-param count of 81 established by grep and pasted into the plan with the exact command.
- `add_backward` shape-match branch documented as `(dY, dY) = correct path-gradient split`, with `arithmetic.mojo:354` cited for the broadcast-dim reduction path.
- All test scalar reads use `t.load[DType.float32](i)`; `._data.bitcast[T]()` occurrences purged.
- `randn(shape, dtype, seed=0)` cited at `tensor_creation.mojo:531`; reproducibility fixture uses `seed=42` kwarg with the citation inline.
- `ResNet18Velocities` factory uses kwargs (one per line, 81 fields) with a note that positional at that scale is a POLA violation.
- CACHE / VELOCITY / FORWARD_CACHE contracts defined locally in the R1 PR (scaffold-first); the "if #5514 merges first with different names, do rename pass" is stated as the merge plan.

### Residual risks

- Plan not yet executed under `pixi run mojo build` or CI; this skill remains `verified-local`.
- `_batch_norm2d_backward_training` behavior verified by reading source, not by running a gradient-check probe — a gradient-check should be added when the plan is implemented.
- If ProjectOdyssey `main` moves and re-numbers lines, the cited `file:line` anchors need refresh at PR-open time.

### Generalizable lessons (durable takeaway)

1. **NOGO on unverified claims → read impl bodies, don't argue.** Signature-level trust is the recurring failure. The fix is `Read` the file range, paste `file:line` back into the plan.
2. **Parameter names in a backward-op signature do not tell you which inputs the training branch consumes.** Read the training branch. Ignore the running-mean/var parameter unless it appears in the training branch body.
3. **Docstring counts drift. Grep beats prose.** For any per-field trainable-param sweep, grep + paste + move on.
4. **`add(a,b)` backward returns `(dY,dY)` for shape-match — this is CORRECT.** Write the chain-rule justification in the plan verbatim so downstream reviewers do not re-raise.
5. **Scalar reads in tests use `t.load[dtype](i)`.** Not `._data.bitcast[T]()[i]`.
6. **Grep the signature before writing a keyword arg.** Cite the line.
7. **`@fieldwise_init` factories with 20+ fields use kwargs, one per line.**
8. **Unmerged dep → scaffold-first; rename-pass on merge.** Do not block; do not invent names.

## Verified On

| Project | Context | Details |
| --------- | --------- | --------- |
| ProjectOdyssey | Issue #5515 planning (R0) | R0 plan hand-waved all six patterns; reviewer NOGO'd for unverified claims. Failed Attempts table above captures the R0 mistakes verbatim |
| ProjectOdyssey | Issue #5515 planning (R1, 2026-07-02) | `verified-local` — every load-bearing R1 claim verified by direct grep + Read of pinned `main` source (impl bodies, not signatures). Cited file:line evidence inline: `normalization.mojo:371-455` (BN backward training branch semantics), `any_tensor.mojo:1479` (sanctioned scalar read `load[dtype]`), `arithmetic.mojo:354` (`_reduce_broadcast_dims`, add-backward broadcast path), `tensor_creation.mojo:531` (`randn` seed kwarg). Trainable-param count grep against `examples/resnet18_cifar10/model.mojo` returned 81. Plan execution / CI still pending — this remains `verified-local`, not `verified-ci` |
