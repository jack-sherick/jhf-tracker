import os
import re
import time

import config
from logtypes import Encounter
import parser
import run_tracker
import save_reader

LOG_PATH = os.path.join(config._sts2_data_dir(), "logs", "godot.log")
OUT_PATH = os.path.join(config.CONFIG_DIR, "session.log")


def _detect_patch(f):
    pos = f.tell()
    f.seek(0)
    for line in f:
        m = re.search(r'\[INFO\] \[Sentry\.NET\] Initialized:.*release=(v[\S]+)', line)
        if m:
            run_tracker.set_patch(m.group(1))
            break
    f.seek(pos)


def _open_log():
    while True:
        try:
            f = open(LOG_PATH, "r", encoding="utf-8")
            _detect_patch(f)
            f.seek(0, 2)
            print("[listener] Opened log file")
            return f
        except FileNotFoundError:
            time.sleep(1)


def run():
    os.makedirs(config.CONFIG_DIR, exist_ok=True)

    if save_reader.detect_mode():
        save_reader.set_mode(True)
        parser.set_player_prefix(f"Player {config.STEAM_ID}")
        print("[listener] detected active multiplayer session")

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

                            for event in events:
                                if isinstance(event, Encounter) and event.mode == "Event":
                                    run_tracker.on_event_room(save_reader.read_save())
                                elif isinstance(event, Encounter) and event.mode == "Merchant":
                                    run_tracker.on_merchant_enter(save_reader.parse_save(save_reader.read_save()))
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
