import json
import os
import platform

def _sts2_data_dir() -> str:
    system = platform.system()
    if system == "Windows":
        return os.path.expandvars(r"%APPDATA%\SlaytheSpire2")
    elif system == "Darwin":
        return os.path.expanduser("~/Library/Application Support/SlayTheSpire2")
    else:
        return os.path.expanduser("~/.local/share/SlayTheSpire2")

def _app_config_dir() -> str:
    system = platform.system()
    if system == "Windows":
        return os.path.expandvars(r"%APPDATA%\jhf-tracker")
    elif system == "Darwin":
        return os.path.expanduser("~/Library/Application Support/jhf-tracker")
    else:
        return os.path.expanduser("~/.config/jhf-tracker")

CONFIG_DIR = _app_config_dir()
CONFIG_PATH = os.path.join(CONFIG_DIR, "config.json")

VERSION = "0.1.2"

DB_URL = "postgresql://neondb_owner:npg_VcGZ8TFAbx4m@ep-little-hat-aedez85o-pooler.c-2.us-east-2.aws.neon.tech/neondb?channel_binding=require&sslmode=require"


def _detect_steam_id() -> str:
    steam_dir = os.path.join(_sts2_data_dir(), "steam")
    try:
        accounts = [e for e in os.listdir(steam_dir) if os.path.isdir(os.path.join(steam_dir, e))]
    except FileNotFoundError:
        accounts = []

    if len(accounts) == 1:
        print(f"[config] Detected Steam ID: {accounts[0]}")
        return accounts[0]

    if len(accounts) > 1:
        print("Multiple Steam accounts found:")
        for i, a in enumerate(accounts):
            print(f"  {i + 1}. {a}")
        while True:
            choice = input("Select account number: ").strip()
            if choice.isdigit() and 1 <= int(choice) <= len(accounts):
                return accounts[int(choice) - 1]

    return input("Could not detect Steam ID. Enter it manually: ").strip()


def _create() -> dict:
    steam_id = _detect_steam_id()
    cfg = {"steam_id": steam_id, "profile": 1}
    os.makedirs(CONFIG_DIR, exist_ok=True)
    with open(CONFIG_PATH, "w") as f:
        json.dump(cfg, f, indent=2)
    print(f"[config] Saved to {CONFIG_PATH}")
    return cfg


def _load() -> dict:
    try:
        with open(CONFIG_PATH) as f:
            return json.load(f)
    except FileNotFoundError:
        return _create()


_cfg = _load()

STEAM_ID: str = _cfg["steam_id"]
PLAYER_ID: str = STEAM_ID
PROFILE: int = _cfg["profile"]
