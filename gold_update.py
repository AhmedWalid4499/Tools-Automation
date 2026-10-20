"""In-app updates from GitHub Releases.

A release is published on https://github.com/AhmedWalid4499/Tools-Automation/releases with the tag
v<version> (e.g. v1.5.0) and the setup file GOLD_Express_Setup_<version>.exe attached
(build_release.py --publish does this). The app compares that version with its own, downloads the
setup and runs it silently: it upgrades the installed app in place (settings and data are kept)
and starts it again.
"""
import json
import os
import re
import subprocess
import sys
import tempfile
import urllib.request
from pathlib import Path

from version import __version__

REPO = "AhmedWalid4499/Tools-Automation"
LATEST_URL = f"https://api.github.com/repos/{REPO}/releases/latest"
RELEASES_PAGE = f"https://github.com/{REPO}/releases"
HEADERS = {"User-Agent": f"GOLD-Express/{__version__}", "Accept": "application/vnd.github+json"}


def _vtuple(v):
    return tuple(int(x) for x in re.findall(r"\d+", v)[:3]) or (0,)


def is_newer(remote, local=__version__):
    return _vtuple(remote) > _vtuple(local)


def latest_release(timeout=15):
    """The newest published release: {version, notes, url, name, size, page} or None if none yet."""
    req = urllib.request.Request(LATEST_URL, headers=HEADERS)
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            data = json.loads(r.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        if e.code == 404:
            return None  # no release published yet
        raise
    asset = next((a for a in data.get("assets", [])
                  if a["name"].lower().startswith("gold_express_setup") and a["name"].lower().endswith(".exe")),
                 None)
    if not asset:
        return None
    return {"version": data.get("tag_name", "").lstrip("vV"), "notes": (data.get("body") or "").strip(),
            "url": asset["browser_download_url"], "name": asset["name"], "size": asset.get("size", 0),
            "page": data.get("html_url", RELEASES_PAGE)}


def check():
    """(release, newer?) - release is None when nothing is published."""
    rel = latest_release()
    return rel, bool(rel and is_newer(rel["version"]))


def download(release, progress=None):
    """Download the setup to a temp folder. progress(done_bytes, total_bytes)."""
    dest = Path(tempfile.gettempdir()) / "GOLD Express update" / release["name"]
    dest.parent.mkdir(parents=True, exist_ok=True)
    req = urllib.request.Request(release["url"], headers={"User-Agent": HEADERS["User-Agent"]})
    with urllib.request.urlopen(req, timeout=60) as r, open(dest, "wb") as f:
        total = int(r.headers.get("Content-Length") or release.get("size") or 0)
        done = 0
        while True:
            chunk = r.read(256 * 1024)
            if not chunk:
                break
            f.write(chunk)
            done += len(chunk)
            if progress:
                progress(done, total)
    if release.get("size") and dest.stat().st_size != release["size"]:
        raise RuntimeError("the download is incomplete - please try again")
    return dest


def can_self_update():
    """Only the installed app (GOLD Express.exe) updates itself; the source version uses git pull."""
    return bool(getattr(sys, "frozen", False))


def run_installer(setup):
    """Start the setup silently (shows a small progress window). It closes this app, upgrades the
    installed copy in place, and starts GOLD Express again when done."""
    flags = 0x00000008 | 0x00000200  # DETACHED_PROCESS | CREATE_NEW_PROCESS_GROUP
    subprocess.Popen([str(setup), "/SILENT", "/SUPPRESSMSGBOXES", "/NORESTART", "/CURRENTUSER",
                      "/CLOSEAPPLICATIONS", "/NOCANCEL"], creationflags=flags, close_fds=True,
                     cwd=os.path.dirname(str(setup)))
