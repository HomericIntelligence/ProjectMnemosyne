---
name: ci-failure-triage-and-diagnosis
description: "Canonical workflow for triaging CI failures: log analysis, core dump capture, subprocess hang diagnosis, container forensics, libKGEN/JIT crash retrieval, GHA-only vs cross-environment failures, PR-specific vs systemic failure separation. Use when: (1) a CI run failed and you need to identify the root cause, (2) deciding whether a failure is PR-induced or pre-existing, (3) capturing core dumps from container environments, (4) reproducing a GHA-only crash locally, (5) GraphQL/REST rate-limited CI monitoring."
category: ci-cd
date: 2026-06-20
version: "1.1.0"
user-invocable: false
verification: verified-local
history: ci-failure-triage-and-diagnosis.history
tags: [merged, ci-failure, triage, log-analysis, core-dump, forensics, coredump, gdb, podman, mojo, libkgen, github-actions, rate-limit, subprocess, signal, avx-512, cpu-survey, workflow-dispatch]
---

# CI Failure Triage and Diagnosis

## Overview

| Field | Value |
| ------- | ------- |
| **Date** | 2026-05-18 |
| **Objective** | Consolidated canonical skill for triaging any CI failure: from identifying whether a failure is PR-induced or systemic, to capturing core dumps from containerized JIT crashes, diagnosing subprocess hangs, and reproducing GHA-only crashes across CPU fleets. |
| **Outcome** | Operational — merged from 14 narrower skills covering the full CI-triage lifecycle. |

## When to Use

- A CI run failed and you need to identify the root cause before deciding to revert, fix, or rerun
- `mergeStateStatus: BLOCKED` with zero failing checks (required context never posted)
- Multiple unrelated PRs failing on the same job at the same file/line — treat as broken-main, not per-PR
- Core dumps are empty despite a known JIT crash inside a container (mount-namespace or signal-handler pitfall)
- GHA-only crash suspected to be CPU-feature-sensitive (AVX-512, CPUID masking under Hyper-V)
- E2E runner hangs at "Starting N tiers in parallel" and ignores Ctrl+C
- GitHub API 403 rate-limit errors during batch CI diagnostic loops
- Debug CI instrumentation (gdb, coredump capture) is slowing every PR run and you need an opt-in gate
- pixi.lock stale across multiple PR branches
- You are writing an implementation plan / fix for a reported CI failure and have NOT yet fetched the actual failing-step log — STOP and fetch it first (`gh run view --job=<id> --log-failed`) before forming any root-cause hypothesis
- An issue reports a CI failure with a run ID/URL and says "no detailed error output available via API" — the per-step log IS still retrievable; the issue author simply did not fetch it
- Before proposing any CI fix, you have not yet checked whether the reported failure was already resolved by a later commit/PR on main

## Verified Workflow

### Quick Reference

```bash
# ── PHASE 0: BEFORE writing any plan/fix — read the ACTUAL failing log ──
#    (verified-local against ProjectOdyssey run 25217481782, issue #252)
# 0a. List jobs/steps; the failing step shows an X
gh run view <RUN_ID> --repo <org>/<repo>
# 0b. Pull the ACTUAL failing-step log — works even when the issue claims "no output via API"
gh run view --job=<JOB_ID> --repo <org>/<repo> --log-failed \
  | grep -iE "command not found|exit code|error|traceback" | head
# 0c. Note action VERSIONS in the failing log (e.g. setup-pixi@v0.8.1). A stale version
#     proves the workflow changed since the run — the fix may already exist on main.
# 0d. Check whether the fix already landed on main BEFORE proposing anything:
git log -S "<the fix string, e.g. Install just>" --oneline -- .github/workflows/<file>
gh run list --repo <org>/<repo> --workflow=<file> --branch main --limit 3 \
  --json conclusion --jq '.[].conclusion'   # all "success" => already fixed; document, don't re-fix
# exit 127 / "command not found" => the recipe NEVER RAN (missing tool/interpreter on PATH),
# the failure is BEFORE the recipe body — not inside it.

# ── PHASE 1: Is main broken? Check BEFORE rebasing any downstream PR ──
gh run list --branch main --limit 5 --json conclusion,status,name,createdAt
# If "Build and Test" or "Static Analysis" show conclusion=failure → fix main FIRST

# ── PHASE 2: Transient vs reproducible ──
gh run rerun <run_id> --failed --repo HomericIntelligence/<repo>
gh run watch <new_run_id> --repo HomericIntelligence/<repo>
# Passes → transient, no action. Fails again → reproducible, file issue + PR.

# ── PHASE 3: Identify root cause from log ──
gh run view <run_id> --repo <org>/<repo> --log-failed 2>&1 | \
  grep -E "::error|Error:|FAILED|Killed|out of memory|libKGEN" | head -20

# ── PHASE 4: Classify OOM vs JIT crash (modular#6433 vs #6413) ──
JOB_IDS=$(gh pr view <PR> --json statusCheckRollup | python3 -c "
import sys, json
for c in (json.load(sys.stdin).get('statusCheckRollup') or []):
    if c.get('conclusion') == 'FAILURE':
        print(c.get('detailsUrl','?').rsplit('/job/',1)[-1])")
for id in $JOB_IDS; do
  HITS=$(gh run view --job=$id --log 2>&1 \
    | grep -iE "Killed|OOM-killer|out of memory|virtual address|mmap.*failed" \
    | grep -vE "TCMalloc|echo|# " | head -3)
  [ -n "$HITS" ] && echo "OOM (#6433 not fixed)" || \
    gh run view --job=$id --log 2>&1 | grep -E "libKGENCompilerRTShared.so\+0x" | head -1
done

# ── PHASE 5: Same job failing on N unrelated PRs → broken-main lint ──
git log --oneline -5 -- skills/<offending-file>.md   # when file landed on main
gh pr diff <num> -- skills/<offending-file>.md        # empty → PR didn't touch it
# YES → fix at root with one PR against main, rebase downstream after merge

# ── PHASE 6: Required context never posted (BLOCKED, 0 FAILUREs) ──
gh api "repos/<ORG>/<REPO>/branches/main/protection/required_status_checks" \
  --jq '.contexts' > /tmp/required.json
gh pr view <PR> --json statusCheckRollup --jq '[.statusCheckRollup[].name]|unique' \
  > /tmp/present.json
comm -23 <(jq -r '.[]' /tmp/required.json | sort) \
         <(jq -r '.[]' /tmp/present.json  | sort)
# Output = required contexts that never posted = the blockers

# ── PHASE 7: GitHub API rate limit budget ──
gh api rate_limit --jq '.resources.core | "used:\(.used)/\(.limit) resets:\(.reset|todate)"'
RESET=$(gh api rate_limit --jq '.resources.core.reset')
DELAY=$(( RESET - $(date +%s) + 60 ))
echo "Sleep ${DELAY}s until reset"

# ── PHASE 8: Fix stale pixi.lock ──
git checkout <branch>
pixi install   # regenerates pixi.lock
git add pixi.lock && git commit -m "chore: regenerate pixi.lock" && git push
# Re-trigger if SHA mismatch (empty commits don't reliably trigger CI):
gh run list --branch <branch> --json databaseId,conclusion \
  --jq '.[]|select(.conclusion=="failure").databaseId' \
  | xargs -I{} gh run rerun {} --repo <org>/<repo> --failed
```

### Detailed Steps

#### Step 0 — Triage discipline: read the failing log before forming a hypothesis (verified-local)

When planning a fix for a *reported* CI failure (an issue links a run ID/URL), the FIRST action is to fetch the actual failing-step log — never hypothesize a root cause from the recipe's internals.

1. `gh run view <RUN_ID> --repo <org>/<repo>` to find the failing job ID (failing step shows an X).
2. `gh run view --job=<JOB_ID> --repo <org>/<repo> --log-failed` to pull the exact error line. This works even when the issue says "no detailed error output available via API" — that narration is not authoritative; the author simply did not fetch it.
3. Read the error literally:
   - `command not found` / exit code **127** → the recipe/tool **never ran**; the runner lacked the interpreter or tool on PATH (e.g. `just: command not found` because the job had no "Install just" step). This is a whole class of "fails in CI, passes locally" failures that have nothing to do with the recipe body. "Passes locally + recipe exits 0 locally" is a strong signal the failure happened **before** the recipe body executed.
4. Reconcile the failing run's workflow snapshot against current main. The failing log captures the action **versions** in effect at run time (e.g. `setup-pixi@v0.8.1`); if current main pins a newer version (`v0.9.6`), the workflow changed since the run and the fix may already exist.
5. Check whether the failure was already resolved on main BEFORE proposing a fix:
   - `git log -S "<fix string>" --oneline -- .github/workflows/<file>` to find the landing commit/PR.
   - `gh run list --workflow=<file> --branch main --limit 3 --json conclusion --jq '.[].conclusion'` — all `success` ⇒ already fixed.
   - An "investigate" issue can be legitimately resolved by DOCUMENTING that the failure is already fixed plus a minimal residual hardening — not by inventing a large fix.
6. Any tool you cite in a `verification:` block must actually exist in the repo's env. Grep the dependency manifest first (`pixi.toml`, `pyproject.toml`) and mirror how the repo's own jobs invoke it — e.g. do not write `pixi run check-jsonschema` if `check-jsonschema` is installed via pip in the schema-validation job rather than declared in `pixi.toml`.

> Verification note: the triage commands in this step (`gh run view --log-failed`, `git log -S`, `gh run list --branch main`) are **verified-local** — run live against ProjectOdyssey run 25217481782 (issue #252) this session. The downstream Odysseus hardening they informed (sourcing yamllint from pixi) is a **proposal**, not yet applied or CI-verified.

#### Step 1 — Pre-flight: Is main broken?

Before rebasing any downstream PR, verify main is green:

```bash
gh run list --branch main --limit 5 \
  --json conclusion,status,name,createdAt \
  --jq '.[] | "\(.name): \(.conclusion // .status)"'
```

If "Build and Test", "Static Analysis", or "Code Coverage" show `failure`:
1. Create `fix-ci-<symptom>-<date>` branch from `origin/main`
2. Apply minimal fix
3. Open PR with `gh pr merge <N> --auto --squash`
4. After fix merges, rebase all downstream PRs and re-arm auto-merge (force-push clears it)

#### Step 2 — Identical failure across unrelated PRs

When N unrelated PRs all fail on the same job pointing to the same file/line:

1. Same job failing on multiple unrelated PRs?
2. `gh run view --job <id> --log-failed` points to the same file and line on every PR?
3. Is that file on `main` and untouched by each PR's diff?

If all YES → fix at root. Do NOT add per-PR suppression comments — this is technical debt across N branches.

#### Step 3 — Required context never posts (BLOCKED, 0 FAILUREs)

Two mechanisms that block PRs with no failing checks:

| Cause | Tell-tale | Fix |
| ----- | --------- | --- |
| Workflow `paths:` filter excludes PR | `gh run list --branch <branch> --workflow=<file>` shows no runs | Broaden `paths:` filter |
| Whole-job `if:` skip on event type | Job shows `conclusion: skipped` in run view | Aggregator/summary gate |

Key invariant: a whole-job `if:` skip shows as **missing** to branch protection, not success. A step-level skip inside a running job still posts success.

#### Step 4 — Coredump capture in containerized CI

When a JIT crash inside a Podman/Docker container produces an empty `cores/` directory:

**Mount-namespace fix**: `core_pattern` is resolved in the crashing process's mount namespace, NOT the host's. Set it to the container-side path:

```bash
# WRONG — host CWD path, invisible inside container
echo "$(pwd)/crash-bundle/cores/core.%p.%e.%t" | sudo tee /proc/sys/kernel/core_pattern

# CORRECT — container-side bind-mount path
echo "/workspace/crash-bundle/cores/core.%p.%e.%t" | sudo tee /proc/sys/kernel/core_pattern
```

**libKGEN signal-handler defeat**: When `ulimit -c unlimited` + `core_pattern` still produce no cores (libKGEN installs its own in-process SIGABRT/SIGILL handler that beats the kernel), run `mojo` under gdb:

```bash
# scripts/mojo-under-gdb.sh <cores-dir> <mojo args...>
#!/usr/bin/env bash
set -euo pipefail
CORES_DIR="${1:?}"; shift
mkdir -p "$CORES_DIR"
MOJO_BIN="$(pixi run -- bash -c 'command -v mojo')"
EXIT_FILE="$(mktemp)"; trap 'rm -f "$EXIT_FILE"' EXIT
GDB_PY=$(cat <<'PYEOF'
import gdb, os
signaled = False
NAME_TO_NUM = {"SIGHUP":1,"SIGINT":2,"SIGILL":4,"SIGABRT":6,"SIGBUS":7,
               "SIGFPE":8,"SIGKILL":9,"SIGSEGV":11,"SIGTERM":15}
def on_stop(ev):
    global signaled
    if isinstance(ev, gdb.SignalEvent):
        signo = NAME_TO_NUM.get(ev.stop_signal, 6)
        gdb.execute(f"generate-core-file {os.environ['CORES_DIR']}/core.{gdb.selected_inferior().pid}")
        with open(os.environ["EXIT_FILE"], "w") as f: f.write(str(128 + signo))
        signaled = True
def on_exit(ev):
    if not signaled:
        code = ev.exit_code if ev.exit_code is not None else 0
        with open(os.environ["EXIT_FILE"], "w") as f: f.write(str(code))
gdb.events.stop.connect(on_stop)
gdb.events.exited.connect(on_exit)
PYEOF
)
export CORES_DIR EXIT_FILE
set +e
pixi run -- gdb -batch -nx \
  -ex "python\n$GDB_PY" \
  -ex "set pagination off" \
  -ex "handle SIGILL SIGSEGV SIGABRT SIGBUS SIGFPE stop nopass" \
  -ex "run $*" "$MOJO_BIN"
set -e
cat "$EXIT_FILE" 2>/dev/null | { read -r rc; exit "${rc:-1}"; }
```

**Key rules**:
- Always run gdb **through** `pixi run -- gdb` (inherits `MODULAR_HOME` and stdlib paths)
- Use Python `gdb.events.stop` filtered to `SignalEvent`, NOT `hook-stop` (fires on exit-stop in gdb 15.1)
- Write exit code to a file; `--return-child-result` is unreliable in `-batch` mode
- Handle SIGILL in addition to SIGABRT/SIGSEGV — Mojo `os.abort()` lowers to `llvm.trap` → SIGILL

**Symbolication must run inside the container**:

```yaml
- name: Symbolicate cores (disasm + registers around $pc)
  if: inputs.phase == 'collect' && always()
  shell: bash
  run: |
    mkdir -p crash-bundle/symbolicated
    shopt -s nullglob
    CORES=( crash-bundle/cores/core.* crash-bundle/cores/core.gdb.* )
    shopt -u nullglob
    [ ${#CORES[@]} -eq 0 ] && exit 0
    for core in "${CORES[@]}"; do
      base=$(basename "$core")
      c_core="/workspace/crash-bundle/cores/$base"
      out="crash-bundle/symbolicated/${base}.symbolicated.log"
      podman compose exec -T <service> bash <<HEREDOC > "$out" 2>&1 || true
    MOJO_BIN=\$(pixi run which mojo 2>/dev/null | tail -1)
    pixi run gdb -batch -ex "set pagination off" \
      -ex "thread apply 1 bt 25" \
      -ex "info all-registers" \
      -ex "disassemble \\\$pc - 64, \\\$pc + 64" \
      "\$MOJO_BIN" "${c_core}" 2>&1 | head -400
HEREDOC
    done
```

#### Step 5 — GHA-only crash: cross-CPU survey

When a crash reproduces only on GHA runners (suspected CPU-feature mismatch):

```bash
TARGETS="host1 host2 host3 host4 host5"
JUMPHOST=host2
rsync -avz --partial container-image-*/dev.tar "${JUMPHOST}:~/dev.tar"
for host in $TARGETS; do
  [ "$host" = "$JUMPHOST" ] && continue
  ssh "$JUMPHOST" "scp ~/dev.tar ${host}:~/dev.tar" &
done; wait
for host in $TARGETS; do
  ssh "$JUMPHOST" "ssh $host '
    grep -m1 \"model name\" /proc/cpuinfo
    grep -o -E \"avx2|avx512[a-z]*\" /proc/cpuinfo | sort -u | tr \"\n\" \" \"; echo
    podman load -i ~/dev.tar >/dev/null
    for i in \$(seq 1 50); do
      podman run --rm --userns=keep-id -v \"\$(pwd):/workspace:Z\" -w /workspace \
        <image>:dev bash -c \"pixi run mojo run repro/REPRO.mojo >/dev/null 2>&1; echo exit=\$?\"
    done | sort | uniq -c
  '"
done | tee survey-results.log
```

Note: On GHA Azure runners, silicon is AMD EPYC Zen 4 (native AVX-512) but Hyper-V **masks** AVX-512 CPUID bits. LLVM may emit AVX-512 based on CPU-name fingerprinting, not CPUID probing, causing SIGILL on hardware that reports no AVX-512 capability.

#### Step 6 — Gate debug instrumentation behind workflow_dispatch

When always-on debug instrumentation (gdb wrapper, coredump capture) slows every PR run:

```yaml
on:
  workflow_dispatch:
    inputs:
      enable_gdb_cores:
        description: 'Capture gdb core dumps for libKGEN JIT crashes'
        required: false
        default: false
        type: boolean
  pull_request:
    branches: [main]
  push:
    branches: [main]

jobs:
  test:
    env:
      MOJO_TEST_UNDER_GDB: ${{ (github.event_name == 'workflow_dispatch' && inputs.enable_gdb_cores) && '1' || '0' }}
    steps:
      - run: just test-mojo  # reads MOJO_TEST_UNDER_GDB internally
```

```bash
# Manually trigger with gdb capture enabled
gh workflow run comprehensive-tests.yml -f enable_gdb_cores=true --ref <branch>
```

Rules: always `default: false` (opt-in); always combine `github.event_name == 'workflow_dispatch'` with `inputs.X`; place at job-level `env:`, not step-level.

#### Step 7 — Subprocess hang and signal fixes

When a Python test runner hangs at "Starting N tiers in parallel" or ignores Ctrl+C:

```python
# Replace blocking as_completed() + future.result() with poll loop
from concurrent.futures import FIRST_COMPLETED, wait

pending = set(futures.keys())
while pending:
    if is_shutdown_requested():
        for f in pending: f.cancel()
        raise ShutdownInterruptedError("Shutdown during parallel execution")
    done, pending = wait(pending, timeout=2.0, return_when=FIRST_COMPLETED)
    for future in done:
        result = future.result(timeout=0)  # already done, no block

# Replace proc.communicate(timeout=3600) with polling helper
def _communicate_with_shutdown_check(proc, timeout, ctx):
    poll_interval = 2.0
    remaining = float(timeout)
    while True:
        try:
            return proc.communicate(timeout=poll_interval)
        except subprocess.TimeoutExpired:
            remaining -= poll_interval
            if remaining <= 0: raise
            if is_shutdown_requested():
                _kill_process_group(proc)
                raise ShutdownInterruptedError() from None
```

```python
# Prevent terminal corruption from subprocess inheriting stdin
result = subprocess.run(cmd, stdout=log_file, stderr=subprocess.STDOUT,
                        stdin=subprocess.DEVNULL, text=True, check=False)

# Restore terminal on exit
def _restore_terminal():
    if sys.stdin.isatty():
        try: subprocess.run(["stty", "sane"], stdin=sys.stdin, check=False)
        except Exception: pass
```

Key invariants:
- `as_completed()` + `future.result()` blocks indefinitely — always use `wait(timeout=N)`
- `communicate(timeout=N)` does NOT consume partial output on `TimeoutExpired` — safe to loop
- `threading.Event.wait()` without timeout blocks forever — always add a timeout
- SIGTSTP is job-control — don't register it alongside graceful shutdown handlers

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
| --------- | ---------------- | --------------- | ---------------- |
| `core_pattern` set to host runner CWD | `echo "$(pwd)/crash-bundle/cores/core.%p.%e.%t" \| sudo tee /proc/sys/kernel/core_pattern` | Crashing PID runs inside `podman compose exec` where host path doesn't exist; kernel silently writes nothing | `core_pattern` paths resolve in the crashing PID's mount namespace — use the container-side bind-mount path |
| Bare `ulimit -c unlimited` + `core_pattern` for Mojo crashes | Standard recipe applied to Mojo JIT crashes | `libKGENCompilerRTShared.so` installs an in-process SIGABRT/SIGILL handler; user-space handler beats the kernel, calls `_exit()`, kernel never dumps | Run `mojo` under `gdb` (ptrace intercepts signals before delivery to user-space handlers) |
| `gdb $(which mojo)` outside `pixi run` | Bare gdb invocation to avoid pixi overhead | Mojo errors with `unable to locate module 'std'` before it can crash — `MODULAR_HOME` and stdlib paths unset | Always launch gdb through `pixi run -- gdb` so inferior inherits the activated pixi env |
| `hook-stop` + `generate-core-file` in gdb | Standard gdb idiom for "dump on signal stop" | In gdb 15.1, `hook-stop` fires on the synthetic "Inferior exited normally" stop; `generate-core-file` errors `You can't do that without a process to debug` on every clean-exit test | Use Python `gdb.events.stop` filtered to `isinstance(event, gdb.SignalEvent)` — exit-stop is an `ExitedEvent` and is harmlessly ignored |
| `--return-child-result` in gdb batch mode | Documented gdb flag for exit-code propagation | In gdb 15.1 `-batch`, returns `0` even when inferior died on a handled signal | Write exit code to a temp file from Python event handlers; read it after gdb exits |
| Handle only SIGABRT and SIGSEGV in gdb wrapper | Assumed those were the only fatal signals | Mojo `os.abort()` lowers to `llvm.trap` → SIGILL on Linux, not SIGABRT | Always include SIGILL (+ SIGBUS, SIGFPE) in the handled-signal set for any Mojo wrapper |
| Host-side gdb for symbolication | Resolved mojo path via `podman compose exec which mojo`, then ran gdb on host | Container-side path unresolvable on host → "Could not resolve mojo binary — skipping" | Symbolication must run inside the container alongside the binary and the bind-mounted cores |
| `apt-get install gdb` on runner to unblock host-side symbolication | Pre-install gdb on host image | Mojo binary path still container-side; solving tool availability doesn't fix namespace mismatch | The bottleneck is mount-namespace alignment, not gdb availability |
| Treating all JIT failures as `modular#6433` (OOM) | Assumed 7 red jobs on a fix-verification PR meant #6433 unfixed | Failures were `modular#6413` (separate pre-existing bug); reverting would have lost a valid cleanup | Read log signatures literally: OOM keywords = #6433; `libKGENCompilerRTShared.so+0x` = #6413 |
| Using exit code 137 to classify OOM vs JIT crash | Assumed `137` == SIGKILL == OOM-killer | libKGEN crashes also exit 137 via in-process signal handler | Combine exit code with log signature — the log signature beats the exit code |
| Trusting CPUID flags as ground truth for GHA-only crash | Hypothesis: "any non-AVX-512 CPU triggers it" | All 6 surveyed non-AVX-512 Intel CPUs ran clean; GHA Azure runner crashes 80% | Hyper-V on AMD Zen 4 masks AVX-512 CPUID bits while LLVM may still emit AVX-512 based on CPU-name fingerprinting |
| Per-PR `gh pr view` loop for batch investigation | Called `gh pr view <N>` for each of 13 PRs sequentially | 13 API calls instead of 1 | Use `gh pr list --json` to get all PR statuses at once; check rate limit (`gh api rate_limit`) before batch ops |
| Empty commits to re-trigger CI | `git commit --allow-empty -m "ci: re-trigger"` | Workflows with `concurrency: cancel-in-progress: true` deduplicate same SHA | Use `gh run rerun --failed` instead |
| Filing issues without first re-running CI | Filed issues immediately after observing a red run | Some failures were transient (network, timing); issue was unnecessary | Always re-run the failing job first; only file if the new run also fails |
| Admin-merge to bypass missing required context | Skipped required check via admin for one PR | Leaves every future PR that touches the same files permanently BLOCKED | Fix the workflow misconfig in a separate PR; admin-merge is for one-off pre-existing rot, not systemic gaps |
| `as_completed()` + `future.result()` for parallel subprocess wait | Standard concurrent.futures pattern | Blocks indefinitely when no future completes; main thread never checks shutdown flag | Use `wait(timeout=2.0, return_when=FIRST_COMPLETED)` to poll with interruptibility windows |
| Gate debug CI instrumentation at step level with `if:` | Added `if: github.event_name == 'workflow_dispatch' && inputs.X` to each gdb step | Duplicates logic per job; cannot toggle env-var-driven behavior inside a step that always runs | Gate at job-level `env:` — the env var propagates to all steps including container exec |
| Default debug gate to `true` for safety during libKGEN investigation | Kept default `true` so cores still captured during investigation | Every PR pays the gdb cost; defeats the opt-in purpose | Debug gates must be `default: false`; dispatch manually when cores needed |
| Hypothesized root cause from the recipe internals without reading the failing log | Wrote a full plan blaming unpinned yamllint + a silent-no-op `yamllint configs/` | The recipe never ran — real error was `just: command not found` / exit 127, visible only in the per-step log; plan got NOGO grade D | ALWAYS `gh run view --job=<id> --log-failed` BEFORE forming a root-cause hypothesis |
| Trusted the issue's claim that "no detailed error output is available via API" | Skipped log retrieval because the issue said the log was unavailable | `--log-failed` returned the exact error line; the issue author simply hadn't fetched it | Issue narration about missing logs is not authoritative — try `gh run view --log-failed` yourself |
| Proposed a fix without checking if the failure was already resolved on main | Planned recipe changes for an already-green build job | PR #254 had already added the missing `Install just` step; latest main runs were all green | Before any CI fix: `git log -S` for the fix + `gh run list --branch main` to confirm current status |
| Cited a verification tool not in the repo env | `pixi run check-jsonschema` in the verification block | `check-jsonschema` absent from `pixi.toml`; the schema-validation job installs it via pip, so the command would itself fail | Grep the dependency manifest before putting a tool in a verification command; mirror how the repo's own jobs invoke it |

## Results & Parameters

### OOM vs JIT Crash Classification

| Signal | Bug | Action |
| ------ | --- | ------ |
| OOM keywords (`Killed`, `out of memory`, `virtual address`), no libKGEN trace | `modular#6433` not fixed | Revert the workaround removal |
| `libKGENCompilerRTShared.so+0x<offset>` trace, no OOM | `modular#6413` (separate open bug) | Keep the change; file separate upstream bug |
| All jobs green | Both workarounds unnecessary | Ship it |
| Mixed OOM + libKGEN | `modular#6433` only partially fixed | Investigate before reverting |
| Unknown signature | Neither pattern matches | Escalate; do not auto-revert or auto-ship |

### Rate Limit Budget

| Operation | Cost |
| --------- | ---- |
| `gh api rate_limit` | 1 call |
| `gh pr list --json ...` (50 PRs) | 1 call (bulk — always prefer) |
| `gh pr view <N> --json statusCheckRollup` | 1 call |
| `gh run view <RUN_ID> --log-failed` | 2-5 calls |
| `gh api /repos/.../actions/jobs/<ID>/logs` | 1+ calls (expensive; avoid in bulk) |

Stop log fetching when `remaining < 500`; stop all non-essential calls when `remaining < 100`.

### Subprocess Signal Fix Parameters

```yaml
poll_interval: 2.0            # seconds between shutdown checks
wait_return_when: FIRST_COMPLETED
future_result_timeout: 0      # done futures only, never blocks
resume_event_timeout: 2.0     # worker pause poll interval
```

### GHA Coredump Capture — Required Config

```yaml
core_pattern: '/workspace/crash-bundle/cores/core.%p.%e.%t'  # container-side path
suid_dumpable: 2
ulimit_c: unlimited (set inside the same exec that runs the crashing process)
upload-artifact.if-no-files-found: warn  # NOT ignore — missing artifact must be visible
upload-artifact.retention-days: 14
systemd-coredump: stopped      # must stop both systemd-coredump.socket and apport.service
```

Always emit metadata + symbols even when no cores exist (signals that capture ran vs capture broken).

### Most Uncertain Assumptions (reviewer focus for the Odysseus #252 hardening proposal)

These are unverified at plan time — flagged so a reviewer reuses the TRIAGE discipline (verified-local) without inheriting the unverified downstream fix as fact:

- `yamllint >=1.35,<2` resolving on conda-forge `linux-64` is NOT yet run (gated behind `pixi install` with a `yamllint = "*"` fallback; resolution unconfirmed).
- Removing the `pip install yamllint` CI step is safe ONLY if `pixi.lock` is correctly regenerated and committed; if the lock is not updated, `pixi run yamllint` hard-breaks the currently-green build job — a self-inflicted regression risk.
- The local verification of `pixi run yamllint` used an ambient yamllint 1.38.0 from an unrelated active env (Hephaestus), NOT the Odysseus pixi env, so the "verified" tool behavior is partly ambient.

### CPU Survey Table Format

```text
| Host     | CPU                           | Year | AVX2 | AVX-512 | Hypervisor | Result      |
| -------- | ----------------------------- | ---- | ---- | ------- | ---------- | ----------- |
| aeolus   | Intel i7-3820 Sandy Bridge-E  | 2012 | no   | no      | bare       | clean 50/50 |
| titan    | Intel i5-4440 Haswell         | 2013 | yes  | no      | bare       | clean 50/50 |
| GHA Azure| AMD EPYC 9V74 Zen 4           | -    | yes  | masked  | Hyper-V    | crash ~80%  |
```

## Verified On

| Project | Context | Details |
| --------- | --------- | --------- |
| ProjectOdyssey | PRs #5363, #5364, #5378, #5380, #5382, #5399, #5406, #5407, #5411; modular/modular#6413 JIT crash investigation | Coredump capture, symbolication, cross-CPU survey, workflow_dispatch gate, required-context triage; verified-ci on multiple CI runs |
| ProjectScylla | PR #1515 — E2E runner hang and signal handling | 6 signal/hang bugs fixed, 4924 tests pass, 77.74% coverage; verified-ci |
| AchaeanFleet | Batch investigation of 13 open PRs, 2026-04-24 | Rate limit exhaustion observed; bulk endpoint patterns verified |
| HomericIntelligence ecosystem | All 14 repos triaged, 2026-05-01; Mnemosyne 5 unrelated PRs with identical lint failure, 2026-05-18 | Broken-main pattern, transient-vs-reproducible triage, fix-at-root vs per-PR suppression |
| Odysseus | Issue #252 ("validate-configs fails in CI, passes locally"), run 25217481782, 2026-06-20 | Step 0 triage discipline (verified-local): `--log-failed` surfaced `just: command not found`/exit 127; `git log -S "Install just"` + `gh run list --branch main` confirmed PR #254 had already fixed it. Downstream pixi-yamllint hardening is a proposal, not yet CI-verified. |

## References

- [ci-cd-triage-pr-vs-systemic-failures](ci-cd-triage-pr-vs-systemic-failures.md) — PR vs systemic failure separation (keep as example)
- [pr-preexisting-failure-triage](pr-preexisting-failure-triage.md) — pre-existing failure triage (keep as example)
- [extract-gha-container-image-cache-locally](extract-gha-container-image-cache-locally.md) — extract GHA cached container image for local reproduction
- [ci-cd-summary-aggregator-job-skip-required-context](ci-cd-summary-aggregator-job-skip-required-context.md) — aggregator gate for whole-job skip required context
- [mojo-jit-crash-retry](mojo-jit-crash-retry.md) — dynsym/objdump procedure for analysing captured cores
