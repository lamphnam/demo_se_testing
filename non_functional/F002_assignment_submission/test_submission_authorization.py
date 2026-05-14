import os
import unittest

from common.driver_factory import DriverFactory
from common.login_helper import LoginHelper

from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC


class SubmissionAuthorizationTest(unittest.TestCase):
    """
    Non-Functional Test: Authorization / Security
    Verifies that a standard student cannot access the teacher's
    grading interface for an assignment.
    """

    ASSIGNMENT_URL = "https://school.moodledemo.net/mod/assign/view.php?id=871"

    @classmethod
    def setUpClass(cls):
        cls.driver = DriverFactory.get_driver()
        cls.wait = WebDriverWait(cls.driver, 15)
        # Login as a standard student — should NOT have grading rights
        LoginHelper.login(cls.driver, username="student", password="moodle26")

    @classmethod
    def tearDownClass(cls):
        cls.driver.quit()

    def test_student_cannot_access_grading_interface(self):
        """
        A student must be blocked from accessing the teacher's grading
        page by forcefully appending &action=grading to the assignment URL.
        Moodle should either display a permission error or silently ignore
        the action parameter and keep the user on the normal submission view.
        """
        driver = self.driver
        wait = self.wait

        # Step 1: Navigate to the assignment page normally
        driver.get(self.ASSIGNMENT_URL)
        wait.until(EC.presence_of_element_located((By.ID, "page")))

        # Step 2: Forcefully attempt to access the grading interface
        grading_url = self.ASSIGNMENT_URL + "&action=grading"
        driver.get(grading_url)
        wait.until(EC.presence_of_element_located((By.ID, "page")))

        page_source = driver.page_source.lower()

        # Check 1: Look for an explicit permission error message
        try:
            error_element = WebDriverWait(driver, 5).until(
                EC.visibility_of_element_located(
                    (By.CSS_SELECTOR, ".alert-danger, .errormessage, .accesshide + .alert")
                )
            )
            self.assertTrue(error_element.is_displayed())
            print(f"Authorization blocked correctly. Message: {error_element.text}")
            return
        except Exception:
            pass

        # Check 2: Moodle silently ignored the parameter — the grading
        # table should NOT be present in the DOM
        grading_table = driver.find_elements(
            By.CSS_SELECTOR,
            "table.generaltable.flexible, #grading-actions-panel, "
            "[data-region='grading-actions-panel'], .gradingtable"
        )
        self.assertEqual(
            len(grading_table), 0,
            "SECURITY ISSUE: Student can see the teacher's grading table!"
        )

        # Check 3: Verify "permission" or "not allowed" keywords are NOT
        # absent — i.e., at least the page didn't render the grading view
        grading_keywords = ["grading summary", "grade actions", "all submissions"]
        for keyword in grading_keywords:
            self.assertNotIn(
                keyword, page_source,
                f"SECURITY ISSUE: Grading keyword '{keyword}' found in page!"
            )

        print("Authorization enforced: Grading interface not accessible by student.")


if __name__ == "__main__":
    unittest.main()
