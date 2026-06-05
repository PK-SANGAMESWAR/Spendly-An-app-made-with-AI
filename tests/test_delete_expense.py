import pytest
import sqlite3
import tempfile
import os
from datetime import date, timedelta
from app import app
from database.db import get_db, init_db, seed_db, create_user
from database.queries import get_expense_by_id
from werkzeug.security import generate_password_hash


@pytest.fixture
def client():
    """Flask test client with temporary file-based database (not :memory: due to seed_db conflicts)."""
    db_fd, db_path = tempfile.mkstemp()
    app.config['TESTING'] = True
    app.config['DATABASE'] = db_path
    
    with app.app_context():
        init_db()
        # seed_db() is run by app context init if database is empty; we create a custom state
        
        # Create test users
        pw_hash = generate_password_hash("password123", method="pbkdf2:sha256")
        user1_id = create_user("User One", "test.user1@test.com", pw_hash)
        user2_id = create_user("User Two", "test.user2@test.com", pw_hash)
        
        # Insert test expenses
        conn = get_db()
        cursor = conn.cursor()
        
        today = date.today()
        cursor.execute(
            """INSERT INTO expenses (user_id, amount, category, date, description)
               VALUES (?, ?, ?, ?, ?)""",
            (user1_id, 500.00, "Food", today.isoformat(), "Lunch"),
        )
        expense1_id = cursor.lastrowid
        
        cursor.execute(
            """INSERT INTO expenses (user_id, amount, category, date, description)
               VALUES (?, ?, ?, ?, ?)""",
            (user1_id, 1200.00, "Bills", (today - timedelta(days=5)).isoformat(), "Electricity"),
        )
        expense2_id = cursor.lastrowid
        
        cursor.execute(
            """INSERT INTO expenses (user_id, amount, category, date, description)
               VALUES (?, ?, ?, ?, ?)""",
            (user2_id, 300.00, "Travel", today.isoformat(), "Auto"),
        )
        user2_expense_id = cursor.lastrowid
        
        conn.commit()
        conn.close()
        
        yield app.test_client(), user1_id, user2_id, expense1_id, expense2_id, user2_expense_id
    
    app.config['DATABASE'] = None
    os.close(db_fd)
    os.unlink(db_path)


# ---- GET /expenses/<id>/delete Tests ----

def test_get_delete_expense_unauthenticated(client):
    """GET /expenses/<id>/delete without login redirects to login page."""
    test_client, _, _, expense1_id, _, _ = client
    response = test_client.get(f'/expenses/{expense1_id}/delete')
    assert response.status_code == 302
    assert '/login' in response.location


def test_get_delete_expense_owned(client):
    """GET /expenses/<id>/delete for owned expense returns 200 and confirmation page details."""
    test_client, user1_id, _, expense1_id, _, _ = client
    
    # Login as user 1
    test_client.post('/login', data={
        'email': 'test.user1@test.com',
        'password': 'password123',
    })
    
    response = test_client.get(f'/expenses/{expense1_id}/delete')
    assert response.status_code == 200
    
    html = response.data.decode('utf-8')
    assert 'Spendly — Delete Expense' in html
    assert 'Delete Expense' in html
    assert 'Are you sure you want to delete this expense?' in html
    assert 'Warning: This action cannot be undone.' in html
    assert 'Lunch' in html
    assert 'Food' in html
    assert '500' in html or '500.0' in html
    assert 'Delete' in html
    assert 'Cancel' in html
    assert f'action="/expenses/{expense1_id}/delete"' in html


def test_get_delete_expense_not_owned(client):
    """GET /expenses/<id>/delete for unowned expense redirects to dashboard with flash error."""
    test_client, _, _, _, _, user2_expense_id = client
    
    # Login as user 1
    test_client.post('/login', data={
        'email': 'test.user1@test.com',
        'password': 'password123',
    })
    
    response = test_client.get(f'/expenses/{user2_expense_id}/delete', follow_redirects=True)
    assert response.status_code == 200
    assert b'Expense not found.' in response.data


def test_get_delete_expense_not_found(client):
    """GET /expenses/<id>/delete for non-existent expense redirects to dashboard with flash error."""
    test_client, _, _, _, _, _ = client
    
    # Login as user 1
    test_client.post('/login', data={
        'email': 'test.user1@test.com',
        'password': 'password123',
    })
    
    response = test_client.get('/expenses/9999/delete', follow_redirects=True)
    assert response.status_code == 200
    assert b'Expense not found.' in response.data


# ---- POST /expenses/<id>/delete Tests ----

def test_post_delete_expense_unauthenticated(client):
    """POST /expenses/<id>/delete without login redirects to login page."""
    test_client, _, _, expense1_id, _, _ = client
    response = test_client.post(f'/expenses/{expense1_id}/delete')
    assert response.status_code == 302
    assert '/login' in response.location


def test_post_delete_expense_success(client):
    """POST /expenses/<id>/delete for owned expense deletes it and redirects with success flash."""
    test_client, user1_id, _, expense1_id, _, _ = client
    
    # Login as user 1
    test_client.post('/login', data={
        'email': 'test.user1@test.com',
        'password': 'password123',
    })
    
    # Verify expense exists in DB first
    assert get_expense_by_id(user1_id, expense1_id) is not None
    
    response = test_client.post(f'/expenses/{expense1_id}/delete', follow_redirects=True)
    assert response.status_code == 200
    assert b'Expense deleted successfully.' in response.data
    
    # Verify expense is deleted in DB
    assert get_expense_by_id(user1_id, expense1_id) is None


def test_post_delete_expense_not_owned(client):
    """POST /expenses/<id>/delete for unowned expense does NOT delete it and redirects with flash error."""
    test_client, _, user2_id, _, _, user2_expense_id = client
    
    # Login as user 1
    test_client.post('/login', data={
        'email': 'test.user1@test.com',
        'password': 'password123',
    })
    
    # Verify user 2's expense exists
    with app.app_context():
        assert get_expense_by_id(user2_id, user2_expense_id) is not None
    
    response = test_client.post(f'/expenses/{user2_expense_id}/delete', follow_redirects=True)
    assert response.status_code == 200
    assert b'Expense not found.' in response.data
    
    # Verify user 2's expense still exists in DB
    with app.app_context():
        assert get_expense_by_id(user2_id, user2_expense_id) is not None


def test_post_delete_expense_not_found(client):
    """POST /expenses/<id>/delete for non-existent expense redirects to dashboard with flash error."""
    test_client, _, _, _, _, _ = client
    
    # Login as user 1
    test_client.post('/login', data={
        'email': 'test.user1@test.com',
        'password': 'password123',
    })
    
    response = test_client.post('/expenses/9999/delete', follow_redirects=True)
    assert response.status_code == 200
    assert b'Expense not found.' in response.data
