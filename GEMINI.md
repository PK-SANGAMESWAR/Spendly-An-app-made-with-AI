# GEMINI.md — Spendly Expense Tracker

> **MANDATORY RULE — Read First**
> At the start of **every** prompt, before taking any action, you **must** read this file (`GEMINI.md`) in full using the `view_file` tool. Only then proceed with the user's request. This rule has the highest priority and overrides all other instructions.

---


## 1. Project Overview

**Spendly** is a personal expense-tracking web app for the Indian market (₹/INR). Users log expenses, view category breakdowns, and manage budgets — no spreadsheets needed.

**Purpose:** Step-by-step learning project; features are implemented across Steps 1–9.

**Current Focus:** Step 1 — implementing `database/db.py` (`get_db`, `init_db`, `seed_db`).

**Tech Stack:** Python 3 · Flask 3.x · SQLite (`sqlite3`) · Jinja2 · Vanilla HTML/CSS/JS · Google Fonts (`DM Serif Display` + `DM Sans`) · pytest + pytest-flask

---

## 2. Architecture & Directory Structure

```
expense-tracker/
├── app.py              # Flask app instance + all route definitions
├── requirements.txt    # Pinned dependencies
├── GEMINI.md           # This file
├── database/
│   ├── __init__.py
│   └── db.py           # get_db(), init_db(), seed_db() — SQLite helpers only
├── templates/
│   ├── base.html       # Master layout (navbar, footer, fonts, CSS/JS links)
│   ├── landing.html    # Public marketing page
│   ├── register.html   # Registration form
│   ├── login.html      # Login form
│   ├── terms.html      # Terms & Conditions
│   └── privacy.html    # Privacy Policy
└── static/
    ├── css/
    │   ├── style.css   # Global design system (tokens, navbar, footer, forms)
    │   └── landing.css # Landing-page-only styles
    └── js/
        └── main.js     # Global JS placeholder
```

> Every page extends `base.html` and uses blocks: `title`, `head`, `content`, `scripts`.

---

## 3. Development Commands

```bash
python -m venv venv
venv\Scripts\activate          # Windows — use source venv/bin/activate on mac/Linux
pip install -r requirements.txt
python app.py                  # http://127.0.0.1:5001  (port 5001, debug=True)
pytest                         # Run all tests
pytest tests/test_routes.py -v # Run specific file
```

---

## 4. Coding Conventions & Style Rules

**Python:** PEP 8, 4-space indent, `snake_case`. Use section banners in `app.py`:
```python
# ------------------------------------------------------------------ #
# Section Name                                                        #
# ------------------------------------------------------------------ #
```
Import only what's needed from Flask. Placeholder routes return `"Feature — coming in Step N"`.

**HTML/Jinja2:** Always `{% extends "base.html" %}`. Use semantic HTML5 (`<section>`, `<main>`, etc.). Load page CSS in `{% block head %}`, page JS in `{% block scripts %}` — never inline.

**CSS:** No frameworks (no Bootstrap, no Tailwind). Global tokens in `style.css`; page-specific files named `<page>.css`. Use CSS custom properties. Always use `₹` — never `"Rs."` or `"INR"`.

**JavaScript:** Vanilla JS only. Inline scripts use IIFE pattern (see `landing.html`). Global helpers go in `main.js`.

**Naming:** Routes → `snake_case` · CSS classes → `kebab-case` · Templates → `snake_case.html`

---

## 5. Key Files & Entry Points

| File | Role |
|---|---|
| `app.py` | Main entry point — Flask app + all routes |
| `templates/base.html` | Master layout — modify for sitewide elements |
| `static/css/style.css` | Global design system — extend here, don't override |
| `database/db.py` | SQLite data-access layer only |
| `requirements.txt` | Pinned Python dependencies |

---

## 6. Environment & Dependencies

- **Python 3.10+** required. Always activate `venv\Scripts\activate` first.
- **Dependencies:** `flask==3.1.3` · `werkzeug==3.1.6` · `pytest==8.3.5` · `pytest-flask==1.3.0`
- **`FLASK_SECRET_KEY`** — store in `.env` (gitignored); never hardcode.
- **SQLite DB:** `expense_tracker.db` — auto-generated, gitignored.

---

## 7. Error Handling Conventions

- **Flash messages:** Use `flask.flash(message, category)` for all user-facing feedback. Categories: `success`, `error`, `info`. Render them in `base.html` inside the `<main>` block so every page inherits them automatically.
- **Custom error pages:** Register handlers for `404` and `500` using `@app.errorhandler`. Templates: `templates/404.html` and `templates/500.html` (both extend `base.html`).
- **No bare `abort()` without context:** Always flash a message or set a meaningful HTTP status before redirecting on validation failures.

---

## 8. What NOT to Do

- ❌ No CSS/JS frameworks (Bootstrap, Tailwind, jQuery, React, Vue)
- ❌ No inline `style="..."` attributes — use CSS classes
- ❌ Do not change the server port away from `5001`
- ❌ Do not commit `expense_tracker.db`, `venv/`, or `.env`
- ❌ Do not add UI/route logic to `database/db.py` — data-access only
- ❌ Do not skip `{% extends "base.html" %}` on any template
- ❌ Do not use `"Rs."` or `"INR"` — always use `₹`
- ❌ Do not pin new packages arbitrarily — match existing style and comment the reason

---

## 8. Testing Strategy

**Framework:** pytest + pytest-flask. Tests live in `tests/`, named `test_<feature>.py`.

```bash
pytest -v                                      # All tests, verbose
pytest tests/test_routes.py::test_landing -v   # Single test
```

**What to test:** Route status codes (200/302/404) · DB helpers against `:memory:` · Auth flows (login, logout, register, sessions) · CRUD operations with fixture data.

**Coverage bar:** Every route introduced in a step must have at least one status-code test before that step is considered done. Do not move to the next step with failing or missing tests.

---

## 9. Project-Specific Context

**Step status:**

| Step | Feature | Status |
|---|---|---|
| 0 | Scaffold, landing page, base template | ✅ Done |
| 1 | Database setup (`db.py`) | 🔲 Stub |
| 2 | User registration | 🔲 Template only |
| 3 | Login / Logout | 🔲 Stub |
| 4 | User profile | 🔲 Stub |
| 5–6 | Expense dashboard / listing | 🔲 Not started |
| 7 | Add expense | 🔲 Stub |
| 8 | Edit expense | 🔲 Stub |
| 9 | Delete expense | 🔲 Stub |

**When implementing a step:** replace the placeholder return → create the template → add CSS → implement DB logic in `db.py`.

**Domain:** Indian market, `₹` formatting (e.g., ₹18,240). Categories: Food, Travel, Bills, Shopping, Health, Entertainment, Other. Auth uses Flask sessions + Werkzeug hashing (no JWT/OAuth).

**SQLite rules:** Enable `PRAGMA foreign_keys = ON` per connection. Set `conn.row_factory = sqlite3.Row` in `get_db()`.

**DB migrations:** There is no migration tool — schema is managed entirely inside `init_db()` using `CREATE TABLE IF NOT EXISTS`. When a new step adds a table, add its `CREATE TABLE IF NOT EXISTS` statement to `init_db()`. Do **not** drop and recreate existing tables. There is no `schema.sql` file; `db.py` is the single source of truth for schema. `seed_db()` is for development data only and must be safe to call multiple times (use `INSERT OR IGNORE`).

**Design language:** Brand `◈ Spendly` · Fonts: `DM Serif Display` (headings) + `DM Sans` (body) · Tone: clean, modern, trustworthy. Extend `style.css` — never ad-hoc overrides.
