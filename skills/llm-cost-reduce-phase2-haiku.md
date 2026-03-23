---
name: llm-cost-reduce-phase2-haiku
description: "How to audit Claude API token usage in a FastAPI grading pipeline, eliminate essay re-sends between sequential LLM calls, and route a lightweight generation phase to Haiku for ~37% cost reduction. Use when: (1) auditing LLM API costs for a multi-phase Claude pipeline, (2) optimizing token consumption in sequential instructor calls, (3) configuring per-call model routing in pydantic-settings."
category: optimization
date: 2026-03-23
version: "1.0.0"
user-invocable: false
tags: [anthropic, claude, instructor, cost-optimization, haiku, token-tracking, fastapi, pydantic-settings]
---

# LLM Cost Reduction: Phase 2 Haiku + Essay Re-Send Elimination

## Overview

| Field | Value |
|-------|-------|
| **Date** | 2026-03-23 |
| **Objective** | Audit Claude API token usage in a FastAPI essay-grading pipeline and reduce cost per student by ~37% |
| **Outcome** | Successful — Phase 2 essay re-send eliminated, Haiku configured for Phase 2, token counts logged per student result |

## When to Use

- You have a multi-phase Claude pipeline where Phase 2 receives the same large input (e.g. essay text) already processed by Phase 1
- You want per-call token usage logged to a database for cost attribution and anomaly detection
- You need to route a lightweight generation task (short comment writing) to a cheaper model without changing the main grading model
- You are using `instructor` with Anthropic and need to capture raw `usage` from structured output calls

## Verified Workflow

### Quick Reference

```python
# Capture token usage with instructor (create_with_completion instead of create)
result, completion = client.chat.completions.create_with_completion(
    model=model,
    max_tokens=1024,
    system=system_prompt,
    messages=[{"role": "user", "content": user_message}],
    response_model=MyOutputSchema,
)
input_tokens = completion.usage.input_tokens
output_tokens = completion.usage.output_tokens

# Phase 2: build from Phase 1 output only — don't re-send the full document
section_lines = "\n".join(
    f"  [{s.section_id}] {s.score}/{s.max_points}: {s.feedback}"
    for s in phase1.sections
)
# Phase 1 feedback already contains direct essay quotes — no need to re-send essay_text
```

```python
# pydantic-settings: separate model per pipeline phase
claude_model: str = "claude-sonnet-4-6"                    # Phase 1 (complex grading)
claude_phase2_model: str = "claude-haiku-4-5-20251001"     # Phase 2 (short comments)
```

```python
# grade_student() — return token usage as third element
def grade_student(...) -> tuple[Phase1Output, Phase2Output, dict]:
    ...
    usage = {"input_tokens": p1_in + p2_in, "output_tokens": p1_out + p2_out}
    return phase1, phase2, usage
```

```sql
-- Migration: add token columns to student_results
ALTER TABLE student_results ADD COLUMN llm_input_tokens INTEGER;
ALTER TABLE student_results ADD COLUMN llm_output_tokens INTEGER;
```

### Detailed Steps

1. **Audit all Claude API calls** — find every `client.chat.completions.create()` call, note system prompt sizes, what's in the user message, and whether large content (essay text) is re-sent across phases.

2. **Identify re-sends** — in sequential Phase 1 → Phase 2 pipelines, Phase 2 often re-sends the full source document even though Phase 1 already extracted structured feedback. Remove the document from Phase 2's user message; use Phase 1's `sections[].feedback` strings instead (they contain direct quotes).

3. **Switch to `create_with_completion()`** — instructor's `create()` returns only the parsed model. `create_with_completion()` returns `(parsed_model, raw_completion)` where `raw_completion.usage.input_tokens` and `.output_tokens` are available.

4. **Update return type** — change the orchestrating function to return a 3-tuple `(Phase1Output, Phase2Output, dict)` with combined token counts. Update all callers to unpack accordingly.

5. **Add DB columns** — add `llm_input_tokens` and `llm_output_tokens` (nullable Integer) to the result model and migration. Store from the returned usage dict in the worker.

6. **Add `claude_phase2_model` config setting** — default to Haiku (`claude-haiku-4-5-20251001`) for the lightweight comment-generation phase. Pass via env var (`CLAUDE_PHASE2_MODEL`) to override. Both models share the same `ANTHROPIC_API_KEY`.

7. **Log token counts** — include `[tokens: in=%d out=%d]` in existing log lines for each phase so costs are visible in logs without a DB query.

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
|---------|----------------|---------------|----------------|
| Attempt 1 | Used `client.chat.completions.create()` and tried to access `.usage` on result | `create()` returns only the parsed Pydantic model, not the raw completion — no `.usage` attribute | Use `create_with_completion()` which returns `(model, raw_completion)` tuple |
| Attempt 2 | Considered passing essay text to Phase 2 as truncated excerpt | Truncation introduces risk of missing context and adds prompt engineering complexity | Phase 1 `sections[].feedback` already contains direct essay quotes — use those, no truncation needed |

## Results & Parameters

### Cost estimates (claude-sonnet-4-6: $3/MTok in, $15/MTok out)

| Essay Length | Words | Before (per student) | After (per student) | Savings |
|---|---|---|---|---|
| Short response | 500 | ~$0.028 | ~$0.018 | 36% |
| Standard essay (3–5 pages) | 1,500 | ~$0.038 | ~$0.024 | 37% |
| Research paper (8–10 pages) | 2,500 | ~$0.047 | ~$0.030 | 36% |

### Monthly impact (typical teacher: 5 classes × 30 students, 3 assignments/month = 450 essays)

| Metric | Value |
|---|---|
| Before | ~$17.10/month |
| After | ~$10.80/month |
| Monthly savings | ~$6.30 (~37%) |
| Annual savings | ~$57 per teacher |

### Key config values

```python
# app/config.py
claude_model: str = "claude-sonnet-4-6"
claude_phase2_model: str = "claude-haiku-4-5-20251001"

# Railway env var to revert Phase 2 to Sonnet if quality issues arise:
# CLAUDE_PHASE2_MODEL=claude-sonnet-4-6
```

### Token logging pattern

```python
# In worker, after grade_student() call:
student_result.llm_input_tokens = llm_usage.get("input_tokens")
student_result.llm_output_tokens = llm_usage.get("output_tokens")
```

## Verified On

| Project | Context | Details |
|---------|---------|---------|
| teachwithcolin | FastAPI essay grading SaaS, Railway deployment | instructor 1.x + anthropic SDK, ARQ worker, SQLAlchemy 2.0 async |
