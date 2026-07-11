---
name: projecthephaestus-queue-pipeline-strict-review-remediation
description: "Review and repair ProjectHephaestus queue-pipeline PRs after strict review. Use when: (1) review-pr-strict reports sandbox coverage gaps, (2) queue-only automation docs drift from code, (3) worker attribution must prove different workers claim different queue entries, (4) logging basicConfig migrations need direct CLI-main delegation tests."
category: architecture
date: 2026-07-09
version: "1.0.0"
user-invocable: false
verification: verified-local
tags:
  - projecthephaestus
  - queue-pipeline
  - strict-pr-review
  - documentation-drift
  - worker-attribution
  - logging
  - testing
---

# ProjectHephaestus Queue Pipeline Strict Review Remediation

## Overview

| Field | Value |
|-------|-------|
| **Date** | 2026-07-09 |
| **Objective** | Preserve the ProjectHephaestus queue-only automation pipeline contract while fixing strict PR review findings for issue #1404 / PR #2029. |
| **Outcome** | Successful locally: queue worker attribution, queue-only docs, and missing logging-delegation tests were repaired and verified in the ProjectHephaestus PR branch. |
| **Verification** | verified-local. ProjectHephaestus local tests, ruff, format, mypy, and targeted pre-commit passed; Mnemosyne CI validation for this skill PR is pending. |

## When to Use

- `/review-pr-strict` initially returns NO-GO because the default sandbox cannot spawn `/bin/bash` or `/bin/sh`, leaving code-quality or security dimensions unreviewed.
- A ProjectHephaestus queue-pipeline PR touches automation-loop docs after the #1818/#1819 cutover.
- Docs or runbooks still mention `hephaestus-automation-loop --pipeline`, say `--pipeline` remains accepted, or describe a `--legacy-loop` rollback selector.
- Wrapper docs still describe `hephaestus-plan-issues`, `hephaestus-implement-issues`, `hephaestus-review-prs`, or `hephaestus-drive-prs-green` as legacy/manual paths even though code now treats them as thin queue-pipeline scoped wrappers.
- A reviewer asks how to prove that queue entries and workers are decoupled, or whether one worker is secretly running all jobs sequentially.
- A logging cleanup replaces `logging.basicConfig(...)` with `configure_cli_logging(...)` in a CLI `main()` function and needs direct behavioral coverage.

## Verified Workflow

Verified locally only - CI validation pending for the skill repository.

### Quick Reference

```bash
# If strict review failed only because shell/file access failed, retry the
# read-only evidence commands with approved escalation instead of grading the PR
# as defective.
gh pr view <pr> --json number,title,body,baseRefName,headRefName,headRefOid,files,commits,closingIssuesReferences,statusCheckRollup
gh pr checks <pr>
gh pr diff <pr> > /tmp/pr-<pr>.diff
git diff --name-status origin/main...HEAD
rg "logging\\.basicConfig\\(" hephaestus -g "*.py"

# Queue-only docs must not preserve compatibility flags that code does not parse.
rg -- "--pipeline|--legacy-loop|hephaestus-automation-loop --pipeline" AGENTS.md README.md docs tests

# ProjectHephaestus local verification used for PR #2029 follow-up fixes.
pixi run pytest tests/unit/docs tests/unit/automation/test_audit_reviewer.py -q --no-cov --tb=short
pixi run pytest tests/unit -q --no-cov --tb=short
pixi run python -m ruff check .
pixi run python -m ruff format --check .
pixi run python -m mypy hephaestus/
```

### Detailed Steps

1. **Separate audit-tool failure from PR defects.** If dimension agents report that they could not spawn `/bin/bash` or `/bin/sh`, treat that as a coverage gap in the audit environment, not as code evidence. Rerun essential read-only commands with approved escalation and require every dimension to re-grade from direct evidence.

2. **Recompute the strict-review verdict after evidence is available.** In PR #2029, the first strict review was NO-GO because Dimension 3 and Dimension 5 could not read the diff. After escalated read-only access, `gh pr view`, `gh pr checks`, `git diff`, `rg`, and targeted file reads succeeded; code quality and security regraded to B- and the overall verdict moved to CONDITIONAL.

3. **Use code as ground truth for queue-pipeline architecture.** For post-cutover ProjectHephaestus, `hephaestus-automation-loop` is queue-only. There is no executable `--pipeline` compatibility flag and no `--legacy-loop` rollback selector. Remove doc/runbook examples that imply either flag works unless the parser actually accepts it.

4. **Document wrapper scripts by their real current behavior.** `hephaestus-plan-issues`, `hephaestus-implement-issues`, `hephaestus-review-prs`, and `hephaestus-drive-prs-green` are thin queue-pipeline scoped wrappers. `hephaestus-merge-prs` remains a manual command outside the queue coordinator. Do not describe the thin wrappers as legacy/manual entry points.

5. **Lock architecture text with docs tests.** Add regression tests that assert architecture docs contain no stale `--pipeline` compatibility claim, no `--legacy-loop` rollback path, no stale `hephaestus-automation-loop --pipeline` command, and wrapper wording that matches thin queue-pipeline scoped entry points. Update crash/CI runbooks to use queue-pipeline wording too.

6. **Prove queue entries are not all run sequentially by one worker.** Use a real `WorkerPool(size=2)`, submit at least two `BuildTestJob`s with distinct `claim_key` and `claim_stage` values, and patch `subprocess.run` behind a `threading.Barrier(2)` so both worker threads must enter concurrently before either returns. Assert two distinct `JobResult.worker_id` values and `worker_claim` log records for both queue item/stage pairs.

7. **Cover changed CLI mains directly.** When a CLI `main()` changes from `logging.basicConfig(...)` to `configure_cli_logging(...)`, add a direct test that patches the module-local `configure_cli_logging`, invokes the main function with a safe mode such as `["--dry-run", "--verbose"]`, and asserts `configure_cli_logging(verbose=True)`.

8. **Keep verification scoped but broad enough.** Run the targeted docs/CLI tests first, then the full unit suite and static checks. Use full PR CI as the current-state hygiene gate, but do not claim Mnemosyne skill CI until that separate PR's CI passes.

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
|---------|----------------|---------------|----------------|
| Treat sandbox access failure as a PR defect | The first strict review graded code quality and security as F because workers could not spawn `/bin/bash` or read the diff. | The failure was lack of audit access, not direct evidence that the PR was unsafe or low quality. | Mark the dimension as a coverage gap, rerun read-only `gh`/`git`/`rg`/file reads with approved escalation, then update the verdict from evidence. |
| Preserve stale `--pipeline` / `--legacy-loop` docs | Architecture docs and runbooks kept commands such as `hephaestus-automation-loop --pipeline ...` and prose saying `--pipeline` remained accepted. | The parser no longer accepted those flags, so docs contradicted code and misled operators. | Code is ground truth; remove stale compatibility claims or restore executable parser support. Add docs regression tests to prevent reintroduction. |
| Describe thin wrappers as legacy/manual paths | `AGENTS.md` and architecture docs treated queue-scoped wrappers as legacy/manual entry points after the cutover. | Current wrapper modules dispatch through the queue pipeline, so the documentation was obsolete. | Update wrapper docs to say thin queue-pipeline scoped wrappers, while keeping `hephaestus-merge-prs` documented as manual/out-of-band. |
| Rely on static no-`basicConfig` guard only | A CLI main moved to `configure_cli_logging(...)`, but no test asserted that the main function called the helper. | The static guard proves `logging.basicConfig(...)` is absent, not that the replacement helper is invoked with the right verbosity. | Add direct main-function delegation coverage by patching module-local `configure_cli_logging` and asserting the call. |
| Infer worker distribution from sequential logs | A queue worker attribution check only inspected completion output after jobs had finished. | Sequential execution by one worker can produce plausible logs; it does not prove concurrent workers claimed distinct entries. | Use a `threading.Barrier(2)` in patched `subprocess.run` with `WorkerPool(size=2)` and assert distinct `worker_id` values plus item/stage-specific `worker_claim` log lines. |

## Results & Parameters

### ProjectHephaestus PR #2029 Verification Observed

```text
pixi run pytest tests/unit/docs tests/unit/automation/test_audit_reviewer.py -q --no-cov --tb=short
71 passed

pixi run pytest tests/unit -q --no-cov --tb=short
5856 passed, 21 skipped

pixi run python -m ruff check .
passed

pixi run python -m ruff format --check .
passed

pixi run python -m mypy hephaestus/
passed
```

Targeted pre-commit passed on the changed docs/tests:

```bash
pixi run pre-commit run --files \
  AGENTS.md \
  README.md \
  docs/AUTOMATION_LOOP_ARCHITECTURE.md \
  docs/runbooks/automation-loop-crash.md \
  docs/runbooks/ci-driver-stall.md \
  tests/unit/automation/test_audit_reviewer.py \
  tests/unit/docs/test_automation_loop_architecture.py \
  tests/unit/docs/test_automation_loop_crash_runbook.py
```

### Queue Worker Attribution Test Pattern

```python
barrier = threading.Barrier(2, timeout=5)


def fake_run(*args, **kwargs):
    barrier.wait()
    return subprocess.CompletedProcess(args[0], 0, stdout="", stderr="")


pool = WorkerPool(size=2)
future_a = pool.submit(
    BuildTestJob(("pytest", "-q")),
    claim_key="test/repo#123",
    claim_stage="ci",
)
future_b = pool.submit(
    BuildTestJob(("pytest", "-q")),
    claim_key="test/repo!456",
    claim_stage="pr_review",
)

result_a = future_a.result(timeout=10)
result_b = future_b.result(timeout=10)

assert result_a.worker_id != result_b.worker_id
assert "item=test/repo#123 stage=ci" in caplog.text
assert "item=test/repo!456 stage=pr_review" in caplog.text
```

### CLI Main Delegation Test Pattern

```python
with patch("hephaestus.automation.audit_reviewer.configure_cli_logging") as configure:
    rc = audit_reviewer.main(["--dry-run", "--verbose"])

assert rc == 0
configure.assert_called_once_with(verbose=True)
```

## Verified On

| Project | Context | Details |
|---------|---------|---------|
| ProjectHephaestus | PR #2029 / issue #1404 strict-review remediation | Local verification passed after docs drift fixes, queue worker attribution tests, and direct `audit_reviewer.main()` logging delegation coverage. |
