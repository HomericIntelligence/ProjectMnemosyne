---
name: documentation-state-machine-consistency-review
description: "Review design documents for state machine self-consistency. Use when: (1) a design doc defines a state type and diagram, (2) reviewing API lifecycle designs, (3) verifying all states appear in transition diagram."
category: documentation
date: 2026-06-12
version: "1.0.0"
user-invocable: false
verification: verified-local
tags: [design-doc, state-machine, review, consistency, endpoint]
---

# Design Document State Machine Consistency Review

## Overview

| Field | Value |
|-------|-------|
| **Date** | 2026-06-12 |
| **Objective** | Review design document for internal consistency of EndpointStatus state machine |
| **Outcome** | Found 3 of 8 states missing from diagram; fixed with all states and transitions |
| **Verification** | verified-local |

## When to Use

- Design document defines both a type (Literal) and a visual diagram (Mermaid)
- Reviewing API lifecycle or endpoint state machine designs
- Verifying all states in a type definition appear in the transition diagram

## Verified Workflow

### Quick Reference

1. Extract all state names from the type definition
2. Extract all states from the Mermaid diagram
3. Diff: find states in type but not in diagram
4. For each missing state, define transitions
5. Add direct terminal transitions from all active states
6. Verify every non-terminal state has outgoing transitions

### Detailed Steps

1. Read the type definition and list all state values
2. Read the Mermaid stateDiagram and list all state nodes
3. Compute the diff between type states and diagram states
4. For each missing state, determine position in the lifecycle
5. Add entry, exit, and terminal transitions
6. Add notes for modifier states that are not type values
7. Verify no orphan states exist
8. Cross-check diagram against text descriptions

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
|---------|----------------|---------------|----------------|
| Missing terminal transitions from serving | Added serving but only connected to running | No path to dead during active serving | Every active state needs direct terminal transitions |
| Claimed broken cross-references | Reported sections 8.3 and 8.5 as missing | They actually existed in the document | Verify cross-references by checking actual headers |

## Results & Parameters

Before: 5 of 8 EndpointStatus values in diagram
After: All 8 values present plus exclusive modifier

Key principle: every non-terminal state must have direct transitions to all 3 terminal states
