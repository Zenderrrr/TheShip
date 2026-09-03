#!/usr/bin/env python3
"""
================================================================================
          THE SHIP — G-STATION 3-4 60-SECOND TETHER & CONTACT TRACKER
================================================================================
Monitors and logs contact with the moving 'G-Station 3-4' until reaching
the required 60-second threshold.
"""

import time
import math
import sys
import os

# Add script directory to python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import config
import nav

TARGET_STATION = "G-Station 3-4"
REQUIRED_SECONDS = 60
STAGING_COORDS = (-19567, 16308)

def main():
    print("=" * 70)
    print("      🛰️  THE SHIP — G-STATION 3-4 (60s PROXIMITY TRACKER)")
    print("=" * 70)
    print(f"Staging Location : G-Station {STAGING_COORDS}")
    print(f"Target Object    : {TARGET_STATION}")
    print(f"Target Duration  : {REQUIRED_SECONDS} seconds")
    print("-" * 70)

    # 1. Check if already near staging coordinates
    pos_data = config.curl(f"http://{config.HOST}:2011/pos")
    if isinstance(pos_data, dict) and pos_data.get("kind") == "success":
        pos = pos_data.get("pos", {})
        dist = math.hypot(STAGING_COORDS[0] - pos.get("x", 0), STAGING_COORDS[1] - pos.get("y", 0))
        if dist > 35:
            print(f"🚀 Flying to G-Station staging coordinates {STAGING_COORDS}...")
            nav.set_target(STAGING_COORDS)
            while True:
                p_data = config.curl(f"http://{config.HOST}:2011/pos")
                if isinstance(p_data, dict) and p_data.get("kind") == "success":
                    p = p_data.get("pos", {})
                    d = math.hypot(STAGING_COORDS[0] - p.get("x", 0), STAGING_COORDS[1] - p.get("y", 0))
                    sys.stdout.write(f"\rApproaching G-Station... Distance: {d:.1f} units   ")
                    sys.stdout.flush()
                    if d <= 25:
                        print("\n✅ Arrived in position.")
                        nav.stop_ship()
                        break
                time.sleep(0.5)
        else:
            print(f"✅ In position at G-Station ({pos.get('x'):.1f}, {pos.get('y'):.1f}).")
            nav.stop_ship()

    total_accumulated = 0.0
    current_streak = 0.0
    last_contact_time = None
    pass_count = 0
    in_pass = False

    print(f"\n📡 Radar active. Monitoring for '{TARGET_STATION}' passes...")
    print("-" * 70)

    try:
        while total_accumulated < REQUIRED_SECONDS:
            now = time.time()
            reach = config.curl(f"http://{config.HOST}:2011/stations_in_reach")
            pos_data = config.curl(f"http://{config.HOST}:2011/pos")

            p = pos_data.get("pos", {}) if isinstance(pos_data, dict) else {}
            
            contact = False
            detected_name = None
            if isinstance(reach, dict) and reach.get("kind") == "success":
                st_dict = reach.get("stations", {})
                for st in st_dict:
                    if "g-station" in st.lower() or "3-4" in st:
                        contact = True
                        detected_name = st
                        break

            if contact:
                if not in_pass:
                    pass_count += 1
                    in_pass = True
                    print(f"\n⚡ [{time.strftime('%H:%M:%S')}] Pass #{pass_count} STARTED! Contact with '{detected_name}'")

                if last_contact_time is not None:
                    dt = now - last_contact_time
                    current_streak += dt
                    total_accumulated += dt
                last_contact_time = now

                pct = min(100.0, (total_accumulated / REQUIRED_SECONDS) * 100)
                filled = int(pct / 100 * 25)
                bar = "█" * filled + "░" * (25 - filled)
                
                sys.stdout.write(
                    f"\r🟢 IN CONTACT | Pass #{pass_count} Streak: {current_streak:.1f}s | "
                    f"Total: [{bar}] {total_accumulated:.1f}/{REQUIRED_SECONDS}s ({pct:.0f}%)   "
                )
                sys.stdout.flush()
            else:
                if in_pass:
                    print(f"\n🔴 [{time.strftime('%H:%M:%S')}] Pass #{pass_count} ENDED (Duration: {current_streak:.1f}s). Total so far: {total_accumulated:.1f}s / {REQUIRED_SECONDS}s")
                    in_pass = False
                    current_streak = 0.0

                last_contact_time = None
                pct = min(100.0, (total_accumulated / REQUIRED_SECONDS) * 100)
                filled = int(pct / 100 * 25)
                bar = "█" * filled + "░" * (25 - filled)

                sys.stdout.write(
                    f"\r⏳ STANDBY... | Passes: {pass_count} | "
                    f"Total: [{bar}] {total_accumulated:.1f}/{REQUIRED_SECONDS}s ({pct:.0f}%) | "
                    f"Ship: ({p.get('x', 0):.0f}, {p.get('y', 0):.0f})   "
                )
                sys.stdout.flush()

            time.sleep(0.1)

        print("\n" + "=" * 70)
        print(f"🎉 MISSION ACCOMPLISHED! Reached {total_accumulated:.1f}s in proximity of {TARGET_STATION}!")
        print("=" * 70)
        nav.stop_ship()

    except KeyboardInterrupt:
        print("\n\n⏹️ Tracker paused by user.")
        nav.stop_ship()

if __name__ == "__main__":
    main()
