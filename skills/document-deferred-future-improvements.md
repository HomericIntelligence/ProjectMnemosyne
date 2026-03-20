---
name: document-deferred-future-improvements
description: 'Pattern for documenting deferred Future Improvements in design docs:
  add Status, Why Deferred, and Acceptance Criteria to each item so future contributors
  avoid re-investigating implementation status'
category: documentation
date: 2026-02-22
version: 1.0.0
user-invocable: false
---
# Document Deferred Future Improvements

## Overview

| Field | Value |
|-------|-------|
| **Date** | 2026-02-22 |
| **Issue** | #881 |
| **PR** | #990 |
| **Objective** | Add structured deferral notes to confirmed-unimplemented Future Improvements in `docs/design/container-architecture.md` |
| **Outcome** | ✅ All four items annotated with Status, Why Deferred, Acceptance Criteria; health check noted as already implemented |
| **Status** | Completed and merged |

## When to Use This Skill

Apply this pattern when:

1. A design doc contains a **Future Improvements** (or similar) section with bare list items
2. Items have been **confirmed unimplemented** via code inspection
3. Future contributors would otherwise need to **re-investigate status** (wasted effort)
4. A follow-up issue explicitly requests **clarifying deferral rationale**

**Do NOT use** when:

- Items are actively in-flight (mark as WIP instead)
- The section is already annotated with status fields
- The doc is auto-generated from code (annotations would be overwritten)

## Verified Workflow

### 1. Read the design doc and identify Future Improvements items

```bash
# Find the section
grep -n "Future Improvements" docs/design/*.md
```

### 2. Inspect actual implementation files to confirm status

For each item, read the relevant implementation files directly:

```bash
# For container items: Dockerfile and wrapper scripts
cat docker/Dockerfile
cat scripts/run_experiment_in_container.sh
```

Look for:
- Flags / directives the item would require (e.g., `--memory`, `--platform`, named volumes)
- If absent → item is **Deferred (not implemented)**
- If present → item is **Implemented** — note where

### 3. For each item, write three sub-bullets

```markdown
1. **Item name**: One-line description.

   - **Status**: Deferred (not implemented)  [or: Implemented — see FILE:LINE]
   - **Why deferred**: Concrete reason grounded in what you saw in the code.
     Reference specific flags, files, or constraints that block implementation.
   - **Acceptance criteria**: Measurable conditions to implement (2-3 bullets).
```

### 4. Surface any already-implemented items

If an item in the list is actually implemented, add a separate entry noting it:

```markdown
5. **Health checks**: Verify container readiness via `HEALTHCHECK`.

   - **Status**: Implemented — see `docker/Dockerfile` lines 116–117.
```

This prevents future contributors from treating already-done work as pending.

### 5. Commit, push, PR

Pure documentation changes — no Python code, no tests needed:

```bash
git add docs/design/container-architecture.md
git commit -m "docs(container): document future improvements implementation status

Closes #<issue-number>"
git push -u origin <branch>
gh pr create --title "docs(container): ..." --body "Closes #<issue-number>"
gh pr merge --auto --rebase
```

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
|---------|----------------|---------------|----------------|
| N/A | Direct approach worked | N/A | Solution was straightforward |
## Results & Parameters

### Files Modified

| File | Change |
|---|---|
| `docs/design/container-architecture.md` | +50 lines: expanded Future Improvements from 4 bare bullets to structured entries with Status/Why Deferred/Acceptance Criteria |

### Item Findings (issue-881 specific)

| Item | Status | Key Evidence |
|---|---|---|
| Multi-platform ARM64 | Deferred | `FROM` SHA digest is x86_64-only; no ARM64 CI runner |
| Layer caching | Deferred | Source + deps copied together before `pip install`; hatchling makes split non-trivial |
| Resource limits | Deferred | No `--memory`/`--cpus` flags in wrapper script; no profiling data |
| Volume optimization | Deferred | Wrapper uses bind mounts only; named volumes add lifecycle complexity |
| Health checks | Implemented | `docker/Dockerfile:116-117` |

### Acceptance Criteria Template

For container-related deferred items, acceptance criteria typically include:

- **ARM64**: ARM64 CI runner available; `buildx --platform` used; digests updated
- **Layer caching**: Build with source-only changes skips pip install layer; CI time ≥30% faster
- **Resource limits**: Profiling done; flags added as configurable params with documented defaults per tier
- **Volume optimization**: Named volumes created; cold-start ≥20% faster

## Related Skills

- **docker-multistage-build** — Implementing the layer caching improvement
- **pin-npm-dockerfile** — Relates to Dockerfile reproducibility

## References

- Issue #881: <https://github.com/HomericIntelligence/ProjectScylla/issues/881>
- PR #990: <https://github.com/HomericIntelligence/ProjectScylla/pull/990>
- Follow-up from: Issue #759
