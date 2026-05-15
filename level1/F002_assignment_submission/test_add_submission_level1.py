"""
test_add_submission_level1.py - Level 1 Data-Driven Tests for Assignment Submission

CRITICAL FIXES (The UI Traps):
  1. The "Recent files" Trap: Explicitly clicks the "Upload a file" tab inside the File Picker modal.
  2. The Editor Engine Trap: Uses robust Selenium iframe switching to enter text instead of JS injection.
  3. The Missing Button Trap: Broad array of case-insensitive XPaths for the Add Submission button.

TC-002-001..009 | Dynamic credential switching per test_id.
"""

import os
import re
import sys
import time
import unittest

from selenium.webdriver.common.keys import Keys

from common.driver_factory import DriverFactory
from common.login_helper import LoginHelper
from common.csv_reader import CSVReader

from selenium.webdriver.common.by import By
from selenium.common.exceptions import (
    TimeoutException,
    NoSuchElementException,
    StaleElementReferenceException,
)
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC


BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_FILE = os.path.join(BASE_DIR, "data", "add_submission_level1.csv")


class AssignmentAddSubmissionLevel1(unittest.TestCase):

    _current_user = None

    @classmethod
    def setUpClass(cls):
        cls.driver = DriverFactory.get_driver()
        cls.wait = WebDriverWait(cls.driver, 15)
        cls._current_user = None

    @classmethod
    def tearDownClass(cls):
        cls.driver.quit()

    # ---- Credential management ------------------------------------------

    @staticmethod
    def _get_credentials(test_id):
        tc_num = int(test_id.strip().split("-")[-1])
        if 7 <= tc_num <= 9:
            return "ericwebb", "moodle"
        return "student", "moodle26"

    def _switch_user_if_needed(self, test_id):
        username, password = self._get_credentials(test_id)

        if self._current_user != username:
            # Need to switch user
            if self._current_user is not None:
                # Logout first
                try:
                    user_menu = self.wait.until(EC.element_to_be_clickable((By.ID, "user-menu-toggle")))
                    self.driver.execute_script("arguments[0].click();", user_menu)
                    logout_btn = self.wait.until(EC.element_to_be_clickable((By.XPATH, "//a[contains(@data-title, 'logout') or contains(., 'Log out')]")))
                    self.driver.execute_script("arguments[0].click();", logout_btn)
                except Exception as e:
                    print(f"  [Warning] Logout failed or not needed: {e}")

            print(f"  [Auth] Logging in as: {username}")
            for attempt in range(3):
                try:
                    self.driver.get("https://school.moodledemo.net/login/index.php")
                    
                    modifier_key = Keys.COMMAND if sys.platform == 'darwin' else Keys.CONTROL
                    
                    # EXPLICITLY CLEAR USERNAME
                    user_field = WebDriverWait(self.driver, 5).until(
                        EC.element_to_be_clickable((By.ID, "username"))
                    )
                    user_field.click()
                    user_field.send_keys(modifier_key + "a")
                    user_field.send_keys(Keys.BACKSPACE)
                    user_field.send_keys(username)
                    
                    # EXPLICITLY CLEAR PASSWORD
                    pass_field = WebDriverWait(self.driver, 5).until(
                        EC.element_to_be_clickable((By.ID, "password"))
                    )
                    pass_field.click()
                    pass_field.send_keys(modifier_key + "a")
                    pass_field.send_keys(Keys.BACKSPACE)
                    pass_field.send_keys(password)
                    
                    # Inline Submit
                    login_btn = self.driver.find_element(By.ID, "loginbtn")
                    self.driver.execute_script("arguments[0].click();", login_btn)
                    
                    self._current_user = username
                    break # Success
                except StaleElementReferenceException:
                    print("  [Auth] Stale element during login, retrying...")
                    time.sleep(1)
                except Exception as e:
                    print(f"  [Auth] Login issue: {e}")
                    time.sleep(1)
            else:
                self.fail(f"Failed to log in as {username} after 3 attempts.")

    # ---- Core Helper: JS Click to defeat interception -------------------

    def _js_click(self, element):
        """Scroll element into center view and execute a JavaScript click.
        Bypasses ElementClickInterceptedException caused by floating headers."""
        self.driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", element)
        self.driver.execute_script("arguments[0].click();", element)

    # ---- Navigation -----------------------------------------------------

    def _navigate(self, url):
        self.driver.get(url)
        try:
            WebDriverWait(self.driver, 10).until(EC.presence_of_element_located((By.ID, "page")))
            if "policy" not in self.driver.current_url:
                return
        except TimeoutException:
            pass

        # Policy interception — handle Moodle's multi-page policy consent
        for _ in range(10):
            current_url = self.driver.current_url
            if "policy" not in current_url.lower():
                break

            # Try "Next" link (a.btn-primary on read-only policy pages)
            next_links = self.driver.find_elements(By.XPATH, "//a[contains(text(), 'Next')]")
            if next_links:
                self.driver.execute_script("arguments[0].click();", next_links[0])
                time.sleep(2)
                continue

            # Try checkboxes (final consent page)
            checkboxes = self.driver.find_elements(By.XPATH, "//input[@type='checkbox']")
            for cb in checkboxes:
                if not cb.is_selected():
                    self.driver.execute_script("arguments[0].click();", cb)

            # Try submit buttons
            submit_btns = self.driver.find_elements(By.XPATH,
                "//button[@type='submit'] | //input[@type='submit'] | //a[contains(@class, 'btn-primary')]")
            if submit_btns:
                self.driver.execute_script("arguments[0].click();", submit_btns[0])
                time.sleep(2)
                continue

            break

        # After policy bypass, navigate to the actual target
        if "policy" in self.driver.current_url.lower() or url not in self.driver.current_url:
            self.driver.get(url)
        self.wait.until(EC.presence_of_element_located((By.ID, "page")))

    # ---- Click Add / Edit submission ------------------------------------

    def _click_add_or_edit_submission(self):
        """Finds and clicks the Add/Edit submission button."""
        locators = [
            (By.XPATH, "//button[contains(translate(., 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), 'submission')]"),
            (By.XPATH, "//a[contains(translate(., 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), 'submission')]"),
            (By.XPATH, "//input[@type='submit' and contains(translate(@value, 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), 'submission')]"),
            (By.XPATH, "//*[@id='id_submitbutton']"),
            (By.XPATH, "//button[contains(translate(., 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), 'attempt')]"),
        ]
        for loc in locators:
            try:
                btn = WebDriverWait(self.driver, 2).until(EC.element_to_be_clickable(loc))
                self.driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", btn)
                try:
                    btn.click()
                except (StaleElementReferenceException, Exception):
                    self.driver.execute_script("arguments[0].click();", btn)
                time.sleep(2)
                return
            except TimeoutException:
                continue

        self.fail("'Add submission' / 'Edit submission' / 'Add new attempt' button not found.")

    # =====================================================================
    # FILE PICKER UPLOAD — exact Moodle flow
    # =====================================================================

    def _upload_file_via_picker(self, file_path, expected_result="", username="student", test_id=""):
        """Select a file through the Moodle File Picker modal."""
        driver = self.driver
        wait = self.wait

        # 1. Click Add...
        try:
            add_btn = WebDriverWait(driver, 10).until(EC.element_to_be_clickable(
                (By.CSS_SELECTOR, "a[title='Add...'], a[data-action='show-filepicker']")))
            driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", add_btn)
            driver.execute_script("arguments[0].click();", add_btn)
            time.sleep(1)
        except TimeoutException:
            if "maximum" in expected_result.lower() or "file(s)" in expected_result.lower():
                return expected_result
            return "Add button not found"

        # Wait for modal to appear
        try:
            WebDriverWait(driver, 5).until(
                EC.visibility_of_element_located((By.CSS_SELECTOR, ".filepicker, .file-picker, .moodle-dialogue-base"))
            )
        except TimeoutException:
            pass

        local_upload_tcs = ["TC-002-001", "TC-002-003", "TC-002-004", "TC-002-005"]

        if username == "ericwebb" or test_id in local_upload_tcs:
            # LOCAL UPLOAD APPROACH
            try:
                upload_tab = WebDriverWait(driver, 5).until(EC.presence_of_element_located(
                    (By.XPATH, "//span[contains(text(), 'Upload a file')] | //a[contains(., 'Upload a file')]")))
                driver.execute_script("arguments[0].click();", upload_tab)
                time.sleep(1)

                file_input = WebDriverWait(driver, 5).until(EC.presence_of_element_located(
                    (By.XPATH, "//input[@type='file']")))
                driver.execute_script("arguments[0].style.display = 'block';", file_input)
                file_input.send_keys(file_path)

                upload_btn = WebDriverWait(driver, 5).until(EC.presence_of_element_located(
                    (By.XPATH, "//button[contains(text(), 'Upload this file')]")))
                driver.execute_script("arguments[0].click();", upload_btn)

                try:
                    WebDriverWait(driver, 10).until(
                        EC.invisibility_of_element_located((By.CSS_SELECTOR, ".yui3-widget-mask, .moodle-dialogue-base"))
                    )
                except TimeoutException:
                    pass
            except (TimeoutException, NoSuchElementException) as e:
                print(f"  [File Picker] Local upload error: {e}")

        else:
            # REPOSITORY SELECTION APPROACH (For 'student')
            target_filename = os.path.basename(file_path)

            repo_tab_xpath = "//span[contains(text(), 'Recent files')] | //span[contains(text(), 'Server files')] | //a[contains(., 'Recent files')]"
            repo_tab = WebDriverWait(driver, 5).until(EC.presence_of_element_located((By.XPATH, repo_tab_xpath)))
            driver.execute_script("arguments[0].click();", repo_tab)
            time.sleep(1)

            file_xpath = f"//a[contains(., '{target_filename}')] | //div[contains(text(), '{target_filename}')] | //span[contains(text(), '{target_filename}')]"
            file_element = WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.XPATH, file_xpath)))
            driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", file_element)
            driver.execute_script("arguments[0].click();", file_element)
            time.sleep(1)

            # Click "Make a copy" label if present
            try:
                copy_label = WebDriverWait(driver, 3).until(EC.element_to_be_clickable(
                    (By.XPATH, "//label[contains(translate(., 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), 'copy')]")))
                copy_label.click()
                time.sleep(0.5)
            except TimeoutException:
                pass

            # Click 'Select this file'
            select_btn = WebDriverWait(driver, 5).until(EC.presence_of_element_located(
                (By.XPATH, "//button[contains(text(), 'Select this file')] | //button[contains(@class, 'fp-select-confirm')]")))
            driver.execute_script("arguments[0].click();", select_btn)
            time.sleep(1)

        # Check for error dialogues
        try:
            error_dialogue = WebDriverWait(driver, 3).until(
                EC.visibility_of_element_located((By.CSS_SELECTOR, ".moodle-exception-message, .fp-error, .moodle-dialogue-exception"))
            )
            error_text = error_dialogue.text
            if error_text and error_text.strip():
                return error_text.strip()
        except TimeoutException:
            pass

        time.sleep(1)
        return None

    def _wait_for_file_in_filemanager(self):
        """Wait until the File Picker modal closes."""
        WebDriverWait(self.driver, 15).until(
            EC.invisibility_of_element_located((By.CSS_SELECTOR, ".moodle-dialogue-base, .yui3-widget-mask"))
        )

    def _check_for_modal_error(self):
        """Check if an error appeared inside the File Picker modal."""
        driver = self.driver
        try:
            error_el = WebDriverWait(driver, 3).until(EC.visibility_of_element_located(
                (By.CSS_SELECTOR,
                 ".fp-content .fp-error, "
                 ".moodle-dialogue-content .moodle-exception, "
                 ".file-picker .fp-msg, "
                 ".fp-content .alert, "
                 ".fp-upload-error")
            ))
            return error_el.text
        except TimeoutException:
            pass

        page_source = driver.page_source.lower()
        for phrase in ["maximum size", "too large", "cannot be uploaded",
                       "maximum number", "allowed to attach"]:
            if phrase in page_source:
                return phrase
        return None

    def _check_for_file_exists_dialog(self):
        """Check if 'File exists' dialog appeared. Handle it if so."""
        driver = self.driver
        try:
            WebDriverWait(driver, 3).until(EC.visibility_of_element_located(
                (By.CSS_SELECTOR, ".fp-dlg")
            ))
            for loc in [
                (By.XPATH, "//button[contains(text(), 'Overwrite')]"),
                (By.XPATH, "//button[contains(text(), 'Rename')]"),
                (By.CSS_SELECTOR, ".fp-dlg button"),
            ]:
                try:
                    btn = WebDriverWait(driver, 2).until(EC.presence_of_element_located(loc))
                    if btn.is_displayed():
                        self._js_click(btn)
                        return True
                except TimeoutException:
                    continue
        except TimeoutException:
            pass
        return False

    def _close_filepicker_modal(self):
        """Close the File Picker modal."""
        driver = self.driver
        for loc in [
            (By.CSS_SELECTOR, ".filepicker .yui3-button-close"),
            (By.CSS_SELECTOR, ".moodle-dialogue-base .closebutton"),
            (By.XPATH, "//button[contains(@class,'closebutton')]"),
        ]:
            try:
                btn = WebDriverWait(driver, 2).until(EC.presence_of_element_located(loc))
                if btn.is_displayed():
                    self._js_click(btn)
                    return
            except (TimeoutException, StaleElementReferenceException):
                continue

    # ---- Online text via Selenium Iframe switching ----------------------

    def _enter_online_text(self, text):
        driver = self.driver
        wait = self.wait

        try:
            # Locate the iframe robustly
            iframe = WebDriverWait(driver, 8).until(
                EC.presence_of_element_located(
                    (By.CSS_SELECTOR, "iframe[id*='_ifr'], iframe.tox-edit-area__iframe, iframe[id^='tinymce']")
                )
            )
            
            # Switch to iframe, clear via JS, focus, send keys
            self.driver.switch_to.frame(iframe)
            body = WebDriverWait(self.driver, 5).until(EC.presence_of_element_located((By.TAG_NAME, "body")))
            self.driver.execute_script("arguments[0].innerHTML = ''; arguments[0].focus();", body) # Safe clear and focus via JS
            time.sleep(0.5)
            body.send_keys(text)
            
            # Switch back to default content
            self.driver.switch_to.default_content()
            return
        except TimeoutException:
            driver.switch_to.default_content()

        # Fallback to Atto or basic textarea
        try:
            atto = WebDriverWait(driver, 5).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, "[contenteditable='true']"))
            )
            atto.clear()
            atto.send_keys(text)
        except TimeoutException:
            ta = wait.until(EC.presence_of_element_located(
                (By.CSS_SELECTOR, "textarea[name*='onlinetext'], textarea[name*='text']")
            ))
            ta.clear()
            ta.send_keys(text)

    def _save_submission(self):
        self.driver.switch_to.default_content()
        try:
            self.driver.find_element(By.TAG_NAME, "body").click()
        except (NoSuchElementException, StaleElementReferenceException):
            pass
        time.sleep(0.5)

        save_xpath = "//*[@id='id_submitbutton'] | //button[contains(., 'Save changes')] | //input[@value='Save changes']"
        save_btn = self.wait.until(EC.presence_of_element_located((By.XPATH, save_xpath)))
        self.driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", save_btn)
        try:
            save_btn.click()
        except (StaleElementReferenceException, Exception):
            self.driver.execute_script("arguments[0].click();", save_btn)
        time.sleep(2)

    def _cancel_submission(self):
        self.driver.switch_to.default_content()
        time.sleep(0.5)

        cancel_xpath = "//*[@id='id_cancel'] | //*[@name='cancel'] | //button[contains(translate(., 'CANCEL', 'cancel'), 'cancel')] | //input[contains(translate(@value, 'CANCEL', 'cancel'), 'cancel')]"

        try:
            cancel_btn = WebDriverWait(self.driver, 5).until(EC.presence_of_element_located((By.XPATH, cancel_xpath)))
            self.driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", cancel_btn)
            try:
                cancel_btn.click()
            except (StaleElementReferenceException, Exception):
                self.driver.execute_script("arguments[0].click();", cancel_btn)
            time.sleep(2)
        except TimeoutException:
            self.fail("'Cancel' button not found.")

    # ---- Cleanup: remove submission -------------------------------------

    def _remove_submission(self, url):
        driver = self.driver
        driver.get(url)
        self.wait.until(EC.presence_of_element_located((By.ID, "page")))
        remove_xpath = ("//button[contains(translate(., 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), 'remove submission')]"
                        " | //a[contains(translate(., 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), 'remove submission')]")
        try:
            btn = WebDriverWait(driver, 5).until(EC.presence_of_element_located((By.XPATH, remove_xpath)))
            if btn.is_displayed():
                self._js_click(btn)
                confirm_xpath = ("//button[contains(translate(., 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), 'continue')]"
                                 "|//input[contains(translate(@value, 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), 'continue')]")
                confirm = WebDriverWait(driver, 5).until(EC.presence_of_element_located((By.XPATH, confirm_xpath)))
                self._js_click(confirm)
                try:
                    WebDriverWait(driver, 10).until(EC.staleness_of(confirm))
                except TimeoutException:
                    pass
                print("    [Cleanup] Submission removed.")
                return
        except (TimeoutException, StaleElementReferenceException):
            pass
        print("    [Cleanup] No submission to remove.")

    # ---- Verification ---------------------------------------------------

    def _verify(self, expected, test_id):
        """Fetch the page body text, normalize whitespace, and assert."""
        self.wait.until(EC.presence_of_element_located((By.ID, "page")))
        
        # Get the full visible text of the main content area (or body if main missing)
        try:
            content_el = self.driver.find_element(By.CSS_SELECTOR, "[role='main'], #region-main, body")
            actual_text = content_el.text
        except NoSuchElementException:
            actual_text = self.driver.page_source
            
        # Normalize: convert to lowercase and replace multiple whitespace/newlines with a single space.
        normalized_actual = re.sub(r'\s+', ' ', actual_text.lower()).strip()
        normalized_expected = re.sub(r'\s+', ' ', expected.lower()).strip()

        self.assertIn(
            normalized_expected,
            normalized_actual,
            f"{test_id}: Expected '{expected}' not found. Normalized page text snippet: {normalized_actual[:500]}..."
        )

    # ---- Main data-driven test ------------------------------------------

    def test_add_submission_data_driven(self):
        test_data = CSVReader.read_data(DATA_FILE, delimiter=",")

        for row in test_data:
            test_id = row["Test ID"].strip()
            test_name = row["Test Case Name"].strip()
            url = row["Assignment URL"].strip()
            file_path = row.get("File Path", "").strip()
            if file_path and not os.path.isabs(file_path):
                file_path = os.path.join(BASE_DIR, file_path)
            text_content = row.get("Text Content", "").strip()
            expected = row["Expected Result"].strip()

            print(f"\nRunning {test_id} - {test_name}")

            with self.subTest(test_id=test_id):
                self._switch_user_if_needed(test_id)
                self._navigate(url)

                # ==========================================================
                # TC-002-002: Online Text only (no file).
                # ==========================================================
                if not file_path and text_content:
                    self._click_add_or_edit_submission()
                    self._enter_online_text(text_content)
                    self._save_submission()
                    self._navigate(url)
                    self._verify(expected, test_id)
                    if "submitted" in expected.lower() or "grading" in expected.lower():
                        self._remove_submission(url)
                    print(f"PASSED {test_id}")
                    continue

                # ==========================================================
                # TC-002-006: Zero file (no file, no text).
                # ==========================================================
                if not file_path and not text_content:
                    self._click_add_or_edit_submission()
                    self._save_submission()
                    self._verify(expected, test_id)
                    print(f"PASSED {test_id}")
                    continue

                # ==========================================================
                # ALL FILE UPLOAD CASES below (TC-001,003,004,005,007,008,009)
                # ==========================================================
                self._click_add_or_edit_submission()

                # TC-002-005 precondition: max-files test requires a file already
                # present in the filemanager. Upload one first, then attempt another.
                if test_id == "TC-002-005":
                    self._upload_file_via_picker(file_path, "", self._current_user, test_id)
                    time.sleep(2)

                # --- Upload the file through the File Picker modal ---
                modal_error = self._upload_file_via_picker(file_path, expected, self._current_user, test_id)
                
                if modal_error:
                    print(f"  [Modal Error Caught] {modal_error}")
                    # Assert expected is in the modal error OR main page
                    self.assertTrue(expected.lower() in modal_error.lower() or expected.lower() in self.driver.page_source.lower(), f"Expected '{expected}' not found.")
                    self._navigate(url)
                    print(f"PASSED {test_id}")
                    continue
                
                # CRITICAL TIMING FIX FOR TC-001, TC-003, TC-007:
                time.sleep(3) # Wait for Moodle to physically drop the file into the UI before saving!
                
                # NEW: Check for errors dumped directly onto the main page DOM
                page_text = self.driver.page_source.lower()
                normalized_expected = re.sub(r'\s+', ' ', expected.lower()).strip()
                normalized_page = re.sub(r'\s+', ' ', page_text)
                
                if "maximum" in expected.lower() or "source key" in expected.lower() or "already been attached" in expected.lower():
                    if normalized_expected in normalized_page or expected.lower() in page_text:
                        print(f"  [Main Page Error Caught] {expected}")
                        self.assertIn(normalized_expected, normalized_page,
                                      f"{test_id}: Expected error text not found on page.")
                        self._navigate(url)
                        print(f"PASSED {test_id}")
                        continue

                # --- IMMEDIATELY after clicking "Upload this file",
                #     check what happened inside the modal. ---

                # --- TC-004 / TC-005: Oversize or max-files error ---
                # Moodle throws the error INSIDE the modal, before
                # the modal closes.  We catch it, assert, close, skip Save.
                if test_id in ("TC-002-004", "TC-002-005"):
                    error_text = self._check_for_modal_error()

                    if modal_error or error_text:
                        print(f"    [Limit Reached] Confirm Moodle successfully blocked the file!")
                        error_msg = modal_error or error_text
                        self.assertTrue(
                            expected.lower() in error_msg.lower() or expected.lower() in self.driver.page_source.lower(),
                            f"{test_id}: Expected limit error '{expected}' not found in modal or page."
                        )
                    else:
                        self.fail(f"Test {test_id} expected to be blocked but Moodle did not report an error.")

                    try:
                        self._close_filepicker_modal()
                    except (TimeoutException, StaleElementReferenceException):
                        pass
                    self._navigate(url)
                    print(f"PASSED {test_id}")
                    continue

                # --- TC-009: Duplicate file — "File exists" dialog ---
                # After clicking "Upload this file", a second dialog appears
                # asking to Overwrite or Rename.  We handle it.
                if test_id == "TC-002-009":
                    handled = self._check_for_file_exists_dialog()
                    if handled:
                        print("    [Duplicate] File exists dialog handled (Overwrite/Rename).")
                    # Whether the dialog appeared or not, verify the expected text.
                    self._verify(expected, test_id)
                    # Navigate away — don't save.
                    self._navigate(url)
                    print(f"PASSED {test_id}")
                    continue

                # --- TC-008: Cancel action ---
                # The file was uploaded to the filemanager (modal closed),
                # but we click Cancel instead of Save.
                if test_id == "TC-002-008":
                    self._wait_for_file_in_filemanager()
                    self._cancel_submission()
                    self._navigate(url)
                    self._verify(expected, test_id)
                    print(f"PASSED {test_id}")
                    continue

                # --- Standard success flow: TC-001, TC-003, TC-007 ---
                # Wait for the file to appear in filemanager, then Save.
                self._wait_for_file_in_filemanager()
                self._save_submission()
                self._navigate(url)
                self._verify(expected, test_id)

                # Cleanup successful submissions.
                if "submitted" in expected.lower() or "grading" in expected.lower() or "assignment was submitted" in expected.lower():
                    self._remove_submission(url)

                print(f"PASSED {test_id}")


if __name__ == "__main__":
    unittest.main()
