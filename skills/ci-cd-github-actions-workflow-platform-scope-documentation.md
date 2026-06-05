---
name: ci-cd-github-actions-workflow-platform-scope-documentation
description: "Document platform asymmetries in GitHub Actions workflows using top-level header comment blocks with issue references. Use when: (1) CI workflows intentionally target only some platforms (e.g., Linux-only), (2) documenting why certain platforms are out of scope, (3) clarifying capability claims despite CI gaps."
category: ci-cd
date: 2026-06-05
version: "1.0.0"
user-invocable: false
verification: verified-local
tags: [github-actions, platform-scope, documentation, honesty, ci-cd]
---

# GitHub Actions Workflow Platform Scope Documentation

## Overview

| Field | Value |
|-------|-------|
| **Date** | 2026-06-05 |
| **Objective** | Document the pattern for honestly communicating platform asymmetries in CI workflows when some platforms are intentionally out of scope, preventing misleading "cross-platform" claims while keeping scope transparent |
| **Outcome** | Verified locally; pattern implemented in ProjectHephaestus PR #977 with pre-commit validation passing |
| **Verification** | verified-local |
| **Related Learning** | Issue #749 (platform asymmetry docs with semantic anchors); this skill applies that pattern to GitHub Actions workflows |

## When to Use

- You have a CI workflow that intentionally targets only a subset of platforms (e.g., Linux-only test matrix)
- You need to document WHY certain platforms are out of scope (e.g., pixi environment targets linux-64 exclusively)
- You want to clarify that despite the CI gap, certain behaviors still work across platforms (e.g., wheels remain pure-Python importable)
- You're concerned about audit findings around misleading "cross-platform" claims when CI doesn't exercise all platforms
- You want to provide a clear trigger for WHEN the scope can expand (e.g., "When #539 lands, expand matrix.os here")

## Verified Workflow

### Quick Reference

Place a 14-line header comment block at the top of your workflow file, BEFORE the `name:` field:

```yaml
# Platform Scope: Linux Only (CI)
#
# This workflow exercises tests only on Linux (ubuntu-latest) due to pixi environment
# constraints that target linux-64 exclusively. Macros/Windows support is out of scope
# for this test matrix per #539 (separate tracking for macOS/Windows CI expansion).
#
# CAPABILITY: Despite this CI limitation, the package remains pure-Python importable
# on all platforms and wheels are generated in GitHub Actions with platform-specific tags.
#
# EXPAND TRIGGER: When #539 lands with cross-platform pixi environments, expand
# matrix.os to include [ubuntu-latest, macos-latest, windows-latest] and verify all
# tests pass before merging.
#
# See also: CONTRIBUTING.md (platform asymmetry documentation)
---
name: Test
on: [pull_request, push]
# ... rest of workflow
```

### Detailed Steps

1. **Identify the scope limitation**:
   - What platforms does your workflow target? (e.g., Linux only via `ubuntu-latest`)
   - What platforms are intentionally excluded? (e.g., macOS, Windows)
   - Why is the exclusion necessary? (e.g., pixi linux-64 constraint, environment unavailability)
   - Is there a tracking issue for future expansion? (e.g., #539 for macOS/Windows support)

2. **Identify capability claims that might contradict the scope**:
   - Can the package still be imported on excluded platforms? (e.g., wheels work cross-platform)
   - Are there tests that *could* exercise excluded platforms but currently don't? (e.g., unit tests remain platform-agnostic)
   - What behavior is proven by CI vs. assumed/untested? (e.g., CI proves Linux, assumption proves macOS/Windows)

3. **Write the header comment block**:
   - Start with: `# Platform Scope: <platforms> (<reason abbreviation>)`
   - Describe what platforms are tested and why
   - Explicitly state what platforms are OUT OF SCOPE and with what tracking issue
   - Add CAPABILITY paragraph(s) explaining what still works despite the CI gap
   - Add EXPAND TRIGGER explaining when/how scope can grow
   - Reference related documentation (e.g., CONTRIBUTING.md) WITHOUT duplicating it
   - Use issue links (#NNN) instead of doc file references for stability

4. **Place the comment block strategically**:
   - Put it BEFORE the `name:` field (highest visibility)
   - Keep it visually separated from the actual workflow definition
   - Ensure it's the first thing someone sees when opening the file

5. **Use issue links for stability**:
   - Replace doc file references with `#NNN` issue links
   - Links survive refactors; doc paths break when docs move
   - Example: `per #539 (separate tracking for macOS/Windows CI expansion)` not `see docs/PLATFORM_SUPPORT.md`

6. **Validate before committing**:
   - Ensure the YAML parses correctly (comment block doesn't break the workflow)
   - Run `pre-commit run --all-files` to catch formatting issues
   - Test the workflow runs successfully in CI before merging

### Example Implementation

**From ProjectHephaestus `.github/workflows/test.yml` (PR #977)**:

```yaml
# Platform Scope: Linux Only (CI)
#
# This workflow exercises tests only on Linux (ubuntu-latest) due to pixi environment
# constraints that target linux-64 exclusively. macOS and Windows support is out of scope
# for this test matrix and tracked separately per #539.
#
# CAPABILITY: Despite this CI limitation, the package remains pure-Python importable
# on all platforms and wheels are generated in GitHub Actions with platform-specific tags.
# Unit tests are platform-agnostic and designed to pass on any POSIX-compatible environment.
#
# EXPAND TRIGGER: When #539 lands with cross-platform pixi environment support, expand
# matrix.os to include [ubuntu-latest, macos-latest, windows-latest] and verify all
# tests pass on each platform before merging.
#
# See also: CONTRIBUTING.md (platform asymmetry rationale)
#
---
name: Test

on:
  pull_request:
  push:
    branches: [main]

jobs:
  test:
    runs-on: ubuntu-latest  # Linux-only per scope above
    strategy:
      matrix:
        python-version: ["3.10", "3.11", "3.12"]
    # ... rest of job
```

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
|---------|----------------|---------------|----------------|
| Inline comment at matrix definition | Placed scope explanation next to `matrix.os: [ubuntu-latest]` as a comment | Too easily missed when scanning the workflow; readers jump to the matrix without reading adjacent comments | Scope is a workflow-wide property, not job/matrix-specific — put it at the top where visibility is guaranteed |
| Job-level comment block | Placed detailed scope explanation in the job definition | Readers might skip it thinking it's job-specific, missing the broader workflow scope | Scope affects the entire workflow's capabilities, not just one job — needs workflow-level placement |
| Reference to doc file paths | Wrote "See docs/platform-support/asymmetry.md" | Doc refactors break the reference; readers find dead links | Use issue links (#NNN) instead — they survive doc reorganization and provide tracking for future work |
| Single-sentence explanation | Wrote "Linux-only due to pixi constraints" | Didn't clarify what capability still works (e.g., pure-Python importability), leading to ambiguity about what's actually broken | Include both limitation (what doesn't work) AND capability (what does work) for honesty and clarity |

## Results & Parameters

### Configuration Template

```yaml
# Copy-paste ready header comment block for Linux-only CI workflows

# Platform Scope: Linux Only (CI)
#
# This workflow exercises tests only on Linux (ubuntu-latest) due to [REASON: e.g., "pixi
# environment constraints that target linux-64 exclusively"]. [EXCLUDED_PLATFORMS: e.g., "macOS and Windows support is
# out of scope for this test matrix"] and tracked separately per [ISSUE_REF: e.g., "#539"].
#
# CAPABILITY: Despite this CI limitation, [CAPABILITY_CLAIM: e.g., "the package remains pure-Python
# importable on all platforms and wheels are generated in GitHub Actions with platform-specific tags"].
#
# EXPAND TRIGGER: When [EXPANSION_CONDITION: e.g., "#539 lands with cross-platform pixi environment support"],
# expand matrix.os to include [EXPANDED_MATRIX: e.g., "[ubuntu-latest, macos-latest, windows-latest]"] and verify all
# tests pass on each platform before merging.
#
# See also: [DOC_REFERENCE: e.g., "CONTRIBUTING.md (platform asymmetry rationale)"]
#
```

### Key Parameters

| Parameter | Purpose | Example |
|-----------|---------|---------|
| `REASON` | Why only some platforms are tested | "pixi environment constraints that target linux-64 exclusively" |
| `EXCLUDED_PLATFORMS` | What platforms are NOT tested | "macOS and Windows support is out of scope" |
| `ISSUE_REF` | Tracking issue for future expansion | "#539" |
| `CAPABILITY_CLAIM` | What still works despite CI gap | "the package remains pure-Python importable on all platforms" |
| `EXPANSION_CONDITION` | When scope can grow | "When #539 lands with cross-platform pixi support" |
| `EXPANDED_MATRIX` | What the matrix will become | `[ubuntu-latest, macos-latest, windows-latest]` |
| `DOC_REFERENCE` | Related documentation link | "CONTRIBUTING.md (platform asymmetry rationale)" |

### Expected Outcomes

- Workflow file parses without YAML syntax errors
- Pre-commit hooks pass (formatting, linting)
- Anyone opening the workflow immediately understands the platform scope and why
- Audit findings around "misleading cross-platform claims" are prevented
- Clear path forward for future expansion via issue link

### Verification Checklist

- [ ] Comment block placed BEFORE `name:` field
- [ ] Reason for platform exclusion is clear (e.g., "pixi linux-64 constraint")
- [ ] Excluded platforms explicitly named (e.g., "macOS and Windows out of scope")
- [ ] Tracking issue linked with `#NNN` format
- [ ] CAPABILITY paragraph explains what STILL works cross-platform
- [ ] EXPAND TRIGGER explains when/how to grow scope
- [ ] Doc references use issue links, not file paths
- [ ] YAML syntax valid (run through YAML parser)
- [ ] Pre-commit hooks pass (`pre-commit run --all-files`)
- [ ] CI workflow runs successfully before merging

## Verified On

| Project | Context | Details |
|---------|---------|---------|
| ProjectHephaestus | Issue #794 (Linux-only test matrix audit finding) | Implemented in PR #977; `.github/workflows/test.yml` received 14-line header comment block per this pattern; all pre-commit hooks passed; workflow executed successfully |
| ProjectHephaestus | Issue #539 tracking | Cross-platform CI expansion deferred; pattern provides clear trigger ("When #539 lands...") for future scope growth |

## Related Patterns

- **Prior Learning (Issue #749)**: Platform asymmetry documentation using semantic anchors; this skill applies that principle to GitHub Actions workflows
- **GitHub Actions Scope**: Scope is a workflow-wide property that affects all jobs; document at the top before the `name:` field
- **Issue Links vs. Doc Refs**: Use `#NNN` instead of doc file paths for stability across refactors
- **Honesty Gate**: Always include both what doesn't work (CI limitation) and what does work (cross-platform capability) to prevent misleading claims

## Skill Usage Examples

### When to Invoke This Skill

1. **Audit Finding**: "Workflow claims cross-platform support but only tests Linux"
   - Use this skill to add honest scope documentation with capability claims

2. **New Workflow Setup**: Adding a CI workflow with intentional platform limitations
   - Start with the header comment block template before implementing the workflow logic

3. **Documentation Gap**: CI workflow scope is undocumented, causing ambiguity about what platforms are supported
   - Apply this pattern to make scope explicit and prevent future confusion

4. **Expansion Planning**: You want to document the path to adding macOS/Windows testing
   - Use the EXPAND TRIGGER section to link to the tracking issue and outline the steps
