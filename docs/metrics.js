// Filter-aware event KPIs for the static dashboard. Line-for-line port of app/metrics.py:
// with no extra filters it reproduces mart_event_kpis (checked by selfTest() below).
// Filters: {window, tentative, segment: [..], fund: [..], seniority: subset of ['senior','non_senior'], excludeOutlier}
// Empty arrays mean no filter; both seniority options selected is the same as none.
(function () {
  const DAY = 864e5;
  const toDate = s => (s ? new Date(s + 'T00:00:00Z') : null);
  const median = xs => {
    const v = xs.filter(x => x != null && !Number.isNaN(x)).sort((a, b) => a - b);
    if (!v.length) return null;
    const m = Math.floor(v.length / 2);
    return v.length % 2 ? v[m] : (v[m - 1] + v[m]) / 2;
  };
  const mean = xs => (xs.length ? xs.reduce((a, b) => a + b, 0) / xs.length : null);
  function rng(seed) { // mulberry32
    return () => { seed |= 0; seed = (seed + 0x6D2B79F5) | 0; let t = Math.imul(seed ^ (seed >>> 15), 1 | seed);
      t = (t + Math.imul(t ^ (t >>> 7), 61 | t)) ^ t; return ((t ^ (t >>> 14)) >>> 0) / 4294967296; };
  }

  function prepare(D) {
    const fe = D.mart_firm_event.map(r => ({...r, ed: toDate(r.event_date)}));
    const opps = D.mart_opportunity.map(o => ({...o, cd: toDate(o.created_date), comd: toDate(o.committed_date), decd: toDate(o.declined_date)}));
    const stages = {};
    D.mart_stage_history.forEach(s => (stages[s.opportunity_id] = stages[s.opportunity_id] || []).push({...s, sd: toDate(s.stage_date)}));
    const seen = new Set(), events = [];
    D.mart_event_kpis.forEach(r => { if (!seen.has(r.event_id)) { seen.add(r.event_id); events.push({...r, ed: toDate(r.event_date)}); } });
    events.sort((a, b) => a.event_id.localeCompare(b.event_id));
    return {fe, opps, stages, events, firms: D.mart_firm, meetings: D.mart_meetings, kpis: D.mart_event_kpis};
  }

  const arr = v => (v == null || v === 'All' ? [] : Array.isArray(v) ? v : [v]);
  const senMode = f => (arr(f.seniority).length === 1 ? arr(f.seniority)[0] : 'All');
  const isDefaultExtra = f => !arr(f.segment).length && !arr(f.fund).length && senMode(f) === 'All' && !f.excludeOutlier;

  function attendance(P, f) {
    let base = P.fe.filter(r => r.is_confirmed || f.tentative);
    if (arr(f.segment).length) base = base.filter(r => arr(f.segment).includes(r.segment));
    const senior = r => (f.tentative ? r.senior_contacts > 0 : r.has_confirmed_senior);
    let att = base;
    if (senMode(f) === 'senior') att = base.filter(senior);
    else if (senMode(f) === 'non_senior') att = base.filter(r => !senior(r));
    return {att, base};
  }

  function filteredOpps(P, f) {
    return P.opps.filter(o => (!arr(f.segment).length || arr(f.segment).includes(o.segment)) && (!arr(f.fund).length || arr(f.fund).includes(o.fund_name)) && !(f.excludeOutlier && o.is_amount_outlier));
  }

  function associate(opps, att, window) {
    const byFirm = {};
    att.forEach(r => (byFirm[r.firm_id] = byFirm[r.firm_id] || []).push(r));
    return opps.map(o => {
      let best = null;
      (byFirm[o.firm_id] || []).forEach(r => {
        const d = Math.round((o.cd - r.ed) / DAY);
        if (d >= 0 && d <= window && (best === null || d < best.d)) best = {e: r.event_id, d};
      });
      return {...o, assoc_event_id: best ? best.e : null, days_after_event: best ? best.d : null};
    });
  }

  function permP(change, attended, rand, n = 5000) {
    const nA = attended.filter(Boolean).length, N = attended.length;
    if (!nA || nA === N) return null;
    const stat = lab => { let a = 0, b = 0; lab.forEach((x, i) => (x ? (a += change[i]) : (b += change[i]))); return a / nA - b / (N - nA); };
    const obs = stat(attended), lab = attended.slice();
    let hits = 0;
    for (let k = 0; k < n; k++) {
      for (let i = N - 1; i > 0; i--) { const j = Math.floor(rand() * (i + 1)); [lab[i], lab[j]] = [lab[j], lab[i]]; }
      if (Math.abs(stat(lab)) >= Math.abs(obs) - 1e-12) hits++;
    }
    return hits / n;
  }

  function eventKpis(P, f) {
    const {att, base} = attendance(P, f);
    const opps = filteredOpps(P, f);
    const assoc = associate(opps, att, f.window);
    const firms = !arr(f.segment).length ? P.firms : P.firms.filter(r => arr(f.segment).includes(r.segment));
    const rand = rng(7);
    const rows = P.events.map(ev => {
      const a = att.filter(r => r.event_id === ev.event_id);
      const attIds = new Set(a.map(r => r.firm_id));
      const allAttIds = new Set(base.filter(r => r.event_id === ev.event_id).map(r => r.firm_id));
      const s = assoc.filter(o => o.assoc_event_id === ev.event_id);
      const n = a.length, sum = (xs, fn) => xs.reduce((t, x) => t + fn(x), 0);
      const r = {event_id: ev.event_id, event_name: ev.event_name, event_date: ev.event_date, event_type: ev.event_type, location: ev.location,
        cost_usd: ev.cost_usd, days_since_event: ev.days_since_event, window_days: f.window, include_tentative: f.tentative};
      r.firms_attended = n; r.tier1_firms = a.filter(x => x.tier === 'Tier 1').length; r.firms_with_senior = a.filter(x => x.has_confirmed_senior).length;
      r.cost_per_firm = n ? ev.cost_usd / n : null;
      r.firms_followup_30 = a.filter(x => x.meetings_post_30 > 0).length; r.followup_rate_30 = n ? r.firms_followup_30 / n : null;
      r.median_days_to_followup = median(a.map(x => x.days_to_first_followup));
      r.meetings_pre_60 = sum(a, x => x.meetings_pre_60); r.meetings_post_60 = sum(a, x => x.meetings_post_60);
      r.assoc_opps = s.length; r.assoc_firms = new Set(s.map(o => o.firm_id)).size; r.firm_conversion_rate = n ? r.assoc_firms / n : null;
      r.assoc_pipeline_usd = sum(s, o => o.amount_usd); r.assoc_pipeline_ex_outlier_usd = sum(s.filter(o => !o.is_amount_outlier), o => o.amount_usd);
      r.assoc_opps_reached_dd = s.filter(o => o.reached_dd).length;
      const won = s.filter(o => o.outcome === 'Committed');
      r.assoc_committed_opps = won.length; r.assoc_committed_usd = sum(won, o => o.amount_usd); r.assoc_declined_opps = s.filter(o => o.outcome === 'Declined').length;
      r.median_days_event_to_opp = median(s.map(o => o.days_after_event));
      r.pipeline_to_cost = r.assoc_pipeline_usd / ev.cost_usd; r.cost_per_assoc_opp = r.assoc_opps ? ev.cost_usd / r.assoc_opps : null;
      const ed = ev.ed, w = f.window * DAY;
      const after = new Set(opps.filter(o => o.cd >= ed && o.cd <= ed.getTime() + w).map(o => o.firm_id));
      const before = new Set(opps.filter(o => o.cd < ed && o.cd >= ed.getTime() - w).map(o => o.firm_id));
      const grp = firms.filter(x => attIds.has(x.firm_id) || !allAttIds.has(x.firm_id));
      const A = grp.filter(x => attIds.has(x.firm_id)), N = grp.filter(x => !attIds.has(x.firm_id));
      const rate = (g, set) => (g.length ? g.filter(x => set.has(x.firm_id)).length / g.length : null);
      r.attendee_new_opp_rate = rate(A, after); r.attendee_prior_opp_rate = rate(A, before);
      r.non_attendee_new_opp_rate = rate(N, after); r.non_attendee_prior_opp_rate = rate(N, before); r.non_attendee_firms = N.length;
      r.diff_in_diff_opp_rate = A.length && N.length ? (r.attendee_new_opp_rate - r.attendee_prior_opp_rate) - (r.non_attendee_new_opp_rate - r.non_attendee_prior_opp_rate) : null;
      r.p_value_did = A.length && N.length && !isDefaultExtra(f)
        ? permP(grp.map(x => (after.has(x.firm_id) ? 1 : 0) - (before.has(x.firm_id) ? 1 : 0)), grp.map(x => attIds.has(x.firm_id)), rand) : null;
      let nA = 0, aA = 0, nN = 0, aN = 0, usd = 0;
      opps.filter(o => o.cd < ed && !(o.comd && o.comd < ed) && !(o.decd && o.decd < ed)).forEach(o => {
        const h = P.stages[o.opportunity_id] || [];
        const rank0 = Math.max(0, ...h.filter(x => x.sd < ed && x.stage_rank > 0).map(x => x.stage_rank));
        const adv = h.some(x => !x.is_future && x.stage_rank > rank0 && x.sd >= ed && x.sd <= ed.getTime() + w);
        if (attIds.has(o.firm_id)) { nA++; aA += adv; usd += o.amount_usd; } else if (!allAttIds.has(o.firm_id)) { nN++; aN += adv; }
      });
      Object.assign(r, {open_opps_attendees: nA, open_opps_attendees_advanced: aA, open_opps_non_attendees: nN, open_opps_non_attendees_advanced: aN, open_pipeline_attendees_usd: usd});
      return r;
    });
    if (isDefaultExtra(f)) { // same p-values as the build, so every surface agrees
      rows.forEach(r => { const m = P.kpis.find(k => k.event_id === r.event_id && k.window_days === f.window && k.include_tentative === f.tentative); r.p_value_did = m.p_value_did; });
    }
    rows.forEach(r => { r.did_significant = r.p_value_did != null && r.p_value_did < 0.05; r.n_permutations = 5000; });
    return rows;
  }

  function selfTest(P) {
    const cols = ['firms_attended', 'tier1_firms', 'firms_with_senior', 'cost_per_firm', 'firms_followup_30', 'followup_rate_30', 'median_days_to_followup',
      'meetings_pre_60', 'meetings_post_60', 'assoc_opps', 'assoc_firms', 'firm_conversion_rate', 'assoc_pipeline_usd', 'assoc_pipeline_ex_outlier_usd',
      'assoc_opps_reached_dd', 'assoc_committed_opps', 'assoc_committed_usd', 'assoc_declined_opps', 'median_days_event_to_opp', 'cost_per_assoc_opp',
      'attendee_new_opp_rate', 'attendee_prior_opp_rate', 'non_attendee_new_opp_rate', 'non_attendee_prior_opp_rate', 'non_attendee_firms',
      'diff_in_diff_opp_rate', 'open_opps_attendees', 'open_opps_attendees_advanced', 'open_opps_non_attendees', 'open_opps_non_attendees_advanced',
      'open_pipeline_attendees_usd'];
    const bad = [];
    [30, 60, 90, 180].forEach(w => [false, true].forEach(t => eventKpis(P, {window: w, tentative: t, segment: [], fund: [], seniority: [], excludeOutlier: false}).forEach(r => {
      const m = P.kpis.find(k => k.event_id === r.event_id && k.window_days === w && k.include_tentative === t);
      cols.forEach(c => { const x = r[c], y = m[c]; if (!((x == null && y == null) || Math.abs(x - y) < 1e-9)) bad.push(`${w}/${t}/${r.event_id}/${c}: ${x} vs ${y}`); });
    })));
    return bad;
  }

  window.IRMetrics = {prepare, attendance, filteredOpps, associate, eventKpis, selfTest, senMode, isDefaultExtra};
})();
