---
name: architecture-dynamic-delegation-refactor-risk-review
description: "Planning and review checklist for behavior-preserving refactors that replace explicit compatibility wrappers with a documented dynamic delegation surface. Use when: (1) deleting many one-line wrapper methods in favor of __getattr__ delegation, (2) reviewing an allowlisted dynamic delegate map such as _PHASE_RUNNER_DYNAMIC_DELEGATES, (3) preserving unittest patch/direct-assignment/delete seams across the refactor, (4) excluding provider-boundary or selected-agent execution wrappers from dynamic dispatch."
category: architecture
date: 2026-06-26
version: "1.0.0"
user-invocable: false
verification: unverified
tags: [architecture, refactoring, dynamic-delegation, __getattr__, __dir__, compatibility-wrapper, test-seam, planning, reviewer-risks, phase-runner]
---

# Dynamic Delegation Refactor Risk Review

## Overview

| Field | Value |
|-------|-------|
| **Date** | 2026-06-26 |
| **Objective** | Capture the planning and review risks for replacing explicit compatibility wrapper methods with an allowlisted dynamic delegation surface while preserving behavior and test seams. |
| **Outcome** | Planning guidance only; issue #1389 implementation was not run end-to-end in this learning capture. |
| **Verification** | unverified - source counts, grep results, and assignment/deletion behavior must be refreshed against current code before implementation or approval. |

This skill is about the planning-risk and review surface for dynamic delegation. It does not claim that a specific implementation is correct.

## When to Use

- A class has many pure one-line compatibility wrappers that only delegate to a runner/helper object.
- A plan proposes replacing explicit wrappers with an allowlist such as `_PHASE_RUNNER_DYNAMIC_DELEGATES` plus `__getattr__` and `__dir__`.
- The refactor must preserve existing instance-level test seams: `patch.object(instance, name)`, direct assignment, and deletion/restoration.
- Some wrappers cross a provider boundary or selected-agent execution boundary and must remain explicit.
- Reviewers need to distinguish current-source evidence from stale issue-plan assumptions.

## Verified Workflow

<!-- This heading is retained because scripts/validate_plugins.py requires it. The actual workflow below is proposed, not verified. -->

> **Warning:** This workflow has not been validated end-to-end. Treat as a hypothesis until CI confirms.

### Proposed Workflow

### Quick Reference

```bash
# 1. Recompute wrapper inventory from current source, not from the issue plan.
python - <<'PY'
import ast
from pathlib import Path

path = Path("hephaestus/automation/implementer.py")
tree = ast.parse(path.read_text())
cls = next(n for n in tree.body if isinstance(n, ast.ClassDef) and n.name == "IssueImplementer")
for node in cls.body:
    if isinstance(node, ast.FunctionDef):
        print(f"{node.lineno}:{node.name}")
PY

# 2. Search for class-level consumers that dynamic instance lookup will not preserve.
rg -n "IssueImplementer\\.[A-Za-z_][A-Za-z0-9_]*|patch\\([^\\n]*IssueImplementer|patch\\.object\\(IssueImplementer|delattr\\(IssueImplementer|hasattr\\(IssueImplementer|dir\\(IssueImplementer" hephaestus tests scripts

# 3. Search runner callback sites for runtime impl.<name> lookup.
rg -n "getattr\\([^\\n]*impl|impl\\.[A-Za-z_][A-Za-z0-9_]*|callback|on_[A-Za-z_]" hephaestus/automation tests

# 4. Keep provider/selected-agent execution wrappers explicit.
rg -n "selected_agent|run_codex|run_claude|agent|provider" hephaestus/automation/implementer.py hephaestus/automation/*phase* tests/unit/automation

# 5. Add seam-preservation tests for get, set, delete, and restoration semantics.
rg -n "patch\\.object\\(|delattr\\(|setattr\\(" tests/unit/automation
```

### Detailed Steps

1. **Recompute the wrapper inventory from AST before planning deletes.**
   Do not reuse counts from a previous plan without refreshing them. The issue #1389 plan was based on a snapshot that claimed 28 pure wrappers, 25 delete candidates, and 3 provider-boundary wrappers excluded. Those numbers are review prompts, not durable facts.

2. **Build the dynamic allowlist from the runner surface, then diff it against wrappers.**
   `_PHASE_RUNNER_DYNAMIC_DELEGATES` must only contain names that are intended runtime delegates. Review both directions: every deleted pure wrapper should be represented, and every allowlisted name should exist on the runner and be safe to expose.

3. **Prove class-level consumers are absent with a broad grep.**
   Instance `__getattr__` does not make `IssueImplementer.method` exist on the class. Search for class-level patching, direct class attribute access, `dir(IssueImplementer)`, `hasattr(IssueImplementer, ...)`, and import-time introspection across product code, tests, and scripts. If any class-level consumer exists, the plan needs a different compatibility strategy.

4. **Preserve instance-level seams deliberately.**
   `__getattr__` can preserve runtime lookup for `impl.<name>`, but tests often rely on instance mutation. Add focused tests proving:
   - `patch.object(impl, "<delegate>")` overrides the dynamic delegate.
   - Direct `impl.<delegate> = fake` shadows the runner delegate.
   - `del impl.<delegate>` restores dynamic delegation when the attribute was shadowed.
   - Missing names still raise `AttributeError` and are not masked by a catch-all fallback.

5. **Keep provider-boundary wrappers explicit.**
   Wrappers that choose or mediate selected-agent execution, Codex/Claude provider calls, sessions, subprocess boundaries, or side-effect policy are not pure compatibility shims. Dynamic delegation should be limited to behavior already owned by the runner.

6. **Review `__dir__` and tooling discoverability as part of the contract.**
   If explicit methods disappear, developers and tools may lose discoverability. `__dir__` should include allowlisted delegate names, and documentation or tests should make that surface intentional. Type-checker limitations should be accepted explicitly or handled with stubs/protocols where needed.

7. **Keep `__getattr__` narrow and boring.**
   It should only resolve names in the allowlist and should raise `AttributeError(name)` for everything else. Avoid swallowing runner-side `AttributeError` in a way that hides real bugs.

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
|---------|----------------|---------------|----------------|
| Trust stale wrapper counts | Planned deletion from prior AST counts like 28 pure wrappers / 25 delete candidates / 3 exclusions | The source may have changed after the plan; deleting by stale count can remove the wrong method or miss a new wrapper | Recompute counts from current source immediately before implementation and again during review |
| Grep only obvious test patch sites | Searched for direct wrapper names but skipped class-level introspection and class patching patterns | Instance `__getattr__` preserves `impl.name`, not `IssueImplementer.name`; class-level consumers break silently | Search for class attribute access, `patch.object(IssueImplementer, ...)`, `dir(IssueImplementer)`, and `hasattr(IssueImplementer, ...)` |
| Put provider-boundary wrappers in the dynamic allowlist | Treated all thin wrappers as pure compatibility shims | Selected-agent execution wrappers encode provider policy and side-effect boundaries, not just delegation | Keep provider/agent execution wrappers explicit unless the runner already owns that exact policy |
| Catch all missing attributes in `__getattr__` | Used a broad fallback to runner lookup for any unknown name | Typos and real missing attributes can become confusing runner errors or false positives | Gate on the allowlist first and raise `AttributeError(name)` for non-delegates |
| Test only happy-path dynamic lookup | Verified `impl.name` calls the runner but skipped assignment and deletion seams | Existing tests may patch or shadow instance methods; behavior changes only appear under mutation | Add tests for `patch.object`, direct assignment, deletion/restoration, and missing-name errors |
| Ignore discoverability/type tooling | Deleted explicit methods without replacing `dir()` visibility or documenting the dynamic surface | IDEs, static tools, and reviewers can no longer see the supported compatibility names | Maintain `__dir__`, document the allowlist, and consider stubs/protocols if type checking depends on explicit members |

## Results & Parameters

### Reviewer Checklist

```text
Dynamic delegation refactor review:

- [ ] Current-source AST inventory recomputed; wrapper counts in the plan were not trusted.
- [ ] Deleted wrapper names exactly match the dynamic allowlist, except documented explicit exclusions.
- [ ] Provider-boundary / selected-agent execution wrappers remain explicit.
- [ ] Whole-repo grep found no class-level patch, direct class access, or introspection consumers that require real class methods.
- [ ] Runner callback sites use runtime instance lookup (`impl.<name>` or equivalent), not stored class method objects.
- [ ] Tests cover dynamic get, instance assignment shadowing, `patch.object(instance, name)`, deletion/restoration, and missing-name `AttributeError`.
- [ ] `__dir__` exposes delegated names for runtime discoverability.
- [ ] The PR description labels all source-count and grep evidence with the date/commit it was collected from.
```

### Issue #1389 Planning Assumptions to Refresh

| Assumption From Plan | Verification Needed Before Approval |
|----------------------|--------------------------------------|
| Current source has 28 pure phase_runner wrappers | Recompute from AST on the implementation base commit |
| 25 wrappers are safe delete candidates | Diff every candidate against runner ownership and exclusions |
| 3 provider-boundary wrappers must remain explicit | Re-read selected-agent / provider execution wrappers and confirm they still carry policy |
| Grep found no class-level patch targets | Repeat broad grep across product code, tests, and scripts |
| Runner callback sites use runtime `impl._name` lookup | Inspect callback wiring and add regression coverage for at least one dynamic delegate callback |
| `patch.object`, assignment, and deletion preserve test seams | Add explicit tests for all three mutation paths plus restoration |

## Verified On

| Project | Context | Details |
|---------|---------|---------|
| ProjectHephaestus | Issue #1389 planning capture for refactoring `IssueImplementer` phase-runner compatibility shims into `_PHASE_RUNNER_DYNAMIC_DELEGATES` plus `__getattr__` / `__dir__` | unverified planning guidance only; implementation and CI were not run as part of this learning capture |
