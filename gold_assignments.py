"""Order Assignment: who (which DPM) is the STM of each open APM order.

The orders come from the "Power BI - APM Open Orders" workbook on the GDO OTB Analytics SharePoint
(kmlibraries, Orange sign-in), which is refreshed every day: the app reads it from that link (once a day,
or on Refresh) and keeps only the latest copy. Each order's "STM Name" is matched with the DPM names list:
assigned to a DPM (with their region, e.g. APM Europe), unassigned (no STM), or assigned to someone who
is not in the DPM list.
"""
import base64
import time
from contextlib import suppress
from datetime import date, datetime
from pathlib import Path
from urllib.parse import urlparse

import gold_names as gn

SOURCE_URL = ("https://kmlibraries-shp.itn.intraorange/GDO-OTB/GDO%20OTB%20Analytics/"
              "Power%20BI%20-%20APM%20Open%20Orders/Power%20BI%20-%20APM%20Open%20Orders.xlsx")

# The workbook's columns we use (by header text, so a moved column still works)
COLUMNS = {"order": "Order Number", "status": "Order Status", "type": "Order Type", "service": "Product/Service To",
           "country": "Country Name", "customer": "Contracting Party Customer Name",
           "end_customer": "End User Customer Name", "cluster": "Contracting Party Sales Cluster",
           "stm": "STM Name", "signed": "Customer Signature Date", "ittd": "Initial Target Delivery Date",
           "rtdd": "Revised Target Delivery Date", "rtdd_reason": "Reason - Revised Target Delivery Date",
           "project": "Project Name", "age": "Order Age_BO", "due_days": "Days to Due Date_BO",
           "backlog": "Backlog_BO", "site_ref": "Customer Site Reference"}

ASSIGNED, UNASSIGNED, NOT_IN_LIST = "Assigned", "Unassigned", "Not in DPM list"
NO_TEAM = "No team"  # a DPM-list name without a team (add it in DPM names > Edit, or import the teams)
REGIONS = {team: dept for dept, team in gn.TEAMS.items()}  # "DPM Egypt" -> "APM Europe"

_FETCH_JS = r"""
const cb = arguments[arguments.length - 1];
fetch(arguments[0], {credentials: 'include'}).then(async r => {
  const b = new Uint8Array(await r.arrayBuffer());
  let s = ''; for (let i = 0; i < b.length; i += 32768) s += String.fromCharCode.apply(null, b.subarray(i, i + 32768));
  cb({status: r.status, data: btoa(s)});
}).catch(e => cb({err: String(e)}));
"""


def fetch(driver, dest, url=SOURCE_URL, sign_in_wait=90):
    """Download the workbook with the user's Orange sign-in: open its SharePoint library in a new tab of the
    app's Firefox (it signs in like GOLD does), fetch the file from there, close the tab. Writes dest."""
    folder = url.rsplit("/", 2)[0] + "/"  # the library the file sits in
    host = urlparse(url).hostname
    home = driver.current_window_handle
    driver.switch_to.new_window("tab")
    try:
        driver.set_page_load_timeout(90)
        with suppress(Exception):
            driver.get(folder)
        deadline = time.time() + sign_in_wait
        while time.time() < deadline:
            with suppress(Exception):
                if urlparse(driver.current_url).hostname == host and \
                        driver.execute_script("return document.readyState") == "complete":
                    break
            time.sleep(1)
        else:
            raise RuntimeError("the SharePoint site did not open - are you on the Orange network?")
        driver.set_script_timeout(240)
        r = driver.execute_async_script(_FETCH_JS, url) or {}
        if "err" in r:
            raise RuntimeError(f"the file could not be downloaded ({r['err']})")
        data = base64.b64decode(r.get("data", ""))
        if r.get("status") != 200 or data[:2] != b"PK":
            raise RuntimeError(f"the file could not be downloaded (HTTP {r.get('status')}) - "
                               "do you have access to the GDO OTB Analytics site?")
        dest = Path(dest)
        dest.parent.mkdir(parents=True, exist_ok=True)
        tmp = dest.with_name(dest.name + ".part")
        tmp.write_bytes(data)
        tmp.replace(dest)
        return dest
    finally:
        with suppress(Exception):
            driver.close()
        driver.switch_to.window(home)


def _cell(v):
    if isinstance(v, datetime):
        return v.date()
    if isinstance(v, str):
        return " ".join(v.split())
    return v


def read(path):
    """The orders in the workbook: [{key: value}] with the COLUMNS keys (dates as date)."""
    import warnings
    from openpyxl import load_workbook
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")  # "Workbook contains no default style"
        wb = load_workbook(path, read_only=True, data_only=True)
    try:
        ws = next((w for w in wb.worksheets if w.title.lower().startswith("open orders")), wb.worksheets[0])
        rows = ws.iter_rows(values_only=True)
        where = None
        for row in rows:  # the header row (there may be empty rows above it)
            names = [str(c or "").strip() for c in row]
            if COLUMNS["order"] in names:
                where = {k: names.index(h) for k, h in COLUMNS.items() if h in names}
                break
        if not where or "stm" not in where:
            raise RuntimeError("this file has no 'Order Number' / 'STM Name' columns - is it the APM Open Orders "
                               "workbook?")
        orders = []
        for row in rows:
            o = {k: _cell(row[i]) if i < len(row) else None for k, i in where.items()}
            if o.get("order"):
                o["order"] = str(o["order"]).strip()
                orders.append(o)
        return orders
    finally:
        wb.close()


def classify(orders, dpm_names):
    """Add to each order: "dpm" (the DPM-list name, or the STM as written), "category" (ASSIGNED,
    UNASSIGNED, NOT_IN_LIST), "team" (DPM Egypt...) and "region" (APM Europe...). Names are matched
    ignoring spaces, hyphens, capitals and first/last order ("Salma El-Shazly" = "Salma Elshazly")."""
    index = {}
    for e in dpm_names:
        full = gn.full_name(e)
        index.setdefault(gn.letters(full), e)
        index.setdefault(gn.letters(e["last"] + e["first"]), e)
    for o in orders:
        stm = (o.get("stm") or "").strip()
        o["target"] = o.get("rtdd") or o.get("ittd")
        if not stm:
            o.update(dpm="", category=UNASSIGNED, team="", region="")
            continue
        e = index.get(gn.letters(stm))
        if e is None:
            words = stm.split()
            if len(words) > 1:
                e = index.get(gn.letters(" ".join(words[1:] + words[:1])))
        if e is None:
            o.update(dpm=" ".join(w.capitalize() if w.isupper() or w.islower() else w for w in stm.split()),
                     category=NOT_IN_LIST, team="", region="")
        else:
            team = e.get("team") or ""
            o.update(dpm=gn.full_name(e), category=ASSIGNED, team=team,
                     region=REGIONS.get(team, team or NO_TEAM))
    return orders


def summary(orders):
    """Counts for the dashboard."""
    by = lambda cat: sum(1 for o in orders if o["category"] == cat)
    return {"total": len(orders), "assigned": by(ASSIGNED), "unassigned": by(UNASSIGNED),
            "not_in_list": by(NOT_IN_LIST), "dpms": len({o["dpm"] for o in orders if o["category"] == ASSIGNED}),
            "outsiders": len({o["dpm"] for o in orders if o["category"] == NOT_IN_LIST})}


def per_person(orders):
    """[(name, region or category, number of orders, overdue)] for every STM, most orders first."""
    count, overdue, where = {}, {}, {}
    for o in orders:
        if o["category"] == UNASSIGNED:
            continue
        k = o["dpm"]
        count[k] = count.get(k, 0) + 1
        overdue[k] = overdue.get(k, 0) + (1 if str(o.get("backlog") or "").lower() == "overdue" else 0)
        where[k] = o["region"] if o["category"] == ASSIGNED else NOT_IN_LIST
    return sorted(((k, where[k], count[k], overdue[k]) for k in count), key=lambda r: (-r[2], r[0].lower()))


def fmt_date(d):
    return d.strftime("%d-%b-%Y") if isinstance(d, date) else (str(d) if d else "")
