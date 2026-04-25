---
name: already-done-issue-detection
description: "Detect GitHub issues that are already fixed before starting implementation. Use when: (1) starting a batch triage of 10+ open issues, (2) assigned an issue in a repo with active prior automation, (3) audit issues filed weeks/months ago, (4) issue title contains 'missing', 'add', 'fix' for a file or config value."
category: tooling
date: 2026-04-25
version: 1.3.0
user-invocable: false
verification: verified-ci
history: already-done-issue-detection.history
tags: [triage, already-done, issue-classification, batch, audit]
---

# Already-Done Issue Detection

## Overview

| Field | Value |
|-------|-------|
| **Date** | 2026-04-25 |
| **Objective** | Detect GitHub issues that are already fixed before spending time implementing them |
| **Outcome** | Verified: 11/23 open issues (48%) were ALREADY-DONE in ProjectArgus; 6/57 (10.5%) in ProjectTelemachy — closed with evidence, no code written |
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

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
|---------|----------------|---------------|----------------|
| Reading all issue bodies before checking current state | Opened each issue body to understand the fix needed before checking if it was already done | Wasted time reading detailed issue descriptions for changes already in the codebase | Run batch file-existence + grep checks BEFORE reading issue bodies |
| Assuming audit issues are current | Treated all open audit issues as valid action items | Audit tools file issues against a snapshot — the codebase moves on while issues sit open | Audit issues have a half-life of ~2-4 weeks; always verify current state |
| Using `git rev-list --count origin/main..<branch>` to confirm branches were ALREADY-DONE | Branches showed 1-5 "unique" commits by SHA count, so an Explore sub-agent classified them as needing PRs | The branches were created before main moved forward. Their content was cherry-picked onto main with different SHAs (different parent commits). SHA comparison shows divergence even when content is identical. | Use content-level checks (grep/ls on current main files, or `git diff origin/main...<branch>` three-dot diff + manual inspection) rather than SHA counts to confirm ALREADY-DONE status. Even three-dot diffs can mislead — the definitive check is: does the file/feature currently exist on main? |
| Not checking defaultBranchRef before implementing branch-trigger fixes | Saw "Fix CI branch trigger targeting master" and started implementing ci.yml changes | Repo default branch was already `main` and ci.yml already targeted `main` — issue was stale from before the repo was migrated | Always run `gh repo view --json defaultBranchRef --jq .defaultBranchRef.name` BEFORE touching any branch-trigger issue |
| Ignoring .issue_implementer/ cache directory | Did not check for cached issue.json files from prior automation passes | Re-read and re-analyzed issues that had already been processed by a previous myrmidon-swarm pass | Check `ls .issue_implementer/ 2>/dev/null` first — prior passes cache triage decisions in issue.json files |

## Results & Parameters

### ProjectArgus Session (2026-04-23)

| Metric | Value |
|--------|-------|
| Total open issues | 23 |
| ALREADY-DONE | 11 (48%) |
| SIMPLE (implemented) | 3 |
| COMPLEX (deferred) | 9 |
| Time to close ALREADY-DONE issues | ~5 minutes (batch gh issue close) |
| Code written for ALREADY-DONE | 0 lines |

### ProjectTelemachy Session (2026-04-25)

| Metric | Value |
|--------|-------|
| Total open issues | 57 |
| ALREADY-DONE | 6 (10.5%) |
| Lower rate than ProjectArgus | Fewer stale audit issues; more genuine new work |
| Key already-done patterns | Governance commit (closes #32, #39), defaultBranchRef check (closes #27), meta tracker (closes #44), parent-framing tracker (closes #41) |

### Signal-to-Issue mapping (ProjectArgus)

| Issue | Signal checked | File/command |
|-------|---------------|-------------|
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
|-------|---------------|-------------|
| #27 Fix CI targeting master | `gh repo view --json defaultBranchRef` — already `main`; ci.yml already targets `main` | GitHub API + .github/workflows/ci.yml |
| #32 Missing LICENSE | `ls LICENSE` — present from governance commit (e75e3df) | repo root |
| #39 Missing SECURITY.md | `ls SECURITY.md` — present from governance commit (e75e3df) | repo root |
| #41 No tests for X or Y | Issue body references #8, #9, #10 — parent-framing duplicate tracker | issue body |
| #44 [Audit] Overall Grade: D+ | Meta/grade tracker — never directly implementable | issue body |

### Common ALREADY-DONE signals by issue type

| Issue type | Detection command | Time |
|------------|------------------|------|
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
|---------|------|---------|-------------------|
| ProjectArgus | 2026-04-23 | myrmidon-swarm triage of 23 open issues | 11/23 (48%) |
| ProjectTelemachy | 2026-04-25 | myrmidon-swarm triage of 57 open issues | 6/57 (10.5%) |

## Prior Sessions

### ProjectOdyssey Session (2026-03-15)

Issue #3847 asked for `assert_value_at` and `assert_all_values` calls to be added to shape operation tests. When the file was read, all required assertions were already present. PR #3845 (merged 2026-03-10) had already done the work. Resolution: found two `assert_numel` gaps in sibling tests and filled those instead — opened PR #4813.

**Key signal**: `git log main..HEAD` returns empty + `git diff main -- <file>` returns nothing → issue is already done.
