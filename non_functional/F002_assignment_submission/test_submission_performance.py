import os
import sys
import unittest
import time

from common.driver_factory import DriverFactory
from common.login_helper import LoginHelper

from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, StaleElementReferenceException


class SubmissionPerformanceTest(unittest.TestCase):
    """
    Non-Functional Test: Performance
    Measures the response time of the assignment submission save action.
    The entire save-and-confirm cycle must complete within 10 seconds.
    """

    ASSIGNMENT_URL = "https://school.moodledemo.net/mod/assign/view.php?id=871"
    DUMMY_FILE_PATH = os.path.join(os.getcwd(), "perf_dummy.txt")

    @classmethod
    def setUpClass(cls):
        # 1. Auto-Generate a Dummy Test File
        with open(cls.DUMMY_FILE_PATH, "w") as f:
            f.write("Performance test dummy file content.")
            
        cls.driver = DriverFactory.get_driver()
        cls.wait = WebDriverWait(cls.driver, 15)
        # Login as a standard student
        LoginHelper.login(cls.driver, username="student", password="moodle26")

    @classmethod
    def tearDownClass(cls):
        cls.driver.quit()
        # Delete the dummy file
        if os.path.exists(cls.DUMMY_FILE_PATH):
            os.remove(cls.DUMMY_FILE_PATH)

    # -----------------------------------------------------------------
    # Helper: Navigate with Policy Bypass
    # -----------------------------------------------------------------
    def _navigate(self, url):
        self.driver.get(url)
        time.sleep(2)

        bypassed = False
        for _ in range(5):
            page_text = self.driver.page_source.lower()
            if "policy" in page_text and ("agree" in page_text or "consent" in page_text or "next" in page_text):
                print("  [Auth] Policy interception detected. Bypassing...")
                bypassed = True
                checkboxes = self.driver.find_elements(By.XPATH, "//input[@type='checkbox']")
                for cb in checkboxes:
                    if not cb.is_selected():
                        self.driver.execute_script("arguments[0].click();", cb)
                next_btns = self.driver.find_elements(By.XPATH, "//button[@type='submit'] | //input[@type='submit']")
                if next_btns:
                    try:
                        next_btns[0].click()
                    except Exception:
                        self.driver.execute_script("arguments[0].click();", next_btns[0])
                time.sleep(3)
            else:
                break

        if bypassed:
            self.driver.get(url)
            time.sleep(2)

        self.wait.until(EC.presence_of_element_located((By.ID, "page")))

    # -----------------------------------------------------------------
    # Helper: Click Add / Edit Submission
    # -----------------------------------------------------------------
    def _click_add_or_edit_submission(self):
        locators = [
            (By.XPATH, "//button[contains(translate(., 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), 'submission')]"),
            (By.XPATH, "//a[contains(translate(., 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), 'submission')]"),
            (By.XPATH, "//input[@type='submit' and contains(translate(@value, 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), 'submission')]"),
            (By.XPATH, "//*[@id='id_submitbutton']"),
            (By.XPATH, "//button[contains(translate(., 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), 'attempt')]"),
            (By.XPATH, "//button[@type='submit' and not(contains(translate(., 'CANCEL', 'cancel'), 'cancel'))]"),
        ]
        for loc in locators:
            try:
                btn = WebDriverWait(self.driver, 3).until(EC.element_to_be_clickable(loc))
                self.driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", btn)
                time.sleep(1)
                try:
                    btn.click()
                except Exception:
                    self.driver.execute_script("arguments[0].click();", btn)
                time.sleep(3)
                return
            except TimeoutException:
                continue
        self.fail("'Add submission' / 'Edit submission' button not found.")

    # -----------------------------------------------------------------
    # Helper: Local File Upload
    # -----------------------------------------------------------------
    def _upload_local_file(self, file_path):
        driver = self.driver
        wait = self.wait

        # 1. Click Add...
        add_btn = wait.until(EC.element_to_be_clickable((By.CSS_SELECTOR, "a[title='Add...'], a[data-action='show-filepicker']")))
        driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", add_btn)
        time.sleep(1)
        driver.execute_script("arguments[0].click();", add_btn)
        time.sleep(2)

        # 2. Click the 'Upload a file' tab
        upload_tab = wait.until(EC.presence_of_element_located((By.XPATH, "//span[contains(text(), 'Upload a file')] | //a[contains(., 'Upload a file')]")))
        driver.execute_script("arguments[0].click();", upload_tab)
        time.sleep(2)
        
        # 3. Unhide file input and send_keys
        file_input = wait.until(EC.presence_of_element_located((By.XPATH, "//input[@type='file']")))
        driver.execute_script("arguments[0].style.display = 'block';", file_input)
        file_input.send_keys(file_path)
        
        # 4. Click 'Upload this file'
        upload_btn = wait.until(EC.presence_of_element_located((By.XPATH, "//button[contains(text(), 'Upload this file')]")))
        driver.execute_script("arguments[0].click();", upload_btn)
        
        # 5. CRITICAL TIMING: Wait for the modal mask to disappear
        try:
            WebDriverWait(driver, 10).until(
                EC.invisibility_of_element_located((By.CSS_SELECTOR, ".yui3-widget-mask, .moodle-dialogue-base"))
            )
        except TimeoutException:
            pass # Error dialog might have appeared
            
        time.sleep(2)

    # -----------------------------------------------------------------
    # Helper: Remove Submission (cleanup for repeatability)
    # -----------------------------------------------------------------
    def _remove_submission(self, url):
        driver = self.driver
        short_wait = WebDriverWait(driver, 10)
        driver.get(url)
        self.wait.until(EC.presence_of_element_located((By.ID, "page")))

        for loc in [
            (By.XPATH, "//button[contains(translate(., 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), 'remove submission')]"),
            (By.XPATH, "//a[contains(translate(., 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), 'remove submission')]"),
        ]:
            try:
                btn = short_wait.until(EC.presence_of_element_located(loc))
                if btn.is_displayed():
                    self.driver.execute_script("arguments[0].click();", btn)
                    confirm = short_wait.until(EC.presence_of_element_located((
                        By.XPATH,
                        "//button[contains(translate(., 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), 'continue')]"
                        "|//input[contains(translate(@value, 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), 'continue')]"
                    )))
                    self.driver.execute_script("arguments[0].click();", confirm)
                    try:
                        WebDriverWait(driver, 10).until(EC.staleness_of(confirm))
                    except TimeoutException:
                        pass
                    print("    [Cleanup] Submission removed.")
                    return
            except (TimeoutException, StaleElementReferenceException):
                continue
        print("    [Cleanup] No submission to remove.")

    # =================================================================
    # THE TEST
    # =================================================================
    def test_submission_save_response_time(self):
        """
        Measure the time taken from clicking 'Save changes' to Moodle
        confirming the submission. Must complete in under 10 seconds.
        """
        driver = self.driver
        wait = self.wait

        # Step 1: Navigate to the assignment
        self._navigate(self.ASSIGNMENT_URL)

        # Step 2: Click Add/Edit submission to enter the edit form
        self._click_add_or_edit_submission()

        # Step 3: Upload local file using the robust upload logic
        self._upload_local_file(self.DUMMY_FILE_PATH)

        # Step 4: Locate the Save button
        save_xpath = "//*[@id='id_submitbutton'] | //button[contains(., 'Save changes')] | //input[@value='Save changes']"
        save_btn = wait.until(EC.presence_of_element_located((By.XPATH, save_xpath)))
        driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", save_btn)
        time.sleep(1)

        # ============== START PERFORMANCE TIMER ==============
        start_time = time.time()

        try:
            save_btn.click()
        except Exception:
            driver.execute_script("arguments[0].click();", save_btn)

        # Wait for Moodle to process and display the confirmation page
        wait.until(EC.presence_of_element_located((By.ID, "page")))

        # Wait for the submission status text to confirm success
        try:
            WebDriverWait(driver, 10).until(
                lambda d: "submitted" in d.page_source.lower() or "grading" in d.page_source.lower()
            )
        except TimeoutException:
            pass  # We'll still measure time and assert below

        # ============== STOP PERFORMANCE TIMER ==============
        end_time = time.time()
        response_time = end_time - start_time

        print(f"\n  Submission save response time: {response_time:.2f} seconds")

        # Assert performance requirement: under 10 seconds
        self.assertLess(
            response_time, 10.0,
            f"Submission save took {response_time:.2f}s — exceeds 10-second threshold!"
        )

        # Step 5: Cleanup — remove the submission for repeatability
        self._remove_submission(self.ASSIGNMENT_URL)


if __name__ == "__main__":
    unittest.main()
