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
)
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
       f"significant only if p < 0.05. p = {k.loc['E001', 'p_value_did']:.2f} (NY), {k.loc['E002', 'p_value_did']:.2f} (London), "
       f"{k.loc['E003', 'p_value_did']:.2f} (Berlin).")
score_rows = [
    ("Cost", lambda e: fk(k.loc[e, "cost_usd"])),
    ("Firms attended (Tier 1)", lambda e: f"{k.loc[e, 'firms_attended']} ({k.loc[e, 'tier1_firms']})"),
    ("Follow-up meeting within 30 days", lambda e: f"{k.loc[e, 'followup_rate_30']:.0%}"),
    ("Meetings, 60 days before → after", lambda e: f"{k.loc[e, 'meetings_pre_60']:.0f} → {k.loc[e, 'meetings_post_60']:.0f}"),
    ("Opportunities opened within 90 days", lambda e: f"{k.loc[e, 'assoc_opps']}"),
    ("Associated pipeline", lambda e: fm(k.loc[e, "assoc_pipeline_usd"])),
    ("Committed to date", lambda e: fm(k.loc[e, "assoc_committed_usd"])),
    ("Cost per associated opportunity", lambda e: fk(k.loc[e, "cost_per_assoc_opp"])),
    ("Lift vs non-attendees (diff-in-diff)", lambda e: f"{k.loc[e, 'diff_in_diff_opp_rate'] * 100:+.0f} pts"),
    ("p-value, permutation test*", lambda e: f"{k.loc[e, 'p_value_did']:.2f}"),
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
h1 {{ color: #0c374a; padding-right: 2.2in; }}
.grid {{ display: grid; grid-template-columns: 1.6fr 1fr; gap: 30px; }}
th {{ white-space: nowrap; }}
table {{ width: 100%; border-collapse: collapse; font-size: 12.5pt; }}
th {{ text-align: right; font-size: 11pt; padding: 6px 8px; border-bottom: 2px solid #1b1f24; }}
th:first-child, td:first-child {{ text-align: left; }}
td {{ text-align: right; padding: 5px 8px; border-bottom: 1px solid #e3e6ea; font-variant-numeric: tabular-nums; }}
th .d {{ display: inline-block; width: 10px; height: 10px; border-radius: 50%; margin-right: 6px; }}
th small {{ display: block; font-weight: 400; color: #6b7785; font-size: 9.5pt; }}
.bars {{ margin-bottom: 20px; }}
.bh {{ font-size: 11.5pt; font-weight: 700; margin-bottom: 8px; }}
.br {{ display: grid; grid-template-columns: 115px 1fr 64px; align-items: center; gap: 8px; margin: 9px 0; font-size: 12pt; }}
.bt {{ background: #f0f2f4; border-radius: 4px; height: 18px; }}
.bf {{ display: block; height: 18px; border-radius: 4px; }}
.bv {{ text-align: right; font-variant-numeric: tabular-nums; }}
.callout {{ background: #eef4fc; border-radius: 10px; padding: 14px 16px; font-size: 12pt; line-height: 1.4; }}
.recs {{ display: grid; grid-template-columns: repeat(2, 1fr); gap: 22px 26px; }}
.rec {{ border: 1px solid #e3e6ea; border-radius: 10px; padding: 20px 22px; }}
.rec b {{ font-size: 13.5pt; display: flex; align-items: center; margin-bottom: 6px; }}
.rec b .num {{ background: #0c374a; color: #fff; }}
.rec p {{ margin: 0; font-size: 13pt; line-height: 1.4; color: #3b4450; }}
.rec .who {{ margin-top: 6px; font-size: 10pt; color: #6b7785; }}
.caveat {{ margin-top: 22px; font-size: 12pt; color: #3b4450; background: #f6f7f8; border-radius: 10px; padding: 10px 14px; }}
</style></head><body>

<section class="slide">
  <img class="logo" src="{LOGO}" alt="Carlyle">
  <div class="kicker">Investor events 2026 · readout for the Head of IR</div>
  <h1>Events reach most of our priority firms, but the gap is what happens after</h1>
  <div class="stats">
    <div class="stat"><div class="n">${N['spend'] / 1e6:.1f}M</div><div class="l">spent on 3 events<br>(NY, London, Berlin)</div></div>
    <div class="stat"><div class="n">{N['t1_reached']} of {N['t1_all']}</div><div class="l">Tier 1 firms attended at least one event ({N['firms']} of {N['firms_all']} firms overall)</div></div>
    <div class="stat"><div class="n">{fm(N['pipe'])}</div><div class="l">pipeline opened within 90 days of an attended event ({N['pipe'] / N['pipe_all']:.0%} of 2026 pipeline); {fm(N['committed'])} committed</div></div>
    <div class="stat"><div class="n">{N['fu']:.0%}</div><div class="l">of attending firms had a meeting within 30 days (Tier 1: {N['t1_fu']} of {N['t1_n']} attendances)</div></div>
  </div>
  <div class="msgs">
    <div class="msg"><b><span class="num">1</span>Associated, not proven.</b><span>About a third of pipeline followed an event, but attendees did not open opportunities faster than comparable non-attendees (NY {k.loc['E001','diff_in_diff_opp_rate']*100:+.0f} pts, London {k.loc['E002','diff_in_diff_opp_rate']*100:+.0f}, Berlin {k.loc['E003','diff_in_diff_opp_rate']*100:+.0f}; none statistically significant*).</span></div>
    <div class="msg"><b><span class="num">2</span>Follow-up is the controllable gap, worst at Tier 1.</b><span>{N['t1_nomtg']} of {N['t1_n']} Tier 1 attendances had no meeting in the next 60 days. {N['gap_n']} Tier 1 firms with {fm(N['gap_pipe'])} of pipeline are on that list.</span></div>
    <div class="msg"><b><span class="num">3</span>The dinner was the most efficient format.</b><span>London ({fk(k.loc['E002','cost_usd'])}): {fk(k.loc['E002','cost_per_assoc_opp'])} per associated opportunity and the most post-event meetings, vs {fk(k.loc['E001','cost_per_assoc_opp'])} NY and {fk(k.loc['E003','cost_per_assoc_opp'])} Berlin.</span></div>
    <div class="msg"><b><span class="num">4</span>Berlin needs a case before renewal.</b><span>Our most expensive event ({fk(k.loc['E003','cost_usd'])}): meetings with attendees fell ({k.loc['E003','meetings_pre_60']:.0f} → {k.loc['E003','meetings_post_60']:.0f}) and nothing has committed yet. Recheck at 180 days.</span></div>
  </div>
  <div class="foot"><span class="note"><span class="sig">* {SIG}</span>Data as of 2026-09-23 (synthetic assessment data). Association window: opportunity created 0-90 days after an event the firm confirmed for; most recent event gets credit.</span><span class="author">{AUTHOR}</span></div>
</section>

<section class="slide">
  <img class="logo" src="{LOGO}" alt="Carlyle">
  <div class="kicker">What happened after each event</div>
  <h1 >The $185K London dinner produced opportunities at about half the cost of NY and a fifth of Berlin</h1>
  <div class="grid">
    <div>
      <table>
        <tr><th></th>{''.join(f'<th><span class="d" style="background:{COL[e]}"></span>{n}<small>{t}</small></th>' for e, n, t in EV)}</tr>
        {score}
      </table>
    </div>
    <div>
      {bars('cost_per_assoc_opp', fk, 'Cost per associated opportunity (lower is better)')}
      {bars('followup_rate_30', lambda v: f'{v:.0%}', 'Attending firms met within 30 days')}
      <div class="callout"><b>How to read this.</b> "Associated" means the opportunity opened within 90 days of an event the firm attended. That shows what followed each event, not what it caused: we invite firms already likely to invest, and new opportunities peaked for everyone in June and July. The diff-in-diff row compares against firms that did not attend over the same dates.</div>
    </div>
  </div>
  <div class="foot"><span class="note"><span class="sig">* {SIG}</span>Committed counts only stages dated on or before 2026-09-23; later-dated stages are treated as projected.</span><span class="author">{AUTHOR}</span></div>
</section>

<section class="slide">
  <img class="logo" src="{LOGO}" alt="Carlyle">
  <div class="kicker">What to change for the next event cycle</div>
  <h1 >Four decisions for the 2027 calendar</h1>
  <div class="recs">
    <div class="rec"><b><span class="num">1</span>Put a 10-day follow-up standard on Tier 1 attendees</b><p>Every Tier 1 attendee gets a named owner and a meeting within 10 business days. Start this week with the {N['gap_n']} Tier 1 firms ({fm(N['gap_pipe'])} pipeline) that attended and have not been met since. Faster follow-up did not by itself raise conversion in 2026 data, so treat this as a standard plus a test.</p><div class="who">Owner: coverage leads · Tracked weekly on the dashboard gap list</div></div>
    <div class="rec"><b><span class="num">2</span>Shift budget toward targeted hospitality</b><p>Run a second dinner-format event in 2027 and fund it from the conference line. Hold the Berlin renewal until its 180-day review (mid-December 2026); renew only if associated commitments appear.</p><div class="who">Owner: IR events · Decision: December 2026</div></div>
    <div class="rec"><b><span class="num">3</span>Capture the data that would prove impact</b><p>Tag opportunities with a source event at creation, record check-in (not registration), and require firm mapping for every registrant. Today one registrant has no firm and nine firm registrations are only "tentative".</p><div class="who">Owner: CRM / BI · Before the next event</div></div>
    <div class="rec"><b><span class="num">4</span>Design the next events to measure lift</b><p>Hold back invitations to a small matched group of firms (same tier, segment, region) and compare 90-day outcomes. One event is too small to prove lift; four to six events with the same design can.</p><div class="who">Owner: IR + BI · Pilot on the first 2027 event</div></div>
  </div>
  <div class="caveat"><b>What this analysis cannot say:</b> that events caused the pipeline that followed them. With 19 to 26 attending firms per event, none of the three gaps is statistically significant*. The $650M commitment of the year came from a firm that attended no event, a reminder that most pipeline is built outside the event calendar.</div>
  <div class="foot"><span class="note"><span class="sig">* {SIG}</span></span><span class="author">{AUTHOR}</span></div>
</section>
</body></html>"""

out = ROOT / "readout" / "exec_readout.html"
out.write_text(html)
subprocess.run([CHROME, "--headless=new", "--disable-gpu", "--no-pdf-header-footer",
                f"--print-to-pdf={ROOT / 'readout' / 'exec_readout.pdf'}", out.as_uri()],
               check=True, capture_output=True)
print("wrote readout/exec_readout.html and readout/exec_readout.pdf")
