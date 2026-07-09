---
name: llm-corruption-repro-artifact-review
description: "Durable repro artifact layout and manual-review tooling for long-running LLM corruption investigations. Use when: (1) a corruption sweep must be rerunnable outside the chat or agent session, (2) raw tokens/logits should support later prefix and intervention analysis, (3) manual labels must produce seed-level rates without leaking private operational artifacts."
category: debugging
date: 2026-07-09
version: "1.0.0"
user-invocable: false
verification: verified-local
tags: [llm, corruption, reproducibility, artifacts, manual-review, logits, tokens, redaction]
---

# LLM Corruption Repro Artifact Review

## Overview

| Field | Value |
|-------|-------|
| **Date** | 2026-07-09 |
| **Objective** | Make LLM corruption investigations durable, rerunnable, and reviewable by standardizing per-seed run artifacts and manual-review tooling. |
| **Outcome** | Store issue-specific scripts, docs, summaries, and review state under a durable repro directory; keep each run self-contained; report corruption rates by seed totals; keep private artifacts out of git or redacted. |
| **Verification** | verified-local from local Inference360 issue 257 scripts, tests, and PR work. ProjectMnemosyne PR CI is separate and must not be claimed until checks prove it. |

## When to Use

- You are debugging long-running LLM text corruption, output degeneration, cache instability, or token/logit divergence across many seeds.
- A run must be replayable by another host, cluster, or reviewer without relying on chat history, shell history, or an agent's local session state.
- You need raw `tokens.jsonl` or `logits.jsonl` from broad sweeps so the same data can support later first-bad-token, prefix-comparison, or force-token intervention analysis.
- Manual review must label candidate corruption events without losing state, double-counting bursts, or flooding reviewers with per-token dumps by default.
- You are preparing docs, PRs, issue comments, or repro packages that must redact internal paths, endpoints, checkpoints, prompts, tokens, cookies, and user-specific locations.

## Verified Workflow

Verification status: `verified-local`. The workflow was validated through local Inference360 issue 257 repro scripts/tests and PR work. Do not mark this skill `verified-ci` unless the ProjectMnemosyne PR checks are observed green.

### Quick Reference

```text
1. Create a durable issue-specific repro root: repro/<issue-id>/.
2. Put scripts, docs, run directions, summaries, and reviewer tools there.
3. Emit one self-contained run root per backend/model/config/seed.
4. Store repro.sh, output.txt or assistant.txt, tokens.jsonl, logits.jsonl,
   request/config metadata, and summary.json in each run root.
5. Keep large/private artifacts outside git or replace them with placeholders.
6. Review with scripts that auto-discover run roots and persist labels.
7. Report rates as bad seeds / total seeds, not candidate or burst totals.
```

### Detailed Steps

1. **Create the repro root first.** Use `repro/<issue-id>/` as the durable home for issue-specific scripts, run directions, summaries, reviewer tools, and small sanitized fixtures. Keep large raw artifacts in a private artifact root and reference them with placeholders such as `<REDACTED_ARTIFACT_ROOT>`.
2. **Make every run self-contained.** Write each seed to a path like `runs/<backend>/<seed>/` or `runs/<model>/<config>/<seed>/`. Each run root should contain `repro.sh`, `output.txt` or `assistant.txt`, `tokens.jsonl`, `logits.jsonl`, `request.json`, `config.json`, and `summary.json`.
3. **Make `repro.sh` rerunnable.** It should reconstruct one seed independently from explicit metadata, not from chat context, shell state, or untracked environment assumptions. Use placeholders for private endpoints and checkpoints, for example `<REDACTED_ENDPOINT>` and `<REDACTED_CHECKPOINT_PATH>`.
4. **Capture raw tokens and logits during broad sweeps.** Approach-3 sweeps should preserve raw `tokens.jsonl` and `logits.jsonl` even if the first analysis only needs a binary label. The same files enable later approach-1 and approach-2 work: aggregate failing seeds, find first bad token, compare closest good/bad prefixes, and run force-token interventions.
5. **Summarize in machine-readable form.** Each `summary.json` should include issue id, backend or model alias, config name, seed, prompt hash, output hash, label, candidate count, first bad token index when known, artifact schema version, and the redacted run-root shape.
6. **Write processing scripts instead of reading artifacts manually.** Reviewer tools should auto-discover run roots, read summary and JSONL files, and print compact per-model/per-config counts. Per-token dumps should require `--verbose`.
7. **Persist manual labels.** Store review decisions in a state file such as `review_state.json` so a reviewer can resume, audit who labeled which seed, and avoid re-reviewing the same seed after every script invocation.
8. **Advance review after labeling one seed.** The loop should move to the next seed once a seed receives a label, but it must inspect all candidate events in a log when the first candidate is benign.
9. **Review all corruption classes.** Do not hard-code the loop to the first ellipsis-like event. The classifier should allow every candidate class the investigation tracks, including text degeneration, stop/control-token artifacts, repetition bursts, JSON/tool-call corruption, tokenizer artifacts, and backend-specific logit divergence.
10. **Treat benign ellipsis and control-token artifacts separately.** Comma-adjacent ellipsis fragments that function as array separators are usually benign. Stop-token or control-token renderings should be classified as artifacts unless the surrounding plain text actually degenerates.
11. **Report seed-level rates.** Use `bad seeds / total seeds (%)` per model and config. Candidate count and burst count can be supporting diagnostics, but they are not the denominator for corruption rate.
12. **Redact before publishing.** Docs, PRs, issue comments, and committed repro files must not include internal absolute paths, endpoint addresses, checkpoint names, private prompts, token-bearing artifacts, cookies, or user-specific locations. Keep shape with placeholders such as `<REDACTED_ARTIFACT_ROOT>/runs/<model>/<config>/<seed>/`.

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
|---------|----------------|---------------|----------------|
| Candidate-count denominator | Counted corruption candidates or bursts instead of seeds | Burst totals made the rate look like a complete sample, for example reporting `2/2` reviewed bad cases instead of `2/256` seed rate | Always report `bad seeds / total seeds (%)`; keep candidate and burst counts as secondary diagnostics |
| First-candidate-only review | Stopped after the first candidate event in each log | A benign first candidate hid later real corruption events in the same seed output | When the first candidate is benign, continue scanning every candidate event before labeling the seed clean |
| Noisy default token dump | Printed every token/logit line during normal review | Reviewers could not scan model/config rates or labeling progress efficiently | Default to compact summaries; require `--verbose` for per-token dumps |
| Manual artifact reading | Opened run logs by hand and labeled from ad hoc notes | Labels were hard to resume, audit, or reproduce, and later reviewers could not tell what had been reviewed | Build review scripts with auto-discovery, persistent state, and deterministic summaries |
| Dropped raw sweep data | Kept only final text or binary labels from approach-3 sweeps | Later first-bad-token, prefix comparison, and force-token intervention analyses had to rerun expensive seeds | Preserve raw `tokens.jsonl` and `logits.jsonl` for every relevant seed |
| Checked-in raw operations | Committed run artifacts without masking paths, endpoints, checkpoints, prompts, or token-bearing files | Durable repo artifacts can leak operational details even when docs are sanitized | Keep raw artifacts private, commit only sanitized scripts/summaries, and scan files before PRs/issues |
| Ellipsis/control-token false positive | Treated comma-adjacent ellipsis fragments or stop/control-token renderings as text corruption | Parser and formatting artifacts inflated the corruption count | Add benign classifications for separator ellipses and control-token artifacts; require surrounding text degeneration for a bad label |

## Results & Parameters

### Durable Layout

```text
repro/<issue-id>/
  README.md
  run_sweep.py
  review_corruption.py
  summarize_runs.py
  review_state.json
  summaries/
    latest.json
    latest.md
  runs/
    <backend>/<seed>/
      repro.sh
      output.txt
      assistant.txt
      tokens.jsonl
      logits.jsonl
      request.json
      config.json
      summary.json
    <model>/<config>/<seed>/
      repro.sh
      output.txt
      tokens.jsonl
      logits.jsonl
      request.json
      config.json
      summary.json
```

### Per-Run Contract

| Artifact | Purpose |
|----------|---------|
| `repro.sh` | Replays exactly one seed from explicit metadata and redacted placeholders |
| `output.txt` or `assistant.txt` | Human-readable model output for quick review |
| `tokens.jsonl` | Token IDs, text fragments, offsets, stop/control-token indicators, and candidate markers |
| `logits.jsonl` | Raw or summarized logits needed for first-bad-token and prefix-comparison analysis |
| `request.json` | Sanitized request shape, prompt hash, seed, sampling settings, and model/config alias |
| `config.json` | Backend, model alias, artifact schema version, runtime flags, and redacted artifact-root shape |
| `summary.json` | Machine-readable label, counts, hashes, first bad token index, and reviewer metadata |

### Review Script Contract

```text
review_corruption.py --root repro/<issue-id>
review_corruption.py --root repro/<issue-id> --model <model-alias> --config <config-name>
review_corruption.py --root repro/<issue-id> --verbose
summarize_runs.py --root repro/<issue-id> --by model,config
```

Expected summary shape:

```text
model=<model-alias> config=<config-name> bad=2/256 (0.78%) reviewed=256/256
model=<model-alias> config=<other-config> bad=0/256 (0.00%) reviewed=256/256
```

State file shape:

```json
{
  "schema_version": 1,
  "labels": {
    "<model>/<config>/<seed>": {
      "label": "bad",
      "class": "text-degeneration",
      "reviewed_at": "2026-07-09T00:00:00Z",
      "notes": "First non-benign degeneration after a benign separator ellipsis."
    }
  }
}
```

### Redaction Checklist

- Replace private artifact roots with `<REDACTED_ARTIFACT_ROOT>`.
- Replace endpoints with `<REDACTED_ENDPOINT>`.
- Replace checkpoint or tokenizer paths with `<REDACTED_CHECKPOINT_PATH>`.
- Do not publish private prompts, token-bearing artifacts, cookies, bearer tokens, user-specific locations, hostnames, ports, or absolute infrastructure paths.
- Keep examples structural, for example `<REDACTED_ARTIFACT_ROOT>/runs/<model>/<config>/<seed>/`, without exposing real operational values.

## Verified On

| Project | Context | Details |
|---------|---------|---------|
| LLM360/Inference360 | Issue 257 local corruption investigation scripts/tests and PR work | Durable per-run repro layout, raw token/logit capture, review-state tooling, seed-level rate reporting, and redaction rules were validated locally. Verification is `verified-local`, not `verified-ci`, until the ProjectMnemosyne PR checks prove this skill file. |
