"""Ask GOLD: a chat assistant (Claude) that answers questions about GOLD orders.

Claude reads orders through two tools that run on the app's GOLD session (read-only):
  get_order_overview(order)    key facts: dates, status, value, site, people, latest note
  read_order_tab(order, tab)   everything on one tab (Pricing, Milestones, Notes, Billing...)

The API key is never part of the app (the installer is public): it is read at run time from the
team's key file (salto-buddy-team.key) in the team's SharePoint folder - downloaded automatically
with the user's Windows / Orange sign-in, which only team members can open - and kept on this PC
encrypted for this Windows user (DPAPI).
"""
import ctypes
import ctypes.wintypes
import json
import re
import time
from datetime import date, datetime
from pathlib import Path
from urllib.parse import parse_qs, urlparse

MODEL = "claude-opus-5-5"
KEY_FILE_NAME = "salto-buddy-team.key"
# The team folder that holds the key file (opens only for Orange accounts it is shared with).
SHARE_URL = ("https://orange0-my.sharepoint.com/:f:/g/personal/ahmed_elbourgy_ext_orange_com/"
             "IgBIet85KpwDSoTaxyAIlhvqAU5wFrH1Muf4zmBEifupeuw?e=7cyXjl")
CACHE_MIN = 5          # re-use what was read from GOLD for this many minutes
MAX_TOOL_TEXT = 60000  # characters of one tab sent to Claude
MAX_STEPS = 12         # tool rounds per question


# ---------------------------------------------------------------- key file

def _sync_roots():
    """Folders OneDrive syncs on this PC (personal OneDrive with SharePoint shortcuts, synced libraries)."""
    import os
    roots = []
    try:
        import winreg
        base = r"Software\SyncEngines\Providers\OneDrive"
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, base) as k:
            for i in range(winreg.QueryInfoKey(k)[0]):
                with winreg.OpenKey(k, winreg.EnumKey(k, i)) as sub:
                    roots.append(winreg.QueryValueEx(sub, "MountPoint")[0])
    except OSError:
        pass
    roots += [os.environ.get("OneDriveCommercial", "")] + [str(p) for p in Path.home().glob("OneDrive*")]
    return [Path(r) for r in dict.fromkeys(roots) if r and Path(r).is_dir()]


def find_key_file(saved=""):
    """The key file on disk: the one chosen in Settings, else the team folder synced by OneDrive."""
    if saved and Path(saved).is_file():
        return Path(saved)
    for root in _sync_roots():
        for pattern in (f"SALTO Buddy/{KEY_FILE_NAME}", KEY_FILE_NAME, f"*/{KEY_FILE_NAME}",
                        f"*/*/{KEY_FILE_NAME}"):
            for p in root.glob(pattern):
                if p.is_file():
                    return p
    return None


def _first_key(text):
    key = next((line.strip() for line in (text or "").splitlines() if line.strip()), "")
    return key if key.startswith("sk-ant-") else ""


def load_key(path):
    """The API key from a key file on disk, or a clear error."""
    try:
        text = Path(path).read_text(encoding="utf-8-sig")
    except OSError as e:
        raise RuntimeError(f"Could not read the AI key file {path}:\n{e}") from None
    key = _first_key(text)
    if not key:
        raise RuntimeError(f"{path} does not contain an Anthropic API key.")
    return key


# --- the key kept on this PC, encrypted for this Windows user (DPAPI)

class _Blob(ctypes.Structure):
    _fields_ = [("cbData", ctypes.wintypes.DWORD), ("pbData", ctypes.POINTER(ctypes.c_char))]


def _dpapi(data, protect):
    crypt32, kernel32 = ctypes.windll.crypt32, ctypes.windll.kernel32
    src = ctypes.create_string_buffer(data, len(data))
    blob_in, blob_out = _Blob(len(data), src), _Blob()
    fn = crypt32.CryptProtectData if protect else crypt32.CryptUnprotectData
    if not fn(ctypes.byref(blob_in), None, None, None, None, 0x1, ctypes.byref(blob_out)):  # UI_FORBIDDEN
        raise OSError("DPAPI failed")
    try:
        return ctypes.string_at(blob_out.pbData, blob_out.cbData)
    finally:
        kernel32.LocalFree(blob_out.pbData)


def cached_key(cache_file):
    try:
        return _first_key(_dpapi(Path(cache_file).read_bytes(), protect=False).decode("utf-8"))
    except Exception:
        return ""


def save_cached_key(cache_file, key):
    try:
        Path(cache_file).write_bytes(_dpapi(key.encode("utf-8"), protect=True))
    except Exception:
        pass


def forget_cached_key(cache_file):
    try:
        Path(cache_file).unlink()
    except OSError:
        pass


# --- download from the team SharePoint folder with the browser's Windows / Orange sign-in

FETCH_KEY_JS = """
const [folder, name, done] = arguments;
const path = folder + '/' + name;
const site = location.origin + folder.split('/').slice(0, 3).join('/');
const urls = [
  site + "/_api/web/GetFileByServerRelativePath(decodedurl=@a)/$value?@a=" +
      encodeURIComponent("'" + path.replace(/'/g, "''") + "'"),
  site + "/_layouts/15/download.aspx?SourceUrl=" + encodeURIComponent(path),
  location.origin + encodeURI(path),
];
(async () => {
  const tried = [];
  for (const u of urls) {
    try {
      const r = await fetch(u, {credentials: 'include'});
      const t = r.ok ? (await r.text()).trim() : '';
      if (t.startsWith('sk-ant-')) { done({key: t}); return; }
      tried.push(r.status);
    } catch (e) { tried.push('error'); }
  }
  done({tried: tried});
})();
"""


def fetch_key_from_sharepoint(driver, timeout=45):
    """Open the team folder in a new tab of the app's (hidden) Firefox - it signs in to Microsoft 365
    with the Windows account - read the key file, close the tab. Returns the key or raises."""
    from open_gold import page_text
    home = driver.current_window_handle
    driver.switch_to.new_window("tab")
    try:
        driver.get(SHARE_URL)
        folder, deadline = "", time.time() + timeout
        while time.time() < deadline:
            url = driver.current_url
            folder = parse_qs(urlparse(url).query).get("id", [""])[0]
            if folder and KEY_FILE_NAME in page_text(driver):
                break
            time.sleep(0.5)
        host = urlparse(driver.current_url).netloc
        if not folder:
            if "login" in host or "microsoftonline" in host:
                raise RuntimeError("could not sign in to SharePoint automatically")
            raise RuntimeError("the team folder did not open (no access?)")
        driver.set_script_timeout(30)
        result = driver.execute_async_script(FETCH_KEY_JS, folder, KEY_FILE_NAME) or {}
        key = _first_key(result.get("key", ""))
        if not key:
            raise RuntimeError(f"the key file could not be read (HTTP {result.get('tried')})")
        return key
    finally:
        try:
            driver.close()
        finally:
            driver.switch_to.window(home)


def get_key(chosen_file, cache_file, driver_fn, log=print):
    """The API key, from (1) the file chosen in Settings, (2) this PC's encrypted copy,
    (3) the synced team folder, (4) the team SharePoint folder (downloaded automatically)."""
    if chosen_file and Path(chosen_file).is_file():
        return load_key(chosen_file)
    key = cached_key(cache_file)
    if key:
        return key
    local = find_key_file()
    if local:
        try:
            key = load_key(local)
        except RuntimeError:
            key = ""
    if not key:
        log("Ask GOLD: getting the AI key from the team SharePoint folder...")
        try:
            key = fetch_key_from_sharepoint(driver_fn())
        except Exception as e:
            reason = str(e).splitlines()[0] if str(e) else type(e).__name__
            raise RuntimeError(
                f"Ask GOLD could not get the team's AI key from SharePoint ({reason}).\n\nCheck that "
                f"you can open the team 'SALTO Buddy' folder in your browser, then ask again.") from None
    save_cached_key(cache_file, key)
    return key


# ---------------------------------------------------------------- tools

TAB_HINT = ("Usual GOLD tabs: Information, Pricing, Milestones, Notes, Teams, Billing, Documents, "
            "Contacts, Service build, Site, Companion services, Order history.")

TOOLS = [
    {
        "name": "my_orders",
        "description": (
            "INSTANT. The orders GOLD lists for the user (Orders > 'My orders only'), as already read by GOLD "
            "Express: order number, customer, customer site ref, order status, service, target delivery date "
            "(iTTD), order type, Orange site ref, site ID, BAN, sales country. Optional filter: an order number "
            "or any text (customer, site ref, status). Use it first for questions about the user's own orders - "
            "their status, customers, sites, target dates, which are late or due soon."),
        "input_schema": {
            "type": "object",
            "properties": {"filter": {"type": "string",
                                      "description": "Order number or text to filter on; empty for all"}},
            "required": ["filter"],
            "additionalProperties": False,
        },
    },
    {
        "name": "get_order_overview",
        "description": (
            "Key facts of one GOLD order in a single call: customer, project, scope, status, order type, "
            "product, initial / revised target delivery dates and delivery status (RAG), customer "
            "requested date, contract signature date and the 120-day lead-time deadline, next open "
            "milestone, revised-date history, order value (currency, new / existing / change in monthly "
            "charge, one-off charge, term, total value), site (country, city, address, site ID, Orange "
            "site ref, BAN), people (STM, delivery order owner, technical support, order entry, account "
            "manager), external reference, previous order and the latest note. SLOW (it reads six GOLD tabs, "
            "about 20-30 seconds): use it only for a summary of an order or when the question needs facts from "
            "several tabs at once; for one kind of fact, read_order_tab with the right tab is much faster."),
        "input_schema": {
            "type": "object",
            "properties": {"order": {"type": "string", "description": "GOLD order number, e.g. 10-1771012"}},
            "required": ["order"],
            "additionalProperties": False,
        },
    },
    {
        "name": "read_order_tab",
        "description": (
            "Everything shown on one tab of a GOLD order: all fields and tables (e.g. every Pricing line "
            "with its charges, every milestone with target / completed dates and owner, all notes with "
            "their full text, billing and site address details, team members, documents). "
            f"{TAB_HINT} The result also lists the tabs this order has; if the tab asked for does not "
            "exist, pick the closest from that list."),
        "input_schema": {
            "type": "object",
            "properties": {
                "order": {"type": "string", "description": "GOLD order number, e.g. 10-1771012"},
                "tab": {"type": "string", "description": "Tab name as shown in GOLD's left menu, e.g. Pricing"},
            },
            "required": ["order", "tab"],
            "additionalProperties": False,
        },
    },
    {
        "name": "find_person",
        "description": (
            "Look a person up in the Orange Business Org Chart: email, job title, department, country, "
            "phone / mobile, CUID and their manager chain (manager first, then the manager's manager...). "
            "Use it for people named in GOLD (STM, order owner, account manager, milestone owners) when the "
            "user wants their email, phone, job or manager, or asks about someone by name. Accepts a full "
            "name as written in GOLD, a last name, an email or a CUID."),
        "input_schema": {
            "type": "object",
            "properties": {"person": {"type": "string",
                                      "description": "Name (e.g. Nourhane Haidar), last name, email or CUID"}},
            "required": ["person"],
            "additionalProperties": False,
        },
    },
]


def _plain(v):
    if isinstance(v, (date, datetime)):
        return v.strftime("%d-%b-%Y")
    return str(v)


def tab_text(name, payload):
    """A compact text form of one tab for Claude."""
    if name == "Documents" or isinstance(payload, list):
        return json.dumps(payload, default=_plain, ensure_ascii=False)
    if name == "Teams" or "fields" not in payload:
        return json.dumps(payload, default=_plain, ensure_ascii=False)
    out = []
    section = None
    for sec, label, value in payload.get("fields", []):
        if sec != section:
            section = sec
            out.append(f"\n## {sec}" if sec else "")
        out.append(f"{label}: {value}" if label else value)
    for g in payload.get("grids", []):
        out.append(f"\n## Table: {g.get('title') or ''}".rstrip())
        out.append(" | ".join(g["columns"]))
        out += [" | ".join(str(c) for c in r) for r in g["rows"]]
    if payload.get("text"):
        out.append(payload["text"])
    text = "\n".join(out).strip()
    return text[:MAX_TOOL_TEXT] + ("\n[... cut: tab is longer]" if len(text) > MAX_TOOL_TEXT else "")


class GoldReader:
    """Runs the tools on the app's GOLD session. Called on the worker thread."""

    def __init__(self, app):
        self.app = app
        self.cache = {}  # (order, what) -> (time, text)

    def _cached(self, key, read):
        hit = self.cache.get(key)
        if hit and time.time() - hit[0] < CACHE_MIN * 60:
            return hit[1]
        text = read()
        self.cache[key] = (time.time(), text)
        return text

    def run(self, name, args):
        if name == "my_orders":
            return self._my_orders(str(args.get("filter", "")).strip().lower())
        if name == "find_person":
            who = " ".join(str(args.get("person", "")).split())
            if not who:
                raise ValueError("No person given.")
            return self._cached(("person", who.lower()), lambda: self._person(who))
        order = str(args.get("order", "")).strip()
        if not re.fullmatch(r"\d{2}-\d{5,8}", order):
            raise ValueError(f"'{order}' is not a GOLD order number (like 10-1771012).")
        if name == "get_order_overview":
            return self._cached((order, "overview"), lambda: self._overview(order))
        if name == "read_order_tab":
            tab = str(args.get("tab", "")).strip() or "Information"
            return self._cached((order, tab.lower()), lambda: self._tab(order, tab))
        raise ValueError(f"Unknown tool {name}")

    def _my_orders(self, q):
        orders = getattr(self.app, "my_orders", None) or []
        if not getattr(self.app, "my_time", None):  # not read yet (My Orders loads on request): read it now
            import gold_myorders as gmo
            w = self.app.worker
            w.ensure_browser()
            self.app.log("Ask GOLD: reading your orders...")
            orders = gmo.read_my_orders(w.driver, w.wait, self.app.log)
            self.app.ui(lambda o=orders: self.app._my_loaded(o))
        if not orders:
            return "There are no orders in My orders."
        keep = ("order", "customer", "cust_site_ref", "status", "service", "ittd_date", "type", "orange_site_ref",
                "site_id", "ban", "sales_country")
        rows = [{k: o.get(k, "") for k in keep} for o in orders
                if not q or q in " ".join(str(v) for v in o.values()).lower()]
        when = getattr(self.app, "my_time", None)
        head = (f"{len(rows)} of {len(orders)} orders in My orders"
                + (f" (read {int((time.time() - when) // 60)} min ago)" if when else ""))
        return head + "\n" + json.dumps(rows, default=_plain, ensure_ascii=False)

    def _person(self, who):
        self.app.log(f"Ask GOLD: looking up {who} in the Org Chart...")
        people = self.app._org(lambda oc: oc.query(who, levels=4, limit=5))
        if not people:
            return f"Nobody found in the Org Chart for '{who}'."
        keep = ("display_name", "busi_title", "email", "phone", "mobile", "dept_desc", "city", "country_descr",
                "vendor_name", "cuid")
        out = [{**{k: p.get(k, "") for k in keep},
                "managers": [{k: m.get(k, "") for k in ("display_name", "busi_title", "email")}
                             for m in p.get("chain", [])]} for p in people]
        return json.dumps(out, ensure_ascii=False)

    def _overview(self, order):
        import gold_overview as go
        from open_gold import Wait
        cached = getattr(self.app, "ov_cache", {}).get(order)
        if cached and time.time() - cached[0] < CACHE_MIN * 60:
            ov = cached[1]
        else:
            w = self.app.worker
            w.ensure_browser()
            self.app.log(f"Ask GOLD: reading {order}...")
            ov = go.collect(w.driver, Wait(w.driver, 60), order)
            self.app.ov_cache[order] = (time.time(), ov)
        ov = {k: v for k, v in ov.items() if k != "collected"}
        return json.dumps(ov, default=_plain, ensure_ascii=False)

    def _tab(self, order, tab):
        import gold_extract as gx
        import open_order as oo
        w = self.app.worker
        w.ensure_browser()
        if not oo._on_order_page(w.driver, order):
            self.app.log(f"Ask GOLD: opening {order}...")
            for attempt in range(2):
                try:
                    oo.open_orders_tab(w.driver, w.wait, discard_changes=True)
                    oo.untick_my_orders(w.driver)
                    oo.open_result(w.driver, w.wait, oo.search_order(w.driver, w.wait, order), order)
                    break
                except RuntimeError as e:
                    if attempt or "not found" in str(e):
                        raise
                    # The search page left by the My Orders read sometimes ignores clicks: start afresh
                    import open_gold as og
                    w.driver.get(og.GOLD_URL)
                    og.wait_for_gold(w.driver, 60)
        titles = [t for t, _ in oo.list_tabs(w.driver)]
        match = (next((t for t in titles if t.lower() == tab.lower()), None)
                 or next((t for t in titles if t.lower().startswith(tab.lower())), None)
                 or next((t for t in titles if tab.lower() in t.lower()), None))
        if not match:
            return f"Order {order} has no '{tab}' tab. Its tabs are: {', '.join(titles)}"
        self.app.log(f"Ask GOLD: reading {order} > {match}...")
        name = oo.open_tab(w.driver, w.wait, match)
        if name == "Documents":
            payload = oo.read_documents(w.driver)
        elif name == "Teams":
            payload = oo.read_teams(w.driver)
        else:
            payload = gx.extract_tab(w.driver)
            if not payload["fields"] and not payload["grids"]:
                payload["text"] = oo.content_text(w.driver)
        return (f"Order {order} - tab '{name}' (this order's tabs: {', '.join(titles)})\n\n"
                + tab_text(name, payload))


# ---------------------------------------------------------------- conversation

def system_prompt():
    today = date.today().strftime("%A %d %B %Y")
    return f"""You are the Friendly GOLD bot, the assistant inside GOLD Express, a desktop app used by Orange Business \
delivery teams (STMs, DPMs, project managers) to work with GOLD (Global Order Lifecycle Delivery), Orange \
Business's order management system. Today is {today}.

You help the user find information about GOLD orders: deadlines and milestones, delivery status, pricing \
and charges, site addresses, contacts and team members, notes, documents, billing details.

How to work:
- Answer from GOLD data only, read with your tools. Never guess or invent values: if something is not in \
GOLD, say so plainly. Your tools are read-only; you cannot change anything in GOLD - if asked to, explain \
that and point to the right GOLD Express tab (Revised Target Date, Bulk Order Assignment) or GOLD itself.
- Answer quickly: read as little as the question needs.
  - The user's own orders (status, customer, customer site ref, service, target date, type): my_orders is \
instant - use it first for those.
  - One kind of fact: read_order_tab with the one tab that holds it - deadlines / milestones / dates: \
Milestones; STM and other people: Teams; prices and charges: Pricing; site address: Billing; status, \
customer, project and key dates: Information; notes: Notes; documents: Documents.
  - get_order_overview (slow) only for a summary of an order or questions that need several tabs at once.
  - When you need several things, ask for all of them in one step (several tool calls at once).
- When the user does not repeat the order number, use the order(s) from earlier in the conversation. If \
no order number is known, ask for it.
- The order open in GOLD Express's Order explorer is given with each question: questions that name no \
order ("what are the deadlines?", "who is the STM?") are about that order.
- For a person's email, phone, job or manager, use find_person (Orange Business Org Chart) with the name \
as GOLD shows it.
- Several orders: read each one, then compare.
- Dates as dd-Mon-yyyy (e.g. 06-Dec-2026). Amounts with their currency. Say how many days are left \
(or how late) for deadlines when useful.
- Answer in the user's language.

How to lay out the answer (shown as a small Markdown subset; people paste these answers into emails and \
reports, so they must be clean and easy to scan):
- First line: the direct answer in one sentence, with the key value(s) in **bold**. No preamble ("Sure", \
"Let me check", "Based on the data"), no closing offers or questions unless something is truly ambiguous.
- Then only the details that help. Use "### " headings only when the answer has two or more distinct \
groups; keep headings to 1-3 words.
- A few facts about one thing: one bullet each, written "- **Label:** value".
- Several items that share 3 or more fields (milestones, price lines, team members, documents, orders side \
by side): a Markdown table with a header row and one row per item, ordered sensibly. List every item, never \
"...". At most 7 columns.
- Missing values: write "not found" in the cell, never leave it blank or guess. If something needs the \
user's attention (a passed deadline, a missing owner), say so in one bullet after the table.
- Last line, on its own: "Source: GOLD order <number>, <tab(s) read>".
- Use nothing else: no italics, links, code blocks, emojis, nested lists or horizontal rules. Be concise."""


class Chat:
    """One conversation with Claude. ask() runs on the worker thread."""

    def __init__(self, key, reader, model=MODEL, effort="medium", fast=False):
        import anthropic
        self.anthropic = anthropic
        self.client = anthropic.Anthropic(api_key=key, max_retries=3, timeout=180)
        self.reader = reader
        self.messages = []
        self.model, self.effort, self.fast = model, effort, fast

    def _request(self):
        betas = ["server-side-fallback-2026-07-01"]  # if a safety check declines, another model answers
        extra = {}
        if self.fast:  # Opus fast mode (research preview): faster output, higher price
            betas.append("fast-mode-2026-02-01")
            extra["extra_body"] = {"speed": "fast"}
        return dict(model=self.model, max_tokens=16000, system=system_prompt(),
                    # strict: Claude's arguments always match the schemas exactly
                    tools=[{**t, "strict": True} for t in TOOLS], messages=self.messages,
                    output_config={"effort": self.effort}, cache_control={"type": "ephemeral"},
                    betas=betas, fallbacks="default", **extra)

    def _call(self, on_text=None):
        """One request, streamed. If fast mode is not available for this key, it carries on without it."""
        try:
            with self.client.beta.messages.stream(**self._request()) as stream:
                if on_text:
                    for event in stream:
                        if event.type == "content_block_delta" and getattr(event.delta, "type", "") == "text_delta":
                            on_text(event.delta.text)
                return stream.get_final_message()
        except (self.anthropic.BadRequestError, self.anthropic.PermissionDeniedError) as e:
            if not self.fast or not any(w in str(e).lower() for w in ("speed", "fast")):
                raise
            self.fast = False
            return self._call(on_text)

    def ask(self, question, progress=lambda text: None, context="", on_text=None):
        """Send the user's question; run the tools Claude asks for; return the answer (markdown).
        context is added to this question only, e.g. which order is open in the Order explorer.
        on_text(piece) receives the answer's text as it is written (to show it straight away)."""
        self.messages.append({"role": "user",
                              "content": f"[{context}]\n\n{question}" if context else question})
        try:
            for _ in range(MAX_STEPS):
                response = self._call(on_text)
                self.messages.append({"role": "assistant", "content": response.content})
                if response.stop_reason == "refusal":
                    return "I can't help with that request."
                calls = [b for b in response.content if b.type == "tool_use"]
                if response.stop_reason != "tool_use" or not calls:
                    text = "\n".join(b.text for b in response.content if b.type == "text").strip()
                    if response.stop_reason == "max_tokens":
                        text += "\n\n(The answer was cut short - ask for a shorter or narrower answer.)"
                    return text or "(no answer)"
                results = []
                for call in calls:
                    if call.name == "find_person":
                        progress(f"Looking up {call.input.get('person', '')} in the Org Chart...")
                    elif call.name == "my_orders":
                        progress("Checking your orders...")
                    else:
                        what = call.input.get("tab") or "overview"
                        progress(f"Reading {call.input.get('order', '')} - {what}...")
                    try:
                        content, err = self.reader.run(call.name, call.input), False
                    except Exception as e:
                        content, err = f"Error: {str(e).splitlines()[0] if str(e) else type(e).__name__}", True
                    results.append({"type": "tool_result", "tool_use_id": call.id, "content": content,
                                    "is_error": err})
                self.messages.append({"role": "user", "content": results})
                progress("Thinking...")
            return "I needed too many steps for this question - please ask something narrower."
        except Exception:
            self._drop_unanswered()
            raise

    def _drop_unanswered(self):
        """After a failed request, remove the question so the conversation stays valid."""
        while self.messages and not (self.messages[-1]["role"] == "user"
                                     and isinstance(self.messages[-1]["content"], str)):
            self.messages.pop()
        if self.messages:
            self.messages.pop()


def friendly_error(err):
    """A short message for the chat window for API / network errors."""
    try:
        import anthropic
    except ImportError:
        return str(err)
    if isinstance(err, anthropic.AuthenticationError):
        return "The API key in the AI key file was refused (invalid or revoked). Ask the key owner for a new one."
    if isinstance(err, anthropic.PermissionDeniedError):
        return "The API key is not allowed to use this model."
    if isinstance(err, anthropic.RateLimitError):
        return "The AI service is busy (rate limit). Wait a minute and ask again."
    if isinstance(err, anthropic.APIConnectionError):
        return ("Could not reach the AI service (api.anthropic.com). Check the network / VPN / proxy.")
    if isinstance(err, anthropic.APIStatusError):
        return f"The AI service returned an error ({err.status_code}): {getattr(err, 'message', err)}"
    return str(err).splitlines()[0] if str(err) else type(err).__name__
