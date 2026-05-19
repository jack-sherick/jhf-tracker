import json
import os
import platform
import ssl
import subprocess
import sys
import urllib.request

import certifi
import config

_SSL_CTX = ssl.create_default_context(cafile=certifi.where())

from secrets import GITHUB_TOKEN as _GITHUB_TOKEN
_API_URL = "https://api.github.com/repos/jack-sherick/jhf-tracker/releases?per_page=1"
_ASSET_NAME = {
    "Darwin": "jhf-tracker-mac",
    "Linux": "jhf-tracker-linux",
    "Windows": "jhf-tracker.exe",
}


def _parse_version(v: str) -> tuple:
    return tuple(int(x) for x in v.lstrip("v").split("-")[0].split("."))


def check_and_update():
    system = platform.system()
    asset_name = _ASSET_NAME.get(system)
    if not asset_name:
        return

    headers = {
        "Authorization": f"Bearer {_GITHUB_TOKEN}",
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
    }

    print(f"[updater] Checking for updates (current: {config.VERSION})...")
    try:
        req = urllib.request.Request(_API_URL, headers=headers)
        with urllib.request.urlopen(req, timeout=5, context=_SSL_CTX) as resp:
            releases = json.loads(resp.read())
            data = releases[0] if releases else {}
    except Exception as e:
        print(f"[updater] Could not check for updates: {e}")
        return

    latest_tag = data.get("tag_name", "")
    if not latest_tag or _parse_version(latest_tag) <= _parse_version(config.VERSION):
        print(f"[updater] Up to date")
        return

    asset_url = next(
        (a["url"] for a in data.get("assets", []) if a["name"] == asset_name),
        None,
    )
    if not asset_url:
        print(f"[updater] No asset '{asset_name}' found in release {latest_tag}")
        return

    print(f"[updater] Downloading {latest_tag}...")
    try:
        dl_headers = {**headers, "Accept": "application/octet-stream"}
        req = urllib.request.Request(asset_url, headers=dl_headers)
        with urllib.request.urlopen(req, timeout=60, context=_SSL_CTX) as resp:
            new_binary = resp.read()
    except Exception as e:
        print(f"[updater] Download failed: {e}")
        return

    current = os.path.abspath(sys.argv[0])
    tmp = current + ".new"
    try:
        with open(tmp, "wb") as f:
            f.write(new_binary)
    except Exception as e:
        print(f"[updater] Download failed to write: {e}")
        return

    print(f"[updater] Updated to {latest_tag}. Restarting...")

    if system == "Windows":
        bat = current + ".update.bat"
        bat_content = (
            "@echo off\n"
            "ping -n 3 127.0.0.1 >NUL\n"
            f"move /Y \"{tmp}\" \"{current}\"\n"
            f"start \"\" \"{current}\"\n"
            f"del \"{bat}\"\n"
        )
        try:
            with open(bat, "w") as f:
                f.write(bat_content)
            subprocess.Popen(
                ["cmd", "/c", bat],
                creationflags=subprocess.DETACHED_PROCESS | subprocess.CREATE_NO_WINDOW,
                close_fds=True,
            )
        except Exception as e:
            print(f"[updater] Failed to launch updater script: {e}")
            try:
                os.remove(tmp)
            except OSError:
                pass
            return
        sys.exit(0)
    else:
        try:
            os.chmod(tmp, 0o755)
            os.replace(tmp, current)
        except Exception as e:
            print(f"[updater] Failed to replace binary: {e}")
            try:
                os.remove(tmp)
            except OSError:
                pass
            return
        os.execv(current, sys.argv)
