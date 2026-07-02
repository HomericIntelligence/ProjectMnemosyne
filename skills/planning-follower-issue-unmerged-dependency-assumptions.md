---
name: planning-follower-issue-unmerged-dependency-assumptions
description: "You are planning a FOLLOWER issue that `Depends on #<N>` where #N is NOT YET MERGED (state: `plan-go`, `in-progress`, open PR pending, or no branch at all). Every claim you make about the dependency's public surface — struct field names, constructor signatures, function argument orders, exported symbol names, parameter counts — is a HYPOTHESIS, not a fact. Grep proves absence but never proves that a symbol WILL exist with a specific shape. Use when: (1) planning an issue whose `Depends on #<N>` target is unmerged and unimplemented (distinct from `planning-dependent-issue-unverified-upstream`, which handles the case where the dependency IS already merged and just needs to be read), (2) you are inventing struct fields, constructor signatures, or exact parameter counts against a dep whose body only describes them in prose, (3) the dep's issue body itself flags stale numbers in the codebase (e.g. 'comment says 84 but real count is 81') and you might copy the wrong number, (4) you are about to write helpers that call functions in the dependency's expected surface (e.g. `initialize_velocities(model)`) without checking whether the constructor is `@fieldwise_init` (positional per-field) vs a hand-written `fn __init__(out self, model: T)`."
category: architecture
date: 2026-07-02
version: "1.0.0"
user-invocable: false
verification: unverified
tags:
  - planning
  - dependent-issue
  - unmerged-dependency
  - follower-issue
  - hypothesis
  - assumptions
  - scaffold-first
  - fieldwise-init
  - verify-before-planning
  - mojo
---

# Planning a Follower Issue Against an Unmerged Dependency: Every Claim About the Dep Is a Hypothesis

## Overview

| Field | Value |
|-------|-------|
| **Date** | 2026-07-02 |
| **Objective** | Capture the discipline that must be applied when planning an issue whose `Depends on #<N>` target is NOT YET MERGED — so that invented struct fields, invented constructor signatures, and hand-waved parameter counts do not cascade into ~500 lines of code that fails to compile the moment the dep actually lands. |
| **Outcome** | Planning-discipline distilled from a ProjectOdyssey plan (issue #5515, ResNet-18 backward pass) that depends on unmerged issue #5514 (forward-with-cache, `IdentityCache`, `ProjectionCache`, `ResNet18Velocities`). The plan invented ~11 cache fields, a `ResNet18Velocities(model)` constructor, and copied a "84 parameters" count that the dep's own body flagged as WRONG. |
| **Verification** | unverified — this is a heuristic/discipline skill; no downstream build was run. The failure modes below are drawn from a real plan whose invented surface has NOT been reconciled with any merged code (the dep has never been implemented). |

> **Companion / contrast skill.** `planning-dependent-issue-unverified-upstream` covers the OPPOSITE case: dep is already merged and readable — read `git show origin/<branch>:path` to eliminate forks. THIS skill covers what to do when there is nothing to read yet: treat the dep's surface as a hypothesis, list every invented symbol, and recommend a scaffold-first implementation order so integration failure surfaces as a rename pass, not a rewrite.

## When to Use

- Planning an issue whose body includes `Depends on #<N>` and #N has state `plan-go` / `in-progress` / open PR pending / no PR at all — anything short of merged to `main`.
- Your plan invents struct field names, function signatures, or exact parameter counts against a dep that does not yet exist in the working tree. This is unavoidable — but the invention must be flagged as a hypothesis, not written as if verified.
- The dep's task body itself flags stale numbers in the codebase (e.g. "comment says N but real count is M"). This is a trap: it is tempting to transcribe the OLD (wrong) number from an existing file, or to transcribe the NEW (claimed) number without counting yourself.
- The dep declares `@fieldwise_init` (Mojo) or a `@dataclass` (Python) on a struct with many fields, and your plan calls a factory like `initialize_velocities(model)` that assumes a hand-written `__init__(model)` — `@fieldwise_init` on a struct with N fields takes N positional args, not one.
- You are about to write "reverse-chain" backward-pass helpers (or any code that calls a library API positionally) and only checked the SIGNATURE, not the IMPLEMENTATION — the parameter names in a signature can lie about semantics (e.g. `running_mean, running_var` in a training-mode branch may actually use saved batch stats, not running stats).

## Verified Workflow

<!-- Section title per honest verification level: PROPOSED WORKFLOW (unverified). The
"## Verified Workflow" heading is retained only because scripts/validate_plugins.py requires that
literal token; this content is a PROPOSAL derived from a plan that was not executed. -->

### Proposed Workflow (UNVERIFIED — planning-discipline heuristic)

> **Warning:** This workflow has not been validated by executing the resulting plan end-to-end.
> The failure modes below come from a real plan whose invented surface has never been reconciled
> against merged code. Every item is a hypothesis until the dep merges and the follower compiles.

### Quick Reference

```bash
# === Follower-issue planning checklist (dep is UNMERGED) ===
# Replace DEP with the dependency issue number (e.g. 5514) and FOLLOWER with your issue (e.g. 5515).

DEP=5514
FOLLOWER=5515
REPO=HomericIntelligence/ProjectOdyssey

# 1. Confirm the dep is actually unmerged — do NOT assume from the issue body.
gh issue view $DEP --repo $REPO --json state,labels,title,body
gh pr list --repo $REPO --search "$DEP in:body OR $DEP in:title" --state all \
  --json number,title,state,headRefName
# If any PR is merged: STOP — use planning-dependent-issue-unverified-upstream instead.

# 2. Inventory EVERY symbol your plan invents against the dep.
#    Write a table with columns: symbol | source | verification status.
#    Sources are: "dep body prose" | "my guess" | "grep of dep's referenced code".
#    Anything without a grep is an ASSUMPTION — mark it explicitly.

# 3. Grep-confirm each symbol does NOT already exist (absence proof, not presence proof).
grep -rn "struct IdentityCache" .        # if it exists, the dep is partially landed — investigate
grep -rn "struct ResNet18Velocities" .   # if it exists, use the real fields, not your guess
grep -rn "fn initialize_velocities" .

# 4. If the dep body flags a stale count in the codebase, COUNT IT YOURSELF from source.
#    Do not copy the old (wrong) count or the new (claimed) count on faith.
grep -cE "var .*_kernel|var .*_bias|var .*_gamma|var .*_beta" src/.../model.mojo

# 5. Recommend a scaffold-first implementation order in the plan:
#    - Step 1: implementer defines a LOCAL shim matching the assumed surface (struct with
#      guessed fields, factory with guessed signature). This makes integration failure surface
#      as a rename pass when the dep merges, not as a rewrite.
#    - Step 2: implement follower against the shim.
#    - Step 3: when dep merges, delete the shim, run the compiler, fix rename/signature drift.

# 6. For every library call in the follower (backward-pass helpers, tensor ops), read the
#    IMPLEMENTATION (not just the signature) of the branch you are exercising. Parameter names
#    like `running_mean` in a training-mode branch may actually use saved batch stats.

# 7. For every "Verified from X" claim in the plan, cite the exact line range checked
#    (not "model.mojo:568-970" — that is 400 lines and unfalsifiable).
```

### Detailed Steps

1. **Confirm the dep is unmerged before choosing this workflow.** Run `gh issue view <dep> --json state,labels` and `gh pr list --search "<dep> in:body OR <dep> in:title" --state all`. If any linked PR is merged, switch to `planning-dependent-issue-unverified-upstream` — the dep is readable and every fork should be eliminated by `git show`. This skill only applies when there is genuinely nothing to read.
2. **Inventory every invented symbol in a table.** For each struct field, function signature, constructor call, exported name, and numeric count your plan asserts about the dep, add a row: symbol | source (dep body prose / my guess / grep result) / verification status. Anything not backed by a grep result is an ASSUMPTION and must be flagged as such in the plan. Reviewers cannot distinguish "verified from source" from "invented plausibly" unless you label them.
3. **Grep-prove absence, not presence.** `grep -rn "struct <Name>"` can only tell you the symbol does not exist YET. It cannot tell you it will exist with the shape you invented. Document that limitation next to every grep in the plan.
4. **Count against source when the dep body flags a stale number.** The dep's body may say "the comment on line X says 84 but the real count is 81." Do NOT copy either number. Grep `src/.../model.mojo` for the actual field declarations and count. Every downstream count in the follower plan ("~72 SGD update calls", "~20 BN write-back lines") must be derived from a grep result, not from the dep body.
5. **Recognize `@fieldwise_init` constructor semantics.** In Mojo, `@fieldwise_init` on a struct with N fields generates a constructor taking N positional args (one per field). A follower plan that calls `initialize_velocities(model) → ResNet18Velocities(model)` — assuming a one-arg constructor — will not compile against a `@fieldwise_init` struct with ~81 fields. The factory function must either (a) construct each parameter tensor and pass all N positionally, or (b) the dep must expose a separate hand-written constructor. This is a coordination point with the dep — flag it in the plan.
6. **Prescribe a scaffold-first implementation order.** In the follower plan's "Implementation Order" section, step 1 MUST be: "implementer defines a local shim struct matching the assumed surface until the dep merges." This means the follower compiles independently and integration failure surfaces as a rename/signature pass (localized to the shim boundary), not a rewrite of ~500 lines of business logic. Without this step, an implementer who jumps to step 2 writes code against invented fields.
7. **Read the IMPLEMENTATION of every library call in the follower, not just the signature.** Parameter names in a function signature can mislead — especially in dtype/training-mode branches. If the follower calls `batch_norm2d_backward(..., running_mean, running_var, training=True, ...)`, read the `training=True` branch of the implementation to confirm whether the positional slots labeled `running_mean, running_var` are actually consumed as running stats or as saved batch stats. The signature parameter names are contract-adjacent; the branch implementation is the contract.
8. **Verify the semantics of "gradient splitting" in residual paths.** In a residual block, `add(main, skip)` in forward pairs with `add_backward(grad_out)` in backward. For a shape-matching add (no broadcasting), `add_backward` returns two IDENTICAL gradients (both equal to grad_out) — not a "split" of one gradient into two streams. The "two-stream summation" pattern in a ResNet is the sum of the MAIN branch's `conv1_backward.grad_input` and the SKIP branch's independent gradient at the residual junction — not a split of the `add_backward` output. Plan prose that says "split the gradient into two streams" conflates these and misleads implementers.
9. **Cite exact line ranges, not 400-line spans, for every "verified from" claim.** A plan that says "Verified from `model.mojo:568-970`" is unfalsifiable — a reviewer cannot tell what was actually read. Cite the specific decl or call site: `model.mojo:608 (add(bn2_out, block_input))` or `normalization.mojo:519 (batch_norm2d_backward signature)`. This forces the planner to actually read the line, and lets the reviewer spot-check.
10. **Label the plan `unverified` and keep the honesty gate.** No downstream code has been compiled; every invented symbol against the unmerged dep is a hypothesis. Mark the plan `unverified` and list the assumptions in a dedicated section so the reviewer can consent to them explicitly.

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
|---------|----------------|---------------|----------------|
| 1 | Wrote plan for follower issue #5515 (ResNet-18 backward + SGD) inventing ~11 fields on `IdentityCache` (`conv1_pre_bn`, `bn1_pre_relu`, `relu1_out`, `conv2_pre_bn`, `bn2_pre_add`, `block_input`, `skip_pre_relu`, `saved_bn1_mean`, `saved_bn1_var`, `saved_bn2_mean`, `saved_bn2_var`) and analogous fields on `ProjectionCache` — sourced only from dep #5514's prose ("conv pre-BN, BN pre-ReLU, post-ReLU, skip-sum, block-out"). | The dep's prose is a design sketch, not a schema. If the dep lands with any name drift (`pre_bn_conv1` vs `conv1_pre_bn`, `bn_pre_relu1` vs `bn1_pre_relu`), every helper in the follower needs a rename pass. Absent a scaffold-first order, that is a rewrite. | Inventory every invented field in a table; write a local shim struct in the follower until the dep merges; treat prose as a hypothesis. |
| 2 | Wrote `initialize_velocities(model) → ResNet18Velocities(model)` assuming a one-arg constructor that zero-fills tensors by inspecting the model. | Dep body specifies `@fieldwise_init ResNet18Velocities(Movable)`. `@fieldwise_init` generates a positional-per-field constructor, so a struct with ~81 fields requires ~81 positional args at the call site — a one-arg `ResNet18Velocities(model)` does not compile. | `@fieldwise_init` semantics are load-bearing; recognize them when the dep declares them and either (a) construct all fields positionally in the factory or (b) require the dep to expose a hand-written constructor. Flag as a coordination point in the plan. |
| 3 | Copied `Total trainable parameters: 84` from `model.mojo:311` (a print statement) into the plan's cost estimates ("~72 SGD update calls", "~20 BN write-back lines"). | The dep body itself explicitly said the printed count is WRONG — verified count is ~81 kernel/bias/gamma/beta fields. Downstream counts derived from 84 are all off. | When a dep body flags a stale number in the codebase, count the fields yourself with `grep -cE "var .*_kernel\|var .*_bias\|var .*_gamma\|var .*_beta" model.mojo`. Do not transcribe either the wrong number or the claimed number. |
| 4 | Passed `cache.saved_bn1_mean, cache.saved_bn1_var` positionally into `batch_norm2d_backward(grad_output, x, gamma, running_mean, running_var, training, epsilon)` (positions 4 and 5) and did not verify the training-branch implementation. | The signature's parameter NAMES are `running_mean, running_var`. In `training=True` mode, the correct backward math requires the SAVED BATCH mean/var from the forward pass, not the running-EMA stats. Whether the implementation actually uses positions 4/5 as running stats or re-derives batch stats from `x` is unverified — the plan never read `_batch_norm2d_backward_training` at `normalization.mojo:371`. If the impl uses positions 4/5 as running stats even in training mode, the follower's math is silently wrong. | Read the training-mode branch of any BN/dropout/mode-switched backward, not just the signature. Parameter names in a signature can lie about what a branch actually consumes. |
| 5 | Wrote in plan prose: "In the identity block, `add_backward` splits the residual gradient into two streams (main + skip), which we then sum with `conv1_backward.grad_input`." | For a shape-matching `add(main, skip)` with no broadcasting, `add_backward(grad_out)` returns `GradientPair(grad_a=grad_out, grad_b=grad_out)` — the two are IDENTICAL, not a split. Verified from `arithmetic.mojo:412`. The "two-stream summation" is the sum of the main branch's `conv1_backward.grad_input` and the skip branch's independent gradient (which happens to equal grad_out from `add_backward.grad_b`) — but describing it as a "split" is semantically misleading and will confuse implementers. | For elementwise ops without broadcasting, `X_backward` returns identical gradients for each input. Describe the residual-summation pattern in terms of "the two branches converge at the residual junction and their gradients sum," not "add_backward splits one gradient into two." |
| 6 | Claimed "Verified from `model.mojo:568-970`" as a blanket citation for the entire forward-pass chain in the plan's Approach section. | 402-line spans are unfalsifiable. A reviewer cannot tell what was actually checked; a follow-up reader cannot spot-check. In practice, only the shape of `add(bn2_out, block_input)` at line 608 and a few similar sites were read — the intermediate BN/conv shape flow was not walked. | Cite exact decl/call-site lines: `model.mojo:608 (add(bn2_out, block_input))`. If a claim rests on more than one site, list each. No 400-line "verified" spans. |
| 7 | Assumed `tensor_creation.randn(shape, DType.float32, seed=42)` accepts a `seed` keyword based on the "randn is a standard API" heuristic. | Never grep-confirmed the actual signature. If `randn` does not accept `seed`, the follower's test harness fails to compile. Two-line grep skipped. | Any invented keyword or positional argument in a library call must be grep-confirmed against the callee's declaration, even for "standard" APIs. Standard-ness is not a substitute for verification. |
| 8 | Assumed `AnyTensor._data.bitcast[Float32]()[0]` returns the first element for the training-loss return path and for `_snapshot_scalar` in tests. | Only holds if the tensor is contiguous (`is_contiguous()`). For a view or non-contiguous layout, offset 0 is not necessarily the first logical element. Parameters here happen to be contiguous (freshly `he_uniform`'d), so it works today — but the test would silently pass a false negative if that ever changes. The team-knowledge skill `mojo-tensor-design-view-semantics-numeric-correctness` warns about this. | Never use `bitcast[T]()[0]` as a "get scalar" shortcut without asserting `is_contiguous()`. Prefer a dedicated `scalar_at` / `.item()` method that respects strides. |

## Results & Parameters

- **Status:** Planning-discipline methodology distilled from ProjectOdyssey plan for issue #5515 (ResNet-18 backward pass) which depends on unmerged issue #5514 (`forward_with_cache`, `IdentityCache`, `ProjectionCache`, `ResNet18Velocities`, `initialize_velocities`). The plan was written and reviewed; the code has NOT been compiled. Every invented surface against the dep is a hypothesis.
- **The trap:** treating dep-body prose as a schema. A dep issue's body describes intended fields, methods, and counts — but those are DESIGN INTENT written before implementation. Grepping for absence proves the symbol does not exist YET; it does not prove it will exist with the shape you invented.
- **The distinction from the sibling skill:** `planning-dependent-issue-unverified-upstream` handles the MERGED-BUT-UNREAD case: `git show origin/<branch>:path` eliminates every fork. THIS skill handles the UNMERGED case: there is nothing to read, so the plan must (a) inventory every invented symbol, (b) label each as an assumption, (c) prescribe a scaffold-first implementation order so integration failure is a rename pass, not a rewrite.

### Reviewer / Author Pre-Flight Checklist for a Follower-Issue Plan (copy-paste)

```text
[ ] Confirmed the dep is genuinely unmerged (no linked PR is merged).
[ ] Inventory table present: every invented struct field / signature / count listed
    with source (dep prose / my guess / grep) and verification status.
[ ] For every count derived from the dep, I re-derived it from `grep` against source
    rather than transcribing the dep body.
[ ] Recognized `@fieldwise_init` semantics: any factory calling a `@fieldwise_init`
    struct constructor lists all N positional args or requires the dep to expose a
    separate hand-written __init__.
[ ] Implementation Order step 1 = "define local shim struct in the follower matching
    assumed surface until dep merges." No downstream step depends on the real dep
    struct existing.
[ ] For every library backward call used, read the IMPLEMENTATION of the branch being
    exercised (not just the signature). Documented which stats/inputs the branch
    actually consumes, not just what the parameter names claim.
[ ] Residual-block gradient prose describes "branches converge at the residual sum,"
    NOT "add_backward splits one gradient into two."
[ ] Every "Verified from X" citation is a specific line (or short range < 20 lines),
    not a 100+ line span.
[ ] Plan is labeled `unverified`; assumptions listed in a dedicated section so the
    reviewer can consent to them explicitly.
```

### Prescriptive Recommendations for Future Planners

1. **Never claim "verified from X" without a grep result cited inline.** A blanket "Verified from `model.mojo:568-970`" (402 lines) is unfalsifiable and useless to a reviewer.
2. **When the dep body flags a stale count in the codebase, count it yourself.** Copying either the old wrong number or the claimed new number is equally wrong. `grep -cE 'var .*_kernel|var .*_bias|var .*_gamma|var .*_beta' model.mojo` takes one line.
3. **Recognize `@fieldwise_init` semantics before writing factory calls.** A `@fieldwise_init` struct with N fields does not have a one-arg constructor. Factory functions must construct all N fields positionally or the dep must expose a hand-written `__init__`.
4. **Read the training-mode branch of any mode-switched backward.** Signature parameter names (`running_mean`, `running_var`) can lie about what a branch actually consumes. In training mode, BN backward needs SAVED batch stats; whether positions 4/5 carry those or something else is only knowable by reading the impl.
5. **For elementwise-add residuals, describe the gradient flow as "branches converge at the sum," NOT "add_backward splits one gradient into two."** `add_backward` for a shape-matching add returns two IDENTICAL gradients. The "two streams" language is semantically misleading.
6. **Grep-confirm every invented keyword or positional arg in a library call.** "It's a standard API" is not a substitute for a grep against the callee's declaration.
7. **Never use `._data.bitcast[T]()[0]` as a "get scalar" shortcut without asserting `is_contiguous()`.** For views or non-contiguous tensors, offset 0 is not the first logical element.

## Verified On

| Project | Context | Details |
|---------|---------|---------|
| ProjectOdyssey | Issue #5515 (ResNet-18 backward pass + SGD-momentum update in `examples/resnet18_cifar10/train.mojo`) which depends on unmerged issue #5514 (`forward_with_cache`, `IdentityCache`, `ProjectionCache`, `ResNet18Velocities`, `initialize_velocities`) | Plan written and reviewed; code NOT compiled. All invented surface against #5514 flagged as hypothesis. |
