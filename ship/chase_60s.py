#!/usr/bin/env python3
"""
================================================================================
     THE SHIP — ACTIVE 60-SECOND CONTINUOUS ORBIT PURSUIT & TETHER
================================================================================
Actively tracks and flies alongside 'G-Station 3-4' to maintain continuous
docking proximity (< 25 units) for 60 consecutive seconds.
"""

import time
import math
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import config
import nav

TARGET_STATION = "G-Station 3-4"
REQUIRED_SECONDS = 60.0
PERIOD = 95.7  # Measured orbital period in seconds
STAGING_COORDS = (-19567, 16308)

def main():
    print("=" * 72)
    print("      🛰️  ACTIVE 60-SECOND CONTINUOUS TETHER CONTROLLER")
    print("=" * 72)
    print(f"Target Object   : {TARGET_STATION}")
    print(f"Required Streak : {REQUIRED_SECONDS:.0f} continuous seconds")
    print(f"Estimated Period: {PERIOD:.1f}s")
    print("-" * 72)

    # 1. Staging
    pos_data = config.curl(f"http://{config.HOST}:2011/pos")
    if isinstance(pos_data, dict) and pos_data.get("kind") == "success":
        pos = pos_data.get("pos", {})
        cx, cy = pos.get("x", 0), pos.get("y", 0)
        dist = math.hypot(STAGING_COORDS[0] - cx, STAGING_COORDS[1] - cy)
        if dist > 35:
            print(f"Moving to staging area {STAGING_COORDS}...")
            nav.fly_to(STAGING_COORDS)
        else:
            print(f"In staging position ({cx:.1f}, {cy:.1f}).")
            nav.stop_ship()

    print("\nRadar active. Standing by for next pass...")
    
    continuous_streak = 0.0
    last_in_range = None
    following = False
    heading_angle = 0.0

    try:
        while continuous_streak < REQUIRED_SECONDS:
            now = time.time()
            reach = config.curl(f"http://{config.HOST}:2011/stations_in_reach")
            pos_data = config.curl(f"http://{config.HOST}:2011/pos")
            
            p = pos_data.get("pos", {}) if isinstance(pos_data, dict) else {}
            v = pos_data.get("velocity", {}) if isinstance(pos_data, dict) else {}
            ship_x, ship_y = p.get("x", 0.0), p.get("y", 0.0)
            ship_vx, ship_vy = v.get("x", 0.0), v.get("y", 0.0)

            in_range = False
            if isinstance(reach, dict) and reach.get("kind") == "success":
                st_dict = reach.get("stations", {})
                for st in st_dict:
                    if "g-station" in st.lower() or "3-4" in st:
                        in_range = True
                        break

            if in_range:
                if last_in_range is not None:
                    dt = now - last_in_range
                    continuous_streak += dt
                else:
                    continuous_streak = 0.1
                    following = True
                    print(f"\n⚡ [{time.strftime('%H:%M:%S')}] Contact established! Engaging active pursuit...")

                last_in_range = now

                # Dynamic orbit pursuit logic:
                # G-Station center is at (-19567, 16308)
                # We calculate tangential vector to orbit with the station
                dx = ship_x - STAGING_COORDS[0]
                dy = ship_y - STAGING_COORDS[1]
                r = math.hypot(dx, dy)
                if r < 5.0:
                    dx, dy = 10.0, 10.0
                    r = math.hypot(dx, dy)

                # Tangent velocity direction
                theta = math.atan2(dy, dx)
                # Next waypoint ahead along the orbit curve
                target_theta = theta + (2 * math.pi / PERIOD) * 2.0  # 2s lookahead
                target_x = STAGING_COORDS[0] + r * math.cos(target_theta)
                target_y = STAGING_COORDS[1] + r * math.sin(target_theta)

                # Nudge autopilot to target waypoint ahead
                config.curl(f'-XPOST http://{config.HOST}:2009/set_target -d \'{{"target": {{"x": {target_x:.1f}, "y": {target_y:.1f}}}}}\'')

                pct = min(100.0, (continuous_streak / REQUIRED_SECONDS) * 100)
                filled = int(pct / 100 * 25)
                bar = "█" * filled + "░" * (25 - filled)
                sys.stdout.write(
                    f"\r🟢 PURSUIT ACTIVE | Continuous: [{bar}] {continuous_streak:.1f}s / {REQUIRED_SECONDS:.0f}s ({pct:.0f}%) | "
                    f"Speed: {math.hypot(ship_vx, ship_vy):.1f}   "
                )
                sys.stdout.flush()

            else:
                if following:
                    print(f"\n🔴 Lost contact at {continuous_streak:.1f}s. Returning to staging area...")
                    continuous_streak = 0.0
                    following = False
                    nav.set_target(STAGING_COORDS)
                
                last_in_range = None
                sys.stdout.write(f"\r⏳ STANDBY for pass... Ship: ({ship_x:.0f}, {ship_y:.0f}) | Target: {TARGET_STATION}   ")
                sys.stdout.flush()

            time.sleep(0.1)

        print("\n" + "=" * 72)
        print(f"🎉 60-SECOND CONTINUOUS LOCK ACHIEVED ({continuous_streak:.1f}s)! Mission complete!")
        print("=" * 72)
        nav.stop_ship()

    except KeyboardInterrupt:
        print("\n\n⏹️ Pursuit stopped by user.")
        nav.stop_ship()

if __name__ == "__main__":
    main()
