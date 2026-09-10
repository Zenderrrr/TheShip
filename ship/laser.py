#!/usr/bin/env python3
"""
================================================================================
   ARAKROCK MINING & VESTA DELIVERY — self-contained version
================================================================================
Ziel: Vollbeladen mit Stein bei Vesta Station (7000, 7000) andocken.
Stein wird bei Arakrock (-18236, -11783) abgebaut.

This version does NOT depend on config.curl() or nav.py, because the
config.py actually on this VM doesn't have a curl() function (it's a
different/newer version than the one this was originally written against).
It only uses config.HOST, config.STATIONS, and config.normalize_station,
which do exist — everything else (HTTP calls, flying, docking) is done
directly with urllib here.

Run with --probe to just dump one raw /hold response and exit.
"""

import json
import math
import os
import sys
import time
import urllib.error
import urllib.request

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import config

# --------------------------------------------------------------------------
# CONFIG
# --------------------------------------------------------------------------
ARAKROCK = (-18236.0, -11783.0)
VESTA_STATION_NAME = "Vesta Station"
REQUIRED_UNITS = 12
ARRIVE_RADIUS = 25.0

MINING_TIMEOUT = 180.0
MINING_POLL = 2.0
FLY_POLL = 0.5


# --------------------------------------------------------------------------
# Minimal HTTP helpers (replaces config.curl)
# --------------------------------------------------------------------------
def http_get(port, path):
    url = f"http://{config.HOST}:{port}/{path.lstrip('/')}"
    try:
        with urllib.request.urlopen(url, timeout=5) as resp:
            return json.loads(resp.read().decode())
    except Exception as e:
        return {"kind": "error", "message": str(e)}


def http_post(port, path, payload):
    url = f"http://{config.HOST}:{port}/{path.lstrip('/')}"
    data = json.dumps(payload).encode()
    req = urllib.request.Request(
        url, data=data, method="POST", headers={"Content-Type": "application/json"}
    )
    try:
        with urllib.request.urlopen(req, timeout=5) as resp:
            return json.loads(resp.read().decode())
    except Exception as e:
        return {"kind": "error", "message": str(e)}


# --------------------------------------------------------------------------
# Flight helpers (inline replacement for nav.py)
# --------------------------------------------------------------------------
def get_pos():
    data = http_get(2011, "pos")
    if data.get("kind") == "success":
        p = data.get("pos", {})
        return p.get("x", 0.0), p.get("y", 0.0)
    return None


def set_target(target):
    if isinstance(target, str):
        name = config.normalize_station(target)
        if name in config.STATIONS:
            tx, ty = config.STATIONS[name]
            return http_post(2009, "set_target", {"target": {"x": tx, "y": ty}})
        return http_post(2009, "set_target", {"target": name})
    tx, ty = target
    return http_post(2009, "set_target", {"target": {"x": tx, "y": ty}})


def stop_ship():
    return http_post(2009, "set_target", {"target": "stop"})


def station_in_reach(name_fragment):
    data = http_get(2011, "stations_in_reach")
    if data.get("kind") == "success":
        for name in data.get("stations", {}):
            if name_fragment.lower() in name.lower():
                return True
    return False


def fly_to(target, timeout=180.0):
    if isinstance(target, str):
        name = config.normalize_station(target)
        tx, ty = config.STATIONS.get(name, (0, 0))
        label = name
    else:
        tx, ty = target
        label = f"({tx}, {ty})"

    print(f"Flying to {label} ...")
    res = set_target(target)
    if res.get("kind") == "error":
        print(f"Autopilot error: {res.get('message')}")
        return False

    start = time.time()
    while (time.time() - start) < timeout:
        pos = get_pos()
        if pos:
            cx, cy = pos
            dist = math.hypot(tx - cx, ty - cy)
            print(
                f"\rPosition: ({cx:.1f}, {cy:.1f})  Distance to {label}: {dist:.1f}   ",
                end="",
                flush=True,
            )
            if dist <= ARRIVE_RADIUS or (
                isinstance(target, str) and station_in_reach(label)
            ):
                print(f"\nArrived at {label}.")
                stop_ship()
                return True
        time.sleep(FLY_POLL)

    print(f"\nTimed out flying to {label}.")
    return False


# --------------------------------------------------------------------------
# Mission logic
# --------------------------------------------------------------------------
def get_resources():
    data = http_get(2012, "hold")
    if data.get("kind") == "success":
        return data.get("hold", {}).get("resources", {})
    return {}


def probe():
    print("Raw /hold response:")
    print(json.dumps(http_get(2012, "hold"), indent=2))


def mine_at_arakrock():
    fly_to(ARAKROCK)

    baseline = get_resources()
    print(f"Resources on arrival: {baseline}")

    mined_key = None
    start = time.time()
    current = baseline

    while (time.time() - start) < MINING_TIMEOUT:
        time.sleep(MINING_POLL)
        current = get_resources()

        if mined_key is None:
            for key, val in current.items():
                if val > baseline.get(key, 0):
                    mined_key = key
                    break

        if mined_key is not None:
            count = current.get(mined_key, 0)
            filled = int(min(count / REQUIRED_UNITS, 1.0) * 20)
            bar = "#" * filled + "-" * (20 - filled)
            print(
                f"\rMining {mined_key}: [{bar}] {count}/{REQUIRED_UNITS}   ",
                end="",
                flush=True,
            )
            if count >= REQUIRED_UNITS:
                print()
                return mined_key, count
        else:
            elapsed = time.time() - start
            print(
                f"\rWaiting for mining to start... ({elapsed:.0f}s, resources: {current})   ",
                end="",
                flush=True,
            )

    print()
    if mined_key is not None:
        print(f"Timed out, but collected {current.get(mined_key, 0)} of {mined_key}.")
        return mined_key, current.get(mined_key, 0)

    print(
        "No resource count changed at all — mining isn't happening "
        "automatically. Check the ship's live web dashboard 'Documentation' "
        "tab for a mining/laser endpoint, since it may differ from the "
        "static docu.txt/ship_manual.md files."
    )
    return None, 0


def main():
    if "--probe" in sys.argv:
        probe()
        return

    print("=" * 72)
    print("  ARAKROCK MINING -> VESTA DELIVERY")
    print("=" * 72)
    print(f"Current cargo: {get_resources()}")

    key, count = mine_at_arakrock()

    if key is not None and count > 0:
        fly_to(VESTA_STATION_NAME)
        print(f"\nFinal cargo: {get_resources()}")
    else:
        print("\nMission incomplete: nothing was mined.")

    stop_ship()


if __name__ == "__main__":
    main()
