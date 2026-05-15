# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Selenium WebDriver UI test suite for **Moodle LMS** (`https://school.moodledemo.net`) using Python's `unittest` framework. Tests cover five features at multiple levels:

- **F001 Quiz Attempt and Result Review** — 10 test cases (TC001001 through TC001010), student role
- **F002 Assignment Submission** — 3 functional modules in L1 (add/cutoff/remove), 1 consolidated module in L2; mixed credentials (`student` and `ericwebb` for grading scenarios)
- **F003 Forum Discussion** — 14 test cases (TC-003-001 through TC-003-014), student role
- **F004 Glossary** — 1 module per level dispatching by `action_type` (add/search/browse/add_and_search_and_browse), student role
- **F005 Add Course** — 12 test cases (TC-005-001 through TC-005-012), manager role

| Level | Purpose | Locator source |
|-------|---------|---------------|
| **Level 1** | Functional UI tests | Hardcoded `By.*` tuples in Python |
| **Level 2** | Data-driven with externalized locators | `data/locators.json` resolved via `get_by()` or `_get_locator()` |
| **Non-functional** | Accessibility, reliability, performance, responsive, authorization | Data-driven CSV config (or hardcoded for F002/F005 authorization) |

## Credentials

| Role | Username | Password | Used by |
|------|----------|----------|---------|
| Student | `student` | `moodle26` | F001 (quiz), F002 (TC-002-001..006), F003 (forum), F004 (glossary) |
| Teacher | `ericwebb` | `moodle` | F002 (TC-002-007..009 grading scenarios) |
| Manager | `manager` | `moodle26` | F005 (course) |

## Running Tests

All commands from project root (`proj_3/`). Requires Chrome + ChromeDriver on PATH.

```bash
pip install -r requirements.txt

# Run all suites
python run_all.py

# Run a single feature/level
python -m unittest discover -s level1/F001_quiz_attempt_review -p "test_*.py" -v
python -m unittest discover -s level2/F001_quiz_attempt_review -p "test_*.py" -v
python -m unittest discover -s level1/F002_assignment_submission -p "test_*.py" -v
python -m unittest discover -s level2/F002_assignment_submission -p "test_*.py" -v
python -m unittest discover -s level1/F003_forum_discussion -p "test_*.py" -v
python -m unittest discover -s level2/F003_forum_discussion -p "test_*.py" -v
python -m unittest discover -s level1/F004_glossary -p "test_*.py" -v
python -m unittest discover -s level2/F004_glossary -p "test_*.py" -v
python -m unittest discover -s level1/F005_add_course -p "test_*.py" -v
python -m unittest discover -s level2/F005_add_course -p "test_*.py" -v
python -m unittest discover -s non_functional/F001_quiz_attempt_review -p "test_*.py" -v
python -m unittest discover -s non_functional/F002_assignment_submission -p "test_*.py" -v
python -m unittest discover -s non_functional/F003_forum_discussion -p "test_*.py" -v
python -m unittest discover -s non_functional/F004_glossary -p "test_*.py" -v
python -m unittest discover -s non_functional/F005_add_course -p "test_*.py" -v

# Run a single test module
python -m unittest level2.F003_forum_discussion.test_create_discussion_level2 -v
python -m unittest level1.F001_quiz_attempt_review.test_level_1 -v
```

Tests require live network access to `https://school.moodledemo.net`. The Moodle demo site resets periodically; transient failures on attachment/image-upload tests (TC-003-013) are a known flaky area.

**Known gap**: `run_all.py` only registers F001/F003/F005 directories. F002 and F004 must be run individually with `python -m unittest discover` until they are added to the `test_dirs` list.

## Architecture

### `common/` — Shared Utilities

All static-method classes, no instantiation needed:

- **`DriverFactory.get_driver(browser="chrome")`** — creates a maximized WebDriver
- **`LoginHelper.login(driver, url, username, password)`** — navigates to login page, fills credentials, waits for `#page`
- **`LoginHelper.ensure_logged_in(driver, return_url)`** — checks `#user-menu-toggle`; re-logins if session expired
- **`CSVReader.read_data(file_path, delimiter="\t")`** — returns `list[dict]` from tab-separated CSV
- **`Assertions`** — defined but unused; all tests use `self.assertIn()` directly

### Level 1 → Level 2 Difference

**F003/F005**: Level 1 and Level 2 have **identical test logic and CSV data**. The only difference is locator resolution:

- **Level 1**: `(By.ID, "id_subject")` hardcoded inline
- **Level 2**: `self.get_by("subject_input")` → reads `["id", "id_subject"]` from `locators.json` → returns `(By.ID, "id_subject")`

The `get_by()` method supports template interpolation for dynamic locators:
```python
self.get_by("discussion_link_template", subject="My Topic")
# locators.json: "discussion_link_template": ["xpath", "//a[contains(normalize-space(), '{subject}')]"]
# returns: (By.XPATH, "//a[contains(normalize-space(), 'My Topic')]")
```

Supported strategies in `locators.json`: `id`, `css selector`, `xpath`, `link text`, `partial link text`.

**F001**: Uses a different locator externalization pattern:
- **Level 1**: Locators hardcoded in `setUp()` as `self.loc_*` tuples
- **Level 2**: `locators.json` uses `{"by": "XPATH", "value": "..."}` dict format, resolved via `_get_locator(key)` → returns `(By.XPATH, "...")`
- F001 CSV uses **comma-separated** format (not tab-separated), read via Python's `csv.DictReader` directly (not `CSVReader`)
- F001 creates a fresh browser per CSV row (setUp/tearDown per row), unlike F003/F005 which share one driver across all rows

**F002**: Level 1 has **three separate test modules** (add/cutoff/remove) each reading their own CSV; Level 2 **consolidates them into one module** (`test_assignment_level2.py`) that loads all three CSVs and dispatches by file. Both levels switch credentials mid-run via `_switch_user_if_needed(test_id)` because TC-002-007..009 require teacher account `ericwebb`/`moodle` for grading scenarios. CSVs are **comma-separated**, header `Test ID,Test Case Name,Assignment URL,...`. Level 2 reuses the L1 CSVs (no separate L2 data files).

**F004**: One test module per level dispatching by `action_type` column (`add`, `search`, `browse`, `add_and_search_and_browse`). Both levels read **comma-separated CSVs** via `CSVReader.read_data(DATA_FILE, delimiter=",")` (overriding the default tab delimiter). Successful `add` rows get a `uuid.uuid4().hex[:4]` suffix appended to `concept`/`search_term`/`expected_text` to avoid duplicate-entry errors on the shared demo site.

### Test Class Pattern

**F003/F005** test classes follow this skeleton:

1. **`setUpClass()`** — load locators (L2), create driver, login, create prerequisite data if needed
2. **`tearDownClass()`** — quit driver
3. **`ensure_logged_in()`** — session guard delegating to `LoginHelper`
4. **`input_tinymce_message()`** — TinyMCE content entry (see below)
5. **Action helpers** — `create_seed_discussion()`, `click_reply()`, etc.
6. **`verify_result(expected_type, expected_text)`** — dispatches assertion by type
7. **Single `test_*_data_driven()` method** — iterates CSV rows with `self.subTest(test_case_id=...)`

**F001** test classes use a different pattern:

1. **`setUp()`** — define locators, initialize `self.driver = None`
2. **`tearDown()`** — call `_stop_driver()` for safety cleanup
3. **Per-row browser lifecycle** — `_start_driver()` / `_stop_driver()` called inside the test loop for each CSV row
4. **Flow methods** — `_login()`, `_open_course_and_quiz()`, `_fill_answers()`, `_finish_attempt()`, `_finish_review()`, `_logout()`
5. **`_verify_expected_parts(expected_text, seen_texts, label)`** — splits expected by comma, checks each part is substring of any seen text
6. **Error collection** — failures are collected in `self.errors[]` and reported at end via `self.fail()`

**Non-functional** test classes use the F003 pattern: `setUpClass`/`tearDownClass` with shared driver, CSV-driven (`CSVReader.read_data(...)` with `delimiter=","` for F004 / default `"\t"` for F003), `self.subTest()` iteration. Exceptions: F002 and F005 authorization tests (`test_*_authorization.py`) are single-method tests with hardcoded URLs and no CSV — they probe role-based access control by directly hitting privileged URLs as a non-privileged user.

### TinyMCE — Two Input Approaches

Moodle embeds TinyMCE in `iframe.tox-edit-area__iframe`. Two approaches coexist:

1. **Two-layer** (Create, Reply, DeleteReply, Attachment): switch into iframe → set `innerHTML` on `#tinymce` body → switch back → then sync via TinyMCE JS API (`setContent`, `fire('change')`, `save()`, `triggerSave()`) + hidden textarea events. More resilient when TinyMCE API hasn't fully initialized.

2. **API-only** (EditDiscussion, EditReply, DeleteDiscussion): wait for iframe presence but don't switch into it → set content purely via TinyMCE JS API + hidden textarea sync + `time.sleep(0.5)`. Works because the editor is already initialized when editing existing content.

### Seed Discussions and UUID Uniqueness

Edit, Reply, Delete, and Attachment tests create a **seed discussion** first with a `uuid.uuid4().hex[:6]` suffix to avoid collisions on the shared demo site. Successful create/edit operations also append UUID suffixes to subjects/short names.

### Locator Fallback Chains

Several methods try multiple locator strategies in sequence with short waits, failing only when all are exhausted:
- `click_add_discussion()` — 6 fallback locators for the "Add discussion" button
- `click_edit_for_reply()` / `click_delete_for_reply()` — 4 ancestor class names (`forumpost`, `forum-post-container`, `post-content-container`, `post`), then fallback to last Edit/Delete link on page

### Delete Confirmation

Combined XPath matching Moodle's version-variable confirm button (`Continue` | `Delete` | `Yes`), followed by `EC.staleness_of()` to confirm page redirect.

### Image Upload via TinyMCE

`upload_image_via_tinymce()` handles image attachment through TinyMCE's toolbar Image button → modal with hidden `input[type='file']` → alt text (5 locator fallbacks) or "Decorative image" checkbox → Save. A 1×1 px `sample_image.png` is auto-generated from base64 if missing.

## Data Files

### CSV Format
- **F003/F005**: **Tab-separated** (`\t` delimiter), header row, one row per test case. Read via `CSVReader.read_data()` with the default delimiter.
- **F001 functional**: **Comma-separated**, header row, read via Python `csv.DictReader` directly (not `CSVReader`).
- **F002 functional**: **Comma-separated**, header row uses Title Case keys (`Test ID`, `Assignment URL`, ...). L2 consumes the L1 CSVs directly — there are no L2-specific CSVs.
- **F004 functional**: **Comma-separated**, read via `CSVReader.read_data(file_path, delimiter=",")`.
- **Non-functional configs**: F003 uses tab-separated, F004 uses comma-separated. Both read via `CSVReader.read_data()` with explicit delimiter argument.
- Naming: `<action>_level<N>.csv` (functional), `<type>_config.csv` (non-functional)
- `expected_type` values — F003: `success`, `error_subject`, `error_message`, `deleted`; F004: `success`, `success_search`, `error_*`; F005: `success`, `success_return`, `cancel`, `error_full_name`, `error_short_name`, `error_category`, `error_date`, `error_multiple`

### `locators.json` Format
```json
{
    "logical_name": ["strategy", "value"],
    "template_name": ["xpath", "//a[contains(text(), '{variable}')]"]
}
```

## Coding Conventions

- `unittest.TestCase` only — no pytest
- `self.subTest(test_case_id=...)` for data-driven iteration
- `WebDriverWait(driver, 15)` with `EC.*` expected conditions — minimize `time.sleep()`
- `EC.staleness_of()` to confirm page navigation after form submission
- Class naming: `Forum<Action>Level<N>` (F003), `CourseCreateLevel<N>` (F005), `Level<N>DataDrivenTest` (F001), `AssignmentAddSubmissionLevel1` / `AssignmentLevel2` (F002), `GlossaryLevel<N>` (F004)
- Non-functional class naming: `Quiz<Type>Test` (F001), `Submission<Type>Test` (F002), `Forum<Type>Test` (F003), `Glossary<Type>Test` (F004)
- Console output — functional: `Running TC-XXX-NNN - Expected: ...` then `PASSED TC-XXX-NNN`
- Console output — non-functional: `Running NF-FNNN-XXX-NNN - <scenario>` then `PASSED NF-FNNN-XXX-NNN`
- Tab-separated CSV in `data/` subdirectory per feature (except F001/F002/F004 functional + F004 non-functional which use comma-separated)

## Constraints When Modifying

- Do not change credentials or the Moodle target site URL
- Do not convert away from `unittest` or add pytest
- Do not add dependencies beyond `selenium>=4.0.0`
- Do not modify Level 1 tests when implementing Level 2
- Do not submit/finish quiz attempts in F001 non-functional tests (no "Submit all and finish" confirmation)
- F002: do not hardcode the teacher account in shared utilities — credentials are selected per `test_id` via `_get_credentials()` (TC-002-007..009 use `ericwebb`/`moodle`, all others use `student`/`moodle26`); maintain `_current_user` state to avoid re-logging in unnecessarily between rows
- F004: append a `uuid.uuid4().hex[:4]` suffix to `concept`/`search_term`/`expected_text` for `add` rows so reruns don't collide with existing glossary entries
- New features: add `__init__.py`, register in `run_all.py`'s `test_dirs` list, update `README.md`. Note F002 and F004 are not yet registered in `run_all.py`
- `level1/F004_glossary/init.py` is misnamed (missing leading/trailing underscores). Test discovery via `python -m unittest discover -s level1/F004_glossary` still works because unittest's discovery only requires `__init__.py` for package imports, not for discovery. Renaming to `__init__.py` is recommended if F004 needs to be importable as a package (e.g., from `run_all.py`)
- The `.gitignore` blocks `*.png` — allowlist specific `sample_image.png` paths if adding new features
- F001 quiz has 93 answer inputs across 25 questions; scores are attempt-dependent on the shared demo site
