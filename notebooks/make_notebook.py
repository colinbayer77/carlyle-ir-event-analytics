"""Generate and execute notebooks/analysis.ipynb.

Kept as a script so the notebook is reproducible and diffable:
    python notebooks/make_notebook.py
"""
from pathlib import Path

import nbformat as nbf
from nbconvert.preprocessors import ExecutePreprocessor

HERE = Path(__file__).parent
md, code = nbf.v4.new_markdown_cell, nbf.v4.new_code_cell

cells = [
    md("""# IR event outcomes: analysis and validation

This notebook does three things:
1. Profiles the raw data (what the DQ log is based on).
2. **Independently recomputes the headline numbers in pandas from the raw CSVs** and checks them against the DuckDB SQL marts. Two separate implementations agreeing is the main guard against a logic error (mine or the AI's).
3. Tests how robust the findings are: window sensitivity, comparison groups, tier cuts, and a permutation test on the attendee vs non-attendee gap.

Run `python src/build.py` first."""),
    code("""import sys, subprocess
from pathlib import Path
import numpy as np, pandas as pd
ROOT = Path.cwd().parent if Path.cwd().name == 'notebooks' else Path.cwd()
subprocess.run([sys.executable, str(ROOT / 'src' / 'build.py')], check=True, capture_output=True, cwd=ROOT / 'src')
RAW, MARTS = ROOT / 'data' / 'raw', ROOT / 'data' / 'marts'
raw = {p.stem: pd.read_csv(p, dtype=str) for p in RAW.glob('*.csv')}
marts = {p.stem: pd.read_csv(p) for p in MARTS.glob('*.csv')}
AS_OF = pd.Timestamp('2026-09-23')
pd.set_option('display.width', 200)
{k: v.shape for k, v in raw.items()}"""),
    md("## 1. Profile"),
    code("""ev = raw['events'].assign(event_date=lambda d: pd.to_datetime(d.event_date), cost_usd=lambda d: d.cost_usd.astype(float))
att = raw['event_attendees']
mtg = raw['meetings'].assign(meeting_date=lambda d: pd.to_datetime(d.meeting_date))
osh = raw['opportunity_stage_history'].assign(created_date=lambda d: pd.to_datetime(d.created_date), stage_date=lambda d: pd.to_datetime(d.stage_date),
                                               amount=lambda d: d.opportunity_amount_usd.astype(float))
firms = raw['firms']
print('duplicate attendance rows:', att.duplicated().sum())
print('attendees with blank firm:', att.firm_id.isna().sum())
print('float-formatted amounts:', osh.opportunity_amount_usd.str.contains(r'\\.').sum())
print('stage rows after as-of:', (osh.stage_date > AS_OF).sum())
print('amount distribution ($M):', sorted((osh.groupby('opportunity_id').amount.first() / 1e6).unique()))
print('opps created by month:'); print(osh.groupby('opportunity_id').created_date.first().dt.to_period('M').value_counts().sort_index().to_dict())"""),
    md("## 2. Independent recomputation vs SQL marts"),
    code("""# Clean exactly as documented, but in pandas
att_c = att.drop_duplicates().dropna(subset=['firm_id'])
conf = att_c[att_c.attendance_status == 'Confirmed'][['event_id', 'firm_id']].drop_duplicates().merge(ev[['event_id', 'event_date', 'cost_usd']])
actual = osh[osh.stage_date <= AS_OF]
# Same opportunity entered twice under two IDs (identical firm, fund, dates, stages, amount): keep the lowest ID
sig = osh.sort_values(['stage_date', 'stage']).groupby('opportunity_id').apply(lambda g: (g.firm_id.iloc[0], g.fund_name.iloc[0], g.created_date.iloc[0], tuple(zip(g.stage_date, g.stage, g.amount))))
dups = sig[sig.duplicated(keep='first')].index
print('duplicate opportunity IDs dropped:', list(dups))
osh = osh[~osh.opportunity_id.isin(dups)]
actual = osh[osh.stage_date <= AS_OF]
opp = osh.groupby('opportunity_id').agg(firm_id=('firm_id', 'first'), created=('created_date', 'first'), amount=('amount', 'first')).reset_index()
committed = actual[actual.stage == 'Committed'].groupby('opportunity_id').stage_date.min()
opp['committed'] = opp.opportunity_id.map(committed).notna()

# Association: created 0..90 days after an attended event, most recent event wins
pairs = opp.merge(conf, on='firm_id')
pairs['d'] = (pairs.created - pairs.event_date).dt.days
pairs = pairs[(pairs.d >= 0) & (pairs.d <= 90)].sort_values('d').drop_duplicates('opportunity_id')
pd_kpi = pairs.groupby('event_id').agg(assoc_opps=('opportunity_id', 'count'), assoc_pipeline_usd=('amount', 'sum'),
                                        assoc_committed_usd=('amount', lambda s: s[pairs.loc[s.index, 'committed']].sum()))
pd_kpi['firms_attended'] = conf.groupby('event_id').firm_id.nunique()

# Follow-up within 30 days
fu = conf.merge(mtg, on='firm_id', how='left')
fu['in30'] = (fu.meeting_date > fu.event_date) & (fu.meeting_date <= fu.event_date + pd.Timedelta(days=30))
pd_kpi['firms_followup_30'] = fu.groupby(['event_id', 'firm_id']).in30.any().groupby('event_id').sum()

sql = marts['mart_event_kpis'].query('window_days == 90 and not include_tentative').set_index('event_id')[pd_kpi.columns]
check = pd.concat({'pandas': pd_kpi, 'sql': sql}, axis=1)
display(check)
assert np.allclose(pd_kpi.values.astype(float), sql.values.astype(float)), 'pandas and SQL disagree'
print('MATCH: pandas recomputation equals SQL marts for all headline KPIs')"""),
    md("## 3. How robust are the findings?\n\n### Window sensitivity"),
    code("""k = marts['mart_event_kpis']
k[~k.include_tentative].pivot_table(index='window_days', columns='event_id',
    values=['assoc_opps', 'assoc_pipeline_usd', 'diff_in_diff_opp_rate', 'followup_rate_30']).round(2)"""),
    md("""Reading: associated pipeline grows with the window (as it must), but the **ranking of events on efficiency does not change** at 30, 60, or 90 days: London is cheapest per opportunity, Berlin most expensive. The difference-in-differences is positive for NY at every window, negative for London from 60 days on, and within 3 points of zero for Berlin at every window. Follow-up rates do not depend on the window."""),
    md("### Permutation test: is the attendee vs non-attendee gap distinguishable from noise?"),
    code("""rng = np.random.default_rng(7)
fw = []
for _, e in ev.iterrows():
    a = set(conf[conf.event_id == e.event_id].firm_id)
    for f in firms.firm_id:
        o = opp[opp.firm_id == f]
        after = ((o.created >= e.event_date) & (o.created <= e.event_date + pd.Timedelta(days=90))).any()
        before = ((o.created < e.event_date) & (o.created >= e.event_date - pd.Timedelta(days=90))).any()
        fw.append((e.event_id, f, f in a, int(after) - int(before)))
fw = pd.DataFrame(fw, columns=['event_id', 'firm_id', 'attended', 'change'])

def did(df):
    return df[df.attended].change.mean() - df[~df.attended].change.mean()

rows = []
for eid, g in fw.groupby('event_id'):
    obs = did(g)
    null = [did(g.assign(attended=rng.permutation(g.attended.values))) for _ in range(5000)]
    rows.append((eid, round(obs * 100, 1), round(np.mean(np.abs(null) >= abs(obs)), 3)))
pd.DataFrame(rows, columns=['event', 'diff_in_diff_pts', 'p_value (two-sided)'])"""),
    md("""None of the three differences is statistically significant: every p-value is well above the 0.05 threshold, with 19 to 26 attending firms per event. The build computes the same test for every window and attendance setting (`p_value_did` in `mart_event_kpis`). The honest conclusion is **"no detectable lift in new-opportunity creation"**, not "events do not work". The readout says exactly that, and recommends a design that could detect lift (see section 5)."""),
    md("### Tier and follow-up cuts"),
    code("""fe = marts['mart_firm_event'].query('is_confirmed')
display(fe.groupby('tier').agg(firm_events=('firm_id', 'count'), followup_30=('followed_up_30', 'mean'),
                               no_meeting_60=('meetings_post_60', lambda s: (s.fillna(0) == 0).mean()),
                               converted=('assoc_opps_90', lambda s: (s > 0).mean())).round(2))
display(fe.groupby('followed_up_30').agg(n=('firm_id', 'count'), converted=('assoc_opps_90', lambda s: (s > 0).mean())).round(2))"""),
    md("""Tier 1 firms get the **least** follow-up (29% within 30 days, and over half have no meeting within 60 days). Follow-up within 30 days is not associated with higher conversion in this data (37% vs 40%), which is a caution against promising that faster follow-up alone will lift pipeline. The recommendation is framed as an operating standard plus a test, not a guaranteed return."""),
    md("### Where did pipeline come from?"),
    code("""o = marts['mart_opportunity']
t = o.groupby('source_bucket').agg(opps=('opportunity_id', 'count'), pipeline_m=('amount_usd', lambda s: s.sum() / 1e6),
                                   committed_m=('amount_usd', lambda s: s[o.loc[s.index, 'outcome'] == 'Committed'].sum() / 1e6))
t['share_of_pipeline'] = (t.pipeline_m / t.pipeline_m.sum()).round(2)
t"""),
    md("""## 4. Outlier check

O0017 ($650M committed, firm F041) is 4x the next largest ticket. F041 attended no event and had no logged meetings, so it does not touch any event metric. It does dominate total commitments ($1.2B YTD), so any "events vs rest" comparison of committed dollars should be read ex-outlier."""),
    code("""o[o.is_amount_outlier][['opportunity_id', 'firm_name', 'amount_usd', 'outcome', 'source_bucket']]"""),
    md("""## 5. What would let us measure causation next time

- **Source tagging.** Add `source_event_id` / campaign to opportunities at creation in the CRM.
- **Check-in data.** Capture actual attendance, not registration status.
- **Holdout.** For the next event, randomly hold back invitations to a small set of comparable firms (matched on tier, segment, region) and compare 90-day outcomes. With about 25 attendees per event, one event cannot prove lift; pooling 4 to 6 events with a consistent design can.
- **Follow-up SLA as an experiment.** Assign an owner and a 10-business-day SLA for Tier 1 attendees and compare conversion against the 2026 baseline."""),
]

nb = nbf.v4.new_notebook(cells=cells, metadata={"kernelspec": {"name": "python3", "display_name": "Python 3", "language": "python"}})
ExecutePreprocessor(timeout=300, kernel_name="python3").preprocess(nb, {"metadata": {"path": str(HERE)}})
nbf.write(nb, HERE / "analysis.ipynb")
print("wrote notebooks/analysis.ipynb")
