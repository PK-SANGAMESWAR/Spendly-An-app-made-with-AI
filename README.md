# ◈ Spendly — Expense Tracker

Spendly is a premium, personal expense-tracking web application designed specifically for the Indian market. It allows users to seamlessly log expenses, view detailed category breakdowns, manage budgets, and trace transaction trends—all with a clean, responsive interface and absolutely no spreadsheets required.

---

## 🚀 Features & Milestones

Spendly is built as a step-by-step progressive learning application. Below is the current implementation status:

| Step / Feature | Description | Status |
| :--- | :--- | :--- |
| **Step 0: Scaffold & Landing** | Base templates, master layout, global styles, public landing page. | ✅ Complete |
| **Step 1: Database Setup** | SQLite connection configurations (`db.py`), auto-initialization, and demo data seeding. | ✅ Complete |
| **Step 2: User Registration** | Form validations, password match checks, and user database storage. | ✅ Complete |
| **Step 3: Authentication** | Secure Login/Logout, Werkzeug password hashing, session guards, and flash messages. | ✅ Complete |
| **Step 4: User Profile** | User statistics summary card, transaction count, and category spending breakdown. | ✅ Complete |
| **Step 5–6: Dashboard & Listing** | Unified dashboard showing paginated expense list, text search, and category filter. | ✅ Complete |
| **Step 7 Feature Add-on** | Profile page date-range filter (preset filters & custom picker). | ✅ Complete |
| **Step 7: Add Expense** | Interactive add-expense forms with input validations and category routing. | ✅ Complete |
| **Step 8: Edit Expense** | Full transaction editing interface for modifying existing logged expenses. | ✅ Complete |
| **Step 9: Delete Expense** | Safe deletion operations to remove expenses from the user's registry. | ✅ Complete |

---

## 🛠️ Technology Stack

- **Backend:** Python 3.10+ · Flask 3.x (Route management, template filters, custom session auth)
- **Database:** SQLite (`sqlite3`)
  - Configured with `PRAGMA foreign_keys = ON` to enforce database integrity constraints.
  - Leverages `sqlite3.Row` for intuitive column-name access.
- **Frontend:** Vanilla HTML5 / Vanilla CSS3 (Custom properties, CSS grid, glassmorphism) / Vanilla JS (modular IIFE structure, event bindings)
- **Typography:** Google Fonts (`DM Serif Display` for headings, `DM Sans` for body text)
- **Testing Suite:** `pytest` + `pytest-flask` for robust endpoint and database tests.

---

## 📁 Project Directory Structure

```text
expense-tracker/
├── app.py                  # Main entry point (Flask configuration & route endpoints)
├── requirements.txt        # Pinned Python dependencies
├── GEMINI.md               # Mandatory developer rules and guidelines
├── database/
│   ├── __init__.py
│   ├── db.py               # Database connections, init, & seeding logic
│   └── queries.py          # Data-access queries (dashboard and profile statistics)
├── templates/
│   ├── base.html           # Master layout template (navbar, footer, global styles, fonts)
│   ├── landing.html        # Public marketing page
│   ├── register.html       # Signup form template
│   ├── login.html          # Sign-in form template
│   ├── profile.html        # Profile & filtered stats page
│   ├── dashboard.html      # Expense dashboard & transaction browser
│   ├── terms.html          # Terms & Conditions
│   └── privacy.html        # Privacy Policy
├── static/
│   ├── css/
│   │   ├── style.css       # Global design tokens, layouts, forms, buttons
│   │   ├── landing.css     # Landing-page-only custom styles
│   │   ├── register.css    # Register page layout overrides
│   │   ├── login.css       # Login page specific styles
│   │   ├── profile.css     # Profile stats and cards CSS
│   │   └── dashboard.css   # Dashboard layout grid and pagination styles
│   └── js/
│       └── main.js         # Sitewide global JS placeholder
└── tests/                  # Test suites for routes, auth, database and filtering
```

---

## ⚙️ Setup & Installation

### 1. Clone the repository
Ensure you are in the project's root folder:
```bash
cd expense-tracker
```

### 2. Set up a Virtual Environment
Create and activate a virtual environment for Python:
**Windows (PowerShell):**
```powershell
python -m venv venv
.\venv\Scripts\Activate.ps1
```
**macOS / Linux:**
```bash
python3 -m venv venv
source venv/bin/activate
```

### 3. Install Dependencies
Install the pinned Python packages:
```bash
pip install -r requirements.txt
```

### 4. Set Environment Variables
Create a `.env` file in the root directory (this is gitignored) and add a secure secret key:
```env
FLASK_SECRET_KEY=your_secure_random_key_here
```
*Note: If no secret key is defined in the environment, the app falls back to a development key.*

### 5. Run the Application
Start the local development server:
```bash
python app.py
```
The server will start on [http://127.0.0.1:5001](http://127.0.0.1:5001).

---

## 🧪 Testing

The codebase includes an extensive suite of automated tests verifying database helpers, authentication procedures, and routing filters.

To run all tests:
```bash
pytest -v
```

To run tests in a specific file:
```bash
pytest tests/test_profile.py -v
```

---

## 💡 Design & Naming Conventions

- **Currency formatting:** Always formatted to the Indian Rupee standard (e.g. `₹18,240.00`). No `Rs.` or `INR` abbreviations are permitted.
- **Routing:** All routes are defined using snake_case (e.g., `@app.route("/expenses/add")`).
- **CSS Style Rules:** No CSS frameworks allowed. Design tokens are defined in `style.css` and page-specific layout rules reside in their corresponding `<page>.css` file.
- **Database Schema:** SQLite database migrations are handled directly within `init_db()` using `CREATE TABLE IF NOT EXISTS` commands.
