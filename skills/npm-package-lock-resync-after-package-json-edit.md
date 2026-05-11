---
name: npm-package-lock-resync-after-package-json-edit
description: "Regenerate and commit package-lock.json in the SAME PR whenever a Node.js dependency in package.json changes (add/remove/upgrade/downgrade). CI uses `npm ci` (strict) and will fail with EUSAGE 'lock file's X@A.B.C does not satisfy X@D.E.F' if the lockfile is stale. Use when: (1) editing any dependency version in package.json, (2) an audit/easy-issue says 'downgrade X to satisfy engines constraint', (3) dispatching a sub-agent to edit package.json, (4) the repo has multiple Node sub-projects (e.g., `dagger/package.json` plus root) and you might miss the right lockfile."
category: ci-cd
date: 2026-05-10
version: "1.0.0"
user-invocable: false
verification: verified-ci
tags: [npm, package-json, package-lock, lockfile, npm-ci, eusage, node, dagger, sub-agent-dispatch, easy-issue, engines]
---

# npm: Resync package-lock.json After Editing package.json

## Overview

| Field | Value |
| ------- | ------- |
| **Date** | 2026-05-10 |
| **Objective** | Prevent `npm ci` regressions caused by editing `package.json` without regenerating the sibling `package-lock.json` in the same PR |
| **Outcome** | Successful — pattern verified by ProjectProteus PR #136, which restored the lockfile after PR #135 broke CI |
| **Verification** | verified-ci — Proteus #136 regenerates `dagger/package-lock.json` via `npm install` and commits ONLY the lockfile; subsequent `npm ci` runs clean |

## When to Use

- **Editing any dependency version in `package.json`** — added, removed, upgraded, or downgraded (including `dependencies`, `devDependencies`, `peerDependencies`, `optionalDependencies`).
- **Audit issue says "downgrade X to satisfy `engines` constraint"** — never edit `package.json` alone. The lockfile is part of the same atomic change.
- **Sub-agent dispatch prompts that ask for `package.json` edits** — the brief MUST explicitly tell the sub-agent to regenerate the lockfile in the same directory.
- **CI uses `npm ci`** (the strict mode) rather than `npm install`. `npm ci` refuses to install if `package.json` and `package-lock.json` disagree.
- **Repo has multiple Node sub-projects** (e.g., `dagger/package.json` plus a root `package.json`) — easy to miss the right lockfile when running `find` from the wrong directory.

## Verified Workflow

### Quick Reference

```bash
# 1. cd to the SAME directory as the package.json you edited
cd <pkg-dir>          # e.g., cd dagger

# 2. Regenerate the lockfile (this updates package-lock.json AND populates node_modules/)
npm install

# 3. Stage ONLY the lockfile (never node_modules/)
git add package-lock.json

# 4. Commit with a message that ties the lockfile bump to the package.json edit
git commit -m "chore(<pkg-dir>): regenerate package-lock.json after @types/node downgrade"
```

Suggested commit-message conventions:

- `chore(<pkg-dir>): regenerate package-lock.json after <dep> <action>`
- `fix(<pkg-dir>): resync package-lock.json with package.json (<dep> <old> -> <new>)`
- For combined PRs: include both files in one commit `chore(<pkg-dir>): downgrade <dep> to <range> + lockfile`.

### Detailed Steps

1. **Identify which directory owns the `package.json` you edited.** If the file is `dagger/package.json`, you must `cd dagger` before running `npm install`. Running it from the repo root regenerates the WRONG lockfile (or none at all).

2. **Confirm a lockfile exists in that directory** before assuming there is none:

   ```bash
   ls <pkg-dir>/package-lock.json <pkg-dir>/npm-shrinkwrap.json 2>/dev/null
   ```

   Do NOT trust a project-root `find . -name package-lock.json` that returned empty if you ran it from the wrong CWD or with restrictive `-maxdepth`.

3. **Run `npm install` in that directory.** This rewrites `package-lock.json` to match the new `package.json` and creates `node_modules/`. The `node_modules/` directory should NOT be committed (it is normally gitignored — verify before staging).

4. **Stage only the lockfile.**

   ```bash
   git status                        # confirm package-lock.json is the only new/changed file you want
   git add <pkg-dir>/package-lock.json
   ```

5. **Verify locally with the same command CI runs:**

   ```bash
   cd <pkg-dir>
   rm -rf node_modules
   npm ci                            # must succeed cleanly with no EUSAGE error
   ```

6. **Commit and push.** Include the lockfile in the same PR as the `package.json` edit. Never split them across two PRs.

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
| --------- | ---------------- | --------------- | ---------------- |
| Easy-issue sweep agent (Proteus #135) | Edited `dagger/package.json` to downgrade `@types/node` from `^25.x` to `^20.x`, claimed "no `package-lock.json` present", merged | Agent ran `find . -name package-lock.json` from repo root with the wrong CWD/depth assumption and missed `dagger/package-lock.json`. CI then failed with `npm error code EUSAGE` and `Invalid: lock file's @types/node@25.6.2 does not satisfy @types/node@20.19.40` | Always run `ls <pkg-dir>/package-lock.json` from the same directory as the edited `package.json`. Never trust a single `find` result as proof a lockfile is absent. |
| Edit `package.json` and push without `npm install` | Hoping local `node_modules/` was fresh enough that everything "just works" | Local builds may use `npm install` (which mutates the lockfile) or pre-existing `node_modules/`, masking the problem. CI uses `npm ci` (strict) and refuses any `package.json` <-> `package-lock.json` mismatch | Use the same command CI uses: `npm ci` after `rm -rf node_modules`. If that fails locally, it will fail in CI. |
| Run `npm install` from the repo root when `package.json` is nested | Assumed npm would auto-discover the right package | npm only operates on the CWD's `package.json`. From the repo root with no root `package.json`, the command errors or regenerates an unrelated lockfile | Always `cd <pkg-dir>` first. The lockfile lives next to its `package.json`. |
| Commit `node_modules/` along with the lockfile | Trying to "be safe" by committing the resolved tree | `node_modules/` is large, platform-specific, and gitignored for a reason. Bloats the diff and clutters review | Only `package-lock.json` belongs in the commit. Confirm `.gitignore` covers `node_modules/`. |

## Results & Parameters

### Pattern: Expand Easy-Issue Briefs

When an easy-issue brief says **"change `<dep>`'s version in package.json"**, mentally (and in any sub-agent prompt) expand it to:

> "Change `<dep>`'s version in `<pkg-dir>/package.json` AND regenerate `<pkg-dir>/package-lock.json` by running `npm install` in `<pkg-dir>/`. Commit both files in the same PR."

### Sub-Agent Dispatch Template Addition

Append this clause to any dispatch brief that may touch a `package.json`:

```text
If you edit any package.json:
  1. cd into the SAME directory as that package.json.
  2. Run `npm install` to regenerate package-lock.json.
  3. Run `rm -rf node_modules && npm ci` to verify the lockfile is in sync.
  4. Stage and commit ONLY package.json AND package-lock.json (NOT node_modules/).
  5. Both files MUST land in the same PR.
CI uses `npm ci`, which is strict and will fail with EUSAGE if the lockfile is stale.
```

### Expected Output

A successful regeneration looks like:

```text
$ cd dagger
$ npm install
added 142 packages, and audited 143 packages in 4s
$ rm -rf node_modules && npm ci
added 142 packages in 3s
$ git status
  modified:   dagger/package.json
  modified:   dagger/package-lock.json
```

CI then passes with no `npm error code EUSAGE` lines.

## Verified On

| Project | Context | Details |
| --------- | --------- | --------- |
| ProjectProteus | PR #135 (regression source) — `@types/node` downgraded in `dagger/package.json` only; `npm ci` failed with EUSAGE in follow-up workflow run | Easy-issue sweep agent missed `dagger/package-lock.json` |
| ProjectProteus | PR #136 (fix) — regenerated `dagger/package-lock.json` via `npm install` in `dagger/`, committed lockfile only, CI green | Validates the regen-and-commit pattern end-to-end |

## References

- [npm ci documentation](https://docs.npmjs.com/cli/v10/commands/npm-ci) — explains the strict mode and the EUSAGE error class
- [npm install documentation](https://docs.npmjs.com/cli/v10/commands/npm-install) — the command that regenerates `package-lock.json`
- [package-lock.json reference](https://docs.npmjs.com/cli/v10/configuring-npm/package-lock-json)
