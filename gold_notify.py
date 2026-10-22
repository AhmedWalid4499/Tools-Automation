"""Windows notifications (toasts) for GOLD Express, with nothing extra to install.

The toast is shown by Windows' own notification API (Windows.UI.Notifications), called from a hidden
PowerShell. Windows only shows a desktop app's toasts when a Start-menu shortcut carries the app's
AppUserModelID: the installer creates it (installer/gold_express.iss). When running from source there is
no such shortcut, so the toast is sent under PowerShell's id instead (it then says "Windows PowerShell").
"""
import base64
import ctypes
import subprocess
import sys
import threading
from pathlib import Path
from xml.sax.saxutils import escape

APP_ID = "AhmedElBourgy.GOLDExpress"
POWERSHELL_ID = "{1AC14E77-02E7-4E5D-B744-2EB1AE5198B7}\\WindowsPowerShell\\v1.0\\powershell.exe"
FROZEN = getattr(sys, "frozen", False)

SCRIPT = r"""
[Windows.UI.Notifications.ToastNotificationManager, Windows.UI.Notifications, ContentType = WindowsRuntime] | Out-Null
[Windows.Data.Xml.Dom.XmlDocument, Windows.Data.Xml.Dom.XmlDocument, ContentType = WindowsRuntime] | Out-Null
$xml = New-Object Windows.Data.Xml.Dom.XmlDocument
$xml.LoadXml(@'
{xml}
'@)
$toast = New-Object Windows.UI.Notifications.ToastNotification $xml
$toast.Tag = '{tag}'
$toast.Group = 'GOLDExpress'
[Windows.UI.Notifications.ToastNotificationManager]::CreateToastNotifier('{app_id}').Show($toast)
"""


def set_app_id():
    """Call once at start-up: the window groups and notifies under GOLD Express's own id."""
    try:
        ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(APP_ID)
    except Exception:
        pass


def _logo():
    base = Path(getattr(sys, "_MEIPASS", Path(__file__).parent))
    p = base / "assets" / "logo_96.png"
    return p if p.exists() else None


def toast_xml(title, text, attribution=""):
    logo = _logo()
    image = f'<image placement="appLogoOverride" src="{escape(logo.as_uri())}"/>' if logo else ""
    extra = f'<text placement="attribution">{escape(attribution)}</text>' if attribution else ""
    return (f'<toast><visual><binding template="ToastGeneric"><text>{escape(title)}</text>'
            f'<text>{escape(text)}</text>{extra}{image}</binding></visual></toast>')


def notify(title, text, tag="gx", attribution="", wait=False):
    """Show a Windows notification. Never raises; returns True when PowerShell accepted it."""
    app_id = APP_ID if FROZEN else POWERSHELL_ID
    script = SCRIPT.replace("{xml}", toast_xml(title, text, attribution)).replace(
        "{tag}", tag.replace("'", "")[:60]).replace("{app_id}", app_id)
    encoded = base64.b64encode(script.encode("utf-16-le")).decode("ascii")

    def run():
        try:
            r = subprocess.run(["powershell", "-NoProfile", "-NonInteractive", "-ExecutionPolicy", "Bypass",
                                "-EncodedCommand", encoded], capture_output=True, timeout=30,
                               creationflags=0x08000000)  # CREATE_NO_WINDOW
            return r.returncode == 0
        except Exception:
            return False
    if wait:
        return run()
    threading.Thread(target=run, daemon=True).start()
    return True
