---
name: github-relative-doc-links-resolve-to-file-location
description: "GitHub resolves a relative markdown link RELATIVE TO THE FILE'S OWN LOCATION, not the repo root. A doc link added to a file in a subdirectory (e.g. `.github/pull_request_template.md`) needs `../docs/X.md`, not `docs/X.md` — and the rule is easy to get wrong from memory. The robust fix is an ABSOLUTE `https://github.com/<owner>/<repo>/blob/<branch>/docs/X.md` URL that resolves identically from any file location. Also: markdownlint does NOT validate that relative link targets resolve, so a grep + lint pass is green even with a broken link — add an explicit `test -f <target>`. And: do not cite `pixi run markdownlint` without confirming the task exists; in some repos markdown is gated only by a `markdownlint-cli2` pre-commit hook. Use when: (1) adding a doc link inside a markdown file that lives in a subdirectory (`.github/`, `docs/`, `.github/ISSUE_TEMPLATE/`); (2) a plan or PR asserts how GitHub resolves a relative link from a non-root file; (3) an acceptance criterion is 'references doc X' and you need to actually verify the link resolves; (4) a reviewer flags an ambiguous `../docs/...` vs `docs/...` relative link; (5) deciding which lint command actually gates markdown in a repo."
category: documentation
date: 2026-06-23
version: "1.0.0"
user-invocable: false
verification: verified-local
tags: [github, markdown, relative-links, pull-request-template, issue-template, markdownlint, pre-commit, doc-links, blob-url, planning, review]
---

# GitHub Relative Doc Links Resolve to the File's Location, Not the Repo Root

## Overview

| Field | Value |
|-------|-------|
| **Date** | 2026-06-23 |
| **Objective** | Add a doc link inside `.github/pull_request_template.md` and have it resolve correctly on GitHub. The plan first asserted GitHub resolves relative links relative to the repo root, then contradicted itself; the reviewer returned NOGO. |
| **Outcome** | Resolved by sidestepping relative resolution entirely with an absolute `https://github.com/<owner>/<repo>/blob/<branch>/docs/...` URL — backed by a verified in-repo sibling pattern that already does exactly this. |
| **Verification** | verified-local — sibling-pattern evidence and markdownlint link behavior confirmed by grep/inspection in-repo this session; the actual PR's CI not yet observed. |
| **History** | n/a (initial version) |

## When to Use

- Adding a doc link inside a markdown file that lives in a subdirectory (`.github/`, `.github/ISSUE_TEMPLATE/`, `docs/`), not at the repo root.
- A plan or PR body asserts *how* GitHub resolves a relative link from a non-root file — verify before trusting it.
- An acceptance criterion reads "references doc X" and you need to confirm the link actually resolves (not just that lint passes).
- A reviewer flags an ambiguous `../docs/X.md` vs `docs/X.md` relative link.
- Deciding which lint command actually gates markdown in a repo before citing it in a plan.

## Verified Workflow

### Quick Reference

```bash
# 1. The rule: GitHub resolves a relative link RELATIVE TO THE LINKING FILE.
#    From .github/pull_request_template.md, repo-root docs/X.md is "../docs/X.md".
#    Easy to get wrong from memory — so prefer an absolute blob URL instead:
#    https://github.com/<owner>/<repo>/blob/<branch>/docs/X.md
#    (resolves identically regardless of where the linking file lives)

# 2. Find the proven in-repo pattern before inventing a link form.
#    Sibling templates already use absolute blob URLs for exactly this reason:
grep -rn "github.com/.*/blob/" .github/ISSUE_TEMPLATE/

# 3. markdownlint does NOT check that a relative link target exists.
#    Add an explicit existence check whenever a plan says "references doc X":
test -f docs/X.md && echo "OK: target exists" || echo "BROKEN LINK TARGET"

# 4. Confirm the ACTUAL markdown lint runner before citing it in a plan.
grep -n markdownlint pixi.toml        # may be empty — do not assume it exists
grep -n markdownlint .pre-commit-config.yaml   # often the real gate (markdownlint-cli2 hook)
```

### Detailed Steps

1. **Identify the linking file's directory.** A relative link is resolved against
   the directory of the file that contains it, exactly like a browser resolves a
   relative `href`. From `.github/pull_request_template.md`, the repo-root
   `docs/X.md` is `../docs/X.md` — NOT `docs/X.md`, and NOT relative to the repo root.
2. **Prefer an absolute blob URL.** Use
   `https://github.com/<owner>/<repo>/blob/<branch>/docs/X.md`. This resolves the
   same no matter where the linking file lives, removing the entire class of
   relative-path-depth bugs and the "is it `../` or not" ambiguity.
3. **Cite the proven sibling pattern.** Before inventing a link form, grep for how
   existing files in the same directory do it. In ProjectHephaestus,
   `.github/ISSUE_TEMPLATE/bug_report.yml:76` and
   `.github/ISSUE_TEMPLATE/feature_request.yml:58` already link to repo-root docs
   via absolute `blob/main/docs/...` URLs — precisely to avoid relative resolution.
4. **Verify the target exists.** markdownlint validates markdown *syntax*, not that
   a link's target file resolves. A grep + `markdownlint` pass stays green over a
   dead link. When acceptance is "references doc X", add `test -f docs/X.md` (or an
   equivalent link-existence assertion) to the verification step.
5. **Confirm the lint runner exists.** Do not write `pixi run markdownlint` into a
   plan without checking. In ProjectHephaestus markdown is gated by the
   `markdownlint-cli2` pre-commit hook in `.pre-commit-config.yaml`, not a pixi
   task. `grep markdownlint pixi.toml` returns nothing there.

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
|---------|----------------|---------------|----------------|
| 1 | Asserted from memory that GitHub resolves a relative link relative to the repo root, so `docs/X.md` from `.github/pull_request_template.md` would work | GitHub resolves relative links relative to the LINKING FILE's directory; from `.github/` the correct relative path is `../docs/X.md`. The plan asserted the wrong rule and contradicted itself; reviewer returned NOGO | Never assert GitHub relative-link semantics from memory. Resolution is relative-to-file, like a browser `href` — and the safest move is to not rely on it at all |
| 2 | Planned to rely on `grep` + markdownlint to confirm the doc link was valid | markdownlint validates markdown syntax, not link-target resolution; the lint passes even when the target path is wrong/missing. A "references doc X" criterion would be falsely marked satisfied | Add an explicit `test -f <target>` (or link-existence) check; lint is not a link checker |
| 3 | Cited `pixi run markdownlint` as the verification command in the plan | That pixi task does not exist in ProjectHephaestus; markdown is gated by the `markdownlint-cli2` pre-commit hook in `.pre-commit-config.yaml` | Confirm the actual lint runner (`grep markdownlint pixi.toml` + check `.pre-commit-config.yaml`) before naming a command in a plan |

## Results & Parameters

**Robust link form (copy-paste, resolves from ANY file location):**

```markdown
[Contributing guide](https://github.com/<owner>/<repo>/blob/<branch>/docs/CONTRIBUTING.md)
```

**Fragile relative forms (correct path depends on the linking file's directory):**

```markdown
<!-- From a repo-ROOT file (e.g. README.md): -->
[docs](docs/X.md)

<!-- From .github/pull_request_template.md (one level deep): -->
[docs](../docs/X.md)

<!-- WRONG from .github/pull_request_template.md — resolves to .github/docs/X.md (404): -->
[docs](docs/X.md)
```

**Verified in-repo evidence (ProjectHephaestus):**

- `.github/ISSUE_TEMPLATE/bug_report.yml:76` — absolute `blob/main/docs/...` URL.
- `.github/ISSUE_TEMPLATE/feature_request.yml:58` — absolute `blob/main/docs/...` URL.
- Markdown gate: `markdownlint-cli2` hook in `.pre-commit-config.yaml`; no
  `markdownlint` task in `pixi.toml`.

**Verification checklist for "references doc X" acceptance criteria:**

```bash
test -f docs/X.md                          # the target actually exists
grep -q "blob/<branch>/docs/X.md\|\.\./docs/X.md" <linking-file>   # link form is correct for its location
```

## Verified On

| Project | Context | Details |
|---------|---------|---------|
| ProjectHephaestus | Adding a doc link to `.github/pull_request_template.md`; plan asserted wrong relative-resolution rule, reviewer NOGO; fixed with absolute blob URL backed by sibling-template evidence | Sibling links: `.github/ISSUE_TEMPLATE/bug_report.yml:76`, `feature_request.yml:58` |
