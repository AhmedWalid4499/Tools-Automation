# GOLD Express - Developer Guide

The complete guide to how GOLD Express works and how to change it safely. It is written for a developer
who has never seen the code, and for Claude (see also [`CLAUDE.md`](CLAUDE.md), the short version that Claude
Code reads automatically).

> **How to read this guide.** Start with [1. What the app is](#1-what-the-app-is),
> [2. Quick start](#2-quick-start) and [5. The golden rules](#5-the-golden-rules). Then jump to the part you
> are changing: every feature has its own section, and [16. Recipes](#16-recipes-how-to-make-common-changes)
> gives step-by-step instructions for the usual changes.
>
> **About references.** Code is referred to as `file.py` + function name, for example
> `gold_app.py` > `App._bulk_run`. Find it with your editor's search or `grep -n "def _bulk_run" gold_app.py`.
> Line numbers are avoided on purpose: they move with every change.

---

## Contents

1. [What the app is](#1-what-the-app-is)
2. [Quick start](#2-quick-start)
3. [Repository map](#3-repository-map)
4. [Architecture](#4-architecture)
5. [The golden rules](#5-the-golden-rules)
6. [Where data lives, and the settings](#6-where-data-lives-and-the-settings)
7. [Threads: the Worker](#7-threads-the-worker)
8. [The window, pages and shared helpers](#8-the-window-pages-and-shared-helpers)
9. [The look: `gold_ui`](#9-the-look-gold_ui)
10. [Driving GOLD with Firefox](#10-driving-gold-with-firefox)
11. [The features, one by one](#11-the-features-one-by-one)
12. [Business rules reference](#12-business-rules-reference)
13. [Excel exports](#13-excel-exports)
14. [Updates, build, release and the website](#14-updates-build-release-and-the-website)
15. [Testing](#15-testing)
16. [Recipes: how to make common changes](#16-recipes-how-to-make-common-changes)
17. [Gotchas](#17-gotchas)
18. [Known issues and loose ends](#18-known-issues-and-loose-ends)
19. [Glossary](#19-glossary)

---

## 1. What the app is

**GOLD Express** is a Windows desktop app for Orange Business people who work in **GOLD** (Global Order
Lifecycle Delivery), the order-management web application. It drives GOLD in a hidden Firefox window, so routine
order work takes a few clicks instead of many, and it adds dashboards GOLD does not have.

- **Language and libraries:** Python 3.12, tkinter/ttk for the window, Selenium + Firefox to drive GOLD,
  openpyxl for Excel, Pillow for every rounded or gradient picture, the Anthropic SDK for the AI chat.
- **Distribution:** a Windows installer (Inno Setup) published on GitHub Releases; installed copies update
  themselves.
- **Author:** Ahmed El-Bourgy. Copyright © 2026 Ahmed El-Bourgy. All rights reserved.

| Page (side menu) | What it does | Reads or writes GOLD |
|---|---|---|
| **My Orders** | Your orders in GOLD ("My orders only"): counters, list, and a clickable Dashboard. Finds each order's RTDD, and sends overdue orders to Revised Target Date. | Reads |
| **Order Assignment** | Which DPM has which open APM order, from the APM Open Orders sheet on SharePoint. | Reads (SharePoint) |
| **DPM dashboard** | RTDD, revenue and workload per DPM and manager: clickable charts, a Scorecard that opens level by level, and Detailed orders due. | Reads (SharePoint) |
| **Overview** | Key facts of one or more orders, Red/Amber/Green delivery and 120-day lead-time status, a Tracker, Excel. | Reads |
| **Order explorer** | Open an order, browse its tabs, screenshots, documents, teams, export tabs to Excel. | Reads |
| **GOLD bot** (Ask GOLD) | AI chat (Claude) that answers questions about orders, using read-only GOLD tools. | Reads |
| **Revised Target Date** | Adds the "Revised Target Date" milestone to many orders at once. | **Writes** |
| **Bulk assignment** | Makes a DPM the primary STM of many orders at once. | **Writes** |
| **Org Chart** | Find anyone at Orange Business, and the team of an order. | Reads (Org Chart) |
| **DPM names** | The DPM list, synced weekly from the Org Chart. | Reads |

**Only two pages ever change GOLD**: Revised Target Date and Bulk assignment, and only after the user presses
**Run update** and confirms. Both have a **Test only** mode that fills the form and cancels.

---

## 2. Quick start

### Set up

```bash
pip install selenium openpyxl pillow anthropic pyinstaller
```

You also need Windows, Mozilla Firefox, and GOLD access with an Orange account (sign-in is automatic through
SSO). To build the installer you need Inno Setup 6 (`winget install JRSoftware.InnoSetup --scope user`), and
to publish you need the GitHub CLI (`gh auth login`).

### Run from source

```bash
python gold_app.py
```

Or double-click `GOLD Express.bat` (runs it with `pythonw`, no console). From source, the app keeps its data
in the repository folder itself (see [6](#6-where-data-lives-and-the-settings)).

### Check that nothing is broken (no GOLD needed)

```bash
python gold_app.py --ui-selftest
```

It opens every page and writes `ui_selftest_report.txt` (`RESULT: OK - N pages shown`) and `ui_selftest.png`.
More tests in [15. Testing](#15-testing).

### Release a new version

1. Bump `__version__` in `version.py`.
2. Add a `## <version>` section at the top of `CHANGELOG.md` (it becomes the release notes).
3. Build and test:
   ```bash
   python build_release.py
   "%TEMP%\gold_express_build\dist\GOLD Express\GOLD Express.exe" --ui-selftest
   ```
4. Commit and push (subject: `<what changed> (<version>)`).
5. Publish: `python build_release.py --publish`.

Full details in [14. Updates, build, release and the website](#14-updates-build-release-and-the-website).

---

## 3. Repository map

| File | Alias in `gold_app.py` | What it is |
|---|---|---|
| `gold_app.py` | | The app: the `App` window (every page), the `Worker` thread, self-tests and the entry point. About 5,800 lines. |
| `gold_ui.py` | `gui` | Look and feel: themes, rounded tiles, stat cards, charts, side menu, animations, rounded ttk styles. |
| `gold_board.py` | `gb` | Clickable dashboards: charts that filter each other (`Board`). |
| `open_gold.py` | | Paths (`HERE`, `BUNDLE_DIR`, profiles), starting Firefox, waiting for GOLD's SSO sign-in. |
| `open_order.py` | `oo` | Order search page, searching, opening an order and its tabs, Documents and Teams. |
| `gold_extract.py` | `gx` | Turns a GOLD tab into tables and fields; writes styled Excel sheets. |
| `gold_grid.py` | (`EditGrid`) | Excel-like editable table used by the bulk pages. |
| `gold_myorders.py` | `gmo` | Reads GOLD's "My orders only" list (all pages); adds RTDD-based dates; counts. |
| `gold_overview.py` | `go` | Reads one order for Overview; RAG and 120-day lead-time rules; Overview Excel. |
| `gold_tracker.py` | `gtr` | Tracker columns, comments, tracker Excel. |
| `gold_milestones.py` | `gm` | Revised Target Date milestones: add (writes) and read. Date parsing, reasons. |
| `gold_teams.py` | `gt` | Making a DPM the primary STM (writes); GOLD user lookup (reads). |
| `gold_assignments.py` | `gas` | APM Open Orders sheet: SharePoint fetch, read, classify; RTDD rules; KPIs; chart dimensions. |
| `gold_assign_dashboard.py` | `gad` (imported locally) | Excel exports of Order Assignment and the DPM dashboard. |
| `gold_names.py` | `gn` | DPM names list, name matching, Org Chart helpers, departments and teams. |
| `gold_orgchart.py` | `goc` | Org Chart client (runs inside a signed-in browser tab), with a cache. |
| `gold_ai.py` | `gai` | GOLD bot: getting the AI key, Claude conversation, read-only GOLD tools. |
| `gold_markdown.py` | `gmd` | Shows Claude's Markdown answers (tables included) in a tk `Text`. |
| `gold_notify.py` | `gnotify` | Windows toast notifications. |
| `gold_update.py` | `gu` | Finds, downloads and installs new releases. |
| `version.py` | | `__version__`, author and copyright: the single source of the version. |
| `build_release.py` | | Builds the app (PyInstaller) and installer (Inno Setup), optionally publishes the release. |
| `build_installer.bat`, `GOLD Express.bat` | | Build with the standard Python; run from source. |
| `installer/` | | Inno Setup script `gold_express.iss` and the "Before you install" page. |
| `assets/` | | Logo and bot pictures (several sizes). Made by `tools/make_logo.py` and `tools/make_bot.py`. |
| `docs/` | | The public download website (GitHub Pages): `index.html` and its pictures. |
| `CHANGELOG.md` | | What's new, one section per version; the release notes. |

**Not in the repository** (see `.gitignore`), and must never be: the AI key (`ai_key.bin`, `*.key`), user
settings and lists (`gold_app_settings.json`, `dpm_names.json`), downloaded sheets and exports (`output/`,
`apm_open_orders.xlsx*`), the built-in DPM list (`data/`), logs, chats, caches, self-test reports and build
output (`release/`, `dist/`, `build/`).

---

## 4. Architecture

```
            ┌───────────────────────── GOLD Express process ─────────────────────────┐
            │                                                                        │
  user ───▶ │  UI thread (tkinter)            Worker thread              Firefox     │
            │  ─────────────────────          ─────────────────          (Selenium)  │
            │  App: pages, charts, tables     one job at a time  ──────▶ hidden      │
            │      │   ▲                       ensure_browser()           window:    │
            │      │   │ self.ui(fn)            fn() ...                  GOLD,       │
            │      │   └──────────────────────  done(result) ◀─┐         SharePoint,  │
            │      └── worker.submit(label, fn, done) ─────────┘         Org Chart    │
            │                                                                        │
            │  Data folder (HERE): settings, DPM list, sheet copy, caches, exports   │
            └────────────────────────────────────────────────────────────────────────┘
                       │                                        │
                 GitHub Releases (updates)              Anthropic API (GOLD bot only)
```

- **One window, one UI thread.** Everything visible is built by `App` in `gold_app.py`. Pages are plain
  `tk.Frame`s shown by a side menu (`gui.SideNav`).
- **One worker thread owns Firefox.** Every GOLD action is a *job*: a function run on the worker thread, one
  at a time, followed by a `done` callback on the UI thread. See [7](#7-threads-the-worker).
- **Everything goes through the user's own sign-in.** GOLD, SharePoint and the Org Chart are opened in the
  app's Firefox, with the user's SSO session. The app never stores passwords.
- **Data is local.** Settings, lists, the latest APM sheet, caches and exports are files in the data folder
  (`HERE`).

---

## 5. The golden rules

These protect users, their data and GOLD. Do not break them.

1. **Only Revised Target Date and Bulk assignment write to GOLD**, and only after **Run update** and a
   confirmation. Everything else must only read. A new feature that writes needs the same safeguards: a
   **Test only** mode, a confirmation, a check after saving, and no automatic retry
   (see [11.5](#115-revised-target-date) and [16.5](#165-add-a-new-bulk-action)).
2. **Never touch a widget from the worker thread.** Use `self.ui(fn)` or `self.log(msg)`
   ([7](#7-threads-the-worker)).
3. **Never retry a job that saves.** `retry=True` is only for read-only jobs.
4. **The AI key is never in the code, the repository, the installer, logs or messages.** Never print it or
   read it in a tool. It is fetched at run time with the user's sign-in and kept encrypted for that Windows
   user ([11.9](#119-gold-bot-ask-gold)).
5. **Nothing from the AI is kept on the AI's side.** No prompt caching, no server-side storage. Chats are
   saved only if the user ticks **Save chats**, and then only on that PC, outside OneDrive.
6. **No private data in the repository or the installer.** Both are public. The DPM names list, customer data,
   order data, settings and keys stay out (`.gitignore`). The installer does not bundle the DPM list.
7. **Never show the GitHub address in the app's messages or on the website.** Users see the download page
   (`gold_update.DOWNLOAD_PAGE`); the website starts downloads from a click handler so no address shows.
8. **DPM departments are APM departments only** (APM Europe, APM APAC, APM AME), never CPM.
9. **Publishing a release is the owner's decision.** Build and test freely; publish only when asked.
10. **Use theme tokens, never hard-coded colours**, so the three looks keep working ([9](#9-the-look-gold_ui)).

---

## 6. Where data lives, and the settings

### The data folder `HERE`

Defined in `open_gold.py`:

```python
HERE = Path.home() / "Documents" / APP_NAME if FROZEN else Path(__file__).parent
```

- **Installed app:** `Documents\GOLD Express` (on the first run it copies settings from the old
  `Documents\GOLD Assistant`).
- **From source:** the repository folder.

| File (in `HERE` unless stated) | Constant | What |
|---|---|---|
| `gold_app_settings.json` | `SETTINGS_FILE` | The settings (below). |
| `dpm_names.json` | `gold_names.NAMES_FILE` | The DPM list. |
| `ai_key.bin` | `AI_KEY_CACHE` | The AI key, encrypted with Windows DPAPI for this user. |
| `orgchart_cache.json` | `OC_CACHE` | Org Chart lookups, kept 7 days. |
| `my_orders_snapshot.json` | `MY_SNAPSHOT` | Last My Orders read, to notice changes. |
| `my_rtdd.json` | `MY_RTDD_FILE` | RTDDs read from GOLD for My Orders. |
| `apm_open_orders.xlsx` | `OA_FILE` | The latest APM Open Orders sheet (replaced on every refresh). |
| `tracker_comments.json` | `TRACKER_COMMENTS` | Overview > Tracker comments. |
| `output\` | `open_gold.OUT_DIR` | Screenshots, exports, downloads (folders can be changed in Settings). |
| `gold_app_error.log` | | Tracebacks of errors. |
| `%LOCALAPPDATA%\GOLD Express\chats\` | `CHATS_DIR` | Saved GOLD bot chats (only if the user ticks Save chats). Deliberately outside OneDrive. |
| `~\.gold-automation\firefox-profile` | `open_gold.PROFILE_DIR` | Firefox profile (override with `GOLD_PROFILE_DIR`). Outside OneDrive. |
| `~\.gold-automation\helper-sessions\` | `HELPER_PROFILES_DIR` | Extra headless sessions for Overview. |

### Settings keys

Settings live in `self.settings` (a dict) and are saved with `save_settings(self.settings)`. Defaults are in
`load_settings()`; the Settings window copies its Tk variables back with `_store_settings()`.

| Key | Meaning |
|---|---|
| `screenshots`, `exports` | Output folders. |
| `full_page`, `auto_shot`, `per_order_folder` | Screenshot options. |
| `show_browser` | Show the Firefox window (changing it restarts the session). |
| `parallel_sessions` | Overview may read several orders side by side. |
| `ai_key_file` | An AI key file chosen in Settings (optional). |
| `notify_on`, `notify_orders`, `notify_every`, `notify_digest`, `notify_updates`, `notify_tasks` | Notifications. |
| `notified_version`, `digest_date` | Bookkeeping: last version announced, last daily digest. |
| `theme`, `theme_v3` | Look: `neo` (Futuristic), `light`, `dark`. `theme` counts only when `theme_v3` is set. |
| `save_chats`, `chat_privacy` | Save GOLD bot chats on this PC (off by default). |
| `bot_speed` | `fast` (default) or `thorough` for the GOLD bot. |
| `oa_url` | Override of the APM Open Orders sheet link. |
| `oa_checked`, `oa_version`, `oa_source`, `oa_modified` | When the sheet was last checked, its ETag, link and SharePoint time. |
| `kpi_filters` | DPM dashboard: remembered Region, Manager and DPM. |
| `tracker_view` | Tracker view (management or customer). |
| `assign_teams` | Bulk assignment: which DPM teams are offered. |
| `dpm_departments` | Org Chart departments whose people are DPMs (APMs only). |
| `dpm_synced`, `dpm_synced_departments`, `dpm_managers` | Weekly DPM list sync bookkeeping. |

**To add a setting:** give it a default in `load_settings()`, read it with `self.settings.get("key", default)`,
save with `save_settings(self.settings)`. If it is in the Settings window, add a Tk variable and copy it back in
`_store_settings()`.

---

## 7. Threads: the Worker

`gold_app.py` > `class Worker`. One daemon thread runs GOLD jobs one at a time and owns the Selenium driver.

```python
def submit(self, label, fn, done=None, retry=False):
    """retry=True for read-only jobs: if they fail because of the connection, reconnect to
    GOLD (fresh session) and run them once more. Jobs that save in GOLD are never retried."""
```

- `label` shows in the status pill ("Reading my orders").
- `fn()` runs **on the worker thread**. It must start with `w.ensure_browser()`.
- `done(result)` runs later **on the UI thread**. The app is already idle by then (`set_idle` runs first).
- On an exception, `job_failed` logs it, writes `gold_app_error.log` and shows an error box.
- `submit` itself must be called from the UI thread (it updates the busy state).

### The pattern to copy

```python
def _x_load(self):
    if self.busy:
        return
    w = self.worker

    def job():                                   # worker thread: GOLD only, no widgets
        w.ensure_browser()
        self.log("Reading something from GOLD...")   # log() is safe from any thread
        return some_module.read_something(w.driver, w.wait)

    def done(result):                            # UI thread: widgets are fine here
        self.x_data = result
        self._x_render()

    w.submit("Reading something", job, done, retry=True)   # retry only because it only reads
```

### What else to know

- **`ensure_browser()`** reuses a healthy session, repairs it by reloading GOLD, or starts a new Firefox
  (headless unless `show_browser`). If a headless sign-in fails, it restarts Firefox visible so the user can
  sign in.
- **`self.ui(fn)`** queues `fn` for the UI thread (emptied every 100 ms by `_pump`). Each call is isolated, so
  one error cannot leave the app stuck as busy.
- **`self.busy`** is set while a job runs. Buttons created with `self._btn(...)` are disabled while busy; plain
  `ttk.Button`s are not. Most actions start with `if self.busy: return`.
- **`self._when_idle(what, then)`** waits for the current job (used for closing, restarting and updating).
- **Connection loss:** a watcher thread checks the network every 20 s, shows "Offline - waiting for network",
  and reconnects when it is back. Any error raised while offline counts as a connection error.
- **Helper sessions:** `worker.helper_drivers(n)` starts extra headless Firefox sessions with their own
  profiles, for read-only parallel work (Overview).
- **Plain threads** are used for work that does not need Firefox (Excel exports, reading the sheet file,
  update downloads). They also report back with `self.ui(...)`.

---

## 8. The window, pages and shared helpers

### Start-up (`App.__init__`, in order)

1. Windows app ID for notifications, window, icon, DPI-scaled size.
2. `load_settings()`, `move_old_chats()`, `gn.load()` (DPM list), the UI queue, `Worker(self)`.
3. `_style()` (ttk styles, then `gui.style_rounded`), `_build()` (every page).
4. Error handler, close handler, `_pump` loop, connection watcher.
5. Quiet update check after 4 s, GOLD pre-warm after 300 ms, My Orders change watch every 60 s.

The entry point (`if __name__ == "__main__":`) makes the process DPI-aware, handles the self-test flags and
`--after-pid` (used by restarts), enforces a single instance (named mutex
`Local\GOLDExpressSingleInstance`), then runs `App().mainloop()`.

### Pages and the side menu

`App._build` creates each page as a frame and registers it with `nav.add(frame, title, icon, subtitle)`
(`gui.SideNav`, which behaves like the parts of `ttk.Notebook` the app uses):

```python
def page(pad=True):
    return tk.Frame(content_host, background=BG)

my, overview, explorer, ask = page(), page(), page(), page(False)
...
nav.section("Orders")
nav.add(my, "My Orders", "\uE80F", "Your orders in GOLD (My orders only) at a glance")
nav.add(kpi, "DPM dashboard", "\uF246", "RTDD, revenue and workload for DPMs and managers - ...")
...
self._build_my_tab(my)
self._build_kpi_tab(kpi)
```

- Switch page from code with `self.notebook.select(self.some_frame)`.
- **`_page_changed(title, subtitle)`** runs whenever a page is shown. It loads data lazily by **page title**:
  the DPM list sync for "DPM names", "Bulk assignment", "Order Assignment" and "DPM dashboard", and the APM
  sheet for "Order Assignment" and "DPM dashboard". Renaming a page title means updating these checks.

### Helpers every page uses

| Helper | What it does |
|---|---|
| `self._tile(parent, pad=10, **pack)` | A rounded tile (`gui.Tile`). Put widgets in `.body`. Packed when pack options are given. |
| `self._tile_head(parent, title, icon)` | The icon + bold title row of a tile. Returns the row, so buttons can go on its right. |
| `self._btn(parent, text, cmd, style=None)` | A `ttk.Button` that is disabled while the app is busy. Styles: `"Accent.TButton"`, `"Small.TButton"`. |
| `self._board_area(parent)` | A scrolling 3-column grid for chart tiles. Returns `(frame, tile_height)`. |
| `self._board_tile(f, height, row, col, title, icon)` | A chart tile at (row, col) of a `_board_area`; returns its body. |
| `self.log(msg)` | Writes to the activity log and status line. Safe from any thread. |
| `self._notify(title, text, kind)` | A Windows notification, if the user allows that kind (`orders`, `digest`, `updates`, `tasks`). |
| `self._ctx()` | Snapshot of folder settings for a job (`workbook`, `shots`, `docs_dest`...). Exports are written next to `_ctx()["workbook"]`. |
| `self._dialog(title, width)` / `self._dialog_head(...)` | A small window in the app's style. |
| `self._orders_to_rtdd(orders)` | Puts order numbers in the Revised Target Date table and opens that page. |
| `self._my_open(order)` | Opens an order in the Order explorer. |

A tile with a title and a refresh button:

```python
t = self._tile(parent, fill="x")
head = self._tile_head(t.body, "My section", "\uE8A5")
self._btn(head, "↻  Refresh", lambda: self._x_load(), "Small.TButton").pack(side="right")
tk.Label(t.body, text="Hello", bg=CARD, fg=INK, font=(FONT, 10)).pack(anchor="w")
```

### Sizes on scaled screens

Sizes in the code are written for 100% Windows scaling and multiplied by the screen's scale:

```python
scale = self.winfo_fpixels("1i") / 96          # 1.0 at 100%, 1.5 at 150%
tree.column("name", width=int(140 * scale))
```

Fonts are given in points and scale by themselves. The process is made DPI-aware before the first window
(`gui.sharp_on_scaled_screens()`), so everything stays sharp.

---

## 9. The look: `gold_ui`

### Why everything is a picture

Tkinter draws only square shapes. Every rounded or gradient surface (tiles, cards, buttons, charts, the side
menu pill) is drawn with Pillow, usually 3-4 times larger and then shrunk for smooth edges, and shown on a
`tk.Canvas`. Each such widget redraws itself when its size changes (the `_Redraw` mixin: debounced `<Configure>`
→ `redraw(w, h)`).

### Themes

`gold_ui.THEMES` has three looks: `light`, `dark` and `neo` (shown as "Futuristic", the default). The chosen
theme's tokens become module constants at import (`gui.BG`, `gui.CARD`, `gui.AI_A`...), and `gold_app` copies
the common ones (`BG`, `CARD`, `INK`, `MUTED`, `ORANGE`, `GREEN`, `RED`...).

| Tokens | Use |
|---|---|
| `BG`, `CARD` | Page background, tile background. |
| `INK`, `MUTED`, `FAINT`, `SUB_INK` | Text: main, secondary, faint. |
| `LINE`, `TRACK`, `ZEBRA`, `HEAD_BG` | Lines, empty chart tracks, alternate table rows, table headings. |
| `ORANGE`, `ORANGE_DARK`, `ORANGE_SOFT`, `ACCENT2` | The accent (in Futuristic, "ORANGE" is violet). |
| `GREEN_FG/BG`, `AMBER_FG/BG`, `RED_FG/BG`, `GREY_FG/BG` | Status colours (Red/Amber/Green, no date). |
| `AI_A`, `AI_B`, `AI_SOFT` | The GOLD bot's violet and cyan. |

- The theme is read when the app starts (`_initial_theme()`), so **changing the theme needs a restart**;
  `_set_theme` offers one. For testing: `set GOLD_THEME=light` before starting.
- A widget's `bg` must match what is behind it (`bg=CARD` inside a tile, `bg=BG` on the page), or its corners
  show the wrong colour.

### Widgets

| Widget | Use | Key methods |
|---|---|---|
| `Tile(parent, radius=18, pad=10, bg=BG, fill=CARD, ...)` | Rounded tile with a shadow; content goes in `.body`. | |
| `StatCard(parent, caption, icon, palette, sub_lines=2, big_size=24, command=None)` | Colourful counter card. Palettes: `v_blue`, `v_green`, `v_orange`, `v_purple`, `v_teal`, `v_rose`... | `set(big, sub, palette, caption)` |
| `Donut(parent, size=None, thickness=0.2, on_click=None)` | Ring chart; clicking a slice calls `on_click(label)`. | `set(items, big, small, selected=None)` |
| `Bars(parent, on_click=None, rows=6)` | Horizontal bars; height fixed by `rows`. | `set(items, selected=None)` |
| `Progress(parent, height=10, colour=ORANGE)` | Progress bar. | `set(fraction)` |
| `Pill(parent, text, fg, fill, command=None)` | Rounded label or chip. | `set(text, fg, fill)` |
| `IconButton(parent, icon, command, tip="", size=38)` | Round icon button (top bar). | `set_icon`, `set_tip`, `set_highlight` |
| `ClickCard`, `Bubble`, `Tooltip(widget, text)` | Suggestion card, chat bubble, hover tip. | |
| `TableCopy(tree, on_copy=None, menu=True)` | Adds Excel-like cell selection and copying (Ctrl+C) to a `ttk.Treeview`. | `add_items(menu, row, col)`, `_cell_at(event)` |
| `SideNav(parent, host, on_change)` | The side menu. | `section`, `add`, `select`, `current` |
| `Bot`, `AIBanner`, `AIThinking` | The animated GOLD bot, its flowing header, the thinking dots. | `Bot.start(mode)`, `Bot.hop()` |

Chart items are always `(label, value, colour)`. Helpers: `rounded_image`, `gradient`, `mix(a, b, t)`,
`fit_text(text, font, width, lines)`.

A row of clickable stat cards (pattern used on every dashboard):

```python
cards = tk.Frame(f, background=BG)
cards.pack(fill="x", padx=6, pady=(0, 8))
self.x_cards = {}
for col, (key, caption, icon, palette) in enumerate((
        ("open", "Open orders", "\uE8A5", "v_blue"),
        ("late", "Overdue", "\uE7BA", "v_rose"))):
    card = gui.StatCard(cards, caption, icon, palette, sub_lines=1, big_size=15,
                        command=lambda k=key: self._x_card(k))
    card.grid(row=0, column=col, sticky="ew", padx=(0 if col == 0 else 12, 0))
    cards.columnconfigure(col, weight=1, uniform="xcards")
    self.x_cards[key] = card
# later: self.x_cards["open"].set("1,234", "€2.4M  ·  12 DPMs")
```

### Icons

Icons are characters of the **Segoe Fluent Icons** font (falling back to Segoe MDL2 Assets), drawn with
`font=(gui.ICONS, size)`. Some icons in the source are written as invisible "private use" characters; they look
like `""` in most editors and can be lost when code is copied through other tools. **Write new icons as escapes**
(`"\uE8A5"`), and never delete an "empty-looking" icon string. Look up codes in Microsoft's Segoe Fluent Icons
list.

### Animations

The bot, its banner and the thinking dots follow the **clock**, not a frame counter: each tick (every
`FRAME_MS = 15` ms) works out where the animation should be from `time.perf_counter()`, so a busy moment skips a
frame instead of slowing the movement. Bot frames are built once per movement and cached; the banner is one
long seamless picture sliding under rounded corners. Speeds: `Bot.SECONDS`, `AIBanner.SECONDS`,
`AIThinking.SECONDS`.

### Clickable dashboards (`gold_board`)

`gb.Board(dims, on_change)` makes charts filter each other, like slicers in Power BI.

- `dims(order)` returns what an order can be filtered on (`gas.order_dims`: `status`, `due`, `late`,
  `reason`, `age`, `stage`, `type`, `service`, `country`, `customer`, `manager`, `dpm`, `team`, `region`,
  `cluster`, `action`).
- `board.selected` is `{dimension: value}`. A click calls `toggle(dim, value)`; clicking the same value again
  removes it. `choose`, `clear` also exist. Each change calls `on_change()`.
- `board.chosen()`: orders matching every click (for cards and tables).
  `board.without(dim)`: orders matching every click except those on `dim` (what a chart of `dim` shows, so the
  clicked slice stays highlighted next to the others).
- `board.donut(parent, dim, {value: colour}, note=None)` and
  `board.bars(parent, dim, colour_or_dict, rows=6, values=None)` add charts; `board.refresh()` redraws them all.

---

## 10. Driving GOLD with Firefox

### Starting Firefox and signing in (`open_gold.py`)

- `GOLD_URL` is GOLD's home page. `start_firefox(headless=False, profile_dir=None)` uses a persistent profile,
  saves downloads straight to `output\downloads`, and enables Windows SSO (also used for SharePoint).
- `wait_for_gold(driver, timeout)` waits until the page shows GOLD's **"Inbox"** (sign-in done), then closes
  GOLD's announcement pop-up (`dismiss_splash`, calling GOLD's own `closeSplashScreen()`).
- Only one process can use a Firefox profile. A second copy (for example a test) needs its own:
  `set GOLD_PROFILE_DIR=C:\some\other\folder`.
- `Wait(driver, timeout)` is a `WebDriverWait` that polls every 0.1 s (Selenium's 0.5 s default is slow).
- `page_text(driver)` returns the page text in one call.

### Moving around GOLD (`open_order.py`)

| Function | What it does |
|---|---|
| `open_orders_tab(driver, wait, discard_changes=False)` | Goes to the order search page (`#orderNb`). With `discard_changes=True` it accepts GOLD's "You will lose any changes" prompt. |
| `untick_my_orders(driver)` | Unticks "My orders only" (`#myOrdersOnlyCB`). |
| `search_order(driver, wait, order_nb)` | Searches and returns the result row (raises if not found). |
| `open_result(driver, wait, row, order_nb)` | Opens the order (checks the page shows `order # : <nb>`). |
| `list_tabs(driver)` / `open_tab(driver, wait, title)` | The order's side-menu tabs, for example `"Milestones"`, `"Documents [12]"`. |
| `content_text(driver)` | Text of the tab, without the side menu. |
| `read_teams`, documents, `download_document` | Teams and Documents tabs. |

The usual sequence to read an order:

```python
oo.open_orders_tab(driver, wait, discard_changes=True)
oo.untick_my_orders(driver)
row = oo.search_order(driver, wait, order)
oo.open_result(driver, wait, row, order)
oo.open_tab(driver, wait, "Milestones")
data = gx.extract_tab(driver)          # {"banner": ..., "grids": [...], "fields": [...]}
oo.open_orders_tab(driver, wait, discard_changes=True)   # leave cleanly
```

**Rules learned the hard way:**

- Wait for the old page to go stale before reading results, or you read the previous search.
- After reading pages of results, go back to page 1 (`gotoPage(1, 'OrderManager')`): GOLD keeps the page, and
  later row clicks miss.
- From inside an order, the top "Orders" link reopens that order; `open_orders_tab` uses "All orders" first.
- Login detection depends on the word "Inbox" on GOLD's home page.

### Reading tabs as tables (`gold_extract.py`)

`extract_tab(driver)` returns `{"banner": str, "grids": [{"title", "columns", "rows"}], "fields": [(section,
field, value)]}`: list grids are found automatically, other tables become label/value fields, notes keep their
full text. `write_sheet(path, sheet, header_lines, blocks)` writes styled Excel sheets
(`blocks = [(title, columns, rows)]`), replacing a sheet of the same name.

### The editable table (`gold_grid.EditGrid`)

Used by the bulk pages. `EditGrid(parent, columns)`, where each column is a dict:

| Key | Meaning |
|---|---|
| `key`, `title`, `width`, `stretch` | Identifier, heading, width, stretch. |
| `choices` | Function returning a list (a drop-down). |
| `typeahead`, `match` | Searchable drop-down; `match(choice, typed)`. |
| `normalize` | Cleans a value when typed or pasted (for example dates, names). |

A **Status** column is added automatically. Main methods: `rows()`, `record(iid)`, `filled()`,
`set_value(iid, key, value)` (clears the status), `set_status(iid, text, tag)` (tags `ok`, `bad`, `run`),
`add_rows(n)`, `clear()`, `mark_done(iid)` / `is_done(iid, record)` (so a re-run never saves a row twice),
`failed` (rows for "Run failed tasks"), `load(path)` (Excel/CSV), `paste()` (Ctrl+V from Excel).

---

## 11. The features, one by one

Every page is built by `App._build_<x>_tab` in `gold_app.py`; its methods share a prefix (`_my_`, `_oa_`, `_kpi_`,
`_ov_`, `_rtdd_`, `_assign_`, `_names_`, `_org_`, `_ask_`). Search for the prefix to see the whole feature.

### 11.1 My Orders

**Code:** `_my_*`, `gold_myorders.py`.

**Data flow:** **Get my orders** → `_my_load` → job `gmo.read_my_orders(driver, wait)` (reads every results page
of "My orders only"; GOLD embeds the rows in its page script, `_grid_setupDetails` / `_grid_addDetail`) →
`_my_loaded` → `_my_render`.

**The RTDD problem and how it is solved.** GOLD's list only has the *initial* target date (iTTD). An order past
it may already have a later Revised Target Date, so the app finds each order's RTDD:

1. **From the APM sheet**, if this user has it and it is under 3 days old (`MY_SHEET_DAYS`).
2. **From GOLD**, by opening the order's Milestones tab (`gm.read_rtdd`, read-only). Results are kept in
   `my_rtdd.json` and trusted if read today, or if the RTDD is still ahead.

`gmo.apply_rtdd(orders, known)` then sets on every order: `rtdd`, `rtdd_known`, `target` (the **later** of
RTDD and iTTD, as GOLD's reports count it) and `due_days`. Overdue means **target on or before today**.

The list shows **ITDD and RTDD side by side** (`MY_SHOWN`), so the DPM can decide whether the RTDD needs
moving. The RTDD column says "No RTDD" (read, none set) or "Not checked" (not read yet). A row is red when the
target (the later date) is reached. Clicking a date heading sorts by it (`MY_DATES`).

- **Check RTDDs** (`_my_check_rtdds`) reads the RTDD of orders past their initial date whose RTDD is not known
  (about 8 s per order; asks first above 20; stops after 3 failures in a row).
- **Send overdue to RTDD** (`_my_send_overdue`) checks first, then puts the really overdue orders in the
  Revised Target Date table. Nothing is saved in GOLD at this step.
- After an RTDD is changed through the app, `_my_forget_rtdds(orders)` makes those orders read again.
- **Orders / Dashboard** switch: the Dashboard is a `gb.Board` over the open orders (`_build_my_board`);
  clicks also filter the Orders list.
- **Notifications** (`_my_watch`, `_my_changes`): when allowed and idle, the list is re-read in the background;
  new orders, status and date changes and a daily digest are notified.

### 11.2 Overview and Tracker

**Code:** `_ov_*`, `gold_overview.py`, `gold_tracker.py`.

- `go.collect(driver, wait, order)` reads one order (search row, Information, Billing, Milestones, Teams,
  Pricing, Notes) without changing anything, and works out the dates, value and people.
- **Delivery RAG** (`go.rag`): past target → Red; due today or within 14 days (`AMBER_DAYS`) → Amber; else Green.
- **120-day lead time** (`go.lead_time`): the delivery date compared with signature date + 120 days
  (`LEAD_TIME_DAYS`): after it → Red, within 14 days of it → Amber, else Green.
- Several orders are read side by side (from 3 orders, up to 3 sessions) when `parallel_sessions` allows; reads
  are cached 10 minutes.
- **Tracker**: management or customer view (`gold_tracker` columns tagged `m`/`c`), comments per order
  (double-click a cell; saved in `tracker_comments.json`), tracker Excel.

### 11.3 Order explorer

Open an order, browse its tabs (`gx.extract_tab`), screenshots (full page optional), export one tab or all
tabs to the order's workbook (`<exports>\<order>.xlsx`), download documents, see the teams (double-click a
person to look them up in the Org Chart).

### 11.4 Bulk pages: the shared machinery

Both writing pages are built from the same parts:

- `_grid_toolbar(f, title, hint, grid_attr)`: Clear all, +10 rows, Paste from Excel, Load Excel/CSV.
- `_bulk_bar(f, dry_var, run_cmd, check_cmd)`: **Test only**, **Stop**, **Run update**, **Run failed tasks**,
  **Check**.
- `_bulk_run(grid, stop_btn, items, label, action, columns, sheet, header_line, dry)`: runs
  `action(driver, wait, item)` for each `(iid, item, row_values)` in one worker job and marks each row:

| Outcome | Row status | In results Excel | Re-run by "Run failed tasks" |
|---|---|---|---|
| Success | `✓ message` (row marked done if not a test) | OK | no |
| `gm.AlreadySet` | `ℹ Already set` | ALREADY SET | no |
| `gm.EarlierDate` (user said no) | `✗ Not set` | NOT SET | no |
| Stopped | Skipped (stopped) | SKIPPED | no |
| Any other error | `✗ error` | FAILED | **yes** |

A results workbook `<sheet>_<timestamp>.xlsx` is written next to the exports. **Stop** stops after the current
order. These jobs are never retried automatically.

### 11.5 Revised Target Date

**Code:** `_rtdd_*`, `gold_milestones.py`.  **This feature writes to GOLD.**

1. **Check** (`_rtdd_check`): valid order numbers, no duplicates, a date (or the default date), the reason
   snapped to GOLD's exact wording (`gm.match_reason`); past dates are flagged.
2. **Run update** (`_rtdd_run`): asks about rows with problems, about **past dates** (list, yes/no), and a final
   **Confirm GOLD update** (unless Test only).
3. For each order, `gm.add_rtdd(driver, wait, order, kind, new_date, reason, dry_run, confirm)`:
   - opens the order's Milestones; if the current RTDD already has that date → `AlreadySet`;
   - if the new date is **earlier** than the current RTDD or the initial date, asks
     (Set it / Don't set it / Set all / Skip all) → `EarlierDate` if not;
   - fills the "Create new" form (title `Revised Target Date - Customer Reason` or
     `- Orange Business Services Reason`, reason, date set through GOLD's own `copyToHelper` because the date
     boxes are read-only);
   - **Test only:** cancels. **Real run:** saves, then **verifies** that one more RTDD row has that date.
     GOLD may redraw the Milestones list a while after the form closes, so it re-reads the tab (via the
     Information tab, `_reread`, about 20 s each) for up to `VERIFY_SECONDS` (120 s) before reporting it missing.
     The error then warns against running it again (it may be saved, and a second run would add it twice).
4. `gm.read_rtdd(driver, wait, order)` reads the current RTDD (used by My Orders).

**What counts as an RTDD** (`gm.RTDD_TITLE`, `gm.is_rtdd`): the two titles the app adds, "Revised Target
Delivery Date - O..." (added by GOLD's System Delivery) and "MHS - Revised Target Delivery Date" (from
Nov 2026). The list shortens long titles. **The current RTDD** (`gm.current_rtdd`) is the last open one, else
the latest completed one. GOLD completes the older ones when a new one comes, several on the same day, so ties
go to the latest date. Overview uses the same rule.

### 11.6 Bulk assignment

**Code:** `_assign_*`, `gold_teams.py`.  **This feature writes to GOLD.**

`gt.assign_stm(driver, wait, order, first, last, dry_run, user)` opens the order's Teams > **Manage Teams**,
unticks "Same as project", adds the person to the STM team if needed (searching GOLD users; the GOLD user ID
picks one person when two share a name), makes them primary, then saves (or cancels in Test only) and verifies.
Every error path cancels the edit, because Manage Teams locks the order. "Already the primary STM" counts as OK.

### 11.7 Order Assignment and the DPM dashboard

**Code:** `_oa_*`, `_kpi_*`, `gold_assignments.py`.

**The source** is the **APM Open Orders** workbook on SharePoint, refreshed daily.

- `gas.fetch(driver, dest, link, known_version)` opens the library in a new tab of the app's Firefox (the user's
  sign-in), asks SharePoint for the file's version (ETag) and downloads it only when it changed. It checks the
  file really is an Excel file, then replaces `apm_open_orders.xlsx`.
- It is checked when Order Assignment or the DPM dashboard is shown, at most every 30 minutes
  (`OA_CHECK_MIN`); **Refresh** forces it. The link can be changed in Settings > Order Assignment.
- `gas.read(path)` finds columns by their header text (`gas.COLUMNS`), so moved columns still work.
- `gas.classify(orders, dpm_names)` matches each order's **STM Name** with the DPM list (ignoring spaces,
  hyphens, capitals and name order) and adds `dpm`, `category` (Assigned / Unassigned / Not in DPM list),
  `team`, `region` (the APM department) and `manager`.

**Order Assignment** shows the split, the orders with filters (show, region, STM, manager, search), the
"Orders per STM" list and an Excel export. Selected orders can go to Bulk assignment.

**The DPM dashboard** (only orders assigned to a DPM):

- **Filters:** Region → Manager → DPM and Cluster (each list narrowed by the ones before it), Find (customer,
  site reference, product, project, order). Region, Manager and DPM are remembered (`kpi_filters`).
- **Cards:** Open orders, Overdue RTDD, Overdue in 14 days, Not overdue (each with revenue), No RTDD set,
  Average order age. A card click filters like the matching chart.
- **Overview:** 12 clickable tiles on a `gb.Board` (RTDD status, when orders fall due, why RTDDs moved, how
  late, stage, type, age, products, countries, biggest customers, by manager, most overdue DPMs). Clicks
  combine; the red chip clears them.
- **Scorecard:** rows open level by level along a path (`KPI_GROUPS`, for example
  Manager › DPM › Customer); three column sets (`KPI_SCORE_SETS`: RTDD status, To do, Workload); a Total row;
  double-click a row to see its orders. Row ids are the path joined with tabs (`"~\tManager\tDPM"`).
- **Detailed orders due:** Order number, Order status, Customer site reference, DPM, ITDD, RTDD, Days, RTDD
  status, Reason, €, Age; **Send to RTDD** sends the selected orders (or all shown) to Revised Target Date.
- **Excel:** DPM scorecard, By manager, and Orders due (the same orders as Detailed orders due, with its
  "Show" choice in the title).

### 11.8 DPM names and Org Chart

**Code:** `_names_*`, `_org_*`, `gold_names.py`, `gold_orgchart.py`.

- The list (`dpm_names.json`) holds `first`, `last` and optionally `user` (GOLD user ID), `team`, `email`,
  `manager`, `check`.
- **Weekly sync from the Org Chart** (`_names_import_oc`, `_dpm_auto_sync`): reads the people of the DPM
  departments (`dpm_departments`, APMs only), maps them with `gn.from_org_chart` (manager from the Org Chart),
  merges with `gn.merge_team` (by email, then by name), removes people of departments no longer chosen (only
  those that came from the Org Chart). Runs when a DPM-related page is shown and the last sync is over 7 days old.
- Teams: `gn.TEAMS = {"APM Europe": "DPM Egypt", "APM APAC": "DPM India", "APM AME": "DPM Brazil"}`.
- **Check names in GOLD** looks each name up in GOLD's users and stores the exact GOLD spelling and user ID.
- **Org Chart client** (`goc`): opens the Org Chart in a tab of the app's Firefox and calls its own endpoints
  from inside the signed-in page (with the page's CSRF token). `query()` accepts a name, email or CUID;
  `lookup()` caches results 7 days. `App._org(fn)` keeps one Org Chart tab and switches back to GOLD.
- **When the Org Chart does not open.** It counts as open only when a test search works (`OrgChart._ready`).
  Some accounts get a window to accept, and searches are refused until it is accepted. `_acknowledge` clicks
  the usual buttons; when that is not enough after 45 s, `__enter__` raises `goc.SignInNeeded` (it says what
  the tab shows, from `_diagnose`).
  - `App._org_connect` then shows Firefox on the Org Chart (`Worker.show_browser`), with a message telling
    the user to accept or sign in, and waits up to 5 minutes for the search to work.
  - With `sign_in=False` (the automatic weekly DPM sync) it raises instead of showing a window.
  - Only "site cannot be reached" (network/VPN) fails straight away.
- **When the tab's sign-in expires** (the tab stays open for hours), searches answer 403, or the sign-in
  page in place of JSON. That raises `goc.SearchFailed`; `_org` closes the tab, opens a new one and runs
  `fn` once more.

### 11.9 GOLD bot (Ask GOLD)

**Code:** `_ask_*`, `gold_ai.py`, `gold_markdown.py`.

- **Model:** `gold_ai.MODEL`. Effort `low` + fast mode when `bot_speed` is `fast` (default), else `medium`.
- **Tools (all read-only):** `my_orders`, `get_order_overview` (uses `go.collect`), `read_order_tab`,
  `find_person` (Org Chart). Defined in `gold_ai.TOOLS`, run by `GoldReader.run`, results cached 5 minutes.
- **Flow:** `_ask_send` adds context (the order open in the explorer) → on the worker thread `Chat.ask` streams
  the answer and runs tool calls, up to 12 steps → the answer is drawn by `gmd.render` (tables included,
  **Copy answer** gives plain text).
- **The key** is never in the app. `gai.get_key` uses, in order: a key file chosen in Settings; this PC's
  encrypted copy (`ai_key.bin`, Windows DPAPI); the team key file in a OneDrive-synced team folder; a download
  from the team's SharePoint folder with the user's sign-in. Whatever is found is saved encrypted. If the key is
  refused, the cached copy is dropped and fetched again.
- **Privacy:** no prompt caching, nothing stored on the AI side; chats are saved only with **Save chats**, as
  JSON files in `%LOCALAPPDATA%\GOLD Express\chats`, deleted only by the user.

### 11.10 Updates and notifications

- `gu.check()` finds the latest release without GitHub's rate-limited API (it reads the
  `/releases/latest` redirect, then the Atom feed), compares versions, and the top-bar update button lights up.
- **Update now** downloads the installer to `%TEMP%`, checks it (size, `MZ` header), and runs it silently; the
  installer closes the app and starts it again.
- `gnotify.notify(title, text, tag)` shows a Windows toast (through PowerShell; never raises). When run from
  source the toast is labelled "Windows PowerShell".

---

## 12. Business rules reference

All in `gold_assignments.py` (shared by the DPM dashboard and My Orders).

### RTDD status (`rtdd_status`)

| Status | Rule |
|---|---|
| **Overdue RTDD** (`OVERDUE`) | Days to the target date ≤ 0 (**due today counts as overdue**), or the sheet's Backlog says so. |
| **Overdue in 14 days** (`DUE_14`) | Backlog says so, else 1-14 days left. |
| **Not Overdue** (`NOT_OVERDUE`) | Backlog says so, else more than 14 days left. |
| **No date** (`NO_DATE`) | No target date at all. |

`days_left(o)` uses the sheet's "Days to Due Date_BO", else target − today. The target date is the RTDD if
there is one, else the initial date (My Orders: the later of the two).

### What an overdue order needs (`rtdd_action`)

| Value | Meaning |
|---|---|
| **No RTDD set** (`NO_RTDD`) | Past its initial date and never revised. |
| **RTDD date passed** (`RTDD_PASSED`) | Revised, and that date has passed too. |
| **RTDD not checked** (`NOT_CHECKED`) | My Orders only: its RTDD has not been read yet. |

### Other rules

- **RTDD reason** (`rtdd_reason`): "Customer", "Orange" (Orange Business Services), "MHS" or "Other", from the
  sheet's reason text; the leading date is the date on the reason.
- **Bands:** order age `AGE_BANDS` (under 3 months, 3-6, 6-12 months, 1-2 years, over 2 years); how late
  `LATE_BANDS` (1-30, 31-90, 91-180, over 180 days).
- **Revenue:** the sheet's "Total Revenue" (shown as `€2.66M`, `€89k`, `€950` by `gas.money`).
- **Slip:** RTDD − initial date, in days.
- **Red / amber rows** on the dashboard: 30% or more of the orders overdue → red, 15% or more → amber
  (`KPI_LATE_RED`, `KPI_LATE_AMBER`).

### KPIs (`dpm_kpis(orders, by="dpm", soon=30)`)

One row per value of `by` (any order field: `dpm`, `manager`, `team`, `region`, `cluster`, `customer`;
`by=None` gives one "Total" row; `kpi_total(orders)` is that row). Only assigned orders count.

| Fields | Meaning |
|---|---|
| `name`, `manager`, `region` | Group name; manager and region only when `by="dpm"`. |
| `open`, `revenue`, `dpms`, `customers`, `per_dpm` | Counts and totals. |
| `overdue`, `due14`, `ok`, `no_date` (+ `_rev` revenue) | Orders per RTDD status. |
| `no_rtdd`, `passed` | What the overdue orders need. |
| `due7`, `due_soon` | Due in the next 7 / 30 days. |
| `revised`, `revised_pct`, `slip` | RTDDs set, and average slip. |
| `overdue_pct` | % of the orders overdue. |
| `avg_age`, `oldest`, `over_year` | Order age (days). |
| `manage`, `release`, `on_hold`, `billing` | Orders per stage. |

---

## 13. Excel exports

| Export | Function | Contents |
|---|---|---|
| Order explorer tab(s) | `gx.write_sheet` | One sheet per tab in `<exports>\<order>.xlsx`. |
| Overview | `go.export` | Overview sheet (RAG counts, value, 34 columns) + Order details. |
| Tracker | `gtr.export` | Tracker sheet (management or customer view) + Per order. |
| Bulk results | `_bulk_run` | Rows + Result + Details, "TEST ONLY" when a test. |
| Order Assignment | `gad.export` | Dashboard with native charts, All orders, Unassigned, Not in DPM list, Per STM. |
| DPM dashboard | `gad.export_kpis` | DPM scorecard (+ chart), By manager, Orders due (the orders Detailed orders due shows). Follows the dashboard's filters and clicks. |
| My Orders | `_my_export` | The orders shown, with ITDD, RTDD and target date. |

Exports are written next to the order workbook folder (`_ctx()["workbook"]`) and offered to open. If a file
is open in Excel, the app says so instead of failing.

---

## 14. Updates, build, release and the website

### Build

```bash
python build_release.py             # build only -> release\GOLD_Express_Setup_<version>.exe
python build_release.py --publish   # ...and publish GitHub release v<version>
```

What `build_release.py` does:

1. Works in `%TEMP%\gold_express_build` (outside OneDrive).
2. Draws the installer wizard pictures (`installer\wizard_*.bmp`).
3. Builds the app with PyInstaller (one folder, windowed) including `geckodriver.exe`, the icon and `assets\`,
   collecting `selenium` and `anthropic`. Result:
   `%TEMP%\gold_express_build\dist\GOLD Express\GOLD Express.exe`.
4. Builds the installer with Inno Setup (`installer\gold_express.iss`) → `release\GOLD_Express_Setup_<version>.exe`.
5. With `--publish`: takes the `## <version>` section of `CHANGELOG.md` as notes and runs
   `gh release create v<version> ... --latest` with two files: `GOLD_Express_Setup_<version>.exe` (used by
   in-app updates) and `GOLD_Express_Setup.exe` (used by the website's download button). Keep both.

### Release checklist

1. `version.py`: bump `__version__` (major.minor.patch).
2. `CHANGELOG.md`: add `## <version>` at the top, bullets with **bold** lead-ins, written for users.
3. `python build_release.py`, then run the packaged self-test:
   `"%TEMP%\gold_express_build\dist\GOLD Express\GOLD Express.exe" --ui-selftest` and read
   `Documents\GOLD Express\ui_selftest_report.txt`.
4. Close any test copies of the app.
5. Commit (subject `<summary> (<version>)`) and push.
6. With the owner's OK: `python build_release.py --publish`.
7. Check: `gh api repos/AhmedWalid4499/Tools-Automation/releases/latest` shows the new tag, both files, and the
   tag points at the pushed commit.

### The installer

- Per-user install, no administrator rights (`%LOCALAPPDATA%\Programs\GOLD Express`), x64.
- **`AppId` in `gold_express.iss` must never change**: it is how upgrades are recognised.
- Upgrades delete the old `_internal` folder first, close the running app, and a silent install starts it again.
- User data in `Documents\GOLD Express` is never touched.
- It warns if Firefox is missing. The Start-menu shortcut carries the app ID notifications need.

### The website (`docs/index.html`)

The public download page, served by GitHub Pages from `docs/`. It shows features, install steps and what's
new (read from the latest release). **It must not show GitHub links or words**: the download button starts the
download from a click handler. After changing the logo or bot pictures, copy them to `docs/assets/` too.

---

## 15. Testing

| Command | What it checks | Needs GOLD |
|---|---|---|
| `python gold_app.py --ui-selftest` | Opens every page; writes `ui_selftest_report.txt` and `ui_selftest.png`. | No |
| `python gold_app.py --selftest 10-1771012` | Starts Firefox, signs in, opens the order, exports Milestones; writes `selftest_report.txt`. | Yes |
| `python gold_app.py --ask-selftest` | Gets the AI key and asks the model one question; writes `ask_selftest_report.txt`. | No |
| `python gold_app.py --ask-selftest --sharepoint` | Same, forcing the SharePoint key download (a colleague's first use). | No |

Run the same flags on the built exe before every release. Reports go to the data folder.

### Testing a page without GOLD

Most logic can be tested by creating the app with GOLD switched off and feeding it data. This is how the
dashboards were tested:

```python
import gold_app as ga, gold_assignments as gas
ga.SETTINGS_FILE = Path("test_settings.json")            # never touch the real settings
for name in ("_prewarm", "_check_updates", "_oa_shown", "_dpm_auto_sync"):
    setattr(ga.App, name, lambda self, *a, **k: None)     # no GOLD, no SharePoint
app = ga.App()
app.oa_orders = gas.classify(made_up_orders, made_up_names)
app.oa_time = time.time()
app.after(1000, lambda: (app._oa_render(), check_things(app), app.destroy()))
app.mainloop()
```

Click handlers can be called directly (`app.kpi_board.toggle("status", gas.OVERDUE)`, `app._kpi_card(...)`),
and a GOLD reader can be replaced by a fake (`gm.read_rtdd = fake`, `app.worker.submit = lambda n, job, done=None,
**k: done(job())`).

**When adding a page that loads data when shown,** also stub its loader in the `--ui-selftest` branch of
`__main__`, or the self-test will try to reach GOLD.

---

## 16. Recipes: how to make common changes

### 16.1 Add a page

1. In `App._build`: `xyz = page()`; `nav.add(xyz, "Title", "\uE8A5", "One-line subtitle")` under the right
   `nav.section(...)`; `self.xyz_frame = xyz` if other code needs to open it; `self._build_xyz_tab(xyz)`.
2. Write `_build_xyz_tab(self, f)` with `self._tile(...)`, `self._tile_head(...)`, `self._btn(...)`.
3. Load data with a worker job ([7](#7-threads-the-worker)). To load when the page is shown, add the title to
   `_page_changed`, and stub that loader in `--ui-selftest`.

### 16.2 Add a chart to the DPM dashboard

1. If you need a new dimension, add it to `gas.order_dims(o)` (a short label; `""` = not applicable). My Orders
   uses the same function.
2. In `_build_kpi_overview`, add a tile, for example:
   ```python
   b.bars(tile(4, 0, "Order type", "\uE8A5"), "type",
          {"New": "#22C55E", "Change": "#38BDF8", "Disconnect": "#94A3B8"}, rows=3)
   ```
3. Nothing else: `board.refresh()` draws it, and clicks filter everything.

### 16.3 Add a column to the Scorecard

1. `gold_assignments.py`: add a default in `_blank_kpi`, count it in the `dpm_kpis` loop (or work it out after
   the loop; remove `_`-prefixed helper fields before the row is returned).
2. `gold_app.py`: add `("key", "Heading", width, "e")` to `KPI_SCORE_COLUMNS`, and the key to one or more
   `KPI_SCORE_SETS` (otherwise it is never shown).
3. Special formatting: `_kpi_score_cell` (`*_rev` columns need a matching count column; `*_pct` get "%").
4. Optional: add it to `gad.export_kpis` (`columns` and `numbers()`), keeping the positions in `tidy()` right.

### 16.4 Add a Scorecard breakdown

Add `("A › B › C", ("field_a", "field_b", "field_c"))` to `KPI_GROUPS`. Each field must be an order key that
`dpm_kpis(by=field)` can read **and** a key of `gas.order_dims` (the double-click drill-down filters on it). If
the field does not exist yet, set it in `gas.classify` and add it to `order_dims`.

### 16.5 Add a new bulk action

1. **The GOLD action** in its own module: `def do_x(driver, wait, order, ..., dry_run=False) -> str`.
   - Start with `oo.open_orders_tab(driver, wait, discard_changes=True)`.
   - In `dry_run`, fill the form and cancel.
   - After saving, **verify** the change; raise on any problem.
   - Raise `gm.AlreadySet` when there is nothing to do.
2. **The page**, modelled on `_build_assign_tab`:
   ```python
   f = self._tile(f, fill="both", expand=True).body
   self._grid_toolbar(f, "Orders to update", "click a cell to type  ·  Ctrl+V pastes from Excel", "x_grid")
   self.x_grid = EditGrid(f, [{"key": "order", "title": "Gold order", "width": 140},
                              {"key": "value", "title": "New value", "width": 200}])
   self.x_grid.pack(fill="both", expand=True)
   self.x_dry = tk.BooleanVar(value=False)
   self.x_stop_btn = self._bulk_bar(f, self.x_dry, self._x_run, self._x_check)
   ```
3. **`_x_check(only=None)`**, modelled on `_assign_check`: skip rows not in `only`, skip `g.is_done(iid, r)`
   rows, validate, set statuses, return `(items, bad)` with `items = [(iid, item, [order, ...shown values])]`.
4. **`_x_run(only_failed=False)`**, modelled on `_assign_run`: `if self.busy: return`; failed rows when
   `only_failed`; check; ask about bad rows; confirm "This saves in GOLD" unless Test only; then:
   ```python
   self._bulk_run(self.x_grid, self.x_stop_btn, items, "My bulk action",
                  lambda d, w, it: gx_module.do_x(d, w, it[0], it[1], dry_run=dry),
                  ["Gold order", "New value"], "My bulk action", "What was changed", dry)
   ```
   The `columns` list must be as long as each item's shown values.
5. Register the page (16.1) under "Bulk updates".

### 16.6 Add a tool to the GOLD bot

1. Add its definition to `gai.TOOLS` (strict mode: list every field in `required`, set
   `"additionalProperties": False`):
   ```python
   {"name": "my_tool",
    "description": "What it returns and when to use it.",
    "input_schema": {"type": "object",
                     "properties": {"order": {"type": "string", "description": "GOLD order number"}},
                     "required": ["order"], "additionalProperties": False}},
   ```
2. Handle it in `GoldReader.run` (before the order-number check if it takes no order), wrapped in
   `self._cached(key, fn)`. It runs on the worker thread: call `self.app.worker.ensure_browser()` before using
   the driver, return text, and **only read**.
3. Add a progress message in `Chat.ask`, and tell the model when to use it in `system_prompt()`.
4. Test in the app (`--ask-selftest` does not use tools).

### 16.7 Add a setting

See [6](#6-where-data-lives-and-the-settings): default in `load_settings()`, a Tk variable and a control in the
Settings window (`_open_settings` area), copy back in `_store_settings()`.

### 16.8 Change the look

- Colours: edit the tokens in `gold_ui.THEMES` (all three themes). Restart to see them.
- New widget style: in `gold_ui.style_rounded`.
- New icon: `font=(gui.ICONS, size)` with an escape like `"\uE8A5"`.

### 16.9 Change a business rule

The rules are small functions in `gold_assignments.py` (`rtdd_status`, `rtdd_action`, `days_left`, bands) and
`gold_overview.py` (`rag`, `lead_time`). Change them there, and update [12](#12-business-rules-reference),
the CHANGELOG, and any test that checks them. Both the DPM dashboard and My Orders follow automatically.

---

## 17. Gotchas

**Threads and jobs**

- Never touch a widget from a job; use `self.ui(...)` / `self.log(...)`.
- Only read-only jobs may use `retry=True`; a retried job runs from the start, so it must call
  `ensure_browser()` first.
- `job_failed` shows an error box even for background jobs.
- Buttons lock while busy only if created with `self._btn`.

**GOLD**

- Every write path starts from `open_orders_tab(..., discard_changes=True)`; the app's Firefox is used only by
  the app, and every change is either saved and verified or cancelled.
- Manage Teams locks the order: every error must cancel the edit.
- GOLD shortens long milestone titles in its lists ("Orange Bus..."): match by prefix.
- A second running copy needs its own Firefox profile (`GOLD_PROFILE_DIR`); the app allows one instance.

**UI**

- Theme colours are fixed when the app starts: restart to change.
- Keep a reference to every `PhotoImage`, or it disappears.
- `Bars` has a fixed number of rows; extra items are cut off.
- Page titles are matched as text in `_page_changed`.
- "Empty-looking" icon strings are real icons; write new ones as `\uXXXX`.

**Data**

- The DPM dashboard counts only orders assigned to a DPM.
- `gas.NO_TEAM` ("No team") and `gn.NO_TEAM` ("Other") are different constants.
- Order-number patterns differ slightly: `\d{2}-\d{5,8}` in most places, `\d{2}-\d+` in the grid loader.
- Two Overview caches: 10 minutes for the page, 5 minutes for the GOLD bot.
- Sorting Treeview rows: ids must be unique, which is why order tables use `"<order>#<i>"`.

**Release**

- The CHANGELOG heading must be exactly `## <version>`, or the release notes become just the version.
- Two installer files per release; both are used.
- Never change the installer `AppId`.

---

## 18. Known issues and loose ends

Found while writing this guide; none is urgent.

- **Comments out of date:** `gold_assignments.py` says the sheet data "is never kept in the app", but the latest
  copy is kept as `apm_open_orders.xlsx`; the README and `.gitignore` say the DPM list is packed into the app at
  build time, but it no longer is (the installer is public).
- **Chats:** saved chats have no automatic expiry; they stay until the user deletes them.
- **Error log:** `gold_app_error.log` sits in `Documents\GOLD Express`, which may be synced by OneDrive.

---

## 19. Glossary

| Term | Meaning |
|---|---|
| **GOLD** | Global Order Lifecycle Delivery, Orange Business's order-management web app. |
| **Order number** | `10-1771012` style: two digits, a hyphen, 5-8 digits. |
| **DPM** | Delivery Project Manager. Their departments are the APMs. |
| **APM** | The DPM departments: APM Europe (team DPM Egypt), APM APAC (DPM India), APM AME (DPM Brazil). Not CPM. |
| **STM** | The order's team member in GOLD's PMandCSM team; "STM Name" in the sheet. Bulk assignment makes a DPM the primary STM. |
| **ITDD / ITTD / iTTD** | Initial Target Delivery Date: the first promised date. |
| **RTDD** | Revised Target Delivery Date: a later date set with a milestone and a reason (Customer or Orange Business Services). |
| **Target date / TDD** | The date that counts: the RTDD if there is one, else the ITDD (My Orders: the later of the two). |
| **Overdue RTDD, Overdue in 14 days, Not Overdue** | The sheet's Backlog statuses, used by the dashboards. |
| **APM Open Orders sheet** | The daily SharePoint workbook of open APM orders behind Order Assignment and the DPM dashboard. |
| **RAG** | Red / Amber / Green status. |
| **120-day lead time** | The target is 120 days after the customer's signature. |
| **Org Chart** | Orange Business's people directory. **CUID** is a person's ID (4 letters + 4 digits). |
| **SSO** | Single sign-on: GOLD, SharePoint and the Org Chart open with the user's Windows / Orange account. |
| **Board** | A set of charts that filter each other (`gold_board`). |
