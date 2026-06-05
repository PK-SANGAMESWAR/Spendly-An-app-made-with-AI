"""
tests/test_backend_connection.py — Unit and Route tests for Step 5: Backend Connection.
"""

import sqlite3
import pytest
from unittest.mock import patch
from datetime import datetime

import database.db as db_module
from database.db import init_db, create_user, get_db
from database.queries import (
    get_user_by_id,
    get_summary_stats,
    get_recent_transactions,
    get_category_breakdown
)
from app import app as flask_app


# ------------------------------------------------------------------ #
# Fixtures                                                            #
# ------------------------------------------------------------------ #

@pytest.fixture()
def mem_db(tmp_path):
    """Patch DB_PATH to a fresh temporary file and initialise the schema."""
    db_file = str(tmp_path / "test_backend.db")
    with patch.object(db_module, "DB_PATH", db_file):
        init_db()
        yield db_file


@pytest.fixture()
def client(mem_db):
    """Flask test client wired to the temporary DB."""
    flask_app.config.update({
        "TESTING": True,
        "SECRET_KEY": "test-secret-key",
    })
    # Patch queries database access and app DB_PATH configuration
    with patch.object(db_module, "DB_PATH", mem_db):
        with flask_app.test_client() as c:
            yield c


@pytest.fixture()
def test_user(mem_db):
    """Create a clean test user."""
    with patch.object(db_module, "DB_PATH", mem_db):
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO users (name, email, password_hash, created_at) VALUES (?, ?, ?, ?)",
            ("Test User", "test@example.com", "hash", "2026-06-01 12:00:00")
        )
        user_id = cursor.lastrowid
        conn.commit()
        conn.close()
    return user_id


# ------------------------------------------------------------------ #
# Unit Tests — get_user_by_id                                        #
# ------------------------------------------------------------------ #

def test_get_user_by_id_valid(mem_db, test_user):
    """get_user_by_id returns correct details for a valid ID."""
    with patch.object(db_module, "DB_PATH", mem_db):
        info = get_user_by_id(test_user)
        assert info is not None
        assert info["name"] == "Test User"
        assert info["email"] == "test@example.com"
        assert info["member_since"] == "June 2026"


def test_get_user_by_id_nonexistent(mem_db):
    """get_user_by_id returns None for an invalid/non-existent user ID."""
    with patch.object(db_module, "DB_PATH", mem_db):
        info = get_user_by_id(9999)
        assert info is None


# ------------------------------------------------------------------ #
# Unit Tests — get_summary_stats                                     #
# ------------------------------------------------------------------ #

def test_get_summary_stats_with_expenses(mem_db, test_user):
    """get_summary_stats calculates totals correctly with expenses."""
    with patch.object(db_module, "DB_PATH", mem_db):
        conn = get_db()
        cursor = conn.cursor()
        cursor.executemany(
            "INSERT INTO expenses (user_id, amount, category, date) VALUES (?, ?, ?, ?)",
            [
                (test_user, 100.0, "Food", "2026-06-02"),
                (test_user, 250.0, "Bills", "2026-06-03"),
                (test_user, 150.0, "Bills", "2026-06-04"),
            ]
        )
        conn.commit()
        conn.close()

        stats = get_summary_stats(test_user)
        assert stats["total_spent"] == 500.0
        assert stats["transaction_count"] == 3
        assert stats["top_category"] == "Bills"


def test_get_summary_stats_empty(mem_db, test_user):
    """get_summary_stats handles users with no expenses returning zeros and em-dash."""
    with patch.object(db_module, "DB_PATH", mem_db):
        stats = get_summary_stats(test_user)
        assert stats["total_spent"] == 0.0
        assert stats["transaction_count"] == 0
        assert stats["top_category"] == "—"


# ------------------------------------------------------------------ #
# Unit Tests — get_recent_transactions                               #
# ------------------------------------------------------------------ #

def test_get_recent_transactions_ordered(mem_db, test_user):
    """get_recent_transactions returns items ordered newest date first."""
    with patch.object(db_module, "DB_PATH", mem_db):
        conn = get_db()
        cursor = conn.cursor()
        cursor.executemany(
            "INSERT INTO expenses (user_id, amount, category, date, description) VALUES (?, ?, ?, ?, ?)",
            [
                (test_user, 50.0, "Food", "2026-06-02", "lunch"),
                (test_user, 120.0, "Travel", "2026-06-04", "cab"),
                (test_user, 75.0, "Bills", "2026-06-03", "internet"),
            ]
        )
        conn.commit()
        conn.close()

        transactions = get_recent_transactions(test_user, limit=5)
        assert len(transactions) == 3
        assert transactions[0]["category"] == "Travel"
        assert transactions[1]["category"] == "Bills"
        assert transactions[2]["category"] == "Food"


def test_get_recent_transactions_empty(mem_db, test_user):
    """get_recent_transactions returns empty list if no transactions exist."""
    with patch.object(db_module, "DB_PATH", mem_db):
        transactions = get_recent_transactions(test_user)
        assert transactions == []


# ------------------------------------------------------------------ #
# Unit Tests — get_category_breakdown                                #
# ------------------------------------------------------------------ #

def test_get_category_breakdown_rounding(mem_db, test_user):
    """get_category_breakdown adjusts percentages so they sum to exactly 100%."""
    # We choose amounts that lead to remainder sum issues if standard rounded:
    # Total: 300.0. A: 101.0 (33.67%), B: 101.0 (33.67%), C: 98.0 (32.67%).
    # Rounded: A: 34%, B: 34%, C: 33%. Sum: 101%.
    # Distribute logic should deduct 1% from the largest category (A).
    with patch.object(db_module, "DB_PATH", mem_db):
        conn = get_db()
        cursor = conn.cursor()
        cursor.executemany(
            "INSERT INTO expenses (user_id, amount, category, date) VALUES (?, ?, ?, ?)",
            [
                (test_user, 101.0, "A", "2026-06-02"),
                (test_user, 101.0, "B", "2026-06-03"),
                (test_user, 98.0, "C", "2026-06-04"),
            ]
        )
        conn.commit()
        conn.close()

        breakdown = get_category_breakdown(test_user)
        assert len(breakdown) == 3
        
        # Verify ordered by amount descending
        assert breakdown[0]["name"] in ("A", "B")
        assert breakdown[2]["name"] == "C"
        
        pct_sum = sum(item["pct"] for item in breakdown)
        assert pct_sum == 100


def test_get_category_breakdown_single(mem_db, test_user):
    """get_category_breakdown returns 100% if single category exists."""
    with patch.object(db_module, "DB_PATH", mem_db):
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO expenses (user_id, amount, category, date) VALUES (?, ?, ?, ?)",
            (test_user, 450.0, "Bills", "2026-06-02")
        )
        conn.commit()
        conn.close()

        breakdown = get_category_breakdown(test_user)
        assert len(breakdown) == 1
        assert breakdown[0]["name"] == "Bills"
        assert breakdown[0]["pct"] == 100


def test_get_category_breakdown_empty(mem_db, test_user):
    """get_category_breakdown returns empty list if no transactions exist."""
    with patch.object(db_module, "DB_PATH", mem_db):
        breakdown = get_category_breakdown(test_user)
        assert breakdown == []


# ------------------------------------------------------------------ #
# Route Integration Tests                                            #
# ------------------------------------------------------------------ #

def test_profile_route_unauthenticated_redirects(client):
    """Unauthenticated access to /profile redirects to /login."""
    response = client.get("/profile", follow_redirects=False)
    assert response.status_code == 302
    assert "/login" in response.headers["Location"]


def test_profile_route_authenticated_seed_user(client, mem_db):
    """Authenticated seed user displays correct dynamic stats, currencies, and records."""
    # Seed user demo@spendly.com is needed. Let's create it.
    with patch.object(db_module, "DB_PATH", mem_db):
        conn = get_db()
        cursor = conn.cursor()
        # Add seed user
        cursor.execute(
            "INSERT INTO users (name, email, password_hash, created_at) VALUES (?, ?, ?, ?)",
            ("Demo User", "demo@spendly.com", "somehash", "2026-06-01 10:30:00")
        )
        user_id = cursor.lastrowid
        
        # Add custom 8 expenses summing to exactly 346.24 with "Bills" as top category
        # Categories represented: Bills, Food, Travel, Shopping, Health, Entertainment, Other (all 7!)
        expenses = [
            (user_id, 100.00, "Bills", "2026-06-08", "Electricity bill"),
            (user_id, 50.00,  "Bills", "2026-06-07", "Water bill"),
            (user_id, 30.00,  "Food", "2026-06-06", "Snack"),
            (user_id, 40.00,  "Travel", "2026-06-05", "Bus ride"),
            (user_id, 20.00,  "Shopping", "2026-06-04", "Book"),
            (user_id, 50.00,  "Health", "2026-06-03", "Medicine"),
            (user_id, 50.00,  "Entertainment", "2026-06-02", "Show ticket"),
            (user_id, 6.24,   "Other", "2026-06-01", "Tea"),
        ]
        cursor.executemany(
            "INSERT INTO expenses (user_id, amount, category, date, description) VALUES (?, ?, ?, ?, ?)",
            expenses
        )
        conn.commit()
        conn.close()

    # Perform authenticated route request
    with client.session_transaction() as sess:
        sess["user_id"] = user_id
        sess["user_name"] = "Demo User"

    response = client.get("/profile")
    assert response.status_code == 200
    html = response.data.decode("utf-8")

    # Name and email assertions
    assert "Demo User" in html
    assert "demo@spendly.com" in html
    assert "₹" in html

    # Summary stats verification
    assert "346.24" in html
    assert "8" in html
    assert "Bills" in html



def test_profile_route_brand_new_user(client, mem_db):
    """Brand new user with zero expenses displays zero states cleanly without exceptions."""
    with patch.object(db_module, "DB_PATH", mem_db):
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO users (name, email, password_hash, created_at) VALUES (?, ?, ?, ?)",
            ("Newbie User", "newbie@spendly.com", "somehash", "2026-06-05 12:00:00")
        )
        user_id = cursor.lastrowid
        conn.commit()
        conn.close()

    with client.session_transaction() as sess:
        sess["user_id"] = user_id
        sess["user_name"] = "Newbie User"

    response = client.get("/profile")
    assert response.status_code == 200
    html = response.data.decode("utf-8")

    assert "Newbie User" in html
    assert "newbie@spendly.com" in html
    assert "₹0.00" in html
    assert "0" in html
    assert "—" in html  # Em-dash for top category
