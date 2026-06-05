# Spec: Date Filter for Profile Page

## Overview

This feature adds a date-range filter to the Spendly profile page so users can
scope their summary statistics (Total Spent, Transactions, Top Category) and any
category breakdown or recent-transactions panel to a specific time window.
Without a filter, the profile page always shows all-time aggregates, which
becomes less useful as transaction history grows. The filter is surfaced as a
compact control bar above the stats grid: a set of preset quick-picks (This
Month, Last Month, Last 3 Months, Last 6 Months, This Year, All Time) plus
optional custom From / To date inputs. All filtering is server-side via query
string parameters so the page remains fully functional without JavaScript.

### Preset date-range definitions

These are the exact date boundaries `app.py` must compute for each preset.
`today` is `date.today()`. All values are ISO strings (`YYYY-MM-DD`) or `None`.

| `preset` value | `date_from` | `date_to` |
|---|---|---|
| `this_month` | First day of the current calendar month (`today.replace(day=1)`) | `today` |
| `last_month` | First day of the previous calendar month | Last day of the previous calendar month (`date_from.replace(day=...) - timedelta(days=1)` pattern) |
| `last_3_months` | `today - timedelta(days=90)` | `today` |
| `last_6_months` | `today - timedelta(days=180)` | `today` |
| `this_year` | `date(today.year, 1, 1)` | `today` |
| `all_time` | `None` | `None` |
| *(unknown / missing)* | `None` | `None` (fall back to all-time silently) |

> **`last_month` algorithm** — subtract one day from the first of the current
> month to land on the last day of the previous month, then call `.replace(day=1)`
> on that date to get the first day of the previous month.
> Example for June 2026: `date_to = date(2026, 6, 1) - timedelta(days=1)` → `2026-05-31`;
> `date_from = date_to.replace(day=1)` → `2026-05-01`.

> **Note:** GEMINI.md maps Step 7 to "Add expense". This spec intentionally
> scopes date-filter work as a Step 07 profile enhancement that ships on its own
> branch (`feature/date-filter-for-profile-page`) before the Add Expense route
> is wired up. If the roadmap is tightened in a future GEMINI.md revision, this
> step may be renumbered. The implementation does **not** conflict with Step 7
> "Add expense" work.

---

## Depends on

- **Step 1** — `db.py` (`get_db`) must be complete.
- **Step 2** — User registration (users table must exist).
- **Step 3** — Login / session must be in place (`login_required` decorator).
- **Step 4** — Profile page (`/profile` route + `profile.html` + `profile.css`)
  must be fully implemented, as this spec modifies all three.
- **Step 5 / 6** — `database/queries.py` with `get_summary_stats`,
  `get_category_breakdown`, and `get_recent_transactions` must accept optional
  date-range parameters (new in this step).

---

## Routes

- `GET /profile` — accepts optional query params `date_from`, `date_to`, and
  `preset` — scopes stats and transaction history to the given window — logged-in
  only.

No new routes are added; the existing `/profile` route is extended.

---

## Reuses

- `database/db.py` — `get_db()` — all query helpers call it internally.
- `database/queries.py` — `get_summary_stats(user_id)` → extended to accept
  `date_from=None, date_to=None`; `get_category_breakdown(user_id)` → same
  extension; `get_recent_transactions(user_id, limit)` → same extension.
- `app.py` — `login_required` decorator — applied unchanged to `/profile`.
- `app.py` — `get_user_by_id(user_id)` (from `database.queries`) — called
  unchanged; user identity does not change with date filter.

> **Scope exclusion — user info card:** `get_user_by_id`, initials computation,
> and `member_since` are **never** filtered by date. The user info card (avatar,
> name, email, member-since badge) always shows all-time user data regardless of
> the active filter. Only `get_summary_stats`, `get_category_breakdown`, and
> `get_recent_transactions` receive the date-range parameters.
- `app.py` — `inr` Jinja2 template filter — used in profile template for ₹
  formatting.
- `templates/profile.html` — modified in-place; the stats grid and (optionally)
  recent-transactions table are already rendered and just receive new template
  variables.
- `static/css/profile.css` — extended with filter-bar component classes; all
  existing card, badge, and stat classes reused as-is.
- `static/css/style.css` — CSS custom properties (`--accent`, `--ink`,
  `--border`, `--radius-sm`, `--radius-md`, `--paper-card`, `--border-soft`,
  `--ink-muted`, `--font-body`) used in new filter-bar styles.

---

## Database changes

No new tables or columns. The `expenses.date` column (type `TEXT`,
ISO-8601 `YYYY-MM-DD`) already supports `BETWEEN ? AND ?` comparisons.

All filtering is applied at query time inside `database/queries.py` using
parameterised `WHERE date BETWEEN ? AND ?` clauses appended to the existing
`WHERE user_id = ?` condition.

**`get_recent_transactions` — limit vs. filter order:** the `LIMIT` clause
applies *after* the date filter. The function returns the N most recent
transactions **within** the date window, not N records from all time.

---

## Templates

### Modify: `templates/profile.html`

1. Add a `{% block head %}` link to `profile.css` (already present — no change).
2. Insert a **filter bar** `<section class="filter-bar">` between the page
   heading and the stats grid. The bar contains:
   - A `<form method="GET" action="{{ url_for('profile') }}">` wrapping all
     filter controls so the page degrades gracefully without JS.
   - Quick-pick preset `<button>` elements (This Month, Last Month, Last 3
     Months, Last 6 Months, This Year, All Time). Each button submits the form
     with a hidden `preset` input.
   - A custom range sub-section with two `<input type="date">` fields
     (`date_from`, `date_to`) and an "Apply" `<button type="submit">`.
   - A "Clear" link (`<a href="{{ url_for('profile') }}">`) that resets to the
     all-time view.
3. Update the stats grid to display the active filter label as a small
   `<p class="filter-active-label">` above the grid. The exact string for each
   state is defined in the table below.
4. Pass the currently active `date_from`, `date_to`, and `preset` values back
   into the template so the active preset button is highlighted and the date
   inputs are pre-filled.

### "Showing:" label format

`app.py` must compute a `filter_label` string and pass it to the template.
The template renders it verbatim inside `<p class="filter-active-label">`.

| Active state | `filter_label` value |
|---|---|
| No filter / `all_time` | `"Showing: All Time"` |
| `this_month` | `"Showing: This Month"` |
| `last_month` | `"Showing: Last Month"` |
| `last_3_months` | `"Showing: Last 3 Months"` |
| `last_6_months` | `"Showing: Last 6 Months"` |
| `this_year` | `"Showing: This Year"` |
| Custom range | `"Showing: {date_from} to {date_to}"` (ISO dates as-is, e.g. `"Showing: 2026-01-01 to 2026-03-31"`) |

### JavaScript decision

**Do not add any JavaScript for this feature.** The filter bar is a plain
HTML `<form method="GET">` only. Users must click "Apply" (custom range) or
activate a preset button (which submits the form via its `type="submit"`
behaviour). No auto-submit on preset selection, no `fetch`, no DOM
manipulation. This keeps the implementation scope tight and the page
accessible. JS enhancement can be added in a later step if desired.

### No new templates.

---

## Files to change

| File | What changes |
|---|---|
| `app.py` | `/profile` route: parse `date_from`, `date_to`, `preset` from query string; compute date range from preset using `datetime`; pass range to query helpers; pass filter state to template. |
| `database/queries.py` | `get_summary_stats`, `get_category_breakdown`, `get_recent_transactions` — add optional `date_from=None, date_to=None` params; append `AND date BETWEEN ? AND ?` when both are provided. |
| `templates/profile.html` | Add filter bar `<section>` above stats grid; add active-filter label; wire form values from template variables. |
| `static/css/profile.css` | Add `.filter-bar`, `.filter-presets`, `.filter-preset-btn`, `.filter-preset-btn.active`, `.filter-custom-range`, `.filter-date-input`, `.filter-apply-btn`, `.filter-clear-link`, `.filter-active-label` component styles. |
| `tests/test_profile.py` | Add tests for date-filtered `/profile` responses (see Definition of Done). |

---

## Files to create

None — all changes are to existing files.

---

## New dependencies

No new dependencies.

---

## Rules for implementation

- No SQLAlchemy or ORMs — raw `sqlite3` with `get_db()` only.
- Parameterised queries only — never use f-strings or `.format()` to build SQL
  with user-supplied values.
- Passwords are not touched in this step.
- Use CSS variables (`--accent`, `--border`, etc.) — never hardcode hex values
  in new CSS rules.
- All templates extend `base.html`.
- Date arithmetic (computing preset ranges) must use Python's `datetime` /
  `date` stdlib only — no third-party date libraries.
- Preset resolution happens in `app.py`, not in `db.py` — keep `db.py` as a
  pure data-access layer.
- `date_from` and `date_to` passed to query helpers are always ISO strings
  (`YYYY-MM-DD`) or `None`; the helpers must not parse or transform them
  further.
- The filter form must use `method="GET"` so filtered URLs are bookmarkable.
- Always use `₹` — never `"Rs."` or `"INR"`.
- **No JavaScript** — the filter bar is a plain HTML form. Do not add any JS
  to `profile.html`, `main.js`, or anywhere else for this feature.
- `get_user_by_id`, initials, and `member_since` must **never** receive
  date-range arguments — they are always all-time values.
- `get_recent_transactions` `LIMIT` applies **after** date filtering.

---

## Definition of done

### Query-helper unit tests (in-memory SQLite, `tests/test_profile.py`)

Seed the test DB with these fixed expenses for user `42` before running
query-helper tests:

| id | date | category | amount | description |
|---|---|---|---|---|
| 1 | `2026-06-01` | Food | 1200.00 | June grocery |
| 2 | `2026-06-15` | Bills | 800.00 | June electricity |
| 3 | `2026-05-10` | Travel | 500.00 | May metro |
| 4 | `2026-03-20` | Shopping | 300.00 | March clothing |

Total all-time = **₹2,800.00**, 4 transactions.

| Function | Scenario | Expected |
|---|---|---|
| `get_summary_stats` | `date_from=None, date_to=None` | `total_spent=2800.00`, `transaction_count=4`, `top_category="Food"` |
| `get_summary_stats` | `date_from="2026-06-01", date_to="2026-06-30"` | `total_spent=2000.00`, `transaction_count=2`, `top_category="Food"` |
| `get_summary_stats` | `date_from="2026-06-01", date_to=None` | falls back to all-time: `total_spent=2800.00`, `transaction_count=4` |
| `get_summary_stats` | `date_from=None, date_to="2026-06-30"` | falls back to all-time: `total_spent=2800.00`, `transaction_count=4` |
| `get_summary_stats` | `date_from="2026-05-01", date_to="2026-05-31"` | `total_spent=500.00`, `transaction_count=1`, `top_category="Travel"` |
| `get_category_breakdown` | `date_from="2026-06-01", date_to="2026-06-30"` | two rows: Food 1200.00 (60%), Bills 800.00 (40%) |
| `get_category_breakdown` | `date_from=None, date_to=None` | four rows totalling 2800.00 |
| `get_recent_transactions` | `date_from="2026-06-01", date_to="2026-06-30", limit=10` | 2 rows, ordered by date DESC (id=2 first, then id=1) |
| `get_recent_transactions` | `date_from="2099-01-01", date_to="2099-12-31"` | empty list `[]` |

### Route integration tests

- [ ] `GET /profile` (no params) returns HTTP 200, contains `"Showing: All Time"`.
- [ ] `GET /profile?preset=this_month` returns HTTP 200, contains `"Showing: This Month"`.
- [ ] `GET /profile?preset=last_month` returns HTTP 200, contains `"Showing: Last Month"`.
- [ ] `GET /profile?preset=last_3_months` returns HTTP 200, contains `"Showing: Last 3 Months"`.
- [ ] `GET /profile?preset=last_6_months` returns HTTP 200, contains `"Showing: Last 6 Months"`.
- [ ] `GET /profile?preset=this_year` returns HTTP 200, contains `"Showing: This Year"`.
- [ ] `GET /profile?date_from=2026-01-01&date_to=2026-03-31` returns HTTP 200, contains `"Showing: 2026-01-01 to 2026-03-31"`.
- [ ] `GET /profile?date_from=2026-06-01` (no `date_to`) returns HTTP 200, contains `"Showing: All Time"` (partial range rejected).
- [ ] `GET /profile?preset=bogus_value` returns HTTP 200, contains `"Showing: All Time"`.
- [ ] An active preset renders `.filter-preset-btn.active` class on the matching button.
- [ ] Custom `date_from` / `date_to` inputs are pre-filled in the form when present in query string.
- [ ] The "Clear" anchor href is exactly `/profile` (no query string).
- [ ] The user info card (name, email, member-since) is present and unchanged regardless of filter.
- [ ] `pytest -v` passes with zero failures.
