# Spec: Login and Logout

## Overview

Step 3 adds session-based authentication to Spendly. A registered user
visits `/login`, submits their email and password, and — if the
credentials are valid — is granted a session (`session["user_id"]`) and
redirected to the dashboard. An invalid credential shows an error flash
and re-renders the form with the email field pre-populated (password is
always cleared). The `/logout` route clears the session and redirects
to the landing page. Together these two routes form the authentication
boundary that every Step 4–9 feature depends on.

---

## Depends on

- **Step 1 — Database setup** (`get_db`, `init_db`, `seed_db`, `get_user_by_email`
  must be implemented and the `users` table must exist).
- **Step 2 — Registration** (there must be at least one user in the DB
  to test login; `get_user_by_email` defined in Step 2 is reused here).

---

## Routes

- `GET  /login`  — render the login form — **public**
- `POST /login`  — validate credentials, set session, redirect — **public**
- `GET  /logout` — clear session, redirect to landing — **no access restriction** (safe to call whether or not a session exists)

> The existing `GET /login` stub in `app.py` already renders `login.html`
> (GET only). It must be upgraded to accept POST as well.
> The existing `GET /logout` stub returns a plain string and must be replaced.

**Already-logged-in guard (login route):** At the top of `login()`,
before any other logic, check `session.get("user_id")`. If set,
`redirect(url_for("dashboard"))` immediately.

---

## Reuses

- `database/db.py` — `get_db()` — opens an SQLite connection (used indirectly via helpers)
- `database/db.py` — `get_user_by_email(email)` — returns a `sqlite3.Row` or `None`; used to look up the user during POST /login
- `app.py` — `session` — already imported from Flask; used to set/clear `user_id`
- `app.py` — `url_for("dashboard")` — redirect destination after successful login
- `app.py` — `url_for("landing")` — redirect destination after logout
- `templates/base.html` — flash message rendering is already present; no extra markup needed
- `templates/login.html` — already exists as a static scaffold; will be upgraded with the full form
- `static/css/style.css` — auth component classes already defined:
  - `.auth-section`, `.auth-container`, `.auth-header`, `.auth-title`, `.auth-subtitle`
  - `.auth-card`, `.form-group`, `.form-input`, `.btn-submit`
  - `.auth-switch`, `.auth-error`
  - CSS custom properties: `--accent`, `--ink`, `--paper`, `--border`, `--radius-sm`, `--radius-md`, `--auth-width`, `--font-display`, `--font-body`

---

## Database changes

No new tables or columns required. The `users` table from Step 1 already
contains every field needed for credential verification:

| Column          | Used by login        |
|-----------------|----------------------|
| `id`            | ✅ stored in session  |
| `email`         | ✅ lookup key         |
| `password_hash` | ✅ Werkzeug check     |

No new helper functions are needed in `database/db.py`; `get_user_by_email`
(added in Step 2) is sufficient.

---

## Templates

- **Modify:** `templates/login.html`
  - Already exists as a static scaffold.
  - Set `{% block title %}Spendly — Sign In{% endblock %}`.
  - The page `<h1>` must read **"Welcome back"** (DM Serif Display).
  - Add a sub-heading: `"Sign in to your Spendly account"` styled as `.auth-subtitle`.
  - Add `<form method="POST" action="/login">` with fields:
    - Email (`name="email"`, type `email`, required, `autocomplete="email"`)
    - Password (`name="password"`, type `password`, required, `autocomplete="current-password"`)
    - Submit button labelled **"Sign in"**
  - Re-populate the email field on re-render via `value="{{ email or '' }}"`.
  - Password field is always blank on re-render.
  - Include a "Don't have an account? **Create one**" link to `/register`
    below the form card, using the `.auth-switch` class.
  - Load `login.css` in `{% block head %}`.
  - Flash messages are rendered by `base.html` — no extra markup needed.

- **No other templates need modification.**

---

## Files to change

| File | What changes |
|---|---|
| `app.py` | Upgrade `login()` to handle GET + POST; add credential check, session write, flash, redirect. Replace `logout()` stub with real session-clearing logic. Add `check_password_hash` to the werkzeug import line. |
| `templates/login.html` | Add the full `<form>` markup, page title, headings, and link to `login.css` |

---

## Files to create

| File | Purpose |
|---|---|
| `static/css/login.css` | Page-scoped styles for the login form (minimal — most styles come from `style.css`) |
| `tests/test_login.py` | pytest tests for all login and logout scenarios |

---

## New dependencies

No new dependencies. Uses only:

- `flask` — `request`, `flash`, `redirect`, `url_for`, `session` (already imported in `app.py`)
- `werkzeug.security` — `check_password_hash` (already installed; add to existing import line)
- `database.db` — `get_user_by_email` (add to existing import line in `app.py`)

---

## Rules for implementation

### Python / Flask

- No SQLAlchemy or ORMs — raw `sqlite3` only.
- Parameterised queries only — never string-format SQL.
- Passwords verified with `werkzeug.security.check_password_hash` — never
  compare plaintext.
- `login()` view logic:
  1. **GET:** render `login.html` with `email=""`.
  2. **POST — collect:** `email = request.form.get("email", "").strip()`,
     `password = request.form.get("password", "")`.
  3. **POST — validate (stop at first failure):**
     - Both fields must be non-empty; if not: `flash("Email and password are required.", "error")`,
       re-render with `render_template("login.html", email=email)`.
  4. **POST — look up user:** call `get_user_by_email(email)`.
     - If `None` **or** `check_password_hash(user["password_hash"], password)` is `False`:
       `flash("Invalid email or password.", "error")`, re-render with
       `render_template("login.html", email=email)`.
       Use a **single generic message** for both cases (no user enumeration).
  5. **POST — success:** `session.clear()`, then `session["user_id"] = user["id"]`,
     `session["user_name"] = user["name"]`, `flash("Welcome back, {name}!", "success")`,
     `redirect(url_for("dashboard"))`.
- `logout()` view logic:
  - Call `session.clear()`.
  - `flash("You have been signed out.", "info")`.
  - `redirect(url_for("landing"))`.
- **Do NOT apply a `login_required` decorator to `logout()`.** That decorator does not exist yet — it is introduced in Step 4. Applying it now would cause a `NameError` at import time. `session.clear()` is safe to call on an empty or non-existent session; no guard is needed.
- Import `check_password_hash` from `werkzeug.security` (add to the existing import line).
- Import `get_user_by_email` from `database.db` (add to the existing import line).
- Use `session.clear()` instead of `session.pop(...)` — clears all keys atomically.
- Do **not** log the user in automatically after registration (Step 2 already enforces this).

### HTML / Jinja2

- Template must `{% extends "base.html" %}`.
- Use semantic HTML5 — wrap the form in a `<section class="auth-section">` inside the
  `{% block content %}` block; the form itself lives inside `<div class="auth-card">`.
- Load `login.css` in `{% block head %}` — never inline styles.
- Each input must have a matching `<label>` with a `for=` attribute.
- Add `autocomplete` attributes: `email` for the email input, `current-password`
  for the password input.

### CSS (`login.css`)

- Use CSS custom properties from `style.css` — **never hardcode hex values**.
- The auth component classes from `style.css` handle layout, card, inputs, and
  button; `login.css` should only add page-specific overrides if needed (e.g.,
  an icon, a decorative rule, or minor spacing adjustments).
- The form must be responsive — single column on mobile, centred on desktop with
  `max-width: var(--auth-width)`.
- Always use `₹` if any currency label appears — not `"Rs."` or `"INR"`.

---

## Definition of done

- [ ] `GET /login` returns HTTP 200 and renders the login form.
- [ ] `GET /login` while already logged in redirects to `/dashboard` (HTTP 302).
- [ ] The page `<title>` is `Spendly — Sign In`.
- [ ] The page `<h1>` reads "Welcome back".
- [ ] Submitting the form with valid credentials sets `session["user_id"]` and
      redirects to `/dashboard` (HTTP 302).
- [ ] After successful login a success flash message containing the user's name
      is displayed.
- [ ] Submitting with an unrecognised email re-renders the form with
      `"Invalid email or password."` — the email field is pre-populated,
      the password field is blank.
- [ ] Submitting with the correct email but wrong password re-renders the form
      with the same `"Invalid email or password."` message (no user enumeration).
- [ ] Submitting with blank email or password re-renders with
      `"Email and password are required."`.
- [ ] `GET /logout` clears the session and redirects to `/` (HTTP 302).
- [ ] `GET /logout` works even if the user is not logged in (no crash).
- [ ] After logout an info flash message `"You have been signed out."` is visible
      on the landing page.
- [ ] Passwords are verified using `check_password_hash` — plaintext comparison
      never occurs.
- [ ] `tests/test_login.py` passes with `pytest -v` and covers all scenarios above.
- [ ] The login page looks consistent with the Spendly design system
      (DM Serif Display heading, DM Sans body, auth-card layout from `style.css`).
