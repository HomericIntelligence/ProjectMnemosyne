---
name: gcovr-lcov-excl-region-exclusion
description: "Replace file-level gcovr excludes with fine-grained LCOV_EXCL_START/STOP region markers so complex C++ files stay inside the coverage gate, excluding only regions provably unreachable without a live external dependency. Use when: (1) removing a file-level `--exclude foo.cpp` from a gcovr coverage gate and replacing it with fine-grained LCOV_EXCL_START/STOP markers, (2) deciding which regions to exclude vs leave measured when code requires a live external service (broker/DB) to execute, (3) a reviewer flags measured-but-provably-unreachable lines or 'covered by integration tests' comments that assert nonexistent coverage, (4) coverage numbers must be evidenced reviewer-visibly (PR body / --print-summary)."
category: ci-cd
date: 2026-07-02
version: "1.0.0"
user-invocable: false
verification: verified-local
tags: [gcovr, lcov-excl, coverage-threshold, cpp, ctest, fail-under-line, coverage-exclusion, live-dependency-code, review-driven]
---

# gcovr LCOV_EXCL Region Exclusion for C++ Coverage Gates

## Overview

| Field | Value |
| ------- | ------- |
| **Date** | 2026-07-02 |
| **Objective** | Include the most complex production file (C++ NATS client, a nats.c wrapper) in an 80% gcovr line-coverage gate instead of excluding it wholesale via `--exclude` |
| **Outcome** | Successful — gate passes at 94.1% total lines with the file measured at 88%; Coverage CI workflow green on the PR; the refined marker set verified locally (verified-local) |
| **Verification** | verified-local — the full workflow was executed end-to-end locally; the initial marker set also passed CI on the PR |

## When to Use

- You are removing a file-level `--exclude foo.cpp` from a gcovr coverage gate and replacing it with fine-grained `LCOV_EXCL_START`/`LCOV_EXCL_STOP` markers.
- You must decide which regions to exclude vs leave measured when code requires a live external service (message broker, database) to execute.
- A reviewer flags measured-but-provably-unreachable lines, or flags "covered by integration tests" comments that assert coverage from a suite that does not exist.
- Coverage numbers must be evidenced reviewer-visibly (pasted `--print-summary` output in the PR body, green workflow-run link).

## Verified Workflow

### Quick Reference

```bash
# Mandatory pre-flight: run the EXACT CI gate invocation locally, require exit 0
gcovr --root . --filter include --filter src \
  --exclude src/server_main.cpp \
  --gcov-ignore-parse-errors=negative_hits.warn \
  --print-summary --fail-under-line 80 build/coverage

# Marker-effectiveness check: markers must be balanced and actually consumed by gcovr
grep -c LCOV_EXCL_START src/nats_client.cpp   # must equal...
grep -c LCOV_EXCL_STOP src/nats_client.cpp    # ...this count
gcovr --root . --filter include --filter src --json -o /tmp/cov.json build/coverage
# assert the file reports gcovr/excluded lines > 0 (catches syntactically-wrong
# markers being silently ignored)

# Pin gcovr in CI — do NOT use the apt package (Ubuntu 24.04 apt version drifts
# from the version the marker placement was tested against)
pip install 'gcovr==8.6'
```

Marker form (the "why" comment is mandatory):

```cpp
// LCOV_EXCL_START — <why unreachable in unit tests>
...live-only code...
// LCOV_EXCL_STOP
```

### Detailed Steps

1. **Remove the file-level `--exclude` in lock-step everywhere.** Delete it from BOTH the CI threshold gate and the developer report script in the same commit, so what the gate measures equals what developers see (DRY/POLA).
2. **Add markers only around regions provably unreachable without the live dependency.** Wrap with `// LCOV_EXCL_START — <why unreachable in unit tests>` / `// LCOV_EXCL_STOP`: connect-success branches, retry/reconnect loop bodies, provisioning loops, publish happy paths, library-callback shims and handlers. Leave guards and early-returns measured where unit tests drive them (disconnected-path tests).
3. **Apply the exclusion-boundary rules learned from review:**
   - If a function's ONLY caller is itself excluded, exclude the WHOLE function including its entry/guard. Verify the call graph yourself — do not trust a plan's claim that teardown paths exercise it (a plan claimed `close()` exercised a guard; `close()` never called that function).
   - Library callbacks that fire only for an established connection (e.g. nats.c `ClosedCB` when `conn_` is always `nullptr` in unit tests) are provably unreachable — exclude them rather than leaving ~20 measured-but-uncovered lines.
   - Exclusion comments must NOT assert "covered by integration tests" when no such suite exists. Write future tense with a tracking issue — "to be covered by integration tests (#NNN)" — and create the follow-up issue if it is missing.
4. **Pin gcovr in CI** via `pip install 'gcovr==8.6'` and remove the apt gcovr package (Ubuntu 24.04's apt version drifts from the version the marker placement was tested against). Add `--print-summary` to the gate step.
5. **Mandatory pre-flight before pushing:** run the EXACT CI gate invocation locally (see Quick Reference) and require exit 0. Never lower the threshold, never re-add the file exclude — widen markers only for genuinely live-only regions.
6. **Marker-effectiveness check:** generate gcovr JSON and assert the file has `gcovr/excluded` lines > 0 (catches syntactically-wrong markers being silently ignored); keep `grep -c LCOV_EXCL_START` equal to `grep -c LCOV_EXCL_STOP`.
7. **Post evidence reviewer-visibly:** paste the `--print-summary` numbers and the green workflow-run link into the PR body. Reviewers WILL block on unverified threshold claims.
8. **Re-anchor every region semantically at edit time.** Plan line numbers go stale (the file drifted ~75 lines between plan and implementation) — grep for the function name instead; never edit by line number.

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
| --------- | ---------------- | --------------- | ---------------- |
| Trust the plan's teardown claim | Leaving a guarded function entry measured because the plan said teardown exercises it | Reviewer proved the only caller was excluded; `close()` never called it | Verify the call graph before leaving code measured |
| Present-tense coverage claims | Present-tense "covered by integration tests" exclusion comments | Repo had no integration suite; reviewer flagged asserting nonexistent coverage | Future tense + tracking issue reference ("to be covered by integration tests (#NNN)") |
| File-level exclude | File-level `--exclude src/nats_client.cpp` (the original state) | Hides the real test quality of the most complex module | Fine-grained markers keep the honest number |
| Partial callback exclusion | Leaving `shim_closed`/`on_closed` measured (plan Decision 4) | `ClosedCB` never fires without an established connection, leaving ~8 permanently-uncovered measured lines | Callbacks gated on live-connection state are provably live-only — exclude them |

## Results & Parameters

### Configuration

```bash
# CI gate invocation (the exact command that must exit 0 locally before pushing)
gcovr --root . --filter include --filter src \
  --exclude src/server_main.cpp \
  --gcov-ignore-parse-errors=negative_hits.warn \
  --print-summary --fail-under-line 80 build/coverage

# gcovr version pin in CI (replaces apt gcovr)
pip install 'gcovr==8.6'
```

### Expected Output

- Before: `src/nats_client.cpp` wholly excluded from the gate; total ~92% lines.
- After refined markers: total 94.1% lines (590/627); file at 88% lines (71/80); functions 100%.
- `--fail-under-line 80` exits 0; 171/171 ctest tests pass.
- gcovr JSON shows 145 excluded lines in the file; 11 `LCOV_EXCL_START` / 11 `LCOV_EXCL_STOP` markers, balanced.
- Coverage CI workflow green on the PR, with `--print-summary` numbers pasted into the PR body.

## Verified On

| Project | Context | Details |
| --------- | --------- | --------- |
| ProjectNestor | issue #29 / PR #118 — coverage-gate inclusion of nats_client.cpp | commits 42a1bcd + 7f02349 |

## References

- [gcovr exclusion markers documentation](https://gcovr.com/en/stable/guide/exclusion-markers.html)
- [pytest-coverage-threshold-and-enforcement](pytest-coverage-threshold-and-enforcement.md) — Python-side coverage threshold patterns
