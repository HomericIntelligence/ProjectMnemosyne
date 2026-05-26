---
name: tooling-dry-run-smoke-full-profile-dispatcher
description: 'Ship long-running training/inference/experiment scripts behind a single-file
  bash dispatcher exposing three named execution profiles (dry-run, smoke, full).
  Use when: (1) a script has a wall-clock budget ranging from seconds (verify pipeline)
  to hours (real experiment), (2) users need an unambiguous CI-friendly verification
  command separate from the real run, (3) per-user improvised flag bundles are drifting
  apart and need to be co-located.'
category: tooling
date: 2026-05-25
version: 1.0.0
user-invocable: false
---
# Dry-Run / Smoke / Full Profile Dispatcher

## Overview

| Item | Details |
| ------ | --------- |
| Date | 2026-05-25 |
| Objective | Provide a uniform `./train.sh {dry-run\|smoke\|full}` entrypoint for long-running scripts so users (and CI) never accidentally launch the multi-hour run when they meant to verify a code change. |
| Outcome | Operational — implemented as `examples/grok/lenet_emnist/train.sh` in ProjectOdyssey PR #5453. `./train.sh dry-run` exits 0 in ~30s. |

## When to Use

- Any training, inference, sweep, or experiment script whose `full` wall clock is measured in
  hours (or more) and whose `dry-run` could complete in seconds.
- After a user asks "is there a way to just verify this runs end-to-end?" — that's a `dry-run`
  profile request, not a one-off CLI invocation.
- When a project's CI needs to run "the training command" deterministically — CI calls
  `./train.sh dry-run` with a ~30s budget.
- When per-user verification scripts are drifting apart: collapse them into co-located profile
  presets in one bash file.

## Do NOT Use For

- Pure CLI tools whose wall clock is already seconds (just add a `--help` and ship; no
  dispatcher needed).
- Scripts where the only difference between modes is a single flag (e.g. `--verbose`) — a
  flag is fine, dispatcher is overkill.
- Production inference servers — these need full config systems (Hydra, YAML), not a 3-bucket
  bash file.

## The Three Profiles (Contract)

| Profile | Wall clock | Purpose | When run |
| ------- | ---------- | ------- | -------- |
| `dry-run` | Seconds (target ~30s) | Compile + load + 1 batch + write 1 checkpoint + exit 0 | After ANY code change, before commit. CI-friendly. |
| `smoke` | 5–15 min | Reach an early milestone (memorization complete, first eval, first val accuracy bump) | After non-trivial code changes. Verifies training *dynamics* start correctly. |
| `full` | Hours+ | The real experiment | When you actually want a result |

**Naming is load-bearing.** Use exactly `dry-run`, `smoke`, `full` — these are the
ecosystem-standard names. Do not invent synonyms (`quick`, `fast`, `real`, `prod`); users
must be able to switch between projects without re-learning the vocabulary.

## Verified Workflow

1. **Identify the inner command.** Whatever long-running Mojo/Python/binary you'd otherwise
   invoke directly — that becomes the `exec`'d command at the bottom of `train.sh`.
2. **Inventory the flags.** Sort them into two buckets: (a) `COMMON_FLAGS` that never change
   between profiles (lr, weight-decay, paths, batch size); (b) `PROFILE_FLAGS` that DO change
   (subset size, epochs, log-every, checkpoint-every, max-batches).
3. **Pick budgets.** `dry-run` should write at least one checkpoint and run at least one
   batch so all code paths execute. `smoke` should reach the earliest training-dynamics
   milestone (first eval bump). `full` is whatever the experiment actually needs.
4. **Write the dispatcher** using the template below.
5. **Test all four edge cases** from the "Bash Gotchas" section below.
6. **Wire into CI.** Add a `./train.sh dry-run` job with a 2-minute timeout.

## Results & Parameters

| Parameter | Value | Why |
| --------- | ----- | --- |
| Profile names | `dry-run`, `smoke`, `full` | Ecosystem standard; do not invent synonyms. |
| Profile arg position | Positional `$1` | Shorter, naturally forces explicit choice. |
| Usage-error exit code | `2` | Unix convention; distinguishes from runtime failure (`1`). |
| Pass-through args | `"$@"` after `shift` | Lets users override single settings. |
| Inner invocation | `exec` (not subshell) | Signal propagation; no double-process overhead. |
| Working directory | `git rev-parse --show-toplevel` | Robust against `pwd` assumptions. |
| `dry-run` wall clock target | < 60s (CI timeout 2 min) | Enforces "verify pipeline" semantics. |
| `smoke` wall clock target | 5–15 min | Long enough for first eval, short enough for local iteration. |

## Verified Implementation Template

```bash
#!/usr/bin/env bash
# train.sh — <example>/<model> training dispatcher.
set -euo pipefail

if [ $# -lt 1 ]; then
  echo "usage: $0 {dry-run|smoke|full} [extra flags...]" >&2
  exit 2
fi
PROFILE="$1"
shift

REPO_ROOT="$(git rev-parse --show-toplevel)"
cd "$REPO_ROOT"

case "$PROFILE" in
  dry-run)
    PROFILE_FLAGS=(
      --subset-size 64
      --epochs 1
      --max-batches 1
      --log-every 1
      --checkpoint-every 1
    )
    ;;
  smoke)
    PROFILE_FLAGS=(
      --subset-size 1000
      --epochs 300
      --log-every 10
      --checkpoint-every 50
    )
    ;;
  full)
    PROFILE_FLAGS=(
      --subset-size 1000
      --epochs 30000
      --log-every 50
      --checkpoint-every 500
    )
    ;;
  *)
    echo "error: unknown profile '$PROFILE'" >&2
    exit 2
    ;;
esac

COMMON_FLAGS=(
  --lr 1e-3
  --weight-decay 1.0
  --batch-size 64
  --data-dir datasets/<dataset>
  --weights-dir "<example_path>/checkpoints"
)

echo "==> profile: $PROFILE"
exec <runtime> <command> "${COMMON_FLAGS[@]}" "${PROFILE_FLAGS[@]}" "$@"
```

## Subtle Design Choices (each one matters)

- **Profile is positional, not a flag.** `./train.sh dry-run` reads naturally and is shorter
  than `./train.sh --profile=dry-run`. The trade-off (can't be defaulted) is a feature: users
  must consciously pick a budget.
- **Extra args after the profile pass through (`"$@"`).** Lets users override a single
  setting without forking the script: `./train.sh smoke --weight-decay 0.5`.
- **`exec` the underlying command.** No double-process overhead; signals (Ctrl-C, SIGTERM
  from CI timeouts) propagate cleanly.
- **`cd "$(git rev-parse --show-toplevel)"`.** Lets users invoke from any subdirectory.
  Robust against `pwd` assumptions in the inner command (data paths, weights paths).
- **No reliance on `just` / `make` / project task runner.** Pure bash + the language
  runtime. The dispatcher itself is portable across projects and invocable from CI without
  setting up a task-runner toolchain.
- **`COMMON_FLAGS` separated from `PROFILE_FLAGS`.** Common flags (lr, weight-decay, paths)
  do not change between profiles; only the budget knobs do. This is the single most
  important invariant — if you find yourself duplicating `--lr` across all three profiles,
  hoist it into `COMMON_FLAGS`.

## Failed Attempts (Don't Repeat)

| Attempt | Why it failed | Lesson |
| ------- | ------------- | ------ |
| `PROFILE="${1:?usage: $0 {dry-run\|smoke\|full} [extra...]}"` | The literal `}` inside `{a\|b\|c}` closes the parameter expansion early; bash parses the rest as garbage. | Don't use `:?` with usage strings containing `}`. Use an explicit `[ $# -lt 1 ]` check. |
| Profile as `--profile=NAME` flag | Required users to remember the flag name and forced double-parsing. | Positional first; optional flags after. |
| Hard-coding profile flags into the underlying Mojo/Python script | Tightly couples bash dispatcher to script internals; adding a 4th profile requires touching the inner script. | Keep dispatcher as a thin presets layer — inner script stays generic. |
| `just <profile>` recipes instead of `train.sh` | Tied the dispatcher to the project's task runner; harder to invoke from arbitrary contexts (CI matrix, ad-hoc shells). | Bash dispatcher can invoke `just _run` (or any runtime) as the inner command, but should not BE the just recipe. |

## Bash Gotchas to Test Before Shipping

1. **`./train.sh dry-run` with no extra args must exit 0.** Arrays + `set -u` + empty `"$@"`
   misbehaves on some bash versions. Verify explicitly.
2. **`./train.sh` (no profile) must print usage and exit 2** (not 0, not crash). Convention:
   exit 2 = usage error.
3. **`./train.sh bogus` must print "unknown profile" and exit 2** — not silently fall through
   to a default.
4. **`./train.sh dry-run --weight-decay 0.5` must pass `--weight-decay 0.5` through to the
   inner command** — this is the override path, and breaking it defeats the point.

## CI Integration

A `dry-run` profile is the *natural* CI smoke target for any training script:

```yaml
# .github/workflows/training-smoke.yml
- name: Verify training pipeline still runs end-to-end
  run: ./examples/grok/lenet_emnist/train.sh dry-run
  timeout-minutes: 2
```

The 2-minute timeout enforces the "seconds wall clock" contract — if a code change
accidentally turns `dry-run` into a 30-minute job, CI catches it.

## Verification

verified-ci: implemented as `examples/grok/lenet_emnist/train.sh` in ProjectOdyssey PR
\#5453. `./train.sh dry-run` exits 0 in ~30s and produces the expected output (1 EPOCH log
line, 7 checkpoint subdirs). All three profiles parsed correctly. Bash parameter-expansion
bug (the `:?` usage-string trap) was hit and fixed locally before push.

## Related Skills

- `script-dry-run-flag` — for adding `--dry-run` to a Python validation script (different
  problem: non-blocking preview of errors, not budget control for a long-running job).
- `extend-workflow-smoke-tests` — CI smoke tests for GitHub Actions workflows; complementary,
  not overlapping.
- `train-model` — generic training-loop guidance; this dispatcher pattern is a layer
  *around* such a training entrypoint.
