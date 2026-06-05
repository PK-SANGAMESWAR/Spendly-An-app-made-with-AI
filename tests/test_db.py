"""
tests/test_db.py — Unit tests for database/db.py (Step 1)

All tests use an in-memory SQLite database via a pytest fixture that
patches DB_PATH so the real expense_tracker.db is never touched.
"""

import sqlite3
import pytest
from unittest.mock import patch

import database.db as db_module
from database.db import get_db, init_db, seed_db


# ------------------------------------------------------------------ #
# Fixtures                                                            #
# ------------------------------------------------------------------ #

@pytest.fixture()
def mem_db(tmp_path):
    """Patch DB_PATH to a temporary file, then initialise the schema.

    Using a real file (not :memory:) keeps the module-level DB_PATH
    patching simple — each test gets a fresh, isolated database.
    """
    db_file = str(tmp_path / "test.db")
    with patch.object(db_module, "DB_PATH", db_file):
        init_db()
        yield db_file


@pytest.fixture()
def seeded_db(mem_db):
    """mem_db with seed data already applied."""
    seed_db()
    return mem_db


# ------------------------------------------------------------------ #
# get_db() tests                                                      #
# ------------------------------------------------------------------ #

def test_get_db_returns_connection(mem_db):
    """get_db() should return a sqlite3.Connection."""
    conn = get_db()
    assert isinstance(conn, sqlite3.Connection)
    conn.close()


def test_row_factory_is_set(mem_db):
    """Rows returned by get_db() support column-name access."""
    conn = get_db()
    row = conn.execute("SELECT 1 AS value").fetchone()
    assert row["value"] == 1
    conn.close()


def test_foreign_keys_enabled(mem_db):
    """Inserting an expense with a non-existent user_id should raise IntegrityError."""
    conn = get_db()
    with pytest.raises(sqlite3.IntegrityError):
        conn.execute(
            "INSERT INTO expenses (user_id, amount, category, date) VALUES (?, ?, ?, ?)",
            (9999, 100.0, "Food", "2024-01-01"),
        )
        conn.commit()
    conn.close()


# ------------------------------------------------------------------ #
# init_db() tests                                                     #
# ------------------------------------------------------------------ #

def test_init_db_creates_users_table(mem_db):
    """users table should exist after init_db()."""
    conn = get_db()
    result = conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name='users'"
    ).fetchone()
    assert result is not None
    conn.close()


def test_init_db_creates_expenses_table(mem_db):
    """expenses table should exist after init_db()."""
    conn = get_db()
    result = conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name='expenses'"
    ).fetchone()
    assert result is not None
    conn.close()


def test_init_db_idempotent(mem_db):
    """Calling init_db() a second time should not raise any error."""
    init_db()   # called once already by the fixture; call again
    init_db()   # third call — still fine


# ------------------------------------------------------------------ #
# seed_db() tests                                                     #
# ------------------------------------------------------------------ #

def test_seed_db_inserts_demo_user(seeded_db):
    """demo@spendly.com should exist in the users table after seed_db()."""
    conn = get_db()
    user = conn.execute(
        "SELECT * FROM users WHERE email = ?", ("demo@spendly.com",)
    ).fetchone()
    assert user is not None
    assert user["name"] == "Demo User"
    conn.close()


def test_seed_db_inserts_expenses(seeded_db):
    """Exactly 8 expense rows should exist after seed_db()."""
    conn = get_db()
    count = conn.execute("SELECT COUNT(*) FROM expenses").fetchone()[0]
    assert count == 8
    conn.close()


def test_seed_db_idempotent(mem_db):
    """Calling seed_db() multiple times should not duplicate rows."""
    seed_db()
    seed_db()
    seed_db()

    conn = get_db()
    user_count    = conn.execute("SELECT COUNT(*) FROM users").fetchone()[0]
    expense_count = conn.execute("SELECT COUNT(*) FROM expenses").fetchone()[0]
    conn.close()

    assert user_count    == 1
    assert expense_count == 8


def test_password_is_hashed(seeded_db):
    """The stored password_hash must not equal the plain-text password."""
    conn = get_db()
    user = conn.execute(
        "SELECT password_hash FROM users WHERE email = ?", ("demo@spendly.com",)
    ).fetchone()
    assert user["password_hash"] != "demo123"
    assert len(user["password_hash"]) > 20   # hashed strings are long
    conn.close()
