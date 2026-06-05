---
description: Create a spec file and feature branch for the next Spendly step
argument-hint: "Step number and feature name e.g. 2 registration"
allowed-tools: Read, Write, Glob, Bash(git:*)
---

You are a senior developer spinning up a new feature for the
Spendly expense tracker. Always follow the rules in GEMINI.md.

User input: $ARGUMENTS

## Step 1 — Check working directory is clean
Run `git status` and check for uncommitted, unstaged, or
untracked files. If any exist, stop immediately and tell
the user to commit or stash changes before proceeding.
DO NOT CONTINUE until the working directory is clean.

## Step 2 — Parse the arguments
From $ARGUMENTS extract:

1. `step_number` — zero-padded to 2 digits: 2 → 02, 11 → 11

2. `feature_title` — human readable title in Title Case
   - Example: "Registration" or "Login and Logout"

3. `feature_slug` — git and file safe slug
   - Lowercase, kebab-case
   - Only a-z, 0-9 and -
   - Maximum 40 characters
   - Example: registration, login-logout

4. `branch_name` — format: `feature/<feature_slug>`
   - Example: `feature/registration`

If you cannot infer these from $ARGUMENTS, ask the user
to clarify before proceeding.

## Step 3 — Check branch name is not taken
Run `git branch` to list existing branches.
If `branch_name` is already taken, append a number:
`feature/registration-01`, `feature/registration-02` etc.

## Step 4 — Switch to main and pull latest
Run:
```
git checkout main
git pull origin main 2>/dev/null || echo "Could not pull from origin — continuing with local main"
```
If the pull fails (offline, no remote configured, etc.) print a
notice but **continue** — do not abort the command.

## Step 5 — Create and switch to the feature branch
Run:
```
git checkout -b <branch_name>
```

## Step 6 — Research the codebase
Read these files before writing the spec:
- `GEMINI.md` — roadmap, conventions, schema
- `app.py` — existing routes and structure
- `database/db.py` — existing schema and functions
- All files in `.gemini/specs/` — avoid duplicating existing specs

Validate `step_number` against the roadmap table in `GEMINI.md`:
- If the step number does **not** appear in the table, warn the user
  ("Step N does not exist in the GEMINI.md roadmap") and **stop**.
- If the step is already marked ✅ Done, warn the user and **stop**.

## Step 6.5 — Identify what already exists
Before writing the spec, scan the codebase for anything the new
feature can reuse:
- **`database/db.py`** — list helper functions already present
  (e.g. `get_db`, `get_user_by_email`) that this feature will call.
- **`app.py`** — list any existing routes, decorators, or utilities
  relevant to this feature.
- **`templates/`** — list any existing templates or partials
  (e.g. `base.html` blocks) this feature builds on.
- **`static/css/style.css`** — note CSS custom properties or
  component classes already defined that the new page should use.

Record your findings; they will populate the **Reuses** section
of the spec (Step 7). If nothing is reusable, write "Nothing to reuse".

## Step 7 — Write the spec
Generate a spec document with this exact structure:

---
# Spec: <feature_title>

## Overview
One paragraph describing what this feature does and why
it exists at this stage of the Spendly roadmap.

## Depends on
Which previous steps this feature requires to be complete.

## Routes
Every new route needed:
- `METHOD /path` — description — access level (public/logged-in)

If no new routes: state "No new routes".

## Reuses
Existing code this feature calls or extends — populated from
Step 6.5 research. List each item as:
- `file` — function / class / route / CSS token — how it is used

If nothing is reused: state "Nothing to reuse".

## Database changes
Any new tables, columns, or constraints needed.
Always verify against `database/db.py` before writing this.
If none: state "No database changes".

## Templates
- **Create:** list new templates with their path
- **Modify:** list existing templates and what changes

## Files to change
Every file that will be modified.

## Files to create
Every new file that will be created.

## New dependencies
Any new pip packages. If none: state "No new dependencies".

## Rules for implementation
Specific constraints Claude must follow. Always include:
- No SQLAlchemy or ORMs
- Parameterised queries only
- Passwords hashed with werkzeug
- Use CSS variables — never hardcode hex values
- All templates extend `base.html`

## Definition of done
A specific testable checklist. Each item must be
something that can be verified by running the app.
---

## Step 8 — Save the spec
Save to: `.gemini/specs/<step_number>-<feature_slug>.md`

## Step 9 — Report to the user
Print a short summary in this exact format:
```
Branch:    <branch_name>
Spec file: .gemini/specs/<step_number>-<feature_slug>.md
Title:     <feature_title>
```

Then tell the user:
"Review the spec at `.gemini/specs/<step_number>-<feature_slug>.md`
then enter Plan Mode with Shift+Tab twice to begin implementation."

Do not print the full spec in chat unless explicitly asked.