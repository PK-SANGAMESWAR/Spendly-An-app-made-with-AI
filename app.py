import os
import sqlite3
from functools import wraps
from datetime import datetime

from flask import Flask, render_template, request, flash, redirect, url_for, session
from werkzeug.security import generate_password_hash, check_password_hash

from database.db import get_db, init_db, seed_db, create_user, get_user_by_email

app = Flask(__name__)

# Load secret key from environment; fall back to a dev-only key when
# running locally without a .env file.  Never use the fallback in production.
app.secret_key = os.environ.get("FLASK_SECRET_KEY", "dev-only-insecure-key-change-me")


# ------------------------------------------------------------------ #
# Database Initialisation                                             #
# ------------------------------------------------------------------ #

with app.app_context():
    init_db()
    seed_db()


# ------------------------------------------------------------------ #
# Helper Decorators                                                  #
# ------------------------------------------------------------------ #

def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not session.get("user_id"):
            flash("Please log in to access this page.", "error")
            return redirect(url_for("login"))
        return f(*args, **kwargs)
    return decorated_function


# ------------------------------------------------------------------ #
# Routes                                                              #
# ------------------------------------------------------------------ #

@app.route("/")
def landing():
    return render_template("landing.html")


@app.route("/register", methods=["GET", "POST"])
def register():
    # Already-logged-in guard — redirect authenticated users away from this page
    if session.get("user_id"):
        return redirect(url_for("profile"))

    if request.method == "GET":
        return render_template("register.html", name="", email="")

    # ---- POST: collect submitted values ----
    name             = request.form.get("name", "").strip()
    email            = request.form.get("email", "").strip()
    password         = request.form.get("password", "")
    confirm_password = request.form.get("confirm_password", "")
    agree_terms      = request.form.get("agree_terms")  # "on" when checked

    # ---- Server-side validation (stop at first failure) ----
    if not all([name, email, password, confirm_password]):
        flash("All fields are required.", "error")
        return render_template("register.html", name=name, email=email)

    if agree_terms != "on":
        flash("You must agree to the Terms and Conditions.", "error")
        return render_template("register.html", name=name, email=email)

    if len(password) < 8:
        flash("Password must be at least 8 characters.", "error")
        return render_template("register.html", name=name, email=email)

    if password != confirm_password:
        flash("Passwords do not match.", "error")
        return render_template("register.html", name=name, email=email)

    # ---- Write to DB ----
    try:
        pw_hash = generate_password_hash(password, method="pbkdf2:sha256")
        create_user(name, email, pw_hash)
        flash("Account created! Please log in.", "success")
        return redirect(url_for("login"))
    except sqlite3.IntegrityError:
        flash("An account with that email already exists.", "error")
        return render_template("register.html", name=name, email=email)


@app.route("/login", methods=["GET", "POST"])
def login():
    # Already-logged-in guard — redirect authenticated users away from this page
    if session.get("user_id"):
        return redirect(url_for("profile"))

    if request.method == "GET":
        return render_template("login.html", email="")

    # ---- POST: collect submitted values ----
    email    = request.form.get("email", "").strip()
    password = request.form.get("password", "")

    # ---- Validate: both fields must be non-empty ----
    if not email or not password:
        flash("Email and password are required.", "error")
        return render_template("login.html", email=email)

    # ---- Look up user and verify password ----
    user = get_user_by_email(email)
    if user is None or not check_password_hash(user["password_hash"], password):
        # Single generic message — prevents user enumeration
        flash("Invalid email or password.", "error")
        return render_template("login.html", email=email)

    # ---- Success: write session and redirect ----
    session.clear()
    session["user_id"]   = user["id"]
    session["user_name"] = user["name"]
    flash(f"Welcome back, {user['name']}!", "success")
    return redirect(url_for("profile"))


@app.route("/terms")
def terms():
    return render_template("terms.html")


@app.route("/privacy")
def privacy():
    return render_template("privacy.html")


# ------------------------------------------------------------------ #
# Placeholder routes — students will implement these                  #
# ------------------------------------------------------------------ #

@app.route("/dashboard")
@login_required
def dashboard():
    return "Dashboard — coming in Step 5"


@app.route("/logout")
def logout():
    session.clear()
    flash("You have been signed out.", "info")
    return redirect(url_for("landing"))


@app.route("/profile")
@login_required
def profile():
    user = {
        "name": "Demo User",
        "email": "demo@spendly.com",
        "created_at": "2026-06-01 10:30:00"
    }
    stats = {
        "total_spent": 5200.00,
        "transaction_count": 8,
        "top_category": "Food"
    }
    expenses = [
        {"date": "2026-06-02", "description": "Weekly Groceries", "category": "Food", "amount": 2400.00},
        {"date": "2026-06-03", "description": "Electricity Bill", "category": "Bills", "amount": 1800.00},
        {"date": "2026-06-04", "description": "Metro Recharge", "category": "Travel", "amount": 1000.00}
    ]
    categories = [
        {"category": "Food", "amount": 2400.00, "percentage": 46.15},
        {"category": "Bills", "amount": 1800.00, "percentage": 34.62},
        {"category": "Travel", "amount": 1000.00, "percentage": 19.23}
    ]
    initials = ''.join(w[0].upper() for w in user['name'].split()[:2])
    created_dt = datetime.strptime(user["created_at"], "%Y-%m-%d %H:%M:%S")
    member_since = created_dt.strftime("%B %Y")
    
    return render_template(
        "profile.html",
        user=user,
        stats=stats,
        expenses=expenses,
        categories=categories,
        initials=initials,
        member_since=member_since
    )


@app.route("/expenses/add")
def add_expense():
    return "Add expense — coming in Step 7"


@app.route("/expenses/<int:id>/edit")
def edit_expense(id):
    return "Edit expense — coming in Step 8"


@app.route("/expenses/<int:id>/delete")
def delete_expense(id):
    return "Delete expense — coming in Step 9"


if __name__ == "__main__":
    app.run(debug=True, port=5001)
