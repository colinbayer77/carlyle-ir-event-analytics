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
import numpy as np

from dq_checks import run_checks

ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "data" / "raw"
MARTS = ROOT / "data" / "marts"
DB_PATH = ROOT / "data" / "ir_events.duckdb"

# Parameters. AS_OF_DATE is the day the data extract was delivered (zip timestamp);
# stage changes dated after it are treated as projected rather than achieved.
AS_OF_DATE = date(2026, 9, 23)
OUTLIER_AMOUNT_USD = 500_000_000  # single tickets at or above this are flagged
N_PERMUTATIONS = 5_000  # permutation test for the difference-in-differences
SIGNIFICANCE_LEVEL = 0.05

RAW_FILES = ["events", "firms", "event_attendees", "meetings", "opportunity_stage_history"]
EXPORT_TABLES = [
    "mart_event_kpis",
    "mart_firm_event",
    "mart_firm",
    "mart_opportunity",
    "mart_firm_timeline",
    "mart_segment",
    "mart_monthly",
    "mart_event_curve",
    "mart_stage_history",
    "mart_meetings",
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

    add_significance(con)
    run_checks(con)
    return con


def add_significance(con: duckdb.DuckDBPyConnection) -> None:
    """Two-sided permutation test for each event's difference-in-differences.

    For every firm, change = (opened an opportunity in the W days after the event date)
    - (opened one in the W days before). The statistic is mean change for attendees minus
    mean change for non-attendees. Shuffling which firms attended, N_PERMUTATIONS times,
    gives the distribution under "attendance made no difference"; the p-value is the share
    of shuffles at least as extreme as the observed gap.
    """
    rows = con.execute("""
        SELECT g.window_days, g.include_tentative, w.event_id, w.firm_id,
               (w.opps_after > 0)::INT - (w.opps_before > 0)::INT AS change,
               ar.firm_id IS NOT NULL AS attended
        FROM grid g
        JOIN int_firm_window_opps w ON w.window_days = g.window_days
        LEFT JOIN int_attendance_rule ar
          ON ar.firm_id = w.firm_id AND ar.event_id = w.event_id AND ar.include_tentative = g.include_tentative
        ORDER BY 1, 2, 3, 4""").fetchall()
    groups: dict[tuple, list] = {}
    for w, t, e, _, change, att in rows:
        groups.setdefault((w, t, e), []).append((change, att))
    rng = np.random.default_rng(7)
    out = []
    for (w, t, e), vals in groups.items():
        change = np.array([v[0] for v in vals], dtype=float)
        att = np.array([v[1] for v in vals], dtype=bool)
        obs = change[att].mean() - change[~att].mean()
        perms = rng.permuted(np.tile(att, (N_PERMUTATIONS, 1)), axis=1)
        n_att = att.sum()
        null = (perms @ change) / n_att - ((~perms) @ change) / (len(att) - n_att)
        p = float(np.mean(np.abs(null) >= abs(obs) - 1e-12))
        out.append((w, t, e, float(obs), p))
    con.execute("CREATE OR REPLACE TABLE did_significance (window_days INT, include_tentative BOOLEAN, event_id VARCHAR, did DOUBLE, p_value_did DOUBLE)")
    con.executemany("INSERT INTO did_significance VALUES (?, ?, ?, ?, ?)", out)
    con.execute(f"""
        CREATE OR REPLACE TABLE mart_event_kpis AS
        SELECT k.*, s.p_value_did, s.p_value_did < {SIGNIFICANCE_LEVEL} AS did_significant, {N_PERMUTATIONS} AS n_permutations
        FROM mart_event_kpis k JOIN did_significance s USING (window_days, include_tentative, event_id)
        ORDER BY window_days, include_tentative, event_id""")
    bad = con.execute("SELECT COUNT(*) FROM mart_event_kpis k JOIN did_significance s USING (window_days, include_tentative, event_id) WHERE ABS(k.diff_in_diff_opp_rate - s.did) > 1e-9").fetchone()[0]
    if bad:
        raise AssertionError("Permutation-test statistic does not match the SQL difference-in-differences")


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
