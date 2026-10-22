"""Show Claude's markdown answers in a tkinter Text widget: headings, bullet and numbered lists,
bold / italic / code, quotes, code blocks, rules, and tables (as real grids, right-click to copy)."""
import re
import tkinter as tk

INLINE = re.compile(r"(\*\*[^*]+\*\*|__[^_]+__|`[^`]+`|\*[^*\s][^*]*\*)")
TABLE_SEP = re.compile(r"^\s*\|?\s*:?-{2,}:?\s*(\|\s*:?-{2,}:?\s*)*\|?\s*$")
BULLET = re.compile(r"^(\s*)[-*•]\s+(.*)$")
NUMBERED = re.compile(r"^(\s*)(\d+)[.)]\s+(.*)$")
HEADING = re.compile(r"^(#{1,4})\s+(.*?)\s*#*$")


def setup(text, font="Segoe UI", ink="#1F2328", muted="#6B7280", accent="#FF7900", soft="#FFE8D6",
          line="#E2E4E8", code_bg=None, indent=0, size=10, card=None, zebra=None):
    """Create the tags render() uses (call once per Text widget). indent: left margin of the
    whole answer in pixels (e.g. to line it up under the assistant's name). card / zebra / code_bg:
    table and code colours (default: the app's theme)."""
    import gold_ui as gui
    code_bg = code_bg or gui.TRACK
    text.md = dict(font=font, ink=ink, muted=muted, accent=accent, soft=soft, line=line, code_bg=code_bg,
                   indent=indent, card=card or gui.CARD, zebra=zebra or gui.ZEBRA)
    m = indent + 2
    text.tag_configure("p", font=(font, size), foreground=ink, spacing1=2, spacing3=5, lmargin1=m, lmargin2=m,
                       rmargin=24)
    text.tag_configure("b", font=(font, size, "bold"))
    text.tag_configure("i", font=(font, size, "italic"))
    text.tag_configure("code", font=("Consolas", size - 1), background=code_bg)
    text.tag_configure("h1", font=(font, size + 3, "bold"), foreground=ink, spacing1=12, spacing3=4,
                       lmargin1=m, lmargin2=m)
    text.tag_configure("h2", font=(font, size + 2, "bold"), foreground=ink, spacing1=12, spacing3=4,
                       lmargin1=m, lmargin2=m)
    text.tag_configure("h3", font=(font, size + 1, "bold"), foreground=ink, spacing1=10, spacing3=3,
                       lmargin1=m, lmargin2=m)
    text.tag_configure("quote", foreground=muted, lmargin1=m + 14, lmargin2=m + 14, font=(font, size, "italic"))
    text.tag_configure("pre", font=("Consolas", size - 1), background=code_bg, lmargin1=m + 10,
                       lmargin2=m + 10, spacing1=0, spacing3=0)
    for level in range(4):
        text.tag_configure(f"li{level}", lmargin1=m + 6 + 20 * level, lmargin2=m + 24 + 20 * level,
                           spacing1=2, spacing3=3, font=(font, size), foreground=ink, rmargin=24)
    text.tag_configure("mark", foreground=accent, font=(font, size, "bold"))
    text.tag_configure("source", font=(font, size - 2), foreground=muted, lmargin1=m, lmargin2=m, spacing1=8,
                       spacing3=2)
    text.tag_configure("tbl", lmargin1=m, lmargin2=m, spacing1=4, spacing3=6)
    for tag in ("b", "i", "code", "mark"):  # inline styles win over the paragraph / list font
        text.tag_raise(tag)


def _inline(text, s, tags):
    """Insert one line with **bold**, *italic* and `code` spans."""
    for part in INLINE.split(s):
        if not part:
            continue
        if (part.startswith("**") and part.endswith("**")) or (part.startswith("__") and part.endswith("__")):
            text.insert("end", part[2:-2], tags + ("b",))
        elif part.startswith("`") and part.endswith("`"):
            text.insert("end", part[1:-1], tags + ("code",))
        elif part.startswith("*") and part.endswith("*") and len(part) > 2:
            text.insert("end", part[1:-1], tags + ("i",))
        else:
            text.insert("end", part, tags)


def _cells(line):
    line = line.strip()
    if line.startswith("|"):
        line = line[1:]
    if line.endswith("|"):
        line = line[:-1]
    return [c.strip() for c in re.split(r"(?<!\\)\|", line)]


def _plain(s):
    return re.sub(r"\*\*|__|`", "", s).replace("\\|", "|")


def _table(text, rows, width):
    """Embed a table: header row in the accent tint, thin grid lines, wrapped cells."""
    md = text.md
    head, body = rows[0], rows[1:]
    ncol = max(len(r) for r in rows)
    outer = tk.Frame(text, background=md["line"], padx=1, pady=1)
    # Share the width between columns by how much text they hold (short columns stay narrow).
    def cell(row, c):
        return _plain(row[c]) if c < len(row) else ""
    need = [max(min(len(cell(row, c)), 60) for row in rows) + 1 for c in range(ncol)]
    word = [max((len(w) for row in rows for w in cell(row, c).split()), default=1) + 1 for c in range(ncol)]
    room = max(width - md["indent"] - 40 - 18 * ncol, 60 * ncol)
    px = 8  # ~ average character width at 9 pt (bold)
    if sum(need) * px <= room:
        widths = [0] * ncol  # everything fits on one line: no wrapping
    else:
        widths = [max(word[c] * px, int(room * need[c] / sum(need))) for c in range(ncol)]
    for r, row in enumerate([head] + body):
        for c in range(ncol):
            value = row[c] if c < len(row) else ""
            bold = r == 0 or (value.startswith("**") and value.endswith("**"))
            bg = md["soft"] if r == 0 else (md["card"] if r % 2 else md["zebra"])
            lab = tk.Label(outer, text=_plain(value), background=bg, foreground=md["ink"], anchor="nw",
                           justify="left", wraplength=widths[c], padx=8, pady=4,
                           font=(md["font"], 9, "bold" if bold else "normal"))
            lab.grid(row=r, column=c, sticky="nsew", padx=(0, 1), pady=(0, 1))
            lab.bind("<Button-3>", lambda e, rows=rows: _table_menu(text, e, rows))
    idx = text.index("end-1c")
    text.window_create(idx, window=outer)
    text.tag_add("tbl", idx)
    text.insert("end", "\n", ("tbl",))


def _table_menu(text, event, rows):
    menu = tk.Menu(text, tearoff=0)
    tsv = "\n".join("\t".join(_plain(c) for c in row) for row in rows)
    menu.add_command(label="Copy table (paste into Excel)",
                     command=lambda: (text.clipboard_clear(), text.clipboard_append(tsv)))
    menu.tk_popup(event.x_root, event.y_root)


def plain(md_text):
    """The answer as clean text for the clipboard: tables tab-separated (they paste as Excel
    columns), bullets as •, no Markdown marks."""
    out = []
    for line in md_text.strip().splitlines():
        s = line.rstrip()
        if s.lstrip().startswith("|"):
            if not TABLE_SEP.match(s):
                out.append("\t".join(_plain(c) for c in _cells(s)))
            continue
        if re.fullmatch(r"\s*(-{3,}|\*{3,}|_{3,})\s*", s):
            continue
        m = HEADING.match(s.strip())
        if m:
            s = m.group(2)
        s = BULLET.sub(lambda m: m.group(1) + "• " + m.group(2), s)
        out.append(_plain(s))
    return "\n".join(out)


def render(text, md_text, width=900):
    """Append markdown to the Text widget (which must be in 'normal' state)."""
    lines = md_text.replace("\r\n", "\n").split("\n")
    i = 0
    while i < len(lines):
        line = lines[i]
        s = line.strip()
        if s.startswith("```"):
            i += 1
            code = []
            while i < len(lines) and not lines[i].strip().startswith("```"):
                code.append(lines[i])
                i += 1
            text.insert("end", "\n".join(code) + "\n", ("pre",))
            i += 1
            continue
        if s.startswith("|") and i + 1 < len(lines) and TABLE_SEP.match(lines[i + 1]):
            rows = [_cells(line)]
            i += 2
            while i < len(lines) and lines[i].strip().startswith("|"):
                rows.append(_cells(lines[i]))
                i += 1
            _table(text, rows, width)
            continue
        m = HEADING.match(s)
        if m:
            level = min(len(m.group(1)), 3)
            text.insert("end", _plain(m.group(2)) + "\n", (f"h{level}",))
        elif re.fullmatch(r"(-{3,}|\*{3,}|_{3,})", s):
            pass  # horizontal rules: the layout has enough structure without them
        elif BULLET.match(line):
            m = BULLET.match(line)
            level = min(len(m.group(1).replace("\t", "  ")) // 2, 3)
            text.insert("end", ("•", "◦", "▪", "▪")[level] + "  ", (f"li{level}", "mark"))
            _inline(text, m.group(2), (f"li{level}",))
            text.insert("end", "\n", (f"li{level}",))
        elif NUMBERED.match(line):
            m = NUMBERED.match(line)
            level = min(len(m.group(1).replace("\t", "  ")) // 2, 3)
            text.insert("end", f"{m.group(2)}.  ", (f"li{level}", "mark"))
            _inline(text, m.group(3), (f"li{level}",))
            text.insert("end", "\n", (f"li{level}",))
        elif re.match(r"^sources?\s*:", s, re.I):
            text.insert("end", _plain(s) + "\n", ("source",))
        elif s.startswith(">"):
            _inline(text, s.lstrip("> "), ("quote",))
            text.insert("end", "\n", ("quote",))
        elif s:
            _inline(text, s, ("p",))
            text.insert("end", "\n", ("p",))
        i += 1
