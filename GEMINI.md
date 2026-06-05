# CLAUDE.md — Spendly Expense Tracker

## 1. Project Overview

**Spendly** is a personal expense-tracking web application built for the Indian market (currency: ₹ / INR). It lets users log expenses, view category breakdowns, and manage their budget — without spreadsheets.

**Purpose:** A step-by-step learning project where core features (auth, database, CRUD) are implemented incrementally across numbered steps (Step 1 through Step 9+).

**Tech Stack:**
- **Backend:** Python 3 · Flask 3.x
- **Database:** SQLite (via Python's built-in `sqlite3`)
- **Templating:** Jinja2 (via Flask)
- **Frontend:** Vanilla HTML + Vanilla CSS + Vanilla JavaScript (no frameworks)
- **Typography:** Google Fonts — `DM Serif Display` (headings) and `DM Sans` (body)
- **Testing:** pytest + pytest-flask

---

## 2. Architecture & Directory Structure

```
expense-tracker/
├── app.py                  # Flask application factory & all route definitions
├── requirements.txt        # Pinned Python dependencies
├── CLAUDE.md               # This file
├── .gitignore
│
├── database/
│   ├── __init__.py
│   └── db.py               # get_db(), init_db(), seed_db() — SQLite helpers
│
├── templates/
│   ├── base.html           # Master layout: navbar, footer, Google Fonts, CSS/JS links
│   ├── landing.html        # Public marketing page (extends base.html)
│   ├── register.html       # User registration form
│   ├── login.html          # User login form
│   ├── terms.html          # Terms and Conditions (static legal page)
│   └── privacy.html        # Privacy Policy (static legal page)
│
└── static/
    ├── css/
    │   ├── style.css       # Global design system: tokens, navbar, footer, forms, utilities
    │   └── landing.css     # Landing-page-only styles (hero, features, CTA, modal)
    └── js/
        └── main.js         # Global JS (currently a placeholder; add global helpers here)
```

> **Template pattern:** Every page extends `base.html` using `{% extends "base.html" %}` and fills `{% block title %}`, `{% block head %}` (for page-specific CSS), `{% block content %}`, and `{% block scripts %}`.

---

## 3. Development Commands

```bash
# 1. Create and activate a virtual environment (first time only)
python -m venv venv
venv\Scripts\activate          # Windows PowerShell
# source venv/bin/activate     # macOS / Linux

# 2. Install dependencies
pip install -r requirements.txt

# 3. Run the development server
python app.py
# App runs at http://127.0.0.1:5001
# debug=True is on — Flask auto-reloads on file save

# 4. Run tests
pytest

# 5. Run a specific test file
pytest tests/test_routes.py -v
```

> The dev server port is **5001** (not the default 5000) — see `app.run(debug=True, port=5001)` in `app.py`.

---

## 4. Coding Conventions & Style Rules

### Python
- Follow **PEP 8** — 4-space indentation, snake_case for variables/functions.
- Use section-comment banners to separate logical blocks in `app.py`:
  ```python
  # ------------------------------------------------------------------ #
  # Section Name                                                        #
  # ------------------------------------------------------------------ #
  ```
- Import only what is used from Flask (`from flask import Flask, render_template, ...`).
- Placeholder routes should return a plain string like `"Feature — coming in Step N"` until the real implementation is added.

### HTML / Jinja2
- All pages **must** extend `base.html`.
- Use semantic HTML5 elements (`<section>`, `<nav>`, `<main>`, `<footer>`, `<article>`).
- Block names to use: `title`, `head`, `content`, `scripts`.
- Page-specific CSS files should be loaded in `{% block head %}`, not inline.
- Page-specific JS should be placed in `{% block scripts %}`, not inline `<script>` tags in `<head>`.

### CSS
- **No frameworks** (no Bootstrap, no Tailwind). All styles are hand-written vanilla CSS.
- Global tokens (colors, fonts, spacing) live in `static/css/style.css`.
- Landing-page-only styles go in `static/css/landing.css`.
- New page-specific CSS files should follow the naming pattern: `<page-name>.css`.
- Use CSS custom properties (`--var-name`) for repeated values.
- Currency amounts must always display with the **₹** symbol (not "Rs." or "INR").

### JavaScript
- Vanilla JS only — no jQuery, no React, no external JS libraries.
- Page-specific inline scripts go in `{% block scripts %}` using an IIFE `(function() { ... }())` pattern to avoid polluting the global scope (see `landing.html` for the reference pattern).
- Global utilities go in `static/js/main.js`.

### Naming
- Route functions: `snake_case` matching the resource name (e.g., `add_expense`, `edit_expense`).
- CSS classes: `kebab-case` (e.g., `hero-badge`, `dash-stat-value`).
- Template files: `snake_case.html` (e.g., `add_expense.html`).

---

## 5. Key Files & Entry Points

| File | Role |
|---|---|
| [`app.py`](app.py) | **Main entry point.** Flask app instance, all routes. Start here. |
| [`templates/base.html`](templates/base.html) | **Master layout.** Navbar, footer, font/CSS/JS imports. Modify to add sitewide elements. |
| [`static/css/style.css`](static/css/style.css) | **Global design system.** Color tokens, typography, navbar, footer, form styles. |
| [`database/db.py`](database/db.py) | **SQLite helpers.** Implement `get_db()`, `init_db()`, `seed_db()` here. |
| [`requirements.txt`](requirements.txt) | Pinned Python dependencies. |

---

## 6. Environment & Dependencies

### Python Version
- **Python 3.10+** is recommended. No Python 2.

### Virtual Environment
- Always activate `venv` before running or installing:
  ```powershell
  venv\Scripts\activate
  ```

### Dependencies (pinned in `requirements.txt`)
```
flask==3.1.3
werkzeug==3.1.6
pytest==8.3.5
pytest-flask==1.3.0
```

### Environment Variables
- **`FLASK_SECRET_KEY`** — Required for session management (once auth is implemented). Store in a `.env` file; never hardcode in source.
- `.env` is gitignored. Use `python-dotenv` or set it in the shell for local dev.

### Database
- SQLite file: `expense_tracker.db` (auto-generated at runtime, gitignored).
- The database helper functions live in `database/db.py` and must be implemented as part of Step 1.

---

## 7. What NOT to Do

- **Do not use any CSS framework** (Bootstrap, Tailwind, Bulma, etc.). All styling is vanilla CSS.
- **Do not use any JS framework or library** (React, Vue, jQuery). Vanilla JS only.
- **Do not change the server port** away from `5001` without updating all documentation.
- **Do not commit `expense_tracker.db`** — it is gitignored for a reason (contains user data).
- **Do not commit the `venv/` directory.**
- **Do not commit `.env` files** containing secrets.
- **Do not pin new package versions arbitrarily** — match the existing pinning style in `requirements.txt` and note the reason in a comment if you deviate.
- **Do not add inline `style="..."` attributes** to HTML — always use CSS classes.
- **Do not add UI code or route logic to `database/db.py`** — it is strictly a data-access layer.
- **Do not skip the `{% extends "base.html" %}` pattern** — every new page template must extend the base.
- **Do not use `"Rs."` or `"INR"`** for currency display — always use the `₹` symbol.

---

## 8. Testing Strategy

### Framework
- **pytest** with the **pytest-flask** plugin.

### Structure
- Test files live in a `tests/` directory (to be created as the project grows).
- Test files are named `test_<feature>.py` (e.g., `test_routes.py`, `test_auth.py`).

### Running Tests
```bash
# Run all tests
pytest

# Run with verbose output
pytest -v

# Run a specific file
pytest tests/test_routes.py -v

# Run a specific test function
pytest tests/test_routes.py::test_landing_page -v
```

### What to Test
- **Routes:** Assert correct HTTP status codes (200, 302, 404) and that the right template content appears in the response.
- **Database helpers:** Test `get_db()`, `init_db()`, `seed_db()` in isolation using an in-memory SQLite database (`:memory:`).
- **Auth flows:** Once implemented, test login, logout, registration, and session handling.
- **CRUD operations:** Test add, edit, and delete expense flows with fixture data.

---

## 9. Project-Specific Context

### Step-Based Learning Structure
This project is built incrementally across numbered steps. Placeholder routes already exist in `app.py` with comments like `"Feature — coming in Step N"`. When implementing a step:
1. Replace the placeholder string return with real logic.
2. Create the corresponding template in `templates/`.
3. Add any needed CSS to the appropriate stylesheet.
4. Implement database interactions in `database/db.py`.

### Current Implementation Status
| Step | Feature | Status |
|---|---|---|
| Step 0 | Project scaffold, landing page, base template | ✅ Done |
| Step 1 | Database setup (`db.py`) | 🔲 Stub only |
| Step 2 | User registration | 🔲 Template exists, no logic |
| Step 3 | Login / Logout | 🔲 Stub |
| Step 4 | User profile | 🔲 Stub |
| Step 5–6 | Expense dashboard / listing | 🔲 Not started |
| Step 7 | Add expense | 🔲 Stub |
| Step 8 | Edit expense | 🔲 Stub |
| Step 9 | Delete expense | 🔲 Stub |

### Domain Context
- Target market: **India** — use `₹` (INR), Indian number formatting where appropriate (e.g., ₹18,240).
- Expense categories expected: Food, Travel, Bills, Shopping, Health, Entertainment, Other.
- The app uses **session-based authentication** (Flask sessions + Werkzeug password hashing) — no JWT, no OAuth in scope.
- SQLite foreign keys must be **explicitly enabled** per connection via `PRAGMA foreign_keys = ON` (Flask does not do this automatically).
- The `get_db()` function should set `conn.row_factory = sqlite3.Row` so rows are accessible by column name.

### Design Language
- **Brand name:** Spendly · **Brand icon:** `◈`
- **Fonts:** `DM Serif Display` (headings/display) + `DM Sans` (body/UI)
- **Tone:** Clean, modern, trustworthy — not loud or flashy.
- The design system (colors, spacing, component styles) is defined in `static/css/style.css`. Extend it there, don't override it ad-hoc.
