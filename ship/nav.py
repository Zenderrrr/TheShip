#!/usr/bin/env python3
import math
import time
import json
import urllib.request
import urllib.error
import config

def _http_post(port, path, data):
    url = f"http://{config.HOST}:{port}/{path.lstrip('/')}"
    payload = json.dumps(data).encode("utf-8")
    req = urllib.request.Request(
        url,
        data=payload,
        headers={"Content-Type": "application/json"},
        method="POST"
    )
    try:
        with urllib.request.urlopen(req, timeout=2) as resp:
            content = resp.read().decode("utf-8")
            return json.loads(content) if content else {}
    except Exception as e:
        return {"kind": "error", "message": str(e)}

def _http_get(port, path):
    url = f"http://{config.HOST}:{port}/{path.lstrip('/')}"
    req = urllib.request.Request(url)
    try:
        with urllib.request.urlopen(req, timeout=2) as resp:
            content = resp.read().decode("utf-8")
            return json.loads(content) if content else {}
    except Exception as e:
        return {"kind": "error", "message": str(e)}

# set autopilot target
def set_target(target):
    if isinstance(target, str):
        st_name = config.normalize_station(target)
        if st_name in config.STATIONS:
            tx, ty = config.STATIONS[st_name]
            return _http_post(2009, "set_target", {"target": {"x": tx, "y": ty}})
        else:
            return _http_post(2009, "set_target", {"target": st_name})
    elif isinstance(target, (tuple, list)):
        tx, ty = target
        return _http_post(2009, "set_target", {"target": {"x": float(tx), "y": float(ty)}})
    else:
        return _http_post(2009, "set_target", {"target": str(target)})

# emergency stop ship
def stop_ship():
    return _http_post(2009, "set_target", {"target": "stop"})

# idle drift mode
def idle_ship():
    return _http_post(2009, "set_target", {"target": "idle"})

# fly to station name or tuple (x, y) and wait until arrived
def fly_to(target):
    is_named_station = isinstance(target, str)

    if is_named_station:
        station_name = config.normalize_station(target)
        tx, ty = config.STATIONS.get(station_name, (0, 0))
        target_name = station_name
    elif isinstance(target, (tuple, list)):
        tx, ty = target
        target_name = f"({tx:.1f}, {ty:.1f})"
    else:
        print(f"Invalid target: {target}")
        return

    # check if already in range
    pos_data = _http_get(2011, "pos")
    if isinstance(pos_data, dict) and pos_data.get("kind") == "success":
        pos = pos_data.get("pos", {})
        cx, cy = pos.get("x", 0), pos.get("y", 0)
        dist = math.hypot(tx - cx, ty - cy)
        if dist <= 25:
            print(f"Already in range of {target_name} (Distance: {dist:.1f}).")
            return

    print(f"Setting autopilot to {target_name}...")
    res = set_target(target)
    if isinstance(res, dict) and res.get("kind") == "error":
        print(f"Autopilot error: {res.get('message', 'Failed to set target')}")
        return

    try:
        while True:
            pos_data = _http_get(2011, "pos")
            if isinstance(pos_data, dict) and pos_data.get("kind") == "success":
                pos = pos_data.get("pos", {})
                cx, cy = pos.get("x", 0), pos.get("y", 0)
                dist = math.hypot(tx - cx, ty - cy)
                vel = pos_data.get("velocity", {})
                speed = math.hypot(vel.get("x", 0), vel.get("y", 0))
                print(f"Position: ({cx:.1f}, {cy:.1f}) | Speed: {speed:.1f} | Distance to {target_name}: {dist:.1f}      ", end="\r", flush=True)

                reach = _http_get(2011, "stations_in_reach")
                if (isinstance(reach, dict) and is_named_station and target_name in reach.get("stations", {})) or dist <= 25:
                    print(f"\nArrived at {target_name}! Stopping ship...")
                    stop_ship()
                    break

            time.sleep(0.3)
    except KeyboardInterrupt:
        print(f"\nFlight interrupted by user. Stopping ship...")
        stop_ship()

if __name__ == "__main__":
    import sys
    dest = sys.argv[1] if len(sys.argv) > 1 else "Core Station"
    fly_to(dest)