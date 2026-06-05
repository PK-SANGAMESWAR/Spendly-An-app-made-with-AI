import os
import sqlite3
import math
from functools import wraps
from datetime import datetime, date, timedelta

from flask import Flask, render_template, request, flash, redirect, url_for, session
from werkzeug.security import generate_password_hash, check_password_hash

from database.db import get_db, init_db, seed_db, create_user, get_user_by_email
from database.queries import get_recent_transactions, get_user_by_id, get_summary_stats, get_category_breakdown, get_extended_summary_stats, get_filtered_expenses, get_filtered_expenses_count

app = Flask(__name__)

# Load secret key from environment; fall back to a dev-only key when
# running locally without a .env file.  Never use the fallback in production.
app.secret_key = os.environ.get("FLASK_SECRET_KEY", "dev-only-insecure-key-change-me")


@app.template_filter("inr")
def inr_filter(value):
    try:
        val = float(value)
    except (ValueError, TypeError):
        val = 0.0
    return f"₹{val:,.2f}"



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
# Route Helpers                                                       #
# ------------------------------------------------------------------ #

def _resolve_preset(preset):
    """Translate a preset slug into (date_from, date_to, filter_label).

    Returns ISO date strings or None.  Any unknown preset falls back to
    all-time so the caller never needs to guard against invalid input.

    Preset definitions (from spec 07-date-filter-for-profile-page.md):
      this_month    — first day of current calendar month to today
      last_month    — first day to last day of previous calendar month
      last_3_months — 90 days ago to today
      last_6_months — 180 days ago to today
      this_year     — Jan 1 of current year to today
      all_time      — None / None
    """
    today = date.today()

    if preset == "this_month":
        date_from = today.replace(day=1)
        date_to   = today
        label     = "Showing: This Month"

    elif preset == "last_month":
        # Subtract one day from the 1st of current month → last day of prev month
        date_to   = today.replace(day=1) - timedelta(days=1)
        date_from = date_to.replace(day=1)
        label     = "Showing: Last Month"

    elif preset == "last_3_months":
        date_from = today - timedelta(days=90)
        date_to   = today
        label     = "Showing: Last 3 Months"

    elif preset == "last_6_months":
        date_from = today - timedelta(days=180)
        date_to   = today
        label     = "Showing: Last 6 Months"

    elif preset == "this_year":
        date_from = date(today.year, 1, 1)
        date_to   = today
        label     = "Showing: This Year"

    else:
        # Covers "all_time" explicitly and any unknown / missing value
        return None, None, "Showing: All Time"

    return date_from.isoformat(), date_to.isoformat(), label


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

PAGE_SIZE = 10

@app.route("/dashboard")
@login_required
def dashboard():
    user_id = session["user_id"]
    # --- parse query params ---
    q        = request.args.get("q", "").strip()
    category = request.args.get("category", "").strip()
    try:
        page = int(request.args.get("page", 1))
        if page <= 0:
            page = 1
    except ValueError:
        page = 1
    # --- query ---
    stats      = get_extended_summary_stats(user_id)
    user       = get_user_by_id(user_id)
    if not user:
        flash("User not found.", "error")
        return redirect(url_for("logout"))
    categories = get_category_breakdown(user_id)

    count      = get_filtered_expenses_count(user_id, q, category)
    total_pages = max(1, math.ceil(count / PAGE_SIZE))
    page        = min(page, total_pages)
    offset      = (page - 1) * PAGE_SIZE
    expenses   = get_filtered_expenses(user_id, q, category, PAGE_SIZE, offset)
    return render_template(
        "dashboard.html",
        user=user, stats=stats, categories=categories,
        expenses=expenses, q=q, category=category,
        page=page, total_pages=total_pages,
    )



@app.route("/logout")
def logout():
    session.clear()
    flash("You have been signed out.", "info")
    return redirect(url_for("landing"))




@app.route("/profile")
@login_required
def profile():
    user_id   = session["user_id"]
    user_info = get_user_by_id(user_id)
    if not user_info:
        flash("User profile not found.", "error")
        return redirect(url_for("logout"))

    # ---- User card data (never date-filtered) ----
    initials     = ''.join(w[0].upper() for w in user_info['name'].split()[:2])
    member_since = user_info["member_since"]

    # ---- Parse filter query params ----
    preset       = request.args.get("preset",    "").strip()
    date_from_raw = request.args.get("date_from", "").strip()
    date_to_raw   = request.args.get("date_to",   "").strip()

    # ---- Resolve active date range and display label ----
    if preset:
        # Preset wins over custom range when both are present
        date_from, date_to, filter_label = _resolve_preset(preset)
    elif date_from_raw and date_to_raw:
        # Validate both strings are proper ISO dates before accepting the custom range.
        # Invalid formats (e.g. ?date_from=not-a-date) silently fall back to all-time
        # so the page always renders sensibly without exposing an error page.
        try:
            datetime.strptime(date_from_raw, "%Y-%m-%d")
            datetime.strptime(date_to_raw,   "%Y-%m-%d")
            date_from    = date_from_raw
            date_to      = date_to_raw
            filter_label = f"Showing: {date_from} to {date_to}"
        except ValueError:
            date_from    = None
            date_to      = None
            filter_label = "Showing: All Time"
    else:
        # Partial range (or no filter) — fall back to all-time silently
        date_from    = None
        date_to      = None
        filter_label = "Showing: All Time"

    # Explicit boolean so the template doesn't need to re-derive filter state
    is_all_time = date_from is None and date_to is None

    # ---- Fetch stats (date-filtered) ----
    stats      = get_summary_stats(user_id, date_from=date_from, date_to=date_to)
    categories = get_category_breakdown(user_id, date_from=date_from, date_to=date_to)
    recent     = get_recent_transactions(user_id, date_from=date_from, date_to=date_to)

    return render_template(
        "profile.html",
        user=user_info,
        stats=stats,
        categories=categories,
        recent=recent,
        initials=initials,
        member_since=member_since,
        # --- filter state (passed back so form stays in sync) ---
        preset=preset,
        date_from=date_from or "",
        date_to=date_to or "",
        filter_label=filter_label,
        is_all_time=is_all_time,
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
