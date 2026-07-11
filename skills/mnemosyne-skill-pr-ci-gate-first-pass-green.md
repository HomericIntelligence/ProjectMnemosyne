---
name: mnemosyne-skill-pr-ci-gate-first-pass-green
description: "Use when authoring a Mnemosyne /learn skill PR and you want it to pass CI on the FIRST push instead of bouncing on a red gate: (1) before committing a new or amended skills/*.md so you run the SAME two checks the Mnemosyne branch-protection requires — validate (ruff + scripts/validate_plugins.py over the WHOLE skills/ dir + mypy + pytest) and markdownlint (markdownlint-cli2 with .markdownlint.yaml); (2) when a markdown table in your skill has an inline pipe (regex, shell pipe, a|b) that markdownlint MD056/table-column-count rejects but validate_plugins.py silently passes; (3) when /learn emits a skill missing one of the five required ## sections and validate fails on your own new file; (4) when parallel /learn runs fork fresh origin/main against the SAME skill and become mutually DIRTY, so you need the open-PR amend-lock; (5) when a pre-existing broken file already on main reddens validate for files you never touched; (6) before claiming verified-ci, to confirm the gate is actually green and not just your local run."
category: tooling
date: 2026-06-13
version: "1.0.0"
user-invocable: false
verification: verified-local
tags:
  - ci-cd
  - markdownlint
  - skills
  - mnemosyne
---

# Mnemosyne: Author a /learn Skill PR That Passes CI on the First Pass

## Overview

| Field | Value |
| ------- | ------- |
| **Date** | 2026-06-13 |
| **Objective** | Author a Mnemosyne `/learn` skill PR (`skills/*.md` plus optional `.history`) that passes the required CI gate on the FIRST push, instead of discovering a red `markdownlint` or `validate` check after the PR is open |
| **Required gate** | Mnemosyne `main` branch protection requires EXACTLY two contexts: `validate` (ruff + `python3 scripts/validate_plugins.py` over the WHOLE `skills/` dir + mypy + pytest) and `markdownlint` (markdownlint-cli2 with `.markdownlint.yaml`). Branch-protection contexts are literally `["validate","markdownlint"]` |
| **Outcome** | A four-step local validation order (section self-check, markdownlint-cli2, validate\_plugins.py, pre-commit) plus an open-PR amend-lock that prevents the mutually-DIRTY duplicate-PR cluster seen across 117 open Mnemosyne skill PRs |
| **Verification** | verified-local — local markdownlint + `validate_plugins.py` + the section self-check were run and pass on this file. The ProjectHephaestus PR #1323 that carries these same `/learn` + `/advise` fixes is still OPEN/BLOCKED awaiting a GO label, so this is NOT verified-ci yet |
| **Verified On** | ProjectHephaestus PR #1323 (amends `skills/learn/SKILL.md` + `skills/advise/SKILL.md` with all of the lessons below). The dedup query reproduced the duplicate-PR cluster, and the section self-check flagged the exact 4 missing sections in PR #2417's real file |

## When to Use

- You are about to commit a new or amended Mnemosyne `skills/*.md` from a `/learn` run and want it green on the first push.
- A markdown table cell in your skill contains an inline pipe (a regex like `a|b`, a shell pipe, a column of alternatives) and you need to know why `markdownlint` MD056 rejects it even though `validate_plugins.py` passed.
- `/learn` emitted a skill that is missing one of the five required `##` sections and you want to catch it before the `validate` gate does.
- Parallel `/learn` runs each forked a fresh `origin/main` branch against the SAME skill and the resulting PRs are mutually DIRTY — you need the open-PR amend-lock.
- The `validate` gate is red on files you never touched and you need to tell pre-existing main breakage apart from a regression you introduced.
- You are about to label a skill `verified-ci` and want to confirm the gate is actually observed green first.

## Verified Workflow

> **Verification note:** The four-step local order below was run and passes on this skill file (verified-local). The end-to-end CI behavior is carried by ProjectHephaestus PR #1323, which is still OPEN/BLOCKED awaiting a GO label — so treat "passes CI on the first pass" as verified-local, not verified-ci, until that PR's gate is observed green.

### Quick Reference

```text
LOCAL VALIDATION ORDER (run all four from the worktree root BEFORE committing):

  0) SECTION SELF-CHECK — the validate gate fails on your OWN new file if it
     is missing any of the five required ## sections. grep each header first:
       for sec in "## Overview" "## When to Use" "## Verified Workflow" \
                  "## Failed Attempts" "## Results & Parameters"; do
         grep -qF "$sec" skills/<name>.md || echo "MISSING: $sec"
       done
     (validate_plugins.py accepts ONLY "## Verified Workflow"; for an
      unverified skill keep that exact header and add a "> Proposed Workflow"
      warning subtitle under it — do NOT rename the header.)

  1) MARKDOWNLINT — exactly as CI runs it. Fix EVERY MDxxx, not just MD056:
       npx --yes markdownlint-cli2 --config .markdownlint.yaml \
         "skills/<name>.md" "skills/<name>.history"
     MD056/table-column-count is the #1 failure: an unescaped literal pipe in a
     table cell is parsed as a column separator, so the row has more cells than
     the header. Escape inline pipes as backslash-pipe, or balance the row.
     MD012/no-multiple-blanks (two or more consecutive blank lines) also shows
     up on real PRs — markdownlint flags ALL rules, not only MD056.

  2) PLUGIN VALIDATOR — lints the ENTIRE skills/ dir (SKILLS_DIR = "skills"):
       python3 scripts/validate_plugins.py
     It does NOT catch MD056 — that is markdownlint's job (step 1).

  3) PRE-COMMIT — only your file:
       pre-commit run --files skills/<name>.md

AMEND-LOCK (run BEFORE forking origin/main, to avoid the DIRTY duplicate cluster):
   gh pr list --repo HomericIntelligence/Mnemosyne --state open \
     --search "<name> in:title" --json number,headRefName,title
   If an OPEN PR already amends this skill, STACK on its branch (push to it or
   branch FROM its headRefName) — do NOT fork main into a competing branch.

VERIFIED-CI HONESTY:
   Only claim verified-ci AFTER the PR gate is observed green:
     gh pr view <PR> --json mergeStateStatus,statusCheckRollup
   Passing markdownlint + validate_plugins.py LOCALLY is verified-local.
```

1. **Amend-lock first.** Before forking `origin/main`, run the `gh pr list ... --search "<name> in:title"` query and a files-based check. If an open PR already amends the skill, stack on its `headRefName` instead of forking a competing branch. ~35 of 117 open PRs were mutually DIRTY because parallel `/learn` runs each forked fresh main against the same skill.
2. **Section self-check (step 0).** `grep -qF` each of the five required headers; any miss means the `validate` gate will fail on your own new file. Keep the literal header `## Verified Workflow`; for an unverified skill add a `> Proposed Workflow` warning subtitle under it rather than renaming the header.
3. **markdownlint (step 1).** Run `markdownlint-cli2 --config .markdownlint.yaml` over both the `.md` and the `.history`. Fix EVERY rule it reports, with MD056 and MD012 the most common.
4. **validate_plugins.py (step 2).** It lints the whole `skills/` dir. If errors appear only in files you did not touch, that is pre-existing main breakage — surface it as a separate fix PR, do not misattribute it to your change, and do not claim verified-ci off the back of it.
5. **pre-commit (step 3).** `pre-commit run --files skills/<name>.md`.
6. **verified-ci honesty.** Only after the PR's required gate (`validate` + `markdownlint`) is observed green via `gh pr view <PR> --json mergeStateStatus,statusCheckRollup` may you label the skill `verified-ci`. Local green is `verified-local`.

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
| ------- | -------------- | ------------- | -------------- |
| Ran only `validate_plugins.py` before pushing | Treated the plugin validator as the whole CI gate and pushed once it passed | `validate_plugins.py` does NOT parse markdown tables, so MD056/table-column-count reached the `markdownlint` gate and blocked the PR (7 PRs) | The required gate is TWO checks; an inline pipe in a table cell is only caught by `markdownlint-cli2` — run step 1 locally, not just step 2 |
| Forked fresh `origin/main` while other PRs amended the same skill | Each parallel `/learn` run branched from `origin/main` against the SAME skill file | All competing branches modified the same `.md`/`.history`, so they became mutually modify/modify DIRTY (~35 of 117 PRs; e.g. ~9 amending python-module-decomposition, ~14 stale-documentation-audit) | Run the open-PR amend-lock query BEFORE forking; if one exists, STACK on its `headRefName` instead of forking main |
| Generated a skill missing four required sections | Let `/learn` emit a skill and committed without a section self-check | The `validate` gate reported "Missing required section" on the PR's OWN new file (#2417 / #2420) | grep each of the five `##` headers before commit; a missing header is a guaranteed `validate` failure |
| Labeled a skill verified-ci while its own gate was red | Set `verification: verified-ci` based on a passing local run | The PR's `validate`/`markdownlint` gate was still red, so the verification level was untrustworthy | Only claim verified-ci after `gh pr view <PR> --json statusCheckRollup` shows the gate green; local-only is verified-local |
| Blamed validate errors on my own change | Saw red `validate` and assumed my new file broke it | The errors were in files I never touched — a single broken file already on main reddens EVERY PR's whole-dir `validate` | When validate errors point at untouched files, it is pre-existing main breakage; surface a separate fix PR and do not misattribute |

## Results & Parameters

### Quick Reference

- **The gate is exactly two contexts.** Mnemosyne `main` branch protection requires `["validate","markdownlint"]`. `validate` = ruff + `python3 scripts/validate_plugins.py` (whole `skills/` dir) + mypy + pytest. `markdownlint` = `markdownlint-cli2 --config .markdownlint.yaml`. Reproduce BOTH locally or the PR bounces.
- **MD056 is the #1 failure and `validate_plugins.py` cannot catch it.** An unescaped literal pipe inside a table cell (a regex, a shell pipe, an `a|b` alternative) is parsed as a column separator, so the data row has more cells than the header. Escape inline pipes as backslash-pipe, or balance the row. Only `markdownlint` flags this.
- **markdownlint flags ALL rules.** MD012/no-multiple-blanks (two or more consecutive blank lines) was also seen on real PRs. Do not assume MD056 is the only rule that can redden the gate.
- **The required `##` section set is five headers.** `## Overview`, `## When to Use`, `## Verified Workflow`, `## Failed Attempts`, `## Results & Parameters`. `validate_plugins.py` accepts ONLY `## Verified Workflow` — for an unverified/verified-local skill keep that exact header and add a `> Proposed Workflow` warning subtitle under it. A missing header fails `validate` on the PR's own new file.
- **Whole-repo validate.** `validate_plugins.py` sets `SKILLS_DIR = Path("skills")` and lints the ENTIRE dir, so a single broken file already on main reddens every PR's `validate`. Errors in files you did not touch are pre-existing breakage — fix-PR them separately, never claim verified-ci off them.
- **Amend-lock query.** `gh pr list --repo HomericIntelligence/Mnemosyne --state open --search "<name> in:title" --json number,headRefName,title` plus a files-based check. If an open PR already amends the skill, stack on its branch — do not fork main. This is what prevents the ~35-PR DIRTY duplicate cluster.
- **Local validation order (canonical).** (0) section self-check, (1) `markdownlint-cli2 --config .markdownlint.yaml`, (2) `python3 scripts/validate_plugins.py`, (3) `pre-commit run --files <the file>`.
- **verified-ci is observed, not assumed.** Only `gh pr view <PR> --json mergeStateStatus,statusCheckRollup` showing the gate green earns `verified-ci`. A passing local run is `verified-local`.

### Uncertain assumptions / risks (re-check before relying on this)

- **Not yet verified in CI.** Verification level is `verified-local`. The carrier ProjectHephaestus PR #1323 was OPEN/BLOCKED awaiting a GO label at capture time; confirm its `validate`/`markdownlint` gate goes green before upgrading this skill to `verified-ci`.
- **Branch-protection contexts can drift.** `["validate","markdownlint"]` was read at capture time. Re-confirm with `gh api repos/HomericIntelligence/Mnemosyne/rulesets` (or branch-protection) before assuming the gate is still exactly those two checks.
- **markdownlint rule set is config-driven.** `.markdownlint.yaml` disables many rules (MD013, MD022, MD031, MD032, etc.) but NOT MD056 or MD012. If the config changes, re-derive which rules can redden the gate; always run the actual `markdownlint-cli2` rather than reasoning about it.
- **The duplicate-cluster counts (117 PRs, ~35 DIRTY, ~9 / ~14 per skill) were a point-in-time scan.** They illustrate the failure mode, not a stable metric; re-run the amend-lock query for the current open-PR state.

### Related skills

- `ci-markdownlint-all-files-repo-wide-blocks-prs` — the repo-wide markdownlint blast radius (a broken file anywhere reddens unrelated PRs), the analogue of the whole-dir `validate` behavior described here.
- `tooling-stage-only-your-own-files-in-shared-worktree` — staging discipline that keeps a `/learn` commit scoped to your own skill file, complementing the amend-lock.
- `pr-ci-failure-triage-preexisting-vs-introduced` — telling pre-existing main breakage apart from a regression you introduced, the triage step referenced in lesson 5.

## References

- [markdownlint MD056 / table-column-count rule](https://github.com/DavidAnson/markdownlint/blob/main/doc/Rules.md#md056)
- [markdownlint MD012 / no-multiple-blanks rule](https://github.com/DavidAnson/markdownlint/blob/main/doc/Rules.md#md012)
- [markdownlint-cli2 usage and `--config`](https://github.com/DavidAnson/markdownlint-cli2)
- [GitHub: Managing rulesets and required status checks](https://docs.github.com/en/repositories/configuring-branches-and-merges-in-your-repository/managing-rulesets/about-rulesets)
