---
name: pin-action-shas-to-commit
description: "Pin GitHub Actions version tags to full commit SHAs for supply chain security. Use when: composite action files use mutable tags like @v8 or @v0.9.4 instead of full 40-char commit SHAs."
category: ci-cd
date: 2026-03-07
user-invocable: false
---

# Pin Action SHAs to Commit

## Overview

| Item | Details |
|------|---------|
| Date | 2026-03-07 |
| Objective | Replace mutable version tags in GitHub Actions `uses:` references with pinned commit SHAs |
| Outcome | Supply chain security parity between composite action files and workflow files |

## When to Use

- A repo pins workflow `uses:` references to full SHAs (e.g. `actions/checkout@8e8c483...`) but composite actions under `.github/actions/*/action.yml` still use mutable tags like `@v8` or `@v0.9.4`
- A security audit or follow-up issue flags that composite actions weren't included in the SHA-pinning pass
- CI tooling (e.g. Dependabot, StepSecurity) reports unpinned action references in composite action files

## Verified Workflow

1. **Identify unpinned references** across all action and workflow files:

   ```bash
   grep -rn "uses:.*@v[0-9]" .github/
   ```

2. **Resolve the commit SHA for each tag** using the GitHub API:

   ```bash
   # For a lightweight tag (type: commit) — SHA is directly the commit SHA
   gh api repos/<owner>/<repo>/git/ref/tags/<tag> --jq '.object | {sha, type}'

   # For an annotated tag (type: tag) — dereference the tag object to get commit SHA
   gh api repos/<owner>/<repo>/git/tags/<tag-object-sha> --jq '.object.sha'
   ```

   Example:

   ```bash
   gh api repos/prefix-dev/setup-pixi/git/ref/tags/v0.9.4 --jq '.object | {sha, type}'
   # {"sha":"a0af7a228712d6121d37aba47adf55c1332c9c2e","type":"commit"}

   gh api repos/actions/github-script/git/ref/tags/v8 --jq '.object | {sha, type}'
   # {"sha":"ed597411d8f924073f98dfc5c65a23a2325f34cd","type":"commit"}
   ```

3. **Edit each composite action file**, replacing tag references with SHA + comment:

   ```yaml
   # Before
   uses: prefix-dev/setup-pixi@v0.9.4

   # After
   uses: prefix-dev/setup-pixi@a0af7a228712d6121d37aba47adf55c1332c9c2e  # v0.9.4
   ```

4. **Verify no mutable tags remain**:

   ```bash
   grep -rn "uses:.*@v[0-9]" .github/actions/
   # Expected: no output
   ```

5. **Commit and push**:

   ```bash
   git add .github/actions/setup-pixi/action.yml .github/actions/pr-comment/action.yml
   git commit -m "fix(ci): pin composite action versions to full SHAs"
   git push -u origin <branch>
   ```

## Key Distinctions

- **Composite actions** live at `.github/actions/<name>/action.yml` and are often missed in SHA-pinning passes that focus only on `.github/workflows/`
- **Lightweight tags** (type: `commit`) → the returned SHA is directly the commit SHA
- **Annotated tags** (type: `tag`) → the returned SHA is a tag object; you must dereference it with a second API call to get the actual commit SHA
- **README documentation** — if a workflow README contains `uses:` examples in code blocks, those are prose and do not need pinning (leave them as-is)

## Verified On

| Project | Context | Details |
|---------|---------|---------|
| ProjectOdyssey | PR #3971, issue #3342 | [notes.md](../../references/notes.md) |

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
|---------|----------------|---------------|----------------|
| Searching only `.github/workflows/` | Ran `grep` scoped to workflow files to find unpinned references | Missed composite action files under `.github/actions/` which are in a sibling directory | Always scope search to all of `.github/` not just `.github/workflows/` |
| Assuming issue plan was accurate about file locations | Issue plan claimed no composite action files existed; assumed workflow files were the target | Composite action files existed at `.github/actions/` and were the actual source of the mutable references | Always verify with `grep -rn` rather than trusting issue description about file locations |

## Results & Parameters

**SHA resolution — two-step for annotated tags:**

```bash
# Step 1: get tag ref
RESULT=$(gh api repos/OWNER/REPO/git/ref/tags/TAG --jq '.object | {sha, type}')
TYPE=$(echo "$RESULT" | jq -r '.type')
SHA=$(echo "$RESULT" | jq -r '.sha')

# Step 2: dereference if annotated
if [ "$TYPE" = "tag" ]; then
  SHA=$(gh api repos/OWNER/REPO/git/tags/$SHA --jq '.object.sha')
fi
echo "$SHA"
```

**Pinned reference format:**

```yaml
uses: owner/action@<40-char-sha>  # vX.Y.Z
```

**Verified SHAs (as of 2026-03-07):**

| Action | Tag | Commit SHA |
|--------|-----|-----------|
| `prefix-dev/setup-pixi` | `v0.9.4` | `a0af7a228712d6121d37aba47adf55c1332c9c2e` |
| `actions/github-script` | `v8` | `ed597411d8f924073f98dfc5c65a23a2325f34cd` |
