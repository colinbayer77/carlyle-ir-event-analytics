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
# Carlyle navy for chrome; validated categorical palette (dataviz validator, all-pairs, light mode) for data.
NAVY = "#0c374a"
EV_COLOR = {"E001": "#2f6ea5", "E002": "#c98a1b", "E003": "#2a9d8f"}
NEUTRAL, BLUE, AQUA, ORANGE = "#b9b7b0", "#2f6ea5", "#2a9d8f", "#c98a1b"
LOGO_WHITE = ROOT / "assets" / "carlyle_logo_white.png"

st.set_page_config(page_title="Carlyle | IR Event Outcomes", page_icon=str(ROOT / "assets" / "carlyle_logo.png"), layout="wide")


def brand_css() -> None:
    import base64

    logo = base64.b64encode(LOGO_WHITE.read_bytes()).decode()
    st.markdown(
        f"""
<style>
@import url('https://fonts.googleapis.com/css2?family=EB+Garamond:wght@500;600&family=Inter:wght@400;500;600&display=swap');
html, body, [class*="css"], .stMarkdown, .stDataFrame {{ font-family: 'Inter', system-ui, sans-serif; }}
header[data-testid="stHeader"] {{ display: none; }}
.block-container {{ padding-top: 1.2rem; max-width: 1320px; }}
.brand-bar {{ background: {NAVY}; border-radius: 10px; padding: 22px 28px 18px; margin-bottom: 18px; color: #fff; }}
.brand-bar .row {{ display: flex; align-items: center; gap: 18px; flex-wrap: wrap; }}
.brand-bar img {{ height: 24px; }}
.brand-bar .div {{ width: 1px; height: 28px; background: rgba(255,255,255,.35); }}
.brand-bar h1 {{ font-family: 'EB Garamond', Georgia, serif; font-weight: 600; font-size: 28px; margin: 0; padding: 0; color: #fff; }}
.brand-bar p {{ margin: 10px 0 0; color: #c9d7df; font-size: 14px; }}
h2, h3, .stSubheader {{ font-family: 'EB Garamond', Georgia, serif !important; color: {NAVY} !important; font-weight: 600 !important; }}
.chart-title {{ font-family: 'EB Garamond', Georgia, serif; font-size: 20px; font-weight: 600; color: {NAVY}; margin: 6px 0 0; }}
.chart-sub {{ color: #5b6570; font-size: 13px; margin: 2px 0 4px; }}
div[data-testid="stMetric"] {{ background: #f2f5f7; border: 1px solid #e1e7eb; border-radius: 10px; padding: 12px 16px; }}
div[data-testid="stMetricValue"] {{ color: {NAVY}; font-weight: 700; }}
.stTabs [data-baseweb="tab-list"] {{ gap: 6px; border-bottom: 1px solid #e1e7eb; }}
.stTabs [data-baseweb="tab"] {{ font-weight: 500; }}
.stTabs [aria-selected="true"] {{ color: {NAVY} !important; }}
.stTabs [data-baseweb="tab-highlight"] {{ background-color: {NAVY} !important; }}
div[data-testid="stAlert"] {{ background: #eef3f6 !important; border: 1px solid #d6e0e6; }}
div[data-testid="stAlert"] * {{ color: #1b1f24 !important; }}
.foot {{ color: #7a848e; font-size: 12px; margin-top: 30px; border-top: 1px solid #e1e7eb; padding-top: 10px; }}
</style>
<div class="brand-bar"><div class="row"><img src="data:image/png;base64,{logo}" alt="Carlyle"><span class="div"></span>
<h1>Investor Relations · Event Outcomes</h1></div>
<p>What happened after our 2026 investor events, what outcomes are associated with them, and what to change next time.
Association, not causation: see the Method tab.</p></div>
""",
        unsafe_allow_html=True,
    )


def donut_fig(labels, values, colors, center, sub, fmt):
    fig = go.Figure(go.Pie(labels=labels, values=values, hole=0.62, sort=False, direction="clockwise",
                           marker=dict(colors=colors, line=dict(color="#ffffff", width=2)),
                           texttemplate="%{percent:.0%}", textfont=dict(color="#ffffff", size=13),
                           customdata=[fmt(v) for v in values],
                           hovertemplate="%{label}<br>%{customdata} (%{percent:.0%})<extra></extra>"))
    fig.update_layout(height=320, margin=dict(l=10, r=10, t=10, b=10), showlegend=True,
                      legend=dict(orientation="v", x=1.02, y=0.5, font=dict(size=12)),
                      font=dict(family="Inter, system-ui, sans-serif", color="#3b4450"),
                      annotations=[dict(text=f"<span style='font-size:22px;color:{NAVY}'><b>{center}</b></span><br><span style='font-size:12px'>{sub}</span>",
                                        showarrow=False, x=0.5, y=0.5, xref="paper", yref="paper")])
    return fig


def line_layout(fig, height=320, top=40):
    fig.update_layout(height=height, margin=dict(l=10, r=10, t=top, b=10), plot_bgcolor="rgba(0,0,0,0)", hovermode="x unified",
                      legend=dict(orientation="h", y=1.12, x=0), font=dict(family="Inter, system-ui, sans-serif", color="#3b4450"))
    fig.update_yaxes(gridcolor="#e6eaed", zeroline=False, rangemode="tozero")
    return fig


def chart_head(col, title: str, sub: str = "") -> None:
    col.markdown(f'<div class="chart-title">{title}</div>' + (f'<div class="chart-sub">{sub}</div>' if sub else ""), unsafe_allow_html=True)


@st.cache_data
def load() -> dict[str, pd.DataFrame]:
    if not (MARTS / "mart_event_kpis.csv").exists():
        import subprocess, sys

        subprocess.run([sys.executable, str(ROOT / "src" / "build.py")], check=True, cwd=ROOT / "src")
    return {p.stem: pd.read_csv(p) for p in MARTS.glob("*.csv")}


D = load()
monthly, curve = D["mart_monthly"], D["mart_event_curve"]
kpi_all, fe, firms, opps, tl, seg, dq = (
    D["mart_event_kpis"], D["mart_firm_event"], D["mart_firm"], D["mart_opportunity"],
    D["mart_firm_timeline"], D["mart_segment"], D["dq_log"],
)


def fm(v: float) -> str:
    if pd.isna(v):
        return "-"
    if v == 0:
        return "$0M"
    return f"${v / 1e9:.2f}B" if v >= 1e9 else f"${v / 1e6:,.1f}M" if v < 1e7 else f"${v / 1e6:,.0f}M"


def fk(v: float) -> str:
    return "-" if pd.isna(v) else f"${v / 1e3:,.0f}K"


def bar_fig(x, series, yfmt=None, horizontal=False, height=300):
    fig = go.Figure()
    for name, vals, color in series:
        fig.add_bar(name=name, x=vals if horizontal else x, y=x if horizontal else vals,
                    marker_color=color, orientation="h" if horizontal else "v")
    fig.update_layout(barmode="group", height=height, margin=dict(l=10, r=10, t=30, b=10),
                      legend=dict(orientation="h", y=1.12, x=0), plot_bgcolor="rgba(0,0,0,0)",
                      font=dict(family="Inter, system-ui, sans-serif", color="#3b4450"))
    fig.update_yaxes(gridcolor="#e6eaed", zeroline=False)
    if yfmt:
        (fig.update_xaxes if horizontal else fig.update_yaxes)(tickformat=yfmt)
    return fig


brand_css()

c1, c2 = st.columns([1, 3])
window = c1.selectbox("Association window (days)", [30, 60, 90, 180], index=2,
                      help="How many days after an event a new opportunity can be opened and still be linked to that event. The firm must have attended; if several events qualify, the most recent one gets credit. Longer windows link more pipeline but make the link to the event weaker.")
tent = c2.toggle("Include tentative firm registrations as attendance", value=False,
                 help="Each registrant is Confirmed or Tentative. By default a firm counts as attending an event only if at least one of its contacts is Confirmed. Turn this on to also count the 9 firm-event registrations where every contact was Tentative. Off by default because the data has no check-in record, so tentative firms may not have attended.")
K = kpi_all[(kpi_all.window_days == window) & (kpi_all.include_tentative == tent)].sort_values("event_id")
labels = [EV_SHORT[e] for e in K.event_id]

tab_o, tab_f, tab_x, tab_p, tab_m = st.tabs(["Executive summary", "Follow-up & segments", "Firm explorer", "Opportunities", "Method & data quality"])

with tab_o:
    reached = fe[fe.is_confirmed | tent].firm_id.nunique()
    cols = st.columns(3) + st.columns(3)
    cols[0].metric("Event spend", fm(K.cost_usd.sum()), help="3 events, 2026")
    cols[1].metric("Firms reached", reached, help=f"of {len(firms)} covered firms")
    cols[2].metric("Associated opportunities", int(K.assoc_opps.sum()), help=f"of {len(opps)} opened this year")
    cols[3].metric("Associated pipeline", fm(K.assoc_pipeline_usd.sum()))
    cols[4].metric("Associated commitments", fm(K.assoc_committed_usd.sum()))
    cols[5].metric("Follow-up within 30 days", f"{K.firms_followup_30.sum() / K.firms_attended.sum():.0%}")

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
        "Median days to first follow-up": K.median_days_to_followup.map(lambda v: "-" if pd.isna(v) else f"{v:.0f}"),
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
    chart_head(a, "New opportunities and meetings by month, 2026",
               "Dashed lines mark events. Opportunity creation peaked in June and July for all firms. September is partial.")
    mlab = pd.to_datetime(monthly.month).dt.strftime("%b").tolist()
    if monthly.month.iloc[-1].startswith("2026-09"):
        mlab[-1] += "*"
    fig = go.Figure()
    fig.add_scatter(x=mlab, y=monthly.new_opps, name="New opportunities", mode="lines+markers", line=dict(color=BLUE, width=2.5, shape="spline"), marker=dict(size=8))
    fig.add_scatter(x=mlab, y=monthly.meetings, name="Meetings", mode="lines+markers", line=dict(color=ORANGE, width=2.5, shape="spline"), marker=dict(size=8))
    n = 0
    for k, ev in enumerate(monthly.events_in_month):
        if isinstance(ev, str):
            fig.add_vline(x=k, line=dict(color="#8a949c", dash="dash", width=1))
            fig.add_annotation(x=k, y=1.0 + 0.08 * (n % 2), yref="paper", yanchor="bottom",
                               text=" / ".join(EV_SHORT[e] for e in ev.split(",")), showarrow=False, font=dict(size=11, color="#5b6570"))
            n += 1
    fig.update_layout(legend=dict(orientation="h", y=-0.15, x=0))
    a.plotly_chart(line_layout(fig, top=60).update_layout(legend=dict(orientation="h", y=-0.15, x=0)), width="stretch")
    chart_head(b, "Where 2026 pipeline came from", "Share of $ pipeline by source, default rule (90 days, confirmed).")
    order = ["Event-associated (90d)", "Attendee, outside window", "No confirmed attendance"]
    vals = [opps.loc[opps.source_bucket == o, "amount_usd"].sum() for o in order]
    b.plotly_chart(donut_fig(["Opened within 90d of an attended event", "Attendee firm, outside window", "Firm with no confirmed attendance"],
                             vals, [BLUE, AQUA, NEUTRAL], fm(sum(vals)), "2026 pipeline", fm), width="stretch")

    a, b = st.columns(2)
    chart_head(a, "Cost per associated opportunity",
               "Event cost / opportunities created in window (lower is better). Label shows the share of attending firms that converted.")
    fig = go.Figure(go.Bar(
        x=labels, y=K.cost_per_assoc_opp, marker_color=[EV_COLOR[e] for e in K.event_id],
        text=[f"<b>{fk(c)}</b><br>{r:.0%} converted" for c, r in zip(K.cost_per_assoc_opp, K.firm_conversion_rate)],
        textposition="outside", cliponaxis=False))
    fig.update_layout(height=340, margin=dict(l=10, r=10, t=30, b=10), yaxis_tickprefix="$", plot_bgcolor="rgba(0,0,0,0)",
                      font=dict(family="Inter, system-ui, sans-serif", color="#3b4450"),
                      yaxis=dict(range=[0, K.cost_per_assoc_opp.max() * 1.3], gridcolor="#e6eaed"))
    fig.update_layout(uniformtext_minsize=11, uniformtext_mode="show")
    a.plotly_chart(fig, width="stretch")
    chart_head(b, "Associated pipeline and commitments",
               "Percentage on Committed bars is commitment conversion: committed $ / associated pipeline $.")
    conv = (K.assoc_committed_usd / K.assoc_pipeline_usd.where(K.assoc_pipeline_usd > 0)).fillna(0)
    fig = bar_fig(labels, [("Associated pipeline", K.assoc_pipeline_usd / 1e6, BLUE), ("Committed", K.assoc_committed_usd / 1e6, AQUA)], height=340)
    fig.data[0].update(text=[f"<b>{fm(v)}</b>" for v in K.assoc_pipeline_usd], textposition="outside", cliponaxis=False)
    fig.data[1].update(text=[f"<b>{fm(v) if v else '$0M'}</b><br>{c:.0%}" for v, c in zip(K.assoc_committed_usd, conv)],
                       hovertemplate="%{x}<br>Committed: $%{y:.0f}M<extra></extra>",
                       textposition="outside", cliponaxis=False)
    fig.update_yaxes(tickprefix="$", ticksuffix="M", range=[0, K.assoc_pipeline_usd.max() / 1e6 * 1.25])
    fig.update_layout(uniformtext_minsize=11, uniformtext_mode="show", legend=dict(y=1.18))
    b.plotly_chart(fig, width="stretch")
    a, b = st.columns(2)
    chart_head(a, "New-opportunity rate before vs after the event")
    a.plotly_chart(bar_fig(labels, [
        ("Attendees, before", K.attendee_prior_opp_rate, NEUTRAL), ("Attendees, after", K.attendee_new_opp_rate, BLUE),
        ("Non-attendees, before", K.non_attendee_prior_opp_rate, "#dcdad4"), ("Non-attendees, after", K.non_attendee_new_opp_rate, ORANGE)], yfmt=".0%"), width="stretch")
    chart_head(b, "Meetings with attending firms, 60 days before vs after")
    b.plotly_chart(bar_fig(labels, [("Before", K.meetings_pre_60, NEUTRAL), ("After", K.meetings_post_60, BLUE)]), width="stretch")

with tab_f:
    conf = fe[fe.is_confirmed]
    a, b = st.columns(2)
    chart_head(a, "Follow-up within 30 days, by tier and event")
    g = conf.groupby(["tier", "event_id"]).followed_up_30.mean().unstack()
    a.plotly_chart(bar_fig(list(g.index), [(EV_SHORT[e], g[e], EV_COLOR[e]) for e in g.columns], yfmt=".0%"), width="stretch")
    d = conf.days_to_first_followup
    fu_vals = [int((d <= 30).sum()), int(((d > 30) & (d <= 60)).sum()), int((d > 60).sum()), int(d.isna().sum())]
    chart_head(a, "Follow-up status of attending firms", "All confirmed firm-event pairs: time from event to first meeting.")
    a.plotly_chart(donut_fig(["Met within 30 days", "Met in 31-60 days", "Met after 60 days", "No meeting since event"], fu_vals,
                             [BLUE, AQUA, ORANGE, NEUTRAL], f"{fu_vals[0] / len(conf):.0%}", "met within 30 days",
                             lambda v: f"{v} firm-events"), width="stretch")
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
    chart_head(a, "Where pipeline came from ($M)")
    a.plotly_chart(bar_fig(list(src.index), [("Pipeline", src.pipeline / 1e6, BLUE), ("Committed", src.committed.fillna(0) / 1e6, AQUA)]), width="stretch")
    stages = ["Initial Conversation", "Follow-up / VDR", "Due Diligence", "IC / Documentation", "Committed"]
    ea, other = opps[opps.assoc_event_id_90.notna()], opps[opps.assoc_event_id_90.isna()]
    chart_head(b, "Funnel: count reaching each stage")
    b.plotly_chart(bar_fig(stages, [("Event-associated", [(ea.max_stage_rank >= i + 1).sum() for i in range(5)], BLUE),
                                    ("All other", [(other.max_stage_rank >= i + 1).sum() for i in range(5)], NEUTRAL)], horizontal=True), width="stretch")
    chart_head(st, "How fast opportunities followed each event",
               "Cumulative associated opportunities by days after the event (180-day window, confirmed, most recent event gets credit). "
               "Lines stop at each event's age on the as-of date; no opportunities were created after 2026-08-12, so lines flatten after that.")
    fig = go.Figure()
    for e, name in EV_SHORT.items():
        age = int(kpi_all.loc[kpi_all.event_id == e, "days_since_event"].iloc[0])
        days = list(range(0, min(180, age) + 1, 5))
        pts = curve[curve.event_id == e]
        fig.add_scatter(x=days, y=[int(pts.loc[pts.days_after_event <= x, "opps"].sum()) for x in days], name=name, mode="lines",
                        line=dict(color=EV_COLOR[e], width=2.5, shape="hv"))
    fig.update_xaxes(title="Days after event", gridcolor="#f0f2f4")
    fig.update_yaxes(title="Cumulative opportunities")
    st.plotly_chart(line_layout(fig, height=340), width="stretch")
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

def md_doc(name: str) -> str:
    """Read a docs/ markdown file, demote headings under the tab's subheader, escape $ (Streamlit treats $..$ as LaTeX)."""
    import re

    text = (ROOT / "docs" / name).read_text().replace("$", "\\$")
    return re.sub(r"^(#{1,3}) ", lambda m: "#" * (len(m.group(1)) + 2) + " ", text, flags=re.M)


DATA_MODEL_DOT = """
digraph G {
  rankdir=LR; nodesep=0.25; ranksep=0.5;
  node [shape=box, style="rounded,filled", fontname="Helvetica", fontsize=11, color="#c9d3da", fillcolor="#f2f5f7"];
  edge [color="#8a98a3", arrowsize=0.6];
  subgraph cluster_raw { label="Source CSVs"; fontname="Helvetica"; fontsize=12; color="#e1e7eb";
    r_ev [label="events (3)"]; r_fi [label="firms (60)"]; r_at [label="event_attendees (131)"];
    r_me [label="meetings (112)"]; r_op [label="opportunity_stage_history (358)"]; }
  subgraph cluster_core { label="Core model"; fontname="Helvetica"; fontsize=12; color="#e1e7eb";
    d_ev [label="dim_event", fillcolor="#dbe7f1"]; d_fi [label="dim_firm", fillcolor="#dbe7f1"];
    f_fe [label="fct_firm_event\nfirm x event"]; f_me [label="fct_meeting"];
    f_op [label="fct_opportunity\n1 row per opp"]; }
  br [label="bridge_opp_event\nopp -> credited event\n(window x attendance rule)", fillcolor="#f6ecd6"];
  subgraph cluster_mart { label="Marts (dashboards read these)"; fontname="Helvetica"; fontsize=12; color="#e1e7eb";
    m_k [label="mart_event_kpis"]; m_fe [label="mart_firm_event"]; m_f [label="mart_firm"];
    m_o [label="mart_opportunity"]; m_t [label="mart_firm_timeline"]; m_s [label="mart_segment"]; }
  r_ev -> d_ev; r_fi -> d_fi; r_at -> f_fe; r_me -> f_me; r_op -> f_op;
  d_ev -> f_fe; d_fi -> f_fe; f_fe -> br; f_op -> br; d_ev -> br;
  br -> m_k; f_me -> m_k; f_fe -> m_fe; br -> m_fe; br -> m_o; f_op -> m_o; m_o -> m_f; f_me -> m_t; f_op -> m_t; m_fe -> m_s;
}
"""

with tab_m:
    st.subheader("Underlying data and data model")
    st.markdown(md_doc("DATA.md"))
    st.graphviz_chart(DATA_MODEL_DOT, width="stretch")
    st.divider()
    st.markdown(md_doc("METHOD.md"))
    st.subheader("Data-quality log")
    st.dataframe(dq, width="stretch", hide_index=True)

st.markdown('<div class="foot">Synthetic assessment data, as of 2026-09-23. Built by Colin Bayer for the Carlyle BI &amp; Analytics Lead take-home.</div>', unsafe_allow_html=True)
