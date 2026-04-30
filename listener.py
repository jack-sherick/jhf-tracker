import ctypes
import ctypes.wintypes
import sys
import time
import os

import config

import parser
import run_tracker
import save_reader

_HANDLER = ctypes.WINFUNCTYPE(ctypes.c_bool, ctypes.wintypes.DWORD)
_handler_ref = _HANDLER(lambda event: sys.exit(0) or False)
ctypes.windll.kernel32.SetConsoleCtrlHandler(_handler_ref, True)

LOG_PATH = os.path.expandvars(
    r"%APPDATA%\SlaytheSpire2\logs\godot.log"
)

os.makedirs(config.CONFIG_DIR, exist_ok=True)
OUT_PATH = os.path.join(config.CONFIG_DIR, "session.log")


def _open_log():
    while True:
        try:
            f = open(LOG_PATH, "r", encoding="utf-8")
            f.seek(0, 2)
            print("[listener] Opened log file")
            return f
        except FileNotFoundError:
            time.sleep(1)


with open(OUT_PATH, "w", encoding="utf-8") as out:

    f = _open_log()
    try:
        while True:
            line = f.readline()

            if line:
                if line.startswith("[INFO]"):
                    try:
                        events = parser.parse(line)
                        run_tracker.process(line, events)

                        if line.startswith("[INFO] Wrote"):
                            snapshot = save_reader.parse_save(save_reader.read_save())
                            run_tracker.on_save(snapshot)
                    except Exception as e:
                        print(f"[listener] Error processing line: {e}\n  Line: {line.strip()}")

                    if not line.startswith("[INFO] Wrote"):
                        out.write(line + "\n")
                        out.flush()

            else:
                # even if the game is closed, a log file will be present if there is an active run. 
                # this fixes a case where there is no active run and the script is ran before a log file exists
                # but obviously is very ugly
                try:
                    if f.tell() > os.path.getsize(LOG_PATH):
                        print("[listener] Log file replaced, reopening...")
                        f.close()
                        f = _open_log()
                except FileNotFoundError:
                    print("[listener] Log file missing, waiting...")
                    f.close()
                    f = _open_log()

                time.sleep(0.5)
    finally:
        f.close()
