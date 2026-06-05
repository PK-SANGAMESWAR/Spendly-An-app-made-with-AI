"""
tests/test_profile.py — Tests for Step 4: User Profile

Covers all scenarios from the Definition of Done in 04-user-profile.md.
"""

import pytest
import sqlite3
from unittest.mock import patch
from flask import session
from app import app as flask_app
import database.db as db_module
from database.db import init_db, get_db

@pytest.fixture()
def mem_db(tmp_path):
    """Patch DB_PATH to a fresh temporary file and initialise the schema."""
    db_file = str(tmp_path / "test_profile_db.db")
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
def authenticated_client(client, mem_db):
    """Fixture that logs in a user and seeds the DB with their exact expected test data."""
    with patch.object(db_module, "DB_PATH", mem_db):
        conn = get_db()
        cursor = conn.cursor()
        
        # User 42 corresponding to what client.session_transaction() sets!
        cursor.execute(
            "INSERT INTO users (id, name, email, password_hash, created_at) VALUES (?, ?, ?, ?, ?)",
            (42, "Demo User", "demo@spendly.com", "somehash", "2026-06-01 10:30:00")
        )
        
        # Insert 8 expenses for user 42 totaling 5200.00:
        # Food: 2400.00, Bills: 1800.00, Travel: 1000.00
        # 5 other dummy expenses of 0.00 to hit transaction count = 8!
        expenses = [
            (42, 2400.00, "Food", "2026-06-02", "Weekly Groceries"),
            (42, 1800.00, "Bills", "2026-06-03", "Electricity Bill"),
            (42, 1000.00, "Travel", "2026-06-04", "Metro Recharge"),
            (42, 0.00, "Food", "2026-06-01", "dummy1"),
            (42, 0.00, "Food", "2026-06-01", "dummy2"),
            (42, 0.00, "Food", "2026-06-01", "dummy3"),
            (42, 0.00, "Food", "2026-06-01", "dummy4"),
            (42, 0.00, "Food", "2026-06-01", "dummy5"),
        ]
        cursor.executemany(
            "INSERT INTO expenses (user_id, amount, category, date, description) VALUES (?, ?, ?, ?, ?)",
            expenses
        )
        conn.commit()
        conn.close()

    with client.session_transaction() as sess:
        sess["user_id"] = 42
        sess["user_name"] = "Demo User"
    return client



# ------------------------------------------------------------------ #
# Unauthenticated Protection                                         #
# ------------------------------------------------------------------ #

def test_profile_unauthenticated_redirects(client):
    """Visiting /profile without being logged in redirects to /login (302)."""
    response = client.get("/profile", follow_redirects=False)
    assert response.status_code == 302
    assert "/login" in response.headers["Location"]


def test_profile_unauthenticated_flash_error(client):
    """Visiting /profile without being logged in flashes 'Please log in to access this page.' error."""
    client.get("/profile", follow_redirects=False)
    with client.session_transaction() as sess:
        flashes = sess.get("_flashes", [])
        assert any(msg == "Please log in to access this page." and category == "error" for category, msg in flashes)


def test_dashboard_unauthenticated_redirects(client):
    """Visiting /dashboard without being logged in redirects to /login (302)."""
    response = client.get("/dashboard", follow_redirects=False)
    assert response.status_code == 302
    assert "/login" in response.headers["Location"]


def test_dashboard_unauthenticated_flash_error(client):
    """Visiting /dashboard without being logged in flashes 'Please log in to access this page.' error."""
    client.get("/dashboard", follow_redirects=False)
    with client.session_transaction() as sess:
        flashes = sess.get("_flashes", [])
        assert any(msg == "Please log in to access this page." and category == "error" for category, msg in flashes)


# ------------------------------------------------------------------ #
# Authenticated Access                                               #
# ------------------------------------------------------------------ #

def test_profile_authenticated_returns_200(authenticated_client):
    """Visiting /profile while logged in returns HTTP 200."""
    response = authenticated_client.get("/profile")
    assert response.status_code == 200


def test_profile_displays_user_card(authenticated_client):
    """The profile page displays user info card (initials, name, email, member-since)."""
    response = authenticated_client.get("/profile")
    html = response.data.decode("utf-8")
    
    assert "Demo User" in html
    assert "demo@spendly.com" in html
    assert "June 2026" in html
    assert "DU" in html  # Initials


def test_profile_displays_summary_stats(authenticated_client):
    """The profile page displays at least three summary stats (Total Spent, Transactions count, Top Category)."""
    response = authenticated_client.get("/profile")
    html = response.data.decode("utf-8")
    
    assert "Total Spent" in html
    assert "₹5,200.00" in html
    assert "Transactions" in html
    assert "8" in html
    assert "Top Category" in html
    assert "Food" in html

def test_navbar_shows_logged_in_state(authenticated_client):
    """Navbar shows the logged-in state (user name, profile link, dashboard link, and logout)."""
    response = authenticated_client.get("/profile")
    html = response.data.decode("utf-8")
    
    assert "Dashboard" in html
    assert "Profile" in html
    assert "Demo User" in html
    assert "Logout" in html
    assert "Sign in" not in html
