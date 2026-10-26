# GOLD Express - what's new

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
