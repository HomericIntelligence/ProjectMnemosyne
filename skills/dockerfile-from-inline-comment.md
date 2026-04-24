---
name: dockerfile-from-inline-comment
description: "Use when: (1) Docker build fails with 'FROM requires either one or three arguments', (2) a Dockerfile FROM line has a comment after the image digest or tag, (3) adding comments to FROM lines in Dockerfiles."
category: ci-cd
date: 2026-04-23
version: "1.0.0"
user-invocable: false
verification: verified-ci
tags: [docker, dockerfile, from, comment, parse-error, sha256, digest]
---

# Dockerfile FROM Inline Comment Parse Error

## Overview

| Field | Value |
|-------|-------|
| **Date** | 2026-04-23 |
| **Objective** | Fix Docker build parse error caused by inline comments on FROM lines |
| **Outcome** | All three base Dockerfiles fixed; CI passed after removing inline comments |
| **Verification** | verified-ci |

## When to Use

- Docker build fails with `FROM requires either one or three arguments`
- A Dockerfile has an inline comment after the image tag or SHA256 digest on the `FROM` line
- Adding human-readable labels to `FROM` lines (put them ABOVE, not after)

## Verified Workflow

### Quick Reference

```bash
# Find all FROM lines with inline comments
grep -rn "^FROM.*#" bases/ vessels/ Dockerfile*

# Fix: move comment above FROM
# WRONG:
# FROM debian:bookworm-slim@sha256:abc123... # debian:bookworm-slim
#
# CORRECT:
# # debian:bookworm-slim
# FROM debian:bookworm-slim@sha256:abc123...
```

### Detailed Steps

1. Search for offending FROM lines across all Dockerfiles:
   ```bash
   grep -rn "^FROM.*#" .
   ```

2. For each match, move the inline comment to a standalone line above the FROM instruction:
   ```dockerfile
   # Before (BROKEN — comment treated as 4th argument):
   FROM debian:bookworm-slim@sha256:4724b8cc... # debian:bookworm-slim

   # After (CORRECT — comment on its own line):
   # debian:bookworm-slim
   FROM debian:bookworm-slim@sha256:4724b8cc...
   ```

3. Rebuild to verify the parse error is gone:
   ```bash
   docker build -f bases/Dockerfile.node -t achaean-base-node:latest .
   ```

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
|---------|----------------|---------------|----------------|
| Inline comment after SHA256 digest | `FROM debian:bookworm-slim@sha256:abc123... # label` | Docker parser treats `# label` as a 4th positional argument to FROM; FROM only accepts 1 or 3 args | Comments on FROM lines must be on a separate line above the instruction, never inline |

## Results & Parameters

### Error Message

```
failed to solve: failed to read dockerfile: dockerfile parse error on line N:
FROM requires either one or three arguments
```

### Root Cause

Docker's Dockerfile parser does not strip inline comments from instruction lines the way a shell would. A `#` after arguments to `FROM` is parsed as an additional positional argument, not a comment. This makes the parser see 4 arguments (`image`, `@sha256`, `digest`, `#label`) when it expects 1 (just the image ref) or 3 (for multi-stage: `FROM image AS name`).

### Pattern to Fix

| Pattern | Status | Notes |
|---------|--------|-------|
| `FROM image:tag # comment` | BROKEN | Comment is 2nd arg; only 1 allowed unless AS alias is 3rd |
| `FROM image@sha256:... # comment` | BROKEN | Comment is 4th arg when combined with digest |
| `# comment\nFROM image:tag` | CORRECT | Comment on its own line before FROM |
| `FROM image:tag AS alias` | CORRECT | Legal 3-arg form: image AS alias |

## Verified On

| Project | Context | Details |
|---------|---------|---------|
| AchaeanFleet | CI repair session — all 3 base Dockerfiles had this issue | 2026-04-23; CI went green after fix |
