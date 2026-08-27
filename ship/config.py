#!/usr/bin/env python3
import os
import pathlib
import subprocess
import json

def _load_dotenv():
    current_file = pathlib.Path(__file__).resolve()
    candidates = [
        pathlib.Path.cwd() / ".env",
        current_file.parent / ".env",
        current_file.parent.parent / ".env",
    ]
    for env_path in candidates:
        if env_path.is_file():
            try:
                with open(env_path, "r", encoding="utf-8") as f:
                    for line in f:
                        line = line.strip()
                        if line and not line.startswith("#") and "=" in line:
                            k, v = line.split("=", 1)
                            k, v = k.strip(), v.strip().strip("'\"")
                            if k not in os.environ:
                                os.environ[k] = v
            except Exception:
                pass
            break

_load_dotenv()

HOST = os.getenv("SHIP_HOST") or os.getenv("HOST") or "192.168.103.40"

STATIONS = {
    "Core Station": (0, 0),
    "Azura Station": (-1000, 1000),
    "Vesta Station": (7000, 7000),
    "Elyse Terminal": (-70565, 72811),
    "Shangris Station": (4446, 4340),
    "G-Station": (-19567, 16308),
}

STATION_ALIASES = {
    "1": "Core Station",
    "core": "Core Station",
    "corestation": "Core Station",
    "2": "Azura Station",
    "azura": "Azura Station",
    "azurastation": "Azura Station",
    "3": "Vesta Station",
    "vesta": "Vesta Station",
    "vestastation": "Vesta Station",
    "4": "Elyse Terminal",
    "elyse": "Elyse Terminal",
    "5": "Shangris Station",
    "shangris": "Shangris Station",
}

THRUSTER_PORTS = {
    1: 2003,  # Main Forward Propulsion
    2: 2004,  # Retro / Reverse / Braking Engine
    3: 2006,  # Starboard Maneuvering Thruster
    4: 2007,  # Yaw Right / Clockwise Turn
    5: 2008   # Yaw Left / Counter-Clockwise Turn
}

# execute regular curl command
def curl(cmd, parse_json=True):
    clean_cmd = cmd.removeprefix("curl ")
    res = subprocess.run(f"curl -s --max-time 5 {clean_cmd}", shell=True, capture_output=True, text=True)
    out = res.stdout.strip() or res.stderr.strip()
    if parse_json and out:
        try:
            return json.loads(out)
        except Exception:
            pass
    return out

# normalize station name alias
def normalize_station(name):
    clean = str(name).strip().lower()
    return STATION_ALIASES.get(clean, str(name).strip())
