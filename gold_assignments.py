"""Order Assignment: who (which DPM) is the STM of each open APM order.

The orders come from the "Power BI - APM Open Orders" workbook on the GDO OTB Analytics SharePoint
(kmlibraries, Orange sign-in), which is refreshed every day: the app reads it from that link (once a day,
or on Refresh) and keeps only the latest copy. Each order's "STM Name" is matched with the DPM names list:
assigned to a DPM (with their region, e.g. APM Europe), unassigned (no STM), or assigned to someone who
is not in the DPM list.
"""
import base64
import re
import time
from contextlib import suppress
from datetime import date, datetime, timedelta
from pathlib import Path
from urllib.parse import urlparse

import gold_names as gn

# The sheet's SharePoint link, as shared (Settings > Order Assignment can change it). The data is never kept
# in the app: it is read from this link, and read again whenever SharePoint has a newer version.
SOURCE_LINK = ("https://kmlibraries-shp.itn.intraorange/GDO-OTB/GDO%20OTB%20Analytics/"
               "Power%20BI%20-%20APM%20Open%20Orders/Power%20BI%20-%20APM%20Open%20Orders.xlsx"
               "?d=w39fe582af0264b7fa3ba641248168f24")


def file_url(link):
    """The file itself: a shared link's '?d=...' / '?web=1' opens the Excel Online viewer instead."""
    return link.strip().split("#")[0].split("?")[0]


def file_name(link):
    from urllib.parse import unquote
    return unquote(file_url(link).rsplit("/", 1)[-1])

# The workbook's columns we use (by header text, so a moved column still works)
COLUMNS = {"order": "Order Number", "status": "Order Status", "type": "Order Type", "service": "Product/Service To",
           "country": "Country Name", "customer": "Contracting Party Customer Name",
           "end_customer": "End User Customer Name", "cluster": "Contracting Party Sales Cluster",
           "stm": "STM Name", "signed": "Customer Signature Date", "ittd": "Initial Target Delivery Date",
           "rtdd": "Revised Target Delivery Date", "rtdd_reason": "Reason - Revised Target Delivery Date",
           "project": "Project Name", "age": "Order Age_BO", "due_days": "Days to Due Date_BO",
           "backlog": "Backlog_BO", "site_ref": "Customer Site Reference", "revenue": "Total Revenue"}

ASSIGNED, UNASSIGNED, NOT_IN_LIST = "Assigned", "Unassigned", "Not in DPM list"
OVERDUE, DUE_14, NOT_OVERDUE, NO_DATE = "Overdue RTDD", "Overdue in 14 days", "Not Overdue", "No date"  # the sheet's
NO_RTDD, RTDD_PASSED = "No RTDD set", "RTDD date passed"  # what an overdue order needs   # Backlog column
NOT_CHECKED = "RTDD not checked"  # My Orders: past its initial date, and its RTDD has not been read yet
AGE_BANDS = (("Under 3 months", 91), ("3-6 months", 183), ("6-12 months", 366), ("1-2 years", 731),
             ("Over 2 years", None))
LATE_BANDS = (("1-30 days", 31), ("31-90 days", 91), ("91-180 days", 181), ("Over 180 days", None))
NO_TEAM = "No team"  # a DPM-list name without a team (add it in DPM names > Edit, or import the teams)
REGIONS = {team: dept for dept, team in gn.TEAMS.items()}  # "DPM Egypt" -> "APM Europe"

# Ask SharePoint for the file's version (ETag) and time; read it only when it is a version we don't have
_FETCH_JS = r"""
const cb = arguments[arguments.length - 1];
const [url, known] = arguments;
(async () => {
  const h = await fetch(url, {method: 'HEAD', credentials: 'include'});
  const info = {status: h.status, etag: h.headers.get('etag'), modified: h.headers.get('last-modified'),
                type: h.headers.get('content-type') || ''};
  if (h.status !== 200 || (known && info.etag === known)) return cb(info);
  const r = await fetch(url, {credentials: 'include'});
  const b = new Uint8Array(await r.arrayBuffer());
  let s = ''; for (let i = 0; i < b.length; i += 32768) s += String.fromCharCode.apply(null, b.subarray(i, i + 32768));
  info.status = r.status; info.etag = r.headers.get('etag') || info.etag;
  info.modified = r.headers.get('last-modified') || info.modified; info.data = btoa(s);
  cb(info);
})().catch(e => cb({err: String(e)}));
"""


def fetch(driver, dest, link=SOURCE_LINK, known_version=None, sign_in_wait=90):
    """Read the sheet from its SharePoint link with the user's Orange sign-in: open its library in a new tab of
    the app's Firefox (it signs in like GOLD does), ask SharePoint for the file's current version and, when
    it is not known_version (or dest is missing), download it to dest (replacing the old copy). Closes the tab.
    Returns {"changed": bool, "version": etag, "modified": datetime (UTC) or None}."""
    url = file_url(link)
    if Path(dest).exists() is False:
        known_version = None
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
        r = driver.execute_async_script(_FETCH_JS, url, known_version or "") or {}
        if "err" in r:
            raise RuntimeError(f"the sheet could not be read ({r['err']})")
        if r.get("status") != 200:
            raise RuntimeError(f"the sheet could not be read (HTTP {r.get('status')}) - is the link right, and do "
                               "you have access to that SharePoint site?")
        modified = None
        with suppress(Exception):
            from email.utils import parsedate_to_datetime
            modified = parsedate_to_datetime(r["modified"])
        info = {"changed": "data" in r, "version": r.get("etag"), "modified": modified}
        if "data" in r:
            data = base64.b64decode(r["data"])
            if data[:2] != b"PK":
                raise RuntimeError("the link does not give an Excel file - use the sheet's own link")
            dest = Path(dest)
            dest.parent.mkdir(parents=True, exist_ok=True)
            tmp = dest.with_name(dest.name + ".part")
            tmp.write_bytes(data)
            tmp.replace(dest)  # the previous copy is replaced
        return info
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
    UNASSIGNED, NOT_IN_LIST), "team" (DPM Egypt...), "region" (APM Europe...) and "manager" (the DPM's
    manager, from the Org Chart). Names are matched
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
            o.update(dpm="", category=UNASSIGNED, team="", region="", manager="")
            continue
        e = index.get(gn.letters(stm))
        if e is None:
            words = stm.split()
            if len(words) > 1:
                e = index.get(gn.letters(" ".join(words[1:] + words[:1])))
        if e is None:
            o.update(dpm=" ".join(w.capitalize() if w.isupper() or w.islower() else w for w in stm.split()),
                     category=NOT_IN_LIST, team="", region="", manager="")
        else:
            team = e.get("team") or ""
            o.update(dpm=gn.full_name(e), category=ASSIGNED, team=team,
                     region=REGIONS.get(team, team or NO_TEAM), manager=e.get("manager") or "")
    return orders


def summary(orders):
    """Counts for the dashboard."""
    by = lambda cat: sum(1 for o in orders if o["category"] == cat)
    return {"total": len(orders), "assigned": by(ASSIGNED), "unassigned": by(UNASSIGNED),
            "not_in_list": by(NOT_IN_LIST), "dpms": len({o["dpm"] for o in orders if o["category"] == ASSIGNED}),
            "outsiders": len({o["dpm"] for o in orders if o["category"] == NOT_IN_LIST})}


def _number(v):
    try:
        return float(v)
    except (TypeError, ValueError):
        return None


def days_left(o):
    """Days to the target date: the sheet's 'Days to Due Date', which is empty for an order with an RTDD but
    no initial date (then worked out from the RTDD). None without any date."""
    d = _number(o.get("due_days"))
    if d is not None:
        return int(d)
    t = o.get("target")
    return (t - date.today()).days if isinstance(t, date) else None


def rtdd_status(o):
    """OVERDUE, DUE_14, NOT_OVERDUE or NO_DATE: the sheet's Backlog column, else from the days to the target date."""
    backlog = str(o.get("backlog") or "").strip().lower()
    for status in (OVERDUE, DUE_14, NOT_OVERDUE):
        if backlog == status.lower():
            return status
    d = days_left(o)
    return NO_DATE if d is None else OVERDUE if d < 0 else DUE_14 if d <= 14 else NOT_OVERDUE


def is_overdue(o):
    return rtdd_status(o) == OVERDUE


def rtdd_action(o):
    """What an overdue order needs from its DPM: NO_RTDD (never revised), RTDD_PASSED (revised, and that date
    has passed too) or NOT_CHECKED (not known yet). "" for the others."""
    if not is_overdue(o):
        return ""
    return RTDD_PASSED if o.get("rtdd") else NOT_CHECKED if o.get("rtdd_known") is False else NO_RTDD


def rtdd_reason(o):
    """The sheet's reason text as (whose reason, the date on it): '13-Jul-2026 Customer Reason' ->
    ("Customer", date(2026, 7, 13)). ("", None) without a reason."""
    text = str(o.get("rtdd_reason") or "")
    if not text:
        return "", None
    low = text.lower()
    who = ("Customer" if "customer reason" in low else "Orange" if "orange business" in low
           else "MHS" if "mhs" in low else "Other")
    when = None
    m = re.match(r"\s*(\d{2}-[A-Za-z]{3}-\d{4})", text)
    if m:
        with suppress(ValueError):
            when = datetime.strptime(m[1], "%d-%b-%Y").date()
    return who, when


def per_person(orders):
    """[(name, region or category, number of orders, overdue, manager)] for every STM, most orders first."""
    count, overdue, where, manager = {}, {}, {}, {}
    for o in orders:
        if o["category"] == UNASSIGNED:
            continue
        k = o["dpm"]
        count[k] = count.get(k, 0) + 1
        overdue[k] = overdue.get(k, 0) + (1 if is_overdue(o) else 0)
        where[k] = o["region"] if o["category"] == ASSIGNED else NOT_IN_LIST
        manager[k] = o.get("manager") or ""
    return sorted(((k, where[k], count[k], overdue[k], manager[k]) for k in count),
                  key=lambda r: (-r[2], r[0].lower()))


def _blank_kpi(name=""):
    return {"name": name, "manager": "", "region": "", "dpms": 0, "open": 0, "revenue": 0.0, "overdue": 0,
            "overdue_rev": 0.0, "due14": 0, "due14_rev": 0.0, "ok": 0, "ok_rev": 0.0, "no_date": 0, "no_rtdd": 0,
            "passed": 0, "due_soon": 0, "revised": 0, "overdue_pct": 0, "avg_age": None, "oldest": None}


def dpm_kpis(orders, by="dpm", soon=30):
    """The DPM dashboard's numbers for the assigned orders, one row per DPM (or per manager, team, cluster,
    customer: by is the order's field, None for one Total row), most overdue first. Each row: name, manager,
    region, dpms, open, revenue; overdue, due14, ok and no_date (the RTDD status, with _rev: their revenue);
    no_rtdd, passed (what the overdue orders need), due_soon (due in 0..soon days), revised (has an RTDD),
    overdue_pct, avg_age and oldest (order age in days, None when unknown)."""
    rows = {}
    key = {OVERDUE: "overdue", DUE_14: "due14", NOT_OVERDUE: "ok", NO_DATE: "no_date"}
    for o in orders:
        if o["category"] != ASSIGNED:
            continue
        name = "Total" if by is None else (o.get(by) or "")
        r = rows.get(name)
        if r is None:
            r = rows[name] = dict(_blank_kpi(name), manager=(o.get("manager") or "") if by == "dpm" else "",
                                  region=o["region"] if by == "dpm" else "", _ages=[], _dpms=set())
        status = rtdd_status(o)
        revenue = _number(o.get("revenue")) or 0
        d = days_left(o)
        r["open"] += 1
        r["revenue"] += revenue
        r[key[status]] += 1
        if status != NO_DATE:
            r[key[status] + "_rev"] += revenue
        r["no_rtdd"] += rtdd_action(o) == NO_RTDD
        r["passed"] += rtdd_action(o) == RTDD_PASSED
        r["due_soon"] += status != OVERDUE and d is not None and 0 <= d <= soon
        r["revised"] += bool(o.get("rtdd"))
        r["_dpms"].add(o["dpm"])
        age = _number(o.get("age"))
        if age is not None:
            r["_ages"].append(age)
    out = []
    for r in rows.values():
        ages = r.pop("_ages")
        r["dpms"] = len(r.pop("_dpms"))
        r["overdue_pct"] = round(100 * r["overdue"] / r["open"]) if r["open"] else 0
        r["avg_age"] = round(sum(ages) / len(ages)) if ages else None
        r["oldest"] = round(max(ages)) if ages else None
        out.append(r)
    return sorted(out, key=lambda r: (-r["overdue"], -r["open"], r["name"].lower()))


def kpi_total(orders):
    return (dpm_kpis(orders, by=None) or [_blank_kpi("Total")])[0]


def _band(value, bands):
    return next(name for name, top in bands if top is None or value < top)


def week_labels(weeks=5):
    """The weeks of the 'When orders fall due' chart: this one first."""
    monday = date.today() - timedelta(days=date.today().weekday())
    return [f"w/c {monday + timedelta(weeks=i):%d-%b}" for i in range(weeks)]


def due_week(o, weeks=5):
    """When the order falls due: "Overdue", "w/c 02-Nov" (one of week_labels), "Later", or "" without a date."""
    if is_overdue(o):
        return "Overdue"
    d = days_left(o)
    if d is None:
        return ""
    monday = date.today() - timedelta(days=date.today().weekday())
    week = max(((date.today() + timedelta(days=d)) - monday).days // 7, 0)
    return week_labels(weeks)[week] if week < weeks else "Later"


def order_dims(o):
    """What the dashboards' charts can filter on, for one order."""
    late = days_left(o)
    age = _number(o.get("age"))
    who = "Not checked" if o.get("rtdd_known") is False else "Not revised"
    return {"status": rtdd_status(o), "action": rtdd_action(o), "due": due_week(o),
            "late": _band(max(-late, 0), LATE_BANDS) if is_overdue(o) and late is not None else "",
            "reason": (rtdd_reason(o)[0] or "Other") if o.get("rtdd") else who,
            "age": "" if age is None else _band(age, AGE_BANDS), "stage": o.get("status") or "",
            "type": (o.get("type") or "").title(), "service": o.get("service") or "",
            "country": (o.get("country") or o.get("sales_country") or "").title(),
            "customer": o.get("customer") or "", "manager": o.get("manager") or "", "dpm": o.get("dpm") or "",
            "team": o.get("team") or "", "cluster": o.get("cluster") or ""}


def average_slip(orders):
    """How many days the revised orders moved, on average: RTDD minus initial date. None without any."""
    slips = [(o["rtdd"] - o["ittd"]).days for o in orders
             if isinstance(o.get("rtdd"), date) and isinstance(o.get("ittd"), date)]
    return round(sum(slips) / len(slips)) if slips else None


def money(v):
    """€2.66M, €89k, €950, -€1k."""
    v = v or 0
    a = abs(v)
    text = f"€{a / 1e6:.2f}M" if a >= 1e6 else f"€{a / 1e3:.0f}k" if a >= 1e3 else f"€{a:.0f}"
    return "-" + text if v < 0 and text != "€0" else text


def fmt_date(d):
    return d.strftime("%d-%b-%Y") if isinstance(d, date) else (str(d) if d else "")
