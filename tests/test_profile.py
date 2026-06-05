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
from database.queries import get_summary_stats, get_category_breakdown, get_recent_transactions

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


# ------------------------------------------------------------------ #
# Step 07 — Date Filter: fixtures                                     #
# ------------------------------------------------------------------ #

@pytest.fixture()
def filter_db(tmp_path):
    """Patch DB_PATH to a fresh temp file, init schema, and seed the
    4 fixed expenses defined in spec 07-date-filter-for-profile-page.md.

    Seed (user_id=42):
        id=1  2026-06-01  Food      1200.00  June grocery
        id=2  2026-06-15  Bills      800.00  June electricity
        id=3  2026-05-10  Travel     500.00  May metro
        id=4  2026-03-20  Shopping   300.00  March clothing
    Total all-time = 2800.00, 4 transactions, top_category = Food
    """
    db_file = str(tmp_path / "filter_test.db")
    with patch.object(db_module, "DB_PATH", db_file):
        init_db()
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO users (id, name, email, password_hash, created_at) "
            "VALUES (?, ?, ?, ?, ?)",
            (42, "Filter User", "filter@spendly.com", "hash", "2026-01-01 00:00:00")
        )
        expenses = [
            (42, 1200.00, "Food",     "2026-06-01", "June grocery"),
            (42,  800.00, "Bills",    "2026-06-15", "June electricity"),
            (42,  500.00, "Travel",   "2026-05-10", "May metro"),
            (42,  300.00, "Shopping", "2026-03-20", "March clothing"),
        ]
        cursor.executemany(
            "INSERT INTO expenses (user_id, amount, category, date, description) "
            "VALUES (?, ?, ?, ?, ?)",
            expenses
        )
        conn.commit()
        conn.close()
        yield db_file


@pytest.fixture()
def filter_client(filter_db):
    """Flask test client wired to filter_db, pre-authenticated as user 42."""
    flask_app.config.update({"TESTING": True, "SECRET_KEY": "test-secret-key"})
    with patch.object(db_module, "DB_PATH", filter_db):
        with flask_app.test_client() as c:
            with c.session_transaction() as sess:
                sess["user_id"]   = 42
                sess["user_name"] = "Filter User"
            yield c


# ------------------------------------------------------------------ #
# Step 07 — Date Filter: query-helper unit tests                      #
# ------------------------------------------------------------------ #


def test_get_summary_stats_all_time(filter_db):
    """No date filter → all 4 expenses, total 2800.00, top Food."""
    with patch.object(db_module, "DB_PATH", filter_db):
        result = get_summary_stats(42)
    assert result["total_spent"]       == 2800.00
    assert result["transaction_count"] == 4
    assert result["top_category"]      == "Food"


def test_get_summary_stats_june(filter_db):
    """June filter → 2 expenses (Food 1200 + Bills 800 = 2000), top Food."""
    with patch.object(db_module, "DB_PATH", filter_db):
        result = get_summary_stats(42, date_from="2026-06-01", date_to="2026-06-30")
    assert result["total_spent"]       == 2000.00
    assert result["transaction_count"] == 2
    assert result["top_category"]      == "Food"


def test_get_summary_stats_partial_range_date_from_only(filter_db):
    """Only date_from provided → partial range → falls back to all-time."""
    with patch.object(db_module, "DB_PATH", filter_db):
        result = get_summary_stats(42, date_from="2026-06-01", date_to=None)
    assert result["total_spent"]       == 2800.00
    assert result["transaction_count"] == 4


def test_get_summary_stats_partial_range_date_to_only(filter_db):
    """Only date_to provided → partial range → falls back to all-time."""
    with patch.object(db_module, "DB_PATH", filter_db):
        result = get_summary_stats(42, date_from=None, date_to="2026-06-30")
    assert result["total_spent"]       == 2800.00
    assert result["transaction_count"] == 4


def test_get_summary_stats_may(filter_db):
    """May filter → 1 expense (Travel 500), top Travel."""
    with patch.object(db_module, "DB_PATH", filter_db):
        result = get_summary_stats(42, date_from="2026-05-01", date_to="2026-05-31")
    assert result["total_spent"]       == 500.00
    assert result["transaction_count"] == 1
    assert result["top_category"]      == "Travel"


def test_get_category_breakdown_june(filter_db):
    """June filter → 2 categories: Food 60%, Bills 40%."""
    with patch.object(db_module, "DB_PATH", filter_db):
        rows = get_category_breakdown(42, date_from="2026-06-01", date_to="2026-06-30")
    assert len(rows) == 2
    by_name = {r["name"]: r for r in rows}
    assert by_name["Food"]["amount"]  == 1200.00
    assert by_name["Bills"]["amount"] ==  800.00
    assert by_name["Food"]["pct"]  == 60
    assert by_name["Bills"]["pct"] == 40


def test_get_category_breakdown_all_time(filter_db):
    """No date filter → 4 categories, total amounts sum to 2800.00."""
    with patch.object(db_module, "DB_PATH", filter_db):
        rows = get_category_breakdown(42)
    assert len(rows) == 4
    assert sum(r["amount"] for r in rows) == 2800.00
    assert sum(r["pct"] for r in rows)    == 100


def test_get_recent_transactions_june(filter_db):
    """June filter → 2 rows; Bills (2026-06-15) comes first (date DESC)."""
    with patch.object(db_module, "DB_PATH", filter_db):
        rows = get_recent_transactions(42, date_from="2026-06-01", date_to="2026-06-30")
    assert len(rows) == 2
    assert rows[0]["date"]        == "2026-06-15"
    assert rows[0]["category"]    == "Bills"
    assert rows[1]["date"]        == "2026-06-01"
    assert rows[1]["category"]    == "Food"


def test_get_recent_transactions_future_range(filter_db):
    """A future date range that matches nothing → empty list."""
    with patch.object(db_module, "DB_PATH", filter_db):
        rows = get_recent_transactions(42, date_from="2099-01-01", date_to="2099-12-31")
    assert rows == []


# ------------------------------------------------------------------ #
# Step 07 — Date Filter: route integration tests                      #
# ------------------------------------------------------------------ #

def test_profile_no_filter_shows_all_time(filter_client):
    """`GET /profile` with no params shows 'Showing: All Time'."""
    response = filter_client.get("/profile")
    assert response.status_code == 200
    assert "Showing: All Time" in response.data.decode("utf-8")


def test_profile_preset_this_month(filter_client):
    """`GET /profile?preset=this_month` shows 'Showing: This Month'."""
    response = filter_client.get("/profile?preset=this_month")
    assert response.status_code == 200
    assert "Showing: This Month" in response.data.decode("utf-8")


def test_profile_preset_last_month(filter_client):
    """`GET /profile?preset=last_month` shows 'Showing: Last Month'."""
    response = filter_client.get("/profile?preset=last_month")
    assert response.status_code == 200
    assert "Showing: Last Month" in response.data.decode("utf-8")


def test_profile_preset_last_3_months(filter_client):
    """`GET /profile?preset=last_3_months` shows 'Showing: Last 3 Months'."""
    response = filter_client.get("/profile?preset=last_3_months")
    assert response.status_code == 200
    assert "Showing: Last 3 Months" in response.data.decode("utf-8")


def test_profile_preset_last_6_months(filter_client):
    """`GET /profile?preset=last_6_months` shows 'Showing: Last 6 Months'."""
    response = filter_client.get("/profile?preset=last_6_months")
    assert response.status_code == 200
    assert "Showing: Last 6 Months" in response.data.decode("utf-8")


def test_profile_preset_this_year(filter_client):
    """`GET /profile?preset=this_year` shows 'Showing: This Year'."""
    response = filter_client.get("/profile?preset=this_year")
    assert response.status_code == 200
    assert "Showing: This Year" in response.data.decode("utf-8")


def test_profile_custom_range(filter_client):
    """`GET /profile?date_from=2026-01-01&date_to=2026-03-31` shows ISO label."""
    response = filter_client.get("/profile?date_from=2026-01-01&date_to=2026-03-31")
    assert response.status_code == 200
    assert "Showing: 2026-01-01 to 2026-03-31" in response.data.decode("utf-8")


def test_profile_partial_range_fallback(filter_client):
    """Only date_from → partial range rejected → falls back to 'Showing: All Time'."""
    response = filter_client.get("/profile?date_from=2026-06-01")
    assert response.status_code == 200
    assert "Showing: All Time" in response.data.decode("utf-8")


def test_profile_bogus_preset_fallback(filter_client):
    """Unknown preset value → falls back to 'Showing: All Time'."""
    response = filter_client.get("/profile?preset=bogus_value")
    assert response.status_code == 200
    assert "Showing: All Time" in response.data.decode("utf-8")


def test_profile_active_preset_class(filter_client):
    """Active preset button carries the 'active' CSS class."""
    response = filter_client.get("/profile?preset=this_month")
    html = response.data.decode("utf-8")
    # The Jinja template appends ' active' to the class attribute
    assert "filter-preset-btn active" in html


def test_profile_date_inputs_prefilled(filter_client):
    """Custom date inputs are pre-filled from the query string."""
    response = filter_client.get("/profile?date_from=2026-01-01&date_to=2026-03-31")
    html = response.data.decode("utf-8")
    assert 'value="2026-01-01"' in html
    assert 'value="2026-03-31"' in html


def test_profile_clear_link_href(filter_client):
    """The Clear link always points to /profile with no query string."""
    response = filter_client.get("/profile?preset=this_month")
    html = response.data.decode("utf-8")
    assert 'href="/profile"' in html


def test_profile_user_card_unaffected_by_filter(filter_client):
    """User info card (name, email, member-since) is unchanged regardless of filter."""
    response = filter_client.get("/profile?preset=this_month")
    html = response.data.decode("utf-8")
    assert "Filter User"             in html
    assert "filter@spendly.com"      in html
    assert "Member since"            in html
