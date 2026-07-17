---
name: github-label-mass-mislabel-forensics
description: "Triage an org-wide GitHub label mass-mislabel (e.g. dozens of issues suddenly carrying an automation state label like state:skip) by histogramming label timeline events, separating the DISTINCT tagging mechanisms by timestamp cluster, bulk-removing first (timelines preserve provenance), and using the still-running automation as a live probe of which code path re-tags. Use when: (1) many issues across repos carry a label nobody remembers applying, (2) you must decide whether a bulk label removal destroys evidence (it does not — labeled/unlabeled events persist), (3) a label reappears minutes after removal and you need to identify WHICH code path re-applied it, (4) label writes appear on the WRONG repo's issue numbers, (5) sizing an org-wide sweep (gh repo list --limit, pagination, PRs-are-issues)."
category: debugging
date: 2026-07-17
version: "1.0.0"
user-invocable: false
verification: verified-local
tags:
  - github-labels
  - state-skip
  - mass-mislabel
  - forensics
  - label-timeline
  - bulk-removal
  - automation-loop
  - triage
  - gh-cli
  - org-wide-sweep
---

# GitHub Label Mass-Mislabel Forensics

## Overview

| Field | Value |
|-------|-------|
| **Date** | 2026-07-17 |
| **Objective** | Explain and clean up 142 `state:skip` labels spread over 14 HomericIntelligence repos, then identify every distinct mechanism that applied them |
| **Outcome** | All 142 removed (0 failures); three DISTINCT mechanisms identified from timeline clusters and live re-tagging: (1) merge-attempt budget default 1 → 76 labels in one overnight run, (2) cross-repo ambient-cwd label writes, (3) epic-title heuristic false positive. Each became its own issue + fixed PR (Hephaestus #2249, #2248, #2253) |
| **Verification** | verified-local — the forensic workflow itself; the three fixes it produced are each verified-ci in Hephaestus |

## When to Use

- Dozens/hundreds of issues carry an automation-owned label (`state:skip`, `state:*`) nobody
  remembers applying, possibly across many repos.
- You are asked to bulk-remove labels FIRST and investigate after — and need to know what evidence
  survives removal.
- A removed label reappears minutes later and you must attribute the re-tag to a specific code path.
- Labels appear on issue numbers that correspond to a DIFFERENT repo's issues (the ambient-cwd
  write bug — see [[automation-ambient-cwd-repo-resolution-breaker-cascade]]).

## Verified Workflow

### Quick Reference

```bash
# 1. Org-wide sweep of label carriers. PRs ARE issues on this endpoint — split them.
for repo in $(gh repo list ORG --limit 1000 --no-archived --json name --jq '.[].name'); do
  gh api "repos/ORG/$repo/issues?labels=state%3Askip&state=all&per_page=100" --paginate \
    --jq '.[] | select(.pull_request | not) | .number'
done

# 2. Bulk-remove is SAFE for forensics: labeled/unlabeled timeline events persist.
gh api -X DELETE "repos/ORG/REPO/issues/N/labels/state%3Askip"

# 3. Histogram WHO/WHEN from timelines (the core forensic move):
gh api "repos/ORG/REPO/issues/N/timeline?per_page=100" --paginate \
  --jq '.[] | select(.event=="labeled" and .label.name=="state:skip") | "\(.actor.login) \(.created_at)"'
# Bucket created_at by hour across all carriers; each timestamp CLUSTER is one mechanism/run.
```

### Detailed Steps

1. **Sweep the whole org, not one repo.** `gh repo list --limit 1000` (the default 30 / a low limit
   silently truncates); the `issues?labels=` endpoint returns PRs too — filter `.pull_request | not`
   and record labeled PRs separately.
2. **Remove first if asked; evidence survives.** GitHub label timelines keep `labeled`/`unlabeled`
   events (actor + timestamp) after removal, so bulk cleanup does not destroy provenance. Automation
   running under the operator's token shows the OPERATOR as actor — timestamps (e.g. 02:00 clusters),
   not actors, distinguish automation from humans.
3. **Histogram timestamps and count clusters.** Each tight cluster (minutes-wide, many issues) is one
   run of one mechanism. In the verified case: 53 labels at 02:0x + 23 at 06:00 on one date = one
   overnight run whose merge budget (default 1) skip-parked every issue that failed once.
4. **Use the running automation as a live probe.** After removal, watch what gets re-tagged within
   the next loop iteration. Re-tags on the CORRECT repos' epics are by-design; re-tags on colliding
   issue numbers of the launch-directory repo exposed the ambient-cwd write bug the moment they
   reappeared. Diff "what returned" against "what should return".
5. **Attribute each cluster to a code path before fixing.** Grep the automation for every site that
   applies the label (`add_labels.*STATE_SKIP`); map each cluster to one site (budget exhaustion,
   epic tagging, review exhaustion...). File ONE issue per distinct root-cause signature, not per
   symptom — the 142 labels reduced to three defects.
6. **Beware self-referential false positives.** An issue FILED ABOUT the mislabel can itself be
   swept up by keyword heuristics (the bug report mentioning "epic labels" was skip-parked by the
   epic-title match — see [[automation-loop-exclude-epic-roadmap-issues]]). Title such issues to
   avoid the automation's own trigger tokens, or fix the heuristic first.

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
|---------|----------------|---------------|----------------|
| Investigate before removing | Sample timelines before bulk removal | User needed the labels gone immediately; investigation blocked cleanup | Removal is evidence-safe — timelines persist; act first, attribute after |
| Actor-based attribution | Identify the tagger from `.actor.login` | Automation runs under the operator's token; every event shows the human account | Cluster by TIMESTAMP; 02:00-hour clusters over dozens of issues are automation runs |
| One issue per symptom | Treat 142 labels as the bug count | Three code paths produced all of them | Count distinct root-cause signatures (see the triage insight in [[automation-ambient-cwd-repo-resolution-breaker-cascade]]) |

## Results & Parameters

```text
Sweep:    gh repo list ORG --limit 1000 --no-archived; issues endpoint returns PRs (filter .pull_request)
Removal:  142/142 OK via DELETE .../issues/N/labels/state%3Askip (URL-encode the colon)
Evidence: labeled/unlabeled timeline events survive removal; actor = token owner; cluster by hour
Outcome:  3 distinct mechanisms -> Hephaestus #2246/#2249 (merge budget default 1),
          #2245/#2248 (ambient-cwd cross-repo writes), #2251/#2253 (epic-title false positive)
```

## Verified On

| Project | Context | Details |
|---------|---------|---------|
| HomericIntelligence org (16 repos) | 2026-07-16/17 state:skip mass-mislabel | 142 labels removed, three mechanisms attributed and fixed (verified-ci each) |
