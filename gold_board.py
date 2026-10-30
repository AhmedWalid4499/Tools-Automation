"""Clickable dashboards: charts that filter each other, like slicers in Power BI.

A Board holds the orders and what has been clicked ({dimension: value}). Each chart shows the orders that fit
every click except its own, so the clicked slice stays highlighted next to the others and another one can be
picked. board.chosen() is what fits all the clicks, for the cards and tables around the charts.

    board = Board(gas.order_dims, on_change)      # dims(order) -> {dimension: value}
    board.donut(parent, "status", colours)
    board.bars(parent, "stage", colours, rows=6)
    board.set_orders(orders); board.refresh()
"""
import tkinter as tk
from collections import Counter

import gold_ui as gui

CARD, INK, MUTED = gui.CARD, gui.INK, gui.MUTED
FONT = gui.FONT


class Board:
    def __init__(self, dims, on_change):
        self.dims, self.on_change = dims, on_change
        self.selected, self.rows, self.charts = {}, [], []

    def set_orders(self, orders):
        self.rows = [(o, self.dims(o)) for o in orders]

    def _fits(self, d, skip=None):
        return all(d.get(k) == v for k, v in self.selected.items() if k != skip)

    def chosen(self):
        """The orders that fit every click."""
        return [o for o, d in self.rows if self._fits(d)]

    def without(self, dim):
        """The orders that fit every click but those on dim: what a chart of dim shows."""
        return [o for o, d in self.rows if self._fits(d, dim)]

    def toggle(self, dim, value):
        """A click: pick the value, or drop it when it was picked already."""
        if self.selected.get(dim) == value:
            del self.selected[dim]
        else:
            self.selected[dim] = value
        self.on_change()

    def choose(self, dim, value):
        self.selected[dim] = value
        self.on_change()

    def clear(self):
        self.selected.clear()
        self.on_change()

    def text(self):
        """What is clicked, for a chip."""
        return "  ·  ".join(v or "(not known)" for v in self.selected.values())

    def refresh(self):
        for draw in self.charts:
            draw()

    def _counts(self, dim):
        return Counter(d.get(dim) for o, d in self.rows if self._fits(d, dim))

    def donut(self, parent, dim, colours, note=None, unit="orders"):
        """A ring and its legend, for a few fixed values. note(value, orders) adds to a legend line."""
        row = tk.Frame(parent, background=CARD)
        row.pack(fill="x")
        ring = gui.Donut(row, on_click=lambda v: self.toggle(dim, v))
        ring.pack(side="left", padx=(0, 14))
        legend = tk.Frame(row, background=CARD)
        legend.pack(side="left", fill="x", expand=True)

        def draw():
            counts = self._counts(dim)
            picked = self.selected.get(dim)
            items = [(k, counts.get(k, 0), c) for k, c in colours.items()]
            ring.set(items, f"{sum(v for _, v, _ in items):,}", unit, selected=picked)
            for w in legend.winfo_children():
                w.destroy()
            for k, v, colour in items:
                r = tk.Frame(legend, background=CARD, cursor="hand2")
                r.pack(fill="x", pady=1)
                faded = picked is not None and picked != k
                dot = tk.Label(r, text="●", bg=CARD, fg=gui.mix(colour, gui.TRACK, 0.6) if faded else colour,
                               font=(FONT, 11))
                dot.pack(side="left", anchor="n")
                text = tk.Frame(r, background=CARD)
                text.pack(side="left", padx=(4, 0), fill="x", expand=True)
                name = tk.Label(text, text=k, bg=CARD, fg=MUTED if faded else INK, anchor="w",
                                font=(FONT, 9, "bold" if picked == k else "normal"))
                name.pack(fill="x")
                extra = note(k, [o for o, d in self.rows if self._fits(d, dim) and d.get(dim) == k]) if note else ""
                line = tk.Label(text, text=f"{v:,}" + (f"  ·  {extra}" if extra else ""), bg=CARD, fg=MUTED,
                                font=(FONT, 8, "bold"), anchor="w")
                line.pack(fill="x")
                for w in (r, dot, text, name, line):
                    w.bind("<Button-1>", lambda e, k=k: self.toggle(dim, k))
        self.charts.append(draw)
        return ring

    def bars(self, parent, dim, colour, rows=6, values=None):
        """Bars, biggest first (or for the fixed values). colour: one colour, or {value: colour}."""
        chart = gui.Bars(parent, rows=rows, on_click=lambda v: self.toggle(dim, v))
        chart.pack(fill="x")
        pick = colour.get if isinstance(colour, dict) else (lambda k, c=colour: c)

        def draw():
            counts = self._counts(dim)
            picked = self.selected.get(dim)
            if values:
                keys = list(values)
            else:
                keys = [k for k, _ in counts.most_common() if k][:rows]
                if picked and picked not in keys:
                    keys[-1:] = [picked]
            chart.set([(k, counts.get(k, 0), pick(k, gui.GREY_FG)) for k in keys], selected=picked)
        self.charts.append(draw)
        return chart
