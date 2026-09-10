#!/usr/bin/env python3
"""
================================================================================
   ARAKROCK MINING & VESTA DELIVERY — rewritten against documented endpoints
================================================================================
Ziel: Vollbeladen mit Stein bei Vesta Station (7000, 7000) andocken.
Stein wird bei Arakrock (-18236, -11783) abgebaut.

Why this version differs from the original:
  - docu.txt / ship_manual.md only document GET /hold on port 2012 for
    cargo — there is no documented /inventory endpoint. Switched to /hold.
  - There's no documented /laser/activate. Instead of assuming a call is
    required, this script just sits at Arakrock and watches /hold — if a
    resource count rises on its own, mining is automatic. If nothing
    changes after a while, it prints a clear message instead of silently
    assuming success.
  - There's no documented /deliver. The mission as described is just
    "dock fully loaded" — so this script flies to Vesta Station and
    confirms via /stations_in_reach, without calling a guessed endpoint.
  - Resource key name (STONE vs stone vs Stone) is auto-detected by
    diffing /hold before and after mining, instead of hardcoding a guess.

Run with --probe to just dump one raw /hold response and exit (useful for
inspecting the actual resource key names before running the full mission).
"""

import math
import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import config
import nav

# --------------------------------------------------------------------------
# CONFIG
# --------------------------------------------------------------------------
ARAKROCK = (-18236.0, -11783.0)
VESTA_STATION_NAME = "Vesta Station"
VESTA_COORDS = (7000.0, 7000.0)  # fallback if named-target fails
REQUIRED_UNITS = 12
MINING_TIMEOUT = 180.0  # seconds to wait for mining before giving up
MINING_POLL = 2.0  # seconds between /hold checks while mining
DOCK_TIMEOUT = 30.0
DOCK_POLL = 0.5


def get_hold():
    """Raw GET /hold on the documented cargo port (2012)."""
    data = config.curl(f"http://{config.HOST}:2012/hold")
    if isinstance(data, dict) and data.get("kind") == "success":
        return data.get("hold", {})
    return {}


def get_resources():
    return get_hold().get("resources", {})


def check_station_in_reach(name_fragment):
    reach = config.curl(f"http://{config.HOST}:2011/stations_in_reach")
    if isinstance(reach, dict) and reach.get("kind") == "success":
        for name in reach.get("stations", {}):
            if name_fragment.lower() in name.lower():
                return True
    return False


def probe():
    print("Raw /hold response:")
    import json

    print(json.dumps(get_hold(), indent=2))


def mine_at_arakrock():
    print(f"\nFlying to Arakrock {ARAKROCK} ...")
    nav.fly_to(ARAKROCK)

    baseline = get_resources()
    print(f"Resources on arrival: {baseline}")

    mined_key = None
    start = time.time()
    last_total = None

    while (time.time() - start) < MINING_TIMEOUT:
        time.sleep(MINING_POLL)
        current = get_resources()

        if mined_key is None:
            # figure out which resource key is rising compared to baseline
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
                f"\rWaiting for mining to start... ({elapsed:.0f}s, resources unchanged: {current})   ",
                end="",
                flush=True,
            )

    print()
    if mined_key is not None:
        print(f"Timed out, but collected {current.get(mined_key, 0)} of {mined_key}.")
        return mined_key, current.get(mined_key, 0)

    print(
        "No resource count changed the whole time — mining did not start "
        "automatically. This means Arakrock likely needs an explicit "
        "activation call we don't know the name of yet. Check the ship's "
        "live web dashboard 'Documentation' tab (it can differ from the "
        "static docu.txt/ship_manual.md files) for a laser/mining endpoint."
    )
    return None, 0


def dock_at_vesta():
    print(f"\nFlying to {VESTA_STATION_NAME} ...")
    try:
        nav.fly_to(VESTA_STATION_NAME)
    except Exception:
        nav.fly_to(VESTA_COORDS)

    start = time.time()
    while (time.time() - start) < DOCK_TIMEOUT:
        if check_station_in_reach("vesta"):
            print("Docked at Vesta Station.")
            return True
        time.sleep(DOCK_POLL)

    print("Could not confirm docking at Vesta Station within timeout.")
    return False


def main():
    if "--probe" in sys.argv:
        probe()
        return

    print("=" * 72)
    print("  ARAKROCK MINING -> VESTA DELIVERY")
    print("=" * 72)

    resources = get_resources()
    print(f"Current cargo: {resources}")

    key, count = mine_at_arakrock()

    if key is not None and count > 0:
        dock_at_vesta()
        final = get_resources()
        print(f"\nFinal cargo: {final}")
    else:
        print("\nMission incomplete: no resource was successfully mined.")

    nav.stop_ship()


if __name__ == "__main__":
    main()
