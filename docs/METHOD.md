# Method, metric definitions, and assumptions

## The question, broken down

| Leadership question | How it is answered here |
|---|---|
| What happened after each event? | Follow-up meetings (rate, speed, before vs after), new opportunities, stage progress of existing pipeline |
| What outcomes are associated with events? | Opportunities, pipeline, and commitments linked to an event by a timing rule, compared against firms that did not attend |
| What should we learn for future events? | Cost efficiency per event and format, follow-up gaps by tier, segment cuts, data-capture fixes |

## Association, not causation

An opportunity is **event-associated** when the firm attended the event and the opportunity was created 0 to W days after the event date (default W = 90). If more than one attended event qualifies, the most recent one gets credit (last touch), so no opportunity is double-counted.

That rule shows what followed events. It does not show events caused it, because:

- **Selection.** IR invites the firms most likely to invest, and firms choose to come. Attendees differ from non-attendees before the event.
- **Timing and seasonality.** New opportunities peaked in June and July for everyone, attendees or not.
- **No source field.** Opportunities carry no campaign or source tag, so timing is the only link.

To test for lift beyond the base rate, each event's attendees are compared with a comparison group over the same calendar window, before and after the event date (difference-in-differences). That controls for seasonality and for stable differences between the groups. It still does not remove selection on things that change over time.

Two comparison groups are shown, because the choice changes the answer:

- **Firms not at that event** (34 to 41 firms). Most of them (21 to 28) attended one of the other two events, and the events sit inside each other's windows (London falls in NY's 90-day after-window; NY and Berlin fall in London's before and after windows). This group is therefore partly treated.
- **Firms at no event** (13 firms). Clean, but small.

At the default rule the difference-in-differences is NY +12, London -14, Berlin -3 points against the first group, and NY -8, London +8, Berlin +18 against the second. The sign flips for every event, and none is significant under either group. The honest reading is that the data cannot distinguish attendees from non-attendees; no single event's sign should be quoted as evidence.

**Statistical significance.** Each gap is tested with a two-sided permutation test: which firms attended the event is randomly reshuffled 5,000 times, and the p-value is the share of reshuffles that produce a gap at least as large as the observed one. A gap counts as significant only if p < 0.05. At the default rule, p = 0.61 (NY), 0.44 (London), 1.00 (Berlin) against firms not at the event, and 0.84, 0.79, 0.52 against firms at no event; across all 24 window and attendance settings the smallest is 0.07 (NY, 30 days). With 19 to 26 attendees and 13 to 41 comparison firms, a gap would need to be roughly 35 to 40 points to reach significance, so "not significant" means "not detectable at this size", not "no effect". The dashboards show 72 tests (24 settings x 3 events), so a few values below 0.05 would be expected by chance alone; none occurs.

## Dashboard filters

The window and tentative controls read precomputed SQL results. Five more filters recompute every card and chart from firm- and opportunity-level data (`app/metrics.py`, and `docs/metrics.js` for the static page):

| Filter | What it does |
|---|---|
| Event (multi-select) | Shows only the selected events in cards, scorecard and charts. Credit for each opportunity is still assigned across all three events (most recent attended event within the window), so filtering never moves an opportunity to a different event |
| Investor segment (multi-select) | Keeps only firms in the selected segments: attendees, the non-attendee comparison group, and their opportunities |
| Fund (multi-select) | Keeps only opportunities for the selected funds. Attendance, meetings and follow-up do not change |
| Attendee seniority (multi-select) | Counts attendance only where a CIO or Managing Director was registered, or only where none was; selecting both is the same as no filter. Firms dropped by this filter also leave the comparison group, rather than being counted as non-attendees |
| Exclude $650M outlier | Removes O0017. The firm attended no event, so event metrics do not change; totals, the pipeline donut and opportunity charts do |

Event cost is not split by filter, so cost-per-opportunity under a filter is full event cost over the filtered opportunities. With no filters, both engines reproduce the SQL results exactly for all 24 window and attendance settings (`tests/test_metrics.py`, and a self-test the static page runs on load). Under filters, p-values are recomputed with a fresh set of 5,000 reshuffles, so the two dashboards can differ in the second decimal place. Filtered groups are small: read rates as directional.

## Next event planner (Streamlit)

The planner applies 2026 outcomes to a planned event: format, budget and attending firms by tier. It resamples the 2026 firm-level results for each tier 4,000 times (bootstrap, 90-day window, confirmed attendance) and reports the middle estimate with a 10th to 90th percentile range for associated opportunities, pipeline and cost per opportunity. "All 2026 events" pools 70 firm-attendances; "Same format only" uses only that format's events and rests on fewer firms. With London's budget and tier mix it returns London's actual result (13 opportunities, $14K each). It is a planning aid: 2026 showed no evidence of lift from attending, and the follow-up comparison (37% vs 40% conversion, 27 vs 43 firm-events) is too small to credit follow-up speed, so the planner adds no pipeline for follow-up targets.

## Metric definitions

The short list below covers the headline metrics. Every metric on the dashboard, with its source column and how each filter affects it, is in [DATA_DICTIONARY.md](DATA_DICTIONARY.md).

| Metric | Definition |
|---|---|
| Attended firm | Firm with at least one **Confirmed** contact. Tentative-only firms are added only with the "include tentative" toggle. Confirmed is registration status; there is no check-in data. |
| Follow-up rate (30d) | Attending firms with any meeting 1 to 30 days after the event / attending firms |
| Median days to first follow-up | Median days from event to the firm's first later meeting |
| Meetings 60d before / after | Meetings with attending firms in the 60 days before vs after the event |
| Associated opportunities / pipeline | Count / sum of amount for event-associated opportunities, any stage |
| Firm conversion rate | Attending firms with at least one associated opportunity / attending firms |
| Reached due diligence+ | Associated opportunities whose highest actual stage is Due Diligence or later |
| Committed | Opportunity reached Committed on or before the as-of date |
| Cost per associated opportunity | Event cost / associated opportunities |
| New-opportunity rate | Firms opening at least one opportunity in the window / firms in the group |
| Difference-in-differences | (attendee after - attendee before) - (non-attendee after - non-attendee before), in points |
| p-value (permutation test) | Share of 5,000 random reshuffles of attendance that produce a gap at least as large; significant if below 0.05 |
| Open opps advancing | Opportunities open on the event date that moved up at least one stage within the window, attendees vs non-attendees |

## Data-quality decisions

| Issue | Rows | Decision |
|---|---|---|
| Duplicate attendance row (A0011) | 1 | Collapsed |
| Attendee with blank firm_id (A9998, "Unmapped Contact") | 1 | Kept in contact counts, excluded from firm metrics |
| Tentative-only firm attendance | 9 firm-events | Excluded by default, available via toggle |
| Amounts stored as float text (1500000.0, 2500000.0) | 61 | Cast to integer USD; read as small tickets, not a unit error |
| $650M ticket (O0017), next largest $150M | 1 opp | Kept and flagged. It is not linked to any event, so event metrics are unchanged either way |
| Stage dated after the as-of date | 23 raw rows (latest 2026-11-19); 19 after collapsing repeated same-stage rows (latest 2026-10-28) | Treated as projected: excluded from current stage, commitments, and conversion; shown in firm timelines |
| Same stage logged twice | 13 | Collapsed to the first date the stage was reached |
| Duplicate opportunity: O9998 and O9999 identical (same firm, fund, dates, stage, $25M) | 1 opp | Kept O9998, dropped O9999. Found in the independent audit; before the fix it added 1 opportunity and $25M to London's associated commitments |
| Opportunity with no early stages (O9998 logged directly as Committed) | 1 | Kept; funnel counts the stages it reached |
| Out-of-sequence IDs (O9998/O9999, A9998) | 3 | Look like planted test rows. O9998, the kept copy, commits 10 days after creation (others take 28 to 111) and is London's only associated commitment: London commits $25M with it and $0 without; all events $253M with it, $228M without |
| Possible affiliate firm: F028 "Investor Firm 08 Holdings" vs F008 | 1 | Kept separate (segment and history differ). If merged, London gains 2 associated opportunities ($12.5M) |
| No opportunity created after 2026-08-12 | 42 days | The extract has no new opportunities in the last six weeks before the cutoff (July 23, August 5, September 0). Berlin's 90-day window effectively covers about 57 days |
| Two meetings, same firm and day (F007) | 1 pair | Kept; different type and purpose |
| Meetings on a weekend | 38 of 112 | Kept. A third of meetings fall on Saturday or Sunday, which points to generated dates; no metric depends on the weekday |
| First stage logged 5 to 30 days after created_date | all 106 | Kept. created_date reads as the CRM entry date rather than first contact, so the true start of an opportunity may be up to a month later than the date the association window uses |

**As-of date.** 2026-09-23, the analysis cutoff. It is the extract date (the file timestamps inside the delivered zip), chosen over the 2026-09-28 email date so that no stage dated after the extract counts as achieved. A parameter in `src/build.py`.

## Build-time assertions (the build fails if any break)

- 3 events with total cost $1,215,000; 60 unique firms
- One row per opportunity; one firm and one amount per opportunity; no stage before created date
- Every firm in attendance, meetings, and opportunities exists in the firm dimension
- Meetings reconcile to raw
- Each opportunity is credited to at most one event in every sensitivity cell
- Associated pipeline never exceeds total pipeline
- Firm-event mart reconciles to the association bridge

## Known limits

- Three events and 60 firms: every rate is directional.
- Events differ in age at the as-of date (Berlin about 100 days, New York about 195), so commitments favor older events. Compare at equal windows (the 30, 60, and 90 day settings) before judging.
- Registration is not attendance. A check-in field would sharpen every metric.
- The data starts on 2026-01-02, so NY's before-window is short: 69 days of data at both the 90- and 180-day settings (its 90- and 180-day before-rates are identical). At 180 days London's and Berlin's before-windows also start before the data, and their after-windows run past the as-of date (only 125 and 99 days have elapsed). Treat all 180-day comparisons, and NY's at 90 days, as lopsided.
- No opportunity was created after 2026-08-12, 42 days before the as-of date, so the youngest events' after-windows have an empty tail (Berlin about 33 days of its 90).
- Event windows overlap. NY's after-window contains London; Berlin's 60-day "before" meetings include 11 held after the London dinner, 7 with London attendees. The Berlin meeting drop is partly London follow-up rolling off.
- Before and after windows differ by one day: "after" includes the event date (W + 1 days), "before" does not (W days).
- "Associated pipeline" is gross: it includes opportunities later declined ($150M of NY's $829M at the default rule; $150M across all events). The scorecard shows the declined amount beside it.
- The "Attendee, not in window" bucket is mostly opportunities opened before the firm's first event (29 of 39 at the default rule), not after the window closed.
- Meeting counts before and after an event are raw counts for attendees. The scorecard also shows meetings per firm for firms not at the event over the same dates, which fall too in July and August.
- Opportunities created on the event date count as event-associated (one case), even though some may have been opened before the event contact.
- Faster follow-up and conversion: firms met within 30 days converted at 37% vs 40% for those not met (27 vs 43 firm-events). That is too small a sample to say follow-up speed does or does not matter; the 10-day standard in the readout is a service standard to test.
