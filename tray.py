import math
import os
import platform
import sys
import threading
import time

import pystray
from PIL import Image, ImageDraw

_console_visible = False


def _icon_path():
    base = getattr(sys, "_MEIPASS", os.path.dirname(os.path.abspath(__file__)))
    return os.path.join(base, "assets", "stoke.png")


def _make_icon(size: int = 64) -> Image.Image:
    img = Image.open(_icon_path()).convert("RGBA")
    w, h = img.size
    scale = max(size / w, size / h)
    new_w, new_h = math.ceil(w * scale), math.ceil(h * scale)
    scaled = img.resize((new_w, new_h), Image.LANCZOS)
    x, y = 0, new_h - size
    cropped = scaled.crop((x, y, x + size, y + size))
    mask = Image.new("L", (size, size), 0)
    ImageDraw.Draw(mask).ellipse((0, 0, size - 1, size - 1), fill=255)
    result = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    result.paste(cropped, mask=mask)
    return result


def _get_console_hwnd():
    import ctypes
    return ctypes.windll.kernel32.GetConsoleWindow()


def _set_console_visible(visible: bool):
    import ctypes
    hwnd = _get_console_hwnd()
    if hwnd:
        ctypes.windll.user32.ShowWindow(hwnd, 5 if visible else 0)


def run(listener_fn):
    global _console_visible
    image = _make_icon()

    is_windows = platform.system() == "Windows"
    if is_windows:
        _set_console_visible(False)

    def on_toggle_console(icon, item):
        global _console_visible
        _console_visible = not _console_visible
        _set_console_visible(_console_visible)

    def on_quit(icon, item):
        icon.stop()
        sys.exit(0)

    menu_items = []
    if is_windows:
        menu_items.append(
            pystray.MenuItem(
                lambda item: "Hide Logs" if _console_visible else "Show Logs",
                on_toggle_console,
            )
        )
    menu_items.append(pystray.MenuItem("Quit", on_quit))

    icon = pystray.Icon(
        "jhf-tracker",
        image,
        "jhf-tracker",
        menu=pystray.Menu(*menu_items),
    )

    threading.Thread(target=listener_fn, daemon=True).start()
    threading.Thread(target=icon.run, daemon=True).start()

    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        icon.stop()
        sys.exit(0)
