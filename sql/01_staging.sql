-- 01_staging.sql
-- Type-cast raw CSVs, standardize values, and attach data-quality flags.
-- Raw files are loaded as all-VARCHAR tables named raw_<file> by src/build.py.
-- Nothing is dropped here except exact duplicate rows; exclusions happen downstream
-- so every decision stays visible in the DQ log.

-- Parameters (set by build.py): as_of_date, outlier_amount_usd
-- params(as_of_date DATE, outlier_amount_usd DOUBLE)

CREATE OR REPLACE TABLE stg_events AS
SELECT
    event_id,
    event_name,
    CAST(event_date AS DATE)          AS event_date,
    event_type,
    location,
    CAST(cost_usd AS DOUBLE)          AS cost_usd
FROM raw_events;

CREATE OR REPLACE TABLE stg_firms AS
SELECT
    firm_id,
    firm_name,
    segment,
    priority                                           AS tier,
    CAST(historical_commitments_usd AS DOUBLE)         AS historical_commitments_usd,
    coverage_region                                    AS region
FROM raw_firms;

-- Attendance: exact duplicate rows collapsed (A0011 appears twice, identical).
-- Rows with no firm_id are kept but flagged is_mapped = false.
CREATE OR REPLACE TABLE stg_attendees AS
SELECT DISTINCT
    attendance_id,
    event_id,
    NULLIF(TRIM(firm_id), '')                          AS firm_id,
    contact_name,
    contact_title,
    attendance_status,
    NULLIF(TRIM(firm_id), '') IS NOT NULL              AS is_mapped,
    contact_title IN ('CIO', 'Managing Director')      AS is_senior
FROM raw_event_attendees;

CREATE OR REPLACE TABLE stg_meetings AS
SELECT
    meeting_id,
    firm_id,
    CAST(meeting_date AS DATE)                         AS meeting_date,
    meeting_type,
    internal_attendee,
    purpose
FROM raw_meetings;

-- Opportunity stage history.
--  * amount: some rows are formatted as floats ("2500000.0"); cast and flag.
--  * stage_rank gives an ordered funnel; Declined is terminal and ranked separately.
--  * is_future: stage dates after the as-of date are treated as projected, not actual.
--  * Repeated rows for the same stage (e.g. IC / Documentation logged twice) are
--    collapsed to the first date that stage was reached.
CREATE OR REPLACE TABLE stg_opp_stage_raw AS
SELECT
    opportunity_id,
    firm_id,
    fund_name,
    CAST(created_date AS DATE)                         AS created_date,
    CAST(stage_date AS DATE)                           AS stage_date,
    stage,
    CAST(CAST(opportunity_amount_usd AS DOUBLE) AS BIGINT) AS amount_usd,
    opportunity_amount_usd LIKE '%.%'                  AS amount_float_format,
    CASE stage
        WHEN 'Initial Conversation' THEN 1
        WHEN 'Follow-up / VDR'      THEN 2
        WHEN 'Due Diligence'        THEN 3
        WHEN 'IC / Documentation'   THEN 4
        WHEN 'Committed'            THEN 5
        WHEN 'Declined'             THEN 0
    END                                                AS stage_rank
FROM raw_opportunity_stage_history;

CREATE OR REPLACE TABLE stg_opp_stage AS
SELECT
    s.opportunity_id,
    s.firm_id,
    s.fund_name,
    s.created_date,
    s.stage,
    s.stage_rank,
    MIN(s.stage_date)                                   AS stage_date,
    COUNT(*)                                            AS source_rows,
    ANY_VALUE(s.amount_usd)                             AS amount_usd,
    BOOL_OR(s.amount_float_format)                      AS amount_float_format,
    MIN(s.stage_date) > (SELECT as_of_date FROM params) AS is_future
FROM stg_opp_stage_raw s
GROUP BY ALL;
