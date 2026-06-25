---
name: planning-generated-doc-from-source-headers
description: "When planning a task that generates a doc/index/matrix by parsing a convention out of many source files (e.g. a README from per-file headers), the load-bearing assumption is the textual convention itself — and it is almost always UNENFORCED. Citing this skill is NOT applying it: the deliverable of the 'run the parser over ALL inputs' rule is pasted command OUTPUT (e.g. 37/37 conform, count=65, T4=7), not the sentence 'verified across all files' — a reviewer can falsify a prose claim against the real repo in minutes. Use when: (1) planning a task that generates a doc/index/matrix by parsing a convention out of many source files, (2) a plan quotes counts derived from grep/sed spot-checks as if they were facts, (3) adding a `--check`/drift gate over a committed generated artifact, (4) a plan adds a `python3`/tool CI step assuming the interpreter is present on the runner. Headline lessons: (a) run the REAL parser over ALL inputs and PASTE the output asserting 100% parse coverage before trusting any count; (b) `grep -rl <phrase>` over-matches (catches runtime strings, not just the header line) — extract from the exact positional line; (c) labeled ID ranges are non-contiguous — enumerate tokens, never assume density; (d) a committed generated artifact + a `--check` drift gate must be sequenced so the committed file is produced by the exact generator version CI runs, compared structurally (not byte-exact)."
category: documentation
date: 2026-06-20
version: "1.1.0"
user-invocable: false
verification: verified-local
history: planning-generated-doc-from-source-headers.history
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
  - grep-rl-overmatch
  - non-contiguous-ranges
  - paste-output-not-claims
---

# Planning: Generate a Doc/Matrix by Parsing a Source-File Convention

## Overview

| Field | Value |
| ------- | ------- |
| **Date** | 2026-06-20 |
| **Objective** | Capture the durable planning pattern for tasks that generate a doc/index/matrix by parsing a textual convention out of many source files — and the unverified assumptions that silently corrupt the output |
| **Outcome** | An R0 plan that *cited this skill* still earned a NOGO because it applied the lessons as prose claims and shipped three falsified facts. The session converged only after each NOGO finding was re-derived against ground truth. Distilled meta-lesson: citing the skill ≠ applying it; the deliverable is pasted command OUTPUT, not assertions |
| **Verification** | verified-local |
| **History** | [changelog](./planning-generated-doc-from-source-headers.history) |

The concrete trigger was a plan to generate a test-coverage matrix README for the `e2e/tests` directory (Odysseus issue #199): every test file was claimed to carry a deterministic 2-line header, and a generator would parse those headers into a table. The plan asserted the convention held based on a `sed -n '2,4p'` spot-check of a couple files plus a `grep` count — it never ran the actual parser regex over all files, so nothing proved the regex parses them.

**Headline framing (the amendment's substance):** *Citing this skill ≠ applying it. The deliverable of the "run the parser over all inputs" rule is pasted command OUTPUT (37/37 conform, count=65, T4=7), not the sentence "verified across all files." A reviewer can falsify a prose claim against the real repo in minutes.* The R0 plan from the prior round got a NOGO **even though it cited `planning-generated-doc-from-source-headers`** — it quoted the skill's lessons as prose ("verified across all 37 files") yet still shipped three falsified facts (an over-counted T4 flag, a fabricated contiguous-range total, and a colon-anchored regex that dropped one description). The meta-pattern from the whole session: an iterative plan→review→replan loop converged precisely because each NOGO finding was re-derived against ground truth — the value was in *executing* the checks the prior plan only asserted.

## When to Use

Use this skill when:

- Planning a task that generates a doc / index / matrix / table by parsing a convention out of many source files (a README from per-file headers, a coverage matrix from test-file titles, an API index from docstrings).
- A plan quotes counts as facts ("37 tests, 64 IDs, 8 T4-only") that were actually derived from a `grep`/`sed` spot-check rather than from running the real parser and pasting its output.
- A plan uses `grep -rl <phrase>` over a directory to count files that carry a positional flag (a flag defined by line 2 / line 3, not "anywhere in the file").
- A plan computes a population count by treating a labeled ID range (`A01–A18`) as densely populated.
- Adding a `--check` / drift gate over a committed generated artifact (CI regenerates and diffs against the committed file).
- A plan adds a `python3 ...` (or any tool) CI step on the assumption the interpreter is present on that job's runner/declared env.
- Any plan whose output correctness depends on a textual source-file convention that is not mechanically enforced.

## Verified Workflow

> **Note:** planning workflow — facts verified locally via grep/sed/xxd against the real repo; generator + CI not yet executed. The ground-truth numbers below (65 IDs, 37 tests, 7 T4-only, the no-colon line, the em-dash byte) were each confirmed by running real `grep`/`sed`/`xxd` against the actual Odysseus repo this session. The generator script itself was NOT executed and CI never ran, so this remains a planning artifact (hence `verification: verified-local`, not `verified-ci`).

### Quick Reference

The headline checks before trusting a header-driven generator plan — each must produce PASTED OUTPUT in the plan, not a prose claim:

```bash
# 1. PARSE-COVERAGE PROOF — run the REAL parser over ALL inputs, PASTE the output.
#    A spot-check + a grep count is NOT proof the regex parses every file.
#    "verified across all files" is a falsifiable sentence; "37/37 conform" with
#    the command that produced it is a fact.
python3 generate_matrix.py --validate   # asserts every file parses; exits non-zero NAMING the offender

# 2. POSITIONAL FLAG — extract from the EXACT line, never a whole-file grep.
#    `grep -rl 'T4 only' e2e/tests/` over-matches: it returns files where the
#    phrase appears in a runtime string (e.g. skip_topology "... (T4 only)" on
#    line 14), not just the line-2 header. Count from the header line only:
T4=$(for f in e2e/tests/*.sh; do sed -n '2p' "$f" | grep -q 'T4 only' && echo "$f"; done | wc -l)
echo "T4-only (header-derived) = $T4"    # → 7, NOT the 8 a whole-file grep returns

# 3. NON-CONTIGUOUS RANGES — enumerate tokens; never assume a labeled range is dense.
#    "A01–A18, B01–B14, C01–C16, D01–D12, E01–E13" implies 64 but C skips
#    C10/C13/C14, D skips D04/D05, E is sparse → actual unique count is 65.
COUNT=$(grep -ohE '\b[ABCDE][0-9]{2}\b' e2e/tests/*.sh | sort -u | wc -l)
echo "unique IDs = $COUNT"               # → 65; let the count fall out of enumeration

# 4. DUMP ALL N LINES of the parsed field to surface the 1-in-N exception.
#    36/37 line-3 descriptions use `# Validates:`/`# Measures:`; subject-routing.sh:3
#    is `# Validates NATS subject construction...` with NO colon. A colon-anchored
#    regex silently drops it. A spot-check of the first few files misses it.
for f in e2e/tests/*.sh; do sed -n '3p' "$f"; done   # eyeball ALL N, not the first 3

# 5. Generate the committed artifact with the FINAL script, in the SAME PR as the gate.
python3 generate_matrix.py > e2e/tests/README.md && git add e2e/tests/README.md

# 6. Confirm the interpreter the CI step needs is actually guaranteed on that runner —
#    prefer co-location with an existing working invocation over a bare assertion.
grep -nE 'python3' .github/workflows/_required.yml   # host the gate where python3 already runs
grep -E 'python' pixi.toml || echo "declare python = '>=3.11' for the local just-lint path"
```

### Detailed Steps (planning checklist)

1. **Treat the convention as the load-bearing assumption.** Write the plan as if the convention will be violated, because it is unenforced. Identify every textual feature the parser relies on (line count, line *position*, delimiter character, ordering, ID format).
2. **Run the real parser over ALL inputs and PASTE its output.** Citing this rule is not satisfying it. The plan must contain the actual `--validate` run output (`37/37 conform`, the named offender on failure), the actual `count=65` from enumeration, the actual `T4=7`. A sentence like "verified across all files" is exactly the kind of unfalsified prose claim that earned the prior plan a NOGO.
3. **Extract positional flags from their exact line, never a whole-file grep.** A flag defined by its position (line 2 header) must be read with `sed -n '2p' | grep -q`, not `grep -rl <phrase> <dir>/` — the latter conflates documentation with runtime strings and over-counts (8 vs the true 7).
4. **Enumerate tokens for any count; never assume a labeled range is dense.** Compute counts with `grep -ohE '<idpat>' | sort -u | wc -l` and let the number fall out. Writing "X01–Xnn" in a plan implies a density you have not verified — the real IDs were non-contiguous (true unique count 65, not the 64 the dense-range reading implied).
5. **Dump ALL N lines of every parsed field** to surface the 1-in-N exception (the no-colon `subject-routing.sh:3`). A spot-check of the first few files is exactly what misses it; this is the concrete payoff of the "run over ALL inputs" rule.
6. **Add a `--validate` mode that asserts every file parses** (non-empty title AND non-empty description) and exits non-zero NAMING the offender — and SHOW its output over the real tree in the plan. Position-based parsing (line 2 / line 3) is fragile to any inserted license header or blank line, which shifts every field.
7. **Cross-check every quoted count against an INDEPENDENT enumeration.** Do not let the verification step grep for the same numbers the plan derived by grep — that is circular and passes vacuously.
8. **Sequence the committed-artifact + drift-gate explicitly.** Generate the committed file with the exact final generator version in the same PR as the `--check` gate, and compare structurally (or normalize newlines/CRLF/locale) rather than byte-exact — otherwise `--check` red-flags on the first PR.
9. **Host a new interpreter CI gate in a job that ALREADY runs that interpreter on the same runner.** Do not assert "python3 is present." In Odysseus, `python3` is undeclared in `pixi.toml`, but the pinned required gate `_required.yml`'s `unit-tests` job already runs `python3 -c "..."` on `ubuntu-latest` — adding the new check there proves availability by co-location with a working invocation. For the local path (`just lint` shelling to python3) declare the interpreter (`python = ">=3.11"` in `pixi.toml`). Per the `ci-hygiene-and-validation-gates` skill, do NOT rename a pinned-context required job — the job `name:` is pinned in the org ruleset.

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
| --------- | ---------------- | --------------- | ---------------- |
| Citing the skill instead of applying it | The R0 plan cited `planning-generated-doc-from-source-headers` and wrote "verified across all 37 files" as prose, then shipped three falsified facts | A prose claim of coverage is unfalsifiable in the plan but trivially falsifiable against the real repo; the reviewer re-ran the checks in minutes and found the over-count, the fabricated total, and the dropped description | The deliverable of the "run the parser over ALL inputs" rule is pasted command OUTPUT (37/37 conform, count=65, T4=7), NOT the sentence "verified across all files." Citing ≠ applying |
| `grep -rl` to count a positional flag | `grep -rl 'T4 only' e2e/tests/` returned 8 files for the T4-only count | One file (`hermes-reconnect.sh`) only contained "T4 only" inside a runtime `skip_topology "... (T4 only)"` string on line 14, NOT in its line-2 header; the true header-derived count is 7 | A whole-file `grep -rl` conflates documentation with runtime strings. When a flag is defined by its position (line 2 header), extract from that exact line (`sed -n '2p' \| grep -q`), never a whole-file grep |
| Dense-range count | Quoted IDs as contiguous: "A01–A18, B01–B14, C01–C16, D01–D12, E01–E13 = 64" | The real IDs are non-contiguous (C skips C10/C13/C14, D skips D04/D05, E sparse); actual unique count is 65, not the 64 the dense reading implied | Never compute a count by assuming a labeled range is fully populated; enumerate the actual tokens (`grep -ohE '<idpat>' \| sort -u \| wc -l`) and let the count fall out. Writing "X01–Xnn" implies density you have not verified |
| Colon-anchored description regex | A regex anchored on `# Validates:`/`# Measures:` to parse line-3 descriptions | `subject-routing.sh:3` is `# Validates NATS subject construction...` with NO colon (36/37 use a colon); the regex silently dropped it | The "1 exception in N" is exactly what a spot-check of the first few files misses; dumping ALL N lines (`for f in .../*.sh; do sed -n '3p' "$f"; done`) surfaces it — the concrete payoff of "run over ALL inputs" |
| Position-based parse with no validator | Parsed line 2 / line 3 by fixed position, with no guard against shifts | A license header or blank line at the top shifts every field; the generator mis-parses silently | Add a `--validate` mode that asserts every file parses (non-empty title AND description) and exits non-zero NAMING the offender — and show its OUTPUT over the real tree in the plan, not just describe it |
| Bare "python3 is present" assertion | Added `python3 generate_matrix.py` as a CI step asserting the interpreter exists | `python3` is undeclared in Odysseus `pixi.toml`; asserting presence proves nothing | Host the new gate in a job that ALREADY runs bare `python3` on the same runner (`_required.yml` `unit-tests`, which runs `python3 -c "..."` on `ubuntu-latest`) — co-location with a working invocation beats an assertion. Declare `python = ">=3.11"` in `pixi.toml` for the local path. Do NOT rename the pinned-context required job |
| Em-dash topology flag | `HEADER_RE` uses a literal em-dash `—` (U+2014) to detect "— T4 only" topology | Any file using a hyphen `-` or en-dash `–` sets the flag silently wrong; no error is raised | Detecting semantics from an exact glyph is brittle; test the flag against real files (verify the byte with `xxd`) and normalize/allow dash variants, or fail loudly on unexpected glyphs |
| Non-greedy title vs optional group | Title capture `(?P<title>.*?)` is non-greedy before an OPTIONAL `t4` group | On non-T4 lines the title can capture empty/partial; the synthetic test lines were both T4-ish | Non-greedy capture before an optional group needs a test against a REAL non-T4 line, not synthetic happy-path examples |
| Over-broad ID regex | IDs matched with `\b[ABCDE][0-9]{2}\b` anywhere in lines 2–3 | Matches stray tokens like "D08" appearing in prose, inflating counts | Anchor ID extraction to its column/field, not "anywhere in the line" |
| Byte-exact drift diff | CI `--check` compared `current != content` byte-for-byte against the committed README | Trailing-newline / CRLF / locale differences flip the diff; a committed file from an older generator red-flags on the first PR | Normalize or compare structurally, and always generate the committed artifact with the FINAL script in the SAME PR as the gate |
| Circular count verification | Verification step greps for "37 tests, 64 IDs, 8 T4-only" — the same numbers the plan derived by grep | Both sides come from the same `grep`; it passes vacuously | Cross-check the generator's emitted count against an INDEPENDENT enumeration |

## Results & Parameters

### Ground-truth facts (verified this session via real grep/sed/xxd against the Odysseus repo)

| Fact | Value | How it was verified | The trap it defeats |
| ---- | ----- | ------------------- | ------------------- |
| Test files | 37 | `ls e2e/tests/*.sh \| wc -l` | — |
| Unique IDs | 65 | `grep -ohE '\b[ABCDE][0-9]{2}\b' e2e/tests/*.sh \| sort -u \| wc -l` | Non-contiguous ranges → dense reading wrongly gives 64 |
| T4-only files | 7 | `for f in *.sh; do sed -n '2p' "$f" \| grep -q 'T4 only'; done` | `grep -rl 'T4 only'` returns 8 (one runtime string) |
| Description exception | 1 (`subject-routing.sh:3`, no colon) | `for f in *.sh; do sed -n '3p' "$f"; done` | Colon-anchored regex silently drops it |
| Topology dash | em-dash U+2014 | `xxd` on the header line | Hyphen/en-dash sets the flag silently wrong |

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
DESC_RE = re.compile(r"^#\s+\w+:")          # colon-anchored → drops subject-routing.sh:3 which has no colon
```

### Corrected verification commands (paste the OUTPUT, not the claim)

```bash
# Assert 100% parse coverage — generator names and fails on ANY unparsed file:
python3 generate_matrix.py --validate
# Contract inside the generator:
#   bad = [f for f in files if not (title(f) and desc(f))]
#   if bad: sys.exit(f"UNPARSED/INCOMPLETE: {bad}")   # never silently skip

# Positional T4 flag — header line ONLY (→ 7, not the 8 from grep -rl):
for f in e2e/tests/*.sh; do sed -n '2p' "$f" | grep -q 'T4 only' && echo "$f"; done | wc -l

# Independent ID enumeration (→ 65; never assume range density):
grep -ohE '\b[ABCDE][0-9]{2}\b' e2e/tests/*.sh | sort -u | wc -l

# Dump ALL N description lines to surface the no-colon exception:
for f in e2e/tests/*.sh; do printf '%s: ' "$f"; sed -n '3p' "$f"; done

# Structural (not byte-exact) drift gate — normalize trailing newline/CRLF:
python3 generate_matrix.py | git --no-pager diff --no-index --ignore-cr-at-eol - e2e/tests/README.md
```

### Sequencing the committed artifact + drift gate (same PR)

1. Finalize the generator (including `--validate`).
2. Regenerate the committed README with that exact script in the SAME PR.
3. Add the `--check` gate that regenerates and compares structurally.
4. Host the `python3` gate in a job that already runs `python3` (`_required.yml` `unit-tests`); declare `python = ">=3.11"` in `pixi.toml` for the local path. Do not rename the pinned-context required job.

### Expected output of a correct plan

- The plan contains pasted command OUTPUT: `37/37 conform`, `unique IDs = 65`, `T4-only = 7`, the named no-colon offender — not the sentence "verified across all files."
- Counts are corroborated by an INDEPENDENT enumeration, not by the grep that produced them.
- Positional flags are extracted from their exact line; no whole-file `grep -rl` counts a positional flag.
- The committed artifact and the drift gate land together; `--check` is green on the first PR.
- The CI interpreter is proven by co-location with an existing working invocation, not asserted.

## Verified On

| Project | Context | Details |
| --------- | --------- | --------- |
| Odysseus | e2e/tests matrix generator plan for issue #199 — ground-truth facts (37 files, 65 IDs, 7 T4-only, 1 no-colon description, em-dash U+2014) each verified via real `grep`/`sed`/`xxd` this session. An R0 plan that *cited this skill* still earned a NOGO by shipping three falsified facts as prose; the loop converged only after each finding was re-derived against ground truth. Generator + CI not yet executed → `verified-local` | This skill |

## References

- [planning-verify-full-population-not-just-named-entities](planning-verify-full-population-not-just-named-entities.md)
- [planning-verify-assumptions-before-enforcement-gate](planning-verify-assumptions-before-enforcement-gate.md)
- [ci-hygiene-and-validation-gates](ci-hygiene-and-validation-gates.md)
- [ci-matrix-yaml-multiformat-regex-fallback](ci-matrix-yaml-multiformat-regex-fallback.md)
- [doc-comment-count-drift-verify-frozen-test](doc-comment-count-drift-verify-frozen-test.md)
