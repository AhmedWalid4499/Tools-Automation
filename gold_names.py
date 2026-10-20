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
