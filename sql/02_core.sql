-- 02_core.sql
-- Conformed dimensions and facts at their natural grain.

CREATE OR REPLACE TABLE dim_event AS
SELECT * FROM stg_events;

CREATE OR REPLACE TABLE dim_firm AS
SELECT
    f.*,
    CASE WHEN f.historical_commitments_usd = 0 THEN 'New relationship'
         WHEN f.historical_commitments_usd < 50e6 THEN 'Existing < $50M'
         ELSE 'Existing $50M+' END                       AS relationship_band
FROM stg_firms f;

-- Grain: firm x event. A firm "attended" if at least one contact is Confirmed;
-- "tentative only" firms are tracked separately and included only in the
-- include-tentative sensitivity.
CREATE OR REPLACE TABLE fct_firm_event AS
SELECT
    a.event_id,
    a.firm_id,
    COUNT(*)                                                   AS contacts,
    COUNT(*) FILTER (WHERE a.attendance_status = 'Confirmed')  AS confirmed_contacts,
    COUNT(*) FILTER (WHERE a.is_senior)                        AS senior_contacts,
    BOOL_OR(a.attendance_status = 'Confirmed')                 AS is_confirmed,
    BOOL_OR(a.is_senior AND a.attendance_status = 'Confirmed') AS has_confirmed_senior
FROM stg_attendees a
WHERE a.is_mapped
GROUP BY ALL;

CREATE OR REPLACE TABLE fct_meeting AS
SELECT * FROM stg_meetings;

-- Grain: opportunity. Status is evaluated as of the as-of date; stage rows
-- dated after it are reported as "projected" and do not count as achieved.
CREATE OR REPLACE TABLE fct_opportunity AS
WITH actual AS (
    SELECT * FROM stg_opp_stage WHERE NOT is_future
),
agg AS (
    SELECT
        o.opportunity_id,
        ANY_VALUE(o.firm_id)                          AS firm_id,
        ANY_VALUE(o.fund_name)                        AS fund_name,
        ANY_VALUE(o.created_date)                     AS created_date,
        ANY_VALUE(o.amount_usd)                       AS amount_usd,
        BOOL_OR(o.amount_float_format)                AS amount_float_format,
        MIN(o.stage_rank) FILTER (WHERE o.stage_rank > 0) AS first_stage_rank,
        MAX(o.stage_rank)                             AS max_stage_rank_incl_projected,
        COUNT(*) FILTER (WHERE o.is_future)           AS projected_stage_rows,
        SUM(o.source_rows) - COUNT(*)                 AS duplicate_stage_rows
    FROM stg_opp_stage o
    GROUP BY 1
),
act AS (
    SELECT
        opportunity_id,
        MAX(stage_rank)                                           AS max_stage_rank,
        MIN(stage_date) FILTER (WHERE stage = 'Committed')        AS committed_date,
        MIN(stage_date) FILTER (WHERE stage = 'Declined')         AS declined_date,
        MIN(stage_date) FILTER (WHERE stage_rank >= 3)            AS dd_date,
        ARG_MAX(stage, stage_date)                                AS current_stage,
        MAX(stage_date)                                           AS last_stage_date
    FROM actual
    GROUP BY 1
)
SELECT
    g.*,
    COALESCE(a.max_stage_rank, 0)                                 AS max_stage_rank,
    a.current_stage,
    a.last_stage_date,
    a.dd_date,
    a.committed_date,
    a.declined_date,
    CASE WHEN a.committed_date IS NOT NULL THEN 'Committed'
         WHEN a.declined_date  IS NOT NULL THEN 'Declined'
         ELSE 'Open' END                                          AS outcome,
    DATE_DIFF('day', g.created_date, a.committed_date)            AS days_to_commit,
    COALESCE(a.max_stage_rank, 0) >= 3                            AS reached_dd,
    g.first_stage_rank > 1                                        AS skipped_early_stages,
    g.amount_usd >= (SELECT outlier_amount_usd FROM params)       AS is_amount_outlier
FROM agg g
LEFT JOIN act a USING (opportunity_id);
