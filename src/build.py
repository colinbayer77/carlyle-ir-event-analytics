"""Build the IR event analytics model.

Loads raw CSVs into DuckDB, runs sql/01..03 in order, runs data-quality checks,
and exports marts to data/marts/*.csv plus docs/data.js for the static dashboard.

Usage:  python src/build.py
"""
from __future__ import annotations

import json
import math
from datetime import date
from pathlib import Path

import duckdb

from dq_checks import run_checks

ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "data" / "raw"
MARTS = ROOT / "data" / "marts"
DB_PATH = ROOT / "data" / "ir_events.duckdb"

# Parameters. AS_OF_DATE is the day the data extract was delivered (zip timestamp);
# stage changes dated after it are treated as projected rather than achieved.
AS_OF_DATE = date(2026, 9, 23)
OUTLIER_AMOUNT_USD = 500_000_000  # single tickets at or above this are flagged

RAW_FILES = ["events", "firms", "event_attendees", "meetings", "opportunity_stage_history"]
EXPORT_TABLES = [
    "mart_event_kpis",
    "mart_firm_event",
    "mart_firm",
    "mart_opportunity",
    "mart_firm_timeline",
    "mart_segment",
    "dq_log",
]


def build(db_path: Path = DB_PATH) -> duckdb.DuckDBPyConnection:
    db_path.unlink(missing_ok=True)
    con = duckdb.connect(str(db_path))
    for name in RAW_FILES:
        con.execute(
            f"CREATE TABLE raw_{name} AS SELECT * FROM read_csv('{RAW / (name + '.csv')}', all_varchar = true, header = true)"
        )
    con.execute("CREATE TABLE params (as_of_date DATE, outlier_amount_usd DOUBLE)")
    con.execute("INSERT INTO params VALUES (?, ?)", [AS_OF_DATE, OUTLIER_AMOUNT_USD])

    for sql_file in sorted((ROOT / "sql").glob("*.sql")):
        con.execute(sql_file.read_text())

    run_checks(con)
    return con


def _clean(v):
    if isinstance(v, float) and (math.isnan(v) or math.isinf(v)):
        return None
    if isinstance(v, date):
        return v.isoformat()
    return v


def export(con: duckdb.DuckDBPyConnection) -> None:
    MARTS.mkdir(parents=True, exist_ok=True)
    payload = {
        "meta": {
            "as_of_date": AS_OF_DATE.isoformat(),
            "outlier_amount_usd": OUTLIER_AMOUNT_USD,
            "default_window_days": 90,
        }
    }
    for t in EXPORT_TABLES:
        con.execute(f"COPY {t} TO '{MARTS / (t + '.csv')}' (HEADER)")
        rel = con.execute(f"SELECT * FROM {t}")
        cols = [d[0] for d in rel.description]
        payload[t] = [dict(zip(cols, map(_clean, row))) for row in rel.fetchall()]
    # Data ships as a script (not fetched JSON) so docs/index.html also works from file:// without a server.
    (ROOT / "docs" / "data.js").write_text("window.IR_DATA = " + json.dumps(payload, default=str) + ";\n")


if __name__ == "__main__":
    con = build()
    export(con)
    print(con.sql("SELECT check_name, severity, rows_affected FROM dq_log ORDER BY severity, check_name"))
    print(
        con.sql(
            """SELECT event_id, firms_attended, followup_rate_30, assoc_opps,
                      assoc_pipeline_usd / 1e6 AS pipeline_m, assoc_committed_usd / 1e6 AS committed_m,
                      pipeline_to_cost
               FROM mart_event_kpis WHERE window_days = 90 AND NOT include_tentative"""
        )
    )
    print(f"Built {DB_PATH.relative_to(ROOT)} and exported {len(EXPORT_TABLES)} marts.")
