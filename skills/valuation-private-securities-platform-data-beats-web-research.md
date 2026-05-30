---
name: valuation-private-securities-platform-data-beats-web-research
description: "When valuing private securities (Reg-CF crowdfunding, pre-IPO equity, private LLCs) for legal disclosure (divorce FL-142, estate tax, FBAR), the investor platform's own portfolio data beats web research for quantitative facts (share counts, cost basis, current marks) but platform marks lag wipeouts by months-to-years. Use platform data as authoritative for quantities; use parallel web research to catch silent wipeouts. Use when: (1) building FL-142 or estate-tax disclosure for a venture-investment LLC, (2) reconciling agent web research against an investor portfolio snapshot, (3) deciding whether to trust platform mark vs independent valuation."
category: documentation
date: 2026-05-30
version: "1.0.0"
user-invocable: false
verification: verified-local
tags:
  - private-securities
  - crowdfunding
  - reg-cf
  - startengine
  - valuation
  - due-diligence
  - fl-142
  - divorce-disclosure
  - platform-data
  - web-research
  - investor-platform-primary-source
---

## Overview

| Field | Value |
|---|---|
| Date | 2026-05-30 |
| Objective | Determine authoritative valuation methodology for private/Reg-CF securities on legal disclosure forms (FL-142, FBAR, estate tax) |
| Outcome | Hybrid methodology: investor platform as primary for quantitative facts; parallel web research as primary for wipeout/closure events |
| Verification | verified-local |
| Context | Villmow FL-142 §14 disclosure, VillmowFutures LLC, 17 Reg-CF holdings, May 2026 |

## When to Use

- Building FL-142 Schedule of Assets and Debts (§14 other assets) for a venture-investment LLC
- Preparing FBAR or estate-tax disclosure that includes Reg-CF or pre-IPO equity positions
- Reconciling agent web-research numbers against an investor platform portfolio screenshot
- Deciding whether to trust a platform mark vs an independent agent valuation
- Valuing a portfolio on StartEngine, Carta, AngelList, EquityZen, or similar investor platforms
- Pre-IPO equity reconciliation where bonus shares, splits, or stock-dividend-in-kind credits may have been retroactively applied
- Any divorce disclosure involving a spouse's crowdfunding or angel-investing portfolio

## Verified Workflow

### Quick Reference (3-Step Methodology)

**Step 1 — Pull the platform snapshot first.**
Before dispatching any research agents, obtain the investor platform's own portfolio page (screenshot, export, or API). Record: share counts, cost basis, current platform-stated value, and any per-position status flags (e.g., "wind-down", "inactive", "IPO'd").

**Step 2 — Dispatch parallel web-research agents (one per holding).**
While processing the platform data, run one Sonnet agent per holding to independently verify: (a) operational status, (b) recent SEC filings or state court records, (c) any wipeout/insolvency/auction events the platform may not have flagged yet.

**Step 3 — Reconcile using the decision rules below and document every discrepancy.**
When platform data and web research disagree, apply the decision rules. In the final disclosure, cite both sources and explain which was used and why.

### Decision Rules

| Disagreement Type | Which Source Wins | Rationale |
|---|---|---|
| Share count / share quantity | **Platform wins** | Platforms retroactively credit bonus shares, splits, and stock dividends-in-kind that agents cannot reconstruct from public filings |
| Cost basis / purchase price | **Platform wins** | Platform recorded the original investment transaction |
| Current per-share price | **Platform wins** (unless wipeout confirmed) | Platform has access to latest round pricing or secondary market data |
| Wipeout / insolvency / wind-down | **Web research wins** | Platform marks lag wipeout events by months-to-years |
| Operational status (active vs closed) | **Web research wins** | Agents find court filings, news, and state records the platform mark hasn't caught |
| Classification / sector / description | **Web research wins** | Platform descriptions are often stale marketing copy |

**When documenting a discrepancy:** Use language such as: "StartEngine portfolio shows $5,500.88 face value; independent research confirms Austrian parent BlueSky Energy GmbH filed insolvency Wels Regional Court fall 2022 and Aurena auction liquidation Aug 7 2023. FMV = $0."

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
|---|---|---|---|
| Trusted agent web-research alone for share count | Agent extrapolated 84 original shares × $1.60 Round 5 price = $134.40 for StartEngine equity position | Missed the 20:1 share bonus retroactively credited by StartEngine (84 × 20 = 1,680 shares); correct value was $2,688 — agent was off by $2,554 | Always pull the platform portfolio first; agents cannot reconstruct retroactive bonus shares from public filings |
| Trusted platform mark alone for fairness | Relied on StartEngine portfolio's $1,874.67 face value for Island Brands ABH HoldCo | Platform mark was stale — StartEngine's own investor-update section had posted a May 2025 wind-down notice declaring equity = $0 more than a year earlier; platform portfolio and communications systems were not synchronized | Always run independent web research even when platform shows a positive non-zero value; a platform can simultaneously post a wind-down notice and display the pre-wind-down face value |
| Assigned one agent to handle multiple holdings | Dispatched a single research agent to cover multiple Reg-CF holdings in one prompt | Agent conflated similar company names (e.g., "BlueSky Energy" USA startup vs "BlueSky Energy GmbH" Austrian parent), produced lower-confidence results, and missed the Austrian Wels Regional Court insolvency | Dispatch exactly one agent per holding; see companion swarm-orchestration skill for parallel dispatch pattern |

## Results & Parameters

### Concrete Numbers (Villmow FL-142, May 2026)

| Metric | Value |
|---|---|
| Total cost basis (all 17 holdings) | $75,392.12 |
| StartEngine portfolio face value (all 17) | $100,016.87 |
| Realistic FMV after confirmed wipeouts | $92,641.32 |
| Confirmed wipeouts (FMV = $0) | 2 |
| Island Brands — cost basis | $1,035.00 |
| Island Brands — StartEngine face value | $1,874.67 |
| Island Brands — confirmed FMV | $0 (May 2025 wind-down notice) |
| BlueSky Energy — cost basis | $5,177.00 |
| BlueSky Energy — StartEngine face value | $5,500.88 |
| BlueSky Energy — confirmed FMV | $0 (Wels Regional Court insolvency fall 2022; Aurena auction Aug 7 2023) |

### Discrepancy Pattern Table

| Discrepancy Type | Example | Resolution |
|---|---|---|
| Platform face value vs confirmed $0 wipeout | Island Brands: $1,874.67 face vs $0 actual | Web research wins; document wind-down notice date and source |
| Platform face value vs confirmed $0 wipeout | BlueSky Energy: $5,500.88 face vs $0 actual | Web research wins; document court filing and auction date |
| Agent share-count vs platform share-count | StartEngine: 84 shares (agent) vs 1,680 shares (platform, post 20:1 bonus) | Platform wins; document bonus share event and effective date |
| Agent price-per-share vs platform price | StartEngine equity: Round 5 $1.60 used correctly by platform | Platform wins when no conflicting public secondary-market data |

### Key Platform Lag Observation

StartEngine's own portfolio page showed $1,874.67 face value for Island Brands at the same time StartEngine's own investor update section displayed the May 2025 wind-down notice. The platform's portfolio valuation system and its investor-communications system are not synchronized — a platform can simultaneously post a wind-down notice and continue displaying the pre-wind-down face value. This is a known class of platform-lag error; web research is the only reliable counter.
