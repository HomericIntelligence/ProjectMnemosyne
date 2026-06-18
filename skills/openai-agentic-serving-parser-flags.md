---
name: openai-agentic-serving-parser-flags
description: "Configure OpenAI-compatible serving engines for agentic tool use. Use when: (1) vLLM or SGLang serves a model family that requires an explicit parser, (2) a client uses automatic tool choice, (3) errors mention --enable-auto-tool-choice or --tool-call-parser."
category: tooling
date: 2026-06-18
version: "1.0.1"
user-invocable: false
verification: verified-ci
tags: [openai-compatible, agentic, serving, vllm, sglang, tool-calling, parser-flags]
---

# OpenAI Agentic Serving Parser Flags

## Overview

| Field | Value |
|-------|-------|
| **Date** | 2026-06-18 |
| **Objective** | Make OpenAI-compatible serving surfaces work with clients that request automatic tool choice when the model family requires an explicit parser. |
| **Outcome** | Successful. Parser and tool-call flags are emitted from generated launch configuration, with vLLM also enabling automatic tool choice. |
| **Verification** | verified-ci |

## When to Use

- A vLLM or SGLang model surface fails an agentic client that requests automatic tool choice.
- The client error says `"auto" tool choice requires --enable-auto-tool-choice and --tool-call-parser to be set`.
- Adding or reviewing generated manifests, multi-model launcher defaults, or service command args for a model family with custom parser requirements.
- Auditing production versus experimental serving surfaces for parser flags before exposing tool use.

## Verified Workflow

### Quick Reference

```bash
# Replace family_parser with the parser name supported by the serving engine.
PARSER_NAME="${PARSER_NAME:-family_parser}"

# vLLM agentic surface.
python -m vllm.entrypoints.openai.api_server \
  --model "$MODEL_PATH" \
  --served-model-name "$MODEL_ID" \
  --enable-auto-tool-choice \
  --reasoning-parser "$PARSER_NAME" \
  --tool-call-parser "$PARSER_NAME"

# SGLang surface when parser flags are available.
python -m sglang.launch_server \
  --model-path "$MODEL_PATH" \
  --served-model-name "$MODEL_ID" \
  --reasoning-parser "$PARSER_NAME" \
  --tool-call-parser "$PARSER_NAME"

# Launcher defaults should keep ad hoc launches aligned with generated manifests.
REASONING_PARSER="${REASONING_PARSER:-$PARSER_NAME}"
TOOL_CALL_PARSER="${TOOL_CALL_PARSER:-$PARSER_NAME}"
```

### Detailed Steps

1. Treat agentic serving as an explicit parser configuration problem, not as a generic OpenAI route issue.
2. Identify the parser name supported by the serving engine for the model family.
3. For vLLM surfaces, include all three flags: `--enable-auto-tool-choice`, `--reasoning-parser "$PARSER_NAME"`, and `--tool-call-parser "$PARSER_NAME"`.
4. For SGLang surfaces that support parser flags, include `--reasoning-parser "$PARSER_NAME"` and `--tool-call-parser "$PARSER_NAME"`.
5. In manifest generators, emit parser flags from the manifest source of truth rather than hand-patching service commands.
6. In launchers, default `REASONING_PARSER` and `TOOL_CALL_PARSER` to the parser name for that model family so ad hoc launches match generated manifests.
7. Add focused regression tests around generated manifests and launcher text before relying on full validation or CI.

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
|---------|----------------|---------------|----------------|
| Agentic client with automatic tool choice but no parser flags | Ran an OpenAI-compatible client using `"auto"` tool choice against the model surface | vLLM returned `Error: "auto" tool choice requires --enable-auto-tool-choice and --tool-call-parser to be set` | Tool use must be enabled at engine launch, not only at the client or route layer |
| Set only a reasoning parser | Added reasoning support but no tool-call parser | Auto tool choice still lacked the parser vLLM needs to interpret tool calls | Reasoning and tool-call parsing are separate serving concerns and both must be configured |
| Set parser flags without vLLM auto tool choice | Included parser selection but omitted `--enable-auto-tool-choice` | vLLM still rejected requests that ask for automatic tool choice | vLLM requires the explicit auto-tool-choice gate in addition to parser selection |
| Hand-patch one service command | Fixed a single launch path manually | Generated manifests and multi-model launches can drift back to missing flags | Put the rule in the manifest generator and launcher defaults, then cover both with tests |

## Results & Parameters

Durable rule for vLLM:

```text
--enable-auto-tool-choice
--reasoning-parser <parser-name>
--tool-call-parser <parser-name>
```

Durable rule for SGLang when parser flags are supported:

```text
--reasoning-parser <parser-name>
--tool-call-parser <parser-name>
```

Implementation points verified in the source repository:

```text
manifest generator
  Emits vLLM parser flags, including --enable-auto-tool-choice,
  --reasoning-parser, and --tool-call-parser.

multi-model launcher
  Defaults REASONING_PARSER to the model-family parser.
  Defaults TOOL_CALL_PARSER to the model-family parser.
  Includes --enable-auto-tool-choice in the vLLM command path.
```

Verification evidence:

```text
Focused tests passed.
Full local validation passed.
Source-repository CI passed.
Verification level: verified-ci.
```

## Verified On

| Project | Context | Details |
|---------|---------|---------|
| LLM360/Inference360 | Agentic parser flags for H200 Slurm model-family serving surfaces | OpenAI-compatible client failure fixed by vLLM/SGLang parser flags, focused tests passed, full local validation passed, CI passed |
