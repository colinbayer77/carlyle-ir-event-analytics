-- 03_marts.sql
-- Analysis-ready marts consumed by the HTML dashboard, Streamlit app, and notebook.
--
-- Association rule (documented in README):
--   An opportunity is "event-associated" when the firm attended the event and the
--   opportunity was created 0..W days after the event date. If several attended
--   events qualify, the most recent prior event gets the credit (last touch).
--   This measures association, not causation.
-- Sensitivity grid: W in (30, 60, 90, 180) x include tentative-only firms (yes/no).
-- Default view: W = 90, confirmed attendance only.

CREATE OR REPLACE TABLE grid AS
SELECT * FROM (VALUES (30), (60), (90), (180)) w(window_days)
CROSS JOIN (VALUES (false), (true)) t(include_tentative);

-- Firm x event attendance under each tentative rule.
CREATE OR REPLACE TABLE int_attendance_rule AS
SELECT fe.*, t.include_tentative
FROM fct_firm_event fe
CROSS JOIN (VALUES (false), (true)) t(include_tentative)
WHERE fe.is_confirmed OR t.include_tentative;

-- Every (opportunity, attended event) pair with the opportunity created on/after the event.
CREATE OR REPLACE TABLE int_opp_event_candidates AS
SELECT
    o.opportunity_id,
    ar.event_id,
    ar.include_tentative,
    DATE_DIFF('day', e.event_date, o.created_date) AS days_after_event
FROM fct_opportunity o
JOIN int_attendance_rule ar ON ar.firm_id = o.firm_id
JOIN dim_event e            ON e.event_id = ar.event_id
WHERE o.created_date >= e.event_date;

-- Last-touch association per grid cell.
CREATE OR REPLACE TABLE bridge_opp_event AS
SELECT g.window_days, g.include_tentative, c.opportunity_id,
       ARG_MIN(c.event_id, c.days_after_event) AS event_id,
       MIN(c.days_after_event)                 AS days_after_event
FROM grid g
JOIN int_opp_event_candidates c
  ON c.include_tentative = g.include_tentative
 AND c.days_after_event <= g.window_days
GROUP BY ALL;

-- Opportunities that were already open on the event date (pipeline the event could accelerate).
CREATE OR REPLACE TABLE int_open_at_event AS
SELECT
    e.event_id,
    o.opportunity_id,
    o.firm_id,
    o.amount_usd,
    (SELECT MAX(s.stage_rank) FROM stg_opp_stage s
      WHERE s.opportunity_id = o.opportunity_id AND s.stage_date < e.event_date AND s.stage_rank > 0) AS rank_at_event,
    e.event_date
FROM dim_event e
JOIN fct_opportunity o
  ON o.created_date < e.event_date
 AND COALESCE(o.committed_date, DATE '9999-12-31') >= e.event_date
 AND COALESCE(o.declined_date,  DATE '9999-12-31') >= e.event_date;

-- Did an open opportunity advance at least one stage within W days of the event?
CREATE OR REPLACE TABLE int_open_advanced AS
SELECT g.window_days, oe.event_id, oe.opportunity_id, oe.firm_id, oe.amount_usd,
       EXISTS (
         SELECT 1 FROM stg_opp_stage s
         WHERE s.opportunity_id = oe.opportunity_id
           AND NOT s.is_future
           AND s.stage_rank > COALESCE(oe.rank_at_event, 0)
           AND s.stage_date >= oe.event_date
           AND s.stage_date <= oe.event_date + g.window_days
       ) AS advanced
FROM int_open_at_event oe
CROSS JOIN (SELECT DISTINCT window_days FROM grid) g;

-- First meeting after each firm-event (follow-up speed) and meeting counts around the event.
CREATE OR REPLACE TABLE int_firm_event_meetings AS
SELECT
    fe.event_id, fe.firm_id,
    MIN(DATE_DIFF('day', e.event_date, m.meeting_date))
        FILTER (WHERE m.meeting_date > e.event_date)                              AS days_to_first_followup,
    COUNT(m.meeting_id) FILTER (WHERE m.meeting_date >  e.event_date
                                  AND m.meeting_date <= e.event_date + 30)        AS meetings_post_30,
    COUNT(m.meeting_id) FILTER (WHERE m.meeting_date >  e.event_date
                                  AND m.meeting_date <= e.event_date + 60)        AS meetings_post_60,
    COUNT(m.meeting_id) FILTER (WHERE m.meeting_date <  e.event_date
                                  AND m.meeting_date >= e.event_date - 60)        AS meetings_pre_60
FROM fct_firm_event fe
JOIN dim_event e USING (event_id)
LEFT JOIN fct_meeting m ON m.firm_id = fe.firm_id
GROUP BY ALL;

-- Per-firm new-opportunity flag after/before each event date (for comparison groups).
CREATE OR REPLACE TABLE int_firm_window_opps AS
SELECT g.window_days, e.event_id, f.firm_id,
       COUNT(o.opportunity_id) FILTER (WHERE o.created_date >= e.event_date
                                         AND o.created_date <= e.event_date + g.window_days) AS opps_after,
       COUNT(o.opportunity_id) FILTER (WHERE o.created_date <  e.event_date
                                         AND o.created_date >= e.event_date - g.window_days) AS opps_before
FROM (SELECT DISTINCT window_days FROM grid) g
CROSS JOIN dim_event e
CROSS JOIN dim_firm f
LEFT JOIN fct_opportunity o ON o.firm_id = f.firm_id
GROUP BY ALL;

-- ------------------------------------------------------------------------------------
-- mart_event_kpis: one row per event per sensitivity cell. Single source for KPI tiles.
-- ------------------------------------------------------------------------------------
CREATE OR REPLACE TABLE mart_event_kpis AS
WITH att AS (
    SELECT g.window_days, g.include_tentative, ar.event_id, ar.firm_id, ar.is_confirmed,
           ar.has_confirmed_senior, f.tier
    FROM grid g
    JOIN int_attendance_rule ar ON ar.include_tentative = g.include_tentative
    JOIN dim_firm f USING (firm_id)
),
att_agg AS (
    SELECT window_days, include_tentative, event_id,
           COUNT(*)                                          AS firms_attended,
           COUNT(*) FILTER (WHERE tier = 'Tier 1')           AS tier1_firms,
           COUNT(*) FILTER (WHERE has_confirmed_senior)      AS firms_with_senior
    FROM att GROUP BY ALL
),
contacts AS (
    SELECT event_id,
           COUNT(*)                                                      AS contact_rows,
           COUNT(*) FILTER (WHERE attendance_status = 'Confirmed')       AS confirmed_contacts,
           COUNT(*) FILTER (WHERE NOT is_mapped)                         AS unmapped_contacts
    FROM stg_attendees GROUP BY 1
),
fu AS (
    SELECT a.window_days, a.include_tentative, a.event_id,
           COUNT(*) FILTER (WHERE m.meetings_post_30 > 0)                AS firms_followup_30,
           MEDIAN(m.days_to_first_followup)                              AS median_days_to_followup,
           SUM(m.meetings_post_60)                                       AS meetings_post_60,
           SUM(m.meetings_pre_60)                                        AS meetings_pre_60
    FROM att a JOIN int_firm_event_meetings m USING (event_id, firm_id)
    GROUP BY ALL
),
assoc AS (
    SELECT b.window_days, b.include_tentative, b.event_id,
           COUNT(*)                                                      AS assoc_opps,
           COUNT(DISTINCT o.firm_id)                                     AS assoc_firms,
           SUM(o.amount_usd)                                             AS assoc_pipeline_usd,
           SUM(o.amount_usd) FILTER (WHERE NOT o.is_amount_outlier)      AS assoc_pipeline_ex_outlier_usd,
           COUNT(*) FILTER (WHERE o.reached_dd)                          AS assoc_opps_reached_dd,
           COUNT(*) FILTER (WHERE o.outcome = 'Committed')               AS assoc_committed_opps,
           COALESCE(SUM(o.amount_usd) FILTER (WHERE o.outcome = 'Committed'), 0) AS assoc_committed_usd,
           COUNT(*) FILTER (WHERE o.outcome = 'Declined')                AS assoc_declined_opps,
           MEDIAN(b.days_after_event)                                    AS median_days_event_to_opp
    FROM bridge_opp_event b JOIN fct_opportunity o USING (opportunity_id)
    GROUP BY ALL
),
cmp AS (  -- new-opportunity rate: attendees vs non-attendees after the event, attendees before
    SELECT g.window_days, g.include_tentative, w.event_id,
           AVG(CASE WHEN w.opps_after  > 0 THEN 1.0 ELSE 0 END) FILTER (WHERE ar.firm_id IS NOT NULL) AS attendee_new_opp_rate,
           AVG(CASE WHEN w.opps_before > 0 THEN 1.0 ELSE 0 END) FILTER (WHERE ar.firm_id IS NOT NULL) AS attendee_prior_opp_rate,
           AVG(CASE WHEN w.opps_after  > 0 THEN 1.0 ELSE 0 END) FILTER (WHERE ar.firm_id IS NULL)     AS non_attendee_new_opp_rate,
           AVG(CASE WHEN w.opps_before > 0 THEN 1.0 ELSE 0 END) FILTER (WHERE ar.firm_id IS NULL)     AS non_attendee_prior_opp_rate,
           COUNT(*) FILTER (WHERE ar.firm_id IS NULL)                                                  AS non_attendee_firms
    FROM grid g
    JOIN int_firm_window_opps w ON w.window_days = g.window_days
    LEFT JOIN int_attendance_rule ar
      ON ar.firm_id = w.firm_id AND ar.event_id = w.event_id AND ar.include_tentative = g.include_tentative
    GROUP BY ALL
),
adv AS (  -- acceleration of pipeline already open at the event
    SELECT g.window_days, g.include_tentative, a.event_id,
           COUNT(*) FILTER (WHERE ar.firm_id IS NOT NULL)                               AS open_opps_attendees,
           COUNT(*) FILTER (WHERE ar.firm_id IS NOT NULL AND a.advanced)                AS open_opps_attendees_advanced,
           COUNT(*) FILTER (WHERE ar.firm_id IS NULL)                                   AS open_opps_non_attendees,
           COUNT(*) FILTER (WHERE ar.firm_id IS NULL AND a.advanced)                    AS open_opps_non_attendees_advanced,
           COALESCE(SUM(a.amount_usd) FILTER (WHERE ar.firm_id IS NOT NULL), 0)         AS open_pipeline_attendees_usd
    FROM grid g
    JOIN int_open_advanced a ON a.window_days = g.window_days
    LEFT JOIN int_attendance_rule ar
      ON ar.firm_id = a.firm_id AND ar.event_id = a.event_id AND ar.include_tentative = g.include_tentative
    GROUP BY ALL
)
SELECT
    e.event_id, e.event_name, e.event_date, e.event_type, e.location, e.cost_usd,
    aa.window_days, aa.include_tentative,
    c.contact_rows, c.confirmed_contacts, c.unmapped_contacts,
    aa.firms_attended, aa.tier1_firms, aa.firms_with_senior,
    e.cost_usd / aa.firms_attended                                   AS cost_per_firm,
    fu.firms_followup_30,
    fu.firms_followup_30 * 1.0 / aa.firms_attended                   AS followup_rate_30,
    fu.median_days_to_followup,
    fu.meetings_pre_60, fu.meetings_post_60,
    COALESCE(s.assoc_opps, 0)                                        AS assoc_opps,
    COALESCE(s.assoc_firms, 0)                                       AS assoc_firms,
    COALESCE(s.assoc_firms, 0) * 1.0 / aa.firms_attended             AS firm_conversion_rate,
    COALESCE(s.assoc_pipeline_usd, 0)                                AS assoc_pipeline_usd,
    COALESCE(s.assoc_pipeline_ex_outlier_usd, 0)                     AS assoc_pipeline_ex_outlier_usd,
    COALESCE(s.assoc_opps_reached_dd, 0)                             AS assoc_opps_reached_dd,
    COALESCE(s.assoc_committed_opps, 0)                              AS assoc_committed_opps,
    COALESCE(s.assoc_committed_usd, 0)                               AS assoc_committed_usd,
    COALESCE(s.assoc_declined_opps, 0)                               AS assoc_declined_opps,
    s.median_days_event_to_opp,
    COALESCE(s.assoc_pipeline_usd, 0) / e.cost_usd                   AS pipeline_to_cost,
    COALESCE(s.assoc_pipeline_ex_outlier_usd, 0) / e.cost_usd        AS pipeline_to_cost_ex_outlier,
    e.cost_usd / NULLIF(s.assoc_opps, 0)                             AS cost_per_assoc_opp,
    cmp.attendee_new_opp_rate, cmp.attendee_prior_opp_rate,
    cmp.non_attendee_new_opp_rate, cmp.non_attendee_prior_opp_rate, cmp.non_attendee_firms,
    (cmp.attendee_new_opp_rate - cmp.attendee_prior_opp_rate)
      - (cmp.non_attendee_new_opp_rate - cmp.non_attendee_prior_opp_rate)   AS diff_in_diff_opp_rate,
    DATE_DIFF('day', e.event_date, (SELECT as_of_date FROM params))         AS days_since_event,
    adv.open_opps_attendees, adv.open_opps_attendees_advanced,
    adv.open_opps_non_attendees, adv.open_opps_non_attendees_advanced,
    adv.open_pipeline_attendees_usd
FROM att_agg aa
JOIN dim_event e USING (event_id)
JOIN contacts c USING (event_id)
JOIN fu USING (window_days, include_tentative, event_id)
LEFT JOIN assoc s USING (window_days, include_tentative, event_id)
JOIN cmp USING (window_days, include_tentative, event_id)
JOIN adv USING (window_days, include_tentative, event_id)
ORDER BY window_days, include_tentative, event_id;

-- ------------------------------------------------------------------------------------
-- mart_firm_event: firm x event detail at the default rule (W = 90, confirmed only),
-- plus tentative-only rows flagged, for segment cuts and the firm explorer.
-- ------------------------------------------------------------------------------------
CREATE OR REPLACE TABLE mart_firm_event AS
SELECT
    fe.event_id, e.event_name, e.event_date, fe.firm_id, f.firm_name, f.segment, f.tier, f.region,
    f.relationship_band, f.historical_commitments_usd,
    fe.contacts, fe.confirmed_contacts, fe.senior_contacts, fe.is_confirmed, fe.has_confirmed_senior,
    m.days_to_first_followup, m.meetings_pre_60, m.meetings_post_30, m.meetings_post_60,
    COALESCE(m.meetings_post_30, 0) > 0                         AS followed_up_30,
    COUNT(o.opportunity_id)                                     AS assoc_opps_90,
    COALESCE(SUM(o.amount_usd), 0)                              AS assoc_pipeline_90_usd,
    COALESCE(SUM(o.amount_usd) FILTER (WHERE o.outcome = 'Committed'), 0) AS assoc_committed_90_usd,
    COUNT(o.opportunity_id) FILTER (WHERE o.reached_dd)         AS assoc_opps_reached_dd_90
FROM fct_firm_event fe
JOIN dim_event e USING (event_id)
JOIN dim_firm f USING (firm_id)
LEFT JOIN int_firm_event_meetings m USING (event_id, firm_id)
LEFT JOIN (
    SELECT b.event_id, o.*
    FROM bridge_opp_event b JOIN fct_opportunity o USING (opportunity_id)
    WHERE b.window_days = 90 AND NOT b.include_tentative
) o ON o.event_id = fe.event_id AND o.firm_id = fe.firm_id
GROUP BY ALL
ORDER BY fe.event_id, fe.firm_id;

-- ------------------------------------------------------------------------------------
-- mart_opportunity: every opportunity with its default-rule event association.
-- ------------------------------------------------------------------------------------
CREATE OR REPLACE TABLE mart_opportunity AS
SELECT
    o.*, f.firm_name, f.segment, f.tier, f.region,
    b.event_id                                 AS assoc_event_id_90,
    b.days_after_event                         AS days_after_event_90,
    CASE WHEN b.event_id IS NOT NULL THEN 'Event-associated (90d)'
         WHEN o.firm_id IN (SELECT firm_id FROM fct_firm_event WHERE is_confirmed) THEN 'Attendee, outside window'
         ELSE 'No confirmed attendance' END             AS source_bucket
FROM fct_opportunity o
JOIN dim_firm f USING (firm_id)
LEFT JOIN bridge_opp_event b
       ON b.opportunity_id = o.opportunity_id AND b.window_days = 90 AND NOT b.include_tentative
ORDER BY o.opportunity_id;

-- ------------------------------------------------------------------------------------
-- mart_firm: one row per firm, for the explorer table.
-- ------------------------------------------------------------------------------------
CREATE OR REPLACE TABLE mart_firm AS
SELECT
    f.firm_id, f.firm_name, f.segment, f.tier, f.region, f.relationship_band, f.historical_commitments_usd,
    (SELECT STRING_AGG(event_id, ', ' ORDER BY event_id) FROM fct_firm_event x WHERE x.firm_id = f.firm_id AND x.is_confirmed) AS events_confirmed,
    (SELECT STRING_AGG(event_id, ', ' ORDER BY event_id) FROM fct_firm_event x WHERE x.firm_id = f.firm_id AND NOT x.is_confirmed) AS events_tentative_only,
    (SELECT COUNT(*) FROM fct_meeting m WHERE m.firm_id = f.firm_id)                                   AS meetings,
    (SELECT COUNT(*) FROM fct_opportunity o WHERE o.firm_id = f.firm_id)                               AS opps,
    (SELECT COALESCE(SUM(amount_usd), 0) FROM fct_opportunity o WHERE o.firm_id = f.firm_id)           AS pipeline_usd,
    (SELECT COALESCE(SUM(amount_usd), 0) FROM fct_opportunity o WHERE o.firm_id = f.firm_id AND outcome = 'Committed') AS committed_usd,
    (SELECT COUNT(*) FROM mart_opportunity o WHERE o.firm_id = f.firm_id AND assoc_event_id_90 IS NOT NULL) AS assoc_opps_90,
    (SELECT COALESCE(SUM(amount_usd), 0) FROM mart_opportunity o WHERE o.firm_id = f.firm_id AND assoc_event_id_90 IS NOT NULL) AS assoc_pipeline_90_usd,
    -- Leakage flag: confirmed at an event, no meeting within 60 days after any attended event
    EXISTS (SELECT 1 FROM mart_firm_event x WHERE x.firm_id = f.firm_id AND x.is_confirmed AND COALESCE(x.meetings_post_60, 0) = 0) AS has_unfollowed_event
FROM dim_firm f
ORDER BY f.firm_id;

-- ------------------------------------------------------------------------------------
-- mart_firm_timeline: every touchpoint for the firm drill-down.
-- ------------------------------------------------------------------------------------
CREATE OR REPLACE TABLE mart_firm_timeline AS
SELECT fe.firm_id, e.event_date AS dt, 'Event' AS kind,
       e.event_name || CASE WHEN fe.is_confirmed THEN ' (confirmed, ' ELSE ' (tentative, ' END
         || fe.contacts || ' contacts)' AS detail, false AS is_projected
FROM fct_firm_event fe JOIN dim_event e USING (event_id)
UNION ALL
SELECT firm_id, meeting_date, 'Meeting', purpose || ' | ' || meeting_type || ' | ' || internal_attendee, false
FROM fct_meeting
UNION ALL
SELECT firm_id, stage_date, 'Opportunity',
       opportunity_id || ' ' || fund_name || ': ' || stage || ' ($' || ROUND(amount_usd / 1e6, 1) || 'M)', is_future
FROM stg_opp_stage
ORDER BY firm_id, dt, kind;

-- ------------------------------------------------------------------------------------
-- mart_segment: default-rule outcomes by tier and segment across all events.
-- ------------------------------------------------------------------------------------
CREATE OR REPLACE TABLE mart_segment AS
SELECT 'Tier' AS dimension, tier AS value,
       COUNT(*) AS firm_events, AVG(followed_up_30::INT) AS followup_rate_30,
       AVG((assoc_opps_90 > 0)::INT) AS conversion_rate, SUM(assoc_pipeline_90_usd) AS assoc_pipeline_usd
FROM mart_firm_event WHERE is_confirmed GROUP BY ALL
UNION ALL
SELECT 'Segment', segment, COUNT(*), AVG(followed_up_30::INT), AVG((assoc_opps_90 > 0)::INT), SUM(assoc_pipeline_90_usd)
FROM mart_firm_event WHERE is_confirmed GROUP BY ALL
UNION ALL
SELECT 'Senior attendee', CASE WHEN has_confirmed_senior THEN 'CIO/MD confirmed' ELSE 'No CIO/MD' END,
       COUNT(*), AVG(followed_up_30::INT), AVG((assoc_opps_90 > 0)::INT), SUM(assoc_pipeline_90_usd)
FROM mart_firm_event WHERE is_confirmed GROUP BY ALL
UNION ALL
SELECT 'Follow-up in 30d', CASE WHEN followed_up_30 THEN 'Yes' ELSE 'No' END,
       COUNT(*), AVG(followed_up_30::INT), AVG((assoc_opps_90 > 0)::INT), SUM(assoc_pipeline_90_usd)
FROM mart_firm_event WHERE is_confirmed GROUP BY ALL
UNION ALL
SELECT 'Relationship', relationship_band,
       COUNT(*), AVG(followed_up_30::INT), AVG((assoc_opps_90 > 0)::INT), SUM(assoc_pipeline_90_usd)
FROM mart_firm_event WHERE is_confirmed GROUP BY ALL
ORDER BY 1, 2;

-- ------------------------------------------------------------------------------------
-- mart_monthly: activity by month (context for seasonality around event dates).
-- ------------------------------------------------------------------------------------
CREATE OR REPLACE TABLE mart_monthly AS
WITH months AS (
    SELECT CAST(m AS DATE) AS month
    FROM generate_series(DATE '2026-01-01', DATE_TRUNC('month', (SELECT as_of_date FROM params)), INTERVAL 1 MONTH) g(m)
)
SELECT
    mo.month,
    (SELECT COUNT(*) FROM fct_opportunity o WHERE DATE_TRUNC('month', o.created_date) = mo.month)                 AS new_opps,
    (SELECT COALESCE(SUM(amount_usd), 0) FROM fct_opportunity o WHERE DATE_TRUNC('month', o.created_date) = mo.month) AS new_pipeline_usd,
    (SELECT COUNT(*) FROM fct_meeting m WHERE DATE_TRUNC('month', m.meeting_date) = mo.month)                     AS meetings,
    (SELECT STRING_AGG(event_id, ',') FROM dim_event e WHERE DATE_TRUNC('month', e.event_date) = mo.month)         AS events_in_month
FROM months mo
ORDER BY mo.month;

-- ------------------------------------------------------------------------------------
-- mart_event_curve: associated opportunities by days after each event (180-day window,
-- confirmed attendance, last touch). Dashboards cumulate this into a conversion curve.
-- ------------------------------------------------------------------------------------
CREATE OR REPLACE TABLE mart_event_curve AS
SELECT b.event_id, b.days_after_event, COUNT(*) AS opps, SUM(o.amount_usd) AS pipeline_usd
FROM bridge_opp_event b JOIN fct_opportunity o USING (opportunity_id)
WHERE b.window_days = 180 AND NOT b.include_tentative
GROUP BY ALL
ORDER BY 1, 2;
