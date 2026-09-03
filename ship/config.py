#!/usr/bin/env python3
import os
import pathlib

for p in [pathlib.Path.cwd() / ".env", pathlib.Path(__file__).parent / ".env", pathlib.Path(__file__).parent.parent / ".env"]:
    if p.is_file():
        with open(p) as f:
            for line in f:
                if "=" in line and not line.strip().startswith("#"):
                    k, v = line.strip().split("=", 1)
                    os.environ.setdefault(k.strip(), v.strip().strip("'\""))
        break

HOST = os.getenv("SHIP_HOST", os.getenv("HOST", "127.0.0.1"))

STATIONS = {
    "Core Station": (0, 0),
    "Azura Station": (-1000, 1000),
    "Vesta Station": (7000, 7000),
    "Elyse Terminal": (-70565, 72811),
    "Shangris Station": (4446, 4340),
    "G-Station": (-19567, 16308),
}

ALIASES = {
    "1": "Core Station", "core": "Core Station",
    "2": "Azura Station", "azura": "Azura Station",
    "3": "Vesta Station", "vesta": "Vesta Station",
    "4": "Elyse Terminal", "elyse": "Elyse Terminal",
    "5": "Shangris Station", "shangris": "Shangris Station",
    "6": "G-Station", "g-station": "G-Station", "g": "G-Station"
}

THRUSTERS = {1: 2003, 2: 2004, 3: 2006, 4: 2007, 5: 2008}

def normalize_station(name):
    return ALIASES.get(str(name).strip().lower(), str(name).strip())
