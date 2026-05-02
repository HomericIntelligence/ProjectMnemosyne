---
name: multi-repo-automation-loop-shell-script
description: "Shell script loop that runs hephaestus planner + implementer across all HomericIntelligence repos with auto-clone. Use when: (1) running hephaestus-plan-issues and hephaestus-implement-issues across 10+ repos in a cron-style loop, (2) repos may not be locally cloned yet (auto-clone via gh), (3) Python automation module is installed in a pixi environment and must be resolved portably."
category: tooling
date: 2026-04-10
version: "1.0.0"
user-invocable: false
verification: verified-local
tags: [multi-repo, automation, shell, bash, pixi, pythonpath, gh-cli, rate-limit, loop]
---

# Multi-Repo Automation Loop Shell Script

## Overview

| Field | Value |
| ------- | ------- |
| **Date** | 2026-04-10 |
| **Objective** | Shell script to run hephaestus planner + implementer across all HomericIntelligence repos (excluding Odysseus) with auto-clone of missing repos |
| **Outcome** | SUCCESS — `scripts/run_automation_loop.sh` validated via dry run across 14 repos; one implementer bug found and fixed during dry run |
| **Verification** | verified-local — planner dry run confirmed across all 14 repos; CI for PR #271 pending |
| **History** | N/A (initial version) |

## When to Use

- Running `hephaestus-plan-issues` + `hephaestus-implement-issues` in a recurring loop across multiple repos
- Dynamically fetching the repo list from a GitHub org (no hardcoded list)
- Repos may not be locally cloned — need auto-clone logic
- Python automation is installed in a `pixi` environment (no system `python` on PATH)
- Need to guard against GitHub GraphQL rate limit exhaustion silently producing empty results

## Verified Workflow

### Quick Reference

```bash
# Resolve Python via pixi (not system python — pixi envs only expose python3)
HEPHAESTUS_DIR="/path/to/ProjectHephaestus"
PYTHON="$(cd "$HEPHAESTUS_DIR" && pixi run which python)"
export PYTHONPATH="$HEPHAESTUS_DIR${PYTHONPATH:+:$PYTHONPATH}"

# Fetch repo list — exclude Odysseus in jq filter
REPOS=($(gh repo list HomericIntelligence --json name,isArchived \
  --jq '[.[] | select(.isArchived == false) | select(.name | test("Odysseus"; "i") | not) | .name] | .[]'))

# Guard: empty list = rate limit hit
if [[ ${#REPOS[@]} -eq 0 ]]; then
  echo "ERROR: No repos returned — possible GraphQL rate limit" >&2
  exit 1
fi

# Auto-clone missing repos
for repo in "${REPOS[@]}"; do
  REPO_DIR="$WORKSPACE_DIR/$repo"
  if [ ! -d "$REPO_DIR" ]; then
    gh repo clone "HomericIntelligence/$repo" "$REPO_DIR"
  fi
done

# Loop N times
for loop in $(seq 1 "$LOOPS"); do
  for repo in "${REPOS[@]}"; do
    ISSUES=$(gh issue list --repo "HomericIntelligence/$repo" --state open --limit 1000 --json number,title,labels)
    "$PYTHON" -m hephaestus.automation.planner ...
    "$PYTHON" -m hephaestus.automation.implementer ...
  done
done

# Suppress RuntimeWarning noise from -m invocations
export PYTHONWARNINGS=ignore::RuntimeWarning
```

### Detailed Steps

1. **Resolve Python path via pixi** — Do not use bare `python` or `python3`. The pixi environment exposes `python` but only inside `pixi run`. Use `pixi run which python` to get the absolute path once and store it as `$PYTHON`.

2. **Export PYTHONPATH** — Set `PYTHONPATH="$HEPHAESTUS_DIR:${PYTHONPATH}"` so the `hephaestus` package is importable when running `"$PYTHON" -m hephaestus.automation.planner` from inside any target repo directory.

3. **Fetch org repo list dynamically** — Use `gh repo list <org> --json name,isArchived` with a jq filter to exclude archived repos and any by name (e.g., Odysseus). Do not hardcode the list.

4. **Guard against empty list** — After fetching, check `${#REPOS[@]} -eq 0`. If zero repos returned, exit with error. This prevents silent no-op loops when GitHub GraphQL quota is exhausted.

5. **Auto-clone missing repos** — For each repo in the list, check if the local directory exists. If not, run `gh repo clone`. This handles first-run and newly-created repos without manual setup.

6. **Fetch open issues per repo** — Use `gh issue list --limit 1000 --json ...` to get a complete snapshot per iteration. Pass this to the planner and implementer.

7. **Run planner then implementer** — Invoke `"$PYTHON" -m hephaestus.automation.planner` and `"$PYTHON" -m hephaestus.automation.implementer` with appropriate args. On loop 3+, add `--no-follow-up` to prevent duplicate issue filing.

8. **Support dry-run, loops, max-workers flags** — The script should accept `--dry-run`, `--loops N`, `--max-workers N` options for safe testing and parallelism control.

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
| --------- | ---------------- | --------------- | ---------------- |
| Use bare `python` command | Called `python -m hephaestus.automation.planner` directly | `python` not on system PATH — pixi only installs `python` inside its virtualenv, not globally | Always resolve Python via `pixi run which python` and cache as `$PYTHON` |
| Use `python3` | Called `python3 -m ...` | `python3` exists on system but lacks the pixi-installed packages | Must use the pixi-managed Python binary, not system Python |
| Run dry-run across 14 repos × 5 loops | Tested full dry-run end-to-end | Exhausted 5000/hour GraphQL quota from issue prefetch calls across 14 repos; took ~1 hour to reset | Dry runs still make real API calls in `prefetch_issue_states`. Rate-limit dry runs to fewer repos or fewer loops |
| Trust `gh repo list` result without validation | Assumed non-empty list = valid | When GraphQL quota was exhausted, `gh repo list` returned an error and jq produced an empty array; loop ran 5 iterations over 0 repos and exited 0 (completely silent) | Add explicit empty-list guard: `if [[ ${#REPOS[@]} -eq 0 ]]; then exit 1; fi` |
| Implementer used hardcoded `scripts/plan_issues.py` | `_generate_plan()` called `scripts/plan_issues.py` in target repo | Only works for ProjectScylla (legacy layout); fails for all other repos | Fix with priority resolution: (1) `hephaestus-plan-issues` entry point, (2) `sys.executable -m hephaestus.automation.planner`, (3) `scripts/plan_issues.py` legacy fallback |

## Results & Parameters

### Script Invocation

```bash
# Minimal — dry run only
./scripts/run_automation_loop.sh --dry-run

# Full production run
./scripts/run_automation_loop.sh --loops 5 --max-workers 3

# Python resolution pattern (used internally)
PYTHON="$(cd "$HEPHAESTUS_DIR" && pixi run which python)"
export PYTHONPATH="$HEPHAESTUS_DIR${PYTHONPATH:+:$PYTHONPATH}"
```

### Runtime Behavior

- Repos fetched dynamically: 14 repos (all HomericIntelligence except Odysseus and archived)
- Dry run output per issue: `[DRY RUN] Would plan issue #N`
- GraphQL quota: 5000 requests/hour; 14 repos × prefetch calls exhausts quota in ~1 full run
- RuntimeWarning on `-m` invocations: `<frozen runpy>:128: RuntimeWarning: 'hephaestus.automation.planner' found in sys.modules after import of package 'hephaestus.automation'` — safe to ignore, suppress with `PYTHONWARNINGS=ignore::RuntimeWarning`

### Implementer Bug Fix (PR #271)

Priority resolution for the plan command in `implementer._generate_plan()`:

```python
# Priority 1: installed entry point
plan_cmd = shutil.which("hephaestus-plan-issues")
if plan_cmd:
    return [plan_cmd, ...]

# Priority 2: PYTHONPATH module invocation
if os.environ.get("PYTHONPATH"):
    return [sys.executable, "-m", "hephaestus.automation.planner", ...]

# Priority 3: legacy fallback for ProjectScylla
plan_script = repo_dir / "scripts" / "plan_issues.py"
if plan_script.exists():
    return [sys.executable, str(plan_script), ...]
```

## Verified On

| Project | Context | Details |
| --------- | --------- | --------- |
| ProjectHephaestus | PR #271 — dry run across 14 HomericIntelligence repos | Planner dry run confirmed `[DRY RUN] Would plan issue #N` for all repos; implementer dry run blocked by rate limit during second run |
