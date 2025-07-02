# selenium_helper.py
from pathlib import Path
import subprocess
import shutil, os

from selenium import webdriver
from selenium.webdriver.chrome.options import Options

def _find_playwright_chrome() -> str | None:
    """Return path to Playwright-managed Chromium binary, or None if not found."""
    # The browser is stored under ~/.cache/ms-playwright/chromium-*/chrome-linux/chrome
    cache_root = Path.home() / ".cache" / "ms-playwright"
    if not cache_root.exists():
        return None

    # Globbing for the first revision that contains the binary. The exact revision
    # number (e.g. chromium-1179) changes with Playwright releases, so we cannot
    # hard-code it.
    for revision_dir in sorted(cache_root.glob("chromium-*"), reverse=True):
        candidate = revision_dir / "chrome-linux" / "chrome"
        if candidate.exists():
            return candidate.as_posix()
    return None

def _ensure_playwright_chrome() -> str | None:
    path = _find_playwright_chrome()
    if path:
        return path
    # Try to install Chromium via playwright if not yet present
    try:
        subprocess.run(["playwright", "install", "chromium"], check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    except Exception as e:
        print("[WARN] Failed to install Playwright Chromium automatically:", e)
        return None
    return _find_playwright_chrome()

def _strip_stale_system_chromedriver() -> None:
    """Remove /usr/local/bin from PATH if an incompatible chromedriver sits there.

    On hosting platforms such as PythonAnywhere the directory /usr/local/bin is
    writable only by the base image and ships an outdated chromedriver (131 at
    the time of writing). We cannot delete or rename it, so we temporarily
    drop that directory from PATH for the current process before Selenium
    Manager runs its resolution algorithm.
    """
    sys_driver = shutil.which("chromedriver")
    if not sys_driver:
        return

    # If the driver is inside the user's home (very likely something we
    # installed ourselves), leave it alone. Otherwise (e.g. /usr/bin or
    # /usr/local/bin) drop that directory from PATH so Selenium Manager will
    # ignore it.
    home = str(Path.home())
    if not sys_driver.startswith(home):
        stale_dir = os.path.dirname(sys_driver)
        path_parts = [p for p in os.environ.get("PATH", "").split(os.pathsep) if p != stale_dir]
        os.environ["PATH"] = os.pathsep.join(path_parts)
        # If `chromedriver` still resolves (some other occurrence), recurse
        if shutil.which("chromedriver") and shutil.which("chromedriver") != sys_driver:
            _strip_stale_system_chromedriver()

def make_driver() -> webdriver.Chrome:
    """Create a headless Chrome driver whose binary is Playwright's Chromium.

    We rely on Selenium Manager (built into selenium>=4.10) to fetch the
    matching ChromeDriver automatically, avoiding version mismatches like:
        "This version of ChromeDriver only supports Chrome version 114".
    """
    opts = Options()
    opts.add_argument("--headless=new")
    opts.add_argument("--no-sandbox")
    opts.add_argument("--disable-gpu")

    # Ensure Selenium Manager does not pick the stale chromedriver shipped in
    # /usr/local/bin on PythonAnywhere (v131). We call this *before* touching
    # anything driver-related so that the lookup path is clean.
    _strip_stale_system_chromedriver()

    playwright_chrome = _ensure_playwright_chrome()
    if playwright_chrome:
        opts.binary_location = playwright_chrome

    # Let Selenium Manager pick/download the correct driver for the chosen
    # browser binary. A Service instance is *not* passed – that would override
    # Selenium Manager and re-introduce version-mismatch problems.
    return webdriver.Chrome(options=opts)