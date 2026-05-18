---
name: rebase-merge-shadow-var-tdz-ts-error
description: "Diagnose and fix TypeScript TS7022 + TS2448 errors that appear only after a rebase or merge, when two non-overlapping branch edits independently introduced a function parameter and a local `const` of the same name in the same scope — producing a shadowing/TDZ bug that auto-merge cannot detect. Use when: (1) CI fails after rebase with TS7022/TS2448 on adjacent lines for the same identifier, (2) the file compiled cleanly on both source branches individually, (3) no conflict markers appeared during the rebase."
category: debugging
date: 2026-05-18
version: "1.0.0"
user-invocable: false
verification: verified-ci
tags: [typescript, rebase, merge, shadowing, tdz, ts7022, ts2448, block-scoped, dagger, achaeanfleet]
---

# Rebase/Merge Produces Shadow-Variable TDZ TypeScript Error (TS7022 + TS2448)

## Overview

| Field | Value |
| ------- | ------- |
| **Date** | 2026-05-18 |
| **Objective** | Diagnose and fix TypeScript TS7022 + TS2448 errors that appear *only* after a rebase or merge, where a successful auto-merge introduced a shadowing/TDZ bug between a function parameter and a local `const` of the same name |
| **Outcome** | Successful. Renaming the inner local `const` (cheaper than renaming the parameter at every call site) restores a clean type-check. |
| **Verification** | verified-ci (fix landed on AchaeanFleet PR #661 commit `9ada664`; "Validate Dagger Pipeline → Type-check TypeScript pipeline" turned green and the PR auto-merged) |

## The Bug Pattern

A rebase or merge produces a hybrid `.ts` file where a local `const tags = [...]` array is declared inside a function whose **parameter is also named** `tags: { shortSha: string; dateTag: string }`. The local array's initializer references `tags.shortSha` and `tags.dateTag` (intending the parameter) — but because of block-scoping, those references resolve to the not-yet-initialized local array, producing:

```
error TS7022: 'tags' implicitly has type 'any' because it does not have a type annotation
              and is referenced directly or indirectly in its own initializer.
error TS2448: Block-scoped variable 'tags' used before its declaration.
```

The bug compiled cleanly on each branch individually (each branch had a self-consistent version) but the merge produced a broken hybrid:

- **Branch A** renamed the parameter to `tags: {...}`
- **Branch B** independently introduced the local `const tags = [...]` array

Neither developer saw the conflict because the change locations were different lines. Git's auto-merge resolves **textual** conflicts, not **semantic** ones — two non-overlapping edits in the same lexical scope can produce shadowing/TDZ bugs that compile-time enforcement only catches *after* the merge.

## When to Use

- After rebasing or resolving a merge conflict in a TypeScript file
- CI reports `TS7022` + `TS2448` on adjacent lines for the same identifier
- The file compiled cleanly on both source branches individually
- Diff-3 conflict markers may NOT have appeared — the conflict was textually adjacent enough to auto-merge but semantically broken
- Same pattern recurs in any language with block-scoping (let/const in JS, var-in-block in C++) when two non-overlapping branch edits independently introduce a parameter and a local with the same name

## Verified Workflow

```bash
# 1. Reproduce locally: rebase onto the new base
git rebase origin/main

# 2. Run the type-checker
cd dagger && npm ci && npx tsc --noEmit

# 3. If you see TS7022 + TS2448 on the same identifier on adjacent lines,
#    look for a parameter and a const with the same name in the same scope.
grep -n -B2 -A2 "const tags = \[" pipeline.ts

# 4. Rename the inner const (cheaper than renaming the param everywhere)
#    e.g., tags -> tagList
sed -i 's/const tags = \[/const tagList = [/g; s/for (const tag of tags)/for (const tag of tagList)/g' pipeline.ts

# 5. Re-typecheck — should be silent
npx tsc --noEmit
```

## Results & Parameters (the actual fix from PR #661)

File: `dagger/pipeline.ts`

Diff (sole change in commit `9ada664`):

```diff
-      const tags = [
+      const tagList = [
         `${registry}/${base.name}:latest`,
         `${registry}/${base.name}:git-${tags.shortSha}`,
         `${registry}/${base.name}:${tags.dateTag}`,
       ];
-      for (const tag of tags) {
+      for (const tag of tagList) {
```

Applied identically in both `buildBases` and `buildVessels`. Local `npx tsc --noEmit` exits 0 after the rename; CI's "Validate Dagger Pipeline → Type-check TypeScript pipeline" step turns SUCCESS.

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
|---|---|---|---|
| Trust auto-merge / non-conflicting rebase | Assumed a successful `git rebase` with no conflict markers meant the result was semantically correct | Auto-merge resolves textual conflicts, not semantic ones — two non-overlapping edits in the same scope can produce shadowing/TDZ bugs | After any rebase touching shared code, run the type-checker (or linter for the language) locally before pushing |
| Suppress with `@ts-ignore` | Considered silencing the TS7022 to ship the rebase | The runtime bug remains: the local `tags` array's `${tags.shortSha}` becomes `undefined` at runtime, producing broken image tag strings like `registry/image:git-undefined` | Don't silence type errors; they map to real runtime breakage. Fix the shadow. |
| Rename the parameter instead of the local | Considered renaming the function parameter from `tags` to e.g. `tagInfo` | Would have required updating every call site of `buildBases`/`buildVessels` plus internal references; the local rename touches only the array declaration and its for-of loop | Default to renaming the *narrower-scope* identifier — fewer call sites to touch, less review surface |

## Verified On

| Project | Context | Details |
|---|---|---|
| HomericIntelligence/AchaeanFleet | PR #661 — rebased onto post-#662 main produced TS7022/TS2448 on `dagger/pipeline.ts:128,130,131,186,188,189`. Fix in commit `9ada664`. CI went green; PR auto-merged. | Two character changes: `const tags = [` -> `const tagList = [` and `for (const tag of tags)` -> `for (const tag of tagList)` in both `buildBases` and `buildVessels`. |

## Why This Is Worth Capturing

Searches for "TS7022 rebase", "rebase produced shadowing", or "block-scoped variable used before declaration after merge" should land here. The same pattern recurs in any language with block-scoping (let/const in JS, var-in-block in C++) when two non-overlapping branch edits independently introduce a parameter and a local with the same name. The general rule — *after any rebase, run the type-checker before assuming semantic correctness* — applies far beyond TypeScript.
