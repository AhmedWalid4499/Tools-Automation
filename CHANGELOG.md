# GOLD Express - what's new

## 2.19.0
- **DPM dashboard: now a full RTDD dashboard for DPMs and managers** - built like the Performance
  Management page of the DPM KPIs report, from the daily APM Open Orders sheet. Six cards: open orders,
  Overdue RTDD, Overdue in 14 days, Not overdue (each with its revenue), No RTDD set and average order age.
- **Three views**
  - **Overview**: RTDD status, when orders fall due week by week, why RTDDs moved (Customer, Orange,
    MHS), order age, biggest customers and a By manager table.
  - **Scorecard**: Not overdue, Overdue in 14 days, Overdue RTDD and Total, each with orders and revenue,
    plus % overdue, No RTDD and average age, by DPM, manager, DPM team, sales cluster or customer.
    Double-click a row to see its orders.
  - **Orders due**: the orders to act on, most overdue first, with ITTD, RTDD, days to due, RTDD status,
    reason and revenue. Show overdue, next 14 or 30 days, No RTDD set, RTDD date passed and more.
    Select orders and press **Update RTDD** to send them to the Revised Target Date page.
- **Filters**: region, manager, DPM, sales cluster, and a find box for customer, product, project or
  order number. Region, manager and DPM are remembered, so everyone comes back to their own numbers.
  Click a card or a status to open those orders.
- **Excel export**: adds revenue and RTDD status to the scorecards, and a new Orders due sheet.
- Overdue now follows the sheet's Backlog column everywhere, including Order Assignment, so the app's
  numbers use the same rule as the report.

## 2.18.0
- **DPM dashboard (new page, under Order Assignment)** - KPIs for managers, from the same APM Open
  Orders sheet: DPMs with orders, open orders, overdue, due in the next 30 days, orders per DPM and
  average order age. A DPM scorecard (open, overdue, % overdue, due in 30 days, RTDD set, average
  age) sorts by any column; rows are red when 30% or more of a DPM's orders are overdue, amber from
  15%. Delivery status chart, and a By manager table: click a manager to see only their DPMs.
  Filter by region, manager or name; double-click a DPM to see their orders; Excel export.
- **Order Assignment: filter by manager.** A Manager filter next to STM (DPM), and the Orders per
  STM list now shows each DPM's manager, has a find box (STM or manager) and sorts by any column
  (click a heading).
- Each DPM's manager comes from the Org Chart with the DPM list's weekly update (the first update
  after installing brings them in). The Excel exports have a Manager column.

## 2.17.1
- **Sharp on every screen.** On laptops set to 125% or 150% scaling, Windows used to stretch the
  window, so text and edges looked blurry and pixelated. GOLD Express now draws at the screen's
  full resolution. Table rows, the logo and the top icons grow with the scaling, and the window
  opens maximized when it doesn't fit.
- The Run update / Run failed tasks buttons always stay visible on smaller screens.

## 2.17.0
- **Revised Target Date warns before an earlier date.** Each order's new RTDD is compared with
  its ITDD when it has no RTDD yet, or else with the later of its current RTDD and ITDD. If the new
  date is earlier, you're asked first: Set it / Don't set it, or Set all / Skip all for the rest of
  the run. Orders you don't set show "Not set". In Test only runs the warning is shown in the row.
- **"Run failed tasks"** in Revised Target Date and Bulk Order Assignment runs only the orders
  that failed in the last run; the other rows keep their results. The end-of-run message lists
  the failed orders.

## 2.16.0
- **Revised Target Date checks before updating GOLD:**
  - If the order's current RTDD already has the date you chose, nothing is added and the row
    says "Already set"; the end-of-run message lists those orders.
  - A date in the past is flagged when you check or run. Before anything is saved, a pop-up asks
    whether you agree to set it to that past date anyway: Yes sets it, No leaves those orders out.

## 2.15.1
- **Updates, look and Settings are icons at the top right** (next to the status), like other apps -
  hover for a tip. When a new version is ready, the update icon lights up with a dot.

## 2.15.0
- **A new futuristic look** (now the default): deep-space background, glass tiles with glowing
  edges, neon wave cards, and glowing violet-to-blue buttons and menu. Prefer the old look?
  Settings > Appearance > Light or Dark (or the button at the bottom of the side menu).
- **The GOLD bot looks like an AI**: a flowing aurora header with an "AI" badge, a glowing bot,
  your questions in gradient bubbles, animated "thinking" dots, AI suggestion cards and a glowing
  message box - in every look.

## 2.14.2
- Clearer update messages: when updates can't be checked, GOLD Express says so in plain words and
  points to the GOLD Express download page.

## 2.14.1
- **APMs only**: the DPM list holds the APM departments only (APM Europe = DPM Egypt, APM APAC =
  DPM India, APM AME = DPM Brazil) - still filled automatically for everyone. The CPM and other
  departments that 2.14.0 added are removed again (names you typed yourself stay), so anyone outside
  the APMs shows in Order Assignment as "Not in DPM list".

## 2.14.0
- **The APMs of every department, for everyone**: Bulk assignment and Order Assignment now offer the
  DPMs of nine Org Chart departments - APM Europe, APM APAC, APM AME, CPM Egypt, CPM India, CPM Brazil,
  Project Mgt Experts EUR, Project Management APAC and Project Mgt LAM (about 430 people) - each with
  its own team tick-box / region.
- **Your DPM list fills itself**: it is updated from the Org Chart automatically (when you open DPM
  names, Bulk assignment or Order Assignment, at most once a week) - nothing to import by hand.
  Names you added yourself are kept.
- Settings > DPM departments: the list of departments (add or remove one there).

## 2.13.0
Privacy of the GOLD bot:
- **Nothing kept on the AI's side by GOLD Express**: no prompt caching (which stored the conversation
  for a few minutes) and no server-side fallback (which recorded a fingerprint of it). GOLD data is
  sent only to answer the question and is not used to train the AI.
- **Chats are no longer saved** unless you tick "Save chats" - and then only on this PC, in its local
  app-data folder that OneDrive never syncs (chats saved earlier were moved there). With saving off,
  a chat is gone when you start a new one or close the app.

## 2.12.0
- **New: Tracker** (Overview > Tracker) - the orders you type in the Overview as a tracker to share:
  project, site, service, status, target delivery date, delivery status, next milestone and your own
  **Comments / next steps** (double-click to type; kept for next time).
  - **For Management**: everything, incl. customer, STM, 120-day lead time, order value and the
    latest GOLD note. **For Customer**: only what a customer should see, in plain words.
  - **Excel tracker**: a ready-to-send sheet - title, "prepared for", status counts, coloured
    delivery status, filters, one landscape page wide when printed - plus a page per order.
- The Overview's order list is narrower, so the order details get more room.

## 2.11.0
- **Order Assignment dashboard in Excel**: "Excel dashboard" (Order Assignment tab) saves a
  workbook with a Dashboard sheet - headline numbers (open, assigned, unassigned, not in the DPM
  list, DPMs with orders, overdue) and charts: who has the orders, assigned orders per region,
  assignment by order status, top 15 DPMs, top 15 STMs not in the DPM list, and unassigned orders
  by sales cluster and by age - plus sheets with all orders, the unassigned ones, the ones with
  people not in the DPM list, and orders per STM (with filters). It follows the tab's filters.
- "Overdue" now means past the target date (Days to Due Date below 0).

## 2.10.1
- **Order Assignment is live on the sheet's link**: every time you open the tab (at most every
  30 minutes) GOLD Express asks SharePoint whether the APM Open Orders sheet has a newer version and
  reads it when it does - nothing is kept from an old copy. Refresh reads it straight away.
- The link is in Settings > Order Assignment (paste a new link there if the sheet moves); the tab
  shows which sheet it reads and when SharePoint last refreshed it - click that line to open the
  sheet in your browser.

## 2.10.0
- **New: Order Assignment** - which DPM has which open APM order. It reads the "Power BI - APM
  Open Orders" sheet straight from its SharePoint link (with your Orange sign-in), once a day when
  you open the tab - the sheet is refreshed daily - or whenever you click Refresh.
  - Counters for all orders, assigned to DPMs, **unassigned**, and assigned to people who are **not
    in the DPM list**.
  - Filter by region (APM Europe, APM APAC, APM AME), by STM name (type any part, e.g. "elshazly")
    or search anything; "Orders per STM" lists everyone with their number of orders - click a name.
  - Right-click orders to open them or to assign a DPM in Bulk assignment; export to Excel.
- The bulk tab is now called **Bulk assignment**.

## 2.9.0
Safety fixes from a full check of the app:
- **No duplicate updates**: running Revised Target Date or Order assignment again (e.g. after Stop)
  skips the rows already saved in GOLD (✓). Change a row to run it again.
- **The right DPM**: a pasted or typed name is only matched to a list name when it is the same
  name (spaces, hyphens, capitals or order aside) - "Sara Ali" is no longer turned into
  "Sara Alington". Pick partial names from the suggestions. The Org Chart import keeps two people
  with the same names but different emails apart.
- **Safe updates**: an update that did not download completely is never installed.
- **No more stuck "busy"**: one error no longer freezes the app; the table buttons are disabled
  while a run is going; the results file failing to save no longer hides the results.
- **Closing during a run**: GOLD Express asks first, stops after the current order and then
  closes. Updating or restarting (dark mode) waits until the task is finished.
- **The DPM list is no longer part of the installer.** New users fill it with DPM names >
  "Import DPM teams from Org Chart". Existing lists are kept.

## 2.8.1
- Org Chart: the person card with the "Reports to" tree now scrolls (scrollbar and mouse wheel)
  when the manager chain is long; the results table scrolls sideways to show every column.

## 2.8.0
- **DPM teams from the Org Chart**: DPM names > "Import DPM teams from Org Chart" reads the APM
  departments (APM Europe = DPM Egypt, APM APAC = DPM India, APM AME = DPM Brazil), adds the
  people and gives every name its team. Filter the list by team; set a name's team in Edit.
- **Choose the DPM teams in Order assignment**: tick DPM Egypt / DPM India / DPM Brazil / Other
  and only those names are offered (remembered for next time).
- **Find a DPM by any part of the name**: type "elbourgy", "el bourgy" or "bourgy ahmed" in the
  STM cell - the matching names show under the cell; pick with the arrows + Enter or a click.
- **Dates in any format** (Revised Target Date): 6/12/2026, 6.12.26, 2026-12-06, Dec 6 2026,
  6th December, 6 Dec (this year), Excel dates, today, tomorrow, +14 (days from today)...

## 2.7.0
- **My Orders loads when you ask**: GOLD Express no longer reads your orders at start-up. Click
  "Get my orders" (or Refresh) on the My Orders page. Asking the GOLD bot about your orders also
  reads them. Order notifications start once your orders have been read.
- **Smoother maximize / restore / minimize**: the window no longer shows half-drawn tiles and
  black patches while it changes size.

## 2.6.1
- Fixed: picking a name from the drop-down list in Order assignment (and other lists in the bulk
  tables) showed an error.

## 2.6.0
- **A much quicker GOLD bot**: questions about your orders ("which are late?") are answered
  in seconds from My Orders, and order questions read only the tab they need (Teams for the STM,
  Milestones for deadlines) instead of the whole order.
- **See the answer as it is written**: the bot shows its words while it is still answering.
- **Fast or Thorough**: Settings > GOLD bot answers. Fast (the default) answers quicker;
  Thorough takes a little longer to think on harder questions.
- Fixed: the bot sometimes could not open an order right after My Orders was refreshed.

## 2.5.0
- **Meet the Friendly GOLD bot** (was Ask GOLD): an animated bot that floats on the welcome screen,
  bobs along while it works, and hops when you click it. It greets you and answers as "GOLD bot".
- **Copy from any table, like Excel**: click a cell (orange outline) or drag across cells, then
  Ctrl+C; right-click to copy the cell, the selection, the row, the column or the whole table
  (pastes into Excel as cells). Works in My Orders, Overview, Org Chart, DPM names, Teams, Documents,
  the order tabs and the bot's answers.
- **Drag down to fill** in Revised Target Date and Order assignment: select a cell and drag the
  small orange square down (or Ctrl+D) to copy its value into the rows below.
- **Neat tables in the Order explorer**: Milestones, Pricing, Notes and every other tab show their
  tables as real tables with a "Copy table" button; completed milestones in green, open ones past
  their target date in red.

## 2.4.0
- **Dark mode**: Settings > Appearance, or "Dark mode" at the bottom of the side menu (GOLD Express
  restarts to switch).
- **Ask GOLD history**: chats are saved and listed on the left, grouped by the order numbers they
  mention. Click one to see it again and carry on asking; right-click to delete; "Save chats" to turn
  it off.
- Ask GOLD: a smaller message box (one line, growing as you type) and a smaller send button.
- Revised Target Date and Order assignment: a **running timer** while orders are processed - total
  time, which order is being worked on and for how long, and a progress bar; each result shows how
  long that order took.

## 2.3.0
- **Overview** now looks like My Orders: colourful counters (Orders, On track, Due soon, Late,
  Lead time at risk - click one to jump to that order), an Orders tile and an Order details tile.
- **New update window** in the app's style: what's new, Later / Update now, and a progress bar.
  The "up to date" and error messages match the app too.
- **Windows notifications** (Settings > Notifications, all on by default):
  - My orders: new orders, status changes and moved target dates (checked every 30 minutes while
    you are not using GOLD Express; 15 / 60 / 120 possible).
  - A daily reminder of late orders and orders due within 7 days.
  - A new version of GOLD Express is available.
  - A long task has finished while you were working in another window.

## 2.2.1
- **Smaller, lighter buttons**, fields and selectors everywhere.
- **Compact cards** on the Overview and My Orders: about half the height, so the tables and details
  get more room.

## 2.2.0
- New **My Orders** dashboard (first page in the menu): every order GOLD lists under "My orders
  only", read from all result pages as soon as GOLD Express is connected.
  - Colourful counters: My orders, In progress, Due in 30 days, Past target date, Customers.
  - Orders by status (ring chart) and orders per customer (bars).
  - The orders: customer name, customer site ref, order status and target date; search, Open /
    Closed / All, late orders in red. Click a counter, a status or a customer to filter.
  - Double-click an order to open it in the Order explorer; right-click for Overview, Ask GOLD or
    copy; export to Excel (with service, site, BAN and more).

## 2.1.0
- **Softer, rounder design.** Every page is now made of separate rounded tiles with a soft shadow.
- Pill-shaped buttons, rounded fields and drop-downs, rounded selectors and checkboxes, and slim
  rounded scrollbars.
- The side menu highlights the current page with a rounded pill; the status is a rounded badge.
- Ask GOLD: rounded chat bubbles, rounded suggestion cards, and a rounded message box with a round
  send button.

## 2.0.1
- Fixed: on some company networks the update check said "You have the latest version" although a
  newer one was published. It now tries three ways to read GitHub and says so when it cannot,
  instead of reporting no update. The message also shows the newest version found.

## 2.0.0
- **A fresh new look.** A neat side menu replaces the tabs, grouped into Orders (Overview, Order
  explorer, Ask GOLD), Bulk updates (Revised Target Date, Order assignment) and People (Org Chart,
  DPM names), with icons and a clear page title.
- **New logo** and app icon.
- Light, warm design with rounded panels, rounded buttons and fields, and calmer tables.
- **Colourful Overview**: counters for all orders read (On track / Due soon / Late) and gradient
  cards for order value, delivery status and lead time.

## 1.9.1
- Fixed: the **Update** button could stop responding when it was clicked while GOLD Express was
  still busy (e.g. connecting to GOLD at start-up). Now the update starts as soon as the current
  action has finished.
- Unexpected errors are now shown (and saved to gold_app_error.log) instead of nothing happening.

## 1.9.0
- New **Org Chart** tab: find anyone at Orange Business by name, last name, email or CUID and see
  their email, job, department, phone, location and who they report to (click a manager to open
  them). Names written the GOLD way ("ahmed elbourgy") are found too.
- **Order team**: one click looks up the people on the open order's GOLD teams (primary members and
  small teams; tick "all members" for everyone) with their email and manager.
- Order explorer > Teams: **double-click a member** to see them in the Org Chart.
- Ask GOLD can now look people up: "what is the email of the STM's manager?"

## 1.8.0
- **Ask GOLD knows your order.** It answers about the order open (or typed) in the Order explorer:
  just ask "what are the deadlines?" or "who is the STM?". One click on a suggestion card
  (Deadlines, Pricing, Site, People) asks about that order straight away.
- **New chat design**: your questions in bubbles, answers with clean tables, headings and a source
  line, a "Copy answer" link under each answer (tables paste into Excel as columns), and a live
  "Reading Milestones..." indicator while GOLD is read.
- **No setup**: the first question gets the team's AI key automatically from the team SharePoint
  folder (with your Windows / Orange sign-in) and keeps it on your PC, encrypted for your Windows
  account. A synced copy of the folder is still used when present.

## 1.7.0
- New **Ask GOLD** tab: an AI assistant (Claude) for your orders. Ask in plain words - "what are the
  deadlines of 10-1771012?", "show the pricing details", "site address and STM?", "compare these
  two orders" - and it reads GOLD for you and answers with tables and lists. Follow-up questions
  remember the order. Right-click a table to copy it into Excel. It only reads GOLD, never changes it.
- Uses the team's AI key file (synced from the team SharePoint folder); choose another one in
  Settings > AI assistant.

## 1.6.0
- **Much faster.** Opening an order takes about 5 seconds instead of 25-45, tabs open in 1-3 seconds,
  and Teams / Documents appear instantly. GOLD Express signs in to GOLD in the background as soon
  as it starts, so the first order opens straight away.
- **Overview reads several orders side by side** (up to 3 GOLD sessions; can be turned off in Settings),
  and orders read in the last 10 minutes are shown again instantly. New **Refresh** button.

## 1.5.1
- The update check now works reliably on shared office networks (it no longer depends on GitHub's
  limited API), and shows the release notes instantly.

## 1.5.0
- **Updates from inside the app**: GOLD Express checks for new versions at start-up. When one is
  available the "Update" button in the top bar turns orange - one click downloads it, updates the
  app and opens it again. Your settings and files are kept.

## 1.4.0
- Bulk Order Assignment: pick the STM from a **DPM dropdown** (type to filter).
- New **DPM Names** tab: add, edit, delete, import / export names, and check them in GOLD
  (stores the exact GOLD name and user ID; a user ID picks the right person when two GOLD users
  share a name).

## 1.3.0
- Overview: **order total value** card (new monthly charge x term + one-off) and a
  **120-day lead-time** status (planned delivery vs contract signature + 120 days).
- **Reconnects by itself** after the network drops - no need to restart the app.

## 1.2.0
- New **Overview** tab: key facts of one or more orders with a Red / Amber / Green delivery
  status, exportable to a management-ready Excel.

## 1.1.1
- Copyright notice in the setup wizard and the app.

## 1.1.0
- New **Bulk Order Assignment** tab: make a person the primary STM of many orders.

## 1.0.0
- First release: Order explorer (tabs, screenshots, documents, teams, Excel export) and bulk
  Revised Target Date updates, with a setup wizard.
