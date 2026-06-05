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
        # Note: seed_db() is called by app initialization; we skip it here to avoid seeding
        
        # Create test users (avoiding conflicts with seeded demo user)
        pw_hash = generate_password_hash("password123", method="pbkdf2:sha256")
        user1_id = create_user("User One", "test.user1@test.com", pw_hash)
        user2_id = create_user("User Two", "test.user2@test.com", pw_hash)
        
        # Insert test expenses for user 1
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


# ---- GET /expenses/<id>/edit Tests ----

def test_get_edit_expense_unauthenticated(client):
    """GET /expenses/1/edit without login should redirect to login."""
    test_client, _, _, _, _, _ = client
    response = test_client.get('/expenses/1/edit')
    assert response.status_code == 302
    assert '/login' in response.location


def test_get_edit_expense_owned(client):
    """GET /expenses/<id>/edit for owned expense should return 200 and form."""
    test_client, user1_id, _, expense1_id, _, _ = client
    
    # Login as user 1
    test_client.post('/login', data={
        'email': 'test.user1@test.com',
        'password': 'password123',
    })
    
    response = test_client.get(f'/expenses/{expense1_id}/edit')
    assert response.status_code == 200
    assert b'Edit Expense' in response.data
    assert b'Lunch' in response.data
    assert b'500' in response.data or b'500.0' in response.data


def test_get_edit_expense_not_owned(client):
    """GET /expenses/<id>/edit for non-owned expense should redirect to dashboard."""
    test_client, user1_id, _, _, _, user2_expense_id = client
    
    # Login as user 1
    test_client.post('/login', data={
        'email': 'test.user1@test.com',
        'password': 'password123',
    })
    
    # Try to access user2's expense
    response = test_client.get(f'/expenses/{user2_expense_id}/edit')
    assert response.status_code == 302
    assert '/dashboard' in response.location


def test_get_edit_expense_not_found(client):
    """GET /expenses/<id>/edit for non-existent expense should redirect to dashboard."""
    test_client, _, _, _, _, _ = client
    
    # Login
    test_client.post('/login', data={
        'email': 'test.user1@test.com',
        'password': 'password123',
    })
    
    response = test_client.get('/expenses/9999/edit')
    assert response.status_code == 302
    assert '/dashboard' in response.location


# ---- POST /expenses/<id>/edit Tests ----

def test_post_edit_expense_success(client):
    """POST /expenses/<id>/edit with valid data should update the expense and redirect."""
    test_client, user1_id, _, expense1_id, _, _ = client
    
    # Login
    test_client.post('/login', data={
        'email': 'test.user1@test.com',
        'password': 'password123',
    })
    
    new_amount = 750.00
    new_description = "Updated lunch"
    new_date = date.today().isoformat()
    
    response = test_client.post(f'/expenses/{expense1_id}/edit', data={
        'amount': str(new_amount),
        'category': 'Food',
        'date': new_date,
        'description': new_description,
    })
    
    # Should redirect to dashboard with success
    assert response.status_code == 302
    assert '/dashboard' in response.location
    
    # Verify DB was updated
    updated = get_expense_by_id(user1_id, expense1_id)
    assert updated is not None
    assert updated['amount'] == new_amount
    assert updated['description'] == new_description


def test_post_edit_expense_invalid_amount(client):
    """POST /expenses/<id>/edit with invalid amount should show error and not update."""
    test_client, user1_id, _, expense1_id, _, _ = client
    
    # Login
    test_client.post('/login', data={
        'email': 'test.user1@test.com',
        'password': 'password123',
    })
    
    response = test_client.post(f'/expenses/{expense1_id}/edit', data={
        'amount': 'not-a-number',
        'category': 'Food',
        'date': date.today().isoformat(),
        'description': 'Test',
    })
    
    # Should re-render form with error
    assert response.status_code == 200
    assert b'valid number' in response.data
    
    # Verify DB was NOT updated
    original = get_expense_by_id(user1_id, expense1_id)
    assert original['amount'] == 500.00
    assert original['description'] == 'Lunch'


def test_post_edit_expense_negative_amount(client):
    """POST /expenses/<id>/edit with negative amount should show error."""
    test_client, user1_id, _, expense1_id, _, _ = client
    
    # Login
    test_client.post('/login', data={
        'email': 'test.user1@test.com',
        'password': 'password123',
    })
    
    response = test_client.post(f'/expenses/{expense1_id}/edit', data={
        'amount': '-100',
        'category': 'Food',
        'date': date.today().isoformat(),
        'description': 'Test',
    })
    
    assert response.status_code == 200
    assert b'positive number' in response.data


def test_post_edit_expense_missing_category(client):
    """POST /expenses/<id>/edit without category should show error."""
    test_client, user1_id, _, expense1_id, _, _ = client
    
    # Login
    test_client.post('/login', data={
        'email': 'test.user1@test.com',
        'password': 'password123',
    })
    
    response = test_client.post(f'/expenses/{expense1_id}/edit', data={
        'amount': '500',
        'category': '',
        'date': date.today().isoformat(),
        'description': 'Test',
    })
    
    assert response.status_code == 200
    assert b'required' in response.data


def test_post_edit_expense_invalid_date(client):
    """POST /expenses/<id>/edit with invalid date format should show error."""
    test_client, user1_id, _, expense1_id, _, _ = client
    
    # Login
    test_client.post('/login', data={
        'email': 'test.user1@test.com',
        'password': 'password123',
    })
    
    response = test_client.post(f'/expenses/{expense1_id}/edit', data={
        'amount': '500',
        'category': 'Food',
        'date': '13/06/2026',  # Invalid format
        'description': 'Test',
    })
    
    assert response.status_code == 200
    assert b'YYYY-MM-DD' in response.data


def test_post_edit_expense_not_owned(client):
    """POST /expenses/<id>/edit for non-owned expense should redirect."""
    test_client, _, _, _, _, user2_expense_id = client
    
    # Login as user 1
    test_client.post('/login', data={
        'email': 'test.user1@test.com',
        'password': 'password123',
    })
    
    # Try to modify user 2's expense
    response = test_client.post(f'/expenses/{user2_expense_id}/edit', data={
        'amount': '999',
        'category': 'Food',
        'date': date.today().isoformat(),
        'description': 'Hacked',
    })
    
    assert response.status_code == 302
    assert '/dashboard' in response.location


def test_post_edit_expense_with_description(client):
    """POST /expenses/<id>/edit should allow empty description."""
    test_client, user1_id, _, expense1_id, _, _ = client
    
    # Login
    test_client.post('/login', data={
        'email': 'test.user1@test.com',
        'password': 'password123',
    })
    
    response = test_client.post(f'/expenses/{expense1_id}/edit', data={
        'amount': '250.50',
        'category': 'Entertainment',
        'date': date.today().isoformat(),
        'description': '',  # Empty description is allowed
    })
    
    assert response.status_code == 302
    
    # Verify update
    updated = get_expense_by_id(user1_id, expense1_id)
    assert updated['amount'] == 250.50
    assert updated['category'] == 'Entertainment'
    assert updated['description'] == ''


def test_post_edit_expense_zero_amount(client):
    """POST /expenses/<id>/edit with zero amount should show error."""
    test_client, _, _, expense1_id, _, _ = client
    
    # Login
    test_client.post('/login', data={
        'email': 'test.user1@test.com',
        'password': 'password123',
    })
    
    response = test_client.post(f'/expenses/{expense1_id}/edit', data={
        'amount': '0',
        'category': 'Food',
        'date': date.today().isoformat(),
        'description': 'Test',
    })
    
    assert response.status_code == 200
    assert b'positive' in response.data
