---
name: asymptotic-safety-quantum-gravity-refs
description: "Key papers, formulas, and physical facts for asymptotic safety quantum gravity and spectral dimension flow in sci-fi mechanism design. Use when: (1) designing a fictional device based on Planck-scale RG-flow physics, (2) citing real quantum gravity results about dimensional reduction to d_s=2, (3) grounding a sci-fi simulation engine in asymptotic-safety or CDT results."
category: architecture
date: 2026-06-01
version: "1.0.0"
user-invocable: false
verification: unverified
tags: [physics, quantum-gravity, asymptotic-safety, spectral-dimension, CDT, Planck-scale, renormalization-group, scifi, worldbuilding, mechanism-design]
---

# Asymptotic Safety Quantum Gravity — Physics References

## Overview

| Field | Value |
|-------|-------|
| **Date** | 2026-06-01 |
| **Objective** | Compile real physics results, citations, and formulas for asymptotic safety (AS) and CDT quantum gravity for use in mechanism design and sci-fi grounding |
| **Outcome** | Canonical citation set assembled; spectral dimension flow d_s: 4→2 confirmed cross-approach; analogue rescaling trick documented |
| **Verification** | unverified — reference compilation, not implemented code |

## When to Use

- Needing real citations for spectral dimension flow to 2 at Planck scales
- Designing a mechanism that uses RG flow as a computational substrate
- Citing the Weinberg/Reuter asymptotic safety program in worldbuilding docs
- Checking if asymptotic safety predicts smooth vs. discrete spacetime at Planck scale
- Grounding "fractal spacetime" claims in actual physics papers

## Verified Workflow

> **Warning (Proposed Workflow):** This workflow has not been validated end-to-end. Treat as a hypothesis until CI confirms. Verification level: `unverified` — reference collection only.

### Quick Reference

```
Key formula (Wetterich/FRG flow equation):
  ∂_t Γ_k = (1/2) Tr[(Γ_k^(2) + R_k)^{-1} ∂_t R_k]
  where t = ln(k/k_0) is RG time, R_k is the infrared regulator

Spectral dimension result:
  d_s = 4  (macroscopic, k << k_Planck)
  d_s = 2  (microscopic, k >> k_Planck)
  — exact result, independent of truncation (Lauscher-Reuter 2005)
  — independently confirmed by CDT Monte Carlo (Ambjorn-Jurkiewicz-Loll 2005)

Planck scales (for premise correction):
  Planck LENGTH:      ℓ_P = √(ℏG/c³) ≈ 1.616×10⁻³⁵ m  ← "Planck-scale" means this
  Planck CONSTANT:    h = 6.626×10⁻³⁴ J·s               ← NOT what "Planck-level" means
  Planck energy:      E_P = m_P c² ≈ 1.22×10¹⁹ GeV
  Planck temperature: T_P ≈ 1.42×10³² K
```

### Canonical Citation Set

```
[1] Weinberg, S. (1979).
    "Ultraviolet divergences in quantum theories of gravitation."
    In: General Relativity: An Einstein Centenary Survey,
    eds. Hawking & Israel, Cambridge University Press, pp. 790-831.
    [Book chapter, no arXiv. First use of "asymptotic safety" term.]

[2] Reuter, M. (1998).
    "Nonperturbative evolution equation for quantum gravity."
    Physical Review D 57, 971.
    arXiv: hep-th/9605030 (submitted May 1996)
    URL: https://arxiv.org/abs/hep-th/9605030
    [First nonperturbative FRG for gravity; establishes Reuter fixed point]

[3] Lauscher, O. & Reuter, M. (2005).
    "Fractal Spacetime Structure in Asymptotically Safe Gravity."
    Journal of High Energy Physics 10, 050.
    arXiv: hep-th/0508202 (submitted August 2005)
    URL: https://arxiv.org/abs/hep-th/0508202
    [Proves d_s = 2 at UV fixed point; fractal spacetime; exact, no truncation]

[4] Ambjorn, J., Jurkiewicz, J. & Loll, R. (2005).
    "Spectral Dimension of the Universe."
    Physical Review Letters 95, 171301.
    arXiv: hep-th/0505113 (submitted May 2005)
    URL: https://arxiv.org/abs/hep-th/0505113
    [CDT Monte Carlo: d_s flows 4→2 at short distances; "dynamical dimensional reduction"]

[5] Reuter, M. & Saueressig, F. (2023).
    "The Functional Renormalization Group in Quantum Gravity."
    Handbook of Quantum Gravity, Springer Singapore.
    arXiv: 2302.14152 (submitted February 2023)
    URL: https://arxiv.org/abs/2302.14152
    [Comprehensive modern review: Wetterich equation, fixed-point structure, d_s flow]
```

### Physical Facts Confirmed by These Papers

```
FACT 1: Spacetime is smooth all the way to the Planck scale in AS
  — Unlike loop quantum gravity (discrete spin foam) or string theory, AS predicts
    no minimum length granularity; spacetime remains a manifold even at ℓ_P.
  — The "fractal" behavior is in the effective (scale-dependent) geometry, not topology.

FACT 2: d_s → 2 is an exact result
  — Not a truncation artifact; proven to hold in the full theory assuming the UV
    fixed point exists.
  — Formula: d_s(k) = 4 / (1 + (k/k_0)^2 for smooth interpolation (approximate)

FACT 3: CDT and AS agree on d_s → 2
  — Two completely independent approaches (analytic FRG vs. Monte Carlo path integral)
    give the same answer. This cross-check is strong evidence for the result.
  — CDT finds d_s ≈ 3/2 at the Planck scale (slightly below 2); AS finds exactly 2.
    Discrepancy may be truncation scheme or CDT phase transition artifact.

FACT 4: The UV fixed point is at finite, nonzero coupling
  — Newton's constant G and cosmological constant Λ run to a UV fixed point G*, Λ*
    with G* ≠ 0. The theory is NOT free (asymptotic freedom) but interacting
    (asymptotic safety) at the fixed point.
  — Only one UV-relevant direction at the Reuter fixed point (Newton's constant);
    the theory has one free parameter (confirmed in Einstein-Hilbert truncation).

FACT 5: Asymptotic safety remains unproven in the full 4D theory
  — Evidence is strong within truncations (Einstein-Hilbert, f(R), higher-derivative).
  — Lattice (CDT) results are consistent but not a proof.
  — No rigorous mathematical proof of the fixed point's existence in full QG.
```

### Mechanism Design Implications

```
ADVANTAGE over other QG approaches for device design:
1. Smooth substrate: no need for lattice discretization or spin-foam registers;
   the substrate is a continuum field, easier to manipulate with analogue systems.

2. 2D UV regime: once the device reaches (or simulates) the UV fixed point,
   the effective physics is 2-dimensional — dramatically simpler than 4D.
   Conformal field theories in 2D are exactly solvable (Virasoro algebra).

3. Sign problem: CDT formulation is Lorentzian (causal), not Euclidean.
   The Euclidean sign problem (oscillatory path integral) does not arise.
   This is a genuine computational advantage vs. lattice QCD methods.

CAUTION:
- d_s=2 ≠ the theory is a 2D CFT. Spectral dimension measures diffusion;
  the actual fixed-point action is the full gravitational effective action,
  which remains complex.
- "Scale invariance at the UV fixed point" does not mean all observables are
  trivially computable; it means the beta functions vanish.
```

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
|---------|----------------|---------------|----------------|
| Using "Planck constant" as the relevant scale | Treating h=6.626e-34 J·s as the "Planck-level field" energy scale | Planck constant is a fixed unit of action; "Planck-scale physics" means physics at Planck LENGTH ~1.6e-35 m, i.e., Planck ENERGY ~1.22e19 GeV | Always disambiguate: Planck CONSTANT (h, action) vs Planck LENGTH (ℓ_P, geometry) — they are numerically close but physically unrelated |
| Claiming d_s=2 means 2D Liouville gravity | Asserting that spectral dimension 2 implies the UV fixed point is governed by 2D Liouville quantum gravity | Spectral dimension is a probe property (diffusion exponent); the actual geometry at the fixed point is fractal 4D, not a genuine 2-manifold | The d_s=2 result is a kinematic statement about random walk; the dynamical theory (action, partition function) remains 4-dimensional |
| Treating CDT d_s ≈ 3/2 as equivalent to AS d_s = 2 | Conflating the two results in citations | CDT finds ~3/2, AS finds exactly 2; discrepancy is unresolved and matters for precision claims | Always cite the specific value per approach and note the unresolved discrepancy |

## Results & Parameters

### Analogue Gravity Rescaling Reference

```
Goal: access UV fixed point regime without Planck-energy accelerators.

True Planck scale:      ℓ_P = 1.616×10⁻³⁵ m,  E_P = 1.22×10¹⁹ GeV
                        Would require accelerator ~10,000 light-years long.

Analogue Planck scale:  ℓ_P^eff ~ 10⁻¹⁰ m (atomic lattice spacing)
                        E_P^eff = ℏc/ℓ_P^eff ≈ 2×10⁻²⁴ J ≈ 12 eV (soft X-ray)

Physical realization:   Topological insulator stack with engineered spin-orbit coupling.
                        Analogue model: condensed matter system obeying same RG flow
                        equations as quantum gravity in (2+1)D.

Breakdown scale:        Analogue fails above Debye frequency (~10¹³ Hz in solids).
                        Device requires analogue fidelity to ~10¹⁵ Hz (2 orders beyond
                        current experimental range) — a known engineering gap.

Reference:              Unruh (1981) acoustic black holes; Barcelo-Liberati-Visser (2005)
                        analogue gravity review.
```

### Key Physical Numbers for Mechanism Design

```
Planck length:          ℓ_P ≈ 1.616×10⁻³⁵ m
Planck mass:            m_P ≈ 2.176×10⁻⁸ kg = 1.22×10¹⁹ GeV/c²
Planck energy:          E_P ≈ 1.956×10⁹ J ≈ 1.22×10¹⁹ GeV
Planck time:            t_P ≈ 5.391×10⁻⁴⁴ s
Planck temperature:     T_P ≈ 1.416×10³² K

Holographic capacity at 1 mm² boundary (analogue):
  S_max = A / (4 ℓ_P^eff²) ≈ 10⁻⁶ / (4×10⁻²⁰) ≈ 2.5×10¹³ bits ≈ 3 TB

Spectral dimension:
  Macroscopic:  d_s = 4.00 (classical 4D spacetime)
  Planck scale: d_s = 2.00 (AS) or ~1.5 (CDT)

RG time:
  t = ln(k/k_0) where k is momentum cutoff
  One RG step = integrating out one momentum shell
```

### Status of Asymptotic Safety (as of 2026)

```
CONFIRMED (within truncations):
  - Non-trivial UV fixed point exists in Einstein-Hilbert + f(R) + higher-derivative truncations
  - Spectral dimension flows to 2 at UV fixed point (exact within AS)
  - CDT independently confirms dimensional reduction to ~1.5-2

UNRESOLVED:
  - Existence of fixed point in full (non-truncated) theory: unproven
  - Exact value of d_s in UV: 2 (AS) vs ~1.5 (CDT) — not reconciled
  - Whether AS and CDT describe the same theory: unknown
  - Whether Standard Model matter destabilizes the fixed point: active research

RULED OUT by AS:
  - Planck-scale spacetime discreteness (AS predicts smooth manifold)
  - Trans-Planckian catastrophe (fixed point tames UV divergences)
```

## Verified On

| Project | Context | Details |
|---------|---------|---------|
| HomericIntelligence/Story | M16 asymptotic-safety smooth substrate mechanism design, Myrmidon swarm physics agent | Mechanism file at Research/Mechanisms/M16-asymptotic-safety-substrate.md |
