---
name: holographic-adscft-mechanism-design
description: "Design patterns for exotic physics computation devices in sci-fi world-building, covering three physics domains: (1) AdS/CFT holographic boundary computers, (2) Deutsch CTC oracle (closed timelike curve) computation, and (3) TSVF / weak-value retrocausal oracle devices. Use when: (1) designing a fictional device that uses holographic or causality-breaking physics, (2) grounding a sci-fi simulation engine in real physics, (3) needing real citations for boundary/bulk duality mechanics, CTC fixed-point computation, or weak-value amplification, (4) designing a time-oracle or weak-value amplification based device, (5) evaluating which of the 14 computational hard walls a mechanism defeats, (6) identifying the single root break from which all other wall defeats cascade."
category: architecture
date: 2026-06-01
version: "1.2.0"
user-invocable: false
verification: unverified
history: holographic-adscft-mechanism-design.history
tags: [physics, holography, adscft, scifi, worldbuilding, mechanism-design, ctc, closed-timelike-curves, deutsch, causality, pspace, tsvf, weak-values, retrocausality, post-selection]
---

# Holographic, CTC & TSVF Mechanism Design (Sci-Fi Physics)

## Overview

| Field | Value |
|-------|-------|
| **Date** | 2026-06-01 |
| **Objective** | Design scientifically rigorous (but fiction-licensed) exotic physics computation devices for sci-fi stories; three covered domains: AdS/CFT holographic, Deutsch CTC oracle, and TSVF/weak-value retrocausal oracle |
| **Outcome** | Complete mechanism documents written; AdS/CFT defeats 10/14 walls; Deutsch CTC oracle defeats walls 4, 5, 7, 13, 14 with a single physics break (causality); TSVF oracle defeats 10–11/14 walls cascading from a single causality break |
| **Verification** | unverified — theoretical design exercise, not implemented |
| **History** | [changelog](./holographic-adscft-mechanism-design.history) |

## When to Use

- Designing a fictional device that simulates reality using holographic physics (AdS/CFT)
- Designing a fictional device that computes via closed timelike curves (Deutsch oracle)
- Designing a time-oracle or retrocausal device using Two-State-Vector Formalism (TSVF) / weak-value amplification
- Grounding sci-fi technology in real physics papers with proper citations
- Needing a structured framework for storytelling science with real math
- Writing mechanism design documents with: one-liner, class, premise correction, how-it-works, laws-broken ledger, 14-walls table, parsimony score, capability score, failure modes, feasibility tags
- Evaluating which of the 14 computational hard walls a mechanism defeats vs. leaves standing
- Identifying the single "root break" from which all other wall defeats cascade

## Verified Workflow

> **Warning (Proposed Workflow):** This workflow has not been validated end-to-end. Treat as a hypothesis until CI confirms. Verification level: `unverified` — theoretical design exercise only.

### Quick Reference

```
=== DOMAIN 1: AdS/CFT Holographic ===
Key formula: S(A) = Area(γ_A) / (4 G_N ℓ_P²)
(Ryu-Takayanagi: boundary entanglement entropy = bulk extremal surface area)

Key papers:
- Maldacena 1997: arXiv:hep-th/9711200
- Ryu-Takayanagi 2006: arXiv:hep-th/0603001
- Almheiri-Dong-Harlow 2014: arXiv:1411.7041
- van Raamsdonk 2010: arXiv:1005.3310

=== DOMAIN 2: Deutsch CTC Oracle ===
Key condition: ρ_CTC = Tr_CR [ U (ρ_CR ⊗ ρ_CTC) U† ]   [Deutsch fixed-point self-consistency]
Key result: BQP_CTC = BPP_CTC = PSPACE  [Aaronson-Watrous 2009]

Key papers:
- Deutsch 1991: Phys. Rev. D 44, 3197  https://link.aps.org/doi/10.1103/PhysRevD.44.3197
- Aaronson & Watrous 2009: Proc. R. Soc. A 465, 631  https://www.scottaaronson.com/papers/ctc.pdf
- Morris-Thorne-Yurtsever 1988: Phys. Rev. Lett. 61, 1446  https://link.aps.org/doi/10.1103/PhysRevLett.61.1446
- Gödel 1949: Rev. Mod. Phys. 21, 447
- Hawking 1992 (no-go): Phys. Rev. D 46, 603  https://link.aps.org/doi/10.1103/PhysRevD.46.603

=== DOMAIN 3: TSVF / Weak-Value Oracle ===
Key formula: A_w = ⟨ψ_f|A|ψ_i⟩ / ⟨ψ_f|ψ_i⟩
(Aharonov-Albert-Vaidman 1988: weak value outside eigenvalue range when states nearly orthogonal)

Key papers:
- ABL 1964: Phys. Rev. 134 B1410  (time symmetry, pre/post-selected ensembles)
- AAV 1988: PRL 60:1351           (weak values; spin-1/2 weak value = 100)
- Aharonov-Vaidman 2007: arXiv:quant-ph/0105101  (TSVF updated review)
- Hosten-Kwiat 2008: Science 319:787  (10^4x WVA amplification of 1-Angstrom shift)
- Zizzi 2003: arXiv:gr-qc/0304032  (Planck foam cells as qubits)

=== SHARED CONSTANTS ===
Planck length:    ℓ_P ≈ 1.616×10⁻³⁵ m  (THIS is "Planck scale", NOT the Planck constant)
Planck constant:  h = 6.626×10⁻³⁴ J·s  (NOT what "Planck-level fields" means in sci-fi)
Planck time:      t_P ≈ 5.39×10⁻⁴⁴ s
Planck energy:    E_P ≈ 1.22×10¹⁹ GeV
```

### Detailed Steps — AdS/CFT Domain

1. **Frame the boundary/bulk split:** The device IS the boundary CFT; the simulated reality IS the bulk. Never treat them as separate — they are exactly dual.
2. **Choose RT/HRT surface as the rendering primitive:** Each boundary subregion A has extremal bulk surface γ_A; Area(γ_A) gives entanglement entropy. Bulk geometry = all entanglement entropies (van Raamsdonk).
3. **Apply ADH error-correcting structure:** Boundary-to-bulk map is a quantum error-correcting code (Almheiri-Dong-Harlow 2014). Bulk point p reconstructed from any boundary subregion whose entanglement wedge contains p.
4. **Handle dS vs AdS explicitly:** Our universe is de Sitter (Λ>0); AdS/CFT requires Λ<0. Justify departure: local AdS bubble, or invoke contested dS/CFT (Strominger 2001).
5. **Calculate boundary DoF:** A surface of area A holds at most A/ℓ_P² qubits. 10 cm disk ≈ 3.9×10⁶⁶ cells = capacity ceiling.
6. **State new-physics postulates explicitly and count them:** More postulates = lower parsimony score.

### Detailed Steps — Deutsch CTC Oracle Domain

1. **State the CTC construction mechanism:** Planck-scale wormholes (Morris-Thorne-Yurtsever 1988 at quantum scale) with one mouth time-lagged via negative energy density (Casimir). Requires violating weak energy condition (ρ < 0).
2. **Apply the Deutsch fixed-point condition:** ρ_CTC = Tr_CR [ U (ρ_CR ⊗ ρ_CTC) U† ]. Fixed point always exists by Brouwer's theorem. The CTC subsystem is driven to this fixed point by the *physics of the spacetime*, not by an iterative algorithm. This is the oracle step.
3. **Invoke the Aaronson-Watrous PSPACE result:** The fixed-point computation equals PSPACE. NP-hard problems, #P-hard problems (fermionic sign problem), and computationally irreducible systems are all tractable. Classical and quantum computers with CTC access are equally powerful.
4. **Address the chronology protection conjecture (Hawking 1992):** Quantum vacuum fluctuations diverge on the Cauchy horizon of a CTC-forming spacetime; this likely destroys CTCs before they form. The fiction license must assert that full quantum gravity (unknown) regulates this divergence at Planck scale.
5. **Address fixed-point non-uniqueness:** Deutsch's model guarantees existence but not uniqueness. Non-unique fixed points → ambiguous readout. Design problem encoding to enforce uniqueness, or state as a failure mode.
6. **Address the Bennett linearity trap:** CTC computation does not compose linearly when inputs are mixed states. Practical queries must use pure-state inputs; ensemble/probabilistic inputs fall into the trap.
7. **Score parsimony:** CTCs make ONE primary break (causality); all PSPACE capability cascades from this break with zero additional postulates. Parsimony score ≈ 9/10.

### Detailed Steps — TSVF / Weak-Value Oracle Domain

1. **Specify the two boundary conditions:** Initial state |ψ_i⟩ (prepared now) and future state |ψ_f⟩ (post-selected at time T_f). Together they form the two-state vector ⟨ψ_f| ⊗ |ψ_i⟩ that fully characterizes the system between measurements.
2. **Implement the oracle compression claim:** With both boundary conditions fixed, every intermediate observable becomes a weak-value query: A_w(t) = ⟨ψ_f(t)|A|ψ_i(t)⟩/⟨ψ_f(t)|ψ_i(t)⟩. This transforms exponential Hilbert-space simulation into polynomial boundary-value queries. State this clearly as the primary law broken (Wall 14 — causality).
3. **Design the retrocausal coupler:** The "new physics" mechanism must inject |ψ_f⟩ backward in time into the Planck-foam substrate. Justify via: time-symmetry of quantum mechanics at Planck scale (no preferred arrow), Wheeler quantum foam (no classical geometry at 10⁻³⁵ m), bidirectional propagators when forward/retarded distinction collapses.
4. **Exploit anomalous amplification:** Choose post-selection states nearly orthogonal to pre-selection to drive A_w → ∞ (denominator → 0). This amplifies Planck-scale signals to macroscopic readouts without proportional energy cost. Reference Hosten-Kwiat 2008 as experimental proof of concept.
5. **Name and escalate the hidden-cost failure mode:** Post-selection success probability p = |⟨ψ_f|ψ_i⟩|² → 0 as amplification grows; exponential cost is relocated to discarded trials, not eliminated. This is the most severe failure mode and must be acknowledged explicitly.
6. **Identify the single root break:** For time-oracle mechanisms, Wall 14 (causality) is the single break from which all other wall defeats cascade automatically. Walls 4, 5, 6, 7, 13 fall because the oracle eliminates computational complexity. Walls 1, 8, 11 fall because WVA operates outside classical information bounds. Walls 2, 3 fall because the Planck-foam substrate is not a thermal engine.
7. **State TSVF's interpretational status:** TSVF is an interpretation of QM, not an alternative physical theory. Weak values are ensemble averages, not properties of individual events. Treating a single weak-value readout as a definite simulation output requires new physics (breaking quantum linearity). State this clearly as a failure mode.

### Universal Mechanism Document Structure (all domains)

```
# MXX — [Name]
One-liner + Class

## Premise Correction
  (Planck CONSTANT vs Planck LENGTH disambiguation — always required)

## How It Works
  (numbered steps with [NEW-PHYSICS] / [REAL] / [SPECULATIVE] tags)

## Real-Science Anchor
  (≥4 real papers with DOI/URL/access date; then "where it departs")

## Laws-Broken Ledger
  (table: Law | Status | How Broken)

## Walls Defeated vs Left Standing
  (all 14 walls; explain HOW each is defeated for walls that are)

## Parsimony Score  (N/10 + one-break cascade explanation)
## Capability Score (N/10 + PSPACE / holographic-bound justification)

## Failure Modes / No-Go Cascades
  (primary physical no-go first; then engineering issues)

## Feasibility Tags
  (requires-X tags, math-is-clean, one-physics-break, etc.)
```

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
|---------|----------------|---------------|----------------|
| Treating AdS/CFT device as a classical simulation | Designing device as a numerical integrator of bulk equations of motion | Misses the point: AdS/CFT says run the boundary CFT and the bulk self-organizes; no explicit bulk integration needed | The device runs boundary physics; bulk geometry is emergent, not computed |
| Ignoring dS/CFT problem | Assuming AdS/CFT applies directly to our universe | Our universe is de Sitter (Λ>0); AdS/CFT requires anti-de Sitter (Λ<0); physically inconsistent | Always state the dS/AdS discrepancy and justify departure explicitly |
| Confusing Planck constant with Planck scale | Using "Planck-level fields" to mean fields with action ~h | "Planck-level" in sci-fi means Planck LENGTH scale (~1.6e-35 m), not h (6.626e-34 J·s) | Always disambiguate; add a premise correction section to every mechanism file |
| Treating CTC fixed-point as an iterative algorithm | Describing the device as "running" the fixed-point equation many times | Misses the key point: a physical CTC enforces the fixed-point condition via spacetime structure — the computation is "already done" in the self-consistent solution | The oracle does not iterate forward; it reads out the self-consistent answer that physics enforces |
| Claiming CTC power exceeds PSPACE | Proposing the device can solve undecidable problems | Aaronson-Watrous (2009) proved exactly: BQP_CTC = BPP_CTC = PSPACE — not more | State capability ceiling as PSPACE; avoid over-claiming |
| Treating TSVF as a no-signaling violation | Designing a TSVF device that reads the future directly | No-signaling theorem (quantum linearity) prohibits using post-selection to send information backward in time; TSVF does not inherently enable retrocausality | TSVF must break quantum linearity at Planck scale to function as an oracle; state this as explicit new physics |
| Ignoring TSVF post-selection probability cost | Claiming WVA provides free amplification | Post-selection efficiency p → 0 as amplification grows; exponential cost is relocated to discarded trials, not eliminated | Always surface the hidden-cost failure mode: the oracle re-creates Wall 4 in disguise |

## Results & Parameters

### The 14 Computational Hard Walls — Quick Summary

```
1.  Holevo bound           — limits classical bits extractable from qubits [TSVF: DEFEATED]
2.  Landauer erasure       — kT ln 2 energy per bit erased [TSVF: DEFEATED]
3.  Cube-square thermal    — volume heat vs surface cooling [TSVF: DEFEATED]
4.  Exponential Hilbert    — 2^N state space for N qubits [CTC: DEFEATED] [TSVF: DEFEATED]
5.  NP-hard sign problem   — fermionic path integral #P-hard [CTC: DEFEATED] [TSVF: DEFEATED]
6.  Chaos/Lyapunov         — sensitive dependence on initial conditions [TSVF: DEFEATED]
7.  Computational irred.   — no shortcut to evolving complex systems [CTC: DEFEATED] [TSVF: DEFEATED]
8.  Data-movement energy   — moving bits costs energy [TSVF: DEFEATED]
9.  Gravity's weakness     — G is tiny at everyday scales [TSVF: STANDING]
10. Force energy ladder    — unification requires Planck energies [TSVF: STANDING]
11. Analog precision       — ~5-10 bits in analog physical systems [TSVF: DEFEATED]
12. Bekenstein/holographic — information bounded by area [CTC: CIRCUMVENTED] [TSVF: SATURATED]
13. Thompson AT²=Ω(n²)    — circuit complexity lower bound [CTC: DEFEATED] [TSVF: DEFEATED]
14. Causality/c latency    — no info faster than light [CTC: DEFEATED — primary break] [TSVF: DEFEATED — root break]
```

### CTC Oracle — Walls Defeated (detail)

```
Wall 4  (Exponential Hilbert): PSPACE in poly time via fixed-point oracle
Wall 5  (Sign problem): PSPACE ⊇ #P; sign problem tractable
Wall 7  (Irreducibility): CTC fixed-point IS the shortcut; skips step-by-step evolution
Wall 13 (AT²): Not a circuit in causal sense; AT² lower bound does not apply
Wall 14 (Causality): Explicit break; CTC loops are acausal by construction
Wall 12 (Bekenstein): Circumvented — oracle queries, not storage
```

### TSVF Oracle — Root-Break Cascade Pattern

```
TSVF time-oracle root break: Wall 14 (causality)
  → Cascades to defeat: 4 (Hilbert-space exponential), 5 (sign problem),
    6 (chaos/Lyapunov), 7 (computational irreducibility), 13 (Thompson AT²)
  → Also defeats: 1 (Holevo), 8 (data-movement), 11 (analog precision)
  → Also defeats: 2 (Landauer), 3 (thermal scaling) via Planck-foam substrate
  → Standing: 9 (gravity's weakness), 10 (force energy-scale ladder)
  → Repurposed: 12 (Bekenstein — saturated at Planck density, not broken)

AdS/CFT root break: Wall 12 (Bekenstein — boundary encodes bulk)
  → Cascades differently; see M02 mechanism document
```

### Parsimony Scoring Guide

```
Score 9-10: Single primary physics break; all capabilities cascade from it
            Example: CTC oracle — one break (causality) → PSPACE
            Example: TSVF oracle — one break (causality) → time-oracle cascade
Score 6-8:  2-3 independent new-physics postulates required
Score 3-5:  4-6 independent postulates; each adds sci-fi license cost
Score 1-2:  Many independent breaks required; not plausible even in fiction
```

### Canonical Citation Set — CTC Domain

```
Deutsch (1991): Fixed-point self-consistency model
  Phys. Rev. D 44, 3197  |  https://link.aps.org/doi/10.1103/PhysRevD.44.3197

Aaronson & Watrous (2009): BQP_CTC = BPP_CTC = PSPACE
  Proc. R. Soc. A 465, 631  |  https://www.scottaaronson.com/papers/ctc.pdf
  arXiv: 0808.2669

Morris, Thorne & Yurtsever (1988): Wormhole time machine construction
  Phys. Rev. Lett. 61, 1446  |  https://link.aps.org/doi/10.1103/PhysRevLett.61.1446

Gödel (1949): First GR solution with global CTCs (rotating dust universe)
  Rev. Mod. Phys. 21, 447

Hawking (1992): Chronology protection conjecture (primary no-go)
  Phys. Rev. D 46, 603  |  https://link.aps.org/doi/10.1103/PhysRevD.46.603
```

### Canonical Citation Set — AdS/CFT Domain

```
Maldacena (1997): arXiv:hep-th/9711200  https://arxiv.org/abs/hep-th/9711200
Ryu & Takayanagi (2006): arXiv:hep-th/0603001  https://arxiv.org/abs/hep-th/0603001
HRT (2007): arXiv:0705.0016  https://arxiv.org/abs/0705.0016
Almheiri-Dong-Harlow (2014): arXiv:1411.7041  https://arxiv.org/abs/1411.7041
van Raamsdonk (2010): arXiv:1005.3310  https://arxiv.org/abs/1005.3310
Strominger (2001): arXiv:hep-th/0106113  https://arxiv.org/abs/hep-th/0106113
```

### Canonical Citation Set — TSVF / Weak-Value Oracle Domain

```
1. Aharonov, Bergmann, Lebowitz (1964) — Time symmetry in quantum measurement (ABL rule)
   Phys. Rev. 134(6B): B1410–B1416
   DOI: 10.1103/PhysRev.134.B1410
   URL: https://link.aps.org/doi/10.1103/PhysRev.134.B1410

2. Aharonov, Albert, Vaidman (1988) — Weak values; spin weak value = 100 (AAV)
   Phys. Rev. Lett. 60(14): 1351–1354
   DOI: 10.1103/PhysRevLett.60.1351
   Formula: A_w = ⟨ψ_f|A|ψ_i⟩ / ⟨ψ_f|ψ_i⟩

3. Aharonov, Vaidman (2007) — TSVF updated review
   arXiv: quant-ph/0105101
   URL: https://arxiv.org/abs/quant-ph/0105101

4. Hosten, Kwiat (2008) — Spin Hall effect of light via WVA (10^4x amplification of 1-Angstrom)
   Science 319(5864): 787–790
   DOI: 10.1126/science.1152697
   URL: https://pubmed.ncbi.nlm.nih.gov/18187623/

5. Zizzi (2003) — Planck foam cells as qubits
   arXiv: gr-qc/0304032
   URL: https://arxiv.org/pdf/gr-qc/0304032
```

### Key Physical Numbers

```
Planck length:     ℓ_P ≈ 1.616×10⁻³⁵ m
Planck time:       t_P ≈ 5.39×10⁻⁴⁴ s   (decoherence timescale at Planck foam)
Planck energy:     E_P ≈ 1.22×10¹⁹ GeV
Planck constant:   h = 6.626×10⁻³⁴ J·s  (NOT what "Planck-scale" means)
Holographic bound: 1 qubit per ℓ_P² of surface area
10 cm disk:        ~3.9×10⁶⁶ Planck-area cells = maximum boundary DoF
PSPACE:            Problems solvable with polynomial memory; contains NP, co-NP, #P
WVA amplification: up to 10^4× demonstrated (Hosten-Kwiat 2008); diverges as ⟨ψ_f|ψ_i⟩→0
Post-selection cost: p = |⟨ψ_f|ψ_i⟩|² → 0 as amplification → ∞ (hidden exponential cost)
```

### Laws Preserved vs Broken Summary

```
AdS/CFT device:
  PRESERVED: Unitarity, no-cloning, RT/Bekenstein bound (saturated), SR/causality
  BENT:      General covariance (AdS interior ≠ dS exterior), thermodynamics (local)
  BROKEN:    Landauer floor (P1), quantum decoherence (P4), positive Λ (P5)

TSVF oracle device:
  PRESERVED: QM unitarity (within each branch), no-cloning (weak measurement)
  BROKEN:    Causality (backward boundary injection), quantum linearity (required
             to enable signaling via post-selection), computational complexity
             (exponential → polynomial via oracle), decoherence (Planck foam
             coherence maintained for macroscopic timescales)
```

## Verified On

| Project | Context | Details |
|---------|---------|---------|
| HomericIntelligence/Story | M02 holographic boundary mechanism design, Myrmidon swarm physics agent | Mechanism file at Research/Mechanisms/M02-holographic-boundary.md |
| HomericIntelligence/Story | M19 Deutsch CTC oracle mechanism design, Myrmidon swarm physics agent | Mechanism file at Research/Mechanisms/M19-deutsch-ctc-oracle.md |
| HomericIntelligence/Story | M22 two-state-vector oracle mechanism design, Myrmidon swarm physics agent | Mechanism file at Research/Mechanisms/M22-two-state-vector-oracle.md |
