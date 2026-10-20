"""Build a GOLD Express release: app folder (PyInstaller) + setup wizard (Inno Setup).

    python build_release.py             build release\\GOLD_Express_Setup_<version>.exe
    python build_release.py --publish   ... and publish it as GitHub release v<version>, which every
                                        installed GOLD Express offers through its update button

Before a release: bump __version__ in version.py and add a "## <version>" section to CHANGELOG.md
(its text becomes the release notes users see). Installing a newer setup over an older one
upgrades it in place (settings and data are kept). Publishing needs the GitHub CLI, logged in
(gh auth login).
"""
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path

from version import AUTHOR, COPYRIGHT, PUBLISHER, __version__

HERE = Path(__file__).parent
BUILD = Path(os.environ.get("TEMP", HERE)) / "gold_express_build"   # outside OneDrive
APP_DIR = BUILD / "dist" / "GOLD Express"
INSTALLER_DIR = HERE / "installer"
RELEASE = HERE / "release"
ISCC = Path(os.environ["LOCALAPPDATA"]) / "Programs" / "Inno Setup 6" / "ISCC.exe"
NAMES_DEFAULT = HERE / "data" / "dpm_names_default.json"   # private: not in git, packed into the app
REPO = "AhmedWalid4499/Tools-Automation"


def geckodriver():
    """geckodriver.exe next to the scripts, else let Selenium Manager fetch it (not kept in git)."""
    local = HERE / "geckodriver.exe"
    if local.exists():
        return local
    from selenium.webdriver.common.selenium_manager import SeleniumManager
    path = Path(SeleniumManager().binary_paths(["--driver", "geckodriver"])["driver_path"])
    shutil.copy2(path, local)
    return local


def version_file():
    """Windows file properties (Details tab) for GOLD Express.exe."""
    nums = tuple(int(x) for x in (__version__.split(".") + ["0", "0", "0"])[:4])
    text = f"""VSVersionInfo(
  ffi=FixedFileInfo(filevers={nums}, prodvers={nums}, mask=0x3f, flags=0x0, OS=0x40004,
                    fileType=0x1, subtype=0x0, date=(0, 0)),
  kids=[StringFileInfo([StringTable('040904B0', [
      StringStruct('CompanyName', '{PUBLISHER}'),
      StringStruct('FileDescription', 'GOLD Express'),
      StringStruct('FileVersion', '{__version__}'),
      StringStruct('InternalName', 'GOLD Express'),
      StringStruct('LegalCopyright', '{COPYRIGHT}'),
      StringStruct('OriginalFilename', 'GOLD Express.exe'),
      StringStruct('ProductName', 'GOLD Express'),
      StringStruct('ProductVersion', '{__version__}')])]),
    VarFileInfo([VarStruct('Translation', [1033, 1200])])]
)"""
    path = BUILD / "file_version_info.txt"
    path.write_text(text, encoding="utf-8")
    return path


def wizard_art():
    """Branded bitmaps for the setup wizard (black + orange, like the app)."""
    from PIL import Image, ImageDraw, ImageFont
    INSTALLER_DIR.mkdir(exist_ok=True)
    black, orange, grey = (17, 17, 17), (255, 121, 0), (156, 163, 175)

    def font(size, bold=True):
        for name in (("segoeuib.ttf" if bold else "segoeui.ttf"), "arialbd.ttf", "arial.ttf"):
            try:
                return ImageFont.truetype(name, size)
            except OSError:
                pass
        return ImageFont.load_default()

    # Large side image shown on the Welcome and Finish pages (164x314 at 100% scaling).
    for scale in (1, 1.25, 1.5, 2, 2.5):
        w, h = int(164 * scale), int(314 * scale)
        img = Image.new("RGB", (w, h), black)
        d = ImageDraw.Draw(img)
        d.rectangle((0, h - int(10 * scale), w, h), fill=orange)
        s = int(56 * scale)
        x0, y0 = int(22 * scale), int(34 * scale)
        d.rounded_rectangle((x0, y0, x0 + s, y0 + s), radius=int(9 * scale), fill=orange)
        f = font(int(26 * scale))
        tw = d.textlength("GX", font=f)
        d.text((x0 + (s - tw) / 2, y0 + s / 2), "GX", font=f, fill="white", anchor="lm")
        d.text((x0, y0 + s + int(24 * scale)), "GOLD", font=font(int(30 * scale)), fill="white")
        d.text((x0, y0 + s + int(58 * scale)), "Express", font=font(int(30 * scale)), fill=orange)
        d.text((x0, y0 + s + int(104 * scale)), "Global Order Lifecycle", font=font(int(10 * scale), False),
               fill=grey)
        d.text((x0, y0 + s + int(118 * scale)), "Delivery", font=font(int(10 * scale), False), fill=grey)
        d.text((x0, h - int(62 * scale)), f"Version {__version__}", font=font(int(9 * scale), False), fill=grey)
        d.text((x0, h - int(46 * scale)), f"\u00a9 2026 {AUTHOR}", font=font(int(9 * scale), False), fill="white")
        img.save(INSTALLER_DIR / f"wizard_large_{int(scale * 100)}.bmp")

    # Small image in the top-right corner of the inner pages (55x55 at 100%).
    for scale in (1, 1.25, 1.5, 2, 2.5):
        s = int(55 * scale)
        img = Image.new("RGB", (s, s), "white")
        d = ImageDraw.Draw(img)
        pad = int(4 * scale)
        d.rounded_rectangle((pad, pad, s - pad, s - pad), radius=int(8 * scale), fill=black)
        d.rectangle((pad, s - pad - int(8 * scale), s - pad, s - pad), fill=orange)
        f = font(int(19 * scale))
        g = d.textlength("G", font=f)
        tw = d.textlength("GX", font=f)
        x = (s - tw) / 2
        y = s / 2 - int(3 * scale)
        d.text((x, y), "G", font=f, fill="white", anchor="lm")
        d.text((x + g, y), "X", font=f, fill=orange, anchor="lm")
        img.save(INSTALLER_DIR / f"wizard_small_{int(scale * 100)}.bmp")


def build_app():
    if APP_DIR.exists():
        shutil.rmtree(APP_DIR)
    subprocess.run([
        sys.executable, "-m", "PyInstaller", "--noconfirm", "--onedir", "--windowed",
        "--name", "GOLD Express",
        "--icon", str(HERE / "gold_express.ico"),
        "--version-file", str(version_file()),
        "--add-binary", f"{geckodriver()};.",
        "--add-data", f"{HERE / 'gold_express.ico'};.",
        *(["--add-data", f"{NAMES_DEFAULT};."] if NAMES_DEFAULT.exists() else []),
        "--collect-submodules", "selenium",
        "--workpath", str(BUILD / "work"), "--specpath", str(BUILD), "--distpath", str(BUILD / "dist"),
        str(HERE / "gold_app.py"),
    ], check=True)
    exe = APP_DIR / "GOLD Express.exe"
    if not exe.exists():
        sys.exit("PyInstaller did not produce GOLD Express.exe")
    return exe


def build_installer():
    if not ISCC.exists():
        sys.exit(f"Inno Setup not found at {ISCC}. Install it: winget install JRSoftware.InnoSetup --scope user")
    RELEASE.mkdir(exist_ok=True)
    subprocess.run([str(ISCC), f"/DAppVersion={__version__}", f"/DAppPublisher={PUBLISHER}", f"/DAppCopyright={COPYRIGHT}", f"/DAppAuthor={AUTHOR}",
                    f"/DAppSource={APP_DIR}", f"/O{RELEASE}", str(INSTALLER_DIR / "gold_express.iss")],
                   check=True)
    setup = RELEASE / f"GOLD_Express_Setup_{__version__}.exe"
    print(f"\nRelease ready: {setup}  ({setup.stat().st_size / 1e6:.1f} MB)")
    return setup


def release_notes():
    """The '## <version>' section of CHANGELOG.md."""
    text = (HERE / "CHANGELOG.md").read_text(encoding="utf-8") if (HERE / "CHANGELOG.md").exists() else ""
    m = re.search(rf"^## {re.escape(__version__)}\b.*?\n(.*?)(?=^## |\Z)", text, re.S | re.M)
    return m.group(1).strip() if m else f"GOLD Express {__version__}"


def publish(setup):
    gh = shutil.which("gh") or next(
        (str(p) for p in [Path(os.environ["ProgramFiles"]) / "GitHub CLI" / "gh.exe",
                          *(Path(os.environ["LOCALAPPDATA"]) / "Microsoft" / "WinGet" / "Packages").glob(
                              "GitHub.cli_*/bin/gh.exe")] if p.exists()), "gh")
    notes = BUILD / "release_notes.md"
    notes.write_text(release_notes(), encoding="utf-8")
    subprocess.run([gh, "release", "create", f"v{__version__}", str(setup), "--repo", REPO,
                    "--title", f"GOLD Express {__version__}", "--notes-file", str(notes), "--latest"],
                   check=True)
    print(f"Published: https://github.com/{REPO}/releases/tag/v{__version__}")


if __name__ == "__main__":
    BUILD.mkdir(parents=True, exist_ok=True)
    if not NAMES_DEFAULT.exists():
        print("NOTE: data/dpm_names_default.json not found - the app will start with an empty DPM list.")
    wizard_art()
    print("App built:", build_app())
    setup = build_installer()
    if "--publish" in sys.argv:
        publish(setup)
