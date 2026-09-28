# How I used AI, and how I checked it

**Tools:** Claude Code (Claude Opus) in the terminal, working in this repo, and Wispr Flow for voice dictation: almost every instruction and piece of feedback I gave was dictated rather than typed. I set the direction and the deliverable design, reviewed and approved the approach, and iterated on the output. Claude wrote the code and drafted the analysis, and validated its own work as it went.

## What I directed

- **Deliverable format.** I chose to build two experiences on the same model: a static HTML page for one-click review, and an interactive Streamlit app for anyone who wants to work in Python.
- **Dashboard design.** I set the visual direction and asked for specific changes:
  - Carlyle branding throughout: logo, navy palette, serif headings.
  - Conversion labels on the cost-per-opportunity and pipeline-and-commitments charts.
  - Donut charts (where pipeline came from, follow-up status of attending firms) and line charts (monthly opportunities and meetings with event markers, cumulative opportunities after each event).
  - Renaming the landing tab to "Executive summary".
  - A section in the Underlying Data and Model tab that explains the source data and the data model.
- **Approach and data model.** Claude proposed the plan: the KPI set and headline cards, the three-layer SQL model, the attribution rule, and how to treat data-quality issues. I reviewed and approved it before any code was written.
- **Testing.** I used both dashboards and caught that the Streamlit controls had stopped responding (the app server had been stopped); it was restarted and every control retested.

## Where AI helped

| Step | What AI did | Time saved |
|---|---|---|
| Data profiling | Profiled all five files: duplicates, blank keys, float-formatted amounts, the $650M outlier, stage dates after the delivery date, repeated stage rows | Most of a first morning |
| Data model | Wrote the staging, core, and mart SQL and the sensitivity grid (4 windows x 2 attendance rules) | Hours of boilerplate |
| Two front ends | Built the static page and the Streamlit app on the same marts, so offering both cost little extra | About a day |
| Validation code | Wrote an independent pandas recomputation and a permutation test | An hour |
| Readout | Generated the slides from the marts so no number is typed by hand | Copy-paste errors avoided |

## How the output was validated

1. **Two implementations, one answer.** Headline KPIs are computed in DuckDB SQL and again from the raw CSVs in pandas ([notebook](notebooks/analysis.ipynb), section 2). The notebook asserts they match.
2. **Build-breaking assertions.** `src/dq_checks.py` holds 11 checks: cost reconciles to $1.215M, one row per opportunity, no opportunity credited to two events, associated pipeline never exceeds total, and the firm-level table reconciles to the attribution table. The build fails if any break.
3. **Spot checks against raw data.** Firms were traced end to end in the timeline view (for example F041: no events, no meetings, the $650M commitment) and checked against the CSVs.
4. **Every number in the readout is generated from the marts**, so the slides cannot drift from the dashboard.
5. **Visual review** of every dashboard tab and slide as rendered, not just the code.

## Corrections made along the way

Claude caught most of these during its own validation passes; I reviewed each fix.

- **"Events underperform" became "no detectable lift."** The first comparison showed attendees opening opportunities at lower rates than non-attendees after two of three events. That ignored each group's starting rate and the June to July surge that hit everyone. Pre-period rates, a difference-in-differences, and a permutation test were added. None of the three differences is statistically significant (two-sided permutation test, p = 0.44 to 1.00 against a 0.05 threshold), so the readout says lift cannot be detected and recommends a holdout design that could detect it.
- **A fragile join.** An early version of `mart_firm_event` joined the attribution table on event only and matched the firm in a second join. Totals were right only because the aggregates ignored unmatched rows. It was rewritten to join on event and firm together, with a new reconciliation check.
- **A claim the data did not support.** Draft notebook text said London and Berlin lift "stays at or below zero at every window." The output showed Berlin at +3 points at 180 days. The text now matches the table.
- **A misleading label.** A bucket called "Never attended" included firms that were only tentative. Renamed to "No confirmed attendance."
- **Headline wording.** A draft slide said the London dinner delivered the "same pipeline story at a third of the cost." London's pipeline was half of New York's, so the title now states the cost-per-opportunity comparison. "Events reach nearly all priority firms" became "most" (13 of 17 Tier 1).
- **Attribution rule.** An early plan credited opportunities to the first event a firm attended. With 24 firms at two or more events, that would credit March's summit for opportunities opened weeks after a June event. Changed to the most recent event within the window.
- **Future-dated stages.** 19 stage entries are dated after the data was delivered (up to November 2026). They are treated as projected rather than counted as commitments.
