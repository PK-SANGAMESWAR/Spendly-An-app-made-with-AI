# Spec: Profile Page

## Overview
This feature replaces the `/profile` stub with a fully designed profile page showing static, hardcoded data. The goal is to establish the complete UI layout — user info card, transaction history table, summary stats, and category breakdown — before any real database queries are wired up in Step 5. Building the UI first lets the team validate the design in isolation and ensures the templates are ready for the backend-connection step.

## Depends on
- Step 1: Database setup (schema must exist)
- Step 2: Registration (user accounts must be creatable)
- Step 3: Login + Logout (session must be set; `/profile` must be a protected route)

## Routes
- GET /profile — render the profile page — logged-in only (redirect to /login if not authenticated)

## Database changes
No database changes. The existing `users` and `expenses` tables are sufficient.

## Templates
- Create: `templates/profile.html` — full profile page extending `base.html`; contains four sections:
  1. **User info card** — avatar initials, name, email, member-since date formatted as "Month YYYY" (e.g. "June 2026") (all hardcoded)
  2. **Summary stats row** — total spent, number of transactions, top category (hardcoded)
  3. **Transaction history table** — list of recent expenses with date, description, category badge, amount (hardcoded rows)
  4. **Category breakdown** — per-category totals displayed as a simple list or progress-bar rows (hardcoded)

## Files to change
- `app.py` — replace the `/profile` stub with a real view function that:
  - Redirects unauthenticated users to `/login`
  - Passes hardcoded context variables to `profile.html`

## Files to create
- `templates/profile.html`
- `static/css/profile.css` — page-scoped styles for layout, stats, table, badges, progress bars. Responsive: two-column desktop, single-column below 768px.
- `tests/test_profile.py` — covers: unauthenticated redirect, HTTP 200 when logged in, presence of hardcoded data elements in response

## New dependencies
No new dependencies.

## Rules for implementation
- No SQLAlchemy or ORMs — use raw sqlite3 via `get_db()` if any DB call is ever needed
- Parameterised queries only — never string-format SQL
- Passwords hashed with werkzeug (no changes to auth in this step)
- Use CSS variables — never hardcode hex values
- All templates extend `base.html`
- No inline styles
- Create a `@login_required` decorator in `app.py` using `functools.wraps` (import from `functools`) to prevent Flask duplicate endpoint AssertionErrors. If `session.get("user_id")` is absent: flash("Please log in to access this page.", "error"), then redirect(url_for("login")). Apply to `/profile` and `/dashboard`.
- All data passed to the template must be hardcoded Python dicts/lists in `app.py` — no DB queries in this step. The route must pass these exact hardcoded structures:
  - user: `{"name": "Demo User", "email": "demo@spendly.com", "created_at": "2026-06-01 10:30:00"}`
  - stats: `{"total_spent": 5200.00, "transaction_count": 8, "top_category": "Food"}`
  - expenses: list of 3+ dicts with keys: date, description, category, amount
  - categories: list of 3+ dicts with keys: category, amount, percentage
  - initials: computed as `''.join(w[0].upper() for w in user['name'].split()[:2])`
  - member_since: formatted using strptime/strftime as "June 2026"
- Category badges must use a CSS class, not inline colour styles. Badge classes: `.badge-food`, `.badge-travel`, `.badge-bills`, `.badge-shopping`, `.badge-health`, `.badge-entertainment`, `.badge-other`

## Definition of done
- [ ] Visiting `/profile` without being logged in redirects to `/login`
- [ ] Visiting `/profile` while logged in returns HTTP 200
- [ ] The page displays a user info card with a name and email
- [ ] The page displays at least three summary stat values (e.g. total spent, transaction count, top category)
- [ ] The page displays a transaction history table with at least three hardcoded rows
- [ ] The page displays a category breakdown section with at least three categories
- [ ] The navbar shows the logged-in state (username + logout link)
- [ ] No hex colour values appear in `profile.html` or `profile.css` — only CSS variables