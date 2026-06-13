---
name: mcp-config-deliberate-absence-posture
description: "How to respond to a repo audit finding of 'no MCP server configuration'. Use when: (1) an audit reports a missing .mcp.json / mcpServers key, (2) deciding whether to add live MCP servers vs an empty placeholder, (3) distinguishing Claude Code plugin marketplaces from MCP servers. Recommends a TRACKED .mcp.json with empty mcpServers:{} — NOT a git-ignored file or a .example twin."
category: tooling
date: 2026-06-12
version: "2.0.0"
user-invocable: false
verification: unverified
history: mcp-config-deliberate-absence-posture.history
tags: [mcp, claude-code, config, audit, documentation, mcp-json]
---

# MCP Config: Deliberate-Absence Posture

**History:** [changelog](./mcp-config-deliberate-absence-posture.history)

## Overview

| Field | Value |
|-------|-------|
| **Date** | 2026-06-12 |
| **Objective** | Decide the correct response to a repo audit finding of "no MCP server configuration / missing `.mcp.json` / no `mcpServers`" without breaking Claude Code tool startup. |
| **Outcome** | Ship a **tracked, project-scoped `.mcp.json` with an empty `{"mcpServers": {}}` map** — the canonical, version-controlled, non-breaking shape per the official Claude Code MCP docs. Do NOT git-ignore the file and do NOT add a parallel `.mcp.example.json` twin. |
| **Verification** | `unverified` — planning learning from ProjectHephaestus issue #1186. The MCP *behaviour facts* are quoted from the official Claude Code docs; the repo edits are GO-pending, not implemented or merged. |

### Key Insight

- The official Claude Code MCP docs say a project-scoped `.mcp.json` **"is
  designed to be checked into version control, ensuring all team members have
  access to the same MCP tools and services."** The tracked file IS the shareable
  mechanism — a parallel `.mcp.example.json` is redundant and inverts the
  documented convention.
- An empty `{"mcpServers": {}}` is a valid, canonical, inert shape that satisfies
  an audit's "mcpServers key exists" requirement while starting zero servers.
- "MCP-style integration" references in an ecosystem are frequently Claude Code
  **plugin marketplaces** (a different mechanism, e.g. the Mnemosyne marketplace)
  or NATS/HTTP-REST integrations — NOT MCP servers. Verify the mechanism before
  wiring anything.

## When to Use

- An audit (e.g. `repo-analyze`) reports a missing `.mcp.json` or absent `mcpServers` key.
- You are deciding whether to add live MCP server entries vs. an empty placeholder.
- You need to distinguish a Claude Code plugin marketplace from an MCP server before wiring anything.
- A repo references an "MCP-style integration" and you must confirm the actual mechanism.

## Verified Workflow

> **Warning:** This is a planning-derived workflow, not executed end-to-end. The
> MCP *behaviour facts* below are quoted from the official Claude Code docs; the
> repo edits themselves are unverified until CI confirms.

### Quick Reference

```text
1. grep repo for `mcpServers` — zero real hits => no MCP usage today (false gap).
2. Identify the REAL substrate (plugin marketplace / NATS / HTTP REST). None is MCP.
3. Create a TRACKED `.mcp.json` at repo root: {"mcpServers": {}}.
4. Document the posture (runbook + AGENTS-style doc): non-blocking + approval-gated.
5. Add a structural regression test (exists + valid JSON + mcpServers is a dict).
   Do NOT assert the map is empty.
6. Keep every fenced code block at top document level (markdownlint MD031).

Rule of thumb: ship a TRACKED `.mcp.json` with an empty map — never git-ignore it,
never add a `.mcp.example.json` twin.
```

### Core facts (doc-verified)

These are the durable, official-doc-verified learnings (code.claude.com/docs/en/mcp):

1. Project-scoped `.mcp.json` **"is designed to be checked into version control,
   ensuring all team members have access to the same MCP tools and services."** →
   ship it TRACKED; do NOT git-ignore it; do NOT add a parallel
   `.mcp.example.json` (redundant — the tracked file IS the shareable mechanism).
2. **"MCP startup is … non-blocking by default"**; unreachable servers **"continue
   to connect in the background."** Only a server with `alwaysLoad: true` blocks
   startup, capped at a 5-second connect timeout.
3. **"Claude Code prompts for approval before using project-scoped servers from
   `.mcp.json`."** → an unreachable/unknown server is approval-gated, NOT
   silently-breaking.
4. An empty `{"mcpServers": {}}` is a valid, canonical, inert shape that satisfies
   an audit's "mcpServers key exists" requirement while starting zero servers.
5. "MCP-style integration" references are frequently Claude Code **plugin
   marketplaces** (a different mechanism) or NATS/HTTP-REST integrations — NOT MCP
   servers. Verify the mechanism before wiring.

### Detailed steps

1. `grep` the repo for `mcpServers`. If there are zero real hits (only
   audit-checklist prose), there is no MCP usage today.
2. Identify the real integration substrate (plugin marketplaces, NATS, HTTP REST).
   None of these is MCP.
3. Create a **TRACKED** `.mcp.json` at repo root containing `{"mcpServers": {}}`.
4. Document the posture in a runbook + AGENTS-style doc; explain non-blocking +
   approval-gated startup so future contributors know that adding a server is safe.
5. Add a structural regression test: `.mcp.json` exists + valid JSON + `mcpServers`
   is a dict; every declared server has a string `command` or `url`. Do NOT assert
   the map is empty (so adding a real server later needs no test edit).
6. When writing the runbook, keep every fenced code block at the **top document
   level** with blank lines around it — never nest a fence inside a
   numbered/bulleted list item (markdownlint MD031 is commonly enabled via
   `default: true` and is a PR-blocking gate).

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
|---------|----------------|---------------|----------------|
| Git-ignored file + `.example` twin | Git-ignore `.mcp.json` and ship a parallel `.mcp.example.json` template | Inverts the documented convention that project `.mcp.json` is checked into version control for team sharing; the `.example` twin is redundant | Ship the tracked `.mcp.json` directly with an empty map. |
| "Breaks startup" justification | Justify the `.example` approach with "an active `.mcp.json` with unreachable commands breaks tool startup" | False per docs — MCP startup is non-blocking by default; unreachable servers connect in the background and are approval-gated | Verify runtime behaviour against official docs before using it as a design premise. |
| Trust the audit's vocabulary | Assume the audit's "MCP-style integration" reference means an MCP server | It was a Claude Code plugin marketplace (Mnemosyne), a different mechanism | Distinguish marketplaces / NATS / REST from MCP before wiring. |
| Fence nested in a list | Nest a ```json fence inside a numbered list in the runbook | markdownlint MD031 (blanks-around-fences) is live under `default: true` and blocks the PR | Keep fences top-level with surrounding blank lines. |

## Results & Parameters

**Verified on:** ProjectHephaestus issue #1186 planning session — R0 plan (NOGO,
wrong premises) corrected to R1 plan after fetching the official Claude Code MCP
docs. Verification level: `unverified`.

### Canonical config

The canonical empty, inert, audit-satisfying shape:

```json
{"mcpServers": {}}
```

### Reviewer-risk / unverified items

These are the highest-value durable content — capture and re-confirm before relying on them.

- The MCP *behaviour facts* are doc-quoted and trustworthy; the repo **EDITS** are
  unverified until CI.
- **markdownlint MD031** status is repo-specific — always check the repo's
  `.markdownlint.*` for whether MD031 is overridden before nesting fences.
- The regression test's repo-root resolution
  (`Path(__file__).resolve().parents[N]`) depends on test depth — confirm `N` for
  the target repo.
- The structural test must NOT encode "MCP forever absent"; assert existence +
  well-formedness, never emptiness.
