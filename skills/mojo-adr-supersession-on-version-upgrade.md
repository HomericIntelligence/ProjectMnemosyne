---
name: mojo-adr-supersession-on-version-upgrade
description: "Mark ADRs as Superseded after a Mojo version upgrade removes the limitation they document. Use when: (1) bumping the pinned Mojo version in pixi.toml, (2) an ADR describes a compiler limitation or missing feature that may now work, (3) code still carries scalar workarounds that vectorized paths could replace."
category: documentation
date: 2026-04-11
version: "1.0.0"
user-invocable: false
verification: verified-local
tags: [mojo, adr, superseded, version-upgrade, workaround, fp16, simd]
---

# Mojo ADR Supersession on Version Upgrade

## Overview

| Field | Value |
| ------- | ------- |
| **Date** | 2026-04-11 |
| **Objective** | Ensure ADRs that document compiler limitations are re-tested and marked Superseded when a Mojo version upgrade fixes them |
| **Outcome** | Successful — ADR-010 (FP16 SIMD unsupported in 0.26.1) found still showing "Accepted" after upgrade to 0.26.3 where FP16 SIMD works fully |
| **Verification** | verified-local — test confirmed FP16 SIMD works in Mojo 0.26.3 |
| **History** | [changelog](./mojo-adr-supersession-on-version-upgrade.history) |

## When to Use

- After bumping the pinned Mojo version in `pixi.toml`
- An ADR has `Status: Accepted` and describes a compiler limitation, missing stdlib feature, or workaround
- Code contains comments like `# See ADR-NNN` near scalar paths that were created to avoid a broken feature
- Developers are still using workarounds documented in an ADR (e.g., scalar FP16 ops instead of SIMD)
- Reviewing a PR and noticing outdated ADR references

## Verified Workflow

### Quick Reference

```bash
# After bumping mojo version in pixi.toml, find ADRs describing limitations
grep -l "Limitation\|workaround\|not supported\|blocked\|missing" docs/adr/*.md

# For each candidate ADR, extract the claimed-broken behavior and test it
# Example: ADR-010 claimed SIMD[DType.float16, N] fails
cat > /tmp/test_claim.mojo << 'EOF'
def main():
    var v = SIMD[DType.float16, 8](1.0, 2.0, 3.0, 4.0, 5.0, 6.0, 7.0, 8.0)
    print(v)
EOF
pixi run mojo run /tmp/test_claim.mojo
# If passes → mark ADR Superseded and remove workarounds
# If fails  → ADR still valid, leave it alone

# ADR supersession banner — add at top of file, before ## Executive Summary
# > ⚠️ **SUPERSEDED** — <reason>. Retained for historical context only.
# **Status**: Superseded (<reason>, <date>)
```

### Detailed Steps

1. **Find ADR candidates** after each version bump:

   ```bash
   grep -l "Limitation\|workaround\|not supported\|blocked\|missing" docs/adr/*.md
   ```

2. **For each candidate**, extract the claimed-broken behavior (usually in an "Executive Summary"
   or "Technical Evidence" section) and write a 3-5 line test that exercises it directly.

3. **Run the test** inside the Podman container (to match CI environment):

   ```bash
   just shell
   pixi run mojo run /tmp/test_claim.mojo
   ```

4. **If the test passes** → mark the ADR Superseded:

   a. Add a prominent banner **before** `## Executive Summary`:

   ```markdown
   > ⚠️ **SUPERSEDED** — `SIMD[DType.float16, N]` is fully supported in Mojo 0.26.3.
   > The scalar workaround has been replaced with vectorized `load + cast` in
   > `shared/training/mixed_precision.mojo`. This ADR is retained for historical context only.

   **Status**: Superseded (by Mojo 0.26.3 FP16 SIMD support, YYYY-MM-DD)
   ```

   b. Update `**Status**:` in the Document Metadata section to match.

   c. Mark "Future" checklist items as complete with a phase label:

   ```markdown
   ### Phase 2: Supersession (COMPLETE — Mojo 0.26.3, YYYY-MM-DD)
   - [x] Implement SIMD vectorized FP16↔FP32 paths
   - [x] Mark this ADR as Superseded
   - [x] Remove scalar workaround comments
   ```

   d. Add a `**Superseded By**:` line to Document Metadata:

   ```markdown
   - **Superseded By**: Mojo 0.26.3 native FP16 SIMD support (YYYY-MM-DD)
   ```

   e. Add a `v2.0` row to the Revision History table.

5. **Update code workarounds** that the ADR justified:

   - Remove the scalar hot path and replace with the proper implementation (e.g., vectorized SIMD).
   - Update comments referencing the ADR:
     - Before: `# See ADR-010: FP16 SIMD not supported`
     - After:  `# ADR-010 superseded in 0.26.3 — now using native SIMD`
   - Delete any issue template files that described the now-resolved limitation.

6. **If the test still fails** — leave the ADR as-is. The limitation is still real.

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
| --------- | ---------------- | --------------- | ---------------- |
| Skipping re-test | Assumed version bump automatically supersedes old ADRs | ADR-010 stayed "Accepted" for months while FP16 SIMD already worked in 0.26.3 | Always write a concrete test for the claimed limitation — assumption is not evidence |
| Updating status only | Changed `Status: Accepted` → `Status: Superseded` without adding banner | Other developers missed the status change buried in Document Metadata | Add a visible banner at the top of the file, not just in the metadata |
| Removing workarounds without documenting why | Replaced scalar FP16 with SIMD but left no comment explaining the change | Future reviewers confused about why the scalar code was removed | Update ADR-referencing comments to say "ADR-NNN superseded in X.Y.Z" |

## Results & Parameters

### What a Properly Superseded ADR Looks Like

```markdown
> ⚠️ **SUPERSEDED** — `SIMD[DType.float16, N]` is fully supported in Mojo 0.26.3.
> The scalar workaround has been replaced with vectorized `load + cast` in
> `shared/training/mixed_precision.mojo`. This ADR is retained for historical context only.

**Status**: Superseded (by Mojo 0.26.3 FP16 SIMD support, 2026-04-11)

## Executive Summary
...
```

### Document Metadata block (after supersession)

```markdown
- **Status**: Superseded
- **Superseded By**: Mojo 0.26.3 native FP16 SIMD support (2026-04-11)
- **Date**: 2026-01-15
- **Last Updated**: 2026-04-11
```

### Revision History table (add v2.0 row)

```markdown
| Version | Date       | Author        | Changes                                    |
|---------|------------|---------------|--------------------------------------------|
| 2.0     | 2026-04-11 | Claude Code   | Marked Superseded — FP16 SIMD works in 0.26.3 |
| 1.0     | 2026-01-15 | Micah Villmow | Initial ADR                                |
```

### Consequences of Not Superseding

- Developers continue to use scalar workarounds that are no longer needed (slower code)
- Agents create issue templates for already-fixed bugs
- Blog posts and documentation claim features are broken when they work
- New team members waste time implementing workarounds that have been solved

## Verified On

| Project | Context | Details |
| --------- | --------- | --------- |
| ProjectOdyssey | Mojo 0.26.1 → 0.26.3 version bump | ADR-010 (FP16 SIMD) found still "Accepted"; confirmed FP16 SIMD works in 0.26.3 |
