"""Orange Business Org Chart lookup: a person's email, job, phone and manager chain (the logic behind SALTO Buddy's
People tab and Org Chart tab; in GOLD Express: the Org Chart tab, Teams double-click and Ask GOLD's find_person).

Drop this file into any Python app (pip install selenium). It needs a Selenium WebDriver that can open the Org Chart
with the user's Orange sign-in (SSO). Use your app's own driver, or orgchart.firefox() below.

    import orgchart
    d = orgchart.firefox()                                   # or your own Selenium driver
    with orgchart.OrgChart(d) as oc:
        people = oc.find(last="Khairy", first="Ahmed")       # every match, each with "chain" (manager first)
        print(people[0]["email"], people[0]["chain"][0]["email"])
        names = oc.lookup(["Ahmed Khairy", "Jozef Chovanec"])  # SALTO-style display names -> person + manager

How it works: the Org Chart page (obs-orgchart.sso.infra.ftgroup) searches with a POST to /ooc_staff/search/
(lastName, firstName, email or cuid + the page's CSRF token). We send that same request from inside the signed-in
page, so the Orange sign-in and cookies are the page's own. A person's record has their manager's CUID (supr_cuid):
searching that CUID gives the manager, and so on up the chain.
"""
import json
import os
import re
import time
from contextlib import suppress
from urllib.parse import urlparse

from selenium.common.exceptions import TimeoutException, WebDriverException
from selenium.webdriver.common.by import By

HOME = "https://obs-orgchart.sso.infra.ftgroup/dashboard/home"
HOST = "obs-orgchart.sso.infra.ftgroup"
# display names that are systems, not people (SALTO participants such as "Salto Intl", "Service Level Agent")
NOT_PEOPLE = re.compile(r"^(salto\b|service level agent|system|batch|admin|unassigned)", re.I)

# Org Chart record field -> label (a record has more: pims, mgmt_code, dept_hierarchy, legalLastName...)
FIELDS = {"display_name": "Name", "email": "Email", "busi_title": "Job title", "dept_desc": "Department",
          "country_descr": "Country", "city": "City", "phone": "Phone", "mobile": "Mobile", "vendor_name": "Vendor",
          "supr_display_name": "Manager", "supr_cuid": "Manager CUID", "cuid": "CUID"}

_SEARCH_JS = r"""
const cb = arguments[arguments.length - 1];
const [last, first, email, cuid] = arguments;
$.ajax({url: '/ooc_staff/search/', type: 'POST', timeout: 30000,
  data: {csrfmiddlewaretoken: getCSRFToken(), firstName: first, lastName: last, email: email, cuid: cuid},
  success: j => cb({ok: j.empl || []}), error: x => cb({err: x.status})});
"""


def firefox(profile_dir=None, headless=False):
    """A Firefox driver with its own profile (the Orange sign-in is remembered there after the first time).
    Headless works once signed in; the first time, use headless=False so the user can complete the sign-in."""
    from selenium import webdriver
    from selenium.webdriver.firefox.options import Options
    profile_dir = profile_dir or os.path.join(os.environ.get("LOCALAPPDATA", "."), "OrgChartLookup", "profile")
    os.makedirs(profile_dir, exist_ok=True)
    opts = Options()
    opts.add_argument("-profile")
    opts.add_argument(profile_dir)
    opts.set_preference("network.http.windows-sso.enabled", True)  # Windows sign-in for Orange sites
    if headless:
        opts.add_argument("-headless")
    return webdriver.Firefox(options=opts)


def person(rec):
    """The useful fields of an Org Chart record (missing ones as "")."""
    return {k: (rec.get(k) or "").strip() for k in FIELDS}


class OrgChart:
    """An Org Chart tab in the driver. Use as a context manager: it opens its own tab, and on exit closes it and goes
    back to the tab you were on. cache_file: optional JSON file for lookup() results (kept keep_days)."""

    def __init__(self, driver, cache_file=None, keep_days=7, sign_in_wait=120, log=print):
        self.d, self.log = driver, log
        self.cache_file, self.keep_days, self.sign_in_wait = cache_file, keep_days, sign_in_wait
        self.handle = self.back = None

    # ---------------------------------------------------------------- tab
    def __enter__(self):
        d = self.d
        self.back = d.current_window_handle if d.window_handles else None
        d.switch_to.new_window("tab")
        self.handle = d.current_window_handle
        d.set_page_load_timeout(60)
        with suppress(TimeoutException):
            d.get(HOME)
        deadline = time.time() + self.sign_in_wait
        while time.time() < deadline:
            self._acknowledge()
            with suppress(WebDriverException):
                if urlparse(d.current_url).hostname == HOST and d.execute_script(
                        "return typeof getCSRFToken === 'function' && typeof $ !== 'undefined'"):
                    return self
            time.sleep(1)  # an Orange sign-in page: the user completes it in the window
        raise RuntimeError("The Org Chart did not open (Orange network / sign-in?).")

    def __exit__(self, *exc):
        d = self.d
        with suppress(WebDriverException):
            if self.handle in d.window_handles:
                d.switch_to.window(self.handle)
                d.close()
        with suppress(WebDriverException):
            if self.back:
                d.switch_to.window(self.back)

    def _acknowledge(self):
        """Click the Org Chart's acknowledgement / consent button when it asks for it."""
        with suppress(WebDriverException):
            for el in self.d.find_elements(By.XPATH, "//button | //a[contains(@class,'btn')] | //input[@type='submit']"):
                text = (el.text or el.get_attribute("value") or "").strip()
                if el.is_displayed() and re.search(r"acknowledg|^i agree|^accept|^i understand", text, re.I):
                    self.d.execute_script("arguments[0].click();", el)
                    time.sleep(1.5)
                    return

    # ---------------------------------------------------------------- search
    def search(self, last="", first="", email="", cuid=""):
        """Raw Org Chart records matching the fields (partial names work; same as the page's Search button)."""
        d = self.d
        d.switch_to.window(self.handle)
        d.set_script_timeout(40)
        r = d.execute_async_script(_SEARCH_JS, last, first, email, cuid) or {}
        if "err" in r:
            raise RuntimeError(f"The Org Chart search failed (HTTP {r['err']}).")
        return r.get("ok", [])

    def by_cuid(self, cuid):
        got = self.search(cuid=cuid)
        return person(got[0]) if got else None

    def find(self, last="", first="", email="", levels=6, limit=15):
        """Every match (up to limit), each a person() dict plus "chain": [manager, manager's manager, ...]."""
        return self.with_chains(self.search(last, first, email), levels, limit)

    def query(self, text, levels=6, limit=15):
        """Free-text search, as typed in a search box: "Ahmed El-Bourgy", "El-Bourgy", "KANADE Rahul", an email
        or a CUID. Returns find()-style people (best matches first)."""
        text = " ".join(text.split())
        if not text:
            return []
        if "@" in text:
            return self.find(email=text, levels=levels, limit=limit)
        if re.fullmatch(r"[A-Za-z]{4}\d{4}", text):
            return self.with_chains(self.search(cuid=text.upper()), levels, limit)
        spellings = list(dict.fromkeys([text, text.replace("-", " "), text.replace(" ", "-")]))
        if len(text.split()) == 1:
            for word in spellings:
                for last, first in ((word, ""), ("", word)):
                    recs = self.search(last, first)
                    if recs:
                        return self.with_chains(recs, levels, limit)
            return []
        for name in spellings:
            for last, first in name_variants(name):
                hits = best_matches(name, self.search(last, first))
                if hits:
                    return self.with_chains(hits, levels, limit)
        return self.with_chains(self.fallback(text), levels, limit)

    def fallback(self, name, emails_only=False):
        """Records for a name the plain search misses because it is written differently, e.g. GOLD's
        "ahmed elbourgy" for the Org Chart's "Ahmed EL BOURGY": guessed Orange emails, then every match of each
        word whose name is the same letters once spaces, hyphens and case are ignored."""
        words = [w for w in re.split(r"[\s,]+", name) if w]
        if len(words) < 2:
            return []
        first, rest = _letters(words[0]), _letters("".join(words[1:]))
        for email in (f"{first}.{rest}@orange.com", f"{first}.{rest}.ext@orange.com"):
            recs = self.search(email=email)
            if recs:
                return recs
        if emails_only:
            return []
        target = _letters(name)
        for word in words:
            for last, first_name in ((word, ""), ("", word)):
                recs = [r for r in self.search(last, first_name) if target in _spellings(r)]
                if recs:
                    return recs
        return []

    def with_chains(self, records, levels=6, limit=15):
        seen, people = {}, []
        for rec in records[:limit]:
            p, chain, cuid = person(rec), [], rec.get("supr_cuid")
            while cuid and len(chain) < levels and cuid not in [c["cuid"] for c in chain]:
                if cuid not in seen:
                    seen[cuid] = self.by_cuid(cuid)
                if not seen[cuid]:
                    break
                chain.append(seen[cuid])
                cuid = seen[cuid]["supr_cuid"]
            p["chain"] = chain
            people.append(p)
        return people

    def lookup(self, names, refresh=False):
        """For display names ("Ahmed Khairy", "Linh Le Nu Dieu"): {name: {"person", "manager", "matches", "note"}}.
        person/manager are person() dicts or None; note says "not found..." or "N people with this name..."."""
        cache = {} if refresh else self._load()
        managers = {}
        for name in dict.fromkeys(names):
            if not name or NOT_PEOPLE.match(name) or name in cache:
                continue
            hits = []
            for last, first in name_variants(name):
                hits = best_matches(name, self.search(last, first))
                if hits:
                    break
            if not hits:  # quick part of the fallback only: team lists hold many group names ("GCC EUMA")
                hits = self.fallback(name, emails_only=True)
            entry = {"person": None, "manager": None, "matches": len(hits), "saved": time.time(),
                     "note": "" if len(hits) == 1 else ("not found in the Org Chart" if not hits else
                                                        f"{len(hits)} people with this name: the first is shown")}
            if hits:
                entry["person"] = person(hits[0])
                sup = entry["person"]["supr_cuid"]
                if sup:
                    if sup not in managers:
                        managers[sup] = self.by_cuid(sup)
                    entry["manager"] = managers[sup]
            cache[name] = entry
        self._save(cache)
        return {n: cache[n] for n in dict.fromkeys(names) if n in cache}

    # ---------------------------------------------------------------- cache
    def _load(self):
        if not self.cache_file:
            return {}
        with suppress(OSError, ValueError):
            data = json.load(open(self.cache_file, encoding="utf-8"))
            cutoff = time.time() - self.keep_days * 86400
            return {k: v for k, v in data.items() if v.get("saved", 0) > cutoff}
        return {}

    def _save(self, data):
        if not self.cache_file:
            return
        with suppress(OSError):
            os.makedirs(os.path.dirname(os.path.abspath(self.cache_file)), exist_ok=True)
            merged = {**self._load(), **data}
            with open(self.cache_file + ".tmp", "w", encoding="utf-8") as f:
                json.dump(merged, f)
            os.replace(self.cache_file + ".tmp", self.cache_file)


# ---------------------------------------------------------------- matching a display name
def _letters(s):
    return re.sub(r"[^a-z]", "", (s or "").lower())


def _spellings(rec):
    """A record's name as bare letters, in the orders it may be written (first+last, last+first)."""
    first, last = rec.get("legalFirstName", ""), rec.get("legalLastName", "")
    return {_letters(rec.get("display_name", "")), _letters(first + last), _letters(last + first)}


def name_variants(name):
    """(last, first) guesses for a display name: "Ahmed El-Bourgy", "Linh Le Nu Dieu", "KANADE Rahul"."""
    parts = [p for p in re.split(r"\s+", name.replace(",", " ").strip()) if p]
    if len(parts) < 2:
        return [(parts[0], "")] if parts else []
    out = [(" ".join(parts[1:]), parts[0]), (parts[-1], " ".join(parts[:-1])), (parts[-1], parts[0]),
           (parts[0], " ".join(parts[1:]))]
    return list(dict.fromkeys(out))


def best_matches(name, found):
    """The records that really are this person: most name words in common (at least first + last)."""
    want = {w for w in re.split(r"[\s,.-]+", name.lower()) if w}

    def score(rec):
        have = {w for w in re.split(r"[\s,.-]+", " ".join(
            [rec.get("display_name", ""), rec.get("legalFirstName", ""), rec.get("legalLastName", "")]).lower()) if w}
        return len(want & have)
    if not found:
        return []
    top = max(score(r) for r in found)
    return [r for r in found if score(r) == top and top >= min(2, len(want))]
