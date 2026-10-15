# -*- coding: utf-8 -*-
"""Windows 系统通知（Toast），通过 PowerShell 调用系统接口，不需要额外安装。"""
import os
import subprocess
from xml.sax.saxutils import escape

# 借用 PowerShell 已注册的应用标识，系统才会显示通知
APP_ID = r"{1AC14E77-02E7-4E5D-B744-2EB1AE5198B7}\WindowsPowerShell\v1.0\powershell.exe"
SCRIPT = r"""
[Windows.UI.Notifications.ToastNotificationManager, Windows.UI.Notifications, ContentType = WindowsRuntime] > $null
[Windows.Data.Xml.Dom.XmlDocument, Windows.Data.Xml.Dom.XmlDocument, ContentType = WindowsRuntime] > $null
$xml = New-Object Windows.Data.Xml.Dom.XmlDocument
$xml.LoadXml($env:AIS_TOAST)
$toast = New-Object Windows.UI.Notifications.ToastNotification $xml
[Windows.UI.Notifications.ToastNotificationManager]::CreateToastNotifier($env:AIS_APPID).Show($toast)
"""
CREATE_NO_WINDOW = 0x08000000


def toast(title, body, sound=True):
    xml = ('<toast><visual><binding template="ToastGeneric">'
           f'<text>{escape(title)}</text><text>{escape(body)}</text>'
           '</binding></visual>'
           + ('<audio src="ms-winsoundevent:Notification.Default"/>' if sound else '<audio silent="true"/>')
           + '</toast>')
    env = dict(os.environ, AIS_TOAST=xml, AIS_APPID=APP_ID)
    try:
        subprocess.Popen(["powershell", "-NoProfile", "-NonInteractive", "-ExecutionPolicy", "Bypass",
                          "-WindowStyle", "Hidden", "-Command", SCRIPT],
                         env=env, creationflags=CREATE_NO_WINDOW,
                         stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    except Exception:
        try:
            import winsound
            winsound.MessageBeep(winsound.MB_ICONASTERISK)
        except Exception:
            pass
