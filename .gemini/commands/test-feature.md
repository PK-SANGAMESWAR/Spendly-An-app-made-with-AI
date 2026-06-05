---
description: Writes and runs tests for a specific expense-tracker feature. Pass the spec name as argument e.g. /test-feature backend-connection
allowed-tools: Bash(python -m pytest)
---

Run the full testing pipeline for the feature specified 
in $ARGUMENTS.

If no argument is provided, stop immediately and say:
"Please provide a spec name. Usage: /test-feature 
<spec-name> e.g. /test-feature backend-connection"

If `.claude/specs/$ARGUMENTS.md` does not exist, stop 
immediately and say:
"Spec file not found at .claude/specs/$ARGUMENTS.md. 
Please check the spec name and try again."

---

## Step 1: Write Tests

**Test filename derivation**: Convert the spec name to a valid Python module name:
- Strip any step number prefix (e.g., `05-`)
- Convert all hyphens to underscores
- Prefix with `test_`
- Example: `05-backend-connection` → `tests/test_backend_connection.py`

Invoke the **test-generator** subagent with the following context:

- Spec file to base tests on: 
  `.claude/specs/$ARGUMENTS.md`
- Source files to read for fixture structure ONLY 
  (not test logic):
  - `database/db.py` (for helper function signatures)
  - `conftest.py` if it exists
- Output test file to create:
  `tests/test_[SPEC_NAME_CONVERTED].py` (using converted name above)
- Instruction: Write tests based on what the spec says 
  the feature SHOULD do. Do NOT read or reference 
  implementation code. Cover happy paths, edge cases, 
  auth guards, validation errors, and DB side effects.

**⚠️ Failure condition**: If test-generator does not confirm 
the test file has been created in its response, treat 
as failure and STOP. Do NOT proceed to Step 2.

---

## Step 2: Run Tests

Once test-generator has confirmed the test file is created, 
invoke the **test-runner** subagent with the following context:

- Test file to execute:
  `tests/test_[SPEC_NAME_CONVERTED].py` (same converted name as Step 1)
- Spec file for context:
  `.claude/specs/$ARGUMENTS.md`
- Source files to reference for failure diagnosis:
  - `app.py`
  - `database/db.py`
- Run command:
  `python -m pytest tests/test_[SPEC_NAME_CONVERTED].py -v`
- Instruction: Run ONLY the specified test file. Do 
  NOT run the full test suite. Analyze any failures by 
  cross-referencing test expectations against the spec 
  and implementation. Classify each failure as a bug 
  in the test (test issue) or a bug in implementation 
  (implementation issue).

---

## Handoff Rules

- Do NOT start Step 2 until Step 1 is fully complete 
  and test-generator explicitly confirms file creation
- Do NOT attempt to fix any code regardless of what 
  the test results show
- Do NOT run any tests beyond `tests/test_[SPEC_NAME_CONVERTED].py`
- If test-generator does not confirm the test file was 
  created, STOP immediately and report the reason — 
  do NOT proceed to Step 2
- If test-generator hangs or does not respond, treat as 
  failure and stop

---

## Final Output

After both subagents complete, produce a combined 
summary:

### Testing Pipeline Report — $ARGUMENTS

**Step 1 — Tests Written**
- List each test written with a one-line description 
  of which spec requirement it validates

**Step 2 — Test Results**
- Mirror the test-runner's structured report 
  (summary table, failures with diagnostics, warnings, verdict)

**Verdict**

One of:
- ✅ **Ready for code review** — all tests pass
  - Next: Update CLAUDE.md step status to ✅ Done
  - Commit the spec, tests, and implementation together
- ⚠️ **Partial** — X/Y tests passing
  - List the failing tests and their root causes (test issue vs implementation issue)
  - Recommend which to fix first
- ❌ **Needs fixes** — majority of tests failing
  - List all failing tests and their root causes
  - Recommend fix strategy