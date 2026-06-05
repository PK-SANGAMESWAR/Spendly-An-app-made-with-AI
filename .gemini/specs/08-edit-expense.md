---
# Spec: Edit Expense

## Overview
Provide a page and backend to edit an existing expense. Authenticated users can open an edit form pre-filled with the expense data, change fields (amount, category, date, description) and save the update. This allows users to correct mistakes and keep accurate records.

## Depends on
Steps: 01, 05, 06, 07

## Routes
- `GET /expenses/<int:id>/edit` — render the edit form — access: logged-in
- `POST /expenses/<int:id>/edit` — process form submission and persist changes — access: logged-in

If the expense does not exist or does not belong to the current user, respond with a flash message and redirect to `/dashboard`.

## Reuses
- `database/db.py` — `get_db()` — open DB connections and transactions (used by new queries)
- `database/db.py` — `init_db()` / `seed_db()` — schema and demo data (no schema change needed)
- `database/queries.py` — `get_filtered_expenses()` — example of parameterised queries and paging logic (reference)
- `app.py` — existing placeholder route `/expenses/<int:id>/edit` — replace with real GET/POST handlers and reuse `login_required` decorator
- `templates/base.html` — page blocks (`title`, `head`, `content`, `scripts`) — new template must extend this
- `static/css/style.css` — design tokens and variables (use `--radius-*`, `--accent`, etc.)

If any of the above change points are missing, implement the minimal helpers in `database/queries.py` rather than adding DB access logic into route handlers.

## Database changes
No schema changes required. Use the existing `expenses` table. Add query helpers if needed:
- `get_expense_by_id(user_id, expense_id)` — returns expense row or None
- `update_expense(expense_id, user_id, amount, category, date, description)` — parameterised UPDATE

## Templates
- **Create:** `.gemini/specs/templates/edit_expense.html` — render a form with fields: `amount`, `category` (select), `date` (ISO), `description` (textarea), and CSRF-safe submission via POST. (Actual path: `templates/edit_expense.html`)
- **Modify:** `templates/dashboard.html` — add an "Edit" link for each expense row pointing to `/expenses/<id>/edit` (if not present)

## Files to change
- `app.py` — replace the placeholder `/expenses/<int:id>/edit` route with GET and POST handlers (use `login_required`)
- `database/queries.py` — add `get_expense_by_id()` and `update_expense()` helpers
- `templates/dashboard.html` — add edit link/button per expense row

## Files to create
- `templates/edit_expense.html` — edit form extending `base.html`
- `static/css/edit_expense.css` (optional) — small form styles; prefer reusing `style.css` tokens. If created, import it in the template's `head` block.

## New dependencies
No new dependencies.

## Rules for implementation
- No SQLAlchemy or ORMs
- Parameterised queries only (use `?` placeholders)
- Passwords must continue to be hashed with `werkzeug` (no change for this feature)
- Use CSS variables from `static/css/style.css` — never hardcode hex values
- All templates must extend `base.html`

## Definition of done
- `GET /expenses/<id>/edit` returns `200` and pre-populates the form for the expense owner
- `GET /expenses/<id>/edit` returns a redirect (and flash) when unauthenticated or when the expense is not owned by the user
- `POST /expenses/<id>/edit` validates inputs (amount positive number, category non-empty, date valid ISO) and updates the DB with a parameterised `UPDATE` statement
- After successful POST, user is redirected to `/dashboard` with a `success` flash message
- Add unit tests covering: GET owned expense (200), GET unauthenticated (302), POST successful update (redirect + DB row changed), POST invalid input (shows error, does not update)
- All new/modified templates extend `base.html` and use CSS variables

---
