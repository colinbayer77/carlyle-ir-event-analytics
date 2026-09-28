# How I used AI, and how I checked it

**Tools:** Claude Code in the terminal, working in this repo, with two models: Claude Opus for the build and most of the iteration, and Claude Fable for a final quality pass over the data model. Wispr Flow for voice dictation: almost every instruction and piece of feedback I gave was dictated rather than typed. I set the direction and the deliverable design, reviewed and approved the approach, and iterated on the output. Claude wrote the code and drafted the analysis.

## 1. Where AI helped me

| Step | What AI did |
|---|---|
| Data profiling | Profiled all five files: duplicates, blank keys, float-formatted amounts, the $650M outlier, stage dates after the delivery date, repeated stage rows |
| Data model | Wrote the staging, core, and mart SQL and the sensitivity grid (4 windows x 2 attendance rules) |
| Two front ends | Built the static page and the Streamlit app on the same marts, so offering both cost little extra |
| Validation code | Wrote an independent pandas recomputation, build-breaking assertions, a permutation test, and Streamlit UI tests |
| Readout | Generated the slides from the marts so no number is typed by hand |
| Audit | Ran a separate agent that recomputed every number from the raw CSVs without reusing the project code |

What I directed, rather than delegated:

- **Deliverable format.** Two experiences on one model: a static HTML page for one-click review, and a Streamlit app for anyone who wants to work in Python.
- **Dashboard design.** Carlyle branding (logo, navy palette, serif headings); conversion labels on the cost and pipeline charts; donut and line charts; an Event Scorecard tab; filters for event, investor segment, fund, attendee seniority, and the $650M outlier; a Firm explorer with click-to-select rows and a pipeline-by-stage chart; a Next Event Planner; and a data-model section on the data tab.
- **Approach and data model.** Claude proposed the KPI set, the three-layer SQL model, the attribution rule, and the data-quality handling. I reviewed and approved the plan before any code was written.
- **Testing.** I used both dashboards throughout and reported what was wrong: controls that had stopped responding, duplicate filters on a tab, a timeline panel stuck on one firm, card titles pushed off center by their tooltips.

## 2. How it accelerated my work

- **Claude Code did the typing.** The SQL model, two dashboards, tests, notebook and readout are several days of hands-on work. Claude produced first versions in hours, which left my time for the analytical calls and for review.
- **Wispr Flow removed the keyboard.** I dictated nearly every instruction. Requests like "center the data labels inside the bars and remove the y-axis" take a few seconds to say and a few minutes for Claude to apply across both dashboards. That made it cheap to iterate on the design until it was right.
- **Cheap iteration changed what I asked for.** Because each change cost minutes, I asked for things I would otherwise have skipped: a multi-select on every filter, dollar labels on the Sankey, a stage filter inside a chart, a planner tab. The dashboard ended up more polished than a two-day budget would normally allow.
- **Generated, not typed, numbers.** Every figure in the readout, README and dashboard text is pulled from the marts at build time, so a rebuild after the audit fix updated all of them at once.

## 3. How I validated the output

Two models, three independent implementations, and a human in the loop.

1. **Two implementations, one answer.** Headline KPIs are computed in DuckDB SQL and again from the raw CSVs in pandas ([notebook](notebooks/analysis.ipynb), section 2). The notebook asserts they match. The static page's JavaScript engine also checks itself against the SQL results on every load, for all 24 window and attendance settings.
2. **Build-breaking assertions.** `src/dq_checks.py` holds 11 checks: cost reconciles to $1.215M, one row per opportunity, no opportunity credited to two events, associated pipeline never exceeds total, and the firm-level table reconciles to the attribution table. The build fails if any break.
3. **An independent audit by a separate agent.** After the build, a second Claude agent recomputed every metric from the raw CSVs with fresh code, without reading the project's SQL or engine. It compared 6,246 values against the marts. 6,234 matched; the rest were one definition choice and random permutation noise. It also found a duplicate opportunity the build had missed (section 4). After the fix it re-ran and matched 6,220 of 6,220.
4. **A model switch for the final quality check.** The build and iteration used Claude Opus. For the last pass over the data model I switched to Claude Fable and asked for a full data-cleansing review: duplicates, data types, missing values, join integrity, grain and fan-out, stage-order logic, date ranges. Using a second model guards against one model's blind spots; the two agreed on every material finding, and Fable's pass added two informational findings (weekend meeting dates, and a lag between created_date and the first logged stage) to the data-quality log.
5. **UI tests.** `tests/test_streamlit_app.py` drives the Streamlit app headlessly and checks the headline number under every filter, that filters survive a visit to the planner, and that the planner's defaults reproduce London's actual 2026 result.
6. **Spot checks and visual review.** Firms were traced end to end in the timeline view (for example F041: no events, no meetings, the $650M commitment) and checked against the CSVs. Every dashboard tab and slide was reviewed as rendered, not just as code.

## 4. Where AI-generated work was changed, corrected, or challenged

Claude caught most of these in its own validation passes; the audit agent and I caught the rest. I reviewed each fix.

- **"Events underperform" became "no detectable lift."** The first comparison showed attendees opening opportunities at lower rates than non-attendees after two of three events. That ignored each group's starting rate and the June to July surge that hit everyone. Pre-period rates, a difference-in-differences, and a permutation test were added. None of the three differences is statistically significant (two-sided permutation test, p = 0.44 to 1.00 against a 0.05 threshold), so the readout says lift cannot be detected and recommends a holdout design that could detect it.
- **A duplicate opportunity the first pass missed.** The audit agent found that O9998 and O9999 are the same $25M commitment entered twice, both credited to the London dinner. The build now removes the duplicate and logs it: associated opportunities went from 38 to 37, associated commitments from $278M to $253M, and London's cost per opportunity from $13K to $14K. No conclusion changed, but three headline numbers did.
- **A fragile join.** An early version of `mart_firm_event` joined the attribution table on event only and matched the firm in a second join. Totals were right only because the aggregates ignored unmatched rows. It was rewritten to join on event and firm together, with a new reconciliation check.
- **A claim the data did not support.** Draft notebook text said London and Berlin lift "stays at or below zero at every window." The output showed Berlin at +3 points at 180 days. The text now matches the table.
- **A misleading label.** A bucket called "Never attended" included firms that were only tentative. Renamed to "No confirmed attendance."
- **Headline wording.** A draft slide said the London dinner delivered the "same pipeline story at a third of the cost." London's pipeline was half of New York's, so the title now states the cost-per-opportunity comparison. "Events reach nearly all priority firms" became "most" (13 of 17 Tier 1).
- **Attribution rule.** An early plan credited opportunities to the first event a firm attended. With 24 firms at two or more events, that would credit March's summit for opportunities opened weeks after a June event. Changed to the most recent event within the window.
- **Future-dated stages.** 19 stage entries are dated after the data was delivered (up to October 2026). They are treated as projected rather than counted as commitments.
- **Rounding that disagreed across surfaces.** After the duplicate fix, the readout showed $252M and the dashboards $253M for the same $252.5M. The Python formatters now round the same way as the page.
- **UI defects I found by using the app.** Streamlit controls that had stopped responding, page filters duplicated on the Firm explorer, a timeline panel that stayed on one firm after filtering, and card titles pushed off center by their tooltip icons. Each was fixed and, where possible, covered by a test.
