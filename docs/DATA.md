## Source data

Five CSV extracts, all synthetic. Every table joins on `firm_id`; attendance also joins to events on `event_id`.

| File | Rows | Grain (one row per) | Key fields | What it tells us |
|---|---|---|---|---|
| `events.csv` | 3 | Event | event_id, date, type, location, cost_usd | What we spent and when: NY Summit (Mar), London Dinner (May), Berlin Forum (Jun), $1.215M total |
| `firms.csv` | 60 | Investor firm | firm_id, segment, priority tier, region, historical commitments | Who the investor is and how important they are |
| `event_attendees.csv` | 131 | Contact registered for an event | event_id, firm_id, title, status (Confirmed / Tentative) | Who we reached, how senior, and how firm the registration was |
| `meetings.csv` | 112 | Meeting with a firm | firm_id, date, type, internal attendee, purpose | Engagement before and after each event |
| `opportunity_stage_history.csv` | 358 (107 opportunities) | Stage change on an opportunity | opportunity_id, firm_id, fund, created date, stage date, stage, amount | Pipeline creation, progression, and commitments |

**What is not in the data:** no field records which event (if any) produced an opportunity, and no check-in data (only registration status). Both limits shape the method below.

## Data model

Built in DuckDB with plain SQL in three layers (`sql/01_staging.sql`, `02_core.sql`, `03_marts.sql`), run by `src/build.py`.

| Layer | Tables | Purpose |
|---|---|---|
| **Staging** | `stg_events`, `stg_firms`, `stg_attendees`, `stg_meetings`, `stg_opp_stage` | Cast types, drop the exact duplicate, flag unmapped contacts, collapse repeated stages, flag stages dated after the as-of date |
| **Core** | `dim_event`, `dim_firm`, `fct_firm_event`, `fct_meeting`, `fct_opportunity` | One clean table per business entity. `fct_firm_event` rolls contacts up to firm x event (confirmed?, senior attendee?). `fct_opportunity` is one row per opportunity with highest stage reached, outcome, and dates |
| **Link** | `bridge_opp_event` | Credits each opportunity to at most one event, for every window (30/60/90/180 days) and attendance rule (confirmed only or incl. tentative) |
| **Marts** | `mart_event_kpis`, `mart_firm_event`, `mart_firm`, `mart_opportunity`, `mart_firm_timeline`, `mart_segment`, `dq_log` | What the dashboards read. All metric logic lives here, so the HTML page and this app show identical numbers |

The build also runs 11 assertions (totals reconcile to raw files, one row per opportunity, no double-credited opportunity) and fails if any break.
