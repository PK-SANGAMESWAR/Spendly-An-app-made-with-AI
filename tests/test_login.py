"""
tests/test_login.py — Tests for Step 3: Login and Logout

Covers all scenarios from the Definition of Done in 03-login-and-logout.md.
"""

import pytest
from unittest.mock import patch

import database.db as db_module
from database.db import init_db, create_user, get_user_by_email
from app import app as flask_app
from werkzeug.security import generate_password_hash


# ------------------------------------------------------------------ #
# Fixtures                                                            #
# ------------------------------------------------------------------ #

@pytest.fixture()
def mem_db(tmp_path):
    """Patch DB_PATH to a fresh temporary file and initialise the schema."""
    db_file = str(tmp_path / "test_login.db")
    with patch.object(db_module, "DB_PATH", db_file):
        init_db()
        yield db_file


@pytest.fixture()
def client(mem_db):
    """Flask test client wired to the patched DB.

    Sets SECRET_KEY so flash() and session operations work correctly.
    """
    flask_app.config.update({
        "TESTING": True,
        "SECRET_KEY": "test-secret-key",
    })
    with patch.object(db_module, "DB_PATH", mem_db):
        with flask_app.test_client() as c:
            yield c


@pytest.fixture()
def test_user(mem_db):
    """Create a test user in the temporary database."""
    with patch.object(db_module, "DB_PATH", mem_db):
        pw_hash = generate_password_hash("securepassword123")
        create_user("Test User", "testuser@example.com", pw_hash)
    return {
        "email": "testuser@example.com",
        "password": "securepassword123",
        "name": "Test User"
    }


# ------------------------------------------------------------------ #
# GET /login                                                       #
# ------------------------------------------------------------------ #

def test_login_get_returns_200(client):
    """GET /login must return HTTP 200."""
    response = client.get("/login")
    assert response.status_code == 200


def test_login_get_has_correct_title(client):
    """Page <title> must be exactly 'Spendly — Sign In'."""
    response = client.get("/login")
    assert b"Spendly \xe2\x80\x94 Sign In" in response.data or \
           b"Spendly &#8212; Sign In" in response.data or \
           "Spendly — Sign In".encode() in response.data


def test_login_get_has_correct_h1(client):
    """Page <h1> must read 'Welcome back'."""
    response = client.get("/login")
    assert b"Welcome back" in response.data


def test_login_already_logged_in_redirects(client):
    """GET /login while already logged in must redirect to /profile (302)."""
    with client.session_transaction() as sess:
        sess["user_id"] = 99
    response = client.get("/login")
    assert response.status_code == 302
    assert "/profile" in response.headers["Location"]


# ------------------------------------------------------------------ #
# POST /login — validation and auth flows                            #
# ------------------------------------------------------------------ #

def test_login_post_valid_credentials(client, test_user):
    """Submitting valid credentials sets user_id in session and redirects to profile."""
    response = client.post("/login", data={
        "email": test_user["email"],
        "password": test_user["password"]
    }, follow_redirects=False)
    
    assert response.status_code == 302
    assert "/profile" in response.headers["Location"]
    
    with client.session_transaction() as sess:
        assert sess.get("user_id") is not None
        assert sess.get("user_name") == test_user["name"]


def test_login_post_success_flash(client, test_user):
    """Following a successful login puts the welcome back success flash in the session."""
    client.post("/login", data={
        "email": test_user["email"],
        "password": test_user["password"]
    }, follow_redirects=False)
    
    with client.session_transaction() as sess:
        flashes = sess.get("_flashes", [])
        assert any(msg == "Welcome back, Test User!" for category, msg in flashes)


def test_login_post_wrong_email(client, test_user):
    """Submitting an unregistered email triggers generic error and re-renders form."""
    response = client.post("/login", data={
        "email": "wrongemail@example.com",
        "password": test_user["password"]
    }, follow_redirects=True)
    
    assert response.status_code == 200
    assert b"Invalid email or password." in response.data


def test_login_post_wrong_password(client, test_user):
    """Submitting a wrong password triggers generic error and re-renders form."""
    response = client.post("/login", data={
        "email": test_user["email"],
        "password": "wrongpassword"
    }, follow_redirects=True)
    
    assert response.status_code == 200
    assert b"Invalid email or password." in response.data


def test_login_post_email_prepopulated_on_error(client, test_user):
    """After a failed login, the email field remains pre-populated but password is not."""
    response = client.post("/login", data={
        "email": "wrongemail@example.com",
        "password": "wrongpassword"
    }, follow_redirects=True)
    
    html = response.data.decode("utf-8")
    assert 'value="wrongemail@example.com"' in html
    assert 'value="wrongpassword"' not in html


def test_login_post_blank_fields(client):
    """Submitting both fields blank triggers 'required' validation."""
    response = client.post("/login", data={
        "email": "",
        "password": ""
    }, follow_redirects=True)
    
    assert response.status_code == 200
    assert b"Email and password are required." in response.data


def test_login_post_blank_email(client, test_user):
    """Submitting with email blank triggers required fields error."""
    response = client.post("/login", data={
        "email": "",
        "password": test_user["password"]
    }, follow_redirects=True)
    
    assert response.status_code == 200
    assert b"Email and password are required." in response.data


def test_login_post_blank_password(client, test_user):
    """Submitting with password blank triggers required fields error."""
    response = client.post("/login", data={
        "email": test_user["email"],
        "password": ""
    }, follow_redirects=True)
    
    assert response.status_code == 200
    assert b"Email and password are required." in response.data


# ------------------------------------------------------------------ #
# GET /logout                                                        #
# ------------------------------------------------------------------ #

def test_logout_clears_session(client):
    """GET /logout must clear user_id and other keys from session."""
    with client.session_transaction() as sess:
        sess["user_id"] = 123
        sess["user_name"] = "Some User"
        sess["other_key"] = "value"
        
    client.get("/logout")
    
    with client.session_transaction() as sess:
        assert "user_id" not in sess
        assert "user_name" not in sess
        assert "other_key" not in sess


def test_logout_redirects_to_landing(client):
    """GET /logout redirects (302) to the landing page."""
    response = client.get("/logout", follow_redirects=False)
    assert response.status_code == 302
    assert response.headers["Location"] == "/" or response.headers["Location"].endswith("/")


def test_logout_flash_message(client):
    """Following logout redirect shows 'You have been signed out.' info flash."""
    response = client.get("/logout", follow_redirects=True)
    assert response.status_code == 200
    assert b"You have been signed out." in response.data


def test_logout_unauthenticated_safe(client):
    """Calling /logout when not authenticated is safe, does not crash, and redirects."""
    # Ensure session is empty
    with client.session_transaction() as sess:
        sess.clear()
        
    response = client.get("/logout", follow_redirects=False)
    assert response.status_code == 302
    assert response.headers["Location"] == "/" or response.headers["Location"].endswith("/")
