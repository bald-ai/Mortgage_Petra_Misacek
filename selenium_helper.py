# selenium_helper.py
from pathlib import Path

from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager

# Path to Playwright’s Chromium that you installed earlier
PLAYWRIGHT_CHROME = (
    Path.home()
    / ".cache"
    / "ms-playwright"
    / "chromium-1179"
    / "chrome-linux"
    / "chrome"
).as_posix()

def make_driver() -> webdriver.Chrome:
    opts = Options()
    opts.add_argument("--headless=new")
    opts.add_argument("--no-sandbox")
    opts.add_argument("--disable-gpu")
    opts.binary_location = PLAYWRIGHT_CHROME

    return webdriver.Chrome(
        service=Service(ChromeDriverManager().install()),
        options=opts,
    )