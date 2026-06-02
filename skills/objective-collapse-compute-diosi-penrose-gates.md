---
name: objective-collapse-compute-diosi-penrose-gates
description: "Physics facts and no-go results for using objective wavefunction collapse (GRW/CSL/Diósi-Penrose) as a computational primitive in sci-fi mechanism design. Use when: (1) designing a fictional device that uses gravitational collapse as a compute gate, (2) citing real papers on collapse models for worldbuilding, (3) evaluating no-go cascades (FTL signaling, energy non-conservation, decoherence) for collapse-based compute proposals."
category: architecture
date: 2026-06-01
version: "1.0.0"
user-invocable: false
verification: unverified
tags: [physics, quantum-foundations, collapse-models, diosi-penrose, grw, csl, scifi, worldbuilding, mechanism-design]
---

# Objective-Collapse Compute — Diósi-Penrose Gates

## Overview

| Field | Value |
|-------|-------|
| **Date** | 2026-06-01 |
| **Objective** | Characterize objective-collapse theories (GRW/CSL/Diósi-Penrose) as controllable computational primitives for a sci-fi reality-simulation device |
| **Outcome** | Complete mechanism document written (M29); key no-go cascades identified; real citations verified |
| **Verification** | unverified — theoretical research exercise, not implemented |

## When to Use

- Designing a fictional device that uses gravitational wavefunction collapse as a computation gate
- Citing real physics papers for objective-collapse theories (GRW, CSL, Diósi-Penrose)
- Evaluating which hard walls a collapse-based compute scheme breaks vs. preserves
- Checking experimental constraints before claiming a collapse model is viable
- Investigating the "collapse as measurement / true-random oracle" framing for sci-fi tech

## Verified Workflow

> **Warning:** This workflow has not been validated end-to-end. Treat as a hypothesis — verification level is `unverified`. All findings are theoretical research, not implemented code.

### Quick Reference

```
Key formula: τ_DP = ℏ / E_Δ
where E_Δ = (G/2) ∫∫ [ρ_A(r) − ρ_B(r)][ρ_A(r') − ρ_B(r')] / |r − r'| d³r d³r'

Experimental constraint: parameter-free DP model EXCLUDED by Donadi et al. 2021
Surviving region: smearing length R₀ > 10⁻⁷ m

FTL no-go: Abrams-Lloyd 1998 — any nonlinear QM modification enables superluminal signaling
Energy no-go: CSL/DP predict steady energy injection ∝ ℏλ/m_P² × ∫|∇ρ|² d³r
```

### Core Physics Facts

1. **GRW (1986):** First spontaneous-collapse theory. Each particle collapses spatially at Poisson rate λ_GRW ≈ 10⁻¹⁶ s⁻¹. Collapse is random in time, Born-rule weighted in space, with localization width σ ≈ 10⁻⁷ m. Reference: Ghirardi, Rimini, Weber, *Phys. Rev. D* 34:470 (1986). DOI: 10.1103/PhysRevD.34.470

2. **Diósi-Penrose (DP) model:** Collapse timescale τ = ℏ/E_Δ where E_Δ is the gravitational self-energy of the difference between the two superposed mass distributions. Diósi (1989): *Phys. Rev. A* 40:1165. DOI: 10.1103/PhysRevA.40.1165. Penrose (1996): *Gen. Rel. Grav.* 28:581. DOI: 10.1007/BF02105068. This is the most physically motivated collapse model because it attributes collapse to a physical cause (incompatible spacetime geometries).

3. **CSL (Continuous Spontaneous Localization):** Continuous version of GRW; collapse is gradual rather than instantaneous. Both CSL and DP predict steady energy non-conservation: dE/dt ∝ ℏλ/m_P² × ∫|∇ρ(r)|² d³r. This is an internal theoretical problem — not just a constraint but a known anomaly requiring fixes (dissipative CSL; see Smirne & Bassi 2015).

4. **Canonical review:** Bassi et al. (2013), *Rev. Mod. Phys.* 85:471. DOI: 10.1103/RevModPhys.85.471. Covers all major collapse models, experimental constraints, underlying theories. The go-to reference for collapse model parameter space.

5. **Experimental exclusion:** Donadi et al. (2021), *Nature Physics* 17:74. DOI: 10.1038/s41567-020-1008-4. Gran Sasso underground laboratory, high-purity germanium detectors. The natural parameter-free DP model is experimentally ruled out. Modified versions with smearing length R₀ > 10⁻⁷ m survive. The X-ray emission bound is three orders of magnitude stronger than previous limits.

### Collapse as Computation — What Works and What Doesn't

6. **What collapse gives you:** A physically real, nonlinear, irreversible projection onto a definite classical outcome. This is: (a) a true-random-number generator seeded by quantum gravity noise; (b) a nonlinear decision gate (projection = AND/SELECT step); (c) automatic branch pruning — no exponential Hilbert-space tracking required (defeats Wall 4). Each collapse event produces exactly 1 classical bit.

7. **What collapse does NOT give you automatically:** Universal computation. Collapse alone is a random oracle; without an engineered preparation Hamiltonian H_prep whose Born-rule statistics match the target physics propagator, the output is noise. The H_prep engineering problem is computationally equivalent to the original simulation — a circularity no-go.

8. **FTL signaling no-go (Abrams-Lloyd 1998):** Any nonlinear modification to quantum mechanics enables superluminal signaling. Abrams, D. S. & Lloyd, S. (1998), *Phys. Rev. Lett.* 81:3992. DOI: 10.1103/PhysRevLett.81.3992. Escape: require that the nonlinearity is "operationally linear" — collapse only affects state dynamics, not measurement statistics. Objective-collapse theories are designed with this escape in mind, but engineered feedback loops (collapse-conditioned preparation) may violate it.

9. **Decoherence kill:** Macroscopic mechanical resonators decohere far faster than collapse. Even at 10 mK, decoherence time for a ~10⁻¹⁰ kg object is typically femtoseconds. Any claim of Planck-rate (t_P ≈ 5.39×10⁻⁴⁴ s) collapse gate cycles requires eliminating environmental decoherence by ~40 orders of magnitude — requiring new physics.

### Sci-Fi Mechanism Design Guidance

10. **"Father finds new physics" mapping:** Two decisive discoveries cover all new physics needed: (a) The Planck-torsion field that amplifies gravitational self-energy E_Δ by ~10⁴⁴× to reach Planck-timescale collapse rates. (b) The H_prep correspondence principle — that collapse statistics can be engineered to match the target physics propagator. These are two single decisive discoveries rather than a catalogue of miracles.

11. **Walls defeated without new physics:** Wall 4 (exponential Hilbert space) — collapse enforces single-trajectory simulation; Wall 11 (analog precision) — collapse is binary/digital; Wall 1 (Holevo) — each collapse extracts exactly 1 bit, exploited at the limit. Wall 7 (computational irreducibility) is embraced rather than defeated: the device enacts reality rather than predicting it.

12. **Walls requiring new physics:** Wall 9 (gravity too weak — needs torsion amplifier), Wall 2 (Landauer — needs branch-erasure energy recycling), Wall 3 (cube-square thermal — needs graviton-mediated I/O instead of photonic).

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
|---------|----------------|---------------|----------------|
| Parameter-free DP as direct gate | Use natural (no free parameter) Diósi-Penrose model for collapse timing | Experimentally excluded by Donadi et al. 2021 (Gran Sasso) | Must use modified DP with R₀ > 10⁻⁷ m as free engineering parameter |
| Collapse as deterministic gate | Use collapse outcome to implement deterministic logic directly | Born-rule randomness makes individual outcomes unpredictable; requires many-shot statistics | Collapse is a random oracle, not a deterministic gate; useful only with engineered Born-rule distributions matching target propagator |
| Photonic readout for 10²⁰ nodes | Read each collapse node optically | ~10³⁰ W waste heat; physically impossible in handheld | Graviton-mediated or correlated-readout scheme needed (requires new physics) |
| Real-time prediction via collapse | Use device to predict physics faster than real time | Wall 7 (computational irreducibility) — collapse simulation IS the physics; it enacts, doesn't predict | Collapse-based simulation is inherently real-time-only, not predictive |

## Results & Parameters

### Key Constants for DP Collapse Timing

```
ℏ = 1.055 × 10⁻³⁴ J·s
G = 6.674 × 10⁻¹¹ m³ kg⁻¹ s⁻²
t_P (Planck time) = √(ℏG/c⁵) ≈ 5.39 × 10⁻⁴⁴ s
m_P (Planck mass) = √(ℏc/G) ≈ 2.176 × 10⁻⁸ kg

τ_DP = ℏ / E_Δ
For M_node = 10⁻¹⁰ kg, δx = 100 nm, τ_DP ≈ milliseconds (too slow for compute)
For τ → t_P: need E_Δ → E_P ≈ 1.956 × 10⁹ J → requires Planck-mass configurations or new-physics amplifier
```

### Experimental Constraint Summary (Donadi 2021)

```
Excluded: parameter-free DP model (R₀ = r_nucleon ≈ 10⁻¹⁵ m)
Surviving: R₀ > 10⁻⁷ m (smeared mass density)
Method: X-ray emission from electron diffusion in Ge detectors at Gran Sasso
Sensitivity: 3 orders of magnitude improvement over previous bounds
```

### Energy Non-Conservation Rate (CSL/DP)

```
dE/dt ≈ (ℏ λ_CSL / m_P²) × ∫ |∇ρ(r)|² d³r

For CSL parameters (λ ≈ 10⁻¹⁶ s⁻¹, r_C ≈ 10⁻⁷ m):
Per nucleon contribution ≈ 10⁻²¹ eV/s (negligible individually)
For N = 10²⁰ engineered nodes: aggregate heating potentially catastrophic
```

### Citation Quick Reference

```
GRW 1986:       Phys. Rev. D 34:470    DOI: 10.1103/PhysRevD.34.470
Diósi 1989:     Phys. Rev. A 40:1165   DOI: 10.1103/PhysRevA.40.1165
Penrose 1996:   Gen. Rel. Grav. 28:581  DOI: 10.1007/BF02105068
Bassi 2013:     Rev. Mod. Phys. 85:471  DOI: 10.1103/RevModPhys.85.471
Donadi 2021:    Nature Physics 17:74    DOI: 10.1038/s41567-020-1008-4
Abrams-Lloyd 1998: PRL 81:3992         DOI: 10.1103/PhysRevLett.81.3992
```

## Verified On

| Project | Context | Details |
|---------|---------|---------|
| HomericIntelligence/Story | M29 mechanism design for sci-fi reality-simulation device | M29-objective-collapse-compute.md |
