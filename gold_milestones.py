"""Add a 'Revised Target Date' (RTDD) milestone to GOLD orders.

GOLD: order > Milestones > Create new > "Select or enter Milestone" =
  "Revised Target Date - Customer Reason"  or
  "Revised Target Date - Orange Business Services Reason"
Target Date = the new date (GOLD format DD-Mon-YYYY, e.g. 06-Dec-2026). Description
(the reason) is optional. Save = submitMilestone().
"""
import re
import time
from datetime import date, datetime

from selenium.common.exceptions import NoAlertPresentException
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
# GOLD's Description (reason) choices per type, as read from GOLD (Oct 2026). Optional.
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
TARGET_HIDDEN = "targetDate_tgtX$Date"
TARGET_HELPER = "targetDate_tgtX$DateHelper"

MONTHS = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]


def parse_date(text):
    """'11-oct-2026', '6 Dec 2026', '06/12/2026', '2026-12-06', datetime -> date. Raises ValueError."""
    if isinstance(text, datetime):
        return text.date()
    if isinstance(text, date):
        return text
    s = str(text).strip()
    m = re.fullmatch(r"(\d{1,2})[-\s/.]([A-Za-z]{3,9})[-\s/.,]*(\d{4})", s)
    if m:
        mon = m.group(2)[:3].title()
        if mon not in MONTHS:
            raise ValueError(f"unknown month in '{s}'")
        return date(int(m.group(3)), MONTHS.index(mon) + 1, int(m.group(1)))
    for fmt in ("%d/%m/%Y", "%d.%m.%Y", "%Y-%m-%d", "%Y-%m-%d %H:%M:%S"):
        try:
            return datetime.strptime(s, fmt).date()
        except ValueError:
            pass
    raise ValueError(f"'{s}' is not a date like 11-Oct-2026")


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


def find_rtdd_rows(driver, wait, title):
    """Milestones-tab rows whose Title is this RTDD title: [{Title, Target Date, ...}]."""
    oo.open_tab(driver, wait, "Milestones")
    out = []
    for g in gx.extract_tab(driver)["grids"]:
        if "Title" in g["columns"] and "Target Date" in g["columns"]:
            for r in g["rows"]:
                row = dict(zip(g["columns"], r))
                # GOLD shortens long titles in the list ("Revised Target Date - Orange Bus...").
                shown = row["Title"].rstrip(".")
                if shown and title.startswith(shown):
                    out.append(row)
    return out


def add_rtdd(driver, wait, order, kind, new_date, reason="", dry_run=False, log=print):
    """Open the order and add the RTDD milestone. Returns a short result message.
    dry_run: fill the form, then Cancel instead of Save."""
    title = RTDD_TITLES[kind]
    target = gold_date(new_date)

    # Start each order from the search page. GOLD Express's Firefox is only used by the app and
    # every change is either saved+verified or cancelled, so a leftover 'you will lose
    # changes' warning here is from our own cancelled attempt: safe to accept.
    oo.open_orders_tab(driver, wait, discard_changes=True)
    oo.untick_my_orders(driver)
    row = oo.search_order(driver, wait, order)
    oo.open_result(driver, wait, row, order)
    before = find_rtdd_rows(driver, wait, title)

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
        return f"dry run OK - form filled with {title} / {target}, then cancelled"

    form = driver.find_element(By.ID, "title")
    driver.find_element(By.CSS_SELECTOR, "img.butAddToOrder").click()
    time.sleep(0.4)
    alert = _accept_alert(driver)
    if alert:
        raise RuntimeError(f"GOLD refused: {alert.strip()}")
    Wait(driver, 60).until(EC.staleness_of(form))

    # Verify: a new RTDD row with this target date is on the Milestones tab.
    after = find_rtdd_rows(driver, wait, title)
    new_rows = [r for r in after if r.get("Target Date") == target]
    if len(after) <= len(before) or not new_rows:
        raise RuntimeError("saved, but the new milestone is not visible on the Milestones tab - "
                           "please check the order in GOLD")
    # The milestone is saved (verified above), but GOLD's page still warns "You will lose
    # any changes" because the date box marked the order as modified. Nothing is pending,
    # so leave the order now, accepting that warning, ready for the next one.
    oo.open_orders_tab(driver, wait, discard_changes=True)
    return f"added {title} with Target Date {target}"
