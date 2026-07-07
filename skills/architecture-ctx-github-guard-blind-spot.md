---
name: architecture-ctx-github-guard-blind-spot
description: "Use when: (1) a pipeline architecture AST guard only tracks direct github_api mutators and misses coordinator-neutral ctx.github / StageGitHub calls; (2) you need to keep the guard scope narrow while proving the StageGitHub binding surface separately; (3) a synthetic-stage regression test should document that direct github_api calls are counted but ctx.github calls are out of scope."
category: architecture
date: 2026-07-07
version: "1.0.0"
user-invocable: false
verification: verified-ci
tags:
  - pipeline
  - ctx-github
  - stagegithub
  - ast-guard
  - coordinator
  - regression-test
  - github-api
  - architecture
---

# Architecture: `ctx.github` Guard Blind Spot

## Overview

| Field | Value |
|-------|-------|
| **Date** | 2026-07-07 |
| **Objective** | Keep the pipeline architecture guard honest about its scope: it detects direct `github_api` mutators, but it does not and should not claim to cover coordinator-neutral `ctx.github` / `StageGitHub` calls |
| **Outcome** | Success - ProjectHephaestus issue #1932 / PR #2015 added a regression test that documents the scope boundary and CI turned green |
| **Verification** | verified-ci |

## When to Use

- A static guard scans `github_api.__all__`, import names, or direct `obj.attr` calls and you realize that `ctx.github.*` is a different surface
- You need to keep `StageGitHub` binding coverage in the coordinator adapter tests, not in the direct mutator scan
- CI is red because the guard looks broader than it really is, or because a new `ctx.github` call was assumed to be covered by the import/attribute matcher
- You want to document the negative space explicitly so future refactors do not widen the guard by accident

## Verified Workflow

### Quick Reference

```python
def test_guard_scope_excludes_coordinator_neutral_stage_github_calls(
    tmp_path: Path,
) -> None:
    synthetic = (
        "from hephaestus.automation import github_api\n"
        "def f(ctx):\n"
        "    ctx.github.add_labels(1, ['state:x'])\n"
        "    ctx.github.create_pr(1, 'branch', 'title', 'body')\n"
        "    ctx.github.arm_auto_merge(2)\n"
        "    github_api.gh_issue_add_labels(3, ['state:y'])\n"
    )
    path = tmp_path / "synthetic_stage.py"
    path.write_text(synthetic, encoding="utf-8")

    assert _imported_mutators(path) == {"gh_issue_add_labels"}
```

### Detailed Steps

1. Keep the direct-mutation guard focused on `github_api` names that are actually exported as mutators.
2. Add a synthetic stage that exercises both surfaces: `ctx.github.*` and one direct `github_api.*` call.
3. Assert that the AST matcher sees only the direct `github_api` mutator.
4. Leave `StageGitHub` method binding coverage to `tests/unit/automation/test_pipeline_github.py`.
5. Run the targeted pipeline-architecture tests and confirm the scope test stays green.

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
|---------|----------------|---------------|----------------|
| Assumed `ctx.github.add_labels()` would be counted by the direct mutator scan | Treated the coordinator-neutral accessor as if it were another `github_api` attribute | The matcher only recognizes direct `github_api` names, so the `ctx.github` surface was invisible | Indirect accessor surfaces need their own regression test and their own contract text |
| Let the scope stay implicit | Relied on the existing architecture guard without a synthetic-stage assertion | The guard looked broad enough to be trusted, but its matcher was narrower than the coordinator-owned binding surface | Make the negative space explicit: document what the guard does not cover |
| Tried to fold `StageGitHub` binding checks into the direct AST scan | Mixed coordinator adapter coverage into the import/attribute guard | That conflates two different contracts and makes the guard harder to reason about | Keep the direct scan narrow and test the coordinator adapter separately |

## Results & Parameters

- Target file: `tests/unit/automation/pipeline/test_pipeline_architecture.py`
- Companion coverage: `tests/unit/automation/test_pipeline_github.py`
- Expected AST result for the synthetic stage: `{"gh_issue_add_labels"}`
- Expected non-matches: `ctx.github.add_labels`, `ctx.github.create_pr`, `ctx.github.arm_auto_merge`
- Relevant PR/issue: ProjectHephaestus issue #1932 / PR #2015

## Verified On

| Project | Context | Details |
|---------|---------|---------|
| ProjectHephaestus | issue #1932 / PR #2015 | CI-green regression for the pipeline architecture guard scope |
