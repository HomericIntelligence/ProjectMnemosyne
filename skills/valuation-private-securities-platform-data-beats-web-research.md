---
name: valuation-private-securities-platform-data-beats-web-research
description: "When valuing private securities (Reg-CF crowdfunding, pre-IPO equity, private LLCs) for legal disclosure (divorce FL-142, estate tax, FBAR), the investor platform's own portfolio data beats web research for quantitative facts (share counts, cost basis, current marks) but platform marks lag wipeouts by months-to-years. Use platform data as authoritative for quantities; use parallel web research to catch silent wipeouts. Use when: (1) building FL-142 or estate-tax disclosure for a venture-investment LLC, (2) reconciling agent web research against an investor portfolio snapshot, (3) deciding whether to trust platform mark vs independent valuation, (4) a working-paper share total is unsupported by any document — test it as vesting math against known grant sizes, (5) reading a Series Seed SPA Schedule of Purchasers (SAFE conversions vs cash shares), (6) reconciling ISO exercises via Carta holdings plus IRS Form 3921, (7) valuing converted preferred when the issuer has no 409A."
category: documentation
date: 2026-06-12
version: "1.1.0"
user-invocable: false
verification: verified-local
history: valuation-private-securities-platform-data-beats-web-research.history
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
  - form-3921
  - vesting-decomposition
  - schedule-of-purchasers
  - safe-conversion
  - no-409a
---

## Overview

| Field | Value |
|---|---|
| Date | 2026-06-12 |
| Objective | Determine authoritative valuation methodology for private/Reg-CF securities on legal disclosure forms (FL-142, FBAR, estate tax) |
| Outcome | Hybrid methodology: investor platform as primary for quantitative facts; parallel web research as primary for wipeout/closure events; platform sweep is a required pass that catches positions the document archive misses |
| Verification | verified-local |
| Context | Villmow FL-142 §14 disclosure, VillmowFutures LLC, 17 Reg-CF holdings, May 2026; amended after a June 2026 private-equity share-count reconciliation session |
| **History** | [changelog](./valuation-private-securities-platform-data-beats-web-research.history) |

## When to Use

- Building FL-142 Schedule of Assets and Debts (§14 other assets) for a venture-investment LLC
- Preparing FBAR or estate-tax disclosure that includes Reg-CF or pre-IPO equity positions
- Reconciling agent web-research numbers against an investor platform portfolio screenshot
- Deciding whether to trust a platform mark vs an independent agent valuation
- Valuing a portfolio on StartEngine, Carta, AngelList, EquityZen, or similar investor platforms
- Pre-IPO equity reconciliation where bonus shares, splits, or stock-dividend-in-kind credits may have been retroactively applied
- Any divorce disclosure involving a spouse's crowdfunding or angel-investing portfolio
- A working-paper share "total" is unsupported by any document — test whether it is option-vesting math (an exact k/n fraction of a known grant) before accepting it
- Reading a Series Seed SPA "Schedule of Purchasers" (Exhibit A) to distinguish SAFE conversions from new-money cash purchases
- Reconciling ISO exercises: Carta holdings screenshot plus IRS Form 3921 give grant date, exercise date, strike, FMV-at-exercise, and share count
- Valuing converted preferred shares when the issuer has no 409A valuation on file

## Verified Workflow

### Quick Reference (5-Step Methodology)

**Step 1 — Pull the platform snapshot first.**
Before dispatching any research agents, obtain the investor platform's own portfolio page (screenshot, export, or API). Record: share counts, cost basis, current platform-stated value, and any per-position status flags (e.g., "wind-down", "inactive", "IPO'd").

**Step 2 — Dispatch parallel web-research agents (one per holding).**
While processing the platform data, run one Sonnet agent per holding to independently verify: (a) operational status, (b) recent SEC filings or state court records, (c) any wipeout/insolvency/auction events the platform may not have flagged yet.

**Step 3 — Reconcile using the decision rules below and document every discrepancy.**
When platform data and web research disagree, apply the decision rules. In the final disclosure, cite both sources and explain which was used and why.

**Step 4 — Decompose any unsupported share "total" against known grant sizes (vesting-math heuristic).**
Before trusting a working-paper share total that no document supports, test whether it equals an exact k/n fraction of a known option grant on file. Real example: a claimed "83,333 total shares" decomposed as 79,166 + 4,167 — exactly 19/24 and 1/24 of a 100,000-share advisor option, so the "total" was 20/24 of the option (shares vested through a specific month), not a position total. The actual equity position per the executed SPA was 285,184 preferred shares; the platform (Carta) later showed exactly 83,333 vested, confirming the heuristic. Check ratios against every known grant size on file before accepting any share total.

**Step 5 — Cross-check the SPA "Schedule of Purchasers" (Exhibit A) for converted positions.**
In a Series Seed SPA, columns named "Series Seed-N Convertible Security Shares" are SAFE conversions (Convertible Security = SAFE); blank "Cash Shares" columns prove the holder made no new-money purchase. Corroborate the conversion price across ALL investors in the same sub-series column — every row should equal invested-$ ÷ price (e.g. $50,000 → 71,296, $30,000 → 42,777, $200,000 → 285,184 at $0.7013). Use `pdftotext -layout` for these tables; plain `pdftotext` scrambles the columns.

### Carta / Platform Authority

Carta holdings screenshots are authoritative for:

- **Exercise status** — revealed a 100,000-share option FULLY EXERCISED that working papers assumed outstanding (early exercise, no exercise doc in the archive)
- **Vested-to-date counts** — confirmed the 83,333 vested figure from the decomposition heuristic
- **Total share counts and current FMV** — a Carta screenshot plus IRS Form 3921 surfaced an entirely UNDISCLOSED equity position (288,097 shares at the issuer's $0.67 Carta FMV) that three prior document-only validation passes could not catch
- **ISO exercise details via Form 3921** — grant date, exercise date, strike, FMV-at-exercise, and share count

Platform data finds assets that document archives miss. The platform sweep is a required pass, not a nice-to-have.

### No-409A Valuation Fallback

- When the issuer has no 409A, the priced-round conversion price (invested $ ÷ shares received) is a defensible working basis for the converted preferred.
- Carry exercised common as "pending 409A".
- When one position appears in two schedule sections, value it ONCE and cross-reference the other row ("valued at `<item>` to avoid double-count").

### Decision Rules

| Disagreement Type | Which Source Wins | Rationale |
|---|---|---|
| Share count / share quantity | **Platform wins** | Platforms retroactively credit bonus shares, splits, and stock dividends-in-kind that agents cannot reconstruct from public filings |
| Option exercise status | **Platform wins** | Carta records early exercises that leave no document in the archive; absence of an exercise doc is not evidence the option is outstanding |
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
| Trusted working-paper "total grant is 83,333 shares" | Accepted the working-paper figure as a position total | It was option-vesting math (20/24 of 100,000), not a position total; actual SPA position was 285,184 preferred | Decompose unsupported totals against known grant sizes before accepting them |
| Assumed option unexercised because no exercise doc was in the archive | Characterized a 100,000-share option as outstanding based on archive absence | Carta showed the option fully exercised (early exercise) | Pull the platform holdings page before characterizing option status |
| Searched only the document archive for share counts | Ran document-only validation passes over the archive | The real total appeared in zero of 873 archived PDFs; only platform data + Form 3921 had it | Platform sweep is a required pass, not a nice-to-have |

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

### Concrete Numbers (Share-Count Reconciliation, June 2026)

| Metric | Value |
|---|---|
| Working-paper claimed "total shares" | 83,333 (unsupported by any document) |
| Decomposition of 83,333 | 79,166 + 4,167 = 19/24 + 1/24 of a 100,000-share advisor option (i.e. 20/24 vested through a specific month) |
| Actual SPA position (executed SPA) | 285,184 preferred shares |
| Carta vested-to-date | exactly 83,333 (confirmed the decomposition heuristic) |
| SPA Exhibit A conversion price | $0.7013 ($50,000 → 71,296; $30,000 → 42,777; $200,000 → 285,184) |
| Option status correction | 100,000-share option FULLY EXERCISED per Carta; working papers assumed outstanding |
| Undisclosed position surfaced | 288,097 shares at the issuer's $0.67 Carta FMV (Carta screenshot + IRS Form 3921) |
| Archived PDFs searched that contained the real total | 0 of 873 |
| Document-only validation passes that missed it | 3 |

### Discrepancy Pattern Table

| Discrepancy Type | Example | Resolution |
|---|---|---|
| Platform face value vs confirmed $0 wipeout | Island Brands: $1,874.67 face vs $0 actual | Web research wins; document wind-down notice date and source |
| Platform face value vs confirmed $0 wipeout | BlueSky Energy: $5,500.88 face vs $0 actual | Web research wins; document court filing and auction date |
| Agent share-count vs platform share-count | StartEngine: 84 shares (agent) vs 1,680 shares (platform, post 20:1 bonus) | Platform wins; document bonus share event and effective date |
| Agent price-per-share vs platform price | StartEngine equity: Round 5 $1.60 used correctly by platform | Platform wins when no conflicting public secondary-market data |
| Working-paper total vs platform vested count | 83,333 "total" (working paper) vs 83,333 vested of a larger position (Carta) | Platform wins; the working-paper number was vesting math, not a total |
| Archive absence vs platform exercise record | No exercise doc in archive vs Carta "fully exercised" | Platform wins; early exercises can leave no archived paperwork |

### Key Platform Lag Observation

StartEngine's own portfolio page showed $1,874.67 face value for Island Brands at the same time StartEngine's own investor update section displayed the May 2025 wind-down notice. The platform's portfolio valuation system and its investor-communications system are not synchronized — a platform can simultaneously post a wind-down notice and continue displaying the pre-wind-down face value. This is a known class of platform-lag error; web research is the only reliable counter.
