---
name: already-done-issue-detection
description: "Detect GitHub issues that are already fixed (or partially fixed) before starting implementation. Use when: (1) starting a batch triage of 10+ open issues, (2) assigned an issue in a repo with active prior automation, (3) audit issues filed weeks/months ago, (4) issue title contains 'missing', 'add', 'fix' for a file or config value, (5) BEFORE dispatching multi-agent implementation on any open issue — check if recent merged PRs have invalidated the plan (stale-plan / scope-drift detection)."
category: tooling
date: 2026-05-12
version: 2.1.0
user-invocable: false
verification: verified-ci
history: already-done-issue-detection.history
tags: [triage, already-done, issue-classification, batch, audit, stale-plan, preflight, scope-drift, multi-agent-dispatch, 2-pass-classification, classifier-under-detection]
---

# Already-Done Issue Detection

## Overview

| Field | Value |
| ------- | ------- |
| **Date** | 2026-05-07 |
| **Objective** | Detect GitHub issues that are already fixed (fully or partially) before spending time implementing them — covers two related patterns: (A) full ALREADY-DONE issues in batch triage, and (B) stale-plan scope-drift where a multi-agent dispatch is about to re-implement work that merged during planning |
| **Outcome** | Verified: 11/23 open issues (48%) were ALREADY-DONE in ProjectArgus; 6/57 (10.5%) in ProjectTelemachy. ProjectScylla (issue #1887): preflight caught 4 merged PRs (#1921, #1922, #1928, #1931) that obsoleted ~70% of an approved plan — corrected scope shipped as PRs #1932 and #1933 (both merged green). |
| **Verification** | verified-ci |
| **History** | [changelog](./already-done-issue-detection.history) |

## When to Use

- Starting a batch triage of 10+ open issues on any HomericIntelligence repo
- Assigned an issue about a "missing" file (LICENSE, SECURITY.md, CONTRIBUTING.md, pixi.lock, .dockerignore)
- Issue was filed by an automated audit (repo-analyze, repo-analyze-strict) — these go stale within weeks
- Issue title contains: "missing", "add", "fix", "pin", "rename", "update", "change X to Y"
- A prior automation pass (`auto-impl` branches, batch PRs) may have already addressed the issue
- Issue title is a "parent framing" of other open issues (e.g., "No tests for X or Y") — likely a duplicate tracker covering multiple sub-issues; close as meta
- Issue title references a branch trigger (e.g., "Fix CI targeting master") — always verify actual default branch before implementing
- Issue is a meta/grade tracker (`[Audit] Overall Grade: D+`) — never directly implementable, always close as meta
- **About to dispatch multi-agent implementation** on any open issue — even if the plan was approved 30 seconds ago, run a stale-plan preflight first (see "Stale-Plan Scope Drift" section below). Commits land during planning.
- **Plan agents reference files that may have just been created** (e.g., `src/<pkg>/observability/tracing.py`, `JsonFormatter`, scaffolds) — verify those files don't already exist on `origin/main` before re-creating them.
- **Issue title is older than the most recent comment thread** — the title is a snapshot from the day filed; the most recent maintainer comment is the current scope of remaining work.

## Verified Workflow

### Quick Reference

```bash
# 1. Governance files (covers ~5 common audit issues at once)
ls LICENSE SECURITY.md CONTRIBUTING.md CHANGELOG.md CODE_OF_CONDUCT.md 2>&1

# 2. Lockfile / dependency issues
ls pixi.lock poetry.lock package-lock.json Cargo.lock 2>&1

# 3. Docker / config issues
grep "image:" docker-compose.yml | head -20          # check for :latest
grep "allowUiUpdates\|allowUi" configs/grafana/*.yml  # provisioning flags
ls .dockerignore .gitignore 2>&1                       # existence checks

# 4. Code quality issues (mutable defaults, specific patterns)
grep -n "def <function>" <file> | head -5              # check current signature

# 5. Port / URL mismatches
grep -n "<port>" docker-compose.yml configs/prometheus.yml exporter/*.py 2>&1 | head -20

# 6. Default branch check (ALWAYS run before implementing branch-trigger fixes)
gh repo view --json defaultBranchRef --jq .defaultBranchRef.name

# 7. Check for prior automation cache (may have cached issue state from earlier pass)
ls .issue_implementer/ 2>/dev/null | head

# 8. Governance commit scan (one commit can close 4+ audit issues at once)
git log --oneline | grep -i "governance\|LICENSE\|SECURITY\|CONTRIBUTING"

# Close ALREADY-DONE issue with evidence
gh issue close <N> --repo <owner>/<repo> --comment "Already fixed: <file>:<line> shows <evidence>."
```

**WARNING — SHA count is not reliable for ALREADY-DONE detection:**

`git rev-list --count origin/main..<branch>` shows divergent commits even when content is identical, because cherry-pick/rebase creates new SHAs. Do NOT use commit count to determine if a branch is already merged.

Instead, verify content directly:

```bash
# Check if the feature/file exists on current main
ls <expected-file>                                    # file existence
grep -n "<key-pattern>" <file>                        # specific value
git log --oneline origin/main | grep -i "<keyword>"  # keyword in commit messages (approximate only)

# Three-dot diff shows branch-only changes — but inspect carefully:
# An empty three-dot diff = truly no new content
# A non-empty three-dot diff = may still be already-done if the branch predates main
git diff --name-only origin/main...<branch>
# For each changed file: check if main already has the equivalent content
```

### Detailed Steps

1. **Run the batch signal check first** — before reading any issue body in depth, run the Quick Reference commands. Results often resolve 10-50% of audit issues immediately.

2. **Check `.issue_implementer/` cache** — prior automation passes may have stored `issue.json` files with cached issue state. Review these before re-implementing.

3. **For each issue title containing "missing [file]"**: run `ls <file>` — if it exists, the issue is done.

4. **For each issue about a config value** (e.g., "set X to false"): grep the config file for the current value. If it already matches, the issue is done.

5. **For each issue about a code pattern** (e.g., "mutable default argument"): grep the function signature. If it's already fixed, the issue is done.

6. **For branch-trigger issues** (e.g., "CI targets master instead of main"): always run `gh repo view --json defaultBranchRef` first. If the default branch is already `main` and ci.yml already targets `main`, the issue is done.

7. **For parent-framing issues** (e.g., "No tests for X or Y"): check if the issue body references other issue numbers. If it's a tracker for sub-issues, close as duplicate meta-tracker with references.

8. **For meta/grade tracker issues** (`[Audit] Overall Grade: D+`): these are never directly implementable — close as meta with a comment pointing to the individual action items.

9. **Close with specific evidence** — always include the file path and the current value in the closing comment so the reporter understands what was fixed and when.

10. **For partial fixes** (e.g., CONTRIBUTING.md exists but CHANGELOG.md does not): leave the issue open with a comment explaining which part is done and which remains.

## 2-Pass Classification (added in v2.1.0)

The 2026-05-12 ecosystem-wide easy-sweep (5 repos, 717 issues, 65 wave agents) revealed
that **classifier prompts ALONE are insufficient** for ALREADY-DONE detection. Phase-0
classifier agents reported only 1.2–8% ALREADY_DONE per repo — well below the historical
10–48% baseline. Wave agents that included a per-agent stale-check pre-action
inline-detected an **additional ~15%** (8 of 50 wave issues = 16% additional). Skipping
the per-wave stale-check would have produced ~8 unnecessary PRs that revert-on-merge.

### Pattern

```text
PASS 1 (coarse) — Phase-0 classifier agents:
  - Read issue title + body
  - Apply quick heuristics (governance ls, defaultBranchRef, parent-framing)
  - Bucket into EASY / MEDIUM / HARD / META / ALREADY_DONE
  - Expected ALREADY_DONE rate: 1–10% (UNDER-DETECTS by design — fast, coarse)

PASS 2 (deep, per-wave-agent) — embedded in EVERY wave-agent prompt as a pre-action:
  - Run gh issue view {N} --comments | tail -50
  - Run gh pr list --search "{N} in:title OR {N} in:body" --state all --limit 10
  - For each file/feature mentioned in the issue:
      - ls <file> 2>&1
      - grep -n "<pattern>" <file> 2>&1
      - git log --oneline -5 -- <file>
  - If already done: gh issue close {N} --comment "Verified ALREADY-DONE: ..."
                     then STOP and report ALREADY_DONE. Do NOT create a PR.
  - Expected additional ALREADY_DONE rate: 10–20% on top of Pass 1
```

### Why a single pass is not enough

Phase-0 classifiers are optimized for throughput across 100+ issues per repo. They cannot
afford to run `gh pr list --search` + `git log` + content-grep for every issue — that would
take hours. They use coarse heuristics that miss cases where:

- A recent PR (last 1–7 days) implemented the fix but the issue title wasn't updated.
- The fix is in a sibling/related file that doesn't match the issue's title keywords.
- The implementation differs from what the issue title described (different design choice).
- The issue is a META tracker or parent-framing — needs deep read of body for sub-issue refs.

Wave agents have full context (a single issue, no throughput pressure) and can afford the
deeper check. Pass 2 catches what Pass 1 missed.

### Evidence

| Repo (2026-05-12) | Pass-1 ALREADY_DONE % | Pass-2 additional ALREADY_DONE | Total |
| --- | --- | --- | --- |
| ProjectArgus | ~5% (10 DUPLICATE + 1 ALREADY_DONE on ~200 issues) | several wave-agent inline closes | ~15% |
| ProjectAgamemnon | 1.2% (1 of ~80) | wave-agent inline closes including #127 reality-mismatch | additional |
| Myrmidons | low single digits | several wave-agent inline closes | additional |
| ProjectHermes | ~5% (7 CHANGELOG-policy ALREADY_DONE + 1 wrongly-closed META #316) | wave-agent inline closes incl. #577 (pre-existing validator) | additional |
| ProjectCharybdis | 8% | wave-agent inline closes | additional |
| **Aggregate** | **1.2–8%** | **8 of 50 wave issues = 16% additional** | **realistic 10–25%** |

### Embedding Pass 2 into wave-agent prompts

Every wave-agent prompt MUST include this pre-action between the rebase step (always run
`git fetch origin && git rebase origin/main` first) and the implementation step:

```text
STALE-CHECK PRE-ACTION (mandatory):
1. gh issue view {N} --comments | tail -50
2. gh pr list --search "{N} in:title OR {N} in:body" --state all --limit 10
3. For each file/feature referenced in the issue:
   - ls <file> 2>&1
   - grep -n "<key-pattern>" <file> 2>&1
   - git log --oneline -5 -- <file>
4. If the change is already on origin/main: run
     gh issue close {N} --comment "Verified ALREADY-DONE: <evidence>"
   then STOP and report `ALREADY_DONE` as your final output. Do NOT create a PR.
5. If the issue is a META / parent-framing tracker (body references multiple sub-issues),
   report `META` and STOP. Do NOT close, do NOT implement.
6. Only proceed to implementation if both checks above pass.
```

## Stale-Plan Scope Drift (sibling pattern — preflight before multi-agent dispatch)

This section covers a **distinct but related failure mode** from full-issue ALREADY-DONE detection above.

- **ALREADY-DONE issue** (sections above) = the issue should be **closed** — nothing remains.
- **Stale-plan scope drift** (this section) = the issue is **still open and partially valid**, but a recent merged PR has invalidated 50%+ of the planned implementation. The plan must be **re-scoped** before any agent runs.

### Trigger

Run this preflight whenever you are about to launch implementation agents (sub-agents, myrmidon-swarm, parallel Task agents, worktree-based auto-impl) for an open issue. Even if the plan was just approved.

### Quick Reference

```bash
# Run BEFORE launching any implementation agents on an issue:

ISSUE=<number>

# 1. Recent merged PRs that mention this issue (closes/fixes/refs)
gh pr list --search "$ISSUE in:title" --state merged --limit 20
gh pr list --search "$ISSUE in:body"  --state merged --limit 20

# 2. Most recent comment on the issue — often contains "partial progress, leaving open for X/Y/Z"
gh issue view "$ISSUE" --comments | tail -100

# 3. Files that prior PRs created/modified (so plan exploration is current)
for pr in $(gh pr list --search "$ISSUE in:title OR $ISSUE in:body" --state merged --json number --jq '.[].number'); do
  echo "=== PR #$pr ==="
  gh pr view "$pr" --json files --jq '.files[].path'
done

# 4. Git log on relevant paths
git log --oneline -30 -- <key-paths-from-step-3>

# 5. Final freshness check immediately before dispatch — commits land during planning
git fetch origin
git log origin/main..HEAD  # any new commits since plan was assembled?

# 6. THEN if scope has shifted, re-prompt the user with the corrected remaining scope
#    (use AskUserQuestion or equivalent before re-planning)

# 7. Only after this preflight passes, create worktrees + dispatch agents
```

### Detailed Steps

1. **Run gh pr list FIRST, before any other preflight** — this single command catches the majority of scope drift. Search both `in:title` and `in:body` because closing PRs may reference the issue in either place.

2. **Read the most recent issue comments** — maintainers often post "partial progress, leaving open for X, Y, Z" comments that redefine remaining scope. The issue **title** does not get updated; only the comment thread reflects current state.

3. **Cross-check plan-referenced files against current `origin/main`** — for each file the plan says to create, verify it does not already exist:

   ```bash
   # If plan says: "Create src/scylla/observability/tracing.py"
   find src -name 'tracing.py'
   git log --oneline -5 -- 'src/**/tracing.py'
   ```

4. **Re-fetch immediately before dispatch** — the gap between plan approval and agent launch is non-zero. A 10-minute plan can be invalidated by one merge during those 10 minutes.

5. **If scope has drifted, re-prompt the user** with the corrected remaining scope rather than executing the stale plan. Use `AskUserQuestion` or equivalent. Do not silently rewrite the plan — the user approved the original scope and may want to redirect.

6. **Update the plan in-flight** rather than executing the stale version. Cancel any pre-dispatched worktrees that are based on the stale plan.

### Why this is different from the batch ALREADY-DONE checks above

| Aspect | Full ALREADY-DONE (batch triage) | Stale-Plan Scope Drift (this section) |
|--------|----------------------------------|---------------------------------------|
| **State of issue** | Should be closed | Still open, partially valid |
| **Trigger window** | Triaging old issues (weeks/months) | Just before agent dispatch (minutes) |
| **Detection signal** | `ls`/`grep` for file/value existence | `gh pr list --search "<N> in:title"` for recent merges |
| **Action** | `gh issue close` with evidence | Re-prompt user, re-scope plan, then dispatch |
| **Cost of missing** | Wasted hour reading & implementing | Tens of thousands of tokens + revert-on-merge conflicts |

### ProjectScylla Session (2026-05-06, issue #1887)

**Setup**: User asked to dispatch opus sub-agents to implement the last 2 open issues. Plan agents produced a 9-section design covering JSON logging, OpenTelemetry tracing, and Prometheus metrics emitter.

**Preflight catch**: First `gh pr list --search "1887 in:title" --state all` revealed FOUR merged PRs in the prior 24h:

| PR | What it landed | What the plan said to write |
|----|----------------|-----------------------------|
| #1921 | JSON logging foundation (`JsonFormatter`) | "Write JsonFormatter class" |
| #1922 | MetricEmitter scaffold + Prometheus textfile backend | "Build MetricEmitter with Prometheus backend" |
| #1928 | OpenTelemetry tracing scaffold (`init_tracing` + no-op tracer) | "Create src/scylla/observability/tracing.py with init_tracing" |
| #1931 | Wire MetricEmitter into runtime | "Wire MetricEmitter into experiment runtime" |

**Result**: Plan was ~70% obsolete. The issue's most recent triage comment defined the actual remaining scope: (1) log-record-to-span correlation, (2) deeper span instrumentation, (3) production OTLP collector docs. User confirmed corrected scope via AskUserQuestion. Corrected work shipped as PRs #1932 and #1933 (both merged green).

**Counterfactual cost of skipping preflight**: Two opus sub-agents would have re-implemented `JsonFormatter`, recreated `src/scylla/observability/tracing.py` (when `src/scylla/utils/tracing.py` already existed), added duplicate `[otel]` and `[prometheus]` extras to pyproject.toml, and burned tens of thousands of tokens on changes that would revert-on-merge.

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
| --------- | ---------------- | --------------- | ---------------- |
| Reading all issue bodies before checking current state | Opened each issue body to understand the fix needed before checking if it was already done | Wasted time reading detailed issue descriptions for changes already in the codebase | Run batch file-existence + grep checks BEFORE reading issue bodies |
| Assuming audit issues are current | Treated all open audit issues as valid action items | Audit tools file issues against a snapshot — the codebase moves on while issues sit open | Audit issues have a half-life of ~2-4 weeks; always verify current state |
| Using `git rev-list --count origin/main..<branch>` to confirm branches were ALREADY-DONE | Branches showed 1-5 "unique" commits by SHA count, so an Explore sub-agent classified them as needing PRs | The branches were created before main moved forward. Their content was cherry-picked onto main with different SHAs (different parent commits). SHA comparison shows divergence even when content is identical. | Use content-level checks (grep/ls on current main files, or `git diff origin/main...<branch>` three-dot diff + manual inspection) rather than SHA counts to confirm ALREADY-DONE status. Even three-dot diffs can mislead — the definitive check is: does the file/feature currently exist on main? |
| Not checking defaultBranchRef before implementing branch-trigger fixes | Saw "Fix CI branch trigger targeting master" and started implementing ci.yml changes | Repo default branch was already `main` and ci.yml already targeted `main` — issue was stale from before the repo was migrated | Always run `gh repo view --json defaultBranchRef --jq .defaultBranchRef.name` BEFORE touching any branch-trigger issue |
| Ignoring .issue_implementer/ cache directory | Did not check for cached issue.json files from prior automation passes | Re-read and re-analyzed issues that had already been processed by a previous myrmidon-swarm pass | Check `ls .issue_implementer/ 2>/dev/null` first — prior passes cache triage decisions in issue.json files |
| Trusting the issue title as the work definition | Plan dispatch on issue #1887 used the title `[MINOR] §10-Observability: No structured JSON logging or distributed tracing` as the scope of work | Title hadn't been updated when scaffolds merged in PRs #1921/#1922/#1928/#1931 — title-based scope is a snapshot of the day filed | Always read the most recent comments on the issue (`gh issue view <N> --comments \| tail -100`); titles age poorly and never reflect partial-progress merges |
| Trusting audit findings as the work definition | Sized the plan off F19/F20 from the strict audit doc embedded in a parent issue | Audit findings represent state at audit time; four PRs landed between audit and dispatch | Use audit findings as initial framing only, then verify against current commits with `gh pr list --search "<N> in:title"` and `git log origin/main` |
| Trusting plan-agent file-existence assumptions | Plan agents proposed creating `src/scylla/observability/tracing.py` based on their exploration of the codebase | Exploration was correct AT EXPLORATION TIME; commits landed during the planning window | Between plan approval and agent dispatch, do a final `git fetch && git log origin/main..HEAD` and `find` for each file the plan plans to create |
| Skipping `gh pr list` preflight before launching agents | Relied on the in-plan ALREADY-DONE grep (which runs once agents start) instead of running `gh pr list --search "<N> in:title" --state merged --limit 20` BEFORE any compute is spent | The grep would have caught duplicates but only after worktrees were created and agents began work — wasting tokens on revert-on-merge changes | Make `gh pr list --search "<issue> in:title" --state merged --limit 20` line 1 of every multi-agent dispatch script — runs in seconds, catches scope drift before any agent compute |
| Trusting Phase-0 classifier output to close issues blindly (Hermes #316, 2026-05-12) | Phase-1 manual sweep ran `gh issue close` on the classifier's ALREADY_DONE bucket without reading issue bodies. Hermes #316 was bucketed as ALREADY_DONE but was actually a META tracker epic referencing multiple sub-issues. Issue had to be reopened. | Classifier agents bucket on coarse heuristics (title keywords); they cannot reliably distinguish META trackers from ALREADY_DONE issues when titles look similar. | Never trust classifier ALREADY_DONE output to `gh issue close` blindly. Always run `gh issue view N` and read the body before closing. If body contains issue-number references (`#NNN`) suggesting parent-framing, reclassify as META. |
| Classifier ALREADY_DONE under-detection (2026-05-12 ecosystem-wide easy-sweep, 5 repos / 717 issues) | Treated Phase-0 classifier ALREADY_DONE buckets (1.2–8% per repo) as the complete set; wave agents ran without a per-agent stale-check pre-action. | Phase-0 classifiers are optimized for throughput and use coarse heuristics — they miss ~15% of additional ALREADY_DONE issues that require `gh pr list --search`, `git log`, or content-level grep. Without per-wave stale-check, those 8 issues would have produced revert-on-merge PRs. | Use 2-pass classification (see "2-Pass Classification" section above): Pass 1 = Phase-0 classifier coarse buckets; Pass 2 = mandatory per-wave-agent stale-check pre-action with `gh issue view`, `gh pr list --search`, file-existence + grep. Verified across 5 repos / 50 wave issues — caught 8 additional ALREADY_DONE (16%). |

## Results & Parameters

### ProjectArgus Session (2026-04-23)

| Metric | Value |
| -------- | ------- |
| Total open issues | 23 |
| ALREADY-DONE | 11 (48%) |
| SIMPLE (implemented) | 3 |
| COMPLEX (deferred) | 9 |
| Time to close ALREADY-DONE issues | ~5 minutes (batch gh issue close) |
| Code written for ALREADY-DONE | 0 lines |

### ProjectTelemachy Session (2026-04-25)

| Metric | Value |
| -------- | ------- |
| Total open issues | 57 |
| ALREADY-DONE | 6 (10.5%) |
| Lower rate than ProjectArgus | Fewer stale audit issues; more genuine new work |
| Key already-done patterns | Governance commit (closes #32, #39), defaultBranchRef check (closes #27), meta tracker (closes #44), parent-framing tracker (closes #41) |

### Signal-to-Issue mapping (ProjectArgus)

| Issue | Signal checked | File/command |
| ------- | --------------- | ------------- |
| #5 Grafana port mismatch | `grep "3000:3000" docker-compose.yml` | docker-compose.yml |
| #10 :latest image pins | `grep "image:" docker-compose.yml` — all show pinned versions | docker-compose.yml |
| #12 Mutable default arg | `grep "def gauge" exporter/exporter.py` | exporter/exporter.py |
| #15 Exporter port conflict | `grep "9101" exporter/exporter.py` | exporter/exporter.py + prometheus.yml |
| #18 Incomplete .gitignore | `cat .gitignore` — all missing entries present | .gitignore |
| #23 Missing LICENSE | `ls LICENSE` | repo root |
| #27 Missing SECURITY.md | `ls SECURITY.md` | repo root |
| #31 Missing CONTRIBUTING.md | `ls CONTRIBUTING.md` | repo root (partial — CHANGELOG still missing) |
| #24 No pixi.lock | `ls pixi.lock` | repo root |
| #37 Wrong default branch | `gh repo view --json defaultBranchRef` | GitHub API |
| #41 allowUiUpdates: true | `grep "allowUiUpdates" configs/grafana/dashboards.yml` | configs/grafana/dashboards.yml |

### Signal-to-Issue mapping (ProjectTelemachy)

| Issue | Signal checked | File/command |
| ------- | --------------- | ------------- |
| #27 Fix CI targeting master | `gh repo view --json defaultBranchRef` — already `main`; ci.yml already targets `main` | GitHub API + .github/workflows/ci.yml |
| #32 Missing LICENSE | `ls LICENSE` — present from governance commit (e75e3df) | repo root |
| #39 Missing SECURITY.md | `ls SECURITY.md` — present from governance commit (e75e3df) | repo root |
| #41 No tests for X or Y | Issue body references #8, #9, #10 — parent-framing duplicate tracker | issue body |
| #44 [Audit] Overall Grade: D+ | Meta/grade tracker — never directly implementable | issue body |

### Common ALREADY-DONE signals by issue type

| Issue type | Detection command | Time |
| ------------ | ------------------ | ------ |
| Missing governance file | `ls LICENSE SECURITY.md CONTRIBUTING.md` | 2s |
| No lockfile | `ls pixi.lock` | 1s |
| :latest image tags | `grep "image:" docker-compose.yml` | 2s |
| Wrong default branch | `gh repo view --json defaultBranchRef` | 3s |
| Config flag wrong value | `grep "flagName" configs/file.yml` | 2s |
| Code anti-pattern fixed | `grep -n "def funcName" file.py` | 2s |
| Port mismatch | `grep "PORT" docker-compose.yml justfile README.md` | 3s |
| Governance commit (multi-issue) | `git log --oneline \| grep -i "governance\|docs: add"` | 2s |
| Prior automation cache | `ls .issue_implementer/ 2>/dev/null` | 1s |

## Verified On

| Project | Date | Context | Already-Done Rate |
| --------- | ------ | --------- | ------------------- |
| ProjectArgus | 2026-04-23 | myrmidon-swarm triage of 23 open issues | 11/23 (48%) |
| ProjectTelemachy | 2026-04-25 | myrmidon-swarm triage of 57 open issues | 6/57 (10.5%) |
| ProjectScylla | 2026-05-07 | Stale-plan preflight on issue #1887 caught 4 merged PRs (#1921, #1922, #1928, #1931) before opus sub-agent dispatch | ~70% of plan obsolete; corrected scope shipped as #1932 + #1933 (green) |
| HomericIntelligence/{Argus,Agamemnon,Myrmidons,Hermes,Charybdis} | 2026-05-12 → 2026-05-13 | 2-pass classification verified across ecosystem-wide easy-sweep: 5 parallel classifiers (Phase 0) reported 1.2–8% ALREADY_DONE; per-wave stale-check (Pass 2) caught 8 additional of 50 wave issues (16%). Hermes #316 META-mis-classification surfaced "never close-blindly" rule (had to reopen). | Pass-1 ALREADY_DONE: 1.2–8% per repo; Pass-2 additional: 16% (8/50). Realistic combined rate: 10–25%. |

## Prior Sessions

### ProjectOdyssey Session (2026-03-15)

Issue #3847 asked for `assert_value_at` and `assert_all_values` calls to be added to shape operation tests. When the file was read, all required assertions were already present. PR #3845 (merged 2026-03-10) had already done the work. Resolution: found two `assert_numel` gaps in sibling tests and filled those instead — opened PR #4813.

**Key signal**: `git log main..HEAD` returns empty + `git diff main -- <file>` returns nothing → issue is already done.
