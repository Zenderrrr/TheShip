#!/usr/bin/env python3
"""
================================================================================
   FOLLOW G-STATION — circular-orbit intercept & pursuit
================================================================================
Assumptions (adjust the CONFIG block below if wrong):

  * G-Station orbits in a perfect circle around CENTER (default: Core
    Station at (0, 0) — "Core" + sitting at the origin makes it the most
    plausible hub).
  * The point you gave, (-19567, 16308), is a point ON that circle. Radius
    and starting angle are derived from it automatically.
  * Full revolution period = 90s  ->  angular speed = 4 deg/s.
  * Rotation direction (CW vs CCW) is UNKNOWN. The script guesses
    counter-clockwise first, then self-corrects: after a short probation
    window it checks whether it's actually closing distance to the
    station's predicted position; if it's diverging instead, it flips
    direction and keeps going.

How it works:
  1. Fly to the given meet-point (-19567, 16308) using the existing
     nav.fly_to() helper — this is t=0 for the orbit model.
  2. For FOLLOW_DURATION seconds, repeatedly:
       - compute where G-Station SHOULD be right now (+ a small lead time
         to compensate for our own travel latency)
       - set_target to that predicted point
       - poll our own /pos to see if distance-to-target is shrinking
       - after PROBATION seconds, if we're not converging, flip direction
  3. Stops the ship at the end.

Run this from the `ship/` directory so it can import config.py / nav.py.
"""

import math
import time
import sys

import config
import nav

# --------------------------------------------------------------------------
# CONFIG — tweak here if any assumption turns out wrong
# --------------------------------------------------------------------------
CENTER = (0.0, 0.0)                    # assumed orbit center (Core Station)
MEET_POINT = (-19567.0, 16308.0)       # given point on G-Station's orbit
PERIOD_S = 90.0                        # full revolution time
FOLLOW_DURATION = 60.0                 # how long to follow, in seconds
LEAD_TIME = 1.5                        # seconds to project ahead, compensates travel lag
POLL_INTERVAL = 0.5                    # seconds between control updates
PROBATION_S = 6.0                      # time before we trust the convergence check
ARRIVE_RADIUS = 25.0                   # matches nav.fly_to()'s "close enough" threshold

# --------------------------------------------------------------------------
# Orbit model
# --------------------------------------------------------------------------
cx, cy = CENTER
mx, my = MEET_POINT
RADIUS = math.hypot(mx - cx, my - cy)
THETA0 = math.atan2(my - cy, mx - cx)
OMEGA = 2 * math.pi / PERIOD_S  # rad/s magnitude


def station_pos(t, direction):
    """Predicted G-Station position at time t (s since meet-point), given
    a rotation direction (+1 = CCW, -1 = CW)."""
    theta = THETA0 + direction * OMEGA * t
    return (cx + RADIUS * math.cos(theta), cy + RADIUS * math.sin(theta))


def get_own_pos():
    data = config.curl(f"http://{config.HOST}:2011/pos")
    if isinstance(data, dict) and data.get("kind") == "success":
        p = data.get("pos", {})
        return p.get("x", 0.0), p.get("y", 0.0)
    return None


def follow():
    print(f"Orbit model: center={CENTER}, radius={RADIUS:.1f}, "
          f"theta0={math.degrees(THETA0):.2f} deg, omega={math.degrees(OMEGA):.2f} deg/s")

    print(f"Flying to meet-point {MEET_POINT} ...")
    nav.fly_to(MEET_POINT)

    direction = 1  # start with CCW guess
    t0 = time.time()
    last_dist = None
    flipped = False

    print(f"Starting {FOLLOW_DURATION:.0f}s pursuit, direction guess = "
          f"{'CCW' if direction == 1 else 'CW'} ...")

    try:
        while True:
            elapsed = time.time() - t0
            if elapsed >= FOLLOW_DURATION:
                break

            target = station_pos(elapsed + LEAD_TIME, direction)
            nav.set_target(target)

            own = get_own_pos()
            if own is not None:
                px, py = own
                tx, ty = station_pos(elapsed, direction)
                dist = math.hypot(tx - px, ty - py)

                print(f"t={elapsed:5.1f}s  own=({px:8.1f},{py:8.1f})  "
                      f"predicted_station=({tx:8.1f},{ty:8.1f})  dist={dist:7.1f}  "
                      f"dir={'CCW' if direction == 1 else 'CW'}", end="\r", flush=True)

                # self-correction: after probation, if we're clearly diverging
                # (and haven't already flipped once), try the other direction
                if not flipped and elapsed > PROBATION_S and last_dist is not None:
                    if dist > last_dist * 1.15 and dist > ARRIVE_RADIUS * 2:
                        print(f"\nNot converging (dist growing) — flipping rotation direction.")
                        direction *= -1
                        flipped = True
                        t0 = time.time() - elapsed  # keep same elapsed clock
                last_dist = dist

            time.sleep(POLL_INTERVAL)

    except KeyboardInterrupt:
        print("\nInterrupted by user.")

    print("\nFollow window complete. Stopping ship.")
    nav.stop_ship()


if __name__ == "__main__":
    follow()
