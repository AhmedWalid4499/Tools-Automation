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
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

from version import __version__

REPO = "AhmedWalid4499/Tools-Automation"
RELEASES_PAGE = f"https://github.com/{REPO}/releases"
HEADERS = {"User-Agent": f"GOLD-Express/{__version__}", "Accept": "application/vnd.github+json"}


def _vtuple(v):
    return tuple(int(x) for x in re.findall(r"\d+", v)[:3]) or (0,)


def is_newer(remote, local=__version__):
    return _vtuple(remote) > _vtuple(local)


class _NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, *args, **kwargs):
        return None


TAG_RE = re.compile(r"/releases/tag/([^/?#\"'<>\s]+)")


def _redirect_tag(timeout):
    """'v1.5.0' from where github.com/<repo>/releases/latest redirects to. Unlike the GitHub API
    (60 requests per hour per IP - shared by a whole office), this page has no such limit."""
    opener = urllib.request.build_opener(_NoRedirect)
    req = urllib.request.Request(f"{RELEASES_PAGE}/latest", headers={"User-Agent": HEADERS["User-Agent"]})
    try:
        opener.open(req, timeout=timeout)
    except urllib.error.HTTPError as e:
        m = TAG_RE.search(e.headers.get("Location", "") or "")
        if m:
            return urllib.parse.unquote(m.group(1))
    return None


def _followed_tag(timeout):
    """Same page, letting the redirect happen (some company proxies follow redirects themselves)."""
    req = urllib.request.Request(f"{RELEASES_PAGE}/latest", headers={"User-Agent": HEADERS["User-Agent"]})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        m = TAG_RE.search(r.geturl() or "")
        return urllib.parse.unquote(m.group(1)) if m else None


def _feed_tag(timeout):
    """The newest release in github.com's releases feed."""
    req = urllib.request.Request(f"{RELEASES_PAGE}.atom", headers={"User-Agent": HEADERS["User-Agent"]})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        feed = r.read().decode("utf-8", "replace")
    tags = [urllib.parse.unquote(t) for t in TAG_RE.findall(feed)]
    tags = [t for t in tags if re.match(r"v?\d+(\.\d+)*$", t)]
    return max(tags, key=_vtuple) if tags else None


def _latest_tag(timeout):
    """The newest release tag, trying three ways. Raises when none works (e.g. a proxy answers instead
    of GitHub) - never reports "no update" just because GitHub could not be read."""
    problems = []
    for way in (_redirect_tag, _followed_tag, _feed_tag):
        try:
            tag = way(timeout)
            if tag:
                return tag
            problems.append(f"{way.__name__.strip('_')}: no version found")
        except Exception as e:
            problems.append(f"{way.__name__.strip('_')}: {str(e).splitlines()[0][:120] if str(e) else type(e).__name__}")
    raise RuntimeError("GitHub could not be read from this network (" + "; ".join(problems) + ")")


def _notes(tag, version, timeout):
    """Release notes of that release, from github.com's releases feed (raw.githubusercontent.com
    is very slow on some networks)."""
    import html
    url = f"{RELEASES_PAGE}.atom"
    try:
        with urllib.request.urlopen(urllib.request.Request(url, headers={"User-Agent": HEADERS["User-Agent"]}),
                                    timeout=timeout) as r:
            feed = r.read().decode("utf-8")
    except Exception:
        return ""
    for entry in re.findall(r"<entry>(.*?)</entry>", feed, re.S):
        if f"/releases/tag/{tag}" in entry:
            m = re.search(r"<content[^>]*>(.*?)</content>", entry, re.S)
            if not m:
                return ""
            body = html.unescape(m.group(1))                       # the feed holds escaped HTML
            body = re.sub(r"<li>\s*", "- ", body)
            body = re.sub(r"<br\s*/?>|</p>|</li>", "\n", body)
            body = html.unescape(re.sub(r"<[^>]+>", "", body))
            return "\n".join(l.strip() for l in body.splitlines() if l.strip())
    return ""


def latest_release(timeout=15):
    """The newest published release: {version, notes, url, name, size, page} or None if none yet."""
    tag = _latest_tag(timeout)
    version = tag.lstrip("vV")
    name = f"GOLD_Express_Setup_{version}.exe"
    return {"version": version, "notes": _notes(tag, version, timeout),
            "url": f"{RELEASES_PAGE}/download/{tag}/{name}", "name": name, "size": 0,
            "page": f"{RELEASES_PAGE}/tag/{tag}"}


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
