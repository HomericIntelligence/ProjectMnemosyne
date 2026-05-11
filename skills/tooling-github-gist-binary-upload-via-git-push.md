---
name: tooling-github-gist-binary-upload-via-git-push
description: 'Upload large binary files (up to 100 MB each) to a GitHub Gist by treating
  the gist as a git repo and pushing blobs directly. Use when: you need a permanent URL
  for a binary artifact (core dumps, compressed datasets, CI outputs) and `gh gist create`
  fails because it only accepts text content, and GitHub Actions artifacts have expired
  or will expire.'
category: tooling
date: 2026-05-10
version: 1.0.0
user-invocable: false
---
## Overview

| Field | Value |
| ------- | ------- |
| **Goal** | Attach large binary blobs to a permanent GitHub Gist URL for inclusion in issues, bug reports, or external sharing |
| **Context** | `gh gist create` REST API rejects binary content; GitHub Actions artifacts expire after 14 days by default |
| **Trigger** | Need to share a binary (core dump, compressed archive, dataset) that exceeds Actions artifact retention or text-only gist limits |
| **Output** | A public gist URL with binary file(s) downloadable via raw URLs, suitable for permanent reference in upstream bug reports |

## When to Use

1. Attaching a multi-MB core dump to an upstream issue tracker (e.g., `modular/mojo`) where you need a permanent link beyond the 14-day Actions artifact expiry
2. Archiving CI artifacts (logs, binaries, captures) past the default GitHub Actions retention window
3. Sharing compressed datasets or reproducers with collaborators outside the org without a tagged release
4. Posting a follow-up to a bug report where the original Actions artifact has already expired
5. Need a lower-overhead alternative to GitHub Releases (which require tagging the source repo) for one-off binary sharing

**Do NOT use when:**

- The data is sensitive — gists are public-by-default when shared via URL even with `--secret`
- A single file exceeds **100 MB after compression** — git push to gist hard-fails at that limit
- The artifact is regenerable and a future CI run would suffice — prefer re-running the workflow

## Verified Workflow

### Quick Reference

```bash
# 1. Create a placeholder gist via gh CLI (needs at least one text file)
echo "placeholder" > /tmp/gist-readme.md
gh gist create --public --desc "Description here" /tmp/gist-readme.md
# Output: https://gist.github.com/USER/HASH

# 2. Clone the gist locally (binary push won't work via REST API)
git clone https://gist.github.com/HASH.git /tmp/gist-work
cd /tmp/gist-work

# 3. Compress binaries to fit under 100 MB
xz -k -T 0 -9 path/to/big-binary.bin    # use -9 if -3 produced >100MB
ls -la path/to/big-binary.bin.xz         # verify size

# 4. Stage and push binaries
cp path/to/big-binary.bin.xz /tmp/gist-work/
cp path/to/related-log.txt /tmp/gist-work/
cd /tmp/gist-work
git add -A
git commit -m "Add binary asset"
git push
# GitHub may warn "File X is N MB; larger than recommended 50 MB" but push succeeds at <100 MB
```

### Step 1: Create a placeholder gist via the REST API

The `gh gist create` command requires at least one text file. Create a readable README first
so the gist exists with a known URL — binaries get pushed in later via git.

```bash
echo "Core dump + reproducer for modular/mojo#NNNN" > /tmp/gist-readme.md
gh gist create --public --desc "Mojo JIT crash reproducer 2026-05-10" /tmp/gist-readme.md
# Output: https://gist.github.com/<user>/<hash>
```

Capture the gist URL — you need the `<hash>` for the clone step.

### Step 2: Clone the gist as a normal git repo

Gists are full git repositories. The HTTPS clone URL is `https://gist.github.com/<hash>.git`
(no username segment needed).

```bash
git clone https://gist.github.com/<hash>.git /tmp/gist-work
cd /tmp/gist-work
```

### Step 3: Compress aggressively to fit under 100 MB

GitHub enforces a **100 MB hard limit per file** on git push. It also prints a warning at the
50 MB "recommended" threshold but accepts the push. Always use `xz -9 -T 0` (max compression,
all cores) for binary blobs — `xz -3` produces ~10–15% larger output and can cross the 100 MB line.

```bash
xz -k -T 0 -9 path/to/core.bin             # -k keeps the original; -9 = max ratio; -T 0 = all threads
ls -la path/to/core.bin.xz                 # verify < 100 MB
```

Empirical ratio (verified 2026-05-10): a 662 MB ELF core compressed from 105 MB (`xz -3`,
blocked by limit) → 80 MB (`xz -9`, pushed successfully). On a different 842 MB core,
`xz -3` produced 105 MB and was rejected; `xz -9` brought it to ~72 MB.

### Step 4: Stage and push binaries via git

```bash
cp path/to/core.bin.xz /tmp/gist-work/
cp path/to/reproducer.log /tmp/gist-work/
cd /tmp/gist-work
git add -A
git commit -m "Add core dump + reproducer for modular/mojo#NNNN"
git push
```

Expected output: `remote: warning: File core.bin.xz is 80.00 MB; this is larger than GitHub's
recommended maximum file size of 50.00 MB` followed by a successful push. The warning is
informational only — the push completes and the file is downloadable.

### Step 5: Link the gist in the upstream issue

Reference the raw URL pattern in your bug report so reviewers can download directly:

```text
Core dump: https://gist.github.com/<user>/<hash>/raw/<commit-sha>/core.bin.xz
Reproducer: https://gist.github.com/<user>/<hash>/raw/<commit-sha>/reproducer.log
```

The `<commit-sha>` is optional; omitting it serves the latest revision of the file from the
gist's default branch.

### Step 6: Clean up local artifacts (optional)

The gist persists indefinitely. Local working directory can be removed:

```bash
rm -rf /tmp/gist-work
```

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
| --------- | ---------------- | --------------- | ---------------- |
| `gh gist create --filename core.bin.xz core.bin.xz` | Pass a binary file directly to `gh gist create` | The REST API path validates content as UTF-8 text; binary bytes produce a gist where the file appears empty or corrupted with no error from `gh` | Use the gh CLI only to create a placeholder text gist; push binaries via `git push` instead |
| GitHub Releases as alternative | Considered uploading core dump as a Release asset (no size cap) | Requires a tagged release in the source repo, which adds noise to the changelog for a one-off CI artifact | Use gists for ad-hoc binary sharing; reserve Releases for actual versioned deliverables |
| `xz -3` (default-ish compression) on 842 MB core | Faster compression for quick iteration | Produced 105 MB output, exceeding the 100 MB per-file git push hard limit; push rejected with `remote: error: File X is N MB; this exceeds GitHub's file size limit of 100.00 MB` | Always use `xz -9 -T 0` for binaries near the size threshold — the 5x slowdown is worth the ~15% better ratio |
| Pushing without compression | Attempted to push raw 662 MB core dump | Push rejected at the 100 MB per-file limit; no warning, hard error | Compression is mandatory for any binary >100 MB |
| Using `--secret` to gate access | Created gist with `gh gist create --secret` and shared URL in issue | "Secret" gists are unlisted but anyone with the URL can read them — no actual auth gate | Do not put sensitive data in any gist regardless of `--secret`; use private repos or signed URLs instead |

## Results & Parameters

**Per-file size limit (git push to gist)**: 100 MB hard cap, 50 MB recommended (warning only, push succeeds).

**Compression ratio reference** (xz on ELF core dumps, verified 2026-05-10):

| Input | `xz -3` output | `xz -9 -T 0` output | Verdict |
| ----- | -------------- | ------------------- | ------- |
| 662 MB ELF core | ~105 MB (blocked) | 80 MB (pushed OK) | Use `-9` |
| 842 MB ELF core | 105 MB (blocked) | ~72 MB (pushed OK) | Use `-9` |

**Recommended xz invocation**:

```bash
xz -k -T 0 -9 <file>    # -k=keep original, -T 0=all threads, -9=max compression
```

**Raw download URL pattern**:

```text
https://gist.github.com/<user>/<hash>/raw/<file>
https://gist.github.com/<user>/<hash>/raw/<commit-sha>/<file>   # pin to a specific revision
```

**Constraints to remember**:

- Public-by-default when URL is shared, even with `--secret` — never use for sensitive data
- Web UI shows "No preview available" for binary files, but raw URLs work fine for downloads
- 100 MB cap is **per file**, not per gist — you can attach multiple binaries as long as each fits

**Verification status**: verified-local — gist created + 80 MB binary pushed successfully on 2026-05-10.
