"""The DPM (STM) names list used by Bulk Order Assignment.

Kept per user in <data folder>\\dpm_names.json as [{"first": ..., "last": ...}], seeded from
the built-in list the first time. Names are as they appear in GOLD (first / last name and, when
known, the GOLD user ID); the GOLD search also tolerates other first/last splits.
"""
import json
from pathlib import Path

from open_gold import BUNDLE_DIR, HERE

NAMES_FILE = HERE / "dpm_names.json"

# The starting DPM list (names, GOLD first/last name, GOLD user ID). It is kept out of the public
# source code: data/dpm_names_default.json is git-ignored and packed into the app by build_release.py.
DEFAULT_FILE_NAME = "dpm_names_default.json"


def _default_entries():
    for folder in (BUNDLE_DIR, BUNDLE_DIR / "data", Path(__file__).parent / "data"):
        f = folder / DEFAULT_FILE_NAME
        if f.exists():
            try:
                return json.loads(f.read_text(encoding="utf-8"))
            except ValueError:
                pass
    return []  # no built-in list: users add names in the DPM Names tab


def split_name(full):
    """'Anna Maria Smith' -> ('Anna', 'Maria Smith')."""
    parts = " ".join(str(full).split()).split(" ", 1)
    return (parts[0], parts[1]) if len(parts) == 2 else (parts[0], "")


def full_name(entry):
    return " ".join(x for x in (entry["first"], entry["last"]) if x)


def load():
    try:
        data = json.loads(NAMES_FILE.read_text(encoding="utf-8"))
        return [{**d, "first": d.get("first", "").strip(), "last": d.get("last", "").strip()} for d in data
                if d.get("first") or d.get("last")]  # keeps 'user' (GOLD user ID) and 'check'
    except (OSError, ValueError):
        return save([dict(e) for e in _default_entries()])


def save(names):
    names = sorted(names, key=lambda e: full_name(e).lower())
    NAMES_FILE.parent.mkdir(parents=True, exist_ok=True)
    NAMES_FILE.write_text(json.dumps(names, indent=1, ensure_ascii=False), encoding="utf-8")
    return names


def lookup(names, text):
    """The list entry whose full name matches text (case/space-insensitive), else None."""
    key = " ".join(str(text).split()).lower()
    return next((e for e in names if full_name(e).lower() == key), None)


# ---------- DPM teams (from the Org Chart: Search by Organization > Department "APM ...")
TEAMS = {"APM Europe": "DPM Egypt", "APM APAC": "DPM India", "APM AME": "DPM Brazil"}
NO_TEAM = "Other"


def team_of(entry):
    return entry.get("team") or NO_TEAM


def letters(text):
    """Only the letters, lower case: 'Ahmed El-Bourgy' -> 'ahmedelbourgy' (for forgiving name search)."""
    import re
    return re.sub(r"[^a-z]", "", str(text).lower())


def matches(name, typed):
    """Does a name fit what was typed? 'elbourgy', 'el bourgy', 'ahmed bour', 'Bourgy Ahmed' all fit
    'Ahmed El Bourgy': every typed word, or the whole text without spaces, is part of the name."""
    n = letters(name)
    words = [letters(w) for w in str(typed).split()]
    words = [w for w in words if w]
    return not words or letters(typed) in n or all(w in n for w in words)


def same_person_name(a, b):
    """The same name, written differently: spaces, hyphens, capitals or first/last order."""
    wa, wb = str(a).split(), str(b).split()
    if not wa or not wb:
        return False
    return letters(a) == letters(b) or (len(wb) > 1 and letters(a) == letters(" ".join(wb[1:] + wb[:1]))) \
        or (len(wb) > 1 and letters(a) == letters(" ".join(wb[-1:] + wb[:-1])))


def from_org_chart(rec, team):
    """An Org Chart record -> a list entry. Display names are 'Maria Julia BENVENUTI' (last name in capitals)."""
    words = str(rec.get("display_name") or "").split()
    first = [w for w in words if not w.isupper()]
    last = [w for w in words if w.isupper()]
    if not first or not last:  # no capitals to go by: the legal names
        first, last = [rec.get("legalFirstName", "")], [rec.get("legalLastName", "")]
    cap = lambda ws: " ".join("-".join(p.capitalize() if p.isupper() else p for p in w.split("-")) for w in ws if w)
    return {"first": cap(first), "last": cap(last),
            "team": team, "email": (rec.get("email") or "").strip().lower()}


def merge_team(names, people):
    """Add Org Chart people (from_org_chart entries) to the list, or set the team of names already in it
    (same email, or the same letters in either name order). Returns (added, updated)."""
    added = updated = 0
    for p in people:
        keys = {letters(p["first"] + p["last"]), letters(p["last"] + p["first"])}
        # same email, else the same name - but never two different emails (different people)
        hit = next((e for e in names if p["email"] and e.get("email") == p["email"]), None) or \
            next((e for e in names if letters(e["first"] + e["last"]) in keys
                  and not (p["email"] and e.get("email") and e["email"] != p["email"])), None)
        if hit:
            if hit.get("team") != p["team"] or (p["email"] and not hit.get("email")):
                hit["team"] = p["team"]
                if p["email"]:
                    hit["email"] = p["email"]
                updated += 1
        else:
            names.append(dict(p))
            added += 1
    return added, updated
