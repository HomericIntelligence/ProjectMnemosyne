---
name: computation-hard-walls-analysis
description: "Framework for analyzing 14 fundamental hard walls against exotic computation schemes in sci-fi mechanism design. Use when: (1) evaluating how many physical limits a fictional compute device breaks, (2) scoring mechanism plausibility against known physics limits, (3) writing scientifically rigorous speculative technology documents."
category: architecture
date: 2026-06-01
version: "1.0.0"
user-invocable: false
verification: unverified
tags: [physics, computation, limits, hard-walls, scifi, worldbuilding, mechanism-design]
---

# Computation Hard Walls Analysis Framework

## Overview

| Field | Value |
|-------|-------|
| **Date** | 2026-06-01 |
| **Objective** | Systematically evaluate exotic/fictional compute mechanisms against 14 known physical hard limits |
| **Outcome** | Framework developed; holographic mechanism defeats 10 of 14 walls; 3 are genuinely inviolable |
| **Verification** | unverified — theoretical framework, not implemented |

## When to Use

- Scoring a speculative or fictional computation mechanism for plausibility
- Writing mechanism design documents for sci-fi worldbuilding
- Checking which physical laws a proposed device must break and why
- Comparing multiple exotic compute mechanisms on a common rubric
- Grounding "impossible technology" in real physics language

## Verified Workflow

> **Warning (Proposed Workflow):** This workflow has not been validated end-to-end. Treat as a hypothesis until CI confirms. Verification level: `unverified` — theoretical framework only.

### Quick Reference

```
The 14 Hard Walls (reference list):
 1. Holevo bound (classical bits extractable from qubits)
 2. Landauer floor (k_BT ln2 per bit erased)
 3. Cube-square thermal (volume heat vs surface cooling)
 4. Exponential Hilbert-space scaling (Feynman)
 5. NP-hard fermionic sign problem
 6. Chaos/Lyapunov limit (λ_L ≤ 2πk_BT/ℏ)
 7. Computational irreducibility (Wolfram)
 8. Data-movement/memory-wall energy
 9. Gravity's weakness (G_N extremely small)
10. Force energy-scale ladder (electroweak >> gravity)
11. Analog precision/noise wall (~5-10 bits classical)
12. Bekenstein/holographic bound (S ≤ A/4G_N)
13. Thompson AT²=Ω(n²) I/O lower bound (VLSI)
14. Causality/speed-of-light latency

Status per mechanism (AdS/CFT holographic boundary):
Defeated:  1,2,3,4,5,8,9,10,11,13  (10 walls)
Standing:  6,7,14                    (3 walls — genuinely inviolable)
Saturated: 12                        (operating principle, not broken)
```

### Detailed Assessment Steps

1. **For each wall, ask: does the mechanism's operating principle bypass the assumption?**
   - Wall 1 (Holevo): Only applies to classical readout. If output is quantum, it doesn't apply.
   - Wall 2 (Landauer): Only applies to irreversible erasure. Logically reversible / topologically protected → zero cost.
   - Wall 3 (Cube-square): Only applies to volumetric computers. A surface computer (2D) has no cube-square problem.
   - Wall 4 (Hilbert-space scaling): AdS/CFT trades exponential bulk Hilbert space for polynomial boundary CFT — the whole point.
   - Wall 5 (Sign problem): At large N and strong coupling, bulk classical gravity replaces fermionic path integral — sign problem absorbed into the duality.
   - Wall 6 (Lyapunov): NOT bypassable. The MSS bound (λ_L ≤ 2πk_BT/ℏ) applies to any physical system including the boundary CFT. AdS/CFT *saturates* this bound, never exceeds it.
   - Wall 7 (Irreducibility): NOT bypassable. A physical system is always computationally irreducible — it evolves at its own rate. No mechanism lets you "skip ahead."
   - Wall 8 (Memory wall): Entanglement encodes correlations nonlocally — no data transport, zero movement energy.
   - Wall 9 (Gravity weakness): G_N smallness = 1/N suppression in boundary theory — a feature of the duality, not a bug.
   - Wall 10 (Force ladder): All forces appear as operator families in the CFT spectrum. Unified encoding.
   - Wall 11 (Analog precision): Quantum shot noise 1/√N with N~10⁶⁶ gives ~10³³ digit precision — effectively unlimited.
   - Wall 12 (Holographic bound): Surface computer operating at exactly the bound — saturated, not defeated.
   - Wall 13 (Thompson AT²): Requires wires in classical VLSI. CFT has nonlocal correlators built into physics — Thompson bound doesn't apply.
   - Wall 14 (Causality/latency): NOT bypassable. Entanglement wedge reconstruction is bounded by the bulk causal wedge. Even holography cannot transmit information faster than c.

2. **Score: count DEFEATED walls for Capability Score, count new postulates for Parsimony Score.**

3. **Identify "genuinely inviolable" walls:** Walls 6 (Lyapunov), 7 (irreducibility), and 14 (causality) cannot be defeated by any physical mechanism without violating the foundations of physics. Treat these as permanent constraints in any mechanism design.

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
|---------|----------------|---------------|----------------|
| Claiming all 14 walls defeated | Trying to argue every wall is bypassable to maximize capability score | Walls 6, 7, 14 are definitionally inviolable — bypassing them requires redefining causality or computation itself, which undercuts the scientific grounding | Honest mechanism design requires stating which walls genuinely stand; 3 inviolable walls is actually a strength (shows rigor) |
| Conflating Holevo with Shannon | Treating Holevo bound as equivalent to Shannon channel capacity limit | Holevo applies specifically to classical extraction from quantum states; if output channel stays quantum, it does not apply | Always check if the bound's assumption (classical output) matches the mechanism's actual output channel |
| Treating Bekenstein bound as a wall to defeat | Trying to "break" the holographic bound to fit more information | The holographic bound IS the operating principle of a surface computer — operating at the bound is the goal, not a failure | Reframe: "saturating" a bound is different from "breaking" it; saturation is optimal operation |

## Results & Parameters

### Capability Score Rubric

```
Capability Score = (Walls Defeated) / 14
High (>8/14):    Mechanism has strong physics-based arguments for most walls
Medium (5-8/14): Several walls defeated; others require new-physics postulates
Low (<5/14):     Mechanism relies heavily on breaking physics with no argument

Parsimony Score = 10 / (number of new-physics postulates)
Score 10: 1 postulate (most parsimonious)
Score 5:  2 postulates
Score 2:  5 postulates (highly exotic)
Score 1:  10+ postulates (pure fantasy)
```

### Holographic AdS/CFT Reference Scores

```
Capability Score: 10/14 = 71%  (highest theoretically defensible for any scheme)
Parsimony Score:  2/10         (5 new-physics postulates required)
```

### The Three Inviolable Walls

```
Wall 6 — Chaos/Lyapunov: λ_L ≤ 2πk_BT/ℏ (Maldacena-Shenker-Stanford bound)
  Any physical quantum system saturates but cannot exceed this.
  AdS/CFT is a maximal chaos system — it saturates exactly.

Wall 7 — Computational Irreducibility:
  A physical system always evolves at its own rate.
  No mechanism provides "speedup" over the physical time of the system itself.

Wall 14 — Causality/Speed-of-Light Latency:
  Information cannot propagate faster than c, even via entanglement.
  Entanglement wedge reconstruction is bounded by the causal wedge.
  No-communication theorem applies universally.
```

### Laws Broken Ledger Template

```markdown
| Law / Principle | Status | Note |
|---|---|---|
| [Law name] | [PRESERVED] / [BENT] / [BROKEN] | [Brief justification] |
```

Status definitions:
- `[PRESERVED]`: Mechanism obeys this law completely
- `[BENT]`: Mechanism operates near the boundary; technically valid but unusual
- `[BROKEN]`: Mechanism requires this law to not hold; must state new-physics postulate

## Verified On

| Project | Context | Details |
|---------|---------|---------|
| HomericIntelligence/Story | M02 holographic boundary mechanism design, Myrmidon swarm physics agent | Applied to AdS/CFT boundary computer; see Research/Mechanisms/M02-holographic-boundary.md |
