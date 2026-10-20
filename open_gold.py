"""Open GOLD in the installed Firefox (Selenium) with a dedicated, persistent profile.

Edge can't be automated here: Orange IT sets RemoteDebuggingAllowed = 0.
First run: if GOLD asks you to log in, do it in the Firefox window. The script
waits up to 5 minutes for GOLD to load, then saves a screenshot and the page
text (including frames) to output/.
"""
import os
import shutil
import sys
import time
from pathlib import Path

from selenium import webdriver
from selenium.common.exceptions import WebDriverException
from selenium.webdriver.common.by import By
from selenium.webdriver.firefox.options import Options
from selenium.webdriver.firefox.service import Service

GOLD_URL = "https://gold.sso.infra.ftgroup/home/gold/jsp/Guardian.jsp"
APP_NAME = "GOLD Express"
FROZEN = getattr(sys, "frozen", False)  # running as the packaged GOLD Express.exe
# Where bundled files live (PyInstaller unpacks them to sys._MEIPASS).
BUNDLE_DIR = Path(getattr(sys, "_MEIPASS", Path(__file__).parent))
# Where settings/output go: next to the scripts, or Documents\GOLD Express for the .exe.
HERE = Path.home() / "Documents" / APP_NAME if FROZEN else Path(__file__).parent
_OLD_HERE = Path.home() / "Documents" / "GOLD Assistant"  # the app's earlier name
if FROZEN and not HERE.exists() and (_OLD_HERE / "gold_app_settings.json").exists():
    HERE.mkdir(parents=True, exist_ok=True)  # keep the user's folders/settings from before
    shutil.copy2(_OLD_HERE / "gold_app_settings.json", HERE / "gold_app_settings.json")
# Kept out of OneDrive. GOLD_PROFILE_DIR lets a second copy (e.g. a test run) use its own profile
# while the app is open: Firefox can't share one profile between two windows.
PROFILE_DIR = Path(os.environ.get("GOLD_PROFILE_DIR")
                   or Path.home() / ".gold-automation" / "firefox-profile")
OUT_DIR = HERE / "output"
DOWNLOAD_DIR = OUT_DIR / "downloads"
LOGIN_TIMEOUT_S = 300


def find_firefox():
    for base in (os.environ.get("ProgramFiles"), os.environ.get("ProgramFiles(x86)"),
                 os.environ.get("LOCALAPPDATA")):
        if base:
            exe = Path(base) / "Mozilla Firefox" / "firefox.exe"
            if exe.exists():
                return str(exe)
    exe = shutil.which("firefox")
    if exe:
        return exe
    raise RuntimeError(f"Firefox is not installed. {APP_NAME} needs Mozilla Firefox.")


def find_geckodriver():
    """Bundled geckodriver (packaged app) or one next to the scripts; else None and
    Selenium Manager fetches it (needs internet)."""
    for p in (BUNDLE_DIR / "geckodriver.exe", Path(__file__).parent / "geckodriver.exe"):
        if p.exists():
            return str(p)
    return None


def start_firefox(headless=False):
    """headless=True runs Firefox in the background (no window); GOLD's SSO still signs in."""
    PROFILE_DIR.mkdir(parents=True, exist_ok=True)
    DOWNLOAD_DIR.mkdir(parents=True, exist_ok=True)
    opts = Options()
    opts.binary_location = find_firefox()
    if headless:
        opts.add_argument("-headless")
        opts.add_argument("--width=1600")  # page size for screenshots
        opts.add_argument("--height=1000")
    opts.add_argument("-profile")
    opts.add_argument(str(PROFILE_DIR))
    # Save GOLD documents straight to DOWNLOAD_DIR, no "open/save" dialog, PDFs not opened inline.
    opts.set_preference("browser.download.folderList", 2)
    opts.set_preference("browser.download.dir", str(DOWNLOAD_DIR))
    opts.set_preference("browser.download.useDownloadDir", True)
    opts.set_preference("browser.download.always_ask_before_handling_new_types", False)
    opts.set_preference("browser.download.alwaysOpenPanel", False)
    opts.set_preference("pdfjs.disabled", True)
    opts.set_preference(
        "browser.helperApps.neverAsk.saveToDisk",
        "application/pdf,application/octet-stream,application/vnd.ms-excel,"
        "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet,application/msword,"
        "application/vnd.openxmlformats-officedocument.wordprocessingml.document,"
        "text/plain,text/csv,text/xml,application/xml,image/png,image/jpeg,application/zip",
    )
    gecko = find_geckodriver()
    service = Service(executable_path=gecko) if gecko else Service()
    if FROZEN:  # no console window for geckodriver in the packaged app
        service.creation_flags = 0x08000000  # CREATE_NO_WINDOW
    try:
        driver = webdriver.Firefox(options=opts, service=service)
    except WebDriverException as e:
        if "unexpectedly closed" in str(e) or "already running" in str(e).lower():
            raise RuntimeError(
                "Firefox could not start because its GOLD profile is already in use - another copy of "
                f"{APP_NAME} (or the older 'GOLD Assistant') is probably still open. Close it "
                "(check the taskbar and system tray), then try again.") from None
        raise
    if not headless:
        driver.maximize_window()
    return driver


def page_text(driver):
    """Text of the main document plus every (nested) frame."""
    chunks = []

    def walk(label):
        try:
            chunks.append(f"=== {label}\n" + driver.find_element(By.TAG_NAME, "body").text)
        except Exception:
            pass
        frames = driver.find_elements(By.CSS_SELECTOR, "frame, iframe")
        for i, fr in enumerate(frames):
            name = fr.get_attribute("name") or fr.get_attribute("id") or str(i)
            try:
                driver.switch_to.frame(fr)
                walk(f"{label} > {name} ({driver.execute_script('return location.href')})")
            finally:
                driver.switch_to.parent_frame()

    driver.switch_to.default_content()
    walk("(main)")
    return "\n\n".join(chunks)


def wait_for_gold(driver, timeout=LOGIN_TIMEOUT_S):
    """Wait until SSO is done and GOLD has rendered its menu (Guardian.jsp starts empty)."""
    deadline = time.time() + timeout
    while time.time() < deadline:
        try:
            on_gold = "gold.sso.infra.ftgroup" in driver.current_url
            body = driver.find_element(By.TAG_NAME, "body").text if on_gold else ""
        except Exception:
            body = ""
        if "Inbox" in body:
            time.sleep(2)
            dismiss_splash(driver)
            return True
        time.sleep(2)
    return False


def dismiss_splash(driver):
    """Close GOLD's announcement pop-up (dark overlay + box with a 'Close' link) if shown.
    'Don't show me again' is left for the user to decide."""
    try:
        boxes = [b for b in driver.find_elements(By.ID, "light") if b.is_displayed()]
        for box in boxes:
            for close in box.find_elements(By.XPATH, ".//*[contains(@onclick,'closeSplashScreen')]"):
                if close.is_displayed():
                    close.click()
                    time.sleep(1)
                    break
    except Exception:
        pass


def main():
    OUT_DIR.mkdir(exist_ok=True)
    driver = start_firefox()
    try:
        driver.get(GOLD_URL)
        print("Waiting for GOLD (log in in the Firefox window if asked)...")
        if not wait_for_gold(driver):
            print("Timed out waiting for GOLD; saving whatever is on screen.")
        driver.save_screenshot(str(OUT_DIR / "gold_home.png"))
        text = f"URL: {driver.current_url}\nTITLE: {driver.title}\n\n" + page_text(driver)
        (OUT_DIR / "gold_home.txt").write_text(text, encoding="utf-8")
        (OUT_DIR / "gold_home.html").write_text(driver.page_source, encoding="utf-8")
        print(f"Saved screenshot, text and HTML to {OUT_DIR}")
    finally:
        driver.quit()


if __name__ == "__main__":
    main()
