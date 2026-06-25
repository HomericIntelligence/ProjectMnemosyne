---
name: benchmark-artifact-triage-pr-splitting
description: "Triage generated benchmark result artifacts before committing them. Use when: (1) benchmark/report runs leave many untracked files, (2) result PRs must include durable reports and complete records without logs or scratch residue, (3) Pareto/report assets need validation before staging, (4) large result sets need split into reviewable PRs."
category: tooling
date: 2026-06-25
version: "1.0.0"
user-invocable: false
verification: verified-local
tags: [benchmark, artifacts, triage, results, pareto, pr-splitting, git, reproducibility]
---

# Benchmark Artifact Triage and PR Splitting

## Overview

| Field | Value |
|-------|-------|
| **Date** | 2026-06-25 |
| **Objective** | Turn a messy benchmark-result worktree into reviewable PRs that preserve useful data and exclude transient run residue. |
| **Outcome** | Operational. The workflow produced separate result PRs for endpoint reports, model reports, and complete structured benchmark records while leaving logs, placeholders, progress traces, orphan metadata, and partial records untracked. |
| **Verification** | verified-local. Executed locally in a benchmark-results repository; CI and merge completion were not part of the capture. |

## When to Use

- A benchmark or report-generation run leaves many visible untracked files and you need to decide what belongs in result PRs.
- Generated reports reference images, CSV summaries, markdown summaries, raw JSON records, or reproducibility scripts.
- Some backends or scenarios produced zero-row summaries, placeholders, partial results, interrupted rows, or failure-only evidence.
- A large result set needs to be split by model family, backend, endpoint, or dataset so reviewers can inspect it without a huge all-in-one PR.
- You need to preserve durable benchmark information without committing logs, scratch directories, progress files, overlays, or build/runtime residue.

## Verified Workflow

### Quick Reference

```bash
# 1. Sync to current trunk before triage.
git fetch origin
git switch <trunk-branch>
git pull --ff-only origin <trunk-branch>

# 2. Snapshot visible candidates.
git status --short --untracked-files=all
git status --short --untracked-files=all | awk '$1=="??"{print $2}' > /tmp/benchmark-candidates.txt

# 3. Build reviewed file lists by logical PR.
rg -n "PARETO|summary.csv|summary.md|request_rate_pareto|throughput_pareto" <result-root>
find <result-root> -type f > /tmp/<dataset>-all.txt

# 4. Stage only reviewed paths.
git add --pathspec-from-file=/tmp/<dataset>-commit-list.txt

# 5. Verify staged content before every commit.
git diff --cached --stat
git diff --cached --name-only | wc -l
git diff --cached --name-only | rg -n '(^|/)(logs?|runtime|progress\.jsonl|preflight|overlay|.*\.pid|.*\.err|.*\.out)$|failure|metadata\.json' || true
git diff --cached --check
```

### Detailed Steps

1. **Sync trunk before analyzing artifacts.**
   Fetch, switch to the real trunk branch, and fast-forward it before inspecting branches or untracked files. Result triage depends on the current ignore rules and the current report layout.

2. **Inspect branch state separately from artifact state.**
   First decide whether old branches are merged, stale, or still carrying independent work. Do not mix branch cleanup with result artifact commits. If a branch contains a large unrelated archive or old experiment corpus, split that decision from the benchmark result PRs.

3. **Create explicit candidate lists in `/tmp`.**
   Write one file list per intended PR, such as `/tmp/endpoint-reports.txt`, `/tmp/model-baseline.txt`, or `/tmp/inference-json-complete.txt`. Avoid `git add -A` and broad directory adds; generated benchmark directories often contain valuable reports next to useless runtime files.

4. **Classify artifacts by information value.**
   Keep durable information:
   - generated reports such as `PARETO.md`, backend reports, and README files that summarize results;
   - `summary.csv` and `summary.md` files with non-empty result rows;
   - Pareto or report images referenced by committed markdown;
   - reproducibility scripts used to generate the committed results;
   - complete structured benchmark JSON records.

   Exclude transient or low-information artifacts:
   - logs, process IDs, Slurm output, server output, progress traces, preflight scratch, and runtime directories;
   - overlay/build residue and generated config overlays;
   - zero-row backend placeholders for backends that did not run;
   - orphan metadata-only raw files without adjacent rows or result data;
   - empty failure logs;
   - partial or zero-completion JSON benchmark records unless the PR is explicitly a failure-analysis archive.

5. **Validate CSV report artifacts before staging.**
   For each summary, check row count, status values, profile/scenario coverage, and backend/model labels. A useful report PR should say exactly what it includes, such as "69 rows across short, medium, and long" or "TRT rows only, SGLang absent." If rows are marked interrupted but still plotted, put that caveat in the PR body.

6. **Validate report asset references.**
   Search markdown reports for referenced images and confirm each image exists. If a referenced image is untracked, include it with the report. A report without its referenced Pareto images is broken rendered documentation, not a clean text-only result.

7. **Validate structured JSON benchmark records by completion.**
   Parse JSON rather than relying on filenames. Require `completed == prompt_count` or `completed == num_prompts` for result PRs that claim complete records. Leave zero-completion and partial records untracked unless the PR title and body are explicitly about failure evidence.

8. **Stage from the reviewed file lists.**
   Use `git add --pathspec-from-file=/tmp/<list>.txt` so the staged set exactly matches the reviewed set. After staging, compare `git diff --cached --name-only` to the list and investigate any mismatch.

9. **Run a pre-commit staged audit for every PR.**
   Before each commit, run staged stats, staged file count, a transient-pattern scan, `git diff --cached --check`, and data-specific validation. The transient scan is allowed to have false positives, but every match should be intentionally explained or removed from staging.

10. **Split PRs by dataset and review size.**
    Prefer one PR per endpoint/model family/report surface. For large structured JSON sets, split by model family or experiment group so each PR remains reviewable. State exact included counts and excluded categories in every PR body.

11. **Return to trunk and inspect leftovers.**
    After opening PRs, switch back to trunk and run `git status --short --untracked-files=all`. The remaining untracked files should all be intentionally excluded categories, not forgotten report assets.

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
|---------|----------------|---------------|----------------|
| Commit every visible untracked file | Treat the post-run worktree as if all generated artifacts were useful benchmark output | This would include progress traces, failure logs, zero-row placeholders, orphan metadata, overlays, and partial benchmark records | Build reviewed path lists and classify artifacts before staging. |
| Commit report markdown without referenced images | Stage only text reports and summary tables | Rendered Pareto reports break when referenced images are left untracked | Search report references and include missing images as durable report assets. |
| Treat metadata-only raw files as results | Keep lone `metadata.json` files without adjacent rows or summaries | Metadata alone usually cannot reproduce a metric and creates review noise | Only commit metadata when it is part of a coherent raw-result bundle or deliberate failure archive. |
| Include empty backend placeholders | Commit empty summaries for backends that did not run | Empty files imply coverage that does not exist and inflate reviews | Exclude zero-row placeholders unless documenting absence is the explicit objective. |
| Accept every JSON record in a result directory | Stage partial or zero-completion JSON next to complete records | Partial records contaminate result datasets and make counts misleading | Parse JSON and require complete prompt accounting before staging result records. |

## Results & Parameters

### Information-value Matrix

| Artifact Class | Default Action | Validation |
|----------------|----------------|------------|
| `PARETO.md`, backend reports, result README files | Keep | Check that referenced assets exist and caveats are documented. |
| `summary.csv`, `summary.md` | Keep if non-empty | Count rows and inspect status, profile, backend, model, and scenario fields. |
| Pareto/report images | Keep if referenced | Confirm every referenced image path exists and is staged. |
| Reproducibility scripts | Keep when tied to committed results | Confirm script names and paths are described in the PR body. |
| Complete structured JSON benchmark records | Keep | Require `completed == prompt_count` or `completed == num_prompts`. |
| Logs, Slurm output, PIDs, server output, progress traces | Exclude | Usually transient runtime evidence. |
| Preflight scratch, overlays, runtime directories | Exclude | Usually build or environment residue. |
| Zero-row backend summaries | Exclude | Unless the PR explicitly documents missing coverage. |
| Orphan metadata-only raw files | Exclude | Unless bundled with rows/results or archived as failure evidence. |
| Empty failure logs and partial JSON records | Exclude | Commit only in explicit failure-analysis PRs. |

### CSV Validation Examples

```bash
# Row count and status/profile counters.
python3 - <<'PY'
import csv
from collections import Counter
from pathlib import Path

for path in map(Path, ["<result-root>/vllm/data/summary.csv"]):
    with path.open(newline="") as handle:
        rows = list(csv.DictReader(handle))
    print(path, "rows", len(rows))
    for key in ("status", "profile", "scenario", "backend", "model"):
        if rows and key in rows[0]:
            print(key, Counter(row.get(key, "") for row in rows))
PY
```

### JSON Completion Validation Example

```bash
python3 - <<'PY'
import json
from pathlib import Path

bad = []
complete = 0
for path in Path("<json-result-root>").rglob("*.json"):
    data = json.loads(path.read_text())
    completed = data.get("completed")
    expected = data.get("prompt_count", data.get("num_prompts"))
    if expected is None:
        bad.append((path, "missing expected prompt count"))
    elif completed == expected:
        complete += 1
    else:
        bad.append((path, f"completed={completed} expected={expected}"))

print("complete", complete)
if bad:
    print("excluded", len(bad))
    for path, reason in bad[:20]:
        print(path, reason)
PY
```

### PR Body Checklist

- Exact row or JSON-record counts included.
- Which models, endpoints, backends, profiles, and scenarios are covered.
- Which artifact classes were intentionally excluded.
- Validation commands run before commit.
- Caveats such as interrupted rows, partial backend coverage, or local-only verification.
- Whether the PR is a result PR or a failure-analysis archive.

## Verified On

| Project | Context | Details |
|---------|---------|---------|
| PerfHC | After benchmark artifact ignore-rule PR #31 merged, remaining result artifacts were triaged into five follow-up PRs | Produced PRs #32 through #36 locally: endpoint reports/assets, Qwen 9B baseline, Qwen 27B baseline with interrupted-row caveat, K2-family complete InferenceX JSON records, and Gemma/Qwen complete InferenceX JSON records. |
