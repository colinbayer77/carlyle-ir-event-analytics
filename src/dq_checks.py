"""Data-quality checks.

Two kinds of checks:
  * Findings: known imperfections in the source data. Logged to dq_log with the
    handling decision. They never fail the build.
  * Assertions: invariants the model must satisfy (reconciliation to raw, grain,
    no fan-out). A failure raises and stops the build.
"""
from __future__ import annotations

import duckdb

# (check_name, severity, SQL returning affected row count, handling decision)
FINDINGS = [
    (
        "Duplicate attendance row",
        "Medium",
        "SELECT COUNT(*) - COUNT(DISTINCT (attendance_id, event_id, firm_id, contact_name)) FROM raw_event_attendees",
        "Exact duplicate (A0011) collapsed to one row.",
    ),
    (
        "Duplicate opportunity record",
        "High",
        "SELECT COUNT(*) FROM dup_opportunities",
        "O9998 and O9999 are identical (same firm, fund, dates, stage, $25M). Kept O9998, dropped O9999.",
    ),
    (
        "Attendee with no firm_id",
        "Medium",
        "SELECT COUNT(*) FROM raw_event_attendees WHERE NULLIF(TRIM(firm_id), '') IS NULL",
        "Kept in contact counts, excluded from firm-level metrics. Process fix: enforce firm mapping at registration.",
    ),
    (
        "Tentative-only firm attendance",
        "Low",
        "SELECT COUNT(*) FROM fct_firm_event WHERE NOT is_confirmed",
        "Excluded from default metrics; included via the 'include tentative' sensitivity toggle.",
    ),
    (
        "Amount stored as float text",
        "Low",
        "SELECT COUNT(*) FROM raw_opportunity_stage_history WHERE opportunity_amount_usd LIKE '%.%'",
        "Cast to integer USD. Values (1.5M, 2.5M) read as whole dollars; treated as small tickets, not a unit error.",
    ),
    (
        "Outlier ticket size",
        "High",
        "SELECT COUNT(*) FROM fct_opportunity WHERE is_amount_outlier",
        "O0017 ($650M, next largest $150M) kept as recorded; every pipeline metric is also shown ex-outlier.",
    ),
    (
        "Stage dated after as-of date",
        "Medium",
        "SELECT COUNT(*) FROM stg_opp_stage WHERE is_future",
        "23 raw rows are dated after 2026-09-23 (latest 2026-11-19); 19 remain after collapsing repeated same-stage rows (latest 2026-10-28). Treated as projected: excluded from current stage, commitments and conversion; shown in firm timelines.",
    ),
    (
        "Repeated stage rows",
        "Low",
        "SELECT COALESCE(SUM(source_rows - 1), 0) FROM stg_opp_stage",
        "Collapsed to the first date each stage was reached.",
    ),
    (
        "Opportunity starts past Initial Conversation",
        "Low",
        "SELECT COUNT(*) FROM fct_opportunity WHERE skipped_early_stages",
        "Kept (e.g. O9998 logged directly as Committed). Funnel counts it at the stages it reached.",
    ),
    (
        "Two meetings same firm same day",
        "Low",
        "SELECT COUNT(*) FROM (SELECT firm_id, meeting_date FROM stg_meetings GROUP BY ALL HAVING COUNT(*) > 1)",
        "Kept: different type and purpose (F007, 2026-05-30), plausibly two sessions.",
    ),
    (
        "Meeting on a weekend",
        "Info",
        "SELECT COUNT(*) FROM stg_meetings WHERE dayofweek(meeting_date) IN (0, 6)",
        "34% of meetings fall on Saturday or Sunday, so dates were likely generated without a business-day calendar. Kept; no metric depends on weekday.",
    ),
    (
        "First stage logged well after created_date",
        "Info",
        "SELECT COUNT(*) FROM (SELECT opportunity_id FROM stg_opp_stage GROUP BY 1 HAVING DATE_DIFF('day', ANY_VALUE(created_date), MIN(stage_date)) >= 5)",
        "Every opportunity's first stage is 5 to 30 days after created_date (median 17), so created_date looks like a CRM entry date, not first contact. Association keys off created_date as documented.",
    ),
    (
        "Meeting before first event baseline",
        "Info",
        "SELECT COUNT(*) FROM stg_meetings WHERE meeting_date < (SELECT MIN(event_date) FROM dim_event) - 60",
        "Kept as history; only +/-60 day windows around events are used for engagement lift.",
    ),
]

# (description, SQL that must return TRUE)
ASSERTIONS = [
    ("3 events, cost reconciles to $1.215M", "SELECT COUNT(*) = 3 AND SUM(cost_usd) = 1215000 FROM dim_event"),
    ("60 firms, unique ids", "SELECT COUNT(*) = 60 AND COUNT(DISTINCT firm_id) = 60 FROM dim_firm"),
    (
        "Opportunity grain: one row per raw opportunity_id",
        "SELECT (SELECT COUNT(*) FROM fct_opportunity) = (SELECT COUNT(DISTINCT opportunity_id) FROM raw_opportunity_stage_history) - (SELECT COUNT(*) FROM dup_opportunities)",
    ),
    ("One firm and one amount per opportunity", "SELECT COUNT(*) = 0 FROM (SELECT opportunity_id FROM stg_opp_stage GROUP BY 1 HAVING COUNT(DISTINCT firm_id) > 1 OR COUNT(DISTINCT amount_usd) > 1)"),
    ("No stage before created_date", "SELECT COUNT(*) = 0 FROM stg_opp_stage WHERE stage_date < created_date"),
    ("All attendee/meeting/opp firms exist in dim_firm", """
        SELECT COUNT(*) = 0 FROM (
          SELECT firm_id FROM stg_attendees WHERE is_mapped
          UNION SELECT firm_id FROM stg_meetings
          UNION SELECT firm_id FROM stg_opp_stage) x
        WHERE firm_id NOT IN (SELECT firm_id FROM dim_firm)"""),
    ("Meetings reconcile to raw", "SELECT (SELECT COUNT(*) FROM fct_meeting) = (SELECT COUNT(*) FROM raw_meetings)"),
    ("Each opp credited to at most one event per grid cell", "SELECT COUNT(*) = 0 FROM (SELECT window_days, include_tentative, opportunity_id FROM bridge_opp_event GROUP BY ALL HAVING COUNT(*) > 1)"),
    ("Associated pipeline never exceeds total pipeline", """
        SELECT MAX(p) <= (SELECT SUM(amount_usd) FROM fct_opportunity)
        FROM (SELECT window_days, include_tentative, SUM(assoc_pipeline_usd) p FROM mart_event_kpis GROUP BY ALL)"""),
    ("Firm-event mart reconciles to 90d bridge", """
        SELECT (SELECT SUM(assoc_opps_90) FROM mart_firm_event WHERE is_confirmed)
             = (SELECT COUNT(*) FROM bridge_opp_event WHERE window_days = 90 AND NOT include_tentative)"""),
    ("Event KPI mart has 3 events x 8 grid cells", "SELECT COUNT(*) = 24 FROM mart_event_kpis"),
]


def run_checks(con: duckdb.DuckDBPyConnection) -> None:
    con.execute(
        "CREATE OR REPLACE TABLE dq_log (check_name VARCHAR, severity VARCHAR, rows_affected BIGINT, handling VARCHAR)"
    )
    for name, sev, sql, handling in FINDINGS:
        n = con.execute(sql).fetchone()[0]
        con.execute("INSERT INTO dq_log VALUES (?, ?, ?, ?)", [name, sev, n, handling])

    failures = [desc for desc, sql in ASSERTIONS if not con.execute(sql).fetchone()[0]]
    if failures:
        raise AssertionError("Data-quality assertions failed:\n  - " + "\n  - ".join(failures))
    print(f"DQ: {len(FINDINGS)} findings logged, {len(ASSERTIONS)} assertions passed.")
