import sqlite3
from datetime import datetime
from database.db import get_db

def get_recent_transactions(user_id, limit=10, date_from=None, date_to=None):
    """Retrieve the recent expenses logged by the user, ordered by date descending.

    Args:
        user_id:   ID of the authenticated user.
        limit:     Maximum number of rows to return (applied after date filter).
        date_from: ISO date string 'YYYY-MM-DD' — inclusive lower bound, or None.
        date_to:   ISO date string 'YYYY-MM-DD' — inclusive upper bound, or None.

    If only one of date_from / date_to is provided the date filter is skipped
    and all-time results are returned.  LIMIT applies after filtering.
    """
    conn = get_db()
    try:
        cursor = conn.cursor()
        conditions = ["user_id = ?"]
        params = [user_id]
        if date_from and date_to:
            conditions.append("date BETWEEN ? AND ?")
            params.extend([date_from, date_to])
        sql = (
            f"SELECT date, description, category, amount "
            f"FROM expenses "
            f"WHERE {' AND '.join(conditions)} "
            f"ORDER BY date DESC, id DESC "
            f"LIMIT ?"
        )
        params.append(limit)
        params = tuple(params)  # immutable — safe to pass to sqlite3 execute
        rows = cursor.execute(sql, params).fetchall()
        return [
            {
                "date": row["date"],
                "description": row["description"],
                "category": row["category"],
                "amount": row["amount"]
            }
            for row in rows
        ]
    finally:
        conn.close()

def get_user_by_id(user_id):
    """Retrieve user name, email, and formatted member_since string by user ID."""
    conn = get_db()
    try:
        cursor = conn.cursor()
        row = cursor.execute(
            "SELECT name, email, created_at FROM users WHERE id = ?", (user_id,)
        ).fetchone()
        if not row:
            return None
        
        created_str = row["created_at"]
        try:
            dt = datetime.strptime(created_str, "%Y-%m-%d %H:%M:%S")
        except ValueError:
            try:
                dt = datetime.fromisoformat(created_str)
            except ValueError:
                dt = datetime.now()
        
        member_since = dt.strftime("%B %Y")
        return {
            "name": row["name"],
            "email": row["email"],
            "member_since": member_since
        }
    finally:
        conn.close()

def get_summary_stats(user_id, date_from=None, date_to=None):
    """Retrieve aggregate statistics: total_spent, transaction_count, top_category.

    Args:
        user_id:   ID of the authenticated user.
        date_from: ISO date string 'YYYY-MM-DD' — inclusive lower bound, or None.
        date_to:   ISO date string 'YYYY-MM-DD' — inclusive upper bound, or None.

    If only one of date_from / date_to is provided the date filter is skipped
    and all-time totals are returned.
    """
    conn = get_db()
    try:
        cursor = conn.cursor()
        conditions = ["user_id = ?"]
        params = [user_id]
        if date_from and date_to:
            conditions.append("date BETWEEN ? AND ?")
            params.extend([date_from, date_to])
        where = ' AND '.join(conditions)
        params = tuple(params)  # immutable — reused for both SQL calls below

        # Sum and count
        res = cursor.execute(
            f"SELECT SUM(amount), COUNT(*) FROM expenses WHERE {where}",
            params
        ).fetchone()

        total_spent = res[0] if res[0] is not None else 0.0
        transaction_count = res[1] if res[1] is not None else 0

        if transaction_count == 0:
            return {
                "total_spent": 0.0,
                "transaction_count": 0,
                "top_category": "—"
            }

        # Top category — same WHERE so it respects the same date window
        top_res = cursor.execute(
            f"SELECT category FROM expenses WHERE {where} "
            f"GROUP BY category ORDER BY SUM(amount) DESC, category LIMIT 1",
            params
        ).fetchone()

        top_category = top_res["category"] if top_res else "—"

        return {
            "total_spent": total_spent,
            "transaction_count": transaction_count,
            "top_category": top_category
        }
    finally:
        conn.close()

def get_category_breakdown(user_id, date_from=None, date_to=None):
    """Retrieve category totals and rounded percentage breakdown, summing to exactly 100%.

    Args:
        user_id:   ID of the authenticated user.
        date_from: ISO date string 'YYYY-MM-DD' — inclusive lower bound, or None.
        date_to:   ISO date string 'YYYY-MM-DD' — inclusive upper bound, or None.

    If only one of date_from / date_to is provided the date filter is skipped
    and the all-time breakdown is returned.
    """
    conn = get_db()
    try:
        cursor = conn.cursor()
        conditions = ["user_id = ?"]
        params = [user_id]
        if date_from and date_to:
            conditions.append("date BETWEEN ? AND ?")
            params.extend([date_from, date_to])
        where = ' AND '.join(conditions)
        params = tuple(params)  # immutable — passed to single execute call

        rows = cursor.execute(
            f"SELECT category AS name, SUM(amount) AS amount "
            f"FROM expenses WHERE {where} "
            f"GROUP BY category ORDER BY amount DESC",
            params
        ).fetchall()

        if not rows:
            return []

        total_amount = sum(row["amount"] for row in rows)
        if total_amount == 0.0:
            return []

        breakdown = []
        for row in rows:
            breakdown.append({
                "name": row["name"],
                "amount": row["amount"],
                "pct": int(round((row["amount"] / total_amount) * 100))
            })

        # Distribute rounding remainders to the largest category (first in sorted list)
        pct_sum = sum(item["pct"] for item in breakdown)
        if pct_sum != 100 and len(breakdown) > 0:
            diff = 100 - pct_sum
            breakdown[0]["pct"] += diff

        return breakdown
    finally:
        conn.close()

def get_extended_summary_stats(user_id):
    """Retrieve aggregate statistics for dashboard: total_spent, transaction_count, top_category, avg_spent."""
    conn = get_db()
    try:
        cursor = conn.cursor()
        res = cursor.execute(
            """SELECT 
                   COALESCE(SUM(amount), 0.0) AS total_spent, 
                   COUNT(*) AS transaction_count,
                   COALESCE(AVG(amount), 0.0) AS avg_spent
               FROM expenses 
               WHERE user_id = ?""", 
            (user_id,)
        ).fetchone()
        
        total_spent = res["total_spent"]
        transaction_count = res["transaction_count"]
        avg_spent = res["avg_spent"]
        
        if transaction_count == 0:
            return {
                "total_spent": 0.0,
                "transaction_count": 0,
                "top_category": "—",
                "avg_spent": 0.0
            }
            
        top_res = cursor.execute(
            "SELECT category FROM expenses WHERE user_id = ? GROUP BY category ORDER BY SUM(amount) DESC, category LIMIT 1",
            (user_id,)
        ).fetchone()
        
        top_category = top_res["category"] if top_res else "—"
        
        return {
            "total_spent": total_spent,
            "transaction_count": transaction_count,
            "top_category": top_category,
            "avg_spent": avg_spent
        }
    finally:
        conn.close()

def get_filtered_expenses(user_id, search_query="", category="", limit=10, offset=0):
    """Retrieve filtered and paginated list of user expenses."""
    conn = get_db()
    try:
        conditions = ["user_id = ?"]
        params = [user_id]
        if search_query:
            conditions.append("description LIKE ?")
            params.append(f"%{search_query}%")
        if category:
            conditions.append("category = ?")
            params.append(category)
        
        sql = f"SELECT id, date, description, category, amount FROM expenses WHERE {' AND '.join(conditions)} ORDER BY date DESC, created_at DESC LIMIT ? OFFSET ?"
        params.extend([limit, offset])
        
        cursor = conn.cursor()
        rows = cursor.execute(sql, params).fetchall()
        return [
            {
                "id": row["id"],
                "date": row["date"],
                "description": row["description"],
                "category": row["category"],
                "amount": row["amount"]
            }
            for row in rows
        ]
    finally:
        conn.close()

def get_filtered_expenses_count(user_id, search_query="", category=""):
    """Retrieve count of filtered user expenses."""
    conn = get_db()
    try:
        conditions = ["user_id = ?"]
        params = [user_id]
        if search_query:
            conditions.append("description LIKE ?")
            params.append(f"%{search_query}%")
        if category:
            conditions.append("category = ?")
            params.append(category)
        
        sql = f"SELECT COUNT(*) FROM expenses WHERE {' AND '.join(conditions)}"
        
        cursor = conn.cursor()
        res = cursor.execute(sql, params).fetchone()
        return res[0] if res else 0
    finally:
        conn.close()

