# How I used AI, and how I checked it

**Tool:** Claude Code (Claude Opus) in the terminal, working in this repo. I set the direction, made the analytical calls, and reviewed every number that reaches the readout. Claude did most of the typing.

## Where it helped

| Step | What AI did | Time saved |
|---|---|---|
| Data profiling | Profiled all five files in minutes: duplicates, blank keys, float-formatted amounts, the $650M outlier, stage dates after the delivery date, repeated stage rows | Most of a first morning |
| Data model | Drafted the staging/core/mart SQL and the sensitivity grid (4 windows x 2 attendance rules) from my spec | Hours of boilerplate |
| Two front ends | Built the static dashboard and the Streamlit app on the same marts, so offering both cost little extra | A day, realistically |
| Validation code | Wrote an independent pandas recomputation and the permutation test | An hour |
| Readout | Generated the slides from the marts so no number is typed by hand | Copy-paste errors avoided |

## How I validated the output

1. **Two implementations, one answer.** Headline KPIs are computed in DuckDB SQL and again from the raw CSVs in pandas ([notebook](notebooks/analysis.ipynb), section 2). The notebook asserts they match.
2. **Build-breaking assertions.** `src/dq_checks.py` holds 11 invariants: cost reconciles to $1.215M, one row per opportunity, no opportunity credited to two events, associated pipeline never exceeds total, and the firm-level mart reconciles to the association bridge. The build fails if any break.
3. **Spot checks against raw data.** I traced firms end to end in the timeline view (for example F041: no events, no meetings, the $650M commitment) and checked them against the CSVs.
4. **Every number in the readout is generated from the marts**, and I read each claim against the dashboard before accepting the wording.
5. **Visual review** of every dashboard tab and every slide as rendered, not just the code.

## Where I changed, corrected, or challenged the AI

- **"Events underperform" became "no detectable lift."** The first comparison showed attendees opening opportunities at lower rates than non-attendees after two of the three events. Read naively, that says events hurt. I pushed back: it ignored each group's starting rate and the June to July surge that hit everyone. We added pre-period rates, a difference-in-differences, and a permutation test. None of the three differences is distinguishable from noise, so the readout says we cannot detect lift, and recommends a holdout design that could.
- **A fragile join.** The first draft of `mart_firm_event` joined the association bridge on event only, then matched the firm in a second join. Totals came out right only because the aggregates ignore the unmatched rows. I had it rewritten to join on event and firm together and added an assertion that the mart reconciles to the bridge.
- **A claim the data did not support.** Draft notebook commentary said the London and Berlin lift "stays at or below zero at every window." The executed output showed Berlin at +3 points at 180 days. The text now says what the table shows.
- **A misleading label.** An opportunity bucket called "Never attended" included firms that were only tentative for an event. Renamed to "No confirmed attendance."
- **Headline wording.** A draft slide title said the London dinner delivered the "same pipeline story at a third of the cost." London's pipeline was half of New York's, so that was wrong. The title now states the cost-per-opportunity comparison, which holds. Similarly, "events reach nearly all priority firms" became "most" (13 of 17 Tier 1).
- **Attribution rule.** The first plan credited opportunities to the first event a firm attended. With 24 firms at two or more events, that would credit March's summit for opportunities opened weeks after a June event. I switched to last touch within the window.
- **Treating future-dated stages as fact.** 19 stage entries are dated after the data was delivered (up to November 2026). Rather than count those commitments, they are treated as projected and shown separately.

## What AI did not decide

Which metrics matter to a Head of IR, the association rule and its limits, how to treat the outlier and projected stages, and the four recommendations. Those are judgment calls, and they are mine.
