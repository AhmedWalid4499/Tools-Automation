"""Assign the STM (team 'PMandCSM' in GOLD) of an order to a person, as primary.

GOLD: order > Teams > Manage Teams > STM:
  untick 'Same as project' (when ticked, STM is inherited and has no controls) >
  magnifier (WF_addTeamMember) > pop-up 'Select user for STM team': search Last / First
  name > click the user (returns them to the STM list box) > select them in the list and
  click the orange arrow (WF_selectPrimary; the first person in the list is the primary) >
  Save Teams (doAction2('saveTeams')).
Manage Teams puts the order in edit mode, so on any problem we press Cancel
(doAction2('cancelEditOrder')) to release it.
"""
import time

from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import Select, WebDriverWait

import open_order as oo

TEAM = "PMandCSM"   # GOLD's internal name of the STM team
TEAM_LABEL = "STM"


def _norm(s):
    return " ".join(str(s or "").split()).lower()


def _click(driver, el):
    driver.execute_script("arguments[0].scrollIntoView({block:'center'})", el)
    time.sleep(0.2)
    try:
        el.click()
    except Exception:
        driver.execute_script("arguments[0].click()", el)


def _alert_text(driver, accept=True):
    try:
        a = driver.switch_to.alert
    except Exception:
        return None
    text = a.text
    a.accept() if accept else a.dismiss()
    return text


def _stm_options(driver):
    sel = driver.find_element(By.ID, f"TeamControl{TEAM}")
    return [o.text.strip() for o in sel.find_elements(By.TAG_NAME, "option")]


def _cancel_edit(driver, wait):
    """Leave Manage Teams without saving (releases the order's edit lock)."""
    main = driver.window_handles[0]
    for h in driver.window_handles[1:]:
        try:
            driver.switch_to.window(h)
            driver.close()
        except Exception:
            pass
    driver.switch_to.window(main)
    btns = driver.find_elements(By.CSS_SELECTOR, "img[onclick*='cancelEditOrder']")
    if btns:
        _click(driver, btns[0])
        time.sleep(1)
        _alert_text(driver)  # "You will lose any changes..." -> yes, discard
        wait.until(lambda d: not d.find_elements(By.ID, f"TeamControl{TEAM}_Inherit"))
    # Cancelled: nothing is pending, so leave the order even if GOLD still warns.
    oo.open_orders_tab(driver, wait, discard_changes=True)


def _squash(s):
    return "".join(_norm(s).split()).replace("-", "")


def _search_users(driver, wait, last, last_op, first, first_op):
    """Run one search in the 'Select user' pop-up; returns [(row, [user, first, last, region])]."""
    wait.until(EC.presence_of_element_located((By.ID, "lastNameValUser")))
    for field, value in (("lastNameValUser", last), ("firstNameValUser", first)):
        box = driver.find_element(By.ID, field)
        box.clear()
        if value:
            box.send_keys(value)
    for op, how in (("lastNameOpUser", last_op), ("firstNameOpUser", first_op)):
        Select(driver.find_element(By.NAME, op)).select_by_visible_text(how)
    page = driver.find_element(By.TAG_NAME, "body")
    _click(driver, driver.find_element(By.ID, "searchButton"))
    try:
        WebDriverWait(driver, 30).until(EC.staleness_of(page))  # the pop-up reloads with results
    except Exception:
        pass
    wait.until(lambda d: d.find_elements(By.XPATH, "//tbody[@id='GridTableBody']")
               or "user" in d.find_element(By.TAG_NAME, "body").text.lower())
    time.sleep(1)
    out = []
    for r in driver.find_elements(By.XPATH, "//tbody[@id='GridTableBody']/tr"):
        cells = [c for c in (c.text.strip() for c in r.find_elements(By.TAG_NAME, "td")) if c]
        if len(cells) >= 3:
            out.append((r, cells))
    return out


def _find_user(driver, wait, first, last, user=None):
    """In the 'Select user' pop-up, find exactly one GOLD user for '<first> <last>'.
    1) exact first + last name; 2) if nobody: last word of the name 'Contains', matched on the
    whole name - so 'Anna Maria Smith' is found whether GOLD stores it as
    'Anna' + 'Maria Smith' or 'Anna Maria' + 'Smith'. user (GOLD user ID, e.g. 'asmith2')
    picks one person when two GOLD users share the name."""
    wanted = _squash(f"{first} {last}")
    rows = _search_users(driver, wait, last, "Equals", first, "Equals")
    matches = [(r, c) for r, c in rows if _norm(c[1]) == _norm(first) and _norm(c[2]) == _norm(last)]
    if not matches:
        last_word = f"{first} {last}".split()[-1]
        rows = _search_users(driver, wait, last_word, "Contains", "", "Equals")
        matches = [(r, c) for r, c in rows if _squash(f"{c[1]} {c[2]}") == wanted]
    if user and matches:
        mine = [(r, c) for r, c in matches if c[0].lower() == user.lower()]
        if not mine:
            raise RuntimeError(f"GOLD user ID '{user}' is not one of the users named '{first} {last}' "
                               f"({', '.join(c[0] for _, c in matches)})")
        matches = mine
    if not matches:
        raise RuntimeError(f"no GOLD user named '{first} {last}' - check the name in the DPM Names tab")
    if len(matches) > 1:
        users = ", ".join(c[0] for _, c in matches)
        raise RuntimeError(f"more than one GOLD user named '{first} {last}' ({users}) - "
                           "set the GOLD user ID in the DPM Names tab")
    return matches[0]


def open_user_list(driver, wait):
    """GOLD's Administration > users page: same search as the team pop-up, no order involved."""
    oo.open_orders_tab(driver, wait, discard_changes=True)  # leaves any order cleanly first
    _click(driver, driver.find_element(By.XPATH, "//ul[@id='headMenu']//a[normalize-space()='Administration']"))
    wait.until(EC.presence_of_element_located((By.ID, "lastNameValUser")))


def check_name(driver, wait, first, last, user=None):
    """Find the GOLD user for a name (read-only). Returns (username, gold_first, gold_last)."""
    _, cells = _find_user(driver, wait, first, last, user)
    return cells[0], cells[1], cells[2]


def assign_stm(driver, wait, order, first, last, dry_run=False, log=print, user=None):
    """Make '<first> <last>' the primary STM of the order. Returns a short result message.
    dry_run: do everything except Save Teams, then Cancel."""
    full = f"{first} {last}"
    # Start each order from the search page. GOLD Express's Firefox is only used by the app and
    # every change is either saved+verified or cancelled, so a leftover 'you will lose
    # changes' warning here is from our own cancelled attempt: safe to accept.
    oo.open_orders_tab(driver, wait, discard_changes=True)
    oo.untick_my_orders(driver)
    oo.open_result(driver, wait, oo.search_order(driver, wait, order), order)
    oo.open_tab(driver, wait, "Teams")
    before = oo.read_teams(driver).get(TEAM_LABEL, {})
    if _norm(before.get("primary")) == _norm(full):
        return f"{full} is already the primary STM - nothing to change"

    _click(driver, wait.until(EC.element_to_be_clickable((By.CSS_SELECTOR, "img.butManageTeams"))))
    alert = _alert_text(driver)
    if alert:
        raise RuntimeError(f"GOLD: {alert.strip()}")
    wait.until(EC.presence_of_element_located((By.ID, f"TeamControl{TEAM}_Inherit")))
    time.sleep(1)
    main = driver.current_window_handle
    try:
        inherit = driver.find_element(By.ID, f"TeamControl{TEAM}_Inherit")
        if inherit.is_selected():  # 'Same as project': STM can't be edited until unticked
            _click(driver, inherit)
            time.sleep(1)
            _alert_text(driver)

        if _norm(full) not in [_norm(o) for o in _stm_options(driver)]:
            handles = set(driver.window_handles)
            _click(driver, wait.until(EC.element_to_be_clickable((By.ID, f"TeamControl{TEAM}_add"))))
            WebDriverWait(driver, 30).until(lambda d: len(set(d.window_handles) - handles) == 1)
            popup = (set(driver.window_handles) - handles).pop()
            driver.switch_to.window(popup)
            row, cells = _find_user(driver, wait, first, last, user)
            cell = row.find_elements(By.TAG_NAME, "td")[2]
            _click(driver, cell)  # clicking the selected row returns the user to the team
            time.sleep(2)
            if popup in driver.window_handles:
                try:
                    ActionChains(driver).double_click(cell).perform()
                except Exception:
                    pass
            WebDriverWait(driver, 30).until(lambda d: popup not in d.window_handles)
            driver.switch_to.window(main)
            WebDriverWait(driver, 30).until(
                lambda d: _norm(full) in [_norm(o) for o in _stm_options(d)])
            log(f"  {order}: added {full} ({cells[0]}) to {TEAM_LABEL}")

        # Make them primary: the first person in the list is the primary.
        options = _stm_options(driver)
        idx = [_norm(o) for o in options].index(_norm(full))
        if idx != 0:
            sel = driver.find_element(By.ID, f"TeamControl{TEAM}")
            Select(sel).select_by_index(idx)
            driver.execute_script("arguments[0].dispatchEvent(new Event('change'))", sel)
            time.sleep(0.5)
            _click(driver, driver.find_element(By.ID, f"TeamControl{TEAM}_Select"))  # orange arrow
            time.sleep(1)
            _alert_text(driver)
            WebDriverWait(driver, 60).until(
                lambda d: d.find_elements(By.ID, f"TeamControl{TEAM}")
                and _norm(_stm_options(d)[0]) == _norm(full))
        if _norm(_stm_options(driver)[0]) != _norm(full):
            raise RuntimeError(f"could not make {full} the primary STM")

        if dry_run:
            _cancel_edit(driver, wait)
            return f"test OK - {full} would be primary STM (cancelled, nothing saved)"

        save = driver.find_element(By.CSS_SELECTOR, "img.butSaveTeams")
        _click(driver, save)
        time.sleep(1)
        alert = _alert_text(driver)
        if alert:
            raise RuntimeError(f"GOLD refused to save: {alert.strip()}")
        WebDriverWait(driver, 60).until(EC.staleness_of(save))
    except Exception:
        try:
            _cancel_edit(driver, wait)
        except Exception:
            pass
        raise

    # Verify on the Teams tab.
    oo.open_tab(driver, wait, "Teams")
    after = oo.read_teams(driver).get(TEAM_LABEL, {})
    if _norm(after.get("primary")) != _norm(full):
        raise RuntimeError(f"saved, but Teams shows STM primary '{after.get('primary')}' - please check in GOLD")
    others = [m for m in after.get("members", []) if _norm(m) != _norm(full)]
    return f"{full} is now primary STM" + (f" (also in STM: {', '.join(others)})" if others else "")
