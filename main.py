import os
import sys

import config
import listener
import tray
import updater

APP_LOG = os.path.join(config.CONFIG_DIR, "app.log")

if getattr(sys, "frozen", False) and sys.platform != "win32":
    os.makedirs(config.CONFIG_DIR, exist_ok=True)
    _log_file = open(APP_LOG, "w", buffering=1)
    sys.stdout = sys.stderr = _log_file

print(f"[jhf-tracker] v{config.VERSION}")

if getattr(sys, "frozen", False):
    try:
        updater.check_and_update()
    except Exception as e:
        import traceback
        traceback.print_exc()
        input("[updater] Press Enter to continue...")

tray.run(listener.run, log_path=APP_LOG)
