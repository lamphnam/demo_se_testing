import os
import unittest

from common.driver_factory import DriverFactory
from common.login_helper import LoginHelper
from common.csv_reader import CSVReader

from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC


BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_FILE = os.path.join(BASE_DIR, "data", "authorization_config.csv")


class SubmissionAuthorizationTest(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.driver = DriverFactory.get_driver()
        cls.wait = WebDriverWait(cls.driver, 15)

    @classmethod
    def tearDownClass(cls):
        cls.driver.quit()

    def read_test_data(self):
        return CSVReader.read_data(DATA_FILE, delimiter="\t")

    def test_authorization_data_driven(self):
        test_data = self.read_test_data()

        for row in test_data:
            test_case_id = row["test_case_id"]
            scenario = row["scenario"]
            assignment_url = row["assignment_url"]
            username = row["username"]
            password = row["password"]
            forbidden_action = row["forbidden_action"]

            print(f"\nRunning {test_case_id} - {scenario}")

            with self.subTest(test_case_id=test_case_id):
                LoginHelper.login(self.driver, username=username, password=password)

                self.driver.get(assignment_url)
                self.wait.until(EC.presence_of_element_located((By.ID, "page")))

                grading_url = assignment_url + forbidden_action
                self.driver.get(grading_url)
                self.wait.until(EC.presence_of_element_located((By.ID, "page")))

                page_source = self.driver.page_source.lower()

                # Check 1: explicit permission error
                try:
                    error_element = WebDriverWait(self.driver, 5).until(
                        EC.visibility_of_element_located(
                            (By.CSS_SELECTOR, ".alert-danger, .errormessage, .accesshide + .alert")
                        )
                    )
                    self.assertTrue(error_element.is_displayed(),
                                    f"{test_case_id}: Expected permission error to be visible.")
                    print(f"PASSED {test_case_id} - Authorization blocked with error message.")
                    continue
                except Exception:
                    pass

                # Check 2: grading table should NOT be present
                grading_table = self.driver.find_elements(
                    By.CSS_SELECTOR,
                    "table.generaltable.flexible, #grading-actions-panel, "
                    "[data-region='grading-actions-panel'], .gradingtable"
                )
                self.assertEqual(
                    len(grading_table), 0,
                    f"{test_case_id}: SECURITY ISSUE - Student can see the grading table!"
                )

                # Check 3: grading keywords should not appear
                grading_keywords = ["grading summary", "grade actions", "all submissions"]
                for keyword in grading_keywords:
                    self.assertNotIn(
                        keyword, page_source,
                        f"{test_case_id}: SECURITY ISSUE - Grading keyword '{keyword}' found!"
                    )

                print(f"PASSED {test_case_id} - Authorization enforced.")


if __name__ == "__main__":
    unittest.main()
