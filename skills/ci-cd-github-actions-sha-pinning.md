---
name: ci-cd-github-actions-sha-pinning
description: "Use when: (1) pinning GitHub Actions to immutable commit SHAs for supply-chain security, (2) resolving annotated vs lightweight tags to find the underlying commit SHA, (3) auditing a workflow file for mutable @vN or @vN.N.N tags that should be SHA-pinned, (4) verifying that a newly added or updated action is using the correct commit SHA"
category: ci-cd
date: 2026-04-24
version: 1.0.0
user-invocable: false
verification: verified-ci
tags:
  - github-actions
  - sha-pinning
  - supply-chain
  - security
  - annotated-tags
---

## Overview

| Field | Value |
| ------- | ------- |
| Date | 2026-04-24 |
| Objective | Document how to resolve immutable commit SHAs for GitHub Actions supply-chain hardening |
| Outcome | Verified SHA pinning applied in AchaeanFleet PR #549; CI passed |
| Verification | verified-ci |

## When to Use

- A workflow file uses mutable tags like `@v4`, `@v3.3.0`, or `@main` for any `uses:` action
- Adding a new action and need the commit SHA before merging
- Auditing an existing workflow for supply-chain vulnerabilities
- A tag is an annotated tag (common for major-version aliases) and the first SHA lookup returns the wrong type

## Problem

GitHub Actions that reference mutable version tags (`@v4`, `@v3.3.0`) can be silently replaced if a maintainer's account is compromised. A new commit is pushed to the same tag, and every pipeline that uses `@v4` automatically runs the malicious code.

**Fix**: Pin every `uses:` line to the exact, immutable commit SHA.

### Key Concepts: Annotated vs Lightweight Tags

GitHub supports two tag types, and you **must** handle both:

| Tag type | `git/ref/tags/<tag>` returns | Resolution needed? |
| ---------- | ----------------------------- | -------------------- |
| Lightweight | Commit SHA directly | No — use it as-is |
| Annotated | Tag-object SHA (not a commit) | Yes — one extra API call |

Major-version aliases like `@v4` are **almost always annotated tags** pointing to the latest patch.
Specific version tags like `@v4.1.7` are **often lightweight** (already commit SHAs).

---

## Verified Workflow

### Quick Reference

| Action | Tag | Commit SHA (2026-04-24) | Tag type |
| -------- | ----- | ------------------------ | ---------- |
| `actions/checkout` | `v4` (v4.1.7) | `34e114876b0b11c390a56381ad16ebd13914f8d5` | lightweight |
| `hadolint/hadolint-action` | `v3.3.0` | `2332a7b74a6de0dda2e2221d575162eba76ba5e5` | lightweight |
| `github/codeql-action/upload-sarif` | `v3` | `ce64ddcb0d8d890d2df4a9d1c04ff297367dea2a` | annotated |
| `actions/cache` | `v4.0.2` | `0057852bfaa89a56745cba8c7296529d2fc39830` | lightweight |
| `aquasecurity/trivy-action` | `v0.36.0` | `a9c7b0f06e461e9d4b4d1711f154ee024b8d7ab8` | lightweight |

> **These SHAs will go stale.** Use Dependabot or Renovate to keep them up to date after initial pinning.

### Step 1: Get the tag's object SHA

```bash
gh api "repos/<owner>/<repo>/git/ref/tags/<tag>" --jq '.object | {sha, type}'
# → {"sha": "...", "type": "commit"}   ← lightweight, done
# → {"sha": "...", "type": "tag"}      ← annotated, need Step 2
```

### Step 2: If annotated, dereference to the commit SHA

```bash
gh api "repos/<owner>/<repo>/git/tags/<sha-from-step1>" --jq '.object.sha'
```

**If you get HTTP 404**, the tag is lightweight — the SHA from Step 1 **is** the commit SHA.

### Step 3: Use in workflow YAML with version comment

Always include the human-readable tag as a comment:

```yaml
steps:
  - uses: actions/checkout@34e114876b0b11c390a56381ad16ebd13914f8d5  # v4.1.7
  - uses: hadolint/hadolint-action@2332a7b74a6de0dda2e2221d575162eba76ba5e5  # v3.3.0
  - uses: github/codeql-action/upload-sarif@ce64ddcb0d8d890d2df4a9d1c04ff297367dea2a  # v3
  - uses: actions/cache@0057852bfaa89a56745cba8c7296529d2fc39830  # v4.0.2
  - uses: aquasecurity/trivy-action@a9c7b0f06e461e9d4b4d1711f154ee024b8d7ab8  # v0.36.0
```

### Quick Bash Function

Add to your shell or CI helper script to look up any action's commit SHA:

```bash
gha_sha() {
  local owner_repo="$1"   # e.g. "actions/checkout"
  local tag="$2"           # e.g. "v4" or "v4.1.7"

  local result
  result=$(gh api "repos/${owner_repo}/git/ref/tags/${tag}" --jq '.object | {sha, type}')
  local sha type
  sha=$(echo "$result" | jq -r '.sha')
  type=$(echo "$result" | jq -r '.type')

  if [ "$type" = "tag" ]; then
    sha=$(gh api "repos/${owner_repo}/git/tags/${sha}" --jq '.object.sha')
    echo "Annotated tag resolved → commit SHA: $sha"
  else
    echo "Lightweight tag → commit SHA: $sha"
  fi

  echo "  uses: ${owner_repo}@${sha}  # ${tag}"
}

# Usage:
# gha_sha "actions/checkout" "v4"
# gha_sha "github/codeql-action" "v3"
```

### Keeping SHAs Updated

After initial pinning, automate updates so SHAs don't drift:

```yaml
# .github/dependabot.yml
version: 2
updates:
  - package-ecosystem: github-actions
    directory: /
    schedule:
      interval: weekly
```

Dependabot will open PRs that update the SHA and the version comment simultaneously.
Renovate's `github-actions` manager does the same.

---

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
| --------- | ---------------- | --------------- | ---------------- |
| `gh api "repos/<owner>/<repo>/commits/<tag>"` | Used the `commits` endpoint with a tag name | Returns HTTP 422 for non-commit refs (annotated tags point to tag objects, not commits) | Always use `git/ref/tags/` endpoint, not `commits/` |
| Trusting `git/ref/tags/<tag>.sha` for annotated tags | Used the SHA directly from the `git/ref/tags/` response without checking `.object.type` | The SHA is a tag-object SHA, not a commit SHA — using it in `uses:` causes workflow failure | Always check `.object.type`; if `"tag"`, dereference with `git/tags/<sha>` |
| Pinning only major version aliases | Pinned `@v4` to a SHA but left `@v3.3.0` as a mutable tag | Named version tags can still be moved (rare but possible for yanked releases) | Pin all `uses:` lines regardless of whether they use major or patch versions |

---

## Results & Parameters

### Resolution Summary (AchaeanFleet PR #549, 2026-04-24)

| Action | Tag consulted | `.object.type` | Extra dereference? | Final commit SHA |
| -------- | -------------- | --------------- | -------------------- | ----------------- |
| `actions/checkout` | `v4` | `commit` | No | `34e114876b0b11c390a56381ad16ebd13914f8d5` |
| `hadolint/hadolint-action` | `v3.3.0` | `commit` | No | `2332a7b74a6de0dda2e2221d575162eba76ba5e5` |
| `github/codeql-action/upload-sarif` | `v3` | `tag` (annotated) | Yes (tag obj: `865f5f5c`) | `ce64ddcb0d8d890d2df4a9d1c04ff297367dea2a` |
| `actions/cache` | `v4.0.2` | `commit` | No | `0057852bfaa89a56745cba8c7296529d2fc39830` |
| `aquasecurity/trivy-action` | `v0.36.0` | `commit` | No | `a9c7b0f06e461e9d4b4d1711f154ee024b8d7ab8` |

### CI Outcome

- PR #549 merged to AchaeanFleet `main`
- All CI checks passed with SHA-pinned actions
- No workflow behavior change — SHA pinning is transparent to execution
