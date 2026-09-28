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

To test for lift beyond the base rate, each event is compared with **firms that did not attend that event** over the same calendar window, before and after the event date (difference-in-differences). That controls for seasonality and for stable differences between the groups. It still does not remove selection on things that change over time.

**Statistical significance.** Each gap is tested with a two-sided permutation test: which firms attended the event is randomly reshuffled 5,000 times, and the p-value is the share of reshuffles that produce a gap at least as large as the observed one. A gap counts as significant only if p < 0.05. At the default rule, p = 0.61 (NY), 0.44 (London), 1.00 (Berlin); across all 24 window and attendance settings the smallest is 0.07 (NY, 30 days). With 19 to 26 attending firms per event, only very large gaps could reach significance.

## Dashboard filters

The window and tentative controls read precomputed SQL results. Four more filters recompute every card and chart from firm- and opportunity-level data (`app/metrics.py`, and `docs/metrics.js` for the static page):

| Filter | What it does |
|---|---|
| Investor segment | Keeps only firms in that segment: attendees, the non-attendee comparison group, and their opportunities |
| Fund | Keeps only opportunities for that fund. Attendance, meetings and follow-up do not change |
| Attendee seniority | Counts attendance only where a CIO or Managing Director was registered, or only where none was. Firms dropped by this filter also leave the comparison group, rather than being counted as non-attendees |
| Exclude $650M outlier | Removes O0017. The firm attended no event, so event metrics do not change; totals, the pipeline donut and opportunity charts do |

Event cost is not split by filter, so cost-per-opportunity under a filter is full event cost over the filtered opportunities. With no filters, both engines reproduce the SQL results exactly for all 24 window and attendance settings (`tests/test_metrics.py`, and a self-test the static page runs on load). Under filters, p-values are recomputed with a fresh set of 5,000 reshuffles, so the two dashboards can differ in the second decimal place. Filtered groups are small: read rates as directional.

## Metric definitions

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
| Stage dated after the as-of date (2026-09-23, up to 2026-11-19) | 19 stage entries | Treated as projected: excluded from current stage, commitments, and conversion; shown in firm timelines |
| Same stage logged twice | 13 | Collapsed to the first date the stage was reached |
| Opportunity with no early stages (O9999 logged directly as Committed) | 2 | Kept; funnel counts the stages it reached |
| Two meetings, same firm and day (F007) | 1 pair | Kept; different type and purpose |

**As-of date.** 2026-09-23, the date the data extract was delivered. It is a parameter in `src/build.py`.

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
