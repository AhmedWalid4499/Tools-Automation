"""Ask GOLD: a chat assistant (Claude) that answers questions about GOLD orders.

Claude reads orders through two tools that run on the app's GOLD session (read-only):
  get_order_overview(order)    key facts: dates, status, value, site, people, latest note
  read_order_tab(order, tab)   everything on one tab (Pricing, Milestones, Notes, Billing...)

The API key is never part of the app: it is read at run time from the team's key file
(salto-buddy-team.key, synced from the team's SharePoint/OneDrive folder).
"""
import json
import re
import time
from datetime import date, datetime
from pathlib import Path

MODEL = "claude-opus-5-5"
KEY_FILE_NAME = "salto-buddy-team.key"
CACHE_MIN = 5          # re-use what was read from GOLD for this many minutes
MAX_TOOL_TEXT = 60000  # characters of one tab sent to Claude
MAX_STEPS = 12         # tool rounds per question


# ---------------------------------------------------------------- key file

def find_key_file(saved=""):
    """The key file: the one chosen in Settings, else the synced team folder under OneDrive."""
    if saved and Path(saved).is_file():
        return Path(saved)
    home = Path.home()
    roots = [p for p in home.glob("OneDrive*") if p.is_dir()]
    for root in roots:
        for pattern in (f"SALTO Buddy/{KEY_FILE_NAME}", KEY_FILE_NAME, f"*/{KEY_FILE_NAME}",
                        f"*/*/{KEY_FILE_NAME}"):
            for p in root.glob(pattern):
                if p.is_file():
                    return p
    return None


def load_key(path):
    """The API key from the key file (first non-empty line), or a clear error."""
    if not path:
        raise RuntimeError(
            f"The AI key file ({KEY_FILE_NAME}) was not found.\n\nSync the team's 'SALTO Buddy' "
            "SharePoint folder to OneDrive (open it in the browser > 'Add shortcut to My files' or "
            "'Sync'), or choose the file in Settings > AI assistant.")
    try:
        text = Path(path).read_text(encoding="utf-8-sig")
    except OSError as e:
        raise RuntimeError(f"Could not read the AI key file {path}:\n{e}\n\nIf it is a OneDrive "
                           "file, right-click it > 'Always keep on this device'.") from None
    key = next((line.strip() for line in text.splitlines() if line.strip()), "")
    if not key.startswith("sk-ant-"):
        raise RuntimeError(f"{path} does not contain an Anthropic API key.")
    return key


# ---------------------------------------------------------------- tools

TAB_HINT = ("Usual GOLD tabs: Information, Pricing, Milestones, Notes, Teams, Billing, Documents, "
            "Contacts, Service build, Site, Companion services, Order history.")

TOOLS = [
    {
        "name": "get_order_overview",
        "description": (
            "Key facts of one GOLD order in a single call: customer, project, scope, status, order type, "
            "product, initial / revised target delivery dates and delivery status (RAG), customer "
            "requested date, contract signature date and the 120-day lead-time deadline, next open "
            "milestone, revised-date history, order value (currency, new / existing / change in monthly "
            "charge, one-off charge, term, total value), site (country, city, address, site ID, Orange "
            "site ref, BAN), people (STM, delivery order owner, technical support, order entry, account "
            "manager), external reference, previous order and the latest note. Start with this tool; use "
            "read_order_tab when the question needs detail it does not have."),
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
        order = str(args.get("order", "")).strip()
        if not re.fullmatch(r"\d{2}-\d{5,8}", order):
            raise ValueError(f"'{order}' is not a GOLD order number (like 10-1771012).")
        if name == "get_order_overview":
            return self._cached((order, "overview"), lambda: self._overview(order))
        if name == "read_order_tab":
            tab = str(args.get("tab", "")).strip() or "Information"
            return self._cached((order, tab.lower()), lambda: self._tab(order, tab))
        raise ValueError(f"Unknown tool {name}")

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
            oo.open_orders_tab(w.driver, w.wait, discard_changes=True)
            oo.untick_my_orders(w.driver)
            oo.open_result(w.driver, w.wait, oo.search_order(w.driver, w.wait, order), order)
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
    return f"""You are "Ask GOLD", the assistant inside GOLD Express, a desktop app used by Orange Business \
delivery teams (STMs, DPMs, project managers) to work with GOLD (Global Order Lifecycle Delivery), Orange \
Business's order management system. Today is {today}.

You help the user find information about GOLD orders: deadlines and milestones, delivery status, pricing \
and charges, site addresses, contacts and team members, notes, documents, billing details.

How to work:
- Answer from GOLD data only, read with your tools. Never guess or invent values: if something is not in \
GOLD, say so plainly. Your tools are read-only; you cannot change anything in GOLD - if asked to, explain \
that and point to the right GOLD Express tab (Revised Target Date, Bulk Order Assignment) or GOLD itself.
- Start with get_order_overview; use read_order_tab for details (e.g. Pricing lines, every milestone, full \
notes, site address). When the user does not repeat the order number, use the order(s) from earlier in \
the conversation. If no order number is known, ask for it.
- Several orders: read each one, then compare.
- Dates as dd-Mon-yyyy (e.g. 06-Dec-2026). Amounts with their currency. Say how many days are left \
(or how late) for deadlines when useful.

How to format answers (they are shown in a chat window that renders markdown):
- Lead with the direct answer in one short sentence.
- Use a markdown table (| a | b | with a header separator row) for anything with several items or \
columns: milestones, price lines, team members, documents, several orders side by side.
- Use bullet lists for short sets of facts, ## headings only when the answer has several parts, \
**bold** for the key value. No emoji. Keep it concise: no preamble, no closing offers."""


class Chat:
    """One conversation with Claude. ask() runs on the worker thread."""

    def __init__(self, key, reader):
        import anthropic
        self.anthropic = anthropic
        self.client = anthropic.Anthropic(api_key=key, max_retries=3)
        self.reader = reader
        self.messages = []

    def ask(self, question, progress=lambda text: None):
        """Send the user's question; run the tools Claude asks for; return the answer (markdown)."""
        self.messages.append({"role": "user", "content": question})
        try:
            for _ in range(MAX_STEPS):
                with self.client.messages.stream(
                        model=MODEL,
                        max_tokens=16000,
                        system=system_prompt(),
                        tools=TOOLS,
                        messages=self.messages,
                        output_config={"effort": "medium"},
                        cache_control={"type": "ephemeral"},
                ) as stream:
                    response = stream.get_final_message()
                self.messages.append({"role": "assistant", "content": response.content})
                if response.stop_reason == "refusal":
                    return "I can't help with that request."
                calls = [b for b in response.content if b.type == "tool_use"]
                if response.stop_reason != "tool_use" or not calls:
                    text = "\n".join(b.text for b in response.content if b.type == "text").strip()
                    if response.stop_reason == "max_tokens":
                        text += "\n\n*(The answer was cut short - ask for a shorter or narrower answer.)*"
                    return text or "(no answer)"
                results = []
                for call in calls:
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
