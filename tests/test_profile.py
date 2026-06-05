"""
tests/test_profile.py — Tests for Step 4: User Profile

Covers all scenarios from the Definition of Done in 04-user-profile.md.
"""

import pytest
from flask import session


@pytest.fixture()
def authenticated_client(client):
    """Fixture that logs in a user by setting session transaction variables."""
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


def test_profile_displays_recent_transactions(authenticated_client):
    """The profile page displays a transactions table with recent hardcoded rows."""
    response = authenticated_client.get("/profile")
    html = response.data.decode("utf-8")
    
    assert "Recent Transactions" in html
    # Row 1: Weekly Groceries
    assert "Weekly Groceries" in html
    assert "₹2,400.00" in html
    # Row 2: Electricity Bill
    assert "Electricity Bill" in html
    assert "₹1,800.00" in html
    # Row 3: Metro Recharge
    assert "Metro Recharge" in html
    assert "₹1,000.00" in html


def test_profile_displays_category_breakdown(authenticated_client):
    """The profile page displays category breakdown progress bars."""
    response = authenticated_client.get("/profile")
    html = response.data.decode("utf-8")
    
    assert "Category Breakdown" in html
    assert "Food" in html
    assert "46.15%" in html
    assert "Bills" in html
    assert "34.62%" in html
    assert "Travel" in html
    assert "19.23%" in html


def test_navbar_shows_logged_in_state(authenticated_client):
    """Navbar shows the logged-in state (user name, profile link, dashboard link, and logout)."""
    response = authenticated_client.get("/profile")
    html = response.data.decode("utf-8")
    
    assert "Dashboard" in html
    assert "Profile" in html
    assert "Demo User" in html
    assert "Logout" in html
    assert "Sign in" not in html
