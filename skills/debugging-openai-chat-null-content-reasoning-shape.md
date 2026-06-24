---
name: debugging-openai-chat-null-content-reasoning-shape
description: "Debug OpenAI-compatible chat responses that return null content while exposing reasoning fields. Use when: (1) chat completions return HTTP 200 but no user-visible answer, (2) parser/template behavior may route generated text into reasoning fields, (3) controls are needed to distinguish endpoint health from response-shape bugs."
category: debugging
date: 2026-06-24
version: "1.0.0"
user-invocable: false
verification: verified-local
tags: [openai-compatible, chat-completions, response-shape, reasoning-fields, serving-debugging, redacted]
---

# OpenAI Chat Null Content Reasoning Shape

## Overview

| Field | Value |
|-------|-------|
| **Date** | 2026-06-24 |
| **Objective** | Diagnose OpenAI-compatible chat completions that return successful HTTP envelopes with `message.content: null` while generated text appears in reasoning-style fields. |
| **Outcome** | Successful. A generic response-shape debugging workflow isolates the bug to chat-template / parser / response-normalization behavior without preserving model-specific or infrastructure-specific details. |
| **Verification** | verified-local - workflow executed during an internal endpoint investigation; CI validation pending for any implementation fixes. |

## When to Use

- An OpenAI-compatible `/v1/chat/completions` endpoint returns HTTP 200 but `choices[].message.content` is `null`.
- The raw response includes fields such as `reasoning`, `reasoning_content`, `thinking`, or equivalent non-user-facing text.
- Clients see no assistant answer even though server logs record successful completions.
- You need to distinguish endpoint availability, model-specific behavior, parser configuration, chat-template behavior, and response-normalization bugs.
- You need to write a durable issue or report while redacting model names, endpoints, job identifiers, paths, and other internal details.

## Verified Workflow

### Quick Reference

```bash
# 1. Probe health and model listing.
curl -fsS <endpoint>/health
curl -fsS <endpoint>/v1/models

# 2. Send a minimal chat request and inspect the raw response shape.
curl -fsS <endpoint>/v1/chat/completions \
  -H 'Content-Type: application/json' \
  -d @/tmp/chat-request.json

# 3. Compare against a legacy text-completion path if available.
curl -fsS <endpoint>/v1/completions \
  -H 'Content-Type: application/json' \
  -d @/tmp/completion-request.json

# 4. Search launch/runtime config for parser and auto-tool flags.
rg -n "reasoning-parser|tool-call-parser|enable-auto-tool-choice|chat_template|reasoning_effort" <repo-or-log-root>
```

### Detailed Steps

1. **Start with the raw JSON response.** Record whether `choices[].message.content` is `null`, whether `tool_calls` or `refusal` is populated, and whether reasoning-style fields contain text.
2. **Classify the failure as semantic, not transport, when HTTP is 200.** A successful status code plus unusable `message.content` is still a user-facing API failure.
3. **Run a single-request reproducer before testing parallelism.** If a single request fails, parallelism is not the root cause. Parallel batches are still useful to show blast radius under concurrency.
4. **Compare chat versus text completions.** If `/v1/completions` returns non-null text while `/v1/chat/completions` returns null content, focus on chat template and response parser behavior.
5. **Inspect parser and tool-call launch flags.** Look for reasoning-parser, tool-call-parser, automatic tool-choice, or equivalent response parser settings.
6. **Inspect the chat template.** Determine whether assistant generation begins inside a thinking/reasoning segment and whether an explicit non-reasoning mode exists.
7. **Try request-level controls without overclaiming.** Test supported reasoning-effort levels, template kwargs, low token budgets, and higher token budgets. Record what changes and what does not.
8. **Use non-sensitive controls.** Compare against a known-good OpenAI-compatible endpoint only to establish whether the malformed response shape is general or specific to one serving path.
9. **Write the finding in final-report form.** Include response shape, endpoint class, control result, parser/template evidence, likely failure chain, and acceptance criteria. Redact all internal identifiers.

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
|---------|----------------|---------------|----------------|
| Treating HTTP 200 as success | Endpoint health and server logs showed successful requests | The chat response envelope was syntactically successful but semantically unusable because `message.content` was null and no supported alternative was populated | Validate response shape, not just transport status |
| Assuming concurrency caused the bug | Parallel probes reproduced the malformed shape | Single-request probes reproduced the same response shape, so parallelism was not required | Always establish a single-request baseline before attributing failures to concurrency |
| Increasing token budget as a fix | Larger token budgets were tested | Some simple prompts may eventually produce final content, but realistic prompts can still remain reasoning-only | Token budget can affect symptoms but is not a reliable mitigation |
| Sending unsupported reasoning controls | Tried a non-supported off value for reasoning effort | The server rejected the request because only supported values are accepted | Inspect template/runtime support before assuming an off switch exists |
| Copying raw operational evidence into durable notes | Raw logs and payloads contained internal identifiers | Durable skills should teach the method, not preserve environment details | Use placeholders for endpoints, model IDs, paths, jobs, hosts, and service names |

## Results & Parameters

### Malformed Chat Response Shape

```json
{
  "choices": [
    {
      "message": {
        "role": "assistant",
        "content": null,
        "reasoning": "<present>",
        "reasoning_content": "<present>",
        "tool_calls": []
      },
      "finish_reason": "<stop-or-length>"
    }
  ]
}
```

### Evidence To Capture

| Evidence | What to Record | Redaction Rule |
|----------|----------------|----------------|
| Raw response shape | `content`, `tool_calls`, `refusal`, reasoning-style fields, `finish_reason`, token counts | Redact prompt text and generated reasoning unless the user explicitly approves a truncated excerpt |
| Endpoint coverage | Number and class of affected endpoints | Use `<endpoint-a>`, `<endpoint-b>`, or generic model classes instead of model IDs/IPs |
| Control coverage | Whether comparable endpoints return non-null content | Avoid naming model families unless needed and approved |
| Runtime config | Parser flags, tool-call flags, template behavior | Preserve flag names; redact service names, paths, jobs, and hosts |
| Logs | HTTP status and absence/presence of server errors | Redact client IPs, hostnames, process IDs, and job IDs |

### Likely Failure Chain Template

```text
The chat template starts assistant generation inside a reasoning/thinking segment.
The serving parser maps text in that segment to reasoning-style fields.
If generation stops before a final-content segment appears, the OpenAI-compatible
response can return HTTP 200 with message.content: null.
The gateway/client sees a successful response envelope with no user-visible answer.
```

### Acceptance Criteria Template

- Successful chat completions must not return `message.content: null` unless a supported alternative is populated, such as non-empty tool calls or an explicit refusal.
- Reasoning-style fields must be stripped, disabled, or gated behind an explicit debug/reasoning mode for ordinary user-facing chat traffic.
- Semantic response-shape failures must be counted in monitoring or validation, not treated as successful assistant answers.
- Regression fixtures should cover both `finish_reason: stop` and `finish_reason: length` with null content and populated reasoning fields.
- Regression fixtures should also cover reasoning followed by valid final content so normalization does not discard the user-visible answer.

## Verified On

| Project | Context | Details |
|---------|---------|---------|
| Internal inference service | OpenAI-compatible chat response investigation | Sanitized workflow only; no model IDs, endpoints, paths, jobs, or raw proprietary payloads retained |
