"""Add a 'Revised Target Date' (RTDD) milestone to GOLD orders.

GOLD: order > Milestones > Create new > "Select or enter Milestone" =
  "Revised Target Date - Customer Reason"  or
  "Revised Target Date - Orange Business Services Reason"
Target Date = the new date (GOLD format DD-Mon-YYYY, e.g. 06-Dec-2026). Description (the reason) is
mandatory since Nov 2026: without it GOLD shows the form again with a message in its left panel. Save =
submitMilestone().
"""
import re
import time
from datetime import date, datetime

from selenium.common.exceptions import NoAlertPresentException, UnexpectedAlertPresentException
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import Select, WebDriverWait

import gold_extract as gx
import open_order as oo
from open_gold import Wait

RTDD_TITLES = {
    "Customer": "Revised Target Date - Customer Reason",
    "Orange": "Revised Target Date - Orange Business Services Reason",
}
# GOLD's Description (reason) choices per type, as read from GOLD (Oct 2026). Mandatory since Nov 2026.
REASONS = {
    "Customer": [
        "Order Set On-Hold due to Customer HQ request", "Customer not accepting the order",
        "Media Delivery delay caused by Customer",
        "Awaiting customer approval for access circuit offer change from BIA to DIA",
        "Customer configuration file not provided", "Site Access was not granteed to Field Enginer",
        "Offer requsted changed by Customer", "Unable to reach End user contact",
        "Delay at customer site due to damage from natural disaster",
        "Delay in service delivery due to customer Pandemic situation",
        "Customer hold Customer acceptance testing scheduling",
        "Customer In-House wiring not completed", "Pending Partial Billing request approval",
        "Equipment delivery delay-Customer", "Pending PO from SITA",
        "Request by the End User to postpone or put on hold the service delivery",
        "Missing Media parameters by Customer",
    ],
    "Orange": [
        "Delay due to special event in the country",
        "Delay in service delivery due to Hardware impact due Pandemic situation",
        "Equipment delivery delay-Orange Supply Chain",
        "Equipment delay - Regulatory constraints from a given country",
        "Equipment delivery delay-Provider", "Media Quote Rejection Escalation",
        "copper versus fiber change request by carrier", "Scope of work provided is unclear",
        "Access configuration not available",
        "Intervention at customer site failed due to orange configuration",
        "Intervention at customer site failed due to Carrier circuit error",
        "Intervention failed FE did not show up",
        "Delay in service delivery due to Vendor Pandemic situation",
        "Delay in Provider due to damage from natural disaster", "Tool issue - TT created",
        "Missing Media parameters-Provider", "Trouble Ticket Escalation",
        "Delay at PoP due to natural disaster",
        "ETP Charges Not confirmed by Carrier / Internal team",
        "Equipment delayed due to software requirments", "Provider Infrastructure Build-up Required",
        "Error exists on the equipment order", "Service Configuration not ready",
        "Media delivery delay due to Provider", "Delay in service delivery due to OBS Pandemic situation",
        "Delay due to internal migration request validation", "Quote appears as OPT", "Internal issues",
        "Address in WebAlc does not match customer site address",
        "PoP not compatible with the constrains in the quote", "Unrealistic Target Delivery Date",
        "Interface between tools failed TT created",
    ],
}
# Every milestone GOLD uses for a revised date: the two we add, "Revised Target Delivery Date - O..." (added by
# GOLD's System Delivery) and "MHS - Revised Target Delivery Date" (from Nov 2026). The list shortens long titles.
RTDD_TITLE = re.compile(r"^(MHS - )?Revised Target (Date|Delivery Date)\b", re.I)
VERIFY_SECONDS = 120  # how long to look for a saved RTDD on the Milestones tab (GOLD may redraw it late)
TARGET_HIDDEN = "targetDate_tgtX$Date"
TARGET_HELPER = "targetDate_tgtX$DateHelper"

MONTHS = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]
MONTHS_FULL = ["january", "february", "march", "april", "may", "june", "july", "august", "september", "october",
               "november", "december"]


def parse_date(text, today=None):
    """A date written (almost) any way -> date. Raises ValueError.
    '11-oct-2026', '6 Dec 26', 'October 6th, 2026', 'Tue 6 Oct', '06/12/2026', '6.12.26', '2026-12-06',
    '2026/12/06 00:00', '20261206', an Excel date number (46362), 'today', 'tomorrow', '+14' (days from today).
    Numbers only are read day first (06/12 = 6 December) unless that is impossible (12/31 = 31 December).
    Without a year: this year, or next year if that date has passed."""
    if isinstance(text, datetime):
        return text.date()
    if isinstance(text, date):
        return text
    today = today or date.today()
    raw = " ".join(str(text).split())
    s = raw.lower()
    bad = ValueError(f"'{raw}' is not a date I can read (e.g. 11-Oct-2026)")
    if s in ("today", "now"):
        return today
    if s == "tomorrow":
        return date.fromordinal(today.toordinal() + 1)
    m = re.fullmatch(r"\+\s*(\d{1,4})\s*(d|days?)?", s)
    if m:
        return date.fromordinal(today.toordinal() + int(m.group(1)))
    s = re.sub(r"[t\s]\d{1,2}:\d{2}(:\d{2}(\.\d+)?)?\s*(am|pm)?$", "", s)  # a time after the date
    if re.fullmatch(r"\d{5}(\.0+)?", s) and 20000 < float(s) < 80000:  # Excel's day number
        return date.fromordinal(date(1899, 12, 30).toordinal() + int(float(s)))
    if re.fullmatch(r"\d{8}", s):
        for fmt in ("%Y%m%d", "%d%m%Y"):
            try:
                return datetime.strptime(s, fmt).date()
            except ValueError:
                pass
        raise bad
    s = re.sub(r"(\d)(st|nd|rd|th)\b", r"\1", s)
    words = re.findall(r"[a-z]+", s)
    nums = [int(n) for n in re.findall(r"\d+", s)]
    month = None
    for w in words:
        if w[:3].title() in MONTHS and (len(w) == 3 or MONTHS_FULL[MONTHS.index(w[:3].title())].startswith(w)
                                        or w == "sept"):
            month = MONTHS.index(w[:3].title()) + 1
        elif w[:3] not in ("mon", "tue", "wed", "thu", "fri", "sat", "sun", "of"):
            raise bad
    year = day = None
    if month:  # '6 Dec 2026', 'Dec 6 2026', '2026 Dec 6', '6 dec 26', '6 Dec'
        if len(nums) == 2:
            big = [n for n in nums if n > 31]
            if big:
                rest = list(nums)
                rest.remove(big[0])
                year, day = big[0], rest[0]
            else:
                day, year = nums
        elif len(nums) == 1:
            day = nums[0]
        else:
            raise bad
    else:
        if len(nums) == 3:
            if nums[0] > 31:  # 2026-12-06
                year, month, day = nums
            else:
                day, month, year = nums
                if month > 12 and day <= 12:  # 12/31/2026: month first
                    day, month = month, day
        elif len(nums) == 2:
            day, month = nums
            if month > 12 and day <= 12:
                day, month = month, day
        else:
            raise bad
    if year is None:
        try:
            guess = date(today.year, month, day)
        except ValueError:
            raise bad
        return guess if guess >= today else date(today.year + 1, month, day)
    if year < 100:
        year += 2000
    try:
        return date(year, month, day)
    except ValueError:
        raise bad


def gold_date(d):
    """date -> GOLD's DD-Mon-YYYY."""
    return f"{d.day:02d}-{MONTHS[d.month - 1]}-{d.year}"


def match_reason(kind, text):
    """GOLD's exact reason text for this type, ignoring case/extra spaces; '' for blank.
    Raises ValueError if GOLD has no such reason for the type."""
    norm = lambda s: " ".join(str(s or "").split()).lower()
    if not norm(text):
        return ""
    for r in REASONS[kind]:
        if norm(r) == norm(text):
            return r
    raise ValueError(f"'{text}' is not a {kind} reason in GOLD")


def parse_bulk(text, default_date=None):
    """Lines of 'order  date' (tab, comma, semicolon or spaces; pasted from Excel works).
    A line with only an order uses default_date. Returns [(order, date|None, error|None)]."""
    rows, seen = [], set()
    for line in text.splitlines():
        line = line.strip()
        if not line:
            continue
        m = re.match(r"(\d{2}-\d{5,8})\s*[,;\t ]?\s*(.*)$", line)
        if not m:
            if re.search(r"order|date", line, re.I):
                continue  # a header line
            rows.append((line, None, "not an order number"))
            continue
        order, rest = m.group(1), m.group(2).strip()
        if order in seen:
            rows.append((order, None, "duplicate order in the list"))
            continue
        seen.add(order)
        try:
            d = parse_date(rest) if rest else (parse_date(default_date) if default_date else None)
            rows.append((order, d, None if d else "no date"))
        except ValueError as e:
            rows.append((order, None, str(e)))
    return rows


def reasons_for(driver, kind):
    """Reason (Description) options GOLD offers for this RTDD type, read from the open create form."""
    Select(driver.find_element(By.ID, "title")).select_by_visible_text(RTDD_TITLES[kind])
    time.sleep(0.3)
    return [o.text.strip() for o in driver.find_elements(By.CSS_SELECTOR, "#description option")
            if o.text.strip()]


def _accept_alert(driver):
    try:
        a = driver.switch_to.alert
        text = a.text
        a.accept()
        return text
    except NoAlertPresentException:
        return None


def open_create_form(driver, wait):
    oo.open_tab(driver, wait, "Milestones")
    btn = wait.until(EC.element_to_be_clickable((By.CSS_SELECTOR, "img.butCreateNew")))
    btn.click()
    wait.until(EC.presence_of_element_located((By.ID, "title")))
    time.sleep(0.4)


class AlreadySet(Exception):
    """The order's current RTDD already has the chosen date: nothing was added."""


class EarlierDate(Exception):
    """The new RTDD is earlier than the order's date and the user chose not to set it."""


def _date(text):
    try:
        return parse_date(text) if text else None
    except ValueError:
        return None


def milestone_rows(driver, wait):
    """All rows of the open order's Milestones tab: [{Title, Target Date, Completed Date, ...}]."""
    oo.open_tab(driver, wait, "Milestones")
    rows = []
    for g in gx.extract_tab(driver)["grids"]:
        if "Title" in g["columns"] and "Target Date" in g["columns"]:
            rows += [dict(zip(g["columns"], r)) for r in g["rows"]]
    return rows


def is_rtdd(row):
    return bool(RTDD_TITLE.match(row.get("Title") or ""))


def current_rtdd(rows):
    """The order's current RTDD row (any RTDD milestone): the last open one, else the last completed (GOLD
    completes the older ones when a new one comes, several on the same day: then the latest date). None if none."""
    rtdds = [r for r in rows if is_rtdd(r)]
    open_rows = [r for r in rtdds if not r.get("Completed Date")]
    if open_rows:
        return open_rows[-1]
    return max(rtdds, key=lambda r: (_date(r.get("Completed Date")) or date.min,
                                     _date(r.get("Target Date")) or date.min), default=None)


def _with_date(rows, target):
    """How many RTDD rows have this Target Date (GOLD's DD-Mon-YYYY)."""
    return sum(1 for r in rows if is_rtdd(r) and (r.get("Target Date") or "").strip().lower() == target.lower())


PAGE_ERROR = re.compile(r"error|exception|not allowed|cannot|can't|unable to|failed to|invalid|denied|"
                        r"mandatory|is required|not permitted|please ", re.I)


def page_message(driver):
    """GOLD's error / warning text on the page, or "". GOLD shows some refusals there instead of a pop-up,
    in the left panel under the menu (e.g. "Please select description to add Revised Target Date...")."""
    try:
        text = driver.execute_script("return document.body.innerText") or ""
    except Exception:
        return ""
    lines = [" ".join(l.split()) for l in text.splitlines()]
    lines = [l for l in lines if PAGE_ERROR.search(l) and len(l) < 400 and not l.startswith("* Mandatory")]
    return " / ".join(dict.fromkeys(lines))[:500]


def _reread(driver, wait):
    """The Milestones tab read again from GOLD (via another tab, so the page really reloads)."""
    try:
        oo.open_tab(driver, wait, "Information")
    except UnexpectedAlertPresentException:  # "you will lose changes": the milestone is already saved
        _accept_alert(driver)
        oo.open_tab(driver, wait, "Information")
    return milestone_rows(driver, wait)


def compare_date(driver, wait, rows):
    """(date, what it is) a new RTDD is compared with: the ITDD when the order has no RTDD, else the
    later of the current RTDD and the ITDD. (None, '') when GOLD shows neither."""
    initial = _date(next((r.get("Target Date") for r in rows
                          if r["Title"].startswith("Initial Target Delivery Date")), ""))
    if not initial:  # no ITDD milestone: the order's Information tab has the field
        oo.open_tab(driver, wait, "Information")
        initial = next((_date(v) for _, label, v in gx.extract_tab(driver)["fields"]
                        if label.strip().lower() == "initial target delivery date" and _date(v)), None)
    cur = current_rtdd(rows)
    revised = _date(cur.get("Target Date")) if cur else None
    found = [(d, what) for d, what in ((revised, "the current RTDD"), (initial, "the ITDD")) if d]
    return max(found, key=lambda f: f[0]) if found else (None, "")


def read_rtdd(driver, wait, order):
    """The order's current RTDD, read from its Milestones tab (changes nothing):
    {"rtdd": date or None, "reason": the milestone's title}."""
    oo.open_orders_tab(driver, wait, discard_changes=True)
    oo.untick_my_orders(driver)
    row = oo.search_order(driver, wait, order)
    oo.open_result(driver, wait, row, order)
    cur = current_rtdd(milestone_rows(driver, wait))
    oo.open_orders_tab(driver, wait, discard_changes=True)
    return {"rtdd": _date(cur.get("Target Date")) if cur else None, "reason": cur["Title"] if cur else ""}


def add_rtdd(driver, wait, order, kind, new_date, reason="", dry_run=False, log=print, confirm=None):
    """Open the order and add the RTDD milestone. Returns a short result message.
    dry_run: fill the form, then Cancel instead of Save.
    confirm(order, warning) -> bool is asked when the new date is earlier than the order's date
    (see compare_date); without it, or on False, nothing is set (EarlierDate)."""
    title = RTDD_TITLES[kind]
    target = gold_date(new_date)
    if not reason:
        raise ValueError("GOLD needs a reason (Description) for a Revised Target Date - none was given")

    # Start each order from the search page. GOLD Express's Firefox is only used by the app and
    # every change is either saved+verified or cancelled, so a leftover 'you will lose
    # changes' warning here is from our own cancelled attempt: safe to accept.
    oo.open_orders_tab(driver, wait, discard_changes=True)
    oo.untick_my_orders(driver)
    row = oo.search_order(driver, wait, order)
    oo.open_result(driver, wait, row, order)
    rows = milestone_rows(driver, wait)
    current = current_rtdd(rows)
    if current and current.get("Target Date", "").strip().lower() == target.lower():
        oo.open_orders_tab(driver, wait, discard_changes=True)
        raise AlreadySet(f"the RTDD is already set to {target} - nothing changed")
    ref, what = compare_date(driver, wait, rows)
    warning = f"{target} is earlier than {what} ({gold_date(ref)})" if ref and new_date < ref else ""
    if warning and not dry_run and not (confirm and confirm(order, warning)):
        oo.open_orders_tab(driver, wait, discard_changes=True)
        raise EarlierDate(f"{warning} - not set")
    before = _with_date(rows, target)

    open_create_form(driver, wait)
    Select(driver.find_element(By.ID, "title")).select_by_visible_text(title)
    time.sleep(0.3)
    if reason:
        options = [o.text.strip() for o in driver.find_elements(By.CSS_SELECTOR, "#description option")]
        if reason not in options:
            raise RuntimeError(f"GOLD has no reason '{reason}' for {kind}")
        Select(driver.find_element(By.ID, "description")).select_by_visible_text(reason)

    # The date boxes are read-only; set them the way GOLD's calendar does.
    driver.execute_script(
        "var h=document.getElementById(arguments[0]), v=document.getElementById(arguments[1]);"
        "h.value=arguments[2]; copyToHelper(h.value, v);",
        TARGET_HIDDEN, TARGET_HELPER, target)
    shown = driver.find_element(By.ID, TARGET_HELPER).get_attribute("value")
    if shown != target:
        raise RuntimeError(f"Target Date did not take the value {target} (shows '{shown}')")

    if dry_run:
        driver.find_element(By.CSS_SELECTOR, "img.butCancel").click()
        wait.until(EC.invisibility_of_element_located((By.ID, "title")))
        # Filling the date marks the order as modified; leave it, discarding nothing saved.
        oo.open_orders_tab(driver, wait, discard_changes=True)
        return (f"dry run OK - form filled with {title} / {target}, then cancelled"
                + (f" (warning: {warning} - a real run asks first)" if warning else ""))

    form = driver.find_element(By.ID, "title")
    driver.find_element(By.CSS_SELECTOR, "img.butAddToOrder").click()
    time.sleep(0.4)
    alert = _accept_alert(driver)
    if alert:
        raise RuntimeError(f"GOLD refused: {alert.strip()}")
    Wait(driver, 60).until(EC.staleness_of(form))
    if driver.find_elements(By.ID, "title"):  # the form is back: GOLD refused, with a message in its left panel
        said = page_message(driver) or "no reason given"
        with_cancel = driver.find_elements(By.CSS_SELECTOR, "img.butCancel")
        if with_cancel:
            with_cancel[0].click()
        oo.open_orders_tab(driver, wait, discard_changes=True)
        raise RuntimeError(f"GOLD did not add the RTDD - it says: {said}")
    said = page_message(driver)

    # Verify: one more RTDD row with this target date on the Milestones tab. GOLD may redraw the list a while
    # after the form closes, so look again until it shows (reading it once too early said "not visible").
    deadline = time.time() + VERIFY_SECONDS
    after = milestone_rows(driver, wait)
    while _with_date(after, target) <= before:
        if time.time() > deadline:
            if said:
                raise RuntimeError(f"GOLD did not add the RTDD - it says: {said}")
            raise RuntimeError(f"GOLD took the save, but after {VERIFY_SECONDS} s the new RTDD ({target}) is still "
                               "not on the order's Milestones tab - check the order in GOLD before running it "
                               "again (it may be there, and a second run would add it twice)")
        time.sleep(5)
        after = _reread(driver, wait)
    # The milestone is saved (verified above), but GOLD's page still warns "You will lose
    # any changes" because the date box marked the order as modified. Nothing is pending,
    # so leave the order now, accepting that warning, ready for the next one.
    oo.open_orders_tab(driver, wait, discard_changes=True)
    return f"added {title} with Target Date {target}"
