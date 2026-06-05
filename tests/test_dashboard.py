"""
tests/test_dashboard.py — Unit and Route tests for Step 6: Expense Dashboard.
"""

import sqlite3
import pytest
from unittest.mock import patch
import math

import database.db as db_module
from database.db import init_db, get_db
from database.queries import (
    get_user_by_id,
    get_extended_summary_stats,
    get_filtered_expenses,
    get_filtered_expenses_count
)
from app import app as flask_app


# ------------------------------------------------------------------ #
# Fixtures                                                            #
# ------------------------------------------------------------------ #

@pytest.fixture()
def mem_db(tmp_path):
    """Patch DB_PATH to a fresh temporary file and initialise the schema."""
    db_file = str(tmp_path / "test_dashboard.db")
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
    with patch.object(db_module, "DB_PATH", mem_db):
        with flask_app.test_client() as c:
            yield c


@pytest.fixture()
def seed_user_id(mem_db):
    """Create a clean seed user and expenses matching the spec."""
    with patch.object(db_module, "DB_PATH", mem_db):
        conn = get_db()
        cursor = conn.cursor()
        
        # Add seed user demo@spendly.com
        cursor.execute(
            "INSERT INTO users (name, email, password_hash, created_at) VALUES (?, ?, ?, ?)",
            ("Demo User", "demo@spendly.com", "somehash", "2026-06-01 10:30:00")
        )
        user_id = cursor.lastrowid
        
        # Add 8 seed expenses totaling exactly 346.24 with "Bills" as the top category
        expenses = [
            (user_id, 100.00, "Bills", "2026-06-08", "Electricity bill"),
            (user_id, 50.00,  "Bills", "2026-06-07", "Water bill"),
            (user_id, 30.00,  "Food", "2026-06-06", "Snack coffee"),
            (user_id, 40.00,  "Travel", "2026-06-05", "Bus ride"),
            (user_id, 20.00,  "Shopping", "2026-06-04", "Book"),
            (user_id, 50.00,  "Health", "2026-06-03", "Medicine"),
            (user_id, 50.00,  "Entertainment", "2026-06-02", "Show ticket"),
            (user_id, 6.24,   "Other", "2026-06-01", "Tea coffee"),
        ]
        cursor.executemany(
            "INSERT INTO expenses (user_id, amount, category, date, description) VALUES (?, ?, ?, ?, ?)",
            expenses
        )
        conn.commit()
        conn.close()
    return user_id


# ------------------------------------------------------------------ #
# Unit Tests — get_extended_summary_stats                            #
# ------------------------------------------------------------------ #

def test_get_extended_summary_stats_valid(mem_db, seed_user_id):
    """get_extended_summary_stats returns correct stats for a user with expenses."""
    with patch.object(db_module, "DB_PATH", mem_db):
        stats = get_extended_summary_stats(seed_user_id)
        assert stats is not None
        assert abs(stats["total_spent"] - 346.24) < 1e-9
        assert stats["transaction_count"] == 8
        assert stats["top_category"] == "Bills"
        assert abs(stats["avg_spent"] - (346.24 / 8)) < 1e-9


def test_get_extended_summary_stats_empty(mem_db):
    """get_extended_summary_stats returns safe defaults when user has no expenses."""
    with patch.object(db_module, "DB_PATH", mem_db):
        stats = get_extended_summary_stats(9999)
        assert stats == {
            "total_spent": 0.0,
            "transaction_count": 0,
            "top_category": "—",
            "avg_spent": 0.0
        }


# ------------------------------------------------------------------ #
# Unit Tests — get_filtered_expenses                                 #
# ------------------------------------------------------------------ #

def test_get_filtered_expenses_unfiltered(mem_db, seed_user_id):
    """get_filtered_expenses returns all items ordered newest first."""
    with patch.object(db_module, "DB_PATH", mem_db):
        expenses = get_filtered_expenses(seed_user_id)
        assert len(expenses) == 8
        # Order check: 2026-06-08 should be first
        assert expenses[0]["date"] == "2026-06-08"
        assert expenses[0]["description"] == "Electricity bill"
        assert expenses[-1]["date"] == "2026-06-01"


def test_get_filtered_expenses_search(mem_db, seed_user_id):
    """get_filtered_expenses filters by search keyword correctly."""
    with patch.object(db_module, "DB_PATH", mem_db):
        # search case-insensitive, contains coffee
        expenses = get_filtered_expenses(seed_user_id, search_query="coffee")
        assert len(expenses) == 2
        descriptions = [e["description"] for e in expenses]
        assert "Snack coffee" in descriptions
        assert "Tea coffee" in descriptions


def test_get_filtered_expenses_category(mem_db, seed_user_id):
    """get_filtered_expenses filters by category correctly."""
    with patch.object(db_module, "DB_PATH", mem_db):
        expenses = get_filtered_expenses(seed_user_id, category="Bills")
        assert len(expenses) == 2
        categories = [e["category"] for e in expenses]
        assert all(c == "Bills" for c in categories)


def test_get_filtered_expenses_pagination(mem_db, seed_user_id):
    """get_filtered_expenses respects limit and offset."""
    with patch.object(db_module, "DB_PATH", mem_db):
        expenses = get_filtered_expenses(seed_user_id, limit=3, offset=0)
        assert len(expenses) == 3
        assert expenses[0]["description"] == "Electricity bill"
        
        expenses_next = get_filtered_expenses(seed_user_id, limit=3, offset=3)
        assert len(expenses_next) == 3
        assert expenses_next[0]["description"] == "Bus ride"


def test_get_filtered_expenses_empty(mem_db):
    """get_filtered_expenses returns empty list for user with no expenses."""
    with patch.object(db_module, "DB_PATH", mem_db):
        expenses = get_filtered_expenses(9999)
        assert expenses == []


# ------------------------------------------------------------------ #
# Unit Tests — get_filtered_expenses_count                           #
# ------------------------------------------------------------------ #

def test_get_filtered_expenses_count_unfiltered(mem_db, seed_user_id):
    """get_filtered_expenses_count returns total rows without filters."""
    with patch.object(db_module, "DB_PATH", mem_db):
        count = get_filtered_expenses_count(seed_user_id)
        assert count == 8


def test_get_filtered_expenses_count_category(mem_db, seed_user_id):
    """get_filtered_expenses_count returns correct count for specific category."""
    with patch.object(db_module, "DB_PATH", mem_db):
        count = get_filtered_expenses_count(seed_user_id, category="Bills")
        assert count == 2


def test_get_filtered_expenses_count_empty(mem_db):
    """get_filtered_expenses_count returns 0 for non-existent user."""
    with patch.object(db_module, "DB_PATH", mem_db):
        count = get_filtered_expenses_count(9999)
        assert count == 0


# ------------------------------------------------------------------ #
# Route Integration Tests                                            #
# ------------------------------------------------------------------ #

def test_dashboard_route_unauthenticated(client):
    """Unauthenticated access to /dashboard redirects to /login."""
    response = client.get("/dashboard", follow_redirects=False)
    assert response.status_code == 302
    assert "/login" in response.headers["Location"]


def test_dashboard_route_authenticated_seed_user(client, mem_db, seed_user_id):
    """Authenticated seed user displays dashboard with correct title and header."""
    with client.session_transaction() as sess:
        sess["user_id"] = seed_user_id
        sess["user_name"] = "Demo User"

    with patch.object(db_module, "DB_PATH", mem_db):
        response = client.get("/dashboard")
        assert response.status_code == 200
        html = response.data.decode("utf-8")
        
        # Page title check
        assert "<title>Spendly — Dashboard</title>" in html
        # H1 Welcome check
        assert "Welcome back, Demo User" in html


def test_dashboard_route_authenticated_seed_user_details(client, mem_db, seed_user_id):
    """Dashboard displays the correct stats cards."""
    with client.session_transaction() as sess:
        sess["user_id"] = seed_user_id
        sess["user_name"] = "Demo User"

    with patch.object(db_module, "DB_PATH", mem_db):
        response = client.get("/dashboard")
        assert response.status_code == 200
        html = response.data.decode("utf-8")
        
        # Stats values
        assert "346.24" in html
        assert "8" in html
        assert "Bills" in html


def test_dashboard_route_search_filter(client, mem_db, seed_user_id):
    """Dashboard search query parameter filters transaction table."""
    with client.session_transaction() as sess:
        sess["user_id"] = seed_user_id
        sess["user_name"] = "Demo User"

    with patch.object(db_module, "DB_PATH", mem_db):
        response = client.get("/dashboard?q=coffee")
        assert response.status_code == 200
        html = response.data.decode("utf-8")
        
        # Filtered rows
        assert "Snack coffee" in html
        assert "Tea coffee" in html
        # Non-matching rows should not be present
        assert "Electricity bill" not in html
        
        # Preserves active filter
        assert 'value="coffee"' in html


def test_dashboard_route_category_filter(client, mem_db, seed_user_id):
    """Dashboard category query parameter filters table."""
    with client.session_transaction() as sess:
        sess["user_id"] = seed_user_id
        sess["user_name"] = "Demo User"

    with patch.object(db_module, "DB_PATH", mem_db):
        response = client.get("/dashboard?category=Food")
        assert response.status_code == 200
        html = response.data.decode("utf-8")
        
        assert "Snack coffee" in html
        assert "Electricity bill" not in html
        assert 'value="Food" selected' in html or '<option value="Food" selected>' in html


def test_dashboard_route_malformed_page(client, mem_db, seed_user_id):
    """Dashboard handles malformed page query parameter gracefully."""
    with client.session_transaction() as sess:
        sess["user_id"] = seed_user_id
        sess["user_name"] = "Demo User"

    with patch.object(db_module, "DB_PATH", mem_db):
        response = client.get("/dashboard?page=abc")
        assert response.status_code == 200
        html = response.data.decode("utf-8")
        assert "Welcome back, Demo User" in html


def test_dashboard_route_clamp_page(client, mem_db, seed_user_id):
    """Dashboard clamps out-of-range page parameter to last valid page."""
    with client.session_transaction() as sess:
        sess["user_id"] = seed_user_id
        sess["user_name"] = "Demo User"

    with patch.object(db_module, "DB_PATH", mem_db):
        response = client.get("/dashboard?page=99999")
        assert response.status_code == 200
        html = response.data.decode("utf-8")
        assert "Welcome back, Demo User" in html


def test_dashboard_route_new_user_empty_state(client, mem_db):
    """Dashboard renders empty state layout for user with zero expenses."""
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

    with patch.object(db_module, "DB_PATH", mem_db):
        response = client.get("/dashboard")
        assert response.status_code == 200
        html = response.data.decode("utf-8")
        
        assert "No expenses yet" in html
        assert "Add your first expense" in html
