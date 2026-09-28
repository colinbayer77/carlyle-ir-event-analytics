"""With no extra filters, app/metrics.py must reproduce the SQL mart exactly."""
import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "app"))
from metrics import Filters, event_kpis, prepare  # noqa: E402

D = {p.stem: pd.read_csv(p) for p in (ROOT / "data" / "marts").glob("*.csv")}
P = prepare(D)
COLS = ["firms_attended", "tier1_firms", "firms_with_senior", "cost_per_firm", "firms_followup_30", "followup_rate_30",
        "median_days_to_followup", "meetings_pre_60", "meetings_post_60", "assoc_opps", "assoc_firms", "firm_conversion_rate",
        "assoc_pipeline_usd", "assoc_pipeline_ex_outlier_usd", "assoc_opps_reached_dd", "assoc_committed_opps", "assoc_committed_usd",
        "assoc_declined_opps", "median_days_event_to_opp", "cost_per_assoc_opp", "attendee_new_opp_rate", "attendee_prior_opp_rate",
        "non_attendee_new_opp_rate", "non_attendee_prior_opp_rate", "non_attendee_firms", "diff_in_diff_opp_rate",
        "open_opps_attendees", "open_opps_attendees_advanced", "open_opps_non_attendees", "open_opps_non_attendees_advanced",
        "open_pipeline_attendees_usd", "p_value_did"]


def test_default_filters_match_sql_mart():
    for w in (30, 60, 90, 180):
        for t in (False, True):
            got = event_kpis(P, Filters(window=w, tentative=t)).set_index("event_id")[COLS].astype(float)
            exp = D["mart_event_kpis"].query("window_days == @w and include_tentative == @t").set_index("event_id")[COLS].astype(float)
            np.testing.assert_allclose(got.to_numpy(), exp.to_numpy(), rtol=1e-9, atol=1e-9, equal_nan=True,
                                       err_msg=f"window={w} tentative={t}")


def test_filters_only_shrink():
    base = event_kpis(P, Filters())
    for f in [Filters(segment="Pension"), Filters(fund="Fund Beta"), Filters(seniority="senior"), Filters(exclude_outlier=True),
              Filters(segment=("Pension", "Insurance")), Filters(fund=("Fund Alpha", "Fund Beta"))]:
        k = event_kpis(P, f)
        assert (k.assoc_opps <= base.assoc_opps).all() and (k.firms_attended <= base.firms_attended).all(), f


def test_multiselect_semantics():
    """Two segments = sum of each alone for firm counts; both seniority options = no filter."""
    a, b = event_kpis(P, Filters(segment="Pension")), event_kpis(P, Filters(segment="Insurance"))
    ab = event_kpis(P, Filters(segment=("Pension", "Insurance")))
    assert (ab.firms_attended.values == a.firms_attended.values + b.firms_attended.values).all()
    assert (ab.assoc_opps.values == a.assoc_opps.values + b.assoc_opps.values).all()
    both = event_kpis(P, Filters(seniority=("senior", "non_senior")))
    assert Filters(seniority=("senior", "non_senior")).is_default_extra
    assert (both.assoc_opps.values == event_kpis(P, Filters()).assoc_opps.values).all()


if __name__ == "__main__":
    test_multiselect_semantics()
    test_default_filters_match_sql_mart(); test_filters_only_shrink(); print("metrics tests passed")
