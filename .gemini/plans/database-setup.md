# Implementation Plan — Step 1: Database Setup

## Overview

Replace the comment-only stub in `database/db.py` with a fully working SQLite data-access layer.
This is the **foundation step** — every future feature (auth, profiles, expense tracking) depends
on these three functions being correct.

No new routes, templates, or CSS files are needed. The only two files that change are
`database/db.py` (write from scratch) and `app.py` (add imports + startup calls).

---

## Depends On

Nothing — this is Step 1, the first implementation step.

---

## Files to Change

| File | Change type |
|---|---|
| `database/db.py` | Implement from scratch (currently a stub) |
| `app.py` | Add DB imports + startup initialization block |

No new files are created.

---

## 1. `database/db.py` — Full Implementation

### 1.1 Imports

```python
import sqlite3
import os
from werkzeug.security import generate_password_hash
```

- `sqlite3` — standard library, no install needed.
- `os` — used to build an absolute path to the DB file.
- `generate_password_hash` — from `werkzeug.security` (already in `requirements.txt`).

### 1.2 DB File Path

```python
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DB_PATH  = os.path.join(BASE_DIR, "expense_tracker.db")
```

- `__file__` is `database/db.py`, so `dirname(dirname(...))` resolves to the project root.
- This ensures the `.db` file lands at the project root regardless of the working directory
  when Python is invoked.
- **Name choice:** `expense_tracker.db` — matches the name already documented in `GEMINI.md`
  and the `.gitignore` pattern.

---

### 1.3 `get_db()`

**Purpose:** Open and return a configured SQLite connection.

```python
def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row       # dict-like column access: row["name"]
    conn.execute("PRAGMA foreign_keys = ON")
    return conn
```

Key decisions:
- `sqlite3.Row` is set so callers can access columns by name (`row["amount"]`) instead of index.
- `PRAGMA foreign_keys = ON` is applied **per connection** — SQLite resets this pragma on every
  new connection, so it must be set here, not in `init_db()`.
- The function returns the raw connection; callers are responsible for closing it (or using
  `with` context managers in future route handlers).

---

### 1.4 `init_db()`

**Purpose:** Create both tables idempotently. Safe to call on every app startup.

```python
def init_db():
    conn = get_db()
    try:
        conn.executescript("""
            CREATE TABLE IF NOT EXISTS users (
                id            INTEGER PRIMARY KEY AUTOINCREMENT,
                name          TEXT    NOT NULL,
                email         TEXT    NOT NULL UNIQUE,
                password_hash TEXT    NOT NULL,
                created_at    TEXT    NOT NULL DEFAULT (datetime('now'))
            );

            CREATE TABLE IF NOT EXISTS expenses (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id     INTEGER NOT NULL REFERENCES users(id),
                amount      REAL    NOT NULL,
                category    TEXT    NOT NULL,
                date        TEXT    NOT NULL,
                description TEXT,
                created_at  TEXT    NOT NULL DEFAULT (datetime('now')),
                FOREIGN KEY (user_id) REFERENCES users(id)
            );
        """)
        conn.commit()
    finally:
        conn.close()
```

Key decisions:
- `CREATE TABLE IF NOT EXISTS` — idempotent; repeated calls are safe and do not destroy data.
- `AUTOINCREMENT` on both PKs — prevents ID reuse after deletes.
- `email UNIQUE` — enforces at the DB level (not just application logic).
- `amount REAL` — stores fractional rupee values correctly (e.g., ₹18,240.50).
- `date TEXT NOT NULL` — stored as `YYYY-MM-DD` string; SQLite's `DATE` is just an alias for
  TEXT anyway.
- `FOREIGN KEY (user_id) REFERENCES users(id)` — explicit FK declaration so SQLite's foreign
  key enforcement picks it up.
- `executescript()` is used here because it handles multiple DDL statements in one call and
  auto-commits after each statement. This is safe for DDL-only scripts.
- `try/finally` guarantees the connection is closed even if an exception occurs.

---

### 1.5 `seed_db()`

**Purpose:** Insert one demo user + 8 sample expenses for development. Must be idempotent.

**Idempotency strategy:** Check `SELECT COUNT(*) FROM users` before inserting. If any rows
already exist, return immediately. This avoids both `INSERT OR IGNORE` complexity on the
expenses table and partial-seed states.

```python
def seed_db():
    conn = get_db()
    try:
        cursor = conn.cursor()

        # Guard — skip if data already exists
        count = cursor.execute("SELECT COUNT(*) FROM users").fetchone()[0]
        if count > 0:
            return

        # --- Demo user ---
        password_hash = generate_password_hash("demo123")
        cursor.execute(
            "INSERT INTO users (name, email, password_hash) VALUES (?, ?, ?)",
            ("Demo User", "demo@spendly.com", password_hash),
        )
        user_id = cursor.lastrowid

        # --- 8 sample expenses (one per category + one extra) ---
        from datetime import date, timedelta
        today = date.today()

        expenses = [
            (user_id, 450.00,   "Food",          (today - timedelta(days=1)).isoformat(),  "Lunch at café"),
            (user_id, 120.00,   "Transport",     (today - timedelta(days=2)).isoformat(),  "Auto rickshaw"),
            (user_id, 1800.00,  "Bills",         (today - timedelta(days=5)).isoformat(),  "Electricity bill"),
            (user_id, 350.00,   "Health",        (today - timedelta(days=7)).isoformat(),  "Pharmacy"),
            (user_id, 600.00,   "Entertainment", (today - timedelta(days=10)).isoformat(), "Movie tickets"),
            (user_id, 2200.00,  "Shopping",      (today - timedelta(days=12)).isoformat(), "Clothing"),
            (user_id, 75.00,    "Other",         (today - timedelta(days=14)).isoformat(), "Miscellaneous"),
            (user_id, 980.00,   "Food",          (today - timedelta(days=3)).isoformat(),  "Grocery run"),
        ]

        cursor.executemany(
            """INSERT INTO expenses (user_id, amount, category, date, description)
               VALUES (?, ?, ?, ?, ?)""",
            expenses,
        )

        conn.commit()
    finally:
        conn.close()
```

Key decisions:
- Early-return guard (`COUNT(*) > 0`) prevents any duplicate seeding across repeated app
  restarts.
- `generate_password_hash("demo123")` — Werkzeug's default PBKDF2-HMAC-SHA256 hashing.
- `cursor.lastrowid` — captures the auto-generated `user_id` for the demo user without an
  extra SELECT.
- Dates are computed relative to `date.today()` so they always fall within the "current month"
  as the spec requires, regardless of when the app is first started.
- `executemany` for bulk insert — cleaner and slightly more efficient than 8 individual
  `execute()` calls.
- All 7 categories appear at least once; "Food" appears twice to reach the required 8 rows.
- All amounts are `REAL` (float literals).

---

## 2. `app.py` — Startup Integration

### 2.1 New imports (add to the top)

```python
from database.db import get_db, init_db, seed_db
```

Add this after the existing `from flask import Flask, render_template` line.

### 2.2 New startup block (add after `app = Flask(__name__)`)

```python
# ------------------------------------------------------------------ #
# Database Initialisation                                             #
# ------------------------------------------------------------------ #

with app.app_context():
    init_db()
    seed_db()
```

Key decisions:
- `with app.app_context()` — required by Flask; `g`, `current_app`, etc. are available inside
  the context. Even though `get_db()` doesn't use `g` yet, this is the correct pattern and
  mirrors how Flask's own documentation recommends initializing extensions.
- Calling both functions here ensures the DB is ready **before** the first request is served.
- No try/except wrapper here — if `init_db()` fails at startup, we *want* the app to crash
  loudly rather than silently serving broken routes.

---

## 3. Schema Summary

```sql
-- users
CREATE TABLE IF NOT EXISTS users (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    name          TEXT    NOT NULL,
    email         TEXT    NOT NULL UNIQUE,
    password_hash TEXT    NOT NULL,
    created_at    TEXT    NOT NULL DEFAULT (datetime('now'))
);

-- expenses
CREATE TABLE IF NOT EXISTS expenses (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id     INTEGER NOT NULL,
    amount      REAL    NOT NULL,
    category    TEXT    NOT NULL,
    date        TEXT    NOT NULL,          -- YYYY-MM-DD
    description TEXT,                     -- nullable
    created_at  TEXT    NOT NULL DEFAULT (datetime('now')),
    FOREIGN KEY (user_id) REFERENCES users(id)
);
```

---

## 4. Category Enum (fixed list for the whole project)

```
Food · Transport · Bills · Health · Entertainment · Shopping · Other
```

> ⚠️ The spec lists `Transport` (not `Travel`). Use `Transport` everywhere — in seed data,
> form dropdowns, and validation logic in future steps.

---

## 5. Rules Checklist

| Rule | Satisfied by |
|---|---|
| No ORM | Raw `sqlite3` only |
| Parameterized queries only | `?` placeholders in every `execute()` |
| `PRAGMA foreign_keys = ON` per connection | Set inside `get_db()` |
| `amount` as REAL | Column type + float literals in seed data |
| `werkzeug` password hashing | `generate_password_hash("demo123")` |
| `seed_db()` idempotent | `COUNT(*) > 0` early-return guard |
| Dates in YYYY-MM-DD | `date.isoformat()` from Python's `datetime` module |
| `CREATE TABLE IF NOT EXISTS` | Used in `init_db()` — safe on repeated runs |

---

## 6. Testing Plan

Tests live in `tests/` (per `GEMINI.md`). The following test cases must pass before Step 1 is
marked **Done**:

### `tests/test_db.py` — new file

| Test name | What it checks |
|---|---|
| `test_get_db_returns_connection` | `get_db()` returns a `sqlite3.Connection` instance |
| `test_row_factory_is_set` | A query result supports column-name access (`row["id"]`) |
| `test_foreign_keys_enabled` | Inserting an expense with a non-existent `user_id` raises `IntegrityError` |
| `test_init_db_creates_users_table` | `users` table exists after `init_db()` |
| `test_init_db_creates_expenses_table` | `expenses` table exists after `init_db()` |
| `test_init_db_idempotent` | Calling `init_db()` twice does not raise |
| `test_seed_db_inserts_demo_user` | `demo@spendly.com` exists in `users` after `seed_db()` |
| `test_seed_db_inserts_expenses` | 8 rows exist in `expenses` |
| `test_seed_db_idempotent` | Calling `seed_db()` twice still yields exactly 1 user and 8 expenses |
| `test_password_is_hashed` | `password_hash` column is not the plain string `"demo123"` |

All tests use an **in-memory SQLite database** (`:memory:`) via a pytest fixture — never the
real `expense_tracker.db`. The fixture patches `DB_PATH` or passes a connection directly.

### `tests/test_routes.py` — existing file (smoke test)

- `GET /` → 200
- `GET /register` → 200
- `GET /login` → 200
- `GET /terms` → 200
- `GET /privacy` → 200

These must continue to pass after the `app.py` changes.

---

## 7. Definition of Done

- [ ] `expense_tracker.db` is created on first `python app.py` run
- [ ] Both `users` and `expenses` tables exist with exact schema above
- [ ] Demo user `demo@spendly.com` / `demo123` exists with a hashed password
- [ ] Exactly 8 seed expenses exist, spanning all 7 categories
- [ ] Running `python app.py` a second time does not duplicate seed data
- [ ] `PRAGMA foreign_keys = ON` is verified working (FK violation raises `IntegrityError`)
- [ ] All queries in `db.py` use `?` parameterized placeholders — zero string formatting in SQL
- [ ] App starts without errors on `python app.py`
- [ ] All `test_db.py` tests pass
- [ ] All existing `test_routes.py` smoke tests still pass
