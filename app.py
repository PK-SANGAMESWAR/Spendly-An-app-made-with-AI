import os
import sqlite3

from flask import Flask, render_template, request, flash, redirect, url_for, session
from werkzeug.security import generate_password_hash

from database.db import get_db, init_db, seed_db, create_user

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
# Routes                                                              #
# ------------------------------------------------------------------ #

@app.route("/")
def landing():
    return render_template("landing.html")


@app.route("/register", methods=["GET", "POST"])
def register():
    # Already-logged-in guard — redirect authenticated users away from this page
    if session.get("user_id"):
        return redirect(url_for("dashboard"))

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
        pw_hash = generate_password_hash(password)
        create_user(name, email, pw_hash)
        flash("Account created! Please log in.", "success")
        return redirect(url_for("login"))
    except sqlite3.IntegrityError:
        flash("An account with that email already exists.", "error")
        return render_template("register.html", name=name, email=email)


@app.route("/login")
def login():
    return render_template("login.html")


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
def dashboard():
    return "Dashboard — coming in Step 5"


@app.route("/logout")
def logout():
    return "Logout — coming in Step 3"


@app.route("/profile")
def profile():
    return "Profile page — coming in Step 4"


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
