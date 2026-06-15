---
name: planning-test-coverage-verify-premise-and-mock-targets
description: "When planning a 'add tests for an untested module' task, the issue's filename, line numbers, and 'X is untested' claim are a HYPOTHESIS to verify against the filesystem before adopting them — and the mock.patch target must be the rebound name in the CONSUMER module, not the definition site. Use when: (1) planning unit-test coverage for a module an issue says is untested, (2) an issue tells you to CREATE a specific test file path, (3) the module under test uses `from .x import y` and your tests need to mock y, (4) deciding whether an 'untested' claim means no file or no coverage of specific methods."
category: testing
date: 2026-06-15
version: "1.0.0"
user-invocable: false
verification: unverified
tags:
  - python
  - testing
  - mock
  - patch
  - planning
  - test-coverage
  - issue-premise
  - pytest
  - unittest-mock
  - dry
---

# Planning Test-Coverage Tasks: Verify the Premise and Get Mock Targets Right

## Overview

| Field | Value |
|-------|-------|
| **Date** | 2026-06-15 |
| **Objective** | Produce a correct plan for adding unit-test coverage to a supposedly-untested module, without creating duplicate files or writing mocks that silently exercise real code |
| **Outcome** | Plan produced; NOT executed end-to-end — mock-target paths, keyword-vs-positional `call_args`, and the return-tuple shape were read from source but never run |
| **Verification** | unverified |

When an issue asks you to "add tests for untested method(s) of module X," it usually
sketches a fix: a filename to create, line numbers, sometimes the assertions. That sketch
is a hypothesis, not a spec. Two failure modes dominate the planning phase:

1. **The filename / "untested" premise is wrong** — a test file already exists under a
   different (sibling-convention) name, or the module is partially tested. Adopting the
   issue's literal filename creates a duplicate file (DRY/KISS violation) and splits coverage.
2. **The mock.patch target is wrong** — the module under test rebinds imported names into
   its own namespace (`from .learn import compact_session`), so tests must patch
   `consumer_module.compact_session`, not `learn.compact_session`. Patch the definition site
   and every test silently runs the real subprocess.

## When to Use

- Planning any "add unit tests for untested module/method" issue
- The issue body instructs you to CREATE a specific test file path
- The issue claims a module is "untested" (verify: no file, or no coverage of *these* methods?)
- The module under test uses `from .sibling import name` and your tests must mock `name`
- You are about to write `@patch("pkg.defining_module.func")` for a function the target imports
- You are writing `call_args.kwargs["cwd"]` (or any kwarg) assertions on a mocked call
- The plan proposes removing a coverage omit-allowlist entry (`pyproject.toml`)

## Verified Workflow

> **Warning:** This workflow has not been validated end-to-end. The proposed tests were never executed; mock-target paths and `call_args.kwargs[...]` assumptions were read from source only. Treat as a hypothesis until CI confirms.

### Quick Reference

```bash
# STEP 1 — ls the target test dir BEFORE planning to CREATE a file.
ls tests/unit/automation/ | grep -i post_merge
# → test_post_merge_helpers.py ALREADY EXISTS (sibling convention drops "_processor")
#   The issue said create test_post_merge_PROCESSOR_helpers.py → would duplicate.

# STEP 2 — distinguish "no file" from "no coverage of these methods".
grep -nE "def test_|class Test" tests/unit/automation/test_post_merge_helpers.py
# → only covers mark_drive_green_learn_result; the two named methods ARE untested.

# STEP 3 — find the mock-patch target: how does the CONSUMER bind the symbol?
grep -n "^from\|^import" hephaestus/automation/post_merge_processor.py
# → from .learn import compact_session, invoke_claude_with_session
#   ⇒ patch "hephaestus.automation.post_merge_processor.compact_session"
#     NOT "hephaestus.automation.learn.compact_session"

# STEP 4 — confirm kwarg vs positional at the CALL SITE before asserting on kwargs.
grep -n "invoke_claude_with_session\|compact_session" hephaestus/automation/post_merge_processor.py
# read the call: is cwd= passed as a keyword? If positional, call_args.kwargs["cwd"] KeyErrors.
```

**Core rule (premise):** an issue that sketches a fix (filename, line numbers, "X is
untested") is a hypothesis. `ls` the target dir and `grep` the existing test file's
`def test_` / `class Test` before adopting any of it.

**Core rule (patch target):** `from .x import y` binds `y` into the importer's namespace at
import time. Patch `consumer_module.y`, never `x.y`. (Same Python binding rule as
`testing-module-patch-target-after-extraction`, but here it bites at test-authoring time,
not after a refactor.)

### Detailed Steps

1. **`ls` the target test directory before planning to CREATE a file.** The issue named
   `tests/unit/automation/test_post_merge_processor_helpers.py`. An `ls` revealed
   `test_post_merge_helpers.py` already exists, and that the sibling naming convention drops
   the `_processor` segment. Creating the issue's literal name would have produced a second
   test file for one module — a DRY/KISS violation that splits coverage. Adopt the existing
   file and convention, not the issue's filename.

2. **Distinguish "no test file" from "no coverage of these methods."** The issue said the
   module was untested. Reality: a partial file existed covering only one method, with the two
   named methods genuinely untested. Open the existing file and `grep -nE "def test_|class Test"`
   before accepting an "X is untested" claim. The premise was directionally right but factually
   imprecise — the plan must reflect the actual gap (extend the file), not the claimed one
   (create a file).

3. **Resolve the mock.patch target from the consumer's imports, not the definition site.**
   `post_merge_processor.py` does `from .learn import compact_session, invoke_claude_with_session, ...`,
   binding those names into its own namespace. Tests must patch
   `hephaestus.automation.post_merge_processor.compact_session`, NOT
   `hephaestus.automation.learn.compact_session`. This is the single highest-risk assumption
   in the plan: if wrong, every test silently exercises the real subprocess and passes
   vacuously (false green).

4. **Confirm keyword vs positional before asserting on `call_args.kwargs[...]`.** The plan
   asserts `call_args.kwargs["cwd"]`. That only works if the call site passes `cwd=` as a
   keyword. Read the actual call (`grep -n` the callee in the consumer) — if `cwd` is
   positional, `call_args.kwargs["cwd"]` raises `KeyError`. Reading source confirmed keyword
   here, but it was never executed.

5. **Confirm the mocked return shape.** Assertions depended on the return-tuple shape of
   `invoke_claude_with_session` (read at source lines 156/159/221). A mock that returns the
   wrong arity makes the test pass/fail for the wrong reason. Read the real return statement,
   or — better — run the test once before declaring the plan verified.

6. **Treat coverage-omit-allowlist edits as conditional.** Removing the
   `pyproject.toml` omit entry for the module is only safe if the new tests push module
   coverage above the project threshold. If unsure, leave a note in the PR rather than
   committing the removal — a premature removal turns a green run red.

7. **Prefer a plain helper over a clever raising lambda (POLA).** The
   `(_ for _ in ()).throw(...)` trick to build a no-arg raising callable is clever-but-obscure.
   A 2-line `def _raise(*_a, **_k): raise ...` helper reads better and is equally mockable.

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
|---------|----------------|---------------|----------------|
| Adopt the issue's literal filename | Plan to CREATE `tests/unit/automation/test_post_merge_processor_helpers.py` as the issue said | A file `test_post_merge_helpers.py` already existed (sibling convention drops `_processor`); creating the named file would duplicate test coverage for one module | `ls` the target test dir and learn the naming convention BEFORE planning to create a file; the issue's filename is a hypothesis |
| Trust the "module is untested" claim | Plan assumed zero existing coverage and a fresh file | A partial test file existed covering `mark_drive_green_learn_result`; only the two named methods were actually untested | `grep -nE "def test_\|class Test"` the existing file; "untested" may mean "these methods untested," not "no file" |
| Patch at the definition site | `@patch("hephaestus.automation.learn.compact_session")` (where it is defined) | `post_merge_processor` did `from .learn import compact_session`, rebinding the name into its own namespace; the definition-site patch never intercepts the consumer's lookup | Patch `consumer_module.symbol` (the rebound name), not the defining module; otherwise the real subprocess runs and the test is a false green |
| Assume `cwd` is positional in `call_args` | Planned `call_args.kwargs["cwd"]` without checking the call site | If the call passes `cwd` positionally, `call_args.kwargs["cwd"]` raises `KeyError` (here it was keyword, confirmed by reading source — not by running) | Read the call site to confirm keyword vs positional before asserting on `call_args.kwargs[...]`; or use `call_args.args`/`call_args[1]` deliberately |
| Plan to remove the coverage omit-allowlist entry | Considered deleting the `pyproject.toml` omit line for the module | Safe only if the new tests lift module coverage above the threshold; otherwise the run goes red | Treat omit-allowlist removals as conditional; note in the PR rather than committing when coverage impact is unverified |
| Use a clever raising-lambda for a no-arg callable | `(_ for _ in ()).throw(SomeError(...))` to make a raising side_effect | Clever-but-obscure; violates POLA and is hard to read in review | Use a plain `def _raise(*a, **k): raise ...` helper — same behavior, readable |
| Declare the plan verified from reading source | Read lines 156/159/221 for return shape and call kwargs | Reading is not running; mock-target paths, kwarg assumptions, and return arity were never executed | Run the proposed tests once before claiming verification; until then mark the plan `unverified` and point the reviewer at these assumptions |

## Results & Parameters

### The mock-target rule, concretely

```python
# post_merge_processor.py (the CONSUMER) rebinds the names:
from .learn import compact_session, invoke_claude_with_session

# WRONG — patches the definition site; consumer already rebound the name.
#         The real subprocess runs; the test passes vacuously (false green).
@patch("hephaestus.automation.learn.compact_session")

# CORRECT — patch the rebound name in the consumer's namespace.
@patch("hephaestus.automation.post_merge_processor.compact_session")
@patch("hephaestus.automation.post_merge_processor.invoke_claude_with_session")
def test_run_drive_green_compact(self, mock_invoke, mock_compact):
    ...
```

### kwarg-vs-positional assertion guard

```python
# Only valid if the call site passes cwd= as a KEYWORD:
#   compact_session(session_id, cwd=repo_root)   ← keyword → OK
assert mock_compact.call_args.kwargs["cwd"] == repo_root

# If the call site is positional:
#   compact_session(session_id, repo_root)       ← positional → KeyError above
# then assert on the positional slot deliberately:
assert mock_compact.call_args.args[1] == repo_root
```

### Pre-plan checklist for "add tests for untested module X"

```text
1. ls <test_dir>           → does a file already exist? what's the sibling naming convention?
2. grep def test_/class Test in any existing file → which methods are ALREADY covered?
3. grep ^from/^import in module X → which names are rebound? (patch targets live here)
4. read the call site → is each asserted kwarg passed by keyword or positionally?
5. read the callee's return statement → what arity/shape must the mock return?
6. coverage omit-allowlist edit → only if new tests clear the threshold; else note in PR
7. RUN the tests once → only then may the plan be called "verified"
```

### Context (ProjectHephaestus issue #1362)

Task: add unit-test coverage for `run_drive_green_learnings` and `run_drive_green_compact`
on `PostMergeProcessor` in `hephaestus/automation/post_merge_processor.py`.

- Issue said create `test_post_merge_processor_helpers.py`; the real file is
  `tests/unit/automation/test_post_merge_helpers.py` (63 lines, sibling convention drops
  `_processor`). Adopting the issue's name would have created a duplicate.
- Issue said "untested"; the file partially covered `mark_drive_green_learn_result` only.
- Highest-risk assumption: patch `hephaestus.automation.post_merge_processor.<name>`
  (consumer binding), not `hephaestus.automation.learn.<name>`.
- Plan was NOT executed — `unverified`. Reviewer focus: mock-target paths,
  `call_args.kwargs["cwd"]` keyword assumption, and the return-tuple shape of
  `invoke_claude_with_session`.

### Related skills

- `testing-module-patch-target-after-extraction` — same Python import-binding rule, but in
  the post-refactor failure context (tests that broke after a module extraction).
- `planning-follow-up-issue-line-number-drift` — verify cited line numbers against current
  HEAD; complementary "verify the issue's premise" discipline for line drift specifically.

## Verified On

| Project | Context | Details |
|---------|---------|---------|
| ProjectHephaestus | Issue #1362 — add coverage for `run_drive_green_learnings` / `run_drive_green_compact` on `PostMergeProcessor` | unverified — plan produced from source reading; tests never executed |
