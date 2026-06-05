import os
import sqlite3
from werkzeug.security import generate_password_hash

# ------------------------------------------------------------------ #
# Path Configuration                                                  #
# ------------------------------------------------------------------ #

# database/db.py lives one level below the project root, so we go up
# two dirname() calls to reach the project root.
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DB_PATH  = os.path.join(BASE_DIR, "expense_tracker.db")


# ------------------------------------------------------------------ #
# get_db                                                              #
# ------------------------------------------------------------------ #

def get_db():
    """Open and return a configured SQLite connection.

    Every connection has:
    - row_factory = sqlite3.Row    (column-name access: row["amount"])
    - PRAGMA foreign_keys = ON     (must be set per connection in SQLite)
    """
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


# ------------------------------------------------------------------ #
# init_db                                                             #
# ------------------------------------------------------------------ #

def init_db():
    """Create all tables using CREATE TABLE IF NOT EXISTS.

    Safe to call on every app startup — does not drop or alter existing
    tables or data.
    """
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
                user_id     INTEGER NOT NULL,
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


# ------------------------------------------------------------------ #
# seed_db                                                             #
# ------------------------------------------------------------------ #

def seed_db():
    """Insert demo data for development. Safe to call multiple times.

    Guard: if any rows already exist in 'users', returns immediately
    without touching the database — prevents duplicate seed data on
    repeated app restarts.

    Inserts:
    - 1 demo user  (demo@spendly.com / demo123)
    - 8 sample expenses across all 7 categories
    """
    from datetime import date, timedelta

    conn = get_db()
    try:
        cursor = conn.cursor()

        # Early-return guard — skip if seed data already present
        row_count = cursor.execute("SELECT COUNT(*) FROM users").fetchone()[0]
        if row_count > 0:
            return

        # --- Demo user ---
        password_hash = generate_password_hash("demo123", method="pbkdf2:sha256")
        cursor.execute(
            "INSERT INTO users (name, email, password_hash) VALUES (?, ?, ?)",
            ("Demo User", "demo@spendly.com", password_hash),
        )
        user_id = cursor.lastrowid   # capture auto-generated PK

        # --- 8 sample expenses (all 7 categories represented) ---
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


# ------------------------------------------------------------------ #
# User helpers                                                        #
# ------------------------------------------------------------------ #

def create_user(name, email, password_hash):
    """Insert a new user row and return the new user id (int).

    Raises sqlite3.IntegrityError if the email already exists (UNIQUE
    constraint on users.email).  The caller is responsible for catching
    this and showing the user a meaningful error message.

    Uses a parameterised query -- never string-format SQL.
    """
    conn = get_db()
    try:
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO users (name, email, password_hash) VALUES (?, ?, ?)",
            (name, email, password_hash),
        )
        conn.commit()
        return cursor.lastrowid
    finally:
        conn.close()


def get_user_by_email(email):
    """Return the sqlite3.Row for the user with the given email, or None.

    Used here to pre-check duplicates before a DB write, and reused by
    the login route (Step 3) for credential verification.
    """
    conn = get_db()
    try:
        return conn.execute(
            "SELECT * FROM users WHERE email = ?", (email,)
        ).fetchone()
    finally:
        conn.close()
