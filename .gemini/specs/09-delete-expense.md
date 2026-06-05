---
spec: delete-expense
---
# Spec: Delete Expense

## Overview
Provide a secure way to delete an existing expense. Authenticated users can click a "Delete" link on their dashboard, which brings them to a confirmation page. Confirming the deletion sends a POST request that deletes the expense from the SQLite database. This completes the CRUD functionality for expenses and allows users to manage their transaction list.

## Depends on
Steps: 01, 05, 06, 08

## Routes
- `GET /expenses/<int:id>/delete` — render delete confirmation page — access: logged-in
- `POST /expenses/<int:id>/delete` — delete the expense and redirect — access: logged-in

If the expense does not exist or does not belong to the current user, respond with a flash message "Expense not found." and redirect to `/dashboard`.

## Reuses
- `database/db.py` — `get_db()` — open DB connections and transactions
- `database/queries.py` — `get_expense_by_id(user_id, expense_id)` — fetch details of the expense to verify ownership and display on confirmation page. Note: `get_expense_by_id(user_id, expense_id)` must be implemented in Step 08 before this step. If it doesn't exist in `database/queries.py` or is not fully functional, add it here.
- `app.py` — placeholder route `/expenses/<int:id>/delete` — replace with real GET/POST handlers and reuse `login_required` decorator
- `templates/base.html` — page blocks (`title`, `head`, `content`, `scripts`) — new template must extend this
- `static/css/style.css` — design tokens and variables

## Database changes
No schema changes required. Use the existing `expenses` table. Add a query helper:
- `delete_expense(user_id, expense_id)` — runs parameterised `DELETE` statement, returns rowcount (number of rows deleted)

## Templates
- **Create:** `templates/delete_expense.html` — confirmation page that displays the expense details (date, description, category, amount) and contains a form to confirm deletion.
  - Page `<title>` block must set: `{% block title %}Spendly — Delete Expense{% endblock %}`
  - The `<h1>` text must be: "Delete Expense"
  - The confirmation question must be: "Are you sure you want to delete this expense?"
  - The confirm button label must be: "Delete"
  - The cancel link must point back to `/dashboard` with label "Cancel"
  - The form structure: `<form method="POST" action="/expenses/{{ expense.id }}/delete">`
- **Modify:** `templates/dashboard.html` — ensure the "Delete" link points to `/expenses/<id>/delete`.

## Files to change
- `app.py` — replace the placeholder `/expenses/<int:id>/delete` route with GET and POST handlers (use `login_required`)
- `database/queries.py` — add `delete_expense()` helper
- `templates/dashboard.html` — verify delete link points to `delete_expense`

## Files to create
- `templates/delete_expense.html` — delete confirmation page extending `base.html`
- `static/css/delete_expense.css` (optional) — page-specific styles for confirmation card

## New dependencies
No new dependencies.

## Rules for implementation
- No SQLAlchemy or ORMs
- Parameterised queries only (use `?` placeholders)
- Passwords must continue to be hashed with `werkzeug`
- Use CSS variables from `static/css/style.css` — never hardcode hex values
- All templates must extend `base.html`

## Definition of done
- `GET /expenses/<id>/delete` returns `200` and displays confirmation page for the owner
- GET confirmation page displays the expense's description, category, amount, and date
- `GET /expenses/<id>/delete` redirects to `/dashboard` with an error flash message "Expense not found." if the expense doesn't exist or doesn't belong to the user
- `POST /expenses/<id>/delete` executes `delete_expense` helper using parameterised `DELETE` and redirects to `/dashboard` with a success flash message "Expense deleted successfully."
- `POST /expenses/<id>/delete` redirects to `/dashboard` with an error flash message "Expense not found." if the expense doesn't exist or doesn't belong to the user
- Unauthenticated requests to GET or POST `/expenses/<id>/delete` redirect to `/login`
- Add unit tests in `tests/test_delete_expense.py` covering:
  - GET delete page for owned expense (200 + shows confirmation text)
  - GET delete page unauthenticated (302)
  - GET delete page for unowned expense (302 + redirects to dashboard)
  - GET delete page for non-existent expense (302)
  - POST delete for owned expense (302 + row is deleted from DB)
  - POST delete for unowned expense (302 + row is NOT deleted from DB)
- All new/modified templates extend `base.html` and use CSS variables
