# Data dictionary

Every metric shown on the dashboards, with its exact definition, the table and column it comes from, and how the page filters affect it. "Default rule" means the 90-day association window with confirmed attendance only, and no other filters.

## Conventions used throughout

| Term | Meaning |
|---|---|
| As-of date | 2026-09-23, the analysis cutoff. It is the extract date (the file timestamps inside the delivered zip), chosen over the 2026-09-28 email date so that no stage dated after the extract counts as achieved. A parameter in `src/build.py`. Stage entries dated later are "projected" and never count as achieved. |
| Attended / attending firm | A firm with at least one **Confirmed** registrant at the event. With the "Include tentative firm registrations as attendance" toggle on, any registrant counts. Registration is not check-in; the data has no check-in field. |
| Firm-event | One firm's attendance at one event. A firm at two events is two firm-events. 70 confirmed firm-events in 2026 (79 including tentative-only). |
| Association window (W) | Days after an event during which a newly created opportunity can be linked to it: 30, 60, 90 (default) or 180. |
| Event-associated opportunity | An opportunity whose firm attended an event and whose `created_date` falls 0 to W days after that event's date (both ends inclusive). If more than one attended event qualifies, the **most recent** one gets credit, so an opportunity is never counted twice. |
| Comparison groups | Two are shown. **Firms not at the event**: for each event, every firm in scope that did not attend that event; this includes attendees of the other two events (21 to 28 of the 34 to 41 firms), so it is partly treated. **Firms at no event**: firms that attended none of the three events under the current rule (13 at the default rule); clean but small. Firms removed by the seniority filter are dropped from both groups rather than treated as non-attendees. |
| Window before / after | For rates that compare before and after an event: "after" is [event date, event date + W]; "before" is [event date - W, event date). |
| Stage rank | Initial Conversation 1, Follow-up / VDR 2, Due Diligence 3, IC / Documentation 4, Committed 5. Declined is terminal and ranked 0. |
| Actual vs projected stage | Actual: `stage_date` on or before the as-of date. Projected: after it. Only actual stages set an opportunity's current stage, outcome and highest stage reached. |
| Outcome | Committed if an actual Committed stage exists; Declined if an actual Declined stage exists; otherwise Open. |
| Pipeline ($) | Sum of `opportunity_amount_usd`, at any stage, including opportunities later declined, unless the text says committed. Each opportunity has one amount that never changes. |
| Tier | The firm's `priority` field: Tier 1, 2 or 3. |

## Executive summary cards

Source: `mart_event_kpis` summed across the selected events, except where noted. All respond to every page filter.

| Card | Definition | Source |
|---|---|---|
| Event spend | Sum of `cost_usd` for the selected events. Not split by any other filter. | `dim_event.cost_usd` |
| Firms reached | Distinct firms that attended at least one selected event. Sub-label: number of covered firms (60, or those in the selected segments). | `fct_firm_event` |
| Associated opportunities | Count of event-associated opportunities across the selected events. Sub-label: total opportunities in scope (106 after removing one duplicate; fewer under the fund, segment or outlier filters). | `bridge_opp_event` → `fct_opportunity` |
| Associated pipeline | Sum of amounts of the associated opportunities, gross (declined opportunities included; $150M at the default rule). Sub-label: event spend / associated opportunities. | `fct_opportunity.amount_usd` |
| Associated commitments (face value) | Sum of amounts of associated opportunities whose outcome is Committed. Face value of the opportunity, not capital called. Sub-label: their count. | `fct_opportunity` |
| Follow-up within 30 days | Firm-events with at least one meeting 1 to 30 days after the event / attending firm-events. Sub-label: the two counts. | `fct_firm_event`, `fct_meeting` |

The "What leadership should take away" box is fixed at the default rule and does not respond to filters; its numbers are generated from the marts at load time.

## Event scorecard (one column per event)

Source: `mart_event_kpis`, one row per event per window per attendance rule.

| Row | Definition | Column |
|---|---|---|
| Date / type | Event date (mm-dd-yyyy) and event type (Conference or Hospitality). | `event_date`, `event_type` |
| Cost | Event cost. | `cost_usd` |
| Firms attended (Tier 1) | Attending firms, with the Tier 1 count in brackets. | `firms_attended`, `tier1_firms` |
| Cost per firm | Cost / firms attended. | `cost_per_firm` |
| Follow-up within 30d | Attending firms with a meeting 1 to 30 days after the event / attending firms. | `followup_rate_30` |
| Median days to first follow-up | Median, over attending firms that had any later meeting, of days from the event to that firm's first meeting after it. Firms with no later meeting are excluded. | `median_days_to_followup` |
| Meetings 60d before → after | Meetings with attending firms in the 60 days before the event (excluding the event day) → in the 60 days after (excluding the event day). Counts meetings, not firms. | `meetings_pre_60`, `meetings_post_60` |
| Meetings per firm, before → after (attendees; firms not at event) | The same 60-day meeting counts divided by the number of firms in each group, so events of different size and the seasonal trend can be compared. Meetings with firms not at the event use the same dates. Berlin's "before" window includes 11 meetings held after the London dinner. | `meetings_pre_60`, `meetings_post_60`, `non_attendee_meetings_pre_60`, `non_attendee_meetings_post_60` |
| Associated opportunities | Event-associated opportunities credited to this event. | `assoc_opps` |
| Firms converting | Attending firms with at least one associated opportunity / attending firms. | `firm_conversion_rate` |
| Associated pipeline (of which declined) | Sum of amounts of this event's associated opportunities, with the declined part in brackets. | `assoc_pipeline_usd`, `assoc_declined_usd` |
| Reached due diligence+ | Associated opportunities whose highest actual stage rank is 3 or more (Due Diligence, IC / Documentation or Committed). | `assoc_opps_reached_dd` |
| Committed (face value) | Sum of amounts of this event's associated opportunities with outcome Committed, and their count. London's only commitment is O9998, a flagged record (see the data-quality log). | `assoc_committed_usd`, `assoc_committed_opps` |
| Cost per associated opp | Cost / associated opportunities. Blank when there are none. | `cost_per_assoc_opp` |
| New-opp rate: attendees before → after | Share of attending firms that created at least one opportunity in the window before the event → in the window after. | `attendee_prior_opp_rate`, `attendee_new_opp_rate` |
| New-opp rate: firms not at event, before → after | The same two shares for firms not at this event. | `non_attendee_prior_opp_rate`, `non_attendee_new_opp_rate` |
| New-opp rate: firms at no event, before → after | The same two shares for firms that attended no event. | `clean_prior_opp_rate`, `clean_new_opp_rate`, `clean_control_firms` |
| Diff-in-diff vs firms not at event | (attendee after − attendee before) − (comparison after − comparison before), in percentage points, with the permutation p-value. Positive means attendees' rate rose more than the comparison group's over the same dates. | `diff_in_diff_opp_rate`, `p_value_did` |
| Diff-in-diff vs firms at no event | The same, against firms that attended no event, with its own p-value (reshuffles among attendees and those firms only). The two diff-in-diff rows disagree in sign for every event; neither is significant. p-values are two-sided permutation tests with 5,000 reshuffles, significant only if p < 0.05; under extra filters they are recomputed with fresh reshuffles, so they can differ in the second decimal between the two dashboards. | `diff_in_diff_clean`, `p_value_did_clean` |
| Open opps advancing a stage (attendees vs not) | Of opportunities that were open on the event date (created before it, not yet committed or declined), the share that reached a higher actual stage within the window after the event. Shown for attending firms vs the comparison group. | `open_opps_attendees_advanced` / `open_opps_attendees`, and the non-attendee pair |
| Days since event (as-of) | As-of date − event date. Berlin (99 days) has had less time to convert than New York (195). | `days_since_event` |

## Event scorecard charts

| Chart | What each mark shows | Source |
|---|---|---|
| New opportunities and meetings by month | Opportunities created in each calendar month (by `created_date`) and meetings held in each month, for firms in scope. Dashed lines mark the selected events' months. September is partial (to the as-of date). | `mart_monthly`, recomputed under filters from `fct_opportunity` and `fct_meeting` |
| Where 2026 pipeline came from (donut) | Share of total pipeline $ in three buckets: event-associated (default rule), attendee firms outside the window, and firms with no confirmed attendance. | `mart_opportunity.source_bucket` |
| Cost per associated opportunity | The scorecard's cost per associated opp. Label adds "firms converting". | `cost_per_assoc_opp`, `firm_conversion_rate` |
| Associated pipeline and commitments | Associated pipeline $ and associated committed $ per event. The % on the committed bar is committed $ / associated pipeline $. | `assoc_pipeline_usd`, `assoc_committed_usd` |
| Did attending change new-opportunity rates? | The four new-opp rates from the scorecard, as bars. | the four `*_opp_rate` columns |
| Meetings with attending firms, 60 days before vs after | The scorecard's meeting counts. | `meetings_pre_60`, `meetings_post_60` |

## Follow-up & segments tab

Source: `mart_firm_event` (one row per firm-event), filtered to attending firm-events under the current rule.

| Element | Definition | Column |
|---|---|---|
| Follow-up within 30 days, by tier and event | For each tier and event: firm-events with a meeting 1 to 30 days after the event / firm-events. Tooltip shows the count. | `meetings_post_30 > 0` |
| Firms converting to a new opportunity, by cut | For each value of the chosen cut (Tier, Segment, Relationship band, Senior attendee, Follow-up in 30d): share of firm-events with at least one associated opportunity, and share followed up within 30 days. n = firm-events in the group. | `assoc_opps_90 > 0`, `meetings_post_30 > 0` |
| Relationship band | New relationship: historical commitments $0. Existing < $50M. Existing $50M+. | `dim_firm.relationship_band` |
| Senior attendee | A CIO or Managing Director was registered for the firm at that event (Confirmed only by default; any status with the tentative toggle). | `has_confirmed_senior`, `senior_contacts` |
| Follow-up status donut | Firm-events split by days from event to first later meeting: within 30 days, 31 to 60, after 60, or no meeting since the event. | `days_to_first_followup` |
| Follow-up gaps table | Attending firm-events (not firms: a firm at two events can appear twice) with no meeting in the 60 days after the event, sorted by tier then the firm's total pipeline. "Days to next meeting" is the first meeting after the event, if any, which may fall after the 60 days. | `meetings_post_60 = 0`, `days_to_first_followup` |

## Firm explorer tab

Source: `mart_firm` (one row per firm), `mart_firm_timeline`, `mart_stage_history`. This tab has its own filters and ignores the page filters.

| Column / element | Definition | Column |
|---|---|---|
| Events | Events the firm was confirmed for; tentative-only events shown separately. | `events_confirmed`, `events_tentative_only` |
| Mtgs | All meetings with the firm in the file, any date. | `meetings` |
| Opps | All of the firm's opportunities. | `opps` |
| Pipeline | Sum of the firm's opportunity amounts, any stage. | `pipeline_usd` |
| Event-assoc. | Sum of amounts of the firm's event-associated opportunities at the default rule. | `assoc_pipeline_90_usd` |
| Committed | Sum of amounts of the firm's opportunities with outcome Committed. | `committed_usd` |
| Follow-up gap | The firm was confirmed at an event and had no meeting in the 60 days after it. | `has_unfollowed_event` |
| Firm timeline | Every event registration, meeting and opportunity stage entry for the firm, in date order. Projected stage entries are marked. | `mart_firm_timeline` |
| Pipeline dollars by stage, by month | Month-end snapshot: each of the firm's opportunities is counted, at its amount, in the stage it held on the last day of the month. September is taken at the as-of date; later months use projected stages and are marked *. Bars stack Committed at the base up to Initial Conversation, with Declined on top. | `mart_stage_history`, `fct_opportunity.amount_usd` |

## Opportunities tab

Source: `mart_opportunity` (one row per opportunity) and `mart_stage_history`.

| Element | Definition | Column |
|---|---|---|
| Source bucket | Event-associated (in window, attended); Attendee, not in window (the firm attended some selected event but this opportunity is outside every window; at the default rule 29 of these 39 were opened before the firm's first event); No confirmed attendance (the firm attended no selected event under the current rule). | `source_bucket`, recomputed under filters |
| Where pipeline came from | Pipeline $ and committed $ per source bucket, with opportunity counts. | `amount_usd`, `outcome` |
| Funnel: highest stage reached | For event-associated vs all other opportunities: how many reached each stage or beyond, by highest actual stage rank. An opportunity reaching IC counts at Initial Conversation, Follow-up / VDR, Due Diligence and IC. | `max_stage_rank` |
| Opportunity flow (Sankey) | Every opportunity flows from its source (credited event, attendee outside window, or no attendance) to its furthest actual stage group (Intro / VDR = ranks 1-2, Due diligence = 3, IC / documentation = 4) and then to its status (Open or Declined). Committed opportunities flow straight from source to Committed. Node labels show the count and the pipeline $ passing through. | `assoc_event_id`, `max_stage_rank`, `outcome`, `amount_usd` |
| How fast opportunities followed each event | Cumulative count of associated opportunities by days after the event, using a 180-day window. Each line stops at the event's age at the as-of date. | `bridge_opp_event` at 180 days |
| Current stage | The opportunity's latest actual stage. | `current_stage` |
| Associated event, +Nd | The credited event and days from it to `created_date`. | `assoc_event_id`, `days_after_event` |
| Flags | outlier: amount at or above $500M (one opportunity, $650M). projected stages: has stage entries after the as-of date. no early stages: first logged stage is not Initial Conversation. float amount: the amount was stored as a decimal string in the source. | `is_amount_outlier`, `projected_stage_rows`, `skipped_early_stages`, `amount_float_format` |

## Next Event Planner (Streamlit only)

| Element | Definition |
|---|---|
| Benchmark pool | Confirmed firm-events from 2026 with each firm's outcomes at the default rule (`mart_firm_event`): associated opportunities, associated pipeline, follow-up within 30 days. "All 2026 events" uses all 70; "Same format only" uses the events of the chosen format. |
| Ranges | For the planned number of firms in each tier, the pool's firm-events of that tier are resampled with replacement 4,000 times (a bootstrap); the sums give a distribution of total associated opportunities and pipeline. The cards lead with the 10th to 90th percentile range; the middle value is in the tooltip and footnote. It is a historical analog, not a forecast. |
| Cost per firm / per associated opp | Budget / firms reached; budget / median associated opportunities. |
| Firms met within 30 days | Firms reached x the target slider. The planner adds no pipeline for follow-up because the 2026 comparison (37% vs 40% conversion) is too small to show whether follow-up speed matters. |
| Opportunities that followed, by tier | Middle estimate of the same bootstrap run for each tier alone; tier medians need not add to the overall middle value. |

## Page filters

| Filter | Effect | Where it applies |
|---|---|---|
| Association window | Sets W (30, 60, 90, 180 days) for every association-based metric. | All analytic tabs |
| Include tentative firm registrations as attendance | Counts tentative-only registrations as attendance; adds 9 firm-events. | All analytic tabs |
| Event | Keeps only the selected events in cards, scorecard and charts. Credit is still assigned across all events, so no opportunity moves between events. | All analytic tabs |
| Investor segment | Keeps only firms in the selected segments: attendees, comparison group and opportunities. | All analytic tabs |
| Fund | Keeps only opportunities for the selected funds. Attendance, meetings and follow-up are unaffected. | All analytic tabs |
| Attendee seniority | Counts attendance only where a CIO or MD was registered (or only where none was). Selecting both is the same as no filter. Firms dropped by this filter leave the comparison group too. | All analytic tabs |
| Exclude $650M outlier | Removes O0017. The firm attended no event, so event metrics are unchanged; totals and opportunity charts change. | All analytic tabs |

Event cost is never split by filter, so cost per opportunity under a filter is the full event cost over the filtered opportunities. Filtered groups are small (often under 10 firms per event); read rates as directional.

## Source tables behind the metrics

| Table | Grain | Built from |
|---|---|---|
| `dim_event` | 1 row per event (3) | `events.csv` |
| `dim_firm` | 1 row per firm (60) | `firms.csv`, plus `relationship_band` |
| `fct_firm_event` | 1 row per firm x event with any registrant (79) | `event_attendees.csv`, deduplicated, unmapped contact excluded |
| `fct_meeting` | 1 row per meeting (112) | `meetings.csv` |
| `stg_opp_stage` | 1 row per opportunity x stage (first date the stage was reached) | `opportunity_stage_history.csv`, repeated stage rows collapsed, duplicate opportunity O9999 removed |
| `fct_opportunity` | 1 row per opportunity (106) | `stg_opp_stage`, evaluated as of the as-of date |
| `bridge_opp_event` | 1 row per opportunity x window x attendance rule where an event gets credit | `fct_opportunity`, `fct_firm_event`, `dim_event` |
| `mart_event_kpis` | 1 row per event x window x attendance rule (24) | all of the above |
| `mart_firm_event`, `mart_firm`, `mart_opportunity`, `mart_firm_timeline`, `mart_segment`, `mart_monthly`, `mart_event_curve`, `mart_stage_history`, `mart_meetings` | see `docs/DATA.md` | the core tables |
