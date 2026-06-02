---
name: computation-hard-walls-analysis
description: "Framework for analyzing 14 fundamental hard walls against exotic computation schemes in sci-fi mechanism design. Use when: (1) evaluating how many physical limits a fictional compute device breaks, (2) scoring mechanism plausibility against known physics limits, (3) writing scientifically rigorous speculative technology documents."
category: architecture
date: 2026-06-01
version: "1.3.0"
user-invocable: false
verification: unverified
history: computation-hard-walls-analysis.history
tags: [physics, computation, limits, hard-walls, scifi, worldbuilding, mechanism-design, tqc, topological, bekenstein, planck-density, offload-architecture, lloyd, holevo, landauer, reality-computes, computational-universe]
---

# Computation Hard Walls Analysis Framework

## Overview

| Field | Value |
|-------|-------|
| **Date** | 2026-06-01 |
| **Objective** | Systematically evaluate exotic/fictional compute mechanisms against 14 known physical hard limits |
| **Outcome** | Framework developed and applied across mechanism classes: AdS/CFT holographic (M02) defeats 10/14; asymptotic-safety RG (M16) defeats 5/14 + 3 partial; anyon topological braiding (M44) defeats 9/14 — with Wall 11 (Analog Precision) most decisively defeated by topological protection; Reality Offload / computational-universe (M55) defeats 5/14 decisively + 2 via NP-1 + 2 partially, uniquely defeating Wall 4 with zero new physics. Planck-density substrate mechanisms (LQG spin-network M14, anyon fabric M44) share a recurring failure mode: Planck energy density implies black hole collapse. 3 walls (6, 7, 14) are genuinely inviolable across all classes. |
| **Verification** | unverified — theoretical framework, not implemented |
| **History** | [changelog](./computation-hard-walls-analysis.history) |

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

Mechanism comparison (walls defeated):
AdS/CFT holographic boundary (M02):         10/14 defeated  — Parsimony 2/10
Asymptotic-safety RG substrate (M16):        5/14 defeated  — Parsimony 4/10
LQG spin-network processor (M14):           ~8/14 defeated  — Parsimony 3/10
Anyon topological braiding fabric (M44):     9/14 defeated  — Parsimony 3/10
Reality Offload / Comp. Universe (M55): 5/14 + 2 NP + 2 partial — Parsimony 8/10 LOW-BREAK
Inviolable (any mechanism):                  3/14 standing  — Walls 6, 7, 14

WALL 11 CHAMPION: Topological mechanisms (M44) defeat Wall 11 most rigorously —
  topological protection makes gate fidelity exactly discrete; error rate ~ e^{-E_gap/kT}.
```

### Detailed Assessment Steps

1. **For each wall, ask: does the mechanism's operating principle bypass the assumption?**
   - Wall 1 (Holevo): Only applies to classical readout. If output is quantum, it doesn't apply. M55 offload: applies to the RD boundary readout channel — Holevo limits extraction to ≤I_max bits where I_max = A/(4ℓ_P²). Enormous (~10⁶⁵ bits for R=10cm) but finite.
   - Wall 2 (Landauer): Only applies to irreversible erasure. Logically reversible / topologically protected → zero cost. M55 offload: the region's evolution is UNITARY (reversible) during the EO phase — zero Landauer cost there; cost paid only at BE write and RD readout (~10¹² bits/s × k_BT ln2 ≈ 3 nW).
   - Wall 3 (Cube-square): Only applies to volumetric computers. A surface computer (2D) has no cube-square problem. Topological mechanisms: if Planck-gap energy scale, room temperature is negligibly cold — thermal dissipation problem inverted. M55: no heat generated inside the target region (unitary evolution); all heat in macroscopic device electronics with normal surface area.
   - Wall 4 (Hilbert-space scaling): AdS/CFT trades exponential bulk Hilbert space for polynomial boundary CFT. AS/RG (M16): spectral dimension collapse from 4D to 2D reduces Hilbert space. TQC/Fibonacci anyons (M44): fusion Hilbert space grows as φ^N — the physical anyon system IS the exponential register, no classical simulation needed (BUT: TQC is still BQP; arbitrary quantum simulation remains exponentially hard). Reality Offload (M55) — UNIQUE, ZERO NEW PHYSICS: device never simulates the region; the region traverses its own exponential Hilbert space. Feynman's Wall applies to classical SIMULATION; M55 sidesteps by running the actual region. Device pays only polynomial I/O cost.
   - Wall 5 (Sign problem): FOUR distinct defeat mechanisms: (A) AdS/CFT — large-N saddle absorbs fermionic determinant into classical bulk; (B) CDT/Lorentzian RG (M16) — causal ordering eliminates Euclidean oscillatory sign problem; (C) TQC/Fibonacci (M44) — braid group representation is algebraically exact, no Monte Carlo sampling required, no sign problem exists; (D) Reality Offload (M55) — physical region has no sign problem (only classical algorithms simulating quantum systems do), but PARTIAL: the BE must prepare a fermionic initial state, which may require solving a sign problem to SPECIFY.
   - Wall 6 (Lyapunov): NOT bypassable. The MSS bound (λ_L ≤ 2πk_BT/ℏ) applies to any physical system. AdS/CFT saturates this bound, never exceeds it. M55 offload: region evolves chaotically but does not predict or compress it; chaos bites hard at the BE stage (Planck-precision initial conditions needed for chaotic scenarios).
   - Wall 7 (Irreducibility): NOT bypassable. A physical system is always computationally irreducible — it evolves at its own rate. No mechanism lets you skip ahead. CRITICAL for M55: "reality computes itself" does NOT defeat irreducibility — the region still runs every step in real time. The offload sidesteps the cost of CLASSICAL RECOMPUTATION, not the cost of RUNNING.
   - Wall 8 (Memory wall): Entanglement encodes correlations nonlocally — no data transport, zero movement energy. In RG substrates: field configuration IS the memory. TQC: information encoded in non-local fusion channels; gate operations are local braid crossings at Planck spacing. M55: information moves inside region as physical field propagation at c — no external memory bus, no cache miss, no von Neumann bottleneck.
   - Wall 9 (Gravity weakness): G_N smallness = 1/N suppression in boundary theory — a feature of the duality, not a bug. At Planck scale: G m_P²/ℏc = 1 exactly — gravity is not weak. Planck-substrate mechanisms operate where gravity is strong. M55 (NP-1 TCF): postulates O(1) coupling at Planck energies, bridging the hierarchy problem via new physics.
   - Wall 10 (Force ladder): All forces appear as operator families in the CFT spectrum. In analogue RG: energy-scale ladder collapsed by analogue Planck rescaling. In Planck-substrate mechanisms: new-physics postulate required to bridge macroscopic control to Planck-scale excitation. M55: TCF (NP-1) must couple macroscopic eV-scale fields to Planck-scale DOFs — a ~10²⁴ energy-scale gap; NP-1 postulates a resonant cascade. NOTE: the hierarchy problem reappears inside the TCF mechanism itself — M55's deepest internal tension.
   - Wall 11 (Analog precision): Quantum shot noise 1/√N with N~10⁶⁶ gives ~10³³ digit precision for AdS/CFT. TQC (M44): braiding is a discrete topological event — no analog precision requirement at all. Error rate = exp(-E_gap/k_BT). At Planck gap, room temp: error ~ exp(-10^32) ≈ 0. This is the most rigorous Wall 11 defeat across all M-series mechanisms. M55: boundary readout is a projective measurement — discrete eigenvalues, digital at Planck scale.
   - Wall 12 (Holographic bound): Surface computer operating at exactly the bound — saturated, not defeated. Accessible register for 1 kg, 5 mm radius device: ~10^40 bits. Planck-substrate fusion Hilbert spaces (dim ~ 10^(10^97)) vastly exceed this — surplus is formally inaccessible (see Black Hole Failure Mode below). M55: bound EXPLOITED (not defeated) — it enables the boundary readout, I_max = A/(4ℓ_P²) bits; full holographic readout of R=10cm at 300 K costs k_BT ln2 × 10⁶⁵ ≈ 10⁴⁴ J (impossible), so M55 always subsamples in practice.
   - Wall 13 (Thompson AT²): Requires wires in classical VLSI. CFT has nonlocal correlators built into physics — Thompson bound doesn't apply. 3D braid architecture: all gates are nearest-neighbor; AT² 2D VLSI bound inapplicable. M55: 3D computation in free space; boundary is a 2D surface; no VLSI topology applies, AT² bound irrelevant.
   - Wall 14 (Causality/latency): NOT bypassable. Entanglement wedge reconstruction is bounded by the bulk causal wedge. Anyon motion is subluminal. No-communication theorem applies universally. M55: even with NP-4 clock acceleration, region evolves causally — latency bounded below by light-crossing time of region.

2. **Score: count DEFEATED walls for Capability Score, count new postulates for Parsimony Score.**

3. **Identify genuinely inviolable walls:** Walls 6 (Lyapunov), 7 (irreducibility), and 14 (causality) cannot be defeated by any physical mechanism without violating the foundations of physics. Treat these as permanent constraints in any mechanism design.

4. **Name new-physics postulates explicitly (NP-N taxonomy):** Each law broken requires a labeled postulate. Count postulates for Parsimony Score = 10/(number of postulates).

5. **Check for the Planck Density Black Hole failure mode** (see below) — applies to ALL mechanisms using Planck-scale matter density.

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
|---------|----------------|---------------|----------------|
| Claiming all 14 walls defeated | Trying to argue every wall is bypassable to maximize capability score | Walls 6, 7, 14 are definitionally inviolable — bypassing them requires redefining causality or computation itself | Honest mechanism design requires stating which walls genuinely stand; 3 inviolable walls is a strength (shows rigor) |
| Conflating Holevo with Shannon | Treating Holevo bound as equivalent to Shannon channel capacity limit | Holevo applies specifically to classical extraction from quantum states; if output stays quantum, it does not apply | Always check if the bound's assumption (classical output) matches the mechanism's actual output channel |
| Treating Bekenstein bound as a wall to defeat | Trying to break the holographic bound to fit more information | The holographic bound IS the operating principle of a surface computer — operating at the bound is the goal | Reframe: saturating a bound is different from breaking it; saturation is optimal operation |
| Claiming d_s=2 implies 2D CFT tractability | Assuming spectral dimension flow to 2 makes computation exactly solvable via Virasoro symmetry | Spectral dimension characterizes diffusion properties only; it does not imply the geometry is a smooth 2-manifold with Virasoro symmetry | Distinguish between effective (diffusion-measured) dimension and actual geometric dimension; d_s=2 is a probe property, not a Lagrangian property |
| Treating Planck-density fusion Hilbert space as accessible register | Claiming φ^(10^98) dimensional anyon Hilbert space as the usable register | Bekenstein bound limits accessible bits to ~10^40 for a 1 kg device; the rest is topologically inaccessible and requires global measurement exponentially costly to process | Always cross-check claimed register size against Bekenstein-accessible bits; use ~10^40 bits for 1 kg, 5 mm device |
| Ignoring black hole collapse for Planck-density substrates | Designing a "palm-sized" device with Planck-scale energy density | Schwarzschild radius of 1 cm³ of Planck-density matter (ρ ~ 5×10^96 kg/m³) is astronomically large — device is a black hole | ALL Planck-density substrate mechanisms must address this failure mode explicitly; it requires additional new-physics or reframing |
| Claiming offload architecture defeats Wall 7 | M55: argued that running the region bypasses computational irreducibility | Irreducibility applies to the computation itself, not to who runs it; the region runs every step in real time | Wall 7 is inviolable even for the most elegant offload; offload sidesteps SIMULATION cost, not COMPUTATION cost |
| Claiming full holographic boundary readout at handheld power | M55: tried to read all I_max = 10⁶⁵ bits from R=10cm region at 300 K | Landauer cost: k_BT ln2 × 10⁶⁵ ≈ 10⁴⁴ J (Sun's output for ~10¹⁸ years) | Full holographic readout is never feasible; all practical devices subsample to ~10¹² bits/s |

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

LOW-BREAK mechanisms: mechanisms that defeat critical walls WITHOUT new physics.
M55 is a LOW-BREAK mechanism:
  Wall 4 defeated with ZERO new physics (just refuse to simulate).
  Walls 2, 5 partially defeated with ZERO new physics (unitary EO phase is free).
  New physics only needed for I/O: NP-1 (TCF coupling), NP-2 (BE write),
    NP-3 (RD read), NP-4 (clock acceleration, optional).
```

### Multi-Mechanism Comparison Table

```
Mechanism               Walls Defeated  Walls Standing  New-Physics Postulates  Capability  Parsimony
M02 AdS/CFT holo        10/14           3 (6,7,14)      5                       71%         2/10
M16 AS-RG sub           5/14 + 3 part   3 (6,7,14)      3                       ~50%        4/10
M14 LQG spin-network    ~8/14           4 (6,7,12,14)   3                       ~57%        3/10
M44 Anyon TQC fabric    9/14 + 2 part   3 (6,7,14)      3                       ~64%        3/10
M55 Reality Offload     5/14 + 2 part   3 (6,7,14)      4 (root: 1)             ~64%        8/10 LOW-BREAK
```

### M55 Wall-by-Wall Summary (Reality Computes Itself)

```
Wall  Status              Key argument
  1   LEFT STANDING       Holevo limits RD readout to ≤I_max bits (huge but finite)
  2   PARTIALLY DEFEATED  Region EO phase is unitary → zero Landauer; pays at BE/RD I/O only
  3   DEFEATED            No heat in region (unitary); device electronics normal surface area
  4   DEFEATED (ZERO NP)  Device never simulates; region traverses own Hilbert space
  5   PARTIALLY DEFEATED  Region has no sign problem; BE initial-state specification may need it
  6   LEFT STANDING       Region evolves chaotically; Planck-precision BE init required
  7   LEFT STANDING       Region runs every step in real time; irreducibility is irreducible
  8   DEFEATED            Information in region travels as physical fields at c; no memory bus
  9   BROKEN NP-1         TCF: O(1) Planck coupling via father's new physics
 10   BROKEN NP-1         TCF resonant cascade bridges 10^24 energy-scale gap (most speculative)
 11   DEFEATED            Boundary readout is projective measurement → discrete eigenvalues
 12   LEFT STANDING       Bekenstein exploited as readout surface; I_max ceiling stands
 13   IRRELEVANT          3D free space; no 2D VLSI topology; AT² bound inapplicable
 14   LEFT STANDING       Region evolves causally; c-latency sets minimum readout time
```

### Wall 5 Sign Problem — Four Distinct Defeat Mechanisms

```
Mechanism A (AdS/CFT):   Large-N saddle point → classical bulk gravity; fermionic
                         determinant absorbed into bulk geometry. Requires large N.

Mechanism B (CDT/AS):    Lorentzian (causal) path integral eliminates oscillatory
                         Euclidean sign problem directly via causal ordering constraint.
                         Works at any N. Requires Lorentzian formulation (CDT or similar).

Mechanism C (TQC/Fibonacci anyons, M44):
                         Braid group representation theory is algebraically exact — braid
                         matrices are computed from representation theory, not Monte Carlo.
                         No sign problem exists because there is no path integral sum with
                         oscillatory signs; braiding unitaries are exact finite group matrices.

Mechanism D (Reality Offload, M55):
                         Physical region has no sign problem — only classical algorithms
                         simulating quantum systems do. Running the region bypasses it.
                         PARTIAL: BE write of a fermionic initial state may still require
                         solving a sign problem to specify.
```

### Wall 4 Defeat — Four Distinct Mechanisms

```
A — Holographic reduction (AdS/CFT, M02):
    Exponential bulk Hilbert space traded for polynomial boundary CFT computation.
    Requires: AdS/CFT duality, holographic dictionary, large-N limit.

B — Spectral dimension collapse (AS-RG, M16):
    Effective spatial dimension flows from 4D to 2D at UV fixed point.
    Requires: asymptotic safety UV fixed point; d_s → 2 at Planck scale.

C — Physical exponential register (TQC/Fibonacci, M44):
    Fusion Hilbert space grows as φ^N; the physical anyon system IS the register.
    Requires: non-abelian anyons; still BQP (no general quantum-simulation speedup).

D — Reality offload (M55) — UNIQUE, NO NEW PHYSICS:
    Device refuses to simulate the region. Region traverses its own exponential Hilbert space.
    Feynman's Wall applies to classical SIMULATION; offload sidesteps by not simulating.
    Device pays only polynomial I/O cost (boundary bits).
    NP-1 TCF needed for I/O coupling, but NOT for the Wall 4 defeat itself.
    This is the ONLY defeat mechanism for Wall 4 requiring zero physics beyond QM + GR.
```

### Wall 11 — Analog Precision: Defeat Hierarchy

```
Weakest defeat:  AdS/CFT — quantum shot noise 1/√N gives ~10^33 digit precision (probabilistic)
Moderate defeat: LQG spin-network — spin labels are discrete integers (area spectrum is discrete)
Strongest defeat: TQC/Fibonacci anyons (M44) — braiding is a DISCRETE TOPOLOGICAL EVENT.
                  No continuous parameter involved in gate application.
                  Error rate = exp(-E_gap/k_BT).
                  At Planck gap (E_P/k_BT ~ 10^32): error ~ exp(-10^32) ≈ 0.
                  This is the only mechanism where Wall 11 defeat is rigorous by construction.
Also discrete:    Reality Offload (M55) — boundary readout is projective measurement,
                  yielding discrete eigenvalues (digital at Planck scale).
```

### The Three Inviolable Walls

```
Wall 6 — Chaos/Lyapunov: λ_L ≤ 2πk_BT/ℏ (Maldacena-Shenker-Stanford bound)
  Any physical quantum system saturates but cannot exceed this.
  AdS/CFT is a maximal chaos system — it saturates exactly.
  M55 offload: region evolves chaotically; chaos bites hard at BE initial-condition write.

Wall 7 — Computational Irreducibility:
  A physical system always evolves at its own rate.
  No mechanism provides speedup over the physical time of the system itself.
  M55: "offload" sidesteps simulation cost, NOT computation cost. Region runs every step.
  Wall 7 is inviolable even for the most elegant offload architecture.

Wall 14 — Causality/Speed-of-Light Latency:
  Information cannot propagate faster than c, even via entanglement.
  Entanglement wedge reconstruction is bounded by the causal wedge.
  No-communication theorem applies universally.
  M55: region evolves causally; RD readout is bounded by c-propagation within region.
```

### Critical Quantitative Limits for Boundary-Readout Mechanisms (M55 class)

```
Bekenstein bound (readout ceiling):
  I_max = A/(4ℓ_P²) = 4πR² / (4 × 2.6e-70 m²)
  For R = 10 cm: I_max ≈ 4π × 0.01 / (1.04e-69) ≈ 1.2e67 bits

Landauer cost of full holographic readout at 300 K:
  E_readout = k_BT ln2 × I_max ≈ 2.9e-21 J × 10^67 ≈ 3e46 J
  (Sun's total output over ~7e18 years — physically impossible)

Practical subsampling to human-perceptible output:
  ~10^12 bits/s (video + audio + haptic)
  Landauer cost: 10^12 × 2.9e-21 J ≈ 3 nW — trivial

CONSEQUENCE: All boundary-readout mechanisms (M55 class) MUST subsample.
Full holographic fidelity is thermodynamically impossible at any practical power.
This must be stated explicitly in the failure modes of any Class C mechanism.
```

### Bekenstein Accessible Bits Calculation

```
For a handheld device — canonical calculation (1 kg, 5 mm radius):
  S_max ≤ 2πRE / (ℏc)
  R = 0.005 m
  E = 1 kg × (3×10^8 m/s)² = 9×10^16 J
  S_max ≤ 2π × 0.005 × 9×10^16 / (10^-34 × 3×10^8)
         ≈ 2π × 4.5×10^14 / 3×10^-26
         ≈ 9.4×10^40 bits

→ Any mechanism claiming more than ~10^40 accessible bits in a handheld device
  violates the Bekenstein bound for that device.
  The surplus is either holographically inaccessible or the mechanism breaks Wall 12.

Compare to claimed registers in M-series mechanisms:
  M14 LQG (10^50-edge spin network in nuclear volume): claims 10^51 bits → INCONSISTENT
  M44 Fibonacci anyons (φ^(10^98) fusion Hilbert space): formally ~10^(5×10^97) → VASTLY INCONSISTENT
  Accessible in both cases via readout: ~10^40 bits (Bekenstein-consistent)
```

### CRITICAL FAILURE MODE: Planck-Density Black Hole Collapse

```
APPLIES TO: Any mechanism using Planck-scale matter density (ρ ~ m_P/ℓ_P³ ~ 5×10^96 kg/m³)

CALCULATION:
  Mass of 1 cm³ device at Planck density:
    M = ρ × V = 5×10^96 kg/m³ × 10^-6 m³ = 5×10^90 kg

  Schwarzschild radius:
    r_S = 2GM/c² = 2 × 6.67×10^-11 × 5×10^90 / (3×10^8)² ≈ 7.4×10^52 m

  Observable universe radius: ~4.4×10^26 m

  The Schwarzschild radius is ~10^26 times larger than the observable universe.
  → The device is not a palm-sized gadget. It IS a black hole many orders of magnitude
    larger than the observable universe.

RESOLUTION OPTIONS (all require additional new physics):
  A) Topological/holographic energy: The Planck-scale quantum effects don't require
     classical energy density — the topological phase is a ground-state property
     with zero classical energy density above vacuum. (Conceptually possible; no model.)
  B) Holographic encoding: Information stored on 2D surface (ℓ_P² per bit) rather than
     volumetrically; device volume is not filled with Planck-density matter.
  C) Acknowledge and state it explicitly as a failure mode requiring additional new physics.

RECOMMENDATION: Always note this failure mode for Planck-substrate mechanisms.
  Do NOT ignore it. State it as Failure Mode #N and note which resolution option the
  narrative adopts.
```

### Analogue Gravity Energy Rescaling (Wall 10 defeat, M16 pattern)

```
True Planck energy: E_P = 1.22×10¹⁹ GeV
Analogue Planck length: ℓ_P^eff ~ 10⁻¹⁰ m  (vs true ℓ_P = 1.6×10⁻³⁵ m)
Rescaling factor: ~6×10²⁴
Analogue Planck energy: ℏc/ℓ_P^eff ≈ 2×10⁻²⁴ J ≈ 12 eV  (soft X-ray)
Result: Planck-scale physics accessible at laboratory energies in the analogue
Caveat: Only within the analogue; real gravitational physics still requires Planck energy
```

### Laws Broken Ledger Status Definitions

```
PRESERVED         — Mechanism obeys this law completely
EXPLOITED         — Mechanism uses this law as operating principle (e.g., Bekenstein as readout surface)
BENT              — Mechanism near the boundary; technically valid but unusual
BROKEN            — Mechanism requires this law to not hold; must state new-physics postulate
DEFEATED          — Mechanism sidesteps the wall without breaking the underlying law
PARTIALLY DEFEATED — Wall applies in some sub-system but not the core computation
IRRELEVANT        — Wall's assumptions (e.g., 2D VLSI) do not apply to this mechanism
```

Laws Broken Ledger template (Markdown):

```text
| Law / Principle | Status | Note |
|---|---|---|
| [Law name] | PRESERVED / BENT / BROKEN | [Brief justification] |
```

## References (M55 class — boundary readout / computational universe)

- Lloyd, S. "Computational Capacity of the Universe." *Phys. Rev. Lett.* 88, 237901 (2002).
- Bekenstein, J. D. "Black Holes and Entropy." *Phys. Rev. D* 7, 2333 (1973).
- Holevo, A. S. "Bounds for the quantity of information transmitted by a quantum channel." *Probl. Peredachi Inf.* 9, 3 (1973).
- Landauer, R. "Irreversibility and Heat Generation in the Computing Process." *IBM J. Res. Dev.* 5, 183 (1961).

## Verified On

| Project | Context | Details |
|---------|---------|---------|
| HomericIntelligence/Story | M02 holographic boundary mechanism design, Myrmidon swarm physics agent | Applied to AdS/CFT boundary computer; see Research/Mechanisms/M02-holographic-boundary.md |
| HomericIntelligence/Story | M16 asymptotic-safety RG substrate mechanism design, Myrmidon swarm physics agent | Applied to AS smooth substrate; see Research/Mechanisms/M16-asymptotic-safety-substrate.md |
| HomericIntelligence/Story | M44 anyon topological braiding fabric, Myrmidon swarm physics agent, 2026-06-01 | Applied to Fibonacci anyon fabric; Planck-density black hole failure mode documented; see Research/Mechanisms/M44-anyon-braiding-fabric.md |
| HomericIntelligence/Story | M55 reality-computes-itself offload design, 2026-06-01 | Discovered LOW-BREAK pattern for Wall 4 (zero NP); Bekenstein readout quantification (10^44 J full holographic); confirmed Wall 7 inviolable for offload; "perfect simulator must BE the region" no-go accepted. Research/Mechanisms/M55-reality-computes-itself.md |
