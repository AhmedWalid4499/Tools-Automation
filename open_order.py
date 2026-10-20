"""Open a GOLD order by number, then explore its side-menu tabs interactively.

Usage:  python open_order.py 10-1771012

Steps: Orders tab -> untick "my orders only" -> type the order number ->
Enter -> click the result row -> list the order's side-menu tabs and ask
which one to open. Every tab visited is screenshotted to output/<order>/.
  - Documents: lists the documents and offers to download them.
  - Teams: lists the teams and answers questions about their members.
  - Other tabs: prints the tab's text.
"""
import argparse
import os
import re
import time

from selenium.common.exceptions import (NoAlertPresentException, NoSuchElementException,
                                        StaleElementReferenceException)
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait

from open_gold import DOWNLOAD_DIR, GOLD_URL, OUT_DIR, start_firefox, wait_for_gold

# Order side-menu items call jumpTo('...'); the main menu ones call tryJumpTo(...).
ORDER_TAB_XPATH = "//tr[@title]/td[contains(@onclick, \"jumpTo('\")]"
GRID_ROWS_XPATH = "//tbody[@id='GridTableBody']/tr"


# ---------- open the order ----------

def _leave_prompt(driver, discard_changes):
    """GOLD asks 'You will lose any changes...' when leaving a modified order.
    Accept only when told to (e.g. after a cancelled dry run); otherwise stop."""
    try:
        alert = driver.switch_to.alert
    except NoAlertPresentException:
        return
    text = alert.text
    if discard_changes:
        alert.accept()
        time.sleep(1)
    else:
        alert.dismiss()
        raise RuntimeError(f"GOLD says the order has unsaved changes: {text.strip()}")


def open_orders_tab(driver, wait, discard_changes=False):
    """Go to the order search page. From inside an order, 'Orders' returns to that
    order, so then use the left menu's 'All orders'."""
    if driver.find_elements(By.ID, "orderNb"):
        return
    driver.find_element(By.XPATH, "//ul[@id='headMenu']//a[normalize-space()='Orders']").click()
    _leave_prompt(driver, discard_changes)
    try:
        WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.ID, "orderNb")))
        return
    except Exception:
        pass
    driver.find_element(By.XPATH, "//tr[@title='All orders']/td").click()
    _leave_prompt(driver, discard_changes)
    wait.until(EC.presence_of_element_located((By.ID, "orderNb")))


def untick_my_orders(driver):
    cb = driver.find_element(By.ID, "myOrdersOnlyCB")
    if cb.is_selected():
        cb.click()  # its onclick syncs the hidden myOrdersOnly field


def search_order(driver, wait, order_nb):
    old_page = driver.find_element(By.TAG_NAME, "body")  # page showing a previous search
    box = driver.find_element(By.ID, "orderNb")
    box.clear()
    box.send_keys(order_nb, Keys.ENTER)
    # The page reloads with new results: wait for the old page to go, so we don't read
    # rows (or "0 orders listed") from the previous search.
    try:
        WebDriverWait(driver, 30).until(EC.staleness_of(old_page))
    except Exception:
        pass
    row_xpath = f"{GRID_ROWS_XPATH}[td[normalize-space()='{order_nb}']]"

    def found_or_empty(d):
        if d.find_elements(By.XPATH, row_xpath):
            return "found"
        text = d.find_element(By.TAG_NAME, "body").text.lower()
        if "0 orders listed" in text or "no orders" in text or "orders were found" in text:
            return "empty"
        if d.find_elements(By.ID, "GridTableBody") and "orders listed" in text:
            return "empty"  # results are shown, but not this order
        return False
    try:
        result = WebDriverWait(driver, 60).until(found_or_empty)
    except Exception:
        result = "empty"
    if result == "empty":
        raise RuntimeError(f"order {order_nb} was not found in GOLD")
    time.sleep(0.5)
    return wait.until(EC.element_to_be_clickable((By.XPATH, row_xpath)))


def _on_order_page(driver, order_nb):
    try:
        return f"order # : {order_nb}" in driver.find_element(By.TAG_NAME, "body").text
    except Exception:
        return False


def open_result(driver, wait, row, order_nb):
    """Open the order from its search-result row. The order page shows e.g.
    "Change order # : 10-1771012". A click sometimes only selects (and redraws) the
    grid, so retry with a double-click on the freshly found row."""
    row_xpath = f"{GRID_ROWS_XPATH}/td[normalize-space()='{order_nb}']"
    for attempt in range(4):
        try:
            cell = row.find_element(By.XPATH, f"./td[normalize-space()='{order_nb}']") \
                if attempt == 0 else driver.find_element(By.XPATH, row_xpath)
            if attempt == 0:
                cell.click()
            else:
                ActionChains(driver).double_click(cell).perform()
        except Exception:
            pass  # page already changing under us
        try:
            WebDriverWait(driver, 20).until(lambda d: _on_order_page(d, order_nb))
            time.sleep(1)
            return
        except Exception:
            if not driver.find_elements(By.XPATH, row_xpath):
                wait.until(lambda d: _on_order_page(d, order_nb))  # still loading the order
                time.sleep(1)
                return
    raise RuntimeError(f"Could not open order {order_nb} from the search results")


# ---------- side-menu tabs ----------

def list_tabs(driver):
    """[(title, td element)] for the order's side menu, e.g. ('Documents [12]', <td>)."""
    tabs = []
    for td in driver.find_elements(By.XPATH, ORDER_TAB_XPATH):
        tabs.append((td.find_element(By.XPATH, "..").get_attribute("title"), td))
    return tabs


def open_tab(driver, wait, title):
    base = re.sub(r"\s*\[\d+\]$", "", title)  # "Documents [12]" -> "Documents"
    xpath = f"//tr[starts-with(@title, '{base}')]/td"
    td = wait.until(EC.element_to_be_clickable((By.XPATH, xpath)))  # page may still be drawing
    td.click()
    # Page reloads; the clicked item becomes the selected one.
    wait.until(EC.staleness_of(td))

    def selected(d):
        try:
            return "Selected" in d.find_element(By.XPATH, xpath).get_attribute("class")
        except (NoSuchElementException, StaleElementReferenceException):
            return False
    wait.until(selected)
    time.sleep(1)
    return base


# Page text without the left menu, with each dropdown shown as its selected value
# instead of all its options. The DOM swap is undone in the same call.
CONTENT_TEXT_JS = """
const swaps = [];
for (const s of document.querySelectorAll('select')) {
  const span = document.createElement('span');
  span.textContent = s.selectedIndex >= 0 ? '[' + s.options[s.selectedIndex].text + ']' : '[]';
  s.replaceWith(span); swaps.push([span, s]);
}
const nav = document.getElementById('LeftNavbarDiv');
const navDisplay = nav ? nav.style.display : null;
if (nav) nav.style.display = 'none';
let text;
try { text = document.body.innerText; }
finally {
  for (const [span, s] of swaps) span.replaceWith(s);
  if (nav) nav.style.display = navDisplay;
}
return text;
"""


def content_text(driver):
    text = driver.execute_script(CONTENT_TEXT_JS)
    return "\n".join(l.rstrip() for l in text.splitlines() if l.strip())


def ask(prompt):
    return input(prompt).replace("﻿", "").strip()


def screenshot(driver, folder, name):
    path = folder / f"{name}.png"
    driver.save_screenshot(str(path))
    print(f"  Screenshot: {path}")
    return path


# ---------- Documents ----------

def read_documents(driver):
    docs = []
    for row in driver.find_elements(By.XPATH, GRID_ROWS_XPATH):
        cells = [c.text.strip() for c in row.find_elements(By.TAG_NAME, "td")[2:]]
        if cells:
            docs.append({"key": row.get_attribute("itemkey"), "title": cells[0],
                         "modified": cells[1], "type": cells[2],
                         "srf": cells[3] if len(cells) > 3 else ""})
    return docs


def print_documents(docs):
    print(f"\n  {len(docs)} documents:")
    for i, d in enumerate(docs, 1):
        print(f"  {i:>3}. {d['title']:<45} {d['modified']:<26} {d['type']}")


# GOLD-stored documents have a /downloadFile/ link. QUOTO-sourced ones first show a
# file icon calling doAction2('downloadDocument', ...): clicking it makes GOLD fetch
# the file from QUOTO and reload the page, which then has the /downloadFile/ link.
FILE_LINK_XPATH = "//a[contains(@href, '/downloadFile/')]"
QUOTO_ICON_XPATH = "//img[contains(@onclick, \"'downloadDocument'\")]"
DOWNLOAD_LINK_XPATH = f"{FILE_LINK_XPATH} | {QUOTO_ICON_XPATH}"


def download_document(driver, wait, doc, dest_dir, timeout=60):
    """Open the document's details page, click its file link, wait for the file.

    Returns (saved file paths, details text). Leaves the browser on the details page.
    """
    # Rows are found by GOLD's document key: positions change when QUOTO docs get fetched.
    row_xpath = f"{GRID_ROWS_XPATH}[@itemkey='{doc['key']}']"
    link = None
    for _ in range(3):  # the grid sometimes ignores the first double-click after a reload
        try:
            # The list can reload right after it first appears, so wait for the row.
            row = WebDriverWait(driver, 20).until(
                EC.presence_of_element_located((By.XPATH, row_xpath)))
            cell = row.find_elements(By.TAG_NAME, "td")[2]
            # Clicking selects the row; clicking an already-selected row opens it.
            cell.click()
            try:
                WebDriverWait(driver, 2).until(EC.staleness_of(row))  # it opened
            except Exception:
                ActionChains(driver).double_click(cell).perform()
        except StaleElementReferenceException:
            time.sleep(1)  # grid was redrawn under us; find the row again
            continue
        try:
            link = WebDriverWait(driver, 15).until(
                EC.element_to_be_clickable((By.XPATH, DOWNLOAD_LINK_XPATH)))
            break
        except Exception:
            if not driver.find_elements(By.XPATH, row_xpath):
                raise  # left the list but no download link: unexpected page
    if link is None:
        return [], ""

    # Make sure the grid opened the document we asked for (list titles may end in "...").
    wanted = doc["title"].removesuffix("...")
    if wanted not in content_text(driver):
        raise RuntimeError(f"GOLD opened a different document than '{doc['title']}'")

    if link.tag_name == "img":  # QUOTO document: fetch it into GOLD first
        link.click()
        wait.until(EC.staleness_of(link))
        link = wait.until(EC.element_to_be_clickable((By.XPATH, FILE_LINK_XPATH)))
    details = content_text(driver)

    # DOWNLOAD_DIR is only a staging folder: empty it so leftovers from earlier runs
    # don't make Firefox rename the new file ("x-1.txt").
    for p in DOWNLOAD_DIR.iterdir():
        try:
            p.unlink()
        except OSError:
            pass
    before = set(DOWNLOAD_DIR.iterdir())
    link.click()
    deadline = time.time() + timeout
    last_sizes = None
    while time.time() < deadline:
        time.sleep(1)
        current = set(DOWNLOAD_DIR.iterdir())
        new = [p for p in current - before if not p.name.endswith(".part")]
        if not new or any(p.name.endswith(".part") for p in current):
            continue
        # Firefox first writes an empty placeholder; wait until sizes are non-zero and stable.
        sizes = [p.stat().st_size for p in new]
        if 0 in sizes or sizes != last_sizes:
            last_sizes = sizes
            continue
        dest_dir.mkdir(parents=True, exist_ok=True)
        saved = []
        for p in new:
            target = dest_dir / p.name
            _move(p, target)
            saved.append(str(target))
        return saved, details
    return [], details


def _move(src, target, tries=20):
    """os.replace (overwrites an older copy), retried while Firefox/antivirus/OneDrive
    still hold the freshly downloaded file open."""
    for i in range(tries):
        try:
            return os.replace(src, target)
        except PermissionError:
            if i == tries - 1:
                raise
            time.sleep(0.5)


def parse_selection(answer, count):
    """'1,3,5-7' / 'all' -> sorted list of 1-based indexes."""
    answer = answer.strip().lower()
    if answer in ("all", "a"):
        return list(range(1, count + 1))
    picked = set()
    for part in re.split(r"[,\s]+", answer):
        if re.fullmatch(r"\d+-\d+", part):
            lo, hi = map(int, part.split("-"))
            picked.update(range(lo, hi + 1))
        elif part.isdigit():
            picked.add(int(part))
    return sorted(i for i in picked if 1 <= i <= count)


def documents_flow(driver, wait, order_dir):
    docs = read_documents(driver)
    print_documents(docs)
    while True:
        ans = ask("\n  Download which? (e.g. 1,3,5-7 / all / Enter = none): ")
        if not ans:
            return
        picks = parse_selection(ans, len(docs))
        if not picks:
            print("  Didn't understand that selection.")
            continue
        dest = order_dir / "documents"
        for i in picks:
            d = docs[i - 1]
            print(f"  Downloading {i}. {d['title']} ...", end=" ", flush=True)
            try:
                saved, details = download_document(driver, wait, d, dest)
            except Exception as e:
                saved, details = [], ""
                print(f"failed: {str(e).splitlines()[0] if str(e) else type(e).__name__}")
            else:
                print(", ".join(saved) if saved else "no file arrived (check the Firefox window)")
            info = re.search(r"Created By.*", details, re.S)
            if info:
                print("      " + " ".join(info.group(0).split())[:200])
            open_tab(driver, wait, "Documents")  # back to the list for the next one
        return


# ---------- Teams ----------

def read_teams(driver):
    """{team name: {"primary": str|None, "members": [names]}} from the Teams tab."""
    teams = {}
    for title_td in driver.find_elements(By.XPATH, "//td[contains(@class,'normalViewBold')]"):
        table = title_td.find_element(By.XPATH, "./ancestor::table[1]")
        name = title_td.text.strip()
        members = []
        for td in table.find_elements(By.XPATH, ".//td[@class='normalView']"):
            members += [m.strip() for m in td.text.splitlines() if m.strip()]
        has_primary = bool(table.find_elements(By.CSS_SELECTOR, "img.iconPrimary"))
        if name:
            teams[name] = {"primary": members[0] if has_primary and members else None,
                           "members": members}
    return teams


def print_teams(teams):
    print(f"\n  {len(teams)} teams:")
    for i, (name, t) in enumerate(teams.items(), 1):
        print(f"  {i:>3}. {name:<40} primary: {t['primary'] or '-':<25} ({len(t['members'])} members)")


def teams_flow(teams):
    print_teams(teams)
    names = list(teams)
    help_text = ("\n  What do you need?\n"
                 "    <number>      all members of that team\n"
                 "    p             primary member of every team\n"
                 "    f <name>      which teams a person is in (partial name OK)\n"
                 "    l             list the teams again\n"
                 "    Enter         back to the tab menu")
    print(help_text)
    while True:
        ans = ask("\n  Teams> ").strip()
        if not ans:
            return
        if ans.isdigit() and 1 <= int(ans) <= len(names):
            name = names[int(ans) - 1]
            t = teams[name]
            print(f"\n  {name} — {len(t['members'])} members (primary: {t['primary'] or '-'})")
            for m in t["members"]:
                print(f"    {'*' if m == t['primary'] else ' '} {m}")
        elif ans.lower() == "p":
            for name, t in teams.items():
                print(f"    {name:<40} {t['primary'] or '-'}")
        elif ans.lower().startswith("f "):
            q = ans[2:].strip().lower()
            hits = [(name, m) for name, t in teams.items() for m in t["members"] if q in m.lower()]
            if not hits:
                print(f"    Nobody matching '{q}'.")
            for name, m in hits:
                star = " (primary)" if teams[name]["primary"] == m else ""
                print(f"    {m:<30} {name}{star}")
        elif ans.lower() == "l":
            print_teams(teams)
        else:
            print(help_text)


# ---------- main loop ----------

def tab_menu(driver, wait, order_nb):
    order_dir = OUT_DIR / order_nb
    order_dir.mkdir(parents=True, exist_ok=True)
    while True:
        tabs = [t for t, _ in list_tabs(driver)]
        print(f"\nOrder {order_nb} — tabs:")
        for i, t in enumerate(tabs, 1):
            print(f"  {i:>3}. {t}")
        ans = ask("\nWhich tab? (number or name, q = quit): ").strip()
        if ans.lower() in ("q", "quit", "exit"):
            return
        if ans.isdigit() and 1 <= int(ans) <= len(tabs):
            title = tabs[int(ans) - 1]
        else:
            matches = [t for t in tabs if t.lower().startswith(ans.lower())] if ans else []
            if len(matches) != 1:
                print("  Pick one of the numbers above.")
                continue
            title = matches[0]

        name = open_tab(driver, wait, title)
        print(f"\n== {name} ==")
        screenshot(driver, order_dir, re.sub(r"\W+", "_", name))
        if name == "Documents":
            documents_flow(driver, wait, order_dir)
        elif name == "Teams":
            teams_flow(read_teams(driver))
        else:
            text = content_text(driver)
            (order_dir / f"{re.sub(r'\W+', '_', name)}.txt").write_text(text, encoding="utf-8")
            print(text)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("order", help="GOLD order number, e.g. 10-1771012")
    args = ap.parse_args()

    driver = start_firefox()
    wait = WebDriverWait(driver, 60)
    try:
        driver.get(GOLD_URL)
        if not wait_for_gold(driver):
            raise SystemExit("GOLD did not load (SSO?)")
        open_orders_tab(driver, wait)
        untick_my_orders(driver)
        row = search_order(driver, wait, args.order)
        open_result(driver, wait, row, args.order)
        print(f"Opened order {args.order}")
        tab_menu(driver, wait, args.order)
    finally:
        driver.quit()


if __name__ == "__main__":
    main()
