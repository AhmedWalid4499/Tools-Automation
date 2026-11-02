# CLAUDE.md - GOLD Express

Windows desktop app (Python 3.12, tkinter/ttk, Selenium + Firefox, openpyxl, Pillow, Anthropic SDK) that drives
Orange Business's GOLD order-management web app and adds dashboards. Owner: Ahmed El-Bourgy.

**Full documentation: [`DEVELOPER_GUIDE.md`](DEVELOPER_GUIDE.md).** Read the section for the area you change
before editing. This file is the short version.

## Rules you must follow

1. **Only two features write to GOLD**: Revised Target Date (`gold_milestones.add_rtdd`) and Bulk assignment
   (`gold_teams.assign_stm`), after Run update + confirmation. Everything else must only read GOLD. Anything new
   that writes needs a Test only mode, a confirmation, a check after saving, and no automatic retry.
2. **Never read, print or copy the AI key** (`ai_key.bin`, `*.key`, the team key file). Do not open
   `gold_app_settings.json`, `dpm_names.json`, `my_orders_snapshot.json`, `my_rtdd.json`, `*.log`,
   `apm_open_orders.xlsx`, `output/`, `data/`, `chats/`: they hold private data.
3. **Nothing from the AI may be stored on the AI side** (no prompt caching, no server-side storage). Chats are
   saved only locally, only if the user ticks Save chats.
4. **The repository and the installer are public.** No customer, order or DPM data, keys or settings in them.
   The DPM names list is never bundled.
5. **Never show the GitHub address** in app messages or on the website (`docs/index.html`). Point users to
   `gold_update.DOWNLOAD_PAGE`.
6. **DPM departments are APM departments only** (APM Europe, APM APAC, APM AME), never CPM.
7. **Publishing a release needs the owner's explicit OK.** Building and testing do not.
8. **Never touch tkinter widgets from the worker thread.** Use `self.ui(fn)` or `self.log(msg)`.
9. **Never use `retry=True` for a job that saves in GOLD.**
10. **Use theme tokens** (`gui.CARD`, `gui.INK`, `RED`...), not hard-coded colours. Write icons as `""`
    escapes; never delete an empty-looking icon string (it holds an invisible icon character).

## Commands

```bash
pip install selenium openpyxl pillow anthropic pyinstaller
python gold_app.py                          # run from source (data folder = this repo)
python gold_app.py --ui-selftest            # open every page, no GOLD -> ui_selftest_report.txt
python gold_app.py --selftest 10-1771012    # real GOLD: open an order -> selftest_report.txt
python gold_app.py --ask-selftest           # AI key + one question -> ask_selftest_report.txt
python build_release.py                     # build -> release\GOLD_Express_Setup_<version>.exe
python build_release.py --publish           # build + GitHub release (owner's OK first)
```

Packaged app for testing: `%TEMP%\gold_express_build\dist\GOLD Express\GOLD Express.exe --ui-selftest`
(report in `Documents\GOLD Express\ui_selftest_report.txt`). Close test copies afterwards: only one instance
can run and a Firefox profile cannot be shared (`GOLD_PROFILE_DIR` gives another).

## Release steps

1. Bump `__version__` in `version.py`.
2. Add `## <version>` at the top of `CHANGELOG.md` (user-facing bullets, **bold** lead-ins). It becomes the
   release notes; the heading must match exactly.
3. `python build_release.py`, then the packaged `--ui-selftest`.
4. Commit with subject `<what changed> (<version>)`, push.
5. With the owner's OK: `python build_release.py --publish`.
6. Verify: `gh api repos/AhmedWalid4499/Tools-Automation/releases/latest` (tag = pushed commit, two assets).

## Map

| File | What |
|---|---|
| `gold_app.py` | `App` (all pages, methods prefixed per page: `_my_`, `_oa_`, `_kpi_`, `_ov_`, `_rtdd_`, `_assign_`, `_names_`, `_org_`, `_ask_`), `Worker`, self-tests, entry point. |
| `gold_ui.py` | Themes, widgets (`Tile`, `StatCard`, `Donut`, `Bars`, `Pill`, `SideNav`, `TableCopy`, `Bot`...), ttk styles. |
| `gold_board.py` | `Board`: charts that filter each other. |
| `gold_assignments.py` | APM Open Orders sheet (SharePoint fetch, read, classify), RTDD rules, `dpm_kpis`, `order_dims`. |
| `gold_assign_dashboard.py` | Excel exports for Order Assignment and the DPM dashboard. |
| `gold_myorders.py` | GOLD's "My orders only" list, `apply_rtdd`, `summary`. |
| `gold_overview.py`, `gold_tracker.py` | Overview (read one order, RAG, 120-day lead time), Tracker, their Excel. |
| `gold_milestones.py`, `gold_teams.py` | The two GOLD writers (RTDD milestone, primary STM) and their readers. |
| `open_gold.py`, `open_order.py`, `gold_extract.py` | Firefox and sign-in, moving around GOLD, tabs to tables, Excel writing. |
| `gold_grid.py` | `EditGrid`, the Excel-like table of the bulk pages. |
| `gold_names.py`, `gold_orgchart.py` | DPM list and matching; Org Chart client. |
| `gold_ai.py`, `gold_markdown.py` | GOLD bot (Claude + read-only tools), answer rendering. |
| `gold_update.py`, `gold_notify.py`, `version.py` | Updates, Windows notifications, version. |
| `build_release.py`, `installer/`, `docs/`, `tools/` | Build/publish, Inno Setup, public website, asset generators. |

## Patterns

A GOLD job (worker thread for GOLD, UI thread for widgets):

```python
def _x_load(self):
    if self.busy:
        return
    w = self.worker

    def job():
        w.ensure_browser()
        return some_module.read_something(w.driver, w.wait)

    w.submit("Reading something", job, self._x_loaded, retry=True)   # retry only for read-only jobs
```

UI building blocks: `self._tile(parent, fill="x")` (put widgets in `.body`), `self._tile_head(body, title, icon)`,
`self._btn(parent, text, cmd, "Small.TButton")` (locks while busy), `gui.StatCard(...).set(big, sub)`,
`gb.Board(gas.order_dims, on_change)` + `board.donut/bars`. Sizes: `int(n * self.winfo_fpixels("1i") / 96)`.

Business rules live in `gold_assignments.py`: due today counts as overdue; target = RTDD else initial date
(My Orders: the later); `rtdd_status`, `rtdd_action`, `dpm_kpis(orders, by=...)`.

## How to work here

- Match the surrounding code: short docstrings in plain words, comments only where the reason is not obvious,
  British spelling in user-facing text ("colour").
- Keep page titles in sync with `_page_changed`, and stub any new auto-loading hook in the `--ui-selftest`
  branch of `__main__`.
- Test logic without GOLD by creating `App()` with `_prewarm`, `_check_updates`, `_oa_shown`, `_dpm_auto_sync`
  stubbed and a temporary `SETTINGS_FILE` (see DEVELOPER_GUIDE.md section 15). Never overwrite the user's real
  data files in tests.
- After a change, update `DEVELOPER_GUIDE.md` if it describes that area, and the CHANGELOG for user-visible
  changes.
