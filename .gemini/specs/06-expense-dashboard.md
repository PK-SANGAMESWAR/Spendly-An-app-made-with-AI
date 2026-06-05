# Spec: Expense Dashboard

## Overview

Step 6 replaces the placeholder `/dashboard` stub with a fully functional,
data-driven central workspace. Every logged-in user lands here after login.
The page aggregates four summary stats, renders a category breakdown, lists
paginated transaction history, and supports description search and category
filtering. Edit and delete action links are wired to the routes that Steps 7–9
will implement — they appear on every row now so the template needs no changes
later. This is the most complex route in the project so far; it introduces
`get_filtered_expenses` and `get_filtered_expenses_count` as new query helpers
and extends the existing stats surface with `get_extended_summary_stats`.

---

## Depends on

- **Step 1 — Database setup** (`get_db()`, `expenses` table, `seed_db()` must exist)
- **Step 2 — Registration** (seed user and real users must be creatable)
- **Step 3 — Login / Logout** (`session["user_id"]` set on login; `@login_required` in place)
- **Step 4 — Profile UI** (`base.html` navbar already renders logged-in state)
- **Step 5 — Backend connection** (`database/queries.py` exists; `get_category_breakdown`,
  `get_user_by_id` already implemented and tested)

---

## Routes

- `GET /dashboard` — render the dashboard — **logged-in only**

  | Query parameter | Type | Default | Description |
  |---|---|---|---|
  | `q` | string | `""` | Filter expenses by description (case-insensitive LIKE) |
  | `category` | string | `""` | Filter by exact category name |
  | `page` | integer | `1` | Pagination page number |

  **Parameter validation rules (apply before any DB call):**
  - `q` and `category`: strip whitespace; treat empty string as no filter.
  - `page`: parse with `int(request.args.get("page", 1))`; if conversion raises
    `ValueError` or result is `<= 0`, set `page = 1`.
  - If `page` exceeds total pages (calculated from count), clamp to the last
    valid page. If there are zero results, clamp to `1`.

---

## Reuses

- `database/db.py` — `get_db()` — SQLite connection (called inside query helpers)
- `database/queries.py` — `get_user_by_id(user_id)` — user name for the welcome heading
- `database/queries.py` — `get_category_breakdown(user_id)` — category progress bars
  (already implemented in Step 5; do not rewrite)
- `app.py` — `@login_required` — access control decorator (already implemented in Step 4)
- `templates/base.html` — layout, navbar, flash messages, Lucide icon init
- `static/css/style.css` — CSS custom properties, `.badge-*` category classes,
  `.btn-submit`, `.form-input`, glassmorphism card variables

---

## Database changes

No new tables or columns. The `expenses` table already has every required column:

| Column | Used by dashboard |
|---|---|
| `id` | ✅ edit / delete links |
| `user_id` | ✅ WHERE clause on all queries |
| `amount` | ✅ stats + table column |
| `category` | ✅ filter + badge + breakdown |
| `date` | ✅ ORDER BY, table column |
| `description` | ✅ search LIKE, table column |
| `created_at` | ✅ tiebreaker sort |

---

## New query helpers — `database/queries.py`

Add three functions. Do **not** remove or modify `get_summary_stats`,
`get_user_by_id`, `get_recent_transactions`, or `get_category_breakdown`.

### `get_extended_summary_stats(user_id)`

Returns a dict:
```python
{
    "total_spent": float,        # SUM(amount) for this user; 0.0 if no expenses
    "transaction_count": int,    # COUNT(*); 0 if no expenses
    "top_category": str,         # category with highest SUM(amount); "—" if no expenses
    "avg_spent": float           # total_spent / transaction_count; 0.0 if no expenses
}
```
SQL pattern:
```sql
SELECT
    COALESCE(SUM(amount), 0)   AS total_spent,
    COUNT(*)                   AS transaction_count,
    COALESCE(AVG(amount), 0)   AS avg_spent
FROM expenses
WHERE user_id = ?
```
Top category: separate query using `GROUP BY category ORDER BY SUM(amount) DESC LIMIT 1`.

### `get_filtered_expenses(user_id, search_query="", category="", limit=10, offset=0)`

Returns a list of dicts, each with keys: `id`, `date`, `description`,
`category`, `amount`. Ordered `date DESC, created_at DESC`.

SQL pattern (build conditions list, join with AND):
```python
conditions = ["user_id = ?"]
params = [user_id]
if search_query:
    conditions.append("description LIKE ?")
    params.append(f"%{search_query}%")
if category:
    conditions.append("category = ?")
    params.append(category)
sql = f"SELECT id, date, description, category, amount FROM expenses WHERE {' AND '.join(conditions)} ORDER BY date DESC, created_at DESC LIMIT ? OFFSET ?"
params.extend([limit, offset])
```
Never use string formatting for values — only for the structural JOIN above.

### `get_filtered_expenses_count(user_id, search_query="", category="")`

Same WHERE logic as `get_filtered_expenses` but returns a single integer
(total matching rows). Used to calculate total pages:
```python
total_pages = max(1, math.ceil(count / PAGE_SIZE))
```

---

## Templates

- **Create:** `templates/dashboard.html`
  - `{% block title %}Spendly — Dashboard{% endblock %}`
  - Page `<h1>` reads: `"Welcome back, {{ user.name }}"` (DM Serif Display).
  - Load `dashboard.css` in `{% block head %}`.
  - Four distinct sections in order:

  **Section 1 — Summary stats row**
  Four cards: Total Spent · Total Transactions · Avg Transaction · Top Category.
  Each card has a Lucide icon, label, and value. Currency cards show `₹`.

  **Section 2 — Category breakdown**
  Reuse the progress-bar list pattern from `profile.html`. Pull from
  `categories` context variable (same shape as Step 5).

  **Section 3 — Search and filter bar**
  - Text input: `name="q"`, `value="{{ q }}"`, placeholder `"Search expenses…"`
  - Category dropdown: `name="category"`. Options: all Spendly categories plus
    an empty "All categories" default. Selected option must match `{{ category }}`.
  - Submit button labelled `"Filter"`.
  - If either filter is active, show a `"Clear filters"` link that points to
    `/dashboard` with no query parameters.
  - The `<form method="GET" action="/dashboard">` — GET, not POST, so filters
    are bookmarkable.

  **Section 4 — Transaction table + pagination**
  Table columns: Date · Description · Category (badge) · Amount · Actions.
  - Amount: right-aligned, `₹` formatted to two decimal places with comma
    separator (e.g. `₹1,250.00`).
  - Category: `<span class="badge badge-{{ expense.category | lower }}">`.
  - Actions column: `"Edit"` link → `/expenses/{{ expense.id }}/edit`;
    `"Delete"` link → `/expenses/{{ expense.id }}/delete`.
    Style as small text links, not buttons — Steps 7–9 will wire them up.
  - **Empty state** (no rows): centered `<div>` with a Lucide icon
    (`shopping-bag` if no expenses at all; `search` if filters active),
    a short message, and a CTA button. Two variants:
    - No expenses at all: `"No expenses yet"` + `"Add your first expense"` button → `#` (Step 7).
    - Filters active but no results: `"No results for your search"` + `"Clear filters"` link.
  - **Pagination controls** (only render if `total_pages > 1`):
    - `"← Previous"` → `?q={{ q }}&category={{ category }}&page={{ page - 1 }}`
      (disabled/hidden if `page == 1`).
    - `"Next →"` → `?q={{ q }}&category={{ category }}&page={{ page + 1 }}`
      (disabled/hidden if `page == total_pages`).
    - Page indicator: `"Page {{ page }} of {{ total_pages }}"`.
    - Pagination links must always carry `q` and `category` parameters even
      when empty, so filters persist across pages.

- **Modify:** `templates/base.html` — no structural changes needed; navbar
  already shows Dashboard link for logged-in users (Step 4).

---

## Files to change

| File | What changes |
|---|---|
| `app.py` | Replace placeholder `dashboard()` with full implementation: parse query params, call query helpers, compute pagination, pass context to `dashboard.html`. Add `import math` at top. |
| `database/queries.py` | Add `get_extended_summary_stats`, `get_filtered_expenses`, `get_filtered_expenses_count`. Existing functions untouched. |

---

## Files to create

| File | Purpose |
|---|---|
| `templates/dashboard.html` | Full dashboard template — stats, breakdown, search, table, pagination |
| `static/css/dashboard.css` | Page-scoped styles (see CSS rules below) |
| `tests/test_dashboard.py` | Unit + route tests (see test table below) |

---

## `app.py` route — expected shape

```python
PAGE_SIZE = 10  # module-level constant, above the route

@app.route("/dashboard")
@login_required
def dashboard():
    user_id = session["user_id"]
    # --- parse query params ---
    q        = request.args.get("q", "").strip()
    category = request.args.get("category", "").strip()
    try:
        page = int(request.args.get("page", 1))
        if page <= 0:
            page = 1
    except ValueError:
        page = 1
    # --- query ---
    stats      = get_extended_summary_stats(user_id)
    user       = get_user_by_id(user_id)
    categories = get_category_breakdown(user_id)
    count      = get_filtered_expenses_count(user_id, q, category)
    total_pages = max(1, math.ceil(count / PAGE_SIZE))
    page        = min(page, total_pages)
    offset      = (page - 1) * PAGE_SIZE
    expenses   = get_filtered_expenses(user_id, q, category, PAGE_SIZE, offset)
    return render_template(
        "dashboard.html",
        user=user, stats=stats, categories=categories,
        expenses=expenses, q=q, category=category,
        page=page, total_pages=total_pages,
    )
```

---

## New dependencies

No new dependencies. Add `import math` to `app.py` (standard library).

---

## CSS rules — `dashboard.css`

- Use CSS custom properties from `style.css` — **never hardcode hex values**.
- **Stats row:** 4-column grid on desktop (`grid-template-columns: repeat(4, 1fr)`);
  2-column on tablet; single-column below `480px`.
- **Category breakdown:** reuse the same progress-bar pattern as `profile.css`.
- **Search bar:** full-width flex row — input takes remaining space, dropdown
  fixed width (`160px`), filter button right-aligned.
- **Table:** full-width, `border-collapse: collapse`. Amount column
  `text-align: right`. Category column `white-space: nowrap`.
  Row hover: `background: var(--glass-bg)`. Horizontal scroll wrapper
  (`overflow-x: auto`) below `768px`.
- **Pagination:** centered flex row, `gap: 8px`. Disabled state uses
  `opacity: 0.4; pointer-events: none`.
- **Empty state:** `text-align: center`, `padding: 64px 24px`,
  Lucide icon at `48px`, muted secondary color, CTA button uses `.btn-submit`.
- Breakpoint: single-column stacked layout below `768px`.

---

## Tests — `tests/test_dashboard.py`

### Unit tests (use in-memory SQLite DB, no Flask app)

| Function | Scenario | Expected |
|---|---|---|
| `get_extended_summary_stats` | user with 8 seed expenses | `total_spent=346.24`, `transaction_count=8`, `top_category="Bills"`, `avg_spent≈43.28` |
| `get_extended_summary_stats` | user with no expenses | `{"total_spent": 0.0, "transaction_count": 0, "top_category": "—", "avg_spent": 0.0}` |
| `get_filtered_expenses` | no filters, seed user | list of 8 dicts, ordered newest date first, each has `id/date/description/category/amount` |
| `get_filtered_expenses` | `search_query="coffee"` | only rows where description contains "coffee" (case-insensitive) |
| `get_filtered_expenses` | `category="Food"` | only rows where category is exactly "Food" |
| `get_filtered_expenses` | `limit=3, offset=0` | exactly 3 rows |
| `get_filtered_expenses` | user with no expenses | empty list |
| `get_filtered_expenses_count` | no filters, seed user | `8` |
| `get_filtered_expenses_count` | `category="Bills"` | count of Bills rows only |
| `get_filtered_expenses_count` | user with no expenses | `0` |

### Route tests (use Flask test client with logged-in session)

| Request | Expected |
|---|---|
| `GET /dashboard` (unauthenticated) | 302 → `/login` |
| `GET /dashboard` (authenticated, seed user) | 200; response contains `"Welcome back, Demo User"` |
| `GET /dashboard` (authenticated, seed user) | response contains `"₹346.24"` and `"Bills"` |
| `GET /dashboard?q=nonexistent` | 200; empty state renders; no crash |
| `GET /dashboard?category=Food` | 200; only Food rows in response |
| `GET /dashboard?page=abc` | 200; defaults to page 1; no crash |
| `GET /dashboard?page=99999` | 200; clamps to last valid page; no crash |
| `GET /dashboard` (new user, no expenses) | 200; "no expenses" empty state visible |

---

## Rules for implementation

### Python / Flask

- No SQLAlchemy or ORMs — raw `sqlite3` only.
- Parameterised queries only — never string-format values into SQL.
- `PAGE_SIZE = 10` as a module-level constant in `app.py`.
- Currency formatting: `f"₹{amount:,.2f}"` — use this pattern in the
  Jinja template directly: `₹{{ "%.2f"|format(expense.amount) }}` won't
  produce comma separators; pass a pre-formatted string from Python or add
  a Jinja filter. Recommended: add a `format_currency` filter to the Flask app:
  ```python
  @app.template_filter("inr")
  def inr_filter(value):
      return f"₹{value:,.2f}"
  ```
  Use as `{{ expense.amount | inr }}` in templates.
- Add `import math` to `app.py`.
- Use section banners in `app.py` as per CLAUDE.md conventions.

### HTML / Jinja2

- Template must `{% extends "base.html" %}`.
- Use semantic HTML5 (`<section>`, `<table>`, `<thead>`, `<tbody>`).
- Search form: `method="GET"` — never POST for filters.
- Category badge: `class="badge badge-{{ expense.category | lower }}"`.
- Pagination links must carry all active filters in the query string.
- Load `dashboard.css` in `{% block head %}`.

### CSS

- Follow all rules in `dashboard.css` section above.
- Never hardcode hex values — CSS variables only.
- Always `₹` — never `Rs.` or `INR`.

---

## Definition of done

- [ ] `GET /dashboard` without a session redirects to `/login` (302) with an error flash.
- [ ] `GET /dashboard` as the seed user returns 200 and displays `"Welcome back, Demo User"`.
- [ ] The page `<title>` is `Spendly — Dashboard`.
- [ ] Four stats cards render: Total Spent (`₹346.24`), Total Transactions (`8`), Avg Transaction, Top Category (`Bills`).
- [ ] Category breakdown progress bars render with non-zero widths for the seed user.
- [ ] The transaction table shows 8 rows for the seed user with Date, Description, Category badge, Amount (`₹` formatted with comma separator), and Edit/Delete links.
- [ ] Rows are ordered newest date first.
- [ ] Searching by a description substring filters the table and keeps the search term pre-filled in the input.
- [ ] Filtering by category shows only matching rows; the dropdown retains the selected value.
- [ ] `"Clear filters"` link appears when any filter is active and resets to unfiltered results.
- [ ] If filters match no rows, a friendly empty state renders with a "Clear filters" link — no crash, no blank table.
- [ ] A brand-new user with no expenses sees the "no expenses yet" empty state with a CTA button.
- [ ] Pagination controls appear only when there are more than 10 rows.
- [ ] Pagination links preserve active search and category filters in the query string.
- [ ] `GET /dashboard?page=abc` and `GET /dashboard?page=99999` both return 200 with no crash.
- [ ] All amounts display `₹` with two decimal places and comma thousands separator.
- [ ] Edit links point to `/expenses/<id>/edit`; Delete links point to `/expenses/<id>/delete`.
- [ ] No hex colour values in `dashboard.html` or `dashboard.css`.
- [ ] The page is responsive — stats stack to 2-column on tablet, 1-column on mobile; table scrolls horizontally below `768px`.
- [ ] All tests in `tests/test_dashboard.py` pass with `pytest -v`.
