---
name: planning-generated-doc-from-source-headers
description: "When planning a task that generates a doc/index/matrix by parsing a convention out of many source files (e.g. a README from per-file headers), the load-bearing assumption is the textual convention itself — and it is almost always UNENFORCED. Use when: (1) planning a task that generates a doc/index/matrix by parsing a convention out of many source files, (2) a plan quotes counts derived from grep/sed spot-checks as if they were facts, (3) adding a `--check`/drift gate over a committed generated artifact, (4) a plan adds a `python3`/tool CI step assuming the interpreter is present on the runner. Headline lessons: (a) run the REAL parser over ALL inputs and assert 100% parse coverage before trusting any count; (b) a committed generated artifact + a `--check` drift gate is a chicken-and-egg that must be sequenced so the committed file is produced by the exact generator version CI runs, and compared structurally (not byte-exact)."
category: documentation
date: 2026-06-20
version: "1.0.0"
user-invocable: false
verification: unverified
tags:
  - planning
  - documentation-generation
  - generated-file
  - drift-gate
  - source-convention
  - header-parsing
  - verification
  - regex-brittleness
  - ci-assumptions
  - unenforced-convention
---

# Planning: Generate a Doc/Matrix by Parsing a Source-File Convention

## Overview

| Field | Value |
| ------- | ------- |
| **Date** | 2026-06-20 |
| **Objective** | Capture the durable planning pattern for tasks that generate a doc/index/matrix by parsing a textual convention out of many source files — and the unverified assumptions that silently corrupt the output |
| **Outcome** | Plan written but NOT executed (the generator script was never run, the regex was never run against the real files, CI never ran). Recorded as a hypothesis: the convention is load-bearing and unenforced, and the plan trusted spot-checks/grep counts in place of a full parse over all inputs |
| **Verification** | unverified |

The concrete trigger was a plan to generate a test-coverage matrix README for the `e2e/tests` directory (issue #199): every one of 37 test files was claimed to carry a deterministic 2-line header, and a generator would parse those headers into a table. The plan asserted the convention held based on a `sed -n '2,4p'` spot-check of a couple of files plus a `grep` count — it never ran the actual parser regex over all 37 files, so nothing proved the regex parses them.

## When to Use

Use this skill when:

- Planning a task that generates a doc / index / matrix / table by parsing a convention out of many source files (a README from per-file headers, a coverage matrix from test-file titles, an API index from docstrings).
- A plan quotes counts as facts ("37 tests, 64 IDs, 8 T4-only") that were actually derived from a `grep`/`sed` spot-check rather than from running the real parser.
- Adding a `--check` / drift gate over a committed generated artifact (CI regenerates and diffs against the committed file).
- A plan adds a `python3 ...` (or any tool) CI step on the assumption the interpreter is present on that job's runner/declared env.
- Any plan whose output correctness depends on a textual source-file convention that is not mechanically enforced.

## Verified Workflow

> **Warning:** This workflow has not been validated end-to-end (proposed — unverified). Treat as a hypothesis until CI confirms.

### Quick Reference

The headline checks before trusting a header-driven generator plan:

```bash
# 1. PARSE-COVERAGE PROOF — run the REAL parser over ALL inputs, assert 100% coverage.
#    A spot-check + a grep count is NOT proof the regex parses every file.
python3 generate_matrix.py --assert-full-parse   # must fail loudly on ANY unparsed file

# 2. Independently enumerate the population; cross-check the generator's count
#    against a DIFFERENT source than the grep that produced the quoted numbers.
ls e2e/tests/*.md | wc -l        # independent file count
# compare to the generator's own emitted row count — they must agree

# 3. Generate the committed artifact with the FINAL script, in the SAME PR as the gate.
python3 generate_matrix.py > e2e/tests/README.md
git add e2e/tests/README.md

# 4. Confirm the interpreter the CI step needs is actually guaranteed on that runner.
grep -E 'python' pixi.toml || echo "python3 NOT a declared dep — do not assume it"
```

### Detailed Steps (proposed planning checklist)

1. **Treat the convention as the load-bearing assumption.** Write the plan as if the convention will be violated, because it is unenforced. Identify every textual feature the parser relies on (line count, delimiter character, ordering, ID format).
2. **Add a step that runs the real parser over ALL inputs and asserts 100% parse coverage BEFORE trusting any count.** The generator must fail loudly (non-zero exit, named file) on any file it cannot parse — not silently drop or mis-parse it. A `sed` spot-check of two files plus a `grep -c` is not a substitute.
3. **Audit the regex for the specific brittle features** (see Results): literal em-dash topology flags, non-greedy title capture before an optional group, over-broad `\b[ABCDE][0-9]{2}\b` ID matching. Each needs a test against a REAL representative line (especially a real non-T4 line), not just synthetic examples.
4. **Cross-check every quoted count against an INDEPENDENT enumeration.** Do not let the verification step grep for the same numbers the plan derived by grep — that is circular and passes vacuously.
5. **Sequence the committed-artifact + drift-gate explicitly.** Generate the committed file with the exact final generator version in the same PR as the `--check` gate, and compare structurally (or normalize newlines/CRLF/locale) rather than byte-exact — otherwise `--check` red-flags on the first PR.
6. **Verify environment assumptions.** If a CI step runs `python3 ...`, confirm the interpreter is a declared dependency (e.g. in `pixi.toml`) or otherwise guaranteed on that job's runner — do not assume the GitHub-hosted `ubuntu-latest` default.

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
| --------- | ---------------- | --------------- | ---------------- |
| Spot-check instead of full parse | Asserted "all 37 files have a deterministic 2-line header" from a `sed -n '2,4p'` view of a couple files plus a `grep` count | The parser regex was never run over all 37 files; a header generator silently drops/mis-parses any deviation (extra license line, blank line 2, wrapped title, em-dash vs hyphen, IDs on a continuation line) | When a generator's output depends on a textual convention, the plan MUST run the real parser over ALL inputs and assert 100% parse coverage before trusting any count |
| Em-dash topology flag | `HEADER_RE` uses a literal em-dash `—` (U+2014) to detect "— T4 only" topology | Any file using a hyphen `-` or en-dash `–` sets the topology flag silently wrong; no error is raised | Detecting semantics from an exact glyph is brittle; test the flag against real files and normalize/allow the dash variants, or fail loudly on unexpected glyphs |
| Non-greedy title vs optional group | Title capture `(?P<title>.*?)` is non-greedy before an OPTIONAL `t4` group | On non-T4 lines the title can capture empty/partial; the two synthetic test lines in the plan were both T4-ish and never exercised a real non-T4 line | Non-greedy capture before an optional group needs a test against a REAL non-T4 line, not synthetic happy-path examples |
| Over-broad ID regex | IDs matched with `\b[ABCDE][0-9]{2}\b` anywhere in lines 2–3 | Matches stray tokens like "D08" appearing in prose (e.g. inside `Validates:`), producing false-positive IDs and inflating counts | Anchor ID extraction to its column/field, not "anywhere in the line"; over-broad `\b...\b` patterns pick up prose tokens |
| Byte-exact drift diff | CI `--check` compared `current != content` byte-for-byte against the committed README | Trailing-newline / CRLF / locale differences between local gen and CI gen flip the diff; also a committed file produced by an older generator version red-flags on the first PR | Normalize or compare structurally, and always generate the committed artifact with the FINAL script in the SAME PR as the gate |
| Assumed python3 in CI | Added `python3 generate_matrix.py` as a `ci.yml validate` step assuming 3.13 is present | `python3` is NOT a declared `pixi` dependency (only `nodejs`, `shellcheck`, etc.); the runner's interpreter was assumed from the `ubuntu-latest` base image, never verified | A plan that adds a `python3`/tool CI step must confirm the interpreter is guaranteed on that job's runner/declared env, not assume the GitHub-hosted default |
| Circular count verification | Verification step greps for "37 tests, 64 IDs, 8 T4-only" — the same numbers the plan derived by grep | Both sides of the check come from the same `grep`; it passes vacuously and proves nothing | A real verification cross-checks the generator's emitted count against an INDEPENDENT enumeration |

## Results & Parameters

### The brittle regex (what to audit)

```python
# Illustrative of the load-bearing parser. Each highlighted feature is a failure mode.
HEADER_RE = re.compile(
    r"^#\s+(?P<id_block>(?:[ABCDE][0-9]{2}[,\s]*)+)\s*"
    r"(?P<title>.*?)"                 # non-greedy title BEFORE an optional group → can under-capture on non-T4 lines
    r"(?:\s+—\s+(?P<t4>T4)\s+only)?"  # literal em-dash U+2014 → silently wrong on hyphen/en-dash
    r"\s*$"
)
ID_RE = re.compile(r"\b[ABCDE][0-9]{2}\b")  # matches stray "D08" anywhere in lines 2–3 → false positives
```

### Corrected verification commands (run the parser over ALL files; cross-check counts independently)

```bash
# Assert 100% parse coverage — generator must name and fail on ANY unparsed file:
python3 generate_matrix.py --assert-full-parse
# Implementation contract inside the generator:
#   unparsed = [f for f in files if HEADER_RE.match(header_line(f)) is None]
#   if unparsed: sys.exit(f"UNPARSED HEADERS: {unparsed}")   # never silently skip

# Independent enumeration to cross-check the generator's emitted count:
EXPECTED=$(ls e2e/tests/*.md | wc -l)
EMITTED=$(python3 generate_matrix.py --count-rows)
[ "$EXPECTED" = "$EMITTED" ] || { echo "COUNT MISMATCH: files=$EXPECTED rows=$EMITTED"; exit 1; }

# Structural (not byte-exact) drift gate — normalize trailing newline/CRLF before diff:
python3 generate_matrix.py | git --no-pager diff --no-index --ignore-cr-at-eol - e2e/tests/README.md
```

### Sequencing the committed artifact + drift gate (same PR)

1. Finalize the generator.
2. Regenerate the committed README with that exact script in the SAME PR.
3. Add the `--check` gate that regenerates and compares structurally.
4. Confirm `python3` (or whatever interpreter) is a declared dep / guaranteed on the runner.

### Expected output of a correct plan

- Generator fails loudly on any unparsed input; parse coverage is 100% and proven by running it, not by spot-check.
- Counts in the plan are corroborated by an independent enumeration, not by the grep that produced them.
- The committed artifact and the drift gate land together; `--check` is green on the first PR.
- The CI interpreter assumption is confirmed against `pixi.toml`/runner env.

## Verified On

| Project | Context | Details |
| --------- | --------- | --------- |
| ProjectMnemosyne | e2e/tests matrix generator plan for issue #199 — plan written, NOT executed (regex never run against real files, CI never run); recorded as an unverified hypothesis | This skill |

## References

- [planning-verify-full-population-not-just-named-entities](planning-verify-full-population-not-just-named-entities.md)
- [planning-verify-assumptions-before-enforcement-gate](planning-verify-assumptions-before-enforcement-gate.md)
- [ci-matrix-yaml-multiformat-regex-fallback](ci-matrix-yaml-multiformat-regex-fallback.md)
- [doc-comment-count-drift-verify-frozen-test](doc-comment-count-drift-verify-frozen-test.md)
