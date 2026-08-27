#!/usr/bin/env python3
import math
import time
import config

# set autopilot target
def set_target(target):
    if isinstance(target, str):
        st_name = config.normalize_station(target)
        if st_name in config.STATIONS:
            tx, ty = config.STATIONS[st_name]
            return config.curl(f'-XPOST http://{config.HOST}:2009/set_target -d \'{{"target": {{"x": {tx}, "y": {ty}}}}}\'')
        else:
            return config.curl(f'-XPOST http://{config.HOST}:2009/set_target -d \'{{"target": "{st_name}"}}\'')
    elif isinstance(target, (tuple, list)):
        tx, ty = target
        # set coordinate target
        return config.curl(f'-XPOST http://{config.HOST}:2009/set_target -d \'{{"target": {{"x": {tx}, "y": {ty}}}}}\'')
    else:
        # set target object
        return config.curl(f'-XPOST http://{config.HOST}:2009/set_target -d \'{{"target": "{target}"}}\'')

# emergency stop ship
def stop_ship():
    # stop autopilot
    return config.curl(f'-XPOST http://{config.HOST}:2009/set_target -d \'{{"target": "stop"}}\'')

# idle drift mode
def idle_ship():
    # set idle mode
    return config.curl(f'-XPOST http://{config.HOST}:2009/set_target -d \'{{"target": "idle"}}\'')

# fly to station name or tuple (x, y) and wait until arrived
def fly_to(target):
    is_named_station = isinstance(target, str)

    # resolve target coordinates
    if is_named_station:
        station_name = config.normalize_station(target)
        tx, ty = config.STATIONS.get(station_name, (0, 0))
        target_name = station_name
    elif isinstance(target, (tuple, list)):
        tx, ty = target
        target_name = f"({tx}, {ty})"
    else:
        print(f"Invalid target format: {target}. Must be station name or tuple (x, y).")
        return

    # check if already in range of target
    pos_data = config.curl(f"http://{config.HOST}:2011/pos")
    if isinstance(pos_data, dict) and pos_data.get("kind") == "success":
        pos = pos_data.get("pos", {})
        cx, cy = pos.get("x", 0), pos.get("y", 0)
        dist = math.hypot(tx - cx, ty - cy)
        if dist <= 25:
            print(f"Already in range of {target_name} (Distance: {dist:.1f}).")
            return

    # check nearby stations
    reach = config.curl(f"http://{config.HOST}:2011/stations_in_reach")
    if isinstance(reach, dict) and is_named_station and target_name in reach.get("stations", {}):
        print(f"Already docked at {target_name}.")
        return

    print(f"Setting autopilot to {target_name}...")
    res = set_target(target)
    if isinstance(res, dict) and res.get("kind") == "error":
        print(f"Autopilot error: {res.get('message', 'Failed to set target')}")
        return

    try:
        while True:
            # get ship position
            pos_data = config.curl(f"http://{config.HOST}:2011/pos")
            if isinstance(pos_data, dict) and pos_data.get("kind") == "success":
                pos = pos_data.get("pos", {})
                cx, cy = pos.get("x", 0), pos.get("y", 0)
                dist = math.hypot(tx - cx, ty - cy)
                vel = pos_data.get("velocity", {})
                speed = math.hypot(vel.get("x", 0), vel.get("y", 0))
                print(f"Position: ({cx:.1f}, {cy:.1f}) | Speed: {speed:.1f} | Distance to {target_name}: {dist:.1f}      ", end="\r", flush=True)

                # check docking reach
                reach = config.curl(f"http://{config.HOST}:2011/stations_in_reach")
                if (isinstance(reach, dict) and is_named_station and target_name in reach.get("stations", {})) or dist <= 25:
                    print(f"\nArrived at {target_name}! Stopping ship...")
                    stop_ship()
                    break

            time.sleep(0.5)
    except KeyboardInterrupt:
        print(f"\nFlight interrupted by user. Stopping ship...")
        stop_ship()

if __name__ == "__main__":
    import sys
    dest = sys.argv[1] if len(sys.argv) > 1 else "Core Station"
    fly_to(dest)