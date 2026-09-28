"""Filter-aware event KPIs, computed from the firm- and opportunity-level marts.

The SQL marts precompute KPIs for the window x tentative grid only. This module
recomputes the same KPIs under extra filters (investor segment, fund, attendee
seniority, excluding the outlier ticket). With no extra filters it reproduces
mart_event_kpis exactly; tests/test_metrics.py asserts that for all 24 grid cells.
docs/metrics.js is a line-for-line port for the static dashboard.

Filter semantics
  segment    keeps firms in the selected investor segments (attendees, comparison group, opportunities)
  fund       keeps opportunities for the selected funds (attendance and meetings unaffected)
  seniority  "senior": count attendance only where a CIO or MD was registered
             "non_senior": only where none was; firms dropped by this filter are
             excluded from the comparison group rather than counted as non-attendees
  Each of these three is multi-select: an empty selection (or "All") means no filter;
  selecting both seniority options is the same as no seniority filter.
  exclude_outlier drops opportunities flagged is_amount_outlier (O0017, $650M)
"""
from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd

N_PERMUTATIONS = 5_000


@dataclass(frozen=True)
class Filters:
    window: int = 90
    tentative: bool = False
    segment: tuple = ()
    fund: tuple = ()
    seniority: tuple = ()  # subset of ("senior", "non_senior")
    exclude_outlier: bool = False

    def __post_init__(self):
        for name in ("segment", "fund", "seniority"):
            v = getattr(self, name)
            v = () if v in (None, "All") else (v,) if isinstance(v, str) else tuple(sorted(x for x in v if x != "All"))
            object.__setattr__(self, name, v)

    @property
    def seniority_mode(self) -> str:
        return self.seniority[0] if len(self.seniority) == 1 else "All"

    @property
    def is_default_extra(self) -> bool:
        return not self.segment and not self.fund and self.seniority_mode == "All" and not self.exclude_outlier


def _median(s: pd.Series):
    s = s.dropna()
    return float(s.median()) if len(s) else None


def prepare(D: dict[str, pd.DataFrame]) -> dict:
    fe = D["mart_firm_event"].copy()
    fe["event_date"] = pd.to_datetime(fe.event_date)
    opps = D["mart_opportunity"].copy()
    for c in ["created_date", "committed_date", "declined_date"]:
        opps[c] = pd.to_datetime(opps[c])
    st = D["mart_stage_history"].copy()
    st["stage_date"] = pd.to_datetime(st.stage_date)
    k = D["mart_event_kpis"]
    events = (k.drop_duplicates("event_id")[["event_id", "event_name", "event_date", "event_type", "location", "cost_usd", "days_since_event"]]
              .assign(event_date=lambda x: pd.to_datetime(x.event_date)).sort_values("event_id").reset_index(drop=True))
    return dict(fe=fe, opps=opps, stages=st, events=events, firms=D["mart_firm"], meetings=D["mart_meetings"], kpis=k)


def attendance(P: dict, f: Filters) -> tuple[pd.DataFrame, pd.DataFrame]:
    """(attending firm-events after all filters, attending firm-events before the seniority filter)."""
    fe = P["fe"]
    base = fe[fe.is_confirmed | f.tentative]
    if f.segment:
        base = base[base.segment.isin(f.segment)]
    senior = base.senior_contacts.gt(0) if f.tentative else base.has_confirmed_senior
    att = base
    if f.seniority_mode == "senior":
        att = base[senior]
    elif f.seniority_mode == "non_senior":
        att = base[~senior]
    return att, base


def filtered_opps(P: dict, f: Filters) -> pd.DataFrame:
    o = P["opps"]
    if f.segment:
        o = o[o.segment.isin(f.segment)]
    if f.fund:
        o = o[o.fund_name.isin(f.fund)]
    if f.exclude_outlier:
        o = o[~o.is_amount_outlier]
    return o


def associate(opps: pd.DataFrame, att: pd.DataFrame, window: int) -> pd.DataFrame:
    """Last-touch association: credited event and days after it (NaN if none)."""
    pairs = opps[["opportunity_id", "firm_id", "created_date"]].merge(att[["firm_id", "event_id", "event_date"]], on="firm_id")
    pairs["days"] = (pairs.created_date - pairs.event_date).dt.days
    pairs = pairs[(pairs.days >= 0) & (pairs.days <= window)].sort_values(["opportunity_id", "days"]).drop_duplicates("opportunity_id")
    out = opps.merge(pairs[["opportunity_id", "event_id", "days"]], on="opportunity_id", how="left")
    return out.rename(columns={"event_id": "assoc_event_id", "days": "days_after_event"})


def _perm_pvalue(change: np.ndarray, attended: np.ndarray, rng) -> float:
    n_att = attended.sum()
    if n_att == 0 or n_att == len(attended):
        return float("nan")
    obs = change[attended].mean() - change[~attended].mean()
    perms = rng.permuted(np.tile(attended, (N_PERMUTATIONS, 1)), axis=1)
    null = (perms @ change) / n_att - ((~perms) @ change) / (len(attended) - n_att)
    return float(np.mean(np.abs(null) >= abs(obs) - 1e-12))


def event_kpis(P: dict, f: Filters) -> pd.DataFrame:
    att, base = attendance(P, f)
    opps = filtered_opps(P, f)
    assoc = associate(opps, att, f.window)
    firms = P["firms"] if not f.segment else P["firms"][P["firms"].segment.isin(f.segment)]
    stages = P["stages"]
    rng = np.random.default_rng(7)
    rows = []
    for ev in P["events"].itertuples():
        a = att[att.event_id == ev.event_id]
        all_att_ids = set(base[base.event_id == ev.event_id].firm_id)
        att_ids = set(a.firm_id)
        s = assoc[assoc.assoc_event_id == ev.event_id]
        n = len(a)
        r = dict(event_id=ev.event_id, event_name=ev.event_name, event_date=ev.event_date.strftime("%Y-%m-%d"), event_type=ev.event_type,
                 location=ev.location, cost_usd=ev.cost_usd, days_since_event=ev.days_since_event, window_days=f.window, include_tentative=f.tentative)
        r.update(firms_attended=n, tier1_firms=int((a.tier == "Tier 1").sum()),
                 firms_with_senior=int((a.senior_contacts.gt(0) if f.tentative else a.has_confirmed_senior).sum()),
                 cost_per_firm=ev.cost_usd / n if n else None,
                 firms_followup_30=int((a.meetings_post_30 > 0).sum()),
                 followup_rate_30=(a.meetings_post_30 > 0).mean() if n else None,
                 median_days_to_followup=_median(a.days_to_first_followup),
                 meetings_pre_60=int(a.meetings_pre_60.sum()), meetings_post_60=int(a.meetings_post_60.sum()),
                 assoc_opps=len(s), assoc_firms=s.firm_id.nunique(),
                 firm_conversion_rate=s.firm_id.nunique() / n if n else None,
                 assoc_pipeline_usd=float(s.amount_usd.sum()),
                 assoc_pipeline_ex_outlier_usd=float(s.loc[~s.is_amount_outlier, "amount_usd"].sum()),
                 assoc_opps_reached_dd=int(s.reached_dd.sum()),
                 assoc_committed_opps=int((s.outcome == "Committed").sum()),
                 assoc_committed_usd=float(s.loc[s.outcome == "Committed", "amount_usd"].sum()),
                 assoc_declined_opps=int((s.outcome == "Declined").sum()),
                 median_days_event_to_opp=_median(s.days_after_event))
        r["pipeline_to_cost"] = r["assoc_pipeline_usd"] / ev.cost_usd
        r["cost_per_assoc_opp"] = ev.cost_usd / r["assoc_opps"] if r["assoc_opps"] else None
        # comparison groups: attendees vs firms that did not attend at all
        ed, w = ev.event_date, pd.Timedelta(days=f.window)
        after = opps[(opps.created_date >= ed) & (opps.created_date <= ed + w)].firm_id.unique()
        before = opps[(opps.created_date < ed) & (opps.created_date >= ed - w)].firm_id.unique()
        grp = firms[firms.firm_id.isin(att_ids) | ~firms.firm_id.isin(all_att_ids)].copy()
        grp["att"] = grp.firm_id.isin(att_ids)
        grp["after"] = grp.firm_id.isin(after).astype(int)
        grp["before"] = grp.firm_id.isin(before).astype(int)
        A, N = grp[grp.att], grp[~grp.att]
        r.update(attendee_new_opp_rate=A.after.mean() if len(A) else None, attendee_prior_opp_rate=A.before.mean() if len(A) else None,
                 non_attendee_new_opp_rate=N.after.mean() if len(N) else None, non_attendee_prior_opp_rate=N.before.mean() if len(N) else None,
                 non_attendee_firms=len(N))
        r["diff_in_diff_opp_rate"] = (None if not len(A) or not len(N) else
                                      (r["attendee_new_opp_rate"] - r["attendee_prior_opp_rate"]) - (r["non_attendee_new_opp_rate"] - r["non_attendee_prior_opp_rate"]))
        r["p_value_did"] = _perm_pvalue((grp.after - grp.before).to_numpy(float), grp.att.to_numpy(bool), rng) if len(A) and len(N) else float("nan")
        # open pipeline at the event, and whether it advanced a stage within the window
        o = opps[(opps.created_date < ed) & ~(opps.committed_date < ed) & ~(opps.declined_date < ed)]
        adv_att = adv_non = n_att = n_non = 0
        open_usd = 0.0
        for op in o.itertuples():
            h = stages[stages.opportunity_id == op.opportunity_id]
            prior = h[(h.stage_date < ed) & (h.stage_rank > 0)].stage_rank
            rank0 = prior.max() if len(prior) else 0
            advanced = bool(((~h.is_future) & (h.stage_rank > rank0) & (h.stage_date >= ed) & (h.stage_date <= ed + w)).any())
            if op.firm_id in att_ids:
                n_att += 1; adv_att += advanced; open_usd += op.amount_usd
            elif op.firm_id not in all_att_ids:
                n_non += 1; adv_non += advanced
        r.update(open_opps_attendees=n_att, open_opps_attendees_advanced=adv_att, open_opps_non_attendees=n_non,
                 open_opps_non_attendees_advanced=adv_non, open_pipeline_attendees_usd=open_usd)
        rows.append(r)
    out = pd.DataFrame(rows)
    if f.is_default_extra:  # use the build's p-values so every surface shows the same number
        m = P["kpis"][(P["kpis"].window_days == f.window) & (P["kpis"].include_tentative == f.tentative)].set_index("event_id")
        out["p_value_did"] = out.event_id.map(m.p_value_did)
    out["did_significant"] = out.p_value_did < 0.05
    out["n_permutations"] = N_PERMUTATIONS
    return out
