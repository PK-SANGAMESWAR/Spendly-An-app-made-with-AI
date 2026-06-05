# Spec: Registration

## Overview

Step 2 adds user account creation to Spendly. A visitor fills in their
full name, email address, and password; the server validates the input,
hashes the password with Werkzeug, inserts a new row into the `users`
table, and redirects the user to the login page with a success flash
message. If the email is already taken, or any field is blank/invalid,
the form is re-displayed with a descriptive error flash. This is the
entry point for all authenticated functionality in the app.

---

## Depends on

- **Step 1 — Database setup** (`get_db`, `init_db`, `seed_db` must be
  working and the `users` table must exist).

---

## Routes

- `GET  /register` — render the registration form — **public**
- `POST /register` — process form submission, create user, redirect — **public**

> The existing `GET /register` stub in `app.py` already renders
> `register.html`. It must be upgraded to support the POST method.

**Already-logged-in guard:** At the top of the `register()` view,
before any other logic, check `session.get("user_id")`. If it is set,
`redirect(url_for("dashboard"))` immediately — logged-in users have no
business on the registration page.

---

## Database changes

No new tables or columns required. The `users` table introduced in
Step 1 already has every field needed:

| Column          | Used by registration |
|-----------------|----------------------|
| `name`          | ✅ from form          |
| `email`         | ✅ from form (UNIQUE) |
| `password_hash` | ✅ Werkzeug hash       |
| `created_at`    | ✅ auto default        |

New helper function to add in `database/db.py`:

- `create_user(name, email, password_hash)` — inserts one row into
  `users`, returns the new `id`. Raises `sqlite3.IntegrityError` on
  duplicate email (caller handles this).

- `get_user_by_email(email)` — returns a `sqlite3.Row` for the user
  matching the given email, or `None`. Used later for login (Step 3),
  but define it here as part of the user data-access surface.

---

## Templates

- **Modify:** `templates/register.html`
  - Already exists as a static scaffold.
  - Set `{% block title %}Spendly — Create Account{% endblock %}`.
  - The page `<h1>` must read **"Create your account"** (DM Serif Display,
    consistent with other Spendly auth pages).
  - Add a proper `<form method="POST" action="/register">` with fields:
    - Full Name (`name="name"`, type `text`, required)
    - Email (`name="email"`, type `email`, required)
    - Password (`name="password"`, type `password`, required, min 8 chars)
    - Confirm Password (`name="confirm_password"`, type `password`, required)
    - Terms acceptance checkbox (`name="agree_terms"`, required)
    - Submit button
  - Include `{{ url_for('terms') }}` and `{{ url_for('privacy') }}` links
    in the terms checkbox label.
  - Flash messages are already rendered by `base.html` — no extra markup
    needed in the template.
  - Load `register.css` in `{% block head %}`.
  - **Re-population on error:** text and email inputs must carry back the
    user's previous input via `value` attributes so they are not wiped on
    a failed submission:
    ```html
    <input type="text"  name="name"  value="{{ name or '' }}">
    <input type="email" name="email" value="{{ email or '' }}">
    ```
    Password fields are intentionally left blank on re-render (standard
    security practice). The route must pass `name=` and `email=` as
    keyword arguments to every `render_template` call — both on GET
    (empty strings) and on POST validation failure (the submitted values).

---

## Files to change

| File | What changes |
|---|---|
| `app.py` | Upgrade `register()` to handle GET + POST; add form validation, DB call, flash messages, redirect |
| `database/db.py` | Add `create_user()` and `get_user_by_email()` functions |
| `templates/register.html` | Add the full `<form>` markup and link to `register.css` |
| `static/css/register.css` | Style the registration form (see rules below) |

---

## Files to create

| File | Purpose |
|---|---|
| `static/css/register.css` | Page-scoped styles for the registration form |
| `tests/test_registration.py` | pytest tests for all registration scenarios |

---

## New dependencies

No new dependencies. Uses only:

- `flask` — `request`, `flash`, `redirect`, `url_for`, `session` (already installed)
- `werkzeug.security` — `generate_password_hash` (already installed)
- `sqlite3` — standard library

---

## Rules for implementation

### Python / Flask

- No SQLAlchemy or ORMs — raw `sqlite3` only.
- Parameterised queries only — never string-format SQL.
- Passwords hashed with `werkzeug.security.generate_password_hash`
  before any DB write.
- Server-side validation must check **all** of the following before
  touching the DB:
  1. `name`, `email`, `password`, `confirm_password` are non-empty after
     `.strip()`.
  2. `password == confirm_password`.
  3. `len(password) >= 8`.
  4. `agree_terms` checkbox is checked (value `"on"` in POST data).
- On validation failure: `flash(message, "error")` and re-render the
  form with `render_template("register.html", name=name, email=email)` —
  **never** redirect on failure, because a redirect loses the submitted
  values. Password fields are always passed as empty strings on re-render.
- On duplicate email (`sqlite3.IntegrityError`): flash
  `"An account with that email already exists."` (category `"error"`) and
  re-render with `render_template("register.html", name=name, email=email)`.
- On success: flash `"Account created! Please log in."` (category
  `"success"`) then `redirect(url_for("login"))`.
- On `GET /register`: call `render_template("register.html", name="", email="")`
  so the template always receives both variables.
- Import only what is needed from Flask: add `request`, `flash`,
  `redirect`, `url_for`, `session` to the existing import line in `app.py`.
- Add `import sqlite3` at the top of `app.py` for catching
  `IntegrityError`.
- After a successful registration **do not log the user in**
  automatically — redirect to `/login` (Step 3 handles sessions).

### HTML / Jinja2

- Template must `{% extends "base.html" %}`.
- Use semantic HTML5 — wrap the form in a `<section>` inside `<main>`.
- Load `register.css` in `{% block head %}` — never inline styles.
- Each input must have a matching `<label>` with `for=` attribute.
- Add `autocomplete` attributes: `name="name"`, `email`, `new-password`
  for password fields.

### CSS (`register.css`)

- Use CSS custom properties from `style.css` — **never hardcode hex
  values**.
- The form card should use glassmorphism consistent with the rest of the
  design: `background: var(--glass-bg)`, `backdrop-filter`, border with
  `var(--border-subtle)`.
- Input focus states must use `var(--accent)` for the outline/border.
- Password strength: no JS meter required at this step.
- The form must be responsive — single column on mobile, centred on
  desktop with a `max-width` of `480 px`.
- Always use `₹` if any currency label appears — not `"Rs."` or `"INR"`.

---

## Definition of done

- [ ] `GET /register` returns HTTP 200 and renders the registration form.
- [ ] `GET /register` while logged in redirects to `/dashboard` (HTTP 302).
- [ ] The page `<title>` is `Spendly — Create Account`.
- [ ] The page `<h1>` reads "Create your account".
- [ ] Submitting the form with all valid fields creates a new user row in
      `users` and redirects to `/login` with a success flash.
- [ ] Submitting with a blank name, email, or password re-renders the
      form with an error flash — no DB write occurs.
- [ ] Submitting with mismatched passwords re-renders the form with an
      error flash.
- [ ] Submitting with a password shorter than 8 characters re-renders
      with an error flash.
- [ ] Submitting without checking the terms checkbox re-renders with an
      error flash.
- [ ] Submitting with an already-registered email re-renders with
      `"An account with that email already exists."`.
- [ ] After a failed submission the name and email fields retain the
      values the user typed; password fields are blank.
- [ ] Passwords are stored as Werkzeug hashes — plaintext is never
      written to the DB.
- [ ] `create_user()` in `db.py` is covered by at least one unit test
      using an in-memory SQLite DB.
- [ ] `tests/test_registration.py` passes with `pytest -v` and covers
      all scenarios above.
- [ ] The registration page looks consistent with the Spendly design
      system (DM Serif Display heading, DM Sans body, glassmorphism card).
