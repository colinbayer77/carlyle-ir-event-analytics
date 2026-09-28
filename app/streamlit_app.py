"""Streamlit version of the IR event outcomes dashboard.

Reads the same marts as docs/index.html (built by src/build.py), so both
experiences show identical numbers.

Run:  streamlit run app/streamlit_app.py
"""
from __future__ import annotations

from pathlib import Path

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

ROOT = Path(__file__).resolve().parents[1]
MARTS = ROOT / "data" / "marts"
EV_SHORT = {"E001": "NY Summit", "E002": "London Dinner", "E003": "Berlin Forum"}
EV_COLOR = {"E001": "#2a78d6", "E002": "#eb6834", "E003": "#1baf7a"}
NEUTRAL, BLUE, AQUA, ORANGE = "#b9b7b0", "#2a78d6", "#1baf7a", "#eb6834"

st.set_page_config(page_title="IR Event Outcomes", layout="wide")


@st.cache_data
def load() -> dict[str, pd.DataFrame]:
    if not (MARTS / "mart_event_kpis.csv").exists():
        import subprocess, sys

        subprocess.run([sys.executable, str(ROOT / "src" / "build.py")], check=True, cwd=ROOT / "src")
    return {p.stem: pd.read_csv(p) for p in MARTS.glob("*.csv")}


D = load()
kpi_all, fe, firms, opps, tl, seg, dq = (
    D["mart_event_kpis"], D["mart_firm_event"], D["mart_firm"], D["mart_opportunity"],
    D["mart_firm_timeline"], D["mart_segment"], D["dq_log"],
)


def fm(v: float) -> str:
    if pd.isna(v):
        return "-"
    return f"${v / 1e9:.2f}B" if v >= 1e9 else f"${v / 1e6:,.1f}M" if v < 1e7 else f"${v / 1e6:,.0f}M"


def fk(v: float) -> str:
    return "-" if pd.isna(v) else f"${v / 1e3:,.0f}K"


def bar_fig(x, series, yfmt=None, horizontal=False, height=300):
    fig = go.Figure()
    for name, vals, color in series:
        fig.add_bar(name=name, x=vals if horizontal else x, y=x if horizontal else vals,
                    marker_color=color, orientation="h" if horizontal else "v")
    fig.update_layout(barmode="group", height=height, margin=dict(l=10, r=10, t=30, b=10),
                      legend=dict(orientation="h", y=1.12, x=0), plot_bgcolor="rgba(0,0,0,0)")
    if yfmt:
        (fig.update_xaxes if horizontal else fig.update_yaxes)(tickformat=yfmt)
    return fig


st.title("Investor Event Outcomes")
st.caption("What happened after our 2026 investor events, what outcomes are associated with them, and what to change next time. "
           "Association, not causation: see the Method tab.")

c1, c2 = st.columns([1, 3])
window = c1.selectbox("Association window (days)", [30, 60, 90, 180], index=2)
tent = c2.toggle("Include tentative-only firms", value=False)
K = kpi_all[(kpi_all.window_days == window) & (kpi_all.include_tentative == tent)].sort_values("event_id")
labels = [EV_SHORT[e] for e in K.event_id]

tab_o, tab_f, tab_x, tab_p, tab_m = st.tabs(["Overview", "Follow-up & segments", "Firm explorer", "Opportunities", "Method & data quality"])

with tab_o:
    reached = fe[fe.is_confirmed | tent].firm_id.nunique()
    cols = st.columns(6)
    cols[0].metric("Event spend", fm(K.cost_usd.sum()))
    cols[1].metric("Firms reached", reached, help=f"of {len(firms)} covered firms")
    cols[2].metric("Associated opps", int(K.assoc_opps.sum()), help=f"of {len(opps)} opened this year")
    cols[3].metric("Associated pipeline", fm(K.assoc_pipeline_usd.sum()))
    cols[4].metric("Associated commitments", fm(K.assoc_committed_usd.sum()))
    cols[5].metric("Follow-up within 30d", f"{K.firms_followup_30.sum() / K.firms_attended.sum():.0%}")

    d = kpi_all[(kpi_all.window_days == 90) & (~kpi_all.include_tentative)].set_index("event_id")
    t1 = fe[fe.is_confirmed & (fe.tier == "Tier 1")]
    st.info(
        f"""**What leadership should take away** (default rule: 90 days, confirmed)

1. **Most pipeline did not follow an event.** {int(d.assoc_opps.sum())} of {len(opps)} opportunities ({fm(d.assoc_pipeline_usd.sum())} of {fm(opps.amount_usd.sum())}) opened within 90 days of an attended event. The largest commitment ($650M) came from a firm that attended nothing.
2. **No consistent lift versus non-attendees.** Difference-in-differences in new-opportunity rate: NY {d.loc['E001','diff_in_diff_opp_rate']*100:+.0f} pts, London {d.loc['E002','diff_in_diff_opp_rate']*100:+.0f} pts, Berlin {d.loc['E003','diff_in_diff_opp_rate']*100:+.0f} pts.
3. **Follow-up is the controllable gap.** {d.firms_followup_30.sum() / d.firms_attended.sum():.0%} of attending firms met within 30 days; Tier 1 only {int(t1.followed_up_30.sum())} of {len(t1)}.
4. **London dinner ($185K) was most efficient:** {fk(d.loc['E002','cost_per_assoc_opp'])} per associated opp vs {fk(d.loc['E001','cost_per_assoc_opp'])} NY and {fk(d.loc['E003','cost_per_assoc_opp'])} Berlin.
5. **Berlin ($610K) needs a case before renewal:** attendee meetings fell {int(d.loc['E003','meetings_pre_60'])} → {int(d.loc['E003','meetings_post_60'])}, no commitments yet (recheck at 180 days)."""
        .replace("$", "\\$")  # stop Streamlit markdown reading $...$ as LaTeX
    )

    rows = {
        "Date / type": K.event_date + " · " + K.event_type,
        "Cost": K.cost_usd.map(fk),
        "Firms attended (Tier 1)": K.firms_attended.astype(str) + " (" + K.tier1_firms.astype(str) + ")",
        "Cost per firm": K.cost_per_firm.map(fk),
        "Follow-up within 30d": K.followup_rate_30.map("{:.0%}".format),
        "Median days to first follow-up": K.median_days_to_followup.astype(str),
        "Meetings 60d before → after": K.meetings_pre_60.astype(int).astype(str) + " → " + K.meetings_post_60.astype(int).astype(str),
        "Associated opportunities": K.assoc_opps.astype(str),
        "Associated pipeline": K.assoc_pipeline_usd.map(fm),
        "Committed": K.assoc_committed_usd.map(fm) + " (" + K.assoc_committed_opps.astype(str) + ")",
        "Cost per associated opp": K.cost_per_assoc_opp.map(fk),
        "New-opp rate attendees before → after": K.attendee_prior_opp_rate.map("{:.0%}".format) + " → " + K.attendee_new_opp_rate.map("{:.0%}".format),
        "New-opp rate non-attendees before → after": K.non_attendee_prior_opp_rate.map("{:.0%}".format) + " → " + K.non_attendee_new_opp_rate.map("{:.0%}".format),
        "Difference-in-differences": (K.diff_in_diff_opp_rate * 100).map("{:+.0f} pts".format),
        "Days since event (as-of)": K.days_since_event.astype(str),
    }
    score = pd.DataFrame({k: list(v) for k, v in rows.items()}, index=[f"{n} ({l})" for n, l in zip(K.event_name, K.location)]).T
    st.subheader("Event scorecard")
    st.dataframe(score, width="stretch")

    a, b = st.columns(2)
    a.markdown("**Cost per associated opportunity**")
    fig = go.Figure(go.Bar(x=labels, y=K.cost_per_assoc_opp, marker_color=[EV_COLOR[e] for e in K.event_id]))
    fig.update_layout(height=300, margin=dict(l=10, r=10, t=10, b=10), yaxis_tickprefix="$", plot_bgcolor="rgba(0,0,0,0)")
    a.plotly_chart(fig, width="stretch")
    b.markdown("**Associated pipeline and commitments ($M)**")
    b.plotly_chart(bar_fig(labels, [("Pipeline", K.assoc_pipeline_usd / 1e6, BLUE), ("Committed", K.assoc_committed_usd / 1e6, AQUA)]), width="stretch")
    a, b = st.columns(2)
    a.markdown("**New-opportunity rate before vs after the event**")
    a.plotly_chart(bar_fig(labels, [
        ("Attendees, before", K.attendee_prior_opp_rate, NEUTRAL), ("Attendees, after", K.attendee_new_opp_rate, BLUE),
        ("Non-attendees, before", K.non_attendee_prior_opp_rate, "#dcdad4"), ("Non-attendees, after", K.non_attendee_new_opp_rate, ORANGE)], yfmt=".0%"), width="stretch")
    b.markdown("**Meetings with attending firms, 60 days before vs after**")
    b.plotly_chart(bar_fig(labels, [("Before", K.meetings_pre_60, NEUTRAL), ("After", K.meetings_post_60, BLUE)]), width="stretch")

with tab_f:
    conf = fe[fe.is_confirmed]
    a, b = st.columns(2)
    a.markdown("**Follow-up within 30 days, by tier and event**")
    g = conf.groupby(["tier", "event_id"]).followed_up_30.mean().unstack()
    a.plotly_chart(bar_fig(list(g.index), [(EV_SHORT[e], g[e], EV_COLOR[e]) for e in g.columns], yfmt=".0%"), width="stretch")
    dim = b.selectbox("Cut conversion by", sorted(seg.dimension.unique()), index=sorted(seg.dimension.unique()).index("Tier"))
    s = seg[seg.dimension == dim]
    b.plotly_chart(bar_fig(list(s.value + " (n=" + s.firm_events.astype(str) + ")"),
                           [("Converted to opp (90d)", s.conversion_rate, BLUE), ("Followed up in 30d", s.followup_rate_30, NEUTRAL)],
                           yfmt=".0%", horizontal=True), width="stretch")
    st.subheader("Follow-up gaps: confirmed firms with no meeting within 60 days")
    leak = conf[conf.meetings_post_60.fillna(0) == 0].merge(firms[["firm_id", "pipeline_usd"]], on="firm_id")
    leak = leak.sort_values(["tier", "pipeline_usd"], ascending=[True, False])
    st.dataframe(leak.assign(event=leak.event_id.map(EV_SHORT), pipeline=leak.pipeline_usd.map(fm))[
        ["firm_name", "tier", "segment", "event", "senior_contacts", "days_to_first_followup", "pipeline"]],
        width="stretch", hide_index=True)

with tab_x:
    c = st.columns(5)
    ev = c[0].selectbox("Event", ["All"] + list(EV_SHORT), format_func=lambda e: EV_SHORT.get(e, e))
    tier = c[1].selectbox("Tier", ["All"] + sorted(firms.tier.unique()))
    sg = c[2].selectbox("Segment", ["All"] + sorted(firms.segment.unique()))
    rg = c[3].selectbox("Region", ["All"] + sorted(firms.region.unique()))
    q = c[4].text_input("Search firm")
    f = firms.copy()
    if ev != "All":
        f = f[f.events_confirmed.fillna("").str.contains(ev) | f.events_tentative_only.fillna("").str.contains(ev)]
    for col, val in [("tier", tier), ("segment", sg), ("region", rg)]:
        if val != "All":
            f = f[f[col] == val]
    if q:
        f = f[f.firm_name.str.contains(q, case=False) | f.firm_id.str.contains(q, case=False)]
    st.caption(f"{len(f)} firms. Select a firm below to see its timeline.")
    st.dataframe(f[["firm_id", "firm_name", "tier", "segment", "region", "events_confirmed", "events_tentative_only", "meetings", "opps",
                    "pipeline_usd", "assoc_pipeline_90_usd", "committed_usd", "has_unfollowed_event"]]
                 .sort_values("pipeline_usd", ascending=False), width="stretch", hide_index=True)
    if len(f):
        pick = st.selectbox("Firm timeline", f.firm_id, format_func=lambda i: f"{i} · {firms.set_index('firm_id').loc[i, 'firm_name']}")
        info = firms.set_index("firm_id").loc[pick]
        st.markdown(f"**{info.firm_name}** · {info.tier} · {info.segment} · {info.region} · historical commitments {fm(info.historical_commitments_usd)}")
        t = tl[tl.firm_id == pick].copy()
        t["detail"] = t.detail + t.is_projected.map({True: " (projected, after as-of date)", False: ""})
        st.dataframe(t[["dt", "kind", "detail"]], width="stretch", hide_index=True)

with tab_p:
    a, b = st.columns(2)
    src = opps.groupby("source_bucket").agg(pipeline=("amount_usd", "sum"), n=("opportunity_id", "count"))
    src["committed"] = opps[opps.outcome == "Committed"].groupby("source_bucket").amount_usd.sum()
    a.markdown("**Where pipeline came from ($M)**")
    a.plotly_chart(bar_fig(list(src.index), [("Pipeline", src.pipeline / 1e6, BLUE), ("Committed", src.committed.fillna(0) / 1e6, AQUA)]), width="stretch")
    stages = ["Initial Conversation", "Follow-up / VDR", "Due Diligence", "IC / Documentation", "Committed"]
    ea, other = opps[opps.assoc_event_id_90.notna()], opps[opps.assoc_event_id_90.isna()]
    b.markdown("**Funnel: count reaching each stage**")
    b.plotly_chart(bar_fig(stages, [("Event-associated", [(ea.max_stage_rank >= i + 1).sum() for i in range(5)], BLUE),
                                    ("All other", [(other.max_stage_rank >= i + 1).sum() for i in range(5)], NEUTRAL)], horizontal=True), width="stretch")
    c = st.columns(3)
    s1 = c[0].selectbox("Source", ["All"] + sorted(opps.source_bucket.unique()))
    s2 = c[1].selectbox("Outcome", ["All", "Open", "Committed", "Declined"])
    s3 = c[2].selectbox("Fund", ["All"] + sorted(opps.fund_name.unique()))
    o = opps
    for col, val in [("source_bucket", s1), ("outcome", s2), ("fund_name", s3)]:
        if val != "All":
            o = o[o[col] == val]
    st.dataframe(o[["opportunity_id", "firm_name", "tier", "fund_name", "created_date", "amount_usd", "current_stage", "outcome",
                    "assoc_event_id_90", "days_after_event_90", "is_amount_outlier", "projected_stage_rows"]],
                 width="stretch", hide_index=True)

with tab_m:
    st.markdown((ROOT / "docs" / "METHOD.md").read_text().replace("$", "\\$"))
    st.subheader("Data-quality log")
    st.dataframe(dq, width="stretch", hide_index=True)
