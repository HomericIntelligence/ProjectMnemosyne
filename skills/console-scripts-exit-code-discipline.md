---
name: console-scripts-exit-code-discipline
description: "Enforce exit-code discipline for Python console-script main() functions without breaking existing return-value contracts. Use when a CLI exits 0 despite recoverable errors, helper methods have tuple-return callers, or cumulative error state must be tracked through instance state instead of changing signatures."
category: architecture
date: 2026-05-28
version: "2.0.0"
user-invocable: false
verification: verified-local
history: console-scripts-exit-code-discipline.history
tags: [python, console-scripts, exit-codes, error-tracking, instance-state, tuple-contracts, cli, ci-cd]
---

# Console Scripts Exit-Code Discipline

## Overview

A console script that exits `0` after recoverable read/write/validation errors trains CI and shell callers to trust failures. The fix must expose a nonzero process exit while preserving existing helper return contracts that tests and callers already unpack.

This skill consolidates the exit-code discipline and instance-state error-tracking memories. The canonical pattern is: keep public tuple returns stable, record cumulative failure on the instance, and have `main()` return the final exit code consumed by `sys.exit()`.

| Field | Value |
|-------|-------|
| Date | 2026-07-04 |
| Objective | Generalize console-script exit-code discipline and preserve tuple-contract compatibility details. |
| Outcome | Canonical v2 replaces the narrower instance-state skill; notes and source snapshots are preserved in history. |
| Verification | verified-local for this consolidation; source examples preserve their original verified-ci status in history. |

## When to Use

- A console-script entrypoint calls `sys.exit(0)` unconditionally or returns `None` despite recoverable errors.
- A helper method returns a fixed-shape tuple that existing tests or callers unpack.
- You need cumulative error state across multiple helper calls without changing public method signatures.
- A pre-commit, CI, or shell pipeline can miss failures because a CLI always exits success.
- You are considering expanding tuple shapes, adding error-tracker parameters, or creating a wrapper class solely to carry exit state.

## Verified Workflow

### Quick Reference

```python
import sys


class Processor:
    def __init__(self, paths: list[str]) -> None:
        self.paths = paths
        self.had_error = False

    def process_file(self, path: str) -> tuple[bool, dict[str, object] | None]:
        try:
            data = self._read(path)
        except OSError:
            self.had_error = True
            return False, None
        return True, data

    def main(self) -> int:
        for path in self.paths:
            self.process_file(path)
        return 1 if self.had_error else 0

if __name__ == "__main__":
    raise SystemExit(Processor(sys.argv[1:]).main())
```

1. Find console entrypoints that mask errors: `rg 'sys\.exit\(0\)|def main\(.*\) -> None' <package>/`.
2. Identify helper methods with tuple-return callers before changing contracts: `rg 'method_name\(.*\)' tests/ <package>/` and inspect unpacking sites.
3. Add `self.had_error: bool = False` or a similarly named instance attribute in `__init__`.
4. Set the flag at every recoverable error site: file read, file write, validation, missing input, or processing errors that should not immediately abort.
5. Preserve existing helper signatures and tuple shapes. Return the same tuple shape callers already expect.
6. Change `main()` to return `int`; compute `1 if self.had_error else 0` after processing.
7. Make the entrypoint consume the returned code exactly once: `sys.exit(main())` or `raise SystemExit(main())`.
8. Add tests for success exit `0` and error exit nonzero without rewriting unrelated tuple-callsite tests.

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
|---|---|---|---|
| Expand tuple return shape | Changed a helper from a 2-tuple to a 3-tuple carrying error state. | Existing tests and callers unpacked the 2-tuple, causing broad churn. | Track CLI error state outside stable helper return contracts. |
| Add error-tracker parameters | Threaded an extra parameter through helper methods. | It required many callsite edits for a CLI-only concern. | Use instance state when the state belongs to the object lifecycle. |
| Re-raise recoverable errors at the end | Collected errors and raised after processing. | It complicates tests and obscures which path set the final exit code. | Let helpers set state and let `main()` make one exit decision. |
| Add a wrapper CLI class | Split processing and CLI exit behavior into separate classes. | It duplicated processing methods and increased maintenance. | One class can support tuple-return helper use and CLI exit-code use. |
| Return an exit code but keep `sys.exit(0)` | Computed a code in `main()` but the entrypoint still exited success. | The parent process never saw the computed failure. | There must be one final exit-code decision point. |
| Use global error state | Considered module-level `_had_error`. | Globals are harder to isolate in tests and unsafe for concurrent use. | Prefer instance state scoped to the processor. |

## Results & Parameters

Implementation checklist:

```yaml
exit_code_contract:
  success: 0
  recoverable_error: 1
compatibility_contract:
  preserve_helper_signatures: true
  preserve_tuple_shapes: true
state_location:
  preferred: instance_attribute
  avoid: [global_flag, tuple_shape_expansion, wrapper_duplication]
entrypoint:
  main_returns: int
  final_call: sys.exit(main())
```

Search commands:

```bash
rg 'sys\.exit\(0\)|def main\(.*\) -> None' hephaestus/ tests/
rg 'fix_file|process_file|validate' tests/ hephaestus/
```

ProjectHephaestus issue #632 outcome:

| Module | Change | Verification |
|---|---|---|
| markdown fixer | Added instance `had_error`, set it at read/write/validation failures, returned nonzero from main. | 119 tests passed. |
| system info | Normalized `main() -> int`. | CI green. |
| dataset downloader | Returned exit code instead of exiting internally. | CI green. |
