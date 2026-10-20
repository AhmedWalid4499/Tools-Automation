"""GOLD Express: a small desktop app for GOLD orders.

Run:  pythonw gold_app.py   (or double-click "GOLD Express.bat"; packaged as GOLD Express.exe)

- Order explorer: type an order number -> Open; click a tab on the left to see it.
  Screenshot -> <Tab>_<n>.png; Excel -> <Order>.xlsx (one sheet per tab);
  Documents: download; Teams: browse / find a person.
- Revised Target Date: add the RTDD milestone to many orders (Gold order | Date | Reason).
GOLD runs in Firefox in the background (Settings > Show the Firefox window to see it).
"""
import json
import os
import queue
import re
import threading
import time
import traceback
from datetime import datetime
from pathlib import Path

import tkinter as tk
from tkinter import filedialog, messagebox, ttk

from selenium.webdriver.support.ui import WebDriverWait

import gold_extract as gx
import gold_milestones as gm
import gold_names as gn
import gold_overview as go
import gold_teams as gt
import gold_update as gu
from gold_grid import EditGrid
import open_order as oo
from open_gold import APP_NAME, BUNDLE_DIR, GOLD_URL, HERE, start_firefox, wait_for_gold
from version import AUTHOR, __version__

SETTINGS_FILE = HERE / "gold_app_settings.json"

# Palette (Orange-style: black header, orange accent, light grey canvas)
ORANGE = "#FF7900"
ORANGE_DARK = "#E06A00"
ORANGE_SOFT = "#FFE8D6"
INK = "#1F2328"
MUTED = "#6B7280"
CANVAS = "#F3F4F6"
CARD = "#FFFFFF"
LINE = "#E2E4E8"
HEADER = "#111111"
GREEN = "#1E7B34"
RED = "#C62828"
FONT = "Segoe UI"


def safe_name(s):
    return re.sub(r"[^\w\-]+", "_", s).strip("_") or "tab"


# ---------------------------------------------------------------- settings

def load_settings():
    s = {"screenshots": str(HERE / "output" / "screenshots"), "exports": str(HERE / "output"),
         "full_page": True, "auto_shot": False, "per_order_folder": True, "show_browser": False}
    try:
        saved = json.loads(SETTINGS_FILE.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        saved = {}
    # Older versions kept folders per project: reuse the last project's folders.
    old = saved.pop("projects", {}).get(saved.pop("project", ""), {})
    s.update({k: v for k, v in old.items() if v})
    s.update(saved)
    return s


def save_settings(s):
    try:
        SETTINGS_FILE.write_text(json.dumps(s, indent=2), encoding="utf-8")
    except OSError:
        pass


# ---------------------------------------------------------------- connection

GOLD_HOST = "gold.sso.infra.ftgroup"
NET_ERROR_TEXT = ("unable to connect", "having trouble finding that site", "secure connection failed",
                  "the connection was reset", "the connection has timed out", "server not found",
                  "problem loading page", "network protocol error", "proxy server is refusing")


def network_ok(timeout=3):
    """Can we reach GOLD's server right now? (plain TCP check, no browser)"""
    import socket
    try:
        socket.create_connection((GOLD_HOST, 443), timeout=timeout).close()
        return True
    except OSError:
        return False


def looks_like_connection_error(err):
    text = str(err).lower()
    return any(k in text for k in ("neterror", "connection", "timed out", "timeout", "reset", "dnsnotfound",
                                   "reached error page", "no connection", "session", "browsing context",
                                   "not reachable", "failed to decode response")) or not network_ok()


# ---------------------------------------------------------------- browser worker

class Worker:
    """Owns the Firefox driver; runs GOLD jobs one at a time on its own thread."""

    def __init__(self, app):
        self.app = app
        self.jobs = queue.Queue()
        self.driver = None
        self.wait = None
        self.restart = False  # set when the "show Firefox" setting changes
        threading.Thread(target=self._loop, daemon=True).start()

    def submit(self, label, fn, done=None, retry=False):
        """retry=True for read-only jobs: if they fail because of the connection, reconnect to
        GOLD (fresh session) and run them once more. Jobs that save in GOLD are never retried."""
        self.app.set_busy(label)
        self.jobs.put((label, fn, done, retry))

    def _loop(self):
        while True:
            label, fn, done, retry = self.jobs.get()
            if fn is None:
                break
            try:
                try:
                    result = fn()
                except Exception as first:
                    if not (retry and self.session_problem(first)):
                        raise
                    self.app.log(f"Connection problem ({str(first).splitlines()[0][:80]}) - reconnecting to GOLD...")
                    self.wait_for_network()
                    self.restart = True
                    result = fn()
                self.app.ui(lambda r=result: (self.app.set_idle(), done and done(r)))
            except Exception as e:
                tb = traceback.format_exc()
                self.app.ui(lambda e=e, tb=tb, label=label: self.app.job_failed(label, e, tb))

    def session_problem(self, err):
        """Did this failure come from a lost connection / expired GOLD session?"""
        return looks_like_connection_error(err) or (self.driver is not None and not self._healthy())

    def wait_for_network(self, timeout=120):
        """Wait (up to timeout seconds) for GOLD's server to be reachable again."""
        deadline = time.time() + timeout
        while not network_ok():
            if time.time() > deadline:
                raise RuntimeError("No connection to GOLD. Check your network / VPN - GOLD Express "
                                   "reconnects by itself when the connection is back.")
            time.sleep(5)

    def _healthy(self):
        """Is the open Firefox alive, on GOLD and not stuck on an error page?"""
        try:
            url = self.driver.current_url
            if url.startswith("about:") and "blank" not in url:
                return False  # about:neterror, about:certerror ...
            if GOLD_HOST not in url:
                return False  # e.g. sign-in page after the session expired
            body = self.driver.execute_script("return (document.body && document.body.innerText || '')"
                                              ".slice(0, 3000).toLowerCase()")
            return not any(k in body for k in NET_ERROR_TEXT)
        except Exception:
            return False

    def _quit_driver(self):
        if self.driver is not None:
            try:
                self.driver.quit()
            except Exception:
                pass
        self.driver = None

    def ensure_browser(self):
        """Make sure there is a working GOLD session: reuse it, repair it (reload GOLD), or start
        a new one. Called before every GOLD action, so a dropped connection heals by itself."""
        if self.restart:
            self.restart = False
            self._quit_driver()
        if self.driver is not None:
            if self._healthy():
                return
            self.app.log("GOLD session lost - reconnecting...")
            self.wait_for_network()
            try:  # first try to repair the session in place
                self.driver.get(GOLD_URL)
                if wait_for_gold(self.driver, timeout=60):
                    self.app.log("Reconnected to GOLD.")
                    return
            except Exception:
                pass
            self._quit_driver()  # then start a fresh one
        if not network_ok():
            self.wait_for_network(timeout=20)
        show = bool(self.app.settings.get("show_browser"))
        self.app.log("Signing in to GOLD" + ("..." if show else " in the background..."))
        self.driver = start_firefox(headless=not show)
        self.wait = WebDriverWait(self.driver, 60)
        self.driver.get(GOLD_URL)
        if wait_for_gold(self.driver, timeout=300 if show else 90):
            return
        if not show:
            # Background sign-in didn't finish: GOLD probably wants a manual login. Show it.
            self.app.log("GOLD needs you to sign in - opening the Firefox window...")
            self._quit_driver()
            self.driver = start_firefox(headless=False)
            self.wait = WebDriverWait(self.driver, 60)
            self.driver.get(GOLD_URL)
            if wait_for_gold(self.driver):
                return
        raise RuntimeError("GOLD did not load. Sign in in the Firefox window, then try again.")

    def close(self):
        self.jobs.put(("quit", None, None, False))
        self._quit_driver()


# ---------------------------------------------------------------- the window

class App(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title(APP_NAME)
        for icon in (BUNDLE_DIR / "gold_express.ico", Path(__file__).parent / "gold_express.ico"):
            if icon.exists():
                self.iconbitmap(default=str(icon))
                break
        self.geometry("1240x800")
        self.minsize(1040, 660)
        self.configure(background=CANVAS)
        self.settings = load_settings()
        self.dpm_names = gn.load()
        self.ui_queue = queue.Queue()
        self.worker = Worker(self)
        self.order = None          # currently open order number
        self.current_tab = None    # name of the GOLD tab shown
        self.tab_titles = []       # side-menu titles of the open order
        self.docs = []             # Documents tab rows
        self.teams = {}            # Teams tab data
        self.buttons = []          # disabled while a job runs
        self.busy = False
        # Settings shown in the Settings window
        self.shot_dir = tk.StringVar(value=self.settings["screenshots"])
        self.export_dir = tk.StringVar(value=self.settings["exports"])
        self.full_page = tk.BooleanVar(value=self.settings["full_page"])
        self.auto_shot = tk.BooleanVar(value=self.settings["auto_shot"])
        self.per_order = tk.BooleanVar(value=self.settings["per_order_folder"])
        self.show_browser = tk.BooleanVar(value=self.settings["show_browser"])

        self._style()
        self._build()
        self.protocol("WM_DELETE_WINDOW", self._on_close)
        self.after(100, self._pump)
        self.online = True
        threading.Thread(target=self._watch_connection, daemon=True).start()
        self.new_release = None
        self.after(4000, lambda: self._check_updates(quiet=True))  # quiet check at start-up

    # ----- thread-safe UI helpers
    def ui(self, fn):
        self.ui_queue.put(fn)

    def _pump(self):
        try:
            while True:
                self.ui_queue.get_nowait()()
        except queue.Empty:
            pass
        self.after(100, self._pump)

    def log(self, msg):
        def add():
            stamp = datetime.now().strftime("%H:%M")
            self.log_box.configure(state="normal")
            self.log_box.insert("end", f"{stamp}  {msg}\n")
            self.log_box.see("end")
            self.log_box.configure(state="disabled")
            self.last_msg.configure(text=msg if len(msg) < 140 else msg[:137] + "...")
        self.ui(add)

    def _set_pill(self, text, fg, bg):
        self.status.configure(text=f"  ●  {text}  ", fg=fg, bg=bg)

    def set_busy(self, label):
        self.busy = True
        self._set_pill(f"{label}...", ORANGE, "#2A2A2A")
        for b in self.buttons:
            b.state(["disabled"])
        self.configure(cursor="watch")

    # ----- updates (GitHub Releases)
    def _check_updates(self, quiet=True):
        """quiet: background check at start-up - only lights the button up when there is an update."""
        if self.new_release and not quiet:
            return self._offer_update(self.new_release)

        def work():
            try:
                rel, newer = gu.check()
            except Exception as e:
                if not quiet:
                    self.ui(lambda e=e: messagebox.showwarning(
                        APP_NAME, f"Could not check for updates:\n{e}\n\nYou can also download new "
                                  f"versions from\n{gu.RELEASES_PAGE}"))
                return
            if newer:
                self.new_release = rel
                self.ui(lambda: self.update_btn.configure(text=f"⬆  Update to {rel['version']}",
                                                          style="Accent.TButton"))
                self.log(f"A new version of {APP_NAME} is available: {rel['version']}")
                if not quiet:
                    self.ui(lambda: self._offer_update(rel))
            elif not quiet:
                self.ui(lambda: messagebox.showinfo(
                    APP_NAME, f"You have the latest version ({__version__})."))
        threading.Thread(target=work, daemon=True).start()

    def _offer_update(self, rel):
        notes = rel["notes"][:900] + ("..." if len(rel["notes"]) > 900 else "")
        if not gu.can_self_update():
            messagebox.showinfo(APP_NAME, f"Version {rel['version']} is available.\n\nThis copy runs from the "
                                          f"source code - update it with 'git pull'.\n\n{gu.RELEASES_PAGE}")
            return
        if self.busy:
            messagebox.showinfo(APP_NAME, "Please wait until the current action has finished, then update.")
            return
        if not messagebox.askyesno(
                f"{APP_NAME} update",
                f"Version {rel['version']} is available (you have {__version__}).\n\n"
                + (f"What's new:\n{notes}\n\n" if notes else "")
                + f"Update now? {APP_NAME} will close, update itself and open again "
                  "(about a minute). Your settings and files are kept."):
            return

        def progress(done, total):
            pct = f"{done * 100 // total}%" if total else f"{done // 1_000_000} MB"
            self.ui(lambda: self._set_pill(f"Downloading update... {pct}", ORANGE, "#2A2A2A"))

        def work():
            try:
                setup = gu.download(rel, progress)
            except Exception as e:
                self.ui(lambda e=e: (self.set_idle(), messagebox.showerror(
                    APP_NAME, f"The update could not be downloaded:\n{e}\n\nTry again later or download it "
                              f"from\n{rel['page']}")))
                return
            self.log(f"Installing {rel['name']}...")
            self.ui(lambda: self._install_update(setup))
        self.set_busy("Downloading update")
        threading.Thread(target=work, daemon=True).start()

    def _install_update(self, setup):
        try:
            gu.run_installer(setup)
        except Exception as e:
            self.set_idle()
            messagebox.showerror(APP_NAME, f"The update could not start:\n{e}")
            return
        self._on_close()  # the setup replaces the app's files and starts it again

    def _watch_connection(self, every=20):
        """Background thread: notice when the network drops and comes back. When it is back,
        replace the (now dead) GOLD session with a fresh one so the app just keeps working."""
        while True:
            time.sleep(every)
            ok = network_ok()
            if ok == self.online:
                continue
            self.online = ok
            if not ok:
                self.log("Connection to GOLD lost - waiting for the network to come back...")
                self.ui(lambda: None if self.busy else self._set_pill("Offline - waiting for network", "#FF8A80",
                                                                      "#2A2A2A"))
                continue
            self.log("Connection is back.")
            if self.worker.driver is None:
                self.ui(lambda: None if self.busy else self.set_idle())
                continue
            self.worker.restart = True  # the old session is gone: start a fresh one

            def reconnect():
                if self.busy:
                    return  # the running job reconnects by itself (ensure_browser)
                self.worker.submit("Reconnecting to GOLD", lambda: (self.worker.ensure_browser(), "ok")[1],
                                   lambda _: self.log("New GOLD session ready."))
            self.ui(reconnect)

    def set_idle(self):
        self.busy = False
        for b in ("rtdd_stop_btn", "assign_stop_btn"):
            if hasattr(self, b):
                getattr(self, b).state(["disabled"])
        if getattr(self, "online", True):
            self._set_pill("Ready", "#7BD88F", "#2A2A2A")
        else:
            self._set_pill("Offline - waiting for network", "#FF8A80", "#2A2A2A")
        for b in self.buttons:
            b.state(["!disabled"])
        self.configure(cursor="")
        self._refresh_action_state()

    def job_failed(self, label, err, tb):
        self.set_idle()
        self.log(f"ERROR while {label.lower()}: {err}")
        (HERE / "gold_app_error.log").write_text(tb, encoding="utf-8")
        messagebox.showerror(APP_NAME, f"{label} failed:\n\n{err}")

    # ----- look
    def _style(self):
        st = ttk.Style(self)
        st.theme_use("clam")
        self.option_add("*Font", (FONT, 10))
        self.option_add("*TCombobox*Listbox.font", (FONT, 10))
        self.option_add("*TCombobox*Listbox.selectBackground", ORANGE)
        st.configure(".", background=CARD, foreground=INK, font=(FONT, 10), bordercolor=LINE,
                     lightcolor=LINE, darkcolor=LINE, focuscolor=ORANGE)
        st.configure("TFrame", background=CARD)
        st.configure("Canvas.TFrame", background=CANVAS)
        st.configure("Card.TFrame", background=CARD, relief="solid", borderwidth=1)
        st.configure("TLabel", background=CARD, foreground=INK)
        st.configure("Card.TLabel", background=CARD)
        st.configure("Muted.TLabel", background=CARD, foreground=MUTED)
        st.configure("CardMuted.TLabel", background=CARD, foreground=MUTED)
        st.configure("Head.TLabel", background=CARD, font=(FONT, 11, "bold"))
        st.configure("CardHead.TLabel", background=CARD, font=(FONT, 11, "bold"))
        st.configure("Big.TLabel", background=CARD, font=(FONT, 13, "bold"))
        # Buttons
        st.configure("TButton", background="#F6F7F9", foreground=INK, borderwidth=1, relief="solid",
                     padding=(12, 6), bordercolor="#CFD3D9", lightcolor="#F6F7F9", darkcolor="#F6F7F9")
        st.map("TButton", background=[("disabled", "#F6F7F9"), ("pressed", "#E4E6EA"), ("active", "#ECEEF1")],
               bordercolor=[("active", ORANGE), ("focus", "#CFD3D9")],
               lightcolor=[("active", "#ECEEF1")], darkcolor=[("active", "#ECEEF1")],
               foreground=[("disabled", "#A0A4AB")])
        st.configure("Accent.TButton", background=ORANGE, foreground="white", bordercolor=ORANGE,
                     lightcolor=ORANGE, darkcolor=ORANGE, font=(FONT, 10, "bold"), padding=(16, 6))
        st.map("Accent.TButton", background=[("disabled", "#F7C49A"), ("pressed", ORANGE_DARK),
                                             ("active", ORANGE_DARK)],
               bordercolor=[("disabled", "#F7C49A"), ("active", ORANGE_DARK)],
               lightcolor=[("disabled", "#F7C49A"), ("active", ORANGE_DARK)],
               darkcolor=[("disabled", "#F7C49A"), ("active", ORANGE_DARK)],
               foreground=[("disabled", "white")])
        st.configure("Header.TButton", background=HEADER, foreground="white", bordercolor="#3A3A3A",
                     lightcolor=HEADER, darkcolor=HEADER, padding=(12, 5))
        st.map("Header.TButton", background=[("active", "#2A2A2A"), ("pressed", "#000000")],
               lightcolor=[("active", "#2A2A2A")], darkcolor=[("active", "#2A2A2A")],
               bordercolor=[("active", ORANGE)])
        # Segmented buttons: radio buttons drawn without the round indicator.
        st.layout("Seg.TRadiobutton", [("Radiobutton.border", {"sticky": "nswe", "children": [
            ("Radiobutton.padding", {"sticky": "nswe", "children": [
                ("Radiobutton.label", {"sticky": "nswe"})]})]})])
        st.configure("Seg.TRadiobutton", background="#F6F7F9", foreground=INK, padding=(16, 7),
                     borderwidth=1, relief="solid", bordercolor="#CFD3D9", font=(FONT, 10, "bold"))
        st.map("Seg.TRadiobutton", background=[("selected", ORANGE), ("active", ORANGE_SOFT)],
               foreground=[("selected", "white")])
        st.configure("TCheckbutton", background=CARD)
        st.configure("Card.TCheckbutton", background=CARD)
        for cb in ("TCheckbutton", "Card.TCheckbutton"):
            st.configure(cb, indicatorbackground=CARD, indicatorforeground="white",
                         indicatormargin=(0, 0, 8, 0), padding=(0, 3))
            st.map(cb, indicatorbackground=[("selected", ORANGE), ("active", ORANGE_SOFT)],
                   indicatorforeground=[("selected", "white")])
        # Inputs
        st.configure("TEntry", fieldbackground=CARD, padding=6, bordercolor=LINE)
        st.map("TEntry", bordercolor=[("focus", ORANGE)], lightcolor=[("focus", ORANGE)])
        st.configure("TCombobox", fieldbackground=CARD, padding=4, arrowsize=14)
        st.map("TCombobox", fieldbackground=[("readonly", CARD)], bordercolor=[("focus", ORANGE)])
        # Tabs
        st.configure("TNotebook", background=CANVAS, borderwidth=0, tabmargins=(0, 6, 0, 0))
        st.configure("TNotebook.Tab", background=CANVAS, foreground=MUTED, padding=(18, 8),
                     font=(FONT, 10, "bold"), borderwidth=0)
        st.map("TNotebook.Tab", background=[("selected", CARD)], foreground=[("selected", ORANGE)],
               expand=[("selected", (0, 0, 0, 0))])
        # Tables
        st.configure("Treeview", background=CARD, fieldbackground=CARD, foreground=INK, rowheight=28,
                     borderwidth=0, font=(FONT, 10))
        st.map("Treeview", background=[("selected", ORANGE_SOFT)], foreground=[("selected", INK)])
        st.configure("Treeview.Heading", background="#F7F7F8", foreground=MUTED, relief="flat",
                     font=(FONT, 9, "bold"), padding=(8, 6), borderwidth=0)
        st.map("Treeview.Heading", background=[("active", "#EFEFF1")])
        st.configure("Grid.Treeview", rowheight=28)
        st.configure("TPanedwindow", background=CARD)
        st.configure("Sash", sashthickness=6, gripcount=0, background=CARD)
        st.configure("Vertical.TScrollbar", background="#E5E7EB", troughcolor=CARD, borderwidth=0,
                     arrowsize=12)
        st.configure("Horizontal.TScrollbar", background="#E5E7EB", troughcolor=CARD, borderwidth=0,
                     arrowsize=12)

    def _btn(self, parent, text, cmd, style=None, **grid):
        b = ttk.Button(parent, text=text, command=cmd, style=style or "TButton")
        self.buttons.append(b)
        return b

    def _card(self, parent, **pack):
        c = ttk.Frame(parent, style="Card.TFrame", padding=(14, 12))
        c.pack(**pack)
        return c

    # ----- layout
    def _build(self):
        # Header band
        head = tk.Frame(self, background=HEADER, height=58)
        head.pack(fill="x")
        head.pack_propagate(False)
        logo = tk.Label(head, text="GX", bg=ORANGE, fg="white", font=(FONT, 12, "bold"), width=3)
        logo.pack(side="left", padx=(18, 10), pady=12)
        tk.Label(head, text=APP_NAME, bg=HEADER, fg="white", font=(FONT, 15, "bold")).pack(side="left")
        tk.Label(head, text="   Global Order Lifecycle Delivery", bg=HEADER, fg="#9CA3AF",
                 font=(FONT, 10)).pack(side="left", pady=(4, 0))
        ttk.Button(head, text="⚙  Settings", style="Header.TButton",
                   command=self._open_settings).pack(side="right", padx=(8, 18))
        self.update_btn = ttk.Button(head, text="⟳  Check for updates", style="Header.TButton",
                                     command=lambda: self._check_updates(quiet=False))
        self.update_btn.pack(side="right", padx=(8, 0))
        self.status = tk.Label(head, font=(FONT, 9, "bold"), bd=0, padx=4, pady=4)
        self.status.pack(side="right")
        self._set_pill("Ready", "#7BD88F", "#2A2A2A")
        tk.Frame(self, background=ORANGE, height=3).pack(fill="x")

        # Status bar (bottom): last message + activity toggle; the log panel above it
        bottom = tk.Frame(self, background=CARD, highlightthickness=1, highlightbackground=LINE)
        bottom.pack(side="bottom", fill="x")
        self.last_msg = tk.Label(bottom, text="Ready.", bg=CARD, fg=MUTED, anchor="w", font=(FONT, 9))
        self.last_msg.pack(side="left", fill="x", expand=True, padx=12, pady=5)
        self.log_toggle = tk.Label(bottom, text="Show activity ▲", bg=CARD, fg=ORANGE, cursor="hand2",
                                   font=(FONT, 9, "bold"))
        self.log_toggle.pack(side="right", padx=12)
        self.log_toggle.bind("<Button-1>", lambda e: self._toggle_log())
        self.log_frame = tk.Frame(self, background=CARD)
        self.log_box = tk.Text(self.log_frame, height=7, state="disabled", font=("Consolas", 9),
                               background="#FAFAFA", foreground=INK, relief="flat", padx=10, pady=6)
        self.log_box.pack(fill="both", expand=True)

        # Main area: two tabs
        root = ttk.Frame(self, padding=(16, 10, 16, 10), style="Canvas.TFrame")
        root.pack(fill="both", expand=True)
        self.notebook = ttk.Notebook(root)
        self.notebook.pack(fill="both", expand=True)
        overview = tk.Frame(self.notebook, background=CARD, padx=16, pady=12)
        self.notebook.add(overview, text="Overview")
        explorer = tk.Frame(self.notebook, background=CARD, padx=14, pady=12)
        self.notebook.add(explorer, text="Order explorer")
        rtdd = tk.Frame(self.notebook, background=CARD, padx=16, pady=12)
        self.notebook.add(rtdd, text="Revised Target Date")
        assign = tk.Frame(self.notebook, background=CARD, padx=16, pady=12)
        self.notebook.add(assign, text="Bulk Order Assignment")
        names = tk.Frame(self.notebook, background=CARD, padx=16, pady=12)
        self.notebook.add(names, text="DPM Names")
        self.bulk_stop_flag = threading.Event()
        self._build_overview_tab(overview)
        self._build_explorer(explorer)
        self._build_rtdd_tab(rtdd)
        self._build_assign_tab(assign)
        self._build_names_tab(names)
        self._refresh_action_state()

    def _toggle_log(self):
        if self.log_frame.winfo_ismapped():
            self.log_frame.pack_forget()
            self.log_toggle.configure(text="Show activity ▲")
        else:
            self.log_frame.pack(side="bottom", fill="x")
            self.log_toggle.configure(text="Hide activity ▼")

    def _build_explorer(self, f):
        # Order bar
        bar = tk.Frame(f, background=CARD)
        bar.pack(fill="x", pady=(0, 10))
        ttk.Label(bar, text="Order #", style="CardHead.TLabel").pack(side="left")
        self.order_var = tk.StringVar()
        ent = ttk.Entry(bar, textvariable=self.order_var, width=16, font=(FONT, 12))
        ent.pack(side="left", padx=(8, 8))
        ent.bind("<Return>", lambda e: self.open_order())
        ent.focus_set()
        self._btn(bar, "Open order", self.open_order, "Accent.TButton").pack(side="left")
        self.order_label = ttk.Label(bar, text="", style="CardMuted.TLabel")
        self.order_label.pack(side="left", padx=16)
        tk.Frame(f, background=LINE, height=1).pack(fill="x", pady=(0, 10))

        main = ttk.Panedwindow(f, orient="horizontal")
        main.pack(fill="both", expand=True)

        left = tk.Frame(main, background=CARD, padx=0)
        ttk.Label(left, text="ORDER TABS", style="CardMuted.TLabel",
                  font=(FONT, 8, "bold")).pack(anchor="w", pady=(0, 6))
        self.tab_list = tk.Listbox(left, width=22, activestyle="none", font=(FONT, 10),
                                   selectbackground=ORANGE, selectforeground="white",
                                   background="#FAFAFA", foreground=INK, borderwidth=0,
                                   highlightthickness=1, highlightbackground=LINE,
                                   highlightcolor=LINE, relief="flat")
        self.tab_list.pack(fill="both", expand=True)
        self.tab_list.bind("<<ListboxSelect>>", lambda e: self._tab_clicked())
        main.add(left, weight=0)

        right = tk.Frame(main, background=CARD, padx=14)
        main.add(right, weight=1)
        head = tk.Frame(right, background=CARD)
        head.pack(fill="x")
        self.tab_title = ttk.Label(head, text="Open an order to start", style="CardHead.TLabel",
                                   font=(FONT, 13, "bold"))
        self.tab_title.pack(side="left")
        self.b_all = self._btn(head, "Export all tabs", self.export_all)
        self.b_all.pack(side="right")
        self.b_xls = self._btn(head, "Export tab to Excel", self.export_tab)
        self.b_xls.pack(side="right", padx=6)
        self.b_shot = self._btn(head, "📷  Screenshot", self.screenshot)
        self.b_shot.pack(side="right")

        self.content = tk.Frame(right, background=CARD, pady=8)
        self.content.pack(fill="both", expand=True)
        self._build_text_view()
        self._build_docs_view()
        self._build_teams_view()
        self._show(self.text_view)

    # ----- settings window
    def _open_settings(self):
        if getattr(self, "_settings_win", None) and self._settings_win.winfo_exists():
            self._settings_win.lift()
            return
        win = self._settings_win = tk.Toplevel(self, background=CARD)
        win.title(f"{APP_NAME} - Settings")
        win.transient(self)
        win.resizable(False, False)
        body = ttk.Frame(win, style="Card.TFrame", padding=(20, 16))
        body.pack(fill="both", expand=True)
        was_shown = self.show_browser.get()

        ttk.Label(body, text="Folders", style="CardHead.TLabel").grid(row=0, column=0, sticky="w",
                                                                      columnspan=4)
        for r, (label, var) in enumerate([("Screenshots", self.shot_dir),
                                          ("Excel & downloads", self.export_dir)], 1):
            ttk.Label(body, text=label, style="Card.TLabel").grid(row=r, column=0, sticky="w", pady=4)
            ttk.Entry(body, textvariable=var, width=62).grid(row=r, column=1, sticky="ew", padx=8)
            ttk.Button(body, text="Browse...", command=lambda v=var: self._browse(v)).grid(row=r, column=2)
            ttk.Button(body, text="Open", command=lambda v=var: self._open_folder(v.get())).grid(
                row=r, column=3, padx=(6, 0))

        ttk.Label(body, text="Screenshots", style="CardHead.TLabel").grid(
            row=3, column=0, sticky="w", columnspan=4, pady=(16, 2))
        for r, (text, var) in enumerate([
                ("Capture the whole page (not just the visible part)", self.full_page),
                ("Take a screenshot automatically when a tab opens", self.auto_shot),
                ("Put each order's screenshots in its own sub-folder", self.per_order)], 4):
            ttk.Checkbutton(body, text=text, variable=var, style="Card.TCheckbutton").grid(
                row=r, column=0, columnspan=4, sticky="w", pady=2)

        ttk.Label(body, text="Browser", style="CardHead.TLabel").grid(
            row=7, column=0, sticky="w", columnspan=4, pady=(16, 2))
        ttk.Checkbutton(body, text="Show the Firefox window (normally GOLD runs hidden in the background)",
                        variable=self.show_browser, style="Card.TCheckbutton").grid(
            row=8, column=0, columnspan=4, sticky="w", pady=2)

        def close():
            self._store_settings()
            if self.show_browser.get() != was_shown and self.worker.driver is not None:
                self.worker.restart = True
                self.log("Firefox will " + ("show" if self.show_browser.get() else "run hidden") +
                         " from the next action.")
            win.destroy()

        btns = ttk.Frame(body, style="Card.TFrame")
        btns.grid(row=9, column=0, columnspan=4, sticky="ew", pady=(18, 0))
        ttk.Label(btns, text=f"{APP_NAME} {__version__}  ·  \u00a9 2026 {AUTHOR}  ·  data folder: {HERE}",
                  style="CardMuted.TLabel", font=(FONT, 8)).pack(side="left")
        ttk.Button(btns, text="Done", style="Accent.TButton", command=close).pack(side="right")
        win.protocol("WM_DELETE_WINDOW", close)
        win.bind("<Escape>", lambda e: close())
        win.update_idletasks()
        x = self.winfo_rootx() + (self.winfo_width() - win.winfo_width()) // 2
        y = self.winfo_rooty() + 80
        win.geometry(f"+{x}+{y}")
        win.grab_set()

    # ----- Overview tab
    RAG_UI = {"Red": ("#C62828", "#FDE7E7"), "Amber": ("#A15C00", "#FFF3D6"),
              "Green": ("#1E7B34", "#E4F4E8"), "No date": ("#595959", "#EFEFEF")}

    def _build_overview_tab(self, f):
        ttk.Label(f, text="Key facts and delivery status of one or more orders. Status is measured against "
                          "the Revised Target Delivery Date (or the Initial one if not revised): "
                          f"Red = passed, Amber = {go.AMBER_DAYS} days or less, Green = more.",
                  style="Muted.TLabel", wraplength=1100, justify="left").pack(anchor="w")
        bar = tk.Frame(f, background=CARD, pady=10)
        bar.pack(fill="x")
        ttk.Label(bar, text="Gold order(s)", style="Head.TLabel").pack(side="left")
        self.ov_input = tk.StringVar()
        ent = ttk.Entry(bar, textvariable=self.ov_input, width=46, font=(FONT, 11))
        ent.pack(side="left", padx=8)
        ent.bind("<Return>", lambda e: self._ov_run())
        self._btn(bar, "Show overview", self._ov_run, "Accent.TButton").pack(side="left")
        ttk.Label(bar, text="  one or more, separated by spaces or commas", style="Muted.TLabel").pack(side="left")
        self.ov_export_btn = self._btn(bar, "Export to Excel", self._ov_export)
        self.ov_export_btn.pack(side="right")

        body = ttk.Panedwindow(f, orient="horizontal")
        body.pack(fill="both", expand=True)
        left = tk.Frame(body, background=CARD)
        ttk.Label(left, text="ORDERS", style="CardMuted.TLabel", font=(FONT, 8, "bold")).pack(anchor="w", pady=(0, 6))
        lf = tk.Frame(left, background=CARD, highlightthickness=1, highlightbackground=LINE)
        lf.pack(fill="both", expand=True)
        self.ov_list = ttk.Treeview(lf, columns=("order", "status", "days", "lead"), show="headings",
                                    selectmode="browse")
        for c, w, t in [("order", 100, "Order"), ("status", 60, "Status"), ("days", 100, "Days left"),
                        ("lead", 80, "Lead time")]:
            self.ov_list.heading(c, text=t, anchor="w")
            self.ov_list.column(c, width=w, anchor="w", stretch=c == "days")
        for k, (fg, bg) in self.RAG_UI.items():
            self.ov_list.tag_configure(k, foreground=fg, background=bg)
        self.ov_list.tag_configure("err", foreground=RED)
        self.ov_list.pack(fill="both", expand=True)
        self.ov_list.bind("<<TreeviewSelect>>", lambda e: self._ov_show_selected())
        body.add(left, weight=0)

        right = tk.Frame(body, background=CARD, padx=14)
        body.add(right, weight=1)
        self.ov_title = ttk.Label(right, text="Enter an order to see its overview", style="CardHead.TLabel",
                                  font=(FONT, 14, "bold"))
        self.ov_title.pack(anchor="w")
        # Cards: order value (big), delivery status, 120-day lead time
        cards = tk.Frame(right, background=CARD)
        cards.pack(fill="x", pady=(10, 10))
        self.ov_cards = {}
        for key, caption, weight in (("value", "ORDER TOTAL VALUE", 3), ("delivery", "DELIVERY STATUS", 2),
                                     ("lead", "120-DAY LEAD TIME", 2)):
            card = tk.Frame(cards, background="#F7F7F8", padx=16, pady=12, highlightthickness=1,
                            highlightbackground=LINE)
            card.pack(side="left", fill="both", expand=True, padx=(0, 10) if key != "lead" else 0)
            cap = tk.Label(card, text=caption, font=(FONT, 8, "bold"), anchor="w", background="#F7F7F8",
                           foreground=MUTED)
            cap.pack(fill="x")
            big = tk.Label(card, text="-", font=(FONT, 22 if key == "value" else 16, "bold"), anchor="w",
                           background="#F7F7F8", foreground=INK)
            big.pack(fill="x", pady=(2, 0))
            sub = tk.Label(card, text="", font=(FONT, 9), anchor="w", justify="left", background="#F7F7F8",
                           foreground=MUTED, wraplength=330)
            sub.pack(fill="x")
            self.ov_cards[key] = (card, cap, big, sub)
        self.ov_banner = tk.Label(right, text="", anchor="w", font=(FONT, 11, "bold"), background=CARD)
        tf = tk.Frame(right, background=CARD)
        tf.pack(fill="both", expand=True)
        self.ov_text = tk.Text(tf, wrap="word", font=(FONT, 10), relief="flat", background=CARD,
                               padx=4, pady=4, tabs=("230",), spacing1=2, spacing3=2)
        sb = ttk.Scrollbar(tf, command=self.ov_text.yview)
        self.ov_text.configure(yscrollcommand=sb.set, state="disabled")
        sb.pack(side="right", fill="y")
        self.ov_text.pack(fill="both", expand=True)
        self.ov_text.tag_configure("section", font=(FONT, 11, "bold"), foreground=ORANGE, spacing1=10, spacing3=4)
        self.ov_text.tag_configure("label", font=(FONT, 10, "bold"), foreground=MUTED)
        self.ov_text.tag_configure("value", font=(FONT, 10), foreground=INK, lmargin2=234)
        self.ov_results = {}   # order -> overview dict
        self.ov_errors = {}    # order -> error text
        self.ov_export_btn.state(["disabled"])

    def _ov_run(self):
        if self.busy:
            return
        orders = []
        for o in re.split(r"[\s,;]+", self.ov_input.get().strip()):
            if o and o not in orders:
                orders.append(o)
        bad = [o for o in orders if not re.fullmatch(r"\d{2}-\d{5,8}", o)]
        if not orders or bad:
            messagebox.showwarning(APP_NAME, "Type GOLD order numbers like 10-1764901"
                                   + (f"\n\nNot an order number: {', '.join(bad)}" if bad else ""))
            return
        self.ov_results, self.ov_errors = {}, {}
        self.ov_list.delete(*self.ov_list.get_children())
        for o in orders:
            self.ov_list.insert("", "end", iid=o, values=(o, "...", "waiting", ""))
        w = self.worker

        def job():
            w.ensure_browser()
            for o in orders:
                self.ui(lambda o=o: self.ov_list.item(o, values=(o, "...", "reading GOLD...", "")))
                try:
                    try:
                        w.ensure_browser()
                        ov = go.collect(w.driver, w.wait, o)
                    except Exception as e:
                        if not w.session_problem(e):
                            raise
                        self.log(f"Connection problem on {o} - reconnecting and retrying...")
                        w.wait_for_network()
                        w.restart = True
                        w.ensure_browser()
                        ov = go.collect(w.driver, w.wait, o)
                    self.ov_results[o] = ov
                    self.ui(lambda o=o, ov=ov: self._ov_listed(o, ov))
                except Exception as e:
                    err = str(e).splitlines()[0] if str(e) else type(e).__name__
                    self.ov_errors[o] = err
                    self.ui(lambda o=o, err=err: self.ov_list.item(o, values=(o, "error", err, ""), tags=("err",)))
                    self.log(f"Overview {o}: FAILED - {err}")
            return len(self.ov_results)

        def done(n):
            self.log(f"Overview ready for {n} of {len(orders)} order(s)")
            first = next((o for o in orders if o in self.ov_results), None)
            if first:
                self.ov_list.selection_set(first)
            self._refresh_action_state()

        w.submit(f"Reading {len(orders)} order(s)", job, done)

    def _ov_listed(self, o, ov):
        days = "" if ov["days_left"] is None else ov["rag_text"]
        self.ov_list.item(o, values=(o, ov["rag"], days, ov["lt_rag"]), tags=(ov["rag"],))
        if not self.ov_list.selection():
            self.ov_list.selection_set(o)

    def _ov_show_selected(self):
        sel = self.ov_list.selection()
        if not sel:
            return
        o = sel[0]
        t = self.ov_text
        t.configure(state="normal")
        t.delete("1.0", "end")
        if o not in self.ov_results:
            self.ov_title.configure(text=o)
            for key in self.ov_cards:
                self._ov_card(key, "-", "", None)
            self._ov_card("value", "Not available", self.ov_errors.get(o, "Not read yet"), None)
            t.configure(state="disabled")
            return
        ov = self.ov_results[o]
        self.ov_title.configure(text=f"{o}   ·   {ov['customer']}")
        cur = ov.get("currency", "")
        if ov.get("total_value") is not None:
            term = f" x {ov['term_months']} months" if ov.get("term_months") else ""
            self._ov_card("value", go.money(ov["total_value"], cur),
                          f"New monthly {go.money(ov['mrc_new'], cur)}{term} + one-off {go.money(ov['one_off'], cur)}",
                          None)
        else:
            self._ov_card("value", "-", "No pricing totals found", None)
        which = "Revised TDD" if ov["revised_tdd"] else "Initial TDD"
        when = go.fmt(ov["key_date"]) if ov["key_date"] else ""
        self._ov_card("delivery", f"● {ov['rag']}  ·  {ov['rag_text']}", f"{which} {when}" if when else "", ov["rag"])
        self._ov_card("lead", f"● {ov['lt_rag']}", ov["lt_text"] + (
            f"\nDeadline {go.fmt(ov['lt_deadline'])} (signed {go.fmt(ov['signature_date'])} + "
            f"{go.LEAD_TIME_DAYS} days)" if ov["lt_deadline"] else ""), ov["lt_rag"])
        prev = None
        for section, label, key in go.LAYOUT:
            if section != prev:
                t.insert("end", section + "\n", "section")
                prev = section
            t.insert("end", label, "label")
            t.insert("end", "\t" + (go.display_value(ov, label, key) or "-") + "\n", "value")
        if ov["rtdd_history"]:
            t.insert("end", "Revised Target Date history\n", "section")
            for title, d, closed in ov["rtdd_history"]:
                t.insert("end", d or "-", "label")
                t.insert("end", f"\t{title}" + (f"  (closed {closed})" if closed else "  (current)") + "\n", "value")
        t.configure(state="disabled")

    def _ov_card(self, key, big_text, sub_text, rag):
        card, cap, big, sub = self.ov_cards[key]
        fg, bg = self.RAG_UI[rag] if rag else (INK, "#F7F7F8")
        if key == "value" and rag is None:
            fg, bg = ORANGE, "#FFF4EB"  # the value card stands out in orange
        for wdg in (card, cap, big, sub):
            wdg.configure(background=bg)
        card.configure(highlightbackground=fg if rag or key == "value" else LINE)
        big.configure(text=big_text, foreground=fg)
        sub.configure(text=sub_text)

    def _ov_export(self):
        order_list = [o for o in self.ov_list.get_children() if o in self.ov_results]
        if not order_list:
            return
        ctx = self._ctx()
        name = (f"Overview_{order_list[0]}" if len(order_list) == 1
                else f"GOLD_overview_{datetime.now():%Y-%m-%d_%H%M}")
        path = Path(ctx["workbook"]).parent / f"{name}.xlsx"
        try:
            go.export([self.ov_results[o] for o in order_list], path)
        except PermissionError:
            messagebox.showerror(APP_NAME, f"{path.name} is open in Excel. Close it and try again.")
            return
        self.log(f"Overview exported: {path}")
        if messagebox.askyesno(APP_NAME, f"Saved to\n{path}\n\nOpen it now?"):
            os.startfile(path)

    # ----- shared pieces of the bulk tabs (Revised Target Date, Bulk Order Assignment)
    def _grid_toolbar(self, f, title, hint, grid_attr):
        tb = tk.Frame(f, background=CARD)
        tb.pack(fill="x", pady=(6, 4))
        ttk.Label(tb, text=title, style="Head.TLabel").pack(side="left")
        ttk.Label(tb, text="   " + hint, style="Muted.TLabel").pack(side="left")
        grid = lambda: getattr(self, grid_attr)
        ttk.Button(tb, text="Clear all", command=lambda: grid().clear()).pack(side="right")
        ttk.Button(tb, text="+ 10 rows", command=lambda: grid().add_rows(10)).pack(side="right", padx=4)
        ttk.Button(tb, text="Paste from Excel", command=lambda: self._grid_paste(grid())).pack(side="right")
        ttk.Button(tb, text="Load Excel/CSV...", command=lambda: self._grid_load(grid())).pack(
            side="right", padx=4)

    def _grid_paste(self, grid):
        n = grid.paste()
        if not n:
            messagebox.showinfo(APP_NAME, "The clipboard is empty. Copy the cells in Excel first.")
        else:
            self.log(f"Pasted {n} row(s)")

    def _grid_load(self, grid):
        path = filedialog.askopenfilename(
            title="Load orders", filetypes=[("Excel / CSV", "*.xlsx *.xlsm *.csv *.txt"), ("All files", "*.*")])
        if not path:
            return
        try:
            n = grid.load(path)
        except Exception as e:
            messagebox.showerror(APP_NAME, f"Could not read the file:\n{e}")
            return
        self.log(f"Loaded {n} row(s) from {Path(path).name}")

    def _bulk_bar(self, f, dry_var, run_cmd, check_cmd):
        rb = tk.Frame(f, background=CARD, pady=8)
        rb.pack(fill="x")
        ttk.Checkbutton(rb, text="Test only (do everything except the final save)",
                        variable=dry_var).pack(side="left")
        stop = ttk.Button(rb, text="Stop", command=self._bulk_stop)
        stop.pack(side="right")
        stop.state(["disabled"])
        self._btn(rb, "Run update", run_cmd, "Accent.TButton").pack(side="right", padx=6)
        ttk.Button(rb, text="Check", command=check_cmd).pack(side="right")
        return stop

    def _bulk_stop(self):
        self.bulk_stop_flag.set()
        self.log("Stopping after the current order...")

    def _bulk_run(self, grid, stop_btn, items, label, action, columns, sheet, header_line, dry):
        """Run action(driver, wait, item) for each (iid, item, row_values) and report per row.
        Writes <sheet>_<date>.xlsx with columns + Result + Details."""
        ctx = self._ctx()
        self.bulk_stop_flag.clear()
        stop_btn.state(["!disabled"])
        w = self.worker

        def set_status(iid, text, tag):
            self.ui(lambda: grid.set_status(iid, text, tag))

        def job():
            w.ensure_browser()
            results = []
            for iid, item, row in items:
                if self.bulk_stop_flag.is_set():
                    set_status(iid, "Skipped (stopped)", "bad")
                    results.append(row + ["SKIPPED", "stopped"])
                    continue
                set_status(iid, "Working...", "run")
                try:
                    w.ensure_browser()  # reconnects if the connection dropped (saves are not retried)
                    msg = action(w.driver, w.wait, item)
                    set_status(iid, f"✓ {msg}", "ok")
                    results.append(row + ["OK", msg])
                    self.log(f"{row[0]}: {msg}")
                except Exception as e:
                    err = str(e).splitlines()[0] if str(e) else type(e).__name__
                    set_status(iid, f"✗ {err}", "bad")
                    results.append(row + ["FAILED", err])
                    self.log(f"{row[0]}: FAILED - {err}")
                    try:  # back to a clean search page for the next order
                        oo.open_orders_tab(w.driver, w.wait, discard_changes=True)
                    except Exception:
                        pass
            stamp = datetime.now().strftime("%Y-%m-%d_%H%M")
            path = Path(ctx["workbook"]).parent / f"{sheet.replace(' ', '_')}_{stamp}.xlsx"
            gx.write_sheet(path, sheet, [header_line + ("  |  TEST ONLY - nothing saved" if dry else ""),
                                         f"Run {datetime.now():%d-%b-%Y %H:%M}"],
                           [("Results", columns + ["Result", "Details"], results)])
            return path, results

        def done(res):
            path, results = res
            ok = sum(1 for r in results if r[len(columns)] == "OK")
            self.log(f"{label}: {ok} of {len(results)} OK. Results: {path}")
            if messagebox.askyesno(APP_NAME, f"{ok} of {len(results)} order(s) "
                                             f"{'tested' if dry else 'done'}.\n\nResults saved to\n{path}"
                                             "\n\nOpen it now?"):
                os.startfile(path)

        w.submit(f"{label}: {len(items)} order(s)", job, done)

    # ----- Revised Target Date tab
    def _build_rtdd_tab(self, f):
        ttk.Label(f, text="Adds a 'Revised Target Date' milestone (Milestones > Create new) to each order "
                          "in the table, with its Target Date and reason.", style="Muted.TLabel").pack(anchor="w")
        opts = tk.Frame(f, background=CARD, pady=10)
        opts.pack(fill="x")
        ttk.Label(opts, text="Reason type").grid(row=0, column=0, sticky="w")
        self.rtdd_kind = tk.StringVar(value="Customer")
        kinds = tk.Frame(opts, background=CARD)
        kinds.grid(row=0, column=1, columnspan=3, sticky="w", padx=8)
        for kind, label in [("Customer", "Customer reason"), ("Orange", "Orange Business Services reason")]:
            ttk.Radiobutton(kinds, text=label, value=kind, variable=self.rtdd_kind,
                            style="Seg.TRadiobutton", command=self._rtdd_kind_changed).pack(side="left", padx=(0, 4))
        ttk.Label(opts, text="For empty cells use", style="Muted.TLabel").grid(row=1, column=0, sticky="w", pady=(8, 0))
        dflt = tk.Frame(opts, background=CARD)
        dflt.grid(row=1, column=1, columnspan=3, sticky="w", padx=8, pady=(8, 0))
        ttk.Label(dflt, text="Date").pack(side="left")
        self.rtdd_default = tk.StringVar()
        ttk.Entry(dflt, textvariable=self.rtdd_default, width=14).pack(side="left", padx=(4, 16))
        ttk.Label(dflt, text="Reason").pack(side="left")
        self.rtdd_reason = tk.StringVar(value="")
        self.rtdd_reason_cb = ttk.Combobox(dflt, textvariable=self.rtdd_reason, state="readonly", width=62)
        self.rtdd_reason_cb.pack(side="left", padx=4)

        def norm_date(v):
            try:
                return gm.gold_date(gm.parse_date(v))
            except ValueError:
                return str(v)

        self._grid_toolbar(f, "Orders to update",
                           "click a cell to type  ·  Ctrl+V pastes rows from Excel  ·  Delete clears rows",
                           "rtdd_grid")
        self.rtdd_grid = EditGrid(f, [
            {"key": "order", "title": "Gold order", "width": 130},
            {"key": "date", "title": "Date", "width": 120, "normalize": norm_date},
            {"key": "reason", "title": "Reason", "width": 430, "stretch": True,
             "choices": lambda: gm.REASONS[self.rtdd_kind.get()]},
        ])
        self.rtdd_grid.pack(fill="both", expand=True)
        self.rtdd_dry = tk.BooleanVar(value=False)
        self.rtdd_stop_btn = self._bulk_bar(f, self.rtdd_dry, self._rtdd_run, self._rtdd_check)
        self._rtdd_kind_changed()

    def _rtdd_kind_changed(self):
        reasons = [""] + gm.REASONS[self.rtdd_kind.get()]
        self.rtdd_reason_cb.configure(values=reasons)
        if self.rtdd_reason.get() not in reasons:
            self.rtdd_reason.set("")

    def _rtdd_check(self):
        """Validate the table; mark Ready or the problem. Returns ([(iid, item, row)], n_bad) or None."""
        g = self.rtdd_grid
        g.close_editor(True)
        kind = self.rtdd_kind.get()
        default_date = self.rtdd_default.get().strip()
        if default_date:
            try:
                gm.parse_date(default_date)
            except ValueError as e:
                messagebox.showwarning(APP_NAME, f"Default date: {e}")
                return None
        items, seen, bad = [], set(), 0
        for iid, r in g.filled():
            try:
                order = r["order"]
                if not re.fullmatch(r"\d{2}-\d{5,8}", order):
                    raise ValueError("not a GOLD order number (like 10-1764901)")
                if order in seen:
                    raise ValueError("this order is already in the list")
                seen.add(order)
                if not (r["date"] or default_date):
                    raise ValueError("no date")
                dt = gm.parse_date(r["date"] or default_date)
                reason = gm.match_reason(kind, r["reason"]) if r["reason"] else self.rtdd_reason.get()
                if r["reason"] and reason != r["reason"]:
                    g.set_value(iid, "reason", reason)  # GOLD's exact wording
                items.append((iid, (order, dt, reason), [order, gm.gold_date(dt), reason]))
                g.set_status(iid, "Ready")
            except ValueError as e:
                bad += 1
                g.set_status(iid, f"✗ {e}", "bad")
        self.log(f"Revised Target Date check: {len(items)} ready" + (f", {bad} with problems" if bad else ""))
        return items, bad

    def _rtdd_run(self):
        if self.busy:
            return
        checked = self._rtdd_check()
        if not checked:
            return
        items, bad = checked
        if not items:
            messagebox.showinfo(APP_NAME, "Fill in at least one Gold order and Date, then try again.")
            return
        if bad and not messagebox.askyesno(APP_NAME, "Some rows have problems (shown in red) and will be "
                                                     "skipped.\nContinue with the others?"):
            return
        kind, dry = self.rtdd_kind.get(), self.rtdd_dry.get()
        title = gm.RTDD_TITLES[kind]
        if not dry and not messagebox.askyesno(
                "Confirm GOLD update", f"Add the milestone\n\n    {title}\n\nto {len(items)} order(s) in GOLD, "
                                       "each with its Date (and Reason, where given)?\n\nThis saves in GOLD."):
            return
        self._bulk_run(self.rtdd_grid, self.rtdd_stop_btn, items, "Revised Target Date",
                       lambda d, w, it: gm.add_rtdd(d, w, it[0], kind, it[1], it[2], dry_run=dry),
                       ["Gold order", "Date", "Reason"], "RTDD update", title, dry)

    # ----- Bulk Order Assignment tab
    def _dpm_choices(self):
        return [gn.full_name(e) for e in self.dpm_names]

    def _dpm_normalize(self, value):
        e = gn.lookup(self.dpm_names, value)
        return gn.full_name(e) if e else " ".join(str(value).split())

    def _build_assign_tab(self, f):
        ttk.Label(f, text="Makes the chosen DPM the primary STM of each order (Teams > Manage Teams > STM), "
                          "then saves the teams. Pick names from the list - manage it in the DPM Names tab.",
                  style="Muted.TLabel").pack(anchor="w")
        opts = tk.Frame(f, background=CARD, pady=10)
        opts.pack(fill="x")
        ttk.Label(opts, text="For empty cells use", style="Muted.TLabel").pack(side="left")
        self.assign_default = tk.StringVar()
        self.assign_default_cb = ttk.Combobox(opts, textvariable=self.assign_default, width=34,
                                              values=[""] + self._dpm_choices())
        self.assign_default_cb.pack(side="left", padx=8)

        def filter_default(event):
            typed = self.assign_default.get().strip().lower()
            self.assign_default_cb.configure(values=[c for c in self._dpm_choices() if typed in c.lower()]
                                             if typed else [""] + self._dpm_choices())
        self.assign_default_cb.bind("<KeyRelease>", filter_default)

        self._grid_toolbar(f, "Orders to assign",
                           "click a cell to type  ·  type in the DPM cell to filter names  ·  Ctrl+V pastes from Excel",
                           "assign_grid")
        self.assign_grid = EditGrid(f, [
            {"key": "order", "title": "Gold order", "width": 140},
            {"key": "dpm", "title": "STM (DPM)", "width": 300, "choices": self._dpm_choices,
             "typeahead": True, "normalize": self._dpm_normalize},
        ])
        self.assign_grid.pack(fill="both", expand=True)
        self.assign_dry = tk.BooleanVar(value=False)
        self.assign_stop_btn = self._bulk_bar(f, self.assign_dry, self._assign_run, self._assign_check)

    def _assign_check(self):
        g = self.assign_grid
        g.close_editor(True)
        default = self.assign_default.get().strip()
        items, seen, bad = [], set(), 0
        for iid, r in g.filled():
            try:
                order = r["order"]
                if not re.fullmatch(r"\d{2}-\d{5,8}", order):
                    raise ValueError("not a GOLD order number (like 10-1764901)")
                if order in seen:
                    raise ValueError("this order is already in the list")
                seen.add(order)
                name = r["dpm"] or default
                if not name:
                    raise ValueError("choose the STM (DPM)")
                entry = gn.lookup(self.dpm_names, name)
                first, last = (entry["first"], entry["last"]) if entry else gn.split_name(name)
                if not last:
                    raise ValueError("the STM needs a first and a last name")
                user = (entry or {}).get("user") or None
                items.append((iid, (order, first, last, user), [order, f"{first} {last}"]))
                g.set_status(iid, "Ready" if entry else "Ready (name is not in the DPM list)")
            except ValueError as e:
                bad += 1
                g.set_status(iid, f"✗ {e}", "bad")
        self.log(f"Bulk Order Assignment check: {len(items)} ready" + (f", {bad} with problems" if bad else ""))
        return items, bad

    def _assign_run(self):
        if self.busy:
            return
        items, bad = self._assign_check()
        if not items:
            messagebox.showinfo(APP_NAME, "Fill in at least one Gold order with its STM (DPM), then try again.")
            return
        if bad and not messagebox.askyesno(APP_NAME, "Some rows have problems (shown in red) and will be "
                                                     "skipped.\nContinue with the others?"):
            return
        dry = self.assign_dry.get()
        people = sorted({row[1] for _, _, row in items})
        if not dry and not messagebox.askyesno(
                "Confirm GOLD update",
                f"Make {', '.join(people[:3])}{' and others' if len(people) > 3 else ''} the primary STM "
                f"of {len(items)} order(s) and save the teams in GOLD?\n\n"
                "Where STM is 'Same as project', that is unticked so the order gets its own STM.\n\n"
                "This saves in GOLD."):
            return
        self._bulk_run(self.assign_grid, self.assign_stop_btn, items, "Bulk Order Assignment",
                       lambda d, w, it: gt.assign_stm(d, w, it[0], it[1], it[2], dry_run=dry, user=it[3]),
                       ["Gold order", "STM (DPM)"], "STM assignment", "Primary STM assignment", dry)

    # ----- DPM Names tab
    def _build_names_tab(self, f):
        ttk.Label(f, text="The DPMs (STMs) offered in Bulk Order Assignment, with their names as they appear in "
                          "GOLD. Add, edit or remove names; the list is saved on this computer.",
                  style="Muted.TLabel").pack(anchor="w")
        tb = tk.Frame(f, background=CARD, pady=10)
        tb.pack(fill="x")
        self._btn(tb, "+ Add name", self._names_add, "Accent.TButton").pack(side="left")
        self._btn(tb, "Edit", self._names_edit).pack(side="left", padx=6)
        self._btn(tb, "Delete", self._names_delete).pack(side="left")
        self._btn(tb, "Check names in GOLD", self._names_check).pack(side="left", padx=(18, 0))
        ttk.Label(tb, text="Find").pack(side="left", padx=(18, 4))
        self.names_filter = tk.StringVar()
        fe = ttk.Entry(tb, textvariable=self.names_filter, width=22)
        fe.pack(side="left")
        fe.bind("<KeyRelease>", lambda e: self._names_fill())
        self._btn(tb, "Export to Excel", self._names_export).pack(side="right")
        self._btn(tb, "Import Excel/CSV...", self._names_import).pack(side="right", padx=6)

        lf = tk.Frame(f, background=CARD, highlightthickness=1, highlightbackground=LINE)
        lf.pack(fill="both", expand=True)
        cols = ("name", "first", "last", "user", "check")
        self.names_tree = ttk.Treeview(lf, columns=cols, show="headings", selectmode="extended")
        for c, w, t in [("name", 220, "Name"), ("first", 160, "GOLD first name"), ("last", 160, "GOLD last name"),
                        ("user", 120, "GOLD user"), ("check", 300, "Checked in GOLD")]:
            self.names_tree.heading(c, text=t, anchor="w")
            self.names_tree.column(c, width=w, anchor="w", stretch=c == "check")
        self.names_tree.tag_configure("ok", foreground=GREEN)
        self.names_tree.tag_configure("bad", foreground=RED)
        self.names_tree.tag_configure("odd", background="#FAFAFB")
        sb = ttk.Scrollbar(lf, command=self.names_tree.yview)
        self.names_tree.configure(yscrollcommand=sb.set)
        sb.pack(side="right", fill="y")
        self.names_tree.pack(fill="both", expand=True)
        self.names_tree.bind("<Double-1>", lambda e: self._names_edit())
        self.names_tree.bind("<Delete>", lambda e: self._names_delete())
        self.names_count = ttk.Label(f, text="", style="Muted.TLabel")
        self.names_count.pack(anchor="w", pady=(6, 0))
        self._names_fill()

    def _names_saved(self):
        self.dpm_names = gn.save(self.dpm_names)
        self._names_fill()
        if hasattr(self, "assign_default_cb"):
            self.assign_default_cb.configure(values=[""] + self._dpm_choices())

    def _names_fill(self):
        t = self.names_tree
        t.delete(*t.get_children())
        q = self.names_filter.get().strip().lower() if hasattr(self, "names_filter") else ""
        shown = 0
        for i, e in enumerate(self.dpm_names):
            name = gn.full_name(e)
            if q and q not in name.lower() and q not in e.get("user", "").lower():
                continue
            status = e.get("check", "")
            tags = ["ok" if status.startswith("✓") else "bad" if status.startswith("✗") else ""]
            if shown % 2:
                tags.append("odd")
            t.insert("", "end", iid=str(i), values=(name, e["first"], e["last"], e.get("user", ""), status),
                     tags=[x for x in tags if x])
            shown += 1
        self.names_count.configure(text=f"{len(self.dpm_names)} names" + (f"  ·  {shown} shown" if q else ""))

    def _names_dialog(self, title, entry=None):
        """Small form for one name. Returns {'first','last'} or None."""
        win = tk.Toplevel(self, background=CARD)
        win.title(title)
        win.transient(self)
        win.resizable(False, False)
        body = ttk.Frame(win, style="Card.TFrame", padding=(20, 16))
        body.pack(fill="both", expand=True)
        ttk.Label(body, text="Type the name exactly as it appears in GOLD.", style="CardMuted.TLabel").grid(
            row=0, column=0, columnspan=2, sticky="w", pady=(0, 10))
        first = tk.StringVar(value=(entry or {}).get("first", ""))
        last = tk.StringVar(value=(entry or {}).get("last", ""))
        user = tk.StringVar(value=(entry or {}).get("user", ""))
        for r, (label, var) in enumerate((("First name", first), ("Last name", last),
                                          ("GOLD user ID", user)), 1):
            ttk.Label(body, text=label, style="Card.TLabel").grid(row=r, column=0, sticky="w", pady=4)
            e = ttk.Entry(body, textvariable=var, width=34)
            e.grid(row=r, column=1, padx=(10, 0), pady=4)
            if r == 1:
                e.focus_set()
        result = {}

        def ok(*_):
            f, l = " ".join(first.get().split()), " ".join(last.get().split())
            if not f or not l:
                messagebox.showwarning(APP_NAME, "Fill in both the first and the last name.", parent=win)
                return
            dup = gn.lookup(self.dpm_names, f"{f} {l}")
            if dup is not None and dup is not entry:
                messagebox.showwarning(APP_NAME, f"{f} {l} is already in the list.", parent=win)
                return
            result.update(first=f, last=l, user=user.get().strip())
            win.destroy()

        ttk.Label(body, text="GOLD user ID is optional - only needed when two GOLD users share the name "
                             "(e.g. asmith2).", style="CardMuted.TLabel", wraplength=360).grid(
            row=4, column=0, columnspan=2, sticky="w", pady=(4, 0))
        btns = ttk.Frame(body, style="Card.TFrame")
        btns.grid(row=5, column=0, columnspan=2, sticky="e", pady=(14, 0))
        ttk.Button(btns, text="Cancel", command=win.destroy).pack(side="right")
        ttk.Button(btns, text="Save", style="Accent.TButton", command=ok).pack(side="right", padx=6)
        win.bind("<Return>", ok)
        win.bind("<Escape>", lambda e: win.destroy())
        win.update_idletasks()
        win.geometry(f"+{self.winfo_rootx() + 200}+{self.winfo_rooty() + 160}")
        win.grab_set()
        self.wait_window(win)
        return result or None

    def _names_add(self):
        new = self._names_dialog("Add DPM name")
        if new and not new.get("user"):
            new.pop("user", None)
        if new:
            self.dpm_names.append(new)
            self._names_saved()
            self.log(f"DPM added: {new['first']} {new['last']}")

    def _names_edit(self):
        sel = self.names_tree.selection()
        if not sel:
            messagebox.showinfo(APP_NAME, "Select a name to edit (or double-click it).")
            return
        entry = self.dpm_names[int(sel[0])]
        new = self._names_dialog("Edit DPM name", entry)
        if new:
            old = gn.full_name(entry)
            entry.update(new)
            if not entry.get("user"):
                entry.pop("user", None)
            entry.pop("check", None)
            self._names_saved()
            self.log(f"DPM edited: {old} -> {gn.full_name(entry)}")

    def _names_delete(self):
        sel = self.names_tree.selection()
        if not sel:
            return
        names = [gn.full_name(self.dpm_names[int(i)]) for i in sel]
        if not messagebox.askyesno(APP_NAME, f"Remove {len(names)} name(s) from the list?\n\n" +
                                   "\n".join(names[:10]) + ("\n..." if len(names) > 10 else "")):
            return
        for i in sorted((int(i) for i in sel), reverse=True):
            del self.dpm_names[i]
        self._names_saved()
        self.log(f"Removed {len(names)} DPM name(s)")

    def _names_import(self):
        path = filedialog.askopenfilename(title="Import DPM names", filetypes=[
            ("Excel / CSV", "*.xlsx *.xlsm *.csv *.txt"), ("All files", "*.*")])
        if not path:
            return
        try:
            rows = []
            if path.lower().endswith((".xlsx", ".xlsm")):
                from openpyxl import load_workbook
                ws = load_workbook(path, read_only=True, data_only=True).worksheets[0]
                rows = [[str(c or "").strip() for c in r[:2]] for r in ws.iter_rows(values_only=True) if r]
            else:
                import csv
                text = Path(path).read_text(encoding="utf-8-sig")
                rows = [r[:2] for r in csv.reader(text.splitlines())]
        except Exception as e:
            messagebox.showerror(APP_NAME, f"Could not read the file:\n{e}")
            return
        added = 0
        for r in rows:
            r = [c for c in r if c and str(c).strip()]
            if not r or re.search(r"\bname\b", " ".join(r), re.I):
                continue  # empty or header row
            first, last = (r[0], r[1]) if len(r) >= 2 else gn.split_name(r[0])
            if last and not gn.lookup(self.dpm_names, f"{first} {last}"):
                self.dpm_names.append({"first": first.strip(), "last": last.strip()})
                added += 1
        self._names_saved()
        self.log(f"Imported {added} new DPM name(s) from {Path(path).name}")
        messagebox.showinfo(APP_NAME, f"{added} new name(s) added.")

    def _names_export(self):
        ctx = self._ctx()
        path = Path(ctx["workbook"]).parent / "DPM_names.xlsx"
        try:
            gx.write_sheet(path, "DPM names", [f"{len(self.dpm_names)} names", f"Exported {datetime.now():%d-%b-%Y %H:%M}"],
                           [("DPM names", ["Name", "GOLD first name", "GOLD last name", "GOLD user", "Checked"],
                             [[gn.full_name(e), e["first"], e["last"], e.get("user", ""), e.get("check", "")]
                              for e in self.dpm_names])])
        except PermissionError:
            messagebox.showerror(APP_NAME, f"{path.name} is open in Excel. Close it and try again.")
            return
        if messagebox.askyesno(APP_NAME, f"Saved to\n{path}\n\nOpen it now?"):
            os.startfile(path)

    def _names_check(self):
        """Look every name up in GOLD (Administration > users, read-only) and store GOLD's exact
        first/last name and user id, so Bulk Order Assignment always finds them."""
        if self.busy:
            return
        sel = self.names_tree.selection()
        entries = [self.dpm_names[int(i)] for i in sel] if sel else list(self.dpm_names)
        if not messagebox.askyesno(APP_NAME, f"Check {len(entries)} name(s) in GOLD?\n\n"
                                             "This only reads GOLD (about 5 seconds per name)."):
            return
        w = self.worker

        def job():
            w.ensure_browser()
            gt.open_user_list(w.driver, w.wait)
            ok = 0
            for n, e in enumerate(entries, 1):
                name = gn.full_name(e)
                self.ui(lambda n=n, name=name: self._set_pill(f"Checking {n}/{len(entries)}: {name}...",
                                                              ORANGE, "#2A2A2A"))
                try:
                    user, gfirst, glast = gt.check_name(w.driver, w.wait, e["first"], e["last"], e.get("user"))
                    e.update(first=gfirst, last=glast, user=user, check=f"✓ found ({datetime.now():%d-%b-%Y})")
                    ok += 1
                except Exception as ex:
                    msg = str(ex).splitlines()[0] if str(ex) else type(ex).__name__
                    e.update(check=f"✗ {msg.replace(' - check the name in the DPM Names tab', '')}")
                    if not w.session_problem(ex):
                        continue
                    w.ensure_browser()
                    gt.open_user_list(w.driver, w.wait)
            return ok

        def done(ok):
            self._names_saved()
            self.log(f"Checked {len(entries)} name(s) in GOLD: {ok} found, {len(entries) - ok} not found")

        w.submit(f"Checking {len(entries)} name(s) in GOLD", job, done)

    def _build_text_view(self):
        f = self.text_view = ttk.Frame(self.content)
        self.text = tk.Text(f, wrap="word", font=("Segoe UI", 10), relief="flat",
                            background="white", padx=10, pady=8)
        sb = ttk.Scrollbar(f, command=self.text.yview)
        self.text.configure(yscrollcommand=sb.set, state="disabled", tabs=("260",))
        self.text.tag_configure("section", font=("Segoe UI Semibold", 11), foreground=ORANGE,
                                spacing1=6, spacing3=2)
        self.text.tag_configure("label", font=("Segoe UI Semibold", 10))
        self.text.tag_configure("mono", font=("Consolas", 9), wrap="none")
        xs = ttk.Scrollbar(f, orient="horizontal", command=self.text.xview)
        self.text.configure(xscrollcommand=xs.set)
        xs.pack(side="bottom", fill="x")
        sb.pack(side="right", fill="y")
        self.text.pack(fill="both", expand=True)

    def _build_docs_view(self):
        f = self.docs_view = ttk.Frame(self.content)
        bar = ttk.Frame(f)
        bar.pack(fill="x", pady=(0, 6))
        ttk.Label(bar, text="Select documents (Ctrl/Shift-click for several)").pack(side="left")
        self._btn(bar, "Download all", lambda: self.download(all_docs=True)).pack(side="right")
        self._btn(bar, "Download selected", self.download, "Accent.TButton").pack(side="right", padx=6)
        cols = ("n", "title", "modified", "type", "saved")
        self.docs_tree = ttk.Treeview(f, columns=cols, show="headings", selectmode="extended")
        for c, w, t in [("n", 40, "#"), ("title", 330, "Document"), ("modified", 170, "Last modified"),
                        ("type", 190, "Type"), ("saved", 200, "Downloaded")]:
            self.docs_tree.heading(c, text=t)
            self.docs_tree.column(c, width=w, anchor="w", stretch=c in ("title", "saved"))
        sb = ttk.Scrollbar(f, command=self.docs_tree.yview)
        self.docs_tree.configure(yscrollcommand=sb.set)
        sb.pack(side="right", fill="y")
        self.docs_tree.pack(fill="both", expand=True)

    def _build_teams_view(self):
        f = self.teams_view = ttk.Frame(self.content)
        bar = ttk.Frame(f)
        bar.pack(fill="x", pady=(0, 6))
        ttk.Label(bar, text="Find a person").pack(side="left")
        self.find_var = tk.StringVar()
        e = ttk.Entry(bar, textvariable=self.find_var, width=28)
        e.pack(side="left", padx=6)
        e.bind("<KeyRelease>", lambda ev: self._find_person())
        self.find_result = ttk.Label(bar, text="", foreground="#595959")
        self.find_result.pack(side="left", padx=6)

        panes = ttk.Panedwindow(f, orient="horizontal")
        panes.pack(fill="both", expand=True)
        lf = ttk.Frame(panes)
        self.teams_tree = ttk.Treeview(lf, columns=("team", "primary", "count"), show="headings",
                                       selectmode="extended")
        for c, w, t in [("team", 230, "Team"), ("primary", 200, "Primary member"), ("count", 80, "Members")]:
            self.teams_tree.heading(c, text=t)
            self.teams_tree.column(c, width=w, anchor="w")
        self.teams_tree.pack(fill="both", expand=True)
        self.teams_tree.bind("<<TreeviewSelect>>", lambda e: self._team_selected())
        panes.add(lf, weight=3)
        rf = ttk.Frame(panes, padding=(8, 0, 0, 0))
        self.members_title = ttk.Label(rf, text="Members", style="Head.TLabel")
        self.members_title.pack(anchor="w")
        self.members = tk.Listbox(rf, font=("Segoe UI", 10), activestyle="none",
                                  selectbackground=ORANGE, borderwidth=1, highlightthickness=0)
        self.members.pack(fill="both", expand=True, pady=(4, 0))
        panes.add(rf, weight=2)

    def _show(self, view):
        for v in (self.text_view, self.docs_view, self.teams_view):
            v.pack_forget()
        view.pack(fill="both", expand=True)

    def _refresh_action_state(self):
        if hasattr(self, "ov_export_btn"):
            self.ov_export_btn.state(["!disabled"] if getattr(self, "ov_results", None) and not self.busy
                                     else ["disabled"])
        on = self.current_tab is not None
        for b in (self.b_shot, self.b_xls):
            b.state(["!disabled"] if on else ["disabled"])
        self.b_all.state(["!disabled"] if self.order else ["disabled"])

    # ----- folders / settings
    def _store_settings(self):
        self.settings.update(screenshots=self.shot_dir.get(), exports=self.export_dir.get(),
                             full_page=self.full_page.get(), auto_shot=self.auto_shot.get(),
                             per_order_folder=self.per_order.get())
        save_settings(self.settings)

    def _browse(self, var):
        d = filedialog.askdirectory(initialdir=var.get() or str(HERE), title="Choose folder")
        if d:
            var.set(d)
            self._store_settings()

    def _open_folder(self, path):
        Path(path).mkdir(parents=True, exist_ok=True)
        os.startfile(path)

    def _ctx(self):
        """Snapshot of the window's settings, taken on the UI thread for a worker job."""
        self._store_settings()
        shots = Path(self.shot_dir.get())
        exports = Path(self.export_dir.get())
        if self.per_order.get() and self.order:
            shots = shots / self.order
        return {"order": self.order,
                "shots": shots, "full_page": self.full_page.get(),
                "auto_shot": self.auto_shot.get(),
                "workbook": exports / f"{self.order}.xlsx",
                "docs_dest": exports / (self.order or "") / "documents"}

    # ----- actions
    def open_order(self):
        order = self.order_var.get().strip()
        if not re.fullmatch(r"\d+-\d+", order):
            messagebox.showwarning(APP_NAME, "Type an order number like 10-1771012.")
            return
        if self.busy:
            return
        self._store_settings()
        w = self.worker

        def job():
            w.ensure_browser()
            self.log(f"Searching order {order}...")
            oo.open_orders_tab(w.driver, w.wait, discard_changes=True)
            oo.untick_my_orders(w.driver)
            row = oo.search_order(w.driver, w.wait, order)
            oo.open_result(w.driver, w.wait, row, order)
            banner = gx.extract_tab(w.driver)["banner"]
            return [t for t, _ in oo.list_tabs(w.driver)], banner

        def done(result):
            titles, banner = result
            self.order = order
            self.tab_titles = titles
            self.tab_list.delete(0, "end")
            for t in titles:
                self.tab_list.insert("end", "  " + t)
            self.order_label.configure(text=banner.replace("  |  ", "   ·   "))
            self.log(f"Opened {order}: {banner}")
            self.current_tab = None
            self._select_tab_by_name("Information")

        w.submit(f"Opening {order}", job, done, retry=True)

    def _ensure_order(self, order, tab=None):
        """Worker thread: healthy GOLD session with this order (and tab) open. After a
        reconnect the new session starts on GOLD's home page, so reopen the order."""
        w = self.worker
        w.ensure_browser()
        if not oo._on_order_page(w.driver, order):
            self.log(f"Reopening {order}...")
            oo.open_orders_tab(w.driver, w.wait, discard_changes=True)
            oo.untick_my_orders(w.driver)
            oo.open_result(w.driver, w.wait, oo.search_order(w.driver, w.wait, order), order)
            if tab:
                oo.open_tab(w.driver, w.wait, tab)

    def _select_tab_by_name(self, name):
        for i, t in enumerate(self.tab_titles):
            if t.startswith(name):
                self.tab_list.selection_clear(0, "end")
                self.tab_list.selection_set(i)
                self._tab_clicked()
                return

    def _tab_clicked(self):
        sel = self.tab_list.curselection()
        if not sel or not self.order:
            return
        title = self.tab_titles[sel[0]]
        ctx = self._ctx()
        if self.busy:
            return  # a job is running; ignore clicks
        w = self.worker
        order = self.order

        def job():
            self._ensure_order(order)
            name = oo.open_tab(w.driver, w.wait, title)
            if name == "Documents":
                payload = oo.read_documents(w.driver)
            elif name == "Teams":
                payload = oo.read_teams(w.driver)
            else:
                payload = gx.extract_tab(w.driver)
                if not payload["fields"] and not payload["grids"]:
                    payload["text"] = oo.content_text(w.driver)
            shot =self._take_screenshot(name, ctx) if ctx["auto_shot"] else None
            return name, payload, shot

        def done(result):
            name, payload, shot = result
            self.current_tab = name
            self.tab_title.configure(text=f"{name}   —   {self.order}")
            if name == "Documents":
                self._fill_docs(payload)
                self._show(self.docs_view)
            elif name == "Teams":
                self._fill_teams(payload)
                self._show(self.teams_view)
            else:
                self._fill_text(payload)
                self._show(self.text_view)
            if shot:
                self.log(f"Screenshot saved: {shot}")
            self._refresh_action_state()

        w.submit(f"Opening {title}", job, done, retry=True)

    def _take_screenshot(self, tab, ctx):
        """Runs on the worker thread. Saves <Tab>_<n>.png with the next free n."""
        folder = ctx["shots"]
        folder.mkdir(parents=True, exist_ok=True)
        base = safe_name(tab)
        n = 1
        while (folder / f"{base}_{n}.png").exists():
            n += 1
        path = folder / f"{base}_{n}.png"
        d = self.worker.driver
        if ctx["full_page"] and hasattr(d, "get_full_page_screenshot_as_file"):
            d.get_full_page_screenshot_as_file(str(path))
        else:
            d.save_screenshot(str(path))
        return path

    def screenshot(self):
        tab, ctx, order = self.current_tab, self._ctx(), self.order
        self.worker.submit("Taking screenshot",
                           lambda: (self._ensure_order(order, tab), self._take_screenshot(tab, ctx))[1],
                           lambda p: self.log(f"Screenshot saved: {p}"), retry=True)

    def _export_current(self, tab, ctx, docs):
        """Runs on the worker thread: extract the tab shown in GOLD and write its sheet."""
        d = self.worker.driver
        data = gx.extract_tab(d)
        header = gx.header_lines(ctx["order"], data["banner"])
        if tab == "Teams":
            teams = oo.read_teams(d)
            blocks = [("Teams", ["Team", "Primary member", "Members"],
                       [[t, v["primary"] or "", len(v["members"])] for t, v in teams.items()]),
                      ("Members", ["Team", "Member", "Primary"],
                       [[t, m, "Yes" if m == v["primary"] else ""]
                        for t, v in teams.items() for m in v["members"]])]
        elif tab == "Documents":
            saved = {doc["key"]: doc.get("saved", "") for doc in docs}
            blocks = [("Documents", ["#", "Document", "Last modified", "Type", "SRF relating",
                                     "Downloaded to"],
                       [[i, doc["title"], doc["modified"], doc["type"], doc["srf"],
                         saved.get(doc["key"], "")]
                        for i, doc in enumerate(oo.read_documents(d), 1)])]
        else:
            blocks = gx.tab_blocks(data)
        if not blocks:
            blocks = [("Content", ["Text"], [[line] for line in oo.content_text(d).splitlines()])]
        try:
            return gx.write_sheet(ctx["workbook"], tab, header, blocks)
        except PermissionError:
            raise RuntimeError(f"{ctx['workbook'].name} is open in Excel. Close it and try again.")

    def export_tab(self):
        tab, ctx, docs, order = self.current_tab, self._ctx(), list(self.docs), self.order
        self.worker.submit(f"Exporting {tab}",
                           lambda: (self._ensure_order(order, tab), self._export_current(tab, ctx, docs))[1],
                           lambda p: self._exported(p, [tab]), retry=True)

    def export_all(self):
        titles, ctx, docs, order = list(self.tab_titles), self._ctx(), list(self.docs), self.order
        w = self.worker

        def job():
            self._ensure_order(order)
            done_tabs = []
            for t in titles:
                name = oo.open_tab(w.driver, w.wait, t)
                self.log(f"  exporting {name}...")
                try:
                    self._export_current(name, ctx, docs)
                    done_tabs.append(name)
                except RuntimeError:
                    raise  # Excel file open: stop
                except Exception as e:
                    self.log(f"  {name}: skipped ({e})")
            if self.current_tab:  # go back to the tab the user was on
                oo.open_tab(w.driver, w.wait, self.current_tab)
            return ctx["workbook"], done_tabs

        w.submit("Exporting all tabs", job, lambda r: self._exported(*r), retry=True)

    def _exported(self, path, tabs):
        self.log(f"Excel updated: {path}  (sheets: {', '.join(tabs)})")
        if messagebox.askyesno(APP_NAME, f"Saved to\n{path}\n\nOpen it now?"):
            os.startfile(path)

    def download(self, all_docs=False):
        items = self.docs_tree.get_children() if all_docs else self.docs_tree.selection()
        if not items:
            messagebox.showinfo(APP_NAME, "Select one or more documents first.")
            return
        picks = [self.docs[int(i)] for i in items]
        dest = self._ctx()["docs_dest"]
        w = self.worker
        order = self.order

        def job():
            results = []
            self._ensure_order(order, "Documents")
            for doc in picks:
                self.log(f"Downloading {doc['title']}...")
                try:
                    saved, _ = oo.download_document(w.driver, w.wait, doc, dest)
                except Exception as e:
                    saved = []
                    self.log(f"  failed: {str(e).splitlines()[0] if str(e) else type(e).__name__}")
                if saved:
                    doc["saved"] = saved[0]
                    self.log(f"  saved {saved[0]}")
                results.append(doc)
                self._ensure_order(order, "Documents")  # reconnect if the connection dropped
                oo.open_tab(w.driver, w.wait, "Documents")
            return results

        def done(_):
            self._fill_docs(self.docs, keep_saved=True)
            ok = sum(1 for d in picks if d.get("saved"))
            self.log(f"{ok} of {len(picks)} documents downloaded to {dest}")

        w.submit(f"Downloading {len(picks)} document(s)", job, done)

    # ----- fill views
    def _fill_text(self, data):
        """Show extracted data: sections of Field / Value, then grids as aligned tables."""
        t = self.text
        t.configure(state="normal")
        t.delete("1.0", "end")
        if data.get("text"):
            t.insert("end", data["text"])
        section = None
        for sec, field, value in data["fields"]:
            if sec != section:
                section = sec
                if sec:
                    t.insert("end", ("\n" if t.index("end-1c") != "1.0" else "") + sec + "\n", "section")
            if field:
                t.insert("end", f"  {field}", "label")
                t.insert("end", f"\t{value}\n")
            else:
                t.insert("end", f"  {value}\n")
        for g in data["grids"]:
            t.insert("end", "\n" + (g.get("title") or "Table") + f"  ({len(g['rows'])} rows)\n", "section")
            cols = g["columns"]
            widths = [min(max([len(c)] + [len(str(r[i])) for r in g["rows"]]), 34)
                      for i, c in enumerate(cols)]
            fmt = lambda row: "  ".join(str(v)[:w].ljust(w) for v, w in zip(row, widths)).rstrip()
            t.insert("end", fmt(cols) + "\n", ("mono", "label"))
            t.insert("end", "  ".join("─" * w for w in widths) + "\n", "mono")
            for r in g["rows"]:
                t.insert("end", fmt(r) + "\n", "mono")
        t.configure(state="disabled")

    def _fill_docs(self, docs, keep_saved=False):
        if not keep_saved:
            old = {d["key"]: d.get("saved") for d in self.docs}
            for d in docs:
                if old.get(d["key"]):
                    d["saved"] = old[d["key"]]
        self.docs = docs
        self.docs_tree.delete(*self.docs_tree.get_children())
        for i, d in enumerate(docs):
            saved = Path(d["saved"]).name if d.get("saved") else ""
            self.docs_tree.insert("", "end", iid=str(i),
                                  values=(i + 1, d["title"], d["modified"], d["type"], saved))

    def _fill_teams(self, teams):
        self.teams = teams
        self.teams_tree.delete(*self.teams_tree.get_children())
        for name, t in teams.items():
            self.teams_tree.insert("", "end", iid=name,
                                   values=(name, t["primary"] or "—", len(t["members"])))
        self.members.delete(0, "end")
        self.members_title.configure(text="Members")
        self._find_person()

    def _team_selected(self):
        sel = self.teams_tree.selection()
        if not sel:
            return
        t = self.teams[sel[0]]
        self.members_title.configure(text=f"{sel[0]} — {len(t['members'])} members")
        self.members.delete(0, "end")
        for m in t["members"]:
            self.members.insert("end", ("★ " if m == t["primary"] else "    ") + m)

    def _find_person(self):
        q = self.find_var.get().strip().lower()
        if not q:
            self.find_result.configure(text="")
            return
        hits = [(name, m) for name, t in self.teams.items() for m in t["members"] if q in m.lower()]
        teams_hit = sorted({name for name, _ in hits})
        people = sorted({m for _, m in hits})
        self.find_result.configure(
            text=(f"{', '.join(people[:3])}{'…' if len(people) > 3 else ''} → in "
                  f"{len(teams_hit)} team(s): {', '.join(teams_hit)}") if hits else "No match")
        self.teams_tree.selection_remove(self.teams_tree.selection())
        for name in teams_hit:
            self.teams_tree.selection_add(name)

    def _on_close(self):
        self._store_settings()
        self.worker.close()
        self.destroy()


def selftest(order):
    """GOLD Express.exe --selftest 10-1771012 : open Firefox + GOLD, open the order,
    read its tabs, export one sheet, and write a report. For troubleshooting."""
    report = HERE / "selftest_report.txt"
    lines = []
    d = None
    try:
        d = start_firefox(headless=True)
        lines.append("Firefox started (background)")
        w = WebDriverWait(d, 60)
        d.get(GOLD_URL)
        if not wait_for_gold(d):
            raise RuntimeError("GOLD did not load (SSO?)")
        lines.append("GOLD loaded")
        oo.open_orders_tab(d, w)
        oo.untick_my_orders(d)
        oo.open_result(d, w, oo.search_order(d, w, order), order)
        tabs = [t for t, _ in oo.list_tabs(d)]
        lines.append(f"Order {order} opened, tabs: {', '.join(tabs)}")
        oo.open_tab(d, w, "Milestones")
        data = gx.extract_tab(d)
        path = gx.write_sheet(HERE / "output" / f"selftest_{order}.xlsx", "Milestones",
                              gx.header_lines(order, data["banner"]), gx.tab_blocks(data))
        lines.append(f"Excel written: {path}")
        lines.append("RESULT: OK")
    except Exception:
        lines.append("RESULT: FAILED\n" + traceback.format_exc())
    finally:
        if d is not None:
            d.quit()
        report.write_text("\n".join(lines), encoding="utf-8")


if __name__ == "__main__":
    import sys
    HERE.mkdir(parents=True, exist_ok=True)
    if len(sys.argv) >= 3 and sys.argv[1] == "--selftest":
        selftest(sys.argv[2])
    else:
        # One GOLD Express at a time: two copies can't share the Firefox profile.
        import ctypes
        kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
        mutex = kernel32.CreateMutexW(None, False, "Local\\GOLDExpressSingleInstance")
        if ctypes.get_last_error() == 183:  # ERROR_ALREADY_EXISTS
            r = tk.Tk(); r.withdraw()
            messagebox.showinfo(APP_NAME, f"{APP_NAME} is already open.\n\n"
                                          "Look for it on the taskbar.")
            sys.exit(0)
        App().mainloop()
