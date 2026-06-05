"""
tests/test_registration.py — Tests for Step 2: User Registration

Covers all scenarios from the Definition of Done in 02-registration.md.

Strategy:
  - Route tests use the Flask test client (from conftest.py).
  - DB helper unit tests patch DB_PATH to a tmp_path file, same pattern
    as test_db.py, so the real expense_tracker.db is never touched.
  - SECRET_KEY is set on the app config so flash() and session work.
"""

import sqlite3
import pytest
from unittest.mock import patch

import database.db as db_module
from database.db import init_db, create_user, get_user_by_email
from app import app as flask_app


# ------------------------------------------------------------------ #
# Fixtures                                                            #
# ------------------------------------------------------------------ #

@pytest.fixture()
def mem_db(tmp_path):
    """Patch DB_PATH to a fresh temporary file and initialise the schema."""
    db_file = str(tmp_path / "test_reg.db")
    with patch.object(db_module, "DB_PATH", db_file):
        init_db()
        yield db_file


@pytest.fixture()
def client(mem_db):
    """Flask test client wired to the patched in-memory DB.

    Sets SECRET_KEY so flash() and session operations work correctly.
    """
    flask_app.config.update({
        "TESTING": True,
        "SECRET_KEY": "test-secret-key",
    })
    with patch.object(db_module, "DB_PATH", mem_db):
        with flask_app.test_client() as c:
            yield c


# ------------------------------------------------------------------ #
# Helpers                                                             #
# ------------------------------------------------------------------ #

VALID_FORM = {
    "name":             "Nitish Kumar",
    "email":            "nitish@example.com",
    "password":         "securepassword1",
    "confirm_password": "securepassword1",
    "agree_terms":      "on",
}


def _post(client, data):
    """POST /register with given form data."""
    return client.post("/register", data=data, follow_redirects=False)


def _post_follow(client, data):
    """POST /register and follow any redirect."""
    return client.post("/register", data=data, follow_redirects=True)


# ------------------------------------------------------------------ #
# GET /register                                                       #
# ------------------------------------------------------------------ #

def test_register_get_200(client):
    """GET /register must return HTTP 200."""
    response = client.get("/register")
    assert response.status_code == 200


def test_register_title(client):
    """Page <title> must contain 'Spendly — Create Account'."""
    response = client.get("/register")
    assert b"Spendly \xe2\x80\x94 Create Account" in response.data or \
           b"Spendly &#8212; Create Account" in response.data or \
           "Spendly — Create Account".encode() in response.data


def test_register_h1(client):
    """Page <h1> must contain 'Create your account'."""
    response = client.get("/register")
    assert b"Create your account" in response.data


def test_register_get_logged_in_redirects(client):
    """GET /register while logged in must redirect (302) to /profile."""
    with client.session_transaction() as sess:
        sess["user_id"] = 1
    response = client.get("/register")
    assert response.status_code == 302
    assert "/profile" in response.headers["Location"]


# ------------------------------------------------------------------ #
# POST /register — success path                                       #
# ------------------------------------------------------------------ #

def test_register_success_redirects_to_login(client):
    """Valid POST must redirect (302) to /login."""
    response = _post(client, VALID_FORM)
    assert response.status_code == 302
    assert "/login" in response.headers["Location"]


def test_register_success_flash_message(client):
    """After a valid POST, following the redirect shows the success flash."""
    response = _post_follow(client, VALID_FORM)
    assert b"Account created" in response.data


def test_register_success_user_in_db(client, mem_db):
    """After a valid POST, the new user row must exist in the database."""
    _post(client, VALID_FORM)
    with patch.object(db_module, "DB_PATH", mem_db):
        user = get_user_by_email("nitish@example.com")
    assert user is not None
    assert user["name"] == "Nitish Kumar"


def test_register_password_not_plaintext(client, mem_db):
    """The stored password_hash must not equal the submitted plain password."""
    _post(client, VALID_FORM)
    with patch.object(db_module, "DB_PATH", mem_db):
        user = get_user_by_email("nitish@example.com")
    assert user is not None
    assert user["password_hash"] != VALID_FORM["password"]
    assert len(user["password_hash"]) > 20  # hashes are long strings


# ------------------------------------------------------------------ #
# POST /register — validation failures                                #
# ------------------------------------------------------------------ #

def test_register_blank_name_error(client):
    """Blank name must re-render the form (200) with an error flash."""
    data = {**VALID_FORM, "name": ""}
    response = _post_follow(client, data)
    assert response.status_code == 200
    assert b"required" in response.data.lower() or b"error" in response.data.lower() \
        or b"All fields" in response.data


def test_register_blank_email_error(client):
    """Blank email must re-render the form (200) with an error flash."""
    data = {**VALID_FORM, "email": ""}
    response = _post_follow(client, data)
    assert response.status_code == 200
    assert b"All fields are required" in response.data


def test_register_blank_password_error(client):
    """Blank password must re-render the form (200) with an error flash."""
    data = {**VALID_FORM, "password": "", "confirm_password": ""}
    response = _post_follow(client, data)
    assert response.status_code == 200
    assert b"All fields are required" in response.data


def test_register_password_mismatch_error(client):
    """Mismatched passwords must re-render the form with an error flash."""
    data = {**VALID_FORM, "confirm_password": "different_password"}
    response = _post_follow(client, data)
    assert response.status_code == 200
    assert b"Passwords do not match" in response.data


def test_register_short_password_error(client):
    """A password shorter than 8 characters must trigger an error flash."""
    data = {**VALID_FORM, "password": "short", "confirm_password": "short"}
    response = _post_follow(client, data)
    assert response.status_code == 200
    assert b"at least 8 characters" in response.data


def test_register_no_terms_error(client):
    """Submitting without the terms checkbox must trigger an error flash."""
    data = {k: v for k, v in VALID_FORM.items() if k != "agree_terms"}
    response = _post_follow(client, data)
    assert response.status_code == 200
    assert b"Terms and Conditions" in response.data


def test_register_duplicate_email_error(client):
    """Registering the same email twice must flash the duplicate error message."""
    _post(client, VALID_FORM)
    response = _post_follow(client, VALID_FORM)
    assert response.status_code == 200
    assert b"An account with that email already exists" in response.data


# ------------------------------------------------------------------ #
# Field re-population                                                 #
# ------------------------------------------------------------------ #

def test_register_field_repopulation(client):
    """After a failed POST, the name and email inputs retain their values."""
    data = {**VALID_FORM, "password": "short", "confirm_password": "short"}
    response = _post_follow(client, data)
    html = response.data.decode("utf-8")
    assert "Nitish Kumar" in html
    assert "nitish@example.com" in html


# ------------------------------------------------------------------ #
# DB helper unit tests (isolated, no HTTP)                            #
# ------------------------------------------------------------------ #

def test_create_user_returns_id(mem_db):
    """create_user() must return an integer row id on success."""
    from werkzeug.security import generate_password_hash
    with patch.object(db_module, "DB_PATH", mem_db):
        user_id = create_user(
            "Test User",
            "test@example.com",
            generate_password_hash("password123"),
        )
    assert isinstance(user_id, int)
    assert user_id > 0


def test_create_user_raises_on_duplicate(mem_db):
    """create_user() must raise IntegrityError on a duplicate email."""
    from werkzeug.security import generate_password_hash
    pw = generate_password_hash("password123")
    with patch.object(db_module, "DB_PATH", mem_db):
        create_user("User One", "dup@example.com", pw)
        with pytest.raises(sqlite3.IntegrityError):
            create_user("User Two", "dup@example.com", pw)


def test_get_user_by_email_found(mem_db):
    """get_user_by_email() must return a Row for a registered email."""
    from werkzeug.security import generate_password_hash
    with patch.object(db_module, "DB_PATH", mem_db):
        create_user("Find Me", "findme@example.com", generate_password_hash("pass1234"))
        user = get_user_by_email("findme@example.com")
    assert user is not None
    assert user["name"] == "Find Me"


def test_get_user_by_email_not_found(mem_db):
    """get_user_by_email() must return None for an unregistered email."""
    with patch.object(db_module, "DB_PATH", mem_db):
        result = get_user_by_email("nobody@example.com")
    assert result is None
