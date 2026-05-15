import os
import time
import unittest

from common.driver_factory import DriverFactory
from common.login_helper import LoginHelper
from common.csv_reader import CSVReader

from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, StaleElementReferenceException


BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_FILE = os.path.join(BASE_DIR, "data", "performance_config.csv")
DUMMY_FILE_PATH = os.path.join(BASE_DIR, "data", "files", "perf_dummy.txt")


class SubmissionPerformanceTest(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        if not os.path.exists(DUMMY_FILE_PATH):
            os.makedirs(os.path.dirname(DUMMY_FILE_PATH), exist_ok=True)
            with open(DUMMY_FILE_PATH, "w") as f:
                f.write("Performance test dummy file content.")

        cls.driver = DriverFactory.get_driver()
        cls.wait = WebDriverWait(cls.driver, 15)
        LoginHelper.login(cls.driver, username="student", password="moodle26")

    @classmethod
    def tearDownClass(cls):
        cls.driver.quit()

    def read_test_data(self):
        return CSVReader.read_data(DATA_FILE, delimiter="\t")

    def _navigate(self, url):
        self.driver.get(url)
        time.sleep(2)

        for _ in range(5):
            page_text = self.driver.page_source.lower()
            if "policy" in page_text and ("agree" in page_text or "consent" in page_text or "next" in page_text):
                checkboxes = self.driver.find_elements(By.XPATH, "//input[@type='checkbox']")
                for cb in checkboxes:
                    if not cb.is_selected():
                        self.driver.execute_script("arguments[0].click();", cb)
                next_btns = self.driver.find_elements(By.XPATH, "//button[@type='submit'] | //input[@type='submit']")
                if next_btns:
                    try:
                        next_btns[0].click()
                    except (StaleElementReferenceException, Exception):
                        self.driver.execute_script("arguments[0].click();", next_btns[0])
                time.sleep(3)
            else:
                break

        self.wait.until(EC.presence_of_element_located((By.ID, "page")))

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
                except (StaleElementReferenceException, Exception):
                    self.driver.execute_script("arguments[0].click();", btn)
                time.sleep(3)
                return
            except TimeoutException:
                continue
        self.fail("'Add submission' / 'Edit submission' button not found.")

    def _upload_local_file(self, file_path):
        driver = self.driver
        wait = self.wait

        add_btn = wait.until(EC.element_to_be_clickable(
            (By.CSS_SELECTOR, "a[title='Add...'], a[data-action='show-filepicker']")))
        driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", add_btn)
        time.sleep(1)
        driver.execute_script("arguments[0].click();", add_btn)
        time.sleep(2)

        upload_tab = wait.until(EC.presence_of_element_located(
            (By.XPATH, "//span[contains(text(), 'Upload a file')] | //a[contains(., 'Upload a file')]")))
        driver.execute_script("arguments[0].click();", upload_tab)
        time.sleep(2)

        file_input = wait.until(EC.presence_of_element_located((By.XPATH, "//input[@type='file']")))
        driver.execute_script("arguments[0].style.display = 'block';", file_input)
        file_input.send_keys(file_path)

        upload_btn = wait.until(EC.presence_of_element_located(
            (By.XPATH, "//button[contains(text(), 'Upload this file')]")))
        driver.execute_script("arguments[0].click();", upload_btn)

        try:
            WebDriverWait(driver, 10).until(
                EC.invisibility_of_element_located((By.CSS_SELECTOR, ".yui3-widget-mask, .moodle-dialogue-base"))
            )
        except TimeoutException:
            pass
        time.sleep(2)

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
                    return
            except (TimeoutException, StaleElementReferenceException):
                continue

    def test_performance_data_driven(self):
        test_data = self.read_test_data()

        for row in test_data:
            test_case_id = row["test_case_id"]
            scenario = row["scenario"]
            assignment_url = row["assignment_url"]
            threshold = float(row["threshold_seconds"])

            print(f"\nRunning {test_case_id} - {scenario}")

            with self.subTest(test_case_id=test_case_id):
                self._navigate(assignment_url)
                self._click_add_or_edit_submission()
                self._upload_local_file(DUMMY_FILE_PATH)

                save_xpath = "//*[@id='id_submitbutton'] | //button[contains(., 'Save changes')] | //input[@value='Save changes']"
                save_btn = self.wait.until(EC.presence_of_element_located((By.XPATH, save_xpath)))
                self.driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", save_btn)
                time.sleep(1)

                start_time = time.time()
                try:
                    save_btn.click()
                except (StaleElementReferenceException, Exception):
                    self.driver.execute_script("arguments[0].click();", save_btn)

                self.wait.until(EC.presence_of_element_located((By.ID, "page")))
                try:
                    WebDriverWait(self.driver, 10).until(
                        lambda d: "submitted" in d.page_source.lower() or "grading" in d.page_source.lower()
                    )
                except TimeoutException:
                    pass

                response_time = time.time() - start_time
                print(f"  Submission save response time: {response_time:.2f}s")

                self.assertLess(
                    response_time, threshold,
                    f"{test_case_id}: Submission save took {response_time:.2f}s — exceeds {threshold}s threshold!"
                )

                self._remove_submission(assignment_url)
                print(f"PASSED {test_case_id}")


if __name__ == "__main__":
    unittest.main()
