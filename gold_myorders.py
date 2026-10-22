"""My Orders: the orders GOLD lists for you (Orders > 'My orders only'), read from every result page.

Read-only. GOLD's results page carries every row's details in its own script
(_grid_setupDetails(<names>) and one _grid_addDetail('detail_..', <values>) per order); we read those, so
nothing depends on the grid being drawn. Each order: order, type, customer, ban, orange_site_ref,
site_id, cust_site_ref, customer_num, status, service, escalation, sales_region, sales_country,
bundled, bundled_type, ittd, installed_offer.
"""
import html
import re
import time
from datetime import date, datetime

from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys

import open_order as oo
from open_gold import Wait, page_text

# GOLD's detail names -> our keys
DETAILS = {"Order": "order", "Order Type": "type", "Customer Name": "customer", "BAN": "ban",
           "Orange Site Ref": "orange_site_ref", "Site Id": "site_id", "Cust. Site Ref": "cust_site_ref",
           "Customer Num.": "customer_num", "Order Status": "status", "Service": "service",
           "Escalation": "escalation", "Sales Region": "sales_region", "Sales Country": "sales_country",
           "Bundled Order": "bundled", "Bundled Type": "bundled_type", "iTTD": "ittd",
           "2nd BAN": "ban2", "Installed Offer Id": "installed_offer"}
ORDER_TYPES = {"N": "New", "C": "Change", "D": "Disconnect"}
STATUSES = ["Creation", "Pricing", "Approval", "Release", "Manage", "Acceptance", "Billing", "Awaiting Close",
            "On-Hold", "Closed"]
_STR = re.compile(r'"((?:[^"\\]|\\.)*)"')


def _strings(args):
    return [re.sub(r"<[^>]*>", "", html.unescape(s.replace('\\"', '"'))).replace("\xa0", " ").strip()
            for s in _STR.findall(args)]


def _ittd(text):
    """'Dec 4, 2026 1:03:11 PM' -> date (or None)."""
    for fmt in ("%b %d, %Y %I:%M:%S %p", "%b %d, %Y"):
        try:
            return datetime.strptime(text.strip(), fmt).date()
        except ValueError:
            pass
    return None


def _read_page(driver):
    """(orders on this results page, total orders listed)."""
    src = driver.page_source
    names = _strings((re.search(r"_grid_setupDetails\((.*?)\);", src, re.S) or [None, ""])[1])
    out = []
    for args in re.findall(r"_grid_addDetail\('[^']*',(.*?)\);\s*\n", src, re.S):
        values = _strings(args)
        row = {DETAILS[n]: values[i] for i, n in enumerate(names) if n in DETAILS and i < len(values)}
        if re.fullmatch(r"\d{2}-\d{5,8}", row.get("order", "")):
            row["type"] = ORDER_TYPES.get(row.get("type", ""), row.get("type", ""))
            row["ittd_date"] = _ittd(row.get("ittd", ""))
            out.append(row)
    m = re.search(r"(\d+) orders? listed", page_text(driver), re.I)
    return out, int(m.group(1)) if m else len(out)


def _wait_results(driver, old_body, timeout=90):
    """Wait for the new results page to have loaded."""
    try:
        Wait(driver, 30).until(lambda d: d.find_element(By.TAG_NAME, "body") != old_body)
    except Exception:
        pass
    Wait(driver, timeout).until(lambda d: d.execute_script("return document.readyState") == "complete" and (
        "orders listed" in page_text(d).lower() or "no orders" in page_text(d).lower()))


def read_my_orders(driver, wait, log=print):
    """All orders in GOLD's 'My orders only' list (every page). Leaves the tick as GOLD had it."""
    oo.open_orders_tab(driver, wait, discard_changes=True)
    cb = driver.find_element(By.ID, "myOrdersOnlyCB")
    was_ticked = cb.is_selected()
    if not was_ticked:
        cb.click()
    page = 1
    try:
        old = driver.find_element(By.TAG_NAME, "body")
        box = driver.find_element(By.ID, "orderNb")
        box.clear()
        box.send_keys(Keys.ENTER)
        _wait_results(driver, old)
        orders, total = _read_page(driver)
        page = 1
        seen = {o["order"] for o in orders}
        while total and len(orders) < total and page < 50:
            page += 1
            log(f"My orders: reading page {page} ({len(orders)} of {total})...")
            old = driver.find_element(By.TAG_NAME, "body")
            driver.execute_script(f"gotoPage({page}, 'OrderManager');")
            _wait_results(driver, old)
            new, _ = _read_page(driver)
            new = [o for o in new if o["order"] not in seen]
            if not new:
                break
            seen.update(o["order"] for o in new)
            orders += new
        return orders
    finally:
        if page > 1:  # back to page 1: GOLD keeps the page for the next search, whose row clicks then miss
            try:
                old = driver.find_element(By.TAG_NAME, "body")
                driver.execute_script("gotoPage(1, 'OrderManager');")
                _wait_results(driver, old)
            except Exception:
                pass
        if not was_ticked:  # leave the search page as the rest of the app expects it
            try:
                driver.find_element(By.ID, "myOrdersOnlyCB").click()
            except Exception:
                pass


def summary(orders):
    """Counts for the dashboard."""
    by_status, by_customer, by_type = {}, {}, {}
    for o in orders:
        by_status[o.get("status") or "Unknown"] = by_status.get(o.get("status") or "Unknown", 0) + 1
        by_customer[o.get("customer") or "Unknown"] = by_customer.get(o.get("customer") or "Unknown", 0) + 1
        by_type[o.get("type") or "Unknown"] = by_type.get(o.get("type") or "Unknown", 0) + 1
    order = {s: i for i, s in enumerate(STATUSES)}
    today = date.today()
    live = [o for o in orders if o.get("status") != "Closed"]
    return {"total": len(orders),
            "open": len(live),
            "closed": by_status.get("Closed", 0),
            "on_hold": by_status.get("On-Hold", 0),
            # target date (iTTD) passed / within 30 days, for orders not closed
            "late": sum(1 for o in live if o.get("ittd_date") and o["ittd_date"] < today),
            "due_30": sum(1 for o in live if o.get("ittd_date") and 0 <= (o["ittd_date"] - today).days <= 30),
            "upcoming": sorted((o for o in live if o.get("ittd_date")), key=lambda o: o["ittd_date"]),
            "customers": len(by_customer),
            "by_status": sorted(by_status.items(), key=lambda kv: order.get(kv[0], 99)),
            "by_customer": sorted(by_customer.items(), key=lambda kv: -kv[1]),
            "by_type": sorted(by_type.items(), key=lambda kv: -kv[1])}
