"""Order Assignment export: an Excel workbook with a Dashboard sheet (headline numbers + native Excel charts)
and the data behind it (all orders, unassigned, not in the DPM list, per STM).

    export(path, orders, source_line, filter_line)   # orders: gold_assignments.classify()'d dicts
"""
from collections import Counter
from datetime import date, datetime

from openpyxl import Workbook
from openpyxl.chart import BarChart, DoughnutChart, Reference
from openpyxl.chart.label import DataLabelList
from openpyxl.chart.series import DataPoint
from openpyxl.chart.shapes import GraphicalProperties
from openpyxl.drawing.line import LineProperties
from openpyxl.styles import Alignment, Border, Font, PatternFill, Side
from openpyxl.utils import get_column_letter

import gold_assignments as gas

ORANGE, INK, MUTED, LINE, SOFT = "FF7900", "1F2328", "6B7280", "E5E7EB", "FFF4EB"
COLOURS = {gas.ASSIGNED: "22A06B", gas.UNASSIGNED: "E5484D", gas.NOT_IN_LIST: "F59E0B"}
REGION_COLOURS = ("1F86E0", "8A3FB8", "128577", "9AA5B1", "DD3F58")
FONT = "Segoe UI"
thin = Side(style="thin", color=LINE)

ORDER_COLUMNS = [("Order", "order"), ("Status", "status"), ("Type", "type"), ("Customer", "customer"),
                 ("End customer", "end_customer"), ("STM (DPM)", "dpm"), ("Assignment", "category"),
                 ("Region", "region"), ("DPM team", "team"), ("Target date", "target"),
                 ("Initial target date", "ittd"), ("Revised target date", "rtdd"), ("Days to due", "due_days"),
                 ("Backlog", "backlog"), ("Order age (days)", "age"), ("Cust. site ref", "site_ref"),
                 ("Country", "country"), ("Sales cluster", "cluster"), ("Service", "service"),
                 ("Project", "project")]


_overdue = gas.is_overdue
F_CELL = Font(name=FONT, size=9, color=INK)
F_HEAD = Font(name=FONT, size=9, bold=True, color="FFFFFF")
FILL_HEAD = PatternFill("solid", fgColor=ORANGE)
F_CAT = {k: Font(name=FONT, size=9, bold=True, color=c) for k, c in COLOURS.items()}


def _value(v):
    return v.strftime("%d-%b-%Y") if isinstance(v, (date, datetime)) else ("" if v is None else v)


def _table(ws, top, left, title, columns, rows, widths=None, total=False):
    """A small styled table; returns (first data row, last data row)."""
    ws.cell(top, left, title).font = Font(name=FONT, size=11, bold=True, color=INK)
    for j, c in enumerate(columns):
        cell = ws.cell(top + 1, left + j, c)
        cell.font = Font(name=FONT, size=9, bold=True, color="FFFFFF")
        cell.fill = PatternFill("solid", fgColor=ORANGE)
        cell.alignment = Alignment(horizontal="left" if j == 0 else "right", vertical="center")
    for i, r in enumerate(rows):
        for j, v in enumerate(r):
            cell = ws.cell(top + 2 + i, left + j, v)
            cell.font = Font(name=FONT, size=9, color=INK, bold=total and i == len(rows) - 1)
            cell.border = Border(bottom=thin)
            cell.alignment = Alignment(horizontal="left" if j == 0 else "right")
            if isinstance(v, float):
                cell.number_format = "0.0"
            if i % 2:
                cell.fill = PatternFill("solid", fgColor="FAFAFA")
    return top + 2, top + 1 + len(rows)


def _kpi(ws, row, col, caption, value, sub, colour):
    """A coloured headline tile over 2 columns x 3 rows."""
    fill = PatternFill("solid", fgColor=colour)
    for r in range(row, row + 3):
        for c in range(col, col + 2):
            ws.cell(r, c).fill = fill
    ws.merge_cells(start_row=row, start_column=col, end_row=row, end_column=col + 1)
    ws.merge_cells(start_row=row + 1, start_column=col, end_row=row + 1, end_column=col + 1)
    ws.merge_cells(start_row=row + 2, start_column=col, end_row=row + 2, end_column=col + 1)
    a = ws.cell(row, col, caption.upper())
    a.font = Font(name=FONT, size=8, bold=True, color="FFFFFF")
    a.alignment = Alignment(horizontal="left", vertical="bottom", indent=1)
    b = ws.cell(row + 1, col, value)
    b.font = Font(name=FONT, size=20, bold=True, color="FFFFFF")
    b.alignment = Alignment(horizontal="left", vertical="center", indent=1)
    b.number_format = "#,##0"
    c = ws.cell(row + 2, col, sub)
    c.font = Font(name=FONT, size=8, color="FFFFFF")
    c.alignment = Alignment(horizontal="left", vertical="top", indent=1)


def _labels(value=True, percent=False):
    """Data labels with just the number (or %), not 'series, category, value'."""
    d = DataLabelList()
    d.showVal, d.showPercent = value, percent
    d.showSerName = d.showCatName = d.showLegendKey = d.showLeaderLines = False
    return d


def _bar(ws, title, cats, data, anchor, colour=ORANGE, horizontal=True, height=7.5, width=15.5, stacked=None):
    ch = BarChart()
    ch.type = "bar" if horizontal else "col"
    ch.title = title
    ch.style = 10
    ch.height, ch.width = height, width
    ch.legend = None if not stacked else ch.legend
    if stacked:
        ch.grouping = "stacked"
        ch.overlap = 100
        ch.legend.position = "b"
    ch.add_data(data, titles_from_data=True)
    ch.set_categories(cats)
    for i, s in enumerate(ch.series):
        s.graphicalProperties.solidFill = stacked[i] if stacked else colour
        s.graphicalProperties.line.solidFill = stacked[i] if stacked else colour
    if not stacked:
        ch.dataLabels = _labels()
    ch.y_axis.delete = False
    ch.x_axis.delete = False
    if horizontal:
        ch.y_axis.majorGridlines = None
        ch.y_axis.delete = True  # the bars carry their numbers
        ch.x_axis.scaling.orientation = "maxMin"  # biggest first, at the top
    elif ch.y_axis.majorGridlines is not None:
        ch.y_axis.majorGridlines.spPr = GraphicalProperties(ln=LineProperties(solidFill=LINE))
    _title_above(ch)
    if stacked:
        ch.legend.position = "t"
    ws.add_chart(ch, anchor)


def _title_above(ch):
    """Keep the title above the plot instead of over the bars."""
    if ch.title is not None:
        ch.title.overlay = False


def export(path, orders, source_line="", filter_line=""):
    s = gas.summary(orders)
    wb = Workbook()
    ws = wb.active
    ws.title = "Dashboard"
    ws.sheet_view.showGridLines = False
    for c in range(1, 30):
        ws.column_dimensions[get_column_letter(c)].width = 11.5

    # --- title
    ws["B2"] = "APM Open Orders - Order Assignment"
    ws["B2"].font = Font(name=FONT, size=18, bold=True, color=INK)
    ws["B3"] = "  ·  ".join(x for x in (source_line, filter_line,
                                         f"exported {datetime.now():%d-%b-%Y %H:%M}") if x)
    ws["B3"].font = Font(name=FONT, size=9, color=MUTED)
    ws.row_dimensions[2].height = 30

    # --- headline numbers
    total = max(s["total"], 1)
    overdue = sum(1 for o in orders if _overdue(o))
    un_overdue = sum(1 for o in orders if o["category"] == gas.UNASSIGNED and _overdue(o))
    tiles = [("Open orders", s["total"], f"{overdue:,} overdue", "1F86E0"),
             ("Assigned to DPMs", s["assigned"], f"{s['assigned'] * 100 / total:.0f}% of the orders", "22A06B"),
             ("Unassigned", s["unassigned"], f"{s['unassigned'] * 100 / total:.0f}%  ·  {un_overdue:,} overdue",
              "E5484D"),
             ("Not in DPM list", s["not_in_list"], f"{s['outsiders']} people", "F59E0B"),
             ("DPMs with orders", s["dpms"],
              f"{s['assigned'] / max(s['dpms'], 1):.0f} orders each on average", "8A3FB8")]
    for i, t in enumerate(tiles):
        _kpi(ws, 5, 2 + i * 3, *t)
    for r in (5, 6, 7):
        ws.row_dimensions[r].height = 20 if r != 6 else 32

    # --- data blocks for the charts (right side, columns T onwards; the charts sit on the left)
    D = 20  # column T
    r = 10
    split = [(gas.ASSIGNED, s["assigned"]), (gas.UNASSIGNED, s["unassigned"]), (gas.NOT_IN_LIST, s["not_in_list"])]
    a1, a2 = _table(ws, r, D, "Assignment", ["Assignment", "Orders", "%"],
                    [[k, v, round(v * 100 / total, 1)] for k, v in split])
    pie = DoughnutChart()
    pie.title = "Who has the orders"
    pie.height, pie.width = 7.5, 11.5
    pie.add_data(Reference(ws, min_col=D + 1, min_row=a1 - 1, max_row=a2), titles_from_data=True)
    pie.set_categories(Reference(ws, min_col=D, min_row=a1, max_row=a2))
    for i, (k, _) in enumerate(split):
        pt = DataPoint(idx=i)
        pt.graphicalProperties.solidFill = COLOURS[k]
        pie.series[0].dPt.append(pt)
    pie.dataLabels = _labels(value=False, percent=True)
    pie.holeSize = 55
    pie.legend.position = "b"
    _title_above(pie)
    ws.add_chart(pie, "B10")

    # orders per region (assigned orders)
    r = a2 + 3
    regions = Counter(o["region"] for o in orders if o["category"] == gas.ASSIGNED)
    region_rows = []
    for reg in [x for x in gas.REGIONS.values() if x in regions] + sorted(set(regions) - set(gas.REGIONS.values())):
        dpms = len({o["dpm"] for o in orders if o["category"] == gas.ASSIGNED and o["region"] == reg})
        od = sum(1 for o in orders if o["category"] == gas.ASSIGNED and o["region"] == reg and _overdue(o))
        team = next((t for t, d in gas.REGIONS.items() if d == reg), "")
        region_rows.append([f"{reg} ({team})" if team else reg, regions[reg], dpms,
                            round(regions[reg] / max(dpms, 1), 1), od])
    b1, b2 = _table(ws, r, D, "Assigned orders per region",
                    ["Region", "Orders", "DPMs", "Orders per DPM", "Overdue"], region_rows)
    if region_rows:
        _bar(ws, "Assigned orders per region", Reference(ws, min_col=D, min_row=b1, max_row=b2),
             Reference(ws, min_col=D + 1, min_row=b1 - 1, max_row=b2), "H10", colour="1F86E0",
             horizontal=False, width=11.5)

    # assignment by order status (stacked)
    r = b2 + 3
    statuses = [k for k, _ in Counter(o.get("status") or "" for o in orders).most_common()]
    by_status = [[st or "(none)"] + [sum(1 for o in orders if (o.get("status") or "") == st and o["category"] == c)
                                     for c in (gas.ASSIGNED, gas.UNASSIGNED, gas.NOT_IN_LIST)] for st in statuses]
    c1, c2 = _table(ws, r, D, "Orders by status", ["Status", gas.ASSIGNED, gas.UNASSIGNED, gas.NOT_IN_LIST],
                    by_status)
    if by_status:
        _bar(ws, "Assignment by order status", Reference(ws, min_col=D, min_row=c1, max_row=c2),
             Reference(ws, min_col=D + 1, max_col=D + 3, min_row=c1 - 1, max_row=c2), "B26",
             stacked=[COLOURS[gas.ASSIGNED], COLOURS[gas.UNASSIGNED], COLOURS[gas.NOT_IN_LIST]],
             horizontal=False, width=23.5, height=7.5)

    # top DPMs
    people = gas.per_person(orders)
    top_dpms = [[n, cnt, od] for n, where, cnt, od in people if where != gas.NOT_IN_LIST][:15]
    r = c2 + 3
    d1, d2 = _table(ws, r, D, "Top 15 DPMs by orders", ["DPM", "Orders", "Overdue"], top_dpms)
    if top_dpms:
        _bar(ws, "Top 15 DPMs by number of orders", Reference(ws, min_col=D, min_row=d1, max_row=d2),
             Reference(ws, min_col=D + 1, min_row=d1 - 1, max_row=d2), "B42", colour="22A06B", height=9.5,
             width=11.5)

    # people not in the DPM list
    outsiders = [[n, cnt, od] for n, where, cnt, od in people if where == gas.NOT_IN_LIST][:15]
    r = d2 + 3
    e1, e2 = _table(ws, r, D, "Top 15 STMs not in the DPM list", ["STM", "Orders", "Overdue"], outsiders)
    if outsiders:
        _bar(ws, "Top 15 STMs not in the DPM list", Reference(ws, min_col=D, min_row=e1, max_row=e2),
             Reference(ws, min_col=D + 1, min_row=e1 - 1, max_row=e2), "H42", colour="F59E0B", height=9.5,
             width=11.5)

    # unassigned orders: by cluster and by age
    un = [o for o in orders if o["category"] == gas.UNASSIGNED]
    clusters = Counter((o.get("cluster") or "(none)") for o in un).most_common(12)
    r = e2 + 3
    f1, f2 = _table(ws, r, D, "Unassigned orders by sales cluster (top 12)", ["Sales cluster", "Orders"],
                    [list(x) for x in clusters])
    if clusters:
        _bar(ws, "Unassigned orders by sales cluster", Reference(ws, min_col=D, min_row=f1, max_row=f2),
             Reference(ws, min_col=D + 1, min_row=f1 - 1, max_row=f2), "B61", colour="E5484D", height=9,
             width=11.5)
    buckets = [("0-30 days", 0, 30), ("31-90 days", 31, 90), ("91-180 days", 91, 180), ("181-365 days", 181, 365),
               ("Over a year", 366, 10 ** 9)]
    ages = [[label, sum(1 for o in un if isinstance(o.get("age"), (int, float)) and lo <= o["age"] <= hi)]
            for label, lo, hi in buckets]
    r = f2 + 3
    g1, g2 = _table(ws, r, D, "Unassigned orders by order age", ["Order age", "Orders"], ages)
    _bar(ws, "Unassigned orders by order age", Reference(ws, min_col=D, min_row=g1, max_row=g2),
         Reference(ws, min_col=D + 1, min_row=g1 - 1, max_row=g2), "H61", colour="E5484D", horizontal=False,
         height=9, width=11.5)
    ws.column_dimensions[get_column_letter(D)].width = 30
    ws.cell(r + len(ages) + 4, D, "The charts on the left are drawn from these tables.").font = \
        Font(name=FONT, size=8, italic=True, color=MUTED)

    # --- data sheets
    def order_sheet(title, rows, note):
        sh = wb.create_sheet(title)
        sh.sheet_view.showGridLines = False
        sh["A1"] = title
        sh["A1"].font = Font(name=FONT, size=14, bold=True, color=INK)
        sh["A2"] = note
        sh["A2"].font = Font(name=FONT, size=9, color=MUTED)
        for j, (h, _) in enumerate(ORDER_COLUMNS, 1):
            c = sh.cell(4, j, h)
            c.font, c.fill = F_HEAD, FILL_HEAD
        for i, o in enumerate(rows, 5):  # values only (fast); the sheet's default font is set below
            for j, (_, k) in enumerate(ORDER_COLUMNS, 1):
                sh.cell(i, j, _value(o.get(k)))
            cat = o["category"]
            if cat != gas.ASSIGNED:
                sh.cell(i, 7).font = F_CAT[cat]
        sh.freeze_panes = "B5"
        if rows:
            sh.auto_filter.ref = f"A4:{get_column_letter(len(ORDER_COLUMNS))}{4 + len(rows)}"
        for j, (h, k) in enumerate(ORDER_COLUMNS, 1):
            longest = max([len(h)] + [len(str(_value(o.get(k)))) for o in rows[:300]])
            sh.column_dimensions[get_column_letter(j)].width = min(max(longest + 2, 9), 42)

    by_target = lambda o: (o.get("target") or date.max) if isinstance(o.get("target"), date) else date.max
    order_sheet("All orders", sorted(orders, key=by_target), f"{len(orders):,} orders  ·  {source_line}")
    order_sheet("Unassigned", sorted(un, key=by_target), f"{len(un):,} orders without an STM")
    nl = [o for o in orders if o["category"] == gas.NOT_IN_LIST]
    order_sheet("Not in DPM list", sorted(nl, key=lambda o: (o["dpm"].lower(), by_target(o))),
                f"{len(nl):,} orders whose STM is not in the DPM list ({s['outsiders']} people) - add them in "
                "GOLD Express > DPM names if they are DPMs")

    sh = wb.create_sheet("Per STM")
    sh.sheet_view.showGridLines = False
    sh["A1"] = "Orders per STM"
    sh["A1"].font = Font(name=FONT, size=14, bold=True, color=INK)
    rows = [[n, where if where != gas.NOT_IN_LIST else "", "In DPM list" if where != gas.NOT_IN_LIST
             else gas.NOT_IN_LIST, cnt, od] for n, where, cnt, od in people]
    _table(sh, 3, 1, f"{len(rows)} people", ["STM", "Region", "DPM list", "Orders", "Overdue"], rows)
    for col, w in zip("ABCDE", (32, 16, 18, 10, 10)):
        sh.column_dimensions[col].width = w
    sh.freeze_panes = "A5"

    path.parent.mkdir(parents=True, exist_ok=True)
    wb.save(path)
    return path
