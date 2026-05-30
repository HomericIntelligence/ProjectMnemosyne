---
name: tooling-gh-label-list-default-limit-truncation
description: "`gh label list --json name` silently truncates to 30 rows by default. When the labels you're validating sort late alphabetically (e.g. `state:*`, `tier:*` in a repo with a rich audit/severity taxonomy), validation queries report 0 matches even when the labels exist — no error, no warning, no exit-code signal, just truncated JSON. The same default-30 pagination bites `gh issue list`, `gh pr list`, `gh release list`, and other `gh <noun> list` subcommands when used in scripts. Fix: always pass `--limit 200` (or higher) when reading list output in scripts. Use when: (1) `gh label list` returns 0 but labels exist when checked interactively, (2) a labels-provisioning script reports success but validation script says labels missing, (3) any `gh <noun> list --json` scripted usage that filters by name/state, (4) batching org-wide repo audits that read labels/issues/PRs across many repos, (5) `gh CLI default pagination 30` is suspected as a root cause, (6) validation script silently missing labels despite create commands succeeding, (7) scripting `gh issue/pr/label` inventory with `jq` filters, (8) writing a CI step that reads `gh` list output and gates on counts."
category: tooling
date: 2026-05-29
version: "1.0.0"
user-invocable: false
verification: verified-ci
tags:
  - gh-cli
  - gh-label-list
  - gh-issue-list
  - gh-pr-list
  - pagination
  - silent-truncation
  - default-limit
  - validation-script
  - scripting
  - jq
  - org-wide-automation
---

# gh CLI List Subcommands: The Silent 30-Row Truncation Trap

## Overview

| Field | Value |
| ------- | ------- |
| **Date** | 2026-05-29 |
| **Objective** | Stop silent truncation in `gh label list` / `gh issue list` / `gh pr list` / other `gh <noun> list` scripted usage where the default 30-row pagination causes validation queries to return 0 matches even when the items exist. |
| **Outcome** | Prescribes `--limit 200` (or higher) for any scripted `gh` list call; gives a comparison table of recommended limits per subcommand; documents the failed-attempt path of blaming the upstream provisioning script. |
| **Verification** | verified-ci — observed end-to-end live during org-wide label provisioning across HomericIntelligence (15 repos, 2026-05-29). Failure mode AND the fix were both demonstrated in the same session: validation reported `0/3` for every repo, manual `--search` confirmed labels existed, adding `--limit 200` returned correct counts immediately. |

## When to Use

- A labels-provisioning (or issues/PRs/releases) script reports success but a follow-up validation script says items are missing.
- `gh label list --repo X --json name -q '[.[].name] | map(select(...)) | length'` returns 0 but `gh label list --repo X --search foo` interactively shows the label exists.
- You are scripting any `gh <noun> list` call that filters by name/state/label and counts matches with `jq`.
- You are running an org-wide audit that reads labels, issues, PRs, or releases across many repos.
- You suspect a silent default pagination cap is hiding rows you expect to see.
- A validation step in CI is gating on counts of items returned by `gh` list output.
- You are migrating from interactive `gh` use ("I just ran it and saw the label") to scripted use ("the JSON output says zero") and want to understand the gap.

## Verified Workflow

### Quick Reference

```bash
# WRONG — silently truncates at 30 rows (the gh CLI default)
gh label list --repo "$repo" --json name

# RIGHT — explicit cap above any reasonable repo's label count
gh label list --repo "$repo" --limit 200 --json name

# Same trap applies to other gh list subcommands; always pass --limit in scripts
gh issue list   --repo "$repo" --limit 500 --json number,title,state
gh pr list      --repo "$repo" --limit 500 --json number,title,mergeStateStatus
gh release list --repo "$repo" --limit 200 --json tagName,name
gh run list     --repo "$repo" --limit 200 --json databaseId,status,conclusion
```

### Detailed Steps

#### The trap, exactly as it appeared

A script provisioned a 42-label taxonomy across 14 repos in `HomericIntelligence/`. It reported:

```text
Ensured 42 label(s) across 14 repo(s)
```

A follow-up validation script ran, for each repo:

```bash
gh label list --repo "$repo" --json name -q \
  '[.[].name]
   | map(select(. == "state:needs-plan"
              or . == "state:plan-no-go"
              or . == "state:plan-go"))
   | length'
```

Every repo returned `0`. Three `state:*` labels times 14 repos = 42 missing matches reported. Conclusion (wrong): "the provisioning script silently failed."

#### Reproduction and the actual root cause

1. Manual `gh label list --repo <repo> --search state` showed the labels existed.
2. Re-running provisioning produced "labels already present" — confirming creation succeeded the first time.
3. Reading the `gh label list` man page: the `--limit` flag exists and defaults to `30`.
4. Many repos already had ~25+ pre-existing labels (audit:_, severity:_, principle:\* taxonomies). The `state:*` prefix sorts after most of those alphabetically — so the `state:*` rows fell off the default 30-row cap.
5. Adding `--limit 200` to the validation query returned `3/3` for every repo.

#### The fix (one flag)

```bash
# Validation query, fixed
gh label list --repo "$repo" --limit 200 --json name -q \
  '[.[].name]
   | map(select(. == "state:needs-plan"
              or . == "state:plan-no-go"
              or . == "state:plan-go"))
   | length'
```

The provisioning script that *created* the labels did not need a change — `gh label create --force` is per-label and is not paginated. Only the *reader* needed the flag.

#### Why this is so easy to miss

- No error, no warning, no stderr signal, no non-zero exit code — the JSON output looks valid and well-formed.
- Interactive (no `--json`) output shows the truncation cue visually: 30 rows on one terminal screen, with a hint at the bottom or visible page break. Many users notice it interactively and never re-encounter it in scripts.
- `--json` strips that visual cue. The pager logic that would otherwise re-prompt is bypassed.
- The default exists for shell-pipe ergonomics: a one-screen preview is what most interactive users want. It is the wrong default for scripts.
- Same pagination defaults apply to every `gh <noun> list` subcommand. The default is **30** everywhere. The bug surfaces the same way.
- `--search <term>` server-side filtering hides the bug interactively: it returns the matching rows whether or not they would have fallen off page one. So a user who validates "by hand" with `--search` sees the labels exist, then writes a script using `--json` (which does not accept `--search`-style server filtering by name) and the truncation reappears.

#### The defensive pattern

For any `gh <noun> list` call inside a script, validation step, or CI job:

1. Pass `--limit <N>` explicitly. Pick `N` comfortably above any reasonable count you expect.
2. For labels: `--limit 200` (most repos have well under 100; 200 is plenty of headroom).
3. For issues, PRs, runs, releases: `--limit 500` for active repos; `--limit 1000` for very large repos or org-wide aggregation.
4. The cost of a too-high limit is one extra REST page or a slightly slower response. The cost of silent truncation in a validation script is hours of misdirected debugging.
5. If the list might exceed your limit, add a length check: if `jq length` of the response equals the limit exactly, suspect truncation and raise the limit.

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
| --------- | ---------------- | --------------- | ---------------- |
| Blame the provisioning script | Re-ran the labels provisioner with `-v` to find the alleged silent failure; spent time reading creation logs | The provisioner was correct — every `gh label create --force` had returned 0 and the labels existed. The bug was the validation reader, not the writer. | When a writer reports success and a reader reports zero, suspect the reader before re-running the writer. |
| `gh label list --json name \| jq length` to count instead of `select(...)` | Reasoned that counting all labels would expose the truncation | Still capped at 30 silently. `jq length` reports the length of the truncated JSON, not the underlying repo's label count. | `jq` operates on what `gh` returned, not on what `gh` should have returned. No `jq` filter rescues a truncated input. |
| `gh label list --search state` to confirm labels exist | Used server-side search to verify | Worked — confirmed the labels existed — but `--search` semantics (server-side substring/field filter) is different from "show me all of them"; not a drop-in replacement in a script that needs to inspect the full set | `--search` is a one-off interactive validator, not a scripting primitive. Use `--limit <N>` plus `jq` for scripted inventory. |
| Switch to the GraphQL API via `gh api graphql` | Considered rewriting validation to query labels through GraphQL with explicit pagination | More code (cursor-based pagination, query authoring) with no benefit over passing one extra flag to the existing REST-backed `gh label list` | Simplest fix wins. `--limit 200` is one flag; GraphQL refactor is dozens of lines and a new pagination loop. |
| Trust the interactive sanity check | Ran `gh label list --repo <repo>` in the terminal, saw labels, concluded the script must be broken upstream | Interactive view does not match scripted `--json` view when the count crosses 30; interactive often shows 30 with no truncation banner; the `state:*` rows were on "page 2" and never appeared | Interactive and `--json` outputs do not share the same default pagination cue. Trust neither without `--limit` in scripts. |
| Add a retry loop around the validation query | Reasoned that intermittent API issues might be hiding the rows | Truncation is deterministic at exactly 30 rows; retries returned the same wrong answer | Deterministic silent caps cannot be diagnosed by retry. Read the man page first when output is too short. |
| Increase parallelism instead of investigating | Re-ran the org-wide validator across more repos in parallel to gather more evidence | All parallel workers produced the same wrong `0` answer; conclusion "every repo is broken the same way" deepened the misdiagnosis | More data points from the same buggy reader do not isolate the bug. Pick one repo and reproduce manually first. |

## Results & Parameters

### Recommended `--limit` per gh subcommand

| Subcommand | Default | Recommended scripted limit | Reason |
| ------------ | --------- | ---------------------------- | -------- |
| `gh label list` | 30 | `--limit 200` | Most repos have < 100 labels; 200 gives generous headroom |
| `gh issue list` | 30 | `--limit 500` | Active repos accumulate hundreds of issues; 500 covers most |
| `gh pr list` | 30 | `--limit 500` | Same as issues; very active repos may need `--limit 1000` |
| `gh release list` | 30 | `--limit 200` | Releases are rarer than issues; 200 is sufficient |
| `gh run list` | 20 | `--limit 200` | Workflow runs accumulate fast; pair with `--branch` / `--workflow` to scope |
| `gh repo list <org>` | 30 | `--limit 1000` | Large orgs can have hundreds of repos; pair with `--json name,isArchived` for filtering |
| `gh secret list` | 30 | `--limit 200` | Secrets are typically < 50 but `--limit` is cheap insurance |
| `gh workflow list` | 50 | `--limit 200` | Workflows per repo are usually < 50; flag still cheap |

### Concrete observation (HomericIntelligence org-wide label provisioning, 2026-05-29)

- Org: `HomericIntelligence`
- Repos provisioned: 14 (plus 1 already-correct)
- Labels per repo (post-provision): ~42 (the new taxonomy added to whatever pre-existed)
- Pre-existing label count (e.g. audit:_, severity:_, principle:\*): ~25+ in most repos, sorting alphabetically before `state:*`
- Validation query: `gh label list --repo "$repo" --json name -q '...select(state:* names)... | length'`
- Result without `--limit`: `0` for every repo (silent truncation at 30; the `state:*` rows fell off page one)
- Result with `--limit 200`: `3` for every repo (correct)
- Time wasted before reading the man page: substantial; mistakenly re-ran the provisioning script before noticing the reader was at fault

### Sanity-check pattern for any scripted gh list

```bash
# If you have to script a gh list, always do BOTH:
#   1. pass --limit explicitly
#   2. assert the count is NOT exactly the limit (which would imply more rows exist)
limit=200
rows=$(gh label list --repo "$repo" --limit "$limit" --json name | jq length)
if [ "$rows" -eq "$limit" ]; then
  echo "WARN: count equals --limit ($limit); raise --limit and re-check" >&2
fi
```

### Related skills

- `audit-driven-remediation-workflow.md` — references `gh label list --limit 100` for label validation; this skill explains *why* the explicit `--limit` is mandatory
- `ci-grep-deprecation-guard.md` — references `gh label list` for checking known labels before `gh pr create --label`
- `batch-pr-rebase-workflow.md` — uses `gh pr list --limit 200` in scripted form; same default-30 trap would otherwise apply
