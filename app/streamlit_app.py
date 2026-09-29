"""Streamlit version of the IR event outcomes dashboard.

Reads the same marts as docs/index.html (built by src/build.py), so both
experiences show identical numbers.

Run:  streamlit run app/streamlit_app.py
"""
from __future__ import annotations

from pathlib import Path

import sys

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

sys.path.insert(0, str(Path(__file__).resolve().parent))
from metrics import Filters, associate, attendance, event_kpis, filtered_opps, prepare  # noqa: E402

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
.block-container {{ padding-top: 0.6rem; padding-bottom: 1rem; max-width: 1320px; }}
.brand-bar {{ background: {NAVY}; border-radius: 10px; padding: 14px 24px 12px; margin-bottom: 12px; color: #fff; }}
.brand-bar .row {{ display: flex; align-items: center; gap: 18px; flex-wrap: wrap; }}
.brand-bar img {{ height: 24px; }}
.brand-bar .div {{ width: 1px; height: 28px; background: rgba(255,255,255,.35); }}
.brand-bar h1 {{ font-family: 'EB Garamond', Georgia, serif; font-weight: 600; font-size: 26px; margin: 0; padding: 0; color: #fff; }}
.brand-bar p {{ margin: 6px 0 0; color: #c9d7df; font-size: clamp(11px, 0.95vw, 13px); white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }}
h2, h3, .stSubheader {{ font-family: 'EB Garamond', Georgia, serif !important; color: {NAVY} !important; font-weight: 600 !important; }}
.chart-title {{ font-family: 'EB Garamond', Georgia, serif; font-size: 20px; font-weight: 600; color: {NAVY}; margin: 6px 0 0; }}
.chart-sub {{ color: #5b6570; font-size: 13px; margin: 2px 0 4px; }}
div[data-testid="stMetric"] {{ background: #f2f5f7; border: 1px solid #e1e7eb; border-radius: 10px; padding: 10px 12px; text-align: center; }}
[data-testid="stMetric"] {{ min-height: 108px; display: flex; flex-direction: column; justify-content: center; }}
[data-testid="stMetricLabel"] {{ display: flex !important; justify-content: center !important; align-items: center; width: 100%; position: static; }}
/* the help icon sits in the card's top-right corner, out of the flow, so the title stays centered */
[data-testid="stMetric"] {{ position: relative; }}
[data-testid="stMetricLabel"] > span {{ position: absolute; right: 8px; top: 8px; }}
[data-testid="stMetricLabel"] > div {{ width: auto !important; justify-content: center; }}
[data-testid="stMetricLabel"] p, [data-testid="stMetricLabel"] div {{ white-space: normal !important; overflow: visible !important; text-overflow: clip !important; text-align: center; }}
div[data-testid="stMetricValue"] {{ color: {NAVY}; font-weight: 700; justify-content: center; text-align: center; font-size: clamp(1.25rem, 2.1vw, 1.9rem); }}
div[data-testid="stMetricValue"] > div {{ text-align: center; width: 100%; overflow: visible !important; text-overflow: clip !important; }}
div[data-testid="stAlert"] p, div[data-testid="stAlert"] li {{ font-size: 14px; line-height: 1.45; margin-bottom: 2px; }}
div[data-testid="stElementContainer"]:has(> div > div[data-testid="stAlert"]) {{ margin-bottom: -6px; }}
.stTabs [data-baseweb="tab-list"] {{ gap: 6px; border-bottom: 1px solid #e1e7eb; }}
.st-key-nav {{ border-bottom: 1px solid #e1e7eb; margin-bottom: 6px; }}
/* denser text on the data model / data quality tab */
.st-key-tab_underlying_data_model_and_data_quality p, .st-key-tab_underlying_data_model_and_data_quality li {{ font-size: 13.5px; line-height: 1.45; }}
.st-key-tab_underlying_data_model_and_data_quality table {{ font-size: 12.5px; }}
.st-key-tab_underlying_data_model_and_data_quality th, .st-key-tab_underlying_data_model_and_data_quality td {{ padding: 5px 8px !important; line-height: 1.35; }}
.st-key-tab_underlying_data_model_and_data_quality td code, .st-key-tab_underlying_data_model_and_data_quality p code {{ font-size: 11.5px; }}
.st-key-tab_underlying_data_model_and_data_quality h4 {{ font-size: 18px !important; margin-top: 10px; }}
.st-key-tab_underlying_data_model_and_data_quality h5 {{ font-size: 15px !important; }}
.st-key-nav [role="radiogroup"] {{ gap: 2px 20px; flex-wrap: wrap; }}
.st-key-nav [data-testid="stRadioOption"] > div > div:first-child {{ display: none; }}
.st-key-nav [data-testid="stRadioOption"] {{ padding: 6px 2px 8px; margin: 0; border-bottom: 3px solid transparent; cursor: pointer; }}
.st-key-nav [data-testid="stRadioOption"][data-selected="true"] {{ border-bottom-color: {NAVY}; }}
.st-key-nav [data-testid="stRadioOption"][data-selected="true"] p {{ color: {NAVY}; font-weight: 600; }}
.st-key-nav [data-testid="stRadioOption"] p {{ font-size: 14px; color: #3b4450; }}
.st-key-nav [data-testid="stRadioOption"]:hover p {{ color: {NAVY}; }}
.stTabs [data-baseweb="tab"] {{ font-weight: 500; }}
.stTabs [aria-selected="true"] {{ color: {NAVY} !important; }}
.stTabs [data-baseweb="tab-highlight"] {{ background-color: {NAVY} !important; }}
div[data-testid="stAlert"] {{ background: #eef3f6 !important; border: 1px solid #d6e0e6; }}
div[data-testid="stAlert"] * {{ color: #1b1f24 !important; }}
.footnote {{ font-size: 10.5px; line-height: 1.35; color: #7a848e; margin: 2px 0 14px; }}
.foot {{ color: #7a848e; font-size: 12px; margin-top: 30px; border-top: 1px solid #e1e7eb; padding-top: 10px; }}
</style>
<div class="brand-bar"><div class="row"><img src="data:image/png;base64,{logo}" alt="Carlyle"><span class="div"></span>
<h1>Investor Relations · Event Outcomes</h1></div>
<p>What happened after our 2026 investor events, what outcomes followed, and what to change next time. Association, not causation.</p></div>
""",
        unsafe_allow_html=True,
    )


def donut_fig(labels, values, colors, center, sub, fmt):
    fig = go.Figure(go.Pie(labels=labels, values=values, hole=0.62, sort=False, direction="clockwise",
                           marker=dict(colors=colors, line=dict(color="#ffffff", width=2)),
                           texttemplate="%{percent:.0%}", textfont=dict(color="#ffffff", size=13),
                           customdata=[fmt(v) for v in values],
                           hovertemplate="%{label}<br>%{customdata} (%{percent:.0%})<extra></extra>"))
    fig.update_layout(height=380, margin=dict(l=10, r=10, t=10, b=70), showlegend=True,
                      legend=dict(orientation="h", x=0.5, xanchor="center", y=-0.08, yanchor="top", font=dict(size=12)),
                      font=dict(family="Inter, system-ui, sans-serif", color="#3b4450"),
                      annotations=[dict(text=f"<span style='font-size:22px;color:{NAVY}'><b>{center}</b></span><br><span style='font-size:12px'>{sub}</span>",
                                        showarrow=False, x=0.5, y=0.5, xref="paper", yref="paper")])
    return fig


def line_layout(fig, height=320, top=40):
    fig.update_layout(height=height, margin=dict(l=10, r=10, t=top, b=10), plot_bgcolor="rgba(0,0,0,0)", hovermode="x unified",
                      legend=dict(orientation="h", y=1.12, x=0), font=dict(family="Inter, system-ui, sans-serif", color="#3b4450"))
    fig.update_yaxes(gridcolor="#e6eaed", zeroline=False, rangemode="tozero")
    return fig


def footnote(text: str) -> None:
    st.markdown(f'<div class="footnote">{text}</div>', unsafe_allow_html=True)


def sig_note(rows: pd.DataFrame, label: str) -> str:
    ps = ", ".join(("n/a" if pd.isna(r.p_value_did) else f"{r.p_value_did:.2f}") + f" ({EV_SHORT[r.event_id]})" for r in rows.itertuples())
    return (f"Statistical significance: two-sided permutation test. Which firms attended each event was randomly reshuffled "
            f"{int(rows.n_permutations.iloc[0]):,} times to see how often a difference-in-differences this large appears by chance; "
            f"a gap counts as significant only if p < 0.05. {label}: p = {ps} against firms not at the event"
            + ("" if "p_value_did_clean" not in rows else "; " + ", ".join(("n/a" if pd.isna(r.p_value_did_clean) else f"{r.p_value_did_clean:.2f}")
                                                                          + f" ({EV_SHORT[r.event_id]})" for r in rows.itertuples()) + " against firms at no event")
            + ". 72 tests across the window and attendance settings; expect a few below 0.05 by chance.")


def inside_labels(values, axis_max, min_share, light_bar=False):
    """Labels centered inside the bar; bars shorter than min_share of the axis get their label just outside.
    White text on dark bars, dark text on light bars (light_bar=True)."""
    inside = [(v is not None and not pd.isna(v) and axis_max and v / axis_max >= min_share) for v in values]
    return dict(textposition=["inside" if i else "outside" for i in inside], insidetextanchor="middle", textangle=0,
                textfont=dict(color=["#ffffff" if i and not light_bar else "#1b1f24" for i in inside], size=10))


def label_bars(fig, labels_per_trace, light=(), min_share=0.12, horizontal=False, headroom=1.12):
    """Add centered data labels to every trace of a bar_fig and hide the value axis."""
    vals = [list(t.x if horizontal else t.y) for t in fig.data]
    vmax = max([v for vs in vals for v in vs if v is not None and not pd.isna(v)] + [1])
    for i, (t, txt) in enumerate(zip(fig.data, labels_per_trace)):
        t.update(text=txt, cliponaxis=False, **inside_labels(vals[i], vmax, min_share, light_bar=i in light))
    (fig.update_xaxes if horizontal else fig.update_yaxes)(visible=False, range=[0, vmax * headroom])
    fig.update_layout(uniformtext_minsize=9, uniformtext_mode="show")
    return fig


def chart_head(col, title: str, sub: str = "") -> None:
    col.markdown(f'<div class="chart-title">{title}</div>' + (f'<div class="chart-sub">{sub}</div>' if sub else ""), unsafe_allow_html=True)


def data_version() -> str:
    """Hash of the mart files. Every cached function takes it as an argument, so a redeploy with new
    data (Streamlit Cloud reruns the script without clearing st.cache_data) never serves stale frames."""
    import hashlib

    if not (MARTS / "mart_event_kpis.csv").exists():
        import subprocess, sys

        subprocess.run([sys.executable, str(ROOT / "src" / "build.py")], check=True, cwd=ROOT / "src")
    h = hashlib.sha256()
    for p in sorted(MARTS.glob("*.csv")):
        h.update(p.name.encode()); h.update(p.read_bytes())
    return h.hexdigest()


@st.cache_data
def load(version: str) -> dict[str, pd.DataFrame]:
    return {p.stem: pd.read_csv(p) for p in MARTS.glob("*.csv")}


DATA_VERSION = data_version()
D = load(DATA_VERSION)
monthly, curve = D["mart_monthly"], D["mart_event_curve"]
kpi_all, fe, firms, opps, tl, seg, dq = (
    D["mart_event_kpis"], D["mart_firm_event"], D["mart_firm"], D["mart_opportunity"],
    D["mart_firm_timeline"], D["mart_segment"], D["dq_log"],
)


def _r(x: float, nd: int = 0) -> float:
    """Round half up, like JavaScript's Math.round, so Python and the static page show the same figure."""
    from decimal import ROUND_HALF_UP, Decimal
    return float(Decimal(str(x)).quantize(Decimal(1).scaleb(-nd), rounding=ROUND_HALF_UP))


def fm(v: float) -> str:
    if pd.isna(v):
        return "-"
    if v == 0:
        return "$0M"
    return f"${_r(v / 1e9, 2):.2f}B" if v >= 1e9 else f"${_r(v / 1e6, 1):,.1f}M" if v < 1e7 else f"${_r(v / 1e6):,.0f}M"


def fk(v: float) -> str:
    return "-" if pd.isna(v) else f"${_r(v / 1e3):,.0f}K"


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

TAB_NAMES = ["Executive summary", "Event Scorecard", "Follow-up & segments", "Firm explorer", "Opportunities",
             "Underlying Data Model and Data Quality", "Next Event Planner"]
# A tab bar that knows which tab is open, so page-level filters can be hidden where they don't apply (the planner).
PAGE = st.radio("View", TAB_NAMES, horizontal=True, key="nav", label_visibility="collapsed")
SHOW_FILTERS = PAGE not in ("Next Event Planner", "Firm explorer", "Underlying Data Model and Data Quality")  # filters do not apply on these tabs
# Remember filter choices across tabs: a widget that isn't drawn on a run loses its state, so keep a copy.
SAVED = st.session_state.setdefault("_filters", {"window": 90, "events": [], "segment": [], "fund": [], "seniority": [], "tent": False, "excl": False})

if SHOW_FILTERS:
    row = st.columns(5)
    window = row[0].selectbox("Association window (days)", [30, 60, 90, 180], index=[30, 60, 90, 180].index(SAVED["window"]),
                              help="How many days after an event a new opportunity can be opened and still be linked to that event. The firm must have attended; if several events qualify, the most recent one gets credit. Longer windows link more pipeline but make the link to the event weaker. At 180 days, London and Berlin have not yet had the full window.")
    events = tuple(row[1].multiselect("Event", list(EV_SHORT), default=SAVED["events"], format_func=EV_SHORT.get, placeholder="All",
                                      help="Show only the selected events. Credit for each opportunity is still assigned across all three events (most recent attended event within the window), so nothing moves between events when you filter."))
    segment = tuple(row[2].multiselect("Investor segment", sorted(firms.segment.unique()), default=SAVED["segment"], placeholder="All",
                                       help="Pick one or more investor segments. Keeps only firms in those segments: attendees, the non-attendee comparison group, and their opportunities."))
    fund = tuple(row[3].multiselect("Fund", sorted(opps.fund_name.unique()), default=SAVED["fund"], placeholder="All",
                                    help="Pick one or more funds. Keeps only opportunities for those funds. Attendance, meetings and follow-up are not affected."))
    seniority = tuple(row[4].multiselect("Attendee seniority", ["senior", "non_senior"], default=SAVED["seniority"], placeholder="All",
                                 format_func={"senior": "CIO or MD registered", "non_senior": "No CIO or MD"}.get,
                                 help="Count attendance only where a CIO or Managing Director was registered (or only where none was). Selecting both options is the same as All. Firms dropped by this filter leave the comparison group too, rather than being counted as non-attendees."))
    row = st.columns([2.2, 1.3, 2.5])
    tent = row[0].toggle("Include tentative firm registrations as attendance", value=SAVED["tent"],
                         help="Each registrant is Confirmed or Tentative. By default a firm counts as attending an event only if at least one of its contacts is Confirmed. Turn this on to also count the 9 firm-event registrations where every contact was Tentative. Off by default because the data has no check-in record, so tentative firms may not have attended.")
    excl = row[1].toggle("Exclude $650M outlier", value=SAVED["excl"],
                         help="Removes O0017, a $650M commitment (next largest ticket is $150M). The firm attended no event, so event metrics do not change; totals, the pipeline donut and opportunity charts do.")
    SAVED.update(window=window, events=list(events), segment=list(segment), fund=list(fund), seniority=list(seniority), tent=tent, excl=excl)
else:
    window, events, segment, fund, seniority = SAVED["window"], tuple(SAVED["events"]), tuple(SAVED["segment"]), tuple(SAVED["fund"]), tuple(SAVED["seniority"])
    tent, excl = SAVED["tent"], SAVED["excl"]
F = Filters(window=window, tentative=tent, segment=segment, fund=fund, seniority=seniority, exclude_outlier=excl, events=events)
P = prepare(D)


@st.cache_data
def kpis_for(version, window, tentative, segment, fund, seniority, exclude_outlier, events) -> pd.DataFrame:
    return event_kpis(P, Filters(window, tentative, segment, fund, seniority, exclude_outlier, events))


K = kpis_for(DATA_VERSION, window, tent, segment, fund, seniority, excl, events).sort_values("event_id").reset_index(drop=True)
labels = [EV_SHORT[e] for e in K.event_id]

# filtered detail shared by the charts
ATT_ALL, _BASE = attendance(P, F)
SEL_EVENTS = list(events) or list(EV_SHORT)
ATT = ATT_ALL[ATT_ALL.event_id.isin(SEL_EVENTS)]  # attendance at the selected events
ATT_FIRMS = set(ATT.firm_id)
NONE_LABEL = "Did not attend selected events" if events else "No qualifying attendance" if F.seniority_mode != "All" else "No attendance" if tent else "No confirmed attendance"
BUCKETS = [f"Event-associated ({window}d)", "Attendee, not in window", NONE_LABEL]
FOPPS = associate(filtered_opps(P, F), ATT_ALL, window)  # credit across all events, then keep selected
FOPPS.loc[~FOPPS.assoc_event_id.isin(SEL_EVENTS), ["assoc_event_id", "days_after_event"]] = [None, float("nan")]
FOPPS["bucket"] = [BUCKETS[0] if isinstance(e, str) else BUCKETS[1] if fid in ATT_FIRMS else NONE_LABEL
                   for e, fid in zip(FOPPS.assoc_event_id, FOPPS.firm_id)]
FIRMS_IN = firms if not segment else firms[firms.segment.isin(segment)]


def describe(f: Filters) -> str:
    parts = [f"{f.window}-day window", "confirmed + tentative attendance" if f.tentative else "confirmed attendance"]
    if f.events:
        parts.append("events: " + ", ".join(EV_SHORT[e] for e in f.events))
    if f.segment:
        parts.append("segment: " + ", ".join(f.segment))
    if f.fund:
        parts.append("fund: " + ", ".join(f.fund))
    if f.seniority_mode != "All":
        parts.append("CIO/MD registered" if f.seniority_mode == "senior" else "no CIO/MD")
    if f.exclude_outlier:
        parts.append("excl. $650M outlier")
    return " · ".join(parts)


def pct(v) -> str:
    return "-" if v is None or pd.isna(v) else f"{v:.0%}"


if SHOW_FILTERS and (not F.is_default_extra or events):
    footnote(f"<b>Filters on:</b> {describe(F)} · {len(ATT)} attending firm-events, {len(FOPPS)} opportunities. "
             "Event cost is not split by filter. Small groups: read rates as directional.")

# Only the open tab stays on the page; the others are drawn into placeholders that are cleared at the end.
_hidden = []


def _tab(name):
    if name == PAGE:
        return st.container(key="tab_" + "".join(c if c.isalnum() else "_" for c in name.lower()))
    ph = st.empty()
    _hidden.append(ph)
    return ph.container()


tab_o, tab_s, tab_f, tab_x, tab_p, tab_m, tab_n = (_tab(n) for n in TAB_NAMES)

with tab_o:
    reached = len(ATT_FIRMS)
    cols = st.columns(6)
    cols[0].metric("Event spend", fk(K.cost_usd.sum()) if K.cost_usd.sum() < 1e6 else fm(K.cost_usd.sum()), help=f"{len(K)} event{'' if len(K) == 1 else 's'}, 2026")
    cols[1].metric("Firms reached", reached, help=f"of {len(FIRMS_IN)} covered firms" + (" in selected segments" if segment else ""))
    cols[2].metric("Associated opportunities", int(K.assoc_opps.sum()), help=f"of {len(FOPPS)} opened this year" + ("" if F.is_default_extra else " (filtered)"))
    cols[3].metric("Associated pipeline", fm(K.assoc_pipeline_usd.sum()))
    cols[4].metric("Associated commitments", fm(K.assoc_committed_usd.sum()), help="Face value of opportunities that reached Committed on or before 2026-09-23")
    cols[5].metric("Follow-up within 30 days", pct(K.firms_followup_30.sum() / K.firms_attended.sum() if K.firms_attended.sum() else None))

    d = kpi_all[(kpi_all.window_days == 90) & (~kpi_all.include_tentative)].set_index("event_id")
    t1 = fe[fe.is_confirmed & (fe.tier == "Tier 1")]
    st.info(
        f"""**What leadership should take away** · Baseline view: 90-day window, confirmed attendance, all events. This box does not change with the filters above; the cards and charts do.

1. **Most pipeline did not follow an event.** {int(d.assoc_opps.sum())} of {len(opps)} opportunities ({fm(d.assoc_pipeline_usd.sum())} of {fm(opps.amount_usd.sum())}) opened within 90 days of an attended event. The largest commitment ($650M) came from a firm that attended nothing.
2. **No evidence of incremental lift versus non-attendees.** The difference-in-differences in new-opportunity rate runs from {min(d.diff_in_diff_opp_rate.min(), d.diff_in_diff_clean.min())*100:+.0f} to {max(d.diff_in_diff_opp_rate.max(), d.diff_in_diff_clean.max())*100:+.0f} pts across events, and its sign flips depending on whether attendees are compared with firms not at that event (NY {d.loc['E001','diff_in_diff_opp_rate']*100:+.0f}, London {d.loc['E002','diff_in_diff_opp_rate']*100:+.0f}, Berlin {d.loc['E003','diff_in_diff_opp_rate']*100:+.0f}) or with the {int(d.clean_control_firms.iloc[0])} firms at no event ({d.loc['E001','diff_in_diff_clean']*100:+.0f}, {d.loc['E002','diff_in_diff_clean']*100:+.0f}, {d.loc['E003','diff_in_diff_clean']*100:+.0f}). None is statistically significant\\*.
3. **Follow-up is the controllable gap.** {d.firms_followup_30.sum() / d.firms_attended.sum():.0%} of attending firms met within 30 days; Tier 1 only {int(t1.followed_up_30.sum())} of {len(t1)}.
4. **London ($185K) was the cheapest way to reach firms:** {fk(d.loc['E002','cost_per_firm'])} per attending firm vs {fk(d.loc['E001','cost_per_firm'])} NY and {fk(d.loc['E003','cost_per_firm'])} Berlin, with a similar share of firms opening an opportunity ({d.loc['E002','firm_conversion_rate']:.0%} vs {d.loc['E001','firm_conversion_rate']:.0%} and {d.loc['E003','firm_conversion_rate']:.0%}). That low cost, not stronger conversion, drives its {fk(d.loc['E002','cost_per_assoc_opp'])} per associated opportunity, and it is one dinner.
5. **Berlin ($610K) needs a case before renewal:** meetings per attending firm fell {d.loc['E003','meetings_pre_60']/d.loc['E003','firms_attended']:.2f} → {d.loc['E003','meetings_post_60']/d.loc['E003','firms_attended']:.2f}, more than for firms not at the event ({d.loc['E003','non_attendee_meetings_pre_60']/d.loc['E003','non_attendee_firms']:.2f} → {d.loc['E003','non_attendee_meetings_post_60']/d.loc['E003','non_attendee_firms']:.2f}), though part of the "before" count is London follow-up. No commitments yet, and no opportunity in the data was created after {opps.created_date.max()}; recheck at 180 days."""
        .replace("$", "\\$")  # stop Streamlit markdown reading $...$ as LaTeX
    )
    footnote("* " + sig_note(d.reset_index(), "Default rule (90 days, confirmed)"))

with tab_s:

    rows = {
        "Date / type": pd.to_datetime(K.event_date).dt.strftime("%m-%d-%Y") + " · " + K.event_type,
        "Cost": K.cost_usd.map(fk),
        "Firms attended (Tier 1)": K.firms_attended.astype(str) + " (" + K.tier1_firms.astype(str) + ")",
        "Cost per firm": K.cost_per_firm.map(fk),
        "Follow-up within 30d": K.followup_rate_30.map(pct),
        "Median days to first follow-up": K.median_days_to_followup.map(lambda v: "-" if pd.isna(v) else f"{v:.0f}"),
        "Meetings 60d before → after": K.meetings_pre_60.astype(int).astype(str) + " → " + K.meetings_post_60.astype(int).astype(str),
        "Meetings per firm, before → after: attendees": [f"{a / n:.2f} → {b / n:.2f}" if n else "n/a" for a, b, n in zip(K.meetings_pre_60, K.meetings_post_60, K.firms_attended)],
        "Meetings per firm, before → after: firms not at event": [f"{a / n:.2f} → {b / n:.2f}" if n else "n/a" for a, b, n in zip(K.non_attendee_meetings_pre_60, K.non_attendee_meetings_post_60, K.non_attendee_firms)],
        "Associated opportunities": K.assoc_opps.astype(str),
        "Firms converting": K.firm_conversion_rate.map(pct),
        "Associated pipeline (of which declined)": K.assoc_pipeline_usd.map(fm) + " (" + K.assoc_declined_usd.map(fm) + ")",
        "Committed (face value)": K.assoc_committed_usd.map(fm) + " (" + K.assoc_committed_opps.astype(str) + ")",
        "Cost per associated opp": K.cost_per_assoc_opp.map(fk),
        "New-opp rate attendees before → after": K.attendee_prior_opp_rate.map(pct) + " → " + K.attendee_new_opp_rate.map(pct),
        "New-opp rate, firms not at event, before → after": K.non_attendee_prior_opp_rate.map(pct) + " → " + K.non_attendee_new_opp_rate.map(pct),
        "New-opp rate, firms at no event, before → after": K.clean_prior_opp_rate.map(pct) + " → " + K.clean_new_opp_rate.map(pct),
        "Diff-in-diff vs firms not at event*": [("n/a" if v is None or pd.isna(v) else f"{v * 100:+.0f} pts") + ("" if pd.isna(p) else f" (p {p:.2f})") for v, p in zip(K.diff_in_diff_opp_rate, K.p_value_did)],
        "Diff-in-diff vs firms at no event*": [("n/a" if v is None or pd.isna(v) else f"{v * 100:+.0f} pts") + ("" if pd.isna(p) else f" (p {p:.2f})") + f", n={int(c)}" for v, p, c in zip(K.diff_in_diff_clean, K.p_value_did_clean, K.clean_control_firms)],
        "Days since event (as-of)": K.days_since_event.astype(str),
    }
    score = pd.DataFrame({k: list(v) for k, v in rows.items()}, index=[f"{n} ({l})" for n, l in zip(K.event_name, K.location)]).T
    st.subheader("Event scorecard")
    score_tbl = score.rename_axis("Metric").reset_index()
    st.dataframe(score_tbl, width="stretch", hide_index=True, height=35 * (len(score_tbl) + 1) + 3,
                 column_config={"Metric": st.column_config.TextColumn("Metric", width="large", pinned=True)})
    footnote("* " + sig_note(K, f"Current settings ({describe(F)})"))

    a, b = st.columns(2)
    chart_head(a, "New opportunities and meetings by month, 2026",
               "Dashed lines mark events. Opportunity creation peaked in June and July for all firms. September is partial.")
    ym = monthly.month.str[:7]
    firm_set = set(FIRMS_IN.firm_id)
    mt = D["mart_meetings"]
    monthly = monthly.assign(new_opps=[int((FOPPS.created_date.dt.strftime("%Y-%m") == m).sum()) for m in ym],
                             meetings=[int((mt.firm_id.isin(firm_set) & (mt.meeting_date.str[:7] == m)).sum()) for m in ym])
    mlab = pd.to_datetime(monthly.month).dt.strftime("%b").tolist()
    if monthly.month.iloc[-1].startswith("2026-09"):
        mlab[-1] += "*"
    fig = go.Figure()
    # point labels: the higher series at each month is labelled above its dot, the lower one below
    op_hi = [o >= m for o, m in zip(monthly.new_opps, monthly.meetings)]
    fig.add_scatter(x=mlab, y=monthly.new_opps, name="New opportunities", mode="lines+markers+text", line=dict(color=BLUE, width=2.5, shape="spline"), marker=dict(size=8),
                    text=[str(v) for v in monthly.new_opps], textposition=["top center" if h else "bottom center" for h in op_hi], textfont=dict(size=11, color="#1b1f24"))
    fig.add_scatter(x=mlab, y=monthly.meetings, name="Meetings", mode="lines+markers+text", line=dict(color=ORANGE, width=2.5, shape="spline"), marker=dict(size=8),
                    text=[str(v) for v in monthly.meetings], textposition=["bottom center" if h else "top center" for h in op_hi], textfont=dict(size=11, color="#1b1f24"))
    n = 0
    for k, ev in enumerate(monthly.events_in_month):
        if isinstance(ev, str):
            fig.add_vline(x=k, line=dict(color="#8a949c", dash="dash", width=1))
            fig.add_annotation(x=k, y=1.0 + 0.08 * (n % 2), yref="paper", yanchor="bottom",
                               text=" / ".join(EV_SHORT[e] for e in ev.split(",")), showarrow=False, font=dict(size=11, color="#5b6570"))
            n += 1
        fig = line_layout(fig, top=60).update_layout(legend=dict(orientation="h", y=-0.18, x=0.5, xanchor="center"))
    fig.update_yaxes(visible=False, range=[-3, max(monthly.new_opps.max(), monthly.meetings.max()) * 1.25])
    a.plotly_chart(fig, width="stretch")
    chart_head(b, "Where 2026 pipeline came from", "Share of $ pipeline by source, under the current filters.")
    vals = [float(FOPPS.loc[FOPPS.bucket == o, "amount_usd"].sum()) for o in BUCKETS]
    b.plotly_chart(donut_fig([f"Opened within {window}d of an attended event", "Attendee firm, not in window (mostly opened before its first event)",
                              "Firm with no confirmed attendance" if NONE_LABEL == "No confirmed attendance" else NONE_LABEL],
                             vals, [BLUE, AQUA, NEUTRAL], fm(sum(vals)), "2026 pipeline", fm), width="stretch")

    a, b = st.columns(2)
    chart_head(a, "Cost per associated opportunity",
               "Event cost / opportunities created in window. Association, not attribution: a low figure means more opportunities followed the event per dollar, not that the event caused them. Label shows the share of attending firms that converted.")
    cmax = K.cost_per_assoc_opp.max() if K.cost_per_assoc_opp.notna().any() else 1
    fig = go.Figure(go.Bar(
        x=labels, y=K.cost_per_assoc_opp, marker_color=[EV_COLOR[e] for e in K.event_id], width=0.75,
        text=[("no opps" if pd.isna(c) else f"<b>{fk(c)}</b>") + f"<br>{pct(r)} converted" for c, r in zip(K.cost_per_assoc_opp, K.firm_conversion_rate)],
        **inside_labels(K.cost_per_assoc_opp, cmax, min_share=0.3), cliponaxis=False))
    fig.update_layout(height=340, margin=dict(l=10, r=10, t=30, b=10), plot_bgcolor="rgba(0,0,0,0)",
                      font=dict(family="Inter, system-ui, sans-serif", color="#3b4450"),
                      yaxis=dict(range=[0, cmax * 1.15], visible=False))
    fig.update_layout(uniformtext_minsize=10, uniformtext_mode="show")
    a.plotly_chart(fig, width="stretch")
    chart_head(b, "Associated pipeline and commitments",
               "Percentage on Committed bars is commitment conversion: committed $ / associated pipeline $.")
    conv = (K.assoc_committed_usd / K.assoc_pipeline_usd.where(K.assoc_pipeline_usd > 0)).fillna(0)
    pmax = max(K.assoc_pipeline_usd.max() / 1e6, 1)
    fig = bar_fig(labels, [("Associated pipeline", K.assoc_pipeline_usd / 1e6, BLUE), ("Committed", K.assoc_committed_usd / 1e6, AQUA)], height=340)
    fig.data[0].update(text=[f"<b>{fm(v)}</b>" for v in K.assoc_pipeline_usd], cliponaxis=False,
                       **inside_labels(K.assoc_pipeline_usd / 1e6, pmax, min_share=0.12))
    fig.data[1].update(text=[f"<b>{fm(v) if v else '$0M'}</b><br>{c:.0%}" for v, c in zip(K.assoc_committed_usd, conv)],
                       hovertemplate="%{x}<br>Committed: $%{y:.0f}M<extra></extra>", cliponaxis=False,
                       **inside_labels(K.assoc_committed_usd / 1e6, pmax, min_share=0.2))
    fig.update_yaxes(range=[0, pmax * 1.12], visible=False)
    fig.update_layout(uniformtext_minsize=10, uniformtext_mode="show", legend=dict(orientation="h", y=-0.12, x=0.5, xanchor="center"), bargap=0.25, bargroupgap=0.05)
    b.plotly_chart(fig, width="stretch")
    a, b = st.columns(2)
    chart_head(a, "New-opportunity rate before vs after the event")
    lift = [K.attendee_prior_opp_rate, K.attendee_new_opp_rate, K.non_attendee_prior_opp_rate, K.non_attendee_new_opp_rate]
    fig = bar_fig(labels, [("Attendees, before", lift[0], NEUTRAL), ("Attendees, after", lift[1], BLUE),
                           ("Non-attendees, before", lift[2], "#dcdad4"), ("Non-attendees, after", lift[3], ORANGE)])
    a.plotly_chart(label_bars(fig, [[pct(v) for v in s] for s in lift], light=(0, 2), min_share=0.15).update_layout(legend=dict(orientation="h", y=-0.12, x=0.5, xanchor="center")), width="stretch")
    chart_head(b, "Meetings with attending firms, 60 days before vs after")
    fig = bar_fig(labels, [("Before", K.meetings_pre_60, NEUTRAL), ("After", K.meetings_post_60, BLUE)])
    b.plotly_chart(label_bars(fig, [[str(int(v)) for v in K.meetings_pre_60], [str(int(v)) for v in K.meetings_post_60]], light=(0,)).update_layout(legend=dict(orientation="h", y=-0.12, x=0.5, xanchor="center")), width="stretch")

with tab_f:
    conf = ATT.copy()
    conf["followed_up_30"] = conf.meetings_post_30 > 0
    conv_keys = set(zip(FOPPS.firm_id, FOPPS.assoc_event_id))
    conf["converted"] = [(fid, e) in conv_keys for fid, e in zip(conf.firm_id, conf.event_id)]
    a, b = st.columns(2)
    chart_head(a, "Follow-up within 30 days, by tier and event")
    g = conf.groupby(["tier", "event_id"]).followed_up_30.mean().unstack()
    fig = bar_fig(list(g.index), [(EV_SHORT[e], g[e], EV_COLOR[e]) for e in g.columns])
    a.plotly_chart(label_bars(fig, [[pct(v) for v in g[e]] for e in g.columns], light=tuple(i for i, e in enumerate(g.columns) if e == "E002"),
                              min_share=0.12, headroom=1.1), width="stretch")
    senior = conf.senior_contacts.gt(0) if tent else conf.has_confirmed_senior
    cuts = {"Tier": conf.tier, "Segment": conf.segment, "Relationship": conf.relationship_band,
            "Senior attendee": senior.map({True: "CIO/MD registered", False: "No CIO/MD"}),
            "Follow-up in 30d": conf.followed_up_30.map({True: "Yes", False: "No"})}
    dim = b.selectbox("Cut conversion by", list(cuts), index=0)
    s = (conf.assign(v=cuts[dim]).groupby("v")
         .agg(firm_events=("firm_id", "size"), conversion_rate=("converted", "mean"), followup_rate_30=("followed_up_30", "mean")).reset_index())
    fig = bar_fig(list(s.v + " (n=" + s.firm_events.astype(str) + ")"),
                  [(f"Converted to opp ({window}d)", s.conversion_rate, BLUE), ("Followed up in 30d", s.followup_rate_30, NEUTRAL)], horizontal=True)
    b.plotly_chart(label_bars(fig, [[pct(v) for v in s.conversion_rate], [pct(v) for v in s.followup_rate_30]], light=(1,),
                              min_share=0.08, horizontal=True, headroom=1.05), width="stretch")
    # donut on its own row, centered on the page
    d = conf.days_to_first_followup
    fu_vals = [int((d <= 30).sum()), int(((d > 30) & (d <= 60)).sum()), int((d > 60).sum()), int(d.isna().sum())]
    _, mid, _ = st.columns([1, 2, 1])
    mid.markdown('<div class="chart-title" style="text-align:center">Follow-up status of attending firms</div>'
                 '<div class="chart-sub" style="text-align:center">Attending firm-event pairs under the current filters: time from event to first meeting.</div>',
                 unsafe_allow_html=True)
    mid.plotly_chart(donut_fig(["Met within 30 days", "Met in 31-60 days", "Met after 60 days", "No meeting since event"], fu_vals,
                               [BLUE, AQUA, ORANGE, NEUTRAL], pct(fu_vals[0] / len(conf) if len(conf) else None), "met within 30 days",
                               lambda v: f"{v} firm-events"), width="stretch")
    st.subheader("Follow-up gaps: firm-events with no meeting within 60 days")
    leak = conf[conf.meetings_post_60.fillna(0) == 0].merge(firms[["firm_id", "pipeline_usd"]], on="firm_id")
    leak = leak.sort_values(["tier", "pipeline_usd"], ascending=[True, False])
    st.dataframe(leak.assign(event=leak.event_id.map(EV_SHORT), pipeline=leak.pipeline_usd.map(fm))[
        ["firm_name", "tier", "segment", "event", "senior_contacts", "days_to_first_followup", "pipeline"]],
        width="stretch", hide_index=True)

with tab_x:
    c = st.columns(5)
    ev = c[0].multiselect("Event", list(EV_SHORT), format_func=EV_SHORT.get, placeholder="All", key="fx_event")
    tier = c[1].multiselect("Tier", sorted(firms.tier.unique()), placeholder="All", key="fx_tier")
    sg = c[2].multiselect("Investor segment", sorted(firms.segment.unique()), placeholder="All", key="fx_segment")
    rg = c[3].multiselect("Region", sorted(firms.region.unique()), placeholder="All", key="fx_region")
    q = c[4].text_input("Search firm", placeholder="Name or ID")
    f = firms.copy()
    if ev:
        has = lambda col: f[col].fillna("").str.split(", ").apply(lambda xs: any(e in xs for e in ev))
        f = f[has("events_confirmed") | has("events_tentative_only")]
    for col, val in [("tier", tier), ("segment", sg), ("region", rg)]:
        if val:
            f = f[f[col].isin(val)]
    if q:
        f = f[f.firm_name.str.contains(q, case=False) | f.firm_id.str.contains(q, case=False)]
    st.caption(f"{len(f)} firms. Click a row to show that firm's timeline and pipeline chart below (the first firm is shown until you pick one).")
    table = (f[["firm_id", "firm_name", "tier", "segment", "region", "events_confirmed", "events_tentative_only", "meetings", "opps",
                "pipeline_usd", "assoc_pipeline_90_usd", "committed_usd", "has_unfollowed_event"]]
             .sort_values("pipeline_usd", ascending=False).reset_index(drop=True))
    sel = st.dataframe(table, width="stretch", hide_index=True, on_select="rerun", selection_mode="single-row", key="fx_table",
                       column_config={"firm_id": st.column_config.TextColumn("Firm ID", pinned=True), "firm_name": "Firm",
                                      "pipeline_usd": st.column_config.NumberColumn("Pipeline", format="dollar"),
                                      "assoc_pipeline_90_usd": st.column_config.NumberColumn("Event-assoc. pipeline", format="dollar"),
                                      "committed_usd": st.column_config.NumberColumn("Committed", format="dollar"),
                                      "has_unfollowed_event": st.column_config.CheckboxColumn("Follow-up gap")})
    if len(table):
        rows = [r for r in sel.selection.rows if r < len(table)]
        pick = table.firm_id[rows[0]] if rows else table.firm_id[0]
        info = firms.set_index("firm_id").loc[pick]
        st.markdown(f"<div class='chart-title' style='margin-top:10px'>Selected firm: {info.firm_name} ({pick})</div>", unsafe_allow_html=True)
        st.markdown(f"**{info.firm_name}** · {info.tier} · {info.segment} · {info.region} · historical commitments {fm(info.historical_commitments_usd)}")
        t = tl[tl.firm_id == pick].copy()
        t["detail"] = t.detail + t.is_projected.map({True: " (projected, after as-of date)", False: ""})
        st.dataframe(t[["dt", "kind", "detail"]], width="stretch", hide_index=True)
        hc = st.columns([3, 1])
        chart_head(hc[0], f"Pipeline dollars by stage, by month: {info.firm_name}", "Month-end snapshot of the selected firm's pipeline dollars, stacked by the stage each opportunity was in. September is as of 09-23; later months (marked *) use projected stages. Event months are marked above the bars.")
        stage_names = {1: "Initial Conversation", 2: "Follow-up / VDR", 3: "Due Diligence", 4: "IC / Documentation", 5: "Committed", 0: "Declined"}
        pick_st = hc[1].multiselect("Stage", list(stage_names), format_func=stage_names.get, placeholder="All", key="fx_stage")
        fo = opps[opps.firm_id == pick]
        if fo.empty:
            st.caption("This firm has no opportunities.")
        else:
            sh = D["mart_stage_history"]
            sh = sh[sh.opportunity_id.isin(fo.opportunity_id)].sort_values("stage_date")
            as_of = "2026-09-23"
            first, last = sh.stage_date.min()[:7], max(sh.stage_date.max(), as_of)[:7]
            months = pd.period_range(first, last, freq="M")
            amt = fo.set_index("opportunity_id").amount_usd
            rows = []
            for m in months:
                snap = as_of if str(m) == as_of[:7] else m.end_time.strftime("%Y-%m-%d")
                cur = sh[sh.stage_date <= snap].groupby("opportunity_id").tail(1)
                label = m.strftime("%b") + ("*" if snap >= as_of else "")
                for r in cur.itertuples():
                    rows.append((label, snap, int(r.stage_rank), r.opportunity_id, float(amt[r.opportunity_id]), snap > as_of))
            mdf = pd.DataFrame(rows, columns=["month", "snap", "rank", "opp", "usd", "projected"])
            labels_m = [m.strftime("%b") + ("*" if (as_of if str(m) == as_of[:7] else m.end_time.strftime("%Y-%m-%d")) >= as_of else "") for m in months]
            colors = {1: "#9fb3c2", 2: "#6f8ea6", 3: "#3f6784", 4: "#1f3f5a", 5: "#008300", 0: "#c23b3a"}
            fig = go.Figure()
            for r in [5, 4, 3, 2, 1, 0]:  # bottom to top: Committed at the base, Declined on top
                if pick_st and r not in pick_st:
                    continue
                g = mdf[mdf["rank"] == r].groupby("month").agg(usd=("usd", "sum"), ids=("opp", ", ".join)).reindex(labels_m)
                if g.usd.fillna(0).sum() == 0:
                    continue
                fig.add_bar(x=labels_m, y=g.usd.fillna(0), name=stage_names[r], marker=dict(color=colors[r]),
                            customdata=g.ids.fillna(""), hovertemplate=stage_names[r] + ": %{y:$,.0f}<br>%{customdata}<extra>%{x}</extra>")
            for k, r in enumerate(fe[fe.firm_id == pick].itertuples()):
                lbl = next((l for l, m in zip(labels_m, months) if str(m) == r.event_date[:7]), None)
                if lbl:
                    fig.add_annotation(x=lbl, y=1.02 + 0.07 * (k % 2), yref="paper", yanchor="bottom", showarrow=False,
                                       text="▼ " + EV_SHORT[r.event_id] + ("" if r.is_confirmed else " (tent.)"), font=dict(size=11, color="#5b6570"))
            fig.update_yaxes(tickprefix="$", gridcolor="#e6eaed", zeroline=False, rangemode="tozero")
            fig.update_layout(barmode="stack", height=380, margin=dict(l=10, r=10, t=50, b=10), plot_bgcolor="rgba(0,0,0,0)", hovermode="x unified",
                              legend=dict(orientation="h", y=-0.15, x=0.5, xanchor="center", traceorder="reversed"), font=dict(family="Inter, system-ui, sans-serif", color="#3b4450"))
            st.plotly_chart(fig, width="stretch")

with tab_p:
    a, b = st.columns(2)
    src = FOPPS.groupby("bucket").agg(pipeline=("amount_usd", "sum"), n=("opportunity_id", "count")).reindex(BUCKETS).fillna(0)
    src["committed"] = FOPPS[FOPPS.outcome == "Committed"].groupby("bucket").amount_usd.sum()
    chart_head(a, "Where pipeline came from ($M)")
    ncom = FOPPS[FOPPS.outcome == "Committed"].groupby("bucket").size().reindex(src.index).fillna(0).astype(int)
    fig = bar_fig(list(src.index), [("Pipeline", src.pipeline / 1e6, BLUE), ("Committed", src.committed.fillna(0) / 1e6, AQUA)])
    a.plotly_chart(label_bars(fig, [[f"{fm(v)}<br>{int(n)} opps" for v, n in zip(src.pipeline, src.n)],
                                    [f"{fm(v)}<br>{int(n)} opps" for v, n in zip(src.committed.fillna(0), ncom)]], min_share=0.18), width="stretch")
    stages = ["Initial Conversation", "Follow-up / VDR", "Due Diligence", "IC / Documentation", "Committed"]
    ea, other = FOPPS[FOPPS.assoc_event_id.notna()], FOPPS[FOPPS.assoc_event_id.isna()]
    chart_head(b, "Funnel: count reaching each stage")
    fun = [[int((ea.max_stage_rank >= i + 1).sum()) for i in range(5)], [int((other.max_stage_rank >= i + 1).sum()) for i in range(5)]]
    fig = bar_fig(stages, [("Event-associated", fun[0], BLUE), ("All other", fun[1], NEUTRAL)], horizontal=True)
    b.plotly_chart(label_bars(fig, [[str(v) for v in f] for f in fun], light=(1,), min_share=0.08, horizontal=True), width="stretch")
    chart_head(st, "Opportunity flow: source → furthest stage → status",
               "Opportunities under the current filters. Band width is the number of opportunities; "
               "hover for $ pipeline. Committed opportunities flow straight to Committed.")
    outside = f"Attendee, not in {window}d window"

    def src_name(r):
        if isinstance(r.assoc_event_id, str):
            return EV_SHORT[r.assoc_event_id]
        return outside if r.bucket == "Attendee, not in window" else NONE_LABEL
    stg_name = lambda k: "Intro / VDR" if k <= 2 else "Due diligence" if k == 3 else "IC / documentation"
    node_color = {"NY Summit": EV_COLOR["E001"], "London Dinner": EV_COLOR["E002"], "Berlin Forum": EV_COLOR["E003"],
                  outside: "#8a98a3", NONE_LABEL: NEUTRAL,
                  "Intro / VDR": "#9fb3c2", "Due diligence": "#6f8ea6", "IC / documentation": "#3f6784",
                  "Committed": "#008300", "Open": "#b8c3cb", "Declined": "#c23b3a"}
    names = list(node_color)
    flows = {}
    for r in FOPPS.itertuples():
        src = src_name(r)
        hops = [(src, "Committed")] if r.outcome == "Committed" else [(src, stg_name(r.max_stage_rank)), (stg_name(r.max_stage_rank), r.outcome)]
        for h in hops:
            f = flows.setdefault(h, [0, 0.0]); f[0] += 1; f[1] += r.amount_usd
    def rgba(hex_, a=0.45):
        h = hex_.lstrip("#"); return f"rgba({int(h[0:2], 16)},{int(h[2:4], 16)},{int(h[4:6], 16)},{a})"
    names = [n for n in names if any(n in k for k in flows)]
    totals = {n: sum(v[0] for (x, y), v in flows.items() if y == n) or sum(v[0] for (x, y), v in flows.items() if x == n) for n in names}
    usd = {n: sum(v[1] for (x, y), v in flows.items() if y == n) or sum(v[1] for (x, y), v in flows.items() if x == n) for n in names}
    order0 = ["NY Summit", "London Dinner", "Berlin Forum", outside, NONE_LABEL]
    order1, order2 = ["Intro / VDR", "Due diligence", "IC / documentation"], ["Committed", "Open", "Declined"]
    def spread(group):
        present = [n for n in group if n in names]
        return {n: (i + 0.5) / len(present) for i, n in enumerate(present)}
    col = {n: 0.001 for n in order0} | {n: 0.5 for n in order1} | {n: 0.999 for n in order2}
    ypos = spread(order0) | spread(order1) | spread(order2)
    fig = go.Figure(go.Sankey(
        arrangement="fixed",
        node=dict(label=[f"{n} ({totals[n]} · {fm(usd[n])})" for n in names], color=[node_color[n] for n in names], pad=18, thickness=14, line=dict(width=0),
                  x=[col[n] for n in names], y=[ypos[n] for n in names],
                  hovertemplate="%{label}: %{value} opportunities<extra></extra>"),
        link=dict(source=[names.index(a) for a, b in flows], target=[names.index(b) for a, b in flows],
                  value=[v[0] for v in flows.values()], color=[rgba(node_color[a]) for a, b in flows],
                  customdata=[fm(v[1]) for v in flows.values()],
                  hovertemplate="%{source.label} → %{target.label}: %{value} opps, %{customdata}<extra></extra>")))
    fig.update_layout(height=460, margin=dict(l=10, r=10, t=10, b=10), font=dict(family="Inter, system-ui, sans-serif", size=12, color="#1b1f24"))
    st.plotly_chart(fig, width="stretch")
    chart_head(st, "How fast opportunities followed each event",
               "Cumulative associated opportunities by days after the event (180-day window, current attendance and opportunity filters, most recent event gets credit). "
               "Lines stop at each event's age on the as-of date; no opportunities were created after 2026-08-12, so lines flatten after that.")
    fig = go.Figure()
    curve180 = associate(filtered_opps(P, F), ATT_ALL, 180)
    for e, name in ((e, EV_SHORT[e]) for e in SEL_EVENTS):
        age = int(kpi_all.loc[kpi_all.event_id == e, "days_since_event"].iloc[0])
        days = list(range(0, min(180, age) + 1, 5))
        pts = curve180[curve180.assoc_event_id == e]
        fig.add_scatter(x=days, y=[int((pts.days_after_event <= x).sum()) for x in days], name=name, mode="lines",
                        line=dict(color=EV_COLOR[e], width=2.5, shape="hv"))
    fig.update_xaxes(title="Days after event", gridcolor="#f0f2f4")
    fig.update_yaxes(title="Cumulative opportunities")
    st.plotly_chart(line_layout(fig, height=340).update_layout(legend=dict(orientation="h", y=1.12, x=0.5, xanchor="center")), width="stretch")
    c = st.columns(5)
    s1 = c[0].multiselect("Source", BUCKETS, placeholder="All", key="ot_source")
    s2 = c[1].multiselect("Outcome", ["Open", "Committed", "Declined"], placeholder="All", key="ot_outcome")
    s3 = c[2].multiselect("Opportunity", sorted(FOPPS.opportunity_id), placeholder="All (type to search)", key="ot_opp")
    o = FOPPS
    for col_, val in [("bucket", s1), ("outcome", s2), ("opportunity_id", s3)]:
        if val:
            o = o[o[col_].isin(val)]
    st.dataframe(o.assign(created_date=o.created_date.dt.strftime("%Y-%m-%d"))[
                 ["opportunity_id", "firm_name", "tier", "fund_name", "created_date", "amount_usd", "current_stage", "outcome",
                  "assoc_event_id", "days_after_event", "is_amount_outlier", "projected_stage_rows"]],
                 width="stretch", hide_index=True)


# ---------------------------------------------------------------------------
# Next event planner: 2026 benchmarks applied to a planned event.
# Estimates resample 2026 firm-level outcomes (bootstrap), so they carry the
# spread of what actually happened; they are planning ranges, not forecasts.
# ---------------------------------------------------------------------------
@st.cache_data
def planner_pool(version: str = "") -> pd.DataFrame:
    fe_ = D["mart_firm_event"].query("is_confirmed")
    k_ = D["mart_event_kpis"].query("window_days == 90 and not include_tentative")[["event_id", "event_type"]]
    return fe_.merge(k_, on="event_id")[["event_id", "event_type", "tier", "assoc_opps_90", "assoc_pipeline_90_usd", "meetings_post_30"]]


def plan_estimate(tier_counts: dict, fmt: str | None, n_boot: int = 4000, seed: int = 7):
    """Bootstrap total associated opportunities and pipeline for a planned attendee mix.
    fmt=None pools all three 2026 events (more stable); otherwise uses that format's events only."""
    import numpy as np
    pool = planner_pool(DATA_VERSION)
    if fmt:
        pool = pool[pool.event_type == fmt]
    rng = np.random.default_rng(seed)
    opps = np.zeros(n_boot)
    pipe = np.zeros(n_boot)
    for tier, n in tier_counts.items():
        g = pool[pool.tier == tier]
        if n <= 0 or g.empty:
            continue
        idx = rng.integers(0, len(g), size=(n_boot, n))
        opps += g.assoc_opps_90.to_numpy()[idx].sum(axis=1)
        pipe += g.assoc_pipeline_90_usd.to_numpy()[idx].sum(axis=1)
    return opps, pipe


with tab_n:
    st.markdown(
        '<div class="chart-sub" style="font-size:14px;margin-bottom:6px"><b>A historical analog, not a forecast.</b> Describe a planned event and see what '
        '<i>followed</i> the most similar 2026 attendances: the tool resamples the 2026 outcomes of firms in each tier (90-day window, confirmed attendance) '
        'and reports the range they span. The three 2026 events differ in format, timing and audience, and none showed evidence of incremental lift, so '
        'these are ranges of what has happened after comparable events, not what a new event will produce. Fixed 2026 benchmarks; the page filters are not shown here.</div>',
        unsafe_allow_html=True)
    fmt_defaults = {"Hospitality (dinner)": ("Hospitality", 185, 6, 12, 7), "Conference": ("Conference", 515, 8, 10, 6)}
    c = st.columns(5)
    fmt_label = c[0].selectbox("Event format", list(fmt_defaults), key="pl_fmt",
                               help="Defaults are 2026 averages: the London dinner, or the mean of the NY and Berlin conferences.")
    fmt, d_cost, d1, d2, d3 = fmt_defaults[fmt_label]
    budget = c[1].number_input("Budget ($K)", min_value=10, max_value=5000, value=d_cost, step=5, key=f"pl_budget_{fmt}")
    t1 = c[2].number_input("Tier 1 firms", min_value=0, max_value=60, value=d1, key=f"pl_t1_{fmt}")
    t2 = c[3].number_input("Tier 2 firms", min_value=0, max_value=60, value=d2, key=f"pl_t2_{fmt}")
    t3 = c[4].number_input("Tier 3 firms", min_value=0, max_value=60, value=d3, key=f"pl_t3_{fmt}")
    c = st.columns([2, 2, 3])
    fu_target = c[0].slider("Target: firms met within 30 days", 0, 100, 80, step=5, format="%d%%", key="pl_fu",
                            help="2026 actual: 39% of attending firms (Tier 1: 29%).")
    basis = c[1].radio("Benchmark basis", ["All 2026 events", "Same format only"], key="pl_basis", horizontal=False,
                       help="All events pools 70 firm-attendances and is more stable. Same format uses only NY and Berlin (conference) or only London (dinner), so ranges are wider and rest on fewer firms.")
    firms_n = int(t1 + t2 + t3)
    if firms_n == 0:
        st.warning("Add at least one attending firm.")
    else:
        opps_b, pipe_b = plan_estimate({"Tier 1": int(t1), "Tier 2": int(t2), "Tier 3": int(t3)}, fmt if basis == "Same format only" else None)
        import numpy as np
        lo, mid, hi_ = (np.percentile(opps_b, q) for q in (10, 50, 90))
        plo, pmid, phi = (np.percentile(pipe_b, q) for q in (10, 50, 90))
        cost = budget * 1e3
        cpo = lambda x: cost / x if x > 0 else float("nan")
        m = st.columns(3) + st.columns(3)
        m[0].metric("Firms reached", firms_n, help=f"Tier 1 {int(t1)} · Tier 2 {int(t2)} · Tier 3 {int(t3)}")
        m[1].metric("Spend per firm", fk(cost / firms_n))
        m[2].metric("Opportunities that followed similar events", f"{lo:.0f}–{hi_:.0f}", help=f"10th to 90th percentile of the resampled 2026 outcomes; middle value {mid:.0f}")
        # a value like "$299M to $839M" would be read as LaTeX ($...$) by the metric widget; use an en dash and one dollar sign
        m[3].metric("Pipeline that followed (face value)", f"{fm(plo)}–{fm(phi)[1:]}", help=f"Range of resampled 2026 outcomes; middle value {fm(pmid)}. Historical analog, not a forecast.")
        m[4].metric("Spend per associated opp", f"{fk(cpo(hi_))}–{fk(cpo(lo))[1:]}", help=f"Budget / opportunities across the range; middle value {fk(cpo(mid))}")
        m[5].metric("Firms met within 30 days", f"{round(firms_n * fu_target / 100)} of {firms_n}",
                    help=f"At the 2026 rate (39%) it would be about {round(firms_n * 0.39)}.")
        footnote(f"Ranges are the 10th to 90th percentile of 4,000 resamples of 2026 firm-level outcomes (basis: {basis.lower()}). "
                 f"Middle values: {mid:.0f} opportunities, {fm(pmid)} pipeline, {fk(cpo(mid))} per opportunity.")

        a, b = st.columns(2)
        chart_head(a, "Spend per associated opportunity: analog vs 2026",
                   "The analog bar shows the middle value with its 10th to 90th percentile range.")
        k90 = kpi_all.query("window_days == 90 and not include_tentative").sort_values("event_id")
        names = ["Analog"] + [EV_SHORT[e] for e in k90.event_id]
        vals = [cpo(mid)] + list(k90.cost_per_assoc_opp)
        fig = go.Figure(go.Bar(x=names, y=vals, marker_color=[NAVY] + [EV_COLOR[e] for e in k90.event_id], width=0.6,
                               error_y=dict(type="data", symmetric=False, array=[cpo(lo) - cpo(mid)] + [0] * 3,
                                            arrayminus=[cpo(mid) - cpo(hi_)] + [0] * 3, color="#1b1f24", thickness=1.5, width=8),
                               text=[f"<b>{fk(v)}</b>" for v in vals], textposition="inside", insidetextanchor="middle", textfont=dict(color="#ffffff", size=11)))
        fig.update_layout(height=320, margin=dict(l=10, r=10, t=20, b=10), plot_bgcolor="rgba(0,0,0,0)",
                          font=dict(family="Inter, system-ui, sans-serif", color="#3b4450"), uniformtext_minsize=10, uniformtext_mode="show")
        fig.update_yaxes(visible=False, range=[0, max(v for v in vals + [cpo(lo)] if v == v) * 1.12])
        a.plotly_chart(fig, width="stretch")

        chart_head(b, "Opportunities that followed, by tier",
                   "Middle estimate per tier from the same resampling. 2026 opportunities per attending firm: Tier 1 0.33, Tier 2 0.48, Tier 3 0.83.")
        per_tier = []
        for tier, n in [("Tier 1", t1), ("Tier 2", t2), ("Tier 3", t3)]:
            o_t, _ = plan_estimate({tier: int(n)}, fmt if basis == "Same format only" else None)
            per_tier.append(float(np.percentile(o_t, 50)) if n else 0.0)
        fig = bar_fig(["Tier 1", "Tier 2", "Tier 3"], [("Middle estimate", per_tier, BLUE)])
        b.plotly_chart(label_bars(fig, [[f"{v:.0f}" for v in per_tier]], min_share=0.1), width="stretch")

        st.subheader("2026 benchmarks")
        bench = k90.assign(event=k90.event_id.map(EV_SHORT))[
            ["event", "event_type", "cost_usd", "firms_attended", "tier1_firms", "cost_per_firm", "assoc_opps", "cost_per_assoc_opp", "followup_rate_30"]]
        bench = bench.assign(opps_per_firm=bench.assoc_opps / bench.firms_attended)
        st.dataframe(bench.assign(cost_usd=bench.cost_usd.map(fk), cost_per_firm=bench.cost_per_firm.map(fk), cost_per_assoc_opp=bench.cost_per_assoc_opp.map(fk),
                                  followup_rate_30=bench.followup_rate_30.map(pct), opps_per_firm=bench.opps_per_firm.map("{:.2f}".format))
                     .rename(columns={"event": "Event", "event_type": "Format", "cost_usd": "Cost", "firms_attended": "Firms", "tier1_firms": "Tier 1 firms",
                                      "cost_per_firm": "Cost per firm", "assoc_opps": "Associated opps (90d)", "cost_per_assoc_opp": "Cost per opp",
                                      "followup_rate_30": "Met within 30d", "opps_per_firm": "Opps per firm"}),
                     width="stretch", hide_index=True)
        st.info("**How to use this.** Compare formats at the same budget, or see how many more Tier 3 firms it takes to match a Tier 1-heavy list. Read every figure as a range of what followed comparable 2026 attendances. "
                "The follow-up target is shown as a count only: in 2026, firms met within 30 days converted at 37% vs 40% for those not met, "
                "on groups too small to tell whether follow-up speed matters, so the planner adds no pipeline for it. Treat that as something to test.")


def md_doc(name: str) -> str:
    """Read a docs/ markdown file, demote headings under the tab's subheader, escape $ (Streamlit treats $..$ as LaTeX)."""
    import re

    text = (ROOT / "docs" / name).read_text().replace("$", "\\$")
    text = re.sub(r"\]\((?!https?://)([A-Za-z_]+\.md)\)", r"](https://github.com/colinbayer77/carlyle-ir-event-analytics/blob/main/docs/\1)", text)
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
    st.divider()
    st.subheader("Data dictionary")
    st.caption("Every metric on the dashboard: definition, source column, and how the page filters affect it. Also in the repo as [docs/DATA_DICTIONARY.md](https://github.com/colinbayer77/carlyle-ir-event-analytics/blob/main/docs/DATA_DICTIONARY.md).")
    st.markdown(md_doc("DATA_DICTIONARY.md"))
    st.subheader("Data-quality log")
    st.dataframe(dq, width="stretch", hide_index=True)

st.markdown('<div class="foot">Candidate take-home submission, not an official Carlyle publication. Synthetic assessment data, as of 2026-09-23. Built by Colin Bayer for the Carlyle BI &amp; Analytics Lead take-home.</div>', unsafe_allow_html=True)


for _ph in _hidden:
    _ph.empty()
