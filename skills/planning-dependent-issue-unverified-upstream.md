---
name: planning-dependent-issue-unverified-upstream
description: "Plan an issue whose dependency has not yet shipped, so the upstream's real interface is unknown. Use when: (1) writing an implementation plan for issue B that builds on a not-yet-merged issue A (e.g. B adds a Dockerfile on top of A's server skeleton), (2) you are tempted to hardcode the upstream's module path / function signature / directory layout into your plan, (3) the repo on disk does not yet contain the dependency's output and you must avoid baking unverified assumptions into 'Files to Modify'."
category: architecture
date: 2026-06-20
version: "1.0.0"
user-invocable: false
verification: unverified
tags:
  - planning
  - dependent-issue
  - unverified-dependency
  - upstream-interface
  - verify-before-planning
  - fallbacks
  - assumptions
  - milestone
---

# Planning a Dependent Issue When the Upstream Output Is Unverified

## Overview

| Field | Value |
|-------|-------|
| **Date** | 2026-06-20 |
| **Objective** | Plan ProjectArgus issue #153 (atlas M1 Dockerfile/embed) which DEPENDS on #152 (creates the Go module + chi server skeleton) — but #152's actual output was not yet on disk at plan time |
| **Outcome** | PLAN ONLY — never executed. The methodology (front-load dependency verification + inline fallbacks) is the durable learning. |
| **Verification** | unverified (plan only — never executed or CI-confirmed) |

## When to Use

- You are writing an implementation plan for an issue that explicitly depends on another, not-yet-merged issue.
- The dependency's concrete output (module path, exported function signatures, directory layout, helper packages) is described in prose but not yet present on disk.
- You catch yourself about to write the upstream's interface (e.g. `server.New(...)`, a module path, a `web/` location) into your plan as fact.
- The repo today is a different shape than your plan assumes (e.g. config-only, no `go.mod`, `find . -name '*.go'` is empty).

## Proposed Workflow

> **Warning:** This workflow has not been validated end-to-end. Treat as a hypothesis until CI confirms.

### Quick Reference

```bash
# STEP 1 of the implementation order is ALWAYS "verify the dependency's real output":
head -1 dashboard/go.mod                 # actual module path (don't hardcode it)
find dashboard -type d -name web         # where the embed source actually lives
ls dashboard/internal/version 2>&1       # does a version package exist?
grep -rn 'func New' dashboard/...        # real server.New signature, if any
ls dashboard/.../atlas.css 2>&1          # does the asset the issue assumes exist?

# Then state a FALLBACK inline next to every assumption:
#   - no version package -> drop `-ldflags -X version.Version=...`
#   - no atlas.css       -> create a minimal one
#   - no /healthz        -> add the handler in this issue
```

### Detailed Steps

1. **Make Step 1 of the implementation order "verify the dependency's actual output."** Do not begin with your own changes. Front-load concrete verification commands that read the upstream's real interface from disk: `head -1 <module>/go.mod` for the module path, `find <dir> -type d -name web` for the embed source location, `ls`/`grep` for any package or asset the issue assumes. At plan time for #153 the repo was config-only — `find . -name '*.go'` was empty and there was no `go.mod` — so EVERY interface detail was a hypothesis, not a fact.
2. **Never hardcode the upstream's interface into the plan.** Treat `server.New(...)`'s signature, the module path, and the `web/` directory location as values to be discovered, not constants to be typed. Write the plan so the implementer fills them in from Step 1's output, e.g. "use the module path from `head -1 go.mod`" rather than "the module is `github.com/.../argus`".
3. **State a conditional fallback inline next to every assumption.** For each thing the upstream might not have produced, write the if/then directly in the step: if no `version` package, drop the `-ldflags -X version.Version=...` flag; if `atlas.css` is missing, add a minimal one in this issue; if `/healthz` was not wired by the dependency, add the handler here. This keeps the plan executable even when the dependency's output differs from prose.
4. **Label the plan's verification level honestly as `unverified`.** Because the dependency was never confirmed and nothing was built, the plan is a hypothesis. Mark it `unverified` and use a "Proposed Workflow" framing — do not claim a verified workflow for a plan that could not even compile against a non-existent upstream.
5. **Separate the dependency-verification risk as the top stated risk.** The single largest risk in a dependent-issue plan is that the upstream shipped a different interface than assumed. Call this out explicitly as the #1 risk so reviewers and implementers re-check it first.

## Verified Workflow

_Not applicable._ This skill was captured from a planning session and is `unverified`: the dependent-issue plan was never executed and the upstream dependency (#152) was never confirmed, so there is no verified workflow. The actionable, hypothesis-level methodology lives under **Proposed Workflow** above and must be treated as unvalidated until CI confirms it. (This placeholder section exists only because `scripts/validate_plugins.py` requires the literal `## Verified Workflow` heading; it intentionally makes no verification claim.)

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
|---------|----------------|---------------|----------------|
| 1 | Wrote the upstream #152's `server.New(...)` signature directly into the #153 plan's "Files to Modify". | #152 was not merged and its real signature was unknown; the repo on disk had no `go.mod` and no `.go` files, so the hardcoded interface was a guess. | Never hardcode an unverified upstream interface; make "discover it from disk" Step 1 and reference the discovered value. |
| 2 | Assumed the embed source `web/` already existed at a known path from #152. | The directory layout #152 would produce was unconfirmed, and `//go:embed` is path-sensitive — a wrong assumed path makes the plan uncompilable. | Add `find <dir> -type d -name web` as a verification step before writing the embed path into the plan. |
| 3 | Assumed `atlas.css` and a `version` package existed because the issue mentioned them. | The issue described intended end-state, not guaranteed upstream output; either could be absent, breaking the `-ldflags -X` build or the static route. | State inline fallbacks: drop `-X version.Version` if no version package; create a minimal `atlas.css`/`/healthz` if absent. |
| 4 | Labeled the plan as a confident, ready-to-execute workflow. | Nothing was built and the dependency was unverified — the plan could not compile against a non-existent upstream. | Mark dependent-issue plans `unverified` and frame them as a "Proposed Workflow" hypothesis until CI confirms the dependency's real shape. |

## Results & Parameters

- **Status:** Methodology distilled from the implementation plan for ProjectArgus issue #153 (depends on #152); plan never executed.
- **Repo state at plan time:** config-only — `find . -name '*.go'` empty, no `go.mod`; every upstream interface detail was a hypothesis.
- **Verification-first commands:** `head -1 <module>/go.mod`, `find <dir> -type d -name web`, `ls internal/version`, `grep -rn 'func New'`, `ls .../atlas.css`.
- **Top stated risk:** the dependency (#152) ships a different interface than assumed — re-verify before implementing.
- **Companion skill:** `atlas-dashboard-dockerfile-embed-distroless` covers the concrete Dockerfile/embed/distroless mechanics of the same issue.
