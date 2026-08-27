#!/usr/bin/env python3
import subprocess
import json

HOST = "192.168.103.40"

STATIONS = {
    "Core Station": (0, 0),
    "Azura Station": (-1000, 1000),
    "Vesta Station": (7000, 7000),
    "Elyse Terminal": (-70565, 72811),
    "Shangris Station": (4446, 4340),
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
    1: 2003,  # Main Forward
    2: 2004,  # Port Lateral
    3: 2006,  # Starboard Lateral
    4: 2007,  # Yaw / Attitude
    5: 2008   # Retro / Braking
}

# execute regular curl command
def curl(cmd, parse_json=True):
    clean_cmd = cmd.removeprefix("curl ")
    res = subprocess.run(f"curl -s {clean_cmd}", shell=True, capture_output=True, text=True)
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
