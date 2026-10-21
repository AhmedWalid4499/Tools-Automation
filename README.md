# GOLD Express

A desktop assistant for Orange Business **GOLD** (Global Order Lifecycle Delivery). It drives GOLD in
a hidden Firefox window, so routine order work takes a few clicks instead of many.

**Created by Ahmed El-Bourgy. Copyright © 2026 Ahmed El-Bourgy. All rights reserved.**

## What it does

| Tab | |
|---|---|
| **Overview** | Key facts of one or more orders: order value, project, scope, STM, site, target dates, with Red / Amber / Green delivery and 120-day lead-time status. Exports a management-ready Excel. |
| **Order explorer** | Open an order, browse its tabs, take screenshots, download documents, see teams, export tabs to Excel. |
| **Revised Target Date** | Add the "Revised Target Date" milestone (Customer or Orange Business Services reason) to many orders at once. |
| **Bulk Order Assignment** | Make a DPM the primary STM of many orders at once. |
| **DPM Names** | Manage the DPM list used by Bulk Order Assignment, and check names in GOLD. |
| **Org Chart** | Find anyone at Orange Business (email, job, phone, manager chain); look up the team of an order. |
| **Ask GOLD** | Chat assistant (Claude): ask about deadlines, pricing, site address, people or notes of any order; answers come as tables and lists, read live from GOLD. |

Ask GOLD uses the team's AI key file (`salto-buddy-team.key` in the team's SharePoint folder). The key
is never part of the app or this repository: on the first question GOLD Express downloads it from the
team folder with the user's Windows / Orange sign-in (only team members can open the folder) and keeps
it on the PC encrypted for that Windows user (DPAPI). A synced copy of the folder, or a file chosen in
Settings > AI assistant, is used instead when present.

GOLD Express only changes GOLD when you click **Run update** on the Revised Target Date or Bulk Order
Assignment tab and confirm; everything else only reads GOLD. Both have a **Test only** mode.

## Install

Download `GOLD_Express_Setup_<version>.exe` from **[Releases](../../releases/latest)** and run it.
No administrator rights are needed. Requirements: Windows, Mozilla Firefox, and GOLD access with your
Orange account (sign-in is automatic through SSO).

Installed copies **update themselves**: when a new release is published, the update button in the
app's top bar turns orange.

## For developers

```
pip install selenium openpyxl pillow anthropic pyinstaller
python gold_app.py                    # run from source
python build_release.py               # build release\GOLD_Express_Setup_<version>.exe (needs Inno Setup 6)
python build_release.py --publish     # ...and publish it as a GitHub release (needs: gh auth login)
```

To release a new version: bump `__version__` in `version.py`, add a section to `CHANGELOG.md`
(it becomes the release notes), then run `build_release.py --publish`.

| File | |
|---|---|
| `gold_app.py` | The app window (tkinter) |
| `open_gold.py`, `open_order.py` | Firefox / GOLD session, opening orders and tabs |
| `gold_extract.py` | Turns GOLD pages into tables and Excel sheets |
| `gold_overview.py` | Overview data, RAG and lead-time rules, management Excel |
| `gold_milestones.py` | Revised Target Date milestones |
| `gold_teams.py` | STM assignment and GOLD user search |
| `gold_names.py` | DPM names list |
| `gold_grid.py` | Excel-like editable table |
| `gold_update.py` | Updates from GitHub Releases |
| `gold_orgchart.py` | Orange Business Org Chart lookups (shared with SALTO Buddy) |
| `gold_ai.py`, `gold_markdown.py` | Ask GOLD: Claude conversation with read-only GOLD tools, answer rendering |
| `installer/` | Inno Setup wizard |

The built-in DPM names list (`data/dpm_names_default.json`) is kept out of this repository and packed
into the app at build time.
