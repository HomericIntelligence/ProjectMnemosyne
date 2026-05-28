---
name: llm-output-verdict-parse-last-line-not-substring
description: "Parse discrete LLM-emitted verdicts (APPROVED/REVISE/BLOCK, GO/NOGO, SAFE/UNSAFE) using last-line regex extraction, not substring `in` checks. Use when: (1) adding a Python/shell consumer that reads a classification marker from LLM output, (2) the prompt instructs the LLM that 'readers take the LAST matching line', (3) the LLM may discuss multiple options before settling on a verdict, (4) a substring-in check would fire on quoted/discussed markers, (5) auditing an existing parser for false-positive verdict reads, (6) a reviewer comment exists but its verdict is never parsed — causing the pipeline to re-review the same issue every pass forever (#615 infinite loop), (7) diagnosing a re-review loop where the log gives no clue what the reviewer wrote."
category: architecture
date: 2026-05-28
version: "1.1.0"
user-invocable: false
verification: verified-ci
history: llm-output-verdict-parse-last-line-not-substring.history
tags:
  - llm-output-parsing
  - verdict-gate
  - regex
  - last-line-wins
  - claude-output
  - prompt-parser-contract
  - false-positive
  - substring-vs-regex
  - bounded-retry
  - infinite-loop
  - observability
---

# LLM Output Verdict Parse: Last-Line Regex, Not Substring

## Overview

| Field | Value |
|-------|-------|
| **Date** | 2026-05-28 |
| **Objective** | Prevent false-positive verdict reads when a Python/shell consumer parses a discrete classification marker (`**Verdict: APPROVED**` etc.) from LLM output. Also prevent the complementary infinite-re-review loop when the verdict is malformed and never parseable. |
| **Outcome** | SUCCESS — regex fix shipped in PR #552; bounded-retry cap + WARNING diagnostic logging shipped in PR #670 (Issues #615/#616). 53-pass infinite loop for issues #455/#468/#484 eliminated. |
| **Verification** | verified-ci — PR #670 passed all pre-commit hooks and CI. |
| **History** | [changelog](./llm-output-verdict-parse-last-line-not-substring.history) |

## When to Use

- You are adding a Python or shell consumer that reads a classification marker (verdict, severity, action, command) from LLM output.
- The prompt that generated the output explicitly says "readers take only the LAST matching line" (or equivalent).
- The LLM is permitted to discuss multiple options before settling — multiple matching markers may legitimately appear.
- A substring `in` check would fire on a quoted/discussed marker.
- You are auditing an existing parser (skip-gate, finalize-gate, ship-gate) for false-positive reads.
- **A plan-review loop re-reviews the same issue every pass without ever terminating** — symptom of a malformed verdict that regex cannot parse.
- **The pipeline log gives no clue what the reviewer wrote** — only says "verdict is None" or "not APPROVED" at DEBUG level.

## Verified Workflow

### Quick Reference

```python
import re

# Anchored to start/end of line; MULTILINE so ^/$ match line boundaries.
# Strict anchoring is intentional (#551/#552) — do NOT loosen to avoid substring false-positives.
_VERDICT_PATTERN = re.compile(
    r'^\*\*Verdict: (APPROVED|REVISE|BLOCK)\*\*\s*$',
    re.MULTILINE,
)

def is_approved(body: str) -> bool:
    """Return True iff the LAST verdict line in `body` is APPROVED."""
    matches = _VERDICT_PATTERN.findall(body)
    return bool(matches) and matches[-1] == "APPROVED"


# --- BOUNDED RETRY CAP (#615) ---
MAX_UNPARSEABLE_VERDICT_PASSES: int = 3

def count_unparseable_verdict_passes(comments: list[dict]) -> int:
    """Count plan-review comments that have no parseable verdict line."""
    return sum(
        1 for c in comments
        if c.get("body", "").startswith(PLAN_REVIEW_PREFIX)
        and _VERDICT_PATTERN.findall(c.get("body", "")) == []
    )

def exceeds_unparseable_verdict_cap(
    comments: list[dict],
    cap: int = MAX_UNPARSEABLE_VERDICT_PASSES,
) -> bool:
    """Return True when malformed-verdict re-review has hit the cap."""
    return count_unparseable_verdict_passes(comments) >= cap


# --- DIAGNOSTIC LOGGING (#615) ---
# In is_plan_review_approved(), when verdict is None emit WARNING not DEBUG:
if verdict is None:
    first_line = latest_review_body.split("\n", 1)[0].strip()
    url_part = latest_review_url or "<no url>"
    logger.warning(
        "Issue %s: plan-review comment has no parseable verdict line "
        "(VERDICT_LINE_RE did not match) — first line: %r | url: %s",
        issue_ref(issue_number),
        first_line[:200],
        url_part,
    )
```

Three guarantees the regex provides that `MARKER in body` does not:

1. **Line-anchored**: the marker must occupy its own line (modulo trailing whitespace) — quoted/inline mentions cannot trigger.
2. **Last-match wins**: early APPROVED then later BLOCK → BLOCK wins.
3. **Strict token equality**: `matches[-1] == "APPROVED"` rejects look-alikes like `APPROVED_WITH_CHANGES`.

### Detailed Steps

1. **Read the prompt template used to generate the LLM output.** Find the explicit "format" instruction. Example from `hephaestus/automation/prompts.py:474-475`: *"End your response with exactly one of the following verdict lines … readers take only the LAST matching line."*

2. **Match the prompt's stated semantics in the parser.**

   | Prompt instruction | Correct parser |
   |---|---|
   | "last matching line wins" | `re.findall(pattern, text, re.MULTILINE)[-1]` |
   | "exactly one verdict at the end" | `text.strip().splitlines()[-1]` plus format assertion |
   | "JSON block at end" | `re.findall(r'```json\n(.*?)\n```', text, re.DOTALL)[-1]` then `json.loads` |
   | "verdict on its own line, anywhere" + "if multiple, treat as error" | `findall` then assert `len(matches) == 1` |

3. **Add bounded-retry guard** when the consumer is in a loop that re-requests reviews:

   ```python
   # Before requesting another review cycle:
   if exceeds_unparseable_verdict_cap(comments):
       logger.error(
           "Issue %s: %d malformed-verdict passes — skipping re-review, needs human",
           issue_ref(issue_number), count_unparseable_verdict_passes(comments),
       )
       return  # surface for human attention instead of looping forever
   ```

4. **Log at WARNING (not DEBUG)** when verdict is None. Include the **first line of the offending comment body** and its **URL**. Without this, a malformed verdict is indistinguishable from "no review comment yet" in the logs, making the loop invisible for days.

5. **Add tests covering at minimum:**

   - Single matching line at end of body → correct verdict.
   - Multiple lines (early APPROVED, late BLOCK) → last wins (BLOCK).
   - Quoted/inline marker → NOT triggered.
   - Marker with trailing whitespace/CRLF → still matches.
   - Malformed body (no matching line) → None, does not raise.
   - `count_unparseable_verdict_passes` counts only review comments with no parseable verdict.
   - `exceeds_unparseable_verdict_cap` returns True at threshold, False below.
   - `exceeds_unparseable_verdict_cap` with custom cap works.

6. **Co-locate the prompt and the parser** in a single review. The defect shipped because the prompt lived in `prompts.py` and the parser in `plan_reviewer.py`, touched in separate PRs.

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
|---|---|---|---|
| 1 | `if "APPROVED" in text:` (substring `in` check, originating defect in `plan_reviewer.py:342`) | Matches the substring anywhere — quoted markers, "NOT APPROVED" prose, early APPROVED overridden by BLOCK all return True. Violates the prompt's "last matching line wins" contract. | Substring `in` against an LLM body cannot enforce line position or last-match semantics — never use it for discrete classification markers. |
| 2 | `if text.endswith("APPROVED"):` | Brittle. Claude may emit trailing whitespace, a postscript, markdown emphasis after the verdict. Returns False when verdict is APPROVED. | `endswith` assumes literal trailing position, which Claude's free-form formatting breaks routinely. |
| 3 | `text.split("\n")[-1] == "APPROVED"` | Assumes the verdict is the literal last line. Breaks when Claude adds a postscript. | "Last line of body" ≠ "last matching line of body". Filter for matching lines first, then take the last. |
| 4 | `re.search(r"APPROVED", text)` | Identical false-positive surface to substring `in` — no line anchoring, no last-match semantics. | A regex without anchors, without `re.MULTILINE`, using `search` not `findall(...)[-1]` provides zero additional safety over `in`. The flags matter as much as the pattern. |
| 5 | Log malformed verdict at DEBUG level | When verdict returned None, only DEBUG log emitted — no clue what the reviewer wrote; loop ran 12+ times per issue unseen | Malformed verdict is an actionable operator alert: log at WARNING with first line of offending comment body + URL. |
| 6 | No retry cap on malformed verdicts | Loop called re-review every pass when verdict was None | Same issues re-reviewed 12× across loops 2–5 (#455/#468/#484). Add `count_unparseable_verdict_passes()` + `exceeds_unparseable_verdict_cap()` with cap=3. |
| 7 | Loosen the strict regex to catch more variants | Considered removing `^...$` anchoring to tolerate whitespace/markdown decorators | Strict anchoring is intentional — it prevents the false-positive substring matches that caused #551/#552. NEVER loosen VERDICT_LINE_RE; fix the LLM prompt output instead. |

## Results & Parameters

**Recommended regex (Python):**

```python
re.compile(r'^\*\*Verdict: (APPROVED|REVISE|BLOCK)\*\*\s*$', re.MULTILINE)
```

**Recommended consumer logic:**

```python
matches = _VERDICT_PATTERN.findall(body)
verdict = matches[-1] if matches else None
is_approved = verdict == "APPROVED"
```

**Bounded-retry constants:**

```python
MAX_UNPARSEABLE_VERDICT_PASSES: int = 3  # surface for human after 3 failed parses
```

**Cross-language equivalents:**

| Language | Pattern | Notes |
|---|---|---|
| Python | `re.compile(r'^\*\*Verdict: (APPROVED\|REVISE\|BLOCK)\*\*\s*$', re.MULTILINE)` | Use `findall(...)[-1]`. |
| JavaScript / TypeScript | `/^\*\*Verdict: (APPROVED\|REVISE\|BLOCK)\*\*\s*$/gm` | Use `[...body.matchAll(re)].at(-1)?.[1]`. |
| Go | `regexp.MustCompile("(?m)^\*\*Verdict: (APPROVED\|REVISE\|BLOCK)\*\*\s*$")` | `FindAllStringSubmatch(body, -1)`; take last element. |
| Rust | `Regex::new(r"(?m)^\*\*Verdict: (APPROVED\|REVISE\|BLOCK)\*\*\s*$")?` | `captures_iter(body).last()`. |
| Bash | `grep -E '^\*\*Verdict: (APPROVED\|REVISE\|BLOCK)\*\*\s*$' \| tail -1` | Pipe through `tail -1` to enforce last-match-wins. |

**Required test cases (minimum):**

1. `body = "**Verdict: APPROVED**\n"` → APPROVED.
2. `body = "**Verdict: APPROVED**\n\nOn reflection…\n\n**Verdict: BLOCK**\n"` → BLOCK (last-match-wins).
3. `body = "we should NOT mark this **Verdict: APPROVED** because…\n**Verdict: REVISE**\n"` → REVISE (inline marker not line-anchored).
4. `body = "**Verdict: APPROVED**   \r\n"` → APPROVED (trailing whitespace / CRLF tolerated).
5. `body = "No verdict here."` → None / False.
6. `body = ""` → None / False.
7. 3 review comments with no parseable verdict → `count_unparseable_verdict_passes == 3`, `exceeds_cap True`.

**Cross-reference these related skills:**

- `automation-graphql-batch-comment-fetch` — batch fetching comments for N issues in one GraphQL call, shipped alongside #615 fix.

## Verified On

| Project | File / Issue | Notes |
|---|---|---|
| ProjectHephaestus | `hephaestus/automation/review_state.py` | `VERDICT_LINE_RE`, `count_unparseable_verdict_passes`, `exceeds_unparseable_verdict_cap`, WARNING logging |
| ProjectHephaestus | Issues #615, #616 / PR #670 | Bounded-retry cap + WARNING diagnostic logging |
| ProjectHephaestus | `hephaestus/automation/prompts.py:474-475` | Prompt source — explicit "readers take only the LAST matching line" instruction. |
| ProjectHephaestus | `hephaestus/automation/plan_reviewer.py:342` | Originating defect — `_FINAL_VERDICT_MARKER in latest_review_body`. Fixed in #552. |
| ProjectHephaestus | Issue #552 (epic #550) | Originating issue under the 1.0 audit remediation epic. |
