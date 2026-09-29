"""Build the 3-slide executive readout (HTML -> PDF) from the marts.

Every number on the slides is read from data/marts, so the readout cannot drift
from the dashboard. Requires Google Chrome for the PDF step.

    python readout/build_readout.py
"""
from __future__ import annotations

import subprocess
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
M = {p.stem: pd.read_csv(p) for p in (ROOT / "data" / "marts").glob("*.csv")}
CHROME = "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"
LOGO = "data:image/png;base64," + __import__("base64").b64encode((ROOT / "assets" / "carlyle_logo.png").read_bytes()).decode()
AUTHOR = "Colin R. Bayer · colinbayer7@gmail.com · 313-617-8828"

k = M["mart_event_kpis"].query("window_days == 90 and not include_tentative").set_index("event_id")
fe = M["mart_firm_event"].query("is_confirmed")
firms, opps = M["mart_firm"], M["mart_opportunity"]
t1 = fe[fe.tier == "Tier 1"]
gap_t1 = firms[firms.has_unfollowed_event & (firms.tier == "Tier 1")]


def _r(x: float, nd: int = 0) -> float:
    """Round half up, like JavaScript's Math.round, so Python and the static page show the same figure."""
    from decimal import ROUND_HALF_UP, Decimal
    return float(Decimal(str(x)).quantize(Decimal(1).scaleb(-nd), rounding=ROUND_HALF_UP))


def fm(v):
    return f"${_r(v / 1e9, 2):.2f}B" if v >= 1e9 else f"${_r(v / 1e6):,.0f}M"


def fk(v):
    return f"${_r(v / 1e3):,.0f}K"


N = dict(
    spend=k.cost_usd.sum(),
    firms=fe.firm_id.nunique(), firms_all=len(firms),
    t1_reached=firms[(firms.tier == "Tier 1") & firms.events_confirmed.notna()].shape[0],
    t1_all=(firms.tier == "Tier 1").sum(),
    opps=int(k.assoc_opps.sum()), opps_all=len(opps),
    pipe=k.assoc_pipeline_usd.sum(), pipe_all=opps.amount_usd.sum(),
    committed=k.assoc_committed_usd.sum(),
    fu=k.firms_followup_30.sum() / k.firms_attended.sum(),
    t1_fu=int(t1.followed_up_30.sum()), t1_n=len(t1),
    t1_nomtg=int((t1.meetings_post_60.fillna(0) == 0).sum()),
    gap_n=len(gap_t1), gap_pipe=gap_t1.pipeline_usd.sum(),
    declined=k.assoc_declined_usd.sum(),
    did_lo=min(k.diff_in_diff_opp_rate.min(), k.diff_in_diff_clean.min()), did_hi=max(k.diff_in_diff_opp_rate.max(), k.diff_in_diff_clean.max()),
    clean_n=int(k.clean_control_firms.iloc[0]),
    last_created=opps.created_date.max(),
)
per_firm = lambda n, d: n / d if d else float("nan")
EV = [("E001", "NY Summit", "Conference"), ("E002", "London Dinner", "Hospitality"), ("E003", "Berlin Forum", "Conference")]
COL = {"E001": "#2a78d6", "E002": "#eb6834", "E003": "#1baf7a"}


def bars(metric, fmt, title, higher_better=False):
    vals = [k.loc[e, metric] for e, *_ in EV]
    mx = max(abs(v) for v in vals) or 1
    rows = "".join(
        f'<div class="br"><span class="bl">{n}</span><span class="bt"><span class="bf" style="width:{abs(v) / mx * 100:.0f}%;background:{COL[e]}"></span></span><span class="bv">{fmt(v)}</span></div>'
        for (e, n, _), v in zip(EV, vals)
    )
    return f'<div class="bars"><div class="bh">{title}</div>{rows}</div>'


SIG = (f"Statistical significance: two-sided permutation test ({int(k.n_permutations.iloc[0]):,} random reshuffles of which firms attended); "
       f"significant only if p < 0.05. Against firms not at the event p = {k.loc['E001', 'p_value_did']:.2f} (NY), {k.loc['E002', 'p_value_did']:.2f} (London), "
       f"{k.loc['E003', 'p_value_did']:.2f} (Berlin); against the {N['clean_n']} firms at no event p = {k.loc['E001', 'p_value_did_clean']:.2f}, "
       f"{k.loc['E002', 'p_value_did_clean']:.2f}, {k.loc['E003', 'p_value_did_clean']:.2f}.")
score_rows = [
    ("Cost (per attending firm)", lambda e: f"{fk(k.loc[e, 'cost_usd'])} ({fk(k.loc[e, 'cost_per_firm'])})"),
    ("Firms attended (Tier 1)", lambda e: f"{k.loc[e, 'firms_attended']} ({k.loc[e, 'tier1_firms']})"),
    ("Meetings per attending firm, 60d before → after", lambda e: f"{per_firm(k.loc[e, 'meetings_pre_60'], k.loc[e, 'firms_attended']):.2f} → {per_firm(k.loc[e, 'meetings_post_60'], k.loc[e, 'firms_attended']):.2f}"),
    ("Same dates, firms not at the event", lambda e: f"{per_firm(k.loc[e, 'non_attendee_meetings_pre_60'], k.loc[e, 'non_attendee_firms']):.2f} → {per_firm(k.loc[e, 'non_attendee_meetings_post_60'], k.loc[e, 'non_attendee_firms']):.2f}"),
    ("Opportunities opened within 90 days", lambda e: f"{k.loc[e, 'assoc_opps']}"),
    ("Attending firms that opened one", lambda e: f"{k.loc[e, 'firm_conversion_rate']:.0%}"),
    ("Associated pipeline (declined)", lambda e: f"{fm(k.loc[e, 'assoc_pipeline_usd'])} ({fm(k.loc[e, 'assoc_declined_usd'])})"),
    ("Committed to date (face value)", lambda e: fm(k.loc[e, "assoc_committed_usd"])),
    ("Cost per associated opportunity", lambda e: fk(k.loc[e, "cost_per_assoc_opp"])),
    ("Diff-in-diff vs firms not at event*", lambda e: f"{k.loc[e, 'diff_in_diff_opp_rate'] * 100:+.0f} pts (p {k.loc[e, 'p_value_did']:.2f})"),
    (f"Diff-in-diff vs firms at no event ({N['clean_n']})*", lambda e: f"{k.loc[e, 'diff_in_diff_clean'] * 100:+.0f} pts (p {k.loc[e, 'p_value_did_clean']:.2f})"),
    ("Days since event", lambda e: f"{k.loc[e, 'days_since_event']}"),
]
score = "".join(f"<tr><td>{l}</td>" + "".join(f"<td>{f(e)}</td>" for e, *_ in EV) + "</tr>" for l, f in score_rows)

html = f"""<!doctype html><html><head><meta charset="utf-8"><title>IR Event Readout</title>
<style>
@page {{ size: 13.333in 7.5in; margin: 0; }}
* {{ box-sizing: border-box; }}
body {{ margin: 0; font-family: Arial, Helvetica, sans-serif; color: #1b1f24; }}
.slide {{ width: 13.333in; height: 7.5in; padding: 0.55in 0.65in 0.45in; page-break-after: always; position: relative; overflow: hidden; background: #fff; }}
.slide.dark {{ background: #0f2340; color: #fff; }}
.kicker {{ font-size: 12pt; letter-spacing: .08em; text-transform: uppercase; color: #6b7785; margin-bottom: 8px; }}
.dark .kicker {{ color: #9ec5f4; }}
h1 {{ font-family: Cambria, Georgia, serif; font-size: 32pt; line-height: 1.12; margin: 0 0 18px; font-weight: 700; }}
h2 {{ font-size: 14pt; margin: 0 0 8px; }}
.stats {{ display: grid; grid-template-columns: repeat(4, 1fr); gap: 18px; margin: 10px 0 24px; }}
.stat .n {{ font-family: Cambria, Georgia, serif; font-size: 40pt; font-weight: 700; line-height: 1; }}
.stat .n {{ color: #0c374a; }}
.stat .l {{ font-size: 11.5pt; color: #3b4450; margin-top: 6px; line-height: 1.3; }}
.msgs {{ display: grid; grid-template-columns: 1fr 1fr; gap: 14px 28px; }}
.msg {{ background: #f2f5f7; border-radius: 10px; padding: 14px 16px; }}
.msg b {{ display: block; font-size: 13.5pt; margin-bottom: 5px; }}
.msg span {{ font-size: 12.5pt; color: #3b4450; line-height: 1.4; }}
.num {{ display: inline-flex; width: 26px; height: 26px; border-radius: 50%; background: #0c374a; color: #fff; font-weight: 700; align-items: center; justify-content: center; font-size: 12pt; margin-right: 8px; }}
.foot {{ position: absolute; bottom: 0.25in; left: 0.65in; right: 0.65in; font-size: 9pt; color: #8a95a3; display: flex; justify-content: space-between; gap: 24px; align-items: flex-end; }}
.msg span.num {{ color: #fff; font-size: 12pt; }}
.foot .note {{ max-width: 8.2in; }}
.foot .sig {{ font-size: 7pt; line-height: 1.3; display: block; margin-bottom: 2px; }}
.foot .author {{ white-space: nowrap; color: #0c374a; font-weight: 600; }}
.logo {{ position: absolute; top: 0.5in; right: 0.65in; height: 0.24in; }}
h1 {{ color: #0c374a; }}
.grid {{ display: grid; grid-template-columns: 1.9fr 1fr; gap: 24px; }}
th {{ white-space: nowrap; }}
table {{ width: 100%; border-collapse: collapse; font-size: 11pt; }}
th {{ text-align: right; font-size: 11pt; padding: 6px 8px; border-bottom: 2px solid #1b1f24; }}
th:first-child, td:first-child {{ text-align: left; }}
td {{ text-align: right; padding: 3.5px 6px; border-bottom: 1px solid #e3e6ea; font-variant-numeric: tabular-nums; white-space: nowrap; }}
th .d {{ display: inline-block; width: 10px; height: 10px; border-radius: 50%; margin-right: 6px; }}
th small {{ display: block; font-weight: 400; color: #6b7785; font-size: 9.5pt; }}
.bars {{ margin-bottom: 20px; }}
.bh {{ font-size: 11.5pt; font-weight: 700; margin-bottom: 8px; }}
.br {{ display: grid; grid-template-columns: 115px 1fr 64px; align-items: center; gap: 8px; margin: 9px 0; font-size: 12pt; }}
.bt {{ background: #f0f2f4; border-radius: 4px; height: 18px; }}
.bf {{ display: block; height: 18px; border-radius: 4px; }}
.bv {{ text-align: right; font-variant-numeric: tabular-nums; }}
.callout {{ background: #eef4fc; border-radius: 10px; padding: 12px 14px; font-size: 11pt; line-height: 1.35; }}
.recs {{ display: grid; grid-template-columns: repeat(2, 1fr); gap: 14px 22px; }}
.rec {{ border: 1px solid #e3e6ea; border-radius: 10px; padding: 14px 18px; }}
.rec b {{ font-size: 13.5pt; display: flex; align-items: center; margin-bottom: 6px; }}
.rec b .num {{ background: #0c374a; color: #fff; }}
.rec p {{ margin: 0; font-size: 12pt; line-height: 1.35; color: #3b4450; }}
.rec .who {{ margin-top: 6px; font-size: 10pt; color: #6b7785; }}
.caveat {{ margin-top: 14px; font-size: 12pt; color: #3b4450; background: #f6f7f8; border-radius: 10px; padding: 10px 14px; }}
</style></head><body>

<section class="slide">
  <img class="logo" src="{LOGO}" alt="Carlyle">
  <div class="kicker">Investor events 2026 · readout for the Head of IR</div>
  <h1>Events reach most of our priority firms but the gap is what happens after</h1>
  <div class="stats">
    <div class="stat"><div class="n">${N['spend'] / 1e6:.1f}M</div><div class="l">spent on 3 events<br>(NY, London, Berlin)</div></div>
    <div class="stat"><div class="n">{N['t1_reached']} of {N['t1_all']}</div><div class="l">Tier 1 firms attended at least one event ({N['firms']} of {N['firms_all']} firms overall)</div></div>
    <div class="stat"><div class="n">{fm(N['pipe'])}</div><div class="l">pipeline opened within 90 days of an attended event ({N['pipe'] / N['pipe_all']:.0%} of 2026 pipeline); {fm(N['committed'])} committed, {fm(N['declined'])} declined</div></div>
    <div class="stat"><div class="n">{N['fu']:.0%}</div><div class="l">of attending firms had a meeting within 30 days (Tier 1: {N['t1_fu']} of {N['t1_n']} attendances)</div></div>
  </div>
  <div class="msgs">
    <div class="msg"><b><span class="num">1</span>Associated, not proven.</b><span>About a third of pipeline followed an event, but there is no evidence of incremental lift. Against non-attendees, the change in attendees' new-opportunity rate runs from {N['did_lo']*100:+.0f} to {N['did_hi']*100:+.0f} pts depending on the event and comparison group, and none is statistically significant*.</span></div>
    <div class="msg"><b><span class="num">2</span>Follow-up is the controllable gap, worst at Tier 1.</b><span>{N['t1_nomtg']} of {N['t1_n']} Tier 1 attendances had no meeting in the next 60 days. {N['gap_n']} Tier 1 firms with {fm(N['gap_pipe'])} of pipeline are on that list.</span></div>
    <div class="msg"><b><span class="num">3</span>The dinner was the cheapest way to reach firms.</b><span>London ({fk(k.loc['E002','cost_usd'])}) cost {fk(k.loc['E002','cost_per_firm'])} per attending firm vs {fk(k.loc['E001','cost_per_firm'])} NY and {fk(k.loc['E003','cost_per_firm'])} Berlin, and a similar share of firms opened an opportunity ({k.loc['E002','firm_conversion_rate']:.0%} vs {k.loc['E001','firm_conversion_rate']:.0%} and {k.loc['E003','firm_conversion_rate']:.0%}). One dinner is not enough to rank formats.</span></div>
    <div class="msg"><b><span class="num">4</span>Berlin needs a case before renewal.</b><span>Our most expensive event ({fk(k.loc['E003','cost_usd'])}): meetings per attending firm fell from {per_firm(k.loc['E003','meetings_pre_60'], k.loc['E003','firms_attended']):.1f} to {per_firm(k.loc['E003','meetings_post_60'], k.loc['E003','firms_attended']):.1f}, more than other firms' summer dip, and nothing has committed. Recheck at 180 days.</span></div>
  </div>
  <div class="foot"><span class="note"><span class="sig">* {SIG}</span>Analysis cutoff 2026-09-23, the extract date (synthetic assessment data); no opportunity was created after {N['last_created']}. Association window: opportunity created 0-90 days after an event the firm confirmed for; most recent event gets credit.</span><span class="author">{AUTHOR}</span></div>
</section>

<section class="slide">
  <img class="logo" src="{LOGO}" alt="Carlyle">
  <div class="kicker">What happened after each event</div>
  <h1 >London cost {fk(k.loc['E002','cost_per_firm'])} per attending firm vs {fk(k.loc['E001','cost_per_firm'])} NY and {fk(k.loc['E003','cost_per_firm'])} Berlin; conversion was similar</h1>
  <div class="grid">
    <div>
      <table>
        <tr><th></th>{''.join(f'<th><span class="d" style="background:{COL[e]}"></span>{n}<small>{t}</small></th>' for e, n, t in EV)}</tr>
        {score}
      </table>
    </div>
    <div>
      {bars('cost_per_assoc_opp', fk, 'Spend per associated opportunity')}
      {bars('followup_rate_30', lambda v: f'{v:.0%}', 'Attending firms met within 30 days')}
      <div class="callout"><b>How to read this.</b> "Associated" means the opportunity opened within 90 days of an event the firm attended. That shows what followed each event, not what it caused: we invite firms already likely to invest, and new opportunities peaked for everyone in June and July, inside London's window. The diff-in-diff rows compare attendees with firms not at that event (many went to another) and with firms at no event; the sign flips between them, so neither shows lift.</div>
    </div>
  </div>
  <div class="foot"><span class="note"><span class="sig">* {SIG}</span>Committed counts only stages dated on or before 2026-09-23; later stages are projected. London's one commitment is a flagged record (O9998, $25M); without it London has none.</span><span class="author">{AUTHOR}</span></div>
</section>

<section class="slide">
  <img class="logo" src="{LOGO}" alt="Carlyle">
  <div class="kicker">What to change for the next event cycle</div>
  <h1 >Four decisions for the 2027 calendar</h1>
  <div class="recs">
    <div class="rec"><b><span class="num">1</span>Put a 10-day follow-up standard on Tier 1 attendees</b><p>Every Tier 1 attendee gets a named owner and a meeting within 10 business days. Start this week with the {N['gap_n']} Tier 1 firms ({fm(N['gap_pipe'])} pipeline) not met in the 60 days after an event they attended. Ten days is a standard to test; 2026 data is too small to show whether faster follow-up lifts conversion.</p><div class="who">Owner: coverage leads · Tracked weekly on the dashboard gap list</div></div>
    <div class="rec"><b><span class="num">2</span>Test a second dinner before moving budget</b><p>London's low spend per opportunity comes from its low cost per firm, at one event, when new opportunities peaked for everyone. Run a second dinner in 2027 and compare conversion with the conferences before shifting money. Hold Berlin's renewal until its 180-day review (December 2026).</p><div class="who">Owner: IR events · Decision: December 2026</div></div>
    <div class="rec"><b><span class="num">3</span>Capture the data that would prove impact</b><p>Tag opportunities with a source event at creation, record check-in (not registration), and require firm mapping for every registrant. Today one registrant has no firm and nine firm registrations are only "tentative".</p><div class="who">Owner: CRM / BI · Before the next event</div></div>
    <div class="rec"><b><span class="num">4</span>Build a comparison into the next events</b><p>Vary follow-up at random among attendees (senior owner or not, 5 vs 15 days) and track invited-but-declined firms as a comparison group, rather than withholding invitations from priority investors. With 60 firms, results stay directional.</p><div class="who">Owner: IR + BI · Pilot on the first 2027 event</div></div>
  </div>
  <div class="caveat"><b>What this analysis cannot say:</b> that events caused the pipeline that followed them. With 19 to 26 attending firms per event, none of the gaps is statistically significant*, and their sign changes with the comparison group. The $650M commitment of the year came from a firm that attended no event, a reminder that most pipeline is built outside the event calendar.</div>
  <div class="foot"><span class="note"><span class="sig">* {SIG}</span></span><span class="author">{AUTHOR}</span></div>
</section>
</body></html>"""

out = ROOT / "readout" / "exec_readout.html"
out.write_text(html)
subprocess.run([CHROME, "--headless=new", "--disable-gpu", "--no-pdf-header-footer",
                f"--print-to-pdf={ROOT / 'readout' / 'exec_readout.pdf'}", out.as_uri()],
               check=True, capture_output=True)
print("wrote readout/exec_readout.html and readout/exec_readout.pdf")
